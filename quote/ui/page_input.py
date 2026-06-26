"""商品入力ページ."""

from __future__ import annotations

import streamlit as st

from quote.data.defaults import TARIFF_RATES
from quote.engine.models import ProductInput


def _input_key(idx: int, field: str) -> str:
    return f"product_{idx}_{field}"


def render_product_form(idx: int) -> ProductInput | None:
    """商品1点の入力フォームを描画し、ProductInputを返す."""
    with st.expander(f"商品 {idx + 1}", expanded=(idx == 0)):
        col1, col2, col3 = st.columns(3)

        with col1:
            name = st.text_input(
                "品名", key=_input_key(idx, "name"), value=""
            )
            code = st.text_input(
                "試作コード", key=_input_key(idx, "code"), value=str(idx + 1)
            )
            size = st.text_input(
                "個包装サイズ (cm)",
                key=_input_key(idx, "size"),
                value="",
                placeholder="13*9.5*0.6cm",
            )
            weight = st.number_input(
                "重量 (g)",
                key=_input_key(idx, "weight"),
                value=0.0,
                step=0.1,
                format="%.1f",
            )
            packing = st.number_input(
                "梱包入数",
                key=_input_key(idx, "packing"),
                value=1,
                step=1,
                min_value=1,
            )

        with col2:
            fob = st.number_input(
                "FOB単価 (USD)",
                key=_input_key(idx, "fob"),
                value=0.0,
                step=0.01,
                format="%.2f",
            )
            other_proc = st.number_input(
                "その他加工賃 (USD)",
                key=_input_key(idx, "other_proc"),
                value=0.0,
                step=0.01,
                format="%.2f",
            )
            tariff_label = st.selectbox(
                "関税率",
                key=_input_key(idx, "tariff"),
                options=list(TARIFF_RATES.keys()),
            )
            container_load = st.number_input(
                "コンテナ積載量 (枚)",
                key=_input_key(idx, "container_load"),
                value=0.0,
                step=1000.0,
                format="%.0f",
                help="Excelから転記、または空欄で近似計算",
            )

        with col3:
            quote_price = st.number_input(
                "見積売価 (円)",
                key=_input_key(idx, "quote_price"),
                value=0.0,
                step=1.0,
                format="%.0f",
            )
            lot = st.number_input(
                "ロット (色あたり)",
                key=_input_key(idx, "lot"),
                value=0,
                step=1000,
                min_value=0,
            )
            colors = st.number_input(
                "配色数",
                key=_input_key(idx, "colors"),
                value=1,
                step=1,
                min_value=1,
            )
            retail = st.number_input(
                "上代 (円)",
                key=_input_key(idx, "retail"),
                value=0.0,
                step=10.0,
                format="%.0f",
            )

        with st.expander("詳細設定", expanded=False):
            dcol1, dcol2 = st.columns(2)

            with dcol1:
                st.caption("検品・加工費 (円)")
                insp_jpy = st.number_input(
                    "検品 (円)", key=_input_key(idx, "insp_jpy"), value=0.0, format="%.1f"
                )
                pack_jpy = st.number_input(
                    "包装 (円)", key=_input_key(idx, "pack_jpy"), value=0.0, format="%.1f"
                )
                mat_jpy = st.number_input(
                    "資材 (円)", key=_input_key(idx, "mat_jpy"), value=0.0, format="%.1f"
                )

                st.caption("物流 (倉庫→納品先)")
                lio_fee = st.number_input(
                    "入出庫料", key=_input_key(idx, "lio"), value=70.0, format="%.0f"
                )
                lst_months = st.number_input(
                    "保管月数", key=_input_key(idx, "lst_m"), value=1.0, format="%.0f"
                )
                lst_fee = st.number_input(
                    "保管料/月", key=_input_key(idx, "lst_f"), value=150.0, format="%.0f"
                )
                lslip = st.number_input(
                    "伝票手数料", key=_input_key(idx, "lslip"), value=100.0, format="%.0f"
                )
                lfreight = st.number_input(
                    "運賃", key=_input_key(idx, "lfreight"), value=700.0, format="%.0f"
                )

            with dcol2:
                st.caption("売価調整")
                center_fee = st.number_input(
                    "センターフィー",
                    key=_input_key(idx, "cfee"),
                    value=0.0,
                    format="%.3f",
                )
                rebate = st.number_input(
                    "歩引率",
                    key=_input_key(idx, "rebate"),
                    value=0.0,
                    format="%.3f",
                )

        if not name:
            return None

        tariff_val = TARIFF_RATES.get(tariff_label, 0.0)

        return ProductInput(
            product_name=name,
            prototype_code=code,
            package_size_cm=size,
            weight_g=weight,
            packing_quantity=packing,
            fob_usd=fob,
            other_processing_usd=other_proc,
            tariff_rate_override=tariff_val,
            container_load=container_load,
            quote_price=quote_price,
            lot_per_color=lot,
            num_colors=colors,
            retail_price=retail,
            inspection_jpy=insp_jpy,
            packing_jpy=pack_jpy,
            material_jpy=mat_jpy,
            center_fee=center_fee,
            rebate=rebate,
            logistics_io_fee=lio_fee,
            logistics_storage_months=lst_months,
            logistics_storage_fee=lst_fee,
            logistics_slip_fee=lslip,
            logistics_freight=lfreight,
        )


def render_input_page() -> list[ProductInput]:
    """商品入力ページ全体を描画."""
    st.header("商品入力")

    if "num_products" not in st.session_state:
        st.session_state.num_products = 1

    products: list[ProductInput] = []
    for i in range(st.session_state.num_products):
        product = render_product_form(i)
        if product is not None:
            products.append(product)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("＋ 商品を追加"):
            st.session_state.num_products += 1
            st.rerun()
    with col2:
        if st.session_state.num_products > 1 and st.button("－ 最後の商品を削除"):
            st.session_state.num_products -= 1
            st.rerun()

    return products
