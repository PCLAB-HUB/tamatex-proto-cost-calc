"""デフォルト設定ページ."""

from __future__ import annotations

import streamlit as st

from quote.engine.models import ContainerExpenses, GlobalParams
from quote.storage.settings import load_default_params, save_default_params

_BUILTIN = GlobalParams()


def render_settings_page() -> None:
    """デフォルト設定の編集・保存ページ."""
    st.markdown("### ⚙️ デフォルト設定")
    st.caption(
        "新規見積もり作成時に自動適用されるパラメータです。"
        "見積もりごとに個別変更も可能です。"
    )

    saved = load_default_params() or _BUILTIN
    ce = saved.container_expenses

    with st.container(border=True):
        st.markdown("##### 為替・運賃")
        c1, c2, c3 = st.columns(3)
        with c1:
            internal = st.number_input(
                "社内為替 (円/USD)", value=saved.internal_rate,
                step=1.0, format="%.1f", key="ds_internal",
            )
        with c2:
            current = st.number_input(
                "現行為替 (円/USD)", value=saved.current_rate,
                step=1.0, format="%.1f", key="ds_current",
            )
        with c3:
            freight = st.number_input(
                "海外運賃 (USD/コンテナ)", value=saved.overseas_freight_usd,
                step=10.0, format="%.0f", key="ds_freight",
            )

    with st.container(border=True):
        st.markdown("##### 通貨換算")
        c1, c2 = st.columns(2)
        with c1:
            cny_usd = st.number_input(
                "元→ドル換算率", value=saved.cny_to_usd_rate,
                step=0.01, format="%.2f", key="ds_cny_usd",
            )
        with c2:
            cny_jpy = st.number_input(
                "元→円為替", value=saved.cny_to_jpy_rate,
                step=0.5, format="%.1f", key="ds_cny_jpy",
            )

    with st.container(border=True):
        st.markdown("##### 率")
        c1, c2, c3 = st.columns(3)
        with c1:
            insurance = st.number_input(
                "保険リスク率", value=saved.insurance_risk_rate,
                step=0.0001, format="%.4f", key="ds_insurance",
            )
            b_loss = st.number_input(
                "B品ロス率", value=saved.b_grade_loss_rate,
                step=0.005, format="%.3f", key="ds_bloss",
            )
        with c2:
            sub_loss = st.number_input(
                "副資材ロス率", value=saved.sub_material_loss_rate,
                step=0.01, format="%.2f", key="ds_subloss",
            )
            amort_margin = st.number_input(
                "償却マージン", value=saved.amortization_margin,
                step=0.01, format="%.2f", key="ds_amort",
            )
        with c3:
            margin = st.number_input(
                "マージン率", value=saved.margin,
                step=0.01, format="%.2f", key="ds_margin",
            )

    with st.container(border=True):
        st.markdown("##### コンテナ国内経費 (11項目)")
        c1, c2, c3 = st.columns(3)
        with c1:
            cy = st.number_input("CY CHARGE", value=ce.cy_charge, format="%.0f", key="ds_cy")
            lss = st.number_input("LSS", value=ce.lss, format="%.0f", key="ds_lss")
            lss_usd = st.number_input("LSS/CIC (USD)", value=ce.lss_cic_usd, format="%.0f", key="ds_lssusd")
            thc = st.number_input("THC", value=ce.thc, format="%.0f", key="ds_thc")
        with c2:
            emc = st.number_input("EMC", value=ce.emc, format="%.0f", key="ds_emc")
            do_fee = st.number_input("D/O FEE", value=ce.do_fee, format="%.0f", key="ds_do")
            doc_fee = st.number_input("DOC FEE", value=ce.doc_fee, format="%.0f", key="ds_doc")
            customs = st.number_input("通関手数料", value=ce.customs_fee, format="%.0f", key="ds_customs")
        with c3:
            handling = st.number_input("取扱料", value=ce.handling_fee, format="%.0f", key="ds_handling")
            drayage = st.number_input("ドレー料", value=ce.drayage, format="%.0f", key="ds_drayage")
            devanning = st.number_input("デバン料", value=ce.devanning, format="%.0f", key="ds_devanning")

    st.markdown("")
    if st.button("💾 デフォルト設定を保存", type="primary"):
        new_params = GlobalParams(
            internal_rate=internal,
            current_rate=current,
            overseas_freight_usd=freight,
            cny_to_usd_rate=cny_usd,
            cny_to_jpy_rate=cny_jpy,
            insurance_risk_rate=insurance,
            tariff_rate=0.0,
            b_grade_loss_rate=b_loss,
            sub_material_loss_rate=sub_loss,
            amortization_margin=amort_margin,
            margin=margin,
            container_expenses=ContainerExpenses(
                cy_charge=cy, lss=lss, lss_cic_usd=lss_usd,
                thc=thc, emc=emc, do_fee=do_fee, doc_fee=doc_fee,
                customs_fee=customs, handling_fee=handling,
                drayage=drayage, devanning=devanning,
            ),
        )
        save_default_params(new_params)
        st.success("デフォルト設定を保存しました。新規見積もり作成時に自動適用されます。")
