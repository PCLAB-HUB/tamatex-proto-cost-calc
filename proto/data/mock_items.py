"""モックデータ: 単品タオル6品目.

Excelの「ひな形」シート上段（行7-12）の実データ。
ITEM_01 のみ物流フィールドに実値を設定（他品目はデフォルト0）。
"""

from proto.engine.models import SingleItem

# ① OSD-MOCO BT (行7) — 物流データあり
ITEM_01 = SingleItem(
    item_no="MOCK-001",
    name="OSD-MOCO",
    item_type="BT",
    size="60×120",
    weight_g=290.0,
    weave="JQ",
    lot=6000,
    fob_usd=3.80,
    embroidery_needles=0.0,
    silver_embroidery=0.0,
    ket_embroidery=0.0,
    brand_logo=0.0,
    inspection=0.0,
    other_processing=0.0,
    name_label_1=0.0,
    name_label_2=0.0,
    seal=0.0,
    other_material=0.0,
    # 物流（CI/CJ/CK/CO列）
    logistics_pcs_per_case=100,
    logistics_freight=111.0,
    logistics_packing=12.0,
    logistics_other=3.0,
)

# ② OSD-FUWA BT (行8)
ITEM_02 = SingleItem(
    item_no="MOCK-002",
    name="OSD-FUWA",
    item_type="BT",
    size="60×120",
    weight_g=None,  # 目方なし → 積載計算スキップ
    weave="JQ",
    lot=6000,
    fob_usd=3.21,
    embroidery_needles=0.0,
    silver_embroidery=0.0,
    ket_embroidery=0.0,
    brand_logo=0.0,
    inspection=0.0,
    other_processing=0.0,
    name_label_1=0.0,
    name_label_2=0.0,
    seal=0.0,
    other_material=0.0,
)

# ③ OSD-MOCO FT (行9)
ITEM_03 = SingleItem(
    item_no="MOCK-003",
    name="OSD-MOCO",
    item_type="FT",
    size="34×80",
    weight_g=300.0,
    weave="JQ",
    lot=12000,
    fob_usd=1.62,
    embroidery_needles=0.0,
    silver_embroidery=0.0,
    ket_embroidery=0.0,
    brand_logo=0.0,
    inspection=0.0,
    other_processing=0.0,
    name_label_1=0.0,
    name_label_2=0.0,
    seal=0.0,
    other_material=0.0,
)

# ④ OSD-FUWA FT (行10)
ITEM_04 = SingleItem(
    item_no="MOCK-004",
    name="OSD-FUWA",
    item_type="FT",
    size="34×80",
    weight_g=400.0,
    weave="JQ",
    lot=12000,
    fob_usd=1.34,
    embroidery_needles=0.0,
    silver_embroidery=0.0,
    ket_embroidery=0.0,
    brand_logo=0.0,
    inspection=0.0,
    other_processing=0.0,
    name_label_1=0.0,
    name_label_2=0.0,
    seal=0.0,
    other_material=0.0,
)

# ⑤ ODS-MOCO-BM (行11)
ITEM_05 = SingleItem(
    item_no="MOCK-005",
    name="ODS-MOCO-BM",
    item_type="BM",
    size="60×40",
    weight_g=None,  # 目方なし
    weave="JQ",
    lot=3000,
    fob_usd=3.08,
    embroidery_needles=0.0,
    silver_embroidery=0.0,
    ket_embroidery=0.0,
    brand_logo=0.0,
    inspection=0.0,
    other_processing=0.0,
    name_label_1=0.0,
    name_label_2=0.0,
    seal=0.0,
    other_material=0.0,
)

# ⑥ OSD-FUWA-GJ MT (行12)
ITEM_06 = SingleItem(
    item_no="MOCK-006",
    name="OSD-FUWA-GJ",
    item_type="MT",
    size="25×25",
    weight_g=None,  # 目方なし
    weave="JQ",
    lot=10000,
    fob_usd=0.95,
    embroidery_needles=0.0,
    silver_embroidery=0.0,
    ket_embroidery=0.0,
    brand_logo=0.0,
    inspection=0.0,
    other_processing=0.0,
    name_label_1=0.0,
    name_label_2=0.0,
    seal=0.0,
    other_material=0.0,
)

# 全品目の辞書（品番でアクセス）
ALL_ITEMS: dict[str, SingleItem] = {
    item.item_no: item
    for item in [ITEM_01, ITEM_02, ITEM_03, ITEM_04, ITEM_05, ITEM_06]
}
