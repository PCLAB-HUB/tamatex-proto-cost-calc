# Phase 1: CRITICAL/HIGH修正 実装計画

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** デプロイ前必須のCRITICAL 2件 + HIGH 4件を修正し、既存107テスト全パス + デーモン起動テストを通す

**Architecture:** 各モジュールを個別に修正し、修正ごとにテスト実行。依存関係のある修正は順序を守る（state.py → config.py → main.py → sheets_sync.py → watcher.py）

**Tech Stack:** Python 3.11+, pytest, gspread 6.x, sqlite3, threading

---

## Task 1: C-2 — StateDB コネクションリーク修正

**Files:**
- Modify: `src/tamatex/state.py`
- Test: `tests/test_state.py`

### 変更内容
- `_connect()` を毎回新規作成から単一コネクション保持に変更
- `close()` メソッド追加
- コンテキストマネージャ（`__enter__`/`__exit__`）実装

### 修正コード（state.py）

```python
class StateDB:
    def __init__(self, db_path: str | Path = "./tamatex_state.db"):
        self._db_path = str(db_path)
        self._conn: sqlite3.Connection = sqlite3.connect(self._db_path)
        self._init_db()

    def _init_db(self) -> None:
        with self._conn:
            self._conn.execute("""...""")

    def close(self) -> None:
        if self._conn:
            self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # 各メソッドで self._conn を直接使用（self._connect()廃止）
```

### テスト影響
- 既存16件のテストがStateDBの内部接続方式に依存している可能性あり
- `db` フィクスチャは `StateDB(db_path=tmp_path / "test_state.db")` で変更なし
- close() と __enter__/__exit__ のテスト追加

---

## Task 2: F-04 — SQLiteパスの絶対パス化

**Files:**
- Modify: `src/tamatex/config.py` — SyncConfig に `state_db_path` 追加
- Modify: `src/tamatex/main.py` — config から db_path を取得
- Modify: `config/config.example.yaml` — state_db_path のコメント追加
- Test: `tests/test_config.py`

### 変更内容
- `SyncConfig` に `state_db_path: str = ""` 追加
- `main.py` の `run()` で config_path の親ディレクトリからの相対パスとして解決
- 空文字の場合は config ファイルと同じディレクトリに `tamatex_state.db` を作成

---

## Task 3: C-1 — Google API認証トークン自動更新

**Files:**
- Modify: `src/tamatex/sheets_sync.py` — `authenticate()` を `gspread.service_account()` に変更

### 変更内容（1行修正）
```python
def authenticate(credentials_path: str) -> gspread.Client:
    client = gspread.service_account(filename=credentials_path)
    logger.info("Google API認証成功")
    return client
```

### 削除するインポート
- `from google.oauth2.service_account import Credentials`
- SCOPES 定数（gspread.service_account が内部で設定）

---

## Task 4: F-01 — サービスアカウントキーのパーミッション設定

**Files:**
- Modify: `src/tamatex/sheets_sync.py` — authenticate() に起動時パーミッション警告追加

### 変更内容
- authenticate() の先頭でファイル存在チェック + Unix系でのパーミッション警告

---

## Task 5: F-03 — シンボリックリンク追跡の制限

**Files:**
- Modify: `src/tamatex/watcher.py` — resolve()後にbase_path配下チェック
- Test: `tests/test_watcher.py`

### 変更内容
```python
resolved = file_path.resolve()
base_resolved = base.resolve()
try:
    resolved.relative_to(base_resolved)
except ValueError:
    logger.warning("base_path外のファイル（スキップ）: %s -> %s", file_path, resolved)
    continue
```

---

## Task 6: OH-5 — Windowsサービス停止シグナル対応

**Files:**
- Modify: `src/tamatex/main.py` — atexit + Windows ConsoleCtrlHandler

### 変更内容
- `atexit.register` で StateDB.close() を保証
- Windows環境では `signal.CTRL_C_EVENT` / `signal.CTRL_BREAK_EVENT` にも対応

---

## Task 7: 全テスト実行 + デーモン起動テスト

1. `python -m pytest tests/ -v` — 107件全パス確認
2. テスト用config作成 → `python -m tamatex.main -c test_config.yaml` 起動 → SIGINT で正常終了確認

---

## 実行順序

Task 1 (state.py) → Task 2 (config.py + main.py) → Task 3 (sheets_sync.py) → Task 4 (sheets_sync.py) → Task 5 (watcher.py) → Task 6 (main.py) → Task 7 (E2E)

各タスク完了後に `pytest tests/ -v` で全テストパスを確認する。
