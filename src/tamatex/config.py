"""設定管理モジュール。YAMLファイルからアプリケーション設定を読み込む。"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# HH:MM 形式（00:00 〜 23:59）
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


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
    """同期スケジュール設定。

    mode が "interval" なら従来通り `interval_minutes` 分ごとに同期。
    mode が "times" なら `times` で指定した時刻（HH:MM）に同期。
    どちらの場合もサービス起動直後に1回必ず即時同期する（PC起動時の朝同期に相当）。

    mirror_subfolders を True にすると、NAS上のサブフォルダ構造を
    Drive 上の Sheets/ および PDF/ にもミラー再現する。後方互換のため
    デフォルトは False（従来通りのフラット配置）。
    """
    interval_minutes: int = 15
    state_db_path: str = ""
    mode: str = "interval"  # "interval" or "times"
    times: list[str] = field(default_factory=list)  # ["12:00", "15:00"] etc.
    mirror_subfolders: bool = False


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


def _validate_sync(sync: SyncConfig) -> None:
    """SyncConfig の整合性を検証する。"""
    if sync.mode not in ("interval", "times"):
        raise ValueError(
            f"sync.mode は 'interval' または 'times' である必要があります（現在: {sync.mode!r}）"
        )

    if sync.mode == "times":
        if not sync.times:
            raise ValueError(
                "sync.mode='times' の場合、sync.times に少なくとも1つの時刻指定が必要です"
            )
        for t in sync.times:
            if not isinstance(t, str) or not _TIME_RE.match(t):
                raise ValueError(
                    f"sync.times の値は 'HH:MM' 形式である必要があります（不正な値: {t!r}）"
                )
    else:  # interval
        if sync.interval_minutes <= 0:
            raise ValueError(
                f"sync.interval_minutes は1以上である必要があります（現在: {sync.interval_minutes}）"
            )


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

        sync_cfg = SyncConfig(**data.get("sync", {}))
        _validate_sync(sync_cfg)

        return AppConfig(
            nas=NasConfig(auth=nas_auth, **nas_data),
            google=GoogleConfig(**google_data),
            sync=sync_cfg,
            logging=LogConfig(**data.get("logging", {})),
        )
    except TypeError as e:
        raise ValueError(f"設定ファイルのパラメータが不正です ({config_path}): {e}") from e
