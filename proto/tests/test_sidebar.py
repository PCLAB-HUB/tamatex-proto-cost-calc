"""sidebar.py のユニットテスト.

Streamlit の描画処理には依存しない純粋関数のみをテスト対象とする。
`_expenses_to_session_state_keys` と `apply_condition_to_session_state` の
キー名・値の整合性を検証する。
"""

from __future__ import annotations

import pytest

from proto.data.mock_params import COND_20FT, COND_40FT
from proto.engine.models import ImportCondition, ImportExpenses
from proto.ui.sidebar import _expenses_to_session_state_keys


# ---------------------------------------------------------------------------
# _expenses_to_session_state_keys
# ---------------------------------------------------------------------------


class TestExpensesToSessionStateKeys:
    """_expenses_to_session_state_keys の返却辞書を検証する."""

    def _make_expenses(self) -> ImportExpenses:
        return ImportExpenses(
            cic_usd=100.0,
            cy_charge=10000.0,
            thc=20000.0,
            emc=3000.0,
            cic2=5000.0,
            do_fee=2000.0,
            doc_fee=4000.0,
            customs_fee=8000.0,
            handling_fee=6000.0,
            drayage=15000.0,
            devanning=9000.0,
        )

    def test_returns_eleven_keys(self) -> None:
        """11 項目すべてのキーを返すことを確認する."""
        exp = self._make_expenses()
        result = _expenses_to_session_state_keys(exp, "prefix")
        assert len(result) == 11

    def test_key_names_use_prefix(self) -> None:
        """すべてのキーが指定プレフィックスで始まることを確認する."""
        exp = self._make_expenses()
        prefix = "20FT_大阪_今治_exp_s"
        result = _expenses_to_session_state_keys(exp, prefix)
        for key in result:
            assert key.startswith(prefix), f"Key {key!r} does not start with {prefix!r}"

    def test_values_match_expenses_fields(self) -> None:
        """各キーの値が ImportExpenses フィールドと一致することを確認する."""
        exp = self._make_expenses()
        prefix = "pfx"
        result = _expenses_to_session_state_keys(exp, prefix)

        assert result[f"{prefix}_cic_usd"] == exp.cic_usd
        assert result[f"{prefix}_cy"] == exp.cy_charge
        assert result[f"{prefix}_thc"] == exp.thc
        assert result[f"{prefix}_emc"] == exp.emc
        assert result[f"{prefix}_cic2"] == exp.cic2
        assert result[f"{prefix}_do"] == exp.do_fee
        assert result[f"{prefix}_doc"] == exp.doc_fee
        assert result[f"{prefix}_customs"] == exp.customs_fee
        assert result[f"{prefix}_handling"] == exp.handling_fee
        assert result[f"{prefix}_drayage"] == exp.drayage
        assert result[f"{prefix}_devanning"] == exp.devanning

    def test_cond_20ft_single_prefix(self) -> None:
        """COND_20FT の単品経費プレフィックスが正しく展開されることを確認する."""
        kp = COND_20FT.name.replace(" ", "_").replace("/", "_")
        prefix = f"{kp}_exp_s"
        result = _expenses_to_session_state_keys(COND_20FT.import_expenses_single, prefix)

        assert result[f"{prefix}_cic_usd"] == COND_20FT.import_expenses_single.cic_usd
        assert result[f"{prefix}_drayage"] == COND_20FT.import_expenses_single.drayage
        assert result[f"{prefix}_devanning"] == COND_20FT.import_expenses_single.devanning

    def test_cond_20ft_gift_devanning_value(self) -> None:
        """COND_20FT のギフト経費（デバン料あり）が正しく変換されることを確認する."""
        kp = COND_20FT.name.replace(" ", "_").replace("/", "_")
        prefix = f"{kp}_exp_g"
        result = _expenses_to_session_state_keys(COND_20FT.import_expenses_gift, prefix)

        # ギフト用はデバン料 19200.0
        assert result[f"{prefix}_devanning"] == 19200.0

    def test_different_prefixes_do_not_collide(self) -> None:
        """異なるプレフィックスのキーが衝突しないことを確認する."""
        exp = self._make_expenses()
        result_s = _expenses_to_session_state_keys(exp, "cond_exp_s")
        result_g = _expenses_to_session_state_keys(exp, "cond_exp_g")

        assert set(result_s.keys()).isdisjoint(set(result_g.keys()))


# ---------------------------------------------------------------------------
# apply_condition_to_session_state — バリデーションのテスト
# (Streamlit session_state への書き込みは統合テスト対象のため、ここでは
#  ValueError 送出のみをテストする。)
# ---------------------------------------------------------------------------


class TestApplyConditionValidation:
    """apply_condition_to_session_state のバリデーション検証."""

    def test_raises_value_error_for_unknown_condition_name(self) -> None:
        """未知の条件名を持つ ImportCondition を渡すと ValueError が送出されることを確認する."""
        from proto.ui.sidebar import apply_condition_to_session_state

        # COND_20FT の条件名を書き換えて未知の名前にする
        unknown_cond = ImportCondition(
            name="UNKNOWN_CONDITION",
            internal_rate=150.0,
            current_rate=150.0,
            loss_rate_pct=15.0,
            margin_pct=40.0,
            material_lot=3000,
            material_loss_pct=3.0,
            emb_general=0.0,
            emb_silver=0.0,
            emb_ket=0.0,
            emb_brand=0.0,
            overseas_freight_usd=160.0,
            insurance_rate=0.0018,
            tariff_rate=0.074,
            import_expenses_single=COND_20FT.import_expenses_single,
            import_expenses_gift=COND_20FT.import_expenses_gift,
            io_fee=70.0,
            storage_fee=120.0,
            storage_months=0.0,
        )

        with pytest.raises(ValueError, match="Unknown condition name"):
            apply_condition_to_session_state(unknown_cond)

    def test_known_condition_names_are_accepted(self) -> None:
        """既知のコンテナ条件名（20FT / 40FT）は ValueError を送出しないことを確認する.

        session_state への書き込みは Streamlit 実行環境が必要なため、ここでは
        ValueError が送出されないことのみ検証する。
        """
        from unittest.mock import MagicMock, patch

        from proto.ui.sidebar import apply_condition_to_session_state

        mock_ss: dict[str, object] = {}
        with patch("streamlit.session_state", mock_ss):
            # ValueError が送出されなければ合格
            apply_condition_to_session_state(COND_20FT)
            apply_condition_to_session_state(COND_40FT)

    def test_session_state_keys_set_for_20ft(self) -> None:
        """COND_20FT を渡したとき、期待する widget key が session_state に書き込まれることを確認する."""
        from unittest.mock import patch

        from proto.ui.sidebar import apply_condition_to_session_state

        mock_ss: dict[str, object] = {}
        with patch("streamlit.session_state", mock_ss):
            apply_condition_to_session_state(COND_20FT)

        kp = COND_20FT.name.replace(" ", "_").replace("/", "_")

        # コンテナ radio
        assert mock_ss["sidebar_container_radio"] == COND_20FT.name

        # 為替
        assert mock_ss[f"{kp}_internal_rate"] == COND_20FT.internal_rate
        assert mock_ss[f"{kp}_current_rate"] == COND_20FT.current_rate

        # マージン系
        assert mock_ss[f"{kp}_margin_pct"] == COND_20FT.margin_pct
        assert mock_ss[f"{kp}_loss_rate_pct"] == COND_20FT.loss_rate_pct
        assert mock_ss[f"{kp}_material_lot"] == COND_20FT.material_lot
        assert mock_ss[f"{kp}_material_loss_pct"] == COND_20FT.material_loss_pct

        # 輸入パラメータ
        assert mock_ss[f"{kp}_freight"] == COND_20FT.overseas_freight_usd
        assert mock_ss[f"{kp}_insurance"] == COND_20FT.insurance_rate
        assert mock_ss[f"{kp}_tariff"] == COND_20FT.tariff_rate

        # 物流
        assert mock_ss[f"{kp}_io_fee"] == COND_20FT.io_fee
        assert mock_ss[f"{kp}_storage_fee"] == COND_20FT.storage_fee
        assert mock_ss[f"{kp}_storage_months"] == COND_20FT.storage_months

        # 輸入経費（単品）
        assert mock_ss[f"{kp}_exp_s_cic_usd"] == COND_20FT.import_expenses_single.cic_usd
        assert mock_ss[f"{kp}_exp_s_devanning"] == COND_20FT.import_expenses_single.devanning

        # 輸入経費（ギフト）
        assert mock_ss[f"{kp}_exp_g_cic_usd"] == COND_20FT.import_expenses_gift.cic_usd
        assert mock_ss[f"{kp}_exp_g_devanning"] == COND_20FT.import_expenses_gift.devanning

    def test_session_state_key_count_for_20ft(self) -> None:
        """COND_20FT を渡したとき書き込まれる widget key の総数を確認する.

        期待値: 1(radio) + 2(為替) + 4(マージン系) + 3(輸入) + 3(物流)
                + 11(単品経費) + 11(ギフト経費) = 35
        """
        from unittest.mock import patch

        from proto.ui.sidebar import apply_condition_to_session_state

        mock_ss: dict[str, object] = {}
        with patch("streamlit.session_state", mock_ss):
            apply_condition_to_session_state(COND_20FT)

        assert len(mock_ss) == 35
