"""顧客向けシステム仕様書のPDF生成スクリプト。

新アーキテクチャ（Drive API 直接アップロード方式・PDF同時生成・書式保持対応）
に基づいた仕様書を生成する。
"""

import os
import sys
import tempfile
from pathlib import Path

# --- matplotlib illustrations ---
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# --- reportlab PDF ---
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# ============================================================
# Font setup
# ============================================================
FONT_NAME = "HeiseiKakuGo-W5"
pdfmetrics.registerFont(UnicodeCIDFont(FONT_NAME))

MPL_FONT = "Hiragino Sans"
matplotlib.rcParams["font.family"] = [MPL_FONT, "sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False

# ============================================================
# Colors
# ============================================================
C_PRIMARY = colors.HexColor("#1a73e8")
C_PRIMARY_LIGHT = colors.HexColor("#e8f0fe")
C_DARK = colors.HexColor("#202124")
C_GRAY = colors.HexColor("#5f6368")
C_LIGHT_GRAY = colors.HexColor("#f1f3f4")
C_BORDER = colors.HexColor("#dadce0")
C_GREEN = colors.HexColor("#34a853")
C_ORANGE = colors.HexColor("#ea8600")
C_RED = colors.HexColor("#ea4335")

MC_PRIMARY = "#1a73e8"
MC_GREEN = "#34a853"
MC_ORANGE = "#ea8600"
MC_RED = "#ea4335"
MC_GRAY = "#5f6368"
MC_LIGHT = "#e8f0fe"
MC_BG = "#f8f9fa"
MC_DARK = "#202124"
MC_PURPLE = "#9334e6"

# ============================================================
# Page styles
# ============================================================
PAGE_W, PAGE_H = A4
MARGIN = 20 * mm
CONTENT_W = PAGE_W - 2 * MARGIN


def _ps(name, **kwargs):
    defaults = {"fontName": FONT_NAME, "leading": 20, "textColor": C_DARK}
    defaults.update(kwargs)
    return ParagraphStyle(name, **defaults)


def make_styles():
    return {
        "cover_title": _ps("ct", fontSize=22, alignment=TA_CENTER,
                            leading=32, spaceAfter=10),
        "cover_sub": _ps("cs", fontSize=12, alignment=TA_CENTER,
                          textColor=C_GRAY, spaceAfter=6),
        "h1": _ps("h1", fontSize=16, leading=24, spaceBefore=18,
                   spaceAfter=10, textColor=C_PRIMARY),
        "h2": _ps("h2", fontSize=13, leading=20, spaceBefore=14,
                   spaceAfter=6),
        "body": _ps("body", fontSize=10, leading=17,
                     spaceAfter=6, alignment=TA_JUSTIFY),
        "body_indent": _ps("bi", fontSize=10, leading=17,
                            spaceAfter=4, leftIndent=15),
        "note": _ps("note", fontSize=9, leading=15,
                     textColor=C_GRAY, leftIndent=10, spaceAfter=6),
        "bullet": _ps("bul", fontSize=10, leading=17,
                       leftIndent=18, bulletIndent=6, spaceAfter=3),
        "qa_q": _ps("qq", fontSize=10, leading=17,
                     textColor=C_PRIMARY, spaceBefore=10, spaceAfter=2),
        "qa_a": _ps("qa", fontSize=10, leading=17,
                     leftIndent=15, spaceAfter=6),
        "footer": _ps("ft", fontSize=8, textColor=C_GRAY,
                       alignment=TA_CENTER),
    }


S = make_styles()


# ============================================================
# Helpers
# ============================================================
_CELL_STYLE = ParagraphStyle(
    "cell", fontName=FONT_NAME, fontSize=9, leading=13,
    textColor=C_DARK, wordWrap="CJK",
)
_HEADER_CELL_STYLE = ParagraphStyle(
    "hdr_cell", fontName=FONT_NAME, fontSize=9, leading=13,
    textColor=colors.white, wordWrap="CJK",
)


def _wrap_cell(value, header=False):
    """セル値を Paragraph に包んで自動折り返しを有効にする。"""
    if isinstance(value, Paragraph):
        return value
    style = _HEADER_CELL_STYLE if header else _CELL_STYLE
    text = str(value)
    return Paragraph(text, style)


def styled_table(data, col_widths=None, header=True):
    # 全セルを Paragraph で包む（CJK自動折り返し）
    wrapped = []
    for ri, row in enumerate(data):
        wrapped.append([_wrap_cell(v, header=(header and ri == 0)) for v in row])

    style_cmds = [
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), C_DARK),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
    ]
    if header:
        style_cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARY),
        ]
    for i in range(1, len(wrapped)):
        if i % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), C_LIGHT_GRAY))

    t = Table(wrapped, colWidths=col_widths, repeatRows=1 if header else 0)
    t.setStyle(TableStyle(style_cmds))
    return t


def p(text, style_name="body"):
    return Paragraph(text, S[style_name])


def sp(h=6):
    return Spacer(1, h * mm)


def hr():
    return HRFlowable(width="100%", thickness=0.5, color=C_BORDER,
                       spaceBefore=3, spaceAfter=8)


# ============================================================
# Illustrations
# ============================================================
TMP_DIR = tempfile.mkdtemp()


def _save_fig(fig, name, dpi=180):
    path = os.path.join(TMP_DIR, f"{name}.png")
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white", pad_inches=0.2)
    plt.close(fig)
    return path


def _draw_box(ax, x, y, w, h, label, sub="", color=MC_PRIMARY, icon=None):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15",
                          facecolor=color, edgecolor="white", linewidth=0, alpha=0.15)
    ax.add_patch(box)
    border = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15",
                             facecolor="none", edgecolor=color, linewidth=1.5)
    ax.add_patch(border)
    ty = y + h * 0.55 if sub else y + h * 0.5
    if icon:
        ax.text(x + w * 0.5, y + h * 0.72, icon, ha="center", va="center",
                fontsize=20, color=color)
        ty = y + h * 0.32
    ax.text(x + w * 0.5, ty, label, ha="center", va="center",
            fontsize=10, fontweight="bold", color=color)
    if sub:
        ax.text(x + w * 0.5, y + h * 0.22, sub, ha="center", va="center",
                fontsize=7.5, color=MC_GRAY)


def _draw_arrow(ax, x1, y1, x2, y2, label="", color=MC_GRAY):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=2))
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2 + 0.25
        ax.text(mx, my, label, ha="center", va="center", fontsize=7.5,
                color=color, style="italic",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none"))


def illust_system_overview():
    """NAS → tamatex → Drive (Sheets + PDF) のシステム俯瞰図。"""
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    ax.set_xlim(-0.5, 11)
    ax.set_ylim(-0.3, 3.5)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    # Boxes
    _draw_box(ax, 0, 0.8, 2.2, 2.0, "NAS", "QNAP / Excel", MC_GRAY)
    _draw_box(ax, 3.5, 0.8, 2.5, 2.0, "tamatex", "15分ごとに自動同期", MC_PRIMARY)

    # Right side: Drive with two outputs
    _draw_box(ax, 7.5, 1.95, 2.8, 1.0, "Sheets", "フィルタ・検索", MC_GREEN)
    _draw_box(ax, 7.5, 0.6, 2.8, 1.0, "PDF", "印刷・配布用", MC_ORANGE)

    # Arrows
    _draw_arrow(ax, 2.3, 1.8, 3.4, 1.8, "アップロード")
    _draw_arrow(ax, 6.1, 2.0, 7.4, 2.4, "変換", MC_GREEN)
    _draw_arrow(ax, 6.1, 1.6, 7.4, 1.1, "PDF出力", MC_ORANGE)

    # Actors
    ax.text(1.1, 0.3, "事務員が編集", ha="center", fontsize=8, color=MC_GRAY)
    ax.text(8.9, 0.05, "営業・役員が外出先から閲覧", ha="center",
            fontsize=8, color=MC_GRAY)

    return _save_fig(fig, "system_overview")


def illust_sync_cycle():
    """同期サイクルのタイミング図。"""
    fig, ax = plt.subplots(figsize=(7.5, 2.2))
    ax.set_xlim(-0.5, 12)
    ax.set_ylim(-0.8, 2.5)
    ax.axis("off")

    ax.plot([0, 11], [0.8, 0.8], color=MC_GRAY, lw=2)

    times = ["10:00", "10:15", "10:30", "10:45", "11:00"]
    changed = [True, False, True, False, False]
    labels = ["変更あり\n→ 反映", "変更なし\n→ スキップ",
              "変更あり\n→ 反映", "変更なし\n→ スキップ",
              "変更なし\n→ スキップ"]

    for i, (t, ch, lbl) in enumerate(zip(times, changed, labels)):
        x = i * 2.75
        clr = MC_GREEN if ch else MC_GRAY
        ax.plot(x, 0.8, "o", color=clr, markersize=10, zorder=5)
        ax.text(x, 0.3, t, ha="center", fontsize=9, color=MC_DARK,
                fontweight="bold")
        ax.text(x, 1.55, lbl, ha="center", fontsize=7.5, color=clr,
                linespacing=1.5)

    ax.plot(0.5, -0.4, "o", color=MC_GREEN, markersize=7)
    ax.text(0.9, -0.4, "= 同期実行", fontsize=8, va="center", color=MC_GREEN)
    ax.plot(4.0, -0.4, "o", color=MC_GRAY, markersize=7)
    ax.text(4.4, -0.4, "= 変更なし（スキップ）", fontsize=8, va="center", color=MC_GRAY)

    return _save_fig(fig, "sync_cycle")


def illust_drive_structure():
    """Drive 上のフォルダ構造を表現。"""
    fig, ax = plt.subplots(figsize=(7.5, 2.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    # Root folder
    _draw_box(ax, 0.2, 1.5, 2.8, 2.0, "同期先\nフォルダ", "Google Drive上", MC_PRIMARY)

    # Sheets sub-folder
    _draw_box(ax, 4.2, 2.6, 2.6, 1.2, "Sheets/", "閲覧・検索・フィルタ", MC_GREEN)

    # PDF sub-folder
    _draw_box(ax, 4.2, 1.0, 2.6, 1.2, "PDF/", "印刷・配布用途", MC_ORANGE)

    # Files in each
    _draw_box(ax, 7.4, 2.6, 2.4, 1.2, "[同期] xxx", "Sheets形式", MC_GREEN)
    _draw_box(ax, 7.4, 1.0, 2.4, 1.2, "xxx.pdf", "PDF形式", MC_ORANGE)

    # Connector arrows
    _draw_arrow(ax, 3.1, 2.8, 4.1, 3.2, "", MC_GREEN)
    _draw_arrow(ax, 3.1, 2.2, 4.1, 1.6, "", MC_ORANGE)
    _draw_arrow(ax, 6.9, 3.2, 7.3, 3.2, "", MC_GREEN)
    _draw_arrow(ax, 6.9, 1.6, 7.3, 1.6, "", MC_ORANGE)

    ax.text(5.0, 0.4, "1つの Excel ファイルに対して Sheets と PDF が両方自動生成されます",
            ha="center", fontsize=8, color=MC_GRAY)

    return _save_fig(fig, "drive_structure")


def illust_format_preservation():
    """書式保持を可視化（Excel と Sheets を並べて表示）。"""
    fig, axes = plt.subplots(1, 2, figsize=(7.5, 2.6))
    fig.patch.set_facecolor("white")

    titles = ["Excel（NAS上の原本）", "Google Sheets（同期後）"]
    for ax, title in zip(axes, titles):
        ax.set_xlim(0, 4)
        ax.set_ylim(0, 5)
        ax.axis("off")
        ax.set_title(title, fontsize=10, fontweight="bold",
                     color=MC_PRIMARY, pad=8)

        # Header row (yellow)
        data = [
            ["品番", "金額", "ケース"],
            ["A-001", "¥360", "0.0ケース"],
            ["A-002", "¥1,321", "2.0ケース"],
            ["B-100", "¥842", "0.0ケース"],
        ]
        cell_colors = [
            ["#fff9c4"] * 3,
            ["#ffffff", "#ffffff", "#c8e6c9"],
            ["#ffffff", "#ffffff", "#ffcdd2"],
            ["#ffffff", "#ffffff", "#c8e6c9"],
        ]
        tbl = ax.table(cellText=data, cellColours=cell_colors,
                        loc="center", cellLoc="center")
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(9)
        tbl.scale(1, 1.5)
        for key, cell in tbl.get_celld().items():
            cell.set_edgecolor("#202124")
            cell.set_linewidth(0.8)
            if key[0] == 0:
                cell.set_text_props(fontweight="bold")

    fig.text(0.5, 0.02,
             "罫線・背景色・通貨書式・カスタム書式（"\
             "0.0ケース等）がそのまま再現されます",
             ha="center", fontsize=8, color=MC_GREEN, fontweight="bold")
    fig.subplots_adjust(wspace=0.25)
    return _save_fig(fig, "format_preservation")


def illust_update_behavior():
    """更新動作 — 旧データから新データへの置換を視覚化。"""
    fig, axes = plt.subplots(1, 3, figsize=(7.5, 2.5))
    fig.patch.set_facecolor("white")

    titles = ["① 更新前", "② 更新中（背後で置換）", "③ 更新後（リロードで反映）"]
    cell_colors_list = [
        [["#e8f0fe"] * 3 for _ in range(4)],
        [["#e8f0fe"] * 3 for _ in range(4)],
        [["#c8e6c9"] * 3 for _ in range(4)],
    ]
    data_list = [
        [["A-001", "100", "500"], ["A-002", "200", "300"],
         ["A-003", "150", "420"], ["A-004", "80", "610"]],
        [["A-001", "100", "500"], ["A-002", "200", "300"],
         ["A-003", "150", "420"], ["A-004", "80", "610"]],
        [["A-001", "120", "480"], ["A-002", "210", "290"],
         ["A-003", "155", "400"], ["A-004", "90", "600"]],
    ]

    for ax, title, data, cc in zip(axes, titles, data_list, cell_colors_list):
        ax.set_xlim(0, 3)
        ax.set_ylim(0, 5)
        ax.axis("off")
        ax.set_title(title, fontsize=9, fontweight="bold", color=MC_PRIMARY, pad=8)
        tbl = ax.table(cellText=data, cellColours=cc,
                        colLabels=["品番", "在庫", "価格"],
                        loc="center", cellLoc="center")
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(8)
        tbl.scale(1, 1.3)
        for key, cell in tbl.get_celld().items():
            cell.set_edgecolor("#dadce0")
            if key[0] == 0:
                cell.set_facecolor(MC_PRIMARY)
                cell.set_text_props(color="white", fontweight="bold")

    fig.text(0.365, 0.45, "→", fontsize=20, ha="center", va="center", color=MC_GRAY)
    fig.text(0.655, 0.45, "→", fontsize=20, ha="center", va="center", color=MC_GRAY)

    fig.text(0.5, 0.02,
             "※ 更新中はブラウザ表示は変わりません。リロード（F5）で最新が反映されます",
             ha="center", fontsize=7.5, color=MC_GRAY)

    fig.subplots_adjust(wspace=0.3)
    return _save_fig(fig, "update_behavior")


def illust_file_operations():
    """ファイル操作シナリオ図。"""
    fig, ax = plt.subplots(figsize=(7.5, 3.0))
    ax.set_xlim(-0.5, 10)
    ax.set_ylim(-0.5, 4)
    ax.axis("off")

    scenarios = [
        ("新規追加", 0, MC_GREEN,
         "NASに新Excel追加", "→",
         "Sheets と PDF\nを自動作成"),
        ("ファイル削除", 1.45, MC_ORANGE,
         "NASからExcel削除", "→",
         "Sheets と PDF\nはそのまま残る"),
        ("ファイル名変更", 2.9, MC_RED,
         "旧名: そのまま残る\n新名: 新規作成", "→",
         "URLが変わるため\n再共有が必要"),
    ]

    for title, row, color, left_text, arrow, right_text in scenarios:
        y = 3.2 - row * 1.35
        badge = FancyBboxPatch((0, y - 0.35), 1.8, 0.7,
                                boxstyle="round,pad=0.1",
                                facecolor=color, edgecolor="none", alpha=0.15)
        ax.add_patch(badge)
        ax.text(0.9, y, title, ha="center", va="center", fontsize=9,
                fontweight="bold", color=color)
        ax.text(3.5, y, left_text, ha="center", va="center", fontsize=8,
                color=MC_DARK, linespacing=1.5)
        ax.annotate("", xy=(6.0, y), xytext=(5.0, y),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=2))
        ax.text(7.8, y, right_text, ha="center", va="center", fontsize=8,
                color=MC_DARK, linespacing=1.5)

    return _save_fig(fig, "file_operations")


def illust_access():
    """マルチデバイス閲覧の図。"""
    fig, ax = plt.subplots(figsize=(7.5, 2.0))
    ax.set_xlim(-0.5, 10)
    ax.set_ylim(-0.2, 2.5)
    ax.axis("off")

    _draw_box(ax, 3.5, 0.4, 3.0, 1.6, "Sheets / PDF", "URL固定", MC_GREEN)
    _draw_box(ax, 0.2, 0.6, 1.6, 1.2, "PC", "事務所", MC_GRAY)
    _draw_box(ax, 7.8, 1.2, 1.6, 1.0, "スマホ", "", MC_GREEN)
    _draw_box(ax, 7.8, -0.1, 1.6, 1.0, "ノートPC", "", MC_GREEN)

    _draw_arrow(ax, 1.9, 1.2, 3.4, 1.2, "", MC_GRAY)
    _draw_arrow(ax, 6.6, 1.4, 7.7, 1.7, "", MC_GREEN)
    _draw_arrow(ax, 6.6, 1.0, 7.7, 0.5, "", MC_GREEN)

    ax.text(2.6, 1.55, "Excel編集", fontsize=7.5, ha="center", color=MC_GRAY)
    ax.text(7.3, 1.85, "閲覧・検索", fontsize=7.5, ha="center", color=MC_GREEN)
    ax.text(7.3, 0.25, "閲覧・検索", fontsize=7.5, ha="center", color=MC_GREEN)

    return _save_fig(fig, "access")


def illust_error_recovery():
    """障害時の自動復旧。"""
    fig, ax = plt.subplots(figsize=(7.5, 1.8))
    ax.set_xlim(-0.5, 10)
    ax.set_ylim(-0.2, 2.2)
    ax.axis("off")

    segments = [
        (0, 3, MC_GREEN, "正常同期"),
        (3, 6.5, MC_RED, "障害発生（同期停止）"),
        (6.5, 10, MC_GREEN, "復旧後 自動再開"),
    ]

    for x1, x2, color, label in segments:
        ax.plot([x1, x2], [0.8, 0.8], color=color, lw=6, solid_capstyle="round")
        ax.text((x1 + x2) / 2, 1.35, label, ha="center", fontsize=8,
                color=color, fontweight="bold")

    ax.text(3, 1.8, "⚡", fontsize=18, ha="center", va="center")
    ax.text(6.5, 1.8, "✔", fontsize=14, ha="center", va="center", color=MC_GREEN)

    ax.text(5.0, 0.2,
            "※ Drive 上のデータは消えません（最後に同期されたデータを保持）",
            ha="center", fontsize=8, color=MC_GRAY)

    return _save_fig(fig, "error_recovery")


# ============================================================
# PDF builder
# ============================================================
def build_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=20 * mm,
    )

    story = []

    img_overview = illust_system_overview()
    img_cycle = illust_sync_cycle()
    img_drive = illust_drive_structure()
    img_format = illust_format_preservation()
    img_update = illust_update_behavior()
    img_fileops = illust_file_operations()
    img_access = illust_access()
    img_error = illust_error_recovery()

    def add_img(path, width=CONTENT_W):
        story.append(Image(path, width=width, height=width * 0.37))

    def add_img_tall(path, width=CONTENT_W):
        story.append(Image(path, width=width, height=width * 0.42))

    # ======== COVER PAGE ========
    story.append(Spacer(1, 50 * mm))
    story.append(p("Excel 自動同期システム", "cover_title"))
    story.append(p("仕様・機能・注意事項", "cover_sub"))
    story.append(sp(10))
    story.append(hr())
    story.append(sp(6))
    story.append(p(
        "NAS上のExcelファイルを Google スプレッドシート と PDF へ自動で反映するシステムの仕様書です。",
        "body"))
    story.append(sp(10))
    add_img(img_overview)
    story.append(sp(30))
    story.append(p("バージョン 0.1.0（Drive API 直接アップロード方式・PDF同時生成対応版）",
                   "note"))
    story.append(PageBreak())

    # ======== TOC ========
    story.append(p("目次", "h1"))
    story.append(hr())
    toc_items = [
        "1. システムの概要",
        "2. できること",
        "3. 同期の仕組み",
        "4. 閲覧中に更新が入った場合の動作",
        "5. ファイルの追加・削除・名前変更",
        "6. 事務員の方への影響",
        "7. 反映されるデータ・書式について",
        "8. スプレッドシート・PDFの閲覧について",
        "9. システムが正常に動作しない場合",
        "10. 現時点での制約事項",
        "11. よくあるご質問",
    ]
    for item in toc_items:
        story.append(p(item, "body"))
    story.append(PageBreak())

    # ======== 1. OVERVIEW ========
    story.append(p("1. システムの概要", "h1"))
    story.append(hr())
    story.append(p(
        "本システムは、社内NASに保存されているExcelファイルの内容を、"
        "一定間隔で自動的に <b>Google スプレッドシート</b> および "
        "<b>PDF</b> へ反映します。"))
    story.append(p(
        "これにより、<b>事務員の方は今まで通りExcelで作業</b>しながら、"
        "<b>営業・役員・社長の方はスマートフォンやPCから外出先で"
        "スプレッドシートを閲覧</b>できるようになります。"))
    story.append(p(
        "スプレッドシートは <b>Excel と同じ見た目（罫線・色・マージセル・"
        "通貨書式・カスタム書式・非表示列）</b>が再現された状態で同期されます。"
        "フィルタや検索もスプレッドシート側で実行可能です。"
        "PDFは「印刷した状態」をそのまま再現したファイルとして同時生成されます。"))
    story.append(sp(4))
    add_img(img_overview)
    story.append(sp(4))
    add_img(img_access)

    # ======== 2. FEATURES ========
    story.append(sp(4))
    story.append(p("2. できること", "h1"))
    story.append(hr())
    features = [
        ["機能", "説明"],
        ["自動同期",
         "Excelファイルの更新を検知し、Google Sheets と PDF へ自動反映します"],
        ["書式の自動再現",
         "罫線・セル背景色・文字色・マージセル・通貨書式・"
         "カスタム数値書式・非表示列・列幅 がGoogle側で自動的に保持されます"],
        ["数式の保持",
         "Excel 内の数式はそのまま Sheets 側でも数式として動作します（"
         "=SUM 等の関数は Sheets 互換に自動変換）"],
        ["PDF同時生成",
         "スプレッドシートと同じ内容を PDF としても自動生成します（印刷・配布用途）"],
        ["複数ファイル対応",
         "NAS内のExcelファイル（10〜20個程度）をまとめて管理します"],
        ["複数シート対応",
         "1つのExcel内にシートが複数あっても、すべて反映されます"],
        ["サブフォルダ対応",
         "NASフォルダ内にサブフォルダがある場合も、中のExcelを検出します"],
        ["新規ファイル自動検知",
         "NASに新しいExcelを追加すると、自動でスプレッドシートとPDFが作成されます"],
        ["URL固定",
         "一度作成されたスプレッドシート・PDFのURLは変わりません。ブックマーク可能です"],
        ["閲覧者の自動設定",
         "指定したメールアドレスに対し、閲覧権限が自動で付与されます"],
        ["フィルタビュー対応",
         "閲覧者でも「フィルタビュー」機能で自分専用の絞り込み・並び替えが可能"],
        ["常時自動運用",
         "社内PCで自動起動し、PC再起動後も自動で復帰します"],
    ]
    story.append(styled_table(features, col_widths=[40 * mm, CONTENT_W - 42 * mm]))

    # ======== 3. SYNC MECHANISM ========
    story.append(PageBreak())
    story.append(p("3. 同期の仕組み", "h1"))
    story.append(hr())

    story.append(p("3-1. 同期の方向", "h2"))
    story.append(p(
        "<b>NASのExcel → スプレッドシート / PDF の一方向のみ</b>です。"))
    story.append(p("・事務員がExcelを更新 → スプレッドシートとPDFに反映される", "bullet"))
    story.append(p("・スプレッドシート上で編集しても → Excelには反映されません", "bullet"))
    story.append(p("スプレッドシート・PDFは <b>閲覧専用</b> としてご利用ください。"))

    story.append(sp(2))
    story.append(p("3-2. 同期のタイミング", "h2"))
    story.append(p(
        "<b>15分に1回</b>、自動で同期処理が実行されます。"
        "事務員がExcelを保存してから、<b>最大15分後</b>にスプレッドシートとPDFへ反映されます。"
        "変更がないファイルは処理をスキップします。同期間隔は設定で変更可能です（5分・30分など）。"))
    story.append(sp(3))
    add_img(img_cycle)

    story.append(sp(2))
    story.append(p("3-3. 変更の検知方法", "h2"))
    story.append(p(
        "Excelファイルの<b>更新日時</b>と<b>ファイル内容</b>の両方を確認して変更を検知します。"
        "内容に変化がなければ、保存しただけでは同期は実行されません。"))

    story.append(sp(2))
    story.append(p("3-4. 同期処理の実体", "h2"))
    story.append(p(
        "同期処理では、NAS上のExcelファイルそのものをGoogle Driveにアップロードし、"
        "Google側のコンバータが xlsx を Sheets 形式へ自動変換します。"
        "この方式により <b>書式・数式・非表示列がすべて保持</b> されます。"
        "変換された Sheets はその場で PDF にもエクスポートされます。"))

    # ======== 4. UPDATE BEHAVIOR ========
    story.append(PageBreak())
    story.append(p("4. 閲覧中に更新が入った場合の動作", "h1"))
    story.append(hr())
    story.append(p(
        "スプレッドシートを閲覧中にちょうど更新タイミングが来た場合、"
        "Google 側でファイル全体が新しい内容に置換されます。"))
    story.append(sp(3))

    upd_table = [
        ["タイミング", "画面に表示される内容"],
        ["更新処理の前", "前回同期時のデータ（古いデータ）"],
        ["更新処理の実行中", "ブラウザはキャッシュ時点のデータを表示し続ける"],
        ["更新処理の後",
         "ブラウザを再読み込み（リロード）すると最新データが表示"],
    ]
    story.append(styled_table(upd_table, col_widths=[40 * mm, CONTENT_W - 42 * mm]))
    story.append(sp(4))
    add_img_tall(img_update)
    story.append(sp(2))
    story.append(p("・閲覧中にデータが消える・空白になることはありません", "bullet"))
    story.append(p(
        "・最新データを即座に確認したい場合は、ブラウザの再読み込み（F5 / 下スワイプ）をしてください",
        "bullet"))
    story.append(p("・スマホの Google スプレッドシートアプリでも、開き直しで最新データが取得されます",
                   "bullet"))

    # ======== 5. FILE OPS ========
    story.append(sp(4))
    story.append(p("5. ファイルの追加・削除・名前変更", "h1"))
    story.append(hr())

    story.append(p("<b>新しいExcelファイルをNASに追加した場合</b>", "h2"))
    story.append(p(
        "次の同期タイミングで自動検知し、Sheetsフォルダに新しいスプレッドシートが、"
        "PDFフォルダに新しいPDFが自動作成されます。"
        "設定済みの閲覧者への共有も自動で行われます。"))

    story.append(p("<b>NASからExcelファイルを削除した場合</b>", "h2"))
    story.append(p(
        "対応するスプレッドシートとPDFは <b>削除されません</b>。"
        "最後に同期されたデータがそのまま残ります（データ保全のための仕様）。"
        "不要になったファイルは、Google Drive上で手動で削除してください。"))

    story.append(p("<b>Excelファイルの名前を変更した場合</b>", "h2"))
    story.append(p(
        "旧ファイル名のスプレッドシート・PDFはそのまま残り、新ファイル名で新しいスプレッドシート・PDFが作成されます。"
        "<b>URLが変わるため、営業・役員には新しいURLをお知らせする必要があります。</b>"
        "頻繁なファイル名変更は避けることをお勧めします。"))

    story.append(sp(3))
    add_img_tall(img_fileops)

    story.append(sp(4))
    story.append(p("<b>Excelのシート構成を変更した場合</b>", "h2"))
    sheet_ops = [
        ["操作", "動作"],
        ["シートの追加", "次回同期時にスプレッドシート側にもシートが追加されます"],
        ["シートの削除", "次回同期時にスプレッドシート側のシートも削除されます"],
        ["シート名の変更", "旧シート名は削除され、新シート名のシートに切り替わります"],
    ]
    story.append(styled_table(sheet_ops, col_widths=[40 * mm, CONTENT_W - 42 * mm]))
    story.append(p(
        "ファイル全体を毎回置換する仕組みのため、Excel側のシート構成と Sheets 側は <b>常に完全一致</b> します。",
        "note"))

    # ======== 6. OFFICE WORKER IMPACT ========
    story.append(sp(4))
    story.append(p("6. 事務員の方への影響", "h1"))
    story.append(hr())
    story.append(p("<b>ありません。</b>今まで通りの作業で問題ありません。"))
    story.append(p("・NAS上のExcelをいつも通り開いて、編集して、保存してください", "bullet"))
    story.append(p("・特別な操作や手順の変更は一切不要です", "bullet"))
    story.append(p("・Excelの動作が遅くなることもありません", "bullet"))
    story.append(p("・事務員がExcelを編集中（開いている状態）でも、システムは正常に動作します",
                   "bullet"))
    story.append(p("・Excelが保存されるたびに、次の同期タイミングで反映されます", "bullet"))

    # ======== 7. DATA & FORMAT ========
    story.append(PageBreak())
    story.append(p("7. 反映されるデータ・書式について", "h1"))
    story.append(hr())
    story.append(p("<b>7-1. データの反映</b>", "h2"))
    conv_table = [
        ["Excelでの入力", "スプレッドシートでの表示"],
        ["数値（123, 45.6）", "数値としてそのまま反映"],
        ["文字列（在庫あり）", "そのまま表示"],
        ["日付・日時", "Excel と同じ書式で表示（書式情報も保持）"],
        ["数式（=SUM(A1:A10)）",
         "Sheets 互換の数式に変換され、Sheets 側でも再計算されます"],
        ["通貨（¥360, $1,000）", "通貨記号付きでそのまま表示"],
        ["カスタム書式（\"0.0ケース\"）", "書式定義ごとそのまま反映"],
        ["空セル", "空白のまま"],
    ]
    story.append(styled_table(conv_table, col_widths=[CONTENT_W * 0.4, CONTENT_W * 0.58]))
    story.append(sp(4))

    story.append(p("<b>7-2. 書式の反映（Google コンバータが自動保持）</b>", "h2"))
    fmt_table = [
        ["書式要素", "反映"],
        ["罫線（細線・太線・二重線）", "✓ 保持"],
        ["セル背景色", "✓ 保持"],
        ["文字色・太字・斜体", "✓ 保持"],
        ["マージセル（結合セル）", "✓ Excel と同じ範囲で結合表示"],
        ["非表示の行・列", "✓ Excel で非表示の列は Sheets 側でも非表示"],
        ["列幅・行高", "✓ 概ね保持"],
    ]
    story.append(styled_table(fmt_table, col_widths=[CONTENT_W * 0.5, CONTENT_W * 0.48]))
    story.append(sp(4))
    add_img(img_format)

    story.append(sp(4))
    story.append(p("<b>7-3. 反映されないもの・注意点</b>", "h2"))
    note_table = [
        ["項目", "内容"],
        ["グラフ・画像",
         "Excel内のグラフや画像は Sheets 側に反映されない場合があります"],
        ["マクロ（VBA）",
         "マクロのコード自体は反映されません（実行後に保存された値・書式は反映されます）"],
        ["一部の特殊な数式",
         "Excel 固有関数の一部は #NAME? などのエラーとして表示される場合があります"],
        ["印刷設定",
         "ヘッダー・フッターなど一部の印刷設定は反映されない場合があります"],
    ]
    story.append(styled_table(note_table, col_widths=[CONTENT_W * 0.3, CONTENT_W * 0.68]))
    story.append(p(
        "Excel の見た目とほぼ同じ形で同期されますが、完全な100%再現を保証するものではありません。"
        "重要な業務帳票で気になる差異がある場合は、PDFの方をご利用ください"
        "（PDFは印刷状態をそのまま反映します）。",
        "note"))

    # ======== 8. VIEWING ========
    story.append(PageBreak())
    story.append(p("8. スプレッドシート・PDFの閲覧について", "h1"))
    story.append(hr())

    story.append(p("<b>アクセス方法 — Drive 上のフォルダ構造</b>", "h2"))
    story.append(p(
        "Google Drive 内の指定フォルダに、以下のサブフォルダ構造で格納されます。"))
    story.append(sp(2))
    add_img(img_drive)
    story.append(sp(2))
    story.append(p("・<b>Sheets/</b> 配下: フィルタ・検索が可能なスプレッドシート版", "bullet"))
    story.append(p("・<b>PDF/</b> 配下: 印刷・配布向けのPDF版", "bullet"))
    story.append(p("各スプレッドシートの名前は「[同期] Excelファイル名」、PDFの名前は「Excelファイル名.pdf」 という形式です。",
                   "note"))

    story.append(sp(2))
    story.append(p("<b>ブックマーク</b>", "h2"))
    story.append(p(
        "スプレッドシート・PDF の URL は固定です（ファイル内容が更新されてもURLは変わりません）。"
        "一度ブラウザでブックマークしておけば、次回以降は同じURLで最新データを確認できます。"))

    story.append(sp(2))
    story.append(p("<b>スマートフォンからの閲覧</b>", "h2"))
    story.append(p("・スプレッドシート: Google スプレッドシートアプリ（iOS / Android）から閲覧",
                   "bullet"))
    story.append(p("・PDF: ブラウザまたは標準のPDFビューアで閲覧", "bullet"))

    story.append(sp(2))
    story.append(p("<b>閲覧権限とフィルタ・検索</b>", "h2"))
    story.append(p(
        "営業・役員の方には<b>閲覧のみ</b>の権限が付与されます。"
        "編集はできませんが、以下の操作は閲覧者のままで可能です。"))

    perm_table = [
        ["操作", "閲覧者で可能か"],
        ["検索（Ctrl+F）", "✓ 可能"],
        ["フィルタビュー（自分専用フィルタ）", "✓ 可能"],
        ["フィルタビュー内での並べ替え", "✓ 可能"],
        ["通常フィルタ（他人にも影響する）", "× 編集者権限が必要"],
        ["シート全体のソート", "× 編集者権限が必要"],
    ]
    story.append(styled_table(perm_table, col_widths=[CONTENT_W * 0.55, CONTENT_W * 0.43]))
    story.append(p(
        "フィルタビューの作り方: スプレッドシートで「データ」メニュー → 「フィルタビューを作成」"
        "から作成できます。閲覧者でも自由に作成・利用でき、他の閲覧者には見えません。",
        "note"))

    # ======== 9. ERROR HANDLING ========
    story.append(PageBreak())
    story.append(p("9. システムが正常に動作しない場合", "h1"))
    story.append(hr())
    story.append(p("以下のような状況では、同期が一時的に停止または遅延する場合があります。"))
    story.append(sp(2))

    err_table = [
        ["状況", "影響", "自動復旧"],
        ["NASの電源が切れている",
         "同期が停止（既存のスプレッドシート・PDFは保持）",
         "NAS復旧後、自動で再開"],
        ["社内ネットワークの障害", "同期が停止", "ネットワーク復旧後、自動で再開"],
        ["インターネット接続の障害", "Googleへの送信ができない",
         "接続復旧後、自動で再開"],
        ["同期用PCの電源が切れた", "同期が停止", "PC再起動後、自動で再開"],
        ["Excelファイルが破損している",
         "該当ファイルのみスキップ、他のファイルは正常に同期",
         "ファイル修復後、自動で再開"],
    ]
    story.append(styled_table(err_table, col_widths=[CONTENT_W * 0.30, CONTENT_W * 0.40,
                                                       CONTENT_W * 0.28]))
    story.append(sp(4))
    add_img(img_error)
    story.append(sp(2))
    story.append(p(
        "いずれの場合も、<b>Google Drive 上のデータが消えることはありません。</b>"
        "最後に同期された時点のデータが保持されます。"))

    # ======== 10. LIMITATIONS ========
    story.append(sp(4))
    story.append(p("10. 現時点での制約事項", "h1"))
    story.append(hr())

    lim_table = [
        ["項目", "内容"],
        ["同期の方向", "NAS → Sheets / PDF の一方向のみ。逆方向はできません"],
        ["リアルタイム性", "最大15分の遅延があります（即時反映ではありません）"],
        ["グラフ・画像", "Excel内のグラフや画像は反映されない場合があります"],
        ["マクロ（VBA）",
         "マクロのコード本体は反映されません（実行結果として保存された値・書式は反映されます）"],
        ["一部の特殊な数式",
         "Excel 固有関数の一部は Sheets 上で #NAME? 等になる可能性があります"],
        [".xls形式",
         "旧形式（.xls）のExcelファイルには対応していません。.xlsx形式のみ対象です"],
        ["同時編集", "スプレッドシートでの同時編集には対応しません（閲覧専用）"],
        ["通知機能",
         "同期の成功・失敗を自動通知する機能は現時点では未搭載です"],
        ["ファイルサイズ",
         "Sheets の上限は約1,000万セル / 200MB です。"
         "通常の業務ファイルではまず到達しません"],
    ]
    story.append(styled_table(lim_table, col_widths=[CONTENT_W * 0.25, CONTENT_W * 0.73]))

    # ======== 11. FAQ ========
    story.append(PageBreak())
    story.append(p("11. よくあるご質問", "h1"))
    story.append(hr())

    faqs = [
        ("Q. 事務員がExcelを開いたまま（編集中）でも同期されますか？",
         "A. はい。Excelが保存された時点の内容が、次の同期タイミングで反映されます。"
         "ただし、保存せずに開いたままの編集中の内容は反映されません。"),
        ("Q. 同期間隔を変更できますか？",
         "A. はい。設定ファイルで変更可能です（例: 5分、10分、30分など）。"
         "変更後はサービスの再起動が必要です。"),
        ("Q. スプレッドシートを誤って削除してしまった場合は？",
         "A. NAS上のExcelファイルが残っていれば、次の同期タイミングで新しいスプレッドシートが"
         "自動作成されます。ただしURLが変わりますので、ブックマークの更新が必要です。"),
        ("Q. 閲覧者を追加・削除したい場合は？",
         "A. 管理者にご依頼ください。設定ファイルの変更で対応いたします。"
         "また、Google Drive上で手動での共有追加も可能です。"),
        ("Q. Excel の数式は使えますか？",
         "A. はい。=SUM()、=VLOOKUP() 等の一般的な関数はそのまま Sheets でも動作します。"
         "ただし、Excel 固有の特殊関数や配列数式の一部は変換できない場合があります。"),
        ("Q. 罫線や色は反映されますか？",
         "A. はい。罫線・セル背景色・文字色・マージセル・通貨書式・カスタム書式（"
         "例: \"0.0ケース\"）など、ほぼすべての書式が Excel と同じ見た目で再現されます。"),
        ("Q. 非表示にしている列は Sheets 側でも非表示になりますか？",
         "A. はい。Excel で非表示にしている列は Sheets 側でも非表示の状態で同期されます。"),
        ("Q. PDF と Sheets はどう使い分ければ良いですか？",
         "A. データを検索したい・絞り込みたい・スマホで見やすくしたい場合は <b>Sheets</b>。"
         "印刷したい・取引先に送付したい・見た目を完全に保ちたい場合は <b>PDF</b> を"
         "ご利用ください。両方とも自動生成されています。"),
        ("Q. 閲覧者で並べ替えやフィルタを使うには？",
         "A. スプレッドシートの「データ」メニューから <b>「フィルタビューを作成」</b> を"
         "ご利用ください。フィルタビューは閲覧者でも自由に作成でき、"
         "他の閲覧者には影響しません（自分だけの絞り込みビューです）。"),
        ("Q. NASのフォルダ構成を変更しても大丈夫ですか？",
         "A. 同期対象フォルダの配下であれば、サブフォルダの追加・移動は自動対応されます。"
         "ただし、同期対象フォルダ自体のパスを変更する場合は、設定の変更が必要です。"),
        ("Q. 同期が止まっているかもしれません。確認方法は？",
         "A. スプレッドシートの内容がしばらく更新されていない場合は、管理者にご連絡ください。"
         "同期用PCのログを確認して対応いたします。"),
    ]

    for q, a in faqs:
        story.append(p(q, "qa_q"))
        story.append(p(a, "qa_a"))

    # Footer
    story.append(sp(20))
    story.append(hr())
    story.append(p(
        "本書はシステムバージョン 0.1.0（Drive API 直接アップロード方式・PDF同時生成対応版）時点の内容です。",
        "note"))

    doc.build(story)


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    output = project_root / "docs" / "システム仕様書.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(str(output))
    print(f"PDF generated: {output}")
