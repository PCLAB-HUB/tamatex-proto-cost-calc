"""原価計算書見積もり（プロト） — 3階層ナビゲーション."""

from __future__ import annotations

import streamlit as st

from quote.data.defaults import TARIFF_RATES
from quote.data.mock_data import seed_mock_data
from quote.engine.models import ContainerExpenses, GlobalParams, ProductInput
from quote.storage.db import (
    get_quote,
    list_customers,
    list_staff,
    save_quote,
)
from quote.storage.settings import load_default_params
from quote.ui.page_detail import render_detail_page
from quote.ui.page_list import render_list_page
from quote.ui.page_product import render_product_page
from quote.ui.page_settings import render_settings_page
from quote.ui.page_customer import render_customer_page
from quote.ui.page_staff import render_staff_page
from quote.ui.sidebar import render_sidebar

seed_mock_data()

st.set_page_config(
    page_title="原価計算書見積もり（プロト）",
    page_icon="📝",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #F8F9FA; }

    /* サイドバー全体 */
    [data-testid="stSidebar"] {
        background-color: #1E293B;
        border-right: none;
    }
    [data-testid="stSidebar"] * {
        color: #E2E8F0 !important;
    }
    [data-testid="stSidebar"] h3 {
        color: #94A3B8 !important;
        font-size: 0.75rem !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    [data-testid="stSidebar"] hr {
        border-color: #334155 !important;
    }

    /* サイドバーのナビボタン */
    [data-testid="stSidebar"] button[kind="secondary"] {
        background-color: #334155 !important;
        border: 1px solid #475569 !important;
        color: #E2E8F0 !important;
        border-radius: 6px !important;
    }
    [data-testid="stSidebar"] button[kind="secondary"]:hover {
        background-color: #475569 !important;
        border-color: #64748B !important;
    }

    /* サイドバーの数値入力 */
    [data-testid="stSidebar"] input {
        background-color: #334155 !important;
        border: 1px solid #475569 !important;
        color: #F1F5F9 !important;
        border-radius: 4px !important;
    }
    [data-testid="stSidebar"] input:focus {
        border-color: #60A5FA !important;
        box-shadow: 0 0 0 1px #60A5FA !important;
    }
    [data-testid="stSidebar"] label {
        color: #CBD5E1 !important;
        font-size: 0.82rem !important;
    }

    /* サイドバーのセクション見出し */
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h4,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h5 {
        color: #60A5FA !important;
        font-size: 0.85rem !important;
    }

    /* サイドバーのexpander */
    [data-testid="stSidebar"] [data-testid="stExpander"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
    }

    /* サイドバーの±ボタン */
    [data-testid="stSidebar"] button[data-testid="stNumberInputStepUp"],
    [data-testid="stSidebar"] button[data-testid="stNumberInputStepDown"] {
        color: #E2E8F0 !important;
        background-color: #475569 !important;
        border-color: #64748B !important;
    }
    /* メインエリアの±ボタン控えめに */
    section.main button[data-testid="stNumberInputStepUp"],
    section.main button[data-testid="stNumberInputStepDown"] { opacity: 0.4; }
    section.main button[data-testid="stNumberInputStepUp"]:hover,
    section.main button[data-testid="stNumberInputStepDown"]:hover { opacity: 1; }

    /* メインエリア */
    [data-testid="stMetricValue"] { font-size: 1.3rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "page" not in st.session_state:
    st.session_state.page = "list"

page = st.session_state.page


def _clear_form_state() -> None:
    for k in list(st.session_state.keys()):
        if k.startswith("sp_") or k.startswith("card_"):
            del st.session_state[k]
    st.session_state.pop("edit_loaded", None)
    st.session_state.pop("product_index", None)


# --- サイドバー ---
with st.sidebar:
    st.markdown("### ナビゲーション")
    if st.button("📋 見積もり一覧", use_container_width=True):
        st.session_state.page = "list"
        _clear_form_state()
        st.rerun()
    if st.button("＋ 新規見積もり", use_container_width=True):
        st.session_state.page = "new"
        _clear_form_state()
        st.rerun()
    if st.button("⚙️ パラメータ設定", use_container_width=True):
        st.session_state.page = "settings"
        _clear_form_state()
        st.rerun()
    if st.button("👤 担当者管理", use_container_width=True):
        st.session_state.page = "staff"
        _clear_form_state()
        st.rerun()
    if st.button("🏢 顧客管理", use_container_width=True):
        st.session_state.page = "customer"
        _clear_form_state()
        st.rerun()
    st.markdown("---")

# パラメータ決定
_initial_params = None
if page in ("detail", "product", "edit_header") and "edit_quote_id" in st.session_state:
    _q = get_quote(st.session_state.edit_quote_id)
    if _q and "params" in _q:
        from dataclasses import fields as dc_fields
        _p = dict(_q["params"])
        _ce_data = _p.pop("container_expenses", {})
        _ce = ContainerExpenses(**{
            f.name: _ce_data.get(f.name, f.default)
            for f in dc_fields(ContainerExpenses)
        })
        _initial_params = GlobalParams(
            **{f.name: _p.get(f.name, f.default)
               for f in dc_fields(GlobalParams)
               if f.name != "container_expenses"},
            container_expenses=_ce,
        )
elif page == "new":
    _initial_params = load_default_params()

if page not in ("settings", "staff", "customer", "list"):
    params = render_sidebar(initial=_initial_params)
else:
    params = _initial_params or GlobalParams()

# --- ヘッダー ---
st.markdown(
    '<h1 style="margin-bottom:0;">📝 原価計算書見積もり（プロト）</h1>',
    unsafe_allow_html=True,
)

# =======================================================================
# 設定
# =======================================================================
if page == "settings":
    render_settings_page()

elif page == "staff":
    render_staff_page()

elif page == "customer":
    render_customer_page()

# =======================================================================
# ① 見積もり一覧
# =======================================================================
elif page == "list":
    render_list_page()

# =======================================================================
# ② 見積もり明細
# =======================================================================
elif page == "detail":
    if "edit_quote_id" in st.session_state:
        render_detail_page(st.session_state.edit_quote_id, params)

# =======================================================================
# ③ 商品計算シート
# =======================================================================
elif page == "product":
    if "edit_quote_id" in st.session_state:
        idx = st.session_state.get("product_index", -1)
        render_product_page(st.session_state.edit_quote_id, idx, params)

# =======================================================================
# 新規作成（ヘッダー入力 → 保存 → 明細へ）
# =======================================================================
elif page == "new":
    st.caption("新規見積もり作成")
    with st.container(border=True):
        st.markdown("##### 見積もり情報")
        h1, h2, h3 = st.columns(3)
        customers = list_customers()
        staff = list_staff()
        cust_names = [c["name"] for c in customers]
        staff_names = [s["name"] for s in staff]

        with h1:
            sel_cust = st.selectbox("顧客 *", cust_names, key="new_customer")
        with h2:
            sel_staff = st.selectbox("担当者 *", staff_names, key="new_staff")
        with h3:
            title = st.text_input(
                "見積もりタイトル", key="new_title",
                placeholder="例: 2026年秋冬カタログ用",
            )
        notes = st.text_area(
            "備考", key="new_notes", height=68,
            placeholder="社内メモ（顧客には表示されません）",
        )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("作成して明細へ進む →", type="primary", use_container_width=True):
            cust_id = customers[cust_names.index(sel_cust)]["id"]
            staff_id = staff[staff_names.index(sel_staff)]["id"]
            new_id = save_quote(
                customer_id=cust_id,
                staff_id=staff_id,
                title=title,
                products=[],
                params=params,
                notes=notes,
            )
            st.session_state.page = "detail"
            st.session_state.edit_quote_id = new_id
            _clear_form_state()
            st.rerun()
    with c2:
        if st.button("← キャンセル", use_container_width=True):
            st.session_state.page = "list"
            st.rerun()

# =======================================================================
# 見積もりヘッダー編集
# =======================================================================
elif page == "edit_header":
    quote = get_quote(st.session_state.get("edit_quote_id", 0))
    if not quote:
        st.error("見積もりが見つかりません。")
    else:
        st.caption(f"編集中: {quote['quote_number']}")
        with st.container(border=True):
            st.markdown("##### 見積もり情報")
            customers = list_customers()
            staff = list_staff()
            cust_names = [c["name"] for c in customers]
            staff_names = [s["name"] for s in staff]

            ci = next(
                (i for i, c in enumerate(customers)
                 if c["id"] == quote.get("customer_id")), 0
            )
            si = next(
                (i for i, s in enumerate(staff)
                 if s["id"] == quote.get("staff_id")), 0
            )

            h1, h2, h3 = st.columns(3)
            with h1:
                sel_cust = st.selectbox("顧客 *", cust_names, index=ci, key="eh_cust")
            with h2:
                sel_staff = st.selectbox("担当者 *", staff_names, index=si, key="eh_staff")
            with h3:
                title = st.text_input(
                    "タイトル", value=quote.get("title") or "", key="eh_title"
                )
            notes = st.text_area(
                "備考", value=quote.get("notes") or "", key="eh_notes", height=68
            )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 保存して明細に戻る", type="primary", use_container_width=True):
                from dataclasses import fields as dc_fields
                all_products = []
                valid_fields = {f.name for f in dc_fields(ProductInput)}
                for item in quote.get("items", []):
                    filtered = {k: v for k, v in item.items() if k in valid_fields}
                    all_products.append(ProductInput(**filtered))
                save_quote(
                    customer_id=customers[cust_names.index(sel_cust)]["id"],
                    staff_id=staff[staff_names.index(sel_staff)]["id"],
                    title=title,
                    products=all_products,
                    params=params,
                    notes=notes,
                    quote_id=quote["id"],
                )
                st.session_state.page = "detail"
                st.rerun()
        with c2:
            if st.button("← 戻る（保存しない）", use_container_width=True):
                st.session_state.page = "detail"
                st.rerun()
