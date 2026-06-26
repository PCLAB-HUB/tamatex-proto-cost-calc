"""サイドバー: 見積もり単位の固定パラメータ設定."""

from __future__ import annotations

import streamlit as st

from quote.engine.models import ContainerExpenses, GlobalParams

_DEFAULT = GlobalParams()


def render_sidebar(initial: GlobalParams | None = None) -> GlobalParams:
    """サイドバーに固定パラメータ入力を描画し、GlobalParamsを返す.

    initial が渡された場合、そのパラメータを初期値として使う（見積もり編集時）。
    """
    d = initial or _DEFAULT
    ce = d.container_expenses

    st.sidebar.header("見積もりパラメータ")
    st.sidebar.caption("この見積もりに適用される設定")

    st.sidebar.subheader("為替・運賃")
    internal_rate = st.sidebar.number_input(
        "社内為替 (円/USD)", value=d.internal_rate, step=1.0, format="%.1f",
        key="sp_internal",
    )
    current_rate = st.sidebar.number_input(
        "現行為替 (円/USD)", value=d.current_rate, step=1.0, format="%.1f",
        key="sp_current",
    )
    overseas_freight = st.sidebar.number_input(
        "海外運賃 (USD/コンテナ)", value=d.overseas_freight_usd, step=10.0, format="%.0f",
        key="sp_freight",
    )

    st.sidebar.subheader("通貨換算")
    cny_usd = st.sidebar.number_input(
        "元→ドル換算率", value=d.cny_to_usd_rate, step=0.01, format="%.2f",
        key="sp_cny_usd",
    )
    cny_jpy = st.sidebar.number_input(
        "元→円為替", value=d.cny_to_jpy_rate, step=0.5, format="%.1f",
        key="sp_cny_jpy",
    )

    st.sidebar.subheader("率")
    insurance = st.sidebar.number_input(
        "保険リスク率", value=d.insurance_risk_rate, step=0.0001, format="%.4f",
        key="sp_insurance",
    )
    b_loss = st.sidebar.number_input(
        "B品ロス率", value=d.b_grade_loss_rate, step=0.005, format="%.3f",
        key="sp_bloss",
    )
    sub_loss = st.sidebar.number_input(
        "副資材ロス率", value=d.sub_material_loss_rate, step=0.01, format="%.2f",
        key="sp_subloss",
    )
    amort_margin = st.sidebar.number_input(
        "償却マージン", value=d.amortization_margin, step=0.01, format="%.2f",
        key="sp_amort",
    )
    margin = st.sidebar.number_input(
        "マージン率", value=d.margin, step=0.01, format="%.2f",
        key="sp_margin",
    )

    with st.sidebar.expander("コンテナ国内経費 (11項目)", expanded=False):
        cy = st.number_input("CY CHARGE", value=ce.cy_charge, step=1000.0, format="%.0f", key="sp_cy")
        lss = st.number_input("LSS", value=ce.lss, step=1000.0, format="%.0f", key="sp_lss")
        lss_usd = st.number_input("LSS/CIC (USD)", value=ce.lss_cic_usd, step=10.0, format="%.0f", key="sp_lss_usd")
        thc = st.number_input("THC", value=ce.thc, step=1000.0, format="%.0f", key="sp_thc")
        emc = st.number_input("EMC", value=ce.emc, step=1000.0, format="%.0f", key="sp_emc")
        do_fee = st.number_input("D/O FEE", value=ce.do_fee, step=1000.0, format="%.0f", key="sp_do")
        doc_fee = st.number_input("DOC FEE", value=ce.doc_fee, step=1000.0, format="%.0f", key="sp_doc")
        customs = st.number_input("通関手数料", value=ce.customs_fee, step=100.0, format="%.0f", key="sp_customs")
        handling = st.number_input("取扱料", value=ce.handling_fee, step=1000.0, format="%.0f", key="sp_handling")
        drayage = st.number_input("ドレー料", value=ce.drayage, step=1000.0, format="%.0f", key="sp_drayage")
        devanning = st.number_input("デバン料", value=ce.devanning, step=1000.0, format="%.0f", key="sp_devanning")

        container_expenses = ContainerExpenses(
            cy_charge=cy, lss=lss, lss_cic_usd=lss_usd,
            thc=thc, emc=emc, do_fee=do_fee, doc_fee=doc_fee,
            customs_fee=customs, handling_fee=handling,
            drayage=drayage, devanning=devanning,
        )

    return GlobalParams(
        internal_rate=internal_rate,
        current_rate=current_rate,
        overseas_freight_usd=overseas_freight,
        cny_to_usd_rate=cny_usd,
        cny_to_jpy_rate=cny_jpy,
        insurance_risk_rate=insurance,
        tariff_rate=0.0,
        b_grade_loss_rate=b_loss,
        sub_material_loss_rate=sub_loss,
        amortization_margin=amort_margin,
        margin=margin,
        container_expenses=container_expenses,
    )
