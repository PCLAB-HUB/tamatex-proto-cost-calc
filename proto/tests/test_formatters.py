"""フォーマッタ関数の単体テスト.

対象:
    - format_currency
    - format_percentage
    - format_delta
"""
from __future__ import annotations

import pytest

from proto.ui.components.kpi_cards import (
    format_currency,
    format_delta,
    format_percentage,
)


class TestFormatCurrency:
    """format_currency のテスト."""

    def test_small_amount_with_yen(self) -> None:
        """4桁金額は桁区切りなしで ¥ 付き."""
        assert format_currency(1234) == "¥1,234"

    def test_large_amount_with_thousands_separator(self) -> None:
        """7桁金額は千の桁区切りが入る."""
        assert format_currency(1234567) == "¥1,234,567"

    def test_zero(self) -> None:
        """ゼロ円は ¥0 で表示."""
        assert format_currency(0) == "¥0"

    def test_show_yen_false(self) -> None:
        """show_yen=False のとき ¥ プレフィックスを付けない."""
        assert format_currency(1234, show_yen=False) == "1,234"

    def test_float_rounds_to_integer(self) -> None:
        """小数点以下は切り捨て（.0f フォーマット）."""
        assert format_currency(1234.9) == "¥1,235"

    def test_negative_amount(self) -> None:
        """負の金額はマイナス符号付きで返す."""
        assert format_currency(-500) == "¥-500"


class TestFormatPercentage:
    """format_percentage のテスト."""

    def test_default_one_decimal(self) -> None:
        """デフォルトは小数1位に丸める."""
        assert format_percentage(50.67) == "50.7%"

    def test_two_decimals(self) -> None:
        """decimals=2 のとき小数2位で表示."""
        assert format_percentage(50.67, decimals=2) == "50.67%"

    def test_zero_decimals(self) -> None:
        """decimals=0 のとき整数表示."""
        assert format_percentage(50.67, decimals=0) == "51%"

    def test_zero_value(self) -> None:
        """ゼロは 0.0% で表示."""
        assert format_percentage(0.0) == "0.0%"

    def test_hundred_percent(self) -> None:
        """100% は 100.0% で表示."""
        assert format_percentage(100.0) == "100.0%"


class TestFormatDelta:
    """format_delta のテスト."""

    def test_positive_percentage_delta(self) -> None:
        """正の差分はプラス符号付きのパーセント形式."""
        assert format_delta(55.0, 50.0) == "+5.0%"

    def test_negative_percentage_delta(self) -> None:
        """負の差分はマイナス符号付きのパーセント形式."""
        assert format_delta(45.0, 50.0) == "-5.0%"

    def test_positive_currency_delta(self) -> None:
        """is_currency=True で正の差分は +¥XXX 形式."""
        assert format_delta(1500, 1000, is_currency=True) == "+¥500"

    def test_negative_currency_delta(self) -> None:
        """is_currency=True で負の差分は -¥XXX 形式（マイナス記号込み）."""
        assert format_delta(800, 1000, is_currency=True) == "-¥200"

    def test_zero_delta_percentage(self) -> None:
        """差分ゼロはプラス符号付きの +0.0% で表示."""
        assert format_delta(50.0, 50.0) == "+0.0%"

    def test_zero_delta_currency(self) -> None:
        """差分ゼロの通貨形式は +¥0 で表示."""
        assert format_delta(1000, 1000, is_currency=True) == "+¥0"

    def test_large_currency_delta_with_separator(self) -> None:
        """大きな通貨差分は千の桁区切りが入る."""
        assert format_delta(2500000, 1000000, is_currency=True) == "+¥1,500,000"
