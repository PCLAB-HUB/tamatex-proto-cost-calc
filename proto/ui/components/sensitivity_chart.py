"""為替感度チャートコンポーネント.

社内為替（cond.internal_rate）を指定範囲でスキャンし、平均原価（円建原価）の
変動を plotly 線グラフで描画する。現在の社内為替を赤の縦破線マーカーで強調する。

注意: 本チャートは社内為替（internal_rate）のみを動かす感度分析であり、
現行為替（current_rate）は固定する。FOB の円換算は社内為替で行うため主要な
感度要因だが、海外運賃・関税・単品輸入経費は現行為替に連動する。したがって
USD 為替が実際に動いた場合の総感度は、ここに表示される値より大きくなりうる。
"""

from __future__ import annotations

from dataclasses import replace

import plotly.graph_objects as go
import streamlit as st

from proto.engine.calc_single import calc_single_item
from proto.engine.models import ImportCondition, SingleItem


def _calc_avg_cost_at_fx(
    fx: float,
    cond: ImportCondition,
    items: list[SingleItem],
) -> float:
    """指定為替レートでの平均原価（円建原価）を算出する.

    Args:
        fx: 適用する社内為替レート（円/USD）
        cond: 輸入条件（internal_rate のみ fx で上書きする）
        items: 計算対象の単品リスト

    Returns:
        全品目の円建原価（jpy_cost）の平均値。
        items が空の場合は 0.0 を返す。
    """
    if not items:
        return 0.0

    cond_at_fx = replace(cond, internal_rate=fx)
    costs = [calc_single_item(item, cond_at_fx).jpy_cost for item in items]
    return sum(costs) / len(costs)


def render_fx_sensitivity_chart(
    cond: ImportCondition,
    items: list[SingleItem],
    *,
    fx_range: tuple[float, float] = (140.0, 160.0),
    steps: int = 11,
) -> None:
    """為替感度チャートを Streamlit 上に描画する.

    横軸に社内為替レート、縦軸に全品目の平均原価（円建原価）をプロットする。
    現在の社内為替（cond.internal_rate）に赤の縦破線マーカーと annotation を追加する。
    現行為替（current_rate）は固定され、社内為替単独の感度を示す。

    Args:
        cond: 輸入条件。internal_rate が「現在値」として強調表示される。
        items: 計算対象の単品リスト。空の場合はチャートを描画しない。
        fx_range: 為替レートのスキャン範囲 (min, max)。デフォルト (140.0, 160.0)。
        steps: スキャンステップ数。デフォルト 11（140, 142, ..., 160）。
    """
    if not items:
        st.info("品目データがありません")
        return

    fx_min, fx_max = fx_range
    fx_values: list[float] = [
        fx_min + i * (fx_max - fx_min) / (steps - 1)
        for i in range(steps)
    ]
    avg_costs: list[float] = [_calc_avg_cost_at_fx(fx, cond, items) for fx in fx_values]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=fx_values,
            y=avg_costs,
            mode="lines+markers",
            name="平均原価",
            hovertemplate="社内為替=%{x:.1f}円: ¥%{y:,.0f}<extra></extra>",
            line={"color": "#1f77b4", "width": 2},
            marker={"size": 8},
        )
    )

    # 現在の社内為替に赤の縦破線マーカーを追加
    fig.add_vline(
        x=cond.internal_rate,
        line_dash="dash",
        line_color="#C62828",
        annotation_text=f"現在: 社内為替={cond.internal_rate:.0f}",
        annotation_position="top",
    )

    fig.update_layout(
        title=f"社内為替感度: 平均原価 (社内為替={fx_min:.0f}〜{fx_max:.0f}円/$)",
        xaxis_title="社内為替 (円/$)",
        yaxis_title="平均原価 (円)",
        height=400,
        hovermode="x unified",
        margin={"l": 40, "r": 40, "t": 60, "b": 40},
    )

    st.plotly_chart(fig, use_container_width=True)
