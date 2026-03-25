"""tamatex コードレビュー報告書PDF生成スクリプト。

4観点（セキュリティ・コード品質・運用耐性・テスト品質）の統合レビュー結果を
A4 PDF形式で出力する。
"""

from __future__ import annotations

import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# ============================================================
# Font / Color / Page
# ============================================================
FONT = "HeiseiKakuGo-W5"
pdfmetrics.registerFont(UnicodeCIDFont(FONT))

C_PRIMARY = colors.HexColor("#1a73e8")
C_DARK = colors.HexColor("#202124")
C_GRAY = colors.HexColor("#5f6368")
C_LIGHT = colors.HexColor("#f1f3f4")
C_BORDER = colors.HexColor("#dadce0")
C_CRITICAL = colors.HexColor("#d93025")
C_CRITICAL_BG = colors.HexColor("#fce8e6")
C_HIGH = colors.HexColor("#ea8600")
C_HIGH_BG = colors.HexColor("#fef7e0")
C_MEDIUM = colors.HexColor("#1a73e8")
C_MEDIUM_BG = colors.HexColor("#e8f0fe")
C_LOW = colors.HexColor("#5f6368")
C_LOW_BG = colors.HexColor("#f1f3f4")
C_GREEN = colors.HexColor("#1e8e3e")
C_GREEN_BG = colors.HexColor("#e6f4ea")

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
CW = PAGE_W - 2 * MARGIN

# ============================================================
# Styles
# ============================================================

def _ps(name, **kw):
    d = {"fontName": FONT, "leading": 16, "textColor": C_DARK}
    d.update(kw)
    return ParagraphStyle(name, **d)


S = {
    "title": _ps("t", fontSize=20, alignment=TA_CENTER, leading=28, textColor=C_PRIMARY),
    "subtitle": _ps("st", fontSize=10, alignment=TA_CENTER, textColor=C_GRAY, spaceAfter=4),
    "h1": _ps("h1", fontSize=14, leading=22, spaceBefore=14, spaceAfter=6, textColor=C_PRIMARY),
    "h2": _ps("h2", fontSize=11, leading=18, spaceBefore=10, spaceAfter=4, textColor=C_DARK),
    "h3": _ps("h3", fontSize=10, leading=16, spaceBefore=6, spaceAfter=3, textColor=C_PRIMARY),
    "body": _ps("b", fontSize=9, leading=15, spaceAfter=3, alignment=TA_JUSTIFY),
    "body_bold": _ps("bb", fontSize=9, leading=15, spaceAfter=3),
    "bullet": _ps("bl", fontSize=9, leading=15, leftIndent=12, bulletIndent=4, spaceAfter=2),
    "small": _ps("sm", fontSize=8, leading=12, textColor=C_GRAY),
    "cell": _ps("c", fontSize=8, leading=12),
    "cell_c": _ps("cc", fontSize=8, leading=12, alignment=TA_CENTER),
    "cell_b": _ps("cb", fontSize=8, leading=12, textColor=C_PRIMARY),
    "footer": _ps("ft", fontSize=7, textColor=C_GRAY, alignment=TA_CENTER),
}


def p(text, style="body"):
    return Paragraph(str(text), S[style])


def sp(h=4):
    return Spacer(1, h * mm)


def hr():
    return HRFlowable(width="100%", thickness=0.5, color=C_BORDER, spaceBefore=2, spaceAfter=4)


def severity_color(sev):
    return {"CRITICAL": C_CRITICAL, "HIGH": C_HIGH, "MEDIUM": C_MEDIUM, "LOW": C_LOW}.get(sev, C_GRAY)


def severity_bg(sev):
    return {"CRITICAL": C_CRITICAL_BG, "HIGH": C_HIGH_BG, "MEDIUM": C_MEDIUM_BG, "LOW": C_LOW_BG}.get(sev, C_LIGHT)


# ============================================================
# Table helpers
# ============================================================

def make_table(data, col_widths=None, header=True):
    style_cmds = [
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 12),
        ("TEXTCOLOR", (0, 0), (-1, -1), C_DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
    ]
    if header:
        style_cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ]
    for i in range(2, len(data), 2):
        style_cmds.append(("BACKGROUND", (0, i), (-1, i), C_LIGHT))
    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    t.setStyle(TableStyle(style_cmds))
    return t


def issue_table(issues):
    """issues: list of (ID, severity, file:line, description, fix)"""
    header = [p("ID", "cell_c"), p("深刻度", "cell_c"), p("場所", "cell"),
              p("問題", "cell"), p("推奨修正", "cell")]
    rows = [header]
    style_cmds = [
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("LEADING", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (0, 0), (-1, -1), C_DARK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.4, C_BORDER),
        ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ]
    widths = [12 * mm, 16 * mm, 30 * mm, CW * 0.30, CW - 12 * mm - 16 * mm - 30 * mm - CW * 0.30]

    for i, (id_, sev, loc, desc, fix) in enumerate(issues, start=1):
        sc = severity_color(sev)
        bg = severity_bg(sev)
        rows.append([
            Paragraph(id_, _ps(f"ci{i}", fontSize=7.5, leading=11, alignment=TA_CENTER)),
            Paragraph(f'<font color="{sc.hexval()}">{sev}</font>',
                      _ps(f"cs{i}", fontSize=7.5, leading=11, alignment=TA_CENTER)),
            Paragraph(loc, _ps(f"cl{i}", fontSize=7, leading=10, textColor=C_GRAY)),
            Paragraph(desc, _ps(f"cd{i}", fontSize=7.5, leading=11)),
            Paragraph(fix, _ps(f"cf{i}", fontSize=7.5, leading=11)),
        ])
        style_cmds.append(("BACKGROUND", (1, i), (1, i), bg))

    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle(style_cmds))
    return t


# ============================================================
# Data
# ============================================================
TODAY = datetime.date.today()

# ------ Security Issues ------
SEC_ISSUES = [
    ("F-01", "CRITICAL", "installer.py:1284\nsheets_sync.py:24",
     "サービスアカウントJSONキーのファイルパーミッション未設定。shutil.copy2はパーミッションをそのままコピーし、他ユーザーに読み取り可能な状態で配置される可能性がある。",
     "コピー後にos.chmod 600またはWindows icaclsで制限。authenticate()で起動時にパーミッション警告を出す。"),
    ("F-02", "HIGH", "config.py:18\nsheets_sync.py:22-24",
     "credentials_pathにパストラバーサルやUNCパスの検証なし。UNCパス経由でNTLMリレー攻撃のベクターになりうる。",
     "load_config()内でcredentials_pathの検証追加。UNCパス(\\\\)の拒否。"),
    ("F-03", "HIGH", "watcher.py:51-57",
     "NAS上のシンボリックリンク追跡でbase_path外のファイルがスキャン・同期される可能性。",
     "resolve()後にbase_pathの配下であることをrelative_to()で検証。"),
    ("F-04", "HIGH", "state.py:21\nmain.py:136",
     "SQLiteパスがハードコード相対パス('./tamatex_state.db')。NSSMサービスではC:\\Windows\\System32にDB作成の恐れ。",
     "configにdb_pathを追加し、絶対パスを明示指定可能にする。"),
    ("F-05", "HIGH", "main.py:105\nsheets_sync.py:40",
     "ログにspreadsheet_id（Google Sheets APIキー相当）がフル出力。ログ漏洩時に不正アクセス可能。",
     "通常ログではID先頭8文字のみ表示。DEBUGレベルのみフル出力。"),
    ("F-06", "MEDIUM", "config.py:51-68",
     "YAML読み込み後の型チェック不足。interval_minutesに負数・0設定で無限高速ループ発生しAPI DoSに。",
     "isinstance型チェックと値域チェック(1-1440)を追加。"),
    ("F-07", "MEDIUM", "main.py:109\ninstaller.py:957",
     "エラーメッセージにスタックトレース・OS情報が漏洩。",
     "ユーザー向けメッセージからは技術詳細を除去。"),
    ("F-08", "MEDIUM", "watcher.py:33",
     "MD5ハッシュの使用。セキュリティ用途ではないが、コンプライアンス要件によっては禁止対象。",
     "SHA-256への変更またはusedforsecurity=False指定。"),
    ("F-09", "MEDIUM", "installer.py:1297-1299",
     "pip install時に--require-hashesなし。DNS改竄で悪意あるパッケージインストールの可能性。",
     "requirements-lock.txtとpip --require-hashesの使用。"),
    ("F-10", "MEDIUM", "main.py:139",
     "認証エラー連続発生時の再認証ロジックなし。トークン無効化後にサイレント失敗が継続。",
     "連続認証エラーカウンターを導入し、閾値超過で再認証を試行。"),
]

# ------ Code Quality Issues ------
CODE_ISSUES = [
    ("H-1", "HIGH", "state.py:9\nwatcher.py:17,25",
     "FileState/FileInfo/ChangeResultがmutable dataclass。frozen=Trueが未設定でイミュータビリティ違反。",
     "frozen=True追加。ChangeResultのlistをtupleに変更。"),
    ("H-2", "HIGH", "excel_reader.py:42-64",
     "_expand_merged_cellsがリストをin-place変更。「NEVER mutate」ルール違反。",
     "新しいリストを生成して返すか、構築完了後にfrozenオブジェクトに包む。"),
    ("H-3", "HIGH", "state.py:37-38",
     "StateDBが毎メソッドで新規コネクション作成。with connはclose()しない。コネクションリーク。",
     "単一コネクション保持+close()メソッド追加。コンテキストマネージャ実装。"),
    ("H-4", "HIGH", "pyproject.toml:7\n__init__.py:3\nmain.py:131",
     "バージョン文字列が3箇所にハードコード。同期漏れリスク。",
     "pyproject.tomlのdynamic=[\"version\"]使用。__version__をsingle source of truthに。"),
    ("H-5", "HIGH", "main.py:139\nsheets_sync.py:22-27",
     "Google API認証トークン期限切れ未対応。起動後1時間で同期停止の恐れ。",
     "gspread.service_account()に切替えで自動リフレッシュ保証。"),
    ("M-1", "MEDIUM", "sheets_sync.py:57-139",
     "sync_workbook関数が83行。50行上限超過。2つの責務（同期+削除）が混在。",
     "_sync_sheetと_cleanup_deleted_sheetsに分割。"),
    ("M-2", "MEDIUM", "main.py:29-117",
     "sync_cycle関数が89行。50行上限超過。4フェーズが1関数内に存在。",
     "同期ループ部分を_sync_fileとして抽出。"),
    ("M-3", "MEDIUM", "sheets_sync.py:50,138",
     "except Exceptionで広範囲キャッチ。意図しない例外の飲み込みリスク。",
     "gspread.exceptions.APIErrorに絞る。"),
    ("M-5", "MEDIUM", "main.py:37",
     "stats辞書が型安全でない。キーのタイポを型チェッカーが検出不可。",
     "TypedDictまたはdataclassでSyncStatsを定義。"),
    ("M-7", "MEDIUM", "tests/",
     "sheets_sync.pyのテストが存在しない。最もバグが発生しやすい外部API連携が未テスト。",
     "gspread.Clientをモックした単体テスト作成。"),
]

# ------ Operational Resilience Issues ------
OPS_ISSUES = [
    ("C-1", "CRITICAL", "sheets_sync.py:22-27",
     "Google API認証トークンが自動更新されない。Credentials.from_service_account_fileのトークンは1時間で失効。",
     "gspread.service_account(filename=...)に切替え。1行の変更で解決。"),
    ("C-2", "CRITICAL", "state.py:37-38",
     "SQLite接続が毎回新規作成されクローズされない。長期運用でファイルディスクリプタ枯渇・メモリリーク。",
     "単一コネクション保持+close()メソッド+main.pyでのクリーンアップ。"),
    ("OH-1", "HIGH", "sheets_sync.py全体",
     "Google APIレート制限(60req/min)の対策不十分。20ファイルx3シート=100+リクエストで429エラー頻発。",
     "指数バックオフ付きリトライを実装。tenacityライブラリの使用も検討。"),
    ("OH-2", "HIGH", "excel_reader.py:77",
     "巨大Excelファイル(100MB+)でread_only=FalseのためOOM発生。デーモン全体がクラッシュ。",
     "ファイルサイズ上限チェック追加(デフォルト50MB)。config設定可能に。"),
    ("OH-4", "HIGH", "state.py:21",
     "SQLiteパスが相対パス。NSSMサービスではCWDがSystem32になりDB消失・重複同期。",
     "config.yamlで絶対パス指定。main.pyでconfig_pathからの相対解決。"),
    ("OH-5", "HIGH", "main.py:125-126",
     "SIGTERMのみ対応。WindowsサービスではCTRL_CLOSE_EVENT等を捕捉できずグレースフル停止不可。",
     "win32api.SetConsoleCtrlHandler追加。atexit.registerでクリーンアップ。"),
    ("OH-6", "HIGH", "sheets_sync.py:57-139",
     "Google APIエラー時のリトライ機構なし。一時障害で同期スキップ、15分間反映されない。",
     "OH-1と統合。リトライ可能なAPIラッパー導入。"),
    ("OH-7", "HIGH", "excel_reader.py:77\nmain.py:108",
     "壊れたExcelファイルで未処理例外。毎サイクル同じエラーが繰返しログが汚染される。",
     "連続失敗カウンタ+閾値超過でスキップするサーキットブレーカー。"),
    ("OH-8", "HIGH", "sheets_sync.py:82-117",
     "Excelの列削除時にスプレッドシート側の余剰列がクリアされずデータ不整合。",
     "update前にworksheet.clear()で全クリアしてから書込み。"),
    ("OM-7", "MEDIUM", "main.py全体",
     "ヘルスチェック・死活監視の仕組みなし。プロセス生存だがメインループ停止を検知不可。",
     "ヘルスチェックファイルの定期更新。外部監視でタイムスタンプ確認。"),
]

# ------ Test Quality Issues ------
TEST_ISSUES = [
    ("T-01", "CRITICAL", "tests/ (未作成)",
     "sheets_sync.pyのテストが完全に欠落。同期ロジック(140行)の全関数が未テスト。",
     "gspread.Clientをモックした最低8シナリオのテスト作成。"),
    ("T-02", "CRITICAL", "tests/ (未作成)",
     "main.pyのテストが完全に欠落。sync_cycle(89行)+run(35行)の中核ロジックが未テスト。",
     "外部依存をモックしたsync_cycleのテスト。NAS切断・連続エラー・シャットダウン中断等。"),
    ("T-03", "HIGH", "watcher.py:65-69",
     "mtime前後比較ロジック（書込中スキップ）がテスト未到達。重要な安全機構が未検証。",
     "os.statモックでmtime変化シナリオをテスト。"),
    ("T-04", "HIGH", "watcher.py:76-78",
     "個別ファイルOSErrorハンドリング未テスト。NAS環境で頻繁に発生するパス。",
     "_compute_file_hashモックでOSError発生テスト。"),
    ("T-05", "HIGH", "excel_reader.py:42-64",
     "マージセル展開(_expand_merged_cells)が未テスト。事務員Excelで高頻度使用のコア機能。",
     "マージセル含むxlsx生成しread_workbook経由で検証。"),
    ("T-06", "MEDIUM", "excel_reader.py",
     "エラーパス未テスト。存在しないファイル・破損ファイル・パスワード保護ファイル。",
     "各異常ケースのpytest.raisesテスト追加。"),
    ("T-07", "MEDIUM", "全テストファイル",
     "大量データのエッジケース未テスト。多シート(20+)・大行数(10万行+)・特殊文字・日本語パス。",
     "境界値テスト・特殊文字テストの追加。"),
    ("T-08", "LOW", "test_state.py\ntest_watcher.py",
     "共通フィクスチャがconftest.pyに集約されていない。StateDBのdbフィクスチャが重複定義。",
     "tests/conftest.pyに共通フィクスチャを抽出。"),
]

# ------ Positive findings ------
POSITIVES = [
    "YAML安全読込: yaml.safe_load()によるデシリアライゼーション攻撃防止",
    "SQLパラメータ化: 全SQLiteクエリでプレースホルダ?を使用、SQLインジェクション防止",
    "shell=False: subprocessでシェルインジェクション防止",
    "frozen dataclass: 設定オブジェクトが型レベルで不変",
    "NAS書込なし: Excelファイルへの書込・ロック・一時ファイル作成は一切なし",
    "一時ファイル除外: ~$*, *.tmp, .~lock*パターンで適切に除外",
    "書込中検知: mtime前後比較による書込中ファイルのスキップ",
    "NAS切断検知: 全ファイル消失時にNAS切断と判断し削除をスキップする防御ロジック",
    "グレースフルシャットダウン: threading.Event.wait()で即座に待機解除",
    "APIレート制限定数化: API_WAIT_SECONDS定数と適切なsleep挿入",
    "テスト品質: 107件のテストは命名明確・1テスト1アサーション・フィクスチャ適切",
    "テスト分離: tmp_pathによる完全な分離、グローバル状態の汚染防止",
    ".gitignoreで認証情報(service_account.json, config.yaml)を除外",
    "Google API通信: gspread/google-authがHTTPS/TLSを自動適用",
]


# ============================================================
# Build PDF
# ============================================================

def build_pdf(output_path: str) -> None:
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )
    story = []

    # ---- Cover ----
    story.append(sp(20))
    story.append(p("tamatex コードレビュー報告書", "title"))
    story.append(sp(4))
    story.append(p("Excel → Google スプレッドシート自動同期システム", "subtitle"))
    story.append(p("デプロイ前 総合レビュー", "subtitle"))
    story.append(sp(6))
    story.append(hr())
    story.append(sp(4))

    meta = [
        ["レビュー実施日", TODAY.strftime("%Y年%m月%d日")],
        ["対象バージョン", "tamatex v0.1.0"],
        ["レビュー範囲", "src/tamatex/ (7モジュール), scripts/, tests/, config/"],
        ["レビュー手法", "静的コード分析（全行レビュー）+ テスト実行"],
        ["レビュー観点", "セキュリティ / コード品質 / 運用耐性 / テスト品質"],
    ]
    meta_data = [[p(r[0], "cell_b"), p(r[1], "cell")] for r in meta]
    mt = Table(meta_data, colWidths=[35 * mm, CW - 35 * mm])
    mt.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("GRID", (0, 0), (-1, -1), 0.4, C_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(mt)
    story.append(sp(10))

    # ---- Executive Summary ----
    story.append(p("1. エグゼクティブサマリー", "h1"))
    story.append(hr())

    story.append(p("tamatex v0.1.0 の全ソースコードを4つの観点からレビューした。基本的なコード品質は高く、SQLインジェクション対策・YAML安全読込・frozen dataclass等のベストプラクティスが適用されている。一方、本番デーモンとして24/7稼働するには対処すべき問題が複数検出された。", "body"))
    story.append(sp(3))

    # Summary counts
    summary_data = [
        [p("深刻度", "cell_c"), p("セキュリティ", "cell_c"), p("コード品質", "cell_c"),
         p("運用耐性", "cell_c"), p("テスト品質", "cell_c"), p("合計", "cell_c")],
        [p("CRITICAL", "cell_c"), p("1", "cell_c"), p("0", "cell_c"),
         p("2", "cell_c"), p("2", "cell_c"), p("5", "cell_c")],
        [p("HIGH", "cell_c"), p("4", "cell_c"), p("5", "cell_c"),
         p("7", "cell_c"), p("3", "cell_c"), p("19", "cell_c")],
        [p("MEDIUM", "cell_c"), p("5", "cell_c"), p("5", "cell_c"),
         p("1", "cell_c"), p("2", "cell_c"), p("13", "cell_c")],
        [p("LOW", "cell_c"), p("5", "cell_c"), p("10", "cell_c"),
         p("5", "cell_c"), p("1", "cell_c"), p("21", "cell_c")],
    ]
    sw = CW / 6
    st = Table(summary_data, colWidths=[sw] * 6)
    st_cmds = [
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        # CRITICAL row
        ("BACKGROUND", (0, 1), (0, 1), C_CRITICAL_BG),
        ("BACKGROUND", (-1, 1), (-1, 1), C_CRITICAL_BG),
        # HIGH row
        ("BACKGROUND", (0, 2), (0, 2), C_HIGH_BG),
        ("BACKGROUND", (-1, 2), (-1, 2), C_HIGH_BG),
    ]
    st.setStyle(TableStyle(st_cmds))
    story.append(st)
    story.append(sp(4))

    # Overall score
    story.append(p("<b>総合コンプライアンススコア: 72%</b> — デプロイ前に CRITICAL 5件 + HIGH 主要項目の修正が必須", "body_bold"))
    story.append(sp(2))

    # Top 5 issues
    story.append(p("最優先対応事項（デプロイ前必須）:", "h3"))
    top5 = [
        "Google API認証トークン自動更新の実装 → gspread.service_account()に切替え（1行修正）",
        "SQLiteコネクションリークの修正 → 単一コネクション保持+close()メソッド",
        "SQLiteパスの絶対パス化 → config.yamlに設定項目追加",
        "サービスアカウントキーのパーミッション設定 → chmod 600 / icacls",
        "sheets_sync.py / main.py のテスト作成 → テスト対象カバレッジ 71% → 100%",
    ]
    for item in top5:
        story.append(p(f"• {item}", "bullet"))

    story.append(PageBreak())

    # ---- Section 2: Security ----
    story.append(p("2. セキュリティ監査", "h1"))
    story.append(hr())
    story.append(p("認証情報管理、入力検証、パストラバーサル、依存関係の観点でレビューを実施した。致命的な脆弱性は1件。SQLインジェクション対策やYAML安全読込など基本的なセキュリティプラクティスは適切に実装されている。", "body"))
    story.append(sp(3))
    story.append(issue_table(SEC_ISSUES))

    story.append(PageBreak())

    # ---- Section 3: Code Quality ----
    story.append(p("3. コード品質", "h1"))
    story.append(hr())
    story.append(p("設計パターン、イミュータビリティ、関数サイズ、型安全性、エラーハンドリングの観点でレビューを実施した。全体的に高品質なコードベースだが、dataclassのミュータビリティとコネクション管理に構造的問題がある。", "body"))
    story.append(sp(3))
    story.append(issue_table(CODE_ISSUES))

    story.append(PageBreak())

    # ---- Section 4: Operational Resilience ----
    story.append(p("4. 運用耐性・耐障害性", "h1"))
    story.append(hr())
    story.append(p("24/7デーモンとしての長期安定稼働、NAS/API障害時のリカバリ、メモリ管理、Windowsサービス対応の観点でレビューを実施した。認証トークン期限切れとSQLiteコネクション管理が最大のリスク。", "body"))
    story.append(sp(3))
    story.append(issue_table(OPS_ISSUES))

    story.append(PageBreak())

    # ---- Section 5: Test Quality ----
    story.append(p("5. テスト品質", "h1"))
    story.append(hr())

    # Test execution results
    test_result = [
        [p("項目", "cell_c"), p("結果", "cell_c")],
        [p("テストケース総数", "cell"), p("107件", "cell_c")],
        [p("実行結果", "cell"), p("107 passed / 0 failed (0.20s)", "cell_c")],
        [p("テスト対象モジュール", "cell"), p("5 / 7 (71%)", "cell_c")],
        [p("未テストモジュール", "cell"), p("sheets_sync.py, main.py", "cell_c")],
        [p("テスト:実装行数比", "cell"), p("1.91 : 1", "cell_c")],
    ]
    trw = [CW * 0.5, CW * 0.5]
    trt = Table(test_result, colWidths=trw)
    trt.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("GRID", (0, 0), (-1, -1), 0.4, C_BORDER),
        ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(trt)
    story.append(sp(2))

    # Quality assessment
    tq_data = [
        [p("メトリクス", "cell_c"), p("評価", "cell_c"), p("判定", "cell_c")],
        [p("テスト分離", "cell"), p("完全（tmp_path使用）", "cell"), p("合格", "cell_c")],
        [p("アサーション品質", "cell"), p("優秀（具体的な期待値）", "cell"), p("合格", "cell_c")],
        [p("テスト命名", "cell"), p("優秀（振る舞いが明確）", "cell"), p("合格", "cell_c")],
        [p("エッジケース", "cell"), p("中程度", "cell"), p("改善必要", "cell_c")],
        [p("モジュールカバレッジ", "cell"), p("71%（5/7）", "cell"), p("不合格", "cell_c")],
    ]
    tqt = Table(tq_data, colWidths=[CW * 0.30, CW * 0.45, CW * 0.25])
    tq_style = [
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("GRID", (0, 0), (-1, -1), 0.4, C_BORDER),
        ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (2, 1), (2, 3), C_GREEN_BG),
        ("BACKGROUND", (2, 4), (2, 4), C_HIGH_BG),
        ("BACKGROUND", (2, 5), (2, 5), C_CRITICAL_BG),
    ]
    tqt.setStyle(TableStyle(tq_style))
    story.append(tqt)
    story.append(sp(3))

    story.append(issue_table(TEST_ISSUES))

    story.append(PageBreak())

    # ---- Section 6: Positive Findings ----
    story.append(p("6. 肯定的な評価（ポジティブ所見）", "h1"))
    story.append(hr())
    story.append(p("以下のセキュリティプラクティスおよび設計判断は優れており、プロジェクトの品質基盤として高く評価する。", "body"))
    story.append(sp(2))
    for item in POSITIVES:
        story.append(p(f"• {item}", "bullet"))

    story.append(sp(8))

    # ---- Section 7: Remediation Roadmap ----
    story.append(p("7. 修正ロードマップ", "h1"))
    story.append(hr())

    # Phase 1
    story.append(p("Phase 1: デプロイ前必須（想定工数: 1-2日）", "h2"))
    phase1 = [
        [p("ID", "cell_c"), p("概要", "cell"), p("工数", "cell_c")],
        [p("C-1", "cell_c"), p("gspread.service_account()に切替え（認証トークン自動更新）", "cell"), p("30分", "cell_c")],
        [p("C-2", "cell_c"), p("StateDB接続管理を単一コネクション+close()に変更", "cell"), p("1時間", "cell_c")],
        [p("F-01", "cell_c"), p("サービスアカウントキーのパーミッション設定", "cell"), p("2時間", "cell_c")],
        [p("F-04", "cell_c"), p("SQLiteパスの絶対パス化（config設定追加）", "cell"), p("2時間", "cell_c")],
        [p("F-03", "cell_c"), p("シンボリックリンク追跡の制限", "cell"), p("1時間", "cell_c")],
        [p("OH-5", "cell_c"), p("Windowsサービス停止シグナル対応", "cell"), p("1時間", "cell_c")],
    ]
    p1t = make_table(phase1, [12 * mm, CW - 12 * mm - 20 * mm, 20 * mm])
    story.append(p1t)
    story.append(sp(4))

    # Phase 2
    story.append(p("Phase 2: 初回リリース後30日以内（想定工数: 3-5日）", "h2"))
    phase2 = [
        [p("ID", "cell_c"), p("概要", "cell"), p("工数", "cell_c")],
        [p("OH-1/6", "cell_c"), p("Google API呼出しに指数バックオフリトライ追加", "cell"), p("3時間", "cell_c")],
        [p("T-01", "cell_c"), p("sheets_sync.py のモックテスト作成（8シナリオ以上）", "cell"), p("4時間", "cell_c")],
        [p("T-02", "cell_c"), p("main.py のモックテスト作成", "cell"), p("4時間", "cell_c")],
        [p("F-05", "cell_c"), p("ログのspreadsheet_idマスキング", "cell"), p("1時間", "cell_c")],
        [p("OH-2", "cell_c"), p("巨大Excelファイルサイズ上限チェック", "cell"), p("30分", "cell_c")],
        [p("OH-7", "cell_c"), p("壊れたExcelの連続失敗スキップ（サーキットブレーカー）", "cell"), p("1時間", "cell_c")],
        [p("OH-8", "cell_c"), p("シート全クリア後書込（余剰列対策）", "cell"), p("30分", "cell_c")],
        [p("H-1/2", "cell_c"), p("dataclass frozen=True化・イミュータビリティ改善", "cell"), p("2時間", "cell_c")],
        [p("H-4", "cell_c"), p("バージョン文字列のsingle source of truth化", "cell"), p("1時間", "cell_c")],
    ]
    p2t = make_table(phase2, [12 * mm, CW - 12 * mm - 20 * mm, 20 * mm])
    story.append(p2t)
    story.append(sp(4))

    # Phase 3
    story.append(p("Phase 3: 継続的改善（90日以内）", "h2"))
    phase3 = [
        [p("ID", "cell_c"), p("概要", "cell"), p("工数", "cell_c")],
        [p("F-06", "cell_c"), p("YAML型チェック・値域バリデーション強化", "cell"), p("2時間", "cell_c")],
        [p("F-08", "cell_c"), p("MD5 → SHA-256移行（+DBマイグレーション）", "cell"), p("2時間", "cell_c")],
        [p("M-1/2", "cell_c"), p("sync_workbook/sync_cycleの関数分割（50行以下に）", "cell"), p("2時間", "cell_c")],
        [p("OM-7", "cell_c"), p("ヘルスチェック・死活監視機構の実装", "cell"), p("2時間", "cell_c")],
        [p("T-03/4/5", "cell_c"), p("watcher/excel_readerのエッジケーステスト追加", "cell"), p("3時間", "cell_c")],
        [p("その他", "cell_c"), p("MEDIUM/LOW項目の順次対応", "cell"), p("5時間", "cell_c")],
    ]
    p3t = make_table(phase3, [12 * mm, CW - 12 * mm - 20 * mm, 20 * mm])
    story.append(p3t)

    story.append(sp(10))
    story.append(hr())
    story.append(p(f"本レポートは {TODAY.strftime('%Y年%m月%d日')} に静的コード分析により作成されました。", "small"))
    story.append(p("レビュー対象: tamatex v0.1.0 全ソースコード（src/tamatex/, scripts/, tests/）", "small"))

    # ---- Build ----
    doc.build(story)
    print(f"レビュー報告書を生成しました: {output_path}")


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent.parent / "docs"
    out_dir.mkdir(exist_ok=True)
    build_pdf(str(out_dir / "コードレビュー報告書.pdf"))
