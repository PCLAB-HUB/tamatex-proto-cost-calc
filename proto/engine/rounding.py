"""金額の丸めユーティリティ — Excel ROUNDUP 互換."""

from __future__ import annotations

import math

# float の表現誤差（例: 121.00000000000001）を吸収する丸め桁数。
# 金額（円）の計算で意味を持つのは小数数桁までで、9 桁あれば
# IEEE754 double の表現誤差（おおむね 1e-13 規模）を確実に消せる。
_NOISE_DIGITS = 9


def roundup_yen(value: float) -> int:
    """円単位の切り上げ（Excel ``ROUNDUP(value, 0)`` 互換）。

    素朴な ``math.ceil`` は float の表現誤差で 1 円過大になりうる
    （例: ``110 * 1.10`` は ``121.00000000000001`` となり ceil で 122）。
    Excel の ROUNDUP は 15 有効桁で処理するため、切り上げ前に
    小数 9 桁へ丸めて表現誤差を吸収し、Excel と挙動を一致させる。

    Args:
        value: 切り上げ対象の金額（円）。

    Returns:
        円単位に切り上げた整数値。
    """
    return math.ceil(round(value, _NOISE_DIGITS))
