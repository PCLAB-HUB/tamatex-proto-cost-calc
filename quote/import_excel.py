"""原価計算書参考資料.xlsx の全商品データをツールにインポートする."""

import json
import sys
from pathlib import Path

import openpyxl
from openpyxl.utils import column_index_from_string

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quote.data.mock_data import seed_mock_data
from quote.engine.models import ContainerExpenses, GlobalParams, ProductInput
from quote.storage.db import init_db, save_quote

EXCEL_PATH = Path(__file__).resolve().parent.parent / "原価計算書参考資料.xlsx"
if not EXCEL_PATH.exists():
    EXCEL_PATH = Path("/Users/pclab/Desktop/Project/tamatex/原価計算書参考資料.xlsx")


def _col(letter):
    return column_index_from_string(letter)


def _val(ws, row, col_letter, default=None):
    v = ws.cell(row=row, column=_col(col_letter)).value
    return v if v is not None else default


def _float(ws, row, col_letter, default=0.0):
    v = ws.cell(row=row, column=_col(col_letter)).value
    if v is None:
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def _int(ws, row, col_letter, default=0):
    v = ws.cell(row=row, column=_col(col_letter)).value
    if v is None:
        return default
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return default


def import_all():
    print(f"Reading: {EXCEL_PATH}")
    wb = openpyxl.load_workbook(str(EXCEL_PATH), data_only=True)
    ws = wb.active

    seed_mock_data()
    init_db()

    products = []
    for row in range(9, 134):
        name = _val(ws, row, 'H')
        if not name:
            continue

        weight_g = _float(ws, row, 'M')
        momme = weight_g / 3.75 if weight_g > 0 else 0.0

        p = ProductInput(
            supplier=_val(ws, row, 'A', ''),
            inspection_pass=(_val(ws, row, 'B', '') == '○'),
            customer=_val(ws, row, 'C', ''),
            port=_val(ws, row, 'D', ''),
            delivery_to=_val(ws, row, 'E', ''),
            container_ft=_int(ws, row, 'F', 20),
            ship_to=_val(ws, row, 'G', ''),
            product_name=str(name),
            prototype_code=str(_val(ws, row, 'I', '')),
            item_type=_val(ws, row, 'J', ''),
            package_size_cm=_val(ws, row, 'K', ''),
            weight_momme=momme,
            weight_g=weight_g,
            fabric_quality=_val(ws, row, 'N', ''),
            method=_val(ws, row, 'O', ''),
            packing_quantity=_int(ws, row, 'P', 1),
            packing_size=_val(ws, row, 'Q', ''),
            container_load=_float(ws, row, 'R'),
            fob_usd=_float(ws, row, 'S'),
            other_processing_usd=_float(ws, row, 'T'),
            loss_rate=_float(ws, row, 'U'),
            charge_up_unit=_float(ws, row, 'V'),
            embroidery_per_1000=_float(ws, row, 'W', 0.03),
            stitch_count=_float(ws, row, 'X'),
            die_charge=_float(ws, row, 'Y'),
            inspection_jpy=_float(ws, row, 'AA'),
            packing_jpy=_float(ws, row, 'AB'),
            material_jpy=_float(ws, row, 'AC'),
            inspection_cny=_float(ws, row, 'AD'),
            packing_cny=_float(ws, row, 'AE'),
            material_cny=_float(ws, row, 'AF'),
            inspection_usd=_float(ws, row, 'AG'),
            packing_usd=_float(ws, row, 'AH'),
            material_usd=_float(ws, row, 'AI'),
            tariff_rate_override=_float(ws, row, 'AP'),
            ribbon=_float(ws, row, 'BH'),
            name_label_2=_float(ws, row, 'BI'),
            name_label_3=_float(ws, row, 'BJ'),
            seal_1=_float(ws, row, 'BK'),
            seal_2=_float(ws, row, 'BL'),
            tag=_float(ws, row, 'BM'),
            bag=_float(ws, row, 'BN'),
            other_material=_float(ws, row, 'BO'),
            material_freight=_float(ws, row, 'BP'),
            design_cost=_float(ws, row, 'BU'),
            jq_card=_float(ws, row, 'BV'),
            embroidery_card=_float(ws, row, 'BW'),
            print_unit_price=_float(ws, row, 'BX'),
            print_type_count=_float(ws, row, 'BY'),
            layout=_float(ws, row, 'CA'),
            name_plate=_float(ws, row, 'CB'),
            seal_plate=_float(ws, row, 'CC'),
            tab_plate=_float(ws, row, 'CD'),
            bag_plate=_float(ws, row, 'CE'),
            cardboard_plate=_float(ws, row, 'CF'),
            other_depreciation=_float(ws, row, 'CG'),
            sample_cost=_float(ws, row, 'CH'),
            quality_inspection=_float(ws, row, 'CI'),
            other_amortization=_float(ws, row, 'CJ'),
            logistics_cardboard=_float(ws, row, 'CN'),
            logistics_io_fee=_float(ws, row, 'CO'),
            logistics_storage_months=_float(ws, row, 'CP'),
            logistics_storage_fee=_float(ws, row, 'CQ'),
            logistics_slip_fee=_float(ws, row, 'CR'),
            logistics_freight=_float(ws, row, 'CS'),
            domestic_packing_qty=_int(ws, row, 'CV', 1),
            domestic_processing=_float(ws, row, 'CW'),
            domestic_material=_float(ws, row, 'CX'),
            domestic_cardboard=_float(ws, row, 'CY'),
            domestic_io=_float(ws, row, 'CZ'),
            domestic_storage_months=_float(ws, row, 'DA'),
            domestic_storage_fee=_float(ws, row, 'DB'),
            domestic_freight=_float(ws, row, 'DC'),
            quote_price=_float(ws, row, 'DH'),
            center_fee=_float(ws, row, 'DI'),
            rebate=_float(ws, row, 'DJ'),
            lot_per_color=_int(ws, row, 'DK'),
            num_colors=_int(ws, row, 'DL', 1),
            retail_price=_float(ws, row, 'DP'),
        )
        products.append(p)
        print(f"  Row {row}: {p.product_name} (FOB=${p.fob_usd}, 売価¥{p.quote_price})")

    params = GlobalParams(
        internal_rate=152.0,
        current_rate=152.0,
        overseas_freight_usd=240.0,
        cny_to_usd_rate=0.17,
        cny_to_jpy_rate=13.0,
        insurance_risk_rate=0.0018,
        tariff_rate=0.0,
        b_grade_loss_rate=0.01,
        sub_material_loss_rate=0.05,
        amortization_margin=0.05,
        margin=0.20,
        container_expenses=ContainerExpenses(
            cy_charge=30000.0,
            lss=0.0,
            lss_cic_usd=180.0,
            thc=36000.0,
            emc=3000.0,
            do_fee=5000.0,
            doc_fee=6000.0,
            customs_fee=11800.0,
            handling_fee=8000.0,
            drayage=50000.0,
            devanning=14000.0,
        ),
    )

    quote_id = save_quote(
        customer_id=1,
        staff_id=1,
        title="Excel全データ検証用（94商品）",
        products=products,
        params=params,
        notes="原価計算書参考資料.xlsx の Row 9-133 を全件インポート",
    )
    print(f"\n=== インポート完了 ===")
    print(f"商品数: {len(products)}")
    print(f"見積もりID: {quote_id}")
    print(f"ツールで「見積もり一覧」から開いて確認してください。")


if __name__ == "__main__":
    import_all()
