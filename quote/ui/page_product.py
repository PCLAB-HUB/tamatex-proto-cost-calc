"""③ 商品計算シートページ — 1商品の原価計算詳細."""

from __future__ import annotations

import json
from dataclasses import asdict, fields as dc_fields

import streamlit as st

from quote.engine.calc import calculate
from quote.engine.models import GlobalParams, ProductInput
from quote.storage.db import get_quote, save_quote
from quote.ui.card_view import _render_product_card, _render_result_card


def render_product_page(
    quote_id: int, product_index: int, params: GlobalParams
) -> None:
    """1商品の計算シートを描画."""
    quote = get_quote(quote_id)
    if not quote:
        st.error("見積もりが見つかりません。")
        return

    items = quote.get("items", [])
    is_new = product_index < 0 or product_index >= len(items)

    if is_new:
        st.markdown(f"### 新規商品追加")
        st.caption(f"{quote['quote_number']} に商品を追加")
    else:
        item = items[product_index]
        st.markdown(f"### {item.get('product_name', '商品')} の計算シート")
        st.caption(f"{quote['quote_number']} — 商品 {product_index + 1}")

        _prefix = "card_0"
        if f"{_prefix}_loaded" not in st.session_state:
            valid_fields = {f.name for f in dc_fields(ProductInput)}
            for k, v in item.items():
                if k not in valid_fields:
                    continue
                sk = _field_to_session_key(_prefix, k)
                if sk:
                    st.session_state[sk] = _convert_value(k, v)

            from quote.data.defaults import TARIFF_RATES
            _tariff_reverse = {v: k for k, v in TARIFF_RATES.items()}
            tariff_val = float(item.get("tariff_rate_override") or 0)
            st.session_state[f"{_prefix}_tariff"] = _tariff_reverse.get(
                tariff_val, "非課税"
            )
            st.session_state[f"{_prefix}_loaded"] = True
            st.rerun()

    product = _render_product_card(0)

    if product is not None:
        result = calculate(product, params)
        if result.warnings:
            for w in result.warnings:
                st.warning(w)
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        _render_result_card(product.product_name, result)

    # 保存・戻るボタン
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if product and st.button("💾 保存して明細に戻る", type="primary", use_container_width=True):
            all_products = _load_all_products(quote)
            if is_new:
                all_products.append(product)
            else:
                # card_view が管理するフィールドのみ上書きし、
                # 管理外フィールド（charge_up_unit, die_charge, inspection_* 等）は元の値を保持する
                valid_fields_set = {f.name for f in dc_fields(ProductInput)}
                card_managed = set(_FIELD_MAP.keys()) | {"tariff_rate_override"}
                base = {k: v for k, v in items[product_index].items() if k in valid_fields_set}
                product_dict = asdict(product)
                for field in card_managed:
                    if field in product_dict:
                        base[field] = product_dict[field]
                all_products[product_index] = ProductInput(**base)
            save_quote(
                customer_id=quote["customer_id"],
                staff_id=quote["staff_id"],
                title=quote.get("title") or "",
                products=all_products,
                params=params,
                notes=quote.get("notes") or "",
                quote_id=quote_id,
            )
            st.session_state.page = "detail"
            st.session_state.pop(f"card_0_loaded", None)
            for k in list(st.session_state.keys()):
                if k.startswith("card_"):
                    del st.session_state[k]
            st.rerun()
    with c2:
        if st.button("← 明細に戻る（保存しない）", use_container_width=True):
            st.session_state.page = "detail"
            st.session_state.pop(f"card_0_loaded", None)
            for k in list(st.session_state.keys()):
                if k.startswith("card_"):
                    del st.session_state[k]
            st.rerun()


def _load_all_products(quote: dict) -> list[ProductInput]:
    from dataclasses import fields as dc_fields
    products = []
    valid_fields = {f.name for f in dc_fields(ProductInput)}
    for item in quote.get("items", []):
        filtered = {k: v for k, v in item.items() if k in valid_fields}
        products.append(ProductInput(**filtered))
    return products


_FIELD_MAP = {
    "product_name": "name",
    "prototype_code": "code",
    "package_size_cm": "size",
    "weight_g": "wt",
    "packing_quantity": "pk",
    "container_load": "ld",
    "fob_usd": "fob",
    "other_processing_usd": "op",
    "loss_rate": "loss",
    "quote_price": "qp",
    "lot_per_color": "lot",
    "num_colors": "col",
    "retail_price": "ret",
    "logistics_io_fee": "lio",
    "logistics_slip_fee": "lsl",
    "logistics_storage_months": "lm",
    "logistics_storage_fee": "lf",
    "logistics_freight": "lr",
    "logistics_cardboard": "lcb",
    "center_fee": "cf",
    "rebate": "rebate",
    "ribbon": "ribbon",
    "name_label_2": "nl2",
    "name_label_3": "nl3",
    "seal_1": "seal1",
    "seal_2": "seal2",
    "tag": "tag",
    "bag": "bag",
    "other_material": "omat",
    "material_freight": "matfr",
    "design_cost": "design",
    "jq_card": "jqc",
    "embroidery_card": "embc",
    "print_unit_price": "prup",
    "print_type_count": "prcnt",
    "layout": "layout",
    "name_plate": "namepl",
    "seal_plate": "sealpl",
    "tab_plate": "tabpl",
    "bag_plate": "bagpl",
    "cardboard_plate": "cbpl",
    "other_depreciation": "odep",
    "sample_cost": "sample",
    "quality_inspection": "qinsp",
    "other_amortization": "oamort",
}


def _field_to_session_key(prefix: str, field_name: str) -> str | None:
    short = _FIELD_MAP.get(field_name)
    if short:
        return f"{prefix}_{short}"
    return None


def _convert_value(field_name: str, value):
    if value is None:
        return 0.0 if field_name not in ("product_name", "prototype_code", "package_size_cm") else ""
    if field_name in ("product_name", "prototype_code", "package_size_cm"):
        return str(value)
    if field_name in ("packing_quantity", "lot_per_color", "num_colors"):
        return int(float(value))
    return float(value)
