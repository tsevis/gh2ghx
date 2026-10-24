"""Tkinter GUI for GH to GHX conversion."""

from __future__ import annotations

from pathlib import Path

import logging
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from gh2ghx.converter import convert_gh_to_ghx
from gh2ghx.theme import get_palette, is_macos

logger = logging.getLogger(__name__)

ICON_PATH = Path(__file__).resolve().parent / "assets" / "icons" / "AppIcon-256.png"


class Gh2GhxWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("GH to GHX Converter")
        self.root.geometry("760x340")
        self.root.minsize(700, 320)

        self.style = ttk.Style(self.root)
        if is_macos():
            self.style.theme_use("aqua")
        else:
            self.style.theme_use("clam")

        self.mode = "light"
        self.palette = get_palette(self.mode)
        self._appearance = "auto"

        self.source_var = tk.StringVar()
        self.target_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Select a .gh file to begin.")

        self._build_ui()
        self._apply_palette()

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        header = ttk.Frame(self.root, style="TFrame", padding=(20, 14))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="GH to GHX Converter", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Convert Grasshopper .gh files into XML-readable .ghx output.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.appearance_btn = ttk.Button(header, text="Dark Mode", command=self.toggle_appearance)
        self.appearance_btn.grid(row=0, column=1, rowspan=2, sticky="ne", padx=(0, 4))

        ttk.Separator(self.root, orient="horizontal").grid(row=1, column=0, sticky="ew")

        content = ttk.Frame(self.root, style="TFrame", padding=(20, 16, 20, 16))
        content.grid(row=2, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        card = ttk.Frame(content, style="Card.TFrame", padding=14)
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(1, weight=1)

        ttk.Label(card, text="Source (.gh)").grid(row=0, column=0, sticky="w", pady=(2, 10), padx=(2, 10))
        ttk.Entry(card, textvariable=self.source_var).grid(row=0, column=1, sticky="ew", pady=(2, 10))
        ttk.Button(card, text="Browse", command=self._pick_source).grid(row=0, column=2, padx=(10, 0), pady=(2, 10))

        ttk.Label(card, text="Output (.ghx)").grid(row=1, column=0, sticky="w", pady=(2, 10), padx=(2, 10))
        ttk.Entry(card, textvariable=self.target_var).grid(row=1, column=1, sticky="ew", pady=(2, 10))
        ttk.Button(card, text="Browse", command=self._pick_target).grid(row=1, column=2, padx=(10, 0), pady=(2, 10))

        ttk.Button(card, text="Convert", style="Accent.TButton", command=self.convert).grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=(6, 8)
        )

        self.status_label = ttk.Label(card, textvariable=self.status_var, style="Status.TLabel", anchor="w")
        self.status_label.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(4, 2))

    def _apply_palette(self) -> None:
        p = self.palette
        self.root.configure(bg=p["window_bg"])
        try:
            self.root.tk_setPalette(
                background=p["window_bg"],
                foreground=p["text"],
                activeBackground=p["card_bg"],
                activeForeground=p["text"],
            )
        except tk.TclError:
            pass

        self.style.configure("TFrame", background=p["window_bg"])
        self.style.configure("Card.TFrame", background=p["card_bg"])
        self.style.configure("TLabel", background=p["window_bg"], foreground=p["text"])
        self.style.configure("Title.TLabel", background=p["window_bg"], foreground=p["text"], font=("SF Pro", 19, "bold"))
        self.style.configure("Muted.TLabel", background=p["window_bg"], foreground=p["muted"], font=("SF Pro", 12))
        self.style.configure("Status.TLabel", background=p["card_bg"], foreground=p["muted"], font=("SF Pro", 11))
        self.style.configure("TButton", padding=(10, 6), background=p["card_bg"], foreground=p["text"])
        self.style.map(
            "TButton",
            background=[("active", p["window_bg"])],
            foreground=[("disabled", p["muted"]), ("active", p["text"])],
        )
        self.style.configure("Accent.TButton", padding=(10, 7), background=p["card_bg"], foreground=p["text"])
        self.style.configure("TEntry", fieldbackground=p["entry_bg"], foreground=p["entry_fg"])
        self.style.map(
            "TEntry",
            fieldbackground=[("readonly", p["entry_bg"]), ("disabled", p["entry_bg"])],
            foreground=[("disabled", p["muted"])],
        )

    def toggle_appearance(self) -> None:
        if is_macos():
            try:
                if self._appearance in ("auto", "aqua"):
                    self.root.tk.call(
                        "::tk::unsupported::MacWindowStyle",
                        "appearance",
                        ".",
                        "darkaqua",
                    )
                    self._appearance = "darkaqua"
                    self.mode = "dark"
                    self.appearance_btn.configure(text="Light Mode")
                else:
                    self.root.tk.call(
                        "::tk::unsupported::MacWindowStyle",
                        "appearance",
                        ".",
                        "aqua",
                    )
                    self._appearance = "aqua"
                    self.mode = "light"
                    self.appearance_btn.configure(text="Dark Mode")
            except tk.TclError:
                self.mode = "dark" if self.mode == "light" else "light"
                self.appearance_btn.configure(text="Light Mode" if self.mode == "dark" else "Dark Mode")
        else:
            self.mode = "dark" if self.mode == "light" else "light"
            self.appearance_btn.configure(text="Light Mode" if self.mode == "dark" else "Dark Mode")
        self.palette = get_palette(self.mode)
        self._apply_palette()

    def _pick_source(self) -> None:
        path = filedialog.askopenfilename(
            title="Select .gh file",
            filetypes=[("Grasshopper GH", "*.gh"), ("All files", "*.*")],
        )
        if not path:
            return
        self.source_var.set(path)
        source = Path(path)
        if not self.target_var.get().strip():
            self.target_var.set(str(source.with_suffix(".ghx")))

    def _pick_target(self) -> None:
        suggested = Path(self.source_var.get() or "converted.ghx").with_suffix(".ghx")
        path = filedialog.asksaveasfilename(
            title="Choose .ghx output",
            defaultextension=".ghx",
            initialfile=suggested.name,
            filetypes=[("Grasshopper GHX", "*.ghx"), ("All files", "*.*")],
        )
        if path:
            self.target_var.set(path)

    def _set_status(self, text: str, level: str = "muted") -> None:
        color_key = {"ok": "status_ok", "warn": "status_warn", "err": "status_err"}.get(level, "muted")
        self.style.configure("Status.TLabel", foreground=self.palette[color_key], background=self.palette["card_bg"])
        self.status_var.set(text)

    def convert(self) -> None:
        source_text = self.source_var.get().strip()
        target_text = self.target_var.get().strip()
        if not source_text:
            self._set_status("Please choose a source .gh file.", "err")
            return
        if not target_text:
            self._set_status("Please choose an output .ghx file.", "err")
            return

        source = Path(source_text)
        target = Path(target_text)
        if source.suffix.lower() != ".gh":
            if not messagebox.askyesno(
                "Continue?",
                "Source file does not have a .gh extension. Continue anyway?",
            ):
                self._set_status("Conversion cancelled.", "warn")
                return

        try:
            reconstructed, message = convert_gh_to_ghx(source, target)
        except Exception as exc:
            self._set_status(f"Conversion failed: {exc}", "err")
            return

        if reconstructed:
            self._set_status(f"Success: {message}", "ok")
        else:
            self._set_status(f"Partial: {message}", "warn")


def _set_app_icon(root: tk.Tk) -> None:
    """Set the window icon; a missing file costs only the icon."""
    try:
        root.iconphoto(True, tk.PhotoImage(master=root, file=str(ICON_PATH)))
    except (tk.TclError, OSError):
        logger.warning("Could not load app icon from %s", ICON_PATH)


def run() -> None:
    root = tk.Tk()
    _set_app_icon(root)
    Gh2GhxWindow(root)
    root.mainloop()
