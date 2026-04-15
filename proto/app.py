"""原価計算プロトタイプ — Streamlit メインアプリ.

起動: streamlit run proto/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# proto パッケージの親ディレクトリ（worktreeルート）をパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

st.set_page_config(
    page_title="原価計算プロトタイプ",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="expanded",
)

from proto.ui.sidebar import render_sidebar
from proto.ui.section_basic import render_basic_info
from proto.ui.section_items import render_items
from proto.ui.section_gift import render_gifts
from proto.ui.section_result import render_results
from proto.ui.section_verify import render_verify


def main() -> None:
    st.title("輸入原価計算プロトタイプ")
    st.caption("Excel原価計算シートの計算ロジックをWebアプリで再現 — デモ用")

    # --- サイドバー: 条件設定 ---
    cond = render_sidebar()

    # --- タブ構成 ---
    tab_basic, tab_items, tab_gifts, tab_results, tab_verify = st.tabs([
        "基本情報",
        "単品タオル",
        "ギフトセット",
        "比較一覧",
        "Excel検証",
    ])

    # --- 単品計算（全タブで使うため先に実行） ---
    with tab_items:
        items, item_results = render_items(cond)

    # --- ギフト計算 ---
    with tab_gifts:
        gifts, gift_results = render_gifts(cond, items, item_results)

    # --- 比較一覧 ---
    with tab_results:
        summary = render_results(gifts, gift_results)

    # --- 基本情報（集計結果を表示するため最後に描画） ---
    with tab_basic:
        render_basic_info(cond, summary)

    # --- Excel検証 ---
    with tab_verify:
        render_verify(item_results, gift_results)


if __name__ == "__main__":
    main()
