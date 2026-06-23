"""シナリオシリアライザ — ImportCondition ⇄ JSON 変換.

`ImportCondition` は `ImportExpenses` と `LogisticsParams` をネストした
frozen dataclass。`dataclasses.asdict` でフラットな dict に変換後 JSON
文字列化し、復元時はネストを手動で再構築する。

数値は Python float そのまま JSON に渡すため精度劣化なし。
旧スキーマ（物流を io_fee/storage_fee/storage_months のフラットで保持）も
後方互換で読み込める（物流のみ標準値へ移行する）。
"""

from __future__ import annotations

import json
from dataclasses import asdict

from proto.engine.models import ImportCondition, ImportExpenses, LogisticsParams

# 旧スキーマからの移行時に使う標準物流パラメータ（Excel ひな形の基準値）
_DEFAULT_LOGISTICS_SINGLE = LogisticsParams(
    io_fee=70.0, storage_fee=120.0, storage_months=1.0
)
_DEFAULT_LOGISTICS_GIFT = LogisticsParams(
    io_fee=140.0, storage_fee=200.0, storage_months=1.0
)


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

    旧スキーマ（io_fee/storage_fee/storage_months のフラット保持）も読み込める。
    旧形式は単品/ギフトを区別しないため、物流は標準値（単品 70/120/1・
    ギフト 140/200/1）へ移行する。

    Args:
        s: `condition_to_json` が生成した JSON 文字列（旧形式も可）。

    Returns:
        復元された ImportCondition インスタンス。

    Raises:
        KeyError: JSON に必須フィールドが存在しない場合。
        TypeError: フィールドの型が不正な場合。
    """
    d = json.loads(s)

    # ネストされた ImportExpenses を復元する
    d["import_expenses_single"] = ImportExpenses(**d["import_expenses_single"])
    d["import_expenses_gift"] = ImportExpenses(**d["import_expenses_gift"])

    # 物流: 新スキーマ（logistics_single/gift）を復元。旧スキーマなら標準値へ移行。
    if "logistics_single" in d and "logistics_gift" in d:
        d["logistics_single"] = LogisticsParams(**d["logistics_single"])
        d["logistics_gift"] = LogisticsParams(**d["logistics_gift"])
    else:
        d["logistics_single"] = _DEFAULT_LOGISTICS_SINGLE
        d["logistics_gift"] = _DEFAULT_LOGISTICS_GIFT
    # 旧フラットフィールドは ImportCondition に存在しないため除去する
    for old_key in ("io_fee", "storage_fee", "storage_months"):
        d.pop(old_key, None)

    return ImportCondition(**d)
