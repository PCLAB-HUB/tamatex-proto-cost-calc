"""業務改善提案書PDF生成スクリプト。

2026-04-07 定例会議の内容に基づき、実現可能な項目を
顧客提案用にまとめたPDFを生成する。
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
# Font setup
# ============================================================
FONT_NAME = "HeiseiKakuGo-W5"
pdfmetrics.registerFont(UnicodeCIDFont(FONT_NAME))

# ============================================================
# Colors
# ============================================================
C_PRIMARY = colors.HexColor("#1a73e8")
C_DARK = colors.HexColor("#202124")
C_GRAY = colors.HexColor("#5f6368")
C_LIGHT_GRAY = colors.HexColor("#f1f3f4")
C_BORDER = colors.HexColor("#dadce0")
C_HEADER_BG = colors.HexColor("#1a73e8")
C_CATEGORY_BG = colors.HexColor("#e8f0fe")
C_PHASE1_BG = colors.HexColor("#e6f4ea")  # green tint
C_PHASE2_BG = colors.HexColor("#fef7e0")  # yellow tint
C_PHASE3_BG = colors.HexColor("#fce8e6")  # red tint
C_PROCESS_BG = colors.HexColor("#f3e8fd")  # purple tint
C_GREEN = colors.HexColor("#137333")
C_ORANGE = colors.HexColor("#e37400")
C_RED = colors.HexColor("#c5221f")
C_PURPLE = colors.HexColor("#7627bb")

# ============================================================
# Page setup
# ============================================================
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
    "body": _ps("body", fontSize=9, leading=15, spaceAfter=3),
    "body_indent": _ps("body_indent", fontSize=9, leading=15,
                        spaceAfter=3, leftIndent=10),
    "body_right": _ps("body_right", fontSize=9, leading=15,
                       alignment=TA_RIGHT),
    "body_center": _ps("body_center", fontSize=9, leading=15,
                        alignment=TA_CENTER),
    "small": _ps("small", fontSize=8, leading=13, textColor=C_GRAY),
    "note": _ps("note", fontSize=8, leading=13, textColor=C_GRAY,
                 leftIndent=6, spaceAfter=2),
    "bullet": _ps("bullet", fontSize=9, leading=15, leftIndent=12,
                    spaceAfter=2),
    "cell": _ps("cell", fontSize=8, leading=12),
    "cell_r": _ps("cell_r", fontSize=8, leading=12, alignment=TA_RIGHT),
    "cell_c": _ps("cell_c", fontSize=8, leading=12, alignment=TA_CENTER),
    "cell_bold": _ps("cell_bold", fontSize=8, leading=12,
                      textColor=C_PRIMARY),
    "cell_small": _ps("cell_small", fontSize=7.5, leading=11,
                       textColor=C_GRAY),
    "phase_label": _ps("phase_label", fontSize=9, leading=14,
                        textColor=colors.white),
    "footer": _ps("footer", fontSize=7, leading=10,
                   textColor=C_GRAY, alignment=TA_CENTER),
    "cover_company": _ps("cover_company", fontSize=12, leading=18,
                          alignment=TA_CENTER, textColor=C_DARK),
    "cover_for": _ps("cover_for", fontSize=10, leading=16,
                      alignment=TA_CENTER, textColor=C_GRAY),
}


# ============================================================
# Helpers
# ============================================================

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


# ============================================================
# Proposal data
# ============================================================

TODAY = datetime.date.today()

# Phase A: すぐ着手可能（数日〜1週間）
PHASE_A = {
    "title": "Phase A: 基盤整備",
    "subtitle": "すぐ着手可能 / 工数目安: 数日〜1週間",
    "color": C_GREEN,
    "bg": C_PHASE1_BG,
    "items": [
        ("A-01", "品番マスタのスプレッドシート初版整備",
         "Google Sheets上に品番・品名・仕入先・単価を一覧管理するマスタを構築",
         "数日"),
        ("A-02", "品番命名規則の確定とガイド作成",
         "仕入先コード・カテゴリ記号（T/H/S等）を含む命名ルールを文書化",
         "1日"),
        ("A-03", "見積・原価計算テンプレートの一本化",
         "Google Sheetsで見積書と原価計算を統合、数式で自動連結",
         "2-3日"),
        ("A-04", "送り状・納品書のPDF自動生成",
         "Pythonスクリプトでマスタデータから帳票PDFを自動生成",
         "3-5日"),
        ("A-05", "過去見積の検索基盤整備",
         "顧客名での横断検索が可能な見積データベースを構築",
         "2-3日"),
        ("A-06", "国内向け発注書・仕様書の統一雛形案作成",
         "取引先別に可変対応できるテンプレートを設計",
         "2日"),
        ("A-07", "外部共有（メール/URL）の標準手順策定",
         "スプレッドシート不可の環境も想定した共有手順を文書化",
         "1日"),
        ("A-08", "QRコード/バーコード発行ツール",
         "品番からQRコードを自動生成し、ラベル印刷に対応",
         "2-3日"),
        ("A-09", "社内品番ルール最終確定とガイド",
         "全社向けの品番運用ガイドラインを作成・配布",
         "1-2日"),
        ("A-10", "過去品番体系の棚卸しと再登録",
         "既存品番をスプレッドシートに移行し、新ルールとの整合確認",
         "3-5日"),
    ],
}

# Phase B: 中期開発（1〜4週間）
PHASE_B = {
    "title": "Phase B: 業務効率化",
    "subtitle": "中期開発 / 工数目安: 1〜4週間",
    "color": C_ORANGE,
    "bg": C_PHASE2_BG,
    "items": [
        ("B-01", "西濃運賃チェック機能",
         "西濃の請求データと出荷データを自動照合し差異レポートを生成（ヤマト・佐川の既存システムを横展開）",
         "1週間"),
        ("B-02", "単価マスタ＋入荷時差異チェック",
         "マスタ登録済み単価と入荷伝票を自動照合、差異発生時にアラート通知",
         "1週間"),
        ("B-03", "通関書類の自動転記（インボイス・パッキングリスト）",
         "Excel入力データをGoogle Sheetsへ自動転記し、入荷処理と連携（既存tamatexアーキテクチャを拡張）",
         "1-2週間"),
        ("B-04", "見積〜原価計算〜見積書PDF自動生成フロー",
         "スプレッドシート入力→原価自動計算→PDF見積書を一気通貫で生成",
         "1-2週間"),
        ("B-05", "案件ステータス管理（見積→交渉→受注）",
         "案件ID・ステータス・バージョン管理をスプレッドシートベースで実装",
         "1週間"),
        ("B-06", "発注ステータス可視化",
         "発注の送付済み・担当者・完了状態を一覧表示、ステータス変更時に通知",
         "1週間"),
        ("B-07", "在庫一元管理ビュー（Amazon/eBay/FBA/倉庫）",
         "各販売チャネルのAPI連携で在庫を一覧集約し、低在庫時にアラート発報",
         "2-3週間"),
        ("B-08", "品番揺らぎのAI候補提示ツール",
         "品名の表記ゆれをAIが自動検出し候補を提示、確定結果を学習して精度向上",
         "1-2週間"),
        ("B-09", "社内掲示板/フォーム（単価・品番登録）",
         "Google Formsから単価・品番の登録申請→マスタへ自動反映",
         "3-5日"),
        ("B-10", "発注書→契約書への自動反映",
         "発注書の数値をブランド契約書へAPI経由で自動転記",
         "1-2週間"),
        ("B-11", "資材評価プロセスのシステム化",
         "副資材と製品の紐付けマスタを構築し、コスト加算・申告書への反映を自動化",
         "2週間"),
        ("B-12", "パントン→パールヨット自動変換ツール",
         "色空間変換テーブルを構築し、パントン色番号からパールヨット糸色番号を自動特定",
         "1週間"),
        ("B-13", "見積履歴のバージョン管理",
         "条件変更時にVersion 1→2→確定版と履歴を自動記録、差分を可視化",
         "3-5日"),
        ("B-14", "ABテスト設計（CTR/CVR段階分離）",
         "検索結果画面のCTRと商品ページのCVRを分離して計測・最適化する仕組みを設計",
         "3-5日"),
        ("B-15", "出荷明細との連携・在庫減少アラート",
         "事務員入力の出荷明細をシステム連携し、在庫変動を自動追跡・通知",
         "1-2週間"),
    ],
}

# Phase C: 長期開発（1〜3ヶ月+）
PHASE_C = {
    "title": "Phase C: 高度化・統合",
    "subtitle": "長期開発 / 工数目安: 1〜3ヶ月+",
    "color": C_RED,
    "bg": C_PHASE3_BG,
    "items": [
        ("C-01", "統合ダッシュボード",
         "全業務の情報を集約したダッシュボード（見積・在庫・発注・アラート一覧）を構築",
         "1-2ヶ月"),
        ("C-02", "BOM設計（製品⇔資材品番紐付け）＋在庫自動減算",
         "完成品出荷時に構成部品の在庫を自動減算、仕様差・送り先別単価にも対応",
         "1-2ヶ月"),
        ("C-03", "AI秘書（メール解析→発注書自動作成）",
         "メール本文からAIが発注内容を解析し、発注書を自動作成・社内保管",
         "2-3ヶ月"),
        ("C-04", "ローカルAI＋外部エージェント連携",
         "社内データはローカルAIで処理、外部情報検索は別AIに委託する分離設計",
         "2-3ヶ月"),
        ("C-05", "現場在庫可視化（タブレット＋音声検索）",
         "現場にタブレット端末を設置し、音声で在庫検索→画面表示、事務所とリアルタイム共有",
         "1-2ヶ月"),
        ("C-06", "AI品番揺らぎ学習機構",
         "人手確定のフィードバックをAIが継続学習し、次回以降の品番揺らぎを自動認識",
         "1ヶ月"),
        ("C-07", "生産スケジュール自動計算",
         "過去の需要動向から発注タイミングを予測し、生産スケジュールを自動提案",
         "2-3ヶ月"),
        ("C-08", "AIクリエイティブ自動生成",
         "ABテストの勝ちパターンを学習し、高CVRの商品画像をAIが自動生成",
         "2-3ヶ月"),
        ("C-09", "社員別ダッシュボード＋権限設計",
         "役職・担当に応じた閲覧範囲制御と個別KPIダッシュボードを構築",
         "1-2ヶ月"),
        ("C-10", "刺繍シミュレーション",
         "刺繍デザインの仕上がりを事前にシミュレーション表示する機能を導入",
         "要調査"),
    ],
}

# Phase D: 運用・プロセス整備（ルール策定が主体）
PHASE_D = {
    "title": "運用・プロセス整備",
    "subtitle": "ルール策定・ヒアリングが主体 / システム開発は不要または軽微",
    "color": C_PURPLE,
    "bg": C_PROCESS_BG,
    "items": [
        ("D-01", "取引先別伝票様式のヒアリング実施",
         "各取引先の伝票要件を収集し、可変テンプレートの仕様を確定",
         "-"),
        ("D-02", "仕入先へ品番記載徹底依頼",
         "請求書・納品書・ラベルへの品番記載を仕入先に依頼、移行期間を設定",
         "-"),
        ("D-03", "案件ステータス管理ルール策定",
         "ステータス更新の責任者・タイミング・更新漏れ防止策を文書化",
         "-"),
        ("D-04", "AIデータ境界ルール策定",
         "社内データと社外データの境界・機密分類・アクセス制御ポリシーを策定",
         "-"),
        ("D-05", "口コミ獲得施策設計",
         "体験価値の訴求軸を定義し、購入後レビュー導線を設計",
         "-"),
        ("D-06", "広告代理店との初回ミーティング要件整理",
         "新商品プロモーションの目的・予算・期待値を整理し、ミーティングに備える",
         "-"),
        ("D-07", "タオル商品の再撮影計画作成",
         "ABテストデータに基づき、勝つ構図での再撮影計画を立案",
         "-"),
        ("D-08", "ギフト商品の価格・訴求見直し",
         "ギフト売上不振の要因分析と価格設定・訴求方法の改善案を作成",
         "-"),
        ("D-09", "セール反映の運用フロー明確化",
         "セール価格の担当・反映タイミング・対象システムを明文化し反映漏れを防止",
         "-"),
        ("D-10", "作業履歴・アカウント管理の要件定義",
         "担当者ごとの進捗可視化と引継ぎ指標の要件を整理",
         "-"),
    ],
}

RECOMMENDED_ORDER = [
    ("1", "品番マスタ整備と命名規則確定", "A-01, A-02, A-09",
     "全ての業務改善の土台。品番が統一されることで、以降の自動化が一気に加速。"),
    ("2", "単価マスタ＋差異チェック", "B-02",
     "入荷時の単価確認業務を大幅短縮。ROIが高い。"),
    ("3", "見積・原価テンプレート一本化→PDF自動生成", "A-03, B-04",
     "営業の最重要業務を効率化。見積書の品質と速度を同時に向上。"),
    ("4", "西濃運賃チェック機能", "B-01",
     "既存のヤマト・佐川システムを横展開。即効性が高い。"),
    ("5", "通関書類の自動転記", "B-03",
     "既存tamatexシステムのアーキテクチャを直接活用可能。"),
    ("6", "過去見積の検索基盤", "A-05",
     "複数の社員から要望あり。顧客名キーの横断検索で業務迅速化。"),
    ("7", "在庫一元管理ビュー", "B-07",
     "Amazon/eBay/FBA/倉庫の在庫を統合表示。低在庫アラートで機会損失防止。"),
    ("8", "品番揺らぎAI候補提示", "B-08",
     "AI活用の第一歩。品名の表記ゆれを自動検出し、マスタ品質を向上。"),
    ("9", "案件・発注ステータス管理", "B-05, B-06",
     "業務の見える化。「誰が何をどこまで」を全社で共有。"),
    ("10", "統合ダッシュボード", "C-01",
     "各機能が揃った段階で統合。全業務の一覧性を実現。"),
]


# ============================================================
# PDF Builder
# ============================================================

def _add_page_number(canvas, doc):
    """ページ番号をフッターに追加。"""
    canvas.saveState()
    canvas.setFont(FONT_NAME, 7)
    canvas.setFillColor(C_GRAY)
    canvas.drawCentredString(
        PAGE_W / 2, 10 * mm,
        f"- {doc.page} -"
    )
    canvas.restoreState()


def build_proposal_pdf(output_path: str) -> None:
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    story = []

    # ==========================================================
    # 表紙
    # ==========================================================
    story.append(sp(40))
    story.append(p("業 務 改 善 提 案 書", "title"))
    story.append(sp(4))
    story.append(p("実現可能な施策一覧と推奨実施順序", "subtitle"))
    story.append(sp(8))
    story.append(thick_hr())
    story.append(sp(6))
    story.append(p("2026年4月7日 定例会議の議論に基づく", "body_center"))
    story.append(sp(30))

    # 宛先・発行者
    cover_info = [
        [p("御提出先:", "small"), p("　　　　　　　　　　　　　御中", "body")],
        [sp(4), ""],
        [p("提出日:", "small"), p(TODAY.strftime("%Y年%m月%d日"), "body")],
        [p("作成:", "small"), p("　", "body")],
    ]
    cover_t = Table(cover_info, colWidths=[22 * mm, 80 * mm])
    cover_t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    # Center the cover table
    outer = Table([[cover_t]], colWidths=[CONTENT_W])
    outer.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
    ]))
    story.append(outer)

    story.append(PageBreak())

    # ==========================================================
    # 1. 提案概要
    # ==========================================================
    story.append(p("1. 提案概要", "h1"))
    story.append(hr())

    story.append(p(
        "2026年4月7日に実施した定例会議において、業務改善に関する多数の課題と要望が共有されました。"
        "本提案書では、会議で議論された内容を整理し、<b>技術的に実現可能な施策45項目</b>を"
        "4つのフェーズに分類してご提案いたします。", "body"))
    story.append(sp(4))

    # サマリーテーブル
    summary_data = [
        [p("フェーズ", "cell_c"),
         p("分類", "cell"),
         p("項目数", "cell_c"),
         p("工数目安", "cell_c"),
         p("概要", "cell")],
        [p("A", "cell_c"),
         p("基盤整備", "cell"),
         p("10項目", "cell_c"),
         p("数日〜1週間", "cell_c"),
         p("品番マスタ・テンプレート・ドキュメント整備", "cell")],
        [p("B", "cell_c"),
         p("業務効率化", "cell"),
         p("15項目", "cell_c"),
         p("1〜4週間", "cell_c"),
         p("運賃チェック・通関自動化・在庫管理・AI活用", "cell")],
        [p("C", "cell_c"),
         p("高度化・統合", "cell"),
         p("10項目", "cell_c"),
         p("1〜3ヶ月+", "cell_c"),
         p("ダッシュボード・BOM・AI秘書・生産スケジュール", "cell")],
        [p("D", "cell_c"),
         p("運用・プロセス整備", "cell"),
         p("10項目", "cell_c"),
         p("-", "cell_c"),
         p("ルール策定・ヒアリング（開発不要）", "cell")],
    ]
    sum_w = [12 * mm, 28 * mm, 18 * mm, 26 * mm, CONTENT_W - 84 * mm]
    sum_t = Table(summary_data, colWidths=sum_w)
    sum_style = [
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 1), (-1, 1), C_PHASE1_BG),
        ("BACKGROUND", (0, 2), (-1, 2), C_PHASE2_BG),
        ("BACKGROUND", (0, 3), (-1, 3), C_PHASE3_BG),
        ("BACKGROUND", (0, 4), (-1, 4), C_PROCESS_BG),
    ]
    sum_t.setStyle(TableStyle(sum_style))
    story.append(sum_t)
    story.append(sp(6))

    story.append(p(
        "※ 全施策の基盤となる<b>「品番マスタ」の整備を最優先</b>で推奨いたします。"
        "品番が統一されることで、在庫管理・単価照合・見積連携など"
        "多くの業務改善が加速的に進行します。", "body"))

    story.append(PageBreak())

    # ==========================================================
    # 2-5. Phase details
    # ==========================================================
    phases = [
        ("2", PHASE_A),
        ("3", PHASE_B),
        ("4", PHASE_C),
        ("5", PHASE_D),
    ]

    for section_no, phase in phases:
        story.append(p(f"{section_no}. {phase['title']}", "h1"))
        story.append(p(phase["subtitle"], "small"))
        story.append(hr())

        # Phase items table
        col_w = [14 * mm, 42 * mm, CONTENT_W - 74 * mm, 18 * mm]
        header_row = [
            p("No", "cell_c"),
            p("施策名", "cell"),
            p("概要", "cell"),
            p("工数", "cell_c"),
        ]

        table_data = [header_row]
        style_cmds = [
            ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
            ("BACKGROUND", (0, 0), (-1, 0), phase["color"]),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]

        for i, (no, name, desc, effort) in enumerate(phase["items"]):
            row_i = i + 1
            table_data.append([
                p(no, "cell_c"),
                p(f"<b>{name}</b>", "cell"),
                p(desc, "cell"),
                p(effort, "cell_c"),
            ])
            if row_i % 2 == 0:
                style_cmds.append(
                    ("BACKGROUND", (0, row_i), (-1, row_i), phase["bg"]))

        phase_table = Table(table_data, colWidths=col_w, repeatRows=1)
        phase_table.setStyle(TableStyle(style_cmds))
        story.append(phase_table)
        story.append(sp(6))

        # Phase B の後でページ送り
        if section_no == "3":
            story.append(PageBreak())

    story.append(PageBreak())

    # ==========================================================
    # 6. 推奨実施順序
    # ==========================================================
    story.append(p("6. 推奨実施順序", "h1"))
    story.append(hr())

    story.append(p(
        "投資効果（ROI）と依存関係を考慮し、以下の順序での実施を推奨いたします。"
        "品番マスタの整備が全ての基盤となるため、最初に着手することで"
        "後続の施策が効率的に進行します。", "body"))
    story.append(sp(4))

    order_data = [
        [p("優先度", "cell_c"),
         p("施策群", "cell"),
         p("対象No", "cell_c"),
         p("推奨理由", "cell")],
    ]

    order_styles = [
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]

    for i, (rank, name, refs, reason) in enumerate(RECOMMENDED_ORDER):
        row_i = i + 1
        order_data.append([
            p(rank, "cell_c"),
            p(f"<b>{name}</b>", "cell"),
            p(refs, "cell_c"),
            p(reason, "cell"),
        ])
        if row_i % 2 == 0:
            order_styles.append(
                ("BACKGROUND", (0, row_i), (-1, row_i), C_LIGHT_GRAY))

    order_w = [16 * mm, 46 * mm, 24 * mm, CONTENT_W - 86 * mm]
    order_t = Table(order_data, colWidths=order_w, repeatRows=1)
    order_t.setStyle(TableStyle(order_styles))
    story.append(order_t)

    story.append(sp(8))

    # ==========================================================
    # 7. 備考
    # ==========================================================
    story.append(p("7. 備考", "h1"))
    story.append(hr())

    notes = [
        "本提案書は2026年4月7日の会議内容に基づき、技術的に実現可能な施策を整理したものです。",
        "各施策の工数目安は概算であり、要件の詳細化に伴い変動する可能性があります。",
        "Phase A（基盤整備）は他の全施策の前提となるため、最優先での着手を推奨します。",
        "Phase B以降の施策は、ビジネス上の優先度に応じて順序を調整可能です。",
        "Phase D（運用・プロセス整備）はシステム開発と並行して進めることが可能です。",
        "各施策の詳細な仕様・費用については、別途お見積りいたします。",
        "既に稼働中のExcel→Google Sheets同期システム（tamatex）のアーキテクチャを"
        "最大限活用し、開発コストの最適化を図ります。",
    ]
    for note in notes:
        story.append(p(f"・{note}", "note"))

    story.append(sp(12))
    story.append(hr())
    story.append(p(
        "本提案書の内容についてご不明な点がございましたら、お気軽にお問い合わせください。",
        "body_center"))

    # ==========================================================
    # Build
    # ==========================================================
    doc.build(story, onFirstPage=_add_page_number,
              onLaterPages=_add_page_number)
    print(f"提案書を生成しました: {output_path}")


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent.parent / "docs"
    out_dir.mkdir(exist_ok=True)
    output = str(out_dir / "業務改善提案書.pdf")
    build_proposal_pdf(output)
