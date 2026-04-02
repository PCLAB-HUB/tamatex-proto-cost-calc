# tamatex

## プロジェクト概要

QNAP NAS上のExcelファイル（10〜20個）を15分間隔でポーリング監視し、変更検知時にGoogle Spreadsheetへ一方向同期するPythonデーモン。事務員のExcel運用を変えずに、営業・役員が外出先からスプレッドシートで閲覧可能にする。

## アーキテクチャ

```
src/tamatex/          # メインパッケージ（src-layout）
├── __init__.py       # バージョン定義 (0.1.0)
├── main.py           # エントリーポイント・同期ループ（threading.Event使用）
├── config.py         # YAML設定管理（dataclass frozen=True）
├── watcher.py        # NASポーリング・変更検知（mtime + MD5）
├── excel_reader.py   # openpyxl読取（マージセル展開対応、read_only=False）
├── sheets_sync.py    # Google Sheets API同期（gspread 6.x、service_account()）
├── state.py          # SQLite同期状態管理（単一コネクション、upsert対応）
└── logger.py         # RotatingFileHandler（10MB × 5世代）

scripts/
├── installer.py      # tkinter GUIインストーラー（7ステップウィザード）
├── initial_setup.py  # 初回スプレッドシート一括作成
├── generate_pdf.py   # 仕様書PDF生成
├── generate_estimate_pdf.py    # 見積書PDF生成
├── generate_review_report_pdf.py  # コードレビュー報告書PDF生成
└── build_installer.bat  # PyInstallerでexe化

config/
└── config.example.yaml  # 設定テンプレート（state_db_path追加済み）

tests/                # pytest ユニットテスト（107件）
├── test_state.py     # 16件
├── test_config.py    # 21件
├── test_watcher.py   # 30件
├── test_excel_reader.py  # 23件
└── test_logger.py    # 17件

docs/
├── システム仕様書.md
├── システム仕様書.pdf
├── 導入手順書.md
├── コードレビュー報告書.pdf  # 4観点統合レビュー（7ページ）
├── 見積書.pdf
└── plans/
    └── 2026-03-26-phase1-critical-fixes.md
```

## 技術スタック

- Python 3.11+ / openpyxl / gspread 6.x / google-auth / PyYAML
- パッケージ管理: setuptools (pyproject.toml, src-layout)
- テスト: pytest
- インストーラー: tkinter + PyInstaller
- サービス化: NSSM

## 開発コマンド

```bash
# 仮想環境 & パッケージインストール
python -m venv .venv && source .venv/bin/activate
pip install -e .      # editable install（開発時）
pip install .          # 通常install（本番）

# テスト実行
python -m pytest tests/ -v

# 同期デーモン起動
python -m tamatex.main -c ./config/config.yaml

# 初回セットアップ
python scripts/initial_setup.py
```

## 現在の作業状態

### 直近の作業（2026-04-03）

1. **見積書作成** (6aca711)
   - 顧客向け見積書PDF生成（税込¥1,078,275、7カテゴリ20項目の明細）
   - AI開発 vs 従来型開発の比較分析を実施

2. **コードレビュー実施** (6aca711)
   - 4観点（セキュリティ・コード品質・運用耐性・テスト品質）で全モジュールレビュー
   - CRITICAL 5件、HIGH 19件、MEDIUM 13件、LOW 21件を検出
   - 7ページのレビュー報告書PDFを生成（docs/コードレビュー報告書.pdf）

3. **Phase 1 CRITICAL/HIGH修正** (d0d1ec1, 6ad6210)
   - C-1: `gspread.service_account()`に切替え（トークン自動リフレッシュ保証）
   - C-2: StateDB単一コネクション保持 + `close()` + コンテキストマネージャ
   - F-01: 認証ファイルのパーミッション警告（Unix系）
   - F-03: シンボリックリンクによるbase_path外アクセス防止
   - F-04: SQLiteパスを設定ファイル親ディレクトリで絶対パス解決
   - OH-5: `atexit.register(state_db.close)`でクリーンアップ保証
   - 全107テストPASS + E2E動作確認済み

4. **導入手順書の整合性修正** (5ed58a5)
   - Phase 1修正に伴う9件の不整合を修正
   - initial_setup.pyのDBパス解決をmain.pyと統一
   - NSSM引数、ログ出力例、設定例、エラーメッセージ等を更新

### 次に予定しているタスク
- **Phase 2修正**（初回リリース後30日以内、工数3-5日）:
  - Google API指数バックオフリトライ（OH-1/6）
  - sheets_sync.py / main.py のモックテスト作成（T-01/02）
  - dataclass frozen=True化（H-1/2）
  - 巨大Excelファイルサイズ上限チェック（OH-2）
  - 壊れたExcelの連続失敗スキップ（OH-7）
  - シート全クリア後書込（OH-8）
  - 詳細: docs/コードレビュー報告書.pdf Phase 2セクション参照
- 実顧客環境でのデプロイ・動作確認
- Python不要化の検討（PyInstallerで本体exe化、またはPython embeddable同梱）

### 未解決の問題・注意点
- **Python環境が必須**: 現状のインストーラーはターゲットPCにPython 3.11+が必要
- **Google API実認証は未テスト**: service_account.jsonがテスト環境にないため。API存在確認済み、顧客環境で初回確認必要
- **Windows実機テスト未実施**: macOS上でのテストのみ。パス解決やNSSMは実機確認必要
- **未コミットの変更**: `docs/システム仕様書.md` に軽微な差分あり
- **安全性確認済み**: NAS上のExcelファイルへの書き込み・ロック・一時ファイル作成は一切なし
- **見積書の金額未確定**: 合計¥1,078,275は端数あり。ユーザーが¥1,100,000等への丸めを検討中
