"""計算結果表示・全セット比較一覧セクション."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from proto.engine.calc_summary import calc_summary
from proto.engine.models import GiftSet, GiftSetResult, SummaryResult


def _build_comparison_df(
    gifts: list[GiftSet], results: list[GiftSetResult]
) -> pd.DataFrame:
    """全セット比較テーブルのDataFrame."""
    rows = []
    for gift, r in zip(gifts, results):
        rows.append({
            "セット名": gift.name,
            "販売単価": gift.selling_price,
            "見積単価": r.quote_price,
            "製造原価": round(r.manufacturing_cost, 2),
            "粗利単価": round(r.gross_profit, 2),
            "粗利率(%)": round(r.gross_profit_rate * 100, 1),
            "数量": gift.sales_quantity,
            "売上金額": round(r.sales_amount),
            "粗利金額": round(r.profit_amount),
        })
    return pd.DataFrame(rows)


def _style_profit_rate(val: float) -> str:
    """粗利率に応じた背景色."""
    if val >= 40:
        return "background-color: #d4edda"  # green
    if val >= 30:
        return "background-color: #fff3cd"  # yellow
    return "background-color: #f8d7da"  # red


def render_results(
    gifts: list[GiftSet], results: list[GiftSetResult]
) -> SummaryResult:
    """計算結果・比較一覧セクションを描画し、集計結果を返す."""
    st.header("全セット比較一覧")

    summary = calc_summary(gifts, results)

    # --- 集計サマリー ---
    cols = st.columns(4)
    cols[0].metric("総数量", f"{summary.total_quantity:,} セット")
    cols[1].metric("総売上", f"{summary.total_sales:,.0f} 円")
    cols[2].metric("総粗利", f"{summary.total_profit:,.0f} 円")
    cols[3].metric("平均粗利率", f"{summary.avg_profit_rate:.1%}")

    st.divider()

    # --- 比較テーブル ---
    df = _build_comparison_df(gifts, results)
    styled = df.style.map(
        _style_profit_rate, subset=["粗利率(%)"]
    ).format({
        "販売単価": "{:,.0f}",
        "見積単価": "{:,.0f}",
        "製造原価": "{:,.2f}",
        "粗利単価": "{:,.2f}",
        "粗利率(%)": "{:.1f}%",
        "数量": "{:,}",
        "売上金額": "{:,.0f}",
        "粗利金額": "{:,.0f}",
    })
    st.dataframe(styled, use_container_width=True, hide_index=True)

    # --- 粗利率バーチャート ---
    st.subheader("粗利率比較")
    chart_df = pd.DataFrame({
        "セット名": [g.name for g in gifts],
        "粗利率(%)": [r.gross_profit_rate * 100 for r in results],
    }).set_index("セット名")
    st.bar_chart(chart_df)

    # --- 売上・粗利の積み上げ ---
    st.subheader("売上・粗利構成")
    money_df = pd.DataFrame({
        "セット名": [g.name for g in gifts],
        "粗利金額": [r.profit_amount for r in results],
        "原価金額": [r.sales_amount - r.profit_amount for r in results],
    }).set_index("セット名")
    st.bar_chart(money_df)

    return summary
