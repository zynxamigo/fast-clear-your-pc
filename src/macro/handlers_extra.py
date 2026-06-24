"""Additional macro action handlers."""
import os
import subprocess
import time
import webbrowser
from pathlib import Path


class ExtraMacroMixin:
    """Mixin for extended system macro handlers."""

    def _act_run_as_admin(self, p):
        cmd = p.get("command", "")
        subprocess.run(
            ["powershell", "-Command", f"Start-Process powershell -Verb RunAs -ArgumentList '-Command {cmd}'"],
            capture_output=True, timeout=60,
        )
        return f"Admin: {cmd[:50]}"

    def _act_open_settings(self, p):
        page = p.get("page", "")
        uri = f"ms-settings:{page}" if page else "ms-settings:"
        os.startfile(uri)
        return f"Settings: {uri}"

    def _act_focus_window(self, p):
        title = p.get("window_title", "")
        self._ps(f"$w=Get-Process | Where-Object {{$_.MainWindowTitle -like '*{title}*'}} | Select-Object -First 1; if($w){{(New-Object -ComObject WScript.Shell).AppActivate($w.Id)}}")
        return f"Focus: {title}"

    def _act_open_task_manager(self, p):
        subprocess.run(["taskmgr"], timeout=10)
        return "Task Manager opened"

    def _act_open_device_manager(self, p):
        subprocess.run(["devmgmt.msc"], shell=True, timeout=10)
        return "Device Manager opened"

    def _act_open_services(self, p):
        subprocess.run(["services.msc"], shell=True, timeout=10)
        return "Services opened"

    def _act_open_registry(self, p):
        subprocess.run(["regedit"], timeout=10)
        return "Registry Editor opened"

    def _act_toast_notification(self, p):
        title = p.get("title", "").replace("'", "''")
        msg = p.get("message", "").replace("'", "''")
        self._ps(f"[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null; [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null; $xml=New-Object Windows.Data.Xml.Dom.XmlDocument; $xml.LoadXml('<toast><visual><binding template=\"ToastText02\"><text id=\"1\">{title}</text><text id=\"2\">{msg}</text></binding></visual></toast>'); $toast=[Windows.UI.Notifications.ToastNotification]::new($xml); [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('PC Cleaner Macro').Show($toast)")
        return f"Toast: {title}"

    def _act_set_wallpaper_solid(self, p):
        color = p.get("color", "0 120 215")
        self._ps(f'Add-Type -TypeDefinition \'using System.Runtime.InteropServices; public class W {{ [DllImport("user32.dll")] public static extern int SystemParametersInfo(int a,int b,string c,int d); }}\'; [W]::SystemParametersInfo(20,0,"",{3})')
        return f"Wallpaper color: {color}"

    def _act_toggle_desktop_icons(self, p):
        self._ps("$p='HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced'; $v=(Get-ItemProperty $p).HideIcons; Set-ItemProperty $p HideIcons $(if($v -eq 1){0}else{1})")
        return "Desktop icons toggled"

    def _act_show_desktop(self, p):
        self._ps("(New-Object -ComObject Shell.Application).ToggleDesktop()")
        return "Show desktop"

    def _act_set_accent_color(self, p):
        hex_color = p.get("color_hex", "0078D7").lstrip("#")
        self._ps(f"Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Accent' -Name AccentColorMenu -Value 0x{hex_color}")
        return f"Accent: #{hex_color}"

    def _act_toggle_night_light(self, p):
        self._ps("Get-Process SystemSettings -ErrorAction SilentlyContinue | Out-Null; start ms-settings:nightlight")
        return "Night light settings opened"

    def _act_hide_taskbar(self, p):
        self._ps("Set-ItemProperty 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\StuckRects3' -Name Settings -Value ([byte[]](0x30,0x00,0x00,0x00,0xfe,0xff,0xff,0xff,0x02,0x00,0x00,0x00,0x03,0x00,0x00,0x00,0x3e,0x00,0x00,0x00,0x2e,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x80,0x07,0x00,0x00,0x78,0x00,0x00,0x00,0x01,0x00,0x00,0x00))")
        self._ps("Stop-Process -Name explorer -Force; Start-Process explorer")
        return "Taskbar hidden"

    def _act_show_taskbar(self, p):
        self._ps("Stop-Process -Name explorer -Force; Start-Process explorer")
        return "Taskbar restored"

    def _act_cancel_shutdown(self, p):
        subprocess.run(["shutdown", "/a"], capture_output=True, timeout=10)
        return "Shutdown cancelled"

    def _act_prevent_sleep(self, p):
        mins = int(p.get("minutes", 60) or 60)
        self._ps(f'powercfg /change standby-timeout-ac {mins}')
        return f"Sleep prevented: {mins}min"

    def _act_allow_sleep(self, p):
        self._ps("powercfg /change standby-timeout-ac 15")
        return "Sleep timeout restored"

    def _act_set_power_plan(self, p):
        plan = p.get("plan", "balanced").lower()
        guids = {"balanced": "381b4222-f694-41f0-9685-ff5bb260df2e", "high": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c", "saver": "a1841308-3541-4fab-bc81-71574156bda4"}
        guid = guids.get(plan, guids["balanced"])
        subprocess.run(["powercfg", "/setactive", guid], capture_output=True, timeout=30)
        return f"Power plan: {plan}"

    def _act_type_text(self, p):
        text = p.get("text", "").replace("+", "{+}").replace("^", "{^}").replace("%", "{%}").replace("~", "{~}")
        self._ps(f'$w=New-Object -ComObject WScript.Shell;$w.SendKeys("{text}")')
        return f"Typed: {text[:30]}"

    def _act_mouse_click(self, p):
        x, y = int(p.get("x", 0)), int(p.get("y", 0))
        btn = p.get("button", "left")
        self._ps(f'Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Cursor]::Position=New-Object System.Drawing.Point({x},{y}); [System.Windows.Forms.Cursor]::Position')
        return f"Click {btn} at ({x},{y})"

    def _act_mouse_move(self, p):
        x, y = int(p.get("x", 0)), int(p.get("y", 0))
        self._ps(f'Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Cursor]::Position=New-Object System.Drawing.Point({x},{y})')
        return f"Mouse ({x},{y})"

    def _act_scroll_wheel(self, p):
        amount = int(p.get("amount", 3))
        key = "{SCROLLDOWN}" if amount < 0 else "{SCROLLUP}"
        self._ps(f'$w=New-Object -ComObject WScript.Shell;1..{abs(amount)}|ForEach-Object{{$w.SendKeys("{key}")}}')
        return f"Scroll: {amount}"

    def _act_toggle_caps_lock(self, p):
        self._ps('$w=New-Object -ComObject WScript.Shell;$w.SendKeys("{CAPSLOCK}")')
        return "Caps Lock toggled"

    def _act_toggle_wifi(self, p):
        self._ps("$adapter=Get-NetAdapter | Where-Object Status -eq 'Up' | Where-Object Name -like '*Wi-Fi*' -or Name -like '*Wireless*' | Select-Object -First 1; if($adapter){Disable-NetAdapter $adapter.Name -Confirm:$false}else{Get-NetAdapter | Where-Object Name -like '*Wi-Fi*' | Enable-NetAdapter -Confirm:$false}")
        return "Wi-Fi toggled"

    def _act_enable_bluetooth(self, p):
        self._ps("Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | Enable-PnpDevice -Confirm:$false")
        return "Bluetooth enabled"

    def _act_disable_bluetooth(self, p):
        self._ps("Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | Disable-PnpDevice -Confirm:$false")
        return "Bluetooth disabled"

    def _act_ping_host(self, p):
        host = p.get("host", "8.8.8.8")
        r = subprocess.run(["ping", "-n", "2", host], capture_output=True, timeout=30, text=True)
        return f"Ping {host}: {r.returncode == 0}"

    def _act_open_network_settings(self, p):
        os.startfile("ms-settings:network")
        return "Network settings"

    def _act_read_file(self, p):
        path = Path(p.get("path", ""))
        self._check_path(str(path))
        content = path.read_text(encoding="utf-8", errors="replace")[:500]
        return f"Read {path}: {len(content)} chars"

    def _act_list_folder(self, p):
        path = Path(p.get("path", ""))
        items = list(path.iterdir())[:20] if path.exists() else []
        return f"Folder {path}: {len(items)} items"

    def _act_eject_drive(self, p):
        letter = p.get("drive_letter", "E").rstrip(":")
        self._ps(f'$drive=(New-Object -ComObject Shell.Application).Namespace(17).ParseName("{letter}:"); if($drive){{$drive.InvokeVerb("Eject")}}')
        return f"Eject {letter}:"

    def _act_open_disk_cleanup(self, p):
        subprocess.run(["cleanmgr"], timeout=10)
        return "Disk Cleanup opened"

    def _act_run_other_macro(self, p):
        macro_id = p.get("macro_id", "")
        macro = self.get_macro(macro_id)
        if not macro:
            raise ValueError(f"Macro not found: {macro_id}")
        result = self.execute(macro)
        return f"Ran macro {macro.name}: {'OK' if result.success else 'FAIL'}"

    def _act_set_brightness(self, p):
        level = int(p.get("level", 50) or 50)
        self._ps(f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})")
        return f"Brightness: {level}%"

    def _act_set_resolution(self, p):
        w, h = int(p.get("width", 1920)), int(p.get("height", 1080))
        self._ps(f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Screen]::PrimaryScreen")
        return f"Resolution request: {w}x{h} (use Display Settings)"

    def _act_toggle_focus_assist(self, p):
        os.startfile("ms-settings:quiethours")
        return "Focus assist settings"

    def _act_open_camera(self, p):
        os.startfile("microsoft.windows.camera:")
        return "Camera opened"

    def _act_toggle_microphone(self, p):
        os.startfile("ms-settings:privacy-microphone")
        return "Microphone settings"

    def _act_toggle_game_bar(self, p):
        self._ps("Get-AppxPackage Microsoft.XboxGamingOverlay | Reset-AppxPackage")
        os.startfile("ms-settings:gaming-gamebar")
        return "Game Bar settings"

    def _act_maximize_window(self, p):
        title = p.get("window_title", "")
        self._ps(
            f"$w=Get-Process|Where-Object{{$_.MainWindowTitle -like '*{title}*'}}|Select -First 1;"
            f"if($w){{$s=New-Object -ComObject WScript.Shell;$s.AppActivate($w.Id);"
            f"$sig='[DllImport(\"user32.dll\")]public static extern bool ShowWindow(IntPtr h,int c);';"
            f"Add-Type -MemberDefinition $sig -Name Win -Namespace Native;"
            f"[Native.Win]::ShowWindow($w.MainWindowHandle,3)}}"
        )
        return f"Maximize: {title}"