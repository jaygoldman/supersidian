from __future__ import annotations

from pathlib import Path
import datetime
import re
from typing import Optional, Iterable
from functools import lru_cache

from unidecode import unidecode

import subprocess

import tempfile

from .config import load_config, BridgeConfig

import logging
import os

from .storage import LocalTask, TaskSyncResult, get_known_task_ids, record_task_sync_results
from .todo import TodoContext, provider_from_env

import json
import urllib.request
import urllib.error

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
WEBHOOK_URL = os.environ.get("SUPERSIDIAN_WEBHOOK_URL")
WEBHOOK_TOPIC = os.environ.get("SUPERSIDIAN_WEBHOOK_TOPIC")

# Notification mode: all, errors, none
_raw_notify_mode = os.environ.get("SUPERSIDIAN_WEBHOOK_NOTIFICATIONS", "errors")
NOTIFY_MODE = _raw_notify_mode.strip().strip("'\"").lower()
if NOTIFY_MODE not in {"all", "errors", "none"}:
    NOTIFY_MODE = "errors"

LOG_PATH = Path.home() / ".supersidian.log"

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
        f"Startup configuration: VERBOSE={VERBOSE}, NOTIFY_MODE='{NOTIFY_MODE}', "
        f"WEBHOOK_URL={WEBHOOK_URL!r}, WEBHOOK_TOPIC={WEBHOOK_TOPIC!r}"
    )


BULLET_CHARS = "•–—*-+·►"


@lru_cache(maxsize=None)
def load_replacements(vault_path: Path, bridge_name: str) -> dict[str, str]:
    """Load per-vault replacements from a Markdown note in the Supersidian subfolder.

    File path: <vault>/Supersidian/Replacements - <bridge>.md

    File format (inside the note):
        # comment lines start with '#'
        - wrong -> right
        * WrongWord -> CorrectWord
        wrong -> right

    Any leading markdown list marker is stripped before parsing."""
    repl: dict[str, str] = {}
    cfg_path = vault_path / "Supersidian" / f"Replacements - {bridge_name}.md"
    if not cfg_path.exists():
        return repl

    try:
        with cfg_path.open("r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                line = line.lstrip("-*0123456789. )").strip()
                if "->" not in line:
                    continue
                wrong, right = line.split("->", 1)
                wrong = wrong.strip()
                right = right.strip()
                if wrong:
                    repl[wrong] = right
    except Exception as e:
        log.warning(f"Failed to load replacements from {cfg_path}: {e}")
    return repl


class ExtractionError(Exception):
    def __init__(self, kind: str, message: str):
        self.kind = kind
        super().__init__(message)


def extract_text(note_path: Path) -> Optional[str]:
    # Use a temporary file because supernote-tool's txt output is designed for file targets
    try:
        with tempfile.NamedTemporaryFile(mode="r+", suffix=".txt", delete=False) as tmp:
            tmp_path = tmp.name
        result = subprocess.run(
            [
                "supernote-tool",
                "convert",
                "-t",
                "txt",
                "-a",
                str(note_path),
                tmp_path,
            ],
            capture_output=True,
            text=True,
            check=True,
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

    for i, line in enumerate(raw):
        if i == 0:
            out.append(line)
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

        if not prev_hard and not curr_new_block:
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


def write_status_note(
    bridge: BridgeConfig,
    notes_found: int,
    converted: int,
    skipped: int,
    no_text: int,
    tool_missing: int = 0,
    tool_failed: int = 0,
    supernote_missing: bool = False,
) -> None:
    """Write or update a status note in the Supersidian subfolder for this bridge."""
    sup_dir = bridge.vault_path / "Supersidian"
    status_path = sup_dir / f"Status - {bridge.name}.md"
    sup_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now().isoformat(timespec="seconds")

    lines = [
        f"# Supersidian Status - {bridge.name}",
        "",
        f"- Last run: {now}",
        f"- Supernote path: `{bridge.supernote_path}`",
        f"- Vault path: `{bridge.vault_path}`",
        "",
        "## Summary",
        f"- Notes found: {notes_found}",
        f"- Converted this run: {converted}",
        f"- Skipped (up-to-date): {skipped}",
        f"- No text extracted: {no_text}",
    ]

    errors: list[str] = []

    if supernote_missing:
        errors.append("Supernote path does not exist at last run.")
    if tool_missing:
        errors.append(f"supernote-tool missing for {tool_missing} note(s).")
    if tool_failed:
        errors.append(f"supernote-tool failed for {tool_failed} note(s).")
    if no_text and not (tool_missing or tool_failed):
        errors.append(f"No text extracted for {no_text} note(s).")

    if errors:
        lines.append("")
        lines.append("## Errors")
        for msg in errors:
            lines.append(f"- {msg}")

    status_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info(f"[{bridge.name}] status updated at {status_path}")


def send_notification(
    bridge: BridgeConfig,
    notes_found: int,
    converted: int,
    skipped: int,
    no_text: int,
    tool_missing: int,
    tool_failed: int,
    supernote_missing: bool,
    vault_missing: bool,
) -> None:
    if not WEBHOOK_URL:
        return

    now = datetime.datetime.now().isoformat(timespec="seconds")
    error_flag = bool(tool_missing or tool_failed or no_text or supernote_missing or vault_missing)
    outcome = "ERROR" if error_flag else "OK"

    # Human-readable vault label comes from the vault folder name
    vault_name = bridge.vault_path.name

    # Build a multi-line, ntfy-friendly message
    lines = [
        f"Supersidian: {vault_name} - [{outcome}]",
        "",
        f"Notes: {notes_found}",
        f"Converted: {converted}",
        f"Skipped: {skipped}",
        f"No text: {no_text}",
    ]

    errors: list[str] = []
    if tool_missing:
        errors.append("supernote-tool not found")
    if tool_failed:
        errors.append("supernote-tool failed")
    if supernote_missing:
        errors.append("Supernote path is missing")
    if vault_missing:
        errors.append("Obsidian vault is missing")

    if errors:
        lines.append("")
        if len(errors) == 1:
            lines.append(f"Error: {errors[0]}")
        else:
            lines.append("Errors:")
            for e in errors:
                lines.append(f"- {e}")

    message = "\n".join(lines)

    payload = {
        "bridge": bridge.name,
        "timestamp": now,
        "notes_found": notes_found,
        "converted": converted,
        "skipped": skipped,
        "no_text": no_text,
        "tool_missing": tool_missing,
        "tool_failed": tool_failed,
        "supernote_missing": supernote_missing,
        "vault_missing": vault_missing,
        "title": f"Supersidian: {bridge.name}",
        "message": message,
    }
    if WEBHOOK_TOPIC:
        payload["topic"] = WEBHOOK_TOPIC

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json"},
    )

    if VERBOSE:
        log.debug(
            f"[{bridge.name}] sending notification to {WEBHOOK_URL} "
            f"with payload: {json.dumps(payload, ensure_ascii=False)}"
        )

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            log.info(f"[{bridge.name}] notification sent (status={getattr(resp, 'status', 'unknown')})")
    except Exception as e:
        log.warning(f"[{bridge.name}] failed to send notification to {WEBHOOK_URL}: {e}")


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
        result = subprocess.run(
            [
                "supernote-tool",
                "convert",
                "-t",
                "png",
                "-a",
                str(note_path),
                str(output_prefix),
            ],
            capture_output=True,
            text=True,
            check=True,
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


def build_tags(default_tags: Iterable[str], extra_tags: Iterable[str]) -> str:
    tags = list(dict.fromkeys([*default_tags, *extra_tags]))  # dedupe, keep order
    return "[" + ", ".join(tags) + "]" if tags else "[]"


def process_note_for_bridge(note: Path, bridge: BridgeConfig) -> str:
    rel = note.relative_to(bridge.supernote_path)
    md_path = bridge.vault_path / rel.with_suffix(".md")

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

    repl = load_replacements(bridge.vault_path, bridge.name)
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
            )
            provider = provider_from_env()
            results = provider.sync_tasks(new_open_tasks, ctx)
            record_task_sync_results(new_open_tasks, results)

    first = next((l for l in md_body.splitlines() if l.strip()), "")
    title_candidate = re.sub(r"^[-\*\d\.\)]+\s+", "", first).strip("# ").strip()
    title = sanitize_title(title_candidate or note.stem)

    md_path.parent.mkdir(parents=True, exist_ok=True)

    tags_str = build_tags(bridge.default_tags, bridge.extra_tags)

    frontmatter = [
        "---",
        f'title: "{title}"',
        f'date: "{datetime.datetime.now().isoformat(timespec="seconds")}"',
        f'source_note: "{rel}"',
        f"tags: {tags_str}",
        "---",
        "",
    ]

    body = md_body

    # Optional: export page images for sketches/diagrams and embed them
    image_paths: list[Path] = []
    if getattr(bridge, "export_images", False):
        image_paths = export_images(note, bridge)

    if image_paths:
        body += "\n\n## Sketches\n\n"
        for img in image_paths:
            # Make path relative to vault root for Markdown linking
            rel_img = img.relative_to(bridge.vault_path)
            body += f"![{img.stem}]({rel_img.as_posix()})\n"

    md_path.write_text("\n".join(frontmatter) + body, encoding="utf-8")
    log.info(f"[{bridge.name}] OK {rel} → {md_path}")
    return "converted"


def process_bridge(bridge: BridgeConfig) -> None:
    if not bridge.enabled:
        log.info(f"[{bridge.name}] SKIP disabled")
        return

    if not bridge.supernote_path.exists():
        log.warning(f"[{bridge.name}] supernote_path does not exist: {bridge.supernote_path}")
        # Try to write a status note if the vault exists
        if bridge.vault_path.exists():
            write_status_note(
                bridge,
                notes_found=0,
                converted=0,
                skipped=0,
                no_text=0,
                tool_missing=0,
                tool_failed=0,
                supernote_missing=True,
            )
        # Notify if configured
        if NOTIFY_MODE != "none":
            send_notification(
                bridge,
                notes_found=0,
                converted=0,
                skipped=0,
                no_text=0,
                tool_missing=0,
                tool_failed=0,
                supernote_missing=True,
                vault_missing=not bridge.vault_path.exists(),
            )
        else:
            if VERBOSE:
                log.debug(f"[{bridge.name}] notification suppressed by NOTIFY_MODE='none' (supernote missing)")
        return

    if not bridge.vault_path.exists():
        log.warning(f"[{bridge.name}] vault_path does not exist: {bridge.vault_path}")
        # Cannot write a status note without a vault, but can still notify
        if NOTIFY_MODE != "none":
            send_notification(
                bridge,
                notes_found=0,
                converted=0,
                skipped=0,
                no_text=0,
                tool_missing=0,
                tool_failed=0,
                supernote_missing=False,
                vault_missing=True,
            )
        else:
            if VERBOSE:
                log.debug(f"[{bridge.name}] notification suppressed by NOTIFY_MODE='none' (vault missing)")
        return

    notes = list(bridge.supernote_path.rglob("*.note"))
    if not notes:
        log.info(f"[{bridge.name}] no .note files under {bridge.supernote_path}")
        write_status_note(
            bridge,
            notes_found=0,
            converted=0,
            skipped=0,
            no_text=0,
        )
        return

    converted = 0
    skipped = 0
    no_text = 0
    tool_missing = 0
    tool_failed = 0

    for note in notes:
        status = process_note_for_bridge(note, bridge)
        if status == "converted":
            converted += 1
        elif status == "skipped_up_to_date":
            skipped += 1
        elif status == "no_text":
            no_text += 1
        elif status == "tool_missing":
            tool_missing += 1
        elif status == "tool_failed":
            tool_failed += 1

    write_status_note(
        bridge,
        notes_found=len(notes),
        converted=converted,
        skipped=skipped,
        no_text=no_text,
        tool_missing=tool_missing,
        tool_failed=tool_failed,
        supernote_missing=False,
    )

    errorish = bool(tool_missing or tool_failed or no_text)
    if NOTIFY_MODE == "all" or (NOTIFY_MODE == "errors" and errorish):
        send_notification(
            bridge,
            notes_found=len(notes),
            converted=converted,
            skipped=skipped,
            no_text=no_text,
            tool_missing=tool_missing,
            tool_failed=tool_failed,
            supernote_missing=False,
            vault_missing=False,
        )
    else:
        if VERBOSE:
            log.debug(
                f"[{bridge.name}] notification suppressed by NOTIFY_MODE='{NOTIFY_MODE}' "
                f"(errorish={errorish})"
            )


def main() -> None:
    cfg = load_config()

    for bridge in cfg.bridges:
        process_bridge(bridge)


if __name__ == "__main__":
    main()