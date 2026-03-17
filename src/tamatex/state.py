"""状態管理モジュール。SQLiteでファイルの同期状態を永続管理する。"""

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileState:
    file_path: str
    mtime: float
    file_hash: str
    spreadsheet_id: str
    last_sync: float


class StateDB:
    """SQLiteベースの同期状態管理。"""

    def __init__(self, db_path: str | Path = "./tamatex_state.db"):
        self._db_path = str(db_path)
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_states (
                    file_path TEXT PRIMARY KEY,
                    mtime REAL NOT NULL,
                    file_hash TEXT NOT NULL,
                    spreadsheet_id TEXT NOT NULL DEFAULT '',
                    last_sync REAL NOT NULL DEFAULT 0
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def get_state(self, file_path: str) -> FileState | None:
        """指定ファイルの同期状態を取得。"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT file_path, mtime, file_hash, spreadsheet_id, last_sync "
                "FROM file_states WHERE file_path = ?",
                (file_path,),
            ).fetchone()
        if row is None:
            return None
        return FileState(*row)

    def update_state(
        self,
        file_path: str,
        mtime: float,
        file_hash: str,
        spreadsheet_id: str,
    ) -> None:
        """ファイルの同期状態を更新（upsert）。"""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO file_states (file_path, mtime, file_hash, spreadsheet_id, last_sync)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    mtime = excluded.mtime,
                    file_hash = excluded.file_hash,
                    spreadsheet_id = excluded.spreadsheet_id,
                    last_sync = excluded.last_sync
                """,
                (file_path, mtime, file_hash, spreadsheet_id, time.time()),
            )

    def get_all_states(self) -> list[FileState]:
        """全ファイルの同期状態を取得。"""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT file_path, mtime, file_hash, spreadsheet_id, last_sync "
                "FROM file_states"
            ).fetchall()
        return [FileState(*row) for row in rows]

    def remove_state(self, file_path: str) -> None:
        """指定ファイルの同期状態を削除。"""
        with self._connect() as conn:
            conn.execute("DELETE FROM file_states WHERE file_path = ?", (file_path,))
