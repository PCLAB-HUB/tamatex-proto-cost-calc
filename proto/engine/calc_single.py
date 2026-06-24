"""単品タオルの原価計算.

Excelの「ひな形」シート上段（行7-16）の計算ロジック。
各計算式はExcel列との対応をコメントで明記。

計算チェーン:
  資材代(AB) → トレス(AS) → 償却費(BC,BB) → FOB円(BE)
  → 積載(BZ,BY) → C&F(BG) → CIF(BI) → 関税(BK)
  → 輸入経費(CA,CB) → 物流(CP)
  → 製造原価(M) / 円建原価(N)

Excel式の為替参照:
  BG7: BE7 + (BF7/BZ7) × $N$4  ← $N$4 = 現行為替
  CA7: BO7 × $N$4 + BM7 + ...  ← $N$4 = 現行為替
  BK7: ((...) × $N$4 + ...) × BJ7
"""

from __future__ import annotations

from proto.engine.calc_import import (
    calc_import_cost_total,
    calc_import_cost_unit,
    calc_logistics_cost,
)
from proto.engine.models import ImportCondition, SingleItem, SingleItemResult


# 20FTコンテナの基準容積（固定値）
CONTAINER_20FT_CAPACITY = 3_200_000.0


def calc_single_item(item: SingleItem, cond: ImportCondition) -> SingleItemResult:
    """単品タオルの原価計算.

    Args:
        item: 単品データ
        cond: 輸入条件パラメータ

    Returns:
        全中間値を含む計算結果
    """
    loss_rate = cond.loss_rate_pct / 100.0  # AB4 = Z4/100

    # --- AB列: 日本支給資材 ---
    # AB = (X + Y + Z + AA) × (1 + ロス率)
    material_cost = (
        (item.name_label_1 + item.name_label_2 + item.seal + item.other_material)
        * (1.0 + loss_rate)
    )

    # --- AS列: トレス小計 ---
    # AS = AQ × AR
    trace_subtotal = item.trace_price * item.trace_count

    # --- BC列: 償却費合計 ---
    # BC = AT + AU + AV + AS + AW + AX + AY + AZ + BA
    depreciation_total = (
        item.design_cost
        + item.jq_card
        + item.embroidery_card
        + trace_subtotal
        + item.sample_cost
        + item.inspection_cost
        + item.material_plate_1
        + item.material_plate_2
        + item.material_plate_3
    )

    # --- BB列: 償却費/枚 ---
    # BB = BC / L
    depreciation_per_unit = depreciation_total / item.lot if item.lot > 0 else 0.0

    # --- BE列: FOB(円) ---
    # BE = (P + (R/1000 × R4) + S + T/L + U) × 社内為替 + V + W + AB
    fob_usd_total = (
        item.fob_usd
        + (item.embroidery_needles / 1000.0) * cond.emb_general
        + item.silver_embroidery
        + (item.ket_embroidery / item.lot if item.lot > 0 else 0.0)
        + item.brand_logo
    )
    fob_jpy = (
        fob_usd_total * cond.internal_rate
        + item.inspection
        + item.other_processing
        + material_cost
    )

    # --- BZ列: 積載個数 ---
    # BZ = 3,200,000 / G (目方なし=0)
    if item.weight_g and item.weight_g > 0:
        loaded_pcs = CONTAINER_20FT_CAPACITY / item.weight_g
    else:
        loaded_pcs = 0.0

    # --- BY列: 積載ケース数 ---
    # BY = BZ / BX
    if item.logistics_pcs_per_case > 0 and loaded_pcs > 0:
        loaded_cases = loaded_pcs / item.logistics_pcs_per_case
    else:
        loaded_cases = 0.0

    # --- BG列: C&F ---
    # BG = BE + (BF / BZ) × $N$4(現行為替)
    if loaded_pcs > 0:
        freight_per_unit = (cond.overseas_freight_usd / loaded_pcs) * cond.current_rate
    else:
        freight_per_unit = 0.0
    cnf = fob_jpy + freight_per_unit

    # --- BI列: CIF ---
    # BI = BG × (1 + 保険率)
    cif = cnf * (1.0 + cond.insurance_rate)

    # --- BK列: 関税 ---
    # BK = ((P+(R/1000)×R4+S+T/L+U+BF/BZ)×$N$4+V+W+AB) × BJ
    if loaded_pcs > 0:
        freight_per_unit_for_tariff = cond.overseas_freight_usd / loaded_pcs
    else:
        freight_per_unit_for_tariff = 0.0

    tariff_base = (
        (fob_usd_total + freight_per_unit_for_tariff) * cond.current_rate
        + item.inspection
        + item.other_processing
        + material_cost
    )
    tariff = tariff_base * cond.tariff_rate

    # --- CA列: 輸入経費合計(コンテナ) ---
    # 単品層: BO × $N$4(現行為替) + BM + BN + ...
    import_cost_total = calc_import_cost_total(
        cond.import_expenses_single, cond.current_rate
    )

    # --- CB列: 輸入経費単価 ---
    # CB = CA / BZ
    import_cost_unit = calc_import_cost_unit(import_cost_total, loaded_pcs)

    # --- CP列: 物流経費 ---
    # CP = (CI + CJ + CK + CL + CM×CN) / CO
    logistics_cost = calc_logistics_cost(
        freight_per_case=item.logistics_freight,
        packing_cost=item.logistics_packing,
        other_logistics=item.logistics_other,
        cl=cond.logistics_single.io_fee,
        cm=cond.logistics_single.storage_fee,
        cn=cond.logistics_single.storage_months,
        pcs_per_case=item.logistics_pcs_per_case,
    )

    # --- M列: 製造原価(円) ---
    # M = BE + BB (FOB円 + 償却費/枚)
    # 注: V,W,ABは既にBEに含まれている
    manufacturing_cost = fob_jpy + depreciation_per_unit

    # --- N列: 円建原価 ---
    # N = BI + BK + CB + CP + BB
    jpy_cost = cif + tariff + import_cost_unit + logistics_cost + depreciation_per_unit

    return SingleItemResult(
        material_cost=material_cost,
        trace_subtotal=trace_subtotal,
        depreciation_total=depreciation_total,
        depreciation_per_unit=depreciation_per_unit,
        fob_jpy=fob_jpy,
        loaded_pcs=loaded_pcs,
        loaded_cases=loaded_cases,
        cnf=cnf,
        cif=cif,
        tariff=tariff,
        import_cost_total=import_cost_total,
        import_cost_unit=import_cost_unit,
        logistics_cost=logistics_cost,
        manufacturing_cost=manufacturing_cost,
        jpy_cost=jpy_cost,
    )
