"""ログ設定モジュール。ファイル出力 + コンソール出力 + ローテーション。"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from tamatex.config import LogConfig


def setup_logger(config: LogConfig) -> logging.Logger:
    """アプリケーションロガーを初期化する。"""
    logger = logging.getLogger("tamatex")
    logger.setLevel(getattr(logging, config.level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # コンソール出力
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # ファイル出力（ローテーション付き）
    log_path = Path(config.file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=config.max_size_mb * 1024 * 1024,
        backupCount=config.backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
