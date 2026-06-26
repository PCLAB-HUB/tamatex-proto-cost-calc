"""モック顧客・担当者データの初期投入."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from quote.storage.db import DB_PATH, init_db


MOCK_CUSTOMERS = [
    (1, "コーヨー株式会社", "山田 太郎", "06-1234-5678", "大阪府大阪市中央区本町1-1-1"),
    (2, "サンリオギフト", "佐藤 花子", "03-9876-5432", "東京都品川区大崎2-2-2"),
    (3, "ロフト", "鈴木 一郎", "03-1111-2222", "東京都渋谷区宇田川町3-3-3"),
    (4, "東急ハンズ", "田中 美咲", "03-3333-4444", "東京都新宿区新宿5-5-5"),
    (5, "キャンドゥ", "高橋 健一", "03-5555-6666", "東京都新宿区高田馬場4-4-4"),
]

MOCK_STAFF = [
    (1, "中村 誠", "営業部"),
    (2, "伊藤 直樹", "営業部"),
    (3, "渡辺 由美", "営業部"),
]


def seed_mock_data() -> None:
    """モックデータが未投入なら投入する."""
    init_db()

    conn = sqlite3.connect(str(DB_PATH))
    try:
        existing = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        if existing > 0:
            return

        conn.executemany(
            "INSERT OR IGNORE INTO customers (id, name, contact_person, phone, address) "
            "VALUES (?, ?, ?, ?, ?)",
            MOCK_CUSTOMERS,
        )
        conn.executemany(
            "INSERT OR IGNORE INTO staff (id, name, department) VALUES (?, ?, ?)",
            MOCK_STAFF,
        )
        conn.commit()
    finally:
        conn.close()
