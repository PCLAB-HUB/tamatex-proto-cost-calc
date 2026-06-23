"""状態管理モジュール。SQLite でファイルの同期状態を永続管理する。

スキーマ:
    file_path       : NASファイルの絶対パス（PK）
    mtime           : 最終変更時刻（エポック秒）
    file_hash       : 内容MD5
    spreadsheet_id  : 同期先 Google Sheets の fileId
    pdf_file_id     : 同期先 PDF の fileId
    last_sync       : 最終同期実行時刻（エポック秒）

pdf_file_id は後から追加されたカラムのため、既存 DB に対しては
_init_db() 内で ALTER TABLE による自動マイグレーションを行う。
"""

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
    pdf_file_id: str
    last_sync: float


class StateDB:
    """SQLite ベースの同期状態管理。"""

    def __init__(self, db_path: str | Path = "./tamatex_state.db"):
        self._db_path = str(db_path)
        self._conn: sqlite3.Connection = sqlite3.connect(self._db_path)
        self._init_db()

    def _init_db(self) -> None:
        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS file_states (
                    file_path TEXT PRIMARY KEY,
                    mtime REAL NOT NULL,
                    file_hash TEXT NOT NULL,
                    spreadsheet_id TEXT NOT NULL DEFAULT '',
                    pdf_file_id TEXT NOT NULL DEFAULT '',
                    last_sync REAL NOT NULL DEFAULT 0
                )
            """)
            # 既存DB向けマイグレーション: pdf_file_id カラムが無ければ追加
            existing_cols = {
                row[1]
                for row in self._conn.execute(
                    "PRAGMA table_info(file_states)"
                ).fetchall()
            }
            if "pdf_file_id" not in existing_cols:
                self._conn.execute(
                    "ALTER TABLE file_states ADD COLUMN "
                    "pdf_file_id TEXT NOT NULL DEFAULT ''"
                )

    def close(self) -> None:
        """コネクションを閉じる。"""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def get_state(self, file_path: str) -> FileState | None:
        """指定ファイルの同期状態を取得。"""
        row = self._conn.execute(
            "SELECT file_path, mtime, file_hash, spreadsheet_id, pdf_file_id, last_sync "
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
        pdf_file_id: str = "",
    ) -> None:
        """ファイルの同期状態を更新（upsert）。"""
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO file_states
                    (file_path, mtime, file_hash, spreadsheet_id, pdf_file_id, last_sync)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    mtime = excluded.mtime,
                    file_hash = excluded.file_hash,
                    spreadsheet_id = excluded.spreadsheet_id,
                    pdf_file_id = excluded.pdf_file_id,
                    last_sync = excluded.last_sync
                """,
                (file_path, mtime, file_hash, spreadsheet_id, pdf_file_id, time.time()),
            )

    def get_all_states(self) -> list[FileState]:
        """全ファイルの同期状態を取得。"""
        rows = self._conn.execute(
            "SELECT file_path, mtime, file_hash, spreadsheet_id, pdf_file_id, last_sync "
            "FROM file_states"
        ).fetchall()
        return [FileState(*row) for row in rows]

    def remove_state(self, file_path: str) -> None:
        """指定ファイルの同期状態を削除。"""
        with self._conn:
            self._conn.execute(
                "DELETE FROM file_states WHERE file_path = ?", (file_path,)
            )
