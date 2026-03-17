# テスト依存: pytest
"""logger モジュールの単体テスト。

setup_logger() の動作を検証する。
テスト間でグローバルな logging.Logger の状態が干渉しないよう、
各テストでハンドラをクリーンアップする。
"""

import logging
from logging.handlers import RotatingFileHandler

import pytest

from tamatex.config import LogConfig
from tamatex.logger import setup_logger


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_tamatex_logger():
    """各テストの前後で 'tamatex' ロガーのハンドラをリセットする。

    setup_logger は handlers があると早期リターンするため、
    テスト間の干渉を防ぐために毎回クリアする。
    """
    logger = logging.getLogger("tamatex")
    # テスト前: ハンドラを全削除してクリーンな状態にする
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    yield
    # テスト後: 同様にクリーンアップ
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)


@pytest.fixture()
def log_config(tmp_path):
    """一時ディレクトリへのログ出力設定を返す。"""
    return LogConfig(
        level="INFO",
        file=str(tmp_path / "logs" / "tamatex.log"),
        max_size_mb=5,
        backup_count=3,
    )


# ---------------------------------------------------------------------------
# ハンドラ生成テスト
# ---------------------------------------------------------------------------

def test_setup_logger_returns_logger(log_config):
    """setup_logger が logging.Logger インスタンスを返すこと。"""
    result = setup_logger(log_config)
    assert isinstance(result, logging.Logger)


def test_setup_logger_returns_tamatex_logger(log_config):
    """返されるロガーの名前が 'tamatex' であること。"""
    result = setup_logger(log_config)
    assert result.name == "tamatex"


def test_setup_logger_creates_two_handlers(log_config):
    """setup_logger がコンソールハンドラとファイルハンドラの 2 つを追加すること。"""
    logger = setup_logger(log_config)
    assert len(logger.handlers) == 2


def test_setup_logger_has_stream_handler(log_config):
    """ハンドラの中に StreamHandler（コンソール出力）が含まれること。"""
    logger = setup_logger(log_config)
    handler_types = [type(h) for h in logger.handlers]
    assert logging.StreamHandler in handler_types


def test_setup_logger_has_rotating_file_handler(log_config):
    """ハンドラの中に RotatingFileHandler（ファイル出力）が含まれること。"""
    logger = setup_logger(log_config)
    handler_types = [type(h) for h in logger.handlers]
    assert RotatingFileHandler in handler_types


def test_setup_logger_creates_log_directory(tmp_path, log_config):
    """ログディレクトリが存在しなくても自動作成されること。"""
    log_dir = tmp_path / "logs"
    assert not log_dir.exists()

    setup_logger(log_config)

    assert log_dir.exists()


def test_setup_logger_creates_log_file(tmp_path, log_config):
    """setup_logger 後にログファイルが作成されること。"""
    log_path = tmp_path / "logs" / "tamatex.log"

    setup_logger(log_config)

    assert log_path.exists()


# ---------------------------------------------------------------------------
# ログレベルテスト
# ---------------------------------------------------------------------------

def test_setup_logger_sets_info_level(tmp_path):
    """level='INFO' のとき logging.INFO が設定されること。"""
    config = LogConfig(
        level="INFO",
        file=str(tmp_path / "tamatex.log"),
    )
    logger = setup_logger(config)
    assert logger.level == logging.INFO


def test_setup_logger_sets_debug_level(tmp_path):
    """level='DEBUG' のとき logging.DEBUG が設定されること。"""
    config = LogConfig(
        level="DEBUG",
        file=str(tmp_path / "tamatex.log"),
    )
    logger = setup_logger(config)
    assert logger.level == logging.DEBUG


def test_setup_logger_sets_warning_level(tmp_path):
    """level='WARNING' のとき logging.WARNING が設定されること。"""
    config = LogConfig(
        level="WARNING",
        file=str(tmp_path / "tamatex.log"),
    )
    logger = setup_logger(config)
    assert logger.level == logging.WARNING


def test_setup_logger_sets_error_level(tmp_path):
    """level='ERROR' のとき logging.ERROR が設定されること。"""
    config = LogConfig(
        level="ERROR",
        file=str(tmp_path / "tamatex.log"),
    )
    logger = setup_logger(config)
    assert logger.level == logging.ERROR


# ---------------------------------------------------------------------------
# 再呼び出しテスト
# ---------------------------------------------------------------------------

def test_setup_logger_returns_same_logger_on_second_call(log_config):
    """2 回目の呼び出しでも同じロガーオブジェクトが返されること。"""
    logger1 = setup_logger(log_config)
    logger2 = setup_logger(log_config)
    assert logger1 is logger2


def test_setup_logger_does_not_add_handlers_on_second_call(log_config):
    """2 回目の呼び出しでハンドラが重複追加されないこと。"""
    setup_logger(log_config)
    setup_logger(log_config)  # 2 回目

    logger = logging.getLogger("tamatex")
    # 1 回目で追加した 2 つのハンドラがそのまま維持されること
    assert len(logger.handlers) == 2


def test_setup_logger_updates_level_on_second_call(tmp_path):
    """既にハンドラがある状態で再呼び出しするとログレベルが更新されること。"""
    config_info = LogConfig(level="INFO", file=str(tmp_path / "tamatex.log"))
    config_debug = LogConfig(level="DEBUG", file=str(tmp_path / "tamatex.log"))

    setup_logger(config_info)
    # INFO レベルで初期化済みの状態で DEBUG で再呼び出し
    logger = setup_logger(config_debug)

    assert logger.level == logging.DEBUG


# ---------------------------------------------------------------------------
# RotatingFileHandler 設定テスト
# ---------------------------------------------------------------------------

def test_setup_logger_rotating_handler_max_bytes(tmp_path):
    """RotatingFileHandler の maxBytes が config 値通りに設定されること。"""
    config = LogConfig(
        level="INFO",
        file=str(tmp_path / "tamatex.log"),
        max_size_mb=10,
        backup_count=5,
    )
    logger = setup_logger(config)

    rotating = next(
        h for h in logger.handlers if isinstance(h, RotatingFileHandler)
    )
    assert rotating.maxBytes == 10 * 1024 * 1024


def test_setup_logger_rotating_handler_backup_count(tmp_path):
    """RotatingFileHandler の backupCount が config 値通りに設定されること。"""
    config = LogConfig(
        level="INFO",
        file=str(tmp_path / "tamatex.log"),
        max_size_mb=5,
        backup_count=7,
    )
    logger = setup_logger(config)

    rotating = next(
        h for h in logger.handlers if isinstance(h, RotatingFileHandler)
    )
    assert rotating.backupCount == 7
