"""KPIカードコンポーネント — ダッシュボードと比較ビューで共用."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class KPICardData:
    """KPIカード1枚分のデータ."""

    label: str
    value: str
    sublabel: str = ""
    delta: str | None = None
    delta_color: Literal["normal", "inverse", "off"] = "normal"


def format_currency(amount: float, *, show_yen: bool = True) -> str:
    """数値を通貨文字列に変換する。

    Args:
        amount: 金額（円）。
        show_yen: True のとき先頭に "¥" を付ける。

    Returns:
        千の桁区切り付き文字列（例: "¥1,234"）。
    """
    prefix = "¥" if show_yen else ""
    return f"{prefix}{amount:,.0f}"


def format_percentage(value: float, *, decimals: int = 1) -> str:
    """数値をパーセンテージ文字列に変換する。

    Args:
        value: パーセント値（例: 50.67）。
        decimals: 小数点以下の桁数（デフォルト: 1）。

    Returns:
        パーセント文字列（例: "50.7%"）。
    """
    return f"{value:.{decimals}f}%"


def format_delta(
    current: float,
    baseline: float,
    *,
    is_currency: bool = False,
) -> str:
    """現在値とベースラインの差分を表示用文字列に変換する。

    Args:
        current: 現在の値。
        baseline: 比較基準となる値。
        is_currency: True のとき通貨形式（例: "+¥500"）、
                     False のときパーセント形式（例: "+5.0%"）。

    Returns:
        符号付きの差分文字列。
    """
    diff = current - baseline
    sign = "+" if diff >= 0 else "-"
    abs_diff = abs(diff)
    if is_currency:
        return f"{sign}¥{abs_diff:,.0f}"
    return f"{sign}{abs_diff:.1f}%" if diff < 0 else f"+{abs_diff:.1f}%"


def render_kpi_card(
    label: str,
    value: str,
    sublabel: str = "",
    delta: str | None = None,
    delta_color: Literal["normal", "inverse", "off"] = "normal",
) -> None:
    """単独KPIカードを描画する。

    Args:
        label: カードのラベル（タイトル）。
        value: 主値（大きな文字で表示）。
        sublabel: 補足テキスト（小さく表示）。
        delta: 差分テキスト（省略時は非表示）。
        delta_color: 差分の色方向（"normal" / "inverse" / "off"）。
    """
    import streamlit as st

    st.metric(label=label, value=value, delta=delta, delta_color=delta_color)
    if sublabel:
        st.caption(sublabel)


def render_kpi_row(cards: list[KPICardData]) -> None:
    """複数KPIカードを横並びで描画する。

    `st.columns(len(cards))` で均等分割し、各カラムに1枚ずつ配置する。
    全カードの描画後に `style_metric_cards()` で統一スタイルを適用する。

    Args:
        cards: 表示するカードデータのリスト。空リスト時は何もしない。
    """
    if not cards:
        return

    import streamlit as st
    from streamlit_extras.metric_cards import style_metric_cards

    from proto.ui.components.styles import CARD_BACKGROUND, CARD_BORDER, CARD_BORDER_LEFT

    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        with col:
            render_kpi_card(
                label=card.label,
                value=card.value,
                sublabel=card.sublabel,
                delta=card.delta,
                delta_color=card.delta_color,
            )

    style_metric_cards(
        background_color=CARD_BACKGROUND,
        border_left_color=CARD_BORDER_LEFT,
        border_color=CARD_BORDER,
    )


# ---------------------------------------------------------------------------
# デモ（コメントアウト版）
# ---------------------------------------------------------------------------
# 以下は `streamlit run proto/ui/components/kpi_cards.py` で動作確認できる。
#
# if __name__ == "__main__":
#     import streamlit as st
#
#     st.title("KPIカード デモ")
#     demo_cards = [
#         KPICardData(
#             label="総原価（単品合計）",
#             value=format_currency(1_234_567),
#             sublabel="20FT コンテナ条件",
#             delta=format_delta(1_234_567, 1_200_000, is_currency=True),
#         ),
#         KPICardData(
#             label="平均粗利率",
#             value=format_percentage(38.5),
#             sublabel="6品目加重平均",
#             delta=format_delta(38.5, 35.0),
#             delta_color="normal",
#         ),
#         KPICardData(
#             label="総販売数",
#             value="12,480 pcs",
#             sublabel="全品番合計",
#         ),
#     ]
#     render_kpi_row(demo_cards)
