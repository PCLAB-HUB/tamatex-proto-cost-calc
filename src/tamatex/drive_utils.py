"""Google Drive API 共通ユーティリティ。

サービスアカウント認証・サブフォルダ管理・共有設定など、
sheets_sync と pdf_sync の両方から利用される操作を集約する。
"""

import logging
import socket
import ssl
import sys
import time
from pathlib import Path
from typing import Callable, TypeVar

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger("tamatex")

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]

MIME_SHEETS = "application/vnd.google-apps.spreadsheet"
MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MIME_FOLDER = "application/vnd.google-apps.folder"
MIME_PDF = "application/pdf"

# テストで monkeypatch できるよう、モジュール変数として保持する。
# 本番では time.sleep をそのまま使い、テストでは conftest.py が no-op に差し替える。
_retry_sleep = time.sleep

# 一過性ネットワーク例外（リトライ対象）
# - ConnectionAbortedError / ConnectionResetError / ConnectionRefusedError は
#   ConnectionError の派生。
# - socket.timeout は Python 3.10+ で TimeoutError と同義。
# - ssl.SSLError は SSLEOFError 等の途中切断系を含む。
_TRANSIENT_EXC = (
    ConnectionError,
    TimeoutError,
    socket.timeout,
    ssl.SSLError,
)

# 一過性 HTTP ステータス（リトライ対象）
# 429: rate limit、500/502/503/504: サーバ側一時障害
_TRANSIENT_HTTP_STATUS = frozenset({429, 500, 502, 503, 504})

T = TypeVar("T")


def with_retry(
    fn: Callable[[], T],
    *,
    op_name: str = "API呼出",
    max_attempts: int = 3,
    base_delay: float = 1.0,
) -> T:
    """Drive API 呼出を一過性エラーに耐えて実行する。

    対象:
      - ConnectionAbortedError 等の ConnectionError 派生
      - TimeoutError / socket.timeout / ssl.SSLError
      - HttpError(429, 500, 502, 503, 504)

    対象外:
      - HttpError(その他の 4xx) はそのまま raise（呼び出し側が 404 等で
        分岐するため、リトライしてしまうと意図的なフォールバックを阻害する）
      - その他の例外はそのまま raise

    Parameters
    ----------
    fn : callable
        引数なしで API 呼出を実行する関数。通常は
        ``lambda: service.files().create(...).execute()`` のように渡す。
    op_name : str
        ログに出力する操作名（"files.update" など）。
    max_attempts : int
        最大試行回数（初回含む）。デフォルト 3。
    base_delay : float
        バックオフ初期秒数。実際の sleep は base_delay * 2**(attempt-1)。
        デフォルト 1.0 秒 → 1s, 2s。

    Returns
    -------
    T
        ``fn()`` の戻り値。

    Raises
    ------
    Exception
        最大試行回数に達してもなお失敗した場合、最後の例外をそのまま raise。
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except _TRANSIENT_EXC as e:
            last_exc = e
        except HttpError as e:
            # httplib2 のバージョン差で resp.status が str/int 両方ありうるため
            # int() で明示変換する（変換できなければ非一過性として上位へ送る）
            raw_status = getattr(e.resp, "status", None) if getattr(e, "resp", None) else None
            try:
                status = int(raw_status) if raw_status is not None else None
            except (TypeError, ValueError):
                status = None
            if status not in _TRANSIENT_HTTP_STATUS:
                # 一過性でない HTTP エラー（404 等）はそのまま上位へ
                raise
            last_exc = e

        # ここに到達 = transient 失敗
        if attempt >= max_attempts:
            logger.error(
                "%s: リトライ上限到達 (attempts=%d) - %s",
                op_name, attempt, last_exc,
            )
            assert last_exc is not None
            raise last_exc
        sleep_s = base_delay * (2 ** (attempt - 1))
        logger.warning(
            "%s: transient失敗 (%d/%d)、%.1f秒後にリトライ - %s",
            op_name, attempt, max_attempts, sleep_s, last_exc,
        )
        _retry_sleep(sleep_s)
    # 防御的（到達不能）
    assert last_exc is not None
    raise last_exc


def build_drive_service(credentials_path: str, *, quiet: bool = False):
    """サービスアカウントで Drive API v3 クライアントを構築する。

    Unix 系ではキーファイルのパーミッションが緩い場合に警告する（F-01対策）。

    Parameters
    ----------
    quiet : bool
        True の場合、認証成功ログを DEBUG に下げる。サイクル毎の再生成で
        INFO ログを汚さないために使う。
    """
    cred_path = Path(credentials_path)
    if not cred_path.exists():
        raise FileNotFoundError(f"認証ファイルが見つかりません: {credentials_path}")

    if sys.platform != "win32":
        mode = oct(cred_path.stat().st_mode)[-3:]
        if mode not in ("600", "400"):
            logger.warning(
                "認証ファイルのパーミッションが緩すぎます: %s (現在: %s, 推奨: 600)",
                cred_path, mode,
            )

    creds = service_account.Credentials.from_service_account_file(
        str(cred_path),
        scopes=DRIVE_SCOPES,
    )
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    if quiet:
        logger.debug("Google Drive API認証成功（quiet）")
    else:
        logger.info("Google Drive API認証成功")
    return service


def _escape_q(value: str) -> str:
    """Drive API の q クエリ内シングルクォート・バックスラッシュをエスケープする。"""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def ensure_subfolder(service, parent_folder_id: str, name: str) -> str:
    """parent_folder_id 配下に指定名のサブフォルダを確保し、ID を返す。

    同名フォルダが既存なら最初のものを再利用。複数存在する場合は警告する。
    """
    q = (
        f"'{parent_folder_id}' in parents and "
        f"name = '{_escape_q(name)}' and "
        f"mimeType = '{MIME_FOLDER}' and "
        f"trashed = false"
    )
    res = with_retry(
        lambda: service.files().list(
            q=q,
            fields="files(id,name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            pageSize=10,
        ).execute(),
        op_name="files.list(ensure_subfolder)",
    )
    items = res.get("files", [])
    if items:
        if len(items) > 1:
            logger.warning(
                "同名サブフォルダが複数存在（最初のものを使用）: name=%s count=%d",
                name, len(items),
            )
        logger.debug("サブフォルダ再利用: %s (%s)", name, items[0]["id"])
        return items[0]["id"]

    meta = {
        "name": name,
        "mimeType": MIME_FOLDER,
        "parents": [parent_folder_id],
    }
    new = with_retry(
        lambda: service.files().create(
            body=meta,
            fields="id",
            supportsAllDrives=True,
        ).execute(),
        op_name="files.create(ensure_subfolder)",
    )
    logger.info("サブフォルダ作成: %s (%s)", name, new["id"])
    return new["id"]


def ensure_folder_path(
    service,
    root_folder_id: str,
    path_parts: list[str],
) -> str:
    """root_folder_id 配下にネストしたサブフォルダ構造を確保し、最深のIDを返す。

    例:
        ensure_folder_path(svc, "root", []) → "root" を返す（変更なし）
        ensure_folder_path(svc, "root", ["A"]) → "root/A" のIDを返す
        ensure_folder_path(svc, "root", ["A", "B"]) → "root/A/B" のIDを返す

    各階層について `ensure_subfolder` を順次呼ぶため、既存フォルダがあれば
    再利用し、無ければ作成する。
    """
    current = root_folder_id
    for part in path_parts:
        current = ensure_subfolder(service, current, part)
    return current


def get_file_parents(service, file_id: str) -> list[str]:
    """ファイルの現在の親フォルダ ID 一覧を取得する。"""
    f = with_retry(
        lambda: service.files().get(
            fileId=file_id,
            fields="parents",
            supportsAllDrives=True,
        ).execute(),
        op_name="files.get(parents)",
    )
    return f.get("parents", []) or []


def move_to_folder(service, file_id: str, target_folder_id: str) -> None:
    """ファイルを指定フォルダへ移動する。既に配置済みなら何もしない。"""
    current = get_file_parents(service, file_id)
    if target_folder_id in current:
        return
    with_retry(
        lambda: service.files().update(
            fileId=file_id,
            addParents=target_folder_id,
            removeParents=",".join(current) if current else None,
            supportsAllDrives=True,
        ).execute(),
        op_name="files.update(move)",
    )
    logger.info("ファイル移動: %s → フォルダ %s", file_id, target_folder_id)


def apply_share(service, file_id: str, emails: list[str]) -> None:
    """閲覧者権限を冪等に適用する。既に共有済みアドレスはスキップ。

    個別の追加失敗は警告ログのみで継続する。
    """
    if not emails:
        return

    try:
        existing = with_retry(
            lambda: service.permissions().list(
                fileId=file_id,
                fields="permissions(id,emailAddress,role,type)",
                supportsAllDrives=True,
            ).execute(),
            op_name="permissions.list",
        )
    except HttpError as e:
        logger.warning("共有リスト取得失敗（続行）: %s - %s", file_id, e)
        return

    existing_emails = {
        (p.get("emailAddress") or "").lower()
        for p in existing.get("permissions", [])
        if p.get("type") == "user" and p.get("emailAddress")
    }

    for email in emails:
        if email.lower() in existing_emails:
            continue
        try:
            with_retry(
                lambda email=email: service.permissions().create(
                    fileId=file_id,
                    body={"type": "user", "role": "reader", "emailAddress": email},
                    sendNotificationEmail=False,
                    supportsAllDrives=True,
                ).execute(),
                op_name="permissions.create",
            )
            logger.info("共有追加: %s → %s (閲覧者)", file_id, email)
        except HttpError as e:
            logger.warning("共有設定失敗（続行）: %s → %s - %s", file_id, email, e)
