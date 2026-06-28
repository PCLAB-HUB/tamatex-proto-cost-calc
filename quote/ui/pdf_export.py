"""見積書 HTML 生成 — ブラウザ印刷→PDF 保存用."""

from __future__ import annotations

from datetime import date
from html import escape as _esc

from quote.engine.models import GlobalParams, ProductInput, QuoteResult


def _fmt_jpy(v: float) -> str:
    return f"¥{v:,.0f}"


def _fmt_pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def generate_quote_html(
    quote: dict,
    results: list[tuple[ProductInput, QuoteResult]],
    params: GlobalParams,
) -> str:
    """見積書 HTML 文字列を生成する."""
    today = date.today().isoformat()
    quote_number = _esc(quote.get("quote_number", ""))
    customer_name = _esc(quote.get("customer_name") or "")
    staff_name = _esc(quote.get("staff_name") or "")
    title = _esc(quote.get("title") or "")
    created_at = _esc((quote.get("created_at") or "")[:10])
    # 注: notes は社内メモ（顧客非表示）として入力されるため、
    # 顧客向け HTML には出力しない。

    rows_html = ""
    total_sales = 0.0
    total_profit = 0.0
    for i, (p, r) in enumerate(results):
        pr = r.pricing_with_amort
        total_sales += pr.sales_amount
        total_profit += pr.gross_profit_total
        rows_html += (
            f"<tr>"
            f"<td class='center'>{i + 1}</td>"
            f"<td>{_esc(p.product_name)}</td>"
            f"<td class='right'>{_fmt_jpy(pr.quote_price)}</td>"
            f"<td class='right'>{pr.lot:,}</td>"
            f"<td class='right'>{_fmt_jpy(pr.sales_amount)}</td>"
            f"<td class='right'>{_fmt_pct(pr.gross_profit_rate)}</td>"
            f"</tr>\n"
        )

    avg_rate = total_profit / total_sales if total_sales > 0 else 0.0

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>御見積書 {quote_number}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: "Hiragino Kaku Gothic ProN", "Meiryo", sans-serif;
    font-size: 11pt;
    color: #111;
    background: #fff;
    padding: 20mm 15mm;
  }}
  h1 {{
    text-align: center;
    font-size: 20pt;
    font-weight: bold;
    letter-spacing: 0.2em;
    margin-bottom: 16px;
  }}
  .meta-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 20px;
  }}
  .meta-block dt {{
    font-size: 8pt;
    color: #555;
    margin-bottom: 2px;
  }}
  .meta-block dd {{
    font-size: 11pt;
    font-weight: 500;
    border-bottom: 1px solid #ccc;
    padding-bottom: 3px;
  }}
  .section-title {{
    font-size: 10pt;
    font-weight: 600;
    color: #333;
    border-left: 3px solid #1B73E8;
    padding-left: 6px;
    margin: 18px 0 8px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 10pt;
  }}
  thead th {{
    background: #F0F4FF;
    border: 1px solid #B0BEC5;
    padding: 6px 8px;
    font-weight: 600;
    text-align: center;
  }}
  tbody td {{
    border: 1px solid #CFD8DC;
    padding: 5px 8px;
    vertical-align: middle;
  }}
  tbody tr:nth-child(even) td {{ background: #FAFAFA; }}
  tfoot td {{
    border: 1px solid #B0BEC5;
    padding: 6px 8px;
    font-weight: 600;
    background: #ECEFF1;
  }}
  .center {{ text-align: center; }}
  .right  {{ text-align: right; }}
  .total-row td {{ background: #E8F0FE !important; }}
  .footer-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-top: 20px;
    font-size: 10pt;
  }}
  .footer-block dt {{
    font-size: 8pt;
    color: #555;
    margin-bottom: 2px;
  }}
  .footer-block dd {{
    border-bottom: 1px solid #ccc;
    padding-bottom: 3px;
    min-height: 22px;
  }}
  @media print {{
    body {{ padding: 10mm 12mm; }}
    @page {{ size: A4 portrait; margin: 10mm 12mm; }}
    .no-print {{ display: none; }}
  }}
</style>
</head>
<body>

<div class="no-print" style="text-align:right;margin-bottom:12px;">
  <button onclick="window.print()" style="padding:6px 18px;font-size:11pt;cursor:pointer;">
    印刷 / PDF保存
  </button>
</div>

<h1>御 見 積 書</h1>

<div class="meta-grid">
  <dl class="meta-block">
    <dt>顧客名</dt>
    <dd>{customer_name or "&nbsp;"}</dd>
  </dl>
  <dl class="meta-block">
    <dt>見積番号</dt>
    <dd>{quote_number}</dd>
  </dl>
  <dl class="meta-block">
    <dt>件名</dt>
    <dd>{title or "&nbsp;"}</dd>
  </dl>
  <dl class="meta-block">
    <dt>作成日</dt>
    <dd>{created_at or today}</dd>
  </dl>
  <dl class="meta-block">
    <dt>担当者</dt>
    <dd>{staff_name or "&nbsp;"}</dd>
  </dl>
  <dl class="meta-block">
    <dt>会社名</dt>
    <dd>&nbsp;</dd>
  </dl>
</div>

<p class="section-title">明細</p>
<table>
  <thead>
    <tr>
      <th style="width:4%">No</th>
      <th style="width:34%">品名</th>
      <th style="width:14%">見積売価</th>
      <th style="width:10%">ロット</th>
      <th style="width:16%">売上金額</th>
      <th style="width:12%">粗利率</th>
    </tr>
  </thead>
  <tbody>
    {rows_html if rows_html else '<tr><td colspan="6" class="center" style="color:#888;padding:12px;">商品なし</td></tr>'}
  </tbody>
  <tfoot>
    <tr class="total-row">
      <td class="center" colspan="4"><strong>合計</strong></td>
      <td class="right"><strong>{_fmt_jpy(total_sales)}</strong></td>
      <td class="right"><strong>{_fmt_pct(avg_rate)}</strong></td>
    </tr>
    <tr>
      <td colspan="4" style="font-size:9pt;color:#555;">粗利合計</td>
      <td class="right">{_fmt_jpy(total_profit)}</td>
      <td></td>
    </tr>
  </tfoot>
</table>

<div class="footer-grid">
  <dl class="footer-block">
    <dt>有効期限</dt>
    <dd>&nbsp;</dd>
  </dl>
  <dl class="footer-block">
    <dt>備考</dt>
    <dd>&nbsp;</dd>
  </dl>
</div>

</body>
</html>"""
    return html
