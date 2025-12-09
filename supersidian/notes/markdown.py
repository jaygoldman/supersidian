"""Plain markdown note provider for Supersidian.

This provider writes simple markdown files without app-specific features.
No frontmatter, no special folder structure - just clean markdown.
"""

from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
from typing import Dict, Optional

from .base import BaseNoteProvider, NoteContext, NoteMetadata, StatusStats

log = logging.getLogger(__name__)


class PlainMarkdownProvider(BaseNoteProvider):
    """Note provider for plain markdown files.
    
    Features:
    - Simple markdown files without frontmatter
    - Metadata stored in a separate .supersidian/ directory
    - Replacements stored in a JSON file
    - file:// URLs for opening notes
    
    Directory structure:
        Vault/
        ├── .supersidian/
        │   ├── status.json
        │   └── replacements.json
        └── [your notes].md
    """
    
    name: str = "markdown"
    
    def write_note(
        self,
        content: str,
        metadata: NoteMetadata,
        relative_path: Path,
        ctx: NoteContext,
    ) -> Path:
        """Write a plain markdown file without frontmatter.
        
        Metadata is stored separately in .supersidian/ directory.
        """
        md_path = ctx.vault_path / relative_path
        md_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write just the content, no frontmatter
        md_path.write_text(content, encoding="utf-8")
        
        # Store metadata separately
        self._write_metadata(metadata, relative_path, ctx)
        
        return md_path
    
    def write_status_note(
        self,
        stats: StatusStats,
        ctx: NoteContext,
    ) -> Optional[Path]:
        """Write status as a JSON file in .supersidian/ directory."""
        meta_dir = ctx.vault_path / ".supersidian"
        meta_dir.mkdir(parents=True, exist_ok=True)
        
        status_path = meta_dir / f"status-{ctx.bridge_name}.json"
        
        status_data = {
            "last_run": datetime.datetime.now().isoformat(timespec="seconds"),
            "bridge_name": ctx.bridge_name,
            "vault_path": str(ctx.vault_path),
            "stats": {
                "notes_found": stats.notes_found,
                "converted": stats.converted,
                "skipped": stats.skipped,
                "no_text": stats.no_text,
                "tool_missing": stats.tool_missing,
                "tool_failed": stats.tool_failed,
            },
            "errors": {
                "supernote_missing": stats.supernote_missing,
                "vault_missing": stats.vault_missing,
            }
        }
        
        status_path.write_text(json.dumps(status_data, indent=2), encoding="utf-8")
        
        return status_path
    
    def get_note_url(
        self,
        note_path: str,
        ctx: NoteContext,
    ) -> str:
        """Generate a file:// URL to the markdown file."""
        full_path = ctx.vault_path / f"{note_path}.md"
        return f"file://{full_path}"
    
    def load_replacements(
        self,
        ctx: NoteContext,
    ) -> Dict[str, str]:
        """Load replacements from a JSON file.
        
        File path: <vault>/.supersidian/replacements-<bridge>.json
        
        File format:
            {
                "wrong": "right",
                "WrongWord": "CorrectWord"
            }
        """
        meta_dir = ctx.vault_path / ".supersidian"
        repl_path = meta_dir / f"replacements-{ctx.bridge_name}.json"
        
        if not repl_path.exists():
            # Create an empty replacements file with example
            self._ensure_replacements_template(ctx)
            return {}
        
        try:
            with repl_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.warning(f"Failed to load replacements from {repl_path}: {e}")
            return {}
    
    def _write_metadata(
        self,
        metadata: NoteMetadata,
        relative_path: Path,
        ctx: NoteContext,
    ) -> None:
        """Store note metadata in a separate JSON file."""
        meta_dir = ctx.vault_path / ".supersidian" / "metadata"
        meta_dir.mkdir(parents=True, exist_ok=True)
        
        # Use the note path as the key (replace / with -)
        meta_key = str(relative_path).replace("/", "-").replace("\\", "-")
        meta_path = meta_dir / f"{meta_key}.json"
        
        meta_data = {
            "title": metadata.title,
            "tags": metadata.tags,
            "source_file": metadata.source_file,
            "created_date": metadata.created_date,
            "modified_date": metadata.modified_date,
        }
        
        if metadata.extra_fields:
            meta_data.update(metadata.extra_fields)
        
        meta_path.write_text(json.dumps(meta_data, indent=2), encoding="utf-8")
    
    def _ensure_replacements_template(self, ctx: NoteContext) -> None:
        """Create an example replacements JSON file."""
        meta_dir = ctx.vault_path / ".supersidian"
        meta_dir.mkdir(parents=True, exist_ok=True)
        
        repl_path = meta_dir / f"replacements-{ctx.bridge_name}.json"
        
        if repl_path.exists():
            return
        
        example = {
            "_comment": "Define text replacements as key-value pairs",
            "_example1": "teh -> the",
            "_example2": "Gaurdrail -> Guardrail"
        }
        
        try:
            repl_path.write_text(json.dumps(example, indent=2), encoding="utf-8")
            log.info(f"[{ctx.bridge_name}] created replacements template at {repl_path}")
        except Exception as e:
            log.warning(f"[{ctx.bridge_name}] failed to create replacements template at {repl_path}: {e}")
