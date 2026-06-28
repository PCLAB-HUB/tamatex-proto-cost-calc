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

### 直近の作業（2026-06-29）

**Streamlit Cloud デプロイ完了** — クライアント確認用 URL を公開

- **公開URL**: `https://tamatex-proto-cost-calc-smtuk3y4wpamumnzmxib2p.streamlit.app/`
- **デプロイ先リポジトリ**: `PCLAB-HUB/tamatex-proto-cost-calc` (Public)
- **エントリーポイント**: 既存設定 `proto/app.py` を quote/app_card.py を exec するプロキシとして配置
- 詳細は memory `reference_streamlit_deploy` 参照

直近の整備:
1. **Codex LGTM ループ 5 ラウンド** — 13件指摘中12件修正（残1件は save_quote 全体ロック化、次フェーズ）
2. **DBクリーニング** — 既存 quote_items の改行混入 30件をクリーニング（scripts/clean_db_whitespace.py に常駐）
3. **品名表示の改行吸収** — Excel セル内改行 (\n) を表示時に正規化、import_excel でも取込時に正規化
4. **Streamlit Cloud対応** — テーマ Light 固定、streamlit==1.58.0 ピン留め、CSS でメインエリア入力欄に明示背景・ボーダー

### 直近の作業（2026-06-27）

**原価計算書見積もり（プロト） プロトタイプ新規構築** — quote/ ディレクトリに構築

1. **計算エンジン** — 原価計算書参考資料.xlsxの154列の数式をPython 20関数に忠実変換
   - FOB→C&F→CIF→仕入値→原価→売価→粗利の計算チェーン
   - 26テスト全PASS、94商品中91件がExcel完全一致（残3件はExcel手動上書き）
   - Codex adversarial-review + review 多ラウンド実施、計算ロジック・データ整合性・XSS 全件修正済み

2. **UI** — B案（カード+ダッシュボード）採用、3階層ナビゲーション
   - ① 見積もり一覧（顧客・担当者フィルタ）
   - ② 見積もり明細（ヘッダー+商品テーブル+合計KPI、warnings集約、エクスポートgate）
   - ③ 商品計算シート（1商品の原価計算詳細）
   - ダークサイドバー、ライトメインエリア

3. **管理機能** — 顧客マスタ・担当者マスタ・パラメータ設定・見積書HTML出力
   - SQLite永続化、見積もり番号自動採番(Q-2026-XXXX)
   - パラメータは見積もり単位で保存・復元（楽観ロック付き、session_state baseline）

### 次に予定しているタスク
- クライアントフィードバック収集（公開 URL 経由）
- クライアント確認待ち: 選択肢マスタ実データ、コンテナ積載量(R列)計算方法、センターフィー/歩引の運用
- 見積書PDF出力の充実化（会社ロゴ、印影、消費税計算等）
- save_quote() 全体の楽観ロック化（並行編集対応・次フェーズ）

### 未解決の問題・注意点
- **R列（コンテナ積載量）**: 正確な計算式が不明（旧Excelの計算シートと新Excelの値が完全一致しない）。手動入力で運用中
- **選択肢マスタ**: 仕入先・揚地・出荷先等は現データが1パターンのみ。クライアント確認要
- **デプロイ先データ永続化なし**: Streamlit Cloud コンテナ揮発性のため、クライアントの編集はセッション中のみ
- **ローカル起動**: `/Users/pclab/Desktop/Project/tamatex/.venv/bin/python -m streamlit run quote/app_card.py --server.port 8503`
- **Cloud 再デプロイ**: tamatex-proto-cost-calc リポジトリの main に push で自動更新。初回エラー時は手動 Reboot 必要
