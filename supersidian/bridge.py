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

# Determine verbose mode from environment variable SUPERSIDIAN_VERBOSE
VERBOSE = os.environ.get("SUPERSIDIAN_VERBOSE", "0") == "1"

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


BULLET_CHARS = "•–—*-+·►"


@lru_cache(maxsize=None)
def load_replacements(vault_path: Path) -> dict[str, str]:
    """Load per-vault replacements from a Markdown note in the vault root.

    File path: <vault>/Supersidian Replacements.md

    File format (inside the note):
        # comment lines start with '#'
        - wrong -> right
        * WrongWord -> CorrectWord
        wrong -> right

    Any leading markdown list marker is stripped before parsing."""
    repl: dict[str, str] = {}
    cfg_path = vault_path / "Supersidian Replacements.md"
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
        log.error(f"supernote-tool not found on PATH; cannot extract text for {note_path}")
        return None
    except subprocess.CalledProcessError as e:
        msg = e.stderr.strip() if e.stderr else str(e)
        log.error(f"supernote-tool failed for {note_path}: {msg}")
        return None

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

    bullet_rx = re.compile(
        rf"^(\s*)(?:[{re.escape(BULLET_CHARS)}]|\[[ xX]\])\s+"
    )
    num_rx = re.compile(r"^(\s*)(\d+)[\.)]\s+")

    final: list[str] = []

    for line in out:
        if line.strip() == "" or heading_start.match(line):
            final.append(line.rstrip())
            continue

        # 1) Handle explicit nesting markers -, --, --- at line start
        m = nest_rx.match(line)
        if m:
            base_indent, hyphens, content = m.groups()
            level = len(hyphens)  # 1..6
            extra_indent = "  " * max(level - 1, 0)
            final.append(f"{base_indent}{extra_indent}- {content.rstrip()}")
            continue

        # 2) Handle "normal" bullet characters (•, *, etc.)
        m = bullet_rx.match(line)
        if m:
            indent = m.group(1) or ""
            content = bullet_rx.sub("", line).rstrip()
            final.append(f"{indent}- {content}")
            continue

        # 3) Numbered list
        m = num_rx.match(line)
        if m:
            indent, n = m.groups()
            content = num_rx.sub("", line).rstrip()
            final.append(f"{indent}{n}. {content}")
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


def sanitize_title(s: str) -> str:
    s = s.strip()
    s = re.sub(r"[\r\n]+", " ", s)
    s = unidecode(s)
    s = re.sub(r"[^\w\-\s]", "", s).strip()
    return s[:80] or "Untitled"


def build_tags(default_tags: Iterable[str], extra_tags: Iterable[str]) -> str:
    tags = list(dict.fromkeys([*default_tags, *extra_tags]))  # dedupe, keep order
    return "[" + ", ".join(tags) + "]" if tags else "[]"


def process_note_for_bridge(note: Path, bridge: BridgeConfig) -> None:
    rel = note.relative_to(bridge.supernote_path)
    md_path = bridge.vault_path / rel.with_suffix(".md")

    if md_path.exists() and md_path.stat().st_mtime >= note.stat().st_mtime:
        return

    txt = extract_text(note)
    if not txt:
        log.warning(f"[{bridge.name}] no text extracted for {rel}")
        return

    md_body = unwrap_and_markdown(txt, aggressive=getattr(bridge, "aggressive_cleanup", False))

    repl = load_replacements(bridge.vault_path)
    if repl:
        md_body = apply_replacements(md_body, repl)

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

    md_path.write_text("\n".join(frontmatter) + md_body, encoding="utf-8")
    log.info(f"[{bridge.name}] OK {rel} → {md_path}")


def process_bridge(bridge: BridgeConfig) -> None:
    if not bridge.enabled:
        log.info(f"[{bridge.name}] SKIP disabled")
        return

    if not bridge.supernote_path.exists():
        log.warning(f"[{bridge.name}] supernote_path does not exist: {bridge.supernote_path}")
        return

    if not bridge.vault_path.exists():
        log.warning(f"[{bridge.name}] vault_path does not exist: {bridge.vault_path}")
        return

    notes = list(bridge.supernote_path.rglob("*.note"))
    if not notes:
        log.info(f"[{bridge.name}] no .note files under {bridge.supernote_path}")
        return

    for note in notes:
        process_note_for_bridge(note, bridge)


def main() -> None:
    cfg = load_config()

    for bridge in cfg.bridges:
        process_bridge(bridge)


if __name__ == "__main__":
    main()