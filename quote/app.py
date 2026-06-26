"""ステーショナリー見積もりソフト — Streamlit アプリケーション."""

from __future__ import annotations

import streamlit as st

from quote.engine.calc import calculate
from quote.engine.container import estimate_container_load
from quote.engine.models import ProductInput, QuoteResult
from quote.ui.page_input import render_input_page
from quote.ui.page_result import render_result_page
from quote.ui.sidebar import render_sidebar

st.set_page_config(
    page_title="ステーショナリー見積もりソフト",
    page_icon="📝",
    layout="wide",
)

st.markdown(
    """
    <style>
    /* セクション見出しを控えめに */
    .stMarkdown h5 {
        color: #888;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.8rem;
        margin-bottom: 0.3rem;
        border-bottom: 1px solid #333;
        padding-bottom: 0.2rem;
    }
    /* メトリクスカードの数値を少し大きく */
    [data-testid="stMetricValue"] {
        font-size: 1.4rem;
    }
    /* 商品コンテナの余白調整 */
    [data-testid="stVerticalBlock"] > div[data-testid="stExpander"] {
        margin-top: 0.2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📝 ステーショナリー見積もりソフト")
st.caption("原価計算書参考資料.xlsx ベースのプロトタイプ")

params = render_sidebar()

products = render_input_page()

if products:
    st.divider()

    results: list[tuple[str, QuoteResult]] = []

    for product in products:
        p = product
        if p.container_load <= 0 and p.package_size_cm:
            estimated = estimate_container_load(
                p.package_size_cm, p.packing_quantity, p.container_ft
            )
            if estimated is not None:
                p = ProductInput(
                    **{
                        k: v
                        for k, v in p.__dict__.items()
                        if k != "container_load"
                    },
                    container_load=estimated,
                )

        result = calculate(p, params)
        results.append((p.product_name, result))

    render_result_page(results)
