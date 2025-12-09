"""Obsidian note provider for Supersidian.

This provider writes notes in Obsidian's markdown format with YAML frontmatter.
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import quote

from .base import BaseNoteProvider, NoteContext, NoteMetadata, StatusStats

log = logging.getLogger(__name__)


class ObsidianProvider(BaseNoteProvider):
    """Note provider for Obsidian vaults.
    
    Features:
    - YAML frontmatter with title, date, source_note, tags
    - Status notes in Supersidian subfolder
    - Replacements stored in vault-specific notes
    - obsidian:// URL scheme for opening notes
    
    Directory structure:
        Vault/
        ├── Supersidian/
        │   ├── Status - bridge_name.md
        │   └── Replacements - bridge_name.md
        └── [your notes]
    """
    
    name: str = "obsidian"
    
    def write_note(
        self,
        content: str,
        metadata: NoteMetadata,
        relative_path: Path,
        ctx: NoteContext,
    ) -> Path:
        """Write a note with Obsidian-style YAML frontmatter.
        
        Creates parent directories as needed.
        """
        md_path = ctx.vault_path / relative_path
        md_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build YAML frontmatter
        frontmatter = [
            "---",
            f'title: "{metadata.title}"',
        ]
        
        if metadata.created_date:
            frontmatter.append(f'date: "{metadata.created_date}"')
        else:
            frontmatter.append(f'date: "{datetime.datetime.now().isoformat(timespec="seconds")}"')
        
        frontmatter.append(f'source_note: "{metadata.source_file}"')
        
        # Format tags as YAML list
        if metadata.tags:
            tags_str = "[" + ", ".join(metadata.tags) + "]"
            frontmatter.append(f"tags: {tags_str}")
        
        frontmatter.extend(["---", ""])
        
        # Combine frontmatter and content
        full_content = "\n".join(frontmatter) + content
        
        md_path.write_text(full_content, encoding="utf-8")
        
        return md_path
    
    def write_status_note(
        self,
        stats: StatusStats,
        ctx: NoteContext,
    ) -> Optional[Path]:
        """Write a status note in the Supersidian subfolder.
        
        Also ensures a Replacements template note exists.
        """
        sup_dir = ctx.vault_path / "Supersidian"
        status_path = sup_dir / f"Status - {ctx.bridge_name}.md"
        sup_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure a per-bridge Replacements note exists
        self._ensure_replacements_template(ctx)
        
        now = datetime.datetime.now().isoformat(timespec="seconds")
        supernote_path = ctx.vault_path.parent.parent / "Supernote" / "Note"  # Rough approximation
        
        lines = [
            f"# Supersidian Status - {ctx.bridge_name}",
            "",
            f"- Last run: {now}",
            f"- Vault path: `{ctx.vault_path}`",
            "",
            "## Summary",
            f"- Notes found: {stats.notes_found}",
            f"- Converted this run: {stats.converted}",
            f"- Skipped (up-to-date): {stats.skipped}",
            f"- No text extracted: {stats.no_text}",
        ]
        
        errors: list[str] = []
        
        if stats.supernote_missing:
            errors.append("Supernote path does not exist at last run.")
        if stats.tool_missing:
            errors.append(f"supernote-tool missing for {stats.tool_missing} note(s).")
        if stats.tool_failed:
            errors.append(f"supernote-tool failed for {stats.tool_failed} note(s).")
        if stats.no_text and not (stats.tool_missing or stats.tool_failed):
            errors.append(f"No text extracted for {stats.no_text} note(s).")
        
        if errors:
            lines.append("")
            lines.append("## Errors")
            for msg in errors:
                lines.append(f"- {msg}")
        
        status_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        
        return status_path
    
    def get_note_url(
        self,
        note_path: str,
        ctx: NoteContext,
    ) -> str:
        """Generate an obsidian:// URL to open a note.
        
        Args:
            note_path: Relative path to the note (without .md extension)
            ctx: Note context
            
        Returns:
            obsidian://open?vault=VaultName&file=path/to/note
        """
        # URL-encode the vault name and file path
        vault_param = quote(ctx.vault_name, safe="")
        file_param = quote(note_path, safe="")  # Encodes / as %2F and spaces as %20
        
        return f"obsidian://open?vault={vault_param}&file={file_param}"
    
    def load_replacements(
        self,
        ctx: NoteContext,
    ) -> Dict[str, str]:
        """Load replacements from the Supersidian/Replacements note.
        
        File path: <vault>/Supersidian/Replacements - <bridge>.md
        
        File format:
            # comment lines start with '#'
            - wrong -> right
            * WrongWord -> CorrectWord
            wrong -> right
        
        Any leading markdown list marker is stripped before parsing.
        """
        repl: Dict[str, str] = {}
        cfg_path = ctx.vault_path / "Supersidian" / f"Replacements - {ctx.bridge_name}.md"
        
        if not cfg_path.exists():
            return repl
        
        try:
            with cfg_path.open("r", encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Strip leading list markers
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
    
    def _ensure_replacements_template(self, ctx: NoteContext) -> None:
        """Ensure a Replacements template note exists for this bridge."""
        sup_dir = ctx.vault_path / "Supersidian"
        repl_path = sup_dir / f"Replacements - {ctx.bridge_name}.md"
        
        if repl_path.exists():
            return
        
        repl_lines = [
            f"# Supersidian Replacements - {ctx.bridge_name}",
            "",
            "# Define whole-word replacements for this vault/bridge.",
            "# Each non-empty line should look like:",
            "#   wrong -> right",
            "# You can optionally prefix with '-', '*', or numbers if you prefer list syntax.",
            "# Lines starting with '#' are treated as comments and ignored.",
            "# Example:",
            "# - Gaurdrail -> Guardrail",
            "# teh -> the",
            "",
        ]
        
        try:
            repl_path.write_text("\n".join(repl_lines) + "\n", encoding="utf-8")
            log.info(f"[{ctx.bridge_name}] created replacements template at {repl_path}")
        except Exception as e:
            log.warning(f"[{ctx.bridge_name}] failed to create replacements template at {repl_path}: {e}")
