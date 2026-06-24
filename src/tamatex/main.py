"""メインモジュール。同期サイクルの実行とスケジューリング。

同期先フォルダ配下に Sheets/ と PDF/ のサブフォルダを自動作成し、
同名ファイルをそれぞれに配置する。既存ファイルは fileId 維持のまま
中身と配置場所を更新するため、URL は不変。
"""

import argparse
import atexit
import logging
import signal
import threading
from datetime import datetime, timedelta
from pathlib import Path

from tamatex import __version__
from tamatex.config import AppConfig, load_config
from tamatex.drive_utils import (
    apply_share,
    build_drive_service,
    ensure_folder_path,
    ensure_subfolder,
    move_to_folder,
    trash_file,
)
from tamatex.logger import setup_logger
from tamatex.nas_auth import authenticate_nas
from tamatex.pdf_sync import upsert_pdf
from tamatex.sheets_sync import upsert_sheet
from tamatex.state import StateDB
from tamatex.watcher import detect_changes, scan_files

logger = logging.getLogger("tamatex")

SHEETS_SUBFOLDER = "Sheets"
PDF_SUBFOLDER = "PDF"

MASS_DELETE_MIN = 5       # これ未満の削除は常に通す（小規模整理を妨げない）
MASS_DELETE_RATIO = 0.4   # 登録総数のこの割合を超える削除はブロック


def _is_mass_deletion(deleted_count: int, stored_total: int) -> bool:
    """一括消失ガード判定。True なら異常とみなし削除をスキップすべき。

    NAS部分マウント失敗時に大量ファイルが誤って削除判定されるのを防ぐ。
    """
    if deleted_count < MASS_DELETE_MIN:
        return False
    if stored_total <= 0:
        return False
    return deleted_count > stored_total * MASS_DELETE_RATIO


def _classify_deletions(
    absent_paths: list[str], prev_pending: set[str]
) -> tuple[list[str], set[str]]:
    """2サイクル確認（誤削除防止）の純関数。

    削除候補は「初回不在」では確定せず保留し、2サイクル連続で不在を確認できた
    ものだけを削除確定とする。NASの一時的な部分アンマウントで実体ごと不可視に
    なったファイルは次サイクルで復帰して保留から脱落するため、誤って Drive を
    ゴミ箱送りにする（＝URL断絶・重複生成）ことを防ぐ。

    Parameters
    ----------
    absent_paths : list[str]
        今サイクルで（実体も）不在と確認された削除候補パス。
    prev_pending : set[str]
        前サイクルで不在だった（保留中の）パス集合。

    Returns
    -------
    tuple[list[str], set[str]]
        ``(confirmed, new_pending)``。``confirmed`` = 前サイクルも不在だった
        → 削除確定（trash対象）。``new_pending`` = 今回初めて不在 → 次サイクルで
        再確認するため保留。
    """
    confirmed = [p for p in absent_paths if p in prev_pending]
    new_pending = {p for p in absent_paths if p not in prev_pending}
    return confirmed, new_pending


_shutdown_event = threading.Event()


def _handle_signal(signum, frame):
    logger.info("シャットダウンシグナル受信 (signal=%d)", signum)
    _shutdown_event.set()


def _subfolder_parts(file_path: str, base_path: str) -> list[str]:
    """NAS の絶対パスから base_path を除いた、親ディレクトリの階層パーツを返す。

    例: base="/nas/data", file="/nas/data/テスト/foo.xlsx" → ["テスト"]
    例: base="/nas/data", file="/nas/data/foo.xlsx"        → []
    """
    try:
        rel = Path(file_path).relative_to(Path(base_path))
    except ValueError:
        # base_path 外（通常起きない、watcher がガード済み）
        return []
    return list(rel.parent.parts)


def _resolve_target_folders(
    service,
    file_path: str,
    config: AppConfig,
    sheets_root_id: str,
    pdf_root_id: str,
    cache: dict[tuple[str, ...], tuple[str, str]],
) -> tuple[str, str]:
    """ファイルの NAS 配置から、対応する Drive 上の Sheets/PDF サブフォルダIDを返す。

    mirror_subfolders が False ならルート直下を返す。
    cache はサイクル内でフォルダ ID を再利用してAPI呼出を削減する。
    """
    if not config.sync.mirror_subfolders:
        return sheets_root_id, pdf_root_id

    parts = _subfolder_parts(file_path, config.nas.base_path)
    if not parts:
        return sheets_root_id, pdf_root_id

    key = tuple(parts)
    if key in cache:
        return cache[key]

    sheets_target = ensure_folder_path(service, sheets_root_id, parts)
    pdf_target = ensure_folder_path(service, pdf_root_id, parts)
    cache[key] = (sheets_target, pdf_target)
    return cache[key]


def reorganize_existing_files(
    config: AppConfig,
    state_db: StateDB,
    service,
    sheets_root_id: str,
    pdf_root_id: str,
) -> int:
    """state.db に登録済みの全ファイルを、NAS階層に対応するDriveサブフォルダへ再配置する。

    起動時に1回呼ぶ想定。fileId は維持されるため URL は不変。
    既に正しい場所にあるファイルは move_to_folder 内でスキップされる。
    Returns: 移動した（または確認した）ファイル数。
    """
    if not config.sync.mirror_subfolders:
        return 0

    cache: dict[tuple[str, ...], tuple[str, str]] = {}
    moved = 0
    for state in state_db.get_all_states():
        parts = _subfolder_parts(state.file_path, config.nas.base_path)
        if not parts:
            continue  # ルート直下、移動不要

        key = tuple(parts)
        if key in cache:
            sheets_target, pdf_target = cache[key]
        else:
            sheets_target = ensure_folder_path(service, sheets_root_id, parts)
            pdf_target = ensure_folder_path(service, pdf_root_id, parts)
            cache[key] = (sheets_target, pdf_target)

        try:
            if state.spreadsheet_id:
                move_to_folder(service, state.spreadsheet_id, sheets_target)
            if state.pdf_file_id:
                move_to_folder(service, state.pdf_file_id, pdf_target)
            moved += 1
        except Exception as e:
            logger.warning(
                "再配置失敗（続行）: %s - %s",
                Path(state.file_path).name, e,
            )
    return moved


def sync_cycle(
    config: AppConfig,
    state_db: StateDB,
    service,
    sheets_folder_id: str,
    pdf_folder_id: str,
    shutdown_event: threading.Event | None = None,
    pending_deletions: set[str] | None = None,
) -> dict:
    """1回の同期サイクルを実行する。"""
    _event = shutdown_event or _shutdown_event
    # 2サイクル確認用の保留集合。run() がサイクル跨ぎで保持して渡す。
    # 単独呼び出し（None）では使い捨ての空集合とし、削除は確定しない。
    _pending = pending_deletions if pending_deletions is not None else set()
    stats = {"scanned": 0, "synced": 0, "errors": 0, "skipped": 0}
    folder_cache: dict[tuple[str, ...], tuple[str, str]] = {}

    # 1. NASフォルダをスキャン
    try:
        current_files, scan_complete = scan_files(
            config.nas.base_path,
            config.nas.file_patterns,
            config.nas.exclude_patterns,
        )
    except OSError as e:
        logger.error("NAS接続エラー（次回サイクルで再試行）: %s", e)
        # 信頼できないサイクル: 2サイクル確認の連続性を切る（非連続不在の誤確定防止）。
        _pending.clear()
        return stats

    stats["scanned"] = len(current_files)

    if not current_files:
        logger.info("対象ファイルなし")
        # 全切断/全不可視と区別できないため、ここでも保留をリセットする。
        _pending.clear()
        return stats

    # 2. 変更を検知
    changes = detect_changes(current_files, state_db)
    files_to_sync = list(changes.new_files) + list(changes.modified_files)

    # 2b. PDF未生成のファイルも同期対象に含める（旧版からのアップグレード初回対応）
    synced_paths = {f.path for f in files_to_sync}
    for file_info in current_files:
        if file_info.path in synced_paths:
            continue
        state = state_db.get_state(file_info.path)
        if state and not state.pdf_file_id:
            files_to_sync.append(file_info)
            logger.info(
                "PDF未生成のため同期対象に追加: %s",
                Path(file_info.path).name,
            )

    if not files_to_sync:
        logger.info("変更なし（新規/更新なし）— 削除検知のみ評価")
        stats["skipped"] = stats["scanned"]
    else:
        stats["skipped"] = stats["scanned"] - len(files_to_sync)

    # 3. 変更ファイルを同期
    for file_info in files_to_sync:
        if _event.is_set():
            logger.info("シャットダウン要求のため同期中断")
            break

        file_path = file_info.path
        file_name = Path(file_path).stem

        try:
            state = state_db.get_state(file_path)
            existing_sheet_id = state.spreadsheet_id if state else ""
            existing_pdf_id = state.pdf_file_id if state else ""

            # NAS階層に対応する Drive 上のサブフォルダ ID を解決
            sheets_target, pdf_target = _resolve_target_folders(
                service, file_path, config,
                sheets_folder_id, pdf_folder_id, folder_cache,
            )

            # Sheets: xlsx 変換アップロード（既存fileId維持、フォルダ矯正）
            sheet_title = f"[同期] {file_name}"
            sheet_id = upsert_sheet(
                service,
                xlsx_path=file_path,
                title=sheet_title,
                folder_id=sheets_target,
                existing_file_id=existing_sheet_id,
            )

            # 共有設定を冪等適用（失敗しても同期本体は継続）
            try:
                apply_share(service, sheet_id, config.google.share_with)
            except Exception as e:
                logger.warning("Sheets共有設定でエラー（続行）: %s - %s", sheet_id, e)

            # PDF: Sheetsから export して保存
            pdf_title = f"{file_name}.pdf"
            pdf_id = upsert_pdf(
                service,
                sheet_file_id=sheet_id,
                title=pdf_title,
                folder_id=pdf_target,
                existing_pdf_id=existing_pdf_id,
            )
            try:
                apply_share(service, pdf_id, config.google.share_with)
            except Exception as e:
                logger.warning("PDF共有設定でエラー（続行）: %s - %s", pdf_id, e)

            # 状態更新
            state_db.update_state(
                file_path=file_path,
                mtime=file_info.mtime,
                file_hash=file_info.file_hash,
                spreadsheet_id=sheet_id,
                pdf_file_id=pdf_id,
            )

            logger.info(
                "同期完了: %s → Sheets=%s PDF=%s",
                file_name, sheet_id, pdf_id,
            )
            stats["synced"] += 1

        except Exception as e:
            logger.error("同期失敗（スキップ）: %s - %s", file_name, e, exc_info=True)
            stats["errors"] += 1

    # 4. NAS削除のDrive追従（2サイクル確認＋一括消失ガード）
    deleted = changes.deleted_paths
    if not scan_complete:
        # 走査が不完全（部分I/O障害）なサイクルは削除確認として信頼できない。
        # 連続性を切るため pending をリセットし、削除伝播は行わない。
        if deleted:
            logger.warning(
                "走査不完全のため削除伝播を保留し2サイクル確認をリセット（%d件）",
                len(deleted),
            )
        _pending.clear()
    elif deleted and _event.is_set():
        # 破壊的操作の保護: 停止要求が出ているサイクルでは削除を行わない。
        logger.info("シャットダウン要求のため削除伝播をスキップ（%d件保留）", len(deleted))
    elif deleted and _is_mass_deletion(len(deleted), changes.stored_total):
        logger.warning(
            "一括消失ガード発動: 削除候補=%d件 / 登録総数=%d件。"
            "NAS部分障害または大規模整理の可能性があるため今サイクルの削除を保留します"
            "（Drive上のファイルは保持。意図した一括削除なら運用者の確認が必要）。",
            len(deleted), changes.stored_total,
        )
        # 信頼できないサイクル: pending をリセットし、復帰済みファイルが保留に
        # 残って非連続2回で誤確定されるのを防ぐ。
        _pending.clear()
    else:
        # deleted が空のサイクルでも到達する。前サイクルで保留したが今サイクル
        # 復帰したファイルを保留から確実に外すため、ここで pending を再評価する。
        # 誤削除防止1: 走査時に一時スキップ（保存中・一時I/Oエラー）されただけで
        # 実体がまだNASに在るファイルは削除候補から除外する（URL維持）。
        absent: list[str] = []
        for deleted_path in deleted:
            if _event.is_set():
                break
            if Path(deleted_path).exists():
                logger.warning(
                    "削除検知だが実体が存在するため除外（走査時の一時スキップと判断）: %s",
                    deleted_path,
                )
                continue
            absent.append(deleted_path)

        if not _event.is_set():
            # 誤削除防止2: 2サイクル連続で不在を確認したものだけ削除確定。
            confirmed, new_pending = _classify_deletions(absent, _pending)
            for deleted_path in new_pending:
                logger.info(
                    "削除候補を保留（次サイクルで不在を再確認）: %s", deleted_path
                )
            for deleted_path in confirmed:
                if _event.is_set():
                    logger.info("シャットダウン要求のため削除伝播を中断")
                    break
                try:
                    state = state_db.get_state(deleted_path)
                    if state:
                        # 各破壊的操作の直前で停止要求を再確認し、
                        # shutdown後に新たなtrash/state削除を開始しない。
                        if state.spreadsheet_id:
                            if _event.is_set():
                                break
                            trash_file(service, state.spreadsheet_id)
                        if state.pdf_file_id:
                            if _event.is_set():
                                break
                            trash_file(service, state.pdf_file_id)
                    if _event.is_set():
                        logger.info(
                            "シャットダウン要求のため state 削除を中断: %s", deleted_path
                        )
                        break
                    state_db.remove_state(deleted_path)
                    logger.info(
                        "NAS削除を追従（2サイクル確認済み・Driveゴミ箱へ移動）: %s",
                        deleted_path,
                    )
                except Exception as e:
                    logger.error("削除追従エラー（スキップ）: %s - %s", deleted_path, e)
                    stats["errors"] += 1

            # 保留集合を更新（確定分・復帰分は脱落、初回不在のみ残す）。
            # shutdown 途中で抜けた場合は pending を変えず次回へ持ち越す。
            if not _event.is_set():
                _pending.clear()
                _pending.update(new_pending)

    return stats


def run(config_path: str | Path) -> None:
    """メインループ。設定読み込み → 認証 → 定期同期。"""
    _shutdown_event.clear()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    config = load_config(config_path)
    setup_logger(config.logging)
    logger.info("=== tamatex 起動 (v%s) ===", __version__)
    logger.info("NASパス: %s", config.nas.base_path)
    if config.sync.mode == "times":
        logger.info("同期スケジュール: 時刻指定 %s", config.sync.times)
    else:
        logger.info("同期間隔: %d分", config.sync.interval_minutes)

    # NAS SMB認証（サービス実行時に必須）
    if config.nas.auth is not None:
        authenticate_nas(
            config.nas.auth.server,
            config.nas.auth.username,
            config.nas.auth.password,
        )

    # 状態DB初期化
    if config.sync.state_db_path:
        db_path = Path(config.sync.state_db_path)
    else:
        db_path = Path(config_path).resolve().parent / "tamatex_state.db"
    state_db = StateDB(db_path=db_path)
    atexit.register(state_db.close)
    logger.info("状態DB: %s", db_path)

    # Google Drive API 認証
    service = build_drive_service(config.google.credentials_path)

    # サブフォルダ Sheets/ PDF/ を確保
    sheets_folder_id = ensure_subfolder(
        service, config.google.drive_folder_id, SHEETS_SUBFOLDER
    )
    pdf_folder_id = ensure_subfolder(
        service, config.google.drive_folder_id, PDF_SUBFOLDER
    )
    logger.info("Sheetsフォルダ: %s", sheets_folder_id)
    logger.info("PDFフォルダ  : %s", pdf_folder_id)

    # NAS のサブフォルダ構造を Drive 側にも反映する設定なら、
    # 起動時に既存ファイルを正しいサブフォルダへ再配置する（fileId維持・URL不変）
    if config.sync.mirror_subfolders:
        logger.info("NASフォルダ階層ミラー: 有効 — 既存ファイルを再配置中...")
        moved = reorganize_existing_files(
            config, state_db, service, sheets_folder_id, pdf_folder_id
        )
        logger.info("再配置完了: %d ファイル処理", moved)

    # 削除伝播の2サイクル確認用。前サイクルで不在だった削除候補を保持する。
    pending_deletions: set[str] = set()

    # 初回同期を即座に実行（PC起動時の朝同期に相当）
    _run_sync_cycle(
        config, state_db, service, sheets_folder_id, pdf_folder_id,
        pending_deletions,
    )

    # 定期実行ループ
    # 長時間の sleep 後に httplib2 の TCP セッションが死ぬ問題があるため、
    # 各サイクル前に service を再生成して transient エラーの初発を抑制する。
    # 加えて Windows モダンスタンバイ/休止からのスリープ復帰時にタイマー
    # が伸びる問題への対策として、_sleep_until_event で壁時計を最大60秒毎に
    # 確認しながら待機する。
    while not _shutdown_event.is_set():
        wait_sec, next_run_at = _compute_next_wait(config, datetime.now())
        if next_run_at is None:
            # interval モードは絶対時刻が無いため、現在時刻から積算した
            # 仮想的な target_time を作って同一の待機ロジックに乗せる。
            next_run_at = datetime.now() + timedelta(seconds=wait_sec)
            logger.info("次回同期まで %.0f秒 待機...", wait_sec)
        else:
            logger.info(
                "次回同期: %s（%.0f秒後）",
                next_run_at.strftime("%Y-%m-%d %H:%M:%S"), wait_sec,
            )
        if not _sleep_until_event(next_run_at, _shutdown_event):
            break
        # service 再生成は失敗してもデーモンを止めない。認証ファイルの一時的な
        # 読み取り不可や Google 側の一時障害があっても、前回の service で
        # サイクルを試み、_run_sync_cycle 内のリトライ機構と with_retry に救出を委ねる。
        try:
            service = build_drive_service(config.google.credentials_path, quiet=True)
        except Exception as e:
            logger.error(
                "service再生成失敗（前回のserviceで継続）: %s", e, exc_info=True
            )
        _run_sync_cycle(
            config, state_db, service, sheets_folder_id, pdf_folder_id,
            pending_deletions,
        )

    logger.info("=== tamatex 正常終了 ===")


def _sleep_until_event(
    target_time: datetime,
    shutdown_event: threading.Event,
    chunk_sec: float = 60.0,
    _now=datetime.now,
) -> bool:
    """目標時刻まで chunk_sec ごとに壁時計をチェックしながら待機する。

    Windows モダンスタンバイ/休止状態のスリープから復帰した直後でも、
    最大 chunk_sec の遅延で予定時刻越えを検知して抜ける。
    Python の threading.Event.wait は内部的に OS の相対時間ベースの
    タイマーを使うため、PC がスリープすると残時間がフリーズし
    「予定時刻を過ぎても sleep し続ける」現象が発生する。本関数は
    短いチャンクで wait を分割し、毎回 datetime.now() （壁時計）を見て
    実時刻が target_time を超えていないか確認することでこれを回避する。

    Parameters
    ----------
    target_time : datetime
        目標とする絶対時刻。
    shutdown_event : threading.Event
        シャットダウン要求の通知。発火時は即 False を返す。
    chunk_sec : float
        1回の wait の最大長さ（秒）。デフォルト 60.0。
        PC スリープ復帰時の最大検知遅延に等しい。
    _now : callable
        テスト用注入ポイント。デフォルトは ``datetime.now``。

    Returns
    -------
    bool
        ``True``: 目標時刻に到達。``False``: shutdown 要求あり。
    """
    while not shutdown_event.is_set():
        remaining = (target_time - _now()).total_seconds()
        if remaining <= 0:
            return True
        chunk = min(remaining, chunk_sec)
        if shutdown_event.wait(timeout=chunk):
            return False
    return False


def _compute_next_wait(
    config: AppConfig, now: datetime
) -> tuple[float, datetime | None]:
    """次回同期までの待機秒数と、その絶対時刻を返す。

    sync.mode == "times" のときは指定時刻リストから次の発火時刻を計算する。
    それ以外は interval_minutes ベースの単純待機。
    """
    if config.sync.mode == "times" and config.sync.times:
        candidates: list[datetime] = []
        for t in config.sync.times:
            hh, mm = map(int, t.split(":"))
            today_target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if today_target > now:
                candidates.append(today_target)
            else:
                candidates.append(today_target + timedelta(days=1))
        next_run = min(candidates)
        wait = max((next_run - now).total_seconds(), 1.0)
        return wait, next_run

    return float(config.sync.interval_minutes * 60), None


def _run_sync_cycle(
    config: AppConfig,
    state_db: StateDB,
    service,
    sheets_folder_id: str,
    pdf_folder_id: str,
    pending_deletions: set[str] | None = None,
) -> None:
    """同期サイクルを1回実行してログ出力する。"""
    logger.info("--- 同期サイクル開始 ---")
    try:
        stats = sync_cycle(
            config, state_db, service,
            sheets_folder_id, pdf_folder_id,
            _shutdown_event,
            pending_deletions,
        )
        logger.info(
            "--- 同期サイクル完了: スキャン=%d, 同期=%d, スキップ=%d, エラー=%d ---",
            stats["scanned"], stats["synced"], stats["skipped"], stats["errors"],
        )
    except Exception as e:
        logger.error("同期サイクルで予期しないエラー: %s", e, exc_info=True)
        # 信頼できないサイクル: 渡した pending をリセットし、次サイクルでの
        # 非連続不在の誤確定を防ぐ。
        if pending_deletions is not None:
            pending_deletions.clear()


def main():
    parser = argparse.ArgumentParser(
        description="tamatex - Excel to Google Sheets/PDF sync"
    )
    parser.add_argument(
        "-c", "--config",
        default="./config/config.yaml",
        help="設定ファイルのパス (default: ./config/config.yaml)",
    )
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
