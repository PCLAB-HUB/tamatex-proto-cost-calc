"""ステーショナリー見積もりソフト — カード+ダッシュボード型."""

from __future__ import annotations

import streamlit as st

from quote.data.mock_data import seed_mock_data
from quote.engine.models import GlobalParams, ProductInput
from quote.storage.db import (
    get_quote,
    list_customers,
    list_staff,
    save_quote,
)
from quote.ui.card_view import render_card_view
from quote.ui.page_list import render_list_page
from quote.ui.sidebar import render_sidebar

seed_mock_data()

st.set_page_config(
    page_title="ステーショナリー見積もりソフト",
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

# --- ページルーティング ---
if "page" not in st.session_state:
    st.session_state.page = "list"

page = st.session_state.page

# --- サイドバー: 共通パラメータ + ナビゲーション ---
with st.sidebar:
    st.markdown("### ナビゲーション")
    if st.button("📋 見積もり一覧", use_container_width=True):
        st.session_state.page = "list"
        st.session_state.pop("edit_loaded", None)
        st.rerun()
    if st.button("＋ 新規見積もり", use_container_width=True):
        st.session_state.page = "new"
        st.session_state.pop("edit_quote_id", None)
        st.session_state.pop("edit_loaded", None)
        st.rerun()
    st.markdown("---")

params = render_sidebar()

# --- ヘッダー ---
st.markdown(
    '<h1 style="margin-bottom:0;">📝 ステーショナリー見積もり</h1>',
    unsafe_allow_html=True,
)

# =======================================================================
# 見積もり一覧
# =======================================================================
if page == "list":
    render_list_page()

# =======================================================================
# 新規作成 / 編集
# =======================================================================
elif page in ("new", "edit"):
    editing_quote = None
    if page == "edit" and "edit_quote_id" in st.session_state:
        editing_quote = get_quote(st.session_state.edit_quote_id)

    if editing_quote:
        st.caption(f"編集中: {editing_quote['quote_number']}")
    else:
        st.caption("新規見積もり作成")

    # 見積もり情報ヘッダー
    with st.container(border=True):
        st.markdown("##### 見積もり情報")
        h1, h2, h3 = st.columns(3)
        customers = list_customers()
        staff = list_staff()

        cust_names = [c["name"] for c in customers]
        staff_names = [s["name"] for s in staff]

        default_cust_idx = 0
        default_staff_idx = 0
        default_title = ""
        default_notes = ""

        if editing_quote:
            for i, c in enumerate(customers):
                if c["id"] == editing_quote.get("customer_id"):
                    default_cust_idx = i
                    break
            for i, s in enumerate(staff):
                if s["id"] == editing_quote.get("staff_id"):
                    default_staff_idx = i
                    break
            default_title = editing_quote.get("title") or ""
            default_notes = editing_quote.get("notes") or ""

        with h1:
            selected_customer = st.selectbox(
                "顧客 *",
                cust_names,
                index=default_cust_idx,
                key="quote_customer",
            )
        with h2:
            selected_staff = st.selectbox(
                "担当者 *",
                staff_names,
                index=default_staff_idx,
                key="quote_staff",
            )
        with h3:
            quote_title = st.text_input(
                "見積もりタイトル",
                value=default_title,
                key="quote_title",
                placeholder="例: 2026年秋冬カタログ用",
            )

        quote_notes = st.text_area(
            "備考",
            value=default_notes,
            key="quote_notes",
            height=68,
            placeholder="社内メモ（顧客には表示されません）",
        )

    # 保存済み商品をフォームに流し込む（初回のみ）
    if editing_quote and "edit_loaded" not in st.session_state:
        items = editing_quote.get("items", [])
        st.session_state["card_num_products"] = max(len(items), 1)
        for i, item in enumerate(items):
            _prefix = f"card_{i}"
            st.session_state[f"{_prefix}_name"] = item.get("product_name", "")
            st.session_state[f"{_prefix}_code"] = str(item.get("prototype_code", ""))
            st.session_state[f"{_prefix}_size"] = item.get("package_size_cm", "")
            st.session_state[f"{_prefix}_wt"] = float(item.get("weight_g", 0))
            st.session_state[f"{_prefix}_pk"] = int(item.get("packing_quantity", 1))
            st.session_state[f"{_prefix}_ld"] = float(item.get("container_load", 0))
            st.session_state[f"{_prefix}_fob"] = float(item.get("fob_usd", 0))
            st.session_state[f"{_prefix}_op"] = float(item.get("other_processing_usd", 0))
            st.session_state[f"{_prefix}_loss"] = float(item.get("loss_rate", 0))
            st.session_state[f"{_prefix}_qp"] = float(item.get("quote_price", 0))
            st.session_state[f"{_prefix}_lot"] = int(item.get("lot_per_color", 0))
            st.session_state[f"{_prefix}_col"] = int(item.get("num_colors", 1))
            st.session_state[f"{_prefix}_ret"] = float(item.get("retail_price", 0))
            st.session_state[f"{_prefix}_lio"] = float(item.get("logistics_io_fee", 70))
            st.session_state[f"{_prefix}_lsl"] = float(item.get("logistics_slip_fee", 100))
            st.session_state[f"{_prefix}_lm"] = float(item.get("logistics_storage_months", 1))
            st.session_state[f"{_prefix}_lf"] = float(item.get("logistics_storage_fee", 150))
            st.session_state[f"{_prefix}_lr"] = float(item.get("logistics_freight", 700))
            st.session_state[f"{_prefix}_cf"] = float(item.get("center_fee", 0))
        st.session_state["edit_loaded"] = True
        st.rerun()

    st.markdown("---")

    # 商品入力
    products, results = render_card_view(params)

    # 保存ボタン
    st.markdown("---")
    save_col1, save_col2, save_col3 = st.columns([2, 2, 4])
    with save_col1:
        if st.button("💾 保存", type="primary", use_container_width=True):
            if not products:
                st.error("商品を1つ以上入力してください。")
            else:
                cust_id = customers[cust_names.index(selected_customer)]["id"]
                staff_id = staff[staff_names.index(selected_staff)]["id"]
                qid = editing_quote["id"] if editing_quote else None
                saved_id = save_quote(
                    customer_id=cust_id,
                    staff_id=staff_id,
                    title=quote_title,
                    products=products,
                    params=params,
                    notes=quote_notes,
                    quote_id=qid,
                )
                st.success(f"保存しました (ID: {saved_id})")
                st.session_state.page = "list"
                st.rerun()
    with save_col2:
        if st.button("← 一覧に戻る", use_container_width=True):
            st.session_state.page = "list"
            st.rerun()
