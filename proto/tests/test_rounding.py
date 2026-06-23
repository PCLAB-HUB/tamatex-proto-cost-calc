"""roundup_yen のテスト — Excel ROUNDUP 互換の境界挙動を検証."""

from __future__ import annotations

from proto.engine.rounding import roundup_yen


class TestRoundupYen:
    """roundup_yen の境界挙動."""

    def test_exact_boundary_no_float_inflation(self) -> None:
        """110 × 1.10 は float で 121.00000000000001。121 であるべき（122 ではない）."""
        assert roundup_yen(110.0 * (1.0 + 10.0 / 100.0)) == 121

    def test_rounds_up_real_fraction(self) -> None:
        """真に小数部があれば切り上げる."""
        assert roundup_yen(121.3) == 122
        assert roundup_yen(121.001) == 122

    def test_exact_integer_unchanged(self) -> None:
        """ちょうど整数なら据え置き."""
        assert roundup_yen(121.0) == 121
        assert roundup_yen(0.0) == 0

    def test_small_float_noise_absorbed(self) -> None:
        """9 桁以下の表現誤差は吸収して切り上げない."""
        assert roundup_yen(200.0000000001) == 200

    def test_genuine_sub_yen_still_rounds_up(self) -> None:
        """円未満でも真に超えていれば切り上げる."""
        assert roundup_yen(200.01) == 201

    def test_returns_int(self) -> None:
        """戻り値は int."""
        assert isinstance(roundup_yen(100.5), int)
