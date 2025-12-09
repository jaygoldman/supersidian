"""Local filesystem sync provider for Supersidian.

This provider accesses .note files directly from the local filesystem,
whether they're synced by Dropbox, iCloud, Syncthing, or stored locally.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from .base import BaseSyncProvider, NoteFile, SyncContext


class LocalFilesystemProvider(BaseSyncProvider):
    """Sync provider that accesses files directly from local filesystem.
    
    This is a generic provider that works with any local directory,
    regardless of how the files got there (Dropbox sync, iCloud sync,
    manual copying, etc.).
    
    Configuration:
        SUPERSIDIAN_SUPERNOTE_ROOT: Root directory containing Supernote folders
    
    Example:
        If SUPERSIDIAN_SUPERNOTE_ROOT=/Users/you/Dropbox/Supernote/Note
        and bridge has supernote_subdir="Personal"
        then notes are read from:
        /Users/you/Dropbox/Supernote/Note/Personal/**/*.note
    """
    
    name: str = "local"
    
    def __init__(self) -> None:
        """Initialize the local filesystem provider.
        
        Reads SUPERSIDIAN_SUPERNOTE_ROOT from environment.
        """
        root_str = os.environ.get("SUPERSIDIAN_SUPERNOTE_ROOT", "").strip()
        if root_str:
            self._root = Path(root_str).expanduser().resolve()
        else:
            self._root = None
    
    def get_root_path(self, ctx: SyncContext) -> Optional[Path]:
        """Get the absolute path to the supernote directory for this bridge.
        
        Returns:
            Path like /Users/you/Dropbox/Supernote/Note/Personal
            or None if root is not configured or doesn't exist.
        """
        if not self._root:
            return None
        
        # Combine root with the bridge's subdirectory
        bridge_path = self._root / ctx.supernote_subdir
        
        # Return the path even if it doesn't exist yet
        # (the caller will handle missing directories)
        return bridge_path
    
    def list_notes(self, ctx: SyncContext) -> List[NoteFile]:
        """List all .note files in the bridge's supernote directory.
        
        Recursively searches for *.note files under:
        {SUPERNOTE_ROOT}/{supernote_subdir}/
        
        Returns:
            List of NoteFile objects, sorted by path.
            Returns empty list if directory doesn't exist.
        """
        root_path = self.get_root_path(ctx)
        
        if not root_path:
            return []
        
        if not root_path.exists():
            return []
        
        # Recursively find all .note files
        notes: List[NoteFile] = []
        
        for note_path in root_path.rglob("*.note"):
            # Skip if not a file (shouldn't happen, but be safe)
            if not note_path.is_file():
                continue
            
            # Calculate relative path from the bridge's root
            try:
                relative = note_path.relative_to(root_path)
            except ValueError:
                # Shouldn't happen with rglob, but be defensive
                continue
            
            # Get modification time
            try:
                mtime = note_path.stat().st_mtime
            except OSError:
                # File disappeared or permission denied
                continue
            
            notes.append(
                NoteFile(
                    path=note_path,
                    relative_path=relative,
                    modified_time=mtime,
                )
            )
        
        # Sort by path for consistent ordering
        notes.sort(key=lambda n: n.path)
        
        return notes
    
    def validate_connection(self) -> bool:
        """Validate that the root path is configured and accessible.
        
        Returns:
            True if root path is configured (doesn't need to exist yet),
            False if not configured.
        """
        return self._root is not None
