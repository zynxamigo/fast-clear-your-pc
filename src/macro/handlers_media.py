"""Media & Spotify macro handlers."""
import ctypes
import os
import subprocess
import time

user32 = ctypes.windll.user32

VK_MEDIA_NEXT = 0xB0
VK_MEDIA_PREV = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_VOLUME_UP = 0xAF
VK_VOLUME_DOWN = 0xAE

KEYEVENTF_KEYUP = 0x0002


def _press_vk(vk: int):
    user32.keybd_event(vk, 0, 0, 0)
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


def _send_keys_combo(keys: str):
    """Send keys using WScript.Shell SendKeys syntax or human combo."""
    if "+" in keys and not keys.startswith("+"):
        from .hotkeys import MODIFIER_NAMES, SPECIAL_KEYS, parse_hotkey
        try:
            mods, vk = parse_hotkey(keys)
            # Hold modifiers
            mod_vks = []
            if mods & 0x0002:
                mod_vks.append(0x11)  # VK_CONTROL
            if mods & 0x0001:
                mod_vks.append(0x12)  # VK_MENU (alt)
            if mods & 0x0004:
                mod_vks.append(0x10)  # VK_SHIFT
            for mv in mod_vks:
                user32.keybd_event(mv, 0, 0, 0)
            user32.keybd_event(vk, 0, 0, 0)
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
            for mv in reversed(mod_vks):
                user32.keybd_event(mv, 0, KEYEVENTF_KEYUP, 0)
            return
        except ValueError:
            pass
    subprocess.run(
        ["powershell", "-Command", f'$w=New-Object -ComObject WScript.Shell;$w.SendKeys("{keys}")'],
        capture_output=True, timeout=15,
    )


def _find_spotify() -> str | None:
    local = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        os.path.join(local, "Microsoft", "WindowsApps", "Spotify.exe"),
        os.path.join(os.environ.get("APPDATA", ""), "Spotify", "Spotify.exe"),
        r"C:\Users\%USERNAME%\AppData\Roaming\Spotify\Spotify.exe",
    ]
    for c in candidates:
        expanded = os.path.expandvars(c)
        if os.path.exists(expanded):
            return expanded
    return "spotify:"


def _focus_spotify():
    self_ps = """
    $p = Get-Process Spotify -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
    if ($p) {
        $sig = '[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);'
        Add-Type -MemberDefinition $sig -Name Win -Namespace Native
        [Native.Win]::SetForegroundWindow($p.MainWindowHandle)
        return $true
    }
    return $false
    """
    r = subprocess.run(["powershell", "-Command", self_ps], capture_output=True, timeout=10, text=True)
    return "True" in r.stdout


class MediaMacroMixin:
    """Spotify, media keys and hotkey send handlers."""

    def _act_spotify_next(self, p):
        _press_vk(VK_MEDIA_NEXT)
        return "Spotify: next track"

    def _act_spotify_previous(self, p):
        _press_vk(VK_MEDIA_PREV)
        return "Spotify: previous track"

    def _act_spotify_play_pause(self, p):
        _press_vk(VK_MEDIA_PLAY_PAUSE)
        return "Spotify: play/pause"

    def _act_spotify_open(self, p):
        path = p.get("path") or _find_spotify()
        os.startfile(path)
        return f"Spotify opened: {path}"

    def _act_spotify_next_focused(self, p):
        if _focus_spotify():
            time.sleep(0.15)
            _send_keys_combo("ctrl+right")
        else:
            _press_vk(VK_MEDIA_NEXT)
        return "Spotify: next (focused)"

    def _act_spotify_previous_focused(self, p):
        if _focus_spotify():
            time.sleep(0.15)
            _send_keys_combo("ctrl+left")
        else:
            _press_vk(VK_MEDIA_PREV)
        return "Spotify: previous (focused)"

    def _act_spotify_play_focused(self, p):
        if _focus_spotify():
            time.sleep(0.15)
            _send_keys_combo(" ")
        else:
            _press_vk(VK_MEDIA_PLAY_PAUSE)
        return "Spotify: play/pause (focused)"

    def _act_spotify_like(self, p):
        if _focus_spotify():
            time.sleep(0.15)
            _send_keys_combo("ctrl+l")
            return "Spotify: like song"
        return "Spotify not running"

    def _act_spotify_shuffle(self, p):
        if _focus_spotify():
            time.sleep(0.15)
            _send_keys_combo("ctrl+s")
            return "Spotify: toggle shuffle"
        return "Spotify not running"

    def _act_spotify_repeat(self, p):
        if _focus_spotify():
            time.sleep(0.15)
            _send_keys_combo("ctrl+r")
            return "Spotify: toggle repeat"
        return "Spotify not running"

    def _act_spotify_volume_up(self, p):
        times = int(p.get("times", 3) or 3)
        for _ in range(times):
            _press_vk(VK_VOLUME_UP)
        return f"Volume up x{times}"

    def _act_spotify_volume_down(self, p):
        times = int(p.get("times", 3) or 3)
        for _ in range(times):
            _press_vk(VK_VOLUME_DOWN)
        return f"Volume down x{times}"

    def _act_media_next(self, p):
        _press_vk(VK_MEDIA_NEXT)
        return "Media: next"

    def _act_media_previous(self, p):
        _press_vk(VK_MEDIA_PREV)
        return "Media: previous"

    def _act_media_play_pause(self, p):
        _press_vk(VK_MEDIA_PLAY_PAUSE)
        return "Media: play/pause"

    def _act_send_hotkey(self, p):
        combo = p.get("hotkey", "")
        _send_keys_combo(combo)
        return f"Hotkey sent: {combo}"

    def _act_open_app_hotkey(self, p):
        """Open app then optionally send hotkey after delay."""
        path = p.get("path", "")
        delay = float(p.get("delay_ms", 500) or 500) / 1000
        os.startfile(path)
        time.sleep(delay)
        hk = p.get("hotkey_after", "")
        if hk:
            _send_keys_combo(hk)
        return f"Opened {path}" + (f" + keys {hk}" if hk else "")