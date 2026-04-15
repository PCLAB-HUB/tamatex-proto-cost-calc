"""ギフト構成セクション — 12パターンの構成表示・資材・計算結果."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from proto.data.mock_gifts import ALL_GIFTS
from proto.data.mock_items import ALL_ITEMS
from proto.engine.calc_gift import calc_gift_set
from proto.engine.models import (
    GiftSet,
    GiftSetResult,
    ImportCondition,
    SingleItem,
    SingleItemResult,
)


def _composition_str(gift: GiftSet, items: dict[str, SingleItem]) -> str:
    """構成品を '品名×数量' 形式の文字列に変換."""
    parts = []
    for comp in gift.composition:
        item = items.get(comp.item_no)
        name = item.name if item else comp.item_no
        parts.append(f"{name}({item.item_type})×{comp.quantity}" if item else f"{comp.item_no}×{comp.quantity}")
    return " + ".join(parts)


def _build_gift_overview_df(
    gifts: list[GiftSet],
    results: list[GiftSetResult],
    items: dict[str, SingleItem],
) -> pd.DataFrame:
    """ギフト一覧の概要DataFrame."""
    rows = []
    for gift, r in zip(gifts, results):
        rows.append({
            "セット名": gift.name,
            "構成": _composition_str(gift, items),
            "販売単価": f"{gift.selling_price:,.0f}",
            "数量": f"{gift.sales_quantity:,}",
            "見積単価": f"{r.quote_price:,.0f}",
            "製造原価": f"{r.manufacturing_cost:,.2f}",
            "粗利単価": f"{r.gross_profit:,.2f}",
            "粗利率": f"{r.gross_profit_rate:.1%}",
            "売上金額": f"{r.sales_amount:,.0f}",
            "粗利金額": f"{r.profit_amount:,.0f}",
        })
    return pd.DataFrame(rows)


def _render_gift_detail(
    gift: GiftSet,
    result: GiftSetResult,
    items: dict[str, SingleItem],
) -> None:
    """ギフトセット1件の詳細表示."""
    with st.expander(f"{gift.name} — 粗利率 {result.gross_profit_rate:.1%}", expanded=False):
        # 構成
        st.markdown(f"**構成**: {_composition_str(gift, items)}")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("販売単価", f"{gift.selling_price:,.0f} 円")
        col2.metric("見積単価", f"{result.quote_price:,.0f} 円")
        col3.metric("製造原価", f"{result.manufacturing_cost:,.2f} 円")
        col4.metric("粗利率", f"{result.gross_profit_rate:.1%}")

        # 計算チェーン
        st.markdown("**計算チェーン**")
        chain_cols = st.columns(3)
        chain_cols[0].text(f"タオル代: {result.towel_cost:,.2f}")
        chain_cols[0].text(f"資材代計: {result.material_cost:,.2f}")
        chain_cols[0].text(f"加工代計: {result.processing_cost:,.2f}")
        chain_cols[0].text(f"FOB合計: {result.fob_total:,.2f}")

        chain_cols[1].text(f"積載個数: {result.loaded_pcs:,}")
        chain_cols[1].text(f"C&F: {result.cnf:,.2f}")
        chain_cols[1].text(f"CIF: {result.cif:,.2f}")
        chain_cols[1].text(f"関税: {result.tariff:,.2f}")

        chain_cols[2].text(f"輸入経費合計: {result.import_cost_total:,.0f}")
        chain_cols[2].text(f"輸入経費/個: {result.import_cost_unit:,.2f}")
        chain_cols[2].text(f"物流/個: {result.logistics_cost:,.2f}")
        chain_cols[2].text(f"償却/個: {result.depreciation_unit:,.2f}")

        # 資材内訳
        st.markdown("**資材内訳**")
        mat_cols = st.columns(4)
        mat_cols[0].text(f"化粧箱: {gift.gift_box:,.1f}")
        mat_cols[1].text(f"箱入代: {gift.boxing_cost:,.1f}")
        mat_cols[2].text(f"ケース入数: {gift.pcs_per_case}")
        mat_cols[3].text(f"積載ケース: {gift.cases_loaded}")


def render_gifts(
    cond: ImportCondition,
    items: dict[str, SingleItem],
    item_results: dict[str, SingleItemResult],
) -> tuple[list[GiftSet], list[GiftSetResult]]:
    """ギフト構成セクションを描画し、計算結果を返す."""
    st.header("ギフトセット一覧")

    gifts = list(ALL_GIFTS)

    # --- 計算実行 ---
    results: list[GiftSetResult] = []
    for gift in gifts:
        results.append(calc_gift_set(gift, items, item_results, cond))

    # --- 概要テーブル ---
    st.dataframe(
        _build_gift_overview_df(gifts, results, items),
        use_container_width=True,
        hide_index=True,
    )

    # --- 個別詳細 ---
    st.subheader("セット別詳細")
    for gift, result in zip(gifts, results):
        _render_gift_detail(gift, result, items)

    return gifts, results
