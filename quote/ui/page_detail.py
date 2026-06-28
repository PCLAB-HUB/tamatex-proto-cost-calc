"""② 見積もり明細ページ — ヘッダー + 商品ラインアイテムテーブル + 合計."""

from __future__ import annotations

import html
import json
from dataclasses import asdict

import streamlit as st

from quote.engine.calc import calculate
from quote.engine.models import GlobalParams, ProductInput, QuoteResult
from quote.storage.db import get_quote, list_customers, list_staff, save_quote
from quote.ui.pdf_export import generate_quote_html


def _fmt_jpy(v: float) -> str:
    return f"¥{v:,.0f}"


def _fmt_pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def _profit_color(rate: float) -> str:
    if rate >= 0.25:
        return "#0D904F"
    if rate >= 0.15:
        return "#1B73E8"
    if rate >= 0.05:
        return "#E37400"
    return "#D93025"


def _load_products_from_quote(quote: dict) -> list[ProductInput]:
    from dataclasses import fields as dc_fields
    products = []
    for item in quote.get("items", []):
        valid_fields = {f.name for f in dc_fields(ProductInput)}
        filtered = {k: v for k, v in item.items() if k in valid_fields}
        products.append(ProductInput(**filtered))
    return products


def render_detail_page(quote_id: int, params: GlobalParams) -> None:
    """見積もり明細ページを描画."""
    quote = get_quote(quote_id)
    if not quote:
        st.error("見積もりが見つかりません。")
        return

    # ヘッダー
    qnum = html.escape(str(quote["quote_number"]))
    created = html.escape(str(quote["created_at"])[:10])
    cname = html.escape(str(quote.get("customer_name") or "-"))
    sname = html.escape(str(quote.get("staff_name") or "-"))
    title = html.escape(str(quote.get("title") or "(無題)"))
    status_map = {
        "draft": "📝 下書き",
        "submitted": "📤 提出済",
        "approved": "✅ 承認済",
    }
    status_label = html.escape(
        str(status_map.get(quote["status"], quote["status"]))
    )
    with st.container(border=True):
        h1, h2, h3 = st.columns([2, 2, 2])
        with h1:
            st.markdown(
                f"**{qnum}**<br>"
                f"<span style='color:#5F6368;'>作成: {created}</span>",
                unsafe_allow_html=True,
            )
        with h2:
            st.markdown(
                f"🏢 {cname}<br>"
                f"👤 {sname}",
                unsafe_allow_html=True,
            )
        with h3:
            st.markdown(
                f"{status_label}<br>"
                f"<span style='color:#5F6368;'>"
                f"{title}</span>",
                unsafe_allow_html=True,
            )

    if quote.get("notes"):
        st.caption(f"備考: {quote['notes']}")

    # サイドバー params と保存済 params の差分検知（乖離防止）
    stored_params = quote.get("params") or {}
    current_params_dict = asdict(params)
    params_dirty = current_params_dict != stored_params
    if params_dirty:
        col_warn, col_btn = st.columns([4, 1])
        with col_warn:
            st.warning(
                "⚠️ サイドバーのパラメータがこの見積もりの保存値と異なります。"
                "保存せずに閉じると次回開いた時に乖離します。"
            )
        with col_btn:
            if st.button("💾 パラメータを保存", use_container_width=True):
                save_quote(
                    customer_id=quote["customer_id"],
                    staff_id=quote["staff_id"],
                    title=quote.get("title") or "",
                    products=_load_products_from_quote(quote),
                    params=params,
                    notes=quote.get("notes") or "",
                    quote_id=quote_id,
                )
                st.success("保存しました。")
                st.rerun()

    # 商品を計算
    products = _load_products_from_quote(quote)
    results: list[tuple[ProductInput, QuoteResult]] = []
    for p in products:
        results.append((p, calculate(p, params)))

    # 明細テーブル
    st.markdown("### 明細")
    if not results:
        st.info("商品がまだ追加されていません。")
    else:
        header_cols = st.columns([0.5, 2.5, 1, 1, 1.5, 1, 1])
        headers = ["No", "品名", "見積売価", "ロット", "売上金額", "粗利率", "操作"]
        for col, h in zip(header_cols, headers):
            col.markdown(
                f"<div style='font-size:0.8rem;color:#5F6368;font-weight:600;'>{h}</div>",
                unsafe_allow_html=True,
            )

        total_sales = 0.0
        total_profit = 0.0

        for i, (p, r) in enumerate(results):
            pr = r.pricing_with_amort
            total_sales += pr.sales_amount
            total_profit += pr.gross_profit_total

            profit_color = _profit_color(pr.gross_profit_rate)
            cols = st.columns([0.5, 2.5, 1, 1, 1.5, 1, 1])
            with cols[0]:
                st.markdown(f"**{i + 1}**")
            with cols[1]:
                st.markdown(f"**{p.product_name}**")
            with cols[2]:
                st.markdown(_fmt_jpy(pr.quote_price))
            with cols[3]:
                st.markdown(f"{pr.lot:,}")
            with cols[4]:
                st.markdown(f"**{_fmt_jpy(pr.sales_amount)}**")
            with cols[5]:
                st.markdown(
                    f"<span style='color:{profit_color};font-weight:600;'>"
                    f"{_fmt_pct(pr.gross_profit_rate)}</span>",
                    unsafe_allow_html=True,
                )
            with cols[6]:
                if st.button("計算シート", key=f"detail_open_{i}"):
                    st.session_state.page = "product"
                    st.session_state.product_index = i
                    st.rerun()

        # 合計
        st.markdown("---")
        avg_rate = total_profit / total_sales if total_sales > 0 else 0
        avg_color = _profit_color(avg_rate)
        tc = st.columns(3)
        tc[0].markdown(
            f'<div style="background:#FFFFFF;border:1px solid #DADCE0;border-radius:8px;'
            f'padding:16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.08);">'
            f'<div style="font-size:0.8rem;color:#5F6368;">売上合計</div>'
            f'<div style="font-size:1.5rem;font-weight:600;">{_fmt_jpy(total_sales)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        tc[1].markdown(
            f'<div style="background:#FFFFFF;border:1px solid #DADCE0;border-radius:8px;'
            f'padding:16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.08);">'
            f'<div style="font-size:0.8rem;color:#5F6368;">粗利合計</div>'
            f'<div style="font-size:1.5rem;font-weight:600;color:{avg_color};">'
            f'{_fmt_jpy(total_profit)}</div></div>',
            unsafe_allow_html=True,
        )
        tc[2].markdown(
            f'<div style="background:#FFFFFF;border:1px solid #DADCE0;border-radius:8px;'
            f'padding:16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.08);">'
            f'<div style="font-size:0.8rem;color:#5F6368;">平均粗利率</div>'
            f'<div style="font-size:1.5rem;font-weight:600;color:{avg_color};">'
            f'{_fmt_pct(avg_rate)}</div></div>',
            unsafe_allow_html=True,
        )

    # アクションボタン
    st.markdown("")
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        if st.button("＋ 商品追加", type="primary", use_container_width=True):
            st.session_state.page = "product"
            st.session_state.product_index = -1
            st.rerun()
    with b2:
        if st.button("📝 見積もり情報を編集", use_container_width=True):
            st.session_state.page = "edit_header"
            st.rerun()
    with b3:
        if st.button("← 一覧に戻る", use_container_width=True):
            st.session_state.page = "list"
            for k in list(st.session_state.keys()):
                if k.startswith("sp_") or k.startswith("card_"):
                    del st.session_state[k]
            st.rerun()
    with b4:
        html_bytes = generate_quote_html(quote, results, params).encode("utf-8")
        st.download_button(
            label="📄 見積書出力",
            data=html_bytes,
            file_name=f"{quote.get('quote_number', 'quote')}.html",
            mime="text/html",
            use_container_width=True,
        )
