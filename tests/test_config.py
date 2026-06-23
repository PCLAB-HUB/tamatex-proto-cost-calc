# テスト依存: pytest, pyyaml
"""config モジュールの単体テスト。

load_config() 関数と各 dataclass のデフォルト値を検証する。
"""

import pytest

from tamatex.config import (
    AppConfig,
    GoogleConfig,
    LogConfig,
    NasConfig,
    SyncConfig,
    load_config,
)


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def _write_yaml(path, content: str):
    """tmp_path 配下に YAML ファイルを書き込む。"""
    config_file = path / "config.yaml"
    config_file.write_text(content, encoding="utf-8")
    return config_file


# ---------------------------------------------------------------------------
# load_config: 正常系
# ---------------------------------------------------------------------------

def test_load_config_returns_appconfig_with_valid_yaml(tmp_path):
    """最小限の正しい YAML から AppConfig が返ること。"""
    yaml_content = """
nas:
  base_path: /mnt/nas/data
google:
  credentials_path: /etc/creds.json
"""
    config_file = _write_yaml(tmp_path, yaml_content)
    result = load_config(config_file)

    assert isinstance(result, AppConfig)


def test_load_config_nas_section_is_parsed(tmp_path):
    """NAS セクションが正しく NasConfig に変換されること。"""
    yaml_content = """
nas:
  base_path: /mnt/nas/data
  file_patterns:
    - "*.xlsx"
    - "*.xls"
  exclude_patterns:
    - "~$*"
google:
  credentials_path: /etc/creds.json
"""
    config_file = _write_yaml(tmp_path, yaml_content)
    result = load_config(config_file)

    assert result.nas.base_path == "/mnt/nas/data"
    assert result.nas.file_patterns == ["*.xlsx", "*.xls"]
    assert result.nas.exclude_patterns == ["~$*"]


def test_load_config_google_section_is_parsed(tmp_path):
    """Google セクションが正しく GoogleConfig に変換されること。"""
    yaml_content = """
nas:
  base_path: /mnt/nas/data
google:
  credentials_path: /srv/credentials.json
  drive_folder_id: folder-abc-123
  share_with:
    - user1@example.com
    - user2@example.com
"""
    config_file = _write_yaml(tmp_path, yaml_content)
    result = load_config(config_file)

    assert result.google.credentials_path == "/srv/credentials.json"
    assert result.google.drive_folder_id == "folder-abc-123"
    assert result.google.share_with == ["user1@example.com", "user2@example.com"]


def test_load_config_sync_section_is_parsed(tmp_path):
    """sync セクションが SyncConfig に変換されること。"""
    yaml_content = """
nas:
  base_path: /mnt/nas/data
google:
  credentials_path: /etc/creds.json
sync:
  interval_minutes: 30
"""
    config_file = _write_yaml(tmp_path, yaml_content)
    result = load_config(config_file)

    assert result.sync.interval_minutes == 30


def test_load_config_logging_section_is_parsed(tmp_path):
    """logging セクションが LogConfig に変換されること。"""
    yaml_content = """
nas:
  base_path: /mnt/nas/data
google:
  credentials_path: /etc/creds.json
logging:
  level: DEBUG
  file: /var/log/tamatex.log
  max_size_mb: 20
  backup_count: 10
"""
    config_file = _write_yaml(tmp_path, yaml_content)
    result = load_config(config_file)

    assert result.logging.level == "DEBUG"
    assert result.logging.file == "/var/log/tamatex.log"
    assert result.logging.max_size_mb == 20
    assert result.logging.backup_count == 10


# ---------------------------------------------------------------------------
# load_config: デフォルト値
# ---------------------------------------------------------------------------

def test_load_config_sync_default_interval_is_15(tmp_path):
    """sync セクション省略時は interval_minutes のデフォルト値が 15 であること。"""
    yaml_content = """
nas:
  base_path: /mnt/nas/data
google:
  credentials_path: /etc/creds.json
"""
    config_file = _write_yaml(tmp_path, yaml_content)
    result = load_config(config_file)

    assert result.sync.interval_minutes == 15


def test_load_config_log_default_level_is_info(tmp_path):
    """logging セクション省略時のデフォルトログレベルが INFO であること。"""
    yaml_content = """
nas:
  base_path: /mnt/nas/data
google:
  credentials_path: /etc/creds.json
"""
    config_file = _write_yaml(tmp_path, yaml_content)
    result = load_config(config_file)

    assert result.logging.level == "INFO"


def test_load_config_log_default_file_path(tmp_path):
    """logging セクション省略時のデフォルトログファイルパスが正しいこと。"""
    yaml_content = """
nas:
  base_path: /mnt/nas/data
google:
  credentials_path: /etc/creds.json
"""
    config_file = _write_yaml(tmp_path, yaml_content)
    result = load_config(config_file)

    assert result.logging.file == "./logs/tamatex.log"


def test_load_config_log_default_max_size_mb(tmp_path):
    """logging 省略時のデフォルト max_size_mb が 10 であること。"""
    yaml_content = """
nas:
  base_path: /mnt/nas/data
google:
  credentials_path: /etc/creds.json
"""
    config_file = _write_yaml(tmp_path, yaml_content)
    result = load_config(config_file)

    assert result.logging.max_size_mb == 10


def test_load_config_log_default_backup_count(tmp_path):
    """logging 省略時のデフォルト backup_count が 5 であること。"""
    yaml_content = """
nas:
  base_path: /mnt/nas/data
google:
  credentials_path: /etc/creds.json
"""
    config_file = _write_yaml(tmp_path, yaml_content)
    result = load_config(config_file)

    assert result.logging.backup_count == 5


def test_load_config_nas_default_file_patterns(tmp_path):
    """nas.file_patterns を省略した場合のデフォルト値が ['*.xlsx'] であること。"""
    yaml_content = """
nas:
  base_path: /mnt/nas/data
google:
  credentials_path: /etc/creds.json
"""
    config_file = _write_yaml(tmp_path, yaml_content)
    result = load_config(config_file)

    assert result.nas.file_patterns == ["*.xlsx"]


def test_load_config_nas_default_exclude_patterns(tmp_path):
    """nas.exclude_patterns を省略した場合のデフォルト値が正しいこと。"""
    yaml_content = """
nas:
  base_path: /mnt/nas/data
google:
  credentials_path: /etc/creds.json
"""
    config_file = _write_yaml(tmp_path, yaml_content)
    result = load_config(config_file)

    assert "~$*" in result.nas.exclude_patterns
    assert "*.tmp" in result.nas.exclude_patterns


def test_load_config_google_default_drive_folder_id(tmp_path):
    """drive_folder_id を省略した場合のデフォルト値が空文字であること。"""
    yaml_content = """
nas:
  base_path: /mnt/nas/data
google:
  credentials_path: /etc/creds.json
"""
    config_file = _write_yaml(tmp_path, yaml_content)
    result = load_config(config_file)

    assert result.google.drive_folder_id == ""


def test_load_config_google_default_share_with(tmp_path):
    """share_with を省略した場合のデフォルト値が空リストであること。"""
    yaml_content = """
nas:
  base_path: /mnt/nas/data
google:
  credentials_path: /etc/creds.json
"""
    config_file = _write_yaml(tmp_path, yaml_content)
    result = load_config(config_file)

    assert result.google.share_with == []


# ---------------------------------------------------------------------------
# load_config: エラー系
# ---------------------------------------------------------------------------

def test_load_config_raises_file_not_found_for_missing_file(tmp_path):
    """存在しないパスを渡した場合は FileNotFoundError が送出されること。"""
    nonexistent = tmp_path / "no_such_file.yaml"

    with pytest.raises(FileNotFoundError):
        load_config(nonexistent)


def test_load_config_raises_value_error_for_empty_file(tmp_path):
    """空の YAML ファイルを渡した場合は ValueError が送出されること。"""
    config_file = tmp_path / "empty.yaml"
    config_file.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="空"):
        load_config(config_file)


def test_load_config_raises_value_error_for_missing_nas_section(tmp_path):
    """'nas' セクションがない YAML は ValueError を送出すること。"""
    yaml_content = """
google:
  credentials_path: /etc/creds.json
"""
    config_file = _write_yaml(tmp_path, yaml_content)

    with pytest.raises(ValueError, match="nas"):
        load_config(config_file)


def test_load_config_raises_value_error_for_missing_google_section(tmp_path):
    """'google' セクションがない YAML は ValueError を送出すること。"""
    yaml_content = """
nas:
  base_path: /mnt/nas/data
"""
    config_file = _write_yaml(tmp_path, yaml_content)

    with pytest.raises(ValueError, match="google"):
        load_config(config_file)


def test_load_config_raises_value_error_for_invalid_parameter(tmp_path):
    """認識できないキーを含む YAML は ValueError を送出すること。"""
    yaml_content = """
nas:
  base_path: /mnt/nas/data
  unknown_key: unexpected_value
google:
  credentials_path: /etc/creds.json
"""
    config_file = _write_yaml(tmp_path, yaml_content)

    with pytest.raises((ValueError, TypeError)):
        load_config(config_file)


# ---------------------------------------------------------------------------
# dataclass 不変性テスト
# ---------------------------------------------------------------------------

def test_appconfig_is_frozen(tmp_path):
    """AppConfig は frozen dataclass なので属性変更が禁止されること。"""
    yaml_content = """
nas:
  base_path: /mnt/nas/data
google:
  credentials_path: /etc/creds.json
"""
    config_file = _write_yaml(tmp_path, yaml_content)
    result = load_config(config_file)

    with pytest.raises((AttributeError, TypeError)):
        result.sync = SyncConfig(interval_minutes=99)


def test_syncconfig_is_frozen():
    """SyncConfig は frozen dataclass なので属性変更が禁止されること。"""
    config = SyncConfig(interval_minutes=15)

    with pytest.raises((AttributeError, TypeError)):
        config.interval_minutes = 99


# ---------------------------------------------------------------------------
# sync.mode = "times" バリデーション
# ---------------------------------------------------------------------------

def test_load_config_accepts_times_mode_with_valid_times(tmp_path):
    """sync.mode='times' と正しい時刻リストが受理されること。"""
    yaml_content = """
nas:
  base_path: /nas
google:
  credentials_path: /creds.json
sync:
  mode: times
  times:
    - "12:00"
    - "15:00"
"""
    config = load_config(_write_yaml(tmp_path, yaml_content))
    assert config.sync.mode == "times"
    assert config.sync.times == ["12:00", "15:00"]


def test_load_config_defaults_to_interval_mode(tmp_path):
    """mode 未指定なら 'interval' がデフォルトで、従来通り動作すること。"""
    yaml_content = """
nas:
  base_path: /nas
google:
  credentials_path: /creds.json
sync:
  interval_minutes: 30
"""
    config = load_config(_write_yaml(tmp_path, yaml_content))
    assert config.sync.mode == "interval"
    assert config.sync.interval_minutes == 30


def test_load_config_rejects_invalid_mode(tmp_path):
    """不正な mode 値はエラーになること。"""
    yaml_content = """
nas:
  base_path: /nas
google:
  credentials_path: /creds.json
sync:
  mode: cron
"""
    with pytest.raises(ValueError, match="sync.mode"):
        load_config(_write_yaml(tmp_path, yaml_content))


def test_load_config_rejects_times_mode_without_times(tmp_path):
    """mode='times' で times が空ならエラーになること。"""
    yaml_content = """
nas:
  base_path: /nas
google:
  credentials_path: /creds.json
sync:
  mode: times
"""
    with pytest.raises(ValueError, match="少なくとも1つ"):
        load_config(_write_yaml(tmp_path, yaml_content))


def test_load_config_rejects_invalid_time_format(tmp_path):
    """times に不正な形式（25:00、12:60、12.00 等）が含まれたらエラー。"""
    yaml_content = """
nas:
  base_path: /nas
google:
  credentials_path: /creds.json
sync:
  mode: times
  times:
    - "25:00"
"""
    with pytest.raises(ValueError, match="HH:MM"):
        load_config(_write_yaml(tmp_path, yaml_content))


def test_load_config_rejects_zero_interval(tmp_path):
    """interval mode で interval_minutes=0 はエラーになること。"""
    yaml_content = """
nas:
  base_path: /nas
google:
  credentials_path: /creds.json
sync:
  interval_minutes: 0
"""
    with pytest.raises(ValueError, match="interval_minutes"):
        load_config(_write_yaml(tmp_path, yaml_content))
