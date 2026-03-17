"""顧客向けシステム仕様書のPDF生成スクリプト。イラスト付き。"""

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

# matplotlib colors
MC_PRIMARY = "#1a73e8"
MC_GREEN = "#34a853"
MC_ORANGE = "#ea8600"
MC_RED = "#ea4335"
MC_GRAY = "#5f6368"
MC_LIGHT = "#e8f0fe"
MC_BG = "#f8f9fa"
MC_DARK = "#202124"

# ============================================================
# Styles
# ============================================================
PAGE_W, PAGE_H = A4
MARGIN = 20 * mm
CONTENT_W = PAGE_W - 2 * MARGIN


def _ps(name, **kwargs):
    """ParagraphStyleを作成。デフォルトでJPGothicフォントを使用。"""
    defaults = {"fontName": FONT_NAME, "leading": 20, "textColor": C_DARK}
    defaults.update(kwargs)
    return ParagraphStyle(name, **defaults)


def make_styles():
    """ParagraphStyleの辞書を返す。"""
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
# Table helper
# ============================================================
def styled_table(data, col_widths=None, header=True):
    """統一スタイルのテーブルを作成。"""
    style_cmds = [
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LEADING", (0, 0), (-1, -1), 15),
        ("TEXTCOLOR", (0, 0), (-1, -1), C_DARK),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
    ]
    if header:
        style_cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
        ]
    # Alternate row colors
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), C_LIGHT_GRAY))

    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    t.setStyle(TableStyle(style_cmds))
    return t


def p(text, style_name="body"):
    """shortcut for Paragraph."""
    return Paragraph(text, S[style_name])


def sp(h=6):
    return Spacer(1, h * mm)


def hr():
    return HRFlowable(width="100%", thickness=0.5, color=C_BORDER,
                       spaceBefore=3, spaceAfter=8)


# ============================================================
# Illustrations (matplotlib → temp PNG)
# ============================================================
TMP_DIR = tempfile.mkdtemp()


def _save_fig(fig, name, dpi=180):
    path = os.path.join(TMP_DIR, f"{name}.png")
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white", pad_inches=0.2)
    plt.close(fig)
    return path


def _draw_box(ax, x, y, w, h, label, sub="", color=MC_PRIMARY, icon=None):
    """角丸ボックスを描画する。"""
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
    """System flow diagram."""
    fig, ax = plt.subplots(figsize=(7.5, 2.8))
    ax.set_xlim(-0.5, 10.5)
    ax.set_ylim(-0.3, 3.0)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    # Boxes
    _draw_box(ax, 0, 0.3, 2.5, 2.2, "NAS", "QNAP", MC_GRAY)
    _draw_box(ax, 3.8, 0.3, 2.8, 2.2, "tamatex", "15\u5206\u3054\u3068\u306B\u81EA\u52D5\u540C\u671F", MC_PRIMARY)
    _draw_box(ax, 7.8, 0.3, 2.5, 2.2, "Google\nSheets", "\u5916\u51FA\u5148\u304B\u3089\u95B2\u89A7", MC_GREEN)

    # Arrows
    _draw_arrow(ax, 2.6, 1.4, 3.7, 1.4, "\u8AAD\u307F\u53D6\u308A")
    _draw_arrow(ax, 6.7, 1.4, 7.7, 1.4, "\u66F8\u304D\u8FBC\u307F")

    # Actors
    ax.text(1.25, -0.1, "\u4E8B\u52D9\u54E1\u304C\u7DE8\u96C6", ha="center", fontsize=8, color=MC_GRAY)
    ax.text(9.05, -0.1, "\u55B6\u696D\u30FB\u5F79\u54E1\u304C\u95B2\u89A7", ha="center", fontsize=8, color=MC_GRAY)

    return _save_fig(fig, "system_overview")


def illust_sync_cycle():
    """Sync timing diagram."""
    fig, ax = plt.subplots(figsize=(7.5, 2.2))
    ax.set_xlim(-0.5, 12)
    ax.set_ylim(-0.8, 2.5)
    ax.axis("off")

    # Timeline
    ax.plot([0, 11], [0.8, 0.8], color=MC_GRAY, lw=2)

    times = ["10:00", "10:15", "10:30", "10:45", "11:00"]
    states = ["check", "check", "check", "check", "check"]
    changed = [True, False, True, False, False]
    labels = ["\u5909\u66F4\u3042\u308A\n\u2192 \u53CD\u6620", "\u5909\u66F4\u306A\u3057\n\u2192 \u30B9\u30AD\u30C3\u30D7",
              "\u5909\u66F4\u3042\u308A\n\u2192 \u53CD\u6620", "\u5909\u66F4\u306A\u3057\n\u2192 \u30B9\u30AD\u30C3\u30D7",
              "\u5909\u66F4\u306A\u3057\n\u2192 \u30B9\u30AD\u30C3\u30D7"]

    for i, (t, ch, lbl) in enumerate(zip(times, changed, labels)):
        x = i * 2.75
        clr = MC_GREEN if ch else MC_GRAY
        marker = "\u2714" if ch else "\u2015"

        ax.plot(x, 0.8, "o", color=clr, markersize=10, zorder=5)
        ax.text(x, 0.3, t, ha="center", fontsize=9, color=MC_DARK,
                fontweight="bold")
        ax.text(x, 1.55, lbl, ha="center", fontsize=7.5, color=clr,
                linespacing=1.5)

    # Legend
    ax.plot(0.5, -0.4, "o", color=MC_GREEN, markersize=7)
    ax.text(0.9, -0.4, "= \u540C\u671F\u5B9F\u884C", fontsize=8, va="center", color=MC_GREEN)
    ax.plot(4.0, -0.4, "o", color=MC_GRAY, markersize=7)
    ax.text(4.4, -0.4, "= \u5909\u66F4\u306A\u3057\uFF08\u30B9\u30AD\u30C3\u30D7\uFF09", fontsize=8, va="center", color=MC_GRAY)

    return _save_fig(fig, "sync_cycle")


def illust_update_behavior():
    """Update behavior — no blank screen."""
    fig, axes = plt.subplots(1, 3, figsize=(7.5, 2.5))
    fig.patch.set_facecolor("white")

    titles = ["\u2460 \u66F4\u65B0\u524D", "\u2461 \u66F4\u65B0\u4E2D", "\u2462 \u66F4\u65B0\u5F8C"]
    cell_colors_list = [
        # Before: old data
        [["#e8f0fe"] * 3 for _ in range(4)],
        # During: mixed
        [["#c8e6c9"] * 3, ["#c8e6c9"] * 3, ["#e8f0fe"] * 3, ["#e8f0fe"] * 3],
        # After: all new
        [["#c8e6c9"] * 3 for _ in range(4)],
    ]
    data_list = [
        [["A-001", "100", "500"], ["A-002", "200", "300"],
         ["A-003", "150", "420"], ["A-004", "80", "610"]],
        [["A-001", "120", "480"], ["A-002", "210", "290"],
         ["A-003", "150", "420"], ["A-004", "80", "610"]],
        [["A-001", "120", "480"], ["A-002", "210", "290"],
         ["A-003", "155", "400"], ["A-004", "90", "600"]],
    ]

    for ax, title, data, cc in zip(axes, titles, data_list, cell_colors_list):
        ax.set_xlim(0, 3)
        ax.set_ylim(0, 5)
        ax.axis("off")
        ax.set_title(title, fontsize=10, fontweight="bold", color=MC_PRIMARY, pad=8)
        tbl = ax.table(cellText=data, cellColours=cc,
                        colLabels=["\u54C1\u756A", "\u5728\u5EAB", "\u4FA1\u683C"],
                        loc="center", cellLoc="center")
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(8)
        tbl.scale(1, 1.3)
        for key, cell in tbl.get_celld().items():
            cell.set_edgecolor("#dadce0")
            if key[0] == 0:
                cell.set_facecolor(MC_PRIMARY)
                cell.set_text_props(color="white", fontweight="bold")

    # Arrows between
    fig.text(0.365, 0.45, "\u2192", fontsize=20, ha="center", va="center", color=MC_GRAY)
    fig.text(0.655, 0.45, "\u2192", fontsize=20, ha="center", va="center", color=MC_GRAY)

    fig.text(0.5, 0.02, "\u203B \u7DD1\u306E\u30BB\u30EB = \u65B0\u3057\u3044\u30C7\u30FC\u30BF\u3067\u4E0A\u66F8\u304D\u6E08\u307F\u3000\u9752\u306E\u30BB\u30EB = \u307E\u3060\u65E7\u30C7\u30FC\u30BF\u3000\u203B\u7A7A\u767D\u306B\u306F\u306A\u308A\u307E\u305B\u3093",
             ha="center", fontsize=7.5, color=MC_GRAY)

    fig.subplots_adjust(wspace=0.3)
    return _save_fig(fig, "update_behavior")


def illust_file_operations():
    """File add/delete/rename diagram."""
    fig, ax = plt.subplots(figsize=(7.5, 3.0))
    ax.set_xlim(-0.5, 10)
    ax.set_ylim(-0.5, 4)
    ax.axis("off")

    # Three scenarios
    scenarios = [
        ("\u65B0\u898F\u8FFD\u52A0", 0, MC_GREEN,
         "NAS\u306B\u65B0Excel\u8FFD\u52A0", "\u2192", "\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\n\u81EA\u52D5\u4F5C\u6210"),
        ("\u30D5\u30A1\u30A4\u30EB\u524A\u9664", 1.45, MC_ORANGE,
         "NAS\u304B\u3089Excel\u524A\u9664", "\u2192", "\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\n\u306F\u305D\u306E\u307E\u307E\u6B8B\u308B"),
        ("\u30D5\u30A1\u30A4\u30EB\u540D\u5909\u66F4", 2.9, MC_RED,
         "\u65E7\u540D: \u305D\u306E\u307E\u307E\u6B8B\u308B\n\u65B0\u540D: \u65B0\u898F\u4F5C\u6210", "\u2192", "URL\u304C\u5909\u308F\u308B\u305F\u3081\n\u518D\u5171\u6709\u304C\u5FC5\u8981"),
    ]

    for title, row, color, left_text, arrow, right_text in scenarios:
        y = 3.2 - row * 1.35
        # Title badge
        badge = FancyBboxPatch((0, y - 0.35), 1.8, 0.7, boxstyle="round,pad=0.1",
                                facecolor=color, edgecolor="none", alpha=0.15)
        ax.add_patch(badge)
        ax.text(0.9, y, title, ha="center", va="center", fontsize=9,
                fontweight="bold", color=color)
        # Left
        ax.text(3.5, y, left_text, ha="center", va="center", fontsize=8,
                color=MC_DARK, linespacing=1.5)
        # Arrow
        ax.annotate("", xy=(6.0, y), xytext=(5.0, y),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=2))
        # Right
        ax.text(7.8, y, right_text, ha="center", va="center", fontsize=8,
                color=MC_DARK, linespacing=1.5)

    return _save_fig(fig, "file_operations")


def illust_access():
    """Multi-device access illustration."""
    fig, ax = plt.subplots(figsize=(7.5, 2.0))
    ax.set_xlim(-0.5, 10)
    ax.set_ylim(-0.2, 2.5)
    ax.axis("off")

    # Center: Spreadsheet
    _draw_box(ax, 3.5, 0.4, 3.0, 1.6, "Google\n\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8",
              "URL\u56FA\u5B9A", MC_GREEN)

    # Left: Office PC
    _draw_box(ax, 0.2, 0.6, 1.6, 1.2, "PC", "\u4E8B\u52D9\u6240", MC_GRAY)

    # Right top: Smartphone
    _draw_box(ax, 7.8, 1.2, 1.6, 1.0, "\u30B9\u30DE\u30DB", "", MC_GREEN)

    # Right bottom: Laptop
    _draw_box(ax, 7.8, -0.1, 1.6, 1.0, "\u30CE\u30FC\u30C8PC", "", MC_GREEN)

    # Arrows
    _draw_arrow(ax, 1.9, 1.2, 3.4, 1.2, "", MC_GRAY)
    _draw_arrow(ax, 6.6, 1.4, 7.7, 1.7, "", MC_GREEN)
    _draw_arrow(ax, 6.6, 1.0, 7.7, 0.5, "", MC_GREEN)

    ax.text(2.6, 1.55, "Excel\u7DE8\u96C6", fontsize=7.5, ha="center", color=MC_GRAY)
    ax.text(7.3, 1.85, "\u95B2\u89A7", fontsize=7.5, ha="center", color=MC_GREEN)
    ax.text(7.3, 0.25, "\u95B2\u89A7", fontsize=7.5, ha="center", color=MC_GREEN)

    return _save_fig(fig, "access")


def illust_error_recovery():
    """障害時の自動復旧イラスト。"""
    fig, ax = plt.subplots(figsize=(7.5, 1.8))
    ax.set_xlim(-0.5, 10)
    ax.set_ylim(-0.2, 2.2)
    ax.axis("off")

    # Timeline: Normal → Error → Recovery
    segments = [
        (0, 3, MC_GREEN, "\u6B63\u5E38\u540C\u671F"),
        (3, 6.5, MC_RED, "\u969C\u5BB3\u767A\u751F\uFF08\u540C\u671F\u505C\u6B62\uFF09"),
        (6.5, 10, MC_GREEN, "\u5FA9\u65E7\u5F8C \u81EA\u52D5\u518D\u958B"),
    ]

    for x1, x2, color, label in segments:
        ax.plot([x1, x2], [0.8, 0.8], color=color, lw=6, solid_capstyle="round")
        ax.text((x1 + x2) / 2, 1.35, label, ha="center", fontsize=8,
                color=color, fontweight="bold")

    # Lightning bolt at error point
    ax.text(3, 1.8, "\u26A1", fontsize=18, ha="center", va="center")
    ax.text(6.5, 1.8, "\u2714", fontsize=14, ha="center", va="center", color=MC_GREEN)

    ax.text(5.0, 0.2, "\u203B \u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u306E\u30C7\u30FC\u30BF\u306F\u6D88\u3048\u307E\u305B\u3093\uFF08\u6700\u5F8C\u306E\u540C\u671F\u30C7\u30FC\u30BF\u3092\u4FDD\u6301\uFF09",
             ha="center", fontsize=8, color=MC_GRAY)

    return _save_fig(fig, "error_recovery")


# ============================================================
# PDF Document Builder
# ============================================================
def build_pdf(output_path: str):
    """メインPDF構築。"""
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=20 * mm,
    )

    story = []

    # Generate all illustrations first
    img_overview = illust_system_overview()
    img_cycle = illust_sync_cycle()
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
    story.append(p("Excel \u81EA\u52D5\u540C\u671F\u30B7\u30B9\u30C6\u30E0", "cover_title"))
    story.append(p("\u4ED5\u69D8\u30FB\u6A5F\u80FD\u30FB\u6CE8\u610F\u4E8B\u9805", "cover_sub"))
    story.append(sp(10))
    story.append(hr())
    story.append(sp(6))
    story.append(p("NAS\u4E0A\u306EExcel\u30D5\u30A1\u30A4\u30EB\u3092 Google \u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u3078\u81EA\u52D5\u3067\u53CD\u6620\u3059\u308B\u30B7\u30B9\u30C6\u30E0\u306E\u4ED5\u69D8\u66F8\u3067\u3059\u3002", "body"))
    story.append(sp(10))
    add_img(img_overview)
    story.append(sp(30))
    story.append(p("\u30D0\u30FC\u30B8\u30E7\u30F3 0.1.0", "note"))
    story.append(PageBreak())

    # ======== TOC ========
    story.append(p("\u76EE\u6B21", "h1"))
    story.append(hr())
    toc_items = [
        "1. \u30B7\u30B9\u30C6\u30E0\u306E\u6982\u8981",
        "2. \u3067\u304D\u308B\u3053\u3068",
        "3. \u540C\u671F\u306E\u4ED5\u7D44\u307F",
        "4. \u95B2\u89A7\u4E2D\u306B\u66F4\u65B0\u304C\u5165\u3063\u305F\u5834\u5408\u306E\u52D5\u4F5C",
        "5. \u30D5\u30A1\u30A4\u30EB\u306E\u8FFD\u52A0\u30FB\u524A\u9664\u30FB\u540D\u524D\u5909\u66F4",
        "6. \u4E8B\u52D9\u54E1\u306E\u65B9\u3078\u306E\u5F71\u97FF",
        "7. \u65E5\u4ED8\u30FB\u6570\u5024\u306E\u8868\u793A\u306B\u3064\u3044\u3066",
        "8. \u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u306E\u95B2\u89A7\u306B\u3064\u3044\u3066",
        "9. \u30B7\u30B9\u30C6\u30E0\u304C\u6B63\u5E38\u306B\u52D5\u4F5C\u3057\u306A\u3044\u5834\u5408",
        "10. \u73FE\u6642\u70B9\u3067\u306E\u5236\u7D04\u4E8B\u9805",
        "11. \u3088\u304F\u3042\u308B\u3054\u8CEA\u554F",
    ]
    for item in toc_items:
        story.append(p(item, "body"))
    story.append(PageBreak())

    # ======== 1. OVERVIEW ========
    story.append(p("1. \u30B7\u30B9\u30C6\u30E0\u306E\u6982\u8981", "h1"))
    story.append(hr())
    story.append(p("\u672C\u30B7\u30B9\u30C6\u30E0\u306F\u3001\u793E\u5185NAS\u306B\u4FDD\u5B58\u3055\u308C\u3066\u3044\u308BExcel\u30D5\u30A1\u30A4\u30EB\u306E\u5185\u5BB9\u3092\u3001\u4E00\u5B9A\u9593\u9694\u3067\u81EA\u52D5\u7684\u306BGoogle\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u3078\u53CD\u6620\u3057\u307E\u3059\u3002"))
    story.append(p("\u3053\u308C\u306B\u3088\u308A\u3001<b>\u4E8B\u52D9\u54E1\u306E\u65B9\u306F\u4ECA\u307E\u3067\u901A\u308AExcel\u3067\u4F5C\u696D</b>\u3057\u306A\u304C\u3089\u3001<b>\u55B6\u696D\u30FB\u5F79\u54E1\u30FB\u793E\u9577\u306E\u65B9\u306F\u30B9\u30DE\u30FC\u30C8\u30D5\u30A9\u30F3\u3084PC\u304B\u3089\u5916\u51FA\u5148\u3067\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u3092\u95B2\u89A7</b>\u3067\u304D\u308B\u3088\u3046\u306B\u306A\u308A\u307E\u3059\u3002"))
    story.append(sp(4))
    add_img(img_overview)
    story.append(sp(4))
    add_img(img_access)

    # ======== 2. FEATURES ========
    story.append(sp(4))
    story.append(p("2. \u3067\u304D\u308B\u3053\u3068", "h1"))
    story.append(hr())
    features = [
        ["\u6A5F\u80FD", "\u8AAC\u660E"],
        ["\u81EA\u52D5\u540C\u671F", "Excel\u30D5\u30A1\u30A4\u30EB\u306E\u66F4\u65B0\u3092\u691C\u77E5\u3057\u3001\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u3078\u81EA\u52D5\u53CD\u6620\u3057\u307E\u3059"],
        ["\u8907\u6570\u30D5\u30A1\u30A4\u30EB\u5BFE\u5FDC", "NAS\u5185\u306EExcel\u30D5\u30A1\u30A4\u30EB\uFF0810\uFF5E20\u500B\u7A0B\u5EA6\uFF09\u3092\u307E\u3068\u3081\u3066\u7BA1\u7406\u3057\u307E\u3059"],
        ["\u8907\u6570\u30B7\u30FC\u30C8\u5BFE\u5FDC", "1\u3064\u306EExcel\u5185\u306B\u30B7\u30FC\u30C8\u304C\u8907\u6570\u3042\u3063\u3066\u3082\u3001\u3059\u3079\u3066\u53CD\u6620\u3055\u308C\u307E\u3059"],
        ["\u30B5\u30D6\u30D5\u30A9\u30EB\u30C0\u5BFE\u5FDC", "NAS\u30D5\u30A9\u30EB\u30C0\u5185\u306B\u30B5\u30D6\u30D5\u30A9\u30EB\u30C0\u304C\u3042\u308B\u5834\u5408\u3082\u3001\u4E2D\u306EExcel\u3092\u691C\u51FA\u3057\u307E\u3059"],
        ["\u65B0\u898F\u30D5\u30A1\u30A4\u30EB\u81EA\u52D5\u691C\u77E5", "NAS\u306B\u65B0\u3057\u3044Excel\u3092\u8FFD\u52A0\u3059\u308B\u3068\u3001\u81EA\u52D5\u3067\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u304C\u4F5C\u6210\u3055\u308C\u307E\u3059"],
        ["URL\u56FA\u5B9A", "\u4E00\u5EA6\u4F5C\u6210\u3055\u308C\u305F\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u306EURL\u306F\u5909\u308F\u308A\u307E\u305B\u3093\u3002\u30D6\u30C3\u30AF\u30DE\u30FC\u30AF\u53EF\u80FD\u3067\u3059"],
        ["\u95B2\u89A7\u8005\u306E\u81EA\u52D5\u8A2D\u5B9A", "\u6307\u5B9A\u3057\u305F\u30E1\u30FC\u30EB\u30A2\u30C9\u30EC\u30B9\u306B\u5BFE\u3057\u3001\u95B2\u89A7\u6A29\u9650\u304C\u81EA\u52D5\u3067\u4ED8\u4E0E\u3055\u308C\u307E\u3059"],
        ["\u5E38\u6642\u81EA\u52D5\u904B\u7528", "\u793E\u5185PC\u3067\u81EA\u52D5\u8D77\u52D5\u3057\u3001PC\u518D\u8D77\u52D5\u5F8C\u3082\u81EA\u52D5\u3067\u5FA9\u5E30\u3057\u307E\u3059"],
    ]
    story.append(styled_table(features, col_widths=[40 * mm, CONTENT_W - 42 * mm]))

    # ======== 3. SYNC MECHANISM ========
    story.append(sp(4))
    story.append(p("3. \u540C\u671F\u306E\u4ED5\u7D44\u307F", "h1"))
    story.append(hr())

    story.append(p("3-1. \u540C\u671F\u306E\u65B9\u5411", "h2"))
    story.append(p("<b>NAS\u306EExcel \u2192 \u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8 \u306E\u4E00\u65B9\u5411\u306E\u307F</b>\u3067\u3059\u3002"))
    story.append(p("\u30FB\u4E8B\u52D9\u54E1\u304CExcel\u3092\u66F4\u65B0 \u2192 \u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u306B\u53CD\u6620\u3055\u308C\u308B", "bullet"))
    story.append(p("\u30FB\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u4E0A\u3067\u7DE8\u96C6\u3057\u3066\u3082 \u2192 Excel\u306B\u306F\u53CD\u6620\u3055\u308C\u307E\u305B\u3093", "bullet"))
    story.append(p("\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u306F<b>\u95B2\u89A7\u5C02\u7528</b>\u3068\u3057\u3066\u3054\u5229\u7528\u304F\u3060\u3055\u3044\u3002"))

    story.append(sp(2))
    story.append(p("3-2. \u540C\u671F\u306E\u30BF\u30A4\u30DF\u30F3\u30B0", "h2"))
    story.append(p("<b>15\u5206\u306B1\u56DE</b>\u3001\u81EA\u52D5\u3067\u540C\u671F\u51E6\u7406\u304C\u5B9F\u884C\u3055\u308C\u307E\u3059\u3002\u4E8B\u52D9\u54E1\u304CExcel\u3092\u4FDD\u5B58\u3057\u3066\u304B\u3089\u3001<b>\u6700\u592715\u5206\u5F8C</b>\u306B\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u3078\u53CD\u6620\u3055\u308C\u307E\u3059\u3002\u5909\u66F4\u304C\u306A\u3044\u30D5\u30A1\u30A4\u30EB\u306F\u51E6\u7406\u3092\u30B9\u30AD\u30C3\u30D7\u3059\u308B\u305F\u3081\u3001\u7121\u99C4\u306A\u901A\u4FE1\u306F\u767A\u751F\u3057\u307E\u305B\u3093\u3002\u540C\u671F\u9593\u9694\u306F\u8A2D\u5B9A\u3067\u5909\u66F4\u53EF\u80FD\u3067\u3059\uFF085\u5206\u300130\u5206 \u306A\u3069\uFF09\u3002"))
    story.append(sp(3))
    add_img(img_cycle)

    story.append(sp(2))
    story.append(p("3-3. \u5909\u66F4\u306E\u691C\u77E5\u65B9\u6CD5", "h2"))
    story.append(p("Excel\u30D5\u30A1\u30A4\u30EB\u306E<b>\u66F4\u65B0\u65E5\u6642</b>\u3068<b>\u30D5\u30A1\u30A4\u30EB\u5185\u5BB9</b>\u306E\u4E21\u65B9\u3092\u78BA\u8A8D\u3057\u3066\u5909\u66F4\u3092\u691C\u77E5\u3057\u307E\u3059\u3002\u5185\u5BB9\u306B\u5909\u5316\u304C\u306A\u3051\u308C\u3070\u3001\u4FDD\u5B58\u3057\u305F\u3060\u3051\u3067\u306F\u540C\u671F\u306F\u5B9F\u884C\u3055\u308C\u307E\u305B\u3093\u3002"))

    # ======== 4. UPDATE BEHAVIOR ========
    story.append(PageBreak())
    story.append(p("4. \u95B2\u89A7\u4E2D\u306B\u66F4\u65B0\u304C\u5165\u3063\u305F\u5834\u5408\u306E\u52D5\u4F5C", "h1"))
    story.append(hr())
    story.append(p("<b>\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u304C\u4E00\u77AC\u7A7A\u767D\u306B\u306A\u308B\u3053\u3068\u306F\u3042\u308A\u307E\u305B\u3093\u3002</b>"))
    story.append(p("\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u3092\u95B2\u89A7\u4E2D\u306B\u3061\u3087\u3046\u3069\u66F4\u65B0\u30BF\u30A4\u30DF\u30F3\u30B0\u304C\u6765\u305F\u5834\u5408\u3001\u65E2\u5B58\u306E\u30C7\u30FC\u30BF\u3092\u6D88\u3057\u3066\u304B\u3089\u65B0\u3057\u3044\u30C7\u30FC\u30BF\u3092\u66F8\u304D\u8FBC\u3080\u306E\u3067\u306F\u306A\u304F\u3001<b>\u4E0A\u304B\u3089\u76F4\u63A5\u65B0\u3057\u3044\u30C7\u30FC\u30BF\u3067\u4E0A\u66F8\u304D</b>\u3057\u307E\u3059\u3002\u305D\u306E\u305F\u3081\u3001\u95B2\u89A7\u4E2D\u306B\u753B\u9762\u304C\u771F\u3063\u767D\u306B\u306A\u308B\u3053\u3068\u306F\u3042\u308A\u307E\u305B\u3093\u3002"))
    story.append(sp(3))

    upd_table = [
        ["\u30BF\u30A4\u30DF\u30F3\u30B0", "\u753B\u9762\u306B\u8868\u793A\u3055\u308C\u308B\u5185\u5BB9"],
        ["\u66F4\u65B0\u51E6\u7406\u306E\u524D", "\u524D\u56DE\u540C\u671F\u6642\u306E\u30C7\u30FC\u30BF\uFF08\u53E4\u3044\u30C7\u30FC\u30BF\uFF09"],
        ["\u66F4\u65B0\u51E6\u7406\u306E\u5B9F\u884C\u4E2D", "\u53E4\u3044\u30C7\u30FC\u30BF\u304C\u65B0\u3057\u3044\u30C7\u30FC\u30BF\u306B\u5207\u308A\u66FF\u308F\u308B"],
        ["\u66F4\u65B0\u51E6\u7406\u306E\u5F8C", "\u6700\u65B0\u30C7\u30FC\u30BF"],
    ]
    story.append(styled_table(upd_table, col_widths=[40 * mm, CONTENT_W - 42 * mm]))
    story.append(sp(4))
    add_img_tall(img_update)
    story.append(sp(2))
    story.append(p("\u203B \u66F4\u65B0\u306E\u5207\u308A\u66FF\u308F\u308B\u77AC\u9593\u306F\u4E00\u90E8\u306E\u30BB\u30EB\u3060\u3051\u304C\u65B0\u3057\u3044\u5024\u306B\u5909\u308F\u308B\u306A\u3069\u3001\u4E00\u6642\u7684\u306B\u65B0\u65E7\u30C7\u30FC\u30BF\u304C\u6DF7\u5728\u3057\u3066\u898B\u3048\u308B\u5834\u5408\u304C\u3042\u308A\u307E\u3059\u3002\u6570\u79D2\u3067\u5B8C\u4E86\u3057\u307E\u3059\u306E\u3067\u3001\u30DA\u30FC\u30B8\u3092\u518D\u8AAD\u307F\u8FBC\u307F\u3059\u308C\u3070\u6700\u65B0\u30C7\u30FC\u30BF\u304C\u8868\u793A\u3055\u308C\u307E\u3059\u3002", "note"))

    # ======== 5. FILE OPS ========
    story.append(sp(4))
    story.append(p("5. \u30D5\u30A1\u30A4\u30EB\u306E\u8FFD\u52A0\u30FB\u524A\u9664\u30FB\u540D\u524D\u5909\u66F4", "h1"))
    story.append(hr())

    story.append(p("<b>\u65B0\u3057\u3044Excel\u30D5\u30A1\u30A4\u30EB\u3092NAS\u306B\u8FFD\u52A0\u3057\u305F\u5834\u5408</b>", "h2"))
    story.append(p("\u6B21\u306E\u540C\u671F\u30BF\u30A4\u30DF\u30F3\u30B0\u3067\u81EA\u52D5\u691C\u77E5\u3057\u3001\u65B0\u3057\u3044\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u304C\u81EA\u52D5\u4F5C\u6210\u3055\u308C\u307E\u3059\u3002\u8A2D\u5B9A\u6E08\u307F\u306E\u95B2\u89A7\u8005\u3078\u306E\u5171\u6709\u3082\u81EA\u52D5\u3067\u884C\u308F\u308C\u307E\u3059\u3002\u65B0\u3057\u3044\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u306EURL\u306F\u3001Google Drive\u306E\u540C\u671F\u7528\u30D5\u30A9\u30EB\u30C0\u5185\u306B\u4F5C\u6210\u3055\u308C\u307E\u3059\u306E\u3067\u3001\u55B6\u696D\u30FB\u5F79\u54E1\u3078URL\u3092\u5171\u6709\u3057\u3066\u304F\u3060\u3055\u3044\u3002"))

    story.append(p("<b>NAS\u304B\u3089Excel\u30D5\u30A1\u30A4\u30EB\u3092\u524A\u9664\u3057\u305F\u5834\u5408</b>", "h2"))
    story.append(p("\u5BFE\u5FDC\u3059\u308B\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u306F<b>\u524A\u9664\u3055\u308C\u307E\u305B\u3093</b>\u3002\u6700\u5F8C\u306B\u540C\u671F\u3055\u308C\u305F\u30C7\u30FC\u30BF\u304C\u305D\u306E\u307E\u307E\u6B8B\u308A\u307E\u3059\u3002\u3053\u308C\u306F\u30C7\u30FC\u30BF\u4FDD\u5168\u306E\u305F\u3081\u306E\u4ED5\u69D8\u3067\u3059\u3002\u4E0D\u8981\u306B\u306A\u3063\u305F\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u306F\u3001Google Drive\u4E0A\u3067\u624B\u52D5\u3067\u524A\u9664\u3057\u3066\u304F\u3060\u3055\u3044\u3002"))

    story.append(p("<b>Excel\u30D5\u30A1\u30A4\u30EB\u306E\u540D\u524D\u3092\u5909\u66F4\u3057\u305F\u5834\u5408</b>", "h2"))
    story.append(p("\u65E7\u30D5\u30A1\u30A4\u30EB\u540D\u306E\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u306F\u305D\u306E\u307E\u307E\u6B8B\u308A\u3001\u65B0\u30D5\u30A1\u30A4\u30EB\u540D\u3067\u65B0\u3057\u3044\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u304C\u4F5C\u6210\u3055\u308C\u307E\u3059\u3002<b>URL\u304C\u5909\u308F\u308B\u305F\u3081\u3001\u55B6\u696D\u30FB\u5F79\u54E1\u306B\u306F\u65B0\u3057\u3044URL\u3092\u304A\u77E5\u3089\u305B\u3059\u308B\u5FC5\u8981\u304C\u3042\u308A\u307E\u3059\u3002</b>\u983B\u7E41\u306A\u30D5\u30A1\u30A4\u30EB\u540D\u306E\u5909\u66F4\u306F\u907F\u3051\u308B\u3053\u3068\u3092\u304A\u52E7\u3081\u3057\u307E\u3059\u3002"))

    story.append(sp(3))
    add_img_tall(img_fileops)

    story.append(sp(4))
    story.append(p("<b>Excel\u306E\u30B7\u30FC\u30C8\u69CB\u6210\u3092\u5909\u66F4\u3057\u305F\u5834\u5408</b>", "h2"))
    sheet_ops = [
        ["\u64CD\u4F5C", "\u52D5\u4F5C"],
        ["\u30B7\u30FC\u30C8\u306E\u8FFD\u52A0", "\u6B21\u56DE\u540C\u671F\u6642\u306B\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u5074\u306B\u3082\u30B7\u30FC\u30C8\u304C\u8FFD\u52A0\u3055\u308C\u307E\u3059"],
        ["\u30B7\u30FC\u30C8\u306E\u524A\u9664", "\u6B21\u56DE\u540C\u671F\u6642\u306B\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u5074\u306E\u30B7\u30FC\u30C8\u3082\u524A\u9664\u3055\u308C\u307E\u3059"],
        ["\u30B7\u30FC\u30C8\u540D\u306E\u5909\u66F4", "\u65E7\u30B7\u30FC\u30C8\u304C\u524A\u9664\u3055\u308C\u3001\u65B0\u3057\u3044\u540D\u524D\u306E\u30B7\u30FC\u30C8\u304C\u4F5C\u6210\u3055\u308C\u307E\u3059"],
    ]
    story.append(styled_table(sheet_ops, col_widths=[40 * mm, CONTENT_W - 42 * mm]))

    # ======== 6. OFFICE WORKER IMPACT ========
    story.append(sp(4))
    story.append(p("6. \u4E8B\u52D9\u54E1\u306E\u65B9\u3078\u306E\u5F71\u97FF", "h1"))
    story.append(hr())
    story.append(p("<b>\u3042\u308A\u307E\u305B\u3093\u3002</b>\u4ECA\u307E\u3067\u901A\u308A\u306E\u4F5C\u696D\u3067\u554F\u984C\u3042\u308A\u307E\u305B\u3093\u3002"))
    story.append(p("\u30FBNAS\u4E0A\u306EExcel\u3092\u3044\u3064\u3082\u901A\u308A\u958B\u3044\u3066\u3001\u7DE8\u96C6\u3057\u3066\u3001\u4FDD\u5B58\u3057\u3066\u304F\u3060\u3055\u3044", "bullet"))
    story.append(p("\u30FB\u7279\u5225\u306A\u64CD\u4F5C\u3084\u624B\u9806\u306E\u5909\u66F4\u306F\u4E00\u5207\u4E0D\u8981\u3067\u3059", "bullet"))
    story.append(p("\u30FBExcel\u306E\u52D5\u4F5C\u304C\u9045\u304F\u306A\u308B\u3053\u3068\u3082\u3042\u308A\u307E\u305B\u3093", "bullet"))
    story.append(p("\u30FB\u4E8B\u52D9\u54E1\u304CExcel\u3092\u7DE8\u96C6\u4E2D\uFF08\u958B\u3044\u3066\u3044\u308B\u72B6\u614B\uFF09\u3067\u3082\u3001\u30B7\u30B9\u30C6\u30E0\u306F\u6B63\u5E38\u306B\u52D5\u4F5C\u3057\u307E\u3059", "bullet"))
    story.append(p("\u30FBExcel\u304C\u4FDD\u5B58\u3055\u308C\u308B\u305F\u3073\u306B\u3001\u6B21\u306E\u540C\u671F\u30BF\u30A4\u30DF\u30F3\u30B0\u3067\u53CD\u6620\u3055\u308C\u307E\u3059", "bullet"))

    # ======== 7. DATA CONVERSION ========
    story.append(sp(4))
    story.append(p("7. \u65E5\u4ED8\u30FB\u6570\u5024\u306E\u8868\u793A\u306B\u3064\u3044\u3066", "h1"))
    story.append(hr())
    story.append(p("Excel\u306E\u30C7\u30FC\u30BF\u306F\u3001<b>\u5165\u529B\u3055\u308C\u305F\u5024\u304C\u305D\u306E\u307E\u307E</b>\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u306B\u8EE2\u8A18\u3055\u308C\u307E\u3059\u3002"))
    story.append(sp(2))

    conv_table = [
        ["Excel\u3067\u306E\u5165\u529B", "\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u3067\u306E\u8868\u793A"],
        ["\u6570\u5024\uFF08123, 45.6\uFF09", "\u305D\u306E\u307E\u307E\u8868\u793A"],
        ["\u6587\u5B57\u5217\uFF08\u5728\u5EAB\u3042\u308A\uFF09", "\u305D\u306E\u307E\u307E\u8868\u793A"],
        ["\u65E5\u4ED8\uFF082026/3/17\uFF09", "2026-03-17 \u5F62\u5F0F\u3067\u8868\u793A"],
        ["\u65E5\u6642\uFF082026/3/17 10:30\uFF09", "2026-03-17 10:30:00 \u5F62\u5F0F\u3067\u8868\u793A"],
        ["\u6570\u5F0F\uFF08=SUM(A1:A10)\uFF09", "\u8A08\u7B97\u7D50\u679C\u306E\u5024\u304C\u8EE2\u8A18\u3055\u308C\u307E\u3059"],
        ["\u7A7A\u30BB\u30EB", "\u7A7A\u767D\u306E\u307E\u307E"],
    ]
    story.append(styled_table(conv_table, col_widths=[CONTENT_W * 0.4, CONTENT_W * 0.58]))
    story.append(sp(3))

    story.append(p("<b>\u6CE8\u610F\u70B9:</b>", "h2"))
    story.append(p("\u30FBExcel\u306E\u6570\u5F0F\u306F\u300C\u8A08\u7B97\u7D50\u679C\u306E\u5024\u300D\u306E\u307F\u304C\u53CD\u6620\u3055\u308C\u307E\u3059\u3002\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u5074\u306B\u6570\u5F0F\u306F\u5165\u308A\u307E\u305B\u3093", "bullet"))
    story.append(p("\u30FB\u30BB\u30EB\u306E\u66F8\u5F0F\uFF08\u8272\u3001\u592A\u5B57\u3001\u7F6B\u7DDA\u306A\u3069\uFF09\u306F\u53CD\u6620\u3055\u308C\u307E\u305B\u3093\u3002\u30C7\u30FC\u30BF\u306E\u5024\u306E\u307F\u304C\u5BFE\u8C61\u3067\u3059", "bullet"))
    story.append(p("\u30FB\u30B0\u30E9\u30D5\u30FB\u753B\u50CF\u306F\u53CD\u6620\u3055\u308C\u307E\u305B\u3093", "bullet"))
    story.append(p("\u30FB\u65E5\u4ED8\u306E\u8868\u793A\u5F62\u5F0F\u306FExcel\u3068\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u3067\u7570\u306A\u308B\u5834\u5408\u304C\u3042\u308A\u307E\u3059\uFF08\u30C7\u30FC\u30BF\u306E\u5024\u81EA\u4F53\u306F\u6B63\u78BA\u3067\u3059\uFF09", "bullet"))

    # ======== 8. VIEWING ========
    story.append(PageBreak())
    story.append(p("8. \u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u306E\u95B2\u89A7\u306B\u3064\u3044\u3066", "h1"))
    story.append(hr())

    story.append(p("<b>\u30A2\u30AF\u30BB\u30B9\u65B9\u6CD5</b>", "h2"))
    story.append(p("Google Drive\u5185\u306E\u6307\u5B9A\u30D5\u30A9\u30EB\u30C0\u306B\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u304C\u683C\u7D0D\u3055\u308C\u307E\u3059\u3002\u5404\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u306E\u540D\u524D\u306F\u300C[\u540C\u671F] Excel\u30D5\u30A1\u30A4\u30EB\u540D\u300D\u3068\u3044\u3046\u5F62\u5F0F\u3067\u3059\u3002"))
    story.append(p("\u4F8B: [\u540C\u671F] \u5728\u5EAB\u8868\u3001[\u540C\u671F] \u58F2\u4E0A\u7BA1\u7406\u3001[\u540C\u671F] \u9867\u5BA2\u30EA\u30B9\u30C8", "note"))

    story.append(sp(2))
    story.append(p("<b>\u30D6\u30C3\u30AF\u30DE\u30FC\u30AF</b>", "h2"))
    story.append(p("\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u306EURL\u306F\u56FA\u5B9A\u3067\u3059\u3002\u4E00\u5EA6\u30D6\u30E9\u30A6\u30B6\u3067\u30D6\u30C3\u30AF\u30DE\u30FC\u30AF\u3057\u3066\u304A\u3051\u3070\u3001\u6B21\u56DE\u4EE5\u964D\u306F\u540C\u3058URL\u3067\u6700\u65B0\u30C7\u30FC\u30BF\u3092\u78BA\u8A8D\u3067\u304D\u307E\u3059\u3002"))

    story.append(sp(2))
    story.append(p("<b>\u30B9\u30DE\u30FC\u30C8\u30D5\u30A9\u30F3\u304B\u3089\u306E\u95B2\u89A7</b>", "h2"))
    story.append(p("Google\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u30A2\u30D7\u30EA\uFF08iOS / Android\uFF09\u304B\u3089\u95B2\u89A7\u3067\u304D\u307E\u3059\u3002Google\u30A2\u30AB\u30A6\u30F3\u30C8\u3067\u30ED\u30B0\u30A4\u30F3\u3057\u3001\u5171\u6709\u3055\u308C\u305F\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u3092\u958B\u3044\u3066\u304F\u3060\u3055\u3044\u3002"))

    story.append(sp(2))
    story.append(p("<b>\u95B2\u89A7\u6A29\u9650</b>", "h2"))
    story.append(p("\u30FB\u55B6\u696D\u30FB\u5F79\u54E1\u306E\u65B9\u306B\u306F\u300C\u95B2\u89A7\u306E\u307F\u300D\u306E\u6A29\u9650\u304C\u4ED8\u4E0E\u3055\u308C\u307E\u3059", "bullet"))
    story.append(p("\u30FB\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u4E0A\u3067\u306E\u7DE8\u96C6\u306F\u3067\u304D\u307E\u305B\u3093\uFF08\u8AA4\u64CD\u4F5C\u9632\u6B62\u306E\u305F\u3081\uFF09", "bullet"))
    story.append(p("\u30FB\u95B2\u89A7\u8005\u306E\u8FFD\u52A0\u30FB\u524A\u9664\u306F\u7BA1\u7406\u8005\u304C\u8A2D\u5B9A\u5909\u66F4\u3067\u5BFE\u5FDC\u3057\u307E\u3059", "bullet"))

    # ======== 9. ERROR HANDLING ========
    story.append(sp(4))
    story.append(p("9. \u30B7\u30B9\u30C6\u30E0\u304C\u6B63\u5E38\u306B\u52D5\u4F5C\u3057\u306A\u3044\u5834\u5408", "h1"))
    story.append(hr())
    story.append(p("\u4EE5\u4E0B\u306E\u3088\u3046\u306A\u72B6\u6CC1\u3067\u306F\u3001\u540C\u671F\u304C\u4E00\u6642\u7684\u306B\u505C\u6B62\u307E\u305F\u306F\u9045\u5EF6\u3059\u308B\u5834\u5408\u304C\u3042\u308A\u307E\u3059\u3002"))
    story.append(sp(2))

    err_table = [
        ["\u72B6\u6CC1", "\u5F71\u97FF", "\u81EA\u52D5\u5FA9\u65E7"],
        ["NAS\u306E\u96FB\u6E90\u304C\u5207\u308C\u3066\u3044\u308B", "\u540C\u671F\u304C\u505C\u6B62\uFF08\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u306F\u6700\u5F8C\u306E\u30C7\u30FC\u30BF\u3092\u4FDD\u6301\uFF09", "NAS\u5FA9\u65E7\u5F8C\u3001\u81EA\u52D5\u3067\u518D\u958B"],
        ["\u793E\u5185\u30CD\u30C3\u30C8\u30EF\u30FC\u30AF\u306E\u969C\u5BB3", "\u540C\u671F\u304C\u505C\u6B62", "\u30CD\u30C3\u30C8\u30EF\u30FC\u30AF\u5FA9\u65E7\u5F8C\u3001\u81EA\u52D5\u3067\u518D\u958B"],
        ["\u30A4\u30F3\u30BF\u30FC\u30CD\u30C3\u30C8\u63A5\u7D9A\u306E\u969C\u5BB3", "Google\u3078\u306E\u9001\u4FE1\u304C\u3067\u304D\u306A\u3044", "\u63A5\u7D9A\u5FA9\u65E7\u5F8C\u3001\u81EA\u52D5\u3067\u518D\u958B"],
        ["\u540C\u671F\u7528PC\u306E\u96FB\u6E90\u304C\u5207\u308C\u305F", "\u540C\u671F\u304C\u505C\u6B62", "PC\u518D\u8D77\u52D5\u5F8C\u3001\u81EA\u52D5\u3067\u518D\u958B"],
        ["Excel\u30D5\u30A1\u30A4\u30EB\u304C\u7834\u640D\u3057\u3066\u3044\u308B", "\u8A72\u5F53\u30D5\u30A1\u30A4\u30EB\u306E\u307F\u30B9\u30AD\u30C3\u30D7\u3001\u4ED6\u306F\u6B63\u5E38\u306B\u540C\u671F", "\u30D5\u30A1\u30A4\u30EB\u4FEE\u5FA9\u5F8C\u3001\u81EA\u52D5\u3067\u518D\u958B"],
    ]
    story.append(styled_table(err_table, col_widths=[CONTENT_W * 0.30, CONTENT_W * 0.40, CONTENT_W * 0.28]))
    story.append(sp(4))
    add_img(img_error)
    story.append(sp(2))
    story.append(p("\u3044\u305A\u308C\u306E\u5834\u5408\u3082\u3001<b>\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u4E0A\u306E\u30C7\u30FC\u30BF\u304C\u6D88\u3048\u308B\u3053\u3068\u306F\u3042\u308A\u307E\u305B\u3093\u3002</b>\u6700\u5F8C\u306B\u540C\u671F\u3055\u308C\u305F\u6642\u70B9\u306E\u30C7\u30FC\u30BF\u304C\u4FDD\u6301\u3055\u308C\u307E\u3059\u3002"))

    # ======== 10. LIMITATIONS ========
    story.append(sp(4))
    story.append(p("10. \u73FE\u6642\u70B9\u3067\u306E\u5236\u7D04\u4E8B\u9805", "h1"))
    story.append(hr())

    lim_table = [
        ["\u9805\u76EE", "\u5185\u5BB9"],
        ["\u540C\u671F\u306E\u65B9\u5411", "NAS \u2192 \u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u306E\u4E00\u65B9\u5411\u306E\u307F\u3002\u9006\u65B9\u5411\u306F\u3067\u304D\u307E\u305B\u3093"],
        ["\u30EA\u30A2\u30EB\u30BF\u30A4\u30E0\u6027", "\u6700\u592715\u5206\u306E\u9045\u5EF6\u304C\u3042\u308A\u307E\u3059\uFF08\u5373\u6642\u53CD\u6620\u3067\u306F\u3042\u308A\u307E\u305B\u3093\uFF09"],
        ["\u66F8\u5F0F\u30FB\u88C5\u98FE", "\u30BB\u30EB\u306E\u8272\u3001\u30D5\u30A9\u30F3\u30C8\u3001\u592A\u5B57\u3001\u7F6B\u7DDA\u306A\u3069\u306F\u53CD\u6620\u3055\u308C\u307E\u305B\u3093"],
        ["\u30B0\u30E9\u30D5\u30FB\u753B\u50CF", "Excel\u5185\u306E\u30B0\u30E9\u30D5\u3084\u753B\u50CF\u306F\u53CD\u6620\u3055\u308C\u307E\u305B\u3093"],
        ["\u30DE\u30AF\u30ED\uFF08VBA\uFF09", "\u30DE\u30AF\u30ED\u306E\u5185\u5BB9\u306F\u53CD\u6620\u3055\u308C\u307E\u305B\u3093\uFF08\u5B9F\u884C\u7D50\u679C\u306F\u5024\u3068\u3057\u3066\u53CD\u6620\uFF09"],
        [".xls\u5F62\u5F0F", "\u65E7\u5F62\u5F0F\uFF08.xls\uFF09\u306E\u30D5\u30A1\u30A4\u30EB\u306B\u306F\u5BFE\u5FDC\u3057\u3066\u3044\u307E\u305B\u3093\u3002.xlsx\u306E\u307F\u5BFE\u8C61\u3067\u3059"],
        ["\u540C\u6642\u7DE8\u96C6", "\u8907\u6570\u540D\u304C\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u3067\u540C\u6642\u7DE8\u96C6\u3059\u308B\u7528\u9014\u306B\u306F\u975E\u5BFE\u5FDC\uFF08\u95B2\u89A7\u5C02\u7528\uFF09"],
        ["\u901A\u77E5\u6A5F\u80FD", "\u540C\u671F\u306E\u6210\u529F\u30FB\u5931\u6557\u3092\u81EA\u52D5\u901A\u77E5\u3059\u308B\u6A5F\u80FD\u306F\u73FE\u6642\u70B9\u3067\u306F\u672A\u642D\u8F09\u3067\u3059"],
    ]
    story.append(styled_table(lim_table, col_widths=[CONTENT_W * 0.25, CONTENT_W * 0.73]))

    # ======== 11. FAQ ========
    story.append(PageBreak())
    story.append(p("11. \u3088\u304F\u3042\u308B\u3054\u8CEA\u554F", "h1"))
    story.append(hr())

    faqs = [
        ("Q. \u4E8B\u52D9\u54E1\u304CExcel\u3092\u958B\u3044\u305F\u307E\u307E\uFF08\u7DE8\u96C6\u4E2D\uFF09\u3067\u3082\u540C\u671F\u3055\u308C\u307E\u3059\u304B\uFF1F",
         "A. \u306F\u3044\u3002Excel\u304C\u4FDD\u5B58\u3055\u308C\u305F\u6642\u70B9\u306E\u5185\u5BB9\u304C\u3001\u6B21\u306E\u540C\u671F\u30BF\u30A4\u30DF\u30F3\u30B0\u3067\u53CD\u6620\u3055\u308C\u307E\u3059\u3002\u305F\u3060\u3057\u3001\u4FDD\u5B58\u305B\u305A\u306B\u958B\u3044\u305F\u307E\u307E\u306E\u7DE8\u96C6\u4E2D\u306E\u5185\u5BB9\u306F\u53CD\u6620\u3055\u308C\u307E\u305B\u3093\u3002"),
        ("Q. \u540C\u671F\u9593\u9694\u3092\u5909\u66F4\u3067\u304D\u307E\u3059\u304B\uFF1F",
         "A. \u306F\u3044\u3002\u8A2D\u5B9A\u30D5\u30A1\u30A4\u30EB\u3067\u5909\u66F4\u53EF\u80FD\u3067\u3059\uFF08\u4F8B: 5\u5206\u300110\u5206\u300130\u5206\u306A\u3069\uFF09\u3002\u5909\u66F4\u5F8C\u306F\u30B5\u30FC\u30D3\u30B9\u306E\u518D\u8D77\u52D5\u304C\u5FC5\u8981\u3067\u3059\u3002"),
        ("Q. \u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u3092\u8AA4\u3063\u3066\u524A\u9664\u3057\u3066\u3057\u307E\u3063\u305F\u5834\u5408\u306F\uFF1F",
         "A. NAS\u4E0A\u306EExcel\u30D5\u30A1\u30A4\u30EB\u304C\u6B8B\u3063\u3066\u3044\u308C\u3070\u3001\u6B21\u306E\u540C\u671F\u30BF\u30A4\u30DF\u30F3\u30B0\u3067\u65B0\u3057\u3044\u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u304C\u81EA\u52D5\u4F5C\u6210\u3055\u308C\u307E\u3059\u3002\u305F\u3060\u3057URL\u304C\u5909\u308F\u308A\u307E\u3059\u306E\u3067\u3001\u30D6\u30C3\u30AF\u30DE\u30FC\u30AF\u306E\u66F4\u65B0\u304C\u5FC5\u8981\u3067\u3059\u3002"),
        ("Q. \u95B2\u89A7\u8005\u3092\u8FFD\u52A0\u30FB\u524A\u9664\u3057\u305F\u3044\u5834\u5408\u306F\uFF1F",
         "A. \u7BA1\u7406\u8005\u306B\u3054\u4F9D\u983C\u304F\u3060\u3055\u3044\u3002\u8A2D\u5B9A\u30D5\u30A1\u30A4\u30EB\u306E\u5909\u66F4\u3067\u5BFE\u5FDC\u3044\u305F\u3057\u307E\u3059\u3002\u307E\u305F\u3001Google Drive\u4E0A\u3067\u624B\u52D5\u3067\u306E\u5171\u6709\u8FFD\u52A0\u3082\u53EF\u80FD\u3067\u3059\u3002"),
        ("Q. Excel\u306E\u6570\u5F0F\u306E\u8A08\u7B97\u7D50\u679C\u304C\u53CD\u6620\u3055\u308C\u3066\u3044\u307E\u305B\u3093",
         "A. Excel\u3092\u958B\u3044\u3066\u4E00\u5EA6\u518D\u8A08\u7B97\uFF08Ctrl + Shift + F9\uFF09\u3057\u3066\u304B\u3089\u4FDD\u5B58\u3057\u3066\u304F\u3060\u3055\u3044\u3002Excel\u304C\u6700\u5F8C\u306B\u8A08\u7B97\u3057\u305F\u7D50\u679C\u306E\u5024\u304C\u540C\u671F\u3055\u308C\u307E\u3059\u3002"),
        ("Q. NAS\u306E\u30D5\u30A9\u30EB\u30C0\u69CB\u6210\u3092\u5909\u66F4\u3057\u3066\u3082\u5927\u4E08\u592B\u3067\u3059\u304B\uFF1F",
         "A. \u540C\u671F\u5BFE\u8C61\u30D5\u30A9\u30EB\u30C0\u306E\u914D\u4E0B\u3067\u3042\u308C\u3070\u3001\u30B5\u30D6\u30D5\u30A9\u30EB\u30C0\u306E\u8FFD\u52A0\u30FB\u79FB\u52D5\u306F\u81EA\u52D5\u5BFE\u5FDC\u3055\u308C\u307E\u3059\u3002\u305F\u3060\u3057\u3001\u540C\u671F\u5BFE\u8C61\u30D5\u30A9\u30EB\u30C0\u81EA\u4F53\u306E\u30D1\u30B9\u3092\u5909\u66F4\u3059\u308B\u5834\u5408\u306F\u3001\u8A2D\u5B9A\u306E\u5909\u66F4\u304C\u5FC5\u8981\u3067\u3059\u3002"),
        ("Q. \u540C\u671F\u304C\u6B62\u307E\u3063\u3066\u3044\u308B\u304B\u3082\u3057\u308C\u307E\u305B\u3093\u3002\u78BA\u8A8D\u65B9\u6CD5\u306F\uFF1F",
         "A. \u30B9\u30D7\u30EC\u30C3\u30C9\u30B7\u30FC\u30C8\u306E\u5185\u5BB9\u304C\u3057\u3070\u3089\u304F\u66F4\u65B0\u3055\u308C\u3066\u3044\u306A\u3044\u5834\u5408\u306F\u3001\u7BA1\u7406\u8005\u306B\u3054\u9023\u7D61\u304F\u3060\u3055\u3044\u3002\u540C\u671F\u7528PC\u306E\u30ED\u30B0\u3092\u78BA\u8A8D\u3057\u3066\u5BFE\u5FDC\u3044\u305F\u3057\u307E\u3059\u3002"),
    ]

    for q, a in faqs:
        story.append(p(q, "qa_q"))
        story.append(p(a, "qa_a"))

    # Footer
    story.append(sp(20))
    story.append(hr())
    story.append(p("\u672C\u66F8\u306F\u30B7\u30B9\u30C6\u30E0\u30D0\u30FC\u30B8\u30E7\u30F3 0.1.0 \u6642\u70B9\u306E\u5185\u5BB9\u3067\u3059\u3002", "note"))

    # Build
    doc.build(story)


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    output = project_root / "docs" / "system-overview.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(str(output))
    print(f"PDF generated: {output}")
