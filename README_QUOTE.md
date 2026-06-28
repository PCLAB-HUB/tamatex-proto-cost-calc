# 原価計算書見積もり (プロト) — Streamlit Cloud デプロイ手順

## エントリーポイント

- **Main file path**: `quote/app_card.py`
- **Branch**: `main`
- **Python version**: 3.11 以降（Streamlit Cloud のデフォルトで OK）

## 依存

`requirements.txt` に最小構成（streamlit / pandas / openpyxl）。

## 初期データ

`quote_data.db` をリポジトリに含めて配布。94 商品 / 8 見積もりが初期データとして読み込まれる。
**Streamlit Cloud のコンテナは揮発性**のため、クライアントが入力した編集はコンテナ再起動でリセットされる。
フィードバック収集用途専用で、永続データ保持には別途 Supabase / Neon Postgres などのバックエンドが必要。

## Streamlit Cloud 設定変更手順

既存アプリ `tamatex-proto-cost-calc-smtuk3y4wpamumnzmxib2p.streamlit.app` を流用する場合:

1. https://share.streamlit.io にログイン
2. 対象アプリの「⋮」→「Settings」→「General」
3. **Main file path** を `quote/app_card.py` に変更
4. Save → Reboot

新規アプリとして作成する場合:

1. https://share.streamlit.io → 「New app」
2. Repository: `PCLAB-HUB/tamatex-proto-cost-calc`
3. Branch: `main`
4. Main file path: `quote/app_card.py`
5. Deploy

## ローカル動作確認

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run quote/app_card.py
```
