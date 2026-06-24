# tamatex

## プロジェクト概要

QNAP NAS上のExcelファイル（10〜20個）をポーリング監視し、変更検知時にGoogle Sheets と PDF へ一方向同期するPythonデーモン。事務員のExcel運用を変えずに、営業・役員が外出先からスプレッドシート/PDFで閲覧可能にする。**Drive API直接アップロード方式により書式（罫線・色・マージセル・通貨書式・カスタム書式・非表示列）を完全保持**。NASのサブフォルダ構造をDrive側にも自動ミラー、時刻指定スケジュールで業務時間外への寄せも可能。

## アーキテクチャ

```
src/tamatex/          # メインパッケージ（src-layout）
├── __init__.py       # バージョン定義 (0.1.0)
├── main.py           # エントリーポイント・同期ループ・スケジューリング・サブフォルダ階層解決
├── config.py         # YAML設定管理（mode/times/mirror_subfolders 対応）
├── watcher.py        # NASポーリング・変更検知（mtime + MD5、rglob 再帰）
├── excel_reader.py   # openpyxl読取（旧方式の名残、現在の同期パスでは未使用）
├── sheets_sync.py    # Drive API直接アップロード（xlsx→Sheets変換）+ _local_copy でNASロック最小化
├── pdf_sync.py       # Drive API export で Sheets→PDF 生成・配置（NEW）
├── drive_utils.py    # Drive API共通: build_drive_service / ensure_subfolder / ensure_folder_path / apply_share / move_to_folder（NEW）
├── nas_auth.py       # SMB認証（net use 経由、サービス実行対応）
├── state.py          # SQLite同期状態（pdf_file_id列追加・自動マイグレーション対応）
└── logger.py         # RotatingFileHandler（10MB × 5世代）

scripts/
├── installer.py      # tkinter GUIインストーラー（7ステップウィザード、Phase 2修正対象）
├── generate_pdf.py   # システム仕様書PDF生成（CJK自動折り返し・新仕様反映済）
├── generate_estimate_pdf.py    # 見積書PDF生成
├── generate_review_report_pdf.py  # コードレビュー報告書PDF生成
├── generate_proposal_pdf.py       # 業務改善提案書PDF生成
├── generate_document_feasibility_pdf.py  # 帳票生成実現可能性分析PDF
└── build_installer.bat  # PyInstallerでexe化
# initial_setup.py は新方式（main.py の初回サイクル自動実行）で不要なため削除済

config/
└── config.example.yaml  # 設定テンプレート（mode/times/mirror_subfolders/nas.auth 反映済）

tests/                # pytest ユニットテスト（178件全PASS）
├── test_state.py            # 19件（pdf_file_id列マイグレーション含む）
├── test_config.py           # 27件（times/interval validation含む）
├── test_watcher.py          # 29件
├── test_excel_reader.py     # 25件
├── test_logger.py           # 16件
├── test_nas_auth.py         # 6件
├── test_drive_utils.py      # 15件（NEW: ensure_subfolder/ensure_folder_path/apply_share/move_to_folder）
├── test_sheets_sync.py      # 7件（NEW: upsert+_local_copy）
├── test_pdf_sync.py         # 4件（NEW: upsert_pdf）
├── test_main_schedule.py    # 16件（NEW: _compute_next_wait/times mode/顧客スケジュール）
└── test_main_subfolders.py  # 14件（NEW: _subfolder_parts/_resolve_target_folders/reorganize_existing_files）

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

- Python 3.11+ / openpyxl / **google-api-python-client** / google-auth / PyYAML
- パッケージ管理: setuptools (pyproject.toml, src-layout)
- テスト: pytest（**214件全PASS**）
- インストーラー: tkinter + PyInstaller
- サービス化: NSSM
- gspread 依存は完全排除済（Drive API一本化）

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

# 仕様書PDF再生成（generate_pdf.py 改訂時）
python scripts/generate_pdf.py
```

## 現在の作業状態

### 直近の作業（2026-06-24〜25 セッション12 — 削除伝播の正本復元 + Codex 6ラウンド徹底ハードン）

セッション開始時の調査で、**セッション11で実装・本番デプロイしたはずの削除伝播機能が、この正本リポジトリには統合されていなかった**ことが判明（cb3d9e2 等は別作業コピーへ commit され消失、reflog にも無し）。正本には `drive_utils.trash_file` 断片＋テストしか無く、`main`（_is_mass_deletion・sync_cycle step4）と `watcher`（stored_total）が欠落＝**呼び出し元のないデッドコード状態**（217テスト）。CLAUDE.md の「cb3d9e2／229／reflog復旧可」は誤記で、本セッションで訂正済み。

#### 1. プラン文書から正本へ完全復元（→228テスト）
- `docs/superpowers/plans/2026-06-24-nas-delete-propagation.md`（完全TDDコード）から `watcher.stored_total` / `main._is_mass_deletion` / `sync_cycle` step4＋早期return撤去 / 各テストを復元。
- staged実確認＋pytestゲート＋HEAD着地確認を各コミットで徹底（harness不安定対策）。コミット `0dbf31f`。

#### 2. Codex adversarial-review を6ラウンド（別モデル独立検証・「LGTM」で起動）
同一モデルの自己レビューは初回「健全」と誤判定 → Codex が data-loss 級の盲点を連続発見。各ラウンド事実確認→最小修正→再レビュー:
- **R1**: 走査の一時スキップ→誤trash（実体再確認）/ shutdown中削除（ガード）。`35ac651`
- **R2**: 単一サイクルの部分アンマウント誤削除 → **2サイクル確認**導入 / shutdown細粒度。`3519eef`・`95f738f`
- **R3**: ガード/早期returnで pending stale → 不信頼サイクルで pending リセット。`1fa7abf`
- **R4**: 例外時 stale / 部分スキャンエラー未検出 → `scan_complete`信号（ファイル読取）+ 例外時リセット。`2d4c351`
- **R5**: `rglob` がディレクトリ列挙OSErrorを黙殺 → `os.walk(onerror=)`化。`748bc98`
- **R6**: 同期エラー時も削除確定（→保留）/ partial trashのstate不整合 → 同期エラーゲート（`280c07e`）+ **ファイル境界原子化**（`c9a7f87`、ユーザー判断）。

#### 3. 最終状態
- **245テスト全PASS**、HEAD `c9a7f87`、未push。
- 削除確定の不変条件 = 「**連続2回の、完全走査 ∧ 同期エラーなし ∧ 非空 ∧ 非NASエラー ∧ 非mass ∧ 非shutdown**」。削除は全てゴミ箱（30日復元・完全削除なし）。
- **残リスク（既知・受容/文書化対象）**: 「trash中途のネットワーク失敗＋同一内容で復帰」の二重稀少ケースのみ。全てゴミ箱復元可・手動復旧可。
- 学び: 同一モデル自己レビューの盲点を別系統Codexが補完する価値が定量的に実証された（自己レビュー「健全」→6ラウンドで重大穴を順次除去）。

#### 4. セッション12の残作業（次回最優先）
- **🔴 ハードン版を現場PCへ再デプロイ**: 現場は旧・素のプラン版が稼働中で、ローカル `c9a7f87` が大幅先行。PC復帰後（現在オフライン）に drive_utils/main/watcher 等を `.bak`退避→差し替え→`nssm restart tamatex`→1サイクルのログ確認。当初想定の「差分照合」ではなく更新が本筋。
- **🟡 push 判断**: 未push（ローカル可逆）。リモート反映は明示指示時。

---

### 直近の作業（2026-06-24 セッション11 — NAS削除のDrive追従（削除伝播）機能の実装・本番デプロイ・実証）

現場報告「ファイル名変更で旧スプレッドが残り新名も並ぶ／NASで削除してもDrive側に残る」に対応。**NAS削除→Drive追従（削除伝播）機能**を新規実装し、本番デプロイ・実動作実証まで完了。

- **設計判断**: リネーム検知は省略（YAGNI。「名前変更＋中身更新」はhash変動で検知不能、削除伝播だけで重複は自然解消。URL維持はshare_with空で不要）。削除伝播のみ実装＝**ゴミ箱止まり**（trashed=True・30日復元可・完全削除しない）。一括消失ガード `_is_mass_deletion`（削除数 > 登録総数×0.4 かつ ≥5 でブロック＝60件中25件以上。NAS部分マウント失敗時の大量誤削除防止）。`sync_cycle` の早期return撤去（files_to_sync空だとstep4前にreturnし純粋削除サイクルで削除処理が走らない潜在バグも修正）。
- **実装**: `drive_utils.trash_file` / `watcher.ChangeResult.stored_total` / `main._is_mass_deletion` / `main.sync_cycle` ステップ4書き換え。**229テスト全PASS**。Codex adversarial-review 承認（履歴を `git reset --mixed` でクリーン再構成→HEAD明示で全実装レビューを確証）。⚠️ **セッション12訂正: これらの記録（229テスト・Codex承認・下記コミット cb3d9e2 等）は別クローンのもので、この正本リポジトリには一度も到達していなかった。セッション12でプラン文書から復元（228）→Codex 6ラウンドで再ハードン（245・HEAD c9a7f87）。最上部のセッション12ブロック参照。**
- **本番デプロイ**: 現場PC（client-test, Tailscale経由SSH）に3ファイルを `.bak_20260624_231455` 退避後に差し替え→`nssm restart tamatex`→スキャン60/同期0/エラー0で正常稼働（新ログ「変更なし（新規/更新なし）— 削除検知のみ評価」を確認）。事前確認ヘルパーで削除候補0件＝既存は何も消えず安全。
- **実動作実証**: 現場PCローカルの独立環境（**本番NAS・本番state・本番サービス不可侵**）で「削除→Sheets/PDF両方ゴミ箱・keep無傷・state更新・エラー0」を実証。テスト痕跡は完全掃除済み（事務員に物理的にバレない設計）。
- **環境問題（重要）**: セッション中、Edit/Write/git commit が別作業コピーへ飛ぶ・出力描画が乱れる harness 不安定が頻発。対処は grep/git での実体検証＋python heredocによる「パッチ→検証→テスト→条件commit」の1Bash完結（memory `feedback_tool_apply_verify_onebash` / `reference_isolated_feature_test_remote`）。
- 設計/計画doc: `docs/superpowers/specs/2026-06-24-nas-delete-propagation-design.md`・`plans/2026-06-24-nas-delete-propagation.md`。
- **報告書**: 顧客向け機能改善報告書 `docs/2026-06-24_tamatex機能改善報告書.html/.pdf` をコミット済み（HTML→Chrome headlessでPDF化、専門用語《やさしい言い換え》18箇所、原価計算アプリ拡張への誘導入り）。
- **環境注意（重要・セッション12で訂正済み）**: セッション11のコミット（cb3d9e2 / a3f9c2e 等）は **この正本リポジトリには一度も到達していなかった**（harness不安定で別作業コピーへ commit され、reflog にも残らず消失）。正本には `drive_utils.trash_file` 断片＋テストしか無く、`main`（_is_mass_deletion・sync_cycle step4）と `watcher`（stored_total）が丸ごと欠落＝削除伝播は機能しないデッドコード状態だった。セッション12でプラン文書から完全復元・徹底ハードン済み（最上部のセッション12ブロック参照）。`git add` が空振りすることがあるため `git diff --cached --name-only` で staged を実確認してから commit する習慣は維持。
- **最終コミット（セッション11時点の誤認・訂正済み）**: cb3d9e2 はこの repo に存在しない。削除伝播の現行 HEAD は **c9a7f87（セッション12・245テスト・未push）**。

### 直近の作業（2026-05-20 〜 2026-05-26 セッション10 — Drive API耐性 + Windowsスリープ復帰対策 + コードレビュー反映）

セッション9でリリース後、現場から **「Excel更新がスプレッドシートに反映されない」報告 2回** を受け、独立した2つのバグを発見・対策。コードレビューエージェントによる事後監査で防御コードも追加。**214テスト全PASS、現場で稼働中**。

#### バグ1 (2026-05-20): Drive API 一過性エラー耐性

**症状**: 4ファイル (AAA01Tカラーハンカチ/ピュアカラー/ピュアカラー(鳥生)/NKK01MA7202) が4/24以来慢性的に同期失敗。直近サイクルで `エラー=4` 継続。

**原因**: `build_drive_service()` が起動時1回しか呼ばれず、httplib2 の TCP セッションが長時間アイドルで死ぬ。最初の数件で `ConnectionAbortedError [WinError 10053]` 連続失敗、その後は成功するパターン。リトライ機構も無し。

**対策（fa093f8）**:
- `drive_utils.with_retry()`: `(ConnectionError, TimeoutError, socket.timeout, ssl.SSLError)` + `HttpError(429,500,502,503,504)` 対象、最大3回 exponential backoff
- `ensure_subfolder` / `move_to_folder` / `apply_share` / `get_file_parents` の API 呼出を `with_retry` で wrap
- `sheets_sync.upsert_sheet` / `pdf_sync.upsert_pdf` の API 呼出も wrap（MediaFileUpload は lambda 内で都度再構築）
- **`main.run()` のメインループで各サイクル前に `build_drive_service(quiet=True)` を再生成**
- `tests/conftest.py` で `_retry_sleep` を no-op 化（autouse fixture）

結果: 起動時 baseline サイクルで 11 件全件 in_sync、エラー 0 件、リトライ警告すら出ず（= service 再生成だけで初発エラー解消）。

#### バグ2 (2026-05-25): Windowsスリープ復帰時のタイマー停止

**症状**: 5/22 17:50 のサイクル完了後、5/23(土)/5/24(日)/5/25(月) の 5回の予定サイクルが**完全に未実行**。ログが 62時間ノーアクション。

**原因**: 顧客は「平日17時以降と土日は PC 電源を落としている」と認識していたが、実態は **Fast Startup (HiberbootEnabled=1) + Modern Standby**。Kernel-Power Event 42→107 で 5/22 18:02→5/25 08:56 の 62時間スリープを直接確認、`LastBootUpTime` は 2026/03/16 から不変、Python プロセスは 5/20 から CPU 累計6秒で連続生存。`threading.Event.wait(timeout=18時間)` のタイマーが OS スリープ中にフリーズし、復帰後も「残時間消化」を続けて予定時刻越え未検知。

**対策（2674d25）**:
- `main._sleep_until_event(target_time, shutdown_event, chunk_sec=60.0)`: 目標絶対時刻まで chunk_sec ごとに `datetime.now()` で壁時計を確認しながら待機。PC スリープ復帰直後でも最大60秒で予定時刻越えを検知
- `main.run()` のメインループの `_shutdown_event.wait(timeout=wait_sec)` を `_sleep_until_event(next_run_at, ...)` に置換
- interval モードは `datetime.now() + timedelta(seconds=wait_sec)` を target にして同一パスへ合流

#### コードレビュー反映 (2026-05-26): R1+L2+L8

`code-reviewer` subagent で事後監査 → 重大1 + 軽微8 + 観察6 を独立検証 → 実害ある3点を修正（1064360）:
- **R1**: `drive_utils.with_retry()` で `HttpError.resp.status` を `int()` 明示変換（httplib2 バージョン差で str/int 両方ありうる）
- **L2**: `main.run()` のループ内 `build_drive_service()` を try/except でガード（認証ファイル一時不可・Google一時障害でデーモンが落ちないよう、前回 service で継続）
- **L8**: `test_customer_schedule_12_15` を `next_at.date() == expected_date` に書き直し、4/30/5/31/12/31 の月またぎ・年またぎを追加
- 関連テスト 5 件追加 → 計 214 件 PASS

軽微残5件（L1/L3/L4/L5/L6/L7）と観察6件は別セッション cleanup 候補。

#### 顧客向け報告書

- 5/20 第1報メール文面: Drive API 切断を「電話線が知らないうちに切れていた」の例えで説明
- 5/26 第2報メール文面: PCスリープタイマー停止を「目覚まし時計の電池も止まる」の例えで説明。「事務員様の操作には問題なし、Windows の標準挙動」を明示
- テンプレ化: memory `reference_nontech_customer_report_template.md`

#### 現場の最終稼働状態

```
2026-05-25 14:29:53 [INFO] tamatex - --- 同期サイクル完了: スキャン=60, 同期=3, スキップ=57, エラー=0 ---
2026-05-25 14:29:53 [INFO] tamatex - 次回同期: 2026-05-25 15:00:00（1807秒後）
```
サービス Running、`_sleep_until_event` で次回時刻を待機中。新ロジックでスリープ復帰後も最大60秒で検知して同期発火する状態。

#### バックアップ保全（現場 PC、ロールバック用）
- `C:\nas-googlesync\.venv\Lib\site-packages\tamatex\*.py.bak_20260525_142813`（drive_utils, main, sheets_sync, pdf_sync 各世代）
- `C:\nas-googlesync\.venv\Lib\site-packages\tamatex\main.py.bak_20260525_141321`（スリープ復帰対策デプロイ時）
- 旧セッション分も `*.bak_*` で保持済み

### 未解決の問題・注意点

#### 🔴 顧客から未確証の報告
- **Excel セル日付の反映問題**: 5/25 開始セッションで顧客から「日付が正しく反映されていない」報告。NAS 60 xlsx 全スキャン結果、`m"月"d"日"` 系統が約10万セル + `0"月入荷"`系約1.9万セル と日本式カスタム書式が圧倒的。Sheets コンバータがこれら和文カスタム書式を完全には保持しない仮説が最有力。**仮説確証（Sheets API で実表示取得）と顧客スクショ確認は未実施**。memory `project_customer_excel_date_formats.md`

#### 🟡 顧客とのコミュニケーション残課題
- **第2報メール未送付**: 5/26 作成済みのスリープ復帰対策報告書を顧客送付待ち
- **PC スリープ vs シャットダウン教育**: 顧客は「電源OFF」と認識しているが実態は Modern Standby。今後 Fast Startup 無効化 (`powercfg /h off`) を提案するか検討（現状はコード対策で十分対応）
- **share_with 未設定** (継続): 営業・役員メールを顧客から受領後、config.yaml に追記 → `nssm restart tamatex`
- **`_PoC_test/` Drive 上に残存** (継続)

#### 🟡 残った軽微レビュー指摘（cleanup 候補）
- L1: `drive_utils.with_retry` の到達不能 `assert` 整理
- L3: `e.resp` が None の防御ガード (sheets_sync.py:111, pdf_sync.py:75)
- L4: `move_to_folder` の `removeParents=None` を kwarg で渡している
- L5: `pdf_sync.MediaIoBaseUpload` の `resumable=False` 明示
- L6: `_compute_next_wait` の `HH:MM` パース時の前提コメント
- L7: `conftest.py` autouse fixture の暗黙性
- O系6件: 観察 (型ヒント、関数長、open()コンテキストマネージャ等)

#### プロトタイプ関連（継続）
- **🟠 main マージ未実施**: `feature/proto-cost-calc` は 44 commits ahead of `PCLAB-HUB/tamatex-proto-cost-calc/main`
- **🟠 シナリオ比較 E2E 未自動検証**: claude-in-chrome では aggrid iframe のチェックボックス選択が Streamlit に伝播しない

#### 共通・後続
- インストーラー Phase 2 修正（StringVar スレッドバグ等、`project_installer_known_bugs.md`）
- 顧客への請求・見積書発行
- 帳票生成機能（顧客回答待ち）
- Excel 原価計算の不明点4箇所（顧客確認必要）
- Phase A-01: 品番マスタのスプレッドシート初版整備

### 次に予定しているタスク（優先度順）

**🔴 短期（次回セッション直後にやる）**
0. **【セッション11の残作業】削除伝播 Phase2 + 報告書**: `cleanup_orphans.py`（`docs/superpowers/plans/2026-06-24-nas-delete-propagation.md` に完全コード記載）で既存の溜まった孤立スプレッドを「ドライラン→目視確認→`--apply`」で一掃。顧客向け報告書 `docs/2026-06-24_tamatex機能改善報告書.html/.pdf`（untracked保留）は「price-course＝原価計算アプリ」表記の最終確認後にコミット判断。削除伝播本体は本番デプロイ・実証済み（現場稼働中）。
1. **顧客に第2報メール送付**: スリープ復帰対策の報告（5/26 作成済み文面）
2. **Excel日付反映問題の確証**: Sheets API でサンプル数件取得し「m月d日」表示崩れを確認 → 顧客からのスクショと突合
3. 必要なら日付書式パッチ機能を実装（openpyxl で書き換え or Sheets API でパッチ）

**🟠 中期: プロトタイプ main マージ + 現場デモ**
1. `feature/proto-cost-calc` → `PCLAB-HUB/tamatex-proto-cost-calc/main` に PR/push
2. Streamlit Cloud でビルド成功確認
3. 顧客（社長・役員）への新UIデモ

**🟢 後続課題**
- 軽微レビュー指摘 6件の cleanup
- インストーラー Phase 2 修正
- 顧客への請求・見積書発行
- 帳票生成機能
- プロトタイプ残存課題（40FT テスト、io_fee/storage_fee 設計矛盾、上代 delta 常に ±¥0）

### セッション10 で抽出されたパターン（memory 参照）

- `reference_windows_daemon_sleep_timer.md` — Windows サービスでスリープタイマーが止まる問題と壁時計式 chunked sleep 対策
- `reference_drive_api_resilience_pattern.md` — Drive API TCP死活 + with_retry + サイクル毎service再生成、HttpError.status の型ゆれ防御
- `project_customer_pc_sleep_misconception.md` — 顧客は「電源OFF」認識だが実態は Fast Startup スリープ、診断手順
- `project_customer_excel_date_formats.md` — 顧客 Excel の日付書式調査結果と仮説、スキャンスクリプト保存場所
- `feedback_self_review_with_reviewer_agent.md` — code-reviewer 並列+独立検証、重大/軽微/観察3段階分類
- `reference_nontech_customer_report_template.md` — 非テック顧客向け報告書テンプレ、専門用語マッピング、責任帰属配慮

### 過去のセッション履歴（参考）

セッション9 (2026-04-25〜04-28) — 詳細は git log e3ac5c5 を参照。Drive API 直接アップロード方式へ刷新・PDF同時生成・時刻指定スケジュール・NASフォルダ階層ミラー・Excel保存衝突修正の5大機能拡張。テスト 107→178件。

