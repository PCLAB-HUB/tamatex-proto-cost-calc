"""原価計算プロトタイプ — Streamlit メインアプリ (ダッシュボード中心).

起動: streamlit run proto/app.py
"""

from __future__ import annotations

import os
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

from proto.data.mock_gifts import ALL_GIFTS
from proto.data.mock_items import ALL_ITEMS
from proto.engine.calc_gift import calc_gift_set
from proto.engine.calc_single import calc_single_item
from proto.engine.calc_summary import calc_summary
from proto.storage.scenario_repo import ScenarioRepository
from proto.ui.dashboard import render_dashboard
from proto.ui.scenarios import render_scenarios
from proto.ui.section_basic import render_basic_info
from proto.ui.section_gift import render_gifts
from proto.ui.section_items import render_items
from proto.ui.section_result import render_results
from proto.ui.section_verify import render_verify
from proto.ui.sidebar import render_sidebar


@st.cache_resource
def get_scenario_repo() -> ScenarioRepository:
    """ScenarioRepository のシングルトンを返す.

    環境変数 ``TAMATEX_SCENARIO_DB`` が設定されていればそのパスを使用し、
    未設定の場合は ``proto/data/scenarios.db`` をデフォルトパスとする。

    Returns:
        アプリ全体で共有する ScenarioRepository インスタンス。
    """
    default_path = Path(__file__).parent / "data" / "scenarios.db"
    db_path = os.environ.get("TAMATEX_SCENARIO_DB", str(default_path))
    return ScenarioRepository(db_path)


def main() -> None:
    """アプリのメインエントリーポイント.

    タブ構成:
        0. ダッシュボード — KPI・為替感度・品目別ランキング（デフォルト）
        1. 基本情報      — 条件サマリーと集計KPI（render_basic_info 維持）
        2. 単品タオル    — 6品目の計算結果詳細
        3. ギフトセット  — 12パターンの構成・詳細
        4. 比較一覧      — 粗利率バーチャート付き集計
        5. シナリオ      — 保存・読み込み・横並び比較
        6. Excel検証     — 120/120全一致検証
    """
    st.title("輸入原価計算プロトタイプ")
    st.caption("ダッシュボード型 UI — 意思決定支援版")

    repo = get_scenario_repo()
    cond = render_sidebar(repo=repo)

    # ダッシュボード・シナリオ向けに計算を先行実行
    # render_items / render_gifts は副作用（描画）を伴うため、
    # ダッシュボードタブに渡すデータをここで独立して計算する。
    # mock データは 6 品目のみのため二重計算によるパフォーマンス問題はない。
    items = dict(ALL_ITEMS)
    gifts = list(ALL_GIFTS)
    item_results = {no: calc_single_item(it, cond) for no, it in items.items()}
    gift_results = [calc_gift_set(g, items, item_results, cond) for g in gifts]
    summary = calc_summary(gifts, gift_results)

    tabs = st.tabs([
        "🎯 ダッシュボード",
        "📋 基本情報",
        "👕 単品タオル",
        "🎁 ギフトセット",
        "📊 比較一覧",
        "💾 シナリオ",
        "✅ Excel検証",
    ])

    with tabs[0]:
        render_dashboard(cond, items, item_results, gifts, gift_results, summary)

    with tabs[1]:
        # render_basic_info は「総数量・総売上・総粗利・平均粗利率 KPI」と
        # 「条件の詳細パラメータ（為替・マージン・輸入関連）」を表示する。
        # ダッシュボードで代替できない情報を含むため削除せずに維持する。
        render_basic_info(cond, summary)

    with tabs[2]:
        # render_items は内部で calc_single_item を実行して結果を返す（既存挙動維持）
        render_items(cond)

    with tabs[3]:
        # render_gifts は items / item_results を引数に取り内部で calc_gift_set を実行
        render_gifts(cond, items, item_results)

    with tabs[4]:
        render_results(gifts, gift_results)

    with tabs[5]:
        render_scenarios(cond, items, item_results, gifts, gift_results, repo)

    with tabs[6]:
        render_verify(item_results, gift_results)


if __name__ == "__main__":
    main()
