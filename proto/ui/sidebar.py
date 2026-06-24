"""サイドバー — 条件選択・為替・マージン・輸入経費の編集UI."""

from __future__ import annotations

import streamlit as st

from proto.data.mock_params import COND_20FT, COND_40FT
from proto.engine.models import ImportCondition, ImportExpenses, LogisticsParams
from proto.storage.scenario_repo import ScenarioNameConflictError, ScenarioRepository


__all__ = [
    "render_sidebar",
    "apply_condition_to_session_state",
]


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


def render_sidebar(repo: ScenarioRepository | None = None) -> ImportCondition:
    """サイドバーを描画し、編集後の ImportCondition を返す.

    Args:
        repo: シナリオリポジトリ。None の場合は保存ボタンを表示しない。
              既存の呼び出し箇所は引数なしでも動作する（後方互換性維持）。

    Returns:
        現在のサイドバー値を反映した ImportCondition インスタンス。
    """
    st.sidebar.title("輸入条件設定")

    # --- コンテナ条件選択 ---
    selected = st.sidebar.radio(
        "コンテナ条件",
        list(_CONDITIONS.keys()),
        horizontal=True,
        key="sidebar_container_radio",
    )
    base_cond = _CONDITIONS[selected]

    # コンテナ切替時にwidget値をリセットするため、キーにプレフィックスを付与
    kp = selected.replace(" ", "_").replace("/", "_")

    st.sidebar.divider()

    # --- 為替 ---
    st.sidebar.subheader("💱 為替レート")
    cols = st.sidebar.columns(2)
    internal_rate = cols[0].number_input(
        "社内為替 (円/$)", value=base_cond.internal_rate, step=1.0,
        min_value=1.0, key=f"{kp}_internal_rate",
    )
    current_rate = cols[1].number_input(
        "現行為替 (円/$)", value=base_cond.current_rate, step=1.0,
        min_value=1.0, key=f"{kp}_current_rate",
    )

    st.sidebar.divider()

    # --- マージン・ロス率 ---
    st.sidebar.subheader("🎯 マージン・ロス率")
    cols2 = st.sidebar.columns(2)
    margin_pct = cols2[0].number_input(
        "マージン (%)", value=base_cond.margin_pct, step=1.0,
        min_value=0.0, key=f"{kp}_margin_pct",
    )
    loss_rate_pct = cols2[1].number_input(
        "ロス率 (%)", value=base_cond.loss_rate_pct, step=1.0,
        min_value=0.0, key=f"{kp}_loss_rate_pct",
    )

    # --- 資材 ---
    cols3 = st.sidebar.columns(2)
    material_lot = cols3[0].number_input(
        "資材ロット", value=base_cond.material_lot, step=100,
        min_value=1, key=f"{kp}_material_lot",
    )
    material_loss_pct = cols3[1].number_input(
        "資材ロス率 (%)",
        value=base_cond.material_loss_pct,
        step=0.5,
        min_value=0.0, key=f"{kp}_material_loss_pct",
    )

    st.sidebar.divider()

    # --- 輸入 ---
    st.sidebar.subheader("📦 輸入パラメータ")
    overseas_freight = st.sidebar.number_input(
        "海外運賃 (USD)", value=base_cond.overseas_freight_usd, step=10.0,
        min_value=0.0, key=f"{kp}_freight",
    )
    cols4 = st.sidebar.columns(2)
    insurance_rate = cols4[0].number_input(
        "保険率", value=base_cond.insurance_rate, step=0.0001, format="%.4f",
        min_value=0.0, key=f"{kp}_insurance",
    )
    tariff_rate = cols4[1].number_input(
        "関税率", value=base_cond.tariff_rate, step=0.001, format="%.3f",
        min_value=0.0, key=f"{kp}_tariff",
    )

    st.sidebar.divider()

    # --- 物流 ---
    st.sidebar.subheader("🚚 物流")
    st.sidebar.caption("倉庫料金はケース単位でコンテナ非依存。単品/ギフトで別単価。")
    st.sidebar.markdown("**単品用**")
    cols5s = st.sidebar.columns(3)
    io_fee_s = cols5s[0].number_input(
        "入出庫 (円)", value=base_cond.logistics_single.io_fee, step=10.0,
        min_value=0.0, key=f"{kp}_io_fee_s",
    )
    storage_fee_s = cols5s[1].number_input(
        "保管料 (円)", value=base_cond.logistics_single.storage_fee, step=10.0,
        min_value=0.0, key=f"{kp}_storage_fee_s",
    )
    storage_months_s = cols5s[2].number_input(
        "ヶ月", value=base_cond.logistics_single.storage_months, step=1.0,
        min_value=0.0, key=f"{kp}_storage_months_s",
    )
    st.sidebar.markdown("**ギフト用**")
    cols5g = st.sidebar.columns(3)
    io_fee_g = cols5g[0].number_input(
        "入出庫 (円)", value=base_cond.logistics_gift.io_fee, step=10.0,
        min_value=0.0, key=f"{kp}_io_fee_g",
    )
    storage_fee_g = cols5g[1].number_input(
        "保管料 (円)", value=base_cond.logistics_gift.storage_fee, step=10.0,
        min_value=0.0, key=f"{kp}_storage_fee_g",
    )
    storage_months_g = cols5g[2].number_input(
        "ヶ月", value=base_cond.logistics_gift.storage_months, step=1.0,
        min_value=0.0, key=f"{kp}_storage_months_g",
    )

    st.sidebar.divider()

    # --- 輸入経費（上級者設定・デフォルト折りたたみ） ---
    st.sidebar.subheader("💰 輸入経費（上級者設定）")
    with st.sidebar:
        exp_single = _edit_import_expenses(
            "単品用 輸入経費", base_cond.import_expenses_single, f"{kp}_exp_s",
        )
        exp_gift = _edit_import_expenses(
            "ギフト用 輸入経費", base_cond.import_expenses_gift, f"{kp}_exp_g",
        )

    condition = ImportCondition(
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
        logistics_single=LogisticsParams(
            io_fee=io_fee_s, storage_fee=storage_fee_s, storage_months=storage_months_s
        ),
        logistics_gift=LogisticsParams(
            io_fee=io_fee_g, storage_fee=storage_fee_g, storage_months=storage_months_g
        ),
    )

    # --- シナリオ保存（repo が渡された場合のみ表示） ---
    if repo is not None:
        st.sidebar.divider()
        st.sidebar.subheader("💾 シナリオ保存")
        scenario_name = st.sidebar.text_input(
            "名前",
            placeholder="例: USD150_20FT_標準",
            key="sidebar_scenario_name",
        )
        if st.sidebar.button(
            "現在の条件を保存", type="primary", use_container_width=True
        ):
            if not scenario_name.strip():
                st.sidebar.error("名前を入力してください")
            else:
                try:
                    sid = repo.save_scenario(scenario_name.strip(), condition)
                    st.sidebar.success(f"保存しました (id={sid})")
                except ScenarioNameConflictError:
                    st.sidebar.error("この名前は既に使われています")

    return condition


def _expenses_to_session_state_keys(exp: ImportExpenses, prefix: str) -> dict[str, float]:
    """ImportExpenses フィールドを session_state キー→値の辞書に変換する.

    Streamlit に依存しない純粋関数のため、単体テストが容易。

    Args:
        exp: 輸入経費インスタンス。
        prefix: widget key プレフィックス（例: "20FT_大阪_今治_exp_s"）。

    Returns:
        {widget_key: value} の辞書。
    """
    return {
        f"{prefix}_cic_usd": exp.cic_usd,
        f"{prefix}_cy": exp.cy_charge,
        f"{prefix}_thc": exp.thc,
        f"{prefix}_emc": exp.emc,
        f"{prefix}_cic2": exp.cic2,
        f"{prefix}_do": exp.do_fee,
        f"{prefix}_doc": exp.doc_fee,
        f"{prefix}_customs": exp.customs_fee,
        f"{prefix}_handling": exp.handling_fee,
        f"{prefix}_drayage": exp.drayage,
        f"{prefix}_devanning": exp.devanning,
    }


def apply_condition_to_session_state(cond: ImportCondition) -> None:
    """サイドバーの widget key に cond の値を書き込み、次回描画で反映させる.

    シナリオ読み込み時にこの関数を呼ぶことで、サイドバー全 widget の値が
    cond の内容に更新される。

    Args:
        cond: 書き込む輸入条件。

    Raises:
        ValueError: cond.name が既知のコンテナ条件名でない場合。
    """
    if cond.name not in _CONDITIONS:
        raise ValueError(f"Unknown condition name: {cond.name!r}")

    kp = cond.name.replace(" ", "_").replace("/", "_")

    # コンテナ選択 radio
    st.session_state["sidebar_container_radio"] = cond.name

    # 為替
    st.session_state[f"{kp}_internal_rate"] = cond.internal_rate
    st.session_state[f"{kp}_current_rate"] = cond.current_rate

    # マージン・ロス率・資材
    st.session_state[f"{kp}_margin_pct"] = cond.margin_pct
    st.session_state[f"{kp}_loss_rate_pct"] = cond.loss_rate_pct
    st.session_state[f"{kp}_material_lot"] = cond.material_lot
    st.session_state[f"{kp}_material_loss_pct"] = cond.material_loss_pct

    # 輸入パラメータ
    st.session_state[f"{kp}_freight"] = cond.overseas_freight_usd
    st.session_state[f"{kp}_insurance"] = cond.insurance_rate
    st.session_state[f"{kp}_tariff"] = cond.tariff_rate

    # 物流（単品/ギフト別）
    st.session_state[f"{kp}_io_fee_s"] = cond.logistics_single.io_fee
    st.session_state[f"{kp}_storage_fee_s"] = cond.logistics_single.storage_fee
    st.session_state[f"{kp}_storage_months_s"] = cond.logistics_single.storage_months
    st.session_state[f"{kp}_io_fee_g"] = cond.logistics_gift.io_fee
    st.session_state[f"{kp}_storage_fee_g"] = cond.logistics_gift.storage_fee
    st.session_state[f"{kp}_storage_months_g"] = cond.logistics_gift.storage_months

    # 輸入経費（単品）
    for key, val in _expenses_to_session_state_keys(
        cond.import_expenses_single, f"{kp}_exp_s"
    ).items():
        st.session_state[key] = val

    # 輸入経費（ギフト）
    for key, val in _expenses_to_session_state_keys(
        cond.import_expenses_gift, f"{kp}_exp_g"
    ).items():
        st.session_state[key] = val
