"""コンテナ積載量の近似計算.

旧Excelの「コンテナ積載量計算」シートのロジックを参考にした近似。
正確な値はExcelから貼り付けられた値（R列）を使用し、
本計算はR列が空の場合のフォールバックとして使用する。
"""

from __future__ import annotations

import re

CONTAINER_DIMS = {
    20: {"width": 2340.0, "depth": 5000.0, "height": 2370.0},
    40: {"width": 2340.0, "depth": 11800.0, "height": 2370.0},
}

CONTAINER_LOSS_RATE = 0.10


def parse_size_cm(size_str: str) -> tuple[float, float, float] | None:
    """'13*9.5*0.6cm' → (13.0, 9.5, 0.6) をパース."""
    cleaned = re.sub(r"[cCmM\s]", "", size_str)
    parts = re.split(r"[*×xX]", cleaned)
    if len(parts) != 3:
        return None
    try:
        return (float(parts[0]), float(parts[1]), float(parts[2]))
    except ValueError:
        return None


def estimate_container_load(
    size_cm: str,
    packing_quantity: int,
    container_ft: int = 20,
) -> float | None:
    """製品サイズと梱包入数からコンテナ積載量（枚数）を近似計算.

    旧Excel「コンテナ積載量計算」シートのロジック:
    1. 製品サイズ → ダンボール外寸を推定
    2. コンテナ内寸でダンボール並べ数を計算
    3. ロス率(10%)を適用
    """
    dims = parse_size_cm(size_cm)
    if dims is None:
        return None

    container = CONTAINER_DIMS.get(container_ft)
    if container is None:
        return None

    w_mm, d_mm, h_mm = dims[0] * 10, dims[1] * 10, dims[2] * 10

    carton_w = w_mm * 2 + 2 * 5 + 15
    carton_d = d_mm * 2 + 2 * 5 + 15
    carton_h = h_mm * 10 + 10 * 3 + 15

    cw, cd, ch = container["width"], container["depth"], container["height"]
    margin = 50.0

    fit_w = int((cw - margin) / carton_w) if carton_w > 0 else 0
    fit_d = int((cd - margin) / carton_d) if carton_d > 0 else 0
    fit_h = int((ch - margin) / carton_h) if carton_h > 0 else 0

    total_cartons = fit_w * fit_d * fit_h
    cartons_with_loss = int(total_cartons * (1 - CONTAINER_LOSS_RATE))
    pcs_per_carton = packing_quantity
    total_pcs = cartons_with_loss * pcs_per_carton

    return float(total_pcs) if total_pcs > 0 else None
