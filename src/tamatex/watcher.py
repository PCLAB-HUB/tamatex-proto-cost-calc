"""ファイル監視モジュール。NASフォルダをポーリングして変更を検知する。"""

import fnmatch
import hashlib
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from tamatex.state import StateDB

logger = logging.getLogger("tamatex")

HASH_CHUNK_SIZE = 8192


@dataclass
class FileInfo:
    path: str
    mtime: float
    file_hash: str


@dataclass
class ChangeResult:
    new_files: list[FileInfo]
    modified_files: list[FileInfo]
    deleted_paths: list[str]
    stored_total: int = 0


def _compute_file_hash(path: Path) -> str:
    """ファイルのMD5ハッシュを計算する。"""
    md5 = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(HASH_CHUNK_SIZE):
            md5.update(chunk)
    return md5.hexdigest()


def _matches_any(filename: str, patterns: list[str]) -> bool:
    """ファイル名がいずれかのパターンにマッチするか。"""
    return any(fnmatch.fnmatch(filename, p) for p in patterns)


def scan_files(
    base_path: str,
    file_patterns: list[str],
    exclude_patterns: list[str],
) -> tuple[list[FileInfo], bool]:
    """NASフォルダをスキャンして ``(対象ファイル一覧, 走査完全フラグ)`` を返す。

    走査完全フラグは、列挙・読取で1件でも ``OSError`` を握りつぶした場合 False。
    呼び出し側はこのフラグが False のサイクルでは削除伝播を保留すべき
    （部分I/O障害で実在ファイルを誤って削除扱いにしないため）。
    """
    base = Path(base_path)
    if not base.exists():
        raise OSError(f"NASパスが見つかりません: {base_path}")

    base_resolved = base.resolve()
    files: list[FileInfo] = []
    scan_complete = True
    for pattern in file_patterns:
        for file_path in base.rglob(pattern):
            if not file_path.is_file():
                continue
            if _matches_any(file_path.name, exclude_patterns):
                logger.debug("除外: %s", file_path.name)
                continue
            try:
                resolved = file_path.resolve()
                # シンボリックリンクによるbase_path外への追跡を防止
                try:
                    resolved.relative_to(base_resolved)
                except ValueError:
                    logger.warning("base_path外のファイル（スキップ）: %s -> %s", file_path, resolved)
                    continue
                mtime_before = resolved.stat().st_mtime
                file_hash = _compute_file_hash(resolved)
                mtime_after = resolved.stat().st_mtime
                if mtime_after != mtime_before:
                    logger.debug("書き込み中のためスキップ: %s", resolved)
                    continue
                files.append(FileInfo(
                    path=str(resolved),
                    mtime=mtime_before,
                    file_hash=file_hash,
                ))
            except OSError as e:
                logger.warning("ファイル読み取りエラー（スキップ）: %s - %s", file_path, e)
                # 部分I/O障害。このサイクルの走査は不完全とみなす。
                scan_complete = False
                continue

    logger.info(
        "スキャン完了: %d ファイル検出 (%s)%s",
        len(files), base_path, "" if scan_complete else " ※走査不完全",
    )
    return files, scan_complete


def detect_changes(current_files: list[FileInfo], state_db: StateDB) -> ChangeResult:
    """現在のファイル状態とDB上の状態を比較し、変更を検知する。"""
    current_paths = {f.path for f in current_files}
    stored_states = {s.file_path: s for s in state_db.get_all_states()}
    stored_paths = set(stored_states.keys())

    new_files: list[FileInfo] = []
    modified_files: list[FileInfo] = []

    if not current_files and stored_paths:
        logger.warning("現在のファイルが空ですがDBに状態が存在します。NAS切断の可能性があるため削除検知をスキップします。")
        deleted_paths: list[str] = []
    else:
        deleted_paths = list(stored_paths - current_paths)

    for file_info in current_files:
        state = stored_states.get(file_info.path)
        if state is None:
            new_files.append(file_info)
        elif file_info.file_hash != state.file_hash:
            modified_files.append(file_info)

    if new_files:
        logger.info("新規ファイル: %d 件", len(new_files))
    if modified_files:
        logger.info("更新ファイル: %d 件", len(modified_files))
    if deleted_paths:
        logger.info("削除ファイル: %d 件", len(deleted_paths))

    return ChangeResult(
        new_files=new_files,
        modified_files=modified_files,
        deleted_paths=deleted_paths,
        stored_total=len(stored_states),
    )
