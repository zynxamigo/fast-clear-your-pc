"""System macro engine — Android MacroDroid style."""
import json
import os
import shutil
import subprocess
import time
import urllib.request
import winreg
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .actions import ACTION_DEFINITIONS, TRIGGER_IDS
from .handlers_extra import ExtraMacroMixin
from .handlers_sound import SoundMacroMixin
from .sounds import play_wav

HIVE_MAP = {
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
    "HKCR": winreg.HKEY_CLASSES_ROOT,
}

TYPE_MAP = {
    "REG_SZ": winreg.REG_SZ,
    "REG_DWORD": winreg.REG_DWORD,
    "REG_EXPAND_SZ": winreg.REG_EXPAND_SZ,
}


@dataclass
class MacroAction:
    action_type: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Macro:
    id: str
    name: str
    trigger: str = "manual"
    trigger_params: dict[str, Any] = field(default_factory=dict)
    actions: list[MacroAction] = field(default_factory=list)
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MacroResult:
    success: bool
    messages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _is_macro_path_safe(path: str) -> bool:
    from src.cleaner.safety import is_protected_path
    return not is_protected_path(path)


def _ps(cmd: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        capture_output=True,
        timeout=timeout,
    )


class MacroEngine(SoundMacroMixin, ExtraMacroMixin):
    """Executes and manages system macros."""

    def __init__(self, macros_file: Path, i18n=None):
        self.macros_file = macros_file
        self.i18n = i18n
        self.macros: list[Macro] = []
        self._load()

    def _t(self, key: str, **kwargs) -> str:
        if self.i18n:
            return self.i18n.t(key, **kwargs)
        return key

    def _load(self):
        if self.macros_file.exists():
            try:
                data = json.loads(self.macros_file.read_text(encoding="utf-8"))
                self.macros = [
                    Macro(
                        id=m["id"],
                        name=m["name"],
                        trigger=m.get("trigger", "manual"),
                        trigger_params=m.get("trigger_params", {}),
                        actions=[MacroAction(**a) for a in m.get("actions", [])],
                        enabled=m.get("enabled", True),
                        created_at=m.get("created_at", ""),
                    )
                    for m in data
                ]
            except (json.JSONDecodeError, KeyError):
                self.macros = []

    def save(self):
        data = [
            {
                "id": m.id,
                "name": m.name,
                "trigger": m.trigger,
                "trigger_params": m.trigger_params,
                "actions": [{"action_type": a.action_type, "params": a.params} for a in m.actions],
                "enabled": m.enabled,
                "created_at": m.created_at,
            }
            for m in self.macros
        ]
        self.macros_file.parent.mkdir(parents=True, exist_ok=True)
        self.macros_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_macro(self, macro: Macro):
        self.macros.append(macro)
        self.save()

    def remove_macro(self, macro_id: str):
        self.macros = [m for m in self.macros if m.id != macro_id]
        self.save()

    def get_macro(self, macro_id: str) -> Macro | None:
        return next((m for m in self.macros if m.id == macro_id), None)

    def execute(self, macro: Macro, log_cb: Callable[[str], None] | None = None) -> MacroResult:
        result = MacroResult(success=True)
        for action in macro.actions:
            try:
                msg = self._run_action(action)
                result.messages.append(msg)
                if log_cb:
                    log_cb(msg)
            except Exception as e:
                result.success = False
                err = self._t("macro.error_action", action=action.action_type, error=e)
                result.errors.append(err)
                if log_cb:
                    log_cb(err)
        return result

    def _run_action(self, action: MacroAction) -> str:
        p = action.params
        t = action.action_type
        handler = getattr(self, f"_act_{t}", None)
        if handler:
            return handler(p)
        raise ValueError(self._t("macro.error_unknown", action=t))

    def _check_path(self, path: str):
        if not _is_macro_path_safe(path):
            raise PermissionError(self._t("macro.error_protected"))

    # ── Handlers ─────────────────────────────────────────────

    def _act_run_command(self, p):
        cmd = p.get("command", "")
        _ps(cmd, 300)
        return f"PS: {cmd[:60]}"

    def _act_run_cmd(self, p):
        cmd = p.get("command", "")
        subprocess.run(["cmd", "/c", cmd], capture_output=True, timeout=300)
        return f"CMD: {cmd[:60]}"

    def _act_run_batch(self, p):
        path = p.get("path", "")
        self._check_path(path)
        subprocess.run([path], shell=True, timeout=300)
        return f"Batch: {path}"

    def _act_open_app(self, p):
        os.startfile(p.get("path", ""))
        return f"Opened: {p.get('path', '')}"

    def _act_open_url(self, p):
        import webbrowser
        webbrowser.open(p.get("url", ""))
        return f"URL: {p.get('url', '')}"

    def _act_open_folder(self, p):
        path = p.get("path", "")
        os.startfile(path)
        return f"Folder: {path}"

    def _act_close_app(self, p):
        name = p.get("process_name", "")
        _ps(f"Stop-Process -Name '{name}' -Force -ErrorAction SilentlyContinue")
        return f"Closed: {name}"

    def _act_kill_process(self, p):
        pid = int(p.get("pid", 0))
        _ps(f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue")
        return f"Killed PID: {pid}"

    def _act_kill_process_by_name(self, p):
        name = p.get("process_name", "")
        _ps(f"Get-Process '{name}' -ErrorAction SilentlyContinue | Stop-Process -Force")
        return f"Killed: {name}"

    def _act_create_folder(self, p):
        path = Path(p.get("path", ""))
        self._check_path(str(path))
        path.mkdir(parents=True, exist_ok=True)
        return f"Created folder: {path}"

    def _act_delete_folder(self, p):
        path = Path(p.get("path", ""))
        self._check_path(str(path))
        if path.exists():
            shutil.rmtree(path)
        return f"Deleted folder: {path}"

    def _act_create_file(self, p):
        path = Path(p.get("path", ""))
        self._check_path(str(path.parent))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(p.get("content", ""), encoding="utf-8")
        return f"Created file: {path}"

    def _act_delete_file(self, p):
        path = Path(p.get("path", ""))
        self._check_path(str(path))
        if path.exists():
            path.unlink()
        return f"Deleted file: {path}"

    def _act_append_file(self, p):
        path = Path(p.get("path", ""))
        self._check_path(str(path.parent))
        with open(path, "a", encoding="utf-8") as f:
            f.write(p.get("content", ""))
        return f"Appended: {path}"

    def _act_copy_file(self, p):
        src, dst = Path(p.get("source", "")), Path(p.get("destination", ""))
        self._check_path(str(src))
        self._check_path(str(dst.parent))
        shutil.copy2(src, dst)
        return f"Copied: {src} -> {dst}"

    def _act_move_file(self, p):
        src, dst = Path(p.get("source", "")), Path(p.get("destination", ""))
        self._check_path(str(src))
        self._check_path(str(dst.parent))
        shutil.move(str(src), str(dst))
        return f"Moved: {src} -> {dst}"

    def _act_rename_file(self, p):
        src, dst = Path(p.get("source", "")), Path(p.get("destination", ""))
        self._check_path(str(src))
        self._check_path(str(dst.parent))
        src.rename(dst)
        return f"Renamed: {src} -> {dst}"

    def _act_zip_folder(self, p):
        folder, zip_path = Path(p.get("folder", "")), Path(p.get("zip_path", ""))
        self._check_path(str(folder))
        self._check_path(str(zip_path.parent))
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in folder.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(folder))
        return f"Zipped: {folder} -> {zip_path}"

    def _act_unzip_file(self, p):
        zip_path, dest = Path(p.get("zip_path", "")), Path(p.get("destination", ""))
        self._check_path(str(zip_path))
        self._check_path(str(dest))
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest)
        return f"Unzipped: {zip_path} -> {dest}"

    def _act_set_registry(self, p):
        hive = HIVE_MAP.get(p.get("hive", "HKCU"), winreg.HKEY_CURRENT_USER)
        key_path = p.get("key", "")
        with winreg.CreateKey(hive, key_path) as key:
            val_type = TYPE_MAP.get(p.get("type", "REG_SZ"), winreg.REG_SZ)
            value = p.get("value", "")
            if val_type == winreg.REG_DWORD:
                value = int(value)
            winreg.SetValueEx(key, p.get("name", ""), 0, val_type, value)
        return f"Registry set: {p.get('hive')}\\{key_path}"

    def _act_delete_registry(self, p):
        hive = HIVE_MAP.get(p.get("hive", "HKCU"), winreg.HKEY_CURRENT_USER)
        key_path, name = p.get("key", ""), p.get("name", "")
        with winreg.OpenKey(hive, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, name)
        return f"Registry deleted: {name}"

    def _act_set_env_var(self, p):
        subprocess.run(["setx", p.get("name", ""), p.get("value", "")], capture_output=True, timeout=30)
        return f"Env set: {p.get('name')}={p.get('value')}"

    def _act_delete_env_var(self, p):
        _ps(f"[Environment]::SetEnvironmentVariable('{p.get('name', '')}', $null, 'User')")
        return f"Env deleted: {p.get('name')}"

    def _act_create_shortcut(self, p):
        target, shortcut = p.get("target", ""), p.get("shortcut_path", "")
        _ps(f'$w=New-Object -ComObject WScript.Shell;$s=$w.CreateShortcut("{shortcut}");$s.TargetPath="{target}";$s.Save()')
        return f"Shortcut: {shortcut}"

    def _act_delete_shortcut(self, p):
        path = Path(p.get("shortcut_path", ""))
        self._check_path(str(path))
        if path.exists():
            path.unlink()
        return f"Shortcut deleted: {path}"

    def _act_set_wallpaper(self, p):
        path = p.get("image_path", "")
        _ps(f'Add-Type -TypeDefinition \'using System.Runtime.InteropServices; public class W {{ [DllImport("user32.dll")] public static extern int SystemParametersInfo(int a,int b,string c,int d); }}\'; [W]::SystemParametersInfo(20,0,"{path}",3)')
        return f"Wallpaper: {path}"

    def _act_toggle_service(self, p):
        subprocess.run(["sc", p.get("action", "start"), p.get("service_name", "")], capture_output=True, timeout=60)
        return f"Service {p.get('service_name')}: {p.get('action')}"

    def _act_start_service(self, p):
        subprocess.run(["sc", "start", p.get("service_name", "")], capture_output=True, timeout=60)
        return f"Started: {p.get('service_name')}"

    def _act_stop_service(self, p):
        subprocess.run(["sc", "stop", p.get("service_name", "")], capture_output=True, timeout=60)
        return f"Stopped: {p.get('service_name')}"

    def _act_restart_service(self, p):
        svc = p.get("service_name", "")
        subprocess.run(["sc", "stop", svc], capture_output=True, timeout=60)
        time.sleep(2)
        subprocess.run(["sc", "start", svc], capture_output=True, timeout=60)
        return f"Restarted: {svc}"

    def _act_notification(self, p):
        title, msg = p.get("title", "PC Cleaner Macro"), p.get("message", "")
        _ps(f'[System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms")|Out-Null;[System.Windows.Forms.MessageBox]::Show("{msg}","{title}")')
        return f"Notification: {title}"

    def _act_message_box(self, p):
        title, msg = p.get("title", ""), p.get("message", "")
        mtype = p.get("type", "info")
        icon = {"error": 16, "warning": 48, "question": 32}.get(mtype, 64)
        _ps(f'[System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms")|Out-Null;[System.Windows.Forms.MessageBox]::Show("{msg}","{title}",0,{icon})')
        return f"MessageBox: {title}"

    def _act_play_sound(self, p):
        path = p.get("sound_path", "")
        play_wav(path, async_play=False)
        return f"Sound: {path}"

    def _act_beep(self, p):
        freq = int(p.get("frequency", 440))
        dur = int(p.get("duration_ms", 200))
        import winsound
        winsound.Beep(freq, dur)
        return f"Beep: {freq}Hz"

    def _act_wait(self, p):
        secs = float(p.get("seconds", 1))
        time.sleep(secs)
        return f"Waited: {secs}s"

    def _act_lock_screen(self, p):
        _ps("rundll32.exe user32.dll,LockWorkStation")
        return "Screen locked"

    def _act_sleep_pc(self, p):
        _ps("Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState('Suspend',$false,$false)")
        return "Sleep"

    def _act_hibernate_pc(self, p):
        _ps("shutdown /h /f")
        return "Hibernate"

    def _act_shutdown_pc(self, p):
        delay = int(p.get("delay_seconds", 0))
        subprocess.run(["shutdown", "/s", "/t", str(delay)], capture_output=True, timeout=30)
        return f"Shutdown in {delay}s"

    def _act_restart_pc(self, p):
        delay = int(p.get("delay_seconds", 0))
        subprocess.run(["shutdown", "/r", "/t", str(delay)], capture_output=True, timeout=30)
        return f"Restart in {delay}s"

    def _act_logoff_user(self, p):
        _ps("shutdown /l /f")
        return "Logoff"

    def _act_set_clipboard(self, p):
        text = p.get("text", "").replace('"', '`"')
        _ps(f'Set-Clipboard -Value "{text}"')
        return "Clipboard set"

    def _act_clear_clipboard(self, p):
        _ps("Set-Clipboard -Value $null")
        return "Clipboard cleared"

    def _act_flush_dns(self, p):
        subprocess.run(["ipconfig", "/flushdns"], capture_output=True, timeout=30)
        return "DNS flushed"

    def _act_enable_wifi(self, p):
        _ps("netsh interface set interface name='Wi-Fi' admin=enabled")
        return "Wi-Fi enabled"

    def _act_disable_wifi(self, p):
        _ps("netsh interface set interface name='Wi-Fi' admin=disabled")
        return "Wi-Fi disabled"

    def _act_download_file(self, p):
        url, save = p.get("url", ""), p.get("save_path", "")
        self._check_path(str(Path(save).parent))
        urllib.request.urlretrieve(url, save)
        return f"Downloaded: {url} -> {save}"

    def _act_http_request(self, p):
        url = p.get("url", "")
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = resp.read(500)
        return f"HTTP {url}: {len(data)} bytes"

    def _act_empty_recycle_bin(self, p):
        _ps("Clear-RecycleBin -Force -ErrorAction SilentlyContinue")
        return "Recycle Bin emptied"

    def _act_screenshot(self, p):
        save = p.get("save_path", "")
        self._check_path(str(Path(save).parent))
        _ps(f'Add-Type -AssemblyName System.Windows.Forms;[System.Windows.Forms.Screen]::PrimaryScreen | ForEach-Object {{ $b=New-Object Drawing.Bitmap $_.Bounds.Width,$_.Bounds.Height; $g=[Drawing.Graphics]::FromImage($b); $g.CopyFromScreen($_.Bounds.Location,[Drawing.Point]::Empty,$_.Bounds.Size); $b.Save("{save}") }}')
        return f"Screenshot: {save}"

    def _act_minimize_all(self, p):
        _ps("(New-Object -ComObject Shell.Application).MinimizeAll()")
        return "All windows minimized"

    def _act_set_volume(self, p):
        level = int(p.get("level", 50))
        _ps(f"$vol = New-Object -ComObject WScript.Shell; 1..50 | ForEach-Object {{ $vol.SendKeys([char]174) }}; 1..{level//2} | ForEach-Object {{ $vol.SendKeys([char]175) }}")
        return f"Volume: {level}%"

    def _act_mute_volume(self, p):
        mute = p.get("mute", "true").lower() in ("true", "1", "yes")
        _ps(f"$v=New-Object -ComObject WScript.Shell;$v.SendKeys([char]{173 if mute else 175})")
        return f"Mute: {mute}"

    def _act_add_startup(self, p):
        name, cmd = p.get("name", ""), p.get("command", "")
        key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, name, 0, winreg.REG_SZ, cmd)
        return f"Startup added: {name}"

    def _act_remove_startup(self, p):
        name = p.get("name", "")
        key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, name)
        except FileNotFoundError:
            pass
        return f"Startup removed: {name}"

    def _act_create_task(self, p):
        name, cmd, sched = p.get("task_name", ""), p.get("command", ""), p.get("schedule", "DAILY")
        subprocess.run(
            ["schtasks", "/create", "/tn", name, "/tr", cmd, "/sc", sched, "/f"],
            capture_output=True, timeout=60,
        )
        return f"Task created: {name}"

    def _act_delete_task(self, p):
        subprocess.run(["schtasks", "/delete", "/tn", p.get("task_name", ""), "/f"], capture_output=True, timeout=60)
        return f"Task deleted: {p.get('task_name')}"

    def _act_send_keys(self, p):
        keys = p.get("keys", "")
        _ps(f'$w=New-Object -ComObject WScript.Shell;$w.SendKeys("{keys}")')
        return f"Keys sent: {keys}"

    def _act_enable_dark_mode(self, p):
        key = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "AppsUseLightTheme", 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(k, "SystemUsesLightTheme", 0, winreg.REG_DWORD, 0)
        return "Dark mode enabled"

    def _act_disable_dark_mode(self, p):
        key = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "AppsUseLightTheme", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(k, "SystemUsesLightTheme", 0, winreg.REG_DWORD, 1)
        return "Dark mode disabled"

    def _act_open_control_panel(self, p):
        item = p.get("item", "")
        _ps(f"control.exe {item}")
        return f"Control Panel: {item}"

    def _act_refresh_explorer(self, p):
        _ps("Stop-Process -Name explorer -Force; Start-Process explorer")
        return "Explorer restarted"

    def _act_clear_temp_macro(self, p):
        from src.cleaner.safety import get_user_temp_paths
        from src.cleaner.engine import CleanerEngine
        paths = [str(x) for x in get_user_temp_paths()]
        engine = CleanerEngine([])
        engine.clean(["user_temp"])
        return f"Temp cleared: {len(paths)} paths"

    def _act_set_datetime(self, p):
        dt = p.get("datetime", "")
        subprocess.run(["powershell", "-Command", f"Set-Date -Date '{dt}'"], capture_output=True, timeout=30)
        return f"DateTime: {dt}"

    def _act_block_input(self, p):
        secs = float(p.get("seconds", 5))
        _ps(f'Add-Type -TypeDefinition \'using System.Runtime.InteropServices; public class B {{ [DllImport("user32.dll")] public static extern bool BlockInput(bool b); }}\'; [B]::BlockInput($true); Start-Sleep -Seconds {secs}; [B]::BlockInput($false)')
        return f"Input blocked: {secs}s"

    def _act_unblock_input(self, p):
        _ps('Add-Type -TypeDefinition \'using System.Runtime.InteropServices; public class B {{ [DllImport("user32.dll")] public static extern bool BlockInput(bool b); }}\'; [B]::BlockInput($false)')
        return "Input unblocked"


# Backward compatibility
AVAILABLE_ACTIONS = {k: {"params": v} for k, v in ACTION_DEFINITIONS.items()}
AVAILABLE_TRIGGERS = {t: {} for t in TRIGGER_IDS}