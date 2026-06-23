"""帳票生成機能の実現可能性分析PDF.

原価計算プロトタイプから見積書・商品規格リスト・仕入れ単価帳・販売単価帳を
生成する可能性について、顧客向けに説明する資料。
"""

from __future__ import annotations

import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# ============================================================
# Font / Color / Page
# ============================================================
FONT_NAME = "HeiseiKakuGo-W5"
pdfmetrics.registerFont(UnicodeCIDFont(FONT_NAME))

C_PRIMARY = colors.HexColor("#1a73e8")
C_DARK = colors.HexColor("#202124")
C_GRAY = colors.HexColor("#5f6368")
C_LIGHT_GRAY = colors.HexColor("#f1f3f4")
C_BORDER = colors.HexColor("#dadce0")
C_GREEN = colors.HexColor("#137333")
C_GREEN_BG = colors.HexColor("#e6f4ea")
C_YELLOW_BG = colors.HexColor("#fef7e0")
C_ORANGE = colors.HexColor("#e37400")
C_BLUE_BG = colors.HexColor("#e8f0fe")

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

# ============================================================
# Styles
# ============================================================


def _ps(name: str, **kwargs) -> ParagraphStyle:
    defaults = {"fontName": FONT_NAME, "leading": 16, "textColor": C_DARK}
    defaults.update(kwargs)
    return ParagraphStyle(name, **defaults)


S = {
    "title": _ps("title", fontSize=22, alignment=TA_CENTER, leading=32,
                  textColor=C_PRIMARY),
    "subtitle": _ps("subtitle", fontSize=10, alignment=TA_CENTER,
                     textColor=C_GRAY, spaceAfter=4),
    "date": _ps("date", fontSize=9, alignment=TA_RIGHT,
                textColor=C_GRAY, spaceAfter=2),
    "h1": _ps("h1", fontSize=14, leading=22, spaceBefore=12,
              spaceAfter=6, textColor=C_PRIMARY),
    "h2": _ps("h2", fontSize=11, leading=18, spaceBefore=8,
              spaceAfter=4, textColor=C_PRIMARY),
    "h3": _ps("h3", fontSize=10, leading=16, spaceBefore=6,
              spaceAfter=3, textColor=C_DARK),
    "body": _ps("body", fontSize=9, leading=15, spaceAfter=3),
    "body_indent": _ps("body_indent", fontSize=9, leading=15,
                        spaceAfter=3, leftIndent=10),
    "bullet": _ps("bullet", fontSize=9, leading=15, leftIndent=12,
                    spaceAfter=2),
    "small": _ps("small", fontSize=8, leading=13, textColor=C_GRAY),
    "note": _ps("note", fontSize=8, leading=13, textColor=C_GRAY,
                 leftIndent=6, spaceAfter=2),
    "cell": _ps("cell", fontSize=8, leading=12),
    "cell_r": _ps("cell_r", fontSize=8, leading=12, alignment=TA_RIGHT),
    "cell_c": _ps("cell_c", fontSize=8, leading=12, alignment=TA_CENTER),
    "cell_bold": _ps("cell_bold", fontSize=8, leading=12,
                      textColor=C_PRIMARY),
    "cell_small": _ps("cell_small", fontSize=7.5, leading=11,
                       textColor=C_GRAY),
    "footer": _ps("footer", fontSize=7, leading=10,
                   textColor=C_GRAY, alignment=TA_CENTER),
    "cover_company": _ps("cover_company", fontSize=12, leading=18,
                          alignment=TA_CENTER, textColor=C_DARK),
    "cover_for": _ps("cover_for", fontSize=10, leading=16,
                      alignment=TA_CENTER, textColor=C_GRAY),
    "star": _ps("star", fontSize=9, leading=14, textColor=C_ORANGE),
}


def p(text: str, style_name: str = "body") -> Paragraph:
    return Paragraph(text, S[style_name])


def sp(h: float = 4) -> Spacer:
    return Spacer(1, h * mm)


def hr() -> HRFlowable:
    return HRFlowable(width="100%", thickness=0.5, color=C_BORDER,
                       spaceBefore=2, spaceAfter=4)


def thick_hr() -> HRFlowable:
    return HRFlowable(width="100%", thickness=1.5, color=C_PRIMARY,
                       spaceBefore=4, spaceAfter=6)


def _table_style_base():
    return [
        ("FONT", (0, 0), (-1, -1), FONT_NAME, 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]


def header_table(data, col_widths, header_bg=C_PRIMARY):
    style_cmds = _table_style_base() + [
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_LIGHT_GRAY]),
    ]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle(style_cmds))
    return t


TODAY = datetime.date.today()


# ============================================================
# Content builders
# ============================================================

def build_cover(elems: list) -> None:
    elems.append(sp(30))
    elems.append(p("帳票生成機能の実現可能性分析", "title"))
    elems.append(sp(4))
    elems.append(p("原価計算プロトタイプからの帳票出力について", "subtitle"))
    elems.append(sp(12))
    elems.append(thick_hr())
    elems.append(sp(8))
    elems.append(p("タマテックス株式会社 御中", "cover_for"))
    elems.append(sp(20))
    elems.append(p(f"作成日: {TODAY.strftime('%Y年%m月%d日')}", "date"))
    elems.append(sp(4))
    elems.append(p("PCLab（業務改善コンサルティング）", "cover_company"))
    elems.append(PageBreak())


def build_overview(elems: list) -> None:
    elems.append(p("1. 概要", "h1"))
    elems.append(thick_hr())
    elems.append(p(
        "現在開発中の原価計算プロトタイプには、単品タオル6品目・ギフトセット12パターンの"
        "全原価データ（FOB、CIF、関税、輸入経費、物流費、製造原価、見積単価、粗利等）が"
        "計算エンジンに保持されています。"
    ))
    elems.append(sp(2))
    elems.append(p(
        "このデータを活用し、以下の4種類の帳票を自動生成する機能の追加について"
        "実現可能性を分析しました。"
    ))
    elems.append(sp(4))

    data = [
        [p("帳票名", "cell_c"), p("概要", "cell_c"), p("実現性", "cell_c")],
        [p("見積書", "cell"), p("取引先向けの商品見積り", "cell"),
         p("高（データほぼ揃っている）", "cell")],
        [p("商品規格リスト", "cell"), p("品番・サイズ・素材等の仕様一覧", "cell"),
         p("中（マスタ情報の追加が必要）", "cell")],
        [p("仕入れ単価帳", "cell"), p("品番別の仕入原価一覧", "cell"),
         p("最高（すぐ対応可能）", "cell")],
        [p("販売単価帳", "cell"), p("セット別の販売価格・粗利一覧", "cell"),
         p("高（上代データの投入が必要）", "cell")],
    ]
    t = header_table(data, [80, 200, 180])
    elems.append(t)
    elems.append(sp(6))


def build_current_data(elems: list) -> None:
    elems.append(p("2. 現在のエンジンが保持するデータ", "h1"))
    elems.append(thick_hr())
    elems.append(p(
        "原価計算エンジンは、Excelの全計算式をPython関数化しており、"
        "以下のデータを正確に計算・保持しています（Excel実値と±0.01円以内で一致検証済み）。"
    ))
    elems.append(sp(3))

    elems.append(p("単品タオル（6品目）", "h2"))
    data_single = [
        [p("データ項目", "cell_c"), p("内容", "cell_c"), p("帳票での用途", "cell_c")],
        [p("品番・品名", "cell"), p("OSD-MOCO BT 等", "cell"),
         p("全帳票の基本情報", "cell")],
        [p("アイテム種別・サイズ", "cell"), p("BT/FT/BM/MT, 60x120等", "cell"),
         p("商品規格リスト", "cell")],
        [p("目方・織区分", "cell"), p("290g, JQ等", "cell"),
         p("商品規格リスト", "cell")],
        [p("FOB単価(USD/JPY)", "cell"), p("$3.80 / ¥570", "cell"),
         p("仕入れ単価帳", "cell")],
        [p("CIF・関税・輸入経費", "cell"), p("¥573 / ¥42 / ¥18等", "cell"),
         p("仕入れ単価帳", "cell")],
        [p("製造原価・円建原価", "cell"), p("¥570 / ¥637", "cell"),
         p("仕入れ・販売単価帳", "cell")],
    ]
    t = header_table(data_single, [110, 170, 180])
    elems.append(t)
    elems.append(sp(4))

    elems.append(p("ギフトセット（12パターン）", "h2"))
    data_gift = [
        [p("データ項目", "cell_c"), p("内容", "cell_c"), p("帳票での用途", "cell_c")],
        [p("セット名・構成", "cell"), p("FT2もこ = FT×2枚 等", "cell"),
         p("全帳票の基本情報", "cell")],
        [p("販売単価", "cell"), p("¥1,294 等", "cell"),
         p("見積書・販売単価帳", "cell")],
        [p("見積単価", "cell"), p("¥1,569（原価×1.4切上げ）", "cell"),
         p("見積書", "cell")],
        [p("製造原価", "cell"), p("¥1,120 等", "cell"),
         p("仕入れ単価帳", "cell")],
        [p("粗利・粗利率", "cell"), p("¥174 / 13.4%", "cell"),
         p("見積書・販売単価帳", "cell")],
        [p("資材・加工・物流の内訳", "cell"), p("化粧箱¥356, 箱入代¥45等", "cell"),
         p("仕入れ単価帳（明細）", "cell")],
    ]
    t = header_table(data_gift, [120, 170, 170])
    elems.append(t)
    elems.append(sp(2))
    elems.append(p(
        "※ 上記は20FTコンテナ/大阪揚げ/今治倉庫の条件です。"
        "40FT/東京揚げの条件も切替可能です。",
        "note"
    ))
    elems.append(PageBreak())


def build_detail_analysis(elems: list) -> None:
    elems.append(p("3. 帳票別の詳細分析", "h1"))
    elems.append(thick_hr())

    # --- 3-1: 仕入れ単価帳 ---
    elems.append(p("3-1. 仕入れ単価帳", "h2"))
    _star_rating(elems, 5, "すぐ対応可能")
    elems.append(p(
        "原価計算エンジンの出力がそのまま仕入れ単価帳の核心データとなります。"
        "FOB(USD/JPY)から製造原価までの全計算チェーンが揃っており、"
        "出力フォーマットを整えるだけで帳票化できます。"
    ))
    elems.append(sp(2))

    data = [
        [p("必要項目", "cell_c"), p("現在の状況", "cell_c"), p("対応", "cell_c")],
        [p("品番・品名", "cell"), p("あり", "cell"), p("対応不要", "cell")],
        [p("FOB単価(USD/JPY)", "cell"), p("あり", "cell"), p("対応不要", "cell")],
        [p("CIF・関税・輸入経費", "cell"), p("あり（全中間値）", "cell"), p("対応不要", "cell")],
        [p("製造原価・円建原価", "cell"), p("あり", "cell"), p("対応不要", "cell")],
        [p("為替・コンテナ条件", "cell"), p("あり（切替可能）", "cell"), p("対応不要", "cell")],
        [p("仕入先名", "cell"), p("なし", "cell"), p("入力欄追加", "cell")],
    ]
    t = header_table(data, [130, 180, 150])
    elems.append(t)
    elems.append(sp(6))

    # --- 3-2: 見積書 ---
    elems.append(p("3-2. 見積書", "h2"))
    _star_rating(elems, 4, "実現可能（不足少）")
    elems.append(p(
        "見積単価・数量・金額など計算データは揃っています。"
        "取引先名や自社情報などの帳票ヘッダ情報を入力フォームで追加すれば実現可能です。"
    ))
    elems.append(sp(2))

    data = [
        [p("必要項目", "cell_c"), p("現在の状況", "cell_c"), p("対応", "cell_c")],
        [p("商品名・セット名", "cell"), p("あり", "cell"), p("対応不要", "cell")],
        [p("見積単価・数量・金額", "cell"), p("あり（自動計算済み）", "cell"), p("対応不要", "cell")],
        [p("原価・粗利・粗利率", "cell"), p("あり", "cell"), p("対応不要", "cell")],
        [p("宛先（取引先名）", "cell"), p("なし", "cell"), p("入力欄追加", "cell")],
        [p("見積日・有効期限", "cell"), p("なし", "cell"), p("入力欄追加", "cell")],
        [p("自社情報", "cell"), p("なし", "cell"), p("設定画面で登録", "cell")],
        [p("備考・支払条件", "cell"), p("なし", "cell"), p("入力欄追加", "cell")],
    ]
    t = header_table(data, [130, 180, 150])
    elems.append(t)
    elems.append(sp(6))

    # --- 3-3: 販売単価帳 ---
    elems.append(p("3-3. 販売単価帳", "h2"))
    _star_rating(elems, 4, "実現可能（不足少）")
    elems.append(p(
        "販売単価・見積単価・粗利率は既に計算済みです。"
        "上代（定価）の実データを投入すれば、上代掛率の計算も含めて帳票化できます。"
    ))
    elems.append(sp(2))

    data = [
        [p("必要項目", "cell_c"), p("現在の状況", "cell_c"), p("対応", "cell_c")],
        [p("セット名・構成", "cell"), p("あり", "cell"), p("対応不要", "cell")],
        [p("見積単価・販売単価", "cell"), p("あり", "cell"), p("対応不要", "cell")],
        [p("粗利・粗利率", "cell"), p("あり", "cell"), p("対応不要", "cell")],
        [p("上代（定価）", "cell"), p("項目あり、値が未入力", "cell"), p("実データ投入", "cell")],
        [p("上代掛率", "cell"), p("計算式あり（上代投入後に自動算出）", "cell"), p("対応不要", "cell")],
        [p("卸先別単価", "cell"), p("なし", "cell"), p("必要に応じて追加", "cell")],
    ]
    t = header_table(data, [130, 200, 130])
    elems.append(t)
    elems.append(sp(6))

    # --- 3-4: 商品規格リスト ---
    elems.append(p("3-4. 商品規格リスト", "h2"))
    _star_rating(elems, 3, "実現可能（マスタ情報の追加が必要）")
    elems.append(p(
        "原価計算には不要だった商品マスタ情報（素材、色、JANコード等）の追加が必要です。"
        "ただし、Excelの「生地コスト」シートに品番別の糸仕様・克重等が存在するため、"
        "これを取り込むことで一部は対応できます。"
    ))
    elems.append(sp(2))

    data = [
        [p("必要項目", "cell_c"), p("現在の状況", "cell_c"), p("対応", "cell_c")],
        [p("品番", "cell"), p("モック品番のみ", "cell"), p("正式品番への置換", "cell")],
        [p("品名", "cell"), p("略称のみ", "cell"), p("正式品名の登録", "cell")],
        [p("種別・サイズ・目方", "cell"), p("あり", "cell"), p("対応不要", "cell")],
        [p("素材・組成", "cell"), p("なし（生地コストシートに一部あり）", "cell"),
         p("マスタ追加", "cell")],
        [p("色・柄", "cell"), p("なし", "cell"), p("マスタ追加", "cell")],
        [p("JANコード", "cell"), p("なし", "cell"), p("マスタ追加", "cell")],
        [p("ギフト構成", "cell"), p("あり（単品×枚数）", "cell"), p("対応不要", "cell")],
        [p("化粧箱サイズ", "cell"), p("なし", "cell"), p("マスタ追加", "cell")],
        [p("商品画像", "cell"), p("なし", "cell"), p("将来検討", "cell")],
    ]
    t = header_table(data, [110, 200, 150])
    elems.append(t)
    elems.append(sp(6))


def _star_rating(elems: list, stars: int, label: str) -> None:
    filled = "\u2605" * stars
    empty = "\u2606" * (5 - stars)
    elems.append(p(f"実現性: {filled}{empty}　{label}", "star"))
    elems.append(sp(2))


def build_missing_info(elems: list) -> None:
    elems.append(p("4. ご確認いただきたい事項", "h1"))
    elems.append(thick_hr())
    elems.append(p(
        "帳票生成機能を実装するにあたり、以下の情報をご提供いただく必要があります。"
    ))
    elems.append(sp(3))

    data = [
        [p("#", "cell_c"), p("確認事項", "cell_c"),
         p("詳細", "cell_c"), p("関連帳票", "cell_c")],
        [p("1", "cell_c"), p("正式品番・正式品名", "cell"),
         p("現在はモック品番（MOCK-001等）を使用。実際の品番体系をご教示ください", "cell"),
         p("全帳票", "cell_c")],
        [p("2", "cell_c"), p("上代（定価）", "cell"),
         p("ギフトセットの retail_price が現在0です。実際の上代を入力いただけますか", "cell"),
         p("販売単価帳", "cell_c")],
        [p("3", "cell_c"), p("取引先名・仕入先名", "cell"),
         p("見積書の宛先、仕入れ単価帳の仕入先として使用", "cell"),
         p("見積書\n仕入れ単価帳", "cell_c")],
        [p("4", "cell_c"), p("素材・組成・色", "cell"),
         p("「綿100%」等の素材情報。生地コストシートから一部取得可能", "cell"),
         p("商品規格リスト", "cell_c")],
        [p("5", "cell_c"), p("JANコード", "cell"),
         p("商品規格リストに掲載する場合に必要", "cell"),
         p("商品規格リスト", "cell_c")],
        [p("6", "cell_c"), p("出力形式のご希望", "cell"),
         p("PDF / Excel / 画面表示のいずれか（複数可）", "cell"),
         p("全帳票", "cell_c")],
    ]
    cw = [20, 110, 230, 100]
    style_cmds = _table_style_base() + [
        ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_LIGHT_GRAY]),
    ]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle(style_cmds))
    elems.append(t)
    elems.append(sp(4))
    elems.append(p(
        "※ 項目1〜3は帳票生成に必須の情報です。項目4〜5は商品規格リストのみで使用します。",
        "note"
    ))
    elems.append(sp(6))


def build_implementation_plan(elems: list) -> None:
    elems.append(p("5. 実装イメージ", "h1"))
    elems.append(thick_hr())
    elems.append(p(
        "既存の原価計算プロトタイプ（Streamlit Webアプリ）に帳票出力機能を追加します。"
        "条件を変更して再計算した結果をそのまま帳票に反映できるため、"
        "「為替が変わったら見積書を即更新」といった運用が可能になります。"
    ))
    elems.append(sp(4))

    elems.append(p("実装ステップ", "h2"))
    data = [
        [p("ステップ", "cell_c"), p("内容", "cell_c"),
         p("工数目安", "cell_c")],
        [p("Step 1", "cell_bold"),
         p("仕入れ単価帳の出力機能（データは既存、フォーマットのみ）", "cell"),
         p("1〜2日", "cell_c")],
        [p("Step 2", "cell_bold"),
         p("見積書の出力機能（ヘッダ入力フォーム + PDF生成）", "cell"),
         p("2〜3日", "cell_c")],
        [p("Step 3", "cell_bold"),
         p("販売単価帳の出力機能（上代データ投入後）", "cell"),
         p("1〜2日", "cell_c")],
        [p("Step 4", "cell_bold"),
         p("商品規格リスト（マスタ情報追加 + 出力）", "cell"),
         p("3〜5日", "cell_c")],
    ]
    t = header_table(data, [60, 310, 90])
    elems.append(t)
    elems.append(sp(4))

    elems.append(p("運用イメージ", "h2"))
    elems.append(p("1. Webアプリ上で輸入条件（為替・コンテナ等）を設定", "bullet"))
    elems.append(p("2. 計算結果を画面で確認", "bullet"))
    elems.append(p("3. 「帳票出力」ボタンで必要な帳票をPDF/Excelで出力", "bullet"))
    elems.append(p("4. 条件変更 → 即座に再計算 → 帳票を再出力", "bullet"))
    elems.append(sp(4))

    # highlight box
    box_data = [[p(
        "原価計算の条件変更がリアルタイムで帳票に反映されるため、"
        "Excelで個別にコピー&ペーストする作業が不要になります。",
        "cell"
    )]]
    box = Table(box_data, colWidths=[CONTENT_W - 20])
    box.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), FONT_NAME, 9),
        ("BACKGROUND", (0, 0), (-1, -1), C_BLUE_BG),
        ("BOX", (0, 0), (-1, -1), 1, C_PRIMARY),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    elems.append(box)
    elems.append(sp(6))


def build_conclusion(elems: list) -> None:
    elems.append(p("6. まとめ", "h1"))
    elems.append(thick_hr())

    data = [
        [p("帳票", "cell_c"), p("実現性", "cell_c"),
         p("必要な追加情報", "cell_c"), p("工数目安", "cell_c")],
        [p("仕入れ単価帳", "cell_bold"), p("\u2605\u2605\u2605\u2605\u2605", "cell_c"),
         p("仕入先名のみ", "cell"), p("1〜2日", "cell_c")],
        [p("見積書", "cell_bold"), p("\u2605\u2605\u2605\u2605\u2606", "cell_c"),
         p("取引先名・自社情報", "cell"), p("2〜3日", "cell_c")],
        [p("販売単価帳", "cell_bold"), p("\u2605\u2605\u2605\u2605\u2606", "cell_c"),
         p("上代データ", "cell"), p("1〜2日", "cell_c")],
        [p("商品規格リスト", "cell_bold"), p("\u2605\u2605\u2605\u2606\u2606", "cell_c"),
         p("素材・色・JAN等", "cell"), p("3〜5日", "cell_c")],
    ]
    cw = [100, 80, 180, 80]
    style_cmds = _table_style_base() + [
        ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_LIGHT_GRAY]),
    ]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle(style_cmds))
    elems.append(t)
    elems.append(sp(6))

    elems.append(p(
        "4帳票とも技術的に実現可能です。原価計算エンジンが全原価データを正確に保持しているため、"
        "帳票ごとに必要なマスタ情報を追加すれば対応できます。",
    ))
    elems.append(sp(2))
    elems.append(p(
        "特に仕入れ単価帳は、既存データだけでプロトタイプ出力が可能な状態です。"
        "まずこちらから着手し、順次見積書・販売単価帳・商品規格リストへと"
        "拡張していくことを推奨いたします。",
    ))
    elems.append(sp(8))
    elems.append(hr())
    elems.append(p(
        "本資料に関するご質問・ご要望がございましたら、お気軽にお問い合わせください。",
        "small"
    ))


# ============================================================
# Footer
# ============================================================

def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT_NAME, 7)
    canvas.setFillColor(C_GRAY)
    canvas.drawCentredString(
        PAGE_W / 2, 12 * mm,
        f"帳票生成機能の実現可能性分析 — {TODAY.strftime('%Y-%m-%d')} — Page {doc.page}"
    )
    canvas.restoreState()


# ============================================================
# Main
# ============================================================

def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "docs"
    out_path = out_dir / "帳票生成_実現可能性分析.pdf"

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )

    elems: list = []
    build_cover(elems)
    build_overview(elems)
    build_current_data(elems)
    build_detail_analysis(elems)
    build_missing_info(elems)
    build_implementation_plan(elems)
    build_conclusion(elems)

    doc.build(elems, onFirstPage=_footer, onLaterPages=_footer)
    print(f"PDF generated: {out_path}")


if __name__ == "__main__":
    main()
