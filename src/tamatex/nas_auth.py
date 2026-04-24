"""NAS SMB 認証モジュール（Windows向け）。

Windowsサービス（NSSM）として稼働する場合、サービスセッションには
GUIログインセッションの credential キャッシュが共有されないため、
`net use` で明示的に認証を確立する必要がある。

設定に `nas.auth` セクションがある場合のみ動作する。
非Windows環境では何もしない。
"""

import logging
import subprocess
import sys

logger = logging.getLogger("tamatex")


def authenticate_nas(server: str, username: str, password: str) -> None:
    """現在のプロセスセッションに対して SMB 認証を確立する。

    既存の認証がある場合は /delete してから再設定する（重複エラー1219回避）。
    認証失敗時は RuntimeError を送出して呼び出し元にフェイルファストさせる。

    Parameters
    ----------
    server : str
        SMB サーバー名（例: "Tamatex-nas8tb"）。UNCバックスラッシュは不要。
    username : str
        SMB ユーザー名。
    password : str
        SMB パスワード。ログには出力しない。
    """
    if sys.platform != "win32":
        logger.info("非Windows環境のためNAS認証をスキップ")
        return

    unc_target = rf"\\{server}\IPC$"

    # 既存セッション認証をクリア（失敗しても無視）
    subprocess.run(
        ["net", "use", unc_target, "/delete"],
        capture_output=True,
        check=False,
    )

    # 認証確立。シェルを介さないためパスワードに特殊文字が含まれても安全。
    result = subprocess.run(
        ["net", "use", unc_target, f"/user:{username}", password],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        logger.error(
            "NAS認証失敗: server=%s user=%s returncode=%d",
            server, username, result.returncode,
        )
        logger.error("net use stderr: %s", (result.stderr or "").strip())
        raise RuntimeError(
            f"NAS認証失敗: server={server} user={username} "
            f"(net use returncode={result.returncode})"
        )

    logger.info("NAS認証成功: server=%s user=%s", server, username)
