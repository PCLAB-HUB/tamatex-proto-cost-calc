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
├── generate_proposal_pdf.py       # 業務改善提案書PDF生成
├── generate_document_feasibility_pdf.py  # 帳票生成実現可能性分析PDF
└── build_installer.bat  # PyInstallerでexe化

config/
└── config.example.yaml  # 設定テンプレート（state_db_path追加済み）

tests/                # pytest ユニットテスト（107件）
├── test_state.py     # 16件
├── test_config.py    # 21件
├── test_watcher.py   # 30件
├── test_excel_reader.py  # 23件
└── test_logger.py    # 17件

docs/                        # tamatex本体ドキュメント＋両プロジェクト共通資料
├── システム仕様書.md
├── システム仕様書.pdf
├── 導入手順書.md
├── コードレビュー報告書.pdf  # 4観点統合レビュー（7ページ）
├── 見積書.pdf
├── 業務改善提案書.pdf        # 45項目4フェーズ（6ページ）
├── 2026-04-07_会議要約.md    # PLAUD AI要約タブ（両プロジェクト起点会議）
├── 2026-04-07_会議議事録.md  # PLAUD AI議事録タブ（タイムスタンプ付き33セクション）
├── plans/
│   └── 2026-03-26-phase1-critical-fixes.md
└── cost-calc/                # 原価計算プロトタイプ関連資料（feature/proto-cost-calc用）
    ├── 2026-04-15_原価計算プロトタイプ計画書.md  # プロトタイプ実装計画（全量仕様）
    ├── 営業_原価計算（輸入）.xlsx  # 現行Excel原価計算シート（解析済み）
    ├── 帳票生成_実現可能性分析.pdf  # 4帳票の実現可能性（5ページ）
    ├── 04-14 会議_品番管理システムと原価計算の課題-Summary.md
    └── 04-14 会議_品番管理システムと原価計算の課題-会議議事録.md

proto/                    # 原価計算プロトタイプ（feature/proto-cost-calcブランチ）
├── engine/               # 計算エンジン（本番移植可能）
│   ├── models.py         # dataclass定義（SingleItem, GiftSet, ImportCondition等）
│   ├── calc_single.py    # 単品原価計算
│   ├── calc_gift.py      # ギフトセット原価計算
│   ├── calc_import.py    # 輸入経費・物流共通計算
│   └── calc_summary.py   # 集計計算
├── data/                 # モックデータ（Excel実値）
│   ├── mock_items.py     # 単品6品目
│   ├── mock_gifts.py     # ギフト12パターン
│   └── mock_params.py    # 輸入条件20FT/40FT
├── ui/                   # Streamlit UI（実装済み）
│   ├── sidebar.py        # サイドバー（条件設定、コンテナ切替対応）
│   ├── section_basic.py  # 基本情報表示
│   ├── section_items.py  # 単品タオル一覧
│   ├── section_gift.py   # ギフトセット構成・詳細
│   ├── section_result.py # 比較一覧（チャート付き）
│   └── section_verify.py # Excel検証セクション（120/120全一致）
├── tests/                # 計算エンジンテスト（131件）
│   ├── test_calc_single.py
│   ├── test_calc_gift.py
│   └── test_calc_summary.py
└── app.py                # Streamlitエントリーポイント（5タブ構成）

# プロトタイプ作業管理ファイル（feature/proto-cost-calcブランチのみ）
# task_plan.md / findings.md / progress.md はmasterには存在せず、
# feature/proto-cost-calcのルート配下にのみ存在する
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

### 直近の作業（2026-04-16 セッション6 — 現場導入ライブサポート）

**tamatex 初回現場導入を実施中、config.yaml作成途中でセッション終了**。次回は即座に続きから再開。

#### 現場環境（確定）
- **インストールPC**: Windows 11、Python既存（PATH通過済み）、PowerShell
- **インストール先**: `C:\nas-googlesync`（zip展開先 `C:\tamatex` と分離）
- **NASパス**: `Z:\`（同期対象の親フォルダそのものをZドライブに永続マップ済み）
- **Google Drive フォルダID**: `1mIscR0MzvkIL7kVmEo5RgZHHUcEGdx--`
- **同期間隔**: 15分
- **共有先メール**: 今回は空 `[]`
- **service_account.json**: `C:\Users\User\Downloads\tamatex-ba84a8f4a9c1.json`（インストール先の `config/` に配置済み）

#### 進捗
- ✅ 現場配布用 `tamatex.zip` 作成（机上作業、239KB、社内機密除外済み）
- ✅ `setup.bat` をCP932+CRLF+英字名に修正（UTF-8/日本語名のままだとcmd文字化け）
- ✅ Step 1: ディレクトリ作成 / Step 2: ファイルコピー（インストーラー）
- ❌ GUIインストーラーは Step 3 で `tkinter.TclError` により停止 → **手動インストールに切替**
- ⏸️ Step 3: config.yaml 作成 — **ここで中断**（複数手法で失敗、最終方針は `config.example.yaml` コピー → メモ帳置換）
- ✅ Step 4: service_account.json 配置
- ✅ Step 5: venv作成 / Step 6: pip install
- ❌ 動作テスト未実施、Step 7: NSSMサービス化 未着手

#### インストーラーのバグ2件を現場で発見（Phase 2修正対象）
1. `_create_config_yaml` がバックグラウンドスレッドから `tkinter.StringVar.get()` を呼んで TclError（installer.py:1384-1393）
2. インストール先とzip展開先が同じだと自己コピーで `WinError 32` 発生（重複検知未実装）

### 前回の作業（2026-04-16 セッション5）
1. **顧客請求金額の試算**: 推奨120-200万円（税別）、帳票生成は次フェーズ別見積
2. **原価計算プロトタイプ Streamlit Cloudデプロイ**（セッション4）: `https://tamatex-proto-cost-calc-smtuk3y4wpamumnzmxib2p.streamlit.app/`

### 次に予定しているタスク（次セッション＝現場導入再開）

**最優先: tamatex 現場導入を完了させる**

1. 現状の `C:\nas-googlesync\config\config.yaml` を `Get-Content` で確認
2. `config.example.yaml` からコピー → メモ帳で2箇所置換:
   - `Z:\\共有\\Excel` → `Z:\\`
   - `drive_folder_id: ""` → `drive_folder_id: "1mIscR0MzvkIL7kVmEo5RgZHHUcEGdx--"`
3. YAML構文チェック（PyYAML読み込みテスト）
4. **Drive共有設定**（重要）: `service_account.json` の `client_email` をDriveフォルダに編集者権限で共有
5. 動作テスト: `.\.venv\Scripts\python.exe -m tamatex.main -c .\config\config.yaml`
6. 成功確認 → NSSMサービス化
7. **サービス実行アカウントをLocalSystem→NAS認可ユーザーに変更**（でないとZ:が見えず詰む）
8. PC再起動→自動起動テスト
9. 事務員への運用引き継ぎ

**その後（現場完了後）:**
- インストーラーPhase 2修正: StringVarスレッド参照バグ、インストール先重複検知
- 顧客への請求・見積書発行
- 帳票生成機能（顧客回答待ち）
- プロトタイプ残存課題（40FTテスト、io_fee/storage_fee設計矛盾）
- Phase A-01: 品番マスタのスプレッドシート初版整備

### 未解決の問題・注意点
- **🔴 現場導入中断中**: 現場PC側に `C:\nas-googlesync\config\config.yaml` が壊れた状態で残存している可能性。次回開始時は必ず現状確認から
- **🔴 インストーラー重大バグ2件**: 次の現場導入までに修正必須（詳細はmemory `project_installer_known_bugs.md`）
- **未コミットの変更多数（master）**: CLAUDE.md、システム仕様書.md、会議議事録、提案書、原価計算Excel、計画書、帳票分析PDF等
- **プロトタイプ更新時の二重管理**: feature/proto-cost-calc → PCLAB-HUB/tamatex-proto-cost-calc
- **40FTの検証未実施**: 20FT条件のみ検証済み
- **Excel原価計算の不明点4箇所**: 顧客確認必要（計画書セクション8参照）
- **帳票生成の不足情報**: 正式品番、上代、取引先名、素材・色・JAN（顧客回答待ち）
- **Python環境が必須**: 現状のインストーラーはターゲットPCにPython 3.11+必要
- **Google API実認証**: 現場で初回実施中、動作テスト未完了
- **帳票生成に必要な不足情報**: 正式品番、上代、取引先名、素材・色・JAN（顧客回答待ち）
- **Python環境が必須**: 現状のインストーラーはターゲットPCにPython 3.11+が必要
- **Google API実認証は未テスト**: service_account.jsonがテスト環境にないため
