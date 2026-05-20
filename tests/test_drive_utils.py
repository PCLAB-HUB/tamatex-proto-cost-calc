"""drive_utils.py の単体テスト。Drive API サービスは MagicMock で差し替える。"""

import socket
import ssl
from unittest.mock import MagicMock, call

import pytest
from googleapiclient.errors import HttpError

from tamatex.drive_utils import (
    MIME_FOLDER,
    _escape_q,
    apply_share,
    ensure_folder_path,
    ensure_subfolder,
    get_file_parents,
    move_to_folder,
    with_retry,
)


def _mk_http_error(status: int, reason: str = "err") -> HttpError:
    resp = MagicMock()
    resp.status = status
    resp.reason = reason
    return HttpError(resp=resp, content=b"")


# ---------------------------------------------------------------------------
# _escape_q
# ---------------------------------------------------------------------------

def test_escape_q_escapes_single_quote():
    assert _escape_q("it's") == r"it\'s"


def test_escape_q_escapes_backslash():
    assert _escape_q(r"a\b") == r"a\\b"


# ---------------------------------------------------------------------------
# ensure_subfolder
# ---------------------------------------------------------------------------

def test_ensure_subfolder_reuses_existing():
    """同名フォルダが既にある場合は create せず既存 ID を返す。"""
    svc = MagicMock()
    svc.files().list().execute.return_value = {
        "files": [{"id": "folder-abc", "name": "Sheets"}]
    }

    result = ensure_subfolder(svc, "parent-1", "Sheets")

    assert result == "folder-abc"
    svc.files().create.assert_not_called()


def test_ensure_subfolder_creates_when_missing():
    """同名フォルダが無い場合は create で新規作成。"""
    svc = MagicMock()
    svc.files().list().execute.return_value = {"files": []}
    svc.files().create().execute.return_value = {"id": "new-folder-id"}

    result = ensure_subfolder(svc, "parent-1", "PDF")

    assert result == "new-folder-id"
    # create が正しいメタデータで呼ばれたか
    create_calls = [c for c in svc.files().create.call_args_list if c.kwargs.get("body")]
    assert any(
        c.kwargs["body"] == {
            "name": "PDF",
            "mimeType": MIME_FOLDER,
            "parents": ["parent-1"],
        }
        for c in create_calls
    )


# ---------------------------------------------------------------------------
# get_file_parents / move_to_folder
# ---------------------------------------------------------------------------

def test_get_file_parents_returns_parents_list():
    svc = MagicMock()
    svc.files().get().execute.return_value = {"parents": ["p1", "p2"]}
    assert get_file_parents(svc, "fid") == ["p1", "p2"]


def test_get_file_parents_returns_empty_when_none():
    svc = MagicMock()
    svc.files().get().execute.return_value = {}
    assert get_file_parents(svc, "fid") == []


def test_move_to_folder_skips_when_already_in_target():
    svc = MagicMock()
    svc.files().get().execute.return_value = {"parents": ["target"]}

    move_to_folder(svc, "fid", "target")

    # update は呼ばれないこと
    update_calls = svc.files().update.call_args_list
    # update() with addParents kwarg = actual move op
    move_calls = [c for c in update_calls if "addParents" in c.kwargs]
    assert move_calls == []


def test_move_to_folder_moves_when_in_different_parent():
    svc = MagicMock()
    svc.files().get().execute.return_value = {"parents": ["old-parent"]}

    move_to_folder(svc, "fid", "new-parent")

    # addParents/removeParents を指定した update が呼ばれる
    move_calls = [
        c for c in svc.files().update.call_args_list
        if "addParents" in c.kwargs
    ]
    assert len(move_calls) == 1
    kwargs = move_calls[0].kwargs
    assert kwargs["fileId"] == "fid"
    assert kwargs["addParents"] == "new-parent"
    assert kwargs["removeParents"] == "old-parent"


# ---------------------------------------------------------------------------
# apply_share
# ---------------------------------------------------------------------------

def test_apply_share_noop_when_empty_list():
    svc = MagicMock()
    apply_share(svc, "fid", [])
    svc.permissions().list.assert_not_called()


def test_apply_share_creates_new_permission():
    svc = MagicMock()
    svc.permissions().list().execute.return_value = {"permissions": []}

    apply_share(svc, "fid", ["a@example.com"])

    create_calls = [
        c for c in svc.permissions().create.call_args_list
        if c.kwargs.get("body", {}).get("emailAddress") == "a@example.com"
    ]
    assert len(create_calls) == 1
    assert create_calls[0].kwargs["body"] == {
        "type": "user",
        "role": "reader",
        "emailAddress": "a@example.com",
    }


def test_apply_share_skips_already_shared_emails():
    svc = MagicMock()
    svc.permissions().list().execute.return_value = {
        "permissions": [
            {"emailAddress": "A@Example.com", "role": "reader", "type": "user"}
        ]
    }

    apply_share(svc, "fid", ["a@example.com", "b@example.com"])

    # b@ のみ create される
    create_emails = [
        c.kwargs.get("body", {}).get("emailAddress")
        for c in svc.permissions().create.call_args_list
        if c.kwargs.get("body", {}).get("emailAddress")
    ]
    assert "b@example.com" in create_emails
    assert "a@example.com" not in create_emails


# ---------------------------------------------------------------------------
# ensure_folder_path
# ---------------------------------------------------------------------------

def test_ensure_folder_path_returns_root_when_empty_parts():
    """空のパーツリストならルートIDをそのまま返す（API呼出なし）。"""
    svc = MagicMock()
    result = ensure_folder_path(svc, "root-id", [])
    assert result == "root-id"
    svc.files().list.assert_not_called()
    svc.files().create.assert_not_called()


def test_ensure_folder_path_creates_single_level():
    """1階層: ルート配下に "A" フォルダを確保し、そのIDを返す。"""
    svc = MagicMock()
    # ensure_subfolder の中で list → 空 → create → 新規ID返却
    svc.files().list().execute.return_value = {"files": []}
    svc.files().create().execute.return_value = {"id": "A-id"}

    result = ensure_folder_path(svc, "root", ["A"])
    assert result == "A-id"


def test_ensure_folder_path_creates_nested_levels():
    """2階層: A/B を確保。A→B の順に作られ、最終的に B のIDを返す。"""
    svc = MagicMock()
    # 各 list は空（フォルダ未存在）、create は順次新IDを返す
    svc.files().list().execute.return_value = {"files": []}
    create_results = [{"id": "A-id"}, {"id": "B-id"}]
    svc.files().create().execute.side_effect = create_results

    result = ensure_folder_path(svc, "root", ["A", "B"])
    assert result == "B-id"


# ---------------------------------------------------------------------------
# with_retry — 一過性エラーへの耐性（5/19 現場での AAA01* 等の失敗パターン）
# ---------------------------------------------------------------------------

def test_with_retry_returns_value_on_first_success():
    """1回で成功すれば fn の戻り値をそのまま返す。"""
    fn = MagicMock(return_value="ok")
    assert with_retry(fn, op_name="test") == "ok"
    assert fn.call_count == 1


def test_with_retry_recovers_after_connection_aborted():
    """ConnectionAbortedError は最大回数までリトライされ、回復したら成功する。"""
    fn = MagicMock(side_effect=[
        ConnectionAbortedError("WinError 10053"),
        "ok-after-retry",
    ])
    assert with_retry(fn, op_name="test", max_attempts=3) == "ok-after-retry"
    assert fn.call_count == 2


def test_with_retry_recovers_after_connection_reset():
    """ConnectionResetError もリトライ対象。"""
    fn = MagicMock(side_effect=[ConnectionResetError("reset"), "ok"])
    assert with_retry(fn, op_name="test") == "ok"
    assert fn.call_count == 2


def test_with_retry_recovers_after_timeout():
    """TimeoutError もリトライ対象。"""
    fn = MagicMock(side_effect=[TimeoutError("timeout"), "ok"])
    assert with_retry(fn, op_name="test") == "ok"
    assert fn.call_count == 2


def test_with_retry_recovers_after_socket_timeout():
    """socket.timeout もリトライ対象。"""
    fn = MagicMock(side_effect=[socket.timeout("sock timeout"), "ok"])
    assert with_retry(fn, op_name="test") == "ok"
    assert fn.call_count == 2


def test_with_retry_recovers_after_ssl_error():
    """ssl.SSLError もリトライ対象。"""
    fn = MagicMock(side_effect=[ssl.SSLError("tls aborted"), "ok"])
    assert with_retry(fn, op_name="test") == "ok"
    assert fn.call_count == 2


def test_with_retry_recovers_after_http_500():
    """HttpError 500 はリトライ対象。"""
    err = _mk_http_error(500)
    fn = MagicMock(side_effect=[err, "ok"])
    assert with_retry(fn, op_name="test") == "ok"
    assert fn.call_count == 2


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_with_retry_recovers_after_transient_http_status(status):
    err = _mk_http_error(status)
    fn = MagicMock(side_effect=[err, "ok"])
    assert with_retry(fn, op_name="test") == "ok"
    assert fn.call_count == 2


def test_with_retry_raises_http_404_immediately():
    """404 はリトライせず即座に raise する（呼出側のフォールバック判定のため）。"""
    err = _mk_http_error(404)
    fn = MagicMock(side_effect=err)
    with pytest.raises(HttpError):
        with_retry(fn, op_name="test")
    assert fn.call_count == 1


def test_with_retry_raises_http_403_immediately():
    """403 もリトライ対象外。"""
    err = _mk_http_error(403)
    fn = MagicMock(side_effect=err)
    with pytest.raises(HttpError):
        with_retry(fn, op_name="test")
    assert fn.call_count == 1


def test_with_retry_raises_non_transient_exception_immediately():
    """ValueError 等の予期しない例外はリトライせず raise。"""
    fn = MagicMock(side_effect=ValueError("oops"))
    with pytest.raises(ValueError):
        with_retry(fn, op_name="test")
    assert fn.call_count == 1


def test_with_retry_exhausts_attempts_and_raises_last_exception():
    """全試行が失敗したら最後の例外を raise。"""
    last_err = ConnectionAbortedError("final")
    fn = MagicMock(side_effect=[
        ConnectionAbortedError("first"),
        ConnectionAbortedError("second"),
        last_err,
    ])
    with pytest.raises(ConnectionAbortedError) as exc_info:
        with_retry(fn, op_name="test", max_attempts=3)
    assert exc_info.value is last_err
    assert fn.call_count == 3


def test_with_retry_max_attempts_one_means_no_retry():
    """max_attempts=1 はリトライしない（1回試して即 raise）。"""
    fn = MagicMock(side_effect=ConnectionAbortedError("once"))
    with pytest.raises(ConnectionAbortedError):
        with_retry(fn, op_name="test", max_attempts=1)
    assert fn.call_count == 1


def test_with_retry_uses_exponential_backoff(monkeypatch):
    """sleep 引数が base_delay * 2^(attempt-1) のシーケンスになっている。"""
    import tamatex.drive_utils as du

    sleeps: list[float] = []
    monkeypatch.setattr(du, "_retry_sleep", lambda s: sleeps.append(s))

    fn = MagicMock(side_effect=[
        ConnectionAbortedError("1"),
        ConnectionAbortedError("2"),
        "ok",
    ])
    with_retry(fn, op_name="test", max_attempts=3, base_delay=1.0)

    # attempt 1 失敗 → sleep 1.0、attempt 2 失敗 → sleep 2.0、attempt 3 成功（sleep なし）
    assert sleeps == [1.0, 2.0]


def test_with_retry_no_sleep_after_final_attempt(monkeypatch):
    """最後の試行が失敗しても sleep してから raise しないこと。"""
    import tamatex.drive_utils as du

    sleeps: list[float] = []
    monkeypatch.setattr(du, "_retry_sleep", lambda s: sleeps.append(s))

    fn = MagicMock(side_effect=ConnectionAbortedError("always"))
    with pytest.raises(ConnectionAbortedError):
        with_retry(fn, op_name="test", max_attempts=3, base_delay=1.0)
    # max_attempts=3 のとき、sleep は attempt 1, 2 の後だけ（合計2回）
    assert sleeps == [1.0, 2.0]


# ---------------------------------------------------------------------------
# 既存関数のリトライ統合テスト
# ---------------------------------------------------------------------------

def test_ensure_subfolder_retries_on_connection_aborted():
    """ensure_subfolder の list 呼出が ConnectionAbortedError でリトライ回復する。"""
    svc = MagicMock()
    list_req = MagicMock()
    list_req.execute.side_effect = [
        ConnectionAbortedError("transient"),
        {"files": [{"id": "folder-x", "name": "Sheets"}]},
    ]
    svc.files().list.return_value = list_req

    result = ensure_subfolder(svc, "parent", "Sheets")
    assert result == "folder-x"
    assert list_req.execute.call_count == 2


def test_move_to_folder_retries_on_connection_aborted():
    """move_to_folder の update 呼出がリトライで回復する。"""
    svc = MagicMock()
    svc.files().get().execute.return_value = {"parents": ["old"]}

    update_req = MagicMock()
    update_req.execute.side_effect = [
        ConnectionAbortedError("transient"),
        {"id": "fid"},
    ]
    svc.files().update.return_value = update_req

    # 例外が外に漏れないこと
    move_to_folder(svc, "fid", "new-parent")
    assert update_req.execute.call_count == 2


def test_apply_share_create_retries_on_transient():
    """apply_share の create が 503 でリトライ回復する。"""
    svc = MagicMock()
    svc.permissions().list().execute.return_value = {"permissions": []}

    create_req = MagicMock()
    create_req.execute.side_effect = [
        _mk_http_error(503),
        {"id": "perm-id"},
    ]
    svc.permissions().create.return_value = create_req

    apply_share(svc, "fid", ["a@example.com"])
    assert create_req.execute.call_count == 2


def test_apply_share_continues_on_individual_failure():
    """個別の create 失敗は警告のみで次のメールへ続行すること。"""
    svc = MagicMock()
    svc.permissions().list().execute.return_value = {"permissions": []}

    # 1件目は 403 を返し、2件目は成功
    def create_side_effect(**kwargs):
        email = kwargs.get("body", {}).get("emailAddress")
        mock_req = MagicMock()
        if email == "fail@example.com":
            mock_req.execute.side_effect = _mk_http_error(403, "forbidden")
        else:
            mock_req.execute.return_value = {"id": "perm-id"}
        return mock_req

    svc.permissions().create.side_effect = create_side_effect

    # 例外が外に漏れないこと
    apply_share(svc, "fid", ["fail@example.com", "ok@example.com"])
