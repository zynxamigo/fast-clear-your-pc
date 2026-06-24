"""Sound-related macro action handlers."""
import os
import subprocess

from .sounds import (
    WINDOWS_SOUND_EVENTS,
    open_app_with_sound,
    play_system_event,
    play_wav,
    restore_all_default_sounds,
    restore_windows_sound,
    set_windows_sound,
)


class SoundMacroMixin:
    """Mixin providing sound macro handlers."""

    def _act_open_app_with_sound(self, p):
        return open_app_with_sound(
            p.get("path", ""),
            p.get("sound_path", ""),
            p.get("mode", "simultaneous"),
            int(p.get("delay_ms", 0) or 0),
        )

    def _act_play_sound_async(self, p):
        play_wav(p.get("sound_path", ""), async_play=True)
        return f"Playing async: {p.get('sound_path', '')}"

    def _act_play_mp3(self, p):
        path = p.get("sound_path", "")
        os.startfile(path)
        return f"MP3/Media: {path}"

    def _act_stop_all_sounds(self, p):
        import winsound
        winsound.PlaySound(None, winsound.SND_PURGE)
        return "All sounds stopped"

    def _act_speak_text(self, p):
        text = p.get("text", "").replace('"', '`"')
        rate = int(p.get("rate", 0) or 0)
        subprocess.run(
            ["powershell", "-Command", f"Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Rate={rate}; $s.Speak('{text}')"],
            capture_output=True, timeout=120,
        )
        return f"Spoke: {text[:40]}..."

    def _act_set_device_connect_sound(self, p):
        result = set_windows_sound("device_connect", p.get("wav_path", ""))
        return f"Plug sound set: {result}"

    def _act_set_device_disconnect_sound(self, p):
        result = set_windows_sound("device_disconnect", p.get("wav_path", ""))
        return f"Unplug sound set: {result}"

    def _act_set_system_sound(self, p):
        event = p.get("sound_event", "device_connect")
        result = set_windows_sound(event, p.get("wav_path", ""))
        return f"System sound: {result}"

    def _act_play_system_sound(self, p):
        event = p.get("sound_event", "device_connect")
        play_system_event(event)
        return f"Played event: {event}"

    def _act_restore_system_sound(self, p):
        event = p.get("sound_event", "device_connect")
        result = restore_windows_sound(event)
        return f"Restored: {result}"

    def _act_restore_all_sounds(self, p):
        results = restore_all_default_sounds()
        return f"Restored {len(results)} sounds"

    def _act_open_sound_settings(self, p):
        os.startfile("mmsys.cpl")
        return "Sound settings opened"

    def _act_test_plug_unplug_sounds(self, p):
        play_system_event("device_connect")
        import time
        time.sleep(1)
        play_system_event("device_disconnect")
        return "Tested plug + unplug sounds"

    def _act_set_app_volume(self, p):
        proc = p.get("process_name", "")
        level = int(p.get("level", 50) or 50)
        self._ps(  # noqa: assume _ps from engine
            f"$a=New-Object -ComObject WScript.Shell; $p=Get-Process '{proc}' -ErrorAction SilentlyContinue | Select-Object -First 1; if($p){{$a.SendKeys('') }}"
        )
        return f"Volume hint for {proc}: {level}% (set via system mixer)"