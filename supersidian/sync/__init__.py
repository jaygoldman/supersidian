"""Sync provider registry for Supersidian.

This module wires together the base provider interface and concrete
implementations (e.g., Dropbox, local filesystem) so that supersidian.py
can resolve a configured provider name into a provider instance.
"""

from __future__ import annotations

import os
from typing import Callable, Dict, Optional

from .base import BaseSyncProvider, NoopSyncProvider, SyncContext, NoteFile

# Optional: Local filesystem provider (always available)
try:
    from .local import LocalFilesystemProvider
except Exception:
    LocalFilesystemProvider = None  # type: ignore

# Optional: Dropbox provider (always available)
try:
    from .dropbox import DropboxProvider
except Exception:
    DropboxProvider = None  # type: ignore


_PROVIDER_FACTORIES: Dict[str, Callable[[], BaseSyncProvider]] = {}


def _register_defaults() -> None:
    """Populate the provider registry with built-in providers.
    
    This is kept lazy so that importing supersidian.sync does not
    immediately pull in all optional provider dependencies.
    """
    
    if _PROVIDER_FACTORIES:
        return
    
    # Always available: a no-op provider that returns no notes
    _PROVIDER_FACTORIES["noop"] = lambda: NoopSyncProvider()
    
    # Local filesystem provider
    if LocalFilesystemProvider is not None:
        _PROVIDER_FACTORIES["local"] = lambda: LocalFilesystemProvider()
    
    # Dropbox provider (wraps local for now)
    if DropboxProvider is not None:
        _PROVIDER_FACTORIES["dropbox"] = lambda: DropboxProvider()


def get_provider(name: Optional[str]) -> BaseSyncProvider:
    """Return a sync provider instance for the given name.
    
    If the name is None, empty, or unknown, defaults to "dropbox" for
    backwards compatibility. This ensures that existing configs continue
    to work without modification.
    
    Args:
        name: Provider name ("dropbox", "local", "noop", etc.)
        
    Returns:
        BaseSyncProvider instance
    """
    
    _register_defaults()
    
    # Default to dropbox for backwards compatibility
    if not name:
        name = "dropbox"
    
    key = name.strip().lower()
    factory = _PROVIDER_FACTORIES.get(key)
    
    if factory is None:
        # Unknown provider, default to dropbox
        factory = _PROVIDER_FACTORIES.get("dropbox")
        if factory is None:
            # Fallback to noop if even dropbox isn't available
            return NoopSyncProvider()
    
    return factory()


def provider_from_env() -> BaseSyncProvider:
    """Resolve a provider based on SUPERSIDIAN_SYNC_PROVIDER.
    
    This is a convenience for callers that want a single global
    provider without per-bridge overrides.
    
    Returns:
        BaseSyncProvider instance (defaults to "dropbox" if not set)
    """
    
    name = os.environ.get("SUPERSIDIAN_SYNC_PROVIDER", "").strip() or None
    return get_provider(name)


__all__ = [
    "BaseSyncProvider",
    "NoopSyncProvider",
    "SyncContext",
    "NoteFile",
    "get_provider",
    "provider_from_env",
]
