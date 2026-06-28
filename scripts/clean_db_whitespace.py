"""DB テキストフィールドの改行・タブ・前後空白をクリーニング.

Excel セル内改行 (Alt+Enter) 由来の \\n が混入したテキストデータを正規化する。
対象:
- quote_items.product_json 内の全テキストフィールド
- quotes.title / notes
- customers.name / contact_person / phone / address
- staff.name / department

使い方:
    python scripts/clean_db_whitespace.py --dry-run    # 変更件数のみ表示
    python scripts/clean_db_whitespace.py --execute    # 実行
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# ProductInput の文字列フィールド（engine/models.py より）
PRODUCT_TEXT_FIELDS = [
    "supplier",
    "customer",
    "port",
    "delivery_to",
    "ship_to",
    "product_name",
    "prototype_code",
    "item_type",
    "package_size_cm",
    "fabric_quality",
    "method",
    "packing_size",
]


def _norm(s: str) -> str:
    """改行・キャリッジリターン・タブを空白に置換し、連続空白を1つにまとめ、前後を除去."""
    if not isinstance(s, str):
        return s
    cleaned = s.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    # 連続空白を1つに
    while "  " in cleaned:
        cleaned = cleaned.replace("  ", " ")
    return cleaned.strip()


def _scan_and_clean(
    conn: sqlite3.Connection, execute: bool
) -> tuple[int, dict[str, int]]:
    """変更対象を走査・（execute=True なら）更新.

    Returns:
        (総変更件数, テーブル別件数辞書)
    """
    counts: dict[str, int] = {}
    total = 0

    # 1. quote_items.product_json
    rows = conn.execute(
        "SELECT id, product_json FROM quote_items"
    ).fetchall()
    qi_changed = 0
    for item_id, pj in rows:
        obj = json.loads(pj)
        modified = False
        for field in PRODUCT_TEXT_FIELDS:
            v = obj.get(field)
            if isinstance(v, str):
                cleaned = _norm(v)
                if cleaned != v:
                    obj[field] = cleaned
                    modified = True
        if modified:
            qi_changed += 1
            if execute:
                new_pj = json.dumps(obj, ensure_ascii=False)
                conn.execute(
                    "UPDATE quote_items SET product_json=? WHERE id=?",
                    (new_pj, item_id),
                )
    counts["quote_items.product_json"] = qi_changed
    total += qi_changed

    # 2. quotes.title / notes
    text_targets = [
        ("quotes", ["title", "notes"]),
        ("customers", ["name", "contact_person", "phone", "address"]),
        ("staff", ["name", "department"]),
    ]
    for table, cols in text_targets:
        col_list = ", ".join(["id"] + cols)
        rows = conn.execute(f"SELECT {col_list} FROM {table}").fetchall()
        table_changed = 0
        for row in rows:
            row_id = row[0]
            values = row[1:]
            updates: dict[str, str] = {}
            for col, v in zip(cols, values):
                if isinstance(v, str):
                    cleaned = _norm(v)
                    if cleaned != v:
                        updates[col] = cleaned
            if updates:
                table_changed += 1
                if execute:
                    set_clause = ", ".join(f"{c}=?" for c in updates.keys())
                    params = list(updates.values()) + [row_id]
                    conn.execute(
                        f"UPDATE {table} SET {set_clause} WHERE id=?", params
                    )
        counts[f"{table}.[{','.join(cols)}]"] = table_changed
        total += table_changed

    return total, counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db", default="quote_data.db", help="SQLite DB path (default: quote_data.db)"
    )
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true", help="変更件数のみ表示・更新しない")
    g.add_argument("--execute", action="store_true", help="バックアップ後に実行")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: {db_path} が存在しません", file=sys.stderr)
        return 1

    if args.execute:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = db_path.with_suffix(f".db.bak_{ts}")
        shutil.copy2(db_path, backup)
        print(f"[backup] {backup}")

    conn = sqlite3.connect(db_path)
    try:
        if args.execute:
            conn.execute("BEGIN IMMEDIATE")
        total, counts = _scan_and_clean(conn, execute=args.execute)
        if args.execute:
            conn.commit()
    except Exception:
        if args.execute:
            conn.rollback()
        raise
    finally:
        conn.close()

    mode = "実行" if args.execute else "dry-run"
    print(f"\n=== {mode} 結果 ===")
    for k, v in counts.items():
        print(f"  {k}: {v} 件")
    print(f"  合計: {total} 件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
