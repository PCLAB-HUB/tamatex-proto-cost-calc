# GitHub Issue Mapping

**Epic**: cost-calc-ui-revamp
**Repository**: [PCLAB-HUB/tamatex-proto-cost-calc](https://github.com/PCLAB-HUB/tamatex-proto-cost-calc)
**Synced**: 2026-04-21T02:19:25Z

## Epic Issue

- #1 - Epic: cost-calc-ui-revamp
  - URL: https://github.com/PCLAB-HUB/tamatex-proto-cost-calc/issues/1
  - Labels: `epic`, `epic:cost-calc-ui-revamp`, `feature`

## Task Sub-Issues

| Task File | GitHub Issue | Title | Depends On |
|---|---|---|---|
| 2.md | [#2](https://github.com/PCLAB-HUB/tamatex-proto-cost-calc/issues/2) | 依存ライブラリ追加と .gitignore 更新 | — |
| 3.md | [#3](https://github.com/PCLAB-HUB/tamatex-proto-cost-calc/issues/3) | シナリオ永続化層の実装（SQLite + dataclass ⇄ JSON） | #2 |
| 4.md | [#4](https://github.com/PCLAB-HUB/tamatex-proto-cost-calc/issues/4) | KPIカードコンポーネントの実装 | #2 |
| 5.md | [#5](https://github.com/PCLAB-HUB/tamatex-proto-cost-calc/issues/5) | aggridテーブルファクトリの実装 | #2 |
| 6.md | [#6](https://github.com/PCLAB-HUB/tamatex-proto-cost-calc/issues/6) | 為替感度チャートコンポーネントの実装 | #2 |
| 7.md | [#7](https://github.com/PCLAB-HUB/tamatex-proto-cost-calc/issues/7) | ダッシュボードタブの実装 | #4, #5, #6 |
| 8.md | [#8](https://github.com/PCLAB-HUB/tamatex-proto-cost-calc/issues/8) | シナリオタブと比較ビューの実装 | #3, #4, #5 |
| 9.md | [#9](https://github.com/PCLAB-HUB/tamatex-proto-cost-calc/issues/9) | サイドバー改修（保存ボタン・折りたたみ整理） | #3 |
| 10.md | [#10](https://github.com/PCLAB-HUB/tamatex-proto-cost-calc/issues/10) | 既存タブのaggrid化（単品・ギフト・比較） | #5 |
| 11.md | [#11](https://github.com/PCLAB-HUB/tamatex-proto-cost-calc/issues/11) | app.py統合とsmoke test追加 | #7, #8, #9, #10 |

All tasks are linked as sub-issues of Epic #1 via the `gh-sub-issue` extension.

## Labels Created

- `epic` (#5319e7) — Epic tracker
- `epic:cost-calc-ui-revamp` (#1d76db) — UI大改修エピック
- `feature` (#a2eeef) — New feature
- `task` (#c2e0c6) — Task under epic

## Notes

- **Worktree convention**: 開発は `feature/proto-cost-calc` ブランチ（既存 worktree: `.worktrees/proto-cost-calc/`）で継続。CCPM標準の `epic/<name>` ブランチは作成しない（プロトタイプの integration branch が feature/proto-cost-calc のため）
- **Streamlit Cloud デプロイ**: タスク #11 完了時に `PCLAB-HUB/tamatex-proto-cost-calc` の main ブランチへ反映（別途 PR または直接 push で対応）
