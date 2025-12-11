from __future__ import annotations

from pathlib import Path
import datetime
import re
from typing import Optional, Iterable
from functools import lru_cache

import time
import argparse
import urllib.request
import urllib.error

from unidecode import unidecode

import subprocess

import tempfile

from .config import load_config, BridgeConfig

import logging
import os

from .storage import LocalTask, TaskSyncResult, get_known_task_ids, record_task_sync_results
from .todo import TodoContext, provider_from_env
from .sync import SyncContext, provider_from_env as sync_provider_from_env
from .notes import NoteContext, NoteMetadata, StatusStats, provider_from_env as note_provider_from_env
from .notifications import (
    NotificationPayload,
    NotificationSeverity,
    NotificationContext,
    providers_from_env as notification_providers_from_env,
)
from .__version__ import __version__

# Load environment variables from project .env before reading them, using a simple KEY=VALUE parser
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"

def _load_env_from_file(path: Path) -> None:
    """Minimal .env loader: parses KEY=VALUE lines, ignores others, and does not overwrite existing env vars."""
    if not path.exists():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        if not key:
            continue
        if key not in os.environ:
            os.environ[key] = val

_load_env_from_file(ENV_PATH)

# Determine verbose mode from environment variable SUPERSIDIAN_VERBOSE
VERBOSE = os.environ.get("SUPERSIDIAN_VERBOSE", "0") == "1"

# Notification mode: all, errors, none
_raw_notify_mode = os.environ.get("SUPERSIDIAN_WEBHOOK_NOTIFICATIONS", "errors")
NOTIFY_MODE = _raw_notify_mode.strip().strip("'\"").lower()
if NOTIFY_MODE not in {"all", "errors", "none"}:
    NOTIFY_MODE = "errors"


HEALTHCHECK_URL = os.environ.get("SUPERSIDIAN_HEALTHCHECK_URL")
SUPERNOTE_TOOL = os.environ.get("SUPERSIDIAN_SUPERNOTE_TOOL") or "supernote-tool"


def ping_healthcheck(suffix: str = "") -> None:
    """Ping healthchecks.io (or compatible endpoint) if configured.

    Uses SUPERSIDIAN_HEALTHCHECK_URL as the base; appends an optional suffix
    such as "/start" or "/fail". Any network errors are swallowed so that
    healthcheck outages do not break the main run.
    """
    if not HEALTHCHECK_URL:
        return
    url = HEALTHCHECK_URL.rstrip("/") + suffix
    try:
        with urllib.request.urlopen(url, timeout=5):
            pass
    except Exception as e:
        if VERBOSE:
            log.debug(f"healthcheck ping to {url} failed: {e}")

_default_log_path = Path.home() / ".supersidian.log"
LOG_PATH = Path(os.environ.get("SUPERSIDIAN_LOG_PATH")) if os.environ.get("SUPERSIDIAN_LOG_PATH") else _default_log_path

logging.basicConfig(
    level=logging.DEBUG if VERBOSE else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler() if VERBOSE else logging.NullHandler()
    ]
)

log = logging.getLogger("supersidian")

if VERBOSE:
    log.debug(
        f"Startup configuration: VERBOSE={VERBOSE}, NOTIFY_MODE='{NOTIFY_MODE}'"
    )


BULLET_CHARS = "•–—*-+·►"


class ExtractionError(Exception):
    def __init__(self, kind: str, message: str):
        self.kind = kind
        super().__init__(message)


# Helper to run supernote-tool with retries for transient Dropbox/CloudStorage errors
def run_supernote_tool(args: list[str], retries: int = 4, initial_delay: float = 1.0) -> subprocess.CompletedProcess[str]:
    """Run supernote-tool with exponential backoff retry for transient errors.

    In particular, we retry on cases where the underlying filesystem reports
    a temporary deadlock (e.g. Dropbox/CloudStorage race conditions) which
    surface in supernote-tool's stderr as "Resource deadlock avoided" or
    "[Errno 11]". Other failures are propagated immediately.

    Uses exponential backoff: 1s, 2s, 4s, 8s for better handling of
    cloud storage sync delays.

    For convert operations, if all retries fail with EDEADLK, attempts to
    copy the input file to a temporary location and retry the operation
    there to work around CloudStorage filesystem issues.

    Args:
        args: Command line arguments for supernote-tool
        retries: Number of retry attempts (default: 4, for 5 total attempts)
        initial_delay: Initial delay in seconds (default: 1.0, doubles each retry)

    Returns:
        CompletedProcess from successful run

    Raises:
        CalledProcessError: If all retries exhausted or non-transient error
    """
    last_err: subprocess.CalledProcessError | None = None
    is_convert_cmd = len(args) > 1 and args[1] == "convert"
    input_file = Path(args[2]) if is_convert_cmd and len(args) > 2 else None

    for attempt in range(retries + 1):
        try:
            return subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=True,
                close_fds=True,  # Prevent file descriptor inheritance issues with CloudStorage
            )
        except subprocess.CalledProcessError as e:
            last_err = e
            msg = (e.stderr or "").strip() or (e.stdout or "").strip() or str(e)
            if ("Resource deadlock avoided" in msg or "[Errno 11]" in msg) and attempt < retries:
                # Exponential backoff: 1s, 2s, 4s, 8s
                delay = initial_delay * (2 ** attempt)
                if VERBOSE:
                    log.warning(
                        f"supernote-tool transient EDEADLK (attempt {attempt + 1}/{retries}), "
                        f"retrying in {delay:.1f}s..."
                    )
                time.sleep(delay)
                continue
            # Not a transient deadlock, or out of retries: propagate
            raise

    # Should not be reached, but keeps type checkers happy
    raise last_err  # type: ignore[misc]


def extract_text(note_path: Path) -> Optional[str]:
    # Use a temporary file because supernote-tool's txt output is designed for file targets
    try:
        with tempfile.NamedTemporaryFile(mode="r+", suffix=".txt", delete=False) as tmp:
            tmp_path = tmp.name
        result = run_supernote_tool(
            [
                SUPERNOTE_TOOL,
                "convert",
                "-t",
                "txt",
                "-a",
                str(note_path),
                tmp_path,
            ]
        )
    except FileNotFoundError:
        msg = f"supernote-tool not found on PATH; cannot extract text for {note_path}"
        log.error(msg)
        raise ExtractionError("tool_missing", msg)
    except subprocess.CalledProcessError as e:
        msg = e.stderr.strip() if e.stderr else str(e)
        log.error(f"supernote-tool failed for {note_path}: {msg}")
        raise ExtractionError("tool_failed", msg)

    # Read the temporary output file
    try:
        with open(tmp_path, "r", encoding="utf-8") as f:
            txt = f.read()
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    return txt.strip() or None


def unwrap_and_markdown(text: str, aggressive: bool = False) -> str:
    bullet_start = re.compile(
        rf"^\s*(?:[{re.escape(BULLET_CHARS)}]|\[[ xX]\])\s+"
    )
    numbered_start = re.compile(r"^\s*\d+[\.)]\s+")
    heading_start = re.compile(r"^\s*#{1,6}\s+")
    taskish_start = re.compile(r"^\s*(?:\(\]|I\]|1\]|l\]|\|\]|☐|☑|☒|\[×\])")

    def _cap_first_letter(s: str) -> str:
        """Capitalize the first alphabetic character in the string, leaving the rest unchanged."""
        for i, ch in enumerate(s):
            if ch.isalpha():
                return s[:i] + ch.upper() + s[i+1:]
        return s

    raw = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    last_heading_index = -10  # Track the last heading we saw

    for i, line in enumerate(raw):
        if i == 0:
            out.append(line)
            if heading_start.match(line):
                last_heading_index = 0
            continue

        prev = out[-1]
        prev_blank = prev.strip() == ""
        curr_blank = line.strip() == ""

        curr_new_block = (
            bullet_start.match(line)
            or numbered_start.match(line)
            or heading_start.match(line)
            or taskish_start.match(line)
            or curr_blank
        )

        prev_hard = prev_blank or prev.endswith("  ")
        prev_hyphen = bool(re.search(r"[^\s-]-$", prev))
        prev_heading = bool(heading_start.match(prev))

        # Update heading tracker
        if heading_start.match(line):
            last_heading_index = len(out)

        # Detect if current line looks like a list item (starts with capital letter)
        # This helps when OCR misses checkbox markers
        curr_looks_like_item = line and line.lstrip() and line.lstrip()[0].isupper()

        # Within 5 lines after a heading, preserve line breaks (likely list items)
        lines_since_heading = len(out) - last_heading_index
        near_heading = lines_since_heading <= 5

        # Don't merge lines after headings, near headings, or lines that look like new items
        if not prev_hard and not curr_new_block and not prev_heading and not curr_looks_like_item and not near_heading:
            if prev_hyphen:
                out[-1] = prev[:-1] + line.lstrip()
            else:
                out[-1] = prev.rstrip() + " " + line.lstrip()
        else:
            out.append(line)

    nest_rx = re.compile(r"^(\s*)(-{1,6})\s+(.*)$")

    task_rx = re.compile(r"^(\s*)\[( |x|X)\]\s+(.*)$")

    bullet_rx = re.compile(
        rf"^(\s*)(?:[{re.escape(BULLET_CHARS)}]|\[[ xX]\])\s+"
    )
    num_rx = re.compile(r"^(\s*)(\d+)[\.)]\s+")

    final: list[str] = []

    for line in out:
        if line.strip() == "" or heading_start.match(line):
            final.append(line.rstrip())
            continue

        # Normalize common Supernote checkbox variants and bracket mis-OCRs into ASCII forms so task_rx can see them.
        line = (
            line.replace("☐", "[ ]")
                .replace("☑", "[x]")
                .replace("☒", "[x]")
                .replace("[×]", "[x]")
                # Full-width / decorative bracket characters
                .replace("［", "[")
                .replace("【", "[")
                .replace("〖", "[")
                .replace("『", "[")
                .replace("］", "]")
                .replace("】", "]")
                .replace("〗", "]")
                .replace("』", "]")
                # Common mis-OCR of leading bracket into similar glyphs before ']'
                .replace("(]", "[ ]")
                .replace("I]", "[ ]")
                .replace("1]", "[ ]")
                .replace("l]", "[ ]")
                .replace("|]", "[ ]")
        )

        # 0) Split lines that contain "- -" (or "- --" etc.) in the middle into
        #    a prefix line + a nested bullet line.
        #    Example: "- Question? - -Answer" -> "- Question?" + "    - Answer"
        mid = re.match(r"^(\s*)(.*\S)\s+-\s+(-{1,6})\s*(.*)$", line)
        if mid:
            base_indent, prefix, extra_hyphens, content = mid.groups()
            # First, keep the prefix text as its own line
            final.append(f"{base_indent}{prefix.rstrip()}")

            # Then, treat the trailing "- -..." part as a nested bullet
            level = 1 + len(extra_hyphens)  # one leading '-' implied + N extra
            extra_indent = "    " * max(level - 1, 0)
            text_content = _cap_first_letter(content.rstrip())
            final.append(f"{base_indent}{extra_indent}- {text_content}")
            continue

        # 0) Handle lines like "- -text" or "- -- text" as nested bullets
        special = re.match(r"^(\s*)-\s+(-{1,6})\s*(.*)$", line)
        if special:
            base_indent, extra_hyphens, content = special.groups()
            # One leading '-' (the Supernote bullet) plus N extra hyphens => level N+1
            level = 1 + len(extra_hyphens)
            extra_indent = "    " * max(level - 1, 0)
            text_content = _cap_first_letter(content.rstrip())
            final.append(f"{base_indent}{extra_indent}- {text_content}")
            continue

        # 1) Handle explicit nesting markers -, --, --- at line start
        m = nest_rx.match(line)
        if m:
            base_indent, hyphens, content = m.groups()
            level = len(hyphens)  # 1..6
            extra_indent = "    " * max(level - 1, 0)
            text_content = _cap_first_letter(content.rstrip())
            final.append(f"{base_indent}{extra_indent}- {text_content}")
            continue

        # 1.5) Handle explicit task lines like "[ ] text" or "[x] text"
        m = task_rx.match(line)
        if m:
            indent, mark, content = m.groups()
            mark_char = "x" if mark.lower() == "x" else " "
            text_content = _cap_first_letter(content.rstrip())
            final.append(f"{indent}- [{mark_char}] {text_content}")
            continue

        # 2) Handle "normal" bullet characters (•, *, etc.)
        m = bullet_rx.match(line)
        if m:
            indent = m.group(1) or ""
            content = bullet_rx.sub("", line).rstrip()

            # Allow explicit nesting markers after a Supernote bullet, e.g. "• -- text"
            nested = re.match(r"^(-{1,6})\s+(.*)$", content)
            if nested:
                hyphens, nested_content = nested.groups()
                level = len(hyphens)  # 1..6
                extra_indent = "    " * max(level - 1, 0)
                text_content = _cap_first_letter(nested_content.rstrip())
                final.append(f"{indent}{extra_indent}- {text_content}")
            else:
                text_content = _cap_first_letter(content)
                final.append(f"{indent}- {text_content}")
            continue

        # 3) Numbered list
        m = num_rx.match(line)
        if m:
            indent, n = m.groups()
            content = num_rx.sub("", line).rstrip()
            text_content = _cap_first_letter(content)
            final.append(f"{indent}{n}. {text_content}")
            continue

        final.append(line.rstrip())

    if aggressive:
        final = apply_aggressive_cleanups(final)

    return ("\n".join(final)).strip() + "\n"


def apply_aggressive_cleanups(lines: list[str]) -> list[str]:
    """Extra heuristics to fix common Supernote RT quirks:

    - Split inline headings that ended up on the same line as bullets/text.
      e.g. "second bullets ##Subheading" -> "second bullets" + "## Subheading"
    - Normalize heading spacing: "##Subheading" -> "## Subheading".
    """
    cleaned: list[str] = []

    for raw in lines:
        # Normalize headings starting at column 0: "##Title" -> "## Title"
        m = re.match(r"^(\s*)(#{1,6})\s*(\S.*)$", raw)
        if m and m.group(2):
            indent, hashes, title = m.groups()
            # If there is nothing before the hashes, treat as a heading-only line
            if raw.lstrip().startswith(hashes):
                cleaned.append(f"{indent}{hashes} {title.strip()}")
                continue

        # Look for inline headings later in the line: "... ##Heading"
        inline = re.search(r"(#{1,6})\s*(\S.*)$", raw)
        if inline:
            hash_pos = raw.rfind(inline.group(1))
            if hash_pos > 0:
                prefix = raw[:hash_pos]
                heading = raw[hash_pos:]

                if prefix.strip():
                    m_head = re.match(r"\s*(#{1,6})\s*(\S.*)$", heading)
                    if m_head:
                        hashes, title = m_head.groups()
                        heading_line = f"{hashes} {title.strip()}"
                    else:
                        heading_line = heading.strip()

                    cleaned.append(prefix.rstrip())
                    cleaned.append(heading_line)
                    continue

        cleaned.append(raw)

    return cleaned


# Regex and helper to extract tasks from rendered Markdown
TASK_LINE_RX = re.compile(r"^(\s*)-\s\[( |x|X)\]\s+(.*)$")

def extract_tasks_from_markdown(
    md_body: str,
    bridge: BridgeConfig,
    rel_md_path: Path,
) -> list[LocalTask]:
    """Scan the Markdown body for Obsidian-style tasks and return LocalTask objects.

    This does not perform any provider sync; it only identifies tasks and
    assigns a stable local_id based on bridge, note path, and line number.
    """

    tasks: list[LocalTask] = []
    vault_name = bridge.vault_path.name
    note_rel = rel_md_path.as_posix()

    for idx, line in enumerate(md_body.splitlines(), start=1):
        m = TASK_LINE_RX.match(line)
        if not m:
            continue

        _, mark, title = m.groups()
        title = title.strip()
        if not title:
            continue

        completed = mark.lower() == "x"
        local_id = f"{bridge.name}:{note_rel}:{idx}"

        tasks.append(
            LocalTask(
                local_id=local_id,
                bridge_name=bridge.name,
                vault_name=vault_name,
                note_path=note_rel,
                line_no=idx,
                title=title,
                completed=completed,
            )
        )

    if VERBOSE and tasks:
        log.debug(
            f"[{bridge.name}] detected {len(tasks)} task(s) in {note_rel}"
        )

    return tasks


def apply_replacements(text: str, repl: dict[str, str]) -> str:
    """Apply whole-word replacements to text based on a mapping.

    Only exact whole-word matches are replaced to avoid mangling substrings.
    """
    if not repl:
        return text

    # Build a regex that matches any of the keys as whole words
    pattern = re.compile(r"\b(" + "|".join(re.escape(k) for k in repl.keys()) + r")\b")

    def _sub(m: re.Match) -> str:
        word = m.group(0)
        return repl.get(word, word)

    return pattern.sub(_sub, text)


def send_notifications(
    providers: list,
    bridge: BridgeConfig,
    notes_found: int,
    converted: int,
    skipped: int,
    no_text: int,
    tool_missing: int,
    tool_failed: int,
    supernote_missing: bool,
    vault_missing: bool,
    always_send: bool = False,
) -> None:
    """Send notifications to all configured providers.

    Args:
        providers: List of notification providers to use
        bridge: Bridge configuration
        notes_found: Number of notes discovered
        converted: Number of notes converted
        skipped: Number of notes skipped (up to date)
        no_text: Number of notes with no recognized text
        tool_missing: Number of notes where supernote-tool was missing
        tool_failed: Number of notes where supernote-tool failed
        supernote_missing: Whether the supernote path is missing
        vault_missing: Whether the vault path is missing
        always_send: If True, send to all providers (e.g., for menubar updates)
    """
    if not providers:
        return

    # Determine severity based on errors
    error_flag = bool(tool_missing or tool_failed or supernote_missing or vault_missing)
    severity = NotificationSeverity.ERROR if error_flag else NotificationSeverity.INFO

    # Build notification payload
    payload = NotificationPayload(
        bridge_name=bridge.name,
        vault_name=bridge.vault_path.name,
        severity=severity,
        timestamp=datetime.datetime.now().isoformat(timespec="seconds"),
        notes_found=notes_found,
        converted=converted,
        skipped=skipped,
        no_text=no_text,
        tool_missing=tool_missing,
        tool_failed=tool_failed,
        supernote_missing=supernote_missing,
        vault_missing=vault_missing,
    )

    # Send to all configured providers
    # Menubar provider (name="menubar") is always sent to, regardless of NOTIFY_MODE
    ctx = NotificationContext(bridge_name=bridge.name)
    for provider in providers:
        # Always send to menubar provider (it's a state tracker, not a notification)
        # For other providers, respect the always_send flag
        should_send = always_send or provider.name == "menubar"

        if should_send:
            try:
                provider.send(payload, ctx)
            except Exception as e:
                # Providers should never raise, but catch just in case
                log.warning(
                    f"[{bridge.name}] notification provider {provider.name} raised exception: {e}"
                )


def export_images(note_path: Path, bridge: BridgeConfig) -> list[Path]:
    """Export PNG images for a Supernote .note file into the vault.

    Images are written under:
        <vault>/<images_subdir>/<bridge.name>/<note-stem>/

    Returns a list of PNG paths (possibly empty on failure).
    """
    if not getattr(bridge, "export_images", False):
        return []

    # Determine base assets root (configurable, with a default)
    images_subdir = getattr(bridge, "images_subdir", "Supersidian/Assets")
    base_assets_root = bridge.vault_path / images_subdir
    assets_root = base_assets_root / bridge.name

    # One folder per note, using the note's stem
    note_dir = assets_root / note_path.stem
    note_dir.mkdir(parents=True, exist_ok=True)

    # supernote-tool expects a file path for the output, even when exporting all pages.
    # It will create files like "prefix-1.png", "prefix-2.png", etc.
    output_prefix = note_dir / f"{note_path.stem}.png"

    try:
        result = run_supernote_tool(
            [
                SUPERNOTE_TOOL,
                "convert",
                "-t",
                "png",
                "-a",
                str(note_path),
                str(output_prefix),
            ]
        )
        log.debug(
            f"[{bridge.name}] image export for {note_path} -> {note_dir} "
            f"(stdout={result.stdout.strip()!r})"
        )
    except FileNotFoundError:
        msg = f"supernote-tool not found on PATH; cannot export images for {note_path}"
        log.error(msg)
        # Do not raise; failure to export images should not block text notes.
        return []
    except subprocess.CalledProcessError as e:
        msg = e.stderr.strip() if e.stderr else str(e)
        log.error(f"[{bridge.name}] supernote-tool PNG export failed for {note_path}: {msg}")
        return []

    pngs = sorted(note_dir.glob("*.png"))
    if not pngs:
        log.warning(f"[{bridge.name}] no PNG pages exported for {note_path} into {note_dir}")
    else:
        log.info(f"[{bridge.name}] exported {len(pngs)} page image(s) for {note_path} into {note_dir}")

    return pngs

def sanitize_title(s: str) -> str:
    s = s.strip()
    s = re.sub(r"[\r\n]+", " ", s)
    s = unidecode(s)
    s = re.sub(r"[^\w\-\s]", "", s).strip()
    return s[:80] or "Untitled"


def process_note_for_bridge(note: Path, bridge: BridgeConfig, note_provider, note_ctx: NoteContext) -> str:
    rel = note.relative_to(bridge.supernote_path)
    md_path = bridge.vault_path / rel.with_suffix(".md")

    # Skip files modified in the last 20 minutes to avoid Dropbox/iCloud locking issues
    # These files will be picked up on the next run once cloud storage sync completes
    # Note: Dropbox can take 15+ minutes to fully sync large files in the background
    file_age_seconds = time.time() - note.stat().st_mtime
    min_age_seconds = int(os.environ.get("SUPERSIDIAN_MIN_FILE_AGE_SECONDS", "1200"))  # Default: 20 minutes

    if file_age_seconds < min_age_seconds:
        age_mins = file_age_seconds / 60
        if VERBOSE:
            log.debug(
                f"[{bridge.name}] skipping {rel} (age {age_mins:.1f}m < {min_age_seconds/60:.0f}m threshold)"
            )
        return "skipped_too_recent"

    if md_path.exists() and md_path.stat().st_mtime >= note.stat().st_mtime:
        return "skipped_up_to_date"

    try:
        txt = extract_text(note)
    except ExtractionError as e:
        if e.kind == "tool_missing":
            return "tool_missing"
        elif e.kind == "tool_failed":
            return "tool_failed"
        else:
            log.error(f"[{bridge.name}] unknown extraction error for {rel}: {e}")
            return "extract_error"

    if not txt:
        log.warning(f"[{bridge.name}] no text extracted for {rel}")
        return "no_text"

    md_body = unwrap_and_markdown(txt, aggressive=getattr(bridge, "aggressive_cleanup", False))

    repl = note_provider.load_replacements(note_ctx)
    if repl:
        md_body = apply_replacements(md_body, repl)

    # Detect tasks in the rendered Markdown body.
    rel_md = rel.with_suffix(".md")
    tasks = extract_tasks_from_markdown(md_body, bridge, rel_md)

    # Persist newly seen tasks into the local SQLite registry using the
    # configured todo provider (Todoist, noop, etc.). Supersidian ensures
    # that we only send previously unseen tasks to providers; providers are
    # responsible for attempting the external sync and returning
    # TaskSyncResult objects. Completed tasks ([x]) are *not* synced to
    # external todo systems.
    if tasks:
        task_ids = [t.local_id for t in tasks]
        known_ids = get_known_task_ids(task_ids)
        new_tasks = [t for t in tasks if t.local_id not in known_ids]
        new_open_tasks = [t for t in new_tasks if not t.completed]

        if VERBOSE:
            log.debug(
                f"[{bridge.name}] tasks total={len(tasks)}, known={len(known_ids)}, new={len(new_tasks)}, new_open={len(new_open_tasks)}"
            )

        if new_open_tasks:
            ctx = TodoContext(
                bridge_name=bridge.name,
                vault_name=bridge.vault_path.name,
                vault_path=bridge.vault_path,
                note_url_builder=lambda path: note_provider.get_note_url(path, note_ctx),
            )
            provider = provider_from_env()
            results = provider.sync_tasks(new_open_tasks, ctx)
            record_task_sync_results(new_open_tasks, results)

    first = next((l for l in md_body.splitlines() if l.strip()), "")
    title_candidate = re.sub(r"^[-\*\d\.\)]+\s+", "", first).strip("# ").strip()
    title = sanitize_title(title_candidate or note.stem)

    body = md_body

    # Optional: export page images for sketches/diagrams and embed them
    image_paths: list[Path] = []
    if getattr(bridge, "export_images", False):
        image_paths = export_images(note, bridge)

    if image_paths:
        body += "\n\n## Sketches\n\n"
        for img in image_paths:
            # Use Obsidian wikilink syntax for images - finds images anywhere in vault
            body += f"![[{img.name}]]\n"

    # Build tags list from bridge config
    tags = list(dict.fromkeys([*bridge.default_tags, *bridge.extra_tags]))

    # Create metadata for the note
    metadata = NoteMetadata(
        title=title,
        tags=tags,
        source_file=str(rel),
        created_date=datetime.datetime.now().isoformat(timespec="seconds"),
    )

    # Use note provider to write the note
    rel_md = rel.with_suffix(".md")
    written_path = note_provider.write_note(body, metadata, rel_md, note_ctx)
    log.info(f"[{bridge.name}] OK {rel} → {written_path}")
    return "converted"


def process_bridge(bridge: BridgeConfig, notification_providers: list) -> bool:
    if not bridge.enabled:
        log.info(f"[{bridge.name}] SKIP disabled")
        return False

    # Get sync provider for this bridge
    sync_provider = sync_provider_from_env()
    sync_ctx = SyncContext(
        bridge_name=bridge.name,
        supernote_subdir=bridge.supernote_subdir,
    )

    # Get note provider for this bridge
    note_provider = note_provider_from_env()
    note_ctx = NoteContext(
        bridge_name=bridge.name,
        vault_path=bridge.vault_path,
        vault_name=bridge.vault_path.name,
    )

    # Get the supernote root path from the sync provider
    supernote_root = sync_provider.get_root_path(sync_ctx)

    if not supernote_root or not supernote_root.exists():
        log.warning(f"[{bridge.name}] supernote_path does not exist: {bridge.supernote_path}")
        # Try to write a status note if the vault exists
        if bridge.vault_path.exists():
            stats = StatusStats(
                notes_found=0,
                converted=0,
                skipped=0,
                no_text=0,
                tool_missing=0,
                tool_failed=0,
                supernote_missing=True,
            )
            note_provider.write_status_note(stats, note_ctx)
        # Send notifications (menubar provider always receives, others based on NOTIFY_MODE)
        should_notify_all = NOTIFY_MODE != "none"
        send_notifications(
            notification_providers,
            bridge,
            notes_found=0,
            converted=0,
            skipped=0,
            no_text=0,
            tool_missing=0,
            tool_failed=0,
            supernote_missing=True,
            vault_missing=not bridge.vault_path.exists(),
            always_send=should_notify_all,
        )
        return True

    if not bridge.vault_path.exists():
        log.warning(f"[{bridge.name}] vault_path does not exist: {bridge.vault_path}")
        # Cannot write a status note without a vault, but can still notify
        # (menubar provider always receives, others based on NOTIFY_MODE)
        should_notify_all = NOTIFY_MODE != "none"
        send_notifications(
            notification_providers,
            bridge,
            notes_found=0,
            converted=0,
            skipped=0,
            no_text=0,
            tool_missing=0,
            tool_failed=0,
            supernote_missing=False,
            vault_missing=True,
            always_send=should_notify_all,
        )
        return True

    # Use sync provider to discover notes
    note_files = sync_provider.list_notes(sync_ctx)
    if not note_files:
        log.info(f"[{bridge.name}] no .note files under {supernote_root}")
        stats = StatusStats(
            notes_found=0,
            converted=0,
            skipped=0,
            no_text=0,
        )
        note_provider.write_status_note(stats, note_ctx)
        return False

    converted = 0
    skipped = 0
    no_text = 0
    tool_missing = 0
    tool_failed = 0

    for note_file in note_files:
        status = process_note_for_bridge(note_file.path, bridge, note_provider, note_ctx)
        if status == "converted":
            converted += 1
        elif status == "skipped_up_to_date":
            skipped += 1
        elif status == "skipped_too_recent":
            # Don't count as skipped in stats - file will be processed on next run
            # This prevents "recently synced" files from inflating skip counts
            pass
        elif status == "no_text":
            no_text += 1
        elif status == "tool_missing":
            tool_missing += 1
        elif status == "tool_failed":
            tool_failed += 1

    stats = StatusStats(
        notes_found=len(note_files),
        converted=converted,
        skipped=skipped,
        no_text=no_text,
        tool_missing=tool_missing,
        tool_failed=tool_failed,
        supernote_missing=False,
    )
    note_provider.write_status_note(stats, note_ctx)

    # For error signaling (notifications + healthchecks), only treat structural
    # issues as errors: missing tool, tool failures, or missing paths.
    # Notes with no recognized text are reported in the status/notification
    # summary but do not, by themselves, mark the run as failed.
    errorish = bool(tool_missing or tool_failed)

    # Send notifications (menubar provider always receives updates)
    # Other providers only receive based on NOTIFY_MODE
    should_notify_all = NOTIFY_MODE == "all" or (NOTIFY_MODE == "errors" and errorish)
    send_notifications(
        notification_providers,
        bridge,
        notes_found=len(note_files),
        converted=converted,
        skipped=skipped,
        no_text=no_text,
        tool_missing=tool_missing,
        tool_failed=tool_failed,
        supernote_missing=False,
        vault_missing=False,
        always_send=should_notify_all,
    )

    return errorish


def export_status_json() -> dict:
    """Export complete system configuration and status for the menubar app.

    Returns a dictionary containing:
    - bridges: List of bridge configurations with current status
    - database_path: Path to the SQLite database
    - log_path: Path to the log file
    - providers: Configured notification/sync/todo providers
    """
    import json
    from .storage import _get_connection, DB_PATH

    cfg = load_config()
    conn = _get_connection()
    cur = conn.cursor()

    # Get all bridge status from database
    cur.execute("SELECT * FROM bridge_status")
    status_rows = {row["bridge_name"]: dict(row) for row in cur.fetchall()}

    # Build bridge list with config + status
    bridges = []
    for bridge in cfg.bridges:
        bridge_data = {
            "name": bridge.name,
            "enabled": bridge.enabled,
            "supernote_path": str(bridge.supernote_path),
            "vault_path": str(bridge.vault_path),
            "vault_name": bridge.vault_path.name,
            "default_tags": bridge.default_tags,
            "extra_tags": bridge.extra_tags,
            "aggressive_cleanup": bridge.aggressive_cleanup,
            "spellcheck": bridge.spellcheck,
            "export_images": bridge.export_images,
            "images_subdir": bridge.images_subdir,
        }

        # Merge status if available
        if bridge.name in status_rows:
            bridge_data["status"] = status_rows[bridge.name]

        bridges.append(bridge_data)

    # Get provider info from environment
    notification_providers = notification_providers_from_env()
    provider_names = [p.name for p in notification_providers]

    return {
        "version": __version__,
        "bridges": bridges,
        "database_path": str(DB_PATH),
        "log_path": str(LOG_PATH),
        "supernote_root": str(cfg.supernote_root),
        "providers": {
            "notification": provider_names,
            "sync": os.environ.get("SUPERSIDIAN_SYNC_PROVIDER", "local"),
            "todo": os.environ.get("SUPERSIDIAN_TODO_PROVIDER", "noop"),
            "notes": os.environ.get("SUPERSIDIAN_NOTE_PROVIDER", "obsidian"),
        },
        "settings": {
            "verbose": VERBOSE,
            "notify_mode": NOTIFY_MODE,
            "supernote_tool": SUPERNOTE_TOOL,
        },
    }


def main() -> None:
    global VERBOSE

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Supersidian: Automated pipeline for Supernote notes to Obsidian and task apps"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"Supersidian {__version__}",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging output",
    )
    parser.add_argument(
        "--export-status",
        action="store_true",
        help="Export complete system configuration as JSON (for menubar app)",
    )
    args = parser.parse_args()

    # Override VERBOSE if --verbose flag is passed
    if args.verbose:
        VERBOSE = True

    # Handle --export-status command
    if args.export_status:
        import json
        status = export_status_json()
        print(json.dumps(status, indent=2))
        return

    cfg = load_config()

    # Load notification providers once for all bridges
    notification_providers = notification_providers_from_env()

    # Ping healthcheck at start of run, if configured
    ping_healthcheck("/start")

    errorish = False
    try:
        for bridge in cfg.bridges:
            bridge_error = process_bridge(bridge, notification_providers)
            if bridge_error:
                errorish = True
    except Exception:
        # Any unhandled exception is treated as a failed run for healthchecks
        errorish = True
        raise
    finally:
        # On success, ping base URL; on error, ping /fail
        if errorish:
            ping_healthcheck("/fail")
        else:
            ping_healthcheck("")


if __name__ == "__main__":
    main()