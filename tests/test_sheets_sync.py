"""sheets_sync.py の単体テスト。Drive API サービスは MagicMock で差し替える。"""

import os
from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.errors import HttpError

from tamatex.sheets_sync import _local_copy, upsert_sheet


def _mk_http_error(status: int) -> HttpError:
    resp = MagicMock()
    resp.status = status
    resp.reason = "err"
    return HttpError(resp=resp, content=b"")


@pytest.fixture()
def fake_xlsx(tmp_path):
    p = tmp_path / "sample.xlsx"
    p.write_bytes(b"PK\x03\x04fake xlsx content")
    return str(p)


# ---------------------------------------------------------------------------
# 新規作成ブランチ
# ---------------------------------------------------------------------------

def test_upsert_sheet_creates_new_when_no_existing_id(fake_xlsx):
    """existing_file_id が空なら create で新規作成し ID を返す。"""
    svc = MagicMock()
    svc.files().create().execute.return_value = {"id": "new-sheet-id", "name": "[同期] sample"}

    result = upsert_sheet(
        svc,
        xlsx_path=fake_xlsx,
        title="[同期] sample",
        folder_id="folder-1",
        existing_file_id="",
    )

    assert result == "new-sheet-id"
    # create の body に正しい mimeType と parents が入っているか
    create_calls = [
        c for c in svc.files().create.call_args_list
        if c.kwargs.get("body") is not None
    ]
    assert any(
        c.kwargs["body"]["mimeType"] == "application/vnd.google-apps.spreadsheet"
        and c.kwargs["body"]["parents"] == ["folder-1"]
        for c in create_calls
    )


# ---------------------------------------------------------------------------
# 更新ブランチ
# ---------------------------------------------------------------------------

def test_upsert_sheet_updates_existing_id(fake_xlsx):
    """existing_file_id があれば update で中身置換、同じ ID を返す。"""
    svc = MagicMock()
    svc.files().update().execute.return_value = {"id": "exist-id", "name": "[同期] sample"}
    # move_to_folder から呼ばれる get は現在 parent = target を返すようにし、move をスキップ
    svc.files().get().execute.return_value = {"parents": ["folder-1"]}

    result = upsert_sheet(
        svc,
        xlsx_path=fake_xlsx,
        title="[同期] sample",
        folder_id="folder-1",
        existing_file_id="exist-id",
    )

    assert result == "exist-id"
    # update が呼ばれた
    update_calls = [
        c for c in svc.files().update.call_args_list
        if c.kwargs.get("fileId") == "exist-id" and c.kwargs.get("media_body") is not None
    ]
    assert len(update_calls) == 1


def test_upsert_sheet_falls_back_to_create_on_404(fake_xlsx):
    """既存fileIdが404で見つからない場合、新規作成にフォールバックする。"""
    svc = MagicMock()

    # update 呼び出しが 404 を投げる
    update_req = MagicMock()
    update_req.execute.side_effect = _mk_http_error(404)
    # create が正常に動くこと
    create_req = MagicMock()
    create_req.execute.return_value = {"id": "fallback-id", "name": "t"}

    def files_method():
        m = MagicMock()
        m.update.return_value = update_req
        m.create.return_value = create_req
        # 他のメソッド（get等）も呼ばれうるが副作用不要
        m.get.return_value = MagicMock(execute=MagicMock(return_value={"parents": []}))
        return m

    svc.files = files_method

    result = upsert_sheet(
        svc,
        xlsx_path=fake_xlsx,
        title="title",
        folder_id="folder-1",
        existing_file_id="missing-id",
    )
    assert result == "fallback-id"


def test_upsert_sheet_propagates_non_404_errors(fake_xlsx):
    """404 以外の HttpError はそのまま送出される。"""
    svc = MagicMock()
    update_req = MagicMock()
    update_req.execute.side_effect = _mk_http_error(500)
    svc.files().update.return_value = update_req

    with pytest.raises(HttpError):
        upsert_sheet(
            svc,
            xlsx_path=fake_xlsx,
            title="t",
            folder_id="folder-1",
            existing_file_id="id",
        )


# ---------------------------------------------------------------------------
# ローカル一時コピー（NASロック時間最小化）
# ---------------------------------------------------------------------------

def test_local_copy_creates_temp_file_with_same_content(fake_xlsx):
    """_local_copy が中身を完全コピーした一時ファイルを yield すること。"""
    src_bytes = open(fake_xlsx, "rb").read()
    captured_path = None
    captured_bytes = None
    with _local_copy(fake_xlsx) as local_path:
        captured_path = local_path
        assert os.path.exists(local_path)
        assert local_path != fake_xlsx
        assert local_path.endswith(".xlsx")
        captured_bytes = open(local_path, "rb").read()

    assert captured_bytes == src_bytes
    # コンテキスト終了後、一時ファイルは削除されている
    assert not os.path.exists(captured_path)


def test_local_copy_cleans_up_on_exception(fake_xlsx):
    """_local_copy 内で例外が発生しても一時ファイルが削除されること。"""
    captured_path = None
    with pytest.raises(RuntimeError):
        with _local_copy(fake_xlsx) as local_path:
            captured_path = local_path
            assert os.path.exists(local_path)
            raise RuntimeError("test")

    assert captured_path is not None
    assert not os.path.exists(captured_path)


# ---------------------------------------------------------------------------
# リトライ統合（5/19 現場の AAA01* 連続失敗の再現と回復）
# ---------------------------------------------------------------------------

def test_upsert_sheet_recovers_from_connection_aborted_on_update(fake_xlsx):
    """更新時に ConnectionAbortedError が出ても、リトライで成功すれば fileId を返す。"""
    svc = MagicMock()
    update_req = MagicMock()
    update_req.execute.side_effect = [
        ConnectionAbortedError("WinError 10053"),
        {"id": "exist-id", "name": "[同期] sample"},
    ]
    svc.files().update.return_value = update_req
    svc.files().get().execute.return_value = {"parents": ["folder-1"]}

    result = upsert_sheet(
        svc,
        xlsx_path=fake_xlsx,
        title="[同期] sample",
        folder_id="folder-1",
        existing_file_id="exist-id",
    )

    assert result == "exist-id"
    assert update_req.execute.call_count == 2


def test_upsert_sheet_recovers_from_connection_aborted_on_create(fake_xlsx):
    """新規作成時に ConnectionAbortedError が出ても、リトライで成功する。"""
    svc = MagicMock()
    create_req = MagicMock()
    create_req.execute.side_effect = [
        ConnectionAbortedError("WinError 10053"),
        {"id": "new-id", "name": "[同期] sample"},
    ]
    svc.files().create.return_value = create_req

    result = upsert_sheet(
        svc,
        xlsx_path=fake_xlsx,
        title="[同期] sample",
        folder_id="folder-1",
        existing_file_id="",
    )

    assert result == "new-id"
    assert create_req.execute.call_count == 2


def test_upsert_sheet_uploads_from_local_copy_not_nas(fake_xlsx):
    """upsert_sheet が MediaFileUpload に渡すパスは NAS 元ファイルではなく一時コピーであること。

    これにより NAS ファイルへのロック時間がコピー時間（数百ms）に短縮される。
    """
    svc = MagicMock()
    svc.files().create().execute.return_value = {"id": "x", "name": "t"}

    captured_paths = []

    def fake_media(path, **kwargs):
        captured_paths.append(path)
        return MagicMock()

    with patch("tamatex.sheets_sync.MediaFileUpload", side_effect=fake_media):
        upsert_sheet(
            svc,
            xlsx_path=fake_xlsx,
            title="t",
            folder_id="folder-1",
            existing_file_id="",
        )

    assert len(captured_paths) >= 1
    for path in captured_paths:
        # 渡されたパスは NAS 原本ではなく、tamatex_upload_ プレフィックスの一時ファイル
        assert path != fake_xlsx
        assert "tamatex_upload_" in os.path.basename(path)
