"""pdf_sync.py の単体テスト。Drive API サービスは MagicMock で差し替える。"""

from unittest.mock import MagicMock

import pytest
from googleapiclient.errors import HttpError

from tamatex.pdf_sync import upsert_pdf


def _mk_http_error(status: int) -> HttpError:
    resp = MagicMock()
    resp.status = status
    resp.reason = "err"
    return HttpError(resp=resp, content=b"")


def test_upsert_pdf_creates_new_when_no_existing_id():
    """existing_pdf_id が空なら Sheets をエクスポートして PDF 新規作成。"""
    svc = MagicMock()
    svc.files().export().execute.return_value = b"%PDF-1.4 fake"
    svc.files().create().execute.return_value = {"id": "new-pdf-id", "name": "foo.pdf"}

    result = upsert_pdf(
        svc,
        sheet_file_id="sheet-1",
        title="foo.pdf",
        folder_id="pdf-folder",
        existing_pdf_id="",
    )

    assert result == "new-pdf-id"
    # export 呼び出しの検証
    export_calls = [
        c for c in svc.files().export.call_args_list
        if c.kwargs.get("fileId") == "sheet-1"
    ]
    assert len(export_calls) >= 1
    assert export_calls[0].kwargs["mimeType"] == "application/pdf"


def test_upsert_pdf_updates_existing_id():
    """existing_pdf_id があれば update で中身置換、同じ ID を返す。"""
    svc = MagicMock()
    svc.files().export().execute.return_value = b"%PDF-1.4"
    svc.files().update().execute.return_value = {"id": "exist-pdf", "name": "foo.pdf"}
    svc.files().get().execute.return_value = {"parents": ["pdf-folder"]}

    result = upsert_pdf(
        svc,
        sheet_file_id="sheet-1",
        title="foo.pdf",
        folder_id="pdf-folder",
        existing_pdf_id="exist-pdf",
    )

    assert result == "exist-pdf"
    update_calls = [
        c for c in svc.files().update.call_args_list
        if c.kwargs.get("fileId") == "exist-pdf" and c.kwargs.get("media_body") is not None
    ]
    assert len(update_calls) == 1


def test_upsert_pdf_falls_back_to_create_on_404():
    """既存PDFが404なら新規作成にフォールバック。"""
    svc = MagicMock()
    svc.files().export().execute.return_value = b"%PDF-1.4"

    update_req = MagicMock()
    update_req.execute.side_effect = _mk_http_error(404)
    create_req = MagicMock()
    create_req.execute.return_value = {"id": "fallback-pdf", "name": "t"}
    export_req = MagicMock()
    export_req.execute.return_value = b"%PDF-1.4"
    get_req = MagicMock()
    get_req.execute.return_value = {"parents": []}

    def files_method():
        m = MagicMock()
        m.update.return_value = update_req
        m.create.return_value = create_req
        m.export.return_value = export_req
        m.get.return_value = get_req
        return m

    svc.files = files_method

    result = upsert_pdf(
        svc,
        sheet_file_id="sheet-1",
        title="t",
        folder_id="pdf-folder",
        existing_pdf_id="missing-pdf",
    )
    assert result == "fallback-pdf"


def test_upsert_pdf_recovers_from_connection_aborted_on_export():
    """export 呼出が ConnectionAbortedError でもリトライ回復する。"""
    svc = MagicMock()
    export_req = MagicMock()
    export_req.execute.side_effect = [
        ConnectionAbortedError("WinError 10053"),
        b"%PDF-1.4 ok",
    ]
    create_req = MagicMock()
    create_req.execute.return_value = {"id": "pdf-id", "name": "t"}

    def files_method():
        m = MagicMock()
        m.export.return_value = export_req
        m.create.return_value = create_req
        return m
    svc.files = files_method

    result = upsert_pdf(
        svc,
        sheet_file_id="sheet-1",
        title="t.pdf",
        folder_id="pdf-folder",
        existing_pdf_id="",
    )
    assert result == "pdf-id"
    assert export_req.execute.call_count == 2


def test_upsert_pdf_recovers_from_connection_aborted_on_update():
    """update 呼出が ConnectionAbortedError でもリトライ回復する。"""
    svc = MagicMock()
    export_req = MagicMock()
    export_req.execute.return_value = b"%PDF-1.4"
    update_req = MagicMock()
    update_req.execute.side_effect = [
        ConnectionAbortedError("WinError 10053"),
        {"id": "exist-pdf", "name": "t.pdf"},
    ]
    get_req = MagicMock()
    get_req.execute.return_value = {"parents": ["pdf-folder"]}

    def files_method():
        m = MagicMock()
        m.export.return_value = export_req
        m.update.return_value = update_req
        m.get.return_value = get_req
        return m
    svc.files = files_method

    result = upsert_pdf(
        svc,
        sheet_file_id="sheet-1",
        title="t.pdf",
        folder_id="pdf-folder",
        existing_pdf_id="exist-pdf",
    )
    assert result == "exist-pdf"
    assert update_req.execute.call_count == 2


def test_upsert_pdf_propagates_non_404_errors():
    svc = MagicMock()
    export_req = MagicMock()
    export_req.execute.return_value = b"%PDF-1.4"
    update_req = MagicMock()
    update_req.execute.side_effect = _mk_http_error(500)

    def files_method():
        m = MagicMock()
        m.export.return_value = export_req
        m.update.return_value = update_req
        return m
    svc.files = files_method

    with pytest.raises(HttpError):
        upsert_pdf(
            svc,
            sheet_file_id="s",
            title="t",
            folder_id="f",
            existing_pdf_id="id",
        )
