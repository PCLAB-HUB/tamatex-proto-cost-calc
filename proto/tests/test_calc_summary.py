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
