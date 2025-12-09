"""Webhook notification provider for Supersidian.

This provider sends JSON POST requests to a configured webhook URL.
Works with any service that accepts JSON webhooks (ntfy.sh, custom
endpoints, etc.).
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

from .base import BaseNotificationProvider, NotificationContext, NotificationPayload

log = logging.getLogger("supersidian")


class WebhookProvider(BaseNotificationProvider):
    """Generic webhook notification provider.

    Sends JSON POST requests to a configured URL. The webhook receives
    a JSON payload containing all run statistics and error information.

    Configuration:
        SUPERSIDIAN_WEBHOOK_URL: The webhook endpoint URL (required)
        SUPERSIDIAN_WEBHOOK_TOPIC: Optional topic/title for the notification
        SUPERSIDIAN_WEBHOOK_TIMEOUT: Request timeout in seconds (default: 5)

    The provider preserves the exact JSON payload format from the original
    implementation for backwards compatibility.
    """

    name: str = "webhook"

    def __init__(self) -> None:
        """Initialize webhook provider from environment variables."""
        self.url = os.environ.get("SUPERSIDIAN_WEBHOOK_URL", "").strip()
        self.topic = os.environ.get("SUPERSIDIAN_WEBHOOK_TOPIC", "").strip()
        self.timeout = int(os.environ.get("SUPERSIDIAN_WEBHOOK_TIMEOUT", "5"))

    def send(
        self,
        payload: NotificationPayload,
        ctx: NotificationContext,
    ) -> bool:
        """Send notification via webhook.

        Args:
            payload: Structured notification data
            ctx: Notification context

        Returns:
            True if webhook returned 2xx status, False otherwise
        """
        if not self.url:
            # No webhook URL configured, silently skip
            return False

        # Build JSON payload matching original format exactly
        data = {
            "bridge": payload.bridge_name,
            "timestamp": payload.timestamp,
            "notes_found": payload.notes_found,
            "converted": payload.converted,
            "skipped": payload.skipped,
            "no_text": payload.no_text,
            "tool_missing": payload.tool_missing,
            "tool_failed": payload.tool_failed,
            "supernote_missing": payload.supernote_missing,
            "vault_missing": payload.vault_missing,
            "title": f"Supersidian: {payload.bridge_name}",
            "message": self.format_message(payload),
        }

        # Add optional topic field if configured
        if self.topic:
            data["topic"] = self.topic

        # Encode and prepare request
        encoded = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            self.url,
            data=encoded,
            headers={"Content-Type": "application/json"},
        )

        # Send request, catching all exceptions
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = getattr(resp, "status", 200)
                success = 200 <= status < 300
                if success:
                    log.info(f"[{ctx.bridge_name}] notification sent (status={status})")
                else:
                    log.warning(
                        f"[{ctx.bridge_name}] webhook returned non-2xx status: {status}"
                    )
                return success
        except urllib.error.HTTPError as e:
            log.warning(
                f"[{ctx.bridge_name}] failed to send notification: HTTP {e.code} {e.reason}"
            )
            return False
        except urllib.error.URLError as e:
            log.warning(
                f"[{ctx.bridge_name}] failed to send notification: {e.reason}"
            )
            return False
        except Exception as e:
            log.warning(
                f"[{ctx.bridge_name}] failed to send notification to {self.url}: {e}"
            )
            return False
