# NAS削除のDrive追従（削除伝播）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** NASから消えたExcelに対応する Drive 上の Sheets/PDF をゴミ箱へ移動し、一括消失ガードで誤削除を防ぐ。

**Architecture:** `drive_utils.trash_file` でゴミ箱移動を提供。`watcher.ChangeResult` に登録総数 `stored_total` を追加。`main.sync_cycle` のステップ4を「一括ガード判定 → trash → state行削除」に書き換え、削除処理が `files_to_sync` 空でも走るよう早期returnを撤去。

**Tech Stack:** Python 3.11+, google-api-python-client, pytest, unittest.mock。

## Global Constraints

- 完全削除（`files.delete`）は使わない。削除はすべて `trashed=True`（ゴミ箱、30日復元可）。
- すべての Drive API 呼出は `with_retry` でラップ。
- 一括消失ガード定数: `MASS_DELETE_MIN = 5`、`MASS_DELETE_RATIO = 0.4`。条件 `deleted_count > stored_total * 0.4`（60件中25件以上でブロック、24件以下は通る）。
- 既存の NAS全切断ガード（`scan_files` 空 → 早期return、`detect_changes` の current空スキップ）は維持。
- git 操作はメインがまとめて行う。各タスク末尾でコミット。
- テストは決定的・1テスト1検証。`MagicMock` で service を差し替え、`StateDB` は `tmp_path`。

---

### Task 1: `drive_utils.trash_file`

**Files:**
- Modify: `src/tamatex/drive_utils.py`（末尾に関数追加）
- Test: `tests/test_drive_utils.py`（末尾に追加）

**Interfaces:**
- Consumes: 既存 `with_retry`, `HttpError`（import 済み）
- Produces: `trash_file(service, file_id: str) -> None`（trashed=True で update、404は握りつぶし、それ以外の HttpError は raise）

- [ ] **Step 1: Write the failing tests**

`tests/test_drive_utils.py` の import に `trash_file` を追加し、末尾に追記:

```python
# ---------------------------------------------------------------------------
# trash_file
# ---------------------------------------------------------------------------

def test_trash_file_sets_trashed_true():
    """trashed=True を指定した update が対象 fileId で呼ばれること。"""
    svc = MagicMock()
    trash_file(svc, "fid")
    body_calls = [
        c for c in svc.files().update.call_args_list if c.kwargs.get("body")
    ]
    assert any(c.kwargs["body"] == {"trashed": True} for c in body_calls)
    assert any(c.kwargs.get("fileId") == "fid" for c in body_calls)


def test_trash_file_ignores_404():
    """既に存在しない(404)場合は例外を握りつぶす。"""
    svc = MagicMock()
    svc.files().update().execute.side_effect = _mk_http_error(404)
    trash_file(svc, "missing")  # raise しないこと


def test_trash_file_raises_on_non_404():
    """404 以外の HttpError はそのまま送出する。"""
    svc = MagicMock()
    svc.files().update().execute.side_effect = _mk_http_error(403)
    with pytest.raises(HttpError):
        trash_file(svc, "forbidden")
```

import 行を更新:
```python
from tamatex.drive_utils import (
    MIME_FOLDER,
    _escape_q,
    apply_share,
    ensure_folder_path,
    ensure_subfolder,
    get_file_parents,
    move_to_folder,
    trash_file,
    with_retry,
)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_drive_utils.py -k trash_file -v`
Expected: FAIL（`ImportError: cannot import name 'trash_file'`）

- [ ] **Step 3: Implement `trash_file`**

`src/tamatex/drive_utils.py` の末尾に追加:

```python
def trash_file(service, file_id: str) -> None:
    """ファイルを Drive のゴミ箱へ移動する（完全削除しない・30日復元可）。

    既に存在しない (404) 場合は目的達成とみなし握りつぶす。
    それ以外の HttpError / 例外はそのまま送出する。
    """
    try:
        with_retry(
            lambda: service.files().update(
                fileId=file_id,
                body={"trashed": True},
                fields="id,trashed",
                supportsAllDrives=True,
            ).execute(),
            op_name=f"files.update(trash:{file_id})",
        )
        logger.info("Driveゴミ箱へ移動: %s", file_id)
    except HttpError as e:
        raw = getattr(e.resp, "status", None) if getattr(e, "resp", None) else None
        try:
            status = int(raw) if raw is not None else None
        except (TypeError, ValueError):
            status = None
        if status == 404:
            logger.info("ゴミ箱移動: 対象は既に存在しない (404, 無視): %s", file_id)
            return
        raise
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_drive_utils.py -k trash_file -v`
Expected: PASS（3件）

- [ ] **Step 5: Commit**

```bash
git add src/tamatex/drive_utils.py tests/test_drive_utils.py
git commit -m "feat: drive_utils.trash_file 追加（ゴミ箱移動・404握りつぶし）"
```

---

### Task 2: `watcher.ChangeResult` に `stored_total` 追加

**Files:**
- Modify: `src/tamatex/watcher.py`（`ChangeResult` dataclass と `detect_changes` の return）
- Test: `tests/test_watcher.py`（末尾に追加）

**Interfaces:**
- Produces: `ChangeResult.stored_total: int`（前サイクルでのDB登録総数。デフォルト 0）。`detect_changes` が `len(stored_states)` を設定して返す。

- [ ] **Step 1: Write the failing test**

`tests/test_watcher.py` 末尾に追加:

```python
def test_detect_changes_reports_stored_total(db):
    """ChangeResult.stored_total が DB 登録総数を反映すること。"""
    db.update_state("/nas/a.xlsx", 1.0, "h1", "s1")
    db.update_state("/nas/b.xlsx", 1.0, "h2", "s2")

    current_files = [
        FileInfo("/nas/a.xlsx", 1.0, "h1"),
        FileInfo("/nas/c.xlsx", 1.0, "h3"),
    ]
    result = detect_changes(current_files, db)

    assert result.stored_total == 2


def test_detect_changes_stored_total_zero_for_empty_db(db):
    """空DBなら stored_total は 0。"""
    result = detect_changes([FileInfo("/nas/x.xlsx", 1.0, "h")], db)
    assert result.stored_total == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_watcher.py -k stored_total -v`
Expected: FAIL（`AttributeError: 'ChangeResult' object has no attribute 'stored_total'`）

- [ ] **Step 3: Implement**

`src/tamatex/watcher.py` の `ChangeResult` を変更:

```python
@dataclass
class ChangeResult:
    new_files: list[FileInfo]
    modified_files: list[FileInfo]
    deleted_paths: list[str]
    stored_total: int = 0
```

`detect_changes` の return を変更:

```python
    return ChangeResult(
        new_files=new_files,
        modified_files=modified_files,
        deleted_paths=deleted_paths,
        stored_total=len(stored_states),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_watcher.py -v`
Expected: PASS（既存 + 新規2件すべて）

- [ ] **Step 5: Commit**

```bash
git add src/tamatex/watcher.py tests/test_watcher.py
git commit -m "feat: ChangeResult に stored_total（DB登録総数）を追加"
```

---

### Task 3: `main._is_mass_deletion`（一括消失ガード・純関数）

**Files:**
- Modify: `src/tamatex/main.py`（定数 + 関数追加）
- Test: `tests/test_main_delete_propagation.py`（新規作成）

**Interfaces:**
- Produces: `_is_mass_deletion(deleted_count: int, stored_total: int) -> bool`、定数 `MASS_DELETE_MIN=5`, `MASS_DELETE_RATIO=0.4`

- [ ] **Step 1: Write the failing tests**

`tests/test_main_delete_propagation.py` を新規作成:

```python
"""main.py の削除伝播・一括消失ガードのテスト。"""

from unittest.mock import MagicMock, patch

import pytest

from tamatex.config import (
    AppConfig, NasConfig, GoogleConfig, SyncConfig, LogConfig,
)
from tamatex.main import sync_cycle, _is_mass_deletion
from tamatex.watcher import ChangeResult, FileInfo


# ---------------------------------------------------------------------------
# _is_mass_deletion
# ---------------------------------------------------------------------------

def test_is_mass_deletion_below_min_is_false():
    """MASS_DELETE_MIN 未満は常に通す。"""
    assert _is_mass_deletion(4, 100) is False


def test_is_mass_deletion_blocks_above_ratio():
    """登録60件で25件削除（25 > 24）はブロック。"""
    assert _is_mass_deletion(25, 60) is True


def test_is_mass_deletion_allows_at_boundary():
    """登録60件で24件削除（24 > 24 == False）は通す。"""
    assert _is_mass_deletion(24, 60) is False


def test_is_mass_deletion_zero_total_is_false():
    """登録総数0なら割合計算せず通す（初回など）。"""
    assert _is_mass_deletion(10, 0) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_main_delete_propagation.py -k is_mass_deletion -v`
Expected: FAIL（`ImportError: cannot import name '_is_mass_deletion'`）

- [ ] **Step 3: Implement**

`src/tamatex/main.py` の import 群の直後（`logger = ...` の後あたり）に定数と関数を追加:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_main_delete_propagation.py -k is_mass_deletion -v`
Expected: PASS（4件）

- [ ] **Step 5: Commit**

```bash
git add src/tamatex/main.py tests/test_main_delete_propagation.py
git commit -m "feat: 一括消失ガード _is_mass_deletion 追加"
```

---

### Task 4: `main.sync_cycle` 削除伝播統合＋早期return撤去

**Files:**
- Modify: `src/tamatex/main.py`（import に `trash_file` 追加、`files_to_sync` 空時の早期return撤去、ステップ4書き換え）
- Test: `tests/test_main_delete_propagation.py`（末尾に追加）

**Interfaces:**
- Consumes: `trash_file`（Task 1）, `ChangeResult.stored_total`（Task 2）, `_is_mass_deletion`（Task 3）
- Produces: `sync_cycle` が削除時に Sheets/PDF を trash し state 行を削除する挙動（一括ガード発動時はスキップ、`files_to_sync` 空でも削除は実行）

- [ ] **Step 1: Write the failing tests**

`tests/test_main_delete_propagation.py` 末尾に追加:

```python
# ---------------------------------------------------------------------------
# sync_cycle 削除伝播
# ---------------------------------------------------------------------------

@pytest.fixture()
def cfg(tmp_path):
    return AppConfig(
        nas=NasConfig(
            base_path=str(tmp_path / "nas"),
            file_patterns=["*.xlsx"],
            exclude_patterns=["~$*"],
        ),
        google=GoogleConfig(
            credentials_path=str(tmp_path / "c.json"),
            drive_folder_id="root",
            share_with=[],
        ),
        sync=SyncConfig(),
        logging=LogConfig(),
    )


def _state(sheet, pdf):
    s = MagicMock()
    s.spreadsheet_id = sheet
    s.pdf_file_id = pdf
    return s


def test_sync_cycle_trashes_sheet_and_pdf_on_deletion(cfg):
    """削除されたファイルの Sheets と PDF が両方 trash され state 行が消える。"""
    svc = MagicMock()
    state_db = MagicMock()
    state_db.get_state.side_effect = lambda p: {
        "/nas/keep.xlsx": _state("sheet-keep", "pdf-keep"),
        "/nas/gone.xlsx": _state("sheet-del", "pdf-del"),
    }.get(p)
    fake = ChangeResult([], [], ["/nas/gone.xlsx"], stored_total=10)

    with patch("tamatex.main.scan_files",
               return_value=[FileInfo("/nas/keep.xlsx", 1.0, "h")]), \
         patch("tamatex.main.detect_changes", return_value=fake), \
         patch("tamatex.main.trash_file") as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root")

    mock_trash.assert_any_call(svc, "sheet-del")
    mock_trash.assert_any_call(svc, "pdf-del")
    state_db.remove_state.assert_called_once_with("/nas/gone.xlsx")


def test_sync_cycle_trashes_only_sheet_when_no_pdf(cfg):
    """pdf_file_id が空なら Sheets のみ trash。"""
    svc = MagicMock()
    state_db = MagicMock()
    state_db.get_state.side_effect = lambda p: {
        "/nas/keep.xlsx": _state("sheet-keep", "pdf-keep"),
        "/nas/gone.xlsx": _state("sheet-del", ""),
    }.get(p)
    fake = ChangeResult([], [], ["/nas/gone.xlsx"], stored_total=10)

    with patch("tamatex.main.scan_files",
               return_value=[FileInfo("/nas/keep.xlsx", 1.0, "h")]), \
         patch("tamatex.main.detect_changes", return_value=fake), \
         patch("tamatex.main.trash_file") as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root")

    mock_trash.assert_called_once_with(svc, "sheet-del")


def test_sync_cycle_skips_deletion_when_mass_guard_trips(cfg):
    """25件/60件の削除は一括ガード発動で trash も remove も呼ばれない。"""
    svc = MagicMock()
    state_db = MagicMock()
    state_db.get_state.side_effect = lambda p: _state("s", "p")
    deleted = [f"/nas/del{i}.xlsx" for i in range(25)]
    fake = ChangeResult([], [], deleted, stored_total=60)

    with patch("tamatex.main.scan_files",
               return_value=[FileInfo("/nas/keep.xlsx", 1.0, "h")]), \
         patch("tamatex.main.detect_changes", return_value=fake), \
         patch("tamatex.main.trash_file") as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root")

    mock_trash.assert_not_called()
    state_db.remove_state.assert_not_called()


def test_sync_cycle_propagates_deletion_at_guard_boundary(cfg):
    """24件/60件は非発動 → 24件すべて trash（Sheets+PDF=48）＋remove 24回。"""
    svc = MagicMock()
    state_db = MagicMock()
    state_db.get_state.side_effect = lambda p: _state(f"sheet-{p}", f"pdf-{p}")
    deleted = [f"/nas/del{i}.xlsx" for i in range(24)]
    fake = ChangeResult([], [], deleted, stored_total=60)

    with patch("tamatex.main.scan_files",
               return_value=[FileInfo("/nas/keep.xlsx", 1.0, "h")]), \
         patch("tamatex.main.detect_changes", return_value=fake), \
         patch("tamatex.main.trash_file") as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root")

    assert state_db.remove_state.call_count == 24
    assert mock_trash.call_count == 48


def test_sync_cycle_skips_everything_when_nas_disconnected(cfg):
    """scan_files が空（NAS全切断）なら削除処理に到達しない。"""
    svc = MagicMock()
    state_db = MagicMock()

    with patch("tamatex.main.scan_files", return_value=[]), \
         patch("tamatex.main.trash_file") as mock_trash:
        sync_cycle(cfg, state_db, svc, "sheets-root", "pdf-root")

    mock_trash.assert_not_called()
    state_db.remove_state.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_main_delete_propagation.py -k sync_cycle -v`
Expected: FAIL（現状は Drive保持のため trash 未呼出 / 早期returnで削除未処理）

- [ ] **Step 3: Implement**

(3a) `src/tamatex/main.py` の `from tamatex.drive_utils import (...)` に `trash_file` を追加:

```python
from tamatex.drive_utils import (
    build_drive_service,
    ensure_folder_path,
    apply_share,
    trash_file,
)
```

(3b) `files_to_sync` 空時の早期return（現状 main.py の "変更なし — スキップ" ブロック）を撤去し、削除処理まで通過させる。該当ブロックを置換:

```python
    if not files_to_sync:
        logger.info("変更なし（新規/更新なし）— 削除検知のみ評価")
        stats["skipped"] = stats["scanned"]
    else:
        stats["skipped"] = stats["scanned"] - len(files_to_sync)
```

（`return stats` を消す。`files_to_sync` 空なら次の同期ループは自然に no-op で通過し、ステップ4へ到達する。）

(3c) ステップ4（現状の "NAS上から削除されたファイル — Drive側は保持" のループ）を置換:

```python
    # 4. NAS削除のDrive追従（一括消失ガード付き）
    deleted = changes.deleted_paths
    if deleted:
        if _is_mass_deletion(len(deleted), changes.stored_total):
            logger.warning(
                "一括消失ガード発動: 削除候補=%d件 / 登録総数=%d件。"
                "NAS部分障害の可能性があるため今サイクルの削除をスキップします。",
                len(deleted), changes.stored_total,
            )
        else:
            for deleted_path in deleted:
                try:
                    state = state_db.get_state(deleted_path)
                    if state:
                        if state.spreadsheet_id:
                            trash_file(service, state.spreadsheet_id)
                        if state.pdf_file_id:
                            trash_file(service, state.pdf_file_id)
                    state_db.remove_state(deleted_path)
                    logger.info("NAS削除を追従（Driveゴミ箱へ移動）: %s", deleted_path)
                except Exception as e:
                    logger.error("削除追従エラー（スキップ）: %s - %s", deleted_path, e)
                    stats["errors"] += 1
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `python -m pytest tests/ -v`
Expected: PASS（既存214件 + 新規すべて。回帰なし）

- [ ] **Step 5: Commit**

```bash
git add src/tamatex/main.py tests/test_main_delete_propagation.py
git commit -m "feat: NAS削除のDrive追従（trash+一括ガード）と早期return撤去"
```

---

## Phase 1 完了チェックポイント

- [ ] `python -m pytest tests/ -v` 全PASS。
- [ ] **Codex `adversarial-review`** に「削除伝播の安全性・ガード境界・NAS部分障害時の挙動・早期return撤去の副作用」を見てもらう（ユーザー承認済み）。
- [ ] 指摘反映後、現場PCへデプロイ（`.py.bak_<日時>` バックアップ → 差し替え → `nssm restart tamatex` → 1サイクルのログで削除伝播動作確認）。
- [ ] `CLAUDE.md` の作業状態を更新。

---

### Task 5: `scripts/cleanup_orphans.py`（Phase 2・Phase 1 デプロイ後に実施）

**Files:**
- Create: `scripts/cleanup_orphans.py`
- Test: 手動ドライラン（孤立一覧表示）→ 目視確認 → `--apply`

**Interfaces:**
- Consumes: `build_drive_service`, `trash_file`（drive_utils）, `StateDB`, `load_config`
- Produces: CLI スクリプト。既定はドライラン（孤立ファイル一覧表示のみ）、`--apply` で trash。

- [ ] **Step 1: スクリプト作成**

`scripts/cleanup_orphans.py` を新規作成:

```python
"""Drive 上の孤立ファイル（state DB に無い Sheets/PDF）を棚卸しして掃除する。

削除伝播導入前に蓄積した重複（旧名スプレッド等）を一掃するための一回限りツール。
既定はドライラン（一覧表示のみ）。--apply 指定時のみゴミ箱へ移動する。

使い方:
    python scripts/cleanup_orphans.py -c ./config/config.yaml          # 一覧のみ
    python scripts/cleanup_orphans.py -c ./config/config.yaml --apply  # 実行
"""

import argparse

from tamatex.config import load_config
from tamatex.drive_utils import (
    MIME_FOLDER,
    build_drive_service,
    trash_file,
    with_retry,
)
from tamatex.state import StateDB

MIME_SHEETS = "application/vnd.google-apps.spreadsheet"
MIME_PDF = "application/pdf"


def _list_children(service, folder_id):
    """フォルダ直下の (id, name, mimeType) を全件返す（ページング対応）。"""
    items = []
    page_token = None
    while True:
        res = with_retry(
            lambda: service.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, mimeType)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                pageSize=200,
                pageToken=page_token,
            ).execute(),
            op_name="files.list(cleanup)",
        )
        items.extend(res.get("files", []))
        page_token = res.get("nextPageToken")
        if not page_token:
            break
    return items


def _walk(service, root_id):
    """root_id 配下を再帰的に走査し、フォルダ以外の (id, name, mimeType) を返す。"""
    found = []
    stack = [root_id]
    while stack:
        fid = stack.pop()
        for child in _list_children(service, fid):
            if child["mimeType"] == MIME_FOLDER:
                stack.append(child["id"])
            else:
                found.append(child)
    return found


def main():
    parser = argparse.ArgumentParser(description="Drive孤立ファイル掃除")
    parser.add_argument("-c", "--config", required=True, help="config.yaml パス")
    parser.add_argument("--apply", action="store_true", help="実際にゴミ箱へ移動する")
    args = parser.parse_args()

    config = load_config(args.config)
    service = build_drive_service(config.google.credentials_path)

    db_path = config.sync.state_db_path or "./tamatex_state.db"
    state_db = StateDB(db_path=db_path)
    try:
        known = set()
        for s in state_db.get_all_states():
            if s.spreadsheet_id:
                known.add(s.spreadsheet_id)
            if s.pdf_file_id:
                known.add(s.pdf_file_id)
    finally:
        state_db.close()

    all_files = _walk(service, config.google.drive_folder_id)
    targets = [
        f for f in all_files
        if f["mimeType"] in (MIME_SHEETS, MIME_PDF) and f["id"] not in known
    ]

    print(f"=== Drive走査: {len(all_files)}件 / 孤立候補: {len(targets)}件 ===")
    for f in targets:
        kind = "Sheets" if f["mimeType"] == MIME_SHEETS else "PDF"
        print(f"  [孤立/{kind}] {f['name']}  ({f['id']})")

    if not args.apply:
        print("\n(ドライラン: --apply 指定で上記をゴミ箱へ移動します)")
        return

    print("\n=== ゴミ箱へ移動中 ===")
    for f in targets:
        trash_file(service, f["id"])
    print(f"完了: {len(targets)}件をゴミ箱へ移動しました（30日復元可）。")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: ドライラン実行（孤立一覧の目視確認）**

Run（現場 or 認証可能な環境で）: `python scripts/cleanup_orphans.py -c ./config/config.yaml`
Expected: 孤立候補（旧名スプレッド等）が一覧表示される。件数と名前を目視確認。

- [ ] **Step 3: 確認後に実行**

Run: `python scripts/cleanup_orphans.py -c ./config/config.yaml --apply`
Expected: 孤立ファイルがゴミ箱へ移動（30日復元可）。

- [ ] **Step 4: Commit**

```bash
git add scripts/cleanup_orphans.py
git commit -m "feat: 孤立Driveファイル掃除スクリプト cleanup_orphans.py"
```

---

## Self-Review（記入済み）

- **Spec coverage**: 設計の trash_file(§1)=Task1、ChangeResult.stored_total(§2)=Task2、_is_mass_deletion(§4)=Task3、sync_cycle書き換え+早期return撤去(§3/§3.5)=Task4、既存ガード維持(§5)=Task4で言及、cleanup(§6)=Task5。全要件にタスク対応あり。
- **Placeholder scan**: TBD/TODO/曖昧記述なし。全ステップに実コード・実コマンド・期待値あり。
- **Type consistency**: `trash_file(service, file_id)` / `_is_mass_deletion(deleted_count, stored_total)` / `ChangeResult.stored_total` のシグネチャは Task 間で一致。`sync_cycle(config, state_db, service, sheets_folder_id, pdf_folder_id, ...)` の引数順は既存実装に準拠。
