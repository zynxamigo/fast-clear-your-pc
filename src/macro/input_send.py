"""Reliable keyboard input via SendInput (Windows)."""
import ctypes
import time
from ctypes import wintypes

user32 = ctypes.windll.user32

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001

VK_CONTROL = 0x11
VK_MENU = 0x12
VK_SHIFT = 0x10
VK_LWIN = 0x5B

VK_MEDIA_NEXT = 0xB0
VK_MEDIA_PREV = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_VOLUME_UP = 0xAF
VK_VOLUME_DOWN = 0xAE


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT(ctypes.Structure):
    class _I(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]

    _anonymous_ = ("i",)
    _fields_ = [("type", wintypes.DWORD), ("i", _I)]


def _send_input(*events):
    n = len(events)
    arr = (INPUT * n)(*events)
    sent = user32.SendInput(n, arr, ctypes.sizeof(INPUT))
    if sent != n:
        raise OSError(f"SendInput sent {sent}/{n}")


def _key_down(vk: int, extended: bool = False):
    flags = KEYEVENTF_EXTENDEDKEY if extended else 0
    return INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=vk, dwFlags=flags))


def _key_up(vk: int, extended: bool = False):
    flags = KEYEVENTF_KEYUP | (KEYEVENTF_EXTENDEDKEY if extended else 0)
    return INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=vk, dwFlags=flags))


def press_key(vk: int, extended: bool = False):
    _send_input(_key_down(vk, extended), _key_up(vk, extended))


def press_combo(hotkey_str: str):
    from .hotkeys import MODIFIER_NAMES, SPECIAL_KEYS, parse_hotkey

    mods, vk = parse_hotkey(hotkey_str)
    mod_vks = []
    if mods & 0x0002:
        mod_vks.append(VK_CONTROL)
    if mods & 0x0001:
        mod_vks.append(VK_MENU)
    if mods & 0x0004:
        mod_vks.append(VK_SHIFT)
    if mods & 0x0008:
        mod_vks.append(VK_LWIN)

    extended = vk in (0x25, 0x26, 0x27, 0x28, 0x21, 0x22, 0x23, 0x24, 0x2D, 0x2E)
    events = [_key_down(m) for m in mod_vks]
    events.append(_key_down(vk, extended))
    events.append(_key_up(vk, extended))
    events.extend(_key_up(m) for m in reversed(mod_vks))
    _send_input(*events)


def press_media_next():
    press_key(VK_MEDIA_NEXT)


def press_media_prev():
    press_key(VK_MEDIA_PREV)


def press_media_play_pause():
    press_key(VK_MEDIA_PLAY_PAUSE)


def focus_spotify(timeout: float = 2.0) -> bool:
    import subprocess

    ps = """
    $p = Get-Process -Name Spotify -ErrorAction SilentlyContinue |
         Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero } |
         Select-Object -First 1
    if (-not $p) {
        $spotify = Join-Path $env:APPDATA 'Spotify\\Spotify.exe'
        if (Test-Path $spotify) { Start-Process $spotify; Start-Sleep -Seconds 2 }
        $p = Get-Process -Name Spotify -ErrorAction SilentlyContinue |
             Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero } |
             Select-Object -First 1
    }
    if ($p) {
        Add-Type @"
        using System;
        using System.Runtime.InteropServices;
        public class Win32 {
            [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
            [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int n);
        }
"@
        [Win32]::ShowWindow($p.MainWindowHandle, 9) | Out-Null
        [Win32]::SetForegroundWindow($p.MainWindowHandle) | Out-Null
        Write-Output "OK"
    } else { Write-Output "FAIL" }
    """
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=timeout + 3,
        )
        return "OK" in r.stdout
    except Exception:
        return False


def spotify_shortcut(combo: str):
    """Focus Spotify then send shortcut like ctrl+right."""
    if focus_spotify():
        time.sleep(0.25)
    press_combo(combo)