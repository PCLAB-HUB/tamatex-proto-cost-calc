# Task Plan: 原価計算書見積もり（プロト） プロトタイプ新規構築

## Goal
原価計算書参考資料.xlsxの数式ロジックを忠実に再現し、週次ミーティングでクライアントが操作できるStreamlitプロトタイプを構築する。

## Current Phase
Phase 5 (検証中)

## 設計判断

### 前提
- 前回のタオル原価計算プロトタイプ(proto/)のコードは取り込まない（新規構築）
- Excelの154列中、手動入力は約20列、残りは自動計算
- クライアントが実際に触れるデモを目指す（毎週ミーティングでフィードバック）
- 配置先: `quote/` ディレクトリ（proto/と分離）

### アーキテクチャ
```
quote/
├── app.py                # Streamlitエントリポイント
├── engine/
│   ├── models.py         # dataclass定義（入力・条件・結果）
│   ├── calc.py           # 原価計算ロジック（Excelの数式をPythonに変換）
│   └── container.py      # コンテナ積載量計算
├── ui/
│   ├── page_input.py     # 商品入力ページ
│   ├── page_result.py    # 計算結果・粗利表示ページ
│   ├── sidebar.py        # 固定パラメータ設定（為替・経費等）
│   └── components.py     # 共通UIコンポーネント
├── data/
│   └── defaults.py       # Excelから抽出したデフォルト値
└── tests/
    ├── test_calc.py       # 計算ロジックの検証（Excel実値と突合）
    └── test_container.py  # コンテナ積載計算の検証
```

### 計算フロー（Excel数式の対応表）
```
入力: FOB単価(S) + 加工賃(T) + ロス率(U) + 刺繍(W×X) + 型代(Y)
  → Z列: FOB調整後 = (S+T)*(1+U)+V+(W*X/1000)+Y/DM
  → AM列: C&F = Z*為替 + 検品加工(3通貨) + 海外運賃按分
  → AO列: CIF = C&F*(1+保険率)
  → AQ列: 関税 = CIF*関税率
  → AR列: 仕入値 = CIF+関税

並列加算:
  + BE列: コンテナ経費/枚 = 11項目合計÷積載量
  + BG列: B品ロス = (仕入値+経費)*ロス率
  + BT列: 副資材経費 = (9項目合計)*(1+関税率)*(1+ロス率)
  + CK列: 償却経費/枚 = 14項目合計÷ロット
  + CU列: 物流経費/枚 = (ダンボール+入出庫+保管*月+手数料+運賃)/入数
  + DD列: 加工経費/枚 = 加工費+資材+(ケース系経費)/入数

  → DE列: 製品原価 = 上記すべての合計
  → DG列: 試算売価 = ROUNDUP(原価*(1+マージン))
  → DN列: 歩積込売価 = 見積売価/(1-センターフィー-歩引)
  → DS列: 粗利額 = 見積売価 - 原価
  → DT列: 粗利率 = 粗利額/見積売価
  → DR列: 売上金額 = ロット×歩積込売価

第2価格体系（償却別途）:
  → DW列: 原価(償却除) = DE - CK
  → 以降同様の売価・粗利計算
```

## Phases

### Phase 1: データモデル & デフォルト値抽出
- [x] models.py — 入力データ・条件パラメータ・計算結果のdataclass定義
- [x] defaults.py — Excel Row8-9の実値からデフォルト値を抽出
- [x] container.py — コンテナ積載量計算ロジック（旧Excelの計算シート参照）
- **Status:** complete

### Phase 2: 計算エンジン（コアロジック）
- [x] calc.py — Excel数式をPythonに忠実変換（Z→AM→AO→AR→DE→DG→DS→DT）
- [x] test_calc.py — Excel Row9の実値（DE9=52.64, DG9=64, DS9=11.36, DT9=17.8%）と突合 → 15/15 PASSED
- [x] 第2価格体系（償却別途）の計算も実装
- **Status:** complete

### Phase 3: UI — 入力フォーム & サイドバー
- [x] sidebar.py — 固定パラメータ（為替152円、運賃240USD、経費11項目、ロス率、マージン等）
- [x] page_input.py — 商品情報入力フォーム（品名、サイズ、重量、FOB、入数、検品加工費等）
- [x] 複数商品の追加・削除
- **Status:** complete

### Phase 4: UI — 結果表示 & デモ仕上げ
- [x] page_result.py — 原価内訳、売価、粗利をカード＋テーブル表示
- [x] 2つの価格体系（償却込み/別途）のタブ切替
- [x] app.py — 単一ページ構成（入力→結果をスクロールで連続表示）
- **Status:** complete

### Phase 5: 検証 & デモ準備
- [x] Excel Row 9（ダイカットメモ）の計算結果と突合 → 全値一致
- [x] UIの操作性確認（ブラウザで実操作・スクリーンショット確認済み）
- [ ] 既知の未解決事項を整理（R列の計算、選択肢マスタ等）
- **Status:** in_progress

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| (なし) | - | - |

## Files Created/Modified
| Phase | Files | Action |
|-------|-------|--------|
| 1 | quote/engine/models.py | 作成: dataclass定義 |
| 1 | quote/data/defaults.py | 作成: デフォルト値・サンプル |
| 1 | quote/engine/container.py | 作成: コンテナ積載近似計算 |
| 2 | quote/engine/calc.py | 作成: 計算エンジン（20関数） |
| 2 | quote/tests/test_calc.py | 作成: 15テスト（全PASS） |
| 3 | quote/ui/sidebar.py | 作成: 固定パラメータUI |
| 3 | quote/ui/page_input.py | 作成: 商品入力フォーム |
| 4 | quote/ui/page_result.py | 作成: 結果表示ページ |
| 4 | quote/app.py | 作成: Streamlitエントリ |
