"""B案: カード+ダッシュボード型ビュー."""

from __future__ import annotations

import streamlit as st

from quote.data.defaults import (
    CONTAINER_FT,
    DELIVERY_TO,
    FABRIC_QUALITIES,
    ITEM_TYPES,
    METHODS,
    PACKING_SIZES,
    PORTS,
    SHIP_TO,
    SUPPLIERS,
    TARIFF_RATES,
)
from quote.engine.calc import calculate
from quote.engine.models import GlobalParams, ProductInput, QuoteResult


def _key(idx: int, field: str) -> str:
    return f"card_{idx}_{field}"


def _fmt_jpy(v: float) -> str:
    return f"¥{v:,.1f}"


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


def _hint(msg: str) -> None:
    """未入力・未選択項目の注記を表示."""
    st.markdown(
        f'<p style="color:#E37400;font-size:0.75rem;margin:-10px 0 8px 2px;">'
        f'⚠ {msg}</p>',
        unsafe_allow_html=True,
    )


def _render_kpi_card(label: str, value: str, sub: str = "", color: str = "") -> str:
    color_style = f"color:{color};" if color else ""
    sub_html = f'<div style="font-size:0.75rem;color:#666;margin-top:2px;">{sub}</div>' if sub else ""
    return f"""
    <div style="background:#FFFFFF; border:1px solid #DADCE0; border-radius:8px;
                padding:16px 20px; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <div style="font-size:0.8rem; color:#5F6368; margin-bottom:4px;">{label}</div>
        <div style="font-size:1.5rem; font-weight:600; {color_style}">{value}</div>
        {sub_html}
    </div>
    """


def _render_product_card(idx: int) -> ProductInput | None:
    """商品1点の入力カード."""
    name = st.text_input("品名", key=_key(idx, "name"), placeholder="例: ダイカットメモ")

    if not name:
        st.caption("品名を入力すると入力欄と計算結果が表示されます。")
        return None

    # 取引条件（コンパクトな2行）
    st.markdown(
        '<p style="font-size:0.8rem;color:#5F6368;margin:12px 0 4px;'
        'text-transform:uppercase;letter-spacing:0.05em;border-bottom:1px solid #E8EAED;'
        'padding-bottom:4px;">取引条件</p>',
        unsafe_allow_html=True,
    )
    t1, t2, t3, t4 = st.columns(4)
    with t1:
        supplier = st.selectbox("仕入先", SUPPLIERS, key=_key(idx, "sup"))
    with t2:
        port = st.selectbox("揚地", PORTS, key=_key(idx, "port"))
    with t3:
        delivery = st.selectbox("納入先", DELIVERY_TO, key=_key(idx, "del"))
    with t4:
        ship = st.selectbox("出荷先", SHIP_TO, key=_key(idx, "ship"))

    t5, t6, t7, t8 = st.columns(4)
    with t5:
        ft = st.selectbox("コンテナ", CONTAINER_FT, key=_key(idx, "ft"), format_func=lambda x: f"{x}FT")
    with t6:
        method = st.selectbox("手法", METHODS, key=_key(idx, "method"))
    with t7:
        tariff_label = st.selectbox("関税率", list(TARIFF_RATES.keys()), key=_key(idx, "tariff"))
    with t8:
        code = st.text_input("試作コード", key=_key(idx, "code"), value=str(idx + 1))

    # 製品仕様
    st.markdown(
        '<p style="font-size:0.8rem;color:#5F6368;margin:12px 0 4px;'
        'text-transform:uppercase;letter-spacing:0.05em;border-bottom:1px solid #E8EAED;'
        'padding-bottom:4px;">製品仕様・FOB</p>',
        unsafe_allow_html=True,
    )
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        item_type = st.selectbox("アイテム", ITEM_TYPES, key=_key(idx, "item"))
        if not item_type:
            _hint("アイテムを選択してください")
    with s2:
        size = st.text_input("サイズ(cm)", key=_key(idx, "size"), placeholder="13*9.5*0.6")
        if not size:
            _hint("サイズを入力してください")
    with s3:
        fabric = st.selectbox("生地質", FABRIC_QUALITIES, key=_key(idx, "fabric"))
        if not fabric:
            _hint("生地質を選択してください")
    with s4:
        pack_size = st.selectbox("梱包サイズ", PACKING_SIZES, key=_key(idx, "pksize"))
        if not pack_size:
            _hint("梱包サイズを選択してください")

    s5, s6, s7, s8 = st.columns(4)
    with s5:
        weight = st.number_input("重量(g)", key=_key(idx, "wt"), value=0.0, format="%.1f")
        if weight <= 0:
            _hint("重量を入力してください")
    with s6:
        momme = weight / 3.75 if weight > 0 else 0.0
        st.metric("仕上目方(匁)", f"{momme:.1f}")
    with s7:
        packing = st.number_input("入数", key=_key(idx, "pk"), value=1, min_value=1)
    with s8:
        load = st.number_input("積載量", key=_key(idx, "ld"), value=0.0, format="%.1f")
        if load <= 0:
            _hint("積載量を入力してください（運賃計算に必須）")

    f1, f2, f3 = st.columns(3)
    with f1:
        fob = st.number_input("FOB(USD)", key=_key(idx, "fob"), value=0.0, format="%.3f")
        if fob <= 0:
            _hint("FOBを入力してください（原価計算に必須）")
    with f2:
        oproc = st.number_input("加工賃(USD)", key=_key(idx, "op"), value=0.0, format="%.2f")
    with f3:
        loss = st.number_input("ロス率", key=_key(idx, "loss"), value=0.0, format="%.2f")

    # 価格設定
    st.markdown(
        '<p style="font-size:0.8rem;color:#5F6368;margin:12px 0 4px;'
        'text-transform:uppercase;letter-spacing:0.05em;border-bottom:1px solid #E8EAED;'
        'padding-bottom:4px;">価格設定</p>',
        unsafe_allow_html=True,
    )
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        qp = st.number_input("見積売価(円)", key=_key(idx, "qp"), value=0.0, format="%.1f")
        if qp <= 0:
            _hint("見積売価を入力してください")
    with p2:
        lot = st.number_input("ロット/色", key=_key(idx, "lot"), value=0, min_value=0)
        if lot <= 0:
            _hint("ロットを入力してください")
    with p3:
        colors = st.number_input("配色", key=_key(idx, "col"), value=1, min_value=1)
    with p4:
        retail = st.number_input("上代(円)", key=_key(idx, "ret"), value=0.0, format="%.1f")
        if retail <= 0:
            _hint("上代を入力してください（定価率の計算に必要）")

    # 詳細（折りたたみ）
    with st.expander("日本送付副資材経費/枚（BH-BT列）"):
        st.caption("入力(使用頻度少ない)")
        m1, m2, m3 = st.columns(3)
        with m1:
            v_ribbon = st.number_input("リボン", key=_key(idx, "ribbon"), value=0.0, format="%.1f")
            v_nl2 = st.number_input("ネーム2", key=_key(idx, "nl2"), value=0.0, format="%.1f")
            v_nl3 = st.number_input("ネーム3", key=_key(idx, "nl3"), value=0.0, format="%.1f")
        with m2:
            v_seal1 = st.number_input("シール1", key=_key(idx, "seal1"), value=0.0, format="%.1f")
            v_seal2 = st.number_input("シール2", key=_key(idx, "seal2"), value=0.0, format="%.1f")
            v_tag = st.number_input("タグ", key=_key(idx, "tag"), value=0.0, format="%.1f")
        with m3:
            v_bag = st.number_input("袋", key=_key(idx, "bag"), value=0.0, format="%.1f")
            v_othermat = st.number_input("その他", key=_key(idx, "omat"), value=0.0, format="%.1f")
            v_matfr = st.number_input("資材運賃", key=_key(idx, "matfr"), value=0.0, format="%.1f")

    with st.expander("償却経費/ロット（BU-CJ列）"):
        st.caption("入力(頻度少ない)")
        a1, a2, a3 = st.columns(3)
        with a1:
            v_design = st.number_input("図案", key=_key(idx, "design"), value=0.0, format="%.0f")
            v_jqcard = st.number_input("JQカード", key=_key(idx, "jqc"), value=0.0, format="%.0f")
            v_embcard = st.number_input("刺繍カード", key=_key(idx, "embc"), value=0.0, format="%.0f")
            v_printup = st.number_input("プリント型単価", key=_key(idx, "prup"), value=0.0, format="%.0f")
            v_printcnt = st.number_input("型数", key=_key(idx, "prcnt"), value=0.0, format="%.0f")
        with a2:
            v_layout = st.number_input("レイアウト", key=_key(idx, "layout"), value=0.0, format="%.0f")
            v_namepl = st.number_input("ネーム版代", key=_key(idx, "namepl"), value=0.0, format="%.0f")
            v_sealpl = st.number_input("シール版", key=_key(idx, "sealpl"), value=0.0, format="%.0f")
            v_tabpl = st.number_input("タベル版", key=_key(idx, "tabpl"), value=0.0, format="%.0f")
            v_bagpl = st.number_input("袋版", key=_key(idx, "bagpl"), value=0.0, format="%.0f")
        with a3:
            v_cbpl = st.number_input("ダンボール版", key=_key(idx, "cbpl"), value=0.0, format="%.0f")
            v_otherdep = st.number_input("その他償却", key=_key(idx, "odep"), value=0.0, format="%.0f")
            v_sample = st.number_input("見本経費", key=_key(idx, "sample"), value=0.0, format="%.0f")
            v_qinsp = st.number_input("品質検査代", key=_key(idx, "qinsp"), value=0.0, format="%.0f")
            v_otheramort = st.number_input("その他", key=_key(idx, "oamort"), value=0.0, format="%.0f")

    with st.expander("物流・加工・売価調整"):
        st.caption("倉庫→納品先 物流経費（CN-CS列）")
        d1, d2, d3 = st.columns(3)
        with d1:
            lcb = st.number_input("ダンボール代", key=_key(idx, "lcb"), value=0.0, format="%.0f")
            lio = st.number_input("入出庫料", key=_key(idx, "lio"), value=70.0, format="%.0f")
        with d2:
            lstm = st.number_input("保管月数", key=_key(idx, "lm"), value=1.0, format="%.0f")
            lstf = st.number_input("保管料/月", key=_key(idx, "lf"), value=150.0, format="%.0f")
        with d3:
            lslip = st.number_input("伝票手数料", key=_key(idx, "lsl"), value=100.0, format="%.0f")
            lfr = st.number_input("運賃/ケース", key=_key(idx, "lr"), value=700.0, format="%.0f")

        st.caption("売価調整（DI-DJ列）")
        sa1, sa2 = st.columns(2)
        with sa1:
            cfee = st.number_input("センターフィー", key=_key(idx, "cf"), value=0.0, format="%.3f")
        with sa2:
            rebate_val = st.number_input("歩引率", key=_key(idx, "rebate"), value=0.0, format="%.3f")

    tariff_val = TARIFF_RATES.get(tariff_label, 0.0)

    return ProductInput(
        product_name=name,
        prototype_code=code,
        supplier=supplier if supplier != "（その他）" else "",
        port=port if port != "（その他）" else "",
        delivery_to=delivery if delivery != "（その他）" else "",
        ship_to=ship if ship != "（その他）" else "",
        container_ft=ft,
        method=method,
        item_type=item_type if item_type != "（その他）" else "",
        package_size_cm=size,
        weight_g=weight,
        weight_momme=momme,
        fabric_quality=fabric if fabric != "（その他）" else "",
        packing_quantity=packing,
        packing_size=pack_size if pack_size != "（その他）" else "",
        container_load=load,
        fob_usd=fob,
        other_processing_usd=oproc,
        loss_rate=loss,
        tariff_rate_override=tariff_val,
        ribbon=v_ribbon,
        name_label_2=v_nl2,
        name_label_3=v_nl3,
        seal_1=v_seal1,
        seal_2=v_seal2,
        tag=v_tag,
        bag=v_bag,
        other_material=v_othermat,
        material_freight=v_matfr,
        design_cost=v_design,
        jq_card=v_jqcard,
        embroidery_card=v_embcard,
        print_unit_price=v_printup,
        print_type_count=v_printcnt,
        layout=v_layout,
        name_plate=v_namepl,
        seal_plate=v_sealpl,
        tab_plate=v_tabpl,
        bag_plate=v_bagpl,
        cardboard_plate=v_cbpl,
        other_depreciation=v_otherdep,
        sample_cost=v_sample,
        quality_inspection=v_qinsp,
        other_amortization=v_otheramort,
        logistics_cardboard=lcb,
        logistics_io_fee=lio,
        logistics_storage_months=lstm,
        logistics_storage_fee=lstf,
        logistics_slip_fee=lslip,
        logistics_freight=lfr,
        center_fee=cfee,
        rebate=rebate_val,
        quote_price=qp,
        lot_per_color=lot,
        num_colors=colors,
        retail_price=retail,
    )


def _render_result_card(name: str, result: QuoteResult) -> None:
    """商品の計算結果をKPIカード+内訳で表示."""
    r = result.pricing_with_amort
    c = result.cost
    profit_color = _profit_color(r.gross_profit_rate)

    # KPIカード (4列)
    cols = st.columns(4)
    cards = [
        _render_kpi_card("製品原価", _fmt_jpy(c.product_cost)),
        _render_kpi_card("試算売価", _fmt_jpy(r.trial_price)),
        _render_kpi_card("見積売価", _fmt_jpy(r.quote_price)),
        _render_kpi_card("粗利率", _fmt_pct(r.gross_profit_rate), sub=f"{_fmt_jpy(r.gross_profit_unit)}/枚", color=profit_color),
    ]
    for col, card_html in zip(cols, cards):
        with col:
            st.markdown(card_html, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    cols2 = st.columns(3)
    cards2 = [
        _render_kpi_card("歩積込売価", _fmt_jpy(r.stepped_price)),
        _render_kpi_card("売上金額", _fmt_jpy(r.sales_amount)),
        _render_kpi_card("粗利金額", _fmt_jpy(r.gross_profit_total), color=profit_color),
    ]
    for col, card_html in zip(cols2, cards2):
        with col:
            st.markdown(card_html, unsafe_allow_html=True)

    # 原価内訳（折りたたみ）
    with st.expander("原価内訳を表示"):
        breakdown_items = [
            ("仕入値", c.purchase_price),
            ("コンテナ経費", c.container_expense_unit),
            ("B品ロス", c.b_grade_loss),
            ("副資材", c.sub_material_cost),
            ("償却経費", c.amortization_actual),
            ("物流経費", c.logistics_unit),
            ("加工経費", c.domestic_processing_unit),
        ]
        for label, val in breakdown_items:
            pct = val / c.product_cost * 100 if c.product_cost > 0 else 0
            bar_width = min(pct, 100)
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; margin:4px 0; font-size:0.85rem;">
                    <div style="width:100px; color:#5F6368;">{label}</div>
                    <div style="flex:1; background:#F0F2F6; border-radius:4px; height:20px; margin:0 8px;">
                        <div style="width:{bar_width}%; background:#1B73E8; height:100%;
                                    border-radius:4px; min-width:2px;"></div>
                    </div>
                    <div style="width:80px; text-align:right; font-weight:500;">{_fmt_jpy(val)}</div>
                    <div style="width:50px; text-align:right; color:#5F6368;">{pct:.0f}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown(
            f'<div style="text-align:right; font-weight:600; margin-top:8px; font-size:0.95rem;">'
            f'製品原価合計: {_fmt_jpy(c.product_cost)}</div>',
            unsafe_allow_html=True,
        )


def render_card_view(
    params: GlobalParams, prefix: str = "card"
) -> tuple[list[ProductInput], list[tuple[str, QuoteResult]]]:
    """カード+ダッシュボード型ビューを描画.

    Returns (products, results) for save/export use.
    """
    num_key = f"{prefix}_num_products"
    if num_key not in st.session_state:
        st.session_state[num_key] = 1

    all_products: list[ProductInput] = []
    all_results: list[tuple[str, QuoteResult]] = []

    for i in range(st.session_state[num_key]):
        with st.container(border=True):
            col_title, col_del = st.columns([8, 1])
            with col_title:
                st.markdown(f"#### 商品 {i + 1}")
            with col_del:
                if i > 0 and st.button("🗑", key=f"{prefix}_del_{i}"):
                    st.session_state[num_key] -= 1
                    st.rerun()

            product = _render_product_card(i)

            if product is not None:
                all_products.append(product)
                result = calculate(product, params)
                all_results.append((product.product_name, result))
                if result.warnings:
                    for w in result.warnings:
                        st.warning(w)
                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
                _render_result_card(product.product_name, result)

    if st.button("＋ 商品を追加", type="primary"):
        st.session_state[num_key] += 1
        st.rerun()

    if len(all_results) > 1:
        st.markdown("---")
        total_sales = sum(r.pricing_with_amort.sales_amount for _, r in all_results)
        total_profit = sum(r.pricing_with_amort.gross_profit_total for _, r in all_results)
        avg_rate = total_profit / total_sales if total_sales > 0 else 0

        cols = st.columns(3)
        summary_cards = [
            _render_kpi_card("売上合計", _fmt_jpy(total_sales)),
            _render_kpi_card("粗利合計", _fmt_jpy(total_profit), color=_profit_color(avg_rate)),
            _render_kpi_card("平均粗利率", _fmt_pct(avg_rate), color=_profit_color(avg_rate)),
        ]
        for col, html in zip(cols, summary_cards):
            with col:
                st.markdown(html, unsafe_allow_html=True)

    return all_products, all_results
