"""モックデータ: ギフトセット12パターン.

Excelの「ひな形」シート下段（行23-34）の実データ。
20FT条件での値。

凡例（構成品番マッピング）:
    ① = MOCK-001 (OSD-MOCO BT)
    ② = MOCK-002 (OSD-FUWA BT)
    ③ = MOCK-003 (OSD-MOCO FT)
    ④ = MOCK-004 (OSD-FUWA FT)
    ⑤ = MOCK-005 (ODS-MOCO-BM)
    ⑥ = MOCK-006 (OSD-FUWA-GJ MT)

共通値:
    retail_price   = 0      (D列は None)
    discount_rate  = 0
    cases_loaded   = 150
    freight_per_case = 1230.0  (CI列)
    packing_cost   = 0.0    (CJ列は None)
    other_logistics = 40.0  (CK列=40)
    logistics_cl   = 140.0
    logistics_cm   = 200.0
    logistics_cn   = 1.0
    brand_label〜other_material (AP〜AU) = 0
    design_cost〜other_depreciation (AV〜AY) = 0
    other_process_1 = other_process_2 = 0

pcs_per_case: ギフト01-06は20、ギフト07-12は8
sales_quantity: 行23-30は1000、行31-34は500
"""

from proto.engine.models import GiftComposition, GiftSet

# ---------------------------------------------------------------------------
# ギフト01-06: FT系・BT1系（pcs_per_case=20, sales_quantity=1000）
# ---------------------------------------------------------------------------

# 行23: FT2 もこ — ③×2
GIFT_01 = GiftSet(
    name="FT2 もこ",
    retail_price=0.0,
    selling_price=1294.0,
    sales_quantity=1000,
    discount_rate=0.0,
    composition=(
        GiftComposition(item_no="MOCK-003", quantity=2),
    ),
    # 資材 (AO〜AU列)
    gift_box=355.5,
    brand_label=0.0,
    backing=0.0,
    op_bag=0.0,
    protective_paper=0.0,
    jan_seal=0.0,
    other_material=0.0,
    # 償却 (AV〜AY列)
    design_cost=0.0,
    wooden_mold=0.0,
    plate_cost=0.0,
    other_depreciation=0.0,
    # 加工 (CD〜CF列)
    boxing_cost=45.0,
    other_process_1=0.0,
    other_process_2=0.0,
    # 物流 (BX〜CN列)
    pcs_per_case=20,
    cases_loaded=150,
    freight_per_case=1230.0,
    packing_cost=0.0,
    other_logistics=40.0,
    logistics_cl=140.0,
    logistics_cm=200.0,
    logistics_cn=1.0,
)

# 行24: FT2 ふわ — ④×2
GIFT_02 = GiftSet(
    name="FT2 ふわ",
    retail_price=0.0,
    selling_price=1190.0,
    sales_quantity=1000,
    discount_rate=0.0,
    composition=(
        GiftComposition(item_no="MOCK-004", quantity=2),
    ),
    gift_box=355.5,
    brand_label=0.0,
    backing=0.0,
    op_bag=0.0,
    protective_paper=0.0,
    jan_seal=0.0,
    other_material=0.0,
    design_cost=0.0,
    wooden_mold=0.0,
    plate_cost=0.0,
    other_depreciation=0.0,
    boxing_cost=45.0,
    other_process_1=0.0,
    other_process_2=0.0,
    pcs_per_case=20,
    cases_loaded=150,
    freight_per_case=1230.0,
    packing_cost=0.0,
    other_logistics=40.0,
    logistics_cl=140.0,
    logistics_cm=200.0,
    logistics_cn=1.0,
)

# 行25: FT1MT4 もこ — ③×1, ⑥×4
GIFT_03 = GiftSet(
    name="FT1MT4 もこ",
    retail_price=0.0,
    selling_price=1730.0,
    sales_quantity=1000,
    discount_rate=0.0,
    composition=(
        GiftComposition(item_no="MOCK-003", quantity=1),
        GiftComposition(item_no="MOCK-006", quantity=4),
    ),
    gift_box=361.5,
    brand_label=0.0,
    backing=0.0,
    op_bag=0.0,
    protective_paper=0.0,
    jan_seal=0.0,
    other_material=0.0,
    design_cost=0.0,
    wooden_mold=0.0,
    plate_cost=0.0,
    other_depreciation=0.0,
    boxing_cost=64.5,
    other_process_1=0.0,
    other_process_2=0.0,
    pcs_per_case=20,
    cases_loaded=150,
    freight_per_case=1230.0,
    packing_cost=0.0,
    other_logistics=40.0,
    logistics_cl=140.0,
    logistics_cm=200.0,
    logistics_cn=1.0,
)

# 行26: FT1MT4 ふわ — ④×1, ⑥×4
GIFT_04 = GiftSet(
    name="FT1MT4 ふわ",
    retail_price=0.0,
    selling_price=1678.0,
    sales_quantity=1000,
    discount_rate=0.0,
    composition=(
        GiftComposition(item_no="MOCK-004", quantity=1),
        GiftComposition(item_no="MOCK-006", quantity=4),
    ),
    gift_box=361.5,
    brand_label=0.0,
    backing=0.0,
    op_bag=0.0,
    protective_paper=0.0,
    jan_seal=0.0,
    other_material=0.0,
    design_cost=0.0,
    wooden_mold=0.0,
    plate_cost=0.0,
    other_depreciation=0.0,
    boxing_cost=64.5,
    other_process_1=0.0,
    other_process_2=0.0,
    pcs_per_case=20,
    cases_loaded=150,
    freight_per_case=1230.0,
    packing_cost=0.0,
    other_logistics=40.0,
    logistics_cl=140.0,
    logistics_cm=200.0,
    logistics_cn=1.0,
)

# 行27: BT1 もこ — ①×1
GIFT_05 = GiftSet(
    name="BT1 もこ",
    retail_price=0.0,
    selling_price=1358.0,
    sales_quantity=1000,
    discount_rate=0.0,
    composition=(
        GiftComposition(item_no="MOCK-001", quantity=1),
    ),
    gift_box=324.0,
    brand_label=0.0,
    backing=0.0,
    op_bag=0.0,
    protective_paper=0.0,
    jan_seal=0.0,
    other_material=0.0,
    design_cost=0.0,
    wooden_mold=0.0,
    plate_cost=0.0,
    other_depreciation=0.0,
    boxing_cost=37.5,
    other_process_1=0.0,
    other_process_2=0.0,
    pcs_per_case=20,
    cases_loaded=150,
    freight_per_case=1230.0,
    packing_cost=0.0,
    other_logistics=40.0,
    logistics_cl=140.0,
    logistics_cm=200.0,
    logistics_cn=1.0,
)

# 行28: BT1 ふわ — ②×1
GIFT_06 = GiftSet(
    name="BT1 ふわ",
    retail_price=0.0,
    selling_price=1239.0,
    sales_quantity=1000,
    discount_rate=0.0,
    composition=(
        GiftComposition(item_no="MOCK-002", quantity=1),
    ),
    gift_box=324.0,
    brand_label=0.0,
    backing=0.0,
    op_bag=0.0,
    protective_paper=0.0,
    jan_seal=0.0,
    other_material=0.0,
    design_cost=0.0,
    wooden_mold=0.0,
    plate_cost=0.0,
    other_depreciation=0.0,
    boxing_cost=37.5,
    other_process_1=0.0,
    other_process_2=0.0,
    pcs_per_case=20,
    cases_loaded=150,
    freight_per_case=1230.0,
    packing_cost=0.0,
    other_logistics=40.0,
    logistics_cl=140.0,
    logistics_cm=200.0,
    logistics_cn=1.0,
)

# ---------------------------------------------------------------------------
# ギフト07-08: BT系複合（pcs_per_case=8, sales_quantity=1000）
# ギフト09-12: BT系複合（pcs_per_case=8, sales_quantity=500）
# ---------------------------------------------------------------------------

# 行29: BT1FT2 もこ — ①×1, ③×2
GIFT_07 = GiftSet(
    name="BT1FT2 もこ",
    retail_price=0.0,
    selling_price=2522.0,
    sales_quantity=1000,
    discount_rate=0.0,
    composition=(
        GiftComposition(item_no="MOCK-001", quantity=1),
        GiftComposition(item_no="MOCK-003", quantity=2),
    ),
    gift_box=520.5,
    brand_label=0.0,
    backing=0.0,
    op_bag=0.0,
    protective_paper=0.0,
    jan_seal=0.0,
    other_material=0.0,
    design_cost=0.0,
    wooden_mold=0.0,
    plate_cost=0.0,
    other_depreciation=0.0,
    boxing_cost=67.5,
    other_process_1=0.0,
    other_process_2=0.0,
    pcs_per_case=8,
    cases_loaded=150,
    freight_per_case=1230.0,
    packing_cost=0.0,
    other_logistics=40.0,
    logistics_cl=140.0,
    logistics_cm=200.0,
    logistics_cn=1.0,
)

# 行30: BT1FT2 ふわ — ②×1, ④×2
GIFT_08 = GiftSet(
    name="BT1FT2 ふわ",
    retail_price=0.0,
    selling_price=2298.0,
    sales_quantity=1000,
    discount_rate=0.0,
    composition=(
        GiftComposition(item_no="MOCK-002", quantity=1),
        GiftComposition(item_no="MOCK-004", quantity=2),
    ),
    gift_box=520.5,
    brand_label=0.0,
    backing=0.0,
    op_bag=0.0,
    protective_paper=0.0,
    jan_seal=0.0,
    other_material=0.0,
    design_cost=0.0,
    wooden_mold=0.0,
    plate_cost=0.0,
    other_depreciation=0.0,
    boxing_cost=67.5,
    other_process_1=0.0,
    other_process_2=0.0,
    pcs_per_case=8,
    cases_loaded=150,
    freight_per_case=1230.0,
    packing_cost=0.0,
    other_logistics=40.0,
    logistics_cl=140.0,
    logistics_cm=200.0,
    logistics_cn=1.0,
)

# 行31: BT1FT1BM1 もこ — ①×1, ③×1, ⑤×1
GIFT_09 = GiftSet(
    name="BT1FT1BM1 もこ",
    retail_price=0.0,
    selling_price=2789.0,
    sales_quantity=500,
    discount_rate=0.0,
    composition=(
        GiftComposition(item_no="MOCK-001", quantity=1),
        GiftComposition(item_no="MOCK-003", quantity=1),
        GiftComposition(item_no="MOCK-005", quantity=1),
    ),
    gift_box=520.5,
    brand_label=0.0,
    backing=0.0,
    op_bag=0.0,
    protective_paper=0.0,
    jan_seal=0.0,
    other_material=0.0,
    design_cost=0.0,
    wooden_mold=0.0,
    plate_cost=0.0,
    other_depreciation=0.0,
    boxing_cost=64.5,
    other_process_1=0.0,
    other_process_2=0.0,
    pcs_per_case=8,
    cases_loaded=150,
    freight_per_case=1230.0,
    packing_cost=0.0,
    other_logistics=40.0,
    logistics_cl=140.0,
    logistics_cm=200.0,
    logistics_cn=1.0,
)

# 行32: BT1BM2 もこ — ①×1, ⑤×2
GIFT_10 = GiftSet(
    name="BT1BM2 もこ",
    retail_price=0.0,
    selling_price=3056.0,
    sales_quantity=500,
    discount_rate=0.0,
    composition=(
        GiftComposition(item_no="MOCK-001", quantity=1),
        GiftComposition(item_no="MOCK-005", quantity=2),
    ),
    gift_box=520.5,
    brand_label=0.0,
    backing=0.0,
    op_bag=0.0,
    protective_paper=0.0,
    jan_seal=0.0,
    other_material=0.0,
    design_cost=0.0,
    wooden_mold=0.0,
    plate_cost=0.0,
    other_depreciation=0.0,
    boxing_cost=61.5,
    other_process_1=0.0,
    other_process_2=0.0,
    pcs_per_case=8,
    cases_loaded=150,
    freight_per_case=1230.0,
    packing_cost=0.0,
    other_logistics=40.0,
    logistics_cl=140.0,
    logistics_cm=200.0,
    logistics_cn=1.0,
)

# 行33: BT2 もこ — ①×2
GIFT_11 = GiftSet(
    name="BT2 もこ",
    retail_price=0.0,
    selling_price=2592.0,
    sales_quantity=500,
    discount_rate=0.0,
    composition=(
        GiftComposition(item_no="MOCK-001", quantity=2),
    ),
    gift_box=489.0,
    brand_label=0.0,
    backing=0.0,
    op_bag=0.0,
    protective_paper=0.0,
    jan_seal=0.0,
    other_material=0.0,
    design_cost=0.0,
    wooden_mold=0.0,
    plate_cost=0.0,
    other_depreciation=0.0,
    boxing_cost=64.5,
    other_process_1=0.0,
    other_process_2=0.0,
    pcs_per_case=8,
    cases_loaded=150,
    freight_per_case=1230.0,
    packing_cost=0.0,
    other_logistics=40.0,
    logistics_cl=140.0,
    logistics_cm=200.0,
    logistics_cn=1.0,
)

# 行34: BT2 ふわ — ②×2
GIFT_12 = GiftSet(
    name="BT2 ふわ",
    retail_price=0.0,
    selling_price=2352.0,
    sales_quantity=500,
    discount_rate=0.0,
    composition=(
        GiftComposition(item_no="MOCK-002", quantity=2),
    ),
    gift_box=489.0,
    brand_label=0.0,
    backing=0.0,
    op_bag=0.0,
    protective_paper=0.0,
    jan_seal=0.0,
    other_material=0.0,
    design_cost=0.0,
    wooden_mold=0.0,
    plate_cost=0.0,
    other_depreciation=0.0,
    boxing_cost=64.5,
    other_process_1=0.0,
    other_process_2=0.0,
    pcs_per_case=8,
    cases_loaded=150,
    freight_per_case=1230.0,
    packing_cost=0.0,
    other_logistics=40.0,
    logistics_cl=140.0,
    logistics_cm=200.0,
    logistics_cn=1.0,
)

# 全ギフトセットのリスト
ALL_GIFTS: list[GiftSet] = [
    GIFT_01, GIFT_02, GIFT_03, GIFT_04, GIFT_05, GIFT_06,
    GIFT_07, GIFT_08, GIFT_09, GIFT_10, GIFT_11, GIFT_12,
]
