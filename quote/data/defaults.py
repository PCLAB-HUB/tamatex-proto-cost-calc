"""Excel Row 8-9 から抽出したデフォルト値.

プロトタイプで使う初期値・サンプルデータを定義する。
"""

from __future__ import annotations

from quote.engine.models import ContainerExpenses, GlobalParams, ProductInput

DEFAULT_PARAMS = GlobalParams(
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

SAMPLE_PRODUCTS: tuple[ProductInput, ...] = (
    ProductInput(
        product_name="ダイカットメモ",
        prototype_code="1",
        package_size_cm="13*9.5*0.6cm",
        weight_g=41.0,
        packing_quantity=270,
        fob_usd=0.31,
        embroidery_per_1000=0.03,
        container_load=194318.5,
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
        quote_date="2025/9/12",
    ),
    ProductInput(
        product_name="PVCバッグ+メモカード",
        prototype_code="2",
        package_size_cm="11.8*10.8*0.4cm",
        weight_g=14.0,
        packing_quantity=640,
        fob_usd=0.20,
        embroidery_per_1000=0.03,
        container_load=251354.6,
        tariff_rate_override=0.08,  # PVC製品: 関税8%
        quote_price=48.0,
        lot_per_color=10000,
        num_colors=1,
        retail_price=500.0,
        logistics_io_fee=70.0,
        logistics_storage_months=1.0,
        logistics_storage_fee=150.0,
        logistics_slip_fee=100.0,
        logistics_freight=700.0,
        domestic_packing_qty=1,
        quote_date="2025/9/12",
    ),
    ProductInput(
        product_name="デープ",
        prototype_code="3",
        package_size_cm="11.2*6.3*1.5cm",
        weight_g=16.76,
        packing_quantity=600,
        fob_usd=0.34,
        embroidery_per_1000=0.03,
        container_load=168672.3,
        quote_price=74.0,
        lot_per_color=10000,
        num_colors=1,
        retail_price=700.0,
        logistics_io_fee=70.0,
        logistics_storage_months=1.0,
        logistics_storage_fee=150.0,
        logistics_slip_fee=100.0,
        logistics_freight=700.0,
        domestic_packing_qty=1,
        quote_date="2025/9/12",
    ),
)

TARIFF_RATES: dict[str, float] = {
    "非課税": 0.0,
    "3.9%": 0.039,
    "4.8%": 0.048,
    "8.0%": 0.08,
}

SUPPLIERS = ["SUNVIM", "（その他）"]
PORTS = ["神戸経由", "大阪直", "東京直", "（その他）"]
DELIVERY_TO = ["コーヨー", "（その他）"]
SHIP_TO = ["関東", "関西", "中部", "九州", "（その他）"]
CONTAINER_FT = [20, 40]
METHODS = ["コンテナ", "路線便"]
