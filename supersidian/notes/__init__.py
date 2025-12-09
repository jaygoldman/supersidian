"""Note provider registry for Supersidian.

This module wires together the base provider interface and concrete
implementations (e.g., Obsidian, plain markdown) so that supersidian.py
can resolve a configured provider name into a provider instance.
"""

from __future__ import annotations

import os
from typing import Callable, Dict, Optional

from .base import BaseNoteProvider, NoopNoteProvider, NoteContext, NoteMetadata, StatusStats

# Optional: Obsidian provider (always available)
try:
    from .obsidian import ObsidianProvider
except Exception:
    ObsidianProvider = None  # type: ignore

# Optional: Plain markdown provider (always available)
try:
    from .markdown import PlainMarkdownProvider
except Exception:
    PlainMarkdownProvider = None  # type: ignore


_PROVIDER_FACTORIES: Dict[str, Callable[[], BaseNoteProvider]] = {}


def _register_defaults() -> None:
    """Populate the provider registry with built-in providers.
    
    This is kept lazy so that importing supersidian.notes does not
    immediately pull in all optional provider dependencies.
    """
    
    if _PROVIDER_FACTORIES:
        return
    
    # Always available: a no-op provider that doesn't write notes
    _PROVIDER_FACTORIES["noop"] = lambda: NoopNoteProvider()
    
    # Obsidian provider
    if ObsidianProvider is not None:
        _PROVIDER_FACTORIES["obsidian"] = lambda: ObsidianProvider()
    
    # Plain markdown provider
    if PlainMarkdownProvider is not None:
        _PROVIDER_FACTORIES["markdown"] = lambda: PlainMarkdownProvider()


def get_provider(name: Optional[str]) -> BaseNoteProvider:
    """Return a note provider instance for the given name.
    
    If the name is None, empty, or unknown, defaults to "obsidian" for
    backwards compatibility. This ensures that existing configs continue
    to work without modification.
    
    Args:
        name: Provider name ("obsidian", "markdown", "noop", etc.)
        
    Returns:
        BaseNoteProvider instance
    """
    
    _register_defaults()
    
    # Default to obsidian for backwards compatibility
    if not name:
        name = "obsidian"
    
    key = name.strip().lower()
    factory = _PROVIDER_FACTORIES.get(key)
    
    if factory is None:
        # Unknown provider, default to obsidian
        factory = _PROVIDER_FACTORIES.get("obsidian")
        if factory is None:
            # Fallback to noop if even obsidian isn't available
            return NoopNoteProvider()
    
    return factory()


def provider_from_env() -> BaseNoteProvider:
    """Resolve a provider based on SUPERSIDIAN_NOTE_PROVIDER.
    
    This is a convenience for callers that want a single global
    provider without per-bridge overrides.
    
    Returns:
        BaseNoteProvider instance (defaults to "obsidian" if not set)
    """
    
    name = os.environ.get("SUPERSIDIAN_NOTE_PROVIDER", "").strip() or None
    return get_provider(name)


__all__ = [
    "BaseNoteProvider",
    "NoopNoteProvider",
    "NoteContext",
    "NoteMetadata",
    "StatusStats",
    "get_provider",
    "provider_from_env",
]
