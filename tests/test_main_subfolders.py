"""main の NAS 階層ミラー機能の単体テスト。"""

import os
from unittest.mock import MagicMock, patch

import pytest

from tamatex.config import SyncConfig
from tamatex.main import (
    _resolve_target_folders,
    _subfolder_parts,
    reorganize_existing_files,
)
from tamatex.state import FileState


# ---------------------------------------------------------------------------
# _subfolder_parts
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("base,file,expected", [
    ("/nas/data", "/nas/data/foo.xlsx", []),
    ("/nas/data", "/nas/data/テスト/foo.xlsx", ["テスト"]),
    ("/nas/data", "/nas/data/A/B/foo.xlsx", ["A", "B"]),
    ("/nas/data", "/nas/data/A/B/C/foo.xlsx", ["A", "B", "C"]),
])
def test_subfolder_parts_extracts_directory_components(base, file, expected):
    assert _subfolder_parts(file, base) == expected


def test_subfolder_parts_returns_empty_for_path_outside_base():
    """base_path 外のパスは安全に空リストを返す（ガード）。"""
    assert _subfolder_parts("/other/path/foo.xlsx", "/nas/data") == []


# ---------------------------------------------------------------------------
# _resolve_target_folders
# ---------------------------------------------------------------------------

def _mk_config(mirror: bool, base_path="/nas/data"):
    cfg = MagicMock()
    cfg.sync = SyncConfig(mirror_subfolders=mirror)
    cfg.nas.base_path = base_path
    return cfg


def test_resolve_target_returns_root_when_mirror_disabled():
    """mirror_subfolders=False ならサブフォルダ作成せずルートID返却。"""
    cfg = _mk_config(mirror=False)
    svc = MagicMock()
    cache = {}

    sheets, pdf = _resolve_target_folders(
        svc, "/nas/data/テスト/foo.xlsx", cfg, "S-root", "P-root", cache,
    )
    assert sheets == "S-root"
    assert pdf == "P-root"
    assert cache == {}


def test_resolve_target_returns_root_when_file_at_base():
    """ファイルが NAS ルート直下なら、サブフォルダ作成せずルート返却。"""
    cfg = _mk_config(mirror=True)
    svc = MagicMock()
    cache = {}

    sheets, pdf = _resolve_target_folders(
        svc, "/nas/data/foo.xlsx", cfg, "S-root", "P-root", cache,
    )
    assert sheets == "S-root"
    assert pdf == "P-root"


def test_resolve_target_creates_subfolder_for_nested_file():
    """サブディレクトリ配下のファイルは ensure_folder_path 経由でサブフォルダID返却。"""
    cfg = _mk_config(mirror=True)
    svc = MagicMock()
    cache = {}

    with patch("tamatex.main.ensure_folder_path") as efp:
        efp.side_effect = ["S-sub", "P-sub"]
        sheets, pdf = _resolve_target_folders(
            svc, "/nas/data/テスト/foo.xlsx", cfg, "S-root", "P-root", cache,
        )

    assert sheets == "S-sub"
    assert pdf == "P-sub"
    assert cache == {("テスト",): ("S-sub", "P-sub")}
    assert efp.call_count == 2


def test_resolve_target_uses_cache_on_repeated_lookup():
    """同じサブフォルダの2回目の解決はキャッシュからヒットしAPIを呼ばない。"""
    cfg = _mk_config(mirror=True)
    svc = MagicMock()
    cache = {("テスト",): ("S-cached", "P-cached")}

    with patch("tamatex.main.ensure_folder_path") as efp:
        sheets, pdf = _resolve_target_folders(
            svc, "/nas/data/テスト/another.xlsx", cfg, "S-root", "P-root", cache,
        )
    assert sheets == "S-cached"
    assert pdf == "P-cached"
    efp.assert_not_called()


# ---------------------------------------------------------------------------
# reorganize_existing_files
# ---------------------------------------------------------------------------

def _mk_state(file_path: str, sheet_id: str = "s", pdf_id: str = "p") -> FileState:
    return FileState(
        file_path=file_path,
        mtime=1.0,
        file_hash="h",
        spreadsheet_id=sheet_id,
        pdf_file_id=pdf_id,
        last_sync=0.0,
    )


def test_reorganize_returns_zero_when_disabled():
    """mirror_subfolders=False ではサブフォルダ作成も移動もしない。"""
    cfg = _mk_config(mirror=False)
    state_db = MagicMock()
    state_db.get_all_states.return_value = [_mk_state("/nas/data/sub/a.xlsx")]

    moved = reorganize_existing_files(cfg, state_db, MagicMock(), "S", "P")
    assert moved == 0


def test_reorganize_skips_files_at_base_root():
    """ルート直下のファイルは移動対象外。"""
    cfg = _mk_config(mirror=True)
    state_db = MagicMock()
    state_db.get_all_states.return_value = [_mk_state("/nas/data/root.xlsx")]

    with patch("tamatex.main.ensure_folder_path") as efp, \
         patch("tamatex.main.move_to_folder") as mv:
        moved = reorganize_existing_files(cfg, state_db, MagicMock(), "S", "P")

    assert moved == 0
    efp.assert_not_called()
    mv.assert_not_called()


def test_reorganize_moves_nested_files_to_correct_subfolder():
    """サブディレクトリ配下のファイルは Sheets/PDF 双方が再配置される。"""
    cfg = _mk_config(mirror=True)
    state_db = MagicMock()
    state_db.get_all_states.return_value = [
        _mk_state("/nas/data/テスト/a.xlsx", "sheet-a", "pdf-a"),
        _mk_state("/nas/data/出荷明細/b.xlsx", "sheet-b", "pdf-b"),
    ]

    with patch("tamatex.main.ensure_folder_path") as efp, \
         patch("tamatex.main.move_to_folder") as mv:
        efp.side_effect = ["S-test", "P-test", "S-ship", "P-ship"]
        moved = reorganize_existing_files(cfg, state_db, MagicMock(), "S", "P")

    assert moved == 2
    # Sheets/PDF 各2回 = 計4回 move_to_folder 呼出
    assert mv.call_count == 4

    # 各ファイルが正しい先へ移動されている
    move_targets = {(c.args[1], c.args[2]) for c in mv.call_args_list}
    assert ("sheet-a", "S-test") in move_targets
    assert ("pdf-a", "P-test") in move_targets
    assert ("sheet-b", "S-ship") in move_targets
    assert ("pdf-b", "P-ship") in move_targets


def test_reorganize_caches_subfolder_ids_across_files_in_same_dir():
    """同じサブフォルダ内の複数ファイルは ensure_folder_path を共用キャッシュする。"""
    cfg = _mk_config(mirror=True)
    state_db = MagicMock()
    state_db.get_all_states.return_value = [
        _mk_state("/nas/data/テスト/a.xlsx", "sa", "pa"),
        _mk_state("/nas/data/テスト/b.xlsx", "sb", "pb"),
        _mk_state("/nas/data/テスト/c.xlsx", "sc", "pc"),
    ]

    with patch("tamatex.main.ensure_folder_path") as efp, \
         patch("tamatex.main.move_to_folder"):
        efp.side_effect = ["S-test", "P-test"]  # 1回ずつだけ呼ばれるはず
        reorganize_existing_files(cfg, state_db, MagicMock(), "S", "P")

    # 3ファイルあるが ensure_folder_path は計2回（Sheets/PDF）のみ
    assert efp.call_count == 2


def test_reorganize_continues_on_individual_failure():
    """1ファイルの move 失敗で全体停止しない（警告のみで続行）。"""
    cfg = _mk_config(mirror=True)
    state_db = MagicMock()
    state_db.get_all_states.return_value = [
        _mk_state("/nas/data/A/a.xlsx", "sa", "pa"),
        _mk_state("/nas/data/B/b.xlsx", "sb", "pb"),
    ]

    with patch("tamatex.main.ensure_folder_path", return_value="folder"), \
         patch("tamatex.main.move_to_folder") as mv:
        # 1回目の move（Sheetsへの移動）で例外、それ以外は成功
        mv.side_effect = [RuntimeError("network"), None, None, None]
        moved = reorganize_existing_files(cfg, state_db, MagicMock(), "S", "P")

    # 1ファイル目は失敗したのでカウントされず、2ファイル目は成功
    assert moved == 1
