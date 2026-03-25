"""tamatex 見積書PDF生成スクリプト。

reportlabを使用し、日本のビジネス慣習に沿った見積書を生成する。
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
    HRFlowable, KeepTogether,
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
C_TOTAL_BG = colors.HexColor("#fce8e6")
C_AMOUNT_BOX = colors.HexColor("#e8f0fe")

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
    "title": _ps("title", fontSize=20, alignment=TA_CENTER, leading=28,
                  textColor=C_PRIMARY),
    "subtitle": _ps("subtitle", fontSize=9, alignment=TA_CENTER,
                     textColor=C_GRAY, spaceAfter=4),
    "heading": _ps("heading", fontSize=11, leading=18, spaceBefore=10,
                    spaceAfter=4, textColor=C_PRIMARY),
    "body": _ps("body", fontSize=9, leading=15, spaceAfter=3),
    "body_right": _ps("body_right", fontSize=9, leading=15,
                       alignment=TA_RIGHT),
    "body_center": _ps("body_center", fontSize=9, leading=15,
                        alignment=TA_CENTER),
    "small": _ps("small", fontSize=8, leading=13, textColor=C_GRAY),
    "amount_large": _ps("amount_large", fontSize=14, leading=22,
                         alignment=TA_CENTER, textColor=C_PRIMARY),
    "note": _ps("note", fontSize=8, leading=13, textColor=C_GRAY,
                 leftIndent=6, spaceAfter=2),
    "cell": _ps("cell", fontSize=8.5, leading=13),
    "cell_r": _ps("cell_r", fontSize=8.5, leading=13, alignment=TA_RIGHT),
    "cell_c": _ps("cell_c", fontSize=8.5, leading=13, alignment=TA_CENTER),
    "cell_bold": _ps("cell_bold", fontSize=8.5, leading=13,
                      textColor=C_PRIMARY),
    "cell_bold_r": _ps("cell_bold_r", fontSize=8.5, leading=13,
                        alignment=TA_RIGHT, textColor=C_PRIMARY),
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


def fmt_yen(amount: int) -> str:
    """金額を ¥1,000,000 形式にフォーマット。"""
    return f"¥{amount:,}"


def fmt_yen_p(amount: int, style: str = "cell_r") -> Paragraph:
    return Paragraph(fmt_yen(amount), S[style])


# ============================================================
# Estimate data
# ============================================================

TODAY = datetime.date.today()
ESTIMATE_NO = f"EST-{TODAY.strftime('%Y%m%d')}-001"
VALID_UNTIL = TODAY + datetime.timedelta(days=30)

# 明細データ: (No, カテゴリ, 項目, 数量, 単位, 単価, 金額, 備考)
# カテゴリ行は sub_items=True
ITEMS = [
    # --- 1. 要件定義・設計 ---
    {"cat": "1. 要件定義・設計", "items": [
        ("1-1", "要件ヒアリング・整理",
         1, "式", 50_000, "業務フロー分析・同期対象ファイル選定"),
        ("1-2", "システム設計",
         1, "式", 50_000, "アーキテクチャ設計・モジュール分割・DB設計"),
        ("1-3", "仕様書作成",
         1, "式", 50_000, "システム仕様書（10ページ・PDF納品）"),
    ]},
    # --- 2. システム開発 ---
    {"cat": "2. システム開発", "items": [
        ("2-1", "設定管理・ログ管理モジュール",
         1, "式", 30_000, "YAML設定読込・RotatingFileHandler"),
        ("2-2", "SQLite状態管理モジュール",
         1, "式", 50_000, "同期状態永続化・upsert対応"),
        ("2-3", "Excel読取モジュール",
         1, "式", 80_000, "openpyxl・マージセル展開・型変換対応"),
        ("2-4", "NASファイル変更検知モジュール",
         1, "式", 80_000, "mtime + MD5二重検知・パターンマッチ"),
        ("2-5", "Google Sheets API連携モジュール",
         1, "式", 120_000, "gspread 6.x・認証・同期・フォルダ管理"),
        ("2-6", "メインデーモンプロセス",
         1, "式", 90_000, "15分間隔ポーリング・シグナル処理・エラーリカバリ"),
    ]},
    # --- 3. テスト ---
    {"cat": "3. テスト", "items": [
        ("3-1", "ユニットテスト作成・実行",
         107, "件", 750, "pytest・5モジュール全カバー"),
        ("3-2", "結合テスト・動作検証",
         1, "式", 20_000, "実環境シミュレーション・異常系確認"),
    ]},
    # --- 4. インストーラー開発 ---
    {"cat": "4. インストーラー開発", "items": [
        ("4-1", "GUIインストーラーウィザード",
         1, "式", 100_000, "tkinter 7ステップ・非技術者向けUI"),
        ("4-2", "exe化対応",
         1, "式", 20_000, "PyInstaller・単体実行ファイル生成"),
    ]},
    # --- 5. ドキュメント ---
    {"cat": "5. ドキュメント作成", "items": [
        ("5-1", "導入手順書",
         1, "式", 30_000, "GUI手順・手動手順・トラブルシューティング"),
        ("5-2", "運用マニュアル",
         1, "式", 20_000, "日常運用・障害対応手順"),
    ]},
    # --- 6. 導入・セットアップ ---
    {"cat": "6. 導入・セットアップ", "items": [
        ("6-1", "環境構築",
         1, "式", 20_000, "Python導入・依存パッケージインストール"),
        ("6-2", "Google Cloud設定",
         1, "式", 25_000, "プロジェクト作成・サービスアカウント・API有効化"),
        ("6-3", "システム設定・動作確認",
         1, "式", 20_000, "config設定・初回同期テスト・NSSMサービス登録"),
        ("6-4", "操作説明・引き渡し",
         1, "式", 15_000, "担当者への操作説明・共有設定"),
    ]},
    # --- 7. 初期サポート ---
    {"cat": "7. 初期サポート", "items": [
        ("7-1", "導入後サポート",
         1, "ヶ月", 30_000, "電話・メール対応・軽微な設定変更"),
    ]},
]


def calc_items():
    """明細データを計算して (行リスト, カテゴリ小計リスト, 合計) を返す。"""
    rows = []
    category_subtotals = []
    grand_total = 0

    for group in ITEMS:
        cat_name = group["cat"]
        cat_total = 0
        cat_start = len(rows)

        for no, name, qty, unit, unit_price, note in group["items"]:
            amount = qty * unit_price
            cat_total += amount
            rows.append({
                "no": no, "name": name, "qty": qty, "unit": unit,
                "unit_price": unit_price, "amount": amount, "note": note,
                "is_category": False,
            })

        category_subtotals.append({
            "name": cat_name, "total": cat_total,
            "start": cat_start, "end": len(rows),
        })
        grand_total += cat_total

    return rows, category_subtotals, grand_total


# ============================================================
# PDF Builder
# ============================================================

def build_estimate_pdf(output_path: str) -> None:
    rows, cat_subs, subtotal = calc_items()
    tax_rate = 0.10
    tax = int(subtotal * tax_rate)
    total = subtotal + tax

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    story = []

    # ----------------------------------------------------------
    # Title
    # ----------------------------------------------------------
    story.append(p("御 見 積 書", "title"))
    story.append(sp(2))
    story.append(hr())
    story.append(sp(2))

    # ----------------------------------------------------------
    # Header: left=customer, right=issuer
    # ----------------------------------------------------------
    header_left = [
        [p("御見積日:", "small"), p(TODAY.strftime("%Y年%m月%d日"), "body")],
        [p("見積番号:", "small"), p(ESTIMATE_NO, "body")],
        [p("有効期限:", "small"), p(VALID_UNTIL.strftime("%Y年%m月%d日"), "body")],
        [Spacer(1, 4 * mm), ""],
        [p("宛先:", "small"), ""],
        [p("　　　　　　　　　　　　　　　御中", "body"), ""],
    ]

    header_right = [
        [p("発行者:", "small")],
        [p("　　　　　　　　　　　　　", "body")],
        [p("TEL:", "small")],
        [p("Email:", "small")],
        [Spacer(1, 2 * mm)],
        [p("（押印欄）", "body_center")],
    ]

    left_t = Table(header_left, colWidths=[22 * mm, 60 * mm])
    left_t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))

    right_t = Table(header_right, colWidths=[55 * mm])
    right_t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("BOX", (0, 0), (-1, -1), 0.5, C_BORDER),
    ]))

    header_t = Table([[left_t, right_t]],
                      colWidths=[CONTENT_W * 0.55, CONTENT_W * 0.45])
    header_t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_t)
    story.append(sp(4))

    # ----------------------------------------------------------
    # Subject & Total amount
    # ----------------------------------------------------------
    story.append(p("件名: Excel → Google スプレッドシート 自動同期システム開発・導入", "heading"))
    story.append(sp(2))

    total_box_data = [[
        p("御見積金額（税込）", "body_center"),
        p(f"¥{total:,}-", "amount_large"),
    ]]
    total_box = Table(total_box_data, colWidths=[CONTENT_W * 0.35, CONTENT_W * 0.65])
    total_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_AMOUNT_BOX),
        ("BOX", (0, 0), (-1, -1), 1.5, C_PRIMARY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(total_box)
    story.append(sp(6))

    # ----------------------------------------------------------
    # Detail table
    # ----------------------------------------------------------
    story.append(p("■ 明細", "heading"))

    # Column widths
    col_w = [
        12 * mm,   # No
        62 * mm,   # 項目
        12 * mm,   # 数量
        12 * mm,   # 単位
        24 * mm,   # 単価
        26 * mm,   # 金額
        CONTENT_W - (12 + 62 + 12 + 12 + 24 + 26) * mm,  # 備考
    ]

    # Header row
    table_data = [[
        p("No", "cell_c"),
        p("項目", "cell"),
        p("数量", "cell_c"),
        p("単位", "cell_c"),
        p("単価", "cell_r"),
        p("金額", "cell_r"),
        p("備考", "cell"),
    ]]

    # Style commands
    style_cmds = [
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("LEADING", (0, 0), (-1, -1), 13),
        ("TEXTCOLOR", (0, 0), (-1, -1), C_DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ]

    row_idx = 1  # 0 = header

    for cat_sub in cat_subs:
        # Category header row
        cat_row = [
            "",
            p(f"<b>{cat_sub['name']}</b>", "cell_bold"),
            "", "", "", "", "",
        ]
        table_data.append(cat_row)
        style_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), C_CATEGORY_BG))
        style_cmds.append(("SPAN", (1, row_idx), (-1, row_idx)))
        row_idx += 1

        # Item rows
        for row in rows[cat_sub["start"]:cat_sub["end"]]:
            table_data.append([
                p(row["no"], "cell_c"),
                p(row["name"], "cell"),
                p(str(row["qty"]), "cell_c"),
                p(row["unit"], "cell_c"),
                fmt_yen_p(row["unit_price"]),
                fmt_yen_p(row["amount"]),
                p(row["note"], "cell"),
            ])
            row_idx += 1

        # Category subtotal row
        table_data.append([
            "", "",
            p(f"{cat_sub['name']} 小計", "cell_bold"),
            "", "", "",
            fmt_yen_p(cat_sub["total"], "cell_bold_r"),
        ])
        style_cmds.append(("SPAN", (2, row_idx), (5, row_idx)))
        style_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), C_LIGHT_GRAY))
        row_idx += 1

    # Subtotal / Tax / Grand total rows
    summary_rows = [
        ("小計（税抜）", subtotal),
        ("消費税（10%）", tax),
        ("合計（税込）", total),
    ]
    for label, amount in summary_rows:
        table_data.append([
            "", "", "", "", "",
            p(f"<b>{label}</b>", "cell_r"),
            p(f"<b>{fmt_yen(amount)}</b>", "cell_bold_r"),
        ])
        style_cmds.append(("SPAN", (0, row_idx), (4, row_idx)))
        row_idx += 1

    # Grand total highlight
    style_cmds.append(("BACKGROUND", (0, row_idx - 1), (-1, row_idx - 1), C_TOTAL_BG))

    detail_table = Table(table_data, colWidths=col_w, repeatRows=1)
    detail_table.setStyle(TableStyle(style_cmds))
    story.append(detail_table)
    story.append(sp(8))

    # ----------------------------------------------------------
    # Notes
    # ----------------------------------------------------------
    story.append(p("■ 備考・特記事項", "heading"))
    notes = [
        "本見積書の有効期限は発行日より30日間です。",
        "上記金額には消費税（10%）が含まれています。",
        "導入作業は原則として平日日中（9:00〜18:00）に実施します。",
        "出張が必要な場合、交通費・宿泊費は別途実費を申し受けます。",
        "初期サポート期間（1ヶ月）経過後は、別途保守契約をご提案いたします。",
        "保守契約（任意）: 月額 ¥15,000（障害対応・軽微な設定変更・電話メール対応）",
        "お支払い条件: 納品月末締め翌月末払い",
    ]
    for note in notes:
        story.append(p(f"・{note}", "note"))

    story.append(sp(6))

    # ----------------------------------------------------------
    # Deliverables
    # ----------------------------------------------------------
    story.append(p("■ 納品物一覧", "heading"))
    deliverables = [
        ["No", "納品物", "形式"],
        ["1", "tamatex 同期システム一式（ソースコード）", "Python パッケージ"],
        ["2", "GUIインストーラー", "Python / exe"],
        ["3", "ユニットテスト一式（107件）", "pytest"],
        ["4", "システム仕様書", "PDF（10ページ）"],
        ["5", "導入手順書", "Markdown / PDF"],
        ["6", "運用マニュアル", "Markdown"],
        ["7", "設定テンプレート（config.example.yaml）", "YAML"],
    ]
    del_w = [10 * mm, CONTENT_W * 0.55, CONTENT_W - 10 * mm - CONTENT_W * 0.55]
    del_data = []
    for i, row in enumerate(deliverables):
        if i == 0:
            del_data.append([p(c, "cell_c") for c in row])
        else:
            del_data.append([p(row[0], "cell_c"), p(row[1], "cell"), p(row[2], "cell")])

    del_table = Table(del_data, colWidths=del_w)
    del_style = [
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    for i in range(2, len(deliverables), 2):
        del_style.append(("BACKGROUND", (0, i), (-1, i), C_LIGHT_GRAY))
    del_table.setStyle(TableStyle(del_style))
    story.append(del_table)

    # ----------------------------------------------------------
    # Build
    # ----------------------------------------------------------
    doc.build(story)
    print(f"見積書を生成しました: {output_path}")


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent.parent / "docs"
    out_dir.mkdir(exist_ok=True)
    output = str(out_dir / "見積書.pdf")
    build_estimate_pdf(output)
