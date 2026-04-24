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
├── engine/               # 計算エンジン（本番移植可能、不可侵）
│   ├── models.py         # dataclass定義（SingleItem, GiftSet, ImportCondition等）
│   ├── calc_single.py    # calc_single_item() — 単品原価計算
│   ├── calc_gift.py      # calc_gift_set() — ギフトセット原価計算
│   ├── calc_import.py    # 輸入経費・物流共通計算
│   └── calc_summary.py   # calc_summary() — 集計計算
├── data/                 # モックデータ（Excel実値）
│   ├── mock_items.py     # ALL_ITEMS（単品6品目）
│   ├── mock_gifts.py     # ALL_GIFTS（ギフト12パターン）
│   └── mock_params.py    # COND_20FT/COND_40FT（輸入条件）
├── storage/              # シナリオ永続化層（2026-04-21新規）
│   ├── scenario_repo.py  # ScenarioRepository（SQLite CRUD）
│   └── serializer.py     # ImportCondition ⇄ JSON 変換
├── ui/                   # Streamlit UI（7タブ構成）
│   ├── sidebar.py        # サイドバー + apply_condition_to_session_state
│   ├── dashboard.py      # ダッシュボードタブ（KPI/為替感度/品目ランキング）
│   ├── scenarios.py      # シナリオタブ（CRUD+2件比較）
│   ├── section_basic.py  # 基本情報表示
│   ├── section_items.py  # 単品タオル（aggrid化済）
│   ├── section_gift.py   # ギフトセット（aggrid化済）
│   ├── section_result.py # 比較一覧（aggrid+チャート）
│   ├── section_verify.py # Excel検証（120/120全一致）
│   └── components/       # 共通UI部品
│       ├── kpi_cards.py        # KPIカード+フォーマッタ
│       ├── aggrid_table.py     # aggridファクトリ（JsCode+LargeUtf8対策済）
│       ├── sensitivity_chart.py # plotly為替感度チャート
│       └── styles.py           # CSS定数
├── tests/                # pytest テスト（232件）
│   ├── test_calc_single.py / test_calc_gift.py / test_calc_summary.py  # 既存131件
│   ├── test_scenario_repo.py / test_serializer.py                      # 新規47件
│   ├── test_formatters.py / test_aggrid_table.py / test_sensitivity_chart.py  # 新規50件
│   ├── test_sidebar.py / test_smoke.py                                 # 新規13件
└── app.py                # Streamlitエントリーポイント（7タブ + ScenarioRepository シングルトン）

# CCPM 管理ディレクトリ（feature/proto-cost-calcブランチのみ）
.claude/
├── prds/cost-calc-ui-revamp.md
└── epics/cost-calc-ui-revamp/
    ├── epic.md                  # status: completed, progress: 100%
    ├── 2.md〜11.md              # 10タスク全クローズ
    └── github-mapping.md

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

### 直近の作業（2026-04-24 セッション8 — tamatex 現場導入完遂）

**4-16 から棚上げ中だった tamatex 現場導入を SSH 経由で完遂。NSSM サービス化・自動同期まで到達**。

#### セッション開始時点の状況
- 前セッション（4-16）で config.yaml 作成途中で中断
- 現場 PC (`DESKTOP-3TM1PKS` / Tailscale `100.124.181.55`) へは SSH 鍵認証で接続可能（User アカウント、Administrator 権限あり）
- Python 3.14.4 venv + tamatex 0.1.0 + 依存パッケージは 4-16 時点でインストール済み
- config.yaml は存在、`drive_folder_id: 1mIscR0MzvkIL7kVmEo5RgZHHUcEGdx--` を指していた（個人ドライブ想定）
- service_account.json 配置済み（`tamatex-sync@tamatex.iam.gserviceaccount.com`）
- 4-16 ログに `403: Drive storage quota has been exceeded` が残っていた

#### 今回の作業フロー
1. **点検フェーズ**: SSH 経由で UTF-8 エンコードで config.yaml・ログ・Python 環境・NSSM 存在確認
2. **Google 側再構成**: 顧客が新しく取得した組織アカウント `info816@g.tamatex.jp` 配下に共有ドライブを作成、同期先フォルダを作成（ID `1HaBKW0-Hvctu7o7KlCyU3c88z9RtxDYb`）、サービスアカウントを「コンテンツ管理者」として招待
3. **config.yaml 差し替え**: `drive_folder_id` を新フォルダIDに更新、UTF-8 保持
4. **NAS 認証設計**: SSH (Network logon) からは `cmdkey` 不可、`net use` でセッション認証可能と判明。パスワードは `Tm1225` → `tm1225`（小文字）が正解
5. **tamatex 本体改修**: 
   - `src/tamatex/nas_auth.py` を新規追加（subprocess で `net use` を起動時に実行）
   - `src/tamatex/config.py` に `NasAuthConfig` 追加
   - `src/tamatex/main.py` で `authenticate_nas()` を起動時呼び出し
   - `config/config.example.yaml` にサンプル追記
   - `tests/test_nas_auth.py` 6件追加（113/113 全PASS）
   - **commit `c1c4184`**: `feat: NAS SMB自己認証機能を追加（サービス実行対応）`
6. **現場デプロイ**: 修正した 3 ファイル（config.py / main.py / nas_auth.py）を scp で site-packages に反映、config.yaml に `nas.auth` セクションを追加
7. **統合テスト**: `test_one_cycle.py` で初回同期成功（`scanned=4 synced=4 errors=0`、37シート作成）、2回目は `skipped=4`（変更検知正常）
8. **NSSM サービス化**: `nssm-2.24.zip` をダウンロード → `C:\nas-googlesync\bin\nssm.exe` に配置 → `tamatex` サービスを **LocalSystem** で登録（Start=Automatic, AppRestartDelay=30s）
9. **稼働確認**: 10:34:59 と 10:49:59 の2サイクル連続で正常動作、tamatex 自身がサービスコンテキストで `net use` 認証成功
10. **クリーンアップ**: 現場 PC の一時テストスクリプト類を削除（config.yaml バックアップは残置）

#### 最終稼働構成
- サービス `tamatex`: Running / Automatic / LocalSystem / python.exe (PID稼働中, 53MB)
- ログ: `C:\nas-googlesync\logs\tamatex.log`（UTF-8, 10MB×5ローテーション）
- 15分間隔で自動同期中、エラー・警告ゼロ

### 未解決の問題・注意点

#### tamatex 現場導入（運用フェーズ）
- **🟡 share_with 未設定**: 営業・役員メールを顧客から受領後、config.yaml に追記 → `nssm restart tamatex`
- **🟡 Windows再起動時の自動起動未検証**: `StartType=Automatic` 設定済だが、再起動タイミングで `Get-Service tamatex` 確認要
- **🟡 実運用テスト未完了**: 事務員が通常業務で Excel 更新 → 最大15分以内に Sheets 反映することを顧客確認
- **🟡 config.yaml に NAS パスワード平文**: Windows ACL での保護を追加検討（icacls で Administrators+SYSTEM のみに制限）

#### 現場 PC の保全ファイル（クリーンアップ対象外）
- `C:\nas-googlesync\config\config.yaml.bak_before_shareddrive`（設定変更前のバックアップ、監査証跡として残置）
- `C:\nas-googlesync\logs\tamatex.log.pre_*`（各テストサイクル前のログスナップショット）

#### プロトタイプ関連（前セッションから継続）
- **🟠 main マージ未実施**: `feature/proto-cost-calc` は 44 commits ahead of `PCLAB-HUB/tamatex-proto-cost-calc/main`
- **🟠 シナリオ比較 E2E 未自動検証**: claude-in-chrome では aggrid iframe のチェックボックス選択が Streamlit に伝播しない
- **pandas 3.x + streamlit-aggrid 1.2.1 互換性**: 対策を `aggrid_table.py` に実装済

#### 共通・後続
- **インストーラー Phase 2 修正**（StringVar スレッドバグ + インストール先重複未検知、project_installer_known_bugs.md）
- **顧客への請求・見積書発行**
- **帳票生成機能**（顧客回答待ち）
- **Excel 原価計算の不明点4箇所**（顧客確認必要）
- **Phase A-01: 品番マスタのスプレッドシート初版整備**

### 次に予定しているタスク（優先度順）

**🟠 短期（次回セッション直後にやる）**
1. 現場 `tamatex` サービスの継続稼働確認（数時間〜1日後、ログに連続した15分サイクル記録）
2. 実運用テスト（事務員 Excel 更新 → Sheets 反映確認）
3. 顧客から受領次第、`share_with` に営業・役員メール追加 → `nssm restart tamatex`

**🔴 中期: プロトタイプ main マージ + 現場デモ**
1. `feature/proto-cost-calc` → `PCLAB-HUB/tamatex-proto-cost-calc/main` に PR/push
2. Streamlit Cloud でビルド成功確認
3. 顧客（社長・役員）への新UIデモ

**🟢 後続課題**
- インストーラー Phase 2 修正
- 顧客への請求・見積書発行
- 帳票生成機能
- プロトタイプ残存課題（40FT テスト、io_fee/storage_fee 設計矛盾、上代 delta 常に ±¥0）

### 未コミットの変更（master）

前セッション由来で残っているもの:
- `M docs/システム仕様書.md`（軽微な編集）
- `?? docs/2026-04-07_会議要約.md` / `docs/2026-04-07_会議議事録.md`
- `?? docs/業務改善提案書.pdf`
- `?? scripts/generate_document_feasibility_pdf.py` / `generate_proposal_pdf.py`
- `?? setup.bat`（現場導入用、前セッション作成）
- `?? src/tamatex.egg-info/`（ビルド成果物、.gitignore 候補）

feature/proto-cost-calc 側: なし（全commit済 + origin push済）
