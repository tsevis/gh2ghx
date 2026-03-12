"""Theme helpers for a minimal macOS-first Tkinter UI."""

from __future__ import annotations

import platform


def is_macos() -> bool:
    return platform.system() == "Darwin"


MACOS_PALETTE = {
    "window_bg": "systemWindowBackgroundColor",
    "card_bg": "systemWindowBackgroundColor",
    "text": "systemTextColor",
    "muted": "systemSecondaryLabelColor",
    "entry_bg": "systemTextBackgroundColor",
    "entry_fg": "systemTextColor",
    "status_ok": "systemGreenColor",
    "status_warn": "systemOrangeColor",
    "status_err": "systemRedColor",
}

FALLBACK_LIGHT = {
    "window_bg": "#f4f4f6",
    "card_bg": "#ffffff",
    "text": "#111216",
    "muted": "#61656f",
    "entry_bg": "#ffffff",
    "entry_fg": "#1a1a1a",
    "status_ok": "#0c8f3e",
    "status_warn": "#b06a00",
    "status_err": "#c0392b",
}

FALLBACK_DARK = {
    "window_bg": "#1f2128",
    "card_bg": "#2a2d36",
    "text": "#f2f4f8",
    "muted": "#b3b8c4",
    "entry_bg": "#151821",
    "entry_fg": "#f2f4f8",
    "status_ok": "#5ad98f",
    "status_warn": "#f5c26b",
    "status_err": "#ff8577",
}


def get_palette(mode: str) -> dict[str, str]:
    if is_macos():
        return MACOS_PALETTE
    if mode == "dark":
        return FALLBACK_DARK
    return FALLBACK_LIGHT
