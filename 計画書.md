# Task Plan: QNAP NAS Excel → Google Spreadsheet 自動同期システム (tamatex)

## Goal
QNAP NAS上のExcelファイル（10〜20個）を15分間隔で監視し、変更検知時にGoogle Spreadsheetへ自動反映するPythonスクリプトを構築する。事務員のExcel運用は一切変更せず、営業・役員が外出先からスプレッドシートで閲覧可能にする。

## Current Phase
Phase 1

## システム概要図

```
[QNAP NAS]                [常時稼働PC]                    [Google Cloud]
 ┌─────────┐   SMB/CIFS    ┌──────────────────┐   API      ┌─────────────────┐
 │ Excel    │◄─────────────►│ tamatex          │──────────►│ Google Sheets   │
 │ ファイル  │  (ネットワーク  │ ├─ watcher       │           │ (営業・役員閲覧) │
 │ 10-20個  │   ドライブ)    │ ├─ excel_reader  │           │                 │
 │          │               │ ├─ sheets_sync   │           │ Google Drive    │
 └─────────┘               │ ├─ state (SQLite)│           │ (同期フォルダ)   │
      ▲                    │ └─ scheduler     │           └─────────────────┘
      │                    └──────────────────┘
  事務員が編集                 15分ごとにポーリング
```

## Phases

### Phase 1: プロジェクト基盤構築
- [ ] プロジェクトディレクトリ構造の作成
- [ ] pyproject.toml / requirements.txt 作成
- [ ] .gitignore 作成（シークレット除外）
- [ ] config.example.yaml テンプレート作成
- [ ] git init & 初回コミット
- **Status:** pending

### Phase 2: 設定管理 & 状態管理モジュール
- [ ] config.py — Pydanticモデルによる設定読み込み・バリデーション
- [ ] state.py — SQLiteによる同期状態管理（ファイルハッシュ、最終同期日時等）
- [ ] logger.py — 構造化ログ設定（ファイル出力 + ローテーション）
- [ ] ユニットテスト作成
- **Status:** pending

### Phase 3: ファイル監視モジュール
- [ ] watcher.py — NASフォルダのポーリング監視
- [ ] ファイル変更検知（mtime + MD5ハッシュ比較）
- [ ] テンポラリファイル除外（~$*, *.tmp, .~lock*）
- [ ] 新規ファイル / 更新ファイル / 削除ファイルの分類
- [ ] NAS接続断のグレースフル処理
- [ ] ユニットテスト作成
- **Status:** pending

### Phase 4: Excel読み取りモジュール
- [ ] excel_reader.py — openpyxlによるExcelデータ抽出
- [ ] 複数シート対応
- [ ] マージセル対応（値展開）
- [ ] データ型変換（日付、数値、文字列、空セル）
- [ ] 日本語ファイル名・セル内容のUTF-8処理
- [ ] 読み取り専用モード（ファイルロック回避）
- [ ] ユニットテスト作成
- **Status:** pending

### Phase 5: Google Sheets同期モジュール
- [ ] sheets_sync.py — Google Sheets API連携
- [ ] サービスアカウント認証
- [ ] スプレッドシート新規作成（初回同期時）
- [ ] 既存スプレッドシートへのデータ上書き更新（URL固定化）
- [ ] シート名の同期（Excel側のシート構成変更に追従）
- [ ] バッチ更新（API呼び出し最適化）
- [ ] Google Driveフォルダへの整理
- [ ] 共有設定（営業・役員への自動共有）
- [ ] APIレート制限対応
- [ ] ユニットテスト作成
- **Status:** pending

### Phase 6: メインスケジューラ & 統合
- [ ] main.py — エントリーポイント
- [ ] APSchedulerによる15分間隔の定期実行
- [ ] 同期フロー統合（検知 → 読取 → 同期）
- [ ] エラーハンドリング統合（ファイル単位のスキップ & 継続）
- [ ] グレースフルシャットダウン（SIGTERM/SIGINT対応）
- [ ] ヘルスチェック（ハートビートファイル出力）
- [ ] 統合テスト作成
- **Status:** pending

### Phase 7: テスト & 品質保証
- [ ] 全ユニットテスト実行・通過確認
- [ ] 統合テスト（モックAPI使用）
- [ ] エッジケーステスト
  - [ ] NAS切断中の動作
  - [ ] ファイルロック中の動作
  - [ ] 空ファイル / 破損ファイル
  - [ ] 巨大ファイル（10,000行超）
  - [ ] 同時更新（複数ファイルが同時に変更）
- [ ] セキュリティチェック（シークレット漏洩なし）
- **Status:** pending

### Phase 8: デプロイメント & 運用準備
- [ ] Windowsサービス化スクリプト（NSSM利用）
- [ ] 初回セットアップスクリプト（スプレッドシート一括作成）
- [ ] 運用手順書（セットアップ・設定変更・トラブルシュート）
- [ ] 顧客向け導入マニュアル
- **Status:** pending

## Key Questions

1. NASのマウントパスは？（例: `Z:\共有\Excel` or `\\192.168.x.x\shared`）→ **未確認**
2. Excelファイルの形式は .xlsx のみか、.xls も含むか？→ **未確認（.xlsx前提で進める）**
3. 常時稼働PCのOSは Windows か？→ **未確認（Windows前提で進める）**
4. 閲覧者のGoogleアカウントのドメインは？→ **未確認**
5. Excelにマクロ（VBA）は使われているか？→ **未確認（データ中心のため無い前提）**
6. スプレッドシートの閲覧権限は全員同一か、ファイルごとに異なるか？→ **未確認**

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| ポーリング方式（watchdog不使用） | SMB/CIFSネットワークドライブではファイルシステムイベントが信頼できない。15分間隔ポーリングが最も安定 |
| openpyxl使用 | .xlsx読み取りのデファクトスタンダード。data_only=Trueで計算結果値を取得可能 |
| gspread使用 | Google Sheets APIの高水準ラッパー。google-api-python-clientより簡潔 |
| サービスアカウント認証 | OAuth同意フロー不要。サーバー常駐型に最適。ドメイン全体委任も可能 |
| SQLite状態管理 | 外部DB不要。ACID準拠。ファイル1つで完結。10-20ファイル程度の管理に十分 |
| クリア＆全書き込み方式 | 差分更新より単純で確実。データ中心のためセル書式保持不要。API呼び出し回数も許容範囲 |
| Pydantic設定管理 | バリデーション自動化。型安全。設定ミスを起動時に検出 |
| APScheduler使用 | Pythonネイティブのジョブスケジューラ。cron不要。ミスファイア処理あり |
| NSSM (Windows Service) | Pythonスクリプトを簡単にWindowsサービス化。自動再起動・ログ統合 |
| MD5 + mtime二重検知 | mtimeだけではNAS環境で不正確な場合がある。ハッシュ併用で変更見逃しを防止 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| (未発生) | - | - |

## Notes
- 同期は **一方向**（NAS → Spreadsheet）。スプレッドシート側の編集は想定しない
- スプレッドシートのURLは固定（営業がブックマーク可能）
- 1ファイルの処理に5-10秒として、20ファイルでも最大200秒（3分強）。15分間隔に十分収まる
- Google Sheets API制限: 300 req/min/project, 60 req/min/user — 20ファイルなら余裕
- 日本語ファイル名を正しく扱うためUTF-8を徹底
