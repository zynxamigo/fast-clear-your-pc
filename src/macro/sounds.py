"""Windows system sound utilities."""
import os
import threading
import winreg
from pathlib import Path

SOUND_REGISTRY_BASE = r"AppEvents\Schemes\Apps\.Default"

# User-friendly key -> Windows registry event name
WINDOWS_SOUND_EVENTS = {
    "device_connect": "DeviceConnect",
    "device_disconnect": "DeviceDisconnect",
    "device_fail": "DeviceFailedConnect",
    "startup": "WindowsStart",
    "shutdown": "WindowsExit",
    "logon": "WindowsLogon",
    "logoff": "WindowsLogoff",
    "error": "SystemExclamation",
    "warning": "SystemNotification",
    "question": "SystemQuestion",
    "information": "SystemAsterisk",
    "critical_stop": "SystemHand",
    "notification": "Notification.Default",
    "recycle": "EmptyRecycleBin",
    "mail": "MailBeep",
    "low_battery": "CriticalBatteryAlarm",
    "print_complete": "PrintComplete",
    "navigation": "MoveMenuItem",
    "select": "MenuPopup",
    "close_program": "Close",
    "maximize": "Maximize",
    "minimize": "Minimize",
    "restore": "RestoreDown",
    "menu_command": "MenuCommand",
    "open_folder": "Open",
    "default_beep": "SystemDefault",
}

# Default Windows media sounds for restore
DEFAULT_MEDIA = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Media"


def _validate_wav(wav_path: str) -> Path:
    p = Path(wav_path)
    if not p.exists():
        raise FileNotFoundError(f"Sound file not found: {wav_path}")
    if p.suffix.lower() not in (".wav", ".mp3", ".ogg"):
        raise ValueError("Sound file should be .wav (recommended), .mp3 or .ogg")
    return p.resolve()


def set_windows_sound(event_key: str, wav_path: str) -> str:
    """Set a Windows system sound event to a custom file."""
    if event_key not in WINDOWS_SOUND_EVENTS:
        raise ValueError(f"Unknown sound event: {event_key}")
    event_name = WINDOWS_SOUND_EVENTS[event_key]
    resolved = str(_validate_wav(wav_path))

    for sub in (".Current", ".Default"):
        key_path = f"{SOUND_REGISTRY_BASE}\\{event_name}{sub}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, resolved)

    return f"{event_key} -> {resolved}"


def restore_windows_sound(event_key: str) -> str:
    """Restore a single sound event to Windows default."""
    defaults = {
        "device_connect": DEFAULT_MEDIA / "Windows Hardware Insert.wav",
        "device_disconnect": DEFAULT_MEDIA / "Windows Hardware Remove.wav",
        "device_fail": DEFAULT_MEDIA / "Windows Hardware Fail.wav",
        "startup": DEFAULT_MEDIA / "Windows Startup.wav",
        "shutdown": DEFAULT_MEDIA / "Windows Shutdown.wav",
        "logon": DEFAULT_MEDIA / "Windows Logon.wav",
        "logoff": DEFAULT_MEDIA / "Windows Logoff.wav",
        "error": DEFAULT_MEDIA / "Windows Error.wav",
        "warning": DEFAULT_MEDIA / "Windows Background.wav",
        "question": DEFAULT_MEDIA / "Windows Question.wav",
        "information": DEFAULT_MEDIA / "Windows Information.wav",
        "critical_stop": DEFAULT_MEDIA / "Windows Critical Stop.wav",
        "notification": DEFAULT_MEDIA / "Windows Notify System Generic.wav",
        "recycle": DEFAULT_MEDIA / "Windows Recycle.wav",
        "default_beep": DEFAULT_MEDIA / "Windows Ding.wav",
    }
    if event_key in defaults and defaults[event_key].exists():
        return set_windows_sound(event_key, str(defaults[event_key]))
    raise FileNotFoundError(f"No default sound for: {event_key}")


def restore_all_default_sounds() -> list[str]:
    """Restore all known sounds to Windows defaults."""
    results = []
    for key in WINDOWS_SOUND_EVENTS:
        try:
            results.append(restore_windows_sound(key))
        except (FileNotFoundError, OSError):
            pass
    return results


def play_wav(path: str, async_play: bool = True) -> None:
    """Play a sound file."""
    import winsound
    p = str(_validate_wav(path))
    if async_play:
        winsound.PlaySound(p, winsound.SND_FILENAME | winsound.SND_ASYNC)
    else:
        winsound.PlaySound(p, winsound.SND_FILENAME)


def play_wav_sync(path: str) -> None:
    play_wav(path, async_play=False)


def play_system_event(event_key: str) -> None:
    """Play current system sound for an event."""
    if event_key not in WINDOWS_SOUND_EVENTS:
        raise ValueError(f"Unknown event: {event_key}")
    event_name = WINDOWS_SOUND_EVENTS[event_key]
    key_path = f"{SOUND_REGISTRY_BASE}\\{event_name}\\.Current"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            wav, _ = winreg.QueryValueEx(key, "")
        if wav and Path(wav).exists():
            play_wav_sync(wav)
        else:
            import winsound
            winsound.MessageBeep()
    except OSError:
        import winsound
        winsound.MessageBeep()


def open_app_with_sound(
    app_path: str,
    sound_path: str,
    mode: str = "simultaneous",
    delay_ms: int = 0,
) -> str:
    """
    Open an app with a sound.
    mode: simultaneous | sound_first | app_first
    """
    import time

    def _play():
        try:
            play_wav(sound_path, async_play=True)
        except Exception:
            pass

    mode = mode.lower().strip()
    if mode == "sound_first":
        play_wav_sync(sound_path)
        if delay_ms:
            time.sleep(delay_ms / 1000)
        os.startfile(app_path)
    elif mode == "app_first":
        os.startfile(app_path)
        if delay_ms:
            time.sleep(delay_ms / 1000)
        threading.Thread(target=_play, daemon=True).start()
    else:
        threading.Thread(target=_play, daemon=True).start()
        os.startfile(app_path)

    return f"App: {app_path} | Sound: {sound_path} | Mode: {mode}"