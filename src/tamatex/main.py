"""メインモジュール。同期サイクルの実行とスケジューリング。"""

import argparse
import logging
import signal
import sys
import time
from pathlib import Path

from tamatex.config import load_config, AppConfig
from tamatex.excel_reader import read_workbook
from tamatex.logger import setup_logger
from tamatex.sheets_sync import authenticate, create_spreadsheet, sync_workbook
from tamatex.state import StateDB
from tamatex.watcher import scan_files, detect_changes

logger = logging.getLogger("tamatex")

# グレースフルシャットダウン用フラグ
_shutdown_requested = False


def _handle_signal(signum, frame):
    global _shutdown_requested
    logger.info("シャットダウンシグナル受信 (signal=%d)", signum)
    _shutdown_requested = True


def sync_cycle(config: AppConfig, state_db: StateDB, client) -> dict:
    """1回の同期サイクルを実行する。"""
    stats = {"scanned": 0, "synced": 0, "errors": 0, "skipped": 0}

    # 1. NASフォルダをスキャン
    current_files = scan_files(
        config.nas.base_path,
        config.nas.file_patterns,
        config.nas.exclude_patterns,
    )
    stats["scanned"] = len(current_files)

    if not current_files:
        logger.info("対象ファイルなし")
        return stats

    # 2. 変更を検知
    changes = detect_changes(current_files, state_db)

    files_to_sync = changes.new_files + changes.modified_files
    if not files_to_sync:
        logger.info("変更なし — スキップ")
        return stats

    # 3. 変更ファイルを同期
    for file_info in files_to_sync:
        if _shutdown_requested:
            logger.info("シャットダウン要求のため同期中断")
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


def run(config_path: str) -> None:
    """メインループ。設定読み込み → 認証 → 定期同期。"""
    global _shutdown_requested

    # シグナルハンドラ登録
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # 設定読み込み
    config = load_config(config_path)
    setup_logger(config.logging)
    logger.info("=== tamatex 起動 (v0.1.0) ===")
    logger.info("NASパス: %s", config.nas.base_path)
    logger.info("同期間隔: %d分", config.sync.interval_minutes)

    # 状態DB初期化
    state_db = StateDB()

    # Google API認証
    client = authenticate(config.google.credentials_path)

    interval_sec = config.sync.interval_minutes * 60

    # 初回同期を即座に実行
    logger.info("--- 同期サイクル開始 ---")
    try:
        stats = sync_cycle(config, state_db, client)
        logger.info(
            "--- 同期サイクル完了: スキャン=%d, 同期=%d, エラー=%d ---",
            stats["scanned"], stats["synced"], stats["errors"],
        )
    except Exception as e:
        logger.error("同期サイクルで予期しないエラー: %s", e, exc_info=True)

    # 定期実行ループ
    while not _shutdown_requested:
        logger.info("次回同期まで %d分 待機...", config.sync.interval_minutes)
        # 待機中もシャットダウン要求を検知するため小刻みにsleep
        for _ in range(interval_sec):
            if _shutdown_requested:
                break
            time.sleep(1)

        if _shutdown_requested:
            break

        logger.info("--- 同期サイクル開始 ---")
        try:
            stats = sync_cycle(config, state_db, client)
            logger.info(
                "--- 同期サイクル完了: スキャン=%d, 同期=%d, エラー=%d ---",
                stats["scanned"], stats["synced"], stats["errors"],
            )
        except Exception as e:
            logger.error("同期サイクルで予期しないエラー: %s", e, exc_info=True)

    logger.info("=== tamatex 正常終了 ===")


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
