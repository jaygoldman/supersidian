"""Base note provider interface for Supersidian.

This module defines the abstract interface that all note providers must
implement. Note providers are responsible for writing markdown notes to
different note-taking applications (Obsidian, plain markdown, Notion, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(frozen=True)
class NoteContext:
    """Context information for note operations.
    
    This provides the note provider with information about which
    bridge/vault it's operating on behalf of.
    """
    
    bridge_name: str
    vault_path: Path
    vault_name: str  # Just the vault folder name (e.g., "Personal")


@dataclass(frozen=True)
class NoteMetadata:
    """Metadata for a note to be written.
    
    This represents the frontmatter and other metadata that should be
    included with the note content.
    """
    
    title: str
    tags: List[str]
    source_file: str  # Original .note filename
    created_date: Optional[str] = None
    modified_date: Optional[str] = None
    
    # Additional metadata can be added by providers
    extra_fields: Optional[Dict[str, str]] = None


@dataclass(frozen=True)
class StatusStats:
    """Statistics for a status/summary note."""
    
    notes_found: int
    converted: int
    skipped: int
    no_text: int
    tool_missing: int = 0
    tool_failed: int = 0
    supernote_missing: bool = False
    vault_missing: bool = False


class BaseNoteProvider(ABC):
    """Abstract base class for note providers.
    
    A note provider is responsible for writing markdown notes to a
    specific note-taking application or format. It handles:
    - Writing note files with appropriate formatting/frontmatter
    - Writing status/summary notes
    - Generating app-specific URLs for notes
    - Loading app-specific configuration (like replacements)
    """
    
    name: str = "base"
    
    @abstractmethod
    def write_note(
        self,
        content: str,
        metadata: NoteMetadata,
        relative_path: Path,
        ctx: NoteContext,
    ) -> Path:
        """Write a note file to the vault.
        
        Args:
            content: The markdown content (without frontmatter)
            metadata: Note metadata for frontmatter
            relative_path: Path relative to vault root (e.g., "Folder/Note.md")
            ctx: Note context
            
        Returns:
            Absolute path to the written file
        """
        raise NotImplementedError
    
    @abstractmethod
    def write_status_note(
        self,
        stats: StatusStats,
        ctx: NoteContext,
    ) -> Optional[Path]:
        """Write a status/summary note with processing statistics.
        
        Args:
            stats: Processing statistics
            ctx: Note context
            
        Returns:
            Path to the written status note, or None if status notes
            are not supported by this provider.
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_note_url(
        self,
        note_path: str,
        ctx: NoteContext,
    ) -> str:
        """Generate an app-specific URL to open a note.
        
        For example, Obsidian uses obsidian://open URLs,
        while other apps might use different schemes or HTTP URLs.
        
        Args:
            note_path: Relative path to the note (without .md extension)
            ctx: Note context
            
        Returns:
            URL string that can open the note in the app
        """
        raise NotImplementedError
    
    @abstractmethod
    def load_replacements(
        self,
        ctx: NoteContext,
    ) -> Dict[str, str]:
        """Load text replacement patterns for this vault.
        
        Replacements are app-specific. For Obsidian, they come from
        a special note. For plain markdown, they might come from a
        .replacements file, etc.
        
        Args:
            ctx: Note context
            
        Returns:
            Dictionary mapping old text -> new text.
            Returns empty dict if no replacements configured.
        """
        raise NotImplementedError
    
    def validate_connection(self, ctx: NoteContext) -> bool:
        """Validate that the provider can write to the vault.
        
        Args:
            ctx: Note context
            
        Returns:
            True if the vault path exists and is writable, False otherwise.
            
        Note:
            Default implementation checks if vault_path exists.
            Override for providers that need additional validation.
        """
        return ctx.vault_path.exists()


class NoopNoteProvider(BaseNoteProvider):
    """A note provider that doesn't write any notes.
    
    Useful for testing or dry-run mode.
    """
    
    name: str = "noop"
    
    def write_note(
        self,
        content: str,
        metadata: NoteMetadata,
        relative_path: Path,
        ctx: NoteContext,
    ) -> Path:
        """Return a fake path without writing anything."""
        return ctx.vault_path / relative_path
    
    def write_status_note(
        self,
        stats: StatusStats,
        ctx: NoteContext,
    ) -> Optional[Path]:
        """Don't write status notes."""
        return None
    
    def get_note_url(
        self,
        note_path: str,
        ctx: NoteContext,
    ) -> str:
        """Return a simple file:// URL."""
        return f"file://{ctx.vault_path}/{note_path}.md"
    
    def load_replacements(
        self,
        ctx: NoteContext,
    ) -> Dict[str, str]:
        """Return empty replacements."""
        return {}
