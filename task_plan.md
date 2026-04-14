# Task Plan: 原価計算プロトタイプ

## Goal
Excelの「ひな形」シートの全計算ロジックをPython関数化し、モック品番データで実動作するStreamlitデモアプリを構築する。

## Status: Phase 1完了 — Phase 2実装待ち

## Phases

### Phase 1: 計算エンジン + テスト ✅ 完了 (0d9e01b)
- [x] 1-1: データモデル定義 (engine/models.py)
- [x] 1-2: モックデータ作成 (data/mock_*.py)
- [x] 1-3: 単品原価計算実装 (engine/calc_single.py)
- [x] 1-4: ギフトセット計算実装 (engine/calc_gift.py)
- [x] 1-5: 輸入経費・物流計算実装 (engine/calc_import.py)
- [x] 1-6: 集計計算実装 (engine/calc_summary.py)
- [x] 1-7: テストスイート作成 (tests/test_*.py) — 131件全PASS

### Phase 2: Streamlit UI
- [ ] 2-1: サイドバー (ui/sidebar.py)
- [ ] 2-2: 基本情報セクション (ui/section_basic.py)
- [ ] 2-3: 単品一覧 (ui/section_items.py)
- [ ] 2-4: ギフト構成 (ui/section_gift.py)
- [ ] 2-5: 計算結果表示 (ui/section_result.py)
- [ ] 2-6: 全セット比較一覧表
- [ ] 2-7: Excel検証セクション (ui/section_verify.py)
- [ ] 2-8: メインapp.py統合

### Phase 3: 検証・仕上げ
- [ ] 3-1: 全テスト実行
- [ ] 3-2: Excel完全照合
- [ ] 3-3: UI操作性確認
- [ ] 3-4: デモ手順書作成

## Key Decisions
- 技術: Streamlit（計算エンジンは本番移植可能）
- 検証基準: Excel値と±0.01円以内の一致
- 40FTの#REF!: BA20(=3000)を使用（顧客確認事項）
- 不明点4箇所: 現行Excel値をそのまま使い、確認リスト添付

## Reference
- 計画書: docs/2026-04-15_原価計算プロトタイプ計画書.md
- Excel: docs/営業_原価計算（輸入）.xlsx
- 会議資料: docs/04-14 会議_*.md
