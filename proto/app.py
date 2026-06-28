"""Streamlit Cloud レガシー entrypoint (Main file path: proto/app.py).

既存アプリ設定 (Main file path = proto/app.py) を維持したまま、
実体は quote/app_card.py を実行するためのプロキシ。

sys.path にリポジトリルートを明示追加し、`from quote.xxx import ...` を解決可能にする。
rerun のたびに quote/app_card.py を fresh に exec する。
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_TARGET = _ROOT / "quote" / "app_card.py"

exec(  # noqa: S102
    compile(_TARGET.read_text(encoding="utf-8"), str(_TARGET), "exec"),
    {"__name__": "__main__", "__file__": str(_TARGET)},
)
