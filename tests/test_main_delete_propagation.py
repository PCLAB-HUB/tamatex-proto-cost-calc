"""main.py の削除伝播・一括消失ガードのテスト。"""

import threading
from unittest.mock import MagicMock, patch

import pytest

from tamatex.config import (
    AppConfig, NasConfig, GoogleConfig, SyncConfig, LogConfig,
)
from tamatex.main import (
    sync_cycle,
    _run_sync_cycle,
    _is_mass_deletion,
    _classify_deletions,
)
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
               return_value=([FileInfo("/nas/keep.xlsx", 1.0, "h")], True)), \
         patch("tamatex.main.detect_changes", return_value=fake), \
         patch("tamatex.main.trash_file") as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root",
                   pending_deletions={"/nas/gone.xlsx"})

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
               return_value=([FileInfo("/nas/keep.xlsx", 1.0, "h")], True)), \
         patch("tamatex.main.detect_changes", return_value=fake), \
         patch("tamatex.main.trash_file") as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root",
                   pending_deletions={"/nas/gone.xlsx"})

    mock_trash.assert_called_once_with(svc, "sheet-del")


def test_sync_cycle_skips_deletion_when_mass_guard_trips(cfg):
    """25件/60件の削除は一括ガード発動で trash も remove も呼ばれない。"""
    svc = MagicMock()
    state_db = MagicMock()
    state_db.get_state.side_effect = lambda p: _state("s", "p")
    deleted = [f"/nas/del{i}.xlsx" for i in range(25)]
    fake = ChangeResult([], [], deleted, stored_total=60)

    with patch("tamatex.main.scan_files",
               return_value=([FileInfo("/nas/keep.xlsx", 1.0, "h")], True)), \
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
               return_value=([FileInfo("/nas/keep.xlsx", 1.0, "h")], True)), \
         patch("tamatex.main.detect_changes", return_value=fake), \
         patch("tamatex.main.trash_file") as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root",
                   pending_deletions=set(deleted))

    assert state_db.remove_state.call_count == 24
    assert mock_trash.call_count == 48


def test_sync_cycle_skips_everything_when_nas_disconnected(cfg):
    """scan_files が空（NAS全切断）なら削除処理に到達しない。"""
    svc = MagicMock()
    state_db = MagicMock()

    with patch("tamatex.main.scan_files", return_value=([], True)), \
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
               return_value=([FileInfo("/nas/keep.xlsx", 1.0, "h")], True)), \
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
               return_value=([FileInfo("/nas/keep.xlsx", 1.0, "h")], True)), \
         patch("tamatex.main.detect_changes", return_value=fake), \
         patch("tamatex.main.trash_file") as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root", shutdown_event=ev)

    mock_trash.assert_not_called()
    state_db.remove_state.assert_not_called()


def test_sync_cycle_completes_current_file_then_stops_on_shutdown(cfg):
    """削除はファイル単位で原子的: 処理中ファイルは完遂し、shutdown後は次を開始しない。"""
    svc = MagicMock()
    state_db = MagicMock()
    state_db.get_state.side_effect = lambda p: _state(f"sheet-{p}", f"pdf-{p}")
    deleted = ["/nas/gone1.xlsx", "/nas/gone2.xlsx"]
    fake = ChangeResult([], [], deleted, stored_total=10)
    ev = threading.Event()  # 開始時クリア

    calls = []

    def trash_side_effect(service, fid):
        calls.append(fid)
        ev.set()  # 最初のtrashでSIGTERM相当が入った状況を模す

    with patch("tamatex.main.scan_files",
               return_value=([FileInfo("/nas/keep.xlsx", 1.0, "h")], True)), \
         patch("tamatex.main.detect_changes", return_value=fake), \
         patch("tamatex.main.trash_file", side_effect=trash_side_effect):
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root", shutdown_event=ev,
                   pending_deletions=set(deleted))

    # 1ファイル目(gone1)は Sheets+PDF とも trash し state削除まで完遂、
    # 2ファイル目(gone2)は shutdown 後なので開始しない。
    assert calls == ["sheet-/nas/gone1.xlsx", "pdf-/nas/gone1.xlsx"]
    state_db.remove_state.assert_called_once_with("/nas/gone1.xlsx")


# ---------------------------------------------------------------------------
# _classify_deletions（2サイクル確認の純関数）
# ---------------------------------------------------------------------------

def test_classify_deletions_first_absence_is_pending_not_confirmed():
    """初回不在は確定せず保留に積む。"""
    confirmed, new_pending = _classify_deletions(["/a", "/b"], set())
    assert confirmed == []
    assert new_pending == {"/a", "/b"}


def test_classify_deletions_second_absence_is_confirmed():
    """前サイクルも不在だったものだけ確定し、新規不在は保留へ。"""
    confirmed, new_pending = _classify_deletions(["/a", "/b"], {"/a"})
    assert confirmed == ["/a"]
    assert new_pending == {"/b"}


def test_classify_deletions_empty_clears_pending():
    """今サイクル不在ゼロなら保留は空になる（復帰分の解除）。"""
    confirmed, new_pending = _classify_deletions([], {"/a", "/b"})
    assert confirmed == []
    assert new_pending == set()


# ---------------------------------------------------------------------------
# sync_cycle 2サイクル確認（誤削除防止）
# ---------------------------------------------------------------------------

def test_sync_cycle_defers_deletion_on_first_absence(cfg):
    """初回不在では trash せず保留集合に積む。"""
    svc = MagicMock()
    state_db = MagicMock()
    state_db.get_state.side_effect = lambda p: _state("sheet-del", "pdf-del")
    fake = ChangeResult([], [], ["/nas/gone.xlsx"], stored_total=10)
    pending: set[str] = set()

    with patch("tamatex.main.scan_files",
               return_value=([FileInfo("/nas/keep.xlsx", 1.0, "h")], True)), \
         patch("tamatex.main.detect_changes", return_value=fake), \
         patch("tamatex.main.trash_file") as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root",
                   pending_deletions=pending)

    mock_trash.assert_not_called()
    state_db.remove_state.assert_not_called()
    assert pending == {"/nas/gone.xlsx"}


def test_sync_cycle_trashes_only_after_two_consecutive_absences(cfg):
    """2サイクル連続で不在のときだけ trash する。"""
    svc = MagicMock()
    state_db = MagicMock()
    state_db.get_state.side_effect = lambda p: _state("sheet-del", "pdf-del")
    fake = ChangeResult([], [], ["/nas/gone.xlsx"], stored_total=10)
    pending: set[str] = set()

    with patch("tamatex.main.scan_files",
               return_value=([FileInfo("/nas/keep.xlsx", 1.0, "h")], True)), \
         patch("tamatex.main.detect_changes", return_value=fake), \
         patch("tamatex.main.trash_file") as mock_trash:
        # 1サイクル目: 保留のみ（trashなし）
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root",
                   pending_deletions=pending)
        assert mock_trash.call_count == 0
        assert pending == {"/nas/gone.xlsx"}
        # 2サイクル目: 確定 → trash
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root",
                   pending_deletions=pending)

    mock_trash.assert_any_call(svc, "sheet-del")
    mock_trash.assert_any_call(svc, "pdf-del")
    state_db.remove_state.assert_called_with("/nas/gone.xlsx")
    assert pending == set()


def test_sync_cycle_cancels_pending_when_file_reappears(cfg):
    """前サイクルで保留したファイルが復帰したら保留解除し trash しない。"""
    svc = MagicMock()
    state_db = MagicMock()
    state_db.get_state.side_effect = lambda p: _state("sheet-del", "pdf-del")
    # 今サイクルは復帰: deleted は空、ファイルは current に在る
    fake = ChangeResult([], [], [], stored_total=10)
    pending: set[str] = {"/nas/gone.xlsx"}

    with patch("tamatex.main.scan_files",
               return_value=([FileInfo("/nas/gone.xlsx", 1.0, "h")], True)), \
         patch("tamatex.main.detect_changes", return_value=fake), \
         patch("tamatex.main.trash_file") as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root",
                   pending_deletions=pending)

    mock_trash.assert_not_called()
    state_db.remove_state.assert_not_called()
    assert pending == set()


def test_sync_cycle_resets_pending_on_mass_guard(cfg):
    """一括ガード発動サイクルでは pending をリセットし、非連続不在を誤確定しない。"""
    svc = MagicMock()
    state_db = MagicMock()
    state_db.get_state.side_effect = lambda p: _state("s", "p")
    pending: set[str] = {"/nas/p.xlsx"}  # 前サイクルで不在だった（が今は復帰し得る）
    deleted = [f"/nas/del{i}.xlsx" for i in range(25)]  # 今サイクルは大量不在
    fake = ChangeResult([], [], deleted, stored_total=60)

    with patch("tamatex.main.scan_files",
               return_value=([FileInfo("/nas/keep.xlsx", 1.0, "h")], True)), \
         patch("tamatex.main.detect_changes", return_value=fake), \
         patch("tamatex.main.trash_file") as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root",
                   pending_deletions=pending)

    mock_trash.assert_not_called()
    assert pending == set()


def test_sync_cycle_resets_pending_on_nas_disconnect(cfg):
    """全切断（scan空）サイクルでも pending をリセットする。"""
    svc = MagicMock()
    state_db = MagicMock()
    pending: set[str] = {"/nas/p.xlsx"}

    with patch("tamatex.main.scan_files", return_value=([], True)), \
         patch("tamatex.main.trash_file") as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root",
                   pending_deletions=pending)

    mock_trash.assert_not_called()
    assert pending == set()


def test_sync_cycle_skips_deletion_on_incomplete_scan(cfg):
    """走査不完全（部分I/O障害）なら削除伝播せず pending をリセットする。"""
    svc = MagicMock()
    state_db = MagicMock()
    state_db.get_state.side_effect = lambda p: _state("s", "p")
    pending: set[str] = {"/nas/gone.xlsx"}
    fake = ChangeResult([], [], ["/nas/gone.xlsx"], stored_total=10)

    with patch("tamatex.main.scan_files",
               return_value=([FileInfo("/nas/keep.xlsx", 1.0, "h")], False)), \
         patch("tamatex.main.detect_changes", return_value=fake), \
         patch("tamatex.main.trash_file") as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root",
                   pending_deletions=pending)

    mock_trash.assert_not_called()
    state_db.remove_state.assert_not_called()
    assert pending == set()


def test_run_sync_cycle_clears_pending_on_exception(cfg):
    """sync_cycle が例外で落ちたサイクルでは pending をリセットする。"""
    state_db = MagicMock()
    pending: set[str] = {"/nas/p.xlsx"}

    with patch("tamatex.main.scan_files",
               return_value=([FileInfo("/nas/keep.xlsx", 1.0, "h")], True)), \
         patch("tamatex.main.detect_changes", side_effect=RuntimeError("boom")):
        _run_sync_cycle(cfg, state_db, MagicMock(), "s", "p",
                        pending_deletions=pending)

    assert pending == set()


def test_sync_cycle_skips_deletion_when_sync_had_errors(cfg):
    """同期処理でエラーが出たサイクルは削除伝播せず pending をリセットする。"""
    svc = MagicMock()
    state_db = MagicMock()
    state_db.get_state.side_effect = lambda p: _state("s", "p")
    pending: set[str] = {"/nas/gone.xlsx"}
    # 新規ファイル1件（同期対象・upsertで失敗させる）＋削除候補1件
    new_file = FileInfo("/nas/new.xlsx", 1.0, "h")
    fake = ChangeResult([new_file], [], ["/nas/gone.xlsx"], stored_total=10)

    with patch("tamatex.main.scan_files",
               return_value=([new_file], True)), \
         patch("tamatex.main.detect_changes", return_value=fake), \
         patch("tamatex.main._resolve_target_folders",
               return_value=("sheets-root", "pdf-root")), \
         patch("tamatex.main.upsert_sheet", side_effect=RuntimeError("drive down")), \
         patch("tamatex.main.trash_file") as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root",
                   pending_deletions=pending)

    mock_trash.assert_not_called()
    state_db.remove_state.assert_not_called()
    assert pending == set()
