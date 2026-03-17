"""Excel読み取りモジュール。openpyxlでExcelデータをPythonデータ構造に変換する。"""

import logging
from dataclasses import dataclass
from datetime import datetime, date, time
from pathlib import Path

from openpyxl import load_workbook

logger = logging.getLogger("tamatex")


@dataclass
class SheetData:
    name: str
    rows: list[list]  # 各行は値のリスト


@dataclass
class WorkbookData:
    file_name: str
    sheets: list[SheetData]


def _convert_cell_value(value) -> str | int | float | None:
    """セル値をGoogle Sheets互換の型に変換する。"""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, time):
        return value.strftime("%H:%M:%S")
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    return str(value)


def read_workbook(file_path: str | Path) -> WorkbookData:
    """Excelファイルを読み取り、全シートのデータを返す。"""
    path = Path(file_path)
    logger.info("Excel読み取り開始: %s", path.name)

    wb = load_workbook(str(path), read_only=True, data_only=True)
    try:
        sheets: list[SheetData] = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows: list[list] = []
            for row in ws.iter_rows():
                converted = [_convert_cell_value(cell.value) for cell in row]
                rows.append(converted)

            # 末尾の空行を除去
            while rows and all(v == "" or v is None for v in rows[-1]):
                rows.pop()

            sheets.append(SheetData(name=sheet_name, rows=rows))
            logger.debug("  シート '%s': %d 行", sheet_name, len(rows))

        return WorkbookData(file_name=path.stem, sheets=sheets)
    finally:
        wb.close()
