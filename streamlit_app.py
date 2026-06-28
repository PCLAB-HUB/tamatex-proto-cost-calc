"""Streamlit Cloud エントリーポイント.

Streamlit Cloud は `streamlit_app.py` を既定のメインファイルとして検出する。
本ファイルは毎回の rerun で quote/app_card.py をスクリプトとして実行する。

sys.path にリポジトリルートを明示追加することで `from quote.xxx import ...`
の解決を保証する（runpy.run_path 単体では sys.path 設定が不十分なため）.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_TARGET = _ROOT / "quote" / "app_card.py"

# rerun のたびにモジュールキャッシュをバイパスして fresh に exec する
exec(  # noqa: S102
    compile(_TARGET.read_text(encoding="utf-8"), str(_TARGET), "exec"),
    {"__name__": "__main__", "__file__": str(_TARGET)},
)
