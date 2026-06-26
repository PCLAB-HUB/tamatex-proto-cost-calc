"""A案: Excelライクなテーブル中心ビュー."""

from __future__ import annotations

import pandas as pd
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
from quote.engine.calc import calculate
from quote.engine.models import GlobalParams, ProductInput


def _build_empty_row(idx: int) -> dict:
    return {
        "No": idx + 1,
        "品名": "",
        "仕入先": "SUNVIM",
        "揚地": "神戸経由",
        "納入先": "コーヨー",
        "出荷先": "関東",
        "コンテナ": 20,
        "手法": "コンテナ",
        "サイズ(cm)": "",
        "重量(g)": 0.0,
        "入数": 1,
        "積載量": 0.0,
        "FOB(USD)": 0.0,
        "加工賃(USD)": 0.0,
        "ロス率": 0.0,
        "関税率": "非課税",
        "見積売価(円)": 0.0,
        "ロット/色": 0,
        "配色": 1,
        "上代(円)": 0.0,
    }


def _row_to_product(row: dict) -> ProductInput | None:
    name = row.get("品名", "")
    if not name:
        return None
    tariff_val = TARIFF_RATES.get(row.get("関税率", "非課税"), 0.0)
    return ProductInput(
        product_name=name,
        supplier=row.get("仕入先", "SUNVIM"),
        port=row.get("揚地", "神戸経由"),
        delivery_to=row.get("納入先", "コーヨー"),
        ship_to=row.get("出荷先", "関東"),
        container_ft=int(row.get("コンテナ", 20)),
        method=row.get("手法", "コンテナ"),
        package_size_cm=row.get("サイズ(cm)", ""),
        weight_g=float(row.get("重量(g)", 0)),
        packing_quantity=int(row.get("入数", 1)),
        container_load=float(row.get("積載量", 0)),
        fob_usd=float(row.get("FOB(USD)", 0)),
        other_processing_usd=float(row.get("加工賃(USD)", 0)),
        loss_rate=float(row.get("ロス率", 0)),
        tariff_rate_override=tariff_val,
        quote_price=float(row.get("見積売価(円)", 0)),
        lot_per_color=int(row.get("ロット/色", 0)),
        num_colors=int(row.get("配色", 1)),
        retail_price=float(row.get("上代(円)", 0)),
    )


def _fmt_jpy(v: float) -> str:
    return f"¥{v:,.1f}"


def render_table_view(params: GlobalParams) -> None:
    """Excelライクなテーブルビューを描画."""

    if "table_rows" not in st.session_state:
        st.session_state.table_rows = 3

    rows = [_build_empty_row(i) for i in range(st.session_state.table_rows)]
    df = pd.DataFrame(rows)

    st.markdown(
        """
        <div style="background:#E8F0FE; padding:8px 16px; border-radius:6px;
                    margin-bottom:12px; font-size:0.85rem; color:#1F1F1F;">
            📋 <b>入力列</b>（白背景）にデータを入力してください。
            計算結果は右側に自動表示されます。
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_config = {
        "No": st.column_config.NumberColumn("No", width="small", disabled=True),
        "品名": st.column_config.TextColumn("品名", width="medium", required=True),
        "仕入先": st.column_config.SelectboxColumn("仕入先", options=SUPPLIERS, width="small"),
        "揚地": st.column_config.SelectboxColumn("揚地", options=PORTS, width="small"),
        "納入先": st.column_config.SelectboxColumn("納入先", options=DELIVERY_TO, width="small"),
        "出荷先": st.column_config.SelectboxColumn("出荷先", options=SHIP_TO, width="small"),
        "コンテナ": st.column_config.SelectboxColumn(
            "コンテナ", options=CONTAINER_FT, width="small"
        ),
        "手法": st.column_config.SelectboxColumn("手法", options=METHODS, width="small"),
        "サイズ(cm)": st.column_config.TextColumn("サイズ(cm)", width="medium"),
        "重量(g)": st.column_config.NumberColumn("重量(g)", format="%.1f", width="small"),
        "入数": st.column_config.NumberColumn("入数", width="small", min_value=1),
        "積載量": st.column_config.NumberColumn("積載量", format="%.0f", width="small"),
        "FOB(USD)": st.column_config.NumberColumn("FOB(USD)", format="%.3f", width="small"),
        "加工賃(USD)": st.column_config.NumberColumn("加工賃", format="%.2f", width="small"),
        "ロス率": st.column_config.NumberColumn("ロス率", format="%.2f", width="small"),
        "関税率": st.column_config.SelectboxColumn(
            "関税率", options=list(TARIFF_RATES.keys()), width="small"
        ),
        "見積売価(円)": st.column_config.NumberColumn("見積売価", format="%.0f", width="small"),
        "ロット/色": st.column_config.NumberColumn("ロット/色", format="%d", width="small"),
        "配色": st.column_config.NumberColumn("配色", format="%d", width="small", min_value=1),
        "上代(円)": st.column_config.NumberColumn("上代", format="%.0f", width="small"),
    }

    edited_df = st.data_editor(
        df,
        column_config=col_config,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="product_table",
    )

    # --- 計算結果 ---
    results_data = []
    total_sales = 0.0
    total_profit = 0.0

    for _, row in edited_df.iterrows():
        product = _row_to_product(row.to_dict())
        if product is None:
            continue
        result = calculate(product, params)
        r = result.pricing_with_amort
        results_data.append(
            {
                "品名": product.product_name,
                "原価": result.cost.product_cost,
                "試算売価": r.trial_price,
                "見積売価": r.quote_price,
                "歩積込": r.stepped_price,
                "粗利額/枚": r.gross_profit_unit,
                "粗利率": r.gross_profit_rate,
                "売上金額": r.sales_amount,
                "粗利金額": r.gross_profit_total,
            }
        )
        total_sales += r.sales_amount
        total_profit += r.gross_profit_total

    if results_data:
        st.markdown("---")
        st.markdown("### 📊 計算結果")

        result_df = pd.DataFrame(results_data)

        result_col_config = {
            "品名": st.column_config.TextColumn("品名", width="medium"),
            "原価": st.column_config.NumberColumn("原価", format="¥%.1f"),
            "試算売価": st.column_config.NumberColumn("試算売価", format="¥%.0f"),
            "見積売価": st.column_config.NumberColumn("見積売価", format="¥%.0f"),
            "歩積込": st.column_config.NumberColumn("歩積込", format="¥%.0f"),
            "粗利額/枚": st.column_config.NumberColumn("粗利/枚", format="¥%.1f"),
            "粗利率": st.column_config.NumberColumn("粗利率", format="%.1f%%"),
            "売上金額": st.column_config.NumberColumn("売上金額", format="¥%,.0f"),
            "粗利金額": st.column_config.NumberColumn("粗利金額", format="¥%,.0f"),
        }

        st.dataframe(
            result_df,
            column_config=result_col_config,
            use_container_width=True,
            hide_index=True,
        )

        avg_rate = total_profit / total_sales if total_sales > 0 else 0
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("売上合計", _fmt_jpy(total_sales))
        with c2:
            st.metric("粗利合計", _fmt_jpy(total_profit))
        with c3:
            st.metric("平均粗利率", f"{avg_rate * 100:.1f}%")
