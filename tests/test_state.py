# テスト依存: pytest
"""StateDB の単体テスト。

SQLiteベースの同期状態管理クラス(StateDB)の全メソッドを検証する。
"""

import time

import pytest

from tamatex.state import FileState, StateDB


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------

@pytest.fixture()
def db(tmp_path):
    """一時ディレクトリに作成したStateDBインスタンスを返す。"""
    return StateDB(db_path=tmp_path / "test_state.db")


# ---------------------------------------------------------------------------
# 初期化テスト
# ---------------------------------------------------------------------------

def test_init_creates_table(tmp_path):
    """DBファイルを新規作成すると file_states テーブルが存在すること。"""
    import sqlite3
    db_path = tmp_path / "init_test.db"
    StateDB(db_path=db_path)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='file_states'"
    )
    table = cursor.fetchone()
    conn.close()

    assert table is not None
    assert table[0] == "file_states"


def test_init_creates_table_with_correct_columns(tmp_path):
    """file_states テーブルが必要なカラムをすべて持つこと。"""
    import sqlite3
    db_path = tmp_path / "columns_test.db"
    StateDB(db_path=db_path)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute("PRAGMA table_info(file_states)")
    columns = {row[1] for row in cursor.fetchall()}
    conn.close()

    assert columns == {
        "file_path", "mtime", "file_hash",
        "spreadsheet_id", "pdf_file_id", "last_sync",
    }


def test_init_migrates_old_schema_by_adding_pdf_file_id(tmp_path):
    """pdf_file_id カラムが無い旧DBを開いた際、ALTER TABLE で追加されること。"""
    import sqlite3
    db_path = tmp_path / "legacy.db"

    # 旧スキーマ（pdf_file_id なし）でテーブルを作成
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE file_states (
            file_path TEXT PRIMARY KEY,
            mtime REAL NOT NULL,
            file_hash TEXT NOT NULL,
            spreadsheet_id TEXT NOT NULL DEFAULT '',
            last_sync REAL NOT NULL DEFAULT 0
        )
    """)
    conn.execute(
        "INSERT INTO file_states VALUES (?, ?, ?, ?, ?)",
        ("/nas/legacy.xlsx", 1700000000.0, "legacy-hash", "legacy-sheet", 0),
    )
    conn.commit()
    conn.close()

    # StateDB 初期化で自動マイグレーションされるはず
    db = StateDB(db_path=db_path)
    state = db.get_state("/nas/legacy.xlsx")
    db.close()

    assert state is not None
    assert state.spreadsheet_id == "legacy-sheet"
    assert state.pdf_file_id == ""  # 既存行は空文字で補完される


def test_init_is_idempotent(tmp_path):
    """同じDBパスでStateDBを2回生成してもエラーにならないこと。"""
    db_path = tmp_path / "idempotent_test.db"
    StateDB(db_path=db_path)
    StateDB(db_path=db_path)  # CREATE TABLE IF NOT EXISTS なので2回目も安全


# ---------------------------------------------------------------------------
# get_state テスト
# ---------------------------------------------------------------------------

def test_get_state_returns_none_for_nonexistent_path(db):
    """存在しないファイルパスを指定した場合は None を返すこと。"""
    result = db.get_state("/not/exist/file.xlsx")
    assert result is None


def test_get_state_returns_filestate_after_insert(db):
    """update_stateで登録した内容がget_stateで取得できること。"""
    db.update_state(
        file_path="/nas/data/sample.xlsx",
        mtime=1700000000.0,
        file_hash="abc123",
        spreadsheet_id="sheet-id-001",
    )
    result = db.get_state("/nas/data/sample.xlsx")

    assert result is not None
    assert isinstance(result, FileState)
    assert result.file_path == "/nas/data/sample.xlsx"
    assert result.mtime == 1700000000.0
    assert result.file_hash == "abc123"
    assert result.spreadsheet_id == "sheet-id-001"


def test_get_state_last_sync_is_recent(db):
    """update_state実行後にlast_syncが現在時刻に近い値であること。"""
    before = time.time()
    db.update_state(
        file_path="/nas/data/sample.xlsx",
        mtime=1700000000.0,
        file_hash="abc123",
        spreadsheet_id="sheet-id-001",
    )
    after = time.time()

    result = db.get_state("/nas/data/sample.xlsx")
    assert result is not None
    assert before <= result.last_sync <= after


# ---------------------------------------------------------------------------
# update_state（upsert）テスト
# ---------------------------------------------------------------------------

def test_update_state_inserts_new_record(db):
    """存在しないパスに対してupdate_stateを呼ぶと新規レコードが挿入されること。"""
    db.update_state(
        file_path="/nas/new_file.xlsx",
        mtime=1700000001.0,
        file_hash="def456",
        spreadsheet_id="sheet-id-002",
    )
    result = db.get_state("/nas/new_file.xlsx")

    assert result is not None
    assert result.file_hash == "def456"


def test_update_state_updates_existing_record(db):
    """既存レコードに対してupdate_stateを呼ぶと値が上書きされること。"""
    db.update_state(
        file_path="/nas/existing.xlsx",
        mtime=1700000000.0,
        file_hash="old-hash",
        spreadsheet_id="sheet-id-003",
    )
    db.update_state(
        file_path="/nas/existing.xlsx",
        mtime=1700000999.0,
        file_hash="new-hash",
        spreadsheet_id="sheet-id-003",
    )

    result = db.get_state("/nas/existing.xlsx")
    assert result is not None
    assert result.mtime == 1700000999.0
    assert result.file_hash == "new-hash"


def test_update_state_updates_spreadsheet_id(db):
    """update_stateでspreadsheet_idを変更できること。"""
    db.update_state("/nas/file.xlsx", 1.0, "hash1", "old-sheet-id")
    db.update_state("/nas/file.xlsx", 1.0, "hash1", "new-sheet-id")

    result = db.get_state("/nas/file.xlsx")
    assert result is not None
    assert result.spreadsheet_id == "new-sheet-id"


def test_update_state_persists_pdf_file_id(db):
    """update_stateでpdf_file_idを登録・更新できること。"""
    db.update_state(
        file_path="/nas/f.xlsx",
        mtime=1.0,
        file_hash="h1",
        spreadsheet_id="sheet-1",
        pdf_file_id="pdf-1",
    )
    state = db.get_state("/nas/f.xlsx")
    assert state is not None
    assert state.pdf_file_id == "pdf-1"

    db.update_state(
        file_path="/nas/f.xlsx",
        mtime=2.0,
        file_hash="h2",
        spreadsheet_id="sheet-1",
        pdf_file_id="pdf-2",
    )
    state = db.get_state("/nas/f.xlsx")
    assert state is not None
    assert state.pdf_file_id == "pdf-2"


def test_update_state_defaults_pdf_file_id_to_empty(db):
    """pdf_file_id を省略した場合、空文字で保存されること（後方互換）。"""
    db.update_state("/nas/g.xlsx", 1.0, "h", "sheet-id")
    state = db.get_state("/nas/g.xlsx")
    assert state is not None
    assert state.pdf_file_id == ""


# ---------------------------------------------------------------------------
# get_all_states テスト
# ---------------------------------------------------------------------------

def test_get_all_states_returns_empty_list_on_new_db(db):
    """新規DBではget_all_statesが空リストを返すこと。"""
    result = db.get_all_states()
    assert result == []


def test_get_all_states_returns_all_inserted_records(db):
    """複数のレコードを登録した後、get_all_statesが全件返すこと。"""
    db.update_state("/nas/a.xlsx", 1.0, "hash-a", "sheet-a")
    db.update_state("/nas/b.xlsx", 2.0, "hash-b", "sheet-b")
    db.update_state("/nas/c.xlsx", 3.0, "hash-c", "sheet-c")

    result = db.get_all_states()
    paths = {s.file_path for s in result}

    assert len(result) == 3
    assert paths == {"/nas/a.xlsx", "/nas/b.xlsx", "/nas/c.xlsx"}


def test_get_all_states_returns_filestate_instances(db):
    """get_all_statesの返り値がFileStateのリストであること。"""
    db.update_state("/nas/file.xlsx", 1.0, "hash1", "sheet-1")

    result = db.get_all_states()
    assert all(isinstance(s, FileState) for s in result)


# ---------------------------------------------------------------------------
# remove_state テスト
# ---------------------------------------------------------------------------

def test_remove_state_deletes_existing_record(db):
    """remove_stateを呼ぶと対象レコードが削除されること。"""
    db.update_state("/nas/to_delete.xlsx", 1.0, "hash-del", "sheet-del")
    db.remove_state("/nas/to_delete.xlsx")

    result = db.get_state("/nas/to_delete.xlsx")
    assert result is None


def test_remove_state_does_not_affect_other_records(db):
    """remove_stateは指定パス以外のレコードに影響しないこと。"""
    db.update_state("/nas/keep.xlsx", 1.0, "hash-keep", "sheet-keep")
    db.update_state("/nas/delete.xlsx", 2.0, "hash-del", "sheet-del")

    db.remove_state("/nas/delete.xlsx")

    assert db.get_state("/nas/keep.xlsx") is not None
    assert db.get_state("/nas/delete.xlsx") is None


def test_remove_state_on_nonexistent_path_does_not_raise(db):
    """存在しないパスをremove_stateに渡してもエラーにならないこと。"""
    db.remove_state("/not/exist/path.xlsx")  # 例外が起きなければOK


def test_remove_state_reduces_get_all_states_count(db):
    """remove_state後にget_all_statesの件数が減ること。"""
    db.update_state("/nas/a.xlsx", 1.0, "hash-a", "sheet-a")
    db.update_state("/nas/b.xlsx", 2.0, "hash-b", "sheet-b")

    db.remove_state("/nas/a.xlsx")

    result = db.get_all_states()
    assert len(result) == 1
    assert result[0].file_path == "/nas/b.xlsx"
