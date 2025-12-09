"""Base interfaces for Supersidian todo providers.

This module defines the common abstractions that all todo providers
(Todoist, etc.) should implement. It deliberately does not know about
any specific API; providers live in their own modules and are wired in
via the registry in supersidian.todo.__init__.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

from ..storage import LocalTask, TaskSyncResult


@dataclass(frozen=True)
class TodoContext:
    """Context about the current bridge and vault for todo sync.

    This is provided by supersidian.py when calling a provider so that the
    provider can, for example, add vault-specific labels or include
    note paths in external task descriptions.
    """

    bridge_name: str          # e.g. "klick"
    vault_name: str           # e.g. "Klick"
    vault_path: Path          # absolute path to the vault root
    note_url_builder: Callable[[str], str]  # Function to build app-specific note URLs


class BaseTodoProvider(ABC):
    """Abstract base class for todo providers.

    A provider is responsible for taking LocalTask objects and
    attempting to sync them to an external system (e.g. Todoist).

    It must *not* raise on per-task failures; instead it should return
    a TaskSyncResult for each attempted task describing what happened.
    """

    name: str = "base"

    @abstractmethod
    def sync_tasks(
        self,
        tasks: Sequence[LocalTask],
        ctx: TodoContext,
    ) -> list[TaskSyncResult]:
        """Sync a batch of tasks to the external system.

        Implementations should:
        - treat the input list as *new* tasks to be created (or at most
          idempotently re-checked), not a full mirror of external state;
        - avoid raising on per-task failures, and instead include a
          TaskSyncResult with status="failed" and an error message;
        - return one TaskSyncResult per input LocalTask.

        The storage layer (storage.record_task_sync_results) is
        responsible for persisting these outcomes.
        """
        raise NotImplementedError


class NoopTodoProvider(BaseTodoProvider):
    """A provider that does nothing.

    Useful as a default when todo sync is disabled or misconfigured.
    It simply returns a "skipped" TaskSyncResult for each task.
    """

    name: str = "noop"

    def sync_tasks(
        self,
        tasks: Sequence[LocalTask],
        ctx: TodoContext,
    ) -> list[TaskSyncResult]:
        results: list[TaskSyncResult] = []
        for t in tasks:
            results.append(
                TaskSyncResult(
                    local_id=t.local_id,
                    provider=self.name,
                    external_id=None,
                    status="skipped",
                    error="todo sync disabled or noop provider in use",
                )
            )
        return results
