"""設定管理モジュール。YAMLファイルからアプリケーション設定を読み込む。"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class NasAuthConfig:
    """NAS の SMB 認証情報（Windows向け）。省略可。サービス実行時に net use で認証を確立する。"""
    server: str
    username: str
    password: str


@dataclass(frozen=True)
class NasConfig:
    base_path: str
    file_patterns: list[str] = field(default_factory=lambda: ["*.xlsx"])
    exclude_patterns: list[str] = field(default_factory=lambda: ["~$*", "*.tmp", ".~lock*"])
    auth: NasAuthConfig | None = None


@dataclass(frozen=True)
class GoogleConfig:
    credentials_path: str
    drive_folder_id: str = ""
    share_with: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SyncConfig:
    interval_minutes: int = 15
    state_db_path: str = ""


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

    try:
        nas_data = data.get("nas")
        if not nas_data:
            raise ValueError(f"設定ファイルに 'nas' セクションがありません: {config_path}")
        google_data = data.get("google")
        if not google_data:
            raise ValueError(f"設定ファイルに 'google' セクションがありません: {config_path}")

        auth_data = nas_data.pop("auth", None)
        nas_auth = NasAuthConfig(**auth_data) if auth_data else None

        return AppConfig(
            nas=NasConfig(auth=nas_auth, **nas_data),
            google=GoogleConfig(**google_data),
            sync=SyncConfig(**data.get("sync", {})),
            logging=LogConfig(**data.get("logging", {})),
        )
    except TypeError as e:
        raise ValueError(f"設定ファイルのパラメータが不正です ({config_path}): {e}") from e
