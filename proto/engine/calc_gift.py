"""ギフトセットの原価計算.

Excelの「ひな形」シート下段（行23-42 / 行49-68）の計算ロジック。

計算チェーン:
  タオル代(AB) → 償却単価(AZ) → 資材代計(BC) → 加工代計(CG) → FOB合計(BE)
  → 積載(BZ) → C&F(BG) → CIF(BI) → 関税(BK)
  → 輸入経費(CA,CB) → 物流(CP)
  → 製造原価(P) → 見積単価(M) → 粗利(G,H)

Excel式の為替参照:
  BG23: BE23 + (BF23/BZ23) × $N$4  ← 現行為替
  CA23: BO23 × $M$4 + ...           ← 社内為替（単品層と異なる）
  BK23: BI23 × BJ23                 ← CIF × 関税率（単品層より単純）
"""

from __future__ import annotations

from proto.engine.calc_import import (
    calc_import_cost_total,
    calc_import_cost_unit,
    calc_logistics_cost,
)
from proto.engine.models import (
    GiftSet,
    GiftSetResult,
    ImportCondition,
    SingleItem,
    SingleItemResult,
)
from proto.engine.rounding import roundup_yen


def calc_gift_set(
    gift: GiftSet,
    items: dict[str, SingleItem],
    item_results: dict[str, SingleItemResult],
    cond: ImportCondition,
) -> GiftSetResult:
    """ギフトセットの原価計算.

    Args:
        gift: ギフトセットデータ
        items: 単品品番→SingleItemの辞書
        item_results: 単品品番→SingleItemResultの辞書
        cond: 輸入条件パラメータ

    Returns:
        全中間値を含む計算結果
    """
    margin_rate = cond.margin_pct / 100.0  # N22 = N20/100
    material_loss_rate = cond.material_loss_pct / 100.0  # BB22 = BB20/100

    # --- AB列: タオル代 ---
    # AB = Σ(単品i製造原価 × 使用枚数i), i=①〜⑩
    # Excel式: $R$22*R23 + $S$22*S23 + ... + $AA$22*AA23
    towel_cost = 0.0
    breakdown_qty: dict[str, int] = {}
    for comp in gift.composition:
        if comp.item_no not in item_results:
            raise ValueError(
                f"ギフト'{gift.name}'の構成品番'{comp.item_no}'が単品計算結果に見つかりません"
            )
        item_result = item_results[comp.item_no]
        towel_cost += item_result.manufacturing_cost * comp.quantity
        # 分解数 = 販売数量 × 使用枚数
        breakdown_qty[comp.item_no] = gift.sales_quantity * comp.quantity

    # --- AZ列: 償却単価 ---
    # AZ = (AV + AW + AX + AY) / BA(資材ロット)
    depreciation_total = (
        gift.design_cost
        + gift.wooden_mold
        + gift.plate_cost
        + gift.other_depreciation
    )
    if cond.material_lot > 0:
        depreciation_unit = depreciation_total / cond.material_lot
    else:
        depreciation_unit = 0.0

    # --- BC列: 資材代計 ---
    # BC = (AO+AP+AQ+AR+AS+AT+AU) × (1+資材ロス率) + AZ
    material_subtotal = (
        gift.gift_box
        + gift.brand_label
        + gift.backing
        + gift.op_bag
        + gift.protective_paper
        + gift.jan_seal
        + gift.other_material
    )
    material_cost = material_subtotal * (1.0 + material_loss_rate) + depreciation_unit

    # --- CG列: 加工代計 ---
    # CG = CD + CE + CF
    processing_cost = gift.boxing_cost + gift.other_process_1 + gift.other_process_2

    # --- BE列: FOB合計 ---
    # BE = AB + BC + CG
    fob_total = towel_cost + material_cost + processing_cost

    # --- BZ列: 積載個数 ---
    # BZ = BX × BY
    loaded_pcs = gift.pcs_per_case * gift.cases_loaded

    # --- BG列: C&F ---
    # BG = BE + (BF / BZ) × $N$4(現行為替)
    if loaded_pcs > 0:
        freight_per_unit = (cond.overseas_freight_usd / loaded_pcs) * cond.current_rate
    else:
        freight_per_unit = 0.0
    cnf = fob_total + freight_per_unit

    # --- BI列: CIF ---
    # BI = BG × (1 + 保険率)
    cif = cnf * (1.0 + cond.insurance_rate)

    # --- BK列: 関税 ---
    # BK = BI × BJ(関税率)
    # ※注: ギフト層はCIF全額に関税率を乗じる（単品層とは異なる）
    tariff = cif * cond.tariff_rate

    # --- CA列: 輸入経費合計(コンテナ) ---
    # ギフト層: BO × $M$4(社内為替) + BM + BN + ...
    import_cost_total = calc_import_cost_total(
        cond.import_expenses_gift, cond.internal_rate
    )

    # --- CB列: 輸入経費単価 ---
    # CB = CA / BZ
    import_cost_unit = calc_import_cost_unit(import_cost_total, loaded_pcs)

    # --- CP列: 物流経費 ---
    # CP = (CI + CJ + CK + CL + CM×CN) / CO, CO=BX
    logistics_cost = calc_logistics_cost(
        freight_per_case=gift.freight_per_case,
        packing_cost=gift.packing_cost,
        other_logistics=gift.other_logistics,
        cl=gift.logistics_cl,
        cm=gift.logistics_cm,
        cn=gift.logistics_cn,
        pcs_per_case=gift.pcs_per_case,
    )

    # --- P列: 製造原価 ---
    # P = BI + BK + CB + CP + E×O (歩引)
    discount_amount = gift.selling_price * gift.discount_rate
    manufacturing_cost = cif + tariff + import_cost_unit + logistics_cost + discount_amount

    # --- M列: 見積単価 ---
    # M = ROUNDUP(P × (1 + マージン率), 0)
    # float の表現誤差で 1 円過大になるのを防ぐため roundup_yen を使う。
    quote_price = roundup_yen(manufacturing_cost * (1.0 + margin_rate))

    # --- F列: 上代掛率 ---
    # F = E / D
    if gift.retail_price > 0:
        retail_ratio = gift.selling_price / gift.retail_price
    else:
        retail_ratio = 0.0

    # --- G列: 粗利単価 ---
    # G = E - P
    gross_profit = gift.selling_price - manufacturing_cost

    # --- H列: 粗利率 ---
    # H = (E - P) / E
    if gift.selling_price > 0:
        gross_profit_rate = gross_profit / gift.selling_price
    else:
        gross_profit_rate = 0.0

    # --- J列: 上代金額 ---
    # J = D × I
    retail_amount = gift.retail_price * gift.sales_quantity

    # --- K列: 売上金額 ---
    # K = E × I
    sales_amount = gift.selling_price * gift.sales_quantity

    # --- L列: 粗利金額 ---
    # Excel は L = K × H だが、selling_price=0 で粗利率を 0 に丸めると損失が
    # 集計から消えてしまう（K×H = 0×0 = 0）。粗利率に依存せず
    # gross_profit × 数量で算出する（selling_price>0 では K×H と数学的に同値）。
    profit_amount = gross_profit * gift.sales_quantity

    return GiftSetResult(
        towel_cost=towel_cost,
        depreciation_unit=depreciation_unit,
        material_cost=material_cost,
        processing_cost=processing_cost,
        fob_total=fob_total,
        loaded_pcs=loaded_pcs,
        cnf=cnf,
        cif=cif,
        tariff=tariff,
        import_cost_total=import_cost_total,
        import_cost_unit=import_cost_unit,
        logistics_cost=logistics_cost,
        manufacturing_cost=manufacturing_cost,
        quote_price=quote_price,
        retail_ratio=retail_ratio,
        gross_profit=gross_profit,
        gross_profit_rate=gross_profit_rate,
        retail_amount=retail_amount,
        sales_amount=sales_amount,
        profit_amount=profit_amount,
        breakdown_qty=breakdown_qty,
    )
