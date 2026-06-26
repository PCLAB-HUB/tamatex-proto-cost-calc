"""ステーショナリー見積もりソフト — データモデル定義.

原価計算書参考資料.xlsx の列構造を dataclass で表現する。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProductInput:
    """商品1点の入力データ（手動入力 + 選択項目）.

    Excel Row 9〜の各行に対応する。
    """

    # --- 基本情報 (A-I列) ---
    supplier: str = "SUNVIM"
    inspection_pass: bool = True
    customer: str = ""
    port: str = "神戸経由"
    delivery_to: str = "コーヨー"
    container_ft: int = 20
    ship_to: str = "関東"
    product_name: str = ""
    prototype_code: str = ""

    # --- 製品仕様 (K-Q列) ---
    package_size_cm: str = ""
    weight_g: float = 0.0
    packing_quantity: int = 1
    method: str = "コンテナ"

    # --- FOB関連 (S-Y列) ---
    fob_usd: float = 0.0
    other_processing_usd: float = 0.0
    loss_rate: float = 0.0
    charge_up_unit: float = 0.0
    embroidery_per_1000: float = 0.03
    stitch_count: float = 0.0
    die_charge: float = 0.0

    # --- 検品・加工 3通貨 (AA-AI列) ---
    inspection_jpy: float = 0.0
    packing_jpy: float = 0.0
    material_jpy: float = 0.0
    inspection_cny: float = 0.0
    packing_cny: float = 0.0
    material_cny: float = 0.0
    inspection_usd: float = 0.0
    packing_usd: float = 0.0
    material_usd: float = 0.0

    # --- 日本支給副資材 (BH-BP列) ---
    ribbon: float = 0.0
    name_label_2: float = 0.0
    name_label_3: float = 0.0
    seal_1: float = 0.0
    seal_2: float = 0.0
    tag: float = 0.0
    bag: float = 0.0
    other_material: float = 0.0
    material_freight: float = 0.0

    # --- 償却経費 (BU-CJ列) ---
    design_cost: float = 0.0
    jq_card: float = 0.0
    embroidery_card: float = 0.0
    print_unit_price: float = 0.0
    print_type_count: float = 0.0
    print_mold: float = 0.0
    layout: float = 0.0
    name_plate: float = 0.0
    seal_plate: float = 0.0
    tab_plate: float = 0.0
    bag_plate: float = 0.0
    cardboard_plate: float = 0.0
    other_depreciation: float = 0.0
    sample_cost: float = 0.0
    quality_inspection: float = 0.0
    other_amortization: float = 0.0

    # --- 物流: 倉庫→納品先 (CN-CS列) ---
    logistics_cardboard: float = 0.0
    logistics_io_fee: float = 70.0
    logistics_storage_months: float = 1.0
    logistics_storage_fee: float = 150.0
    logistics_slip_fee: float = 100.0
    logistics_freight: float = 700.0

    # --- 国内加工付帯 (CV-DC列) ---
    domestic_packing_qty: int = 1
    domestic_processing: float = 0.0
    domestic_material: float = 0.0
    domestic_cardboard: float = 0.0
    domestic_io: float = 0.0
    domestic_storage_months: float = 0.0
    domestic_storage_fee: float = 0.0
    domestic_freight: float = 0.0

    # --- 売価設定 (DH-DQ列) ---
    quote_price: float = 0.0
    center_fee: float = 0.0
    rebate: float = 0.0
    lot_per_color: int = 0
    num_colors: int = 1
    quote_date: str = ""
    retail_price: float = 0.0

    # --- 第2価格体系（償却別途） (DZ-EI列) ---
    quote_price_ex_amort: float = 0.0
    center_fee_ex_amort: float = 0.0
    rebate_ex_amort: float = 0.0
    retail_price_ex_amort: float = 0.0

    # --- 商品個別の関税率（AP列、GlobalParamsのデフォルトを上書き） ---
    tariff_rate_override: float | None = None

    # --- コンテナ積載量（R列: 手動 or 計算） ---
    container_load: float = 0.0


@dataclass(frozen=True)
class ContainerExpenses:
    """コンテナ国内経費11項目 (AS-BC列)."""

    cy_charge: float = 30000.0
    lss: float = 0.0
    lss_cic_usd: float = 180.0
    thc: float = 36000.0
    emc: float = 3000.0
    do_fee: float = 5000.0
    doc_fee: float = 6000.0
    customs_fee: float = 11800.0
    handling_fee: float = 8000.0
    drayage: float = 50000.0
    devanning: float = 14000.0


@dataclass(frozen=True)
class GlobalParams:
    """全商品共通の固定パラメータ（サイドバーで設定）."""

    internal_rate: float = 152.0
    current_rate: float = 152.0
    overseas_freight_usd: float = 240.0
    cny_to_usd_rate: float = 0.17
    cny_to_jpy_rate: float = 13.0
    insurance_risk_rate: float = 0.0018
    tariff_rate: float = 0.0
    b_grade_loss_rate: float = 0.01
    sub_material_loss_rate: float = 0.05
    amortization_margin: float = 0.05
    margin: float = 0.20
    container_expenses: ContainerExpenses = field(
        default_factory=ContainerExpenses
    )


@dataclass(frozen=True)
class CostBreakdown:
    """原価計算の中間結果・最終結果."""

    # FOB調整後 (Z列)
    fob_adjusted_usd: float = 0.0
    # C&F (AM列)
    cnf_jpy: float = 0.0
    # CIF (AO列)
    cif_jpy: float = 0.0
    # 関税 (AQ列)
    tariff_jpy: float = 0.0
    # 仕入値 (AR列)
    purchase_price: float = 0.0
    # コンテナ経費合計 (BD列)
    container_expense_total: float = 0.0
    # コンテナ経費/枚 (BE列)
    container_expense_unit: float = 0.0
    # B品ロス額 (BG列)
    b_grade_loss: float = 0.0
    # 副資材経費 (BT列)
    sub_material_cost: float = 0.0
    # 償却経費/枚 実額 (CK列)
    amortization_actual: float = 0.0
    # 償却経費/枚 マージン込 (CM列)
    amortization_with_margin: float = 0.0
    # 物流経費/ケース (CT列)
    logistics_per_case: float = 0.0
    # 物流経費/枚 (CU列)
    logistics_unit: float = 0.0
    # 加工経費/枚 (DD列)
    domestic_processing_unit: float = 0.0
    # 製品原価 (DE列)
    product_cost: float = 0.0


@dataclass(frozen=True)
class PricingResult:
    """価格計算結果（償却込み / 別途の共通構造）."""

    product_cost: float = 0.0
    margin_rate: float = 0.0
    trial_price: float = 0.0
    quote_price: float = 0.0
    center_fee: float = 0.0
    rebate: float = 0.0
    lot: int = 0
    stepped_price: float = 0.0
    retail_price: float = 0.0
    retail_ratio: float = 0.0
    sales_amount: float = 0.0
    gross_profit_unit: float = 0.0
    gross_profit_rate: float = 0.0
    gross_profit_total: float = 0.0


@dataclass(frozen=True)
class QuoteResult:
    """見積もり計算の最終結果."""

    cost: CostBreakdown
    pricing_with_amort: PricingResult
    pricing_without_amort: PricingResult
    amortization_separate: float = 0.0
