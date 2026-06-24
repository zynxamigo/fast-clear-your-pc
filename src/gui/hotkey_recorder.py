"""Dialog to record keyboard shortcuts."""
import tkinter as tk
from tkinter import ttk

SYMBOL_TO_KEY = {
    "space": "space",
    "return": "enter",
    "escape": "esc",
    "left": "left",
    "right": "right",
    "up": "up",
    "down": "down",
    "prior": "pageup",
    "next": "pagedown",
    "home": "home",
    "end": "end",
    "insert": "insert",
    "delete": "delete",
    "tab": "tab",
}

IGNORE_KEYS = {
    "control_l", "control_r", "alt_l", "alt_r", "shift_l", "shift_r",
    "win_l", "win_r", "super_l", "super_r", "caps_lock", "num_lock",
}


class HotkeyRecorder(tk.Toplevel):
    """Capture a key combination like ctrl+alt+right."""

    def __init__(self, parent, title: str, hint: str, on_recorded: callable):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.on_recorded = on_recorded
        self.transient(parent)
        self.grab_set()

        ttk.Label(self, text=hint, padding=12).pack()
        self.display = ttk.Label(self, text="...", font=("Consolas", 12), padding=8)
        self.display.pack()
        ttk.Button(self, text="Cancel", command=self.destroy).pack(pady=8)

        self.bind("<KeyPress>", self._on_key)
        self.focus_force()

    def _on_key(self, event):
        mods = []
        state = event.state
        if state & 0x0004:
            mods.append("ctrl")
        if state & 0x0008 or state & 0x20000:
            mods.append("alt")
        if state & 0x0001:
            mods.append("shift")
        if state & 0x0040 or state & 0x00080:
            mods.append("win")

        key = event.keysym.lower()
        if key in IGNORE_KEYS:
            self.display.config(text="+".join(mods + ["..."]) if mods else "...")
            return "break"

        if len(key) == 1:
            key_name = key
        else:
            key_name = SYMBOL_TO_KEY.get(key, key)

        if not mods:
            self.display.config(text=f"Need modifier + {key_name}")
            return "break"

        combo = "+".join(mods + [key_name])
        self.display.config(text=combo)
        self.on_recorded(combo)
        self.destroy()
        return "break"