"""A案: Excelライクなテーブル中心 — Streamlit アプリ."""

from __future__ import annotations

import streamlit as st

from quote.ui.sidebar import render_sidebar
from quote.ui.table_view import render_table_view

st.set_page_config(
    page_title="見積もりソフト【A案: テーブル型】",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #FAFBFC; }
    [data-testid="stSidebar"] { background-color: #F0F2F6; }
    [data-testid="stMetricValue"] { font-size: 1.3rem; }
    div[data-testid="stDataFrame"] th {
        background-color: #E8F0FE !important;
        font-weight: 600 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<h1 style="margin-bottom:0;">📊 ステーショナリー見積もり</h1>'
    '<p style="color:#5F6368; margin-top:4px;">A案: Excelライク・テーブル入力</p>',
    unsafe_allow_html=True,
)

params = render_sidebar()
render_table_view(params)
