

"""Persistent storage layer for Supersidian.

This module is intentionally small and focused. It provides:

- A SQLite database at ~/.supersidian.db
- A `tasks` table for tracking extracted tasks and their sync status
- A `runs` table for optional per-run metrics (can be expanded later)

This is *only* the storage layer. Higher-level code in bridge.py is
responsible for:
- Extracting tasks from Markdown notes
- Constructing LocalTask instances
- Deciding when to call providers (Todoist, etc.)
- Calling `record_task_sync_result` with outcomes from providers

Nothing in here knows about specific providers or Markdown.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional, Sequence

# Location of the Supersidian database
DB_PATH: Path = Path.home() / ".supersidian.db"

# Global connection handle (lazy-initialized)
_CONN: Optional[sqlite3.Connection] = None


@dataclass(frozen=True)
class LocalTask:
    """Represents a task extracted from a note.

    This is what Supersidian core code passes into the storage and
    providers. It is provider-agnostic.
    """

    local_id: str          # e.g. "klick:Products/Note.md:17"
    bridge_name: str       # e.g. "klick"
    vault_name: str        # e.g. "Klick"
    note_path: str         # path to note, relative to vault root
    line_no: int           # 1-based line number in the note
    title: str             # task text
    completed: bool        # True if [x], False if [ ]


@dataclass(frozen=True)
class TaskSyncResult:
    """Outcome of attempting to sync a local task to an external provider."""

    local_id: str
    provider: str                 # e.g. "todoist"
    external_id: Optional[str]    # provider's task id, if created
    status: str                   # "created", "updated", "skipped", "failed"
    error: Optional[str] = None   # error message, if any


def _get_connection() -> sqlite3.Connection:
    """Return a singleton SQLite connection, initializing the schema if needed."""

    global _CONN
    if _CONN is not None:
        return _CONN

    needs_init = not DB_PATH.exists()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    if needs_init:
        _init_schema(conn)
    else:
        # Even if the file exists, make sure schema is up to date.
        _init_schema(conn)

    _CONN = conn
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they do not exist.

    This is intentionally simple; if we ever need migrations, we can
    add a tiny schema_version table and migrate based on that.
    """

    cur = conn.cursor()

    # Tasks table: one row per local task that Supersidian has seen.
    #
    # local_id is the primary key and should be stable across runs
    # (e.g., vault/note/line combination). External providers can be
    # swapped in and out without changing this identity.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            local_id        TEXT PRIMARY KEY,
            bridge_name     TEXT NOT NULL,
            vault_name      TEXT NOT NULL,
            note_path       TEXT NOT NULL,
            line_no         INTEGER NOT NULL,
            title           TEXT NOT NULL,
            provider        TEXT,
            external_id     TEXT,
            status          TEXT NOT NULL,
            completed       INTEGER NOT NULL,
            created_at      TEXT NOT NULL,
            last_synced_at  TEXT,
            last_error      TEXT
        )
        """
    )

    # Runs table: optional high-level metrics per bridge run.
    # This is not yet used by core logic but gives us a place to
    # store history if we decide to surface it later.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            bridge_name     TEXT NOT NULL,
            started_at      TEXT NOT NULL,
            finished_at     TEXT,
            notes_found     INTEGER DEFAULT 0,
            converted       INTEGER DEFAULT 0,
            skipped         INTEGER DEFAULT 0,
            no_text         INTEGER DEFAULT 0,
            tool_missing    INTEGER DEFAULT 0,
            tool_failed     INTEGER DEFAULT 0,
            todos_extracted INTEGER DEFAULT 0,
            todos_created   INTEGER DEFAULT 0,
            todos_failed    INTEGER DEFAULT 0
        )
        """
    )

    conn.commit()


# ---------------------------------------------------------------------------
# Task-level operations
# ---------------------------------------------------------------------------


def get_known_task_ids(local_ids: Sequence[str]) -> set[str]:
    """Return the subset of local_ids that already exist in the tasks table.

    Used by core logic to avoid creating duplicate tasks in providers.
    """

    if not local_ids:
        return set()

    conn = _get_connection()
    cur = conn.cursor()

    # Use a parameterized IN clause; SQLite supports this fine.
    placeholders = ",".join("?" for _ in local_ids)
    cur.execute(
        f"SELECT local_id FROM tasks WHERE local_id IN ({placeholders})",
        list(local_ids),
    )

    return {row["local_id"] for row in cur.fetchall()}


def record_task_sync_results(
    tasks: Iterable[LocalTask],
    results: Iterable[TaskSyncResult],
) -> None:
    """Persist the outcome of syncing a batch of tasks.

    Expected usage:
    - Core code extracts tasks from a note and builds LocalTask objects.
    - Provider returns TaskSyncResult objects per task.
    - Core calls this function once per batch.

    This function:
    - Inserts rows for newly seen tasks.
    - Updates rows for tasks we've seen before.
    """

    conn = _get_connection()
    cur = conn.cursor()

    # Index results by local_id for quick lookup
    result_by_id = {r.local_id: r for r in results}
    now = datetime.utcnow().isoformat(timespec="seconds")

    for task in tasks:
        res = result_by_id.get(task.local_id)
        if res is None:
            # No provider result recorded for this task; skip.
            continue

        completed_int = 1 if task.completed else 0

        cur.execute(
            """
            INSERT INTO tasks (
                local_id,
                bridge_name,
                vault_name,
                note_path,
                line_no,
                title,
                provider,
                external_id,
                status,
                completed,
                created_at,
                last_synced_at,
                last_error
            ) VALUES (
                :local_id,
                :bridge_name,
                :vault_name,
                :note_path,
                :line_no,
                :title,
                :provider,
                :external_id,
                :status,
                :completed,
                :created_at,
                :last_synced_at,
                :last_error
            )
            ON CONFLICT(local_id) DO UPDATE SET
                provider      = excluded.provider,
                external_id   = excluded.external_id,
                status        = excluded.status,
                completed     = excluded.completed,
                last_synced_at= excluded.last_synced_at,
                last_error    = excluded.last_error
            """,
            {
                "local_id": task.local_id,
                "bridge_name": task.bridge_name,
                "vault_name": task.vault_name,
                "note_path": task.note_path,
                "line_no": task.line_no,
                "title": task.title,
                "provider": res.provider,
                "external_id": res.external_id,
                "status": res.status,
                "completed": completed_int,
                "created_at": now,
                "last_synced_at": now,
                "last_error": res.error,
            },
        )

    conn.commit()


# ---------------------------------------------------------------------------
# Run-level operations (optional, for future use)
# ---------------------------------------------------------------------------


def start_run(bridge_name: str) -> int:
    """Insert a new run row and return its id.

    Core code can call this at the beginning of a bridge run, then
    later call `finish_run` with aggregated metrics.
    """

    conn = _get_connection()
    cur = conn.cursor()
    started_at = datetime.utcnow().isoformat(timespec="seconds")

    cur.execute(
        """
        INSERT INTO runs (
            bridge_name,
            started_at
        ) VALUES (?, ?)
        """,
        (bridge_name, started_at),
    )

    conn.commit()
    return int(cur.lastrowid)


def finish_run(
    run_id: int,
    *,
    notes_found: int = 0,
    converted: int = 0,
    skipped: int = 0,
    no_text: int = 0,
    tool_missing: int = 0,
    tool_failed: int = 0,
    todos_extracted: int = 0,
    todos_created: int = 0,
    todos_failed: int = 0,
) -> None:
    """Update a run row with metrics gathered during the bridge run."""

    conn = _get_connection()
    cur = conn.cursor()
    finished_at = datetime.utcnow().isoformat(timespec="seconds")

    cur.execute(
        """
        UPDATE runs SET
            finished_at      = :finished_at,
            notes_found      = :notes_found,
            converted        = :converted,
            skipped          = :skipped,
            no_text          = :no_text,
            tool_missing     = :tool_missing,
            tool_failed      = :tool_failed,
            todos_extracted  = :todos_extracted,
            todos_created    = :todos_created,
            todos_failed     = :todos_failed
        WHERE id = :run_id
        """,
        {
            "finished_at": finished_at,
            "notes_found": notes_found,
            "converted": converted,
            "skipped": skipped,
            "no_text": no_text,
            "tool_missing": tool_missing,
            "tool_failed": tool_failed,
            "todos_extracted": todos_extracted,
            "todos_created": todos_created,
            "todos_failed": todos_failed,
            "run_id": run_id,
        },
    )

    conn.commit()