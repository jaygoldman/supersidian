"""Dropbox sync provider for Supersidian.

This provider accesses Supernote files synced by the Dropbox desktop client.
Currently, it's a thin wrapper around LocalFilesystemProvider since Dropbox
syncs files to the local filesystem.

Future enhancement: Could use Dropbox API for direct cloud access without
requiring the desktop client.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .base import BaseSyncProvider, NoteFile, SyncContext
from .local import LocalFilesystemProvider


class DropboxProvider(BaseSyncProvider):
    """Sync provider for Dropbox-synced Supernote files.
    
    Currently wraps LocalFilesystemProvider since the Dropbox desktop client
    syncs files to the local filesystem. The SUPERSIDIAN_SUPERNOTE_ROOT should
    point to your Dropbox folder, e.g.:
    
        /Users/you/Dropbox/Supernote/Note
    
    Future versions could bypass the desktop client and use the Dropbox API
    directly for:
        - Selective sync (download only needed files)
        - Faster sync detection via Dropbox cursors
        - Support for systems without the Dropbox client installed
    
    Configuration:
        SUPERSIDIAN_SUPERNOTE_ROOT: Path to Dropbox/Supernote/Note directory
        
    Example:
        SUPERSIDIAN_SUPERNOTE_ROOT=/Users/you/Dropbox/Supernote/Note
    """
    
    name: str = "dropbox"
    
    def __init__(self) -> None:
        """Initialize Dropbox provider.
        
        Currently delegates to LocalFilesystemProvider.
        """
        self._local = LocalFilesystemProvider()
    
    def get_root_path(self, ctx: SyncContext) -> Optional[Path]:
        """Get the absolute path to the Dropbox-synced supernote directory.
        
        Returns:
            Path to the supernote directory for this bridge within Dropbox,
            or None if not configured.
        """
        return self._local.get_root_path(ctx)
    
    def list_notes(self, ctx: SyncContext) -> List[NoteFile]:
        """List all .note files synced by Dropbox for this bridge.
        
        Currently uses local filesystem access. Future versions could
        use Dropbox API to detect changes more efficiently.
        
        Returns:
            List of NoteFile objects found in Dropbox sync directory.
        """
        return self._local.list_notes(ctx)
    
    def validate_connection(self) -> bool:
        """Validate that Dropbox sync directory is configured.
        
        Future versions could verify Dropbox client is running or
        validate Dropbox API credentials.
        
        Returns:
            True if configuration is valid, False otherwise.
        """
        return self._local.validate_connection()
