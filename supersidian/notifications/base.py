"""Base notification provider interface for Supersidian.

This module defines the abstract interface that all notification providers
must implement, along with shared data structures for notification payloads.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List


class NotificationSeverity(Enum):
    """Notification severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class NotificationPayload:
    """Structured data for a notification.

    This payload contains all the information about a bridge run that
    should be included in notifications sent to external services.
    """

    bridge_name: str
    vault_name: str
    severity: NotificationSeverity
    timestamp: str

    # Run statistics
    notes_found: int
    converted: int
    skipped: int
    no_text: int

    # Error flags
    tool_missing: int
    tool_failed: int
    supernote_missing: bool
    vault_missing: bool

    @property
    def has_errors(self) -> bool:
        """True if any structural errors occurred during the run."""
        return bool(
            self.tool_missing
            or self.tool_failed
            or self.supernote_missing
            or self.vault_missing
        )

    @property
    def error_messages(self) -> List[str]:
        """List of human-readable error messages based on error flags."""
        errors = []
        if self.tool_missing:
            errors.append("supernote-tool not found")
        if self.tool_failed:
            errors.append("supernote-tool failed")
        if self.supernote_missing:
            errors.append("Supernote path is missing")
        if self.vault_missing:
            errors.append("Vault is missing")
        return errors


@dataclass(frozen=True)
class NotificationContext:
    """Context for notification sending.

    Contains additional metadata about the environment in which
    the notification is being sent.
    """

    bridge_name: str


class BaseNotificationProvider(ABC):
    """Abstract base class for notification providers.

    A notification provider is responsible for sending structured
    notifications to an external service or display. Providers should
    never raise exceptions - log errors and return False instead.
    """

    name: str = "base"

    @abstractmethod
    def send(
        self,
        payload: NotificationPayload,
        ctx: NotificationContext,
    ) -> bool:
        """Send a notification.

        Args:
            payload: Structured notification data containing run statistics
                     and error information
            ctx: Notification context with additional metadata

        Returns:
            True if notification was sent successfully, False otherwise.

        Note:
            Implementations MUST NOT raise exceptions. Log errors and
            return False instead so that notification failures don't
            break the main pipeline.
        """
        raise NotImplementedError

    def format_message(self, payload: NotificationPayload) -> str:
        """Format a human-readable message from the payload.

        Default implementation creates a simple text message. Override
        for platform-specific formatting (e.g., Slack blocks, Discord
        embeds, HTML email).

        Args:
            payload: The notification payload to format

        Returns:
            Formatted message string ready to send
        """
        outcome = "ERROR" if payload.has_errors else "OK"
        lines = [f"Supersidian: {payload.vault_name} - [{outcome}]", ""]

        # Show errors first if any exist
        if payload.error_messages:
            if len(payload.error_messages) == 1:
                lines.append(f"Error: {payload.error_messages[0]}")
            else:
                lines.append("Errors:")
                for err in payload.error_messages:
                    lines.append(f"- {err}")
            lines.append("")

        # Append run statistics
        lines.extend(
            [
                f"Notes: {payload.notes_found}",
                f"Converted: {payload.converted}",
                f"Skipped: {payload.skipped}",
                f"No text: {payload.no_text}",
            ]
        )

        return "\n".join(lines)


class NoopNotificationProvider(BaseNotificationProvider):
    """A provider that sends no notifications.

    Useful when notifications are disabled or for testing. Always
    returns True to indicate "success" without actually doing anything.
    """

    name: str = "noop"

    def send(
        self,
        payload: NotificationPayload,
        ctx: NotificationContext,
    ) -> bool:
        """Silently succeed without sending any notification."""
        return True
