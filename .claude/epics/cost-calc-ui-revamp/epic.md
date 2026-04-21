---
name: cost-calc-ui-revamp
status: in-progress
created: 2026-04-21T01:54:31Z
updated: 2026-04-21T03:10:00Z
progress: 90%
prd: .claude/prds/cost-calc-ui-revamp.md
github: https://github.com/PCLAB-HUB/tamatex-proto-cost-calc/issues/1
---

# Epic: cost-calc-ui-revamp

## Overview

現行Streamlit UIを**ダッシュボード中心のプレゼンテーション層**に再構築する。既存計算エンジン（`proto/engine/`、131テスト）には一切触らず、`proto/ui/` のリファクタリングと `proto/storage/` の新設で対応する。主要な新規実装は 3 点:

1. **ダッシュボードビュー** — KPIカード・plotly 為替感度チャート・品目別ランキング
2. **シナリオ永続化層** — SQLite ベースの CRUD リポジトリと dataclass ⇄ JSON 変換ユーティリティ
3. **シナリオ管理UI** — streamlit-aggrid ベースの一覧・比較・CRUD 操作

既存タブのテーブルも `streamlit-aggrid` で刷新して通貨フォーマット・ソート機能を付与する。タブ順を「ダッシュボード → 単品 → ギフト → 比較 → シナリオ → Excel検証」に並び替え、起動時は新ダッシュボードをデフォルト表示にする。

## Architecture Decisions

### AD-1. 計算エンジンの不可侵
- `proto/engine/*.py` と `proto/data/mock_*.py` は**一切変更しない**。
- シナリオ復元時も `ImportCondition` dataclass を経由して既存の計算パスを再利用する。
- 理由: 131テストで担保された計算精度を退行させないため。

### AD-2. シナリオ永続化は SQLite ＋ dataclass ⇄ JSON
- `proto/storage/scenario_repo.py` に CRUD リポジトリ実装。
- `ImportCondition`（ネストされた `ImportExpenses` 含む）を `dataclasses.asdict` でdict化 → `json.dumps` で文字列化して格納。
- 復元時は `json.loads` → dataclass コンストラクタに `**kwargs` で再構築。ネストは手動で `ImportExpenses(**d["import_expenses_single"])` を行う小さな factory を `proto/storage/serializer.py` に配置。
- 代替案（検討済み・不採用）:
  - `pickle` — バージョン互換性・セキュリティ懸念
  - `pydantic` — 新規依存追加はダッシュボード系ライブラリに絞る方針

### AD-3. UIコンポーネントライブラリ選定
- テーブル: `streamlit-aggrid` — 通貨フォーマット・バーチャートセル・選択機能
- チャート: `plotly` — 為替感度曲線に必要な interactivity
- KPIカード: `streamlit-extras` の `metric_cards` + CSS インジェクト最小限
- 理由: 全てメジャーで Streamlit Cloud ビルド実績多数、合計追加ビルド時間 30〜60 秒見込み

### AD-4. タブとコンポーネントの分離
- `proto/app.py` は薄いタブルーター化（各タブは `render_*` を呼ぶだけ）
- 各タブ UI は `proto/ui/<tab_name>.py` に独立モジュール
- 共通UIパーツ（KPIカード・シナリオセレクタ等）は `proto/ui/components/` 配下に切り出す
- 理由: ダッシュボードと比較ビューでKPIカードを再利用、テスト単位を小さく

### AD-5. シナリオDBパスは環境変数で切替可能
- デフォルト: `proto/data/scenarios.db`（gitignore対象）
- 環境変数 `TAMATEX_SCENARIO_DB` で上書き可能
- 理由: 将来の本番環境で別パス指定（永続ボリューム等）に備える

### AD-6. CSS カスタマイズは最小限
- Streamlit 標準コンポーネントで不足する箇所のみ `st.markdown(..., unsafe_allow_html=True)` で対応
- グローバル CSS は `proto/ui/components/styles.py` に集約
- 理由: Streamlit バージョンアップで壊れやすい領域を局所化

## Technical Approach

### Frontend Components (proto/ui/)

**新規**:
- `proto/ui/dashboard.py` — ダッシュボードタブ本体
- `proto/ui/scenarios.py` — シナリオ一覧・CRUD・比較タブ
- `proto/ui/components/kpi_cards.py` — KPIカード（ダッシュボード・比較で再利用）
- `proto/ui/components/aggrid_table.py` — aggrid テーブルファクトリ（通貨フォーマット・列定義の共通化）
- `proto/ui/components/sensitivity_chart.py` — 為替感度 plotly チャート
- `proto/ui/components/styles.py` — CSS 定数

**改修**:
- `proto/ui/sidebar.py` — 輸入経費を折りたたみデフォルト化、「シナリオ保存」ボタン追加、最頻使用項目を上段に
- `proto/ui/section_items.py` / `section_gift.py` / `section_result.py` — 既存 `st.dataframe` を `aggrid_table` に差替え
- `proto/ui/section_basic.py` / `section_verify.py` — 軽微調整（タブ順変更対応のみ）
- `proto/app.py` — タブ順変更、ダッシュボード・シナリオ追加、ルーティング簡素化

### Backend Services (proto/storage/)

**新規**:
- `proto/storage/__init__.py`
- `proto/storage/scenario_repo.py` — SQLite CRUD（list / get / save / update / delete / duplicate）
- `proto/storage/serializer.py` — `ImportCondition` ⇄ JSON 変換

**データモデル**:
```sql
CREATE TABLE scenarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  condition_json TEXT NOT NULL
);
CREATE INDEX idx_scenarios_updated ON scenarios(updated_at DESC);
```

**API**（`ScenarioRepository` クラス）:
- `list_scenarios() -> list[ScenarioMeta]`
- `get_scenario(id: int) -> Scenario`  
- `save_scenario(name: str, cond: ImportCondition) -> int`
- `update_scenario(id: int, name: str | None, cond: ImportCondition | None)`
- `delete_scenario(id: int)`
- `duplicate_scenario(id: int, new_name: str) -> int`
- `scenario_exists(name: str) -> bool`

### Infrastructure

- 依存追加: `streamlit-aggrid>=0.3.4`, `plotly>=5.20`, `streamlit-extras>=0.4`
- `.gitignore` に `proto/data/scenarios.db` と `proto/data/*.db-journal` を追加
- `requirements.txt` 更新
- Streamlit Cloud で追加ライブラリが正常にビルドされることを確認

## Implementation Strategy

### フェーズ構成

**Phase 1: 基盤（タスク 001, 002）**
- 依存追加 + `proto/storage/` 層の実装 + ユニットテスト
- 先行必須（他タスクのブロッカー）

**Phase 2: UI部品（タスク 003, 004, 005 並列）**
- KPIカード・aggridテーブルファクトリ・為替感度チャートコンポーネント
- 3タスクを並列実行可能（ファイル非重複）

**Phase 3: 画面統合（タスク 006, 007 並列 / 008, 009 並列）**
- ダッシュボードタブ（006）とシナリオタブ＋比較（007）を並列実装
- サイドバー改修（008）と既存タブのaggrid化（009）を並列実装

**Phase 4: 統合（タスク 010）**
- `proto/app.py` のタブ順変更 + ルーティング簡素化
- E2E smoke test（起動・主要ボタン動作）
- 既存131テストが全てPASSすることの最終確認

### テスト戦略

- `proto/storage/scenario_repo.py` の CRUD: `pytest` ユニットテスト（tmp_path fixture）
- `proto/storage/serializer.py`: ImportCondition ラウンドトリップテスト
- UIロジックは smoke test のみ（Streamlit のテストは工数対効果が低いため、手動動作確認を重視）
- 既存 `proto/tests/test_calc_*.py` 131件は継続 PASS が必須

### リスク管理

- **R-1**: `streamlit-aggrid` の日本語カラム名・通貨表示の挙動 → タスク003で早期に動作確認
- **R-2**: Streamlit Cloud ビルド時間超過 → 追加ライブラリのビルドログを Phase 1 完了時点で確認
- **R-3**: シナリオ復元時の session_state キー衝突 → サイドバーの widget key プレフィクス規約を維持（現行 `kp` パターンを踏襲）
- **R-4**: aggrid のバージョンアップによる API 変更 → 要件を満たす最小バージョンにピン留め

## Task Breakdown Preview

| # | タスク | 主要ファイル | 並列 | 依存 |
|---|---|---|---|---|
| 001 | 依存追加 & .gitignore 更新 | `requirements.txt`, `.gitignore` | - | - |
| 002 | シナリオ永続化層の実装 (repo + serializer + tests) | `proto/storage/`, tests | - | 001 |
| 003 | KPIカードコンポーネント | `proto/ui/components/kpi_cards.py` | ✅ | 001 |
| 004 | aggridテーブルファクトリ | `proto/ui/components/aggrid_table.py` | ✅ | 001 |
| 005 | 為替感度チャートコンポーネント | `proto/ui/components/sensitivity_chart.py` | ✅ | 001 |
| 006 | ダッシュボードタブ実装 | `proto/ui/dashboard.py` | ✅ | 003, 004, 005 |
| 007 | シナリオタブ＋比較ビュー実装 | `proto/ui/scenarios.py` | ✅ | 002, 003, 004 |
| 008 | サイドバー改修（保存ボタン・折りたたみ） | `proto/ui/sidebar.py` | ✅ | 002 |
| 009 | 既存タブの aggrid 化 | `section_items.py` / `section_gift.py` / `section_result.py` | ✅ | 004 |
| 010 | app.py 統合 + E2E smoke test | `proto/app.py`, `proto/tests/test_smoke.py` | - | 006, 007, 008, 009 |

**10タスク、Phase 2-3 で最大 4〜5 タスクを並列実行可能。**

## Dependencies

### 外部
- `streamlit-aggrid>=0.3.4` — aggrid 採用の基盤
- `plotly>=5.20` — 為替感度チャート
- `streamlit-extras>=0.4` — metric_cards 等

### 内部（既存・変更なし）
- `proto/engine/*` — 計算エンジン（不可侵）
- `proto/data/mock_*.py` — モックデータ（不可侵）
- `proto/engine/models.py` の `ImportCondition`, `ImportExpenses` dataclass — シリアライズ対象

### 前提
- Streamlit Cloud デプロイ環境で追加3ライブラリがビルド可能であること（Phase 1 完了時に確認）
- 現場導入中の tamatex 本体（master）作業に影響を与えないこと（`feature/proto-cost-calc` ブランチに完全隔離）

## Success Criteria (Technical)

- [ ] 既存 131 テスト が全て PASS（退行なし）
- [ ] 新規追加テストが全て PASS（シナリオ repo + serializer のユニットテスト）
- [ ] アプリ起動時にダッシュボードタブがデフォルト表示される
- [ ] シナリオを保存・読込・複製・削除・リネームできる
- [ ] 2シナリオを選択して横並び比較ビューに遷移できる
- [ ] 為替感度チャートが plotly でインタラクティブに動作する
- [ ] Streamlit Cloud（PCLAB-HUB/tamatex-proto-cost-calc）にデプロイしてエラーなく起動する
- [ ] `proto/ui/` 内に新規ファイル追加以外の破壊的変更がない（既存 render_* 関数の呼び出しシグネチャ互換維持）

## Estimated Effort

- **総工数**: 3〜5 人日（専念時）
- **実時間**: 並列実行を活用すれば 2〜3 日で完了可能
- **クリティカルパス**: 001 (0.5h) → 002 (4h) → 007 (6h) → 010 (2h) ≒ 12.5h
- **並列可能な最大ワークロード**: Phase 2 で 3タスク同時（003/004/005 各 2-3h）、Phase 3 で 4タスク同時（006/007/008/009 各 3-6h）

### タスク別見積
| タスク | 見積 |
|---|---|
| 001 | 0.5h |
| 002 | 4h |
| 003 | 2h |
| 004 | 2.5h |
| 005 | 2h |
| 006 | 4h |
| 007 | 6h |
| 008 | 3h |
| 009 | 3h |
| 010 | 2h |
| **合計** | **29h** |

### リソース要件
- Python/Streamlit スキル: 中級以上
- 並列実行エージェント: Phase 2-3 で 3〜4 並列が効果的
- 人間レビュー: Phase 1 完了時（シナリオスキーマ） + Phase 4 完了時（UX 最終確認）

## Tasks Created

- [x] #2 (2.md) - 依存ライブラリ追加と .gitignore 更新 (parallel: false, 0.5h)
- [x] #3 (3.md) - シナリオ永続化層の実装（SQLite + dataclass ⇄ JSON） (parallel: true, 4h)
- [x] #4 (4.md) - KPIカードコンポーネントの実装 (parallel: true, 2h)
- [x] #5 (5.md) - aggridテーブルファクトリの実装 (parallel: true, 2.5h)
- [x] #6 (6.md) - 為替感度チャートコンポーネントの実装 (parallel: true, 2h)
- [x] #7 (7.md) - ダッシュボードタブの実装 (parallel: true, 4h)
- [x] #8 (8.md) - シナリオタブと比較ビューの実装 (parallel: true, 6h)
- [x] #9 (9.md) - サイドバー改修（保存ボタン・折りたたみ整理） (parallel: true, 3h)
- [x] #10 (10.md) - 既存タブのaggrid化（単品・ギフト・比較） (parallel: true, 3h)
- [ ] #11 (11.md) - app.py統合とsmoke test追加 (parallel: false, 2h)

Total tasks: 10
Parallel tasks: 8
Sequential tasks: 2 (#2 as foundation, #11 as integration)
Estimated total effort: 29 hours
Critical path: #2 → #3 → #8 → #11 ≒ 12.5h
Max parallel workload: 4 tasks simultaneously in Phase 3 (#7/#8/#9/#10)
