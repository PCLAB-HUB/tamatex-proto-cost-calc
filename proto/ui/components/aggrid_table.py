"""streamlit-aggrid ファクトリ — 通貨・パーセント列の共通化.

このモジュールは streamlit-aggrid を使ったテーブル描画を、プロジェクト全体で
統一された作法で呼び出せるファクトリ関数と列定義ヘルパを提供する。

使用例（単品テーブルを aggrid で描画）:

    import pandas as pd
    from proto.ui.components.aggrid_table import (
        create_aggrid,
        text_column,
        currency_column,
        percent_column,
        number_column,
    )

    df = pd.DataFrame({
        "品名": ["タオルA", "タオルB", "タオルC"],
        "原価": [1000, 1500, 2000],
        "粗利率": [45.5, 52.3, 48.9],
        "入数": [100, 80, 60],
    })

    columns = [
        text_column("品名", "品名", width=200),
        currency_column("原価", "原価（円）"),
        percent_column("粗利率", "粗利率", decimals=1),
        number_column("入数", "入数", decimals=0, width=80),
    ]

    result = create_aggrid(df, columns, selection="multiple", height=300)
    selected = result.selected_rows  # 選択された行のデータ
"""
from __future__ import annotations

from typing import Any, Literal

import pandas as pd

# streamlit-aggrid のインポート（Streamlit ランタイム外でのテスト時はモック不要）
from st_aggrid import AgGrid, ColumnsAutoSizeMode, GridOptionsBuilder
from st_aggrid.shared import DataReturnMode, GridUpdateMode

# ---- JavaScript フォーマッター -----------------------------------------------

_YEN_FORMATTER = """
function(params) {
  if (params.value == null) return '';
  return '¥' + Number(params.value).toLocaleString('ja-JP', {maximumFractionDigits: 0});
}
"""

_PERCENT_FORMATTER_TEMPLATE = """
function(params) {{
  if (params.value == null) return '';
  return Number(params.value).toFixed({decimals}) + '%';
}}
"""

_NUMBER_FORMATTER_TEMPLATE = (
    "function(params) {{ return Number(params.value).toFixed({decimals}); }}"
)


# ---- 列定義ヘルパ ------------------------------------------------------------


def currency_column(field: str, header: str, *, width: int | None = None) -> dict:
    """通貨列定義を返す。

    値を `¥1,234` 形式でフォーマット（JavaScript valueFormatter）し、右寄せ表示する。

    Args:
        field: DataFrame の列名。
        header: テーブルヘッダに表示する文字列。
        width: 列幅（px）。None の場合は自動サイズ。

    Returns:
        AgGrid の column definition に渡す dict。
    """
    col: dict[str, Any] = {
        "field": field,
        "headerName": header,
        "type": ["numericColumn", "rightAligned"],
        "valueFormatter": _YEN_FORMATTER,
        "sortable": True,
        "filter": "agNumberColumnFilter",
    }
    if width is not None:
        col["width"] = width
    return col


def percent_column(
    field: str, header: str, *, decimals: int = 1, width: int | None = None
) -> dict:
    """パーセント列定義を返す。

    値を `50.6%` 形式でフォーマット（小数点桁数は decimals で制御）し、右寄せ表示する。

    Args:
        field: DataFrame の列名。
        header: テーブルヘッダに表示する文字列。
        decimals: 小数点以下の桁数。デフォルト 1。
        width: 列幅（px）。None の場合は自動サイズ。

    Returns:
        AgGrid の column definition に渡す dict。
    """
    col: dict[str, Any] = {
        "field": field,
        "headerName": header,
        "type": ["numericColumn", "rightAligned"],
        "valueFormatter": _PERCENT_FORMATTER_TEMPLATE.format(decimals=decimals),
        "sortable": True,
        "filter": "agNumberColumnFilter",
    }
    if width is not None:
        col["width"] = width
    return col


def text_column(field: str, header: str, *, width: int | None = None) -> dict:
    """テキスト列定義を返す。

    ソートとテキストフィルタを有効化する。

    Args:
        field: DataFrame の列名。
        header: テーブルヘッダに表示する文字列。
        width: 列幅（px）。None の場合は自動サイズ。

    Returns:
        AgGrid の column definition に渡す dict。
    """
    col: dict[str, Any] = {
        "field": field,
        "headerName": header,
        "sortable": True,
        "filter": "agTextColumnFilter",
    }
    if width is not None:
        col["width"] = width
    return col


def number_column(
    field: str, header: str, *, decimals: int = 0, width: int | None = None
) -> dict:
    """純数値列定義を返す。

    値を指定桁数の小数で表示し（通貨記号なし）、右寄せ表示する。

    Args:
        field: DataFrame の列名。
        header: テーブルヘッダに表示する文字列。
        decimals: 小数点以下の桁数。デフォルト 0（整数表示）。
        width: 列幅（px）。None の場合は自動サイズ。

    Returns:
        AgGrid の column definition に渡す dict。
    """
    col: dict[str, Any] = {
        "field": field,
        "headerName": header,
        "type": ["numericColumn", "rightAligned"],
        "valueFormatter": _NUMBER_FORMATTER_TEMPLATE.format(decimals=decimals),
        "sortable": True,
        "filter": "agNumberColumnFilter",
    }
    if width is not None:
        col["width"] = width
    return col


# ---- メインファクトリ ---------------------------------------------------------


def create_aggrid(
    df: pd.DataFrame,
    column_defs: list[dict],
    *,
    selection: Literal["none", "single", "multiple"] = "none",
    height: int = 400,
    theme: str = "streamlit",
):
    """streamlit-aggrid でテーブルを描画する。

    空 DataFrame（0行）を渡してもエラーにならず、空テーブルが表示される。
    戻り値から `.selected_rows` で選択行を取得できる。

    Args:
        df: 表示するデータ。空でも可。
        column_defs: `currency_column` 等のヘルパ関数が返す dict のリスト。
        selection: 行選択モード。
            - ``"none"`` — 選択無効（デフォルト）
            - ``"single"`` — 単一行選択
            - ``"multiple"`` — チェックボックスによる複数行選択
        height: テーブルの高さ（px）。デフォルト 400。
        theme: AgGrid のテーマ名。デフォルト ``"streamlit"``。

    Returns:
        AgGridReturn オブジェクト。`.selected_rows` で選択行を取得可能。

    Example:
        >>> import pandas as pd
        >>> from proto.ui.components.aggrid_table import (
        ...     create_aggrid, text_column, currency_column, percent_column,
        ... )
        >>> df = pd.DataFrame({
        ...     "品名": ["タオルA", "タオルB"],
        ...     "原価": [1000, 1500],
        ...     "粗利率": [45.5, 52.3],
        ... })
        >>> columns = [
        ...     text_column("品名", "品名", width=200),
        ...     currency_column("原価", "原価（円）"),
        ...     percent_column("粗利率", "粗利率"),
        ... ]
        >>> result = create_aggrid(df, columns, selection="multiple", height=300)
        >>> selected = result.selected_rows
    """
    gb = GridOptionsBuilder.from_dataframe(df)

    for col_def in column_defs:
        gb.configure_column(**col_def)

    gb.configure_default_column(
        resizable=True,
        filter=True,
        sortable=True,
    )

    if selection == "single":
        gb.configure_selection(
            selection_mode="single",
            use_checkbox=False,
        )
    elif selection == "multiple":
        gb.configure_selection(
            selection_mode="multiple",
            use_checkbox=True,
        )

    grid_options = gb.build()

    return AgGrid(
        df,
        gridOptions=grid_options,
        height=height,
        theme=theme,
        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT_AND_FILTERED,
        allow_unsafe_jscode=True,  # JS valueFormatter を使うため必須
    )
