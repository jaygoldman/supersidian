"""Menubar notification provider for Supersidian.

This provider updates the SQLite database with current bridge status and
sends Darwin notifications to wake up the macOS menubar app. It writes
to two tables:

- bridge_status: Current status for each bridge (updated on every run)
- sync_history: Historical records for charts and trends

The menubar app reads these tables and listens for Darwin notifications
to update its UI in real-time.
"""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime

from ..storage import _get_connection
from .base import BaseNotificationProvider, NotificationContext, NotificationPayload

log = logging.getLogger("supersidian")


class MenubarProvider(BaseNotificationProvider):
    """Notification provider for macOS menubar app integration.

    This provider writes sync status to the database and sends a Darwin
    notification to trigger UI updates in the menubar app.

    Features:
    - Updates bridge_status table with current state
    - Appends to sync_history for historical tracking
    - Sends Darwin notification via notifyutil
    - Calculates task counts from tasks table
    - Determines status based on errors and conversion results

    The menubar app subscribes to 'com.supersidian.sync.complete' and
    refreshes its display when notified.
    """

    name: str = "menubar"

    def send(
        self,
        payload: NotificationPayload,
        ctx: NotificationContext,
    ) -> bool:
        """Send notification by updating database and posting Darwin notification.

        Args:
            payload: Structured notification data
            ctx: Notification context

        Returns:
            True if database update and notification succeeded, False otherwise
        """
        try:
            # Calculate overall status based on payload
            status = self._determine_status(payload)

            # Get task counts for this bridge
            tasks_total, tasks_open, tasks_completed = self._get_task_counts(
                payload.bridge_name
            )

            # Build error message if needed
            error_message = None
            if payload.has_errors:
                error_message = "; ".join(payload.error_messages)

            # Update bridge_status table
            self._update_bridge_status(
                bridge_name=payload.bridge_name,
                last_sync_time=payload.timestamp,
                status=status,
                notes_found=payload.notes_found,
                converted=payload.converted,
                skipped=payload.skipped,
                no_text=payload.no_text,
                tasks_total=tasks_total,
                tasks_open=tasks_open,
                tasks_completed=tasks_completed,
                error_message=error_message,
                tool_missing=payload.tool_missing,
                tool_failed=payload.tool_failed,
                supernote_missing=int(payload.supernote_missing),
                vault_missing=int(payload.vault_missing),
            )

            # Append to sync_history table
            self._append_sync_history(
                bridge_name=payload.bridge_name,
                sync_time=payload.timestamp,
                notes_converted=payload.converted,
                notes_skipped=payload.skipped,
                tasks_synced=tasks_total,
                success=not payload.has_errors,
            )

            # Send Darwin notification to wake up menubar app
            self._post_darwin_notification()

            log.info(
                f"[{ctx.bridge_name}] menubar notification sent (status={status})"
            )
            return True

        except Exception as e:
            log.warning(
                f"[{ctx.bridge_name}] failed to send menubar notification: {e}"
            )
            return False

    def _determine_status(self, payload: NotificationPayload) -> str:
        """Determine overall sync status from payload.

        Returns one of: 'success', 'warning', 'error', 'syncing'
        """
        # Check for structural errors (missing paths, etc.)
        if payload.supernote_missing or payload.vault_missing:
            return "error"

        # Check for tool issues (these are actual problems)
        if payload.tool_missing > 0 or payload.tool_failed > 0:
            return "warning"

        # Notes with no text are normal (blank notes, drawings, etc.)
        # Consider the sync successful
        return "success"

    def _get_task_counts(self, bridge_name: str) -> tuple[int, int, int]:
        """Get task counts for a bridge from the tasks table.

        Returns:
            (total, open, completed) task counts
        """
        try:
            conn = _get_connection()
            cur = conn.cursor()

            cur.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN completed = 0 THEN 1 ELSE 0 END) as open,
                    SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed
                FROM tasks
                WHERE bridge_name = ?
                """,
                (bridge_name,),
            )

            row = cur.fetchone()
            if row:
                total = row["total"] or 0
                open_count = row["open"] or 0
                completed_count = row["completed"] or 0
                return (total, open_count, completed_count)

            return (0, 0, 0)

        except Exception as e:
            log.warning(f"[{bridge_name}] failed to get task counts: {e}")
            return (0, 0, 0)

    def _update_bridge_status(
        self,
        bridge_name: str,
        last_sync_time: str,
        status: str,
        notes_found: int,
        converted: int,
        skipped: int,
        no_text: int,
        tasks_total: int,
        tasks_open: int,
        tasks_completed: int,
        error_message: str | None,
        tool_missing: int,
        tool_failed: int,
        supernote_missing: int,
        vault_missing: int,
    ) -> None:
        """Update or insert bridge_status row."""
        conn = _get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO bridge_status (
                bridge_name,
                last_sync_time,
                status,
                notes_found,
                converted,
                skipped,
                no_text,
                tasks_total,
                tasks_open,
                tasks_completed,
                error_message,
                tool_missing,
                tool_failed,
                supernote_missing,
                vault_missing
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(bridge_name) DO UPDATE SET
                last_sync_time     = excluded.last_sync_time,
                status             = excluded.status,
                notes_found        = excluded.notes_found,
                converted          = excluded.converted,
                skipped            = excluded.skipped,
                no_text            = excluded.no_text,
                tasks_total        = excluded.tasks_total,
                tasks_open         = excluded.tasks_open,
                tasks_completed    = excluded.tasks_completed,
                error_message      = excluded.error_message,
                tool_missing       = excluded.tool_missing,
                tool_failed        = excluded.tool_failed,
                supernote_missing  = excluded.supernote_missing,
                vault_missing      = excluded.vault_missing
            """,
            (
                bridge_name,
                last_sync_time,
                status,
                notes_found,
                converted,
                skipped,
                no_text,
                tasks_total,
                tasks_open,
                tasks_completed,
                error_message,
                tool_missing,
                tool_failed,
                supernote_missing,
                vault_missing,
            ),
        )

        conn.commit()

    def _append_sync_history(
        self,
        bridge_name: str,
        sync_time: str,
        notes_converted: int,
        notes_skipped: int,
        tasks_synced: int,
        success: bool,
    ) -> None:
        """Append a new sync_history record."""
        conn = _get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO sync_history (
                bridge_name,
                sync_time,
                notes_converted,
                notes_skipped,
                tasks_synced,
                success
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                bridge_name,
                sync_time,
                notes_converted,
                notes_skipped,
                tasks_synced,
                1 if success else 0,
            ),
        )

        conn.commit()

    def _post_darwin_notification(self) -> None:
        """Post a Darwin notification to wake up the menubar app.

        Uses the notifyutil utility which is available on all macOS systems.
        If the utility is not found or fails, we log but don't fail the entire
        notification (database updates still succeeded).
        """
        try:
            subprocess.run(
                ["notifyutil", "-p", "com.supersidian.sync.complete"],
                check=False,
                capture_output=True,
                timeout=1,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
            # Log but don't fail - the database is already updated
            log.debug(f"notifyutil failed (non-critical): {e}")
