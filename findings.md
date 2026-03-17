# Findings & Decisions

## Requirements

### 機能要件
- QNAP NAS上のExcelファイル（10〜20個）を15分間隔で自動同期
- 変更があったファイルのみGoogle Spreadsheetへ反映
- 事務員のExcel運用は変更しない（NAS上のExcelを直接編集・保存）
- 営業・役員・社長が外出先からスプレッドシートで閲覧可能
- スプレッドシートのURLは固定（ブックマーク可能）
- Excelの全シートをスプレッドシートに反映

### 非機能要件
- 常時稼働PC上でサービスとして自動実行
- PC再起動後に自動起動
- エラー発生時もサービスは停止せず、次の同期サイクルで再試行
- ログによる運用状態の可視化
- 15分以内の同期遅延（許容範囲）

### 前提条件
- Google Workspace契約済み
- 常時稼働PC有り（Windows想定）
- Excelファイルはデータ中心（マクロ・VBAなし想定）
- NASはQNAP（SMB/CIFSでアクセス可能）

## Research Findings

### openpyxl
- `load_workbook(path, read_only=True, data_only=True)` で読み取り専用 + 計算結果取得
- read_only=Trueでメモリ使用量を大幅削減（大きなファイル対策）
- マージセルは `merged_cells.ranges` で取得可能
- 日付セルは `datetime` オブジェクトとして読み取り可能
- .xlsは非対応（必要なら xlrd を追加）

### gspread
- `service_account(filename='key.json')` で認証
- `open_by_key(spreadsheet_id)` で既存スプレッドシート操作
- `worksheet.clear()` → `worksheet.update(values)` でクリア＆書き込み
- `batch_update()` で複数操作を1 API呼び出しに集約可能
- 自動的にリクエスト制限を考慮した待機を行う

### Google Sheets API 制限
- 読み取りリクエスト: 300/min/project
- 書き込みリクエスト: 300/min/project
- 1回の書き込み上限: 10,000,000セル
- スプレッドシートあたりシート上限: 200
- セル上限: 10,000,000セル/スプレッドシート

### QNAP NAS + SMB
- WindowsからはUNCパス `\\NAS_IP\share` またはドライブレター `Z:\` でアクセス
- SMBファイルロック: Excelオープン中は `~$ファイル名.xlsx` が作成される
- ネットワーク断時はOSError / PermissionError が発生
- mtime（最終更新日時）はSMB経由でも取得可能だが、NAS設定により精度が異なる場合あり

### Windowsサービス化
- **NSSM (Non-Sucking Service Manager)**: 推奨。任意のexe/scriptをサービス化
  - `nssm install tamatex python.exe path/to/main.py`
  - 自動再起動、ログ出力先設定、起動遅延設定が可能
- **pywin32**: Pythonネイティブだがセットアップが複雑
- **Task Scheduler**: 代替案。15分ごとに実行。ただし状態保持が別途必要

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Python 3.11+ | match文、改善されたエラーメッセージ、パフォーマンス向上 |
| openpyxl (read_only=True, data_only=True) | メモリ効率的な読み取り。数式は計算結果値で取得 |
| gspread >= 6.0 | Google Sheets高水準API。認証・バッチ操作が簡潔 |
| Pydantic v2 | YAML設定のバリデーション。起動時に設定ミスを即座に検出 |
| SQLite3 (標準ライブラリ) | 追加依存なし。同期状態の永続管理に十分 |
| APScheduler | 15分間隔のジョブ管理。ミスファイア処理、次回実行時刻管理 |
| NSSM | Windowsサービス化の最もシンプルな手段 |
| ログローテーション (10MB x 5) | ディスク圧迫を防止。50MBで十分な運用ログを保持 |

## プロジェクト構造

```
tamatex/
├── src/
│   └── tamatex/
│       ├── __init__.py           # バージョン情報
│       ├── main.py               # エントリーポイント、スケジューラ起動
│       ├── config.py             # Pydanticモデル、YAML読み込み
│       ├── watcher.py            # ファイル変更検知（ポーリング）
│       ├── excel_reader.py       # Excel → Pythonデータ変換
│       ├── sheets_sync.py        # Google Sheets API操作
│       ├── state.py              # SQLite状態管理
│       └── logger.py             # ログ設定
├── config/
│   ├── config.example.yaml       # 設定テンプレート（git管理）
│   └── .gitkeep
├── logs/
│   └── .gitkeep
├── scripts/
│   ├── install.bat               # 依存関係インストール
│   ├── setup_service.bat         # NSSMサービス登録
│   └── initial_setup.py          # 初回スプレッドシート一括作成
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # テストフィクスチャ
│   ├── test_config.py
│   ├── test_watcher.py
│   ├── test_excel_reader.py
│   ├── test_sheets_sync.py
│   └── test_state.py
├── pyproject.toml
├── requirements.txt
├── .gitignore
├── .env.example
└── README.md
```

## エッジケース一覧

| ケース | 対応方針 |
|--------|----------|
| Excel編集中（ファイルロック） | read_only=Trueで読み取り可能。~$ファイルは除外 |
| NAS接続断 | OSErrorをキャッチ、ログ出力、次サイクルで再試行 |
| 破損Excelファイル | 例外キャッチ、該当ファイルスキップ、他ファイルは継続 |
| 空のExcelファイル | 空のスプレッドシートシートとして同期 |
| 巨大ファイル（10,000行超） | read_only=Trueで対応。バッチ更新で分割送信 |
| 新規Excelファイル追加 | 自動検知 → スプレッドシート自動作成 → マッピング保存 |
| Excelファイル削除 | スプレッドシートは残す（データ保全）。ログ警告出力 |
| Excelファイル名変更 | 旧ファイル削除 + 新規ファイル追加として処理 |
| シート追加/削除/名前変更 | Excel側のシート構成に追従してスプレッドシートを更新 |
| マージセル | 左上セルの値を全範囲に展開 |
| 日本語ファイル名 | pathlib.Pathで統一処理。UTF-8エンコーディング徹底 |
| Google API一時エラー | exponential backoffで自動リトライ（gspread内蔵） |
| Google APIレート制限 | gspreadのrate limit handling + ファイル間の待機 |
| サービスアカウントキー失効 | エラーログ出力。手動更新が必要 |
| PC再起動 | NSSMサービスにより自動起動 |
| スクリプトクラッシュ | NSSMにより自動再起動 |
| 同期中にExcel更新 | 次サイクルで再検知・再同期（データ中心のため問題なし） |
| 複数ファイル同時更新 | 順次処理。15分間隔なら余裕で完了 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| (未発生) | - |

## Resources
- openpyxl: https://openpyxl.readthedocs.io/
- gspread: https://docs.gspread.org/
- Google Sheets API: https://developers.google.com/sheets/api
- Google Service Account: https://cloud.google.com/iam/docs/service-accounts
- NSSM: https://nssm.cc/
- APScheduler: https://apscheduler.readthedocs.io/
