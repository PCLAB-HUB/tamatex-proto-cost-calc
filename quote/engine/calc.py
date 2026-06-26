"""ステーショナリー見積もり — 原価計算エンジン.

原価計算書参考資料.xlsx の数式を Python に忠実変換する。
全関数は純粋関数（副作用なし）。
"""

from __future__ import annotations

import math

from quote.engine.models import (
    CostBreakdown,
    GlobalParams,
    PricingResult,
    ProductInput,
    QuoteResult,
)


def _effective_tariff(product: ProductInput, params: GlobalParams) -> float:
    if product.tariff_rate_override is not None:
        return product.tariff_rate_override
    return params.tariff_rate


def calc_fob_adjusted(product: ProductInput, lot: int) -> float:
    """Z列: FOB調整後(USD) = (S+T)*(1+U)+V+(W*X/1000)+Y/DM."""
    base = (product.fob_usd + product.other_processing_usd) * (1 + product.loss_rate)
    charge = product.charge_up_unit
    embroidery = product.embroidery_per_1000 * product.stitch_count / 1000
    die = product.die_charge / lot if lot > 0 else 0.0
    return base + charge + embroidery + die


def calc_cnf(
    product: ProductInput,
    fob_adjusted: float,
    params: GlobalParams,
) -> float:
    """AM列: C&F(円).

    = Z*AJ + (AA+AB+AC) + (AD+AE+AF)*(1+元ドル率)*元円率
      + (AG+AH+AI)*AJ + (AL/R)*AK
    """
    rate = params.internal_rate

    usd_part = fob_adjusted * rate
    jpy_part = product.inspection_jpy + product.packing_jpy + product.material_jpy
    cny_part = (
        (product.inspection_cny + product.packing_cny + product.material_cny)
        * (1 + params.cny_to_usd_rate)
        * params.cny_to_jpy_rate
    )
    usd_insp = (
        product.inspection_usd + product.packing_usd + product.material_usd
    ) * rate

    freight_per_unit = 0.0
    if product.container_load > 0:
        freight_per_unit = (
            params.overseas_freight_usd / product.container_load
        ) * params.current_rate

    return usd_part + jpy_part + cny_part + usd_insp + freight_per_unit


def calc_cif(cnf: float, insurance_rate: float) -> float:
    """AO列: CIF = C&F * (1 + 保険率)."""
    return cnf * (1 + insurance_rate)


def calc_tariff(cif: float, tariff_rate: float) -> float:
    """AQ列: 関税 = CIF * 関税率."""
    return cif * tariff_rate


def calc_purchase_price(cif: float, tariff: float) -> float:
    """AR列: 仕入値 = CIF + 関税."""
    return cif + tariff


def calc_container_expense_total(
    params: GlobalParams,
) -> float:
    """BD列: コンテナ経費合計.

    = AS + AT + AU*AK + AV + AW + AX + AY + AZ + BA + BB + BC
    """
    ce = params.container_expenses
    return (
        ce.cy_charge
        + ce.lss
        + ce.lss_cic_usd * params.current_rate
        + ce.thc
        + ce.emc
        + ce.do_fee
        + ce.doc_fee
        + ce.customs_fee
        + ce.handling_fee
        + ce.drayage
        + ce.devanning
    )


def calc_container_expense_unit(
    container_total: float, container_load: float
) -> float:
    """BE列: コンテナ経費/枚 = BD / R."""
    if container_load <= 0:
        return 0.0
    return container_total / container_load


def calc_b_grade_loss(
    purchase_price: float,
    container_expense_unit: float,
    loss_rate: float,
) -> float:
    """BG列: B品ロス = (仕入値 + 経費/枚) * ロス率."""
    return (purchase_price + container_expense_unit) * loss_rate


def calc_sub_material_cost(product: ProductInput, tariff_rate: float) -> float:
    """BT列: 副資材経費.

    BQ = SUM(BH:BP)
    BR = AP (関税率)
    BT = BQ * (1+BR) * (1+BS)
    """
    total = (
        product.ribbon
        + product.name_label_2
        + product.name_label_3
        + product.seal_1
        + product.seal_2
        + product.tag
        + product.bag
        + product.other_material
        + product.material_freight
    )
    return total * (1 + tariff_rate) * (1 + product.loss_rate)


def calc_amortization_per_unit(product: ProductInput, lot: int) -> float:
    """CK列: 償却経費/枚 (実額).

    = (BU+BV+BW+BZ+CA+CB+CC+CD+CE+CF+CG+CH+CI+CJ) / DM
    BZ = BX * BY (プリント型代 = 単価 × 型数)
    """
    if lot <= 0:
        return 0.0
    print_cost = product.print_unit_price * product.print_type_count
    total = (
        product.design_cost
        + product.jq_card
        + product.embroidery_card
        + print_cost
        + product.print_mold
        + product.layout
        + product.name_plate
        + product.seal_plate
        + product.tab_plate
        + product.bag_plate
        + product.cardboard_plate
        + product.other_depreciation
        + product.sample_cost
        + product.quality_inspection
        + product.other_amortization
    )
    return total / lot


def calc_amortization_with_margin(actual: float, margin: float) -> float:
    """CM列: 償却経費マージン込み = CK * (1 + CL)."""
    return actual * (1 + margin)


def calc_logistics_per_case(product: ProductInput) -> float:
    """CT列: 物流経費/ケース.

    = CN + CO + CP*CQ + CR + CS
    """
    return (
        product.logistics_cardboard
        + product.logistics_io_fee
        + product.logistics_storage_months * product.logistics_storage_fee
        + product.logistics_slip_fee
        + product.logistics_freight
    )


def calc_logistics_unit(logistics_per_case: float, packing_qty: int) -> float:
    """CU列: 物流経費/枚 = CT / P."""
    if packing_qty <= 0:
        return 0.0
    return logistics_per_case / packing_qty


def calc_domestic_processing_unit(product: ProductInput) -> float:
    """DD列: 国内加工経費/枚.

    = CW + CX + (CY + CZ + DA*DB + DC) / CV
    """
    case_costs = (
        product.domestic_cardboard
        + product.domestic_io
        + product.domestic_storage_months * product.domestic_storage_fee
        + product.domestic_freight
    )
    per_unit_costs = product.domestic_processing + product.domestic_material
    divisor = product.domestic_packing_qty if product.domestic_packing_qty > 0 else 1
    return per_unit_costs + case_costs / divisor


def calc_product_cost(
    purchase_price: float,
    container_expense_unit: float,
    b_grade_loss: float,
    sub_material_cost: float,
    amortization_actual: float,
    logistics_unit: float,
    domestic_processing_unit: float,
) -> float:
    """DE列: 製品原価.

    = AR + BE + BG + BT + CK + CU + DD
    """
    return (
        purchase_price
        + container_expense_unit
        + b_grade_loss
        + sub_material_cost
        + amortization_actual
        + logistics_unit
        + domestic_processing_unit
    )


def calc_trial_price(product_cost: float, margin: float) -> float:
    """DG列: 試算売価 = ROUNDUP(原価 * (1+マージン))."""
    return math.ceil(product_cost * (1 + margin))


def calc_pricing(
    product_cost: float,
    margin_rate: float,
    quote_price: float,
    center_fee: float,
    rebate: float,
    lot: int,
    retail_price: float,
) -> PricingResult:
    """DE〜DU列（またはDW〜EN列）の価格計算一式."""
    trial = calc_trial_price(product_cost, margin_rate)
    stepped = quote_price / (1 - center_fee - rebate) if (1 - center_fee - rebate) > 0 else 0.0
    retail_ratio = stepped / retail_price if retail_price > 0 else 0.0
    sales_amount = lot * stepped
    gross_unit = quote_price - product_cost
    gross_rate = gross_unit / quote_price if quote_price > 0 else 0.0
    gross_total = lot * gross_unit

    return PricingResult(
        product_cost=product_cost,
        margin_rate=margin_rate,
        trial_price=trial,
        quote_price=quote_price,
        center_fee=center_fee,
        rebate=rebate,
        lot=lot,
        stepped_price=stepped,
        retail_price=retail_price,
        retail_ratio=retail_ratio,
        sales_amount=sales_amount,
        gross_profit_unit=gross_unit,
        gross_profit_rate=gross_rate,
        gross_profit_total=gross_total,
    )


def calculate(product: ProductInput, params: GlobalParams) -> QuoteResult:
    """商品1点の見積もり計算を実行する（メインAPI）."""
    tariff_rate = _effective_tariff(product, params)
    lot = product.lot_per_color * product.num_colors

    # --- 原価積み上げ ---
    fob_adj = calc_fob_adjusted(product, lot)
    cnf = calc_cnf(product, fob_adj, params)
    cif = calc_cif(cnf, params.insurance_risk_rate)
    tariff = calc_tariff(cif, tariff_rate)
    purchase = calc_purchase_price(cif, tariff)

    ct_total = calc_container_expense_total(params)
    ct_unit = calc_container_expense_unit(ct_total, product.container_load)

    b_loss = calc_b_grade_loss(purchase, ct_unit, params.b_grade_loss_rate)

    sub_mat = calc_sub_material_cost(product, tariff_rate)

    amort_actual = calc_amortization_per_unit(product, lot)
    amort_margin = calc_amortization_with_margin(
        amort_actual, params.amortization_margin
    )

    logi_case = calc_logistics_per_case(product)
    logi_unit = calc_logistics_unit(logi_case, product.packing_quantity)

    domestic = calc_domestic_processing_unit(product)

    cost = calc_product_cost(
        purchase, ct_unit, b_loss, sub_mat, amort_actual, logi_unit, domestic
    )

    breakdown = CostBreakdown(
        fob_adjusted_usd=fob_adj,
        cnf_jpy=cnf,
        cif_jpy=cif,
        tariff_jpy=tariff,
        purchase_price=purchase,
        container_expense_total=ct_total,
        container_expense_unit=ct_unit,
        b_grade_loss=b_loss,
        sub_material_cost=sub_mat,
        amortization_actual=amort_actual,
        amortization_with_margin=amort_margin,
        logistics_per_case=logi_case,
        logistics_unit=logi_unit,
        domestic_processing_unit=domestic,
        product_cost=cost,
    )

    # --- 価格体系1: 償却込み (DE-DU列) ---
    pricing_with = calc_pricing(
        product_cost=cost,
        margin_rate=params.margin,
        quote_price=product.quote_price,
        center_fee=product.center_fee,
        rebate=product.rebate,
        lot=lot,
        retail_price=product.retail_price,
    )

    # --- 価格体系2: 償却別途 (DW-EN列) ---
    cost_ex_amort = cost - amort_actual
    amort_separate = 0.0
    rebate_ex = product.rebate_ex_amort
    if (1 - rebate_ex) > 0:
        amort_separate = math.ceil(
            amort_margin / (1 - rebate_ex)
        ) if amort_margin > 0 else 0.0

    pricing_without = calc_pricing(
        product_cost=cost_ex_amort,
        margin_rate=params.margin,
        quote_price=product.quote_price_ex_amort,
        center_fee=product.center_fee_ex_amort,
        rebate=rebate_ex,
        lot=lot,
        retail_price=product.retail_price_ex_amort,
    )

    return QuoteResult(
        cost=breakdown,
        pricing_with_amort=pricing_with,
        pricing_without_amort=pricing_without,
        amortization_separate=amort_separate,
    )
