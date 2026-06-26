"""担当者管理ページ — 登録・編集・削除."""

from __future__ import annotations

import streamlit as st

from quote.storage.db import add_staff, delete_staff, list_staff, update_staff


def render_staff_page() -> None:
    """担当者管理ページを描画."""
    st.markdown("### 👤 担当者管理")

    staff = list_staff()

    # 新規登録
    with st.container(border=True):
        st.markdown("##### 新規登録")
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            new_name = st.text_input("氏名", key="staff_new_name", placeholder="例: 山田 太郎")
        with c2:
            new_dept = st.text_input("部署", key="staff_new_dept", placeholder="例: 営業部")
        with c3:
            st.write("")
            if st.button("登録", type="primary", use_container_width=True):
                if new_name.strip():
                    add_staff(new_name.strip(), new_dept.strip())
                    st.success(f"「{new_name.strip()}」を登録しました。")
                    st.rerun()
                else:
                    st.error("氏名を入力してください。")

    # 一覧・編集
    if not staff:
        st.info("担当者が登録されていません。")
        return

    st.markdown("##### 登録済み担当者")
    for s in staff:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
            with c1:
                edited_name = st.text_input(
                    "氏名", value=s["name"],
                    key=f"staff_name_{s['id']}", label_visibility="collapsed",
                )
            with c2:
                edited_dept = st.text_input(
                    "部署", value=s.get("department") or "",
                    key=f"staff_dept_{s['id']}", label_visibility="collapsed",
                    placeholder="部署",
                )
            with c3:
                if st.button("更新", key=f"staff_update_{s['id']}", use_container_width=True):
                    if edited_name.strip():
                        update_staff(s["id"], edited_name.strip(), edited_dept.strip())
                        st.success("更新しました。")
                        st.rerun()
            with c4:
                if st.button("🗑", key=f"staff_del_{s['id']}"):
                    if delete_staff(s["id"]):
                        st.success("削除しました。")
                        st.rerun()
                    else:
                        st.error("この担当者は見積もりで使用中のため削除できません。")
