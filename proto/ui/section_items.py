"""単品一覧セクション — 6品目の単品タオル表示・計算結果."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from proto.engine.models import ImportCondition, SingleItem, SingleItemResult
from proto.engine.calc_single import calc_single_item
from proto.data.mock_items import ALL_ITEMS


def _build_input_df(items: dict[str, SingleItem]) -> pd.DataFrame:
    """単品入力データをDataFrameに変換."""
    rows = []
    for item in items.values():
        rows.append({
            "品番": item.item_no,
            "品名": item.name,
            "種別": item.item_type,
            "サイズ": item.size,
            "目方(g)": item.weight_g if item.weight_g else "-",
            "織区分": item.weave,
            "ロット": f"{item.lot:,}",
            "FOB($)": item.fob_usd,
        })
    return pd.DataFrame(rows)


def _build_result_df(
    items: dict[str, SingleItem],
    results: dict[str, SingleItemResult],
) -> pd.DataFrame:
    """単品計算結果をDataFrameに変換."""
    rows = []
    for item_no, item in items.items():
        r = results[item_no]
        rows.append({
            "品番": item_no,
            "品名": item.name,
            "種別": item.item_type,
            "FOB(円)": f"{r.fob_jpy:,.2f}",
            "製造原価": f"{r.manufacturing_cost:,.2f}",
            "積載数": f"{r.loaded_pcs:,.0f}" if r.loaded_pcs > 0 else "-",
            "C&F": f"{r.cnf:,.2f}" if r.cnf > 0 else "-",
            "CIF": f"{r.cif:,.2f}" if r.cif > 0 else "-",
            "関税": f"{r.tariff:,.2f}" if r.tariff > 0 else "-",
            "輸入経費/個": f"{r.import_cost_unit:,.2f}" if r.import_cost_unit > 0 else "-",
            "物流/個": f"{r.logistics_cost:,.2f}" if r.logistics_cost > 0 else "-",
            "円建原価": f"{r.jpy_cost:,.2f}",
        })
    return pd.DataFrame(rows)


def render_items(
    cond: ImportCondition,
) -> tuple[dict[str, SingleItem], dict[str, SingleItemResult]]:
    """単品一覧セクションを描画し、計算結果を返す."""
    st.header("単品タオル一覧")

    items = dict(ALL_ITEMS)  # shallow copy

    # --- 入力データ表示 ---
    with st.expander("入力データ", expanded=False):
        st.dataframe(
            _build_input_df(items),
            use_container_width=True,
            hide_index=True,
        )

    # --- 計算実行 ---
    results: dict[str, SingleItemResult] = {}
    for item_no, item in items.items():
        results[item_no] = calc_single_item(item, cond)

    # --- 計算結果テーブル ---
    st.subheader("計算結果")
    st.dataframe(
        _build_result_df(items, results),
        use_container_width=True,
        hide_index=True,
    )

    # --- 個別詳細（折りたたみ） ---
    with st.expander("単品別 計算チェーン詳細", expanded=False):
        for item_no, item in items.items():
            r = results[item_no]
            st.markdown(f"**{item.name} ({item.item_type}) — {item_no}**")
            detail_cols = st.columns(4)
            detail_cols[0].text(f"資材代: {r.material_cost:,.2f}")
            detail_cols[1].text(f"トレス: {r.trace_subtotal:,.2f}")
            detail_cols[2].text(f"償却合計: {r.depreciation_total:,.2f}")
            detail_cols[3].text(f"償却/枚: {r.depreciation_per_unit:,.2f}")
            detail_cols2 = st.columns(4)
            detail_cols2[0].text(f"FOB(円): {r.fob_jpy:,.2f}")
            detail_cols2[1].text(f"輸入経費合計: {r.import_cost_total:,.0f}")
            detail_cols2[2].text(f"輸入経費/個: {r.import_cost_unit:,.2f}")
            detail_cols2[3].text(f"物流/個: {r.logistics_cost:,.2f}")
            st.divider()

    return items, results
