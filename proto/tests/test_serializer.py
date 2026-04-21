"""シリアライザのラウンドトリップテスト.

`condition_to_json` → `condition_from_json` の往復で
元の ImportCondition と完全一致することを確認する。
"""

from __future__ import annotations

import json

import pytest

from proto.data.mock_params import COND_20FT, COND_40FT
from proto.engine.models import ImportCondition, ImportExpenses
from proto.storage.serializer import condition_from_json, condition_to_json


# ---------------------------------------------------------------------------
# ラウンドトリップテスト
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """condition_to_json ⇄ condition_from_json の往復整合性."""

    def test_roundtrip_cond_20ft(self) -> None:
        """COND_20FT が JSON 往復後も等価であること."""
        result = condition_from_json(condition_to_json(COND_20FT))
        assert result == COND_20FT

    def test_roundtrip_cond_40ft(self) -> None:
        """COND_40FT が JSON 往復後も等価であること."""
        result = condition_from_json(condition_to_json(COND_40FT))
        assert result == COND_40FT

    def test_roundtrip_custom_condition(self) -> None:
        """全フィールドを書き換えたカスタム ImportCondition のラウンドトリップ."""
        custom_single = ImportExpenses(
            cic_usd=999.9,
            cy_charge=10000.0,
            thc=20000.0,
            emc=1500.0,
            cic2=5000.0,
            do_fee=2500.0,
            doc_fee=3000.0,
            customs_fee=7000.0,
            handling_fee=4000.0,
            drayage=25000.0,
            devanning=9999.0,
        )
        custom_gift = ImportExpenses(
            cic_usd=888.8,
            cy_charge=11000.0,
            thc=22000.0,
            emc=1600.0,
            cic2=6000.0,
            do_fee=2600.0,
            doc_fee=3100.0,
            customs_fee=7100.0,
            handling_fee=4100.0,
            drayage=26000.0,
            devanning=8888.0,
        )
        custom_cond = ImportCondition(
            name="カスタム条件テスト",
            internal_rate=145.0,
            current_rate=148.5,
            loss_rate_pct=12.0,
            margin_pct=35.0,
            material_lot=5000,
            material_loss_pct=2.5,
            emb_general=1.5,
            emb_silver=2.5,
            emb_ket=3.5,
            emb_brand=4.5,
            overseas_freight_usd=200.0,
            insurance_rate=0.002,
            tariff_rate=0.08,
            import_expenses_single=custom_single,
            import_expenses_gift=custom_gift,
            io_fee=90.0,
            storage_fee=150.0,
            storage_months=3.0,
        )

        result = condition_from_json(condition_to_json(custom_cond))
        assert result == custom_cond


# ---------------------------------------------------------------------------
# condition_to_json の出力形式検証
# ---------------------------------------------------------------------------


class TestToJson:
    """condition_to_json の出力フォーマット確認."""

    def test_output_is_valid_json_string(self) -> None:
        """出力が有効な JSON 文字列であること."""
        s = condition_to_json(COND_20FT)
        assert isinstance(s, str)
        parsed = json.loads(s)
        assert isinstance(parsed, dict)

    def test_japanese_characters_not_escaped(self) -> None:
        """日本語文字が Unicode エスケープされずそのまま出力されること."""
        s = condition_to_json(COND_20FT)
        assert "20FT 大阪/今治" in s

    def test_nested_expenses_serialized_as_dict(self) -> None:
        """ネストされた ImportExpenses が dict として出力されること."""
        s = condition_to_json(COND_20FT)
        parsed = json.loads(s)
        assert isinstance(parsed["import_expenses_single"], dict)
        assert isinstance(parsed["import_expenses_gift"], dict)

    def test_all_expenses_fields_present(self) -> None:
        """ImportExpenses の 11 フィールドが全て JSON に含まれること."""
        s = condition_to_json(COND_20FT)
        parsed = json.loads(s)
        expense_fields = {
            "cic_usd", "cy_charge", "thc", "emc", "cic2",
            "do_fee", "doc_fee", "customs_fee", "handling_fee",
            "drayage", "devanning",
        }
        assert expense_fields == set(parsed["import_expenses_single"].keys())
        assert expense_fields == set(parsed["import_expenses_gift"].keys())


# ---------------------------------------------------------------------------
# condition_from_json のエラーハンドリング
# ---------------------------------------------------------------------------


class TestFromJsonErrors:
    """condition_from_json の異常系."""

    def test_missing_field_raises_type_error(self) -> None:
        """必須フィールドが欠けた JSON は TypeError/KeyError を送出すること."""
        incomplete_json = '{"name": "テスト"}'
        with pytest.raises((KeyError, TypeError)):
            condition_from_json(incomplete_json)

    def test_invalid_json_raises_json_decode_error(self) -> None:
        """不正な JSON 文字列は json.JSONDecodeError を送出すること."""
        with pytest.raises(json.JSONDecodeError):
            condition_from_json("not a json string")
