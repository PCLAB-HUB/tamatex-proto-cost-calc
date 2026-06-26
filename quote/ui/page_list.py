"""見積もり一覧・管理ページ."""

from __future__ import annotations

import streamlit as st

from quote.storage.db import delete_quote, list_customers, list_quotes


def render_list_page() -> None:
    """見積もり一覧を表示し、選択された見積もりIDを返す."""
    st.markdown("### 📋 見積もり一覧")

    customers = list_customers()
    customer_options = {"すべて": None}
    for c in customers:
        customer_options[c["name"]] = c["id"]

    col_filter, col_new = st.columns([3, 1])
    with col_filter:
        selected_customer = st.selectbox(
            "顧客でフィルタ",
            options=list(customer_options.keys()),
            key="list_filter_customer",
        )
    with col_new:
        st.write("")
        if st.button("＋ 新規見積もり", type="primary", use_container_width=True):
            st.session_state.page = "new"
            st.session_state.pop("edit_quote_id", None)
            st.rerun()

    cid = customer_options[selected_customer]
    quotes = list_quotes(customer_id=cid)

    if not quotes:
        st.info("見積もりがまだありません。「新規見積もり」から作成してください。")
        return

    for q in quotes:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 1, 1])
            with c1:
                st.markdown(
                    f"**{q['quote_number']}**<br>"
                    f"<span style='font-size:0.85rem;color:#5F6368;'>{q.get('title') or '(無題)'}</span>",
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(
                    f"🏢 {q.get('customer_name', '-')}<br>"
                    f"<span style='font-size:0.85rem;'>👤 {q.get('staff_name', '-')}</span>",
                    unsafe_allow_html=True,
                )
            with c3:
                status_map = {
                    "draft": "📝 下書き",
                    "submitted": "📤 提出済",
                    "approved": "✅ 承認済",
                }
                st.markdown(
                    f"{status_map.get(q['status'], q['status'])}<br>"
                    f"<span style='font-size:0.8rem;color:#5F6368;'>"
                    f"更新: {q['updated_at'][:10]}</span>",
                    unsafe_allow_html=True,
                )
            with c4:
                if st.button("開く", key=f"open_{q['id']}", use_container_width=True):
                    st.session_state.page = "detail"
                    st.session_state.edit_quote_id = q["id"]
                    for k in list(st.session_state.keys()):
                        if k.startswith("sp_") or k.startswith("card_"):
                            del st.session_state[k]
                    st.rerun()
            with c5:
                if st.button("🗑", key=f"del_{q['id']}"):
                    delete_quote(q["id"])
                    st.rerun()
