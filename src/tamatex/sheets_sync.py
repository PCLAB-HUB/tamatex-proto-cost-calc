"""Google Sheets 同期モジュール。

.xlsx を Drive API でそのままアップロードし、Google 側に Sheets 形式へ
自動変換させる。書式（罫線・色・マージセル・通貨書式・非表示列・カスタム数値書式）は
Google の純正コンバータが保持するため、openpyxl で値を抜き出して書き戻す旧方式より
再現率が大幅に向上する。

既存 fileId がある場合はコンテンツを置換（URL は不変）、フォルダ位置が違えば
自動で矯正する。

NAS 上のファイルを直接 MediaFileUpload に渡すと、Drive API 呼び出しが完了するまで
NAS ファイルが読込ロックされる（Windows SMB のファイル共有モードの都合）。
事務員が同じ Excel を Office で保存しようとすると「ドキュメントが保存されていません」
エラーが出るため、**ローカル一時ファイルにコピーしてからアップロード** することで
NAS ロック時間を最小化する。
"""

import logging
import os
import shutil
import tempfile
from contextlib import contextmanager

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from tamatex.drive_utils import (
    MIME_SHEETS,
    MIME_XLSX,
    move_to_folder,
    with_retry,
)

logger = logging.getLogger("tamatex")


@contextmanager
def _local_copy(src_path: str):
    """NAS ファイルをローカル一時ファイルにコピーし、パスを yield する。

    終了時に一時ファイルを削除する。失敗しても無視（OSエラーは警告ログのみ）。
    NAS ファイルへのアクセスをコピー時間（通常 0.1〜1秒）に最小化することで、
    Excel 側の保存処理との衝突を回避する。
    """
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".xlsx", prefix="tamatex_upload_")
    os.close(tmp_fd)  # ハンドルは閉じてからコピーする
    try:
        shutil.copy2(src_path, tmp_path)
        logger.debug(
            "NASファイルをローカルコピー: %s -> %s (%d bytes)",
            src_path, tmp_path, os.path.getsize(tmp_path),
        )
        yield tmp_path
    finally:
        try:
            os.unlink(tmp_path)
        except OSError as e:
            logger.warning("一時ファイル削除失敗（続行）: %s - %s", tmp_path, e)


def upsert_sheet(
    service,
    xlsx_path: str,
    title: str,
    folder_id: str,
    existing_file_id: str = "",
) -> str:
    """.xlsx を Google Sheets に変換してアップロード、または既存を更新する。

    NAS ロック時間最小化のため、内部でローカル一時ファイルにコピーしてから
    アップロードする。

    Parameters
    ----------
    service : Resource
        Drive API v3 サービスオブジェクト。
    xlsx_path : str
        アップロード元の xlsx ファイル絶対パス（UNC可）。
    title : str
        Sheets のファイル名。
    folder_id : str
        配置先フォルダ ID。
    existing_file_id : str
        既存 Sheets の fileId。空なら新規作成。

    Returns
    -------
    str
        Sheets の fileId。
    """
    with _local_copy(xlsx_path) as local_path:
        if existing_file_id:
            try:
                # MediaFileUpload はリトライ毎に作り直す（ストリーム位置リセットのため）
                with_retry(
                    lambda: service.files().update(
                        fileId=existing_file_id,
                        body={"name": title, "mimeType": MIME_SHEETS},
                        media_body=MediaFileUpload(
                            local_path, mimetype=MIME_XLSX, resumable=False
                        ),
                        fields="id,name",
                        supportsAllDrives=True,
                    ).execute(),
                    op_name=f"files.update[Sheets:{title}]",
                )
                logger.info("Sheets更新: %s (%s)", title, existing_file_id)
                move_to_folder(service, existing_file_id, folder_id)
                return existing_file_id
            except HttpError as e:
                if e.resp.status == 404:
                    logger.warning(
                        "既存Sheets喪失のため新規作成: old_id=%s title=%s",
                        existing_file_id, title,
                    )
                    # 新規作成フローに落ちる
                else:
                    raise

        meta = {
            "name": title,
            "mimeType": MIME_SHEETS,
            "parents": [folder_id],
        }
        new = with_retry(
            lambda: service.files().create(
                body=meta,
                media_body=MediaFileUpload(
                    local_path, mimetype=MIME_XLSX, resumable=False
                ),
                fields="id,name",
                supportsAllDrives=True,
            ).execute(),
            op_name=f"files.create[Sheets:{title}]",
        )
        logger.info("Sheets新規作成: %s (%s)", title, new["id"])
        return new["id"]
