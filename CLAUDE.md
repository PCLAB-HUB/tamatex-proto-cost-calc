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
├── 業務改善提案書.pdf        # 45項目4フェーズ（6ページ）
├── 営業_原価計算（輸入）.xlsx  # 現行Excel原価計算シート（解析済み）
├── 2026-04-15_原価計算プロトタイプ計画書.md  # プロトタイプ実装計画（全量仕様）
├── 04-14 会議_品番管理システムと原価計算の課題-Summary.md
├── 04-14 会議_品番管理システムと原価計算の課題-会議議事録.md
├── 2026-04-07_会議要約.md    # PLAUD AI要約タブ
├── 2026-04-07_会議議事録.md  # PLAUD AI議事録タブ（タイムスタンプ付き33セクション）
└── plans/
    └── 2026-03-26-phase1-critical-fixes.md

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
├── ui/                   # Streamlit UI（未実装）
├── tests/                # 計算エンジンテスト（131件）
│   ├── test_calc_single.py
│   ├── test_calc_gift.py
│   └── test_calc_summary.py
└── app.py                # Streamlitエントリーポイント（未実装）

# プロトタイプ作業管理ファイル（プロジェクトルート）
task_plan.md              # タスク一覧・進捗管理
findings.md               # Excel解析結果
progress.md               # セッションごとの作業記録
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

### 直近の作業（2026-04-15 セッション2）

1. **原価計算プロトタイプ Phase 1 完了** (0d9e01b, feature/proto-cost-calc)
   - 計算エンジン全体を実装（単品・ギフト・輸入経費・物流・集計）
   - Excel実値と±0.01円以内の完全一致を検証（131テスト全PASS）
   - worktree: `.worktrees/proto-cost-calc`
   - 計画書との乖離を多数発見・修正（輸入経費パラメータ差異、ギフトデータ不正確等）

2. **Excel解析の追加発見**
   - 輸入経費パラメータが単品/ギフトで異なる（BQ: 20000 vs 0, BW: 0 vs 19200）
   - CA式のBO列はCIC(USD=180)、CY CHARGEではない
   - CA式の為替: 単品=$N$4(現行), ギフト=$M$4(社内)

### 前回の作業（2026-04-15 セッション1）

1. **2026-04-14会議の議事録読込・分析**
2. **Excel原価計算シートの全量解析**（98列、全計算式を抽出）
3. **原価計算プロトタイプ計画書の作成**

### 次に予定しているタスク（次セッション）
- **原価計算プロトタイプ Phase 2: Streamlit UI構築**（最優先）:
  - `pip install streamlit` が必要
  - 8タスク: サイドバー → 基本情報 → 単品一覧 → ギフト構成 → 計算結果 → 比較表 → Excel検証 → 統合
  - worktree `.worktrees/proto-cost-calc` で作業継続
  - 計画書: docs/2026-04-15_原価計算プロトタイプ計画書.md セクション5 Phase 2
- **原価計算プロトタイプ Phase 3: 検証・デモ準備**（Phase 2後）
- **業務改善の個別施策**（プロトタイプ後）:
  - Phase A-01: 品番マスタのスプレッドシート初版整備
- **tamatex Phase 2修正**（初回リリース後30日以内）

### 未解決の問題・注意点
- **未コミットの変更あり（masterブランチ）**: CLAUDE.md、システム仕様書.md
- **未コミットの変更多数（master untracked）**: 会議議事録、提案書、原価計算Excel、計画書等
- **40FTの検証未実施**: 20FT条件のみ検証済み。40FTは参考値扱い
- **Excel原価計算の不明点4箇所**: 顧客確認が必要（計画書セクション8参照）
- **Python環境が必須**: 現状のインストーラーはターゲットPCにPython 3.11+が必要
- **Google API実認証は未テスト**: service_account.jsonがテスト環境にないため
