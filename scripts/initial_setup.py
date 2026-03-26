"""初回セットアップスクリプト。
NASフォルダ内のExcelファイルに対応するスプレッドシートを一括作成する。
"""

import sys
from pathlib import Path

# srcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tamatex.config import load_config
from tamatex.logger import setup_logger
from tamatex.sheets_sync import authenticate, create_spreadsheet
from tamatex.state import StateDB
from tamatex.watcher import scan_files


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "./config/config.yaml"
    config = load_config(config_path)
    logger = setup_logger(config.logging)

    logger.info("=== 初回セットアップ開始 ===")

    # 認証
    client = authenticate(config.google.credentials_path)

    # 状態DB（main.pyと同じパス解決ロジック）
    if config.sync.state_db_path:
        db_path = Path(config.sync.state_db_path)
    else:
        db_path = Path(config_path).resolve().parent / "tamatex_state.db"

    with StateDB(db_path=db_path) as state_db:
        logger.info("状態DB: %s", db_path)

        # NASスキャン
        files = scan_files(
            config.nas.base_path,
            config.nas.file_patterns,
            config.nas.exclude_patterns,
        )

        if not files:
            logger.warning("対象ファイルが見つかりません: %s", config.nas.base_path)
            return

        logger.info("検出ファイル: %d 個", len(files))

        for file_info in files:
            file_name = Path(file_info.path).stem
            state = state_db.get_state(file_info.path)

            if state and state.spreadsheet_id:
                logger.info("スキップ（既存）: %s → %s", file_name, state.spreadsheet_id)
                continue

            # スプレッドシート作成
            spreadsheet_id = create_spreadsheet(
                client,
                title=f"[同期] {file_name}",
                folder_id=config.google.drive_folder_id,
                share_with=config.google.share_with,
            )

            # 状態保存（hash=空で保存。次回同期で実データが書き込まれる）
            state_db.update_state(
                file_path=file_info.path,
                mtime=0,
                file_hash="",
                spreadsheet_id=spreadsheet_id,
            )

            logger.info("作成完了: %s → %s", file_name, spreadsheet_id)

    logger.info("=== 初回セットアップ完了 ===")
    logger.info("次のステップ: python -m tamatex.main -c config/config.yaml で同期を開始してください")


if __name__ == "__main__":
    main()
