# NAS削除のDrive追従（削除伝播）設計

- **日付**: 2026-06-24
- **ステータス**: 設計合意済み（実装前）
- **対象**: `src/tamatex/`（watcher / main / drive_utils）＋ `scripts/cleanup_orphans.py`（新規）
- **関連**: セッション11。現場報告「ファイル名変更で旧スプレッドが残り新名も並ぶ／削除しても残る」への対応。

## 背景・問題

tamatex はファイルの同一性を **NAS上の絶対パス**（`state.py` の PK = `file_path`）だけで判定する。
内容ハッシュは「同一パスのファイルの**更新**検知」にのみ使い、同一性判定には使わない。
結果、現状は以下が起きる（コード・現場ログで実証済み）:

| NAS側の操作 | 最新版の反映 | 旧版の扱い | 原因 |
|---|---|---|---|
| リネーム（±中身更新） | ✅ 新名で反映 | ❌ 旧名が残る | 新パス=新規作成、旧パス=削除扱いだが Drive保持 |
| 単純削除 | — | ❌ Drive側に残存 | `sync_cycle` ステップ4 が「state行のみ削除、Drive保持」 |

`main.py` `sync_cycle` ステップ4 の現状コメント:「NAS上から削除検知（Drive上のSheets/PDFは保持）」。
これは誤検知・NAS一時切断による巻き込み削除を避ける**意図的な安全側設計**だが、顧客運用（リネーム・整理）では Drive にゴミが蓄積する。
2026-06-12 のログで「新規1件＋削除1件＋NAS削除を検知（Drive保持）」が4サイクル連続 = 現に重複が蓄積中。

## スコープ

### やること
- NASから消えたExcelに対応する Drive 上の **Sheets と PDF を両方ゴミ箱へ移動**（完全削除はしない＝30日復元可能）。
- **一括消失ガード**で、NAS部分マウント失敗時の大量誤削除をブロック。
- 既にDriveに溜まった重複（孤立ファイル）を掃除する**一回限りスクリプト**。

### やらないこと（YAGNI）
- **リネーム検知**（内容ハッシュ照合・複数同時リネームのマッチング・フォルダ間移動の追従）。
  - 理由: ①「名前変更＋中身更新」はハッシュが変わり検知不能。②削除伝播があれば「旧→ゴミ箱、新→新規作成」で重複は自然解消する。リネーム検知の唯一の価値は共有リンク（URL）維持だが、現状 `share_with` 未設定でブックマーク運用なし → 不要と判断。

## 設計詳細

### 1. `drive_utils.trash_file(service, file_id)` 新設
- `files.update(fileId, body={"trashed": True}, supportsAllDrives=True)` を `with_retry` でラップ。
- **404（既に存在しない）は「目的達成」とみなし握りつぶす**（ログは debug/info）。それ以外の HttpError は raise。
- 完全削除（`files.delete`）は使わない。

### 2. `watcher.ChangeResult` に `stored_total: int` を追加
- 一括ガードの分母（前サイクルでのDB登録総数）を `detect_changes` 内で算出して返す。
- `stored_total = len(stored_states)`（既に取得済みの `get_all_states()` の件数）。
- 既存フィールド（new_files / modified_files / deleted_paths）は不変。後方互換のため新フィールドはデフォルト無しの必須追加（呼び出し元は `sync_cycle` のみ）。

### 3. `main.sync_cycle` ステップ4 を書き換え

```
# 4. NAS削除のDrive追従（一括消失ガード付き）
deleted = changes.deleted_paths
if deleted:
    if _is_mass_deletion(len(deleted), changes.stored_total):
        logger.warning(
            "一括消失ガード発動: 削除候補=%d件 / 登録総数=%d件 が閾値超過。"
            "NAS部分障害の可能性があるため今サイクルの削除をスキップ。",
            len(deleted), changes.stored_total,
        )
        # state は触らない → 次サイクルで再評価
    else:
        for deleted_path in deleted:
            state = state_db.get_state(deleted_path)
            if state:
                if state.spreadsheet_id:
                    trash_file(service, state.spreadsheet_id)
                if state.pdf_file_id:
                    trash_file(service, state.pdf_file_id)
            state_db.remove_state(deleted_path)
            logger.info("NAS削除を追従（Driveゴミ箱へ移動）: %s", deleted_path)
```

- trash 失敗（404以外の致命例外）は1ファイル単位で try/except し、警告ログ＋当該ファイルはスキップ（他の削除は継続、`stats["errors"]` 加算）。state行は trash 成功時のみ削除（失敗時は次サイクル再試行）。

### 3.5 早期returnの撤去（潜在バグ修正・必須）
現状 `sync_cycle` は `files_to_sync` が空だと**ステップ4の前で `return`** する（main.py:181-184）。
このため「新規/更新が無く削除だけのサイクル」では削除処理が一切走らない（現状でも state 行が残る潜在バグ）。
**修正**: 早期 `return` を撤去し、`files_to_sync` が空でも同期ループを no-op で通過してステップ4（削除伝播）まで到達させる。NAS全切断ガード（`if not current_files: return`）は手前に残すので、NAS切断時は従来通りステップ4へ進まない。

### 4. 一括消失ガード `_is_mass_deletion`

```
MASS_DELETE_MIN = 5       # これ未満の削除は常に通す（小規模整理を妨げない）
MASS_DELETE_RATIO = 0.4   # 登録総数のこの割合を超える削除はブロック

def _is_mass_deletion(deleted_count: int, stored_total: int) -> bool:
    if deleted_count < MASS_DELETE_MIN:
        return False
    if stored_total <= 0:
        return False
    return deleted_count > stored_total * MASS_DELETE_RATIO
```

- 現場約60件登録 → 閾値は `60 × 0.4 = 24`。条件は `削除数 > 24` なので **25件以上の一括消失でブロック、24件以下は通る**。通常整理（1〜3件）は通る。
- 定数は `main.py` に置く（将来 config 化は YAGNI で見送り、必要時に SyncConfig へ昇格）。

### 5. 既存ガードは維持（二重防御）
- `scan_files` が空 → `sync_cycle` 冒頭で `return`（NAS全切断）。
- `detect_changes` の「current空＆stored非空なら削除検知スキップ」も維持。

### 6. 既存ゴミ掃除スクリプト `scripts/cleanup_orphans.py`（本体実装・デプロイ後に実施）
- `build_drive_service` で認証、`config.yaml` から Sheets/PDF ルートフォルダIDを取得。
- Drive 上のフォルダを再帰列挙し、`mimeType=spreadsheet`（名前 `[同期] *`）と `application/pdf` を収集。
- `state` DB の全 `spreadsheet_id` / `pdf_file_id` 集合と突合 → **DBに無い孤立ファイルを一覧表示（ドライラン既定）**。
- `--apply` 指定時のみ孤立ファイルを `trash_file` でゴミ箱へ。
- 安全のため「一覧 → 目視確認 → `--apply`」の2段運用。`with_retry` 利用。git操作・本体改変はしない。

## テスト計画（TDD）

`tests/test_drive_utils.py`:
- `trash_file` 正常系（trashed=True で update 呼出）。
- `trash_file` の 404 は握りつぶす / その他 HttpError は raise。

`tests/test_watcher.py`:
- `detect_changes` が `stored_total` を正しく返す（new/modified/deleted との整合）。

`tests/test_main_*.py`（新規 `test_main_delete_propagation.py`）:
- 削除1件 → Sheets+PDF 両方 trash＋state行削除。
- `pdf_file_id` 空 → Sheets のみ trash、PDF はスキップ。
- 一括ガード**発動**境界（stored_total=60 で 25件→発動 / 24件→非発動）→ 発動時は trash も remove も呼ばれない。
- 一括ガード**非発動**（小規模 < MASS_DELETE_MIN）→ そのまま削除。
- trash 個別失敗（404以外）→ 他ファイルの削除は継続、state行は残る。
- NAS全切断（current空）→ 既存ガードで削除スキップ（回帰）。

## リスクと対策

| リスク | 対策 |
|---|---|
| NAS部分マウント失敗で大量誤削除 | 一括消失ガード＋ゴミ箱止まり（復元可能） |
| 意図的削除が一括ガードに引っかかり反映されない | ゴミ箱送りは即日反映、ガード発動は警告ログで可視化。閾値（60件中25件以上）は通常運用で踏まない |
| trash 後に「やはり必要だった」 | 30日間 Drive ゴミ箱から復元可能 |
| 高リスク変更（データ消失系） | 実装一段落後に Codex `adversarial-review` を進言（別モデル独立検証） |

## 実装順序（推薦順）

1. **Phase 1: 削除伝播本体** — `trash_file` → `ChangeResult.stored_total` → `_is_mass_deletion` → `sync_cycle` 書き換え → テスト緑 → 現場デプロイ。
2. **Phase 2: 既存ゴミ掃除** — `cleanup_orphans.py` 作成 → ドライランで孤立一覧確認 → `--apply` で trash。
