"""シナリオリポジトリ — SQLite を用いた CRUD 操作.

`ImportCondition` を JSON にシリアライズして `scenarios` テーブルに保存し、
list / get / save / update / delete / duplicate / exists / close の
8 メソッドで CRUD を提供する。

スキーマ:
    scenarios(id, name UNIQUE, created_at, updated_at, condition_json)
    idx_scenarios_updated (updated_at DESC)
"""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from proto.engine.models import ImportCondition
from proto.storage.serializer import condition_from_json, condition_to_json


# ---------------------------------------------------------------------------
# 返却型
# ---------------------------------------------------------------------------


@dataclass
class ScenarioMeta:
    """シナリオのメタ情報（condition_json を除く）."""

    id: int
    name: str
    created_at: str
    updated_at: str


@dataclass
class Scenario:
    """シナリオの完全データ."""

    id: int
    name: str
    created_at: str
    updated_at: str
    condition: ImportCondition


# ---------------------------------------------------------------------------
# 例外
# ---------------------------------------------------------------------------


class ScenarioNotFoundError(Exception):
    """指定 id のシナリオが存在しない場合に送出される."""


class ScenarioNameConflictError(Exception):
    """同名シナリオが既に存在する場合に送出される."""


# ---------------------------------------------------------------------------
# リポジトリ
# ---------------------------------------------------------------------------


class ScenarioRepository:
    """SQLite を用いたシナリオ CRUD リポジトリ.

    Args:
        db_path: SQLite ファイルパス。存在しない場合は自動作成される。

    Example::

        repo = ScenarioRepository(Path("data/scenarios.db"))
        sid = repo.save_scenario("標準", COND_20FT)
        scenario = repo.get_scenario(sid)
        repo.close()
    """

    def __init__(self, db_path: Path | str) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: Streamlit は各スクリプト実行で別スレッドを生成するが、
        # @st.cache_resource でシングルトン化した ScenarioRepository を再利用するため、
        # 別スレッドからの使用を許可する必要がある。複数セッション/タブからの同時
        # アクセスに備え、全 CRUD 操作を _lock（RLock）で直列化する。RLock にする
        # ことで duplicate→save / update→get のメソッド間再入も安全に行える。
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    # ------------------------------------------------------------------
    # スキーマ初期化
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        """初回接続時にテーブルとインデックスを作成する（冪等）."""
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS scenarios (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    name           TEXT    NOT NULL UNIQUE,
                    created_at     TEXT    NOT NULL,
                    updated_at     TEXT    NOT NULL,
                    condition_json TEXT    NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_scenarios_updated
                    ON scenarios (updated_at DESC);
                """
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # 内部ユーティリティ
    # ------------------------------------------------------------------

    @staticmethod
    def _now() -> str:
        """現在時刻を UTC ISO 8601 文字列で返す."""
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # 公開 API
    # ------------------------------------------------------------------

    def list_scenarios(self) -> list[ScenarioMeta]:
        """全シナリオのメタ情報を updated_at DESC 順で返す.

        Returns:
            ScenarioMeta のリスト。シナリオが存在しない場合は空リスト。
        """
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, name, created_at, updated_at "
                "FROM scenarios ORDER BY updated_at DESC"
            )
            return [
                ScenarioMeta(
                    id=row["id"],
                    name=row["name"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in cur.fetchall()
            ]

    def get_scenario(self, id: int) -> Scenario:
        """指定 id のシナリオを完全データで返す.

        Args:
            id: シナリオ ID。

        Returns:
            Scenario インスタンス。

        Raises:
            ScenarioNotFoundError: 指定 id が存在しない場合。
        """
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, name, created_at, updated_at, condition_json "
                "FROM scenarios WHERE id = ?",
                (id,),
            )
            row = cur.fetchone()
        if row is None:
            raise ScenarioNotFoundError(f"Scenario id={id} not found")
        return Scenario(
            id=row["id"],
            name=row["name"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            condition=condition_from_json(row["condition_json"]),
        )

    def save_scenario(self, name: str, cond: ImportCondition) -> int:
        """新規シナリオを保存し、割り当てられた id を返す.

        Args:
            name: シナリオ名（UNIQUE 制約あり）。
            cond: 保存する輸入条件。

        Returns:
            新規シナリオの id。

        Raises:
            ScenarioNameConflictError: 同名シナリオが既に存在する場合。
        """
        now = self._now()
        condition_json = condition_to_json(cond)
        with self._lock:
            try:
                cur = self._conn.execute(
                    "INSERT INTO scenarios (name, created_at, updated_at, condition_json) "
                    "VALUES (?, ?, ?, ?)",
                    (name, now, now, condition_json),
                )
                self._conn.commit()
                return cur.lastrowid  # type: ignore[return-value]
            except sqlite3.IntegrityError as exc:
                self._conn.rollback()
                raise ScenarioNameConflictError(
                    f"Scenario name '{name}' already exists"
                ) from exc

    def update_scenario(
        self,
        id: int,
        *,
        name: str | None = None,
        cond: ImportCondition | None = None,
    ) -> None:
        """既存シナリオを部分更新する.

        Args:
            id: 更新対象のシナリオ ID。
            name: 新しいシナリオ名。None の場合は変更しない。
            cond: 新しい輸入条件。None の場合は変更しない。

        Raises:
            ScenarioNotFoundError: 指定 id が存在しない場合。
            ScenarioNameConflictError: 変更後の name が他シナリオと衝突する場合。
        """
        if name is None and cond is None:
            # 対象の存在確認のみ行い、更新するものがなければ早期リターン
            self.get_scenario(id)
            return

        sets: list[str] = ["updated_at = ?"]
        params: list[object] = [self._now()]

        if name is not None:
            sets.append("name = ?")
            params.append(name)
        if cond is not None:
            sets.append("condition_json = ?")
            params.append(condition_to_json(cond))

        sql = f"UPDATE scenarios SET {', '.join(sets)} WHERE id = ?"  # noqa: S608
        with self._lock:
            # 対象の存在確認（get_scenario は not found 時に例外送出 / RLock 再入）
            self.get_scenario(id)
            params.append(id)
            try:
                self._conn.execute(sql, params)
                self._conn.commit()
            except sqlite3.IntegrityError as exc:
                self._conn.rollback()
                raise ScenarioNameConflictError(
                    f"Scenario name '{name}' already exists"
                ) from exc

    def delete_scenario(self, id: int) -> None:
        """指定 id のシナリオを削除する.

        存在しない id は no-op（例外を送出しない）。

        Args:
            id: 削除対象のシナリオ ID。
        """
        with self._lock:
            self._conn.execute("DELETE FROM scenarios WHERE id = ?", (id,))
            self._conn.commit()

    def duplicate_scenario(self, id: int, new_name: str) -> int:
        """既存シナリオを新しい名前でコピーし、新しい id を返す.

        Args:
            id: コピー元のシナリオ ID。
            new_name: 新しいシナリオ名。

        Returns:
            複製シナリオの id。

        Raises:
            ScenarioNotFoundError: コピー元 id が存在しない場合。
            ScenarioNameConflictError: new_name が既に存在する場合。
        """
        with self._lock:
            # get→save をアトミックに行うため Lock 内で実行（RLock 再入）
            original = self.get_scenario(id)
            return self.save_scenario(new_name, original.condition)

    def scenario_exists(self, name: str) -> bool:
        """指定名のシナリオが存在するかを返す.

        保存前のバリデーションで使用することを想定する。

        Args:
            name: 確認するシナリオ名。

        Returns:
            存在する場合 True、存在しない場合 False。
        """
        with self._lock:
            cur = self._conn.execute(
                "SELECT 1 FROM scenarios WHERE name = ? LIMIT 1", (name,)
            )
            return cur.fetchone() is not None

    def close(self) -> None:
        """SQLite コネクションをクローズする."""
        with self._lock:
            self._conn.close()
