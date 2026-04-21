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

### 直近の作業（2026-04-21 セッション7 — プロトタイプUI大改修エピック完了）

**原価計算プロトタイプの UI 大改修を CCPM で実行し完了。ただし Streamlit Cloud（main）反映は未実施**。

#### 前半: プロジェクト整理 + CCPM 計画
- `docs/cost-calc/` サブフォルダ隔離でプロトタイプ資料を tamatex 本体と分離（master commit `9afe965`）
- ルートの作業管理ファイル（task_plan.md 等）を `feature/proto-cost-calc` に移管（master commit `0bbf093`）
- `PCLAB-HUB/tamatex-proto-cost-calc` を origin に設定
- CCPM で PRD → Epic → 10 タスクに分解、GitHub に Epic #1 + 10 sub-issues（#2〜#11）作成

#### 後半: 並列エージェント実行 + ランタイムバグ修正
- **Phase 2 (4並列 Sonnet)**: 依存永続化層・KPIカード・aggridファクトリ・為替感度チャートを同時実装
- **Phase 3 (4並列 Sonnet)**: ダッシュボード・シナリオタブ・サイドバー改修・既存タブaggrid化を同時実装
- **Phase 4 (1 Sonnet)**: app.py 統合 + smoke test
- 各フェーズ完了後メインセッションで consolidation、GitHub issue クローズ、epic.md 更新
- **ランタイムバグ 5 件を発見・修正**（ブラウザ実機検証で全発覚）:
  1. `DataReturnMode.AS_INPUT_AND_FILTERED` 廃止 → `FILTERED_AND_SORTED`
  2. `sqlite3.ProgrammingError` スレッド越境 → `check_same_thread=False`
  3. KPIカード白×白 判読不能 → 自前CSS
  4. aggrid `LargeUtf8` 未対応 → `_normalize_string_columns` + `use_json_serialization=True`
  5. aggrid `valueFormatter` 関数文字列 SyntaxError → `JsCode` ラッパー
- 詳細は memory `reference_streamlit_aggrid_gotchas.md`

#### 成果物
- **232 テスト全 PASS**（既存131 + 新規101）
- 7タブ UI: ダッシュボード / 基本情報 / 単品タオル / ギフトセット / 比較一覧 / シナリオ / Excel検証
- シナリオ管理: SQLite 永続化 + 2件横並び比較
- `feature/proto-cost-calc` を origin に push 済（44 commits ahead of origin/main）
- **main へのマージは未実施** → Streamlit Cloud 反映は次回

### 棚上げ中の作業（2026-04-16 セッション6 — tamatex 現場導入）

**現場導入は config.yaml 作成途中で中断**。プロトタイプ改修が優先された形。次回再開で必要な情報は memory `project_onsite_deploy_20260416.md` に集約:
- インストール先 `C:\nas-googlesync`、NAS `Z:\` マップ済
- Drive folder ID: `1mIscR0MzvkIL7kVmEo5RgZHHUcEGdx--`
- Step 1-2, 4-6 完了 / Step 3 config.yaml 作成で中断 / Step 7 NSSM 未着手
- インストーラー Phase 2 修正必要（StringVar スレッドバグ + インストール先重複検知）

### 次に予定しているタスク（優先度順）

**🔴 最優先: プロトタイプ main マージ + 現場デモ**
1. `feature/proto-cost-calc` → `PCLAB-HUB/tamatex-proto-cost-calc` の `main` に PR 作成 or 直接 push
   - PR URL: `https://github.com/PCLAB-HUB/tamatex-proto-cost-calc/pull/new/feature/proto-cost-calc`
2. Streamlit Cloud でビルド成功確認（追加 3 ライブラリ: streamlit-aggrid, plotly, streamlit-extras）
3. 顧客（社長・役員）への新UIデモ実施

**🟠 手動 E2E 確認（自動テストで制約あり）**
- シナリオ 2件選択→「📊 比較」ボタンの活性化と比較ビュー描画
- シナリオ CRUD（読込/複製/リネーム/削除）
- サイドバー条件変更→全タブの連動更新

**🟡 現場導入再開（tamatex 本体、別プロジェクト扱い）**
- 現場 PC 側 `C:\nas-googlesync\config\config.yaml` の現状確認
- `config.example.yaml` コピー → メモ帳置換 → PyYAML で構文チェック
- Drive 共有設定 → 動作テスト → NSSM サービス化
- サービス実行アカウントを NAS 認可ユーザーに変更（LocalSystem では Z: が見えない）

**🟢 後続課題**
- インストーラー Phase 2 修正
- 顧客への請求・見積書発行
- 帳票生成機能（顧客回答待ち）
- プロトタイプ残存課題（40FT テスト、io_fee/storage_fee 設計矛盾、上代 delta 常に ±¥0）
- Phase A-01: 品番マスタのスプレッドシート初版整備

### 未解決の問題・注意点

#### プロトタイプ関連
- **🟠 main マージ未実施**: `feature/proto-cost-calc` は 44 commits ahead。次回セッションで即 push/PR
- **🟠 シナリオ比較 E2E 未自動検証**: claude-in-chrome では aggrid iframe のチェックボックス選択が Streamlit に伝播しない（memory `reference_streamlit_browser_automation.md` 参照）
- **🟠 最初のテスト保存で名前重複** (id=1 が「標準_USD150scenario_USD150」): 自動テスト中の入力操作起因、実運用では問題なし。必要なら DELETE 文で id=1 を削除
- **requirements.txt 注意**: worktree 側は tamatex 本体デップのみ。origin/main 側は streamlit/pandas を含む別 requirements.txt。Cloud デプロイ時は origin/main 側が使われる
- **pandas 3.x + streamlit-aggrid 1.2.1 互換性**: 既知の互換性問題に対する対策を `aggrid_table.py` に実装済（`_normalize_string_columns` + `JsCode` + `use_json_serialization=True`）

#### tamatex 本体（棚上げ中）
- **🔴 現場導入中断中**: 現場 PC `C:\nas-googlesync\config\config.yaml` が壊れた状態で残存している可能性
- **🔴 インストーラー重大バグ2件**: 次の現場導入までに修正必須
- **Python 環境必須**: 現状のインストーラーは Python 3.11+ が必要
- **Google API 実認証**: 現場で初回実施中、動作テスト未完了

#### 共通
- **プロトタイプ更新時の二重管理**: feature/proto-cost-calc → PCLAB-HUB/tamatex-proto-cost-calc（別repoデプロイ先）
- **Excel 原価計算の不明点4箇所**: 顧客確認必要（計画書セクション8参照）
- **帳票生成の不足情報**: 正式品番、上代、取引先名、素材・色・JAN（顧客回答待ち）
- **未コミットの変更（master）**: 前セッション由来で残っているもの:
  - `M docs/システム仕様書.md`（軽微な編集）
  - `?? docs/2026-04-07_会議要約.md` / `docs/2026-04-07_会議議事録.md`
  - `?? docs/業務改善提案書.pdf`
  - `?? scripts/generate_document_feasibility_pdf.py` / `generate_proposal_pdf.py`
  - `?? setup.bat`（現場導入用、前セッション作成）
  - `?? src/tamatex.egg-info/`（ビルド成果物、.gitignore 候補）
- **未コミットの変更（feature/proto-cost-calc）**: なし（全commit済 + origin push済）
