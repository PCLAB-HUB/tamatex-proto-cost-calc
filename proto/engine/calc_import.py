"""輸入経費・物流経費の共通計算関数.

Excelの CA列（輸入経費合計）、CB列（輸入経費単価）、CP列（物流経費単価）に対応。
単品計算とギフト計算の両方から呼ばれる。

重要な差異:
  - 単品層: CA = BO × $N$4(現行為替) + (BM+BN+BP+BQ+BR+BS+BT+BU+BV+BW)
  - ギフト層: CA = BO × $M$4(社内為替) + (BM+BN+BP+BQ+BR+BS+BT+BU+BV+BW)
  - さらに単品/ギフトでBM-BWの値自体が異なる（BQ, BWに差異）
  呼び出し側で適切なImportExpensesとexchange_rateを渡す。
"""

from __future__ import annotations

from proto.engine.models import ImportExpenses


def calc_import_cost_total(expenses: ImportExpenses, exchange_rate: float) -> float:
    """輸入経費合計(コンテナ単位) = CA列.

    CA = BO(cic_usd) × exchange_rate + BM + BN + BP + BQ + BR + BS + BT + BU + BV + BW

    Args:
        expenses: 輸入経費11項目
        exchange_rate: 為替レート（単品=$N$4=現行為替, ギフト=$M$4=社内為替）

    Returns:
        輸入経費合計(円)
    """
    cic_jpy = expenses.cic_usd * exchange_rate  # BO × 為替
    jpy_total = (
        expenses.cy_charge
        + expenses.thc
        + expenses.emc
        + expenses.cic2
        + expenses.do_fee
        + expenses.doc_fee
        + expenses.customs_fee
        + expenses.handling_fee
        + expenses.drayage
        + expenses.devanning
    )
    return cic_jpy + jpy_total


def calc_import_cost_unit(import_cost_total: float, loaded_pcs: float) -> float:
    """輸入経費単価 = CB列 = CA / BZ.

    Args:
        import_cost_total: 輸入経費合計(円)
        loaded_pcs: 積載個数

    Returns:
        輸入経費単価(円/個)。積載個数が0の場合は0を返す。
    """
    if loaded_pcs == 0:
        return 0.0
    return import_cost_total / loaded_pcs


def calc_logistics_cost(
    freight_per_case: float,
    packing_cost: float,
    other_logistics: float,
    cl: float,
    cm: float,
    cn: float,
    pcs_per_case: int,
) -> float:
    """物流経費単価 = CP列 = (CI + CJ + CK + CL + CM×CN) / CO.

    CO = BX（ケース入数）

    Args:
        freight_per_case: 運賃/ケース CI列
        packing_cost: 梱包 CJ列
        other_logistics: その他物流 CK列
        cl: CL列
        cm: CM列
        cn: CN列
        pcs_per_case: ケース入数 CO=BX列

    Returns:
        物流経費単価(円/個)。ケース入数が0の場合は0を返す。
    """
    if pcs_per_case == 0:
        return 0.0
    total = freight_per_case + packing_cost + other_logistics + cl + cm * cn
    return total / pcs_per_case
