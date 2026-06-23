"""基本情報セクション — 選択中の条件サマリーとKPIカード."""

from __future__ import annotations

import streamlit as st

from proto.engine.models import ImportCondition, SummaryResult


def render_basic_info(cond: ImportCondition, summary: SummaryResult | None) -> None:
    """条件サマリーと集計KPIを表示."""
    st.header("基本情報")

    # --- KPIカード（集計結果がある場合） ---
    if summary is not None:
        cols = st.columns(4)
        cols[0].metric("総数量", f"{summary.total_quantity:,} セット")
        cols[1].metric("総売上", f"{summary.total_sales:,.0f} 円")
        cols[2].metric("総粗利", f"{summary.total_profit:,.0f} 円")
        cols[3].metric(
            "平均粗利率",
            f"{summary.avg_profit_rate:.1%}"
            if summary.avg_profit_rate is not None
            else "計算不能",
        )

    st.divider()

    # --- 条件サマリーテーブル ---
    st.subheader(f"条件: {cond.name}")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**為替**")
        st.text(f"社内: {cond.internal_rate:.0f} 円/$")
        st.text(f"現行: {cond.current_rate:.0f} 円/$")

    with col2:
        st.markdown("**マージン・ロス**")
        st.text(f"マージン: {cond.margin_pct:.0f}%")
        st.text(f"ロス率: {cond.loss_rate_pct:.0f}%")
        st.text(f"資材ロット: {cond.material_lot:,}")
        st.text(f"資材ロス率: {cond.material_loss_pct:.1f}%")

    with col3:
        st.markdown("**輸入**")
        st.text(f"海外運賃: ${cond.overseas_freight_usd:.0f}")
        st.text(f"保険率: {cond.insurance_rate:.4f}")
        st.text(f"関税率: {cond.tariff_rate:.3f}")
