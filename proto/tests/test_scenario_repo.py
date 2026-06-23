"""ScenarioRepository の CRUD 統合テスト.

pytest の `tmp_path` fixture を使い、テスト毎に独立した SQLite ファイルで
CREATE / READ / UPDATE / DELETE / DUPLICATE / 制約違反 / NOT FOUND をカバーする。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from proto.data.mock_params import COND_20FT, COND_40FT
from proto.engine.models import ImportCondition, ImportExpenses
from proto.storage.scenario_repo import (
    ScenarioNameConflictError,
    ScenarioNotFoundError,
    ScenarioRepository,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def repo(tmp_path: Path) -> ScenarioRepository:
    """テスト毎に独立した SQLite DB を持つリポジトリ."""
    r = ScenarioRepository(tmp_path / "scenarios.db")
    yield r
    r.close()


@pytest.fixture
def populated_repo(repo: ScenarioRepository) -> tuple[ScenarioRepository, int, int]:
    """2 件保存済みのリポジトリと各 id を返す."""
    sid1 = repo.save_scenario("20FT標準", COND_20FT)
    sid2 = repo.save_scenario("40FT標準", COND_40FT)
    return repo, sid1, sid2


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------


class TestCreate:
    """save_scenario のテスト."""

    def test_save_returns_positive_int_id(self, repo: ScenarioRepository) -> None:
        """save_scenario が正の整数 id を返すこと."""
        sid = repo.save_scenario("テスト", COND_20FT)
        assert isinstance(sid, int)
        assert sid > 0

    def test_save_second_gets_different_id(self, repo: ScenarioRepository) -> None:
        """2 件目は 1 件目と異なる id が割り当てられること."""
        sid1 = repo.save_scenario("シナリオA", COND_20FT)
        sid2 = repo.save_scenario("シナリオB", COND_40FT)
        assert sid1 != sid2

    def test_save_name_conflict_raises(self, repo: ScenarioRepository) -> None:
        """同名での 2 回目保存は ScenarioNameConflictError を送出すること."""
        repo.save_scenario("重複テスト", COND_20FT)
        with pytest.raises(ScenarioNameConflictError):
            repo.save_scenario("重複テスト", COND_40FT)


# ---------------------------------------------------------------------------
# READ
# ---------------------------------------------------------------------------


class TestRead:
    """list_scenarios / get_scenario のテスト."""

    def test_get_scenario_returns_correct_name(
        self, populated_repo: tuple[ScenarioRepository, int, int]
    ) -> None:
        """get_scenario が正しい name を返すこと."""
        repo, sid1, _ = populated_repo
        scenario = repo.get_scenario(sid1)
        assert scenario.name == "20FT標準"

    def test_get_scenario_returns_correct_condition(
        self, populated_repo: tuple[ScenarioRepository, int, int]
    ) -> None:
        """get_scenario が保存時の ImportCondition と等価な condition を返すこと."""
        repo, sid1, _ = populated_repo
        scenario = repo.get_scenario(sid1)
        assert scenario.condition == COND_20FT

    def test_list_scenarios_returns_all(
        self, populated_repo: tuple[ScenarioRepository, int, int]
    ) -> None:
        """list_scenarios が全件返すこと."""
        repo, sid1, sid2 = populated_repo
        metas = repo.list_scenarios()
        assert len(metas) == 2

    def test_list_scenarios_no_condition_json(
        self, populated_repo: tuple[ScenarioRepository, int, int]
    ) -> None:
        """list_scenarios の返却値が ScenarioMeta（condition なし）であること."""
        repo, _, _ = populated_repo
        metas = repo.list_scenarios()
        for meta in metas:
            assert not hasattr(meta, "condition")
            assert hasattr(meta, "id")
            assert hasattr(meta, "name")
            assert hasattr(meta, "created_at")
            assert hasattr(meta, "updated_at")

    def test_list_and_get_consistency(
        self, populated_repo: tuple[ScenarioRepository, int, int]
    ) -> None:
        """list_scenarios の id と get_scenario の id・name が一致すること."""
        repo, sid1, sid2 = populated_repo
        metas = repo.list_scenarios()
        meta_ids = {m.id for m in metas}
        assert {sid1, sid2} == meta_ids

        for meta in metas:
            scenario = repo.get_scenario(meta.id)
            assert scenario.id == meta.id
            assert scenario.name == meta.name

    def test_get_scenario_not_found_raises(self, repo: ScenarioRepository) -> None:
        """存在しない id は ScenarioNotFoundError を送出すること."""
        with pytest.raises(ScenarioNotFoundError):
            repo.get_scenario(99999)

    def test_list_scenarios_empty_db(self, repo: ScenarioRepository) -> None:
        """シナリオが 0 件の場合は空リストを返すこと."""
        assert repo.list_scenarios() == []


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------


class TestUpdate:
    """update_scenario のテスト."""

    def test_update_name_only(self, repo: ScenarioRepository) -> None:
        """name のみ更新できること。condition は変わらない."""
        sid = repo.save_scenario("旧名前", COND_20FT)
        repo.update_scenario(sid, name="新名前")
        scenario = repo.get_scenario(sid)
        assert scenario.name == "新名前"
        assert scenario.condition == COND_20FT

    def test_update_condition_only(self, repo: ScenarioRepository) -> None:
        """cond のみ更新できること。name は変わらない."""
        sid = repo.save_scenario("更新テスト", COND_20FT)
        repo.update_scenario(sid, cond=COND_40FT)
        scenario = repo.get_scenario(sid)
        assert scenario.name == "更新テスト"
        assert scenario.condition == COND_40FT

    def test_update_both_name_and_condition(self, repo: ScenarioRepository) -> None:
        """name と cond を同時に更新できること."""
        sid = repo.save_scenario("両方更新テスト", COND_20FT)
        repo.update_scenario(sid, name="新名前両方", cond=COND_40FT)
        scenario = repo.get_scenario(sid)
        assert scenario.name == "新名前両方"
        assert scenario.condition == COND_40FT

    def test_update_not_found_raises(self, repo: ScenarioRepository) -> None:
        """存在しない id への更新は ScenarioNotFoundError を送出すること."""
        with pytest.raises(ScenarioNotFoundError):
            repo.update_scenario(99999, name="存在しない")

    def test_update_name_conflict_raises(self, repo: ScenarioRepository) -> None:
        """更新後の name が他シナリオと衝突する場合は ScenarioNameConflictError."""
        sid1 = repo.save_scenario("名前A", COND_20FT)
        repo.save_scenario("名前B", COND_40FT)
        with pytest.raises(ScenarioNameConflictError):
            repo.update_scenario(sid1, name="名前B")


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------


class TestDelete:
    """delete_scenario のテスト."""

    def test_delete_removes_from_list(
        self, populated_repo: tuple[ScenarioRepository, int, int]
    ) -> None:
        """削除後は list_scenarios に現れないこと."""
        repo, sid1, _ = populated_repo
        repo.delete_scenario(sid1)
        metas = repo.list_scenarios()
        ids = [m.id for m in metas]
        assert sid1 not in ids

    def test_delete_nonexistent_is_noop(self, repo: ScenarioRepository) -> None:
        """存在しない id の削除は例外を送出しないこと（no-op）."""
        repo.delete_scenario(99999)  # 例外が出なければ OK

    def test_delete_then_get_raises(self, repo: ScenarioRepository) -> None:
        """削除後に同 id を get すると ScenarioNotFoundError が送出されること."""
        sid = repo.save_scenario("削除テスト", COND_20FT)
        repo.delete_scenario(sid)
        with pytest.raises(ScenarioNotFoundError):
            repo.get_scenario(sid)


# ---------------------------------------------------------------------------
# DUPLICATE
# ---------------------------------------------------------------------------


class TestDuplicate:
    """duplicate_scenario のテスト."""

    def test_duplicate_returns_new_id(self, repo: ScenarioRepository) -> None:
        """duplicate_scenario が元とは異なる id を返すこと."""
        sid = repo.save_scenario("オリジナル", COND_20FT)
        new_sid = repo.duplicate_scenario(sid, "コピー")
        assert new_sid != sid

    def test_duplicate_has_same_condition(self, repo: ScenarioRepository) -> None:
        """複製シナリオの condition が元と等価であること."""
        sid = repo.save_scenario("オリジナル複製", COND_20FT)
        new_sid = repo.duplicate_scenario(sid, "コピー複製")
        original = repo.get_scenario(sid)
        copy = repo.get_scenario(new_sid)
        assert copy.condition == original.condition

    def test_duplicate_has_new_name(self, repo: ScenarioRepository) -> None:
        """複製シナリオが指定した新名前を持つこと."""
        sid = repo.save_scenario("元シナリオ", COND_40FT)
        new_sid = repo.duplicate_scenario(sid, "複製シナリオ")
        copy = repo.get_scenario(new_sid)
        assert copy.name == "複製シナリオ"

    def test_duplicate_not_found_raises(self, repo: ScenarioRepository) -> None:
        """存在しない id の複製は ScenarioNotFoundError を送出すること."""
        with pytest.raises(ScenarioNotFoundError):
            repo.duplicate_scenario(99999, "複製失敗")

    def test_duplicate_name_conflict_raises(self, repo: ScenarioRepository) -> None:
        """複製先の name が衝突する場合は ScenarioNameConflictError を送出すること."""
        sid = repo.save_scenario("複製元", COND_20FT)
        repo.save_scenario("既存名", COND_40FT)
        with pytest.raises(ScenarioNameConflictError):
            repo.duplicate_scenario(sid, "既存名")


# ---------------------------------------------------------------------------
# scenario_exists
# ---------------------------------------------------------------------------


class TestScenarioExists:
    """scenario_exists のテスト."""

    def test_exists_true_when_saved(self, repo: ScenarioRepository) -> None:
        """保存済みの name は True を返すこと."""
        repo.save_scenario("存在チェック", COND_20FT)
        assert repo.scenario_exists("存在チェック") is True

    def test_exists_false_when_not_saved(self, repo: ScenarioRepository) -> None:
        """未保存の name は False を返すこと."""
        assert repo.scenario_exists("存在しない名前") is False

    def test_exists_false_after_delete(self, repo: ScenarioRepository) -> None:
        """削除後は False を返すこと."""
        sid = repo.save_scenario("削除後チェック", COND_20FT)
        repo.delete_scenario(sid)
        assert repo.scenario_exists("削除後チェック") is False


# ---------------------------------------------------------------------------
# スキーマ初期化
# ---------------------------------------------------------------------------


class TestSchema:
    """DB スキーマの自動作成確認."""

    def test_new_db_creates_schema_automatically(self, tmp_path: Path) -> None:
        """新規 DB ファイルに接続すると scenarios テーブルが自動作成されること."""
        import sqlite3

        db_path = tmp_path / "new.db"
        repo = ScenarioRepository(db_path)
        repo.close()

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='scenarios'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_new_db_creates_index(self, tmp_path: Path) -> None:
        """接続時に idx_scenarios_updated インデックスが作成されること."""
        import sqlite3

        db_path = tmp_path / "idx_check.db"
        repo = ScenarioRepository(db_path)
        repo.close()

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name='idx_scenarios_updated'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_parent_directory_created_automatically(self, tmp_path: Path) -> None:
        """存在しない親ディレクトリが自動作成されること."""
        deep_path = tmp_path / "nested" / "deep" / "scenarios.db"
        repo = ScenarioRepository(deep_path)
        repo.close()
        assert deep_path.exists()


# ---------------------------------------------------------------------------
# CONCURRENCY（共有コネクションの並行アクセス耐性）
# ---------------------------------------------------------------------------


class TestConcurrency:
    """複数スレッドからの同時アクセスに対する堅牢性.

    Streamlit は複数タブ/セッションで `@st.cache_resource` のシングルトン
    リポジトリを共有しうる。RLock が無いと同一 SQLite コネクションへの
    並行アクセスで間欠的なエラーが起きる。
    """

    def test_concurrent_saves_no_error(self, tmp_path: Path) -> None:
        """複数スレッドが同時に save しても sqlite エラーなく全件保存される."""
        import threading

        repo = ScenarioRepository(tmp_path / "concurrent.db")
        errors: list[Exception] = []

        def worker(i: int) -> None:
            try:
                repo.save_scenario(f"シナリオ{i:03d}", COND_20FT)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"並行保存でエラー発生: {errors}"
        assert len(repo.list_scenarios()) == 20
        repo.close()

    def test_concurrent_mixed_ops_no_error(self, tmp_path: Path) -> None:
        """save / list を並行実行してもエラーなく整合する."""
        import threading

        repo = ScenarioRepository(tmp_path / "mixed.db")
        for i in range(10):
            repo.save_scenario(f"初期{i:03d}", COND_20FT)

        errors: list[Exception] = []

        def saver(i: int) -> None:
            try:
                repo.save_scenario(f"追加{i:03d}", COND_40FT)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        def lister() -> None:
            try:
                repo.list_scenarios()
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads: list[threading.Thread] = []
        for i in range(10):
            threads.append(threading.Thread(target=saver, args=(i,)))
            threads.append(threading.Thread(target=lister))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"並行操作でエラー発生: {errors}"
        assert len(repo.list_scenarios()) == 20
        repo.close()
