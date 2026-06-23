"""集計計算のテスト — Excel行22の集計値との照合."""

import pytest

from proto.data.mock_gifts import ALL_GIFTS
from proto.data.mock_items import ALL_ITEMS
from proto.data.mock_params import COND_20FT
from proto.engine.calc_gift import calc_gift_set
from proto.engine.calc_single import calc_single_item
from proto.engine.calc_summary import calc_summary

TOLERANCE = 1.0        # 集計は丸め誤差が累積するため1円許容
RATE_TOLERANCE = 0.001  # 率の許容誤差


@pytest.fixture(scope="module")
def gift_results():
    """全ギフトの計算結果を事前計算."""
    item_results = {
        item_no: calc_single_item(item, COND_20FT)
        for item_no, item in ALL_ITEMS.items()
    }
    return [
        calc_gift_set(gift, ALL_ITEMS, item_results, COND_20FT)
        for gift in ALL_GIFTS
    ]


class TestSummary20FT:
    """行22 集計値（20FT条件）.

    Excel実値:
      I22=10000, K22=18703500, L22=2549877.944, H22=0.1363316
    """

    def test_total_quantity(self, gift_results):
        result = calc_summary(ALL_GIFTS, gift_results)
        # I22 = SUM(I23:I34) = 1000*8 + 500*4 = 10000
        assert result.total_quantity == 10000

    def test_total_sales(self, gift_results):
        result = calc_summary(ALL_GIFTS, gift_results)
        # K22 = SUM(K23:K34)
        assert result.total_sales == pytest.approx(18703500.0, abs=TOLERANCE)

    def test_total_profit(self, gift_results):
        result = calc_summary(ALL_GIFTS, gift_results)
        # L22 = SUM(L23:L34)
        assert result.total_profit == pytest.approx(2549877.944, abs=TOLERANCE)

    def test_avg_profit_rate(self, gift_results):
        result = calc_summary(ALL_GIFTS, gift_results)
        # H22 = L22 / K22
        assert result.avg_profit_rate == pytest.approx(0.1363, abs=RATE_TOLERANCE)


class TestSummaryZeroSales:
    """総売上0で損失がある場合の集計（Codexレビュー指摘の回帰防止）.

    売上0で粗利率を 0% と表示すると赤字が中立に見えるため、avg_profit_rate は
    None（計算不能）を返す。損失自体は total_profit に残る。
    """

    def test_avg_profit_rate_is_none_when_sales_zero(self):
        """全ギフト販売単価0なら平均粗利率は None で、損失は集計に残る."""
        from dataclasses import replace

        zero_gifts = [replace(g, selling_price=0.0) for g in ALL_GIFTS]
        item_results = {
            no: calc_single_item(it, COND_20FT) for no, it in ALL_ITEMS.items()
        }
        results = [
            calc_gift_set(g, ALL_ITEMS, item_results, COND_20FT) for g in zero_gifts
        ]
        summary = calc_summary(zero_gifts, results)

        assert summary.total_sales == 0.0
        # 損失は集計に残る（0 に消えない）
        assert summary.total_profit < 0
        # 粗利率は計算不能（0% と誤表示しない）
        assert summary.avg_profit_rate is None
