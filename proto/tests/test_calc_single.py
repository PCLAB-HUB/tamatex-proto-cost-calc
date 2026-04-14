"""単品原価計算のテスト — Excel実値との照合.

検証基準: ±0.01円以内の一致。
Excel値はdata_only=Trueで取得した計算済み値。
"""

import pytest

from proto.data.mock_items import ITEM_01, ITEM_02, ITEM_03, ITEM_04, ITEM_05, ITEM_06
from proto.data.mock_params import COND_20FT
from proto.engine.calc_single import calc_single_item

TOLERANCE = 0.01  # 許容誤差(円)


class TestSingleItem01_OsdMocoBT:
    """① OSD-MOCO BT (行7) — 20FT条件.

    Excel実値:
      M=570, N=636.63149, BE=570, BG=572.175, BI=573.204915,
      BK=42.34095, BZ=11034.48, CA=197800, CB=17.9256, CP=3.16
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.result = calc_single_item(ITEM_01, COND_20FT)

    def test_fob_jpy(self):
        assert self.result.fob_jpy == pytest.approx(570.0, abs=TOLERANCE)

    def test_manufacturing_cost(self):
        assert self.result.manufacturing_cost == pytest.approx(570.0, abs=TOLERANCE)

    def test_cnf(self):
        assert self.result.cnf == pytest.approx(572.175, abs=TOLERANCE)

    def test_cif(self):
        assert self.result.cif == pytest.approx(573.205, abs=TOLERANCE)

    def test_tariff(self):
        assert self.result.tariff == pytest.approx(42.341, abs=TOLERANCE)

    def test_loaded_pcs(self):
        assert self.result.loaded_pcs == pytest.approx(11034.483, abs=0.01)

    def test_import_cost_total(self):
        assert self.result.import_cost_total == pytest.approx(197800.0, abs=1.0)

    def test_import_cost_unit(self):
        assert self.result.import_cost_unit == pytest.approx(17.926, abs=TOLERANCE)

    def test_logistics_cost(self):
        # CP = (111+12+3+70+120*1)/100 = 316/100 = 3.16
        assert self.result.logistics_cost == pytest.approx(3.16, abs=TOLERANCE)

    def test_jpy_cost(self):
        # N = BI + BK + CB + CP + BB = 573.205 + 42.341 + 17.926 + 3.16 + 0
        assert self.result.jpy_cost == pytest.approx(636.631, abs=TOLERANCE)


class TestSingleItem03_OsdMocoFT:
    """③ OSD-MOCO FT (行9) — 20FT条件.

    Excel実値:
      M=243, N=282.3837, BE=243, CB=18.54375, CP=0
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.result = calc_single_item(ITEM_03, COND_20FT)

    def test_fob_jpy(self):
        assert self.result.fob_jpy == pytest.approx(243.0, abs=TOLERANCE)

    def test_manufacturing_cost(self):
        assert self.result.manufacturing_cost == pytest.approx(243.0, abs=TOLERANCE)

    def test_cif(self):
        assert self.result.cif == pytest.approx(245.691, abs=TOLERANCE)

    def test_tariff(self):
        assert self.result.tariff == pytest.approx(18.149, abs=TOLERANCE)

    def test_import_cost_unit(self):
        assert self.result.import_cost_unit == pytest.approx(18.544, abs=TOLERANCE)

    def test_logistics_cost(self):
        assert self.result.logistics_cost == pytest.approx(0.0, abs=TOLERANCE)

    def test_jpy_cost(self):
        assert self.result.jpy_cost == pytest.approx(282.384, abs=TOLERANCE)


class TestSingleItem04_OsdFuwaFT:
    """④ OSD-FUWA FT (行10) — 20FT条件.

    Excel実値:
      M=201, N=244.1882, CB=24.725, CP=0
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.result = calc_single_item(ITEM_04, COND_20FT)

    def test_fob_jpy(self):
        assert self.result.fob_jpy == pytest.approx(201.0, abs=TOLERANCE)

    def test_manufacturing_cost(self):
        assert self.result.manufacturing_cost == pytest.approx(201.0, abs=TOLERANCE)

    def test_cif(self):
        assert self.result.cif == pytest.approx(204.367, abs=TOLERANCE)

    def test_tariff(self):
        assert self.result.tariff == pytest.approx(15.096, abs=TOLERANCE)

    def test_import_cost_unit(self):
        assert self.result.import_cost_unit == pytest.approx(24.725, abs=TOLERANCE)

    def test_jpy_cost(self):
        assert self.result.jpy_cost == pytest.approx(244.188, abs=TOLERANCE)


class TestSingleItemNoWeight:
    """目方なし品目（②⑤⑥）— 積載数ゼロでC&F以降ゼロ."""

    def test_item02_loaded_pcs_zero(self):
        result = calc_single_item(ITEM_02, COND_20FT)
        assert result.loaded_pcs == 0.0
        assert result.cnf == result.fob_jpy  # 運賃加算なし
        assert result.import_cost_unit == 0.0
        # M = FOB(円) = 3.21 × 150 = 481.5
        assert result.manufacturing_cost == pytest.approx(481.5, abs=TOLERANCE)

    def test_item05_loaded_pcs_zero(self):
        result = calc_single_item(ITEM_05, COND_20FT)
        assert result.loaded_pcs == 0.0
        assert result.manufacturing_cost == pytest.approx(462.0, abs=TOLERANCE)

    def test_item06_loaded_pcs_zero(self):
        result = calc_single_item(ITEM_06, COND_20FT)
        assert result.loaded_pcs == 0.0
        assert result.manufacturing_cost == pytest.approx(142.5, abs=TOLERANCE)
