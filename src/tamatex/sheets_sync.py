"""Google Sheets同期モジュール。Excelデータをスプレッドシートに書き込む。"""

import logging
import time as time_module

import gspread
from google.oauth2.service_account import Credentials

from tamatex.excel_reader import WorkbookData

logger = logging.getLogger("tamatex")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# API呼び出し間の待機秒数（レート制限対策）
API_WAIT_SECONDS = 1.0


def authenticate(credentials_path: str) -> gspread.Client:
    """サービスアカウントで認証し、gspreadクライアントを返す。"""
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    client = gspread.Client(auth=creds)
    logger.info("Google API認証成功")
    return client


def create_spreadsheet(
    client: gspread.Client,
    title: str,
    folder_id: str = "",
    share_with: list[str] | None = None,
) -> str:
    """新規スプレッドシートを作成し、IDを返す。"""
    # folder_idが指定された場合は直接そのフォルダに作成する（gspread 6.x）
    spreadsheet = client.create(title, folder_id=folder_id if folder_id else None)
    spreadsheet_id = spreadsheet.id
    logger.info("スプレッドシート作成: '%s' (ID: %s)", title, spreadsheet_id)
    if folder_id:
        logger.info("フォルダに作成: %s", folder_id)

    # 共有設定
    if share_with:
        for email in share_with:
            try:
                spreadsheet.share(email, perm_type="user", role="reader")
                logger.info("共有追加: %s (閲覧者)", email)
            except Exception as e:
                logger.warning("共有設定失敗（続行）: %s - %s", email, e)
            time_module.sleep(API_WAIT_SECONDS)

    return spreadsheet_id


def sync_workbook(
    client: gspread.Client,
    workbook: WorkbookData,
    spreadsheet_id: str,
) -> None:
    """WorkbookDataの内容を既存スプレッドシートに上書き同期する。"""
    spreadsheet = client.open_by_key(spreadsheet_id)

    existing_sheets = {ws.title: ws for ws in spreadsheet.worksheets()}
    target_sheet_names = [s.name for s in workbook.sheets]

    for sheet_data in workbook.sheets:
        if sheet_data.name in existing_sheets:
            worksheet = existing_sheets[sheet_data.name]
        else:
            # 新しいシートを作成
            rows = max(len(sheet_data.rows), 1)
            cols = max((max(len(r) for r in sheet_data.rows) if sheet_data.rows else 1), 1)
            worksheet = spreadsheet.add_worksheet(
                title=sheet_data.name, rows=rows, cols=cols
            )
            logger.info("  シート追加: '%s'", sheet_data.name)
            time_module.sleep(API_WAIT_SECONDS)

        # データ書き込み（上書き → 余剰行のみクリア）
        if sheet_data.rows:
            # 現在のシート行数を取得（余剰行削除のため）
            old_row_count = worksheet.row_count

            # 行数・列数を調整
            max_cols = max(len(r) for r in sheet_data.rows)
            # 全行の列数を揃える
            normalized_rows = [
                row + [""] * (max_cols - len(row)) for row in sheet_data.rows
            ]

            # clear()なしで直接上書き（空白ウィンドウを排除）
            worksheet.update(
                normalized_rows,
                value_input_option="RAW",
            )
            logger.info(
                "  シート更新: '%s' (%d行 x %d列)",
                sheet_data.name,
                len(normalized_rows),
                max_cols,
            )

            # 新データより多かった旧行を削除してゴミデータを残さない
            new_row_count = len(normalized_rows)
            if old_row_count > new_row_count:
                excess_range = f"{new_row_count + 1}:{old_row_count}"
                worksheet.batch_clear([excess_range])
                logger.debug(
                    "  余剰行クリア: '%s' (%s)",
                    sheet_data.name,
                    excess_range,
                )
        else:
            worksheet.clear()
            logger.info("  シートクリア: '%s' (空)", sheet_data.name)

        time_module.sleep(API_WAIT_SECONDS)

    # Excel側で削除されたシートをスプレッドシートからも削除
    # ただし最低1シートは残す必要がある
    sheets_to_delete = [
        ws for name, ws in existing_sheets.items()
        if name not in target_sheet_names
    ]
    deleted_count = 0
    total_sheets = len(target_sheet_names) + len(sheets_to_delete)
    for ws in sheets_to_delete:
        # 削除後の残シート数が0になる場合は中断する
        if total_sheets - deleted_count <= 1:
            break
        try:
            spreadsheet.del_worksheet(ws)
            deleted_count += 1
            logger.info("  シート削除: '%s'", ws.title)
            time_module.sleep(API_WAIT_SECONDS)
        except Exception as e:
            logger.warning("  シート削除失敗（続行）: '%s' - %s", ws.title, e)
