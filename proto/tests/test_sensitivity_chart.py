"""為替感度チャート — 内部ヘルパのユニットテスト.

render_fx_sensitivity_chart（Streamlit描画）は unit test 対象外。
_calc_avg_cost_at_fx の計算ロジックを検証する。

注意: task仕様の calc_single_cost / cost_jpy は実装に存在しない。
  実際は calc_single_item / jpy_cost を使用している（sensitivity_chart.py 参照）。
"""

from __future__ import annotations

import pytest

from proto.data.mock_items import (
    ITEM_01,
    ITEM_02,
    ITEM_03,
    ITEM_04,
    ITEM_05,
    ITEM_06,
)
from proto.data.mock_params import COND_20FT
from proto.engine.calc_single import calc_single_item
from proto.ui.components.sensitivity_chart import _calc_avg_cost_at_fx

# テスト用品目リスト（モックデータ全6品目）
MOCK_ITEMS = [ITEM_01, ITEM_02, ITEM_03, ITEM_04, ITEM_05, ITEM_06]

TOLERANCE = 0.01  # 許容誤差 (円)


class TestCalcAvgCostAtFx:
    """_calc_avg_cost_at_fx のユニットテスト."""

    def test_matches_calc_single_item_at_150(self):
        """fx=150.0 の結果が calc_single_item で再計算した平均値と一致する."""
        result = _calc_avg_cost_at_fx(150.0, COND_20FT, MOCK_ITEMS)

        from dataclasses import replace

        cond_at_150 = replace(COND_20FT, internal_rate=150.0)
        expected_costs = [calc_single_item(item, cond_at_150).jpy_cost for item in MOCK_ITEMS]
        expected_avg = sum(expected_costs) / len(expected_costs)

        assert result == pytest.approx(expected_avg, abs=TOLERANCE)

    def test_different_value_at_160_vs_150(self):
        """fx=160.0 と fx=150.0 で結果が異なる（為替が原価に影響している）."""
        cost_150 = _calc_avg_cost_at_fx(150.0, COND_20FT, MOCK_ITEMS)
        cost_160 = _calc_avg_cost_at_fx(160.0, COND_20FT, MOCK_ITEMS)

        assert cost_150 != pytest.approx(cost_160, abs=TOLERANCE), (
            "為替 150 と 160 で平均原価が同じ値になっています。"
            "calc_single_item が internal_rate を参照していない可能性があります。"
        )

    def test_higher_fx_yields_higher_cost(self):
        """為替レートが高いほど原価が高くなる（正の相関）."""
        cost_140 = _calc_avg_cost_at_fx(140.0, COND_20FT, MOCK_ITEMS)
        cost_150 = _calc_avg_cost_at_fx(150.0, COND_20FT, MOCK_ITEMS)
        cost_160 = _calc_avg_cost_at_fx(160.0, COND_20FT, MOCK_ITEMS)

        assert cost_140 < cost_150 < cost_160, (
            f"原価の増加順序が期待と異なります: "
            f"cost_140={cost_140:.2f}, cost_150={cost_150:.2f}, cost_160={cost_160:.2f}"
        )

    def test_empty_items_returns_zero(self):
        """items が空リストの場合は 0.0 を返す."""
        result = _calc_avg_cost_at_fx(150.0, COND_20FT, [])

        assert result == pytest.approx(0.0, abs=TOLERANCE)

    def test_single_item_matches_individual_cost(self):
        """単一品目リストの場合、その品目の jpy_cost と一致する."""
        from dataclasses import replace

        fx = 155.0
        cond_at_fx = replace(COND_20FT, internal_rate=fx)
        expected = calc_single_item(ITEM_01, cond_at_fx).jpy_cost

        result = _calc_avg_cost_at_fx(fx, COND_20FT, [ITEM_01])

        assert result == pytest.approx(expected, abs=TOLERANCE)
