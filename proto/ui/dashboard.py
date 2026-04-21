"""ダッシュボードタブ — KPI・為替感度・品目別原価ランキング表示.

営業・役員・社長が開いた瞬間に主要 KPI・為替感度・品目別原価ランキングを
一目で把握できるトップビュー。渡された計算結果を集計して表示するだけで、
計算ロジックは一切追加しない。
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from proto.engine.models import (
    GiftSet,
    GiftSetResult,
    ImportCondition,
    SingleItem,
    SingleItemResult,
    SummaryResult,
)
from proto.ui.components.kpi_cards import (
    KPICardData,
    format_currency,
    format_delta,
    format_percentage,
    render_kpi_row,
)
from proto.ui.components.sensitivity_chart import render_fx_sensitivity_chart


def _render_header(cond: ImportCondition) -> None:
    """現在の輸入条件サマリをヘッダー帯として表示する.

    Args:
        cond: 輸入条件パラメータ。
    """
    st.markdown(
        f"#### 🚢 {cond.name} | 💱 USD={cond.internal_rate:.0f} | 🎯 マージン目標 {cond.margin_pct:.0f}%"
    )
    st.divider()


def _render_kpi_cards(
    item_results: dict[str, SingleItemResult],
    target_margin_pct: float,
) -> None:
    """KPIカード3枚（平均原価・平均上代・平均粗利率）を表示する.

    Args:
        item_results: 単品計算結果（品番キーの dict）。
        target_margin_pct: マージン目標値（%、例: 50.0）。
    """
    if not item_results:
        st.info("品目データがありません")
        return

    results = list(item_results.values())
    avg_cost = sum(r.jpy_cost for r in results) / len(results)

    # 上代 = 原価 / (1 - マージン率)
    margin_rate = target_margin_pct / 100.0
    avg_retail = avg_cost / (1.0 - margin_rate) if margin_rate < 1.0 else 0.0

    # 実効粗利率（%）= マージン目標と同一（逆算なので一致するが明示的に計算）
    actual_margin_pct = (
        (avg_retail - avg_cost) / avg_retail * 100.0 if avg_retail > 0.0 else 0.0
    )

    cards = [
        KPICardData(
            label="平均原価",
            value=format_currency(avg_cost),
            sublabel=f"{len(results)}品目の平均",
        ),
        KPICardData(
            label="平均上代",
            value=format_currency(avg_retail),
            sublabel=f"（マージン{target_margin_pct:.0f}%想定）",
        ),
        KPICardData(
            label="平均粗利率",
            value=format_percentage(actual_margin_pct),
            sublabel=(
                f"目標 {target_margin_pct:.0f}% との差: "
                f"{format_delta(actual_margin_pct, target_margin_pct)}"
            ),
            delta=format_delta(actual_margin_pct, target_margin_pct),
            delta_color="normal",
        ),
    ]
    render_kpi_row(cards)


def _render_item_ranking(
    items: dict[str, SingleItem],
    item_results: dict[str, SingleItemResult],
) -> None:
    """品目別原価ランキングを横棒グラフで表示する.

    品目を円建原価の昇順で並べ、最安値を緑・最高値を赤でハイライトする。

    Args:
        items: 単品入力データ（品番キーの dict）。
        item_results: 単品計算結果（品番キーの dict）。
    """
    st.subheader("品目別原価ランキング")

    if not item_results:
        st.info("品目データがありません")
        return

    # 品番キーで紐付けて昇順ソート
    pairs = sorted(
        [(items[k], item_results[k]) for k in item_results if k in items],
        key=lambda p: p[1].jpy_cost,
    )

    if not pairs:
        st.info("品目データがありません")
        return

    names = [p[0].name for p in pairs]
    costs = [p[1].jpy_cost for p in pairs]

    min_cost = min(costs)
    max_cost = max(costs)

    # 最安値: 緑、最高値: 赤、それ以外: 標準青
    colors = []
    for c in costs:
        if c == min_cost:
            colors.append("#2E7D32")
        elif c == max_cost:
            colors.append("#C62828")
        else:
            colors.append("#1f77b4")

    fig = go.Figure(
        go.Bar(
            x=costs,
            y=names,
            orientation="h",
            marker={"color": colors},
            text=[format_currency(c) for c in costs],
            textposition="outside",
            hovertemplate="%{y}: ¥%{x:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        xaxis_title="円建原価（円）",
        height=max(300, 60 * len(names)),
        margin={"l": 120, "r": 120, "t": 30, "b": 40},
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_gift_summary_cards(
    gifts: list[GiftSet],
    gift_results: list[GiftSetResult],
) -> None:
    """ギフトセットの最大・最小粗利カードを2カラムで表示する.

    Args:
        gifts: ギフトセット入力データのリスト。
        gift_results: ギフトセット計算結果のリスト（gifts と同順）。
    """
    st.subheader("ギフトセット サマリ")

    if not gift_results:
        st.info("ギフトデータがありません")
        return

    pairs = list(zip(gifts, gift_results))

    # gross_profit_rate は 0〜1 の小数
    max_pair = max(pairs, key=lambda p: p[1].gross_profit_rate)
    min_pair = min(pairs, key=lambda p: p[1].gross_profit_rate)

    col_max, col_min = st.columns(2)

    with col_max:
        st.markdown("**🥇 最大粗利**")
        st.markdown(f"**{max_pair[0].name}**")
        st.metric(
            label="粗利率",
            value=f"{max_pair[1].gross_profit_rate:.1%}",
            delta=f"原価 {format_currency(max_pair[1].manufacturing_cost)}",
        )

    with col_min:
        st.markdown("**📉 最小粗利**")
        st.markdown(f"**{min_pair[0].name}**")
        st.metric(
            label="粗利率",
            value=f"{min_pair[1].gross_profit_rate:.1%}",
            delta=f"原価 {format_currency(min_pair[1].manufacturing_cost)}",
        )


def render_dashboard(
    cond: ImportCondition,
    items: dict[str, SingleItem],
    item_results: dict[str, SingleItemResult],
    gifts: list[GiftSet],
    gift_results: list[GiftSetResult],
    summary: SummaryResult,
) -> None:
    """ダッシュボードタブを描画する.

    KPI カード・為替感度チャート・品目別原価ランキング・ギフトサマリを
    上から順に表示する。計算ロジックは一切含まず、渡された結果を集計して
    表示するだけ。空データでも例外を投げない。

    Args:
        cond: 輸入条件パラメータ。
        items: 単品入力データ（品番キーの dict）。
        item_results: 単品計算結果（品番キーの dict）。
        gifts: ギフトセット入力データのリスト。
        gift_results: ギフトセット計算結果のリスト（gifts と同順）。
        summary: 全ギフトセットの集計結果（現バージョンでは参照のみ）。
    """
    _render_header(cond)
    _render_kpi_cards(item_results, target_margin_pct=cond.margin_pct)
    st.divider()

    st.subheader("為替感度チャート")
    render_fx_sensitivity_chart(cond, list(items.values()))
    st.divider()

    _render_item_ranking(items, item_results)
    st.divider()

    _render_gift_summary_cards(gifts, gift_results)
