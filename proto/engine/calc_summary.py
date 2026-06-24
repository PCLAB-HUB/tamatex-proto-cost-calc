"""集計計算 — 全ギフトセットの合算.

Excelの「ひな形」シート行22の集計行に対応。

  I22 = SUM(I23:I42)   ... 総数量
  K22 = SUM(K23:K42)   ... 総売上
  L22 = SUM(L23:L42)   ... 総粗利
  H22 = L22 / K22      ... 平均粗利率
"""

from __future__ import annotations

from proto.engine.models import GiftSet, GiftSetResult, SummaryResult


def calc_summary(
    gifts: list[GiftSet],
    results: list[GiftSetResult],
) -> SummaryResult:
    """全ギフトセットの集計.

    Args:
        gifts: ギフトセットデータのリスト（数量取得用）
        results: 各ギフトセットの計算結果リスト

    Returns:
        集計結果
    """
    if len(gifts) != len(results):
        raise ValueError(
            f"gifts({len(gifts)}件)とresults({len(results)}件)の長さが一致しません"
        )
    total_quantity = sum(g.sales_quantity for g in gifts)
    total_sales = sum(r.sales_amount for r in results)
    total_profit = sum(r.profit_amount for r in results)
    # 売上0では粗利率が計算不能（0除算）。0% と表示すると赤字が中立に
    # 見えてしまうため None（計算不能）を返す。
    avg_profit_rate = total_profit / total_sales if total_sales > 0 else None

    return SummaryResult(
        total_quantity=total_quantity,
        total_sales=total_sales,
        total_profit=total_profit,
        avg_profit_rate=avg_profit_rate,
    )
