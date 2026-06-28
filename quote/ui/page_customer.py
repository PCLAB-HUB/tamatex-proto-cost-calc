"""顧客管理ページ — 登録・編集・削除."""

from __future__ import annotations

import streamlit as st

from quote.storage.db import (
    add_customer,
    delete_customer,
    list_customers,
    update_customer,
)


def render_customer_page() -> None:
    """顧客管理ページを描画."""
    st.markdown("### 🏢 顧客管理")

    customers = list_customers()

    # 新規登録
    with st.container(border=True):
        st.markdown("##### 新規登録")
        c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 3, 1])
        with c1:
            new_name = st.text_input("会社名", key="cust_new_name", placeholder="例: 株式会社山田商事")
        with c2:
            new_contact = st.text_input("担当者名", key="cust_new_contact", placeholder="例: 田中 花子")
        with c3:
            new_phone = st.text_input("電話番号", key="cust_new_phone", placeholder="例: 03-1234-5678")
        with c4:
            new_address = st.text_input("住所", key="cust_new_address", placeholder="例: 東京都渋谷区...")
        with c5:
            st.write("")
            if st.button("登録", type="primary", use_container_width=True):
                if new_name.strip():
                    add_customer(
                        new_name.strip(),
                        new_contact.strip(),
                        new_phone.strip(),
                        new_address.strip(),
                    )
                    st.success(f"「{new_name.strip()}」を登録しました。")
                    st.rerun()
                else:
                    st.error("会社名を入力してください。")

    # 一覧・編集
    if not customers:
        st.info("顧客が登録されていません。")
        return

    st.markdown("##### 登録済み顧客")
    for c in customers:
        with st.container(border=True):
            col1, col2, col3, col4, col5, col6 = st.columns([3, 2, 2, 3, 1, 1])
            with col1:
                edited_name = st.text_input(
                    "会社名", value=c["name"],
                    key=f"cust_name_{c['id']}", label_visibility="collapsed",
                )
            with col2:
                edited_contact = st.text_input(
                    "担当者名", value=c.get("contact_person") or "",
                    key=f"cust_contact_{c['id']}", label_visibility="collapsed",
                    placeholder="担当者名",
                )
            with col3:
                edited_phone = st.text_input(
                    "電話番号", value=c.get("phone") or "",
                    key=f"cust_phone_{c['id']}", label_visibility="collapsed",
                    placeholder="電話番号",
                )
            with col4:
                edited_address = st.text_input(
                    "住所", value=c.get("address") or "",
                    key=f"cust_address_{c['id']}", label_visibility="collapsed",
                    placeholder="住所",
                )
            with col5:
                if st.button("更新", key=f"cust_update_{c['id']}", use_container_width=True):
                    if edited_name.strip():
                        update_customer(
                            c["id"],
                            edited_name.strip(),
                            edited_contact.strip(),
                            edited_phone.strip(),
                            edited_address.strip(),
                        )
                        st.success("更新しました。")
                        st.rerun()
                    else:
                        st.error("会社名は必須です。")
            with col6:
                if st.button("🗑", key=f"cust_del_{c['id']}"):
                    if delete_customer(c["id"]):
                        st.success("削除しました。")
                        st.rerun()
                    else:
                        st.error("この顧客は見積もりで使用中のため削除できません。")
