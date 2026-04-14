"""サイドバー — 条件選択・為替・マージン・輸入経費の編集UI."""

from __future__ import annotations

from dataclasses import replace

import streamlit as st

from proto.data.mock_params import COND_20FT, COND_40FT
from proto.engine.models import ImportCondition, ImportExpenses


_CONDITIONS = {"20FT 大阪/今治": COND_20FT, "40FT 東京": COND_40FT}


def _edit_import_expenses(
    label: str, base: ImportExpenses, key_prefix: str
) -> ImportExpenses:
    """輸入経費11項目の編集フォーム."""
    with st.expander(label, expanded=False):
        cols = st.columns(2)
        cic_usd = cols[0].number_input(
            "CIC (USD)", value=base.cic_usd, step=10.0, key=f"{key_prefix}_cic_usd"
        )
        cy_charge = cols[1].number_input(
            "CY CHARGE", value=base.cy_charge, step=1000.0, key=f"{key_prefix}_cy"
        )
        thc = cols[0].number_input(
            "THC", value=base.thc, step=1000.0, key=f"{key_prefix}_thc"
        )
        emc = cols[1].number_input(
            "EMC", value=base.emc, step=1000.0, key=f"{key_prefix}_emc"
        )
        cic2 = cols[0].number_input(
            "CIC (JPY)", value=base.cic2, step=1000.0, key=f"{key_prefix}_cic2"
        )
        do_fee = cols[1].number_input(
            "D/O", value=base.do_fee, step=1000.0, key=f"{key_prefix}_do"
        )
        doc_fee = cols[0].number_input(
            "DOC", value=base.doc_fee, step=1000.0, key=f"{key_prefix}_doc"
        )
        customs_fee = cols[1].number_input(
            "通関", value=base.customs_fee, step=1000.0, key=f"{key_prefix}_customs"
        )
        handling_fee = cols[0].number_input(
            "取扱料", value=base.handling_fee, step=1000.0, key=f"{key_prefix}_handling"
        )
        drayage = cols[1].number_input(
            "ドレー料", value=base.drayage, step=1000.0, key=f"{key_prefix}_drayage"
        )
        devanning = cols[0].number_input(
            "デバン料", value=base.devanning, step=1000.0, key=f"{key_prefix}_devanning"
        )
    return ImportExpenses(
        cic_usd=cic_usd,
        cy_charge=cy_charge,
        thc=thc,
        emc=emc,
        cic2=cic2,
        do_fee=do_fee,
        doc_fee=doc_fee,
        customs_fee=customs_fee,
        handling_fee=handling_fee,
        drayage=drayage,
        devanning=devanning,
    )


def render_sidebar() -> ImportCondition:
    """サイドバーを描画し、編集後の ImportCondition を返す."""
    st.sidebar.title("輸入条件設定")

    # --- コンテナ条件選択 ---
    selected = st.sidebar.radio(
        "コンテナ条件", list(_CONDITIONS.keys()), horizontal=True
    )
    base_cond = _CONDITIONS[selected]

    st.sidebar.divider()

    # --- 為替 ---
    st.sidebar.subheader("為替レート")
    cols = st.sidebar.columns(2)
    internal_rate = cols[0].number_input(
        "社内為替 (円/$)", value=base_cond.internal_rate, step=1.0, key="internal_rate"
    )
    current_rate = cols[1].number_input(
        "現行為替 (円/$)", value=base_cond.current_rate, step=1.0, key="current_rate"
    )

    st.sidebar.divider()

    # --- マージン・ロス率 ---
    st.sidebar.subheader("マージン・ロス率")
    cols2 = st.sidebar.columns(2)
    margin_pct = cols2[0].number_input(
        "マージン (%)", value=base_cond.margin_pct, step=1.0, key="margin_pct"
    )
    loss_rate_pct = cols2[1].number_input(
        "ロス率 (%)", value=base_cond.loss_rate_pct, step=1.0, key="loss_rate_pct"
    )

    # --- 資材 ---
    cols3 = st.sidebar.columns(2)
    material_lot = cols3[0].number_input(
        "資材ロット", value=base_cond.material_lot, step=100, key="material_lot"
    )
    material_loss_pct = cols3[1].number_input(
        "資材ロス率 (%)",
        value=base_cond.material_loss_pct,
        step=0.5,
        key="material_loss_pct",
    )

    st.sidebar.divider()

    # --- 輸入 ---
    st.sidebar.subheader("輸入パラメータ")
    overseas_freight = st.sidebar.number_input(
        "海外運賃 (USD)", value=base_cond.overseas_freight_usd, step=10.0, key="freight"
    )
    cols4 = st.sidebar.columns(2)
    insurance_rate = cols4[0].number_input(
        "保険率", value=base_cond.insurance_rate, step=0.0001, format="%.4f",
        key="insurance",
    )
    tariff_rate = cols4[1].number_input(
        "関税率", value=base_cond.tariff_rate, step=0.001, format="%.3f",
        key="tariff",
    )

    st.sidebar.divider()

    # --- 物流 ---
    st.sidebar.subheader("物流")
    cols5 = st.sidebar.columns(3)
    io_fee = cols5[0].number_input(
        "入出庫 (円)", value=base_cond.io_fee, step=10.0, key="io_fee"
    )
    storage_fee = cols5[1].number_input(
        "保管料 (円)", value=base_cond.storage_fee, step=10.0, key="storage_fee"
    )
    storage_months = cols5[2].number_input(
        "ヶ月", value=base_cond.storage_months, step=1.0, key="storage_months"
    )

    st.sidebar.divider()

    # --- 輸入経費（単品・ギフト別） ---
    st.sidebar.subheader("輸入経費")
    with st.sidebar:
        exp_single = _edit_import_expenses(
            "単品用 輸入経費", base_cond.import_expenses_single, "exp_s"
        )
        exp_gift = _edit_import_expenses(
            "ギフト用 輸入経費", base_cond.import_expenses_gift, "exp_g"
        )

    return ImportCondition(
        name=selected,
        internal_rate=internal_rate,
        current_rate=current_rate,
        loss_rate_pct=loss_rate_pct,
        margin_pct=margin_pct,
        material_lot=material_lot,
        material_loss_pct=material_loss_pct,
        emb_general=base_cond.emb_general,
        emb_silver=base_cond.emb_silver,
        emb_ket=base_cond.emb_ket,
        emb_brand=base_cond.emb_brand,
        overseas_freight_usd=overseas_freight,
        insurance_rate=insurance_rate,
        tariff_rate=tariff_rate,
        import_expenses_single=exp_single,
        import_expenses_gift=exp_gift,
        io_fee=io_fee,
        storage_fee=storage_fee,
        storage_months=storage_months,
    )
