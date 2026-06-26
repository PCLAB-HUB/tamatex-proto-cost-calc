"""B案: カード+ダッシュボード型 — Streamlit アプリ."""

from __future__ import annotations

import streamlit as st

from quote.ui.card_view import render_card_view
from quote.ui.sidebar import render_sidebar

st.set_page_config(
    page_title="見積もりソフト【B案: カード型】",
    page_icon="📝",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #F8F9FA; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E8EAED; }
    [data-testid="stMetricValue"] { font-size: 1.3rem; }
    [data-testid="stExpander"] {
        background-color: #FFFFFF;
        border: 1px solid #E8EAED;
        border-radius: 8px;
    }
    /* number_input の ± ボタンを控えめに */
    button[data-testid="stNumberInputStepUp"],
    button[data-testid="stNumberInputStepDown"] {
        opacity: 0.4;
    }
    button[data-testid="stNumberInputStepUp"]:hover,
    button[data-testid="stNumberInputStepDown"]:hover {
        opacity: 1;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<h1 style="margin-bottom:0;">📝 ステーショナリー見積もり</h1>'
    '<p style="color:#5F6368; margin-top:4px;">B案: カード＋ダッシュボード</p>',
    unsafe_allow_html=True,
)

params = render_sidebar()
render_card_view(params)
