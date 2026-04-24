"""nas_auth モジュールのユニットテスト。"""
import sys
from unittest.mock import patch, MagicMock

import pytest

from tamatex.nas_auth import authenticate_nas


class TestAuthenticateNas:
    def test_non_windows_is_noop(self):
        """非Windows環境では subprocess を呼ばない。"""
        with patch("tamatex.nas_auth.sys") as mock_sys, \
             patch("tamatex.nas_auth.subprocess.run") as mock_run:
            mock_sys.platform = "darwin"
            authenticate_nas("server", "user", "pass")
            mock_run.assert_not_called()

    def test_windows_success(self):
        """認証成功時: /delete → /user:xxx pwd の2回呼び出し、エラーを送出しない。"""
        with patch("tamatex.nas_auth.sys") as mock_sys, \
             patch("tamatex.nas_auth.subprocess.run") as mock_run:
            mock_sys.platform = "win32"
            mock_run.side_effect = [
                MagicMock(returncode=2),          # /delete (存在しないのでエラーでもOK)
                MagicMock(returncode=0, stderr=""),  # /user:xxx pwd 成功
            ]
            authenticate_nas("srv", "admin", "secret")
            assert mock_run.call_count == 2
            delete_call = mock_run.call_args_list[0]
            add_call = mock_run.call_args_list[1]
            assert r"\\srv\IPC$" in delete_call.args[0]
            assert "/delete" in delete_call.args[0]
            assert "/user:admin" in add_call.args[0]
            assert "secret" in add_call.args[0]

    def test_windows_failure_raises(self):
        """認証失敗時: RuntimeError を送出。"""
        with patch("tamatex.nas_auth.sys") as mock_sys, \
             patch("tamatex.nas_auth.subprocess.run") as mock_run:
            mock_sys.platform = "win32"
            mock_run.side_effect = [
                MagicMock(returncode=2),
                MagicMock(returncode=2, stderr="System error 1326"),
            ]
            with pytest.raises(RuntimeError, match="NAS認証失敗"):
                authenticate_nas("srv", "admin", "wrong")

    def test_password_not_passed_through_shell(self):
        """subprocess.run を shell=True で呼ばない（パスワード特殊文字対策）。"""
        with patch("tamatex.nas_auth.sys") as mock_sys, \
             patch("tamatex.nas_auth.subprocess.run") as mock_run:
            mock_sys.platform = "win32"
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            authenticate_nas("srv", "user", "p@ss w!rd")
            for call in mock_run.call_args_list:
                assert "shell" not in call.kwargs or call.kwargs["shell"] is not True


class TestConfigWithAuth:
    """config.py の NasConfig.auth が正しくパースされるか。"""

    def test_load_config_with_auth(self, tmp_path):
        """nas.auth セクション付き YAML が正しくパースされる。"""
        from tamatex.config import load_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
nas:
  base_path: "Z:/share"
  auth:
    server: "TestNas"
    username: "admin"
    password: "secret"
google:
  credentials_path: "./sa.json"
""".strip(),
            encoding="utf-8",
        )
        cfg = load_config(config_file)
        assert cfg.nas.auth is not None
        assert cfg.nas.auth.server == "TestNas"
        assert cfg.nas.auth.username == "admin"
        assert cfg.nas.auth.password == "secret"

    def test_load_config_without_auth(self, tmp_path):
        """auth セクション省略時は None になる。"""
        from tamatex.config import load_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
nas:
  base_path: "Z:/share"
google:
  credentials_path: "./sa.json"
""".strip(),
            encoding="utf-8",
        )
        cfg = load_config(config_file)
        assert cfg.nas.auth is None
