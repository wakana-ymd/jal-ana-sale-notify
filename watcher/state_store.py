from __future__ import annotations

import sqlite3
from pathlib import Path

from watcher.models import WatchState


class SQLiteStateStore:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def load(self, document_id: str, airline: str, url: str) -> WatchState:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                  airline,
                  url,
                  last_hash,
                  last_notified_hash,
                  last_important_text,
                  last_checked_at,
                  last_changed_at,
                  consecutive_error_count,
                  last_error,
                  is_error_notified
                FROM watch_states
                WHERE document_id = ?
                """,
                (document_id,),
            ).fetchone()

        if row is None:
            return WatchState.empty(airline=airline, url=url)

        data = {
            "airline": row["airline"],
            "url": row["url"],
            "last_hash": row["last_hash"],
            "last_notified_hash": row["last_notified_hash"],
            "last_important_text": row["last_important_text"],
            "last_checked_at": row["last_checked_at"],
            "last_changed_at": row["last_changed_at"],
            "consecutive_error_count": row["consecutive_error_count"],
            "last_error": row["last_error"],
            "is_error_notified": bool(row["is_error_notified"]),
        }
        return WatchState.from_dict(data, airline=airline, url=url)

    def save(self, document_id: str, state: WatchState) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO watch_states (
                  document_id,
                  airline,
                  url,
                  last_hash,
                  last_notified_hash,
                  last_important_text,
                  last_checked_at,
                  last_changed_at,
                  consecutive_error_count,
                  last_error,
                  is_error_notified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET
                  airline = excluded.airline,
                  url = excluded.url,
                  last_hash = excluded.last_hash,
                  last_notified_hash = excluded.last_notified_hash,
                  last_important_text = excluded.last_important_text,
                  last_checked_at = excluded.last_checked_at,
                  last_changed_at = excluded.last_changed_at,
                  consecutive_error_count = excluded.consecutive_error_count,
                  last_error = excluded.last_error,
                  is_error_notified = excluded.is_error_notified
                """,
                (
                    document_id,
                    state.airline,
                    state.url,
                    state.last_hash,
                    state.last_notified_hash,
                    state.last_important_text,
                    state.last_checked_at,
                    state.last_changed_at,
                    state.consecutive_error_count,
                    state.last_error,
                    int(state.is_error_notified),
                ),
            )
            conn.commit()

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS watch_states (
                  document_id TEXT PRIMARY KEY,
                  airline TEXT NOT NULL,
                  url TEXT NOT NULL,
                  last_hash TEXT NOT NULL,
                  last_notified_hash TEXT NOT NULL,
                  last_important_text TEXT NOT NULL,
                  last_checked_at TEXT,
                  last_changed_at TEXT,
                  consecutive_error_count INTEGER NOT NULL DEFAULT 0,
                  last_error TEXT,
                  is_error_notified INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
