"""Global hotkey manager for Windows — reliable message-window approach."""
import ctypes
import threading
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
WM_HOTKEY = 0x0312
PM_REMOVE = 0x0001
ERROR_HOTKEY_ALREADY_REGISTERED = 1409

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
}

for i in range(1, 13):
    SPECIAL_KEYS[f"f{i}"] = 0x6F + i

class _MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


def parse_hotkey(hotkey_str: str) -> tuple[int, int]:
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
    if mods == 0:
        raise ValueError("Hotkey needs at least one modifier (ctrl, alt, shift, win)")
    return mods, vk


def _get_last_error() -> int:
    return kernel32.GetLastError()


_message_hwnd: int | None = None

def create_message_window() -> int:
    """Create invisible message-only window to receive WM_HOTKEY."""
    global _message_hwnd
    if _message_hwnd and user32.IsWindow(_message_hwnd):
        return _message_hwnd

    # HWND_MESSAGE = (HWND)(-3) — receives messages without showing a window
    hwnd_message = wintypes.HWND(-3)

    hwnd = user32.CreateWindowExW(
        0,
        "Static",
        "PCCleanerMacroHotkeys",
        0,
        0, 0, 0, 0,
        hwnd_message,
        0,
        kernel32.GetModuleHandleW(None),
        None,
    )
    if not hwnd:
        raise OSError(f"CreateWindowEx failed: {_get_last_error()}")

    _message_hwnd = hwnd
    return hwnd


class HotkeyManager:
    """Registers global hotkeys via RegisterHotKey + WM_HOTKEY polling."""

    def __init__(self, hwnd: int, on_trigger: callable):
        self.hwnd = hwnd
        self.on_trigger = on_trigger
        self._map: dict[int, tuple[str, str]] = {}
        self._hotkey_to_id: dict[str, int] = {}
        self._next_id = 1
        self._errors: list[str] = []
        self._lock = threading.Lock()

    @property
    def errors(self) -> list[str]:
        return list(self._errors)

    @property
    def registered_count(self) -> int:
        return len(self._map)

    def register(self, macro_id: str, hotkey_str: str) -> bool:
        hotkey_str = hotkey_str.strip().lower()
        if hotkey_str in self._hotkey_to_id:
            self._errors.append(f"Duplicate hotkey: {hotkey_str}")
            return False
        try:
            mods, vk = parse_hotkey(hotkey_str)
        except ValueError as e:
            self._errors.append(str(e))
            return False

        hid = self._next_id
        self._next_id += 1

        if not user32.RegisterHotKey(self.hwnd, hid, mods, vk):
            err = _get_last_error()
            if err == ERROR_HOTKEY_ALREADY_REGISTERED:
                self._errors.append(f"Hotkey already in use by another app: {hotkey_str}")
            else:
                self._errors.append(f"Failed to register {hotkey_str} (error {err})")
            return False

        self._map[hid] = (macro_id, hotkey_str)
        self._hotkey_to_id[hotkey_str] = hid
        return True

    def unregister_all(self):
        for hid in list(self._map):
            user32.UnregisterHotKey(self.hwnd, hid)
        self._map.clear()
        self._hotkey_to_id.clear()

    def reload(self, macros) -> tuple[int, list[str]]:
        with self._lock:
            self._errors.clear()
            self.unregister_all()
            count = 0
            for macro in macros:
                if not macro.enabled or macro.trigger != "hotkey":
                    continue
                hotkey = macro.trigger_params.get("hotkey", "").strip().lower()
                if hotkey and self.register(macro.id, hotkey):
                    count += 1
            return count, self._errors

    def poll(self):
        """Only remove WM_HOTKEY messages — won't break tkinter."""
        msg = _MSG()
        while user32.PeekMessageW(
            ctypes.byref(msg), self.hwnd, WM_HOTKEY, WM_HOTKEY, PM_REMOVE
        ):
            hid = msg.wParam
            if hid in self._map:
                macro_id, hotkey = self._map[hid]
                try:
                    self.on_trigger(macro_id, hotkey)
                except Exception:
                    pass