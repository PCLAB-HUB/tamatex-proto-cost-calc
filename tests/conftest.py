"""pytest 共通設定。

with_retry の sleep を no-op に差し替えて、テスト実行を高速化する。
本番コードの time.sleep を直接 monkeypatch すると state/watcher 系の正常な遅延も
壊れるため、drive_utils 側のモジュール変数 `_retry_sleep` のみ差し替える。
"""

import pytest


@pytest.fixture(autouse=True)
def _disable_retry_sleep(monkeypatch):
    """with_retry のバックオフ sleep を全テストで無効化する。"""
    import tamatex.drive_utils as du

    monkeypatch.setattr(du, "_retry_sleep", lambda _seconds: None)
