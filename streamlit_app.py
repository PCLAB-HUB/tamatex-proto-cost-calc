"""Streamlit Cloud エントリーポイント.

Streamlit Cloud は `streamlit_app.py` を既定のメインファイルとして検出する。
本ファイルは毎回の rerun で quote/app_card.py をスクリプトとして実行する。
"""

from __future__ import annotations

import runpy
from pathlib import Path

_TARGET = Path(__file__).resolve().parent / "quote" / "app_card.py"

runpy.run_path(str(_TARGET), run_name="__main__")
