# Progress Log

## 2026-04-15 セッション1
- [x] Excel「ひな形」シートの全セル・全計算式を解析
- [x] 補助シート（物流費・関税、コンテナ積載量、生地コスト、副資材、マスタ）を解析
- [x] 計算チェーンの特定（単品FOB → ギフトFOB → C&F → CIF → 関税 → 輸入経費 → 物流 → 製造原価 → 見積単価）
- [x] ウェブアプリ実装可能性の判定: 可能
- [x] 20FTと40FTの差異を特定（パラメータ差異、40FTの#REF!エラー、式の微妙な違い）
- [x] 検証用テストケース作成（単品3品目 + ギフト12パターンの全中間値）
- [x] 実装計画書の作成 → docs/2026-04-15_原価計算プロトタイプ計画書.md
- [x] Phase 1 実装完了（2026-04-15 セッション2）

## 2026-04-15 セッション2
- [x] worktree作成: `.worktrees/proto-cost-calc` (feature/proto-cost-calc)
- [x] 1-1: データモデル定義 (engine/models.py) — 8種のdataclass
- [x] 1-2: モックデータ作成 (data/mock_*.py) — Excel実値から転記
- [x] 1-5: 輸入経費・物流共通計算 (engine/calc_import.py)
- [x] 1-3: 単品原価計算 (engine/calc_single.py) — 26テストPASS
- [x] Excel実値との乖離発見・修正（輸入経費パラメータ差異、CA式のBO=CIC(USD)等）
- [x] ImportExpensesモデル追加、単品/ギフト別輸入経費対応
- [x] 1-4: ギフトセット計算 (engine/calc_gift.py) — 101テストPASS
- [x] 1-6: 集計計算 (engine/calc_summary.py) — 4テストPASS
- [x] 1-7: 全テスト確認 — 238件(既存107+プロト131)全PASS
- [x] コミット: 0d9e01b
- [ ] Phase 2 Streamlit UI実装（次セッション）
