"""Proteções de segurança — nunca apaga pastas críticas do sistema."""
import os
from pathlib import Path

# Pastas do Windows que NUNCA podem ser tocadas
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

# Extensões críticas do sistema — nunca apagar
PROTECTED_EXTENSIONS = {
    ".dll", ".sys", ".exe", ".drv", ".ocx", ".cpl",
    ".mui", ".cat", ".inf", ".efi", ".bin", ".reg",
}

# Pastas seguras para limpeza (apenas lixo temporário)
SAFE_CLEAN_TARGETS = [
    {"id": "user_temp", "path": None},
    {"id": "windows_temp", "path": r"C:\Windows\Temp"},
    {"id": "prefetch", "path": r"C:\Windows\Prefetch"},
    {"id": "thumbnail_cache", "path": None},
    {"id": "recycle_bin", "path": None},
    {"id": "chrome_cache", "path": None},
    {"id": "edge_cache", "path": None},
    {"id": "firefox_cache", "path": None},
    {"id": "windows_update_cache", "path": r"C:\Windows\SoftwareDistribution\Download"},
    {"id": "delivery_optimization", "path": r"C:\Windows\SoftwareDistribution\DeliveryOptimization"},
    {"id": "recent_files", "path": None},
    {"id": "error_reports", "path": r"C:\ProgramData\Microsoft\Windows\WER"},
    {"id": "installer_cache", "path": None},
]


def normalize_path(path: str | Path) -> Path:
    """Resolve e normaliza um caminho para comparação segura."""
    try:
        return Path(path).resolve()
    except (OSError, ValueError):
        return Path(os.path.abspath(str(path)))


def is_protected_path(path: str | Path) -> bool:
    """Verifica se o caminho está em área protegida do sistema."""
    try:
        resolved = normalize_path(path)
        resolved_str = str(resolved).lower().rstrip("\\/")
    except Exception:
        return True

    for protected in PROTECTED_DIRS:
        try:
            prot = str(normalize_path(protected)).lower().rstrip("\\/")
            if resolved_str == prot or resolved_str.startswith(prot + "\\"):
                return True
        except Exception:
            continue

    # Bloqueia qualquer pasta chamada system32 em qualquer drive
    parts = [p.lower() for p in resolved.parts]
    if "system32" in parts or "syswow64" in parts:
        return True

    return False


def is_protected_file(path: str | Path) -> bool:
    """Verifica se um arquivo individual é crítico para o sistema."""
    p = Path(path)
    if is_protected_path(p.parent):
        return True
    if p.suffix.lower() in PROTECTED_EXTENSIONS and is_under_windows(p):
        return True
    return False


def is_under_windows(path: Path) -> bool:
    """Verifica se o caminho está dentro de C:\\Windows."""
    try:
        windows = normalize_path(r"C:\Windows")
        resolved = normalize_path(path)
        return str(resolved).lower().startswith(str(windows).lower())
    except Exception:
        return False


def is_safe_to_delete(path: str | Path, user_exclusions: list[str]) -> bool:
    """Decisão final: pode apagar este caminho?"""
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


def get_user_temp_paths() -> list[Path]:
    """Retorna pastas temp do usuário."""
    paths = []
    for env in ("TEMP", "TMP"):
        val = os.environ.get(env)
        if val:
            paths.append(Path(val))
    local = os.environ.get("LOCALAPPDATA")
    if local:
        paths.append(Path(local) / "Temp")
    return list(dict.fromkeys(paths))


def get_browser_cache_paths() -> dict[str, list[Path]]:
    """Retorna caminhos de cache dos navegadores."""
    local = os.environ.get("LOCALAPPDATA", "")
    appdata = os.environ.get("APPDATA", "")
    result = {"chrome": [], "edge": [], "firefox": []}

    if local:
        result["chrome"] = [
            Path(local) / "Google" / "Chrome" / "User Data" / "Default" / "Cache",
            Path(local) / "Google" / "Chrome" / "User Data" / "Default" / "Code Cache",
            Path(local) / "Google" / "Chrome" / "User Data" / "Default" / "GPUCache",
        ]
        result["edge"] = [
            Path(local) / "Microsoft" / "Edge" / "User Data" / "Default" / "Cache",
            Path(local) / "Microsoft" / "Edge" / "User Data" / "Default" / "Code Cache",
        ]

    if appdata:
        profiles = Path(appdata) / "Mozilla" / "Firefox" / "Profiles"
        if profiles.exists():
            for prof in profiles.iterdir():
                if prof.is_dir():
                    result["firefox"].append(prof / "cache2")

    return result


def get_thumbnail_cache_path() -> Path | None:
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "Microsoft" / "Windows" / "Explorer"
    return None


def get_recent_files_path() -> Path | None:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "Microsoft" / "Windows" / "Recent"
    return None


def get_installer_cache_paths() -> list[Path]:
    paths = []
    windir = os.environ.get("WINDIR", r"C:\Windows")
    paths.append(Path(windir) / "Installer" / "$PatchCache$")
    temp = os.environ.get("TEMP")
    if temp:
        paths.append(Path(temp))
    return paths