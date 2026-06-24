"""Smoke test — UI モジュールと ScenarioRepository の基本動作.

Streamlit ランタイムに依存する render_* 関数の実行テストは行わない。
import 成功と hasattr チェック、および純粋な Python コード（ScenarioRepository）の
CRUD 動作のみを検証する。
"""

from __future__ import annotations

from pathlib import Path

import pytest


def test_all_ui_modules_import() -> None:
    """全 UI モジュールが ImportError なく読み込めることを確認する."""
    from proto.ui import (  # noqa: F401
        dashboard,
        scenarios,
        section_basic,
        section_gift,
        section_items,
        section_result,
        section_verify,
        sidebar,
    )
    from proto.ui.components import (  # noqa: F401
        aggrid_table,
        kpi_cards,
        sensitivity_chart,
        styles,
    )

    # 公開 API が存在することを確認
    assert callable(dashboard.render_dashboard)
    assert callable(scenarios.render_scenarios)
    assert callable(sidebar.render_sidebar)
    assert callable(sidebar.apply_condition_to_session_state)
    assert callable(section_basic.render_basic_info)
    assert callable(section_items.render_items)
    assert callable(section_gift.render_gifts)
    assert callable(section_result.render_results)
    assert callable(section_verify.render_verify)


def test_scenario_repo_crud(tmp_path: Path) -> None:
    """ScenarioRepository の保存・取得・削除の基本動作を検証する."""
    from proto.data.mock_params import COND_20FT
    from proto.storage.scenario_repo import ScenarioRepository

    repo = ScenarioRepository(tmp_path / "smoke.db")
    try:
        # 保存
        sid = repo.save_scenario("smoke_test", COND_20FT)
        assert isinstance(sid, int)
        assert sid > 0

        # 取得
        scenario = repo.get_scenario(sid)
        assert scenario.name == "smoke_test"
        assert scenario.condition == COND_20FT

        # 一覧
        metas = repo.list_scenarios()
        assert len(metas) == 1
        assert metas[0].id == sid

        # 削除
        repo.delete_scenario(sid)
        assert len(repo.list_scenarios()) == 0
    finally:
        repo.close()


def test_app_main_can_be_imported() -> None:
    """proto.app が ImportError なく読み込め、main と get_scenario_repo が存在する."""
    import proto.app

    assert hasattr(proto.app, "main")
    assert callable(proto.app.main)
    assert hasattr(proto.app, "get_scenario_repo")
    assert callable(proto.app.get_scenario_repo)
