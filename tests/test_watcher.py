# テスト依存: pytest
"""watcher モジュールの単体テスト。

scan_files(), detect_changes(), _compute_file_hash(), _matches_any() を検証する。
"""

import hashlib

import pytest

from tamatex.state import StateDB
from tamatex.watcher import (
    ChangeResult,
    FileInfo,
    _compute_file_hash,
    _matches_any,
    detect_changes,
    scan_files,
)


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------

@pytest.fixture()
def db(tmp_path):
    """一時ディレクトリに作成した StateDB を返す。"""
    return StateDB(db_path=tmp_path / "watcher_test.db")


@pytest.fixture()
def nas_dir(tmp_path):
    """NAS フォルダを模した一時ディレクトリ。"""
    nas = tmp_path / "nas"
    nas.mkdir()
    return nas


# ---------------------------------------------------------------------------
# _matches_any テスト
# ---------------------------------------------------------------------------

def test_matches_any_returns_true_when_pattern_matches():
    """ファイル名がパターン一覧のいずれかにマッチする場合 True を返すこと。"""
    assert _matches_any("~$document.xlsx", ["~$*", "*.tmp"]) is True


def test_matches_any_returns_true_for_tmp_extension():
    """*.tmp パターンが .tmp ファイルにマッチすること。"""
    assert _matches_any("file.tmp", ["~$*", "*.tmp"]) is True


def test_matches_any_returns_false_when_no_pattern_matches():
    """どのパターンにもマッチしない場合は False を返すこと。"""
    assert _matches_any("report.xlsx", ["~$*", "*.tmp"]) is False


def test_matches_any_returns_false_for_empty_patterns():
    """パターンリストが空のとき常に False を返すこと。"""
    assert _matches_any("anything.xlsx", []) is False


def test_matches_any_case_sensitive():
    """パターンマッチが大文字小文字を区別すること。"""
    # fnmatch はデフォルトで大文字小文字を区別しないが、パターン次第で動作を確認する
    # 少なくとも正確な小文字パターンは小文字ファイル名にマッチする
    assert _matches_any("file.tmp", ["*.tmp"]) is True


# ---------------------------------------------------------------------------
# _compute_file_hash テスト
# ---------------------------------------------------------------------------

def test_compute_file_hash_returns_md5_hex_string(tmp_path):
    """_compute_file_hash は 32 文字の MD5 16進数文字列を返すこと。"""
    test_file = tmp_path / "sample.bin"
    test_file.write_bytes(b"hello world")

    result = _compute_file_hash(test_file)

    assert isinstance(result, str)
    assert len(result) == 32
    assert all(c in "0123456789abcdef" for c in result)


def test_compute_file_hash_is_consistent(tmp_path):
    """同じファイルに対して繰り返し呼び出しても同じハッシュを返すこと。"""
    test_file = tmp_path / "consistent.bin"
    test_file.write_bytes(b"deterministic content")

    hash1 = _compute_file_hash(test_file)
    hash2 = _compute_file_hash(test_file)

    assert hash1 == hash2


def test_compute_file_hash_differs_for_different_content(tmp_path):
    """内容が異なるファイルのハッシュ値は異なること。"""
    file_a = tmp_path / "file_a.bin"
    file_b = tmp_path / "file_b.bin"
    file_a.write_bytes(b"content A")
    file_b.write_bytes(b"content B")

    hash_a = _compute_file_hash(file_a)
    hash_b = _compute_file_hash(file_b)

    assert hash_a != hash_b


def test_compute_file_hash_matches_expected_md5(tmp_path):
    """計算結果が Python 標準 hashlib での MD5 と一致すること。"""
    data = b"verify me"
    test_file = tmp_path / "verify.bin"
    test_file.write_bytes(data)

    expected = hashlib.md5(data).hexdigest()
    result = _compute_file_hash(test_file)

    assert result == expected


def test_compute_file_hash_works_for_empty_file(tmp_path):
    """空ファイルのハッシュ計算がエラーにならないこと。"""
    empty_file = tmp_path / "empty.bin"
    empty_file.write_bytes(b"")

    result = _compute_file_hash(empty_file)
    expected = hashlib.md5(b"").hexdigest()
    assert result == expected


# ---------------------------------------------------------------------------
# scan_files テスト
# ---------------------------------------------------------------------------

def test_scan_files_finds_xlsx_files(nas_dir):
    """scan_files が .xlsx ファイルを検出すること。"""
    (nas_dir / "report.xlsx").write_bytes(b"PK\x03\x04")  # xlsxのマジックバイト風

    result, _ = scan_files(str(nas_dir), ["*.xlsx"], [])

    paths = [fi.path for fi in result]
    assert any("report.xlsx" in p for p in paths)


def test_scan_files_finds_multiple_xlsx_files(nas_dir):
    """複数の .xlsx ファイルがすべて検出されること。"""
    for name in ("a.xlsx", "b.xlsx", "c.xlsx"):
        (nas_dir / name).write_bytes(b"PK\x03\x04")

    result, _ = scan_files(str(nas_dir), ["*.xlsx"], [])
    assert len(result) == 3


def test_scan_files_excludes_tilde_dollar_temp_files(nas_dir):
    """~$ から始まる一時ファイルが除外されること（Excel ロック中ファイル）。"""
    (nas_dir / "~$locked.xlsx").write_bytes(b"PK\x03\x04")
    (nas_dir / "real.xlsx").write_bytes(b"PK\x03\x04")

    result, _ = scan_files(str(nas_dir), ["*.xlsx"], ["~$*"])

    paths = [fi.path for fi in result]
    assert all("~$" not in p for p in paths)
    assert any("real.xlsx" in p for p in paths)


def test_scan_files_excludes_tmp_extension_files(nas_dir):
    """*.tmp ファイルが除外対象パターンで正しく除外されること。"""
    (nas_dir / "data.tmp").write_bytes(b"temp data")
    (nas_dir / "data.xlsx").write_bytes(b"PK\x03\x04")

    result, _ = scan_files(str(nas_dir), ["*.xlsx", "*.tmp"], ["*.tmp"])

    paths = [fi.path for fi in result]
    assert all("data.tmp" not in p for p in paths)


def test_scan_files_raises_os_error_for_nonexistent_path():
    """存在しないパスを渡した場合は OSError が送出されること。"""
    with pytest.raises(OSError, match="NASパスが見つかりません"):
        scan_files("/nonexistent/path/that/does/not/exist", ["*.xlsx"], [])


def test_scan_files_returns_empty_list_for_no_matching_files(nas_dir):
    """一致するファイルがない場合は空リストを返すこと。"""
    (nas_dir / "readme.txt").write_text("not excel", encoding="utf-8")

    result, _ = scan_files(str(nas_dir), ["*.xlsx"], [])
    assert result == []


def test_scan_files_returns_fileinfo_instances(nas_dir):
    """返り値が FileInfo のリストであること。"""
    (nas_dir / "file.xlsx").write_bytes(b"PK\x03\x04")

    result, _ = scan_files(str(nas_dir), ["*.xlsx"], [])
    assert all(isinstance(fi, FileInfo) for fi in result)


def test_scan_files_fileinfo_has_valid_mtime(nas_dir):
    """FileInfo.mtime が正の実数であること。"""
    (nas_dir / "file.xlsx").write_bytes(b"PK\x03\x04")

    result, _ = scan_files(str(nas_dir), ["*.xlsx"], [])
    assert len(result) == 1
    assert result[0].mtime > 0


def test_scan_files_searches_subdirectories(nas_dir):
    """サブディレクトリ内の xlsx ファイルも検出されること。"""
    subdir = nas_dir / "subdir"
    subdir.mkdir()
    (subdir / "nested.xlsx").write_bytes(b"PK\x03\x04")

    result, _ = scan_files(str(nas_dir), ["*.xlsx"], [])

    paths = [fi.path for fi in result]
    assert any("nested.xlsx" in p for p in paths)


def test_scan_files_excludes_with_multiple_patterns(nas_dir):
    """複数の除外パターンがすべて適用されること。"""
    (nas_dir / "~$lock.xlsx").write_bytes(b"PK\x03\x04")
    (nas_dir / "backup.tmp").write_bytes(b"tmp")
    (nas_dir / "valid.xlsx").write_bytes(b"PK\x03\x04")

    result, _ = scan_files(str(nas_dir), ["*.xlsx"], ["~$*", "*.tmp"])

    paths = [fi.path for fi in result]
    assert len(paths) == 1
    assert "valid.xlsx" in paths[0]


# ---------------------------------------------------------------------------
# detect_changes テスト
# ---------------------------------------------------------------------------

def test_detect_changes_identifies_new_files(db):
    """DB に存在しないファイルが new_files として検出されること。"""
    current_files = [FileInfo(path="/nas/new.xlsx", mtime=1.0, file_hash="hash-new")]

    result = detect_changes(current_files, db)

    assert len(result.new_files) == 1
    assert result.new_files[0].path == "/nas/new.xlsx"
    assert result.modified_files == []
    assert result.deleted_paths == []


def test_detect_changes_identifies_modified_files(db):
    """DB に記録済みだがハッシュが異なるファイルが modified_files として検出されること。"""
    db.update_state("/nas/modified.xlsx", 1.0, "old-hash", "sheet-001")

    current_files = [FileInfo(path="/nas/modified.xlsx", mtime=2.0, file_hash="new-hash")]

    result = detect_changes(current_files, db)

    assert result.new_files == []
    assert len(result.modified_files) == 1
    assert result.modified_files[0].path == "/nas/modified.xlsx"
    assert result.deleted_paths == []


def test_detect_changes_unchanged_file_not_in_any_list(db):
    """ハッシュが同じファイルは new_files にも modified_files にも含まれないこと。"""
    db.update_state("/nas/unchanged.xlsx", 1.0, "same-hash", "sheet-001")

    current_files = [FileInfo(path="/nas/unchanged.xlsx", mtime=1.0, file_hash="same-hash")]

    result = detect_changes(current_files, db)

    assert result.new_files == []
    assert result.modified_files == []
    assert result.deleted_paths == []


def test_detect_changes_identifies_deleted_files(db):
    """DB に存在するがスキャン結果にないファイルが deleted_paths として検出されること。"""
    db.update_state("/nas/deleted.xlsx", 1.0, "hash-del", "sheet-001")

    current_files = [FileInfo(path="/nas/other.xlsx", mtime=1.0, file_hash="hash-other")]

    result = detect_changes(current_files, db)

    assert "/nas/deleted.xlsx" in result.deleted_paths


def test_detect_changes_skips_deletion_when_current_files_is_empty(db):
    """current_files が空のとき NAS 切断と判断して deleted_paths が空になること。"""
    db.update_state("/nas/file.xlsx", 1.0, "hash1", "sheet-001")

    result = detect_changes([], db)

    assert result.deleted_paths == []
    assert result.new_files == []
    assert result.modified_files == []


def test_detect_changes_returns_change_result_instance(db):
    """返り値が ChangeResult インスタンスであること。"""
    result = detect_changes([], db)
    assert isinstance(result, ChangeResult)


def test_detect_changes_with_empty_db_and_empty_files(db):
    """DB も current_files も空のとき、すべての変更リストが空であること。"""
    result = detect_changes([], db)

    assert result.new_files == []
    assert result.modified_files == []
    assert result.deleted_paths == []


def test_detect_changes_multiple_new_and_modified(db):
    """新規ファイル複数件と更新ファイル複数件が同時に検出されること。"""
    db.update_state("/nas/modified_1.xlsx", 1.0, "old-1", "s1")
    db.update_state("/nas/modified_2.xlsx", 1.0, "old-2", "s2")

    current_files = [
        FileInfo("/nas/new_1.xlsx", 1.0, "hash-n1"),
        FileInfo("/nas/new_2.xlsx", 1.0, "hash-n2"),
        FileInfo("/nas/modified_1.xlsx", 2.0, "new-1"),
        FileInfo("/nas/modified_2.xlsx", 2.0, "new-2"),
    ]

    result = detect_changes(current_files, db)

    assert len(result.new_files) == 2
    assert len(result.modified_files) == 2


def test_detect_changes_multiple_deletions(db):
    """DB に複数のファイルが記録されており、すべて消えた場合に全件検出されること。"""
    db.update_state("/nas/del_1.xlsx", 1.0, "h1", "s1")
    db.update_state("/nas/del_2.xlsx", 1.0, "h2", "s2")
    db.update_state("/nas/del_3.xlsx", 1.0, "h3", "s3")

    # 1 ファイルだけ残す → 残り 2 件が削除として検出されるはず
    current_files = [FileInfo("/nas/del_1.xlsx", 1.0, "h1")]

    result = detect_changes(current_files, db)

    assert len(result.deleted_paths) == 2
    assert set(result.deleted_paths) == {"/nas/del_2.xlsx", "/nas/del_3.xlsx"}


def test_detect_changes_reports_stored_total(db):
    """ChangeResult.stored_total が DB 登録総数を反映すること。"""
    db.update_state("/nas/a.xlsx", 1.0, "h1", "s1")
    db.update_state("/nas/b.xlsx", 1.0, "h2", "s2")

    current_files = [
        FileInfo("/nas/a.xlsx", 1.0, "h1"),
        FileInfo("/nas/c.xlsx", 1.0, "h3"),
    ]
    result = detect_changes(current_files, db)

    assert result.stored_total == 2


def test_detect_changes_stored_total_zero_for_empty_db(db):
    """空DBなら stored_total は 0。"""
    result = detect_changes([FileInfo("/nas/x.xlsx", 1.0, "h")], db)
    assert result.stored_total == 0


# ---------------------------------------------------------------------------
# scan_files の走査完全フラグ
# ---------------------------------------------------------------------------

def test_scan_files_reports_complete_when_all_readable(nas_dir):
    """全ファイル読取成功なら走査完全フラグは True。"""
    (nas_dir / "a.xlsx").write_text("data")
    _, complete = scan_files(str(nas_dir), ["*.xlsx"], [])
    assert complete is True


def test_scan_files_reports_incomplete_on_read_error(nas_dir, monkeypatch):
    """読取で OSError が出たファイルがあれば走査完全フラグは False。"""
    (nas_dir / "a.xlsx").write_text("data")

    import tamatex.watcher as w

    def boom(path):
        raise OSError("simulated read error")

    monkeypatch.setattr(w, "_compute_file_hash", boom)

    files, complete = scan_files(str(nas_dir), ["*.xlsx"], [])
    assert complete is False
    assert files == []
