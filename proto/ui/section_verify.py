"""Excel検証セクション — 計算結果とExcel実値の差異比較."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from proto.engine.models import GiftSetResult, SingleItemResult


# Excel実値（テストケースと同一のソース）
# 単品: (品番, 品名, FOB円, 製造原価, C&F, CIF, 関税, 輸入経費/個, 物流/個, 円建原価)
EXCEL_SINGLE_VALUES = [
    ("MOCK-001", "OSD-MOCO BT",  570.0, 570.0, 572.175, 573.205, 42.341, 17.926, 3.16, 636.631),
    ("MOCK-003", "OSD-MOCO FT",  243.0, 243.0, 245.250, 245.691, 18.149, 18.544, 0.0, 282.384),
    ("MOCK-004", "OSD-FUWA FT",  201.0, 201.0, 204.000, 204.367, 15.096, 24.725, 0.0, 244.188),
]

# ギフト: (name, 製造原価, 見積単価, 粗利率, FOB合計, CIF, 関税, 輸入単価, 物流)
EXCEL_GIFT_VALUES = [
    ("FT2 もこ",       1120.064, 1569, 0.1344, 897.165,  906.794,  67.103,  65.667, 80.5),
    ("FT2 ふわ",       1029.685, 1442, 0.1347, 813.165,  822.643,  60.876,  65.667, 80.5),
    ("FT1MT4 もこ",    1499.524, 2100, 0.1332, 1249.845, 1260.109, 93.248,  65.667, 80.5),
    ("FT1MT4 ふわ",    1454.335, 2037, 0.1333, 1207.845, 1218.034, 90.134,  65.667, 80.5),
    ("BT1 もこ",       1167.464, 1635, 0.1403, 941.220,  950.929,  70.369,  65.667, 80.5),
    ("BT1 ふわ",       1072.244, 1502, 0.1346, 852.720,  862.269,  63.808,  65.667, 80.5),
    ("BT1FT2 もこ",    2172.570, 3042, 0.1386, 1659.615, 1682.638, 124.515, 164.167, 201.25),
    ("BT1FT2 ふわ",    1986.972, 2782, 0.1354, 1487.115, 1509.828, 111.727, 164.167, 201.25),
    ("BT1FT1BM1 もこ", 2404.972, 3367, 0.1377, 1875.615, 1899.027, 140.528, 164.167, 201.25),
    ("BT1BM2 もこ",    2637.373, 3693, 0.1370, 2091.615, 2115.416, 156.541, 164.167, 201.25),
    ("BT2 もこ",       2224.812, 3115, 0.1417, 1708.170, 1731.281, 128.115, 164.167, 201.25),
    ("BT2 ふわ",       2034.372, 2849, 0.1350, 1531.170, 1553.962, 114.993, 164.167, 201.25),
]

TOLERANCE = 0.01
RATE_TOLERANCE = 0.001


def _delta_style(val: float) -> str:
    """差異値に応じたスタイル."""
    if abs(val) <= TOLERANCE:
        return "background-color: #d4edda"  # OK
    return "background-color: #f8d7da"  # NG


def render_verify(
    item_results: dict[str, SingleItemResult],
    gift_results: list[GiftSetResult],
) -> None:
    """Excel検証セクションを描画."""
    st.header("Excel実値との検証")
    st.caption("許容誤差: ±0.01円 / 粗利率 ±0.001")

    # --- 単品検証 ---
    st.subheader("単品検証（目方ありの3品目）")
    single_rows = []
    single_ok = 0
    single_total = 0
    for excel_vals in EXCEL_SINGLE_VALUES:
        item_no, name, ex_fob, ex_mfg, ex_cnf, ex_cif, ex_tariff, ex_imp, ex_log, ex_jpy = excel_vals
        r = item_results.get(item_no)
        if r is None:
            continue
        checks = [
            ("FOB(円)", r.fob_jpy, ex_fob),
            ("製造原価", r.manufacturing_cost, ex_mfg),
            ("C&F", r.cnf, ex_cnf),
            ("CIF", r.cif, ex_cif),
            ("関税", r.tariff, ex_tariff),
            ("輸入経費/個", r.import_cost_unit, ex_imp),
            ("物流/個", r.logistics_cost, ex_log),
            ("円建原価", r.jpy_cost, ex_jpy),
        ]
        for label, computed, expected in checks:
            delta = computed - expected
            ok = abs(delta) <= TOLERANCE
            single_total += 1
            if ok:
                single_ok += 1
            single_rows.append({
                "品番": item_no,
                "品名": name,
                "項目": label,
                "計算値": round(computed, 3),
                "Excel値": round(expected, 3),
                "差異": round(delta, 4),
                "判定": "OK" if ok else "NG",
            })

    if single_rows:
        df_s = pd.DataFrame(single_rows)
        styled_s = df_s.style.map(_delta_style, subset=["差異"])
        st.dataframe(styled_s, use_container_width=True, hide_index=True)
        st.success(f"単品: {single_ok}/{single_total} 項目 OK")

    # --- ギフト検証 ---
    st.subheader("ギフト検証（全12パターン）")
    gift_rows = []
    gift_ok = 0
    gift_total = 0
    for idx, excel_vals in enumerate(EXCEL_GIFT_VALUES):
        name, ex_mfg, ex_quote, ex_rate, ex_fob, ex_cif, ex_tariff, ex_imp, ex_log = excel_vals
        if idx >= len(gift_results):
            break
        r = gift_results[idx]
        checks = [
            ("製造原価", r.manufacturing_cost, ex_mfg, TOLERANCE),
            ("見積単価", float(r.quote_price), float(ex_quote), 0.5),
            ("粗利率", r.gross_profit_rate, ex_rate, RATE_TOLERANCE),
            ("FOB合計", r.fob_total, ex_fob, TOLERANCE),
            ("CIF", r.cif, ex_cif, TOLERANCE),
            ("関税", r.tariff, ex_tariff, TOLERANCE),
            ("輸入経費/個", r.import_cost_unit, ex_imp, TOLERANCE),
            ("物流/個", r.logistics_cost, ex_log, TOLERANCE),
        ]
        for label, computed, expected, tol in checks:
            delta = computed - expected
            ok = abs(delta) <= tol
            gift_total += 1
            if ok:
                gift_ok += 1
            gift_rows.append({
                "セット名": name,
                "項目": label,
                "計算値": round(computed, 4),
                "Excel値": round(expected, 4),
                "差異": round(delta, 5),
                "判定": "OK" if ok else "NG",
            })

    if gift_rows:
        df_g = pd.DataFrame(gift_rows)
        styled_g = df_g.style.map(_delta_style, subset=["差異"])
        st.dataframe(styled_g, use_container_width=True, hide_index=True)

        if gift_ok == gift_total:
            st.success(f"ギフト: {gift_ok}/{gift_total} 項目 OK — 全項目一致")
        else:
            ng_count = gift_total - gift_ok
            st.warning(f"ギフト: {gift_ok}/{gift_total} 項目 OK — {ng_count}件の差異あり")

    # --- 総合判定 ---
    st.divider()
    total_ok = single_ok + gift_ok
    total_all = single_total + gift_total
    if total_ok == total_all:
        st.success(f"総合: {total_ok}/{total_all} 項目 全一致")
    else:
        st.info(
            f"総合: {total_ok}/{total_all} 項目一致 "
            f"(パラメータ変更時はExcel値との差異が生じます)"
        )
