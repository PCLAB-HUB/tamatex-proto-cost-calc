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

st.title("📝 ステーショナリー見積もりソフト")
st.caption("原価計算書参考資料.xlsx ベースのプロトタイプ")

params = render_sidebar()

products = render_input_page()

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
