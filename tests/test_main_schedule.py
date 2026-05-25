"""main._compute_next_wait の単体テスト。

時刻指定モード（times）と間隔モード（interval）の両方を網羅する。
"""

import threading
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from tamatex.config import SyncConfig
from tamatex.main import _compute_next_wait, _sleep_until_event


def _mk_config(sync: SyncConfig):
    """AppConfig 風の MagicMock を返す（main は config.sync しか参照しない）。"""
    cfg = MagicMock()
    cfg.sync = sync
    return cfg


# ---------------------------------------------------------------------------
# interval モード（後方互換）
# ---------------------------------------------------------------------------

def test_interval_mode_returns_seconds_from_minutes():
    cfg = _mk_config(SyncConfig(interval_minutes=15, mode="interval"))
    now = datetime(2026, 4, 28, 10, 0, 0)
    wait, next_at = _compute_next_wait(cfg, now)

    assert wait == 15 * 60
    assert next_at is None  # interval モードでは絶対時刻なし


def test_interval_mode_default_is_15_minutes():
    cfg = _mk_config(SyncConfig())  # 全デフォルト
    wait, next_at = _compute_next_wait(cfg, datetime(2026, 4, 28, 10, 0, 0))
    assert wait == 15 * 60
    assert next_at is None


# ---------------------------------------------------------------------------
# times モード — 当日内の次の時刻
# ---------------------------------------------------------------------------

def test_times_mode_picks_next_today_time():
    """現在 11:00 で times=[12:00, 15:00] なら 12:00 が次。"""
    cfg = _mk_config(SyncConfig(mode="times", times=["12:00", "15:00"]))
    now = datetime(2026, 4, 28, 11, 0, 0)
    wait, next_at = _compute_next_wait(cfg, now)

    assert next_at == datetime(2026, 4, 28, 12, 0, 0)
    assert wait == 60 * 60  # 1時間 = 3600秒


def test_times_mode_picks_next_after_first_time_passes():
    """現在 12:30 で times=[12:00, 15:00] なら 15:00 が次。"""
    cfg = _mk_config(SyncConfig(mode="times", times=["12:00", "15:00"]))
    now = datetime(2026, 4, 28, 12, 30, 0)
    wait, next_at = _compute_next_wait(cfg, now)

    assert next_at == datetime(2026, 4, 28, 15, 0, 0)
    assert wait == 2.5 * 60 * 60  # 2.5時間


# ---------------------------------------------------------------------------
# times モード — 翌日への繰越
# ---------------------------------------------------------------------------

def test_times_mode_rolls_to_next_day_when_all_times_passed():
    """現在 16:00 で times=[12:00, 15:00] なら翌日 12:00 が次。"""
    cfg = _mk_config(SyncConfig(mode="times", times=["12:00", "15:00"]))
    now = datetime(2026, 4, 28, 16, 0, 0)
    wait, next_at = _compute_next_wait(cfg, now)

    assert next_at == datetime(2026, 4, 29, 12, 0, 0)
    assert wait == 20 * 60 * 60  # 20時間


def test_times_mode_handles_single_time():
    """times=[18:00] のみで現在 09:00 なら当日 18:00。"""
    cfg = _mk_config(SyncConfig(mode="times", times=["18:00"]))
    now = datetime(2026, 4, 28, 9, 0, 0)
    wait, next_at = _compute_next_wait(cfg, now)

    assert next_at == datetime(2026, 4, 28, 18, 0, 0)
    assert wait == 9 * 60 * 60


def test_times_mode_handles_unsorted_times():
    """times の順序は不問、最も早い"次の発火時刻"を選ぶ。"""
    cfg = _mk_config(SyncConfig(mode="times", times=["18:00", "09:00", "13:00"]))
    now = datetime(2026, 4, 28, 10, 0, 0)
    wait, next_at = _compute_next_wait(cfg, now)

    assert next_at == datetime(2026, 4, 28, 13, 0, 0)


def test_times_mode_at_exact_time_skips_to_next():
    """現在時刻と一致する time（例: 12:00:00）は「過去」扱いで翌日になる。

    これは安全側の挙動: 同期サイクル開始の数秒以内に再起動されると
    無限ループの恐れがあるため、現在以後（>now）のみを発火対象とする。
    """
    cfg = _mk_config(SyncConfig(mode="times", times=["12:00", "15:00"]))
    now = datetime(2026, 4, 28, 12, 0, 0)
    wait, next_at = _compute_next_wait(cfg, now)
    # 12:00 は now と等しいので "次" は 15:00
    assert next_at == datetime(2026, 4, 28, 15, 0, 0)


# ---------------------------------------------------------------------------
# 顧客ユースケース: 12:00 と 15:00
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("now,expected_h,expected_d_offset", [
    (datetime(2026, 4, 28,  9,  0, 0), 12, 0),  # 朝起動直後 → 当日12:00
    (datetime(2026, 4, 28, 11, 59, 0), 12, 0),
    (datetime(2026, 4, 28, 12,  0, 0), 15, 0),  # 12:00ジャスト → 15:00
    (datetime(2026, 4, 28, 12,  0, 1), 15, 0),
    (datetime(2026, 4, 28, 14, 59, 0), 15, 0),
    (datetime(2026, 4, 28, 15,  0, 0), 12, 1),  # 15:00ジャスト → 翌日12:00
    (datetime(2026, 4, 28, 18,  0, 0), 12, 1),  # 終業後 → 翌日12:00
    (datetime(2026, 4, 28, 23, 59, 0), 12, 1),  # 深夜 → 翌日12:00
])
def test_customer_schedule_12_15(now, expected_h, expected_d_offset):
    cfg = _mk_config(SyncConfig(mode="times", times=["12:00", "15:00"]))
    _, next_at = _compute_next_wait(cfg, now)

    assert next_at.hour == expected_h
    assert next_at.minute == 0
    assert next_at.day == now.day + expected_d_offset


# ---------------------------------------------------------------------------
# _sleep_until_event — Windowsスリープ復帰タイマー停止問題への対策
# ---------------------------------------------------------------------------

def test_sleep_until_event_returns_true_when_already_past_target():
    """既に予定時刻を過ぎていれば即 True を返す（PCスリープ復帰直後の典型）。"""
    target = datetime(2026, 5, 25, 12, 0, 0)
    fake_now = datetime(2026, 5, 25, 13, 30, 0)  # 1.5h 過ぎ

    ev = threading.Event()
    result = _sleep_until_event(target, ev, chunk_sec=60.0, _now=lambda: fake_now)
    assert result is True


def test_sleep_until_event_returns_true_when_target_reached():
    """壁時計が target を超えたら True で抜ける。"""
    target = datetime(2026, 5, 25, 12, 0, 0)
    times = [
        datetime(2026, 5, 25, 11, 59, 59, 500000),  # まだ
        datetime(2026, 5, 25, 12, 0, 0, 100000),    # 越えた
    ]
    ev = threading.Event()
    result = _sleep_until_event(
        target, ev, chunk_sec=0.01, _now=lambda: times.pop(0)
    )
    assert result is True


def test_sleep_until_event_returns_false_on_shutdown():
    """shutdown_event 発火で False を返す。"""
    target = datetime(2026, 5, 25, 23, 0, 0)
    fake_now = datetime(2026, 5, 25, 12, 0, 0)

    ev = threading.Event()
    ev.set()  # 事前に発火
    result = _sleep_until_event(target, ev, chunk_sec=60.0, _now=lambda: fake_now)
    assert result is False


def test_sleep_until_event_chunks_long_wait():
    """target が遠い場合、chunk_sec ごとに wait される（長時間を一気に待たない）。"""
    target = datetime(2026, 5, 25, 18, 0, 0)
    fake_now = datetime(2026, 5, 25, 12, 0, 0)  # 6時間先

    waited_chunks: list[float] = []

    class FakeEvent:
        def is_set(self):
            return len(waited_chunks) >= 3  # 3回 chunk 待ったら stop 扱い

        def set(self):
            pass

        def wait(self, timeout):
            waited_chunks.append(timeout)
            return False

    fe = FakeEvent()
    _sleep_until_event(target, fe, chunk_sec=60.0, _now=lambda: fake_now)
    # 各 chunk は 60.0 秒以内（remaining が大きいので全部 chunk_sec）
    assert all(c == 60.0 for c in waited_chunks)
    assert len(waited_chunks) == 3  # is_set が True になるまで


def test_sleep_until_event_simulates_pc_sleep_resume():
    """PCスリープ復帰を模した時刻ジャンプを正しく検知する（核心テスト）。

    シナリオ: 5/22 18:00 に sleep 開始、次回 5/23 12:00 が target
    本来 18 時間後だが PC スリープで 62 時間ジャンプ → 5/25 08:56 復帰
    chunk=60s なので 1〜数回の wait で残時間 <=0 を検知して抜ける
    """
    target = datetime(2026, 5, 23, 12, 0, 0)
    # 時刻系列: スリープ前 → 1回目 wait 中 → 1回目復帰時には大幅ジャンプ
    times = [
        datetime(2026, 5, 22, 18, 0, 0),   # while 入口、remaining = 18h
        datetime(2026, 5, 25, 8, 56, 0),   # 復帰、target は既に過去
    ]

    waited: list[float] = []

    class FakeEvent:
        def is_set(self):
            return False

        def wait(self, timeout):
            waited.append(timeout)
            return False  # shutdown 来てない

    result = _sleep_until_event(
        target, FakeEvent(), chunk_sec=60.0, _now=lambda: times.pop(0)
    )
    assert result is True
    # 復帰後の時計判定で抜けるので wait は 1 回だけ呼ばれる
    assert len(waited) == 1
    assert waited[0] == 60.0  # 18h は遠いので chunk_sec で頭打ち
