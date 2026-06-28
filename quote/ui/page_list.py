"""見積もり一覧・管理ページ."""

from __future__ import annotations

import html

import streamlit as st

from quote.storage.db import delete_quote, list_customers, list_quotes, list_staff


def render_list_page() -> None:
    """見積もり一覧を表示."""
    st.markdown("### 📋 見積もり一覧")

    customers = list_customers()
    staff = list_staff()
    customer_options = {"すべて": None}
    for c in customers:
        customer_options[c["name"]] = c["id"]
    staff_options = {"すべて": None}
    for s in staff:
        staff_options[s["name"]] = s["id"]

    f1, f2, f3 = st.columns([2, 2, 1])
    with f1:
        selected_customer = st.selectbox(
            "顧客", options=list(customer_options.keys()),
            key="list_filter_customer",
        )
    with f2:
        selected_staff = st.selectbox(
            "担当者", options=list(staff_options.keys()),
            key="list_filter_staff",
        )
    with f3:
        st.write("")
        if st.button("＋ 新規見積もり", type="primary", use_container_width=True):
            st.session_state.page = "new"
            st.session_state.pop("edit_quote_id", None)
            st.rerun()

    cid = customer_options[selected_customer]
    sid = staff_options[selected_staff]
    quotes = list_quotes(customer_id=cid, staff_id=sid)

    if not quotes:
        st.info("条件に一致する見積もりがありません。")
        return

    for q in quotes:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 1, 1])
            qnum = html.escape(str(q["quote_number"]))
            title = html.escape(str(q.get("title") or "(無題)"))
            cname = html.escape(str(q.get("customer_name") or "-"))
            sname = html.escape(str(q.get("staff_name") or "-"))
            with c1:
                st.markdown(
                    f"**{qnum}**<br>"
                    f"<span style='font-size:0.85rem;color:#5F6368;'>"
                    f"{title}</span>",
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(
                    f"🏢 {cname}<br>"
                    f"<span style='font-size:0.85rem;'>👤 {sname}</span>",
                    unsafe_allow_html=True,
                )
            with c3:
                status_map = {
                    "draft": "📝 下書き",
                    "submitted": "📤 提出済",
                    "approved": "✅ 承認済",
                }
                status_label = html.escape(
                    str(status_map.get(q["status"], q["status"]))
                )
                updated = html.escape(str(q["updated_at"])[:10])
                st.markdown(
                    f"{status_label}<br>"
                    f"<span style='font-size:0.8rem;color:#5F6368;'>"
                    f"更新: {updated}</span>",
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
