"""Notification provider registry for Supersidian.

This module wires together the base provider interface and concrete
implementations (webhook, ntfy, slack, etc.) so that supersidian.py
can resolve configured provider names into provider instances.

It also provides backwards compatibility by auto-detecting webhook
configuration from environment variables.
"""

from __future__ import annotations

import os
from typing import Callable, Dict, List, Optional

from .base import (
    BaseNotificationProvider,
    NoopNotificationProvider,
    NotificationContext,
    NotificationPayload,
    NotificationSeverity,
)

# Optional: Webhook provider
try:
    from .webhook import WebhookProvider
except Exception:
    WebhookProvider = None  # type: ignore

# Optional: Menubar provider (macOS only)
try:
    from .menubar import MenubarProvider
except Exception:
    MenubarProvider = None  # type: ignore


_PROVIDER_FACTORIES: Dict[str, Callable[[], BaseNotificationProvider]] = {}


def _register_defaults() -> None:
    """Populate the provider registry with built-in providers.

    This is kept lazy so that importing supersidian.notifications does
    not immediately pull in all optional provider dependencies.
    """
    if _PROVIDER_FACTORIES:
        return

    # Always available: noop provider that sends nothing
    _PROVIDER_FACTORIES["noop"] = lambda: NoopNotificationProvider()

    # Webhook provider
    if WebhookProvider is not None:
        _PROVIDER_FACTORIES["webhook"] = lambda: WebhookProvider()

    # Menubar provider (macOS only)
    if MenubarProvider is not None:
        _PROVIDER_FACTORIES["menubar"] = lambda: MenubarProvider()


def get_provider(name: Optional[str]) -> BaseNotificationProvider:
    """Return a notification provider instance for the given name.

    If the name is None, empty, or unknown, returns NoopNotificationProvider.

    Args:
        name: Provider name ("webhook", "noop", etc.)

    Returns:
        BaseNotificationProvider instance
    """
    _register_defaults()

    if not name:
        return NoopNotificationProvider()

    key = name.strip().lower()
    factory = _PROVIDER_FACTORIES.get(key)

    if factory is None:
        # Unknown provider, return noop
        return NoopNotificationProvider()

    return factory()


def get_providers(names: Optional[str]) -> List[BaseNotificationProvider]:
    """Get multiple notification providers from comma-separated names.

    This enables sending notifications to multiple channels simultaneously.
    For example: "slack,ntfy,webhook" returns a list of three providers.

    Args:
        names: Comma-separated provider names, or None

    Returns:
        List of provider instances (may be empty for no notifications)
    """
    if not names:
        return []

    provider_list = []
    for name in names.split(","):
        name = name.strip()
        if name:
            provider = get_provider(name)
            # Only add if it's not a noop (unless explicitly requested)
            if name.lower() == "noop" or not isinstance(provider, NoopNotificationProvider):
                provider_list.append(provider)

    return provider_list


def providers_from_env() -> List[BaseNotificationProvider]:
    """Resolve notification providers based on environment variables.

    Supports multiple channels via comma-separated list in
    SUPERSIDIAN_NOTIFICATION_PROVIDERS.

    For backwards compatibility, if NOTIFICATION_PROVIDERS is not set but
    SUPERSIDIAN_WEBHOOK_URL exists, automatically uses the webhook provider.

    Returns:
        List of provider instances (empty list = no notifications)
    """
    # Check for explicit provider configuration
    names = os.environ.get("SUPERSIDIAN_NOTIFICATION_PROVIDERS", "").strip()

    if names:
        # Explicit providers configured
        return get_providers(names)

    # Backwards compatibility: check for webhook URL
    webhook_url = os.environ.get("SUPERSIDIAN_WEBHOOK_URL", "").strip()
    if webhook_url:
        # Legacy webhook configuration detected
        return [WebhookProvider()] if WebhookProvider else []

    # No notification configuration found
    return []


__all__ = [
    "BaseNotificationProvider",
    "NoopNotificationProvider",
    "NotificationContext",
    "NotificationPayload",
    "NotificationSeverity",
    "get_provider",
    "get_providers",
    "providers_from_env",
]
