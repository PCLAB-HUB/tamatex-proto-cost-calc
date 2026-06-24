"""main.py の削除伝播・一括消失ガードのテスト。"""

import threading
from unittest.mock import MagicMock, patch

import pytest

from tamatex.config import (
    AppConfig, NasConfig, GoogleConfig, SyncConfig, LogConfig,
)
from tamatex.main import sync_cycle, _is_mass_deletion
from tamatex.watcher import ChangeResult, FileInfo


# ---------------------------------------------------------------------------
# _is_mass_deletion
# ---------------------------------------------------------------------------

def test_is_mass_deletion_below_min_is_false():
    """MASS_DELETE_MIN 未満は常に通す。"""
    assert _is_mass_deletion(4, 100) is False


def test_is_mass_deletion_blocks_above_ratio():
    """登録60件で25件削除（25 > 24）はブロック。"""
    assert _is_mass_deletion(25, 60) is True


def test_is_mass_deletion_allows_at_boundary():
    """登録60件で24件削除（24 > 24 == False）は通す。"""
    assert _is_mass_deletion(24, 60) is False


def test_is_mass_deletion_zero_total_is_false():
    """登録総数0なら割合計算せず通す（初回など）。"""
    assert _is_mass_deletion(10, 0) is False


# ---------------------------------------------------------------------------
# sync_cycle 削除伝播
# ---------------------------------------------------------------------------

@pytest.fixture()
def cfg(tmp_path):
    return AppConfig(
        nas=NasConfig(
            base_path=str(tmp_path / "nas"),
            file_patterns=["*.xlsx"],
            exclude_patterns=["~$*"],
        ),
        google=GoogleConfig(
            credentials_path=str(tmp_path / "c.json"),
            drive_folder_id="root",
            share_with=[],
        ),
        sync=SyncConfig(),
        logging=LogConfig(),
    )


def _state(sheet, pdf):
    s = MagicMock()
    s.spreadsheet_id = sheet
    s.pdf_file_id = pdf
    return s


def test_sync_cycle_trashes_sheet_and_pdf_on_deletion(cfg):
    """削除されたファイルの Sheets と PDF が両方 trash され state 行が消える。"""
    svc = MagicMock()
    state_db = MagicMock()
    state_db.get_state.side_effect = lambda p: {
        "/nas/keep.xlsx": _state("sheet-keep", "pdf-keep"),
        "/nas/gone.xlsx": _state("sheet-del", "pdf-del"),
    }.get(p)
    fake = ChangeResult([], [], ["/nas/gone.xlsx"], stored_total=10)

    with patch("tamatex.main.scan_files",
               return_value=[FileInfo("/nas/keep.xlsx", 1.0, "h")]), \
         patch("tamatex.main.detect_changes", return_value=fake), \
         patch("tamatex.main.trash_file") as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root")

    mock_trash.assert_any_call(svc, "sheet-del")
    mock_trash.assert_any_call(svc, "pdf-del")
    state_db.remove_state.assert_called_once_with("/nas/gone.xlsx")


def test_sync_cycle_trashes_only_sheet_when_no_pdf(cfg):
    """pdf_file_id が空なら Sheets のみ trash。"""
    svc = MagicMock()
    state_db = MagicMock()
    state_db.get_state.side_effect = lambda p: {
        "/nas/keep.xlsx": _state("sheet-keep", "pdf-keep"),
        "/nas/gone.xlsx": _state("sheet-del", ""),
    }.get(p)
    fake = ChangeResult([], [], ["/nas/gone.xlsx"], stored_total=10)

    with patch("tamatex.main.scan_files",
               return_value=[FileInfo("/nas/keep.xlsx", 1.0, "h")]), \
         patch("tamatex.main.detect_changes", return_value=fake), \
         patch("tamatex.main.trash_file") as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root")

    mock_trash.assert_called_once_with(svc, "sheet-del")


def test_sync_cycle_skips_deletion_when_mass_guard_trips(cfg):
    """25件/60件の削除は一括ガード発動で trash も remove も呼ばれない。"""
    svc = MagicMock()
    state_db = MagicMock()
    state_db.get_state.side_effect = lambda p: _state("s", "p")
    deleted = [f"/nas/del{i}.xlsx" for i in range(25)]
    fake = ChangeResult([], [], deleted, stored_total=60)

    with patch("tamatex.main.scan_files",
               return_value=[FileInfo("/nas/keep.xlsx", 1.0, "h")]), \
         patch("tamatex.main.detect_changes", return_value=fake), \
         patch("tamatex.main.trash_file") as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root")

    mock_trash.assert_not_called()
    state_db.remove_state.assert_not_called()


def test_sync_cycle_propagates_deletion_at_guard_boundary(cfg):
    """24件/60件は非発動 → 24件すべて trash（Sheets+PDF=48）＋remove 24回。"""
    svc = MagicMock()
    state_db = MagicMock()
    state_db.get_state.side_effect = lambda p: _state(f"sheet-{p}", f"pdf-{p}")
    deleted = [f"/nas/del{i}.xlsx" for i in range(24)]
    fake = ChangeResult([], [], deleted, stored_total=60)

    with patch("tamatex.main.scan_files",
               return_value=[FileInfo("/nas/keep.xlsx", 1.0, "h")]), \
         patch("tamatex.main.detect_changes", return_value=fake), \
         patch("tamatex.main.trash_file") as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root")

    assert state_db.remove_state.call_count == 24
    assert mock_trash.call_count == 48


def test_sync_cycle_skips_everything_when_nas_disconnected(cfg):
    """scan_files が空（NAS全切断）なら削除処理に到達しない。"""
    svc = MagicMock()
    state_db = MagicMock()

    with patch("tamatex.main.scan_files", return_value=[]), \
         patch("tamatex.main.trash_file") as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root")

    mock_trash.assert_not_called()
    state_db.remove_state.assert_not_called()


def test_sync_cycle_skips_trash_when_file_still_exists(cfg, tmp_path):
    """走査で一時スキップされただけで実体がNASに在るファイルは trash しない（誤削除防止）。"""
    svc = MagicMock()
    state_db = MagicMock()
    state_db.get_state.side_effect = lambda p: _state("sheet-x", "pdf-x")
    # 保存中・一時I/Oエラー等で走査スキップされたが実体は残っている想定
    real = tmp_path / "still_here.xlsx"
    real.write_text("x")
    fake = ChangeResult([], [], [str(real)], stored_total=10)

    with patch("tamatex.main.scan_files",
               return_value=[FileInfo("/nas/keep.xlsx", 1.0, "h")]), \
         patch("tamatex.main.detect_changes", return_value=fake), \
         patch("tamatex.main.trash_file") as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root")

    mock_trash.assert_not_called()
    state_db.remove_state.assert_not_called()


def test_sync_cycle_skips_deletion_when_shutdown_requested(cfg):
    """shutdown 要求中は削除伝播を行わない（破壊的操作の保護）。"""
    svc = MagicMock()
    state_db = MagicMock()
    state_db.get_state.side_effect = lambda p: _state("s", "p")
    fake = ChangeResult([], [], ["/nas/gone.xlsx"], stored_total=10)
    ev = threading.Event()
    ev.set()

    with patch("tamatex.main.scan_files",
               return_value=[FileInfo("/nas/keep.xlsx", 1.0, "h")]), \
         patch("tamatex.main.detect_changes", return_value=fake), \
         patch("tamatex.main.trash_file") as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root", shutdown_event=ev)

    mock_trash.assert_not_called()
    state_db.remove_state.assert_not_called()


def test_sync_cycle_aborts_mid_deletion_on_shutdown(cfg):
    """削除1件の処理中にshutdownが入ったら以降の破壊的操作を行わない。"""
    svc = MagicMock()
    state_db = MagicMock()
    state_db.get_state.side_effect = lambda p: _state("sheet-del", "pdf-del")
    fake = ChangeResult([], [], ["/nas/gone.xlsx"], stored_total=10)
    ev = threading.Event()  # 開始時はクリア

    def trash_side_effect(service, fid):
        # 1つ目のtrash中にSIGTERM相当が入った状況を模す
        ev.set()

    with patch("tamatex.main.scan_files",
               return_value=[FileInfo("/nas/keep.xlsx", 1.0, "h")]), \
         patch("tamatex.main.detect_changes", return_value=fake), \
         patch("tamatex.main.trash_file", side_effect=trash_side_effect) as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root", shutdown_event=ev)

    # Sheets trashは1回走るが、その後shutdownを見てPDF trashとstate削除は行わない
    assert mock_trash.call_count == 1
    state_db.remove_state.assert_not_called()
