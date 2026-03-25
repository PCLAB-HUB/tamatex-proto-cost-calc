"""メインモジュール。同期サイクルの実行とスケジューリング。"""

import argparse
import atexit
import logging
import signal
import sys
import threading
import time
from pathlib import Path

from tamatex import __version__
from tamatex.config import load_config, AppConfig
from tamatex.excel_reader import read_workbook
from tamatex.logger import setup_logger
from tamatex.sheets_sync import authenticate, create_spreadsheet, sync_workbook
from tamatex.state import StateDB
from tamatex.watcher import scan_files, detect_changes

logger = logging.getLogger("tamatex")

# グレースフルシャットダウン用イベント
_shutdown_event = threading.Event()


def _handle_signal(signum, frame):
    logger.info("シャットダウンシグナル受信 (signal=%d)", signum)
    _shutdown_event.set()


def sync_cycle(
    config: AppConfig,
    state_db: StateDB,
    client,
    shutdown_event: threading.Event | None = None,
) -> dict:
    """1回の同期サイクルを実行する。"""
    _event = shutdown_event or _shutdown_event
    stats = {"scanned": 0, "synced": 0, "errors": 0, "skipped": 0}

    # 1. NASフォルダをスキャン
    try:
        current_files = scan_files(
            config.nas.base_path,
            config.nas.file_patterns,
            config.nas.exclude_patterns,
        )
    except OSError as e:
        logger.error("NAS接続エラー（次回サイクルで再試行）: %s", e)
        return stats

    stats["scanned"] = len(current_files)

    if not current_files:
        logger.info("対象ファイルなし")
        return stats

    # 2. 変更を検知
    changes = detect_changes(current_files, state_db)

    files_to_sync = changes.new_files + changes.modified_files
    if not files_to_sync:
        logger.info("変更なし — スキップ")
        stats["skipped"] = stats["scanned"]
        return stats

    # 3. 変更ファイルを同期
    for file_info in files_to_sync:
        if _event.is_set():
            logger.info("シャットダウン要求のため同期中断")
            stats["skipped"] += len(files_to_sync) - stats["synced"] - stats["errors"]
            break

        file_path = file_info.path
        file_name = Path(file_path).stem
        is_new = file_info in changes.new_files

        try:
            # Excel読み取り
            workbook_data = read_workbook(file_path)

            # スプレッドシートの取得 or 作成
            state = state_db.get_state(file_path)
            if state and state.spreadsheet_id:
                spreadsheet_id = state.spreadsheet_id
            else:
                # 新規作成
                spreadsheet_id = create_spreadsheet(
                    client,
                    title=f"[同期] {file_name}",
                    folder_id=config.google.drive_folder_id,
                    share_with=config.google.share_with,
                )

            # 同期実行
            sync_workbook(client, workbook_data, spreadsheet_id)

            # 状態更新
            state_db.update_state(
                file_path=file_path,
                mtime=file_info.mtime,
                file_hash=file_info.file_hash,
                spreadsheet_id=spreadsheet_id,
            )

            action = "新規同期" if is_new else "更新同期"
            logger.info("%s完了: %s → %s", action, file_name, spreadsheet_id)
            stats["synced"] += 1

        except Exception as e:
            logger.error("同期失敗（スキップ）: %s - %s", file_name, e, exc_info=True)
            stats["errors"] += 1

    # 4. 削除されたファイルの記録（スプレッドシートは残す）
    for deleted_path in changes.deleted_paths:
        logger.warning("NAS上から削除検知: %s（スプレッドシートは保持）", deleted_path)
        state_db.remove_state(deleted_path)

    return stats


def run(config_path: str | Path) -> None:
    """メインループ。設定読み込み → 認証 → 定期同期。"""
    _shutdown_event.clear()

    # シグナルハンドラ登録
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # 設定読み込み
    config = load_config(config_path)
    setup_logger(config.logging)
    logger.info("=== tamatex 起動 (v%s) ===", __version__)
    logger.info("NASパス: %s", config.nas.base_path)
    logger.info("同期間隔: %d分", config.sync.interval_minutes)

    # 状態DB初期化（絶対パスで解決）
    if config.sync.state_db_path:
        db_path = Path(config.sync.state_db_path)
    else:
        db_path = Path(config_path).resolve().parent / "tamatex_state.db"
    state_db = StateDB(db_path=db_path)
    atexit.register(state_db.close)
    logger.info("状態DB: %s", db_path)

    # Google API認証
    client = authenticate(config.google.credentials_path)

    interval_sec = config.sync.interval_minutes * 60

    # 初回同期を即座に実行
    _run_sync_cycle(config, state_db, client)

    # 定期実行ループ
    while not _shutdown_event.is_set():
        logger.info("次回同期まで %d分 待機...", config.sync.interval_minutes)
        # Event.waitで待機（シグナルで即座に解除される）
        if _shutdown_event.wait(timeout=interval_sec):
            break
        _run_sync_cycle(config, state_db, client)

    logger.info("=== tamatex 正常終了 ===")


def _run_sync_cycle(config: AppConfig, state_db: StateDB, client) -> None:
    """同期サイクルを1回実行してログ出力する。"""
    logger.info("--- 同期サイクル開始 ---")
    try:
        stats = sync_cycle(config, state_db, client, _shutdown_event)
        logger.info(
            "--- 同期サイクル完了: スキャン=%d, 同期=%d, スキップ=%d, エラー=%d ---",
            stats["scanned"], stats["synced"], stats["skipped"], stats["errors"],
        )
    except Exception as e:
        logger.error("同期サイクルで予期しないエラー: %s", e, exc_info=True)


def main():
    parser = argparse.ArgumentParser(description="tamatex - Excel to Spreadsheet sync")
    parser.add_argument(
        "-c", "--config",
        default="./config/config.yaml",
        help="設定ファイルのパス (default: ./config/config.yaml)",
    )
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
