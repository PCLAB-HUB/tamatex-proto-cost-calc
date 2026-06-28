"""計算結果表示ページ."""

from __future__ import annotations

import streamlit as st

from quote.engine.models import CostBreakdown, PricingResult, QuoteResult


def _fmt_jpy(v: float) -> str:
    """円表示（整数部のみカンマ区切り）."""
    return f"¥{v:,.1f}"


def _fmt_pct(v: float) -> str:
    """パーセント表示."""
    return f"{v * 100:.1f}%"


def render_cost_breakdown(name: str, cost: CostBreakdown) -> None:
    """原価内訳テーブル."""
    st.subheader(f"📦 {name} — 原価内訳")

    data = {
        "項目": [
            "FOB調整後 (USD)",
            "C&F (円)",
            "CIF (円)",
            "関税 (円)",
            "仕入値 (円/枚)",
            "コンテナ経費 (円/枚)",
            "B品ロス (円/枚)",
            "副資材経費 (円/枚)",
            "償却経費 (円/枚)",
            "物流経費 (円/枚)",
            "加工経費 (円/枚)",
            "製品原価 (円/枚)",
        ],
        "金額": [
            f"${cost.fob_adjusted_usd:.3f}",
            _fmt_jpy(cost.cnf_jpy),
            _fmt_jpy(cost.cif_jpy),
            _fmt_jpy(cost.tariff_jpy),
            _fmt_jpy(cost.purchase_price),
            _fmt_jpy(cost.container_expense_unit),
            _fmt_jpy(cost.b_grade_loss),
            _fmt_jpy(cost.sub_material_cost),
            _fmt_jpy(cost.amortization_actual),
            _fmt_jpy(cost.logistics_unit),
            _fmt_jpy(cost.domestic_processing_unit),
            _fmt_jpy(cost.product_cost),
        ],
    }
    st.table(data)


def render_pricing(label: str, pricing: PricingResult) -> None:
    """価格・粗利の表示."""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("製品原価", _fmt_jpy(pricing.product_cost))
    with col2:
        st.metric("試算売価", _fmt_jpy(pricing.trial_price))
    with col3:
        st.metric("見積売価", _fmt_jpy(pricing.quote_price))
    with col4:
        st.metric(
            "粗利率",
            _fmt_pct(pricing.gross_profit_rate),
            delta=_fmt_jpy(pricing.gross_profit_unit) + "/枚",
        )

    col5, col6, col7 = st.columns(3)
    with col5:
        st.metric("歩積込売価", _fmt_jpy(pricing.stepped_price))
    with col6:
        st.metric("売上金額", _fmt_jpy(pricing.sales_amount))
    with col7:
        st.metric("粗利金額", _fmt_jpy(pricing.gross_profit_total))

    if pricing.retail_price > 0:
        st.caption(
            f"掛率: {_fmt_pct(pricing.retail_ratio)} "
            f"（上代 {_fmt_jpy(pricing.retail_price)}）"
        )


def render_result_page(
    products: list[tuple[str, QuoteResult]],
) -> None:
    """計算結果ページ全体を描画."""
    st.header("計算結果")

    if not products:
        st.info("商品を入力してください。")
        return

    for name, result in products:
        st.divider()
        render_cost_breakdown(name, result.cost)

        tab1, tab2 = st.tabs(["償却込み", "償却別途"])
        with tab1:
            render_pricing("償却込み", result.pricing_with_amort)
        with tab2:
            render_pricing("償却別途", result.pricing_without_amort)
            if result.amortization_separate > 0:
                st.info(f"償却経費別途: {_fmt_jpy(result.amortization_separate)}")

    # 集計
    if len(products) > 1:
        st.divider()
        st.header("全商品集計")
        total_sales = sum(r.pricing_with_amort.sales_amount for _, r in products)
        total_profit = sum(r.pricing_with_amort.gross_profit_total for _, r in products)
        avg_rate = total_profit / total_sales if total_sales > 0 else 0.0

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("売上合計", _fmt_jpy(total_sales))
        with col2:
            st.metric("粗利合計", _fmt_jpy(total_profit))
        with col3:
            st.metric("平均粗利率", _fmt_pct(avg_rate))
