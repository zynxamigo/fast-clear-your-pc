"""Global hotkey manager for Windows."""
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
WM_HOTKEY = 0x0312

MODIFIER_NAMES = {
    "alt": MOD_ALT,
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "windows": MOD_WIN,
}

SPECIAL_KEYS = {
    "space": 0x20,
    "enter": 0x0D,
    "return": 0x0D,
    "tab": 0x09,
    "escape": 0x1B,
    "esc": 0x1B,
    "backspace": 0x08,
    "delete": 0x2E,
    "del": 0x2E,
    "insert": 0x2D,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
    "media_next": 0xB0,
    "media_prev": 0xB1,
    "media_play": 0xB3,
    "media_stop": 0xB2,
    "volume_up": 0xAF,
    "volume_down": 0xAE,
    "volume_mute": 0xAD,
}

for i in range(1, 13):
    SPECIAL_KEYS[f"f{i}"] = 0x6F + i


def parse_hotkey(hotkey_str: str) -> tuple[int, int]:
    """Parse 'ctrl+alt+right' -> (modifiers, virtual_key)."""
    parts = [p.strip().lower() for p in hotkey_str.replace("-", "+").split("+") if p.strip()]
    if not parts:
        raise ValueError("Empty hotkey")

    mods = 0
    vk = None
    for part in parts:
        if part in MODIFIER_NAMES:
            mods |= MODIFIER_NAMES[part]
        elif len(part) == 1 and part.isalnum():
            vk = ord(part.upper())
        elif part in SPECIAL_KEYS:
            vk = SPECIAL_KEYS[part]
        else:
            raise ValueError(f"Unknown key: {part}")

    if vk is None:
        raise ValueError(f"Missing key in hotkey: {hotkey_str}")
    if mods == 0 and len(parts) == 1:
        raise ValueError("Hotkey needs at least one modifier (ctrl, alt, shift, win)")
    return mods, vk


def format_hotkey(mods: int, vk: int) -> str:
    """Format modifiers+vk as human-readable string."""
    names = []
    if mods & MOD_CONTROL:
        names.append("ctrl")
    if mods & MOD_ALT:
        names.append("alt")
    if mods & MOD_SHIFT:
        names.append("shift")
    if mods & MOD_WIN:
        names.append("win")

    vk_to_name = {v: k for k, v in SPECIAL_KEYS.items()}
    if vk in vk_to_name:
        names.append(vk_to_name[vk])
    elif 0x41 <= vk <= 0x5A:
        names.append(chr(vk).lower())
    elif 0x30 <= vk <= 0x39:
        names.append(chr(vk))
    else:
        names.append(f"vk{vk}")
    return "+".join(names)


def get_tk_hwnd(root) -> int:
    """Get proper HWND for RegisterHotKey on tkinter Windows."""
    try:
        wid = root.winfo_id()
        parent = user32.GetParent(wid)
        return parent if parent else wid
    except Exception:
        return root.winfo_id()


class HotkeyManager:
    """Registers global hotkeys and polls WM_HOTKEY messages."""

    def __init__(self, hwnd: int, on_trigger: callable):
        self.hwnd = hwnd
        self.on_trigger = on_trigger
        self._map: dict[int, tuple[str, str]] = {}
        self._next_id = 1

    def register(self, macro_id: str, hotkey_str: str) -> bool:
        try:
            mods, vk = parse_hotkey(hotkey_str)
        except ValueError:
            return False
        hid = self._next_id
        self._next_id += 1
        if not user32.RegisterHotKey(self.hwnd, hid, mods, vk):
            return False
        self._map[hid] = (macro_id, hotkey_str)
        return True

    def unregister_all(self):
        for hid in list(self._map):
            user32.UnregisterHotKey(self.hwnd, hid)
        self._map.clear()

    def reload(self, macros):
        self.unregister_all()
        for macro in macros:
            if not macro.enabled or macro.trigger != "hotkey":
                continue
            hotkey = macro.trigger_params.get("hotkey", "")
            if hotkey:
                self.register(macro.id, hotkey)

    def poll(self):
        msg = wintypes.MSG()
        while user32.PeekMessageW(ctypes.byref(msg), self.hwnd, 0, 0, 1):
            if msg.message == WM_HOTKEY:
                hid = msg.wParam
                if hid in self._map:
                    macro_id, hotkey = self._map[hid]
                    self.on_trigger(macro_id, hotkey)

    def get_hotkey_for_macro(self, macro_id: str) -> str | None:
        for _, (mid, hk) in self._map.items():
            if mid == macro_id:
                return hk
        return None