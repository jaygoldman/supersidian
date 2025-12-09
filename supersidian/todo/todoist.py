"""Todoist provider for Supersidian.

This module implements a minimal Todoist integration that creates
inbox tasks for each LocalTask passed in. It is designed to be
idempotent from Supersidian's point of view by only being called for
*new* tasks; Supersidian's storage layer is responsible for making
sure the same local_id is not sent twice.

Behavior:
- Each LocalTask becomes a Todoist task in the user's inbox.
- The task's content is the LocalTask.title.
- The task's description includes vault/note/line context.
- Labels include "supersidian" and a vault-specific label
  like "vault:Klick".

Configuration (via environment variables):
- SUPERSIDIAN_TODOIST_API_TOKEN: required API token.
- SUPERSIDIAN_TODOIST_BASE_URL: optional override of the base REST URL
  (defaults to https://api.todoist.com/rest/v2).
"""

from __future__ import annotations

import json
import os
from typing import List, Sequence
from urllib import error as urlerror
from urllib import request as urlrequest
from urllib.parse import quote

from .base import BaseTodoProvider, TodoContext
from ..storage import LocalTask, TaskSyncResult


class TodoistProvider(BaseTodoProvider):
    """Concrete todo provider that syncs tasks to Todoist."""

    name: str = "todoist"

    def __init__(self) -> None:
        self._token = os.environ.get("SUPERSIDIAN_TODOIST_API_TOKEN", "").strip()
        # Allow overriding the base URL for testing or self-hosted setups.
        self._base_url = (
            os.environ.get("SUPERSIDIAN_TODOIST_BASE_URL", "https://api.todoist.com/rest/v2")
            .strip()
            .rstrip("/")
        )

    def _build_note_url(self, task: LocalTask, ctx: TodoContext) -> str:
        """Build a note app URL that opens the originating note.

        Uses the note_url_builder from the context, which is provided
        by the note provider (Obsidian, markdown, etc.).
        """
        note_path = task.note_path

        # Strip trailing .md if present
        if note_path.lower().endswith(".md"):
            note_path = note_path[:-3]

        # Use the note provider's URL builder
        return ctx.note_url_builder(note_path)

    def _build_description(self, task: LocalTask, ctx: TodoContext) -> str:
        note_url = self._build_note_url(task, ctx)
        lines = [
            "From Supersidian",
            "",
            f"Vault: {ctx.vault_name}",
            f"Note: {task.note_path}",
            f"Line: {task.line_no}",
            f"Local ID: {task.local_id}",
            "",
            f"Note URL: {note_url}",
        ]
        return "\n".join(lines)

    def _build_labels(self, ctx: TodoContext) -> List[str]:
        labels: List[str] = []
        # Always tag as coming from Supersidian.
        labels.append("supersidian")
        # Add a vault-specific label, which makes it possible to filter
        # tasks by originating vault inside Todoist.
        labels.append(f"vault:{ctx.vault_name}")
        return labels

    def sync_tasks(
        self,
        tasks: Sequence[LocalTask],
        ctx: TodoContext,
    ) -> List[TaskSyncResult]:
        results: List[TaskSyncResult] = []

        if not tasks:
            return results

        if not self._token:
            # Missing token: treat all tasks as failed to sync with a
            # clear error message, but do not raise.
            msg = "SUPERSIDIAN_TODOIST_API_TOKEN is not set"
            for t in tasks:
                results.append(
                    TaskSyncResult(
                        local_id=t.local_id,
                        provider=self.name,
                        external_id=None,
                        status="failed",
                        error=msg,
                    )
                )
            return results

        url = f"{self._base_url}/tasks"

        for t in tasks:
            payload = {
                "content": t.title,
                "description": self._build_description(t, ctx),
                "labels": self._build_labels(ctx),
            }

            data = json.dumps(payload).encode("utf-8")
            req = urlrequest.Request(url, data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("Authorization", f"Bearer {self._token}")

            external_id = None
            status = "created"
            error_msg = None

            try:
                with urlrequest.urlopen(req, timeout=10) as resp:
                    resp_body = resp.read().decode("utf-8") or "{}"
                    try:
                        obj = json.loads(resp_body)
                    except json.JSONDecodeError:
                        obj = {}
                    # Todoist returns an object with an "id" field for
                    # the created task.
                    external_id = str(obj.get("id")) if "id" in obj else None
            except urlerror.HTTPError as e:
                status = "failed"
                error_msg = f"HTTPError {e.code}: {e.reason}"
            except urlerror.URLError as e:
                status = "failed"
                error_msg = f"URLError: {e.reason}"
            except Exception as e:  # pragma: no cover - safety net
                status = "failed"
                error_msg = f"Unexpected error: {e!r}"

            results.append(
                TaskSyncResult(
                    local_id=t.local_id,
                    provider=self.name,
                    external_id=external_id,
                    status=status,
                    error=error_msg,
                )
            )

        return results
