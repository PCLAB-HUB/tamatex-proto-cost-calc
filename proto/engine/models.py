"""原価計算プロトタイプ — データモデル定義.

Excelの「ひな形」シートの構造をdataclassで表現する。
全フィールドはExcel列との対応をコメントで記載。
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# 単品タオル（上段: 行7-16）
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SingleItem:
    """単品タオルの入力データ."""

    item_no: str               # モック品番 (MOCK-001等)
    name: str                  # 品名 (C列)
    item_type: str             # アイテム種別 BT/FT/BM/MT (E列)
    size: str                  # サイズ (F列)
    weight_g: float | None     # 目方(g) (G列) — None許容
    weave: str                 # 織区分 (H列)
    lot: int                   # ロット数 (L列)
    fob_usd: float             # FOB単価(USD) (P列)
    # 加工費
    embroidery_needles: float  # 刺繍針数(千針) (R列)
    silver_embroidery: float   # 銀糸刺繍(USD) (S列)
    ket_embroidery: float      # ケット刺繍(USD) — 型代 (T列)
    brand_logo: float          # ブランドロゴ(USD) (U列)
    inspection: float          # 検品代(円) (V列)
    other_processing: float    # その他(円) (W列)
    # 日本支給資材
    name_label_1: float        # ネーム1(円) (X列)
    name_label_2: float        # ネーム2(円) (Y列)
    seal: float                # シール(円) (Z列)
    other_material: float      # その他資材(円) (AA列)
    # 償却費 — プロトタイプでは0でも可
    trace_price: float = 0.0       # トレス単価(円) (AQ列)
    trace_count: int = 0           # 型数 (AR列)
    design_cost: float = 0.0       # 図案 (AT列)
    jq_card: float = 0.0           # JQカード (AU列)
    embroidery_card: float = 0.0   # 刺繍カード (AV列)
    sample_cost: float = 0.0       # 見本代 (AW列)
    inspection_cost: float = 0.0   # 検査費用 (AX列)
    material_plate_1: float = 0.0  # 資材版1 (AY列)
    material_plate_2: float = 0.0  # 資材版2 (AZ列)
    material_plate_3: float = 0.0  # 資材版3 (BA列)
    # 物流(CI/CJ/CK/CO列) — 品目固有。CL/CM/CN(入出庫/保管/月数)は品目に
    # よらず条件側 ImportCondition.logistics_single が一括で保持する。
    logistics_pcs_per_case: int = 0       # BX/CO列
    logistics_freight: float = 0.0         # CI列
    logistics_packing: float = 0.0         # CJ列
    logistics_other: float = 0.0           # CK列


# ---------------------------------------------------------------------------
# ギフトセット構成要素
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GiftComposition:
    """ギフトセット内の単品構成."""

    item_no: str   # 単品品番
    quantity: int   # 使用枚数


# ---------------------------------------------------------------------------
# ギフトセット（下段: 行23-42 / 行49-68）
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GiftSet:
    """ギフトセットの入力データ."""

    name: str                        # セット名 (C列)
    retail_price: float              # 上代 (D列)
    selling_price: float             # 販売単価 (E列)
    sales_quantity: int              # 販売予定数量 (I列)
    discount_rate: float             # 歩引率 (O列)
    composition: tuple[GiftComposition, ...]  # 単品構成 (R-AA列)
    # 資材
    gift_box: float                  # 化粧箱(円) (AO列)
    brand_label: float               # ブランドラベル(円) (AP列)
    backing: float                   # 台紙(円) (AQ列)
    op_bag: float                    # OP(円) (AR列)
    protective_paper: float          # 保護紙(円) (AS列)
    jan_seal: float                  # JAN/シール(円) (AT列)
    other_material: float            # その他資材(円) (AU列)
    # 償却
    design_cost: float               # デザイン費(円) (AV列)
    wooden_mold: float               # 木型(円) (AW列)
    plate_cost: float                # 版代(円) (AX列)
    other_depreciation: float        # その他償却(円) (AY列)
    # 加工
    boxing_cost: float               # 箱入代(円) (CD列)
    other_process_1: float           # その他加工1(円) (CE列)
    other_process_2: float           # その他加工2(円) (CF列)
    # 物流
    pcs_per_case: int                # ケース入数 (BX列)
    cases_loaded: int                # 積載ケース数 (BY列)
    freight_per_case: float          # 運賃/ケース(円) (CI列)
    packing_cost: float              # 梱包(円) (CJ列)
    other_logistics: float           # その他物流(円) (CK列)
    # CL/CM/CN(入出庫/保管/月数)は条件側 ImportCondition.logistics_gift が保持する。


# ---------------------------------------------------------------------------
# 物流パラメータ（入出庫・保管料・月数）
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LogisticsParams:
    """物流の入出庫・保管パラメータ（単品/ギフト別、コンテナ非依存）.

    Excel ひな形の CL列(入出庫)/CM列(保管料)/CN列(月数)に対応する。
    倉庫料金はケース単位のため 20FT/40FT で共通で、単品/ギフトの区分で決まる
    （単品=$CL$6 系、ギフト=$CL$22 系。40FTギフトも $CL$22 を参照する）。
    """

    io_fee: float          # 入出庫(円/個) — CL列
    storage_fee: float     # 保管料(円/個) — CM列
    storage_months: float  # 保管月数 — CN列


# ---------------------------------------------------------------------------
# 輸入経費（11項目）
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ImportExpenses:
    """輸入経費11項目 — CA列の構成要素.

    CA = cic_usd × exchange_rate + cy_charge + thc + emc + cic2 + do_fee + doc_fee + customs_fee + handling_fee + drayage + devanning
    """

    cic_usd: float      # BO列 — CIC(USD), exchange rate で換算
    cy_charge: float     # BM列 — CY CHARGE(JPY)
    thc: float           # BN列 — THC(JPY)
    emc: float           # BP列 — EMC(JPY)
    cic2: float          # BQ列 — CIC(JPY)
    do_fee: float        # BR列 — D/O(JPY)
    doc_fee: float       # BS列 — DOC(JPY)
    customs_fee: float   # BT列 — 通関(JPY)
    handling_fee: float  # BU列 — 取扱料(JPY)
    drayage: float       # BV列 — ドレー料(JPY)
    devanning: float     # BW列 — デバン料(JPY)


# ---------------------------------------------------------------------------
# 輸入条件（20FT / 40FT）
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ImportCondition:
    """輸入条件パラメータ（20FT大阪今治 / 40FT東京）."""

    name: str                    # 条件名
    internal_rate: float         # 社内為替(円/USD)
    current_rate: float          # 現行為替(円/USD)
    loss_rate_pct: float         # ロス率(%) — AB4 = Z4/100
    margin_pct: float            # マージン(%) — N20
    material_lot: int            # 資材ロット — BA20
    material_loss_pct: float     # 資材ロス率(%) — BB20
    # 刺繍単価(USD)
    emb_general: float           # 一般刺繍 (R4)
    emb_silver: float            # 銀糸刺繍
    emb_ket: float               # ケット刺繍
    emb_brand: float             # ブランドロゴ
    # 輸入
    overseas_freight_usd: float  # 海外運賃(USD) — BF列
    insurance_rate: float        # 保険率 — BH列
    tariff_rate: float           # 関税率 — BJ列
    # 輸入経費11項目(円) — BM〜BW列（単品・ギフト別）
    import_expenses_single: ImportExpenses  # 単品用輸入経費
    import_expenses_gift: ImportExpenses    # ギフト用輸入経費
    # 物流（入出庫/保管料/月数。倉庫料金はケース単位でコンテナ非依存のため、
    #  単品/ギフトの区分で持つ。Excel CL/CM/CN列）
    logistics_single: LogisticsParams  # 単品用 (Excel $CL$6/$CM$6/$CN$6)
    logistics_gift: LogisticsParams    # ギフト用 (Excel $CL$22/$CM$22/$CN$22)


# ---------------------------------------------------------------------------
# 計算結果 — 単品
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SingleItemResult:
    """単品の計算結果（全中間値を保持）."""

    material_cost: float          # 資材代 = AB列
    trace_subtotal: float         # トレス小計 = AS列
    depreciation_total: float     # 償却費合計 = BC列
    depreciation_per_unit: float  # 償却費/枚 = BB列
    fob_jpy: float                # FOB(円) = BE列
    loaded_pcs: float             # 積載個数 = BZ列
    loaded_cases: float           # 積載ケース数 = BY列
    cnf: float                    # C&F = BG列
    cif: float                    # CIF = BI列
    tariff: float                 # 関税 = BK列
    import_cost_total: float      # 輸入経費合計(コンテナ) = CA列
    import_cost_unit: float       # 輸入経費単価 = CB列
    logistics_cost: float         # 物流経費 = CP列
    manufacturing_cost: float     # 製造原価(円) = M列
    jpy_cost: float               # 円建原価 = N列


# ---------------------------------------------------------------------------
# 計算結果 — ギフトセット
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GiftSetResult:
    """ギフトセットの計算結果（全中間値を保持）."""

    towel_cost: float             # タオル代 = AB列
    depreciation_unit: float      # 償却単価 = AZ列
    material_cost: float          # 資材代計 = BC列
    processing_cost: float        # 加工代計 = CG列
    fob_total: float              # FOB合計 = BE列
    loaded_pcs: int               # 積載個数 = BZ列
    cnf: float                    # C&F = BG列
    cif: float                    # CIF = BI列
    tariff: float                 # 関税 = BK列
    import_cost_total: float      # 輸入経費合計 = CA列
    import_cost_unit: float       # 輸入経費単価 = CB列
    logistics_cost: float         # 物流経費 = CP列
    manufacturing_cost: float     # 製造原価 = P列
    quote_price: float            # 見積単価 = M列
    retail_ratio: float           # 上代掛率 = F列
    gross_profit: float           # 粗利単価 = G列
    gross_profit_rate: float      # 粗利率 = H列
    retail_amount: float          # 上代金額 = J列
    sales_amount: float           # 売上金額 = K列
    profit_amount: float          # 粗利金額 = L列
    breakdown_qty: dict[str, int] # 単品別分解数 = AD〜AM列


# ---------------------------------------------------------------------------
# 計算結果 — 集計
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SummaryResult:
    """全ギフトセットの集計結果（行22）."""

    total_quantity: int           # 総数量 = I22
    total_sales: float            # 総売上 = K22
    total_profit: float           # 総粗利 = L22
    avg_profit_rate: float | None  # 平均粗利率 = H22 = L22/K22（売上0で None=計算不能）
