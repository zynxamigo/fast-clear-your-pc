"""Safety protections — never deletes critical system folders."""
import os
from pathlib import Path

PROTECTED_DIRS = {
    r"C:\Windows\System32",
    r"C:\Windows\SysWOW64",
    r"C:\Windows",
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    r"C:\ProgramData\Microsoft\Windows\Start Menu",
    r"C:\Users\Default",
    r"C:\Recovery",
    r"C:\Boot",
    r"C:\EFI",
}

PROTECTED_EXTENSIONS = {
    ".dll", ".sys", ".exe", ".drv", ".ocx", ".cpl",
    ".mui", ".cat", ".inf", ".efi", ".bin", ".reg",
}

# Windows subpaths that are safe to clean (whitelist under C:\Windows)
SAFE_WINDOWS_CLEAN_PATHS = {
    r"C:\Windows\Temp",
    r"C:\Windows\Prefetch",
    r"C:\Windows\SoftwareDistribution\Download",
    r"C:\Windows\SoftwareDistribution\DeliveryOptimization",
    r"C:\Windows\Logs\CBS",
    r"C:\Windows\Logs\DISM",
    r"C:\Windows\Logs\WindowsUpdate",
    r"C:\Windows\Logs\MoSetup",
    r"C:\Windows\Minidump",
    r"C:\Windows\Installer\$PatchCache$",
    r"C:\Windows\ServiceProfiles\NetworkService\AppData\Local\Temp",
    r"C:\Windows\ServiceProfiles\LocalService\AppData\Local\Temp",
    r"C:\Windows\ServiceProfiles\LocalService\AppData\Local\FontCache",
}

SAFE_CLEAN_TARGETS = [
    {"id": "user_temp", "path": None},
    {"id": "windows_temp", "path": r"C:\Windows\Temp"},
    {"id": "prefetch", "path": r"C:\Windows\Prefetch"},
    {"id": "thumbnail_cache", "path": None},
    {"id": "icon_cache", "path": None},
    {"id": "recycle_bin", "path": None},
    {"id": "chrome_cache", "path": None},
    {"id": "edge_cache", "path": None},
    {"id": "firefox_cache", "path": None},
    {"id": "brave_cache", "path": None},
    {"id": "opera_cache", "path": None},
    {"id": "discord_cache", "path": None},
    {"id": "spotify_cache", "path": None},
    {"id": "steam_cache", "path": None},
    {"id": "epic_cache", "path": None},
    {"id": "teams_cache", "path": None},
    {"id": "slack_cache", "path": None},
    {"id": "vscode_cache", "path": None},
    {"id": "npm_cache", "path": None},
    {"id": "pip_cache", "path": None},
    {"id": "gradle_cache", "path": None},
    {"id": "windows_update_cache", "path": r"C:\Windows\SoftwareDistribution\Download"},
    {"id": "delivery_optimization", "path": r"C:\Windows\SoftwareDistribution\DeliveryOptimization"},
    {"id": "recent_files", "path": None},
    {"id": "jump_lists", "path": None},
    {"id": "error_reports", "path": r"C:\ProgramData\Microsoft\Windows\WER"},
    {"id": "installer_cache", "path": None},
    {"id": "inet_cache", "path": None},
    {"id": "microsoft_store_cache", "path": None},
    {"id": "gpu_shader_cache", "path": None},
    {"id": "directx_cache", "path": None},
    {"id": "crash_dumps", "path": None},
    {"id": "minidumps", "path": r"C:\Windows\Minidump"},
    {"id": "windows_logs", "path": None},
    {"id": "clipboard_history", "path": None},
    {"id": "notifications_cache", "path": None},
    {"id": "search_index_temp", "path": None},
    {"id": "office_cache", "path": None},
    {"id": "outlook_cache", "path": None},
    {"id": "java_cache", "path": None},
    {"id": "dotnet_temp", "path": None},
    {"id": "defender_history", "path": None},
    {"id": "remote_desktop_cache", "path": None},
    {"id": "font_cache", "path": None},
    {"id": "dns_cache", "path": None},
    {"id": "windows_old", "path": None},
]


def normalize_path(path: str | Path) -> Path:
    try:
        return Path(path).resolve()
    except (OSError, ValueError):
        return Path(os.path.abspath(str(path)))


def _is_under_safe_windows_path(path: Path) -> bool:
    try:
        resolved = str(normalize_path(path)).lower()
        for safe in SAFE_WINDOWS_CLEAN_PATHS:
            safe_str = str(normalize_path(safe)).lower()
            if resolved == safe_str or resolved.startswith(safe_str + "\\"):
                return True
    except Exception:
        pass
    return False


def is_protected_path(path: str | Path) -> bool:
    try:
        resolved = normalize_path(path)
        resolved_str = str(resolved).lower().rstrip("\\/")
    except Exception:
        return True

    if _is_under_safe_windows_path(resolved):
        return False

    for protected in PROTECTED_DIRS:
        try:
            prot = str(normalize_path(protected)).lower().rstrip("\\/")
            if resolved_str == prot or resolved_str.startswith(prot + "\\"):
                return True
        except Exception:
            continue

    parts = [p.lower() for p in resolved.parts]
    if "system32" in parts or "syswow64" in parts:
        return True

    return False


def is_protected_file(path: str | Path) -> bool:
    p = Path(path)
    if is_protected_path(p.parent):
        return True
    if p.suffix.lower() in PROTECTED_EXTENSIONS and is_under_windows(p):
        return True
    return False


def is_under_windows(path: Path) -> bool:
    try:
        windows = normalize_path(r"C:\Windows")
        resolved = normalize_path(path)
        return str(resolved).lower().startswith(str(windows).lower())
    except Exception:
        return False


def is_safe_to_delete(path: str | Path, user_exclusions: list[str]) -> bool:
    p = normalize_path(path)

    if is_protected_path(p) or is_protected_file(p):
        return False

    for exc in user_exclusions:
        try:
            exc_path = normalize_path(exc)
            exc_str = str(exc_path).lower()
            p_str = str(p).lower()
            if p_str == exc_str or p_str.startswith(exc_str + "\\"):
                return False
        except Exception:
            continue

    return True


def _local() -> str:
    return os.environ.get("LOCALAPPDATA", "")


def _appdata() -> str:
    return os.environ.get("APPDATA", "")


def _userprofile() -> str:
    return os.environ.get("USERPROFILE", "")


def get_user_temp_paths() -> list[Path]:
    paths = []
    for env in ("TEMP", "TMP"):
        val = os.environ.get(env)
        if val:
            paths.append(Path(val))
    local = _local()
    if local:
        paths.append(Path(local) / "Temp")
    return list(dict.fromkeys(paths))


def get_browser_cache_paths() -> dict[str, list[Path]]:
    local, appdata = _local(), _appdata()
    result: dict[str, list[Path]] = {
        "chrome": [], "edge": [], "firefox": [], "brave": [], "opera": [],
    }

    if local:
        chrome_base = Path(local) / "Google" / "Chrome" / "User Data"
        for profile in ["Default"] + [p.name for p in chrome_base.glob("Profile *") if p.is_dir()]:
            base = chrome_base / profile
            result["chrome"].extend([
                base / "Cache", base / "Code Cache", base / "GPUCache",
                base / "Service Worker" / "CacheStorage",
            ])
        edge_base = Path(local) / "Microsoft" / "Edge" / "User Data"
        for profile in ["Default"] + [p.name for p in edge_base.glob("Profile *") if p.is_dir()]:
            base = edge_base / profile
            result["edge"].extend([base / "Cache", base / "Code Cache", base / "GPUCache"])
        brave_base = Path(local) / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default"
        result["brave"] = [brave_base / "Cache", brave_base / "Code Cache", brave_base / "GPUCache"]
        opera_base = Path(local) / "Opera Software" / "Opera Stable"
        result["opera"] = [opera_base / "Cache", opera_base / "Code Cache"]

    if appdata:
        profiles = Path(appdata) / "Mozilla" / "Firefox" / "Profiles"
        if profiles.exists():
            for prof in profiles.iterdir():
                if prof.is_dir():
                    result["firefox"].extend([prof / "cache2", prof / "startupCache"])

    return result


def get_thumbnail_cache_path() -> Path | None:
    local = _local()
    return Path(local) / "Microsoft" / "Windows" / "Explorer" if local else None


def get_icon_cache_paths() -> list[Path]:
    thumb = get_thumbnail_cache_path()
    if not thumb:
        return []
    return [thumb]


def get_recent_files_path() -> Path | None:
    appdata = _appdata()
    return Path(appdata) / "Microsoft" / "Windows" / "Recent" if appdata else None


def get_jump_lists_paths() -> list[Path]:
    appdata = _appdata()
    if not appdata:
        return []
    return [
        Path(appdata) / "Microsoft" / "Windows" / "Recent" / "AutomaticDestinations",
        Path(appdata) / "Microsoft" / "Windows" / "Recent" / "CustomDestinations",
    ]


def get_installer_cache_paths() -> list[Path]:
    paths = []
    windir = os.environ.get("WINDIR", r"C:\Windows")
    paths.append(Path(windir) / "Installer" / "$PatchCache$")
    local = _local()
    if local:
        paths.append(Path(local) / "Downloaded Installations")
    return paths


def get_inet_cache_paths() -> list[Path]:
    local = _local()
    if not local:
        return []
    return [Path(local) / "Microsoft" / "Windows" / "INetCache"]


def get_microsoft_store_cache_paths() -> list[Path]:
    local = _local()
    if not local:
        return []
    return [
        Path(local) / "Packages" / "Microsoft.WindowsStore_8wekyb3d8bbwe" / "LocalCache",
        Path(local) / "Microsoft" / "Windows" / "AppCache",
    ]


def get_gpu_shader_cache_paths() -> list[Path]:
    local = _local()
    if not local:
        return []
    return [
        Path(local) / "D3DSCache",
        Path(local) / "NVIDIA" / "DXCache",
        Path(local) / "NVIDIA" / "GLCache",
        Path(local) / "AMD" / "DxCache",
        Path(local) / "AMD" / "VkCache",
    ]


def get_directx_cache_paths() -> list[Path]:
    local = _local()
    if not local:
        return []
    return [Path(local) / "D3DSCache"]


def get_discord_cache_paths() -> list[Path]:
    appdata = _appdata()
    if not appdata:
        return []
    return [
        Path(appdata) / "discord" / "Cache",
        Path(appdata) / "discord" / "Code Cache",
        Path(appdata) / "discord" / "GPUCache",
    ]


def get_spotify_cache_paths() -> list[Path]:
    local = _local()
    if not local:
        return []
    return [Path(local) / "Spotify" / "Data"]


def get_steam_cache_paths() -> list[Path]:
    paths = []
    for base in [Path(_local()) / "Steam" / "htmlcache", Path("C:/Program Files (x86)/Steam/appcache")]:
        if base.parent.exists() or base.exists():
            paths.append(base)
    steam = Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Steam" / "appcache"
    paths.append(steam)
    return paths


def get_epic_cache_paths() -> list[Path]:
    local = _local()
    if not local:
        return []
    return [Path(local) / "EpicGamesLauncher" / "Saved" / "webcache"]


def get_teams_cache_paths() -> list[Path]:
    paths = []
    for root in [_appdata(), _local()]:
        if root:
            paths.append(Path(root) / "Microsoft" / "Teams" / "Cache")
            paths.append(Path(root) / "Microsoft" / "Teams" / "tmp")
    return paths


def get_slack_cache_paths() -> list[Path]:
    appdata = _appdata()
    if not appdata:
        return []
    return [Path(appdata) / "Slack" / "Cache", Path(appdata) / "Slack" / "Code Cache"]


def get_vscode_cache_paths() -> list[Path]:
    paths = []
    for env, sub in [(_appdata(), "Code"), (_appdata(), "Code - Insiders")]:
        if env:
            base = Path(env) / sub
            paths.extend([base / "Cache", base / "CachedData", base / "logs"])
    return paths


def get_npm_cache_paths() -> list[Path]:
    appdata = _appdata()
    if not appdata:
        return []
    return [Path(appdata) / "npm-cache"]


def get_pip_cache_paths() -> list[Path]:
    local = _local()
    if not local:
        return []
    return [Path(local) / "pip" / "cache"]


def get_gradle_cache_paths() -> list[Path]:
    user = _userprofile()
    if not user:
        return []
    return [Path(user) / ".gradle" / "caches"]


def get_crash_dumps_paths() -> list[Path]:
    local = _local()
    paths = []
    if local:
        paths.append(Path(local) / "CrashDumps")
    paths.append(Path(_userprofile()) / "AppData" / "Local" / "CrashDumps")
    return [p for p in paths if p]


def get_windows_logs_paths() -> list[Path]:
    windir = os.environ.get("WINDIR", r"C:\Windows")
    return [
        Path(windir) / "Logs" / "CBS",
        Path(windir) / "Logs" / "DISM",
        Path(windir) / "Logs" / "WindowsUpdate",
        Path(windir) / "Logs" / "MoSetup",
    ]


def get_notifications_cache_paths() -> list[Path]:
    local = _local()
    if not local:
        return []
    return [Path(local) / "Microsoft" / "Windows" / "Notifications" / "wpndatabase.db-wal"]


def get_search_index_temp_paths() -> list[Path]:
    progdata = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    return [Path(progdata) / "Microsoft" / "Search" / "Data" / "Applications" / "Windows"]


def get_office_cache_paths() -> list[Path]:
    local = _local()
    if not local:
        return []
    return [Path(local) / "Microsoft" / "Office" / "16.0" / "OfficeFileCache"]


def get_outlook_cache_paths() -> list[Path]:
    local = _local()
    if not local:
        return []
    return [
        Path(local) / "Microsoft" / "Outlook" / "HubAppFileCache",
        Path(local) / "Microsoft" / "Olk" / "Cache",
    ]


def get_java_cache_paths() -> list[Path]:
    user = _userprofile()
    if not user:
        return []
    return [Path(user) / "AppData" / "LocalLow" / "Sun" / "Java" / "Deployment" / "cache"]


def get_dotnet_temp_paths() -> list[Path]:
    local = _local()
    if not local:
        return []
    return [Path(local) / "Temp" / ".net"]


def get_defender_history_paths() -> list[Path]:
    progdata = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    return [Path(progdata) / "Microsoft" / "Windows Defender" / "Scans" / "History"]


def get_remote_desktop_cache_paths() -> list[Path]:
    local = _local()
    if not local:
        return []
    return [Path(local) / "Microsoft" / "Terminal Server Client" / "Cache"]


def get_font_cache_paths() -> list[Path]:
    windir = os.environ.get("WINDIR", r"C:\Windows")
    return [Path(windir) / "ServiceProfiles" / "LocalService" / "AppData" / "Local" / "FontCache"]


def get_windows_old_path() -> Path | None:
    p = Path("C:/Windows.old")
    return p if p.exists() else None


# Maps target id -> path resolver function
TARGET_PATH_RESOLVERS: dict[str, callable] = {
    "user_temp": get_user_temp_paths,
    "chrome_cache": lambda: get_browser_cache_paths()["chrome"],
    "edge_cache": lambda: get_browser_cache_paths()["edge"],
    "firefox_cache": lambda: get_browser_cache_paths()["firefox"],
    "brave_cache": lambda: get_browser_cache_paths()["brave"],
    "opera_cache": lambda: get_browser_cache_paths()["opera"],
    "thumbnail_cache": lambda: [get_thumbnail_cache_path()] if get_thumbnail_cache_path() else [],
    "icon_cache": get_icon_cache_paths,
    "recent_files": lambda: [get_recent_files_path()] if get_recent_files_path() else [],
    "jump_lists": get_jump_lists_paths,
    "installer_cache": get_installer_cache_paths,
    "inet_cache": get_inet_cache_paths,
    "microsoft_store_cache": get_microsoft_store_cache_paths,
    "gpu_shader_cache": get_gpu_shader_cache_paths,
    "directx_cache": get_directx_cache_paths,
    "discord_cache": get_discord_cache_paths,
    "spotify_cache": get_spotify_cache_paths,
    "steam_cache": get_steam_cache_paths,
    "epic_cache": get_epic_cache_paths,
    "teams_cache": get_teams_cache_paths,
    "slack_cache": get_slack_cache_paths,
    "vscode_cache": get_vscode_cache_paths,
    "npm_cache": get_npm_cache_paths,
    "pip_cache": get_pip_cache_paths,
    "gradle_cache": get_gradle_cache_paths,
    "crash_dumps": get_crash_dumps_paths,
    "windows_logs": get_windows_logs_paths,
    "notifications_cache": get_notifications_cache_paths,
    "search_index_temp": get_search_index_temp_paths,
    "office_cache": get_office_cache_paths,
    "outlook_cache": get_outlook_cache_paths,
    "java_cache": get_java_cache_paths,
    "dotnet_temp": get_dotnet_temp_paths,
    "defender_history": get_defender_history_paths,
    "remote_desktop_cache": get_remote_desktop_cache_paths,
    "font_cache": get_font_cache_paths,
    "windows_old": lambda: [get_windows_old_path()] if get_windows_old_path() else [],
}


def resolve_target_paths(target_id: str) -> list[Path]:
    """Resolve all filesystem paths for a cleanup target."""
    paths: list[Path] = []

    if target_id in TARGET_PATH_RESOLVERS:
        paths.extend(TARGET_PATH_RESOLVERS[target_id]())

    for t in SAFE_CLEAN_TARGETS:
        if t["id"] == target_id and t.get("path"):
            paths.append(Path(t["path"]))

    seen = set()
    result = []
    for p in paths:
        if p and p.exists():
            key = str(p).lower()
            if key not in seen:
                seen.add(key)
                result.append(p)
    return result