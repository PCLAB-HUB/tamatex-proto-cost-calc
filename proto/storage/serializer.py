"""シナリオシリアライザ — ImportCondition ⇄ JSON 変換.

`ImportCondition` は `ImportExpenses` 2 つをネストした frozen dataclass。
`dataclasses.asdict` でフラットな dict に変換後 JSON 文字列化し、
復元時はネストを手動で再構築する。

数値は Python float そのまま JSON に渡すため精度劣化なし。
"""

from __future__ import annotations

import json
from dataclasses import asdict

from proto.engine.models import ImportCondition, ImportExpenses


def condition_to_json(cond: ImportCondition) -> str:
    """ImportCondition を JSON 文字列に変換する.

    Args:
        cond: シリアライズ対象の輸入条件。

    Returns:
        JSON 文字列（非 ASCII 文字はそのまま出力、インデントなし）。
    """
    return json.dumps(asdict(cond), ensure_ascii=False)


def condition_from_json(s: str) -> ImportCondition:
    """JSON 文字列から ImportCondition を復元する.

    Args:
        s: `condition_to_json` が生成した JSON 文字列。

    Returns:
        復元された ImportCondition インスタンス。

    Raises:
        KeyError: JSON に必須フィールドが存在しない場合。
        TypeError: フィールドの型が不正な場合。
    """
    d = json.loads(s)
    # ネストされた ImportExpenses を手動で復元する
    d["import_expenses_single"] = ImportExpenses(**d["import_expenses_single"])
    d["import_expenses_gift"] = ImportExpenses(**d["import_expenses_gift"])
    return ImportCondition(**d)
