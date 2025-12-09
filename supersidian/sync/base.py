"""Base sync provider interface for Supersidian.

This module defines the abstract interface that all sync providers must
implement. Sync providers are responsible for discovering and accessing
Supernote .note files from various sync services (Dropbox, local filesystem,
iCloud, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class SyncContext:
    """Context information for sync operations.
    
    This provides the sync provider with information about which
    bridge/vault it's operating on behalf of.
    """
    
    bridge_name: str
    supernote_subdir: str  # Subdirectory within the sync root (e.g., "Personal", "Work")


@dataclass(frozen=True)
class NoteFile:
    """Represents a discovered .note file from the sync provider.
    
    This abstraction allows different sync providers to present files
    in a uniform way, regardless of whether they come from Dropbox,
    local filesystem, iCloud, etc.
    """
    
    path: Path  # Absolute path to the .note file
    relative_path: Path  # Path relative to the supernote root for this bridge
    modified_time: float  # Unix timestamp of last modification
    
    @property
    def stem(self) -> str:
        """Return the filename without the .note extension."""
        return self.path.stem


class BaseSyncProvider(ABC):
    """Abstract base class for sync providers.
    
    A sync provider is responsible for discovering Supernote .note files
    from a particular sync service or filesystem location. It abstracts
    away the details of how files are stored and accessed.
    
    Implementations must be thread-safe for reading (though Supersidian
    currently runs single-threaded).
    """
    
    name: str = "base"
    
    @abstractmethod
    def list_notes(
        self,
        ctx: SyncContext,
    ) -> List[NoteFile]:
        """List all .note files for the given bridge.
        
        Args:
            ctx: Sync context containing bridge information
            
        Returns:
            List of NoteFile objects representing discovered .note files.
            Returns empty list if the sync location doesn't exist or
            contains no .note files.
            
        Note:
            Implementations should NOT raise exceptions for missing
            directories. Return an empty list instead and optionally
            log a warning.
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_root_path(self, ctx: SyncContext) -> Optional[Path]:
        """Get the absolute path to the sync root for this bridge.
        
        Args:
            ctx: Sync context containing bridge information
            
        Returns:
            Absolute Path to the supernote root directory for this bridge,
            or None if the path cannot be determined or doesn't exist.
        """
        raise NotImplementedError
    
    def validate_connection(self) -> bool:
        """Validate that the sync provider can connect/access its storage.
        
        Returns:
            True if the provider can access its storage, False otherwise.
            
        Note:
            Default implementation returns True. Override for providers
            that need to validate API connections, mount points, etc.
        """
        return True


class NoopSyncProvider(BaseSyncProvider):
    """A sync provider that returns no notes.
    
    Useful for testing or disabling sync without breaking the pipeline.
    """
    
    name: str = "noop"
    
    def list_notes(self, ctx: SyncContext) -> List[NoteFile]:
        """Return empty list (no notes)."""
        return []
    
    def get_root_path(self, ctx: SyncContext) -> Optional[Path]:
        """Return None (no root path)."""
        return None
