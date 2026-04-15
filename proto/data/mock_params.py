"""モックデータ: 輸入条件パラメータ（20FT / 40FT）.

Excelの「ひな形」シートのパラメータ行から抽出。
単品用・ギフト用の輸入経費を ImportExpenses で個別に保持する。
"""

from proto.engine.models import ImportCondition, ImportExpenses

# ---------------------------------------------------------------------------
# 20FT / 大阪揚げ / 今治倉庫
# ---------------------------------------------------------------------------

# 単品用輸入経費（Excel行6: BM〜BW列）
_EXPENSES_20FT_SINGLE = ImportExpenses(
    cic_usd=180.0,       # BO列 — CIC(USD)
    cy_charge=30000.0,   # BM列 — CY CHARGE(JPY)
    thc=36000.0,         # BN列 — THC(JPY)
    emc=3000.0,          # BP列 — EMC(JPY)
    cic2=20000.0,        # BQ列 — CIC(JPY)
    do_fee=5000.0,       # BR列 — D/O(JPY)
    doc_fee=6000.0,      # BS列 — DOC(JPY)
    customs_fee=11800.0, # BT列 — 通関(JPY)
    handling_fee=8000.0, # BU列 — 取扱料(JPY)
    drayage=51000.0,     # BV列 — ドレー料(JPY)
    devanning=0.0,       # BW列 — デバン料(JPY)
)

# ギフト用輸入経費（Excel行22: BM〜BW列）
_EXPENSES_20FT_GIFT = ImportExpenses(
    cic_usd=180.0,
    cy_charge=30000.0,
    thc=36000.0,
    emc=3000.0,
    cic2=0.0,            # ギフトは CIC2 なし
    do_fee=5000.0,
    doc_fee=6000.0,
    customs_fee=11800.0,
    handling_fee=8000.0,
    drayage=51000.0,
    devanning=19200.0,   # ギフトはデバン料あり
)

COND_20FT = ImportCondition(
    name="20FT 大阪/今治",
    internal_rate=150.0,
    current_rate=150.0,
    loss_rate_pct=15.0,
    margin_pct=40.0,
    material_lot=3000,
    material_loss_pct=3.0,
    # 刺繍単価(USD) — R4行（今回はすべて0）
    emb_general=0.0,
    emb_silver=0.0,
    emb_ket=0.0,
    emb_brand=0.0,
    # 輸入
    overseas_freight_usd=160.0,
    insurance_rate=0.0018,
    tariff_rate=0.074,
    # 輸入経費（単品・ギフト別）
    import_expenses_single=_EXPENSES_20FT_SINGLE,
    import_expenses_gift=_EXPENSES_20FT_GIFT,
    # 物流
    io_fee=70.0,
    storage_fee=120.0,
    storage_months=0.0,
)

# ---------------------------------------------------------------------------
# 40FT / 東京揚げ
# ---------------------------------------------------------------------------

# 単品用輸入経費（暫定: 20FT値から40FT差分を適用）
_EXPENSES_40FT_SINGLE = ImportExpenses(
    cic_usd=180.0,
    cy_charge=30000.0,
    thc=55000.0,         # 40FT は THC が異なる
    emc=46000.0,         # EMC も異なる
    cic2=4000.0,
    do_fee=3000.0,
    doc_fee=6000.0,
    customs_fee=11800.0,
    handling_fee=8000.0,
    drayage=48000.0,     # ドレー料も異なる
    devanning=0.0,
)

# ギフト用輸入経費（暫定: 単品と同一、後日精査）
_EXPENSES_40FT_GIFT = ImportExpenses(
    cic_usd=180.0,
    cy_charge=30000.0,
    thc=55000.0,
    emc=46000.0,
    cic2=4000.0,
    do_fee=3000.0,
    doc_fee=6000.0,
    customs_fee=11800.0,
    handling_fee=8000.0,
    drayage=48000.0,
    devanning=0.0,
)

COND_40FT = ImportCondition(
    name="40FT 東京",
    internal_rate=150.0,
    current_rate=150.0,
    loss_rate_pct=15.0,
    margin_pct=15.0,
    material_lot=3000,   # BA20 (=3000、#REF!修正後)
    material_loss_pct=3.0,
    # 刺繍単価(USD)
    emb_general=0.0,
    emb_silver=0.0,
    emb_ket=0.0,
    emb_brand=0.0,
    # 輸入
    overseas_freight_usd=240.0,
    insurance_rate=0.0018,
    tariff_rate=0.074,
    # 輸入経費（単品・ギフト別）
    import_expenses_single=_EXPENSES_40FT_SINGLE,
    import_expenses_gift=_EXPENSES_40FT_GIFT,
    # 物流
    io_fee=140.0,
    storage_fee=200.0,
    storage_months=0.0,
)
