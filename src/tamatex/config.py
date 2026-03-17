"""設定管理モジュール。YAMLファイルからアプリケーション設定を読み込む。"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class NasConfig:
    base_path: str
    file_patterns: list[str] = field(default_factory=lambda: ["*.xlsx"])
    exclude_patterns: list[str] = field(default_factory=lambda: ["~$*", "*.tmp", ".~lock*"])


@dataclass(frozen=True)
class GoogleConfig:
    credentials_path: str
    drive_folder_id: str = ""
    share_with: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SyncConfig:
    interval_minutes: int = 15


@dataclass(frozen=True)
class LogConfig:
    level: str = "INFO"
    file: str = "./logs/tamatex.log"
    max_size_mb: int = 10
    backup_count: int = 5


@dataclass(frozen=True)
class AppConfig:
    nas: NasConfig
    google: GoogleConfig
    sync: SyncConfig = field(default_factory=SyncConfig)
    logging: LogConfig = field(default_factory=LogConfig)


def load_config(path: str | Path) -> AppConfig:
    """YAMLファイルから設定を読み込む。"""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError(f"設定ファイルが空です: {config_path}")

    return AppConfig(
        nas=NasConfig(**data.get("nas", {})),
        google=GoogleConfig(**data.get("google", {})),
        sync=SyncConfig(**data.get("sync", {})),
        logging=LogConfig(**data.get("logging", {})),
    )
