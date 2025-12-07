"""Todo provider registry for Supersidian.

This module wires together the base provider interface and concrete
implementations (e.g. Todoist) so that bridge.py can resolve a
configured provider name into a provider instance.

At the moment, only the NoopTodoProvider is guaranteed to exist. The
Todoist provider is optional and will be registered if its module is
importable.
"""

from __future__ import annotations

import os
from typing import Callable, Dict, Optional

from .base import BaseTodoProvider, NoopTodoProvider, TodoContext

# Optional: Todoist provider, if implemented.
try:
    from .todoist import TodoistProvider  # type: ignore
except Exception:  # ModuleNotFoundError or any import-time failure
    TodoistProvider = None  # type: ignore


_PROVIDER_FACTORIES: Dict[str, Callable[[], BaseTodoProvider]] = {}


def _register_defaults() -> None:
    """Populate the provider registry with built-in providers.

    This is kept lazy so that importing supersidian.todo does not
    immediately pull in all optional provider dependencies.
    """

    if _PROVIDER_FACTORIES:
        return

    # Always available: a no-op provider that simply marks tasks as skipped.
    _PROVIDER_FACTORIES["noop"] = lambda: NoopTodoProvider()

    # Optional: Todoist provider, only if its module imported cleanly.
    if TodoistProvider is not None:
        _PROVIDER_FACTORIES["todoist"] = lambda: TodoistProvider()


def get_provider(name: Optional[str]) -> BaseTodoProvider:
    """Return a provider instance for the given name.

    If the name is None, empty, or unknown, a NoopTodoProvider is
    returned. This ensures that todo sync never crashes the bridge and
    instead yields explicit "skipped" results.
    """

    _register_defaults()

    if not name:
        return NoopTodoProvider()

    key = name.strip().lower()
    factory = _PROVIDER_FACTORIES.get(key)
    if factory is None:
        return NoopTodoProvider()

    return factory()


def provider_from_env() -> BaseTodoProvider:
    """Resolve a provider based on SUPERSIDIAN_TODO_PROVIDER.

    This is a convenience for callers that want a single global
    provider without per-bridge overrides.
    """

    name = os.environ.get("SUPERSIDIAN_TODO_PROVIDER", "").strip() or None
    return get_provider(name)


__all__ = [
    "BaseTodoProvider",
    "NoopTodoProvider",
    "TodoContext",
    "get_provider",
    "provider_from_env",
]
