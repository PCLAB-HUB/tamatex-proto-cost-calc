"""PDF 生成・同期モジュール。

変換済み Google Sheets から Drive API の export 機能で PDF を取得し、
Drive 上の指定フォルダに保存する。既存 PDF がある場合は中身を置換（URL 不変）。
"""

import io
import logging

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from tamatex.drive_utils import MIME_PDF, move_to_folder, with_retry

logger = logging.getLogger("tamatex")


def upsert_pdf(
    service,
    sheet_file_id: str,
    title: str,
    folder_id: str,
    existing_pdf_id: str = "",
) -> str:
    """Sheets をエクスポートし PDF として Drive に保存 or 更新する。

    Parameters
    ----------
    service : Resource
        Drive API v3 サービスオブジェクト。
    sheet_file_id : str
        エクスポート元の Google Sheets fileId。
    title : str
        PDF のファイル名（拡張子含む、例: "foo.pdf"）。
    folder_id : str
        配置先フォルダ ID。
    existing_pdf_id : str
        既存 PDF の fileId。空なら新規作成。

    Returns
    -------
    str
        PDF の fileId。
    """
    pdf_bytes = with_retry(
        lambda: service.files().export(
            fileId=sheet_file_id,
            mimeType=MIME_PDF,
        ).execute(),
        op_name=f"files.export[PDF:{title}]",
    )
    logger.debug(
        "PDFエクスポート完了: %d bytes (from Sheets %s)",
        len(pdf_bytes), sheet_file_id,
    )

    if existing_pdf_id:
        try:
            with_retry(
                lambda: service.files().update(
                    fileId=existing_pdf_id,
                    body={"name": title},
                    media_body=MediaIoBaseUpload(
                        io.BytesIO(pdf_bytes), mimetype=MIME_PDF
                    ),
                    fields="id,name",
                    supportsAllDrives=True,
                ).execute(),
                op_name=f"files.update[PDF:{title}]",
            )
            logger.info("PDF更新: %s (%s)", title, existing_pdf_id)
            move_to_folder(service, existing_pdf_id, folder_id)
            return existing_pdf_id
        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(
                    "既存PDF喪失のため新規作成: old_id=%s title=%s",
                    existing_pdf_id, title,
                )
            else:
                raise

    meta = {
        "name": title,
        "mimeType": MIME_PDF,
        "parents": [folder_id],
    }
    new = with_retry(
        lambda: service.files().create(
            body=meta,
            media_body=MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype=MIME_PDF),
            fields="id,name",
            supportsAllDrives=True,
        ).execute(),
        op_name=f"files.create[PDF:{title}]",
    )
    logger.info("PDF新規作成: %s (%s)", title, new["id"])
    return new["id"]
