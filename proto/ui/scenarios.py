"""シナリオ管理タブ — 一覧・CRUD・横並び比較.

公開 API:
    render_scenarios(cond, items, item_results, gifts, gift_results, repo)

内部ヘルパ（プライベート）:
    _render_save_form        — 新規保存フォーム
    _render_list_table       — シナリオ一覧 aggrid
    _render_action_buttons   — 読み込み/複製/リネーム/削除/比較 ボタン群
    _render_compare_view     — 2件横並び比較ビュー
    _render_scenario_column  — 比較ビューの1カラム分
    _load_scenario_into_sidebar  — 読み込み時のsession_state復元
    _unique_copy_name        — 複製名の衝突回避
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from proto.engine.calc_gift import calc_gift_set
from proto.engine.calc_single import calc_single_item
from proto.engine.models import (
    GiftSet,
    GiftSetResult,
    ImportCondition,
    SingleItem,
    SingleItemResult,
)
from proto.storage.scenario_repo import (
    ScenarioNameConflictError,
    ScenarioNotFoundError,
    ScenarioRepository,
)
from proto.ui.components.aggrid_table import (
    create_aggrid,
    currency_column,
    number_column,
    percent_column,
    text_column,
)
from proto.ui.components.kpi_cards import (
    KPICardData,
    format_currency,
    format_delta,
    format_percentage,
    render_kpi_row,
)
from proto.ui.sidebar import apply_condition_to_session_state


# ---------------------------------------------------------------------------
# 内部ユーティリティ
# ---------------------------------------------------------------------------


def _unique_copy_name(base_name: str, repo: ScenarioRepository) -> str:
    """複製時に衝突しない名前を生成する。

    `{base_name}_コピー` から始め、衝突すれば `_コピー2`, `_コピー3` ... と連番を付ける。

    Args:
        base_name: コピー元のシナリオ名。
        repo: 名前存在確認に使用するリポジトリ。

    Returns:
        既存シナリオと衝突しないシナリオ名。
    """
    candidate = f"{base_name}_コピー"
    if not repo.scenario_exists(candidate):
        return candidate
    counter = 2
    while repo.scenario_exists(f"{base_name}_コピー{counter}"):
        counter += 1
    return f"{base_name}_コピー{counter}"


# ---------------------------------------------------------------------------
# session_state 復元ヘルパ
# ---------------------------------------------------------------------------


def _load_scenario_into_sidebar(loaded_cond: ImportCondition) -> None:
    """シナリオの ImportCondition をサイドバー widget の session_state に書き込む。

    サイドバー側 (#9) の ``apply_condition_to_session_state()`` を呼び出して
    全 widget key（基本12 + 輸入経費11×2 + コンテナradio = 35キー）を統一的に
    復元する。単一ソース方式で sidebar.py と scenarios.py の重複を排除。

    Args:
        loaded_cond: 読み込むシナリオの輸入条件。
    """
    apply_condition_to_session_state(loaded_cond)
    st.toast(f"シナリオ '{loaded_cond.name}' を読み込みました")


# ---------------------------------------------------------------------------
# 保存フォーム
# ---------------------------------------------------------------------------


def _render_save_form(cond: ImportCondition, repo: ScenarioRepository) -> None:
    """現在の条件を新規シナリオとして保存するフォームを描画する。

    同名シナリオが存在する場合はエラーメッセージを表示する。保存成功後は
    ``st.rerun()`` で一覧を更新する。

    Args:
        cond: 現在のサイドバー輸入条件。
        repo: シナリオリポジトリ。
    """
    with st.expander("➕ 現在の条件を新規保存", expanded=False):
        default_name = (
            f"{cond.name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}"
        )
        name = st.text_input(
            "シナリオ名",
            value=default_name,
            key="new_scenario_name",
        )
        if st.button("保存", key="btn_save_scenario"):
            stripped = name.strip()
            if not stripped:
                st.error("名前を入力してください")
                return
            try:
                sid = repo.save_scenario(stripped, cond)
                st.success(f"シナリオ '{stripped}' を保存しました (id={sid})")
                st.rerun()
            except ScenarioNameConflictError:
                st.error(f"この名前は既に使われています: {stripped}")


# ---------------------------------------------------------------------------
# 一覧テーブル
# ---------------------------------------------------------------------------


def _render_list_table(repo: ScenarioRepository) -> list[dict]:
    """シナリオ一覧を aggrid で描画し、選択行を返す。

    シナリオが 0 件の場合は info メッセージを表示して空リストを返す。

    Args:
        repo: シナリオリポジトリ。

    Returns:
        選択された行データの list[dict]。未選択の場合は空リスト。
    """
    metas = repo.list_scenarios()
    if not metas:
        st.info("保存されたシナリオはありません。現在の条件を保存してください。")
        return []

    df = pd.DataFrame(
        [
            {
                "id": m.id,
                "名前": m.name,
                "作成日時": m.created_at[:19].replace("T", " "),
                "更新日時": m.updated_at[:19].replace("T", " "),
            }
            for m in metas
        ]
    )
    result = create_aggrid(
        df,
        column_defs=[
            text_column("名前", "名前", width=240),
            text_column("作成日時", "作成日時", width=160),
            text_column("更新日時", "更新日時", width=160),
        ],
        selection="multiple",
        height=280,
    )
    # selected_rows は AgGrid バージョンによって list[dict] または pd.DataFrame を返す
    rows = result.selected_rows
    if rows is None:
        return []
    if isinstance(rows, pd.DataFrame):
        return rows.to_dict("records")
    return list(rows)


# ---------------------------------------------------------------------------
# アクションハンドラ
# ---------------------------------------------------------------------------


def _handle_duplicate(
    repo: ScenarioRepository, sid: int, orig_name: str
) -> None:
    """複製処理 — 新名前入力と実行ボタンを session_state で管理する。

    Args:
        repo: シナリオリポジトリ。
        sid: コピー元シナリオ ID。
        orig_name: コピー元シナリオ名。
    """
    default_copy_name = _unique_copy_name(orig_name, repo)
    new_name = st.text_input(
        "複製後の名前",
        value=default_copy_name,
        key="duplicate_name_input",
    )
    if st.button("複製を実行", key="btn_duplicate_confirm"):
        stripped = new_name.strip()
        if not stripped:
            st.error("名前を入力してください")
            return
        try:
            new_id = repo.duplicate_scenario(sid, stripped)
            st.success(f"'{orig_name}' を '{stripped}' として複製しました (id={new_id})")
            # 複製完了後に pending フラグをクリアして一覧更新
            st.session_state.pop("pending_action", None)
            st.rerun()
        except ScenarioNameConflictError:
            st.error(f"この名前は既に使われています: {stripped}")
        except ScenarioNotFoundError:
            st.error(f"コピー元シナリオ (id={sid}) が見つかりません")


def _handle_rename(
    repo: ScenarioRepository, sid: int, orig_name: str
) -> None:
    """リネーム処理 — 新名前入力と実行ボタンを session_state で管理する。

    Args:
        repo: シナリオリポジトリ。
        sid: リネーム対象シナリオ ID。
        orig_name: 現在のシナリオ名。
    """
    new_name = st.text_input(
        "新しい名前",
        value=orig_name,
        key="rename_input",
    )
    if st.button("リネームを実行", key="btn_rename_confirm"):
        stripped = new_name.strip()
        if not stripped:
            st.error("名前を入力してください")
            return
        if stripped == orig_name:
            st.warning("名前が変わっていません")
            return
        try:
            repo.update_scenario(sid, name=stripped)
            st.success(f"'{orig_name}' を '{stripped}' にリネームしました")
            st.session_state.pop("pending_action", None)
            st.rerun()
        except ScenarioNameConflictError:
            st.error(f"この名前は既に使われています: {stripped}")
        except ScenarioNotFoundError:
            st.error(f"シナリオ (id={sid}) が見つかりません")


def _handle_delete(
    repo: ScenarioRepository, sid: int, name: str
) -> None:
    """削除処理 — 確認チェックボックスで誤操作を防ぐ。

    Args:
        repo: シナリオリポジトリ。
        sid: 削除対象シナリオ ID。
        name: 削除対象シナリオ名（確認メッセージに使用）。
    """
    confirmed = st.checkbox(
        f"'{name}' を削除してよいですか？（この操作は元に戻せません）",
        key="delete_confirm_checkbox",
    )
    if st.button("削除を実行", disabled=not confirmed, key="btn_delete_confirm"):
        repo.delete_scenario(sid)
        st.success(f"シナリオ '{name}' を削除しました")
        st.session_state.pop("pending_action", None)
        st.rerun()


# ---------------------------------------------------------------------------
# アクションボタン群
# ---------------------------------------------------------------------------


def _render_action_buttons(
    selected: list[dict],
    repo: ScenarioRepository,
) -> None:
    """読み込み / 複製 / リネーム / 削除 / 比較 ボタンを描画する。

    各ボタンの活性状態:
        - 読み込み / 複製 / リネーム / 削除: 1件選択時のみ活性
        - 比較: 2件選択時のみ活性

    ボタンクリックで ``st.session_state["pending_action"]`` にアクション種別を
    セットし、後続の expander でフォームを表示する。

    Args:
        selected: 選択されたシナリオ行データのリスト。
        repo: シナリオリポジトリ（読み込み処理に使用）。
    """
    single = len(selected) == 1
    double = len(selected) == 2

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        if st.button("📂 読み込み", disabled=not single, key="btn_load"):
            try:
                scenario = repo.get_scenario(selected[0]["id"])
                _load_scenario_into_sidebar(scenario.condition)
                st.rerun()
            except ScenarioNotFoundError:
                st.error(f"シナリオ (id={selected[0]['id']}) が見つかりません")

    with col2:
        if st.button("📋 複製", disabled=not single, key="btn_duplicate"):
            st.session_state["pending_action"] = "duplicate"

    with col3:
        if st.button("✏️ リネーム", disabled=not single, key="btn_rename"):
            st.session_state["pending_action"] = "rename"

    with col4:
        if st.button("🗑️ 削除", disabled=not single, key="btn_delete"):
            st.session_state["pending_action"] = "delete"

    with col5:
        if st.button("📊 比較", disabled=not double, key="btn_compare"):
            st.session_state["compare_ids"] = [s["id"] for s in selected]
            # 比較ビューを表示するため pending_action はクリア
            st.session_state.pop("pending_action", None)

    # --- ペンディングアクションのフォーム表示 ---
    pending = st.session_state.get("pending_action")
    if pending and single:
        sid = selected[0]["id"]
        orig_name = selected[0]["名前"]
        with st.container():
            st.divider()
            if pending == "duplicate":
                st.subheader("📋 複製")
                _handle_duplicate(repo, sid, orig_name)
            elif pending == "rename":
                st.subheader("✏️ リネーム")
                _handle_rename(repo, sid, orig_name)
            elif pending == "delete":
                st.subheader("🗑️ 削除")
                _handle_delete(repo, sid, orig_name)


# ---------------------------------------------------------------------------
# 比較ビュー
# ---------------------------------------------------------------------------


def _build_items_compare_df(
    items: dict[str, SingleItem],
    results: dict[str, SingleItemResult],
) -> pd.DataFrame:
    """比較ビュー用の品目別原価 DataFrame を構築する。

    Args:
        items: 品番 -> SingleItem のマッピング。
        results: 品番 -> SingleItemResult のマッピング。

    Returns:
        品番・品名・円建原価・製造原価・物流/個 の列を持つ DataFrame。
    """
    rows = []
    for item_no, item in items.items():
        r = results[item_no]
        rows.append(
            {
                "品番": item_no,
                "品名": item.name,
                "円建原価": r.jpy_cost,
                "製造原価": r.manufacturing_cost,
                "物流/個": r.logistics_cost,
            }
        )
    return pd.DataFrame(rows)


def _build_gifts_compare_df(
    gifts: list[GiftSet],
    results: list[GiftSetResult],
) -> pd.DataFrame:
    """比較ビュー用のギフトセット DataFrame を構築する。

    Args:
        gifts: GiftSet のリスト。
        results: GiftSetResult のリスト（gifts と同順）。

    Returns:
        セット名・見積単価・製造原価・粗利率 の列を持つ DataFrame。
    """
    rows = []
    for gift, r in zip(gifts, results):
        rows.append(
            {
                "セット名": gift.name,
                "見積単価": r.quote_price,
                "製造原価": r.manufacturing_cost,
                "粗利率": r.gross_profit_rate * 100.0,  # 0-1 -> 0-100 に変換
            }
        )
    return pd.DataFrame(rows)


def _calc_avg_jpy_cost(results: dict[str, SingleItemResult]) -> float:
    """単品結果の平均円建原価を計算する。

    Args:
        results: 品番 -> SingleItemResult のマッピング。

    Returns:
        平均円建原価（0件の場合は 0.0）。
    """
    if not results:
        return 0.0
    return sum(r.jpy_cost for r in results.values()) / len(results)


def _calc_avg_retail(gifts: list[GiftSet]) -> float:
    """ギフトセットの平均上代を計算する。

    Args:
        gifts: GiftSet のリスト。

    Returns:
        平均上代（0件の場合は 0.0）。
    """
    if not gifts:
        return 0.0
    return sum(g.retail_price for g in gifts) / len(gifts)


def _calc_avg_gross_profit_rate(results: list[GiftSetResult]) -> float:
    """ギフトセット結果の平均粗利率を計算する。

    Args:
        results: GiftSetResult のリスト。

    Returns:
        平均粗利率（0〜1 の小数）（0件の場合は 0.0）。
    """
    if not results:
        return 0.0
    return sum(r.gross_profit_rate for r in results) / len(results)


def _render_scenario_column(
    scenario_name: str,
    condition: ImportCondition,
    item_results: dict[str, SingleItemResult],
    gift_results: list[GiftSetResult],
    items: dict[str, SingleItem],
    gifts: list[GiftSet],
    *,
    baseline_item_results: dict[str, SingleItemResult] | None,
    baseline_gift_results: list[GiftSetResult] | None,
) -> None:
    """比較ビューの1カラム分を描画する。

    KPI カード 3 枚（平均原価・平均上代・平均粗利率）と
    品目別原価テーブル・ギフトセットテーブルを表示する。

    Args:
        scenario_name: シナリオ名（カラムヘッダに表示）。
        condition: シナリオの輸入条件。
        item_results: 品番 -> SingleItemResult のマッピング。
        gift_results: GiftSetResult のリスト。
        items: 品番 -> SingleItem のマッピング。
        gifts: GiftSet のリスト。
        baseline_item_results: 差分計算の基準となる item_results（左カラムの値）。
            None の場合は delta を表示しない（左カラム自体の描画時）。
        baseline_gift_results: 差分計算の基準となる gift_results。
            None の場合は delta を表示しない。
    """
    st.markdown(f"### {scenario_name}")
    st.caption(
        f"コンテナ: {condition.name} | "
        f"社内為替: {condition.internal_rate:.0f} 円/$ | "
        f"マージン: {condition.margin_pct:.1f}%"
    )

    avg_cost = _calc_avg_jpy_cost(item_results)
    avg_retail = _calc_avg_retail(gifts)
    avg_gpr = _calc_avg_gross_profit_rate(gift_results)

    # --- delta 計算 ---
    delta_cost: str | None = None
    delta_retail: str | None = None
    delta_gpr: str | None = None

    if baseline_item_results is not None:
        base_cost = _calc_avg_jpy_cost(baseline_item_results)
        delta_cost = format_delta(avg_cost, base_cost, is_currency=True)

    if baseline_gift_results is not None:
        base_retail = _calc_avg_retail(gifts)  # 上代はギフトマスタ固定なので同値
        delta_retail = format_delta(avg_retail, base_retail, is_currency=True)
        base_gpr = _calc_avg_gross_profit_rate(baseline_gift_results)
        delta_gpr = format_delta(avg_gpr * 100.0, base_gpr * 100.0)

    # --- KPI カード ---
    cards = [
        KPICardData(
            label="平均円建原価",
            value=format_currency(avg_cost),
            delta=delta_cost,
            delta_color="inverse",  # 原価は低いほど良い
        ),
        KPICardData(
            label="平均上代",
            value=format_currency(avg_retail),
            delta=delta_retail,
            delta_color="normal",
        ),
        KPICardData(
            label="平均粗利率",
            value=format_percentage(avg_gpr * 100.0),
            delta=delta_gpr,
            delta_color="normal",  # 粗利率は高いほど良い
        ),
    ]
    render_kpi_row(cards)

    # --- 品目別原価テーブル ---
    st.markdown("**品目別原価**")
    items_df = _build_items_compare_df(items, item_results)
    create_aggrid(
        items_df,
        column_defs=[
            text_column("品番", "品番", width=100),
            text_column("品名", "品名", width=160),
            currency_column("円建原価", "円建原価"),
            currency_column("製造原価", "製造原価"),
            currency_column("物流/個", "物流/個"),
        ],
        selection="none",
        height=220,
    )

    # --- ギフトセットテーブル ---
    st.markdown("**ギフトセット**")
    gifts_df = _build_gifts_compare_df(gifts, gift_results)
    create_aggrid(
        gifts_df,
        column_defs=[
            text_column("セット名", "セット名", width=180),
            currency_column("見積単価", "見積単価"),
            currency_column("製造原価", "製造原価"),
            percent_column("粗利率", "粗利率", decimals=1),
        ],
        selection="none",
        height=300,
    )


def _render_compare_view(
    ids: list[int],
    repo: ScenarioRepository,
    items: dict[str, SingleItem],
    gifts: list[GiftSet],
) -> None:
    """2件のシナリオを横並びで比較するビューを描画する。

    各シナリオの ``condition`` を使って単品・ギフトを再計算し、
    左右2カラムで KPI・テーブルを表示する。

    Args:
        ids: 比較する2件のシナリオ ID（左・右の順）。
        repo: シナリオリポジトリ。
        items: 品番 -> SingleItem のマッピング（再計算に使用）。
        gifts: GiftSet のリスト（再計算に使用）。
    """
    try:
        left_s = repo.get_scenario(ids[0])
        right_s = repo.get_scenario(ids[1])
    except ScenarioNotFoundError as exc:
        st.error(f"比較対象のシナリオが見つかりません: {exc}")
        return

    st.subheader(f"比較: {left_s.name}  vs  {right_s.name}")

    # 左シナリオ再計算
    left_item_results: dict[str, SingleItemResult] = {
        no: calc_single_item(item, left_s.condition)
        for no, item in items.items()
    }
    left_gift_results: list[GiftSetResult] = [
        calc_gift_set(g, items, left_item_results, left_s.condition)
        for g in gifts
    ]

    # 右シナリオ再計算
    right_item_results: dict[str, SingleItemResult] = {
        no: calc_single_item(item, right_s.condition)
        for no, item in items.items()
    }
    right_gift_results: list[GiftSetResult] = [
        calc_gift_set(g, items, right_item_results, right_s.condition)
        for g in gifts
    ]

    col_l, col_r = st.columns(2)
    with col_l:
        _render_scenario_column(
            scenario_name=left_s.name,
            condition=left_s.condition,
            item_results=left_item_results,
            gift_results=left_gift_results,
            items=items,
            gifts=gifts,
            baseline_item_results=None,
            baseline_gift_results=None,
        )
    with col_r:
        _render_scenario_column(
            scenario_name=right_s.name,
            condition=right_s.condition,
            item_results=right_item_results,
            gift_results=right_gift_results,
            items=items,
            gifts=gifts,
            baseline_item_results=left_item_results,
            baseline_gift_results=left_gift_results,
        )

    # 比較ビューを閉じるボタン
    if st.button("比較ビューを閉じる", key="btn_close_compare"):
        st.session_state.pop("compare_ids", None)
        st.rerun()


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------


def render_scenarios(
    cond: ImportCondition,
    items: dict[str, SingleItem],
    item_results: dict[str, SingleItemResult],
    gifts: list[GiftSet],
    gift_results: list[GiftSetResult],
    repo: ScenarioRepository,
) -> None:
    """シナリオタブ全体を描画する。

    構成:
        1. 現在の条件を新規保存するフォーム（expander）
        2. シナリオ一覧テーブル（aggrid、複数選択可）
        3. アクションボタン群（読み込み・複製・リネーム・削除・比較）
        4. 比較ビュー（2件選択後「比較」クリック時に展開）

    Args:
        cond: 現在のサイドバー輸入条件（保存フォームのデフォルト値に使用）。
        items: 品番 -> SingleItem のマッピング（比較再計算に使用）。
        item_results: 品番 -> SingleItemResult のマッピング（現在の計算済み結果）。
        gifts: GiftSet のリスト（比較再計算に使用）。
        gift_results: GiftSetResult のリスト（現在の計算済み結果）。
        repo: シナリオリポジトリ（CRUD 操作に使用）。
    """
    _render_save_form(cond, repo)
    selected = _render_list_table(repo)
    _render_action_buttons(selected, repo)

    compare_ids = st.session_state.get("compare_ids")
    if compare_ids and len(compare_ids) == 2:
        st.divider()
        _render_compare_view(compare_ids, repo, items, gifts)
