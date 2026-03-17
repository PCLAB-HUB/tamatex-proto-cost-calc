"""ファイル監視モジュール。NASフォルダをポーリングして変更を検知する。"""

import fnmatch
import hashlib
import logging
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
) -> list[FileInfo]:
    """NASフォルダをスキャンして対象ファイル一覧を返す。"""
    base = Path(base_path)
    if not base.exists():
        logger.error("NASパスが見つかりません: %s", base_path)
        return []

    files: list[FileInfo] = []
    for pattern in file_patterns:
        for file_path in base.glob(pattern):
            if not file_path.is_file():
                continue
            if _matches_any(file_path.name, exclude_patterns):
                logger.debug("除外: %s", file_path.name)
                continue
            try:
                mtime = file_path.stat().st_mtime
                file_hash = _compute_file_hash(file_path)
                files.append(FileInfo(
                    path=str(file_path),
                    mtime=mtime,
                    file_hash=file_hash,
                ))
            except OSError as e:
                logger.warning("ファイル読み取りエラー（スキップ）: %s - %s", file_path, e)
                continue

    logger.info("スキャン完了: %d ファイル検出 (%s)", len(files), base_path)
    return files


def detect_changes(current_files: list[FileInfo], state_db: StateDB) -> ChangeResult:
    """現在のファイル状態とDB上の状態を比較し、変更を検知する。"""
    current_paths = {f.path for f in current_files}
    stored_states = {s.file_path: s for s in state_db.get_all_states()}
    stored_paths = set(stored_states.keys())

    new_files: list[FileInfo] = []
    modified_files: list[FileInfo] = []
    deleted_paths: list[str] = list(stored_paths - current_paths)

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
    )
