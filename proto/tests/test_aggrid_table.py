"""aggrid_table モジュールの列定義ヘルパ関数テスト.

create_aggrid() は Streamlit ランタイムを要するため対象外。
列定義ヘルパ4関数（currency_column / percent_column / text_column / number_column）
の返り値 dict 構造を検証する。
"""

import pytest

from proto.ui.components.aggrid_table import (
    currency_column,
    number_column,
    percent_column,
    text_column,
)


def _formatter_text(col: dict) -> str:
    """valueFormatter の中身を文字列として取り出す（JsCode 対応）."""
    vf = col.get("valueFormatter")
    if vf is None:
        return ""
    # JsCode オブジェクトの場合は .js_code 属性から JS コードを取得
    if hasattr(vf, "js_code"):
        return vf.js_code
    return str(vf)


class TestCurrencyColumn:
    """currency_column のテスト."""

    def test_value_formatter_present(self):
        """valueFormatter キーが存在すること."""
        result = currency_column("price", "価格")
        assert "valueFormatter" in result

    def test_right_aligned(self):
        """type に 'rightAligned' が含まれること."""
        result = currency_column("price", "価格")
        assert "rightAligned" in result["type"]

    def test_field_and_header(self):
        """field と headerName が正しく設定されること."""
        result = currency_column("unit_price", "単価")
        assert result["field"] == "unit_price"
        assert result["headerName"] == "単価"

    def test_yen_sign_in_formatter(self):
        """valueFormatter に円記号（¥）が含まれること."""
        result = currency_column("cost", "原価")
        assert "¥" in _formatter_text(result)

    def test_width_included_when_specified(self):
        """width 指定時は dict に width キーが存在すること."""
        result = currency_column("price", "価格", width=120)
        assert result["width"] == 120

    def test_width_absent_when_none(self):
        """width=None（デフォルト）のとき width キーが存在しないこと."""
        result = currency_column("price", "価格")
        assert "width" not in result

    def test_sortable(self):
        """sortable が True であること."""
        result = currency_column("price", "価格")
        assert result["sortable"] is True


class TestPercentColumn:
    """percent_column のテスト."""

    def test_value_formatter_with_default_decimals(self):
        """デフォルト decimals=1 のとき toFixed(1) が formatter に含まれること."""
        result = percent_column("margin", "粗利率")
        assert "toFixed(1)" in _formatter_text(result)

    def test_value_formatter_with_custom_decimals(self):
        """decimals=2 のとき toFixed(2) が formatter に含まれること."""
        result = percent_column("margin", "粗利", decimals=2)
        assert "toFixed(2)" in _formatter_text(result)

    def test_percent_sign_in_formatter(self):
        """valueFormatter に '%' が含まれること."""
        result = percent_column("margin", "粗利率")
        assert "%" in _formatter_text(result)

    def test_right_aligned(self):
        """type に 'rightAligned' が含まれること."""
        result = percent_column("margin", "粗利率")
        assert "rightAligned" in result["type"]

    def test_width_absent_when_none(self):
        """width=None（デフォルト）のとき width キーが存在しないこと."""
        result = percent_column("margin", "粗利率")
        assert "width" not in result

    def test_width_included_when_specified(self):
        """width 指定時は dict に width キーが存在すること."""
        result = percent_column("margin", "粗利率", width=100)
        assert result["width"] == 100

    def test_decimals_zero(self):
        """decimals=0 のとき toFixed(0) が formatter に含まれること."""
        result = percent_column("margin", "粗利率", decimals=0)
        assert "toFixed(0)" in _formatter_text(result)


class TestTextColumn:
    """text_column のテスト."""

    def test_width_included_when_specified(self):
        """width=200 指定時は dict に 'width': 200 が含まれること."""
        result = text_column("name", "名前", width=200)
        assert result["width"] == 200

    def test_width_absent_when_none(self):
        """width=None（デフォルト）のとき width キーが存在しないこと."""
        result = text_column("name", "名前")
        assert "width" not in result

    def test_field_and_header(self):
        """field と headerName が正しく設定されること."""
        result = text_column("product_name", "商品名")
        assert result["field"] == "product_name"
        assert result["headerName"] == "商品名"

    def test_text_filter(self):
        """filter が agTextColumnFilter であること."""
        result = text_column("name", "名前")
        assert result["filter"] == "agTextColumnFilter"

    def test_sortable(self):
        """sortable が True であること."""
        result = text_column("name", "名前")
        assert result["sortable"] is True

    def test_no_value_formatter(self):
        """テキスト列には valueFormatter が不要（存在しないこと）."""
        result = text_column("name", "名前")
        assert "valueFormatter" not in result


class TestNumberColumn:
    """number_column のテスト."""

    def test_value_formatter_tofixed_zero(self):
        """decimals=0（デフォルト）のとき valueFormatter が toFixed(0) 形式であること."""
        result = number_column("count", "数量", decimals=0)
        assert "toFixed(0)" in _formatter_text(result)

    def test_value_formatter_tofixed_two(self):
        """decimals=2 のとき valueFormatter が toFixed(2) 形式であること."""
        result = number_column("weight", "重量", decimals=2)
        assert "toFixed(2)" in _formatter_text(result)

    def test_right_aligned(self):
        """type に 'rightAligned' が含まれること."""
        result = number_column("count", "数量")
        assert "rightAligned" in result["type"]

    def test_width_absent_when_none(self):
        """width=None（デフォルト）のとき width キーが存在しないこと."""
        result = number_column("count", "数量")
        assert "width" not in result

    def test_width_included_when_specified(self):
        """width 指定時は dict に width キーが存在すること."""
        result = number_column("count", "数量", width=80)
        assert result["width"] == 80

    def test_field_and_header(self):
        """field と headerName が正しく設定されること."""
        result = number_column("qty", "数量")
        assert result["field"] == "qty"
        assert result["headerName"] == "数量"

    def test_no_yen_sign_in_formatter(self):
        """純数値列のフォーマッターに円記号が含まれないこと."""
        result = number_column("count", "数量")
        assert "¥" not in _formatter_text(result)
