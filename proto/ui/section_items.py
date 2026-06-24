"""単品一覧セクション — 6品目の単品タオル表示・計算結果."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from proto.engine.models import ImportCondition, SingleItem, SingleItemResult
from proto.engine.calc_single import calc_single_item
from proto.data.mock_items import ALL_ITEMS
from proto.ui.components.aggrid_table import (
    create_aggrid,
    currency_column,
    number_column,
    text_column,
)


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
            "FOB(円)": r.fob_jpy,
            "製造原価": r.manufacturing_cost,
            "積載数": r.loaded_pcs if r.loaded_pcs > 0 else None,
            "C&F": r.cnf if r.cnf > 0 else None,
            "CIF": r.cif if r.cif > 0 else None,
            "関税": r.tariff if r.tariff > 0 else None,
            "輸入経費/個": r.import_cost_unit if r.import_cost_unit > 0 else None,
            "物流/個": r.logistics_cost if r.logistics_cost > 0 else None,
            "円建原価": r.jpy_cost,
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
        input_columns = [
            text_column("品番", "品番", width=100),
            text_column("品名", "品名", width=160),
            text_column("種別", "種別", width=80),
            text_column("サイズ", "サイズ", width=100),
            text_column("目方(g)", "目方(g)", width=80),
            text_column("織区分", "織区分", width=80),
            text_column("ロット", "ロット", width=90),
            currency_column("FOB($)", "FOB($)", width=100),
        ]
        create_aggrid(
            _build_input_df(items),
            input_columns,
            selection="none",
            height=280,
        )

    # --- 計算実行 ---
    results: dict[str, SingleItemResult] = {}
    for item_no, item in items.items():
        results[item_no] = calc_single_item(item, cond)

    # --- 計算結果テーブル ---
    st.subheader("計算結果")
    result_columns = [
        text_column("品番", "品番", width=100),
        text_column("品名", "品名", width=160),
        text_column("種別", "種別", width=80),
        currency_column("FOB(円)", "FOB(円)"),
        currency_column("製造原価", "製造原価"),
        number_column("積載数", "積載数", decimals=0, width=90),
        currency_column("C&F", "C&F"),
        currency_column("CIF", "CIF"),
        currency_column("関税", "関税"),
        currency_column("輸入経費/個", "輸入経費/個"),
        currency_column("物流/個", "物流/個"),
        currency_column("円建原価", "円建原価"),
    ]
    create_aggrid(
        _build_result_df(items, results),
        result_columns,
        selection="none",
        height=320,
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
