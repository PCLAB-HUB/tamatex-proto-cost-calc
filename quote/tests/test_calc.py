"""Excel Row 9（ダイカットメモ）の実値と計算結果を突合するテスト."""

from __future__ import annotations

import math

import pytest

from quote.engine.calc import (
    calc_b_grade_loss,
    calc_cif,
    calc_cnf,
    calc_container_expense_total,
    calc_container_expense_unit,
    calc_domestic_processing_unit,
    calc_fob_adjusted,
    calc_logistics_per_case,
    calc_logistics_unit,
    calc_product_cost,
    calc_purchase_price,
    calc_sub_material_cost,
    calc_tariff,
    calc_trial_price,
    calculate,
)
from quote.engine.models import ContainerExpenses, GlobalParams, ProductInput


@pytest.fixture
def row9_product() -> ProductInput:
    """Excel Row 9: ダイカットメモ."""
    return ProductInput(
        product_name="ダイカットメモ",
        prototype_code="1",
        package_size_cm="13*9.5*0.6cm",
        weight_g=41.0,
        packing_quantity=270,
        fob_usd=0.31,
        embroidery_per_1000=0.03,
        stitch_count=0.0,
        container_load=194318.4972702878,
        tariff_rate_override=0.0,
        quote_price=64.0,
        lot_per_color=10000,
        num_colors=1,
        retail_price=1200.0,
        logistics_io_fee=70.0,
        logistics_storage_months=1.0,
        logistics_storage_fee=150.0,
        logistics_slip_fee=100.0,
        logistics_freight=700.0,
        domestic_packing_qty=1,
    )


@pytest.fixture
def row9_params() -> GlobalParams:
    return GlobalParams(
        internal_rate=152.0,
        current_rate=152.0,
        overseas_freight_usd=240.0,
        cny_to_usd_rate=0.17,
        cny_to_jpy_rate=13.0,
        insurance_risk_rate=0.0018,
        tariff_rate=0.0,
        b_grade_loss_rate=0.01,
        sub_material_loss_rate=0.05,
        amortization_margin=0.05,
        margin=0.20,
        container_expenses=ContainerExpenses(
            cy_charge=30000.0,
            lss=0.0,
            lss_cic_usd=180.0,
            thc=36000.0,
            emc=3000.0,
            do_fee=5000.0,
            doc_fee=6000.0,
            customs_fee=11800.0,
            handling_fee=8000.0,
            drayage=50000.0,
            devanning=14000.0,
        ),
    )


class TestRow9Formulas:
    """Excel Row 9 の各数式を個別に検証."""

    def test_fob_adjusted(self, row9_product: ProductInput) -> None:
        """Z9 = 0.31 (加工賃・ロス・刺繍・型代すべて0)."""
        result = calc_fob_adjusted(row9_product, lot=10000)
        assert result == pytest.approx(0.31, abs=0.001)

    def test_cnf(
        self, row9_product: ProductInput, row9_params: GlobalParams
    ) -> None:
        """AM9 = 47.3077."""
        fob_adj = 0.31
        result = calc_cnf(row9_product, fob_adj, row9_params)
        assert result == pytest.approx(47.3077, abs=0.01)

    def test_cif(self) -> None:
        """AO9 = 47.3929."""
        result = calc_cif(47.3077, 0.0018)
        assert result == pytest.approx(47.3929, abs=0.01)

    def test_tariff_zero(self) -> None:
        """AQ9 = 0 (関税率0%)."""
        assert calc_tariff(47.3929, 0.0) == 0.0

    def test_purchase_price(self) -> None:
        """AR9 = 47.3929."""
        assert calc_purchase_price(47.3929, 0.0) == pytest.approx(47.3929, abs=0.01)

    def test_container_expense_total(self, row9_params: GlobalParams) -> None:
        """BD9 = 191160."""
        result = calc_container_expense_total(row9_params)
        assert result == pytest.approx(191160.0, abs=1.0)

    def test_container_expense_unit(self) -> None:
        """BE9 = 0.9837."""
        result = calc_container_expense_unit(191160.0, 194318.4972702878)
        assert result == pytest.approx(0.9837, abs=0.001)

    def test_b_grade_loss(self) -> None:
        """BG9 = 0.4838."""
        result = calc_b_grade_loss(47.3929, 0.9837, 0.01)
        assert result == pytest.approx(0.4838, abs=0.001)

    def test_sub_material_zero(self, row9_product: ProductInput) -> None:
        """BT9 = 0 (副資材すべて0)."""
        result = calc_sub_material_cost(
            row9_product, tariff_rate=0.0, sub_material_loss_rate=0.05
        )
        assert result == 0.0

    def test_logistics_per_case(self, row9_product: ProductInput) -> None:
        """CT9 = 1020."""
        result = calc_logistics_per_case(row9_product)
        assert result == pytest.approx(1020.0, abs=0.1)

    def test_logistics_unit(self) -> None:
        """CU9 = 3.7778."""
        result = calc_logistics_unit(1020.0, 270)
        assert result == pytest.approx(3.7778, abs=0.001)

    def test_domestic_processing_zero(self, row9_product: ProductInput) -> None:
        """DD9 = 0 (国内加工なし)."""
        result = calc_domestic_processing_unit(row9_product)
        assert result == pytest.approx(0.0, abs=0.001)

    def test_product_cost(self) -> None:
        """DE9 = 52.638."""
        result = calc_product_cost(
            purchase_price=47.3929,
            container_expense_unit=0.9837,
            b_grade_loss=0.4838,
            sub_material_cost=0.0,
            amortization_actual=0.0,
            logistics_unit=3.7778,
            domestic_processing_unit=0.0,
        )
        assert result == pytest.approx(52.638, abs=0.1)

    def test_trial_price(self) -> None:
        """DG9 = 64 = ROUNDUP(52.638 * 1.2)."""
        result = calc_trial_price(52.638, 0.20)
        assert result == 64


class TestSubMaterialLossRate:
    """副資材ロス率(BS列)がFOBロス率(U列)と混同されないことを検証."""

    def test_sub_material_with_values(self) -> None:
        """副資材に値がある場合、BS=0.05が適用される."""
        product = ProductInput(ribbon=10.0, tag=5.0)
        result = calc_sub_material_cost(
            product, tariff_rate=0.08, sub_material_loss_rate=0.05
        )
        expected = (10.0 + 5.0) * (1 + 0.08) * (1 + 0.05)
        assert result == pytest.approx(expected, abs=0.01)

    def test_sub_material_uses_correct_rate(self) -> None:
        """product.loss_rate(U列)ではなくsub_material_loss_rate(BS列)を使う."""
        product = ProductInput(ribbon=100.0, loss_rate=0.0)
        with_correct = calc_sub_material_cost(product, 0.0, sub_material_loss_rate=0.05)
        assert with_correct == pytest.approx(105.0, abs=0.01)


class TestRow10EndToEnd:
    """Excel Row 10 (PVCバッグ, 関税8%) の一気通貫検証."""

    def test_full_calculation(self) -> None:
        product = ProductInput(
            product_name="PVCバッグ+メモカード",
            fob_usd=0.20,
            embroidery_per_1000=0.03,
            packing_quantity=640,
            container_load=251354.6285093442,
            tariff_rate_override=0.08,
            quote_price=44.0,
            lot_per_color=10000,
            num_colors=1,
            retail_price=500.0,
            logistics_io_fee=70.0,
            logistics_storage_months=1.0,
            logistics_storage_fee=150.0,
            logistics_slip_fee=100.0,
            logistics_freight=1170.0,
        )
        params = GlobalParams(
            internal_rate=152.0,
            current_rate=152.0,
            overseas_freight_usd=240.0,
            cny_to_usd_rate=0.17,
            cny_to_jpy_rate=13.0,
            insurance_risk_rate=0.0018,
            tariff_rate=0.08,
            b_grade_loss_rate=0.01,
            sub_material_loss_rate=0.05,
            amortization_margin=0.05,
            margin=0.20,
        )
        result = calculate(product, params)

        assert result.cost.purchase_price == pytest.approx(33.048, abs=0.01)
        assert result.cost.product_cost == pytest.approx(36.475, abs=0.1)
        assert result.pricing_with_amort.trial_price == 44
        assert result.pricing_with_amort.gross_profit_unit == pytest.approx(7.525, abs=0.1)
        assert result.pricing_with_amort.gross_profit_rate == pytest.approx(0.171, abs=0.005)


class TestRow9EndToEnd:
    """calculate() で Row 9 全体を一気通貫で検証."""

    def test_full_calculation(
        self, row9_product: ProductInput, row9_params: GlobalParams
    ) -> None:
        result = calculate(row9_product, row9_params)

        # 原価
        assert result.cost.product_cost == pytest.approx(52.638, abs=0.1)
        # 試算売価
        assert result.pricing_with_amort.trial_price == 64
        # 粗利額
        assert result.pricing_with_amort.gross_profit_unit == pytest.approx(
            11.362, abs=0.1
        )
        # 粗利率
        assert result.pricing_with_amort.gross_profit_rate == pytest.approx(
            0.1775, abs=0.005
        )
        # 売上金額
        assert result.pricing_with_amort.sales_amount == pytest.approx(
            640000.0, abs=100.0
        )
        # 粗利金額
        assert result.pricing_with_amort.gross_profit_total == pytest.approx(
            113618.0, abs=100.0
        )
