"""商品入力ページ — セクション分け + プルダウン対応."""

from __future__ import annotations

import streamlit as st

from quote.data.defaults import (
    CONTAINER_FT,
    DELIVERY_TO,
    METHODS,
    PORTS,
    SHIP_TO,
    SUPPLIERS,
    TARIFF_RATES,
)
from quote.engine.models import ProductInput


def _key(idx: int, field: str) -> str:
    return f"p{idx}_{field}"


def _render_product(idx: int) -> ProductInput | None:
    """商品1点の入力フォーム."""
    col_title, col_delete = st.columns([6, 1])
    with col_title:
        name = st.text_input(
            "品名 *", key=_key(idx, "name"), placeholder="例: ダイカットメモ"
        )
    with col_delete:
        st.write("")
        if idx > 0:
            if st.button("🗑", key=_key(idx, "del"), help="この商品を削除"):
                st.session_state.num_products -= 1
                st.rerun()

    if not name:
        st.caption("品名を入力すると計算結果が表示されます。")
        return None

    # ── 取引条件 ──
    st.markdown("##### 取引条件")
    tc1, tc2, tc3, tc4 = st.columns(4)
    with tc1:
        supplier = st.selectbox("仕入先", SUPPLIERS, key=_key(idx, "supplier"))
    with tc2:
        port = st.selectbox("揚地", PORTS, key=_key(idx, "port"))
    with tc3:
        delivery = st.selectbox("納入先", DELIVERY_TO, key=_key(idx, "delivery"))
    with tc4:
        ship = st.selectbox("出荷先", SHIP_TO, key=_key(idx, "ship"))

    tc5, tc6, tc7, tc8 = st.columns(4)
    with tc5:
        container_ft = st.selectbox(
            "コンテナ", CONTAINER_FT, key=_key(idx, "ft"), format_func=lambda x: f"{x}FT"
        )
    with tc6:
        method = st.selectbox("手法", METHODS, key=_key(idx, "method"))
    with tc7:
        tariff_label = st.selectbox("関税率", list(TARIFF_RATES.keys()), key=_key(idx, "tariff"))
    with tc8:
        code = st.text_input("試作コード", key=_key(idx, "code"), value=str(idx + 1))

    # ── 製品仕様 & FOB ──
    st.markdown("##### 製品仕様・FOB")
    sp1, sp2, sp3, sp4 = st.columns(4)
    with sp1:
        size_cm = st.text_input(
            "個包装サイズ (cm)", key=_key(idx, "size"), placeholder="13*9.5*0.6"
        )
    with sp2:
        weight = st.number_input("重量 (g)", key=_key(idx, "wt"), value=0.0, step=0.1, format="%.1f")
    with sp3:
        packing = st.number_input("梱包入数", key=_key(idx, "pack"), value=1, step=1, min_value=1)
    with sp4:
        container_load = st.number_input(
            "コンテナ積載量",
            key=_key(idx, "load"),
            value=0.0,
            step=1000.0,
            format="%.0f",
            help="Excelから転記。空欄で近似計算。",
        )

    fp1, fp2, fp3 = st.columns(3)
    with fp1:
        fob = st.number_input(
            "FOB単価 (USD)", key=_key(idx, "fob"), value=0.0, step=0.01, format="%.3f"
        )
    with fp2:
        other_proc = st.number_input(
            "その他加工賃 (USD)", key=_key(idx, "oproc"), value=0.0, step=0.01, format="%.2f"
        )
    with fp3:
        loss_rate = st.number_input(
            "ロス率", key=_key(idx, "loss"), value=0.0, step=0.01, format="%.2f"
        )

    # ── 価格設定（最も重要） ──
    st.markdown("##### 価格設定")
    pr1, pr2, pr3, pr4 = st.columns(4)
    with pr1:
        quote_price = st.number_input(
            "見積売価 (円) *", key=_key(idx, "qp"), value=0.0, step=1.0, format="%.0f"
        )
    with pr2:
        lot = st.number_input("ロット (色あたり)", key=_key(idx, "lot"), value=0, step=1000, min_value=0)
    with pr3:
        colors = st.number_input("配色数", key=_key(idx, "col"), value=1, step=1, min_value=1)
    with pr4:
        retail = st.number_input("上代 (円)", key=_key(idx, "retail"), value=0.0, step=10.0, format="%.0f")

    # ── 詳細コスト（折りたたみ） ──
    with st.expander("検品・加工・副資材・物流（詳細）"):
        st.markdown("###### 検品・加工費")
        ic1, ic2, ic3 = st.columns(3)
        with ic1:
            insp_jpy = st.number_input("検品 (円)", key=_key(idx, "ij"), value=0.0, format="%.1f")
        with ic2:
            pack_jpy = st.number_input("包装 (円)", key=_key(idx, "pj"), value=0.0, format="%.1f")
        with ic3:
            mat_jpy = st.number_input("資材 (円)", key=_key(idx, "mj"), value=0.0, format="%.1f")

        st.markdown("###### 刺繍")
        em1, em2 = st.columns(2)
        with em1:
            emb_per_1000 = st.number_input(
                "1000針単価 (USD)", key=_key(idx, "emb"), value=0.03, format="%.3f"
            )
        with em2:
            stitch = st.number_input("刺繍針数", key=_key(idx, "stitch"), value=0.0, format="%.0f")

        st.markdown("###### 物流（倉庫→納品先）")
        lg1, lg2, lg3 = st.columns(3)
        with lg1:
            lio = st.number_input("入出庫料/ケース", key=_key(idx, "lio"), value=70.0, format="%.0f")
            lslip = st.number_input("伝票手数料", key=_key(idx, "lslip"), value=100.0, format="%.0f")
        with lg2:
            lst_m = st.number_input("保管月数", key=_key(idx, "lstm"), value=1.0, format="%.0f")
            lst_f = st.number_input("保管料/月", key=_key(idx, "lstf"), value=150.0, format="%.0f")
        with lg3:
            lfreight = st.number_input("運賃/ケース", key=_key(idx, "lfr"), value=700.0, format="%.0f")
            lcardboard = st.number_input("ダンボール代", key=_key(idx, "lcb"), value=0.0, format="%.0f")

        st.markdown("###### 売価調整")
        sa1, sa2 = st.columns(2)
        with sa1:
            center_fee = st.number_input(
                "センターフィー", key=_key(idx, "cfee"), value=0.0, step=0.01, format="%.3f"
            )
        with sa2:
            rebate = st.number_input(
                "歩引率", key=_key(idx, "rebate"), value=0.0, step=0.01, format="%.3f"
            )

    tariff_val = TARIFF_RATES.get(tariff_label, 0.0)

    return ProductInput(
        supplier=supplier if supplier != "（その他）" else "",
        port=port if port != "（その他）" else "",
        delivery_to=delivery if delivery != "（その他）" else "",
        ship_to=ship if ship != "（その他）" else "",
        container_ft=container_ft,
        method=method,
        product_name=name,
        prototype_code=code,
        package_size_cm=size_cm,
        weight_g=weight,
        packing_quantity=packing,
        fob_usd=fob,
        other_processing_usd=other_proc,
        loss_rate=loss_rate,
        embroidery_per_1000=emb_per_1000,
        stitch_count=stitch,
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
        logistics_cardboard=lcardboard,
        logistics_io_fee=lio,
        logistics_storage_months=lst_m,
        logistics_storage_fee=lst_f,
        logistics_slip_fee=lslip,
        logistics_freight=lfreight,
    )


def render_input_page() -> list[ProductInput]:
    """商品入力ページ全体を描画."""
    if "num_products" not in st.session_state:
        st.session_state.num_products = 1

    products: list[ProductInput] = []
    for i in range(st.session_state.num_products):
        with st.container(border=True):
            product = _render_product(i)
            if product is not None:
                products.append(product)

    if st.button("＋ 商品を追加", type="secondary"):
        st.session_state.num_products += 1
        st.rerun()

    return products
