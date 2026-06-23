"""シナリオシリアライザ — ImportCondition ⇄ JSON 変換.

`ImportCondition` は `ImportExpenses` と `LogisticsParams` をネストした
frozen dataclass。`dataclasses.asdict` でフラットな dict に変換後 JSON
文字列化し、復元時はネストを手動で再構築する。

数値は Python float そのまま JSON に渡すため精度劣化なし。
旧スキーマ（物流を io_fee/storage_fee/storage_months のフラットで保持）も
後方互換で読み込める（保存値を保持して単品/ギフト両区分へ移行する）。
"""

from __future__ import annotations

import json
from dataclasses import asdict

from proto.engine.models import ImportCondition, ImportExpenses, LogisticsParams

# 旧スキーマで物流フィールドが欠落していた場合のフォールバック標準値
# （Excel ひな形の単品基準値）
_DEFAULT_LOGISTICS = LogisticsParams(io_fee=70.0, storage_fee=120.0, storage_months=1.0)


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
    旧形式は単品/ギフトを区別しないため、保存値を両区分に同値で移行する
    （保存済みシナリオの物流条件を失わない）。欠落フィールドのみ標準値で補完する。

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

    # 物流: 新スキーマ（logistics_single/gift）を復元。旧スキーマ（フラット）は
    # 保存値を保持して単品/ギフト両区分へ移行する（旧形式は両者を区別しないため）。
    if "logistics_single" in d and "logistics_gift" in d:
        d["logistics_single"] = LogisticsParams(**d["logistics_single"])
        d["logistics_gift"] = LogisticsParams(**d["logistics_gift"])
    else:
        legacy = LogisticsParams(
            io_fee=float(d.get("io_fee", _DEFAULT_LOGISTICS.io_fee)),
            storage_fee=float(d.get("storage_fee", _DEFAULT_LOGISTICS.storage_fee)),
            storage_months=float(
                d.get("storage_months", _DEFAULT_LOGISTICS.storage_months)
            ),
        )
        d["logistics_single"] = legacy
        d["logistics_gift"] = legacy
    # 旧フラットフィールドは ImportCondition に存在しないため除去する
    for old_key in ("io_fee", "storage_fee", "storage_months"):
        d.pop(old_key, None)

    return ImportCondition(**d)
