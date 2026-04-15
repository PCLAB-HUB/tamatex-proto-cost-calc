"""ギフトセット原価計算のテスト — Excel実値との照合.

検証基準: ±0.01円以内の一致（粗利率は±0.001以内）。
全12パターン × 20FT条件で検証。
"""

import pytest

from proto.data.mock_gifts import ALL_GIFTS
from proto.data.mock_items import ALL_ITEMS
from proto.data.mock_params import COND_20FT
from proto.engine.calc_gift import calc_gift_set
from proto.engine.calc_single import calc_single_item

TOLERANCE = 0.01       # 円の許容誤差
RATE_TOLERANCE = 0.001  # 率の許容誤差


@pytest.fixture(scope="module")
def item_results():
    """全単品の計算結果を事前計算."""
    return {
        item_no: calc_single_item(item, COND_20FT)
        for item_no, item in ALL_ITEMS.items()
    }


# Excel実値テーブル（20FT条件）
# (name, P(製造原価), M(見積), H(粗利率), BE(FOB), BI(CIF), BK(関税), CB(輸入単価), CP(物流))
EXPECTED_VALUES = [
    ("FT2 もこ",       1120.064, 1569, 0.1344, 897.165,  906.794,  67.103,  65.667, 80.5),
    ("FT2 ふわ",       1029.685, 1442, 0.1347, 813.165,  822.643,  60.876,  65.667, 80.5),
    ("FT1MT4 もこ",    1499.524, 2100, 0.1332, 1249.845, 1260.109, 93.248,  65.667, 80.5),
    ("FT1MT4 ふわ",    1454.335, 2037, 0.1333, 1207.845, 1218.034, 90.134,  65.667, 80.5),
    ("BT1 もこ",       1167.464, 1635, 0.1403, 941.220,  950.929,  70.369,  65.667, 80.5),
    ("BT1 ふわ",       1072.244, 1502, 0.1346, 852.720,  862.269,  63.808,  65.667, 80.5),
    ("BT1FT2 もこ",    2172.570, 3042, 0.1386, 1659.615, 1682.638, 124.515, 164.167, 201.25),
    ("BT1FT2 ふわ",    1986.972, 2782, 0.1354, 1487.115, 1509.828, 111.727, 164.167, 201.25),
    ("BT1FT1BM1 もこ", 2404.972, 3367, 0.1377, 1875.615, 1899.027, 140.528, 164.167, 201.25),
    ("BT1BM2 もこ",    2637.373, 3693, 0.1370, 2091.615, 2115.416, 156.541, 164.167, 201.25),
    ("BT2 もこ",       2224.812, 3115, 0.1417, 1708.170, 1731.281, 128.115, 164.167, 201.25),
    ("BT2 ふわ",       2034.372, 2849, 0.1350, 1531.170, 1553.962, 114.993, 164.167, 201.25),
]


class TestGiftSetAll20FT:
    """全12ギフトパターンの20FT条件テスト."""

    @pytest.fixture(autouse=True)
    def setup(self, item_results):
        self.results = []
        for gift in ALL_GIFTS:
            result = calc_gift_set(gift, ALL_ITEMS, item_results, COND_20FT)
            self.results.append(result)

    @pytest.mark.parametrize(
        "idx",
        range(12),
        ids=[e[0] for e in EXPECTED_VALUES],
    )
    def test_manufacturing_cost(self, idx):
        expected = EXPECTED_VALUES[idx]
        assert self.results[idx].manufacturing_cost == pytest.approx(
            expected[1], abs=TOLERANCE
        ), f"{expected[0]}: P(製造原価)"

    @pytest.mark.parametrize(
        "idx",
        range(12),
        ids=[e[0] for e in EXPECTED_VALUES],
    )
    def test_quote_price(self, idx):
        expected = EXPECTED_VALUES[idx]
        assert self.results[idx].quote_price == expected[2], f"{expected[0]}: M(見積)"

    @pytest.mark.parametrize(
        "idx",
        range(12),
        ids=[e[0] for e in EXPECTED_VALUES],
    )
    def test_gross_profit_rate(self, idx):
        expected = EXPECTED_VALUES[idx]
        assert self.results[idx].gross_profit_rate == pytest.approx(
            expected[3], abs=RATE_TOLERANCE
        ), f"{expected[0]}: H(粗利率)"

    @pytest.mark.parametrize(
        "idx",
        range(12),
        ids=[e[0] for e in EXPECTED_VALUES],
    )
    def test_fob_total(self, idx):
        expected = EXPECTED_VALUES[idx]
        assert self.results[idx].fob_total == pytest.approx(
            expected[4], abs=TOLERANCE
        ), f"{expected[0]}: BE(FOB)"

    @pytest.mark.parametrize(
        "idx",
        range(12),
        ids=[e[0] for e in EXPECTED_VALUES],
    )
    def test_cif(self, idx):
        expected = EXPECTED_VALUES[idx]
        assert self.results[idx].cif == pytest.approx(
            expected[5], abs=TOLERANCE
        ), f"{expected[0]}: BI(CIF)"

    @pytest.mark.parametrize(
        "idx",
        range(12),
        ids=[e[0] for e in EXPECTED_VALUES],
    )
    def test_tariff(self, idx):
        expected = EXPECTED_VALUES[idx]
        assert self.results[idx].tariff == pytest.approx(
            expected[6], abs=TOLERANCE
        ), f"{expected[0]}: BK(関税)"

    @pytest.mark.parametrize(
        "idx",
        range(12),
        ids=[e[0] for e in EXPECTED_VALUES],
    )
    def test_import_cost_unit(self, idx):
        expected = EXPECTED_VALUES[idx]
        assert self.results[idx].import_cost_unit == pytest.approx(
            expected[7], abs=TOLERANCE
        ), f"{expected[0]}: CB(輸入単価)"

    @pytest.mark.parametrize(
        "idx",
        range(12),
        ids=[e[0] for e in EXPECTED_VALUES],
    )
    def test_logistics_cost(self, idx):
        expected = EXPECTED_VALUES[idx]
        assert self.results[idx].logistics_cost == pytest.approx(
            expected[8], abs=TOLERANCE
        ), f"{expected[0]}: CP(物流)"


class TestGiftSetSpecificValues:
    """個別ギフトの中間値テスト."""

    def test_ft2_moko_towel_cost(self, item_results):
        """FT2もこ: タオル代 = ③製造原価(243) × 2 = 486"""
        result = calc_gift_set(ALL_GIFTS[0], ALL_ITEMS, item_results, COND_20FT)
        assert result.towel_cost == pytest.approx(486.0, abs=TOLERANCE)

    def test_ft2_moko_material_cost(self, item_results):
        """FT2もこ: 資材代 = 355.5 × 1.03 + 0 = 366.165"""
        result = calc_gift_set(ALL_GIFTS[0], ALL_ITEMS, item_results, COND_20FT)
        assert result.material_cost == pytest.approx(366.165, abs=TOLERANCE)

    def test_ft2_moko_processing_cost(self, item_results):
        """FT2もこ: 加工代 = 45"""
        result = calc_gift_set(ALL_GIFTS[0], ALL_ITEMS, item_results, COND_20FT)
        assert result.processing_cost == pytest.approx(45.0, abs=TOLERANCE)

    def test_ft2_moko_loaded_pcs(self, item_results):
        """FT2もこ: BZ = 20 × 150 = 3000"""
        result = calc_gift_set(ALL_GIFTS[0], ALL_ITEMS, item_results, COND_20FT)
        assert result.loaded_pcs == 3000

    def test_bt1ft2_moko_loaded_pcs(self, item_results):
        """BT1FT2もこ: BZ = 8 × 150 = 1200"""
        result = calc_gift_set(ALL_GIFTS[6], ALL_ITEMS, item_results, COND_20FT)
        assert result.loaded_pcs == 1200
