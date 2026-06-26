"""見積もりデータベース — SQLite永続化."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from quote.engine.models import GlobalParams, ProductInput

DB_PATH = Path(__file__).resolve().parent.parent.parent / "quote_data.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                contact_person TEXT,
                phone TEXT,
                address TEXT
            );

            CREATE TABLE IF NOT EXISTS staff (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                department TEXT
            );

            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_number TEXT UNIQUE NOT NULL,
                customer_id INTEGER REFERENCES customers(id),
                staff_id INTEGER REFERENCES staff(id),
                title TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                notes TEXT,
                params_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS quote_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_id INTEGER REFERENCES quotes(id) ON DELETE CASCADE,
                item_order INTEGER,
                product_json TEXT NOT NULL
            );
            """
        )


def _next_quote_number_seq(conn) -> str:
    year = datetime.now().year
    row = conn.execute(
        "SELECT MAX(CAST(SUBSTR(quote_number, 8) AS INTEGER)) "
        "FROM quotes WHERE quote_number LIKE ?",
        (f"Q-{year}-%",),
    ).fetchone()
    seq = (row[0] or 0) + 1
    return f"Q-{year}-{seq:04d}"


# --- 顧客 ---

def list_customers() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM customers ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]


def get_customer(customer_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM customers WHERE id=?", (customer_id,)
        ).fetchone()
    return dict(row) if row else None


def add_customer(
    name: str,
    contact_person: str = "",
    phone: str = "",
    address: str = "",
) -> int:
    conn = _conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute(
            "INSERT INTO customers (name, contact_person, phone, address) VALUES (?, ?, ?, ?)",
            (name, contact_person, phone, address),
        )
        conn.execute("COMMIT")
        return cur.lastrowid
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def update_customer(
    customer_id: int,
    name: str,
    contact_person: str = "",
    phone: str = "",
    address: str = "",
) -> None:
    conn = _conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "UPDATE customers SET name=?, contact_person=?, phone=?, address=? WHERE id=?",
            (name, contact_person, phone, address, customer_id),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def delete_customer(customer_id: int) -> bool:
    conn = _conn()
    try:
        in_use = conn.execute(
            "SELECT COUNT(*) FROM quotes WHERE customer_id=?", (customer_id,)
        ).fetchone()[0]
        if in_use > 0:
            return False
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM customers WHERE id=?", (customer_id,))
        conn.execute("COMMIT")
        return True
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


# --- 担当者 ---

def list_staff() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM staff ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]


def add_staff(name: str, department: str = "") -> int:
    conn = _conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute(
            "INSERT INTO staff (name, department) VALUES (?, ?)",
            (name, department),
        )
        conn.execute("COMMIT")
        return cur.lastrowid
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def update_staff(staff_id: int, name: str, department: str = "") -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE staff SET name=?, department=? WHERE id=?",
            (name, department, staff_id),
        )


def delete_staff(staff_id: int) -> bool:
    conn = _conn()
    try:
        in_use = conn.execute(
            "SELECT COUNT(*) FROM quotes WHERE staff_id=?", (staff_id,)
        ).fetchone()[0]
        if in_use > 0:
            return False
        conn.execute("DELETE FROM staff WHERE id=?", (staff_id,))
        conn.close()
        return True
    finally:
        conn.close()


# --- 見積もり CRUD ---

def save_quote(
    customer_id: int,
    staff_id: int,
    title: str,
    products: list[ProductInput],
    params: GlobalParams,
    notes: str = "",
    quote_id: int | None = None,
) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    params_json = json.dumps(asdict(params), ensure_ascii=False)

    conn = _conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        if quote_id is not None:
            conn.execute(
                """UPDATE quotes
                   SET customer_id=?, staff_id=?, title=?,
                       updated_at=?, notes=?, params_json=?
                   WHERE id=?""",
                (customer_id, staff_id, title, now, notes, params_json, quote_id),
            )
            conn.execute("DELETE FROM quote_items WHERE quote_id=?", (quote_id,))
        else:
            qnum = _next_quote_number_seq(conn)
            cur = conn.execute(
                """INSERT INTO quotes
                   (quote_number, customer_id, staff_id, title,
                    created_at, updated_at, status, notes, params_json)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (qnum, customer_id, staff_id, title, now, now, "draft", notes, params_json),
            )
            quote_id = cur.lastrowid

        for i, p in enumerate(products):
            pj = json.dumps(asdict(p), ensure_ascii=False)
            conn.execute(
                "INSERT INTO quote_items (quote_id, item_order, product_json) VALUES (?,?,?)",
                (quote_id, i, pj),
            )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()

    return quote_id


def list_quotes(
    customer_id: int | None = None, staff_id: int | None = None
) -> list[dict]:
    conn = _conn()
    query = """SELECT q.*, c.name AS customer_name, s.name AS staff_name
               FROM quotes q
               LEFT JOIN customers c ON q.customer_id = c.id
               LEFT JOIN staff s ON q.staff_id = s.id"""
    conditions = []
    params = []
    if customer_id:
        conditions.append("q.customer_id = ?")
        params.append(customer_id)
    if staff_id:
        conditions.append("q.staff_id = ?")
        params.append(staff_id)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY q.updated_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_quote(quote_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            """SELECT q.*, c.name AS customer_name, s.name AS staff_name
               FROM quotes q
               LEFT JOIN customers c ON q.customer_id = c.id
               LEFT JOIN staff s ON q.staff_id = s.id
               WHERE q.id = ?""",
            (quote_id,),
        ).fetchone()
        if not row:
            return None
        q = dict(row)
        items = conn.execute(
            "SELECT * FROM quote_items WHERE quote_id=? ORDER BY item_order",
            (quote_id,),
        ).fetchall()
        q["items"] = [json.loads(r["product_json"]) for r in items]
        q["params"] = json.loads(q["params_json"])
    return q


def delete_quote(quote_id: int) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM quotes WHERE id=?", (quote_id,))
