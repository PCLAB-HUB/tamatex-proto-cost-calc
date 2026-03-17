"""tamatex インストーラーウィザード。

Excel→Google Spreadsheet同期システムのGUIセットアップウィザード。
非技術者向けに7ステップのガイド付きインストールを提供する。

対象環境: Windows 11 x64
依存: tkinter (Python標準ライブラリ)
"""

from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import tkinter as tk
import tkinter.ttk as ttk

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

WINDOW_WIDTH = 780
WINDOW_HEIGHT = 560
SIDEBAR_WIDTH = 180
CANVAS_WIDTH = 580
CANVAS_HEIGHT = 140

# Colors
C_PRIMARY = "#1a73e8"
C_SUCCESS = "#34a853"
C_WARNING = "#ea8600"
C_ERROR = "#ea4335"
C_TEXT_DARK = "#202124"
C_TEXT_GRAY = "#5f6368"
C_BG_LIGHT = "#f8f9fa"
C_WHITE = "#ffffff"
C_SIDEBAR_BG = "#e8f0fe"
C_BORDER = "#dadce0"
C_PRIMARY_LIGHT = "#d2e3fc"

STEP_LABELS: list[str] = [
    "ようこそ",
    "Google Cloud設定",
    "サービスアカウント",
    "Google Drive設定",
    "構成入力",
    "インストール",
    "完了",
]

# Files/directories to copy during installation
COPY_ITEMS: list[str] = [
    "src",
    "config/config.example.yaml",
    "scripts/initial_setup.py",
    "requirements.txt",
    "pyproject.toml",
]

SKIP_PATTERNS: set[str] = {
    ".git",
    ".venv",
    "__pycache__",
    "docs",
    ".DS_Store",
    "scripts/installer.py",
    "scripts/generate_pdf.py",
}


# ---------------------------------------------------------------------------
# Canvas drawing helpers
# ---------------------------------------------------------------------------


def _rounded_rect(
    canvas: tk.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float = 10,
    **kwargs: Any,
) -> int:
    """Draw a rounded rectangle on a canvas."""
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def _draw_arrow(
    canvas: tk.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    color: str = C_PRIMARY,
    width: int = 2,
) -> None:
    """Draw an arrow line on a canvas."""
    canvas.create_line(x1, y1, x2, y2, arrow=tk.LAST, fill=color, width=width)


def _draw_icon_circle(
    canvas: tk.Canvas,
    cx: float,
    cy: float,
    r: float,
    fill: str = C_PRIMARY,
) -> None:
    """Draw a filled circle."""
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=fill, outline="")


# ---------------------------------------------------------------------------
# Illustration drawing functions (one per step)
# ---------------------------------------------------------------------------


def _draw_welcome(canvas: tk.Canvas) -> None:
    """Step 0: System flow diagram (NAS -> tamatex -> Google Sheets)."""
    canvas.delete("all")
    cy = 70

    # NAS box
    _rounded_rect(canvas, 30, cy - 30, 160, cy + 30, radius=8,
                  fill="#e8f0fe", outline=C_PRIMARY, width=2)
    canvas.create_text(95, cy - 8, text="QNAP NAS", font=("Helvetica", 11, "bold"),
                       fill=C_PRIMARY)
    canvas.create_text(95, cy + 12, text="Excel Files", font=("Helvetica", 9),
                       fill=C_TEXT_GRAY)

    # Arrow 1
    _draw_arrow(canvas, 165, cy, 225, cy, color=C_PRIMARY, width=3)

    # tamatex box
    _rounded_rect(canvas, 230, cy - 30, 360, cy + 30, radius=8,
                  fill=C_PRIMARY, outline=C_PRIMARY, width=2)
    canvas.create_text(295, cy - 8, text="tamatex", font=("Helvetica", 12, "bold"),
                       fill=C_WHITE)
    canvas.create_text(295, cy + 12, text="自動同期", font=("Helvetica", 9),
                       fill="#d2e3fc")

    # Arrow 2
    _draw_arrow(canvas, 365, cy, 425, cy, color=C_SUCCESS, width=3)

    # Google Sheets box
    _rounded_rect(canvas, 430, cy - 30, 560, cy + 30, radius=8,
                  fill="#e6f4ea", outline=C_SUCCESS, width=2)
    canvas.create_text(495, cy - 8, text="Google", font=("Helvetica", 11, "bold"),
                       fill=C_SUCCESS)
    canvas.create_text(495, cy + 12, text="Spreadsheet", font=("Helvetica", 9),
                       fill=C_TEXT_GRAY)

    # Clock icon (sync interval hint)
    canvas.create_text(295, cy + 55, text="15分ごとに自動同期",
                       font=("Helvetica", 9), fill=C_TEXT_GRAY)

    # Small circular arrows representing sync
    _cx, _cy = 295, cy + 42
    canvas.create_arc(_cx - 8, _cy - 8, _cx + 8, _cy + 8,
                      start=30, extent=300, style=tk.ARC,
                      outline=C_TEXT_GRAY, width=1)


def _draw_google_cloud(canvas: tk.Canvas) -> None:
    """Step 1: Cloud icon with gears."""
    canvas.delete("all")
    cy = 65

    # Cloud shape (overlapping ovals)
    canvas.create_oval(180, cy - 25, 240, cy + 15, fill="#e8f0fe", outline=C_PRIMARY, width=2)
    canvas.create_oval(220, cy - 35, 300, cy + 15, fill="#e8f0fe", outline=C_PRIMARY, width=2)
    canvas.create_oval(280, cy - 25, 340, cy + 15, fill="#e8f0fe", outline=C_PRIMARY, width=2)
    canvas.create_oval(200, cy - 10, 320, cy + 25, fill="#e8f0fe", outline=C_PRIMARY, width=2)
    # Fill center to hide inner outlines
    canvas.create_oval(205, cy - 20, 315, cy + 20, fill="#e8f0fe", outline="#e8f0fe")

    # Gear icon 1
    _draw_gear(canvas, 370, cy - 10, 18, C_PRIMARY)
    # Gear icon 2
    _draw_gear(canvas, 395, cy + 15, 12, C_PRIMARY_LIGHT)

    # Text
    canvas.create_text(260, cy + 50, text="Google Cloud プロジェクト & API設定",
                       font=("Helvetica", 10), fill=C_TEXT_DARK)

    # API labels
    _rounded_rect(canvas, 160, cy + 70, 280, cy + 90, radius=5,
                  fill="#e6f4ea", outline=C_SUCCESS)
    canvas.create_text(220, cy + 80, text="Sheets API", font=("Helvetica", 9),
                       fill=C_SUCCESS)

    _rounded_rect(canvas, 290, cy + 70, 400, cy + 90, radius=5,
                  fill="#e6f4ea", outline=C_SUCCESS)
    canvas.create_text(345, cy + 80, text="Drive API", font=("Helvetica", 9),
                       fill=C_SUCCESS)


def _draw_gear(canvas: tk.Canvas, cx: float, cy: float, r: float, color: str) -> None:
    """Draw a simple gear icon."""
    # Outer circle
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline="")
    # Inner circle
    inner_r = r * 0.45
    canvas.create_oval(cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r,
                       fill=C_WHITE, outline="")
    # Teeth (small rectangles around the circle)
    tooth_count = 6
    tooth_w = r * 0.3
    tooth_h = r * 0.35
    for i in range(tooth_count):
        angle = math.radians(i * (360 / tooth_count))
        tx = cx + (r + tooth_h * 0.3) * math.cos(angle)
        ty = cy + (r + tooth_h * 0.3) * math.sin(angle)
        canvas.create_oval(tx - tooth_w, ty - tooth_w, tx + tooth_w, ty + tooth_w,
                           fill=color, outline="")


def _draw_service_account(canvas: tk.Canvas) -> None:
    """Step 2: Key/lock icon."""
    canvas.delete("all")
    cx, cy = 290, 55

    # Key body
    _draw_icon_circle(canvas, cx - 40, cy, 22, fill=C_PRIMARY)
    _draw_icon_circle(canvas, cx - 40, cy, 10, fill=C_WHITE)
    canvas.create_rectangle(cx - 20, cy - 4, cx + 40, cy + 4,
                            fill=C_PRIMARY, outline="")
    # Key teeth
    canvas.create_rectangle(cx + 20, cy + 4, cx + 28, cy + 14,
                            fill=C_PRIMARY, outline="")
    canvas.create_rectangle(cx + 32, cy + 4, cx + 40, cy + 10,
                            fill=C_PRIMARY, outline="")

    # Lock icon (right side)
    lock_cx = cx + 100
    # Lock body
    _rounded_rect(canvas, lock_cx - 18, cy - 5, lock_cx + 18, cy + 25,
                  radius=4, fill=C_WARNING, outline="")
    # Lock shackle
    canvas.create_arc(lock_cx - 12, cy - 25, lock_cx + 12, cy + 5,
                      start=0, extent=180, style=tk.ARC,
                      outline=C_WARNING, width=4)
    # Keyhole
    _draw_icon_circle(canvas, lock_cx, cy + 6, 4, fill=C_WHITE)
    canvas.create_rectangle(lock_cx - 2, cy + 8, lock_cx + 2, cy + 18,
                            fill=C_WHITE, outline="")

    # Text
    canvas.create_text(290, cy + 55, text="サービスアカウント & JSONキーファイル",
                       font=("Helvetica", 10), fill=C_TEXT_DARK)

    # JSON file icon
    _rounded_rect(canvas, 200, cy + 70, 260, cy + 98, radius=4,
                  fill="#fce8e6", outline=C_ERROR)
    canvas.create_text(230, cy + 84, text=".json", font=("Helvetica", 9, "bold"),
                       fill=C_ERROR)

    # Arrow from JSON to lock
    _draw_arrow(canvas, 265, cy + 84, 310, cy + 84, color=C_TEXT_GRAY, width=1)

    _rounded_rect(canvas, 315, cy + 70, 395, cy + 98, radius=4,
                  fill="#e8f0fe", outline=C_PRIMARY)
    canvas.create_text(355, cy + 84, text="認証完了",
                       font=("Helvetica", 9, "bold"), fill=C_PRIMARY)


def _draw_drive_setup(canvas: tk.Canvas) -> None:
    """Step 3: Folder with sharing icon."""
    canvas.delete("all")
    cx, cy = 290, 55

    # Folder shape
    canvas.create_polygon(
        cx - 50, cy - 20,
        cx - 50, cy + 25,
        cx + 50, cy + 25,
        cx + 50, cy - 10,
        cx + 10, cy - 10,
        cx, cy - 20,
        fill="#e8f0fe", outline=C_PRIMARY, width=2,
    )

    # Share icon (person + arrow)
    share_cx = cx + 80
    _draw_icon_circle(canvas, share_cx, cy - 8, 8, fill=C_SUCCESS)
    canvas.create_arc(share_cx - 12, cy + 2, share_cx + 12, cy + 20,
                      start=0, extent=180, fill=C_SUCCESS, outline="")
    # Arrow
    _draw_arrow(canvas, cx + 55, cy, share_cx - 16, cy, color=C_TEXT_GRAY, width=2)

    # Text
    canvas.create_text(290, cy + 52, text="Google Driveフォルダ作成 & 共有設定",
                       font=("Helvetica", 10), fill=C_TEXT_DARK)

    # Folder ID hint
    _rounded_rect(canvas, 170, cy + 68, 410, cy + 90, radius=5,
                  fill=C_BG_LIGHT, outline=C_BORDER)
    canvas.create_text(290, cy + 79, text="フォルダID: 1AbCd2EfGh3...",
                       font=("Helvetica", 9), fill=C_TEXT_GRAY)


def _draw_config(canvas: tk.Canvas) -> None:
    """Step 4: Settings/gear icon."""
    canvas.delete("all")
    cx, cy = 290, 58

    # Large gear
    _draw_gear(canvas, cx, cy, 30, C_PRIMARY)

    # Small gear
    _draw_gear(canvas, cx + 35, cy + 25, 16, "#5f9ee8")

    # Slider bars (settings)
    for i, (w, c) in enumerate([(40, C_SUCCESS), (55, C_WARNING), (35, C_PRIMARY)]):
        bx = cx - 100
        by = cy - 20 + i * 22
        canvas.create_rectangle(bx, by, bx + 70, by + 6, fill=C_BG_LIGHT, outline="")
        canvas.create_rectangle(bx, by, bx + w, by + 6, fill=c, outline="")
        _draw_icon_circle(canvas, bx + w, by + 3, 5, fill=c)

    # Text
    canvas.create_text(290, cy + 55, text="同期設定 & インストール先の指定",
                       font=("Helvetica", 10), fill=C_TEXT_DARK)


def _draw_install(canvas: tk.Canvas) -> None:
    """Step 5: Download/install icon."""
    canvas.delete("all")
    cx, cy = 290, 50

    # Box (package)
    _rounded_rect(canvas, cx - 35, cy - 10, cx + 35, cy + 30, radius=5,
                  fill="#e8f0fe", outline=C_PRIMARY, width=2)
    # Box flaps
    canvas.create_polygon(
        cx - 40, cy - 10,
        cx, cy - 25,
        cx + 40, cy - 10,
        fill="#d2e3fc", outline=C_PRIMARY, width=2,
    )
    canvas.create_line(cx, cy - 25, cx, cy + 5, fill=C_PRIMARY, width=2)

    # Down arrow
    canvas.create_line(cx, cy - 50, cx, cy - 28, fill=C_SUCCESS, width=3,
                       arrow=tk.LAST, arrowshape=(8, 10, 5))

    # Progress bar hint
    _rounded_rect(canvas, cx - 80, cy + 50, cx + 80, cy + 62, radius=4,
                  fill=C_BG_LIGHT, outline=C_BORDER)
    _rounded_rect(canvas, cx - 80, cy + 50, cx - 10, cy + 62, radius=4,
                  fill=C_SUCCESS, outline="")

    # Text
    canvas.create_text(290, cy + 80, text="自動インストール実行中...",
                       font=("Helvetica", 10), fill=C_TEXT_DARK)


def _draw_complete(canvas: tk.Canvas) -> None:
    """Step 6: Green checkmark."""
    canvas.delete("all")
    cx, cy = 290, 60

    # Circle background
    _draw_icon_circle(canvas, cx, cy, 40, fill="#e6f4ea")
    _draw_icon_circle(canvas, cx, cy, 32, fill=C_SUCCESS)

    # Checkmark
    canvas.create_line(
        cx - 16, cy + 2,
        cx - 4, cy + 14,
        cx + 18, cy - 12,
        fill=C_WHITE, width=5, capstyle=tk.ROUND, joinstyle=tk.ROUND,
    )

    # Text
    canvas.create_text(290, cy + 55, text="セットアップ完了",
                       font=("Helvetica", 12, "bold"), fill=C_SUCCESS)


ILLUSTRATION_DRAWERS: list[Any] = [
    _draw_welcome,
    _draw_google_cloud,
    _draw_service_account,
    _draw_drive_setup,
    _draw_config,
    _draw_install,
    _draw_complete,
]


# ---------------------------------------------------------------------------
# Main application class
# ---------------------------------------------------------------------------


class InstallerWizard:
    """7-step GUI installer wizard for the tamatex system."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Excel同期システム セットアップ")
        self.root.resizable(False, False)

        # Center on screen
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - WINDOW_WIDTH) // 2
        y = (screen_h - WINDOW_HEIGHT) // 2
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")
        self.root.configure(bg=C_WHITE)

        # State variables
        self.current_step: int = 0
        self.installing: bool = False
        self.install_complete: bool = False

        # User inputs (populated during wizard steps)
        self.api_enabled_var = tk.BooleanVar(value=False)
        self.json_key_path: str = ""
        self.service_account_email: str = ""
        self.folder_id_var = tk.StringVar(value="")
        self.folder_shared_var = tk.BooleanVar(value=False)
        self.nas_path_var = tk.StringVar(value="Z:\\")
        self.sync_interval_var = tk.IntVar(value=15)
        self.share_emails_text: tk.Text | None = None
        self.install_path_var = tk.StringVar(value="C:\\tamatex")
        self.json_path_var = tk.StringVar(value="")

        # UI references
        self.sidebar_labels: list[tk.Label] = []
        self.sidebar_checks: list[tk.Label] = []
        self.content_frame: tk.Frame | None = None
        self.canvas: tk.Canvas | None = None
        self.scroll_frame: tk.Frame | None = None
        self.btn_back: tk.Button | None = None
        self.btn_next: tk.Button | None = None
        self.btn_close: tk.Button | None = None
        self.progress_var = tk.DoubleVar(value=0)
        self.log_text: tk.Text | None = None

        self._build_ui()
        self._show_step(0)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Build the main window layout."""
        # Sidebar
        sidebar = tk.Frame(self.root, width=SIDEBAR_WIDTH, bg=C_SIDEBAR_BG)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="セットアップ手順", font=("Helvetica", 10, "bold"),
                 bg=C_SIDEBAR_BG, fg=C_TEXT_DARK, anchor="w", padx=12
                 ).pack(fill=tk.X, pady=(16, 8))

        for i, label_text in enumerate(STEP_LABELS):
            row = tk.Frame(sidebar, bg=C_SIDEBAR_BG)
            row.pack(fill=tk.X, padx=8, pady=2)

            check_lbl = tk.Label(row, text="  ", font=("Helvetica", 10),
                                 bg=C_SIDEBAR_BG, fg=C_SUCCESS, width=2)
            check_lbl.pack(side=tk.LEFT)
            self.sidebar_checks.append(check_lbl)

            step_lbl = tk.Label(
                row, text=f"{i}. {label_text}", font=("Helvetica", 10),
                bg=C_SIDEBAR_BG, fg=C_TEXT_GRAY, anchor="w", padx=4, pady=4,
            )
            step_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.sidebar_labels.append(step_lbl)

        # Right content area
        right = tk.Frame(self.root, bg=C_WHITE)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Canvas for illustrations
        self.canvas = tk.Canvas(
            right, width=CANVAS_WIDTH, height=CANVAS_HEIGHT,
            bg=C_WHITE, highlightthickness=1, highlightbackground=C_BORDER,
        )
        self.canvas.pack(padx=10, pady=(10, 5))

        # Scrollable content area
        content_container = tk.Frame(right, bg=C_WHITE)
        content_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self._content_canvas = tk.Canvas(content_container, bg=C_WHITE,
                                         highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_container, orient=tk.VERTICAL,
                                  command=self._content_canvas.yview)
        self.scroll_frame = tk.Frame(self._content_canvas, bg=C_WHITE)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self._content_canvas.configure(
                scrollregion=self._content_canvas.bbox("all")
            ),
        )

        self._content_canvas.create_window((0, 0), window=self.scroll_frame,
                                           anchor="nw", width=555)
        self._content_canvas.configure(yscrollcommand=scrollbar.set)

        self._content_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind mousewheel scrolling
        self._bind_mousewheel(self._content_canvas)

        # Bottom navigation bar
        nav = tk.Frame(right, bg=C_WHITE, height=50)
        nav.pack(fill=tk.X, padx=10, pady=(0, 10))
        nav.pack_propagate(False)

        self.btn_back = tk.Button(
            nav, text="< 戻る", font=("Helvetica", 10),
            command=self._go_back, state=tk.DISABLED,
            bg=C_WHITE, fg=C_TEXT_DARK, relief=tk.FLAT,
            activebackground=C_BG_LIGHT, padx=16, pady=6,
            cursor="hand2",
        )
        self.btn_back.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_close = tk.Button(
            nav, text="閉じる", font=("Helvetica", 10),
            command=self._on_close,
            bg=C_WHITE, fg=C_TEXT_DARK, relief=tk.FLAT,
            activebackground=C_BG_LIGHT, padx=16, pady=6,
            cursor="hand2",
        )
        self.btn_close.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_close.pack_forget()  # Hidden until final step

        self.btn_next = tk.Button(
            nav, text="次へ >", font=("Helvetica", 10, "bold"),
            command=self._go_next,
            bg=C_PRIMARY, fg=C_WHITE, relief=tk.FLAT,
            activebackground="#1557b0", padx=20, pady=6,
            cursor="hand2",
        )
        self.btn_next.pack(side=tk.RIGHT)

    def _bind_mousewheel(self, widget: tk.Widget) -> None:
        """Bind mousewheel events for scrolling."""
        def _on_mousewheel(event: tk.Event) -> None:  # type: ignore[type-arg]
            # macOS uses event.delta directly; Windows uses event.delta / 120
            if sys.platform == "darwin":
                self._content_canvas.yview_scroll(-event.delta, "units")
            else:
                self._content_canvas.yview_scroll(-event.delta // 120, "units")

        widget.bind("<MouseWheel>", _on_mousewheel)
        # Also bind on the scroll frame for convenience
        self.scroll_frame.bind("<MouseWheel>", _on_mousewheel)  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Sidebar updates
    # ------------------------------------------------------------------

    def _update_sidebar(self) -> None:
        """Highlight current step and mark completed steps."""
        for i, (lbl, chk) in enumerate(zip(self.sidebar_labels, self.sidebar_checks)):
            if i < self.current_step:
                # Completed
                lbl.configure(fg=C_SUCCESS, font=("Helvetica", 10))
                chk.configure(text="\u2713")  # checkmark
            elif i == self.current_step:
                # Current
                lbl.configure(fg=C_PRIMARY, font=("Helvetica", 10, "bold"))
                chk.configure(text="\u25b6")  # triangle
            else:
                # Future
                lbl.configure(fg=C_TEXT_GRAY, font=("Helvetica", 10))
                chk.configure(text="  ")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _go_back(self) -> None:
        """Navigate to the previous step."""
        if self.current_step > 0 and not self.installing:
            self._show_step(self.current_step - 1)

    def _go_next(self) -> None:
        """Validate current step and navigate to the next."""
        if not self._validate_step(self.current_step):
            return
        if self.current_step < len(STEP_LABELS) - 1:
            self._show_step(self.current_step + 1)

    def _validate_step(self, step: int) -> bool:
        """Validate inputs for the given step. Returns True if valid."""
        if step == 1:
            if not self.api_enabled_var.get():
                messagebox.showwarning(
                    "確認", "「APIの有効化が完了しました」にチェックを入れてください。"
                )
                return False

        elif step == 2:
            if not self.json_key_path:
                messagebox.showwarning(
                    "確認", "サービスアカウントのJSONキーファイルを選択してください。"
                )
                return False

        elif step == 3:
            folder_id = self.folder_id_var.get().strip()
            if not folder_id:
                messagebox.showwarning(
                    "確認", "Google DriveフォルダIDを入力してください。"
                )
                return False
            if not self.folder_shared_var.get():
                messagebox.showwarning(
                    "確認", "「フォルダの共有設定が完了しました」にチェックを入れてください。"
                )
                return False
            self.folder_id_var.set(folder_id)

        elif step == 4:
            nas_path = self.nas_path_var.get().strip()
            if not nas_path:
                messagebox.showwarning("確認", "NASパスを入力してください。")
                return False
            install_path = self.install_path_var.get().strip()
            if not install_path:
                messagebox.showwarning("確認", "インストール先を入力してください。")
                return False
            # Warn (but allow) if NAS path is inaccessible
            if not Path(nas_path).exists():
                proceed = messagebox.askyesno(
                    "警告",
                    f"NASパス「{nas_path}」にアクセスできません。\n"
                    "このまま続行しますか？\n\n"
                    "（NASが接続されていない場合は「はい」で続行できます）",
                )
                if not proceed:
                    return False

        return True

    def _on_close(self) -> None:
        """Handle the close button or window close."""
        if self.installing:
            messagebox.showwarning(
                "インストール中",
                "インストール中は閉じることができません。完了までお待ちください。",
            )
            return
        self.root.destroy()

    def _show_step(self, step: int) -> None:
        """Display the specified wizard step."""
        self.current_step = step
        self._update_sidebar()

        # Clear scrollable content
        for widget in self.scroll_frame.winfo_children():  # type: ignore[union-attr]
            widget.destroy()

        # Reset scroll position
        self._content_canvas.yview_moveto(0)

        # Draw illustration
        ILLUSTRATION_DRAWERS[step](self.canvas)

        # Update navigation buttons
        self.btn_back.configure(  # type: ignore[union-attr]
            state=tk.NORMAL if step > 0 and not self.installing else tk.DISABLED,
        )

        if step == len(STEP_LABELS) - 1:
            # Final step
            self.btn_next.pack_forget()  # type: ignore[union-attr]
            self.btn_close.pack(side=tk.RIGHT)  # type: ignore[union-attr]
        else:
            self.btn_close.pack_forget()  # type: ignore[union-attr]
            self.btn_next.pack(side=tk.RIGHT)  # type: ignore[union-attr]
            self.btn_next.configure(state=tk.NORMAL)  # type: ignore[union-attr]

        # Build step content
        builders = [
            self._build_step0,
            self._build_step1,
            self._build_step2,
            self._build_step3,
            self._build_step4,
            self._build_step5,
            self._build_step6,
        ]
        builders[step]()

    # ------------------------------------------------------------------
    # Helper: create styled widgets
    # ------------------------------------------------------------------

    def _heading(self, parent: tk.Frame, text: str) -> tk.Label:
        lbl = tk.Label(parent, text=text, font=("Helvetica", 13, "bold"),
                       bg=C_WHITE, fg=C_TEXT_DARK, anchor="w")
        lbl.pack(fill=tk.X, pady=(8, 4))
        return lbl

    def _paragraph(self, parent: tk.Frame, text: str) -> tk.Label:
        lbl = tk.Label(parent, text=text, font=("Helvetica", 10),
                       bg=C_WHITE, fg=C_TEXT_GRAY, anchor="w",
                       wraplength=540, justify=tk.LEFT)
        lbl.pack(fill=tk.X, pady=(2, 4))
        return lbl

    def _instruction(self, parent: tk.Frame, number: int, text: str) -> tk.Frame:
        row = tk.Frame(parent, bg=C_WHITE)
        row.pack(fill=tk.X, pady=2)
        num_lbl = tk.Label(row, text=f" {number}.", font=("Helvetica", 10, "bold"),
                           bg=C_WHITE, fg=C_PRIMARY, width=3, anchor="ne")
        num_lbl.pack(side=tk.LEFT, anchor="n", padx=(0, 4))
        txt_lbl = tk.Label(row, text=text, font=("Helvetica", 10),
                           bg=C_WHITE, fg=C_TEXT_DARK, anchor="w",
                           wraplength=500, justify=tk.LEFT)
        txt_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        return row

    def _url_button(self, parent: tk.Frame, text: str, url: str) -> tk.Button:
        btn = tk.Button(
            parent, text=text, font=("Helvetica", 10),
            command=lambda: webbrowser.open(url),
            bg=C_WHITE, fg=C_PRIMARY, relief=tk.SOLID,
            borderwidth=1, padx=12, pady=4, cursor="hand2",
            activebackground=C_BG_LIGHT,
        )
        btn.pack(anchor="w", pady=6)
        return btn

    def _action_button(
        self, parent: tk.Frame, text: str, command: Any,
        bg: str = C_PRIMARY, fg: str = C_WHITE,
    ) -> tk.Button:
        btn = tk.Button(
            parent, text=text, font=("Helvetica", 10, "bold"),
            command=command, bg=bg, fg=fg, relief=tk.FLAT,
            padx=16, pady=6, cursor="hand2",
            activebackground=bg,
        )
        btn.pack(anchor="w", pady=6)
        return btn

    def _separator(self, parent: tk.Frame) -> None:
        sep = tk.Frame(parent, bg=C_BORDER, height=1)
        sep.pack(fill=tk.X, pady=8)

    # ------------------------------------------------------------------
    # Step builders
    # ------------------------------------------------------------------

    def _build_step0(self) -> None:
        """Step 0: Welcome."""
        f = self.scroll_frame
        assert f is not None

        self._heading(f, "Excel同期システム セットアップへようこそ")
        self._paragraph(
            f,
            "このウィザードでは、QNAP NAS上のExcelファイルを\n"
            "Google スプレッドシートに自動同期するシステム「tamatex」を\n"
            "セットアップします。",
        )

        self._separator(f)

        self._heading(f, "このツールでできること")
        self._paragraph(
            f,
            "\u2022 NAS上のExcelファイル (.xlsx) を自動検出\n"
            "\u2022 Google スプレッドシートへ定期的に同期\n"
            "\u2022 15分間隔（変更可能）で最新データを反映\n"
            "\u2022 変更があったファイルのみ効率的に同期",
        )

        self._separator(f)

        self._heading(f, "セットアップ所要時間")
        self._paragraph(f, "約 10〜15 分（Google Cloud設定を含む）")

        self._paragraph(
            f,
            "\n「次へ」をクリックして、セットアップを開始してください。",
        )

    def _build_step1(self) -> None:
        """Step 1: Google Cloud Setup."""
        f = self.scroll_frame
        assert f is not None

        self._heading(f, "Google Cloud プロジェクト & API設定")
        self._paragraph(
            f,
            "Google スプレッドシートへの同期にはGoogle Cloud APIが必要です。\n"
            "以下の手順に従って設定してください。",
        )

        self._separator(f)

        self._instruction(
            f, 1,
            "下のボタンからGoogle Cloud Consoleにアクセスし、\n"
            "Googleアカウントでログインしてください。",
        )
        self._instruction(
            f, 2,
            "左上のプロジェクト選択メニューから「新しいプロジェクト」を\n"
            "クリックし、プロジェクト名に「tamatex」と入力して作成します。",
        )
        self._instruction(
            f, 3,
            "作成したプロジェクトを選択した状態で、左メニューの\n"
            "「APIとサービス」→「ライブラリ」を開きます。",
        )
        self._instruction(
            f, 4,
            "検索バーで「Google Sheets API」を検索し、「有効にする」をクリック。\n"
            "同様に「Google Drive API」も検索して有効にしてください。",
        )

        self._separator(f)

        self._url_button(
            f, "Google Cloud Consoleを開く",
            "https://console.cloud.google.com/",
        )

        chk = tk.Checkbutton(
            f, text="APIの有効化が完了しました",
            variable=self.api_enabled_var,
            font=("Helvetica", 10), bg=C_WHITE, fg=C_TEXT_DARK,
            activebackground=C_WHITE, selectcolor=C_WHITE,
            cursor="hand2",
        )
        chk.pack(anchor="w", pady=(8, 4))

    def _build_step2(self) -> None:
        """Step 2: Service Account Setup."""
        f = self.scroll_frame
        assert f is not None

        self._heading(f, "サービスアカウントの作成")
        self._paragraph(
            f,
            "サービスアカウントは、このツールがGoogle APIに\n"
            "アクセスするために使用する専用アカウントです。",
        )

        self._separator(f)

        self._instruction(
            f, 1,
            "下のボタンから認証情報ページを開いてください。\n"
            "（先ほど作成したプロジェクトが選択されていることを確認）",
        )
        self._instruction(
            f, 2,
            "「+ サービスアカウントを作成」をクリックします。\n"
            "名前は「tamatex-sync」などわかりやすいものにしてください。",
        )
        self._instruction(
            f, 3,
            "作成されたサービスアカウントをクリックし、\n"
            "「キー」タブ→「鍵を追加」→「新しい鍵を作成」を選択。\n"
            "タイプは「JSON」のまま「作成」をクリックします。",
        )
        self._instruction(
            f, 4,
            "JSONファイルが自動的にダウンロードされます。\n"
            "下のボタンでダウンロードしたファイルを選択してください。",
        )

        self._separator(f)

        self._url_button(
            f, "認証情報ページを開く",
            "https://console.cloud.google.com/iam-admin/serviceaccounts",
        )

        # File selection row
        file_row = tk.Frame(f, bg=C_WHITE)
        file_row.pack(fill=tk.X, pady=6)

        tk.Label(file_row, text="JSONキーファイル:", font=("Helvetica", 10),
                 bg=C_WHITE, fg=C_TEXT_DARK).pack(side=tk.LEFT)

        self.json_path_var.set(self.json_key_path)
        entry = tk.Entry(file_row, textvariable=self.json_path_var,
                         font=("Helvetica", 9), width=36, state="readonly",
                         readonlybackground=C_BG_LIGHT)
        entry.pack(side=tk.LEFT, padx=(8, 4))

        tk.Button(
            file_row, text="参照...", font=("Helvetica", 9),
            command=self._select_json_key,
            bg=C_WHITE, fg=C_TEXT_DARK, relief=tk.SOLID, borderwidth=1,
            padx=8, pady=2, cursor="hand2",
        ).pack(side=tk.LEFT)

        # Service account email display
        self._sa_email_label = tk.Label(
            f, text="", font=("Helvetica", 10), bg=C_BG_LIGHT,
            fg=C_PRIMARY, anchor="w", padx=8, pady=4,
        )
        if self.service_account_email:
            self._sa_email_label.configure(
                text=f"サービスアカウント: {self.service_account_email}",
            )
            self._sa_email_label.pack(fill=tk.X, pady=4)

    def _select_json_key(self) -> None:
        """Open file dialog to select the JSON key file and validate it."""
        path = filedialog.askopenfilename(
            title="サービスアカウントのJSONキーファイルを選択",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError) as e:
            messagebox.showerror(
                "エラー",
                f"JSONファイルの読み込みに失敗しました。\n\n{e}",
            )
            return

        if "client_email" not in data:
            messagebox.showerror(
                "エラー",
                "このJSONファイルにはサービスアカウント情報（client_email）が\n"
                "含まれていません。正しいファイルを選択してください。",
            )
            return

        self.json_key_path = path
        self.service_account_email = data["client_email"]
        self.json_path_var.set(path)

        # Show email
        self._sa_email_label.configure(
            text=f"サービスアカウント: {self.service_account_email}",
        )
        self._sa_email_label.pack(fill=tk.X, pady=4)

        messagebox.showinfo(
            "確認",
            f"JSONキーファイルを読み込みました。\n\n"
            f"サービスアカウント:\n{self.service_account_email}",
        )

    def _build_step3(self) -> None:
        """Step 3: Google Drive Setup."""
        f = self.scroll_frame
        assert f is not None

        self._heading(f, "Google Driveフォルダの設定")
        self._paragraph(
            f,
            "同期先のGoogle Driveフォルダを作成し、\n"
            "サービスアカウントと共有します。",
        )

        self._separator(f)

        self._instruction(
            f, 1,
            "Google Driveを開き、同期先のフォルダを作成してください。\n"
            "（例: 「Excel同期データ」）",
        )
        self._instruction(
            f, 2,
            "作成したフォルダを開いた状態で、ブラウザのURLバーから\n"
            "フォルダIDをコピーします。\n"
            "URL例: https://drive.google.com/drive/folders/【このID部分】",
        )
        self._instruction(
            f, 3,
            "フォルダを右クリック→「共有」→「ユーザーやグループと共有」で、\n"
            "下に表示されているサービスアカウントのメールアドレスを追加し、\n"
            "「編集者」権限を付与してください。",
        )

        self._separator(f)

        self._url_button(f, "Google Driveを開く", "https://drive.google.com/")

        # Display service account email
        if self.service_account_email:
            email_frame = tk.Frame(f, bg="#e6f4ea", padx=8, pady=6)
            email_frame.pack(fill=tk.X, pady=6)
            tk.Label(
                email_frame, text="共有先メールアドレス（コピーして使用）:",
                font=("Helvetica", 9), bg="#e6f4ea", fg=C_TEXT_GRAY,
            ).pack(anchor="w")

            email_entry = tk.Entry(
                email_frame, font=("Helvetica", 10),
                readonlybackground="#e6f4ea", fg=C_SUCCESS, relief=tk.FLAT,
            )
            email_entry.insert(0, self.service_account_email)
            email_entry.configure(state="readonly")
            email_entry.pack(fill=tk.X, pady=(2, 0))
        else:
            self._paragraph(
                f,
                "（サービスアカウントのメールアドレスは\n"
                "　前のステップで設定すると表示されます）",
            )

        self._separator(f)

        # Folder ID entry
        id_row = tk.Frame(f, bg=C_WHITE)
        id_row.pack(fill=tk.X, pady=4)
        tk.Label(id_row, text="フォルダID:", font=("Helvetica", 10, "bold"),
                 bg=C_WHITE, fg=C_TEXT_DARK).pack(side=tk.LEFT)
        tk.Entry(id_row, textvariable=self.folder_id_var,
                 font=("Helvetica", 10), width=42).pack(side=tk.LEFT, padx=(8, 0))

        self._paragraph(
            f,
            "（URLの末尾の英数字部分を貼り付けてください。例: 1AbCdEfGhIjKlM...）",
        )

        # Checkbox
        chk = tk.Checkbutton(
            f, text="フォルダの共有設定が完了しました",
            variable=self.folder_shared_var,
            font=("Helvetica", 10), bg=C_WHITE, fg=C_TEXT_DARK,
            activebackground=C_WHITE, selectcolor=C_WHITE,
            cursor="hand2",
        )
        chk.pack(anchor="w", pady=(8, 4))

    def _build_step4(self) -> None:
        """Step 4: Configuration Input."""
        f = self.scroll_frame
        assert f is not None

        self._heading(f, "同期設定")
        self._paragraph(f, "同期先の情報とインストール先を設定してください。")
        self._separator(f)

        # NAS path
        tk.Label(f, text="NASパス:", font=("Helvetica", 10, "bold"),
                 bg=C_WHITE, fg=C_TEXT_DARK, anchor="w").pack(fill=tk.X, pady=(4, 2))
        nas_row = tk.Frame(f, bg=C_WHITE)
        nas_row.pack(fill=tk.X, pady=2)
        tk.Entry(nas_row, textvariable=self.nas_path_var,
                 font=("Helvetica", 10), width=40).pack(side=tk.LEFT)
        tk.Button(
            nas_row, text="参照...", font=("Helvetica", 9),
            command=lambda: self._browse_directory(self.nas_path_var),
            bg=C_WHITE, fg=C_TEXT_DARK, relief=tk.SOLID, borderwidth=1,
            padx=8, pady=2, cursor="hand2",
        ).pack(side=tk.LEFT, padx=(8, 0))
        self._paragraph(f, "NASのマウントパス (例: Z:\\ または \\\\192.168.1.100\\shared)")

        self._separator(f)

        # Sync interval
        tk.Label(f, text="同期間隔（分）:", font=("Helvetica", 10, "bold"),
                 bg=C_WHITE, fg=C_TEXT_DARK, anchor="w").pack(fill=tk.X, pady=(4, 2))
        interval_row = tk.Frame(f, bg=C_WHITE)
        interval_row.pack(fill=tk.X, pady=2)
        spinbox = ttk.Spinbox(
            interval_row, from_=5, to=60,
            textvariable=self.sync_interval_var,
            font=("Helvetica", 10), width=8,
        )
        spinbox.pack(side=tk.LEFT)
        tk.Label(interval_row, text="分ごとに同期", font=("Helvetica", 10),
                 bg=C_WHITE, fg=C_TEXT_GRAY).pack(side=tk.LEFT, padx=(8, 0))

        self._separator(f)

        # Share-with emails
        tk.Label(f, text="共有メールアドレス:", font=("Helvetica", 10, "bold"),
                 bg=C_WHITE, fg=C_TEXT_DARK, anchor="w").pack(fill=tk.X, pady=(4, 2))
        self._paragraph(
            f,
            "スプレッドシートを閲覧・編集できるユーザーのメールアドレスを\n"
            "1行につき1つ入力してください（空欄でも構いません）。",
        )
        self.share_emails_text = tk.Text(
            f, font=("Helvetica", 10), height=4, width=50,
            relief=tk.SOLID, borderwidth=1, bg=C_WHITE,
        )
        self.share_emails_text.pack(fill=tk.X, pady=4)
        # Add hint text
        self.share_emails_text.insert("1.0", "例:\nsales@example.com\nexecutive@example.com")
        self.share_emails_text.configure(fg=C_TEXT_GRAY)

        def _on_focus_in(event: tk.Event) -> None:  # type: ignore[type-arg]
            if self.share_emails_text.get("1.0", "end-1c").startswith("例:"):  # type: ignore[union-attr]
                self.share_emails_text.delete("1.0", tk.END)  # type: ignore[union-attr]
                self.share_emails_text.configure(fg=C_TEXT_DARK)  # type: ignore[union-attr]

        def _on_focus_out(event: tk.Event) -> None:  # type: ignore[type-arg]
            if not self.share_emails_text.get("1.0", "end-1c").strip():  # type: ignore[union-attr]
                self.share_emails_text.insert("1.0", "例:\nsales@example.com\nexecutive@example.com")  # type: ignore[union-attr]
                self.share_emails_text.configure(fg=C_TEXT_GRAY)  # type: ignore[union-attr]

        self.share_emails_text.bind("<FocusIn>", _on_focus_in)
        self.share_emails_text.bind("<FocusOut>", _on_focus_out)

        self._separator(f)

        # Install location
        tk.Label(f, text="インストール先:", font=("Helvetica", 10, "bold"),
                 bg=C_WHITE, fg=C_TEXT_DARK, anchor="w").pack(fill=tk.X, pady=(4, 2))
        install_row = tk.Frame(f, bg=C_WHITE)
        install_row.pack(fill=tk.X, pady=2)
        tk.Entry(install_row, textvariable=self.install_path_var,
                 font=("Helvetica", 10), width=40).pack(side=tk.LEFT)
        tk.Button(
            install_row, text="参照...", font=("Helvetica", 9),
            command=lambda: self._browse_directory(self.install_path_var),
            bg=C_WHITE, fg=C_TEXT_DARK, relief=tk.SOLID, borderwidth=1,
            padx=8, pady=2, cursor="hand2",
        ).pack(side=tk.LEFT, padx=(8, 0))
        self._paragraph(f, "システムファイルのインストール先フォルダ")

    def _browse_directory(self, var: tk.StringVar) -> None:
        """Open a folder browser dialog and update the given StringVar."""
        current = var.get()
        initial = current if Path(current).exists() else ""
        path = filedialog.askdirectory(
            title="フォルダを選択", initialdir=initial,
        )
        if path:
            var.set(path)

    def _build_step5(self) -> None:
        """Step 5: Installation (automated)."""
        f = self.scroll_frame
        assert f is not None

        self._heading(f, "インストール実行")
        self._paragraph(f, "「インストール開始」をクリックすると、自動的にセットアップが実行されます。")

        self._separator(f)

        # Progress bar
        self.progress_var.set(0)
        progress = ttk.Progressbar(
            f, variable=self.progress_var, maximum=100, length=540, mode="determinate",
        )
        progress.pack(fill=tk.X, pady=8)

        # Log area
        self.log_text = tk.Text(
            f, font=("Consolas", 9), height=10, width=65,
            bg="#1e1e1e", fg="#d4d4d4", relief=tk.SOLID, borderwidth=1,
            state=tk.DISABLED,
        )
        self.log_text.pack(fill=tk.X, pady=4)

        # Configure log text tags
        self.log_text.tag_configure("info", foreground="#d4d4d4")
        self.log_text.tag_configure("success", foreground=C_SUCCESS)
        self.log_text.tag_configure("warning", foreground=C_WARNING)
        self.log_text.tag_configure("error", foreground=C_ERROR)
        self.log_text.tag_configure("step", foreground="#569cd6", font=("Consolas", 9, "bold"))

        if not self.install_complete:
            self._action_button(f, "インストール開始", self._start_installation,
                                bg=C_SUCCESS, fg=C_WHITE)
            # Disable "Next" until installation completes
            self.btn_next.configure(state=tk.DISABLED)  # type: ignore[union-attr]
        else:
            self._log("インストールは完了済みです。", "success")
            self.btn_next.configure(state=tk.NORMAL)  # type: ignore[union-attr]

    def _log(self, message: str, tag: str = "info") -> None:
        """Append a message to the log text widget (thread-safe)."""
        def _do_log() -> None:
            if self.log_text is None:
                return
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n", tag)
            self.log_text.see(tk.END)
            self.log_text.configure(state=tk.DISABLED)

        self.root.after(0, _do_log)

    def _set_progress(self, value: float) -> None:
        """Set progress bar value (thread-safe)."""
        self.root.after(0, lambda: self.progress_var.set(value))

    def _start_installation(self) -> None:
        """Begin the installation process in a background thread."""
        self.installing = True
        self.btn_back.configure(state=tk.DISABLED)  # type: ignore[union-attr]
        self.btn_next.configure(state=tk.DISABLED)  # type: ignore[union-attr]

        thread = threading.Thread(target=self._run_installation, daemon=True)
        thread.start()

    def _run_installation(self) -> None:
        """Execute installation steps (runs in background thread)."""
        install_dir = Path(self.install_path_var.get().strip())
        total_steps = 7
        errors: list[str] = []

        def _progress(step: int) -> None:
            self._set_progress((step / total_steps) * 100)

        # ------ Step 1: Create directory ------
        self._log("[1/7] インストールディレクトリ作成...", "step")
        try:
            install_dir.mkdir(parents=True, exist_ok=True)
            (install_dir / "config").mkdir(exist_ok=True)
            (install_dir / "logs").mkdir(exist_ok=True)
            self._log(f"  作成完了: {install_dir}", "success")
        except OSError as e:
            self._log(f"  エラー: {e}", "error")
            errors.append(f"ディレクトリ作成失敗: {e}")
            self._finish_installation(False, errors)
            return
        _progress(1)

        # ------ Step 2: Copy project files ------
        self._log("[2/7] プロジェクトファイルをコピー中...", "step")
        try:
            self._copy_project_files(PROJECT_ROOT, install_dir)
            self._log("  コピー完了", "success")
        except (OSError, shutil.Error) as e:
            self._log(f"  エラー: {e}", "error")
            errors.append(f"ファイルコピー失敗: {e}")
            self._finish_installation(False, errors)
            return
        _progress(2)

        # ------ Step 3: Create config.yaml ------
        self._log("[3/7] config.yaml を作成中...", "step")
        try:
            self._create_config_yaml(install_dir)
            self._log("  設定ファイル作成完了", "success")
        except OSError as e:
            self._log(f"  エラー: {e}", "error")
            errors.append(f"設定ファイル作成失敗: {e}")
        _progress(3)

        # ------ Step 4: Copy service account JSON ------
        self._log("[4/7] サービスアカウントキーをコピー中...", "step")
        try:
            dest_json = install_dir / "config" / "service_account.json"
            shutil.copy2(self.json_key_path, dest_json)
            self._log(f"  コピー完了: {dest_json}", "success")
        except (OSError, shutil.Error) as e:
            self._log(f"  エラー: {e}", "error")
            errors.append(f"キーファイルコピー失敗: {e}")
        _progress(4)

        # ------ Step 5: Create venv ------
        self._log("[5/7] Python仮想環境を作成中...", "step")
        self._log("  （少し時間がかかります）", "info")
        try:
            venv_path = install_dir / ".venv"
            result = subprocess.run(
                [sys.executable, "-m", "venv", str(venv_path)],
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr)
            self._log("  仮想環境作成完了", "success")
        except (subprocess.SubprocessError, RuntimeError, OSError) as e:
            self._log(f"  エラー: {e}", "error")
            errors.append(f"仮想環境作成失敗: {e}")
        _progress(5)

        # ------ Step 6: Install dependencies ------
        self._log("[6/7] 依存パッケージをインストール中...", "step")
        self._log("  （数分かかる場合があります）", "info")
        try:
            # Determine pip executable path (Windows vs. Unix)
            if sys.platform == "win32":
                pip_exe = install_dir / ".venv" / "Scripts" / "pip.exe"
            else:
                pip_exe = install_dir / ".venv" / "bin" / "pip"

            req_file = install_dir / "requirements.txt"
            if pip_exe.exists() and req_file.exists():
                result = subprocess.run(
                    [str(pip_exe), "install", "-r", str(req_file)],
                    capture_output=True, text=True, timeout=600,
                )
                if result.returncode != 0:
                    self._log(f"  pip出力: {result.stderr[:500]}", "warning")
                    raise RuntimeError(
                        f"pip install 失敗 (exit code {result.returncode})"
                    )
                self._log("  依存パッケージインストール完了", "success")
            else:
                if not pip_exe.exists():
                    self._log(f"  警告: pipが見つかりません: {pip_exe}", "warning")
                if not req_file.exists():
                    self._log(f"  警告: requirements.txtが見つかりません: {req_file}", "warning")
                errors.append("pipまたはrequirements.txtが見つかりません")
        except (subprocess.SubprocessError, RuntimeError, OSError) as e:
            self._log(f"  エラー: {e}", "error")
            errors.append(f"依存パッケージインストール失敗: {e}")
        _progress(6)

        # ------ Step 7: Create logs directory (ensure) ------
        self._log("[7/7] ログディレクトリを確認中...", "step")
        try:
            (install_dir / "logs").mkdir(exist_ok=True)
            self._log("  完了", "success")
        except OSError as e:
            self._log(f"  エラー: {e}", "error")
            errors.append(f"ログディレクトリ作成失敗: {e}")
        _progress(7)

        # ------ Done ------
        success = len(errors) == 0
        self._finish_installation(success, errors)

    def _copy_project_files(self, src_root: Path, dest_root: Path) -> None:
        """Copy project files from source to destination, skipping excluded items."""
        for item_rel in COPY_ITEMS:
            src_path = src_root / item_rel
            dest_path = dest_root / item_rel

            if not src_path.exists():
                self._log(f"  スキップ（存在しない）: {item_rel}", "warning")
                continue

            if src_path.is_dir():
                self._copy_directory(src_path, dest_path)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dest_path)
                self._log(f"  コピー: {item_rel}", "info")

    def _copy_directory(self, src_dir: Path, dest_dir: Path) -> None:
        """Recursively copy a directory, skipping patterns in SKIP_PATTERNS."""
        dest_dir.mkdir(parents=True, exist_ok=True)
        for item in src_dir.iterdir():
            rel_name = item.name
            if rel_name in SKIP_PATTERNS:
                continue
            dest_item = dest_dir / rel_name
            if item.is_dir():
                self._copy_directory(item, dest_item)
            else:
                shutil.copy2(item, dest_item)

    def _create_config_yaml(self, install_dir: Path) -> None:
        """Generate config.yaml from user inputs."""
        nas_path = self.nas_path_var.get().strip()
        folder_id = self.folder_id_var.get().strip()
        interval = self.sync_interval_var.get()

        # Parse share-with emails
        share_emails: list[str] = []
        if self.share_emails_text is not None:
            raw_text = self.share_emails_text.get("1.0", "end-1c").strip()
            if raw_text and not raw_text.startswith("例:"):
                for line in raw_text.splitlines():
                    email = line.strip()
                    if email and re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                        share_emails.append(email)

        # Build share_with YAML block
        if share_emails:
            share_lines = "\n".join(f'    - "{e}"' for e in share_emails)
            share_with_yaml = f"  share_with:\n{share_lines}"
        else:
            share_with_yaml = "  share_with: []"

        # Escape backslashes for YAML string
        nas_path_escaped = nas_path.replace("\\", "\\\\")

        config_content = (
            f'nas:\n'
            f'  base_path: "{nas_path_escaped}"\n'
            f'  file_patterns:\n'
            f'    - "*.xlsx"\n'
            f'  exclude_patterns:\n'
            f'    - "~$*"\n'
            f'    - "*.tmp"\n'
            f'    - ".~lock*"\n'
            f'\n'
            f'google:\n'
            f'  credentials_path: "./config/service_account.json"\n'
            f'  drive_folder_id: "{folder_id}"\n'
            f'{share_with_yaml}\n'
            f'\n'
            f'sync:\n'
            f'  interval_minutes: {interval}\n'
            f'\n'
            f'logging:\n'
            f'  level: "INFO"\n'
            f'  file: "./logs/tamatex.log"\n'
            f'  max_size_mb: 10\n'
            f'  backup_count: 5\n'
        )

        config_path = install_dir / "config" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(config_content, encoding="utf-8")

    def _finish_installation(self, success: bool, errors: list[str]) -> None:
        """Finalize the installation process."""
        self.installing = False
        self.install_complete = success

        if success:
            self._log("\n=============================", "success")
            self._log("  インストール完了!", "success")
            self._log("=============================\n", "success")
        else:
            self._log("\n=============================", "error")
            self._log("  インストール中にエラーが発生しました", "error")
            for err in errors:
                self._log(f"  - {err}", "error")
            self._log("=============================\n", "error")

        # Re-enable navigation
        def _enable_nav() -> None:
            self.btn_back.configure(state=tk.NORMAL)  # type: ignore[union-attr]
            if success:
                self.btn_next.configure(state=tk.NORMAL)  # type: ignore[union-attr]

        self.root.after(0, _enable_nav)

    def _build_step6(self) -> None:
        """Step 6: Complete."""
        f = self.scroll_frame
        assert f is not None

        install_dir = self.install_path_var.get().strip()

        self._heading(f, "セットアップが完了しました")
        self._paragraph(
            f,
            "tamatex Excel同期システムのインストールが完了しました。\n"
            "以下の情報をご確認ください。",
        )

        self._separator(f)

        # Summary
        self._heading(f, "インストール概要")

        summary_frame = tk.Frame(f, bg=C_BG_LIGHT, padx=12, pady=8)
        summary_frame.pack(fill=tk.X, pady=4)

        summary_items = [
            ("インストール先", install_dir),
            ("NASパス", self.nas_path_var.get()),
            ("同期間隔", f"{self.sync_interval_var.get()} 分"),
            ("DriveフォルダID", self.folder_id_var.get()),
            ("サービスアカウント", self.service_account_email),
        ]

        for label, value in summary_items:
            row = tk.Frame(summary_frame, bg=C_BG_LIGHT)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=f"{label}:", font=("Helvetica", 9, "bold"),
                     bg=C_BG_LIGHT, fg=C_TEXT_DARK, width=18, anchor="e"
                     ).pack(side=tk.LEFT)
            tk.Label(row, text=value, font=("Helvetica", 9),
                     bg=C_BG_LIGHT, fg=C_TEXT_GRAY, anchor="w"
                     ).pack(side=tk.LEFT, padx=(8, 0))

        self._separator(f)

        # Service start button
        self._heading(f, "同期サービスの開始")
        self._paragraph(
            f,
            "下のボタンをクリックすると、NSSMを使用して同期サービスを\n"
            "Windowsサービスとして登録・起動します。\n\n"
            "NSSMがインストールされていない場合は、手動で以下のコマンドを\n"
            "実行してください:",
        )

        # Manual command display
        cmd_frame = tk.Frame(f, bg="#1e1e1e", padx=8, pady=6)
        cmd_frame.pack(fill=tk.X, pady=4)

        if sys.platform == "win32":
            python_exe = f"{install_dir}\\.venv\\Scripts\\python.exe"
        else:
            python_exe = f"{install_dir}/.venv/bin/python"

        cmd_text = (
            f"cd {install_dir}\n"
            f"{python_exe} -m tamatex.main"
        )

        cmd_label = tk.Label(
            cmd_frame, text=cmd_text, font=("Consolas", 9),
            bg="#1e1e1e", fg="#d4d4d4", justify=tk.LEFT, anchor="w",
        )
        cmd_label.pack(anchor="w")

        self._action_button(
            f, "同期サービスを開始",
            self._start_service,
            bg=C_SUCCESS, fg=C_WHITE,
        )

        self._separator(f)

        self._paragraph(
            f,
            "セットアップウィザードは「閉じる」ボタンで終了できます。\n"
            "お疲れさまでした!",
        )

    def _start_service(self) -> None:
        """Attempt to register and start the service using NSSM, or show manual instructions."""
        install_dir = Path(self.install_path_var.get().strip())

        if sys.platform == "win32":
            python_exe = install_dir / ".venv" / "Scripts" / "python.exe"
        else:
            python_exe = install_dir / ".venv" / "bin" / "python"

        # Try NSSM first (Windows only)
        if sys.platform == "win32":
            nssm_path = shutil.which("nssm")
            if nssm_path:
                try:
                    subprocess.run(
                        [
                            nssm_path, "install", "tamatex",
                            str(python_exe), "-m", "tamatex.main",
                        ],
                        check=True, capture_output=True, text=True,
                    )
                    subprocess.run(
                        [nssm_path, "set", "tamatex", "AppDirectory", str(install_dir)],
                        check=True, capture_output=True, text=True,
                    )
                    subprocess.run(
                        [nssm_path, "start", "tamatex"],
                        check=True, capture_output=True, text=True,
                    )
                    messagebox.showinfo(
                        "成功",
                        "tamatex同期サービスを登録・起動しました。\n"
                        "Windows起動時に自動的に実行されます。",
                    )
                    return
                except (subprocess.SubprocessError, OSError) as e:
                    messagebox.showwarning(
                        "NSSM登録失敗",
                        f"NSSMでのサービス登録に失敗しました。\n\n"
                        f"エラー: {e}\n\n"
                        f"管理者権限で実行するか、手動でサービスを登録してください。",
                    )
                    return
            else:
                messagebox.showinfo(
                    "手動設定が必要",
                    "NSSMが見つかりませんでした。\n\n"
                    "手動でサービスを登録するか、以下のコマンドで直接実行できます:\n\n"
                    f"cd {install_dir}\n"
                    f"{python_exe} -m tamatex.main\n\n"
                    "NSSMのインストール: https://nssm.cc/download",
                )
        else:
            # Non-Windows: just show the command
            messagebox.showinfo(
                "手動実行",
                f"以下のコマンドで同期を開始できます:\n\n"
                f"cd {install_dir}\n"
                f"{python_exe} -m tamatex.main",
            )

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Start the Tkinter main loop."""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Launch the installer wizard."""
    app = InstallerWizard()
    app.run()


if __name__ == "__main__":
    main()
