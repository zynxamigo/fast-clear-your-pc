"""Media & Spotify macro handlers."""
import os
import subprocess

from .input_send import (
    VK_VOLUME_DOWN,
    VK_VOLUME_UP,
    focus_spotify,
    press_combo,
    press_key,
    press_media_next,
    press_media_play_pause,
    press_media_prev,
    spotify_shortcut,
)


def _find_spotify() -> str:
    local = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        os.path.join(local, "Microsoft", "WindowsApps", "Spotify.exe"),
        os.path.join(os.environ.get("APPDATA", ""), "Spotify", "Spotify.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "spotify:"


class MediaMacroMixin:
    """Spotify, media keys and hotkey send handlers."""

    def _act_spotify_next(self, p):
        try:
            spotify_shortcut("ctrl+right")
        except Exception:
            press_media_next()
        return "Spotify: next track"

    def _act_spotify_previous(self, p):
        try:
            spotify_shortcut("ctrl+left")
        except Exception:
            press_media_prev()
        return "Spotify: previous track"

    def _act_spotify_play_pause(self, p):
        press_media_play_pause()
        return "Spotify: play/pause"

    def _act_spotify_open(self, p):
        path = p.get("path") or _find_spotify()
        os.startfile(path)
        return f"Spotify opened: {path}"

    def _act_spotify_next_focused(self, p):
        spotify_shortcut("ctrl+right")
        return "Spotify: next (focused)"

    def _act_spotify_previous_focused(self, p):
        spotify_shortcut("ctrl+left")
        return "Spotify: previous (focused)"

    def _act_spotify_play_focused(self, p):
        import time
        focus_spotify()
        time.sleep(0.25)
        press_key(0x20)
        return "Spotify: play/pause (focused)"

    def _act_spotify_like(self, p):
        spotify_shortcut("ctrl+l")
        return "Spotify: like song"

    def _act_spotify_shuffle(self, p):
        spotify_shortcut("ctrl+s")
        return "Spotify: toggle shuffle"

    def _act_spotify_repeat(self, p):
        spotify_shortcut("ctrl+r")
        return "Spotify: toggle repeat"

    def _act_spotify_volume_up(self, p):
        times = int(p.get("times", 3) or 3)
        for _ in range(times):
            press_key(VK_VOLUME_UP)
        return f"Volume up x{times}"

    def _act_spotify_volume_down(self, p):
        times = int(p.get("times", 3) or 3)
        for _ in range(times):
            press_key(VK_VOLUME_DOWN)
        return f"Volume down x{times}"

    def _act_media_next(self, p):
        press_media_next()
        return "Media: next"

    def _act_media_previous(self, p):
        press_media_prev()
        return "Media: previous"

    def _act_media_play_pause(self, p):
        press_media_play_pause()
        return "Media: play/pause"

    def _act_send_hotkey(self, p):
        combo = p.get("hotkey", "")
        press_combo(combo)
        return f"Hotkey sent: {combo}"

    def _act_open_app_hotkey(self, p):
        import time
        path = p.get("path", "")
        delay = float(p.get("delay_ms", 500) or 500) / 1000
        os.startfile(path)
        time.sleep(delay)
        hk = p.get("hotkey_after", "")
        if hk:
            press_combo(hk)
        return f"Opened {path}" + (f" + {hk}" if hk else "")