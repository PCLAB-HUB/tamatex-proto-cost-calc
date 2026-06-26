"""デフォルト設定の永続化 — SQLiteに保存."""

from __future__ import annotations

import json
from dataclasses import asdict, fields as dc_fields

from quote.engine.models import ContainerExpenses, GlobalParams
from quote.storage.db import _conn, init_db


def _ensure_table() -> None:
    with _conn() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )"""
        )


def save_default_params(params: GlobalParams) -> None:
    _ensure_table()
    data = json.dumps(asdict(params), ensure_ascii=False)
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("default_params", data),
        )


def load_default_params() -> GlobalParams | None:
    _ensure_table()
    with _conn() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", ("default_params",)
        ).fetchone()
    if not row:
        return None
    data = json.loads(row["value"])
    ce_data = data.pop("container_expenses", {})
    ce = ContainerExpenses(**{
        f.name: ce_data.get(f.name, f.default)
        for f in dc_fields(ContainerExpenses)
    })
    return GlobalParams(
        **{f.name: data.get(f.name, f.default)
           for f in dc_fields(GlobalParams)
           if f.name != "container_expenses"},
        container_expenses=ce,
    )
