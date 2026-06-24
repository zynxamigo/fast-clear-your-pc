"""Safe PC cleanup engine."""
import os
import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .safety import (
    SAFE_CLEAN_TARGETS,
    get_recent_files_path,
    get_thumbnail_cache_path,
    is_safe_to_delete,
    resolve_target_paths,
)

COMMAND_TARGETS = {"recycle_bin", "dns_cache", "clipboard_history"}
PATTERN_TARGETS = {"thumbnail_cache", "icon_cache"}


@dataclass
class CleanResult:
    bytes_freed: int = 0
    files_deleted: int = 0
    folders_deleted: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    details: list[dict] = field(default_factory=list)


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _dir_size(path: Path) -> int:
    total = 0
    try:
        for root, _, files in os.walk(path):
            for f in files:
                try:
                    total += (Path(root) / f).stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _delete_file(path: Path, exclusions: list[str], result: CleanResult) -> None:
    if not is_safe_to_delete(path, exclusions):
        result.skipped += 1
        return
    try:
        size = _file_size(path)
        path.unlink()
        result.bytes_freed += size
        result.files_deleted += 1
    except OSError as e:
        result.errors.append(f"{path}: {e}")


def _delete_folder_contents(path: Path, exclusions: list[str], result: CleanResult) -> None:
    if not path.exists():
        return
    if not is_safe_to_delete(path, exclusions):
        result.skipped += 1
        return
    try:
        for item in path.iterdir():
            if item.is_file():
                _delete_file(item, exclusions, result)
            elif item.is_dir():
                if is_safe_to_delete(item, exclusions):
                    size = _dir_size(item)
                    try:
                        shutil.rmtree(item, ignore_errors=False)
                        result.bytes_freed += size
                        result.folders_deleted += 1
                    except OSError as e:
                        result.errors.append(f"{item}: {e}")
                        result.skipped += 1
                else:
                    result.skipped += 1
    except OSError as e:
        result.errors.append(f"{path}: {e}")


def _delete_entire_folder(path: Path, exclusions: list[str], result: CleanResult) -> None:
    """Delete a folder entirely (e.g. Windows.old)."""
    if not path.exists():
        return
    if not is_safe_to_delete(path, exclusions):
        result.skipped += 1
        return
    try:
        size = _dir_size(path)
        shutil.rmtree(path, ignore_errors=False)
        result.bytes_freed += size
        result.folders_deleted += 1
    except OSError as e:
        result.errors.append(f"{path}: {e}")


def _empty_recycle_bin(result: CleanResult) -> None:
    try:
        subprocess.run(
            ["powershell", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
            capture_output=True,
            timeout=120,
        )
        result.details.append({"target": "recycle_bin", "status": "ok"})
    except Exception as e:
        result.errors.append(f"Recycle Bin: {e}")


def _flush_dns(result: CleanResult) -> None:
    try:
        subprocess.run(["ipconfig", "/flushdns"], capture_output=True, timeout=30)
        result.details.append({"target": "dns_cache", "status": "ok"})
    except Exception as e:
        result.errors.append(f"DNS: {e}")


def _clear_clipboard_history(result: CleanResult) -> None:
    try:
        subprocess.run(
            ["powershell", "-Command", "Set-Clipboard -Value $null"],
            capture_output=True,
            timeout=15,
        )
        result.details.append({"target": "clipboard_history", "status": "ok"})
    except Exception as e:
        result.errors.append(f"Clipboard: {e}")


def _clean_pattern_cache(target_id: str, exclusions: list[str], result: CleanResult) -> None:
    thumb_path = get_thumbnail_cache_path()
    if not thumb_path or not thumb_path.exists():
        return
    patterns = ["thumbcache_*.db", "iconcache_*.db"]
    if target_id == "thumbnail_cache":
        patterns = ["thumbcache_*.db"]
    elif target_id == "icon_cache":
        patterns = ["iconcache_*.db"]
    for pattern in patterns:
        for item in thumb_path.glob(pattern):
            _delete_file(item, exclusions, result)


def _clean_recent_files(exclusions: list[str], result: CleanResult) -> None:
    recent = get_recent_files_path()
    if not recent or not recent.exists():
        return
    for item in recent.iterdir():
        if item.suffix.lower() in (".lnk", ".automaticdestinations-ms", ".customdestinations-ms"):
            _delete_file(item, exclusions, result)


def _clean_jump_lists(exclusions: list[str], result: CleanResult) -> None:
    from .safety import get_jump_lists_paths
    for path in get_jump_lists_paths():
        if path.is_dir():
            _delete_folder_contents(path, exclusions, result)


def _scan_target(target_id: str, exclusions: list[str], result: CleanResult) -> None:
    if target_id in COMMAND_TARGETS:
        result.details.append({"target": target_id, "size": "n/a"})
        return

    if target_id in PATTERN_TARGETS:
        thumb = get_thumbnail_cache_path()
        if thumb and thumb.exists():
            patterns = ["thumbcache_*.db"] if target_id == "thumbnail_cache" else ["iconcache_*.db"]
            for pattern in patterns:
                for item in thumb.glob(pattern):
                    if is_safe_to_delete(item, exclusions):
                        result.bytes_freed += _file_size(item)
        return

    if target_id == "recent_files":
        recent = get_recent_files_path()
        if recent and recent.exists():
            for item in recent.iterdir():
                if item.suffix.lower() == ".lnk" and is_safe_to_delete(item, exclusions):
                    result.bytes_freed += _file_size(item)
        return

    if target_id == "jump_lists":
        from .safety import get_jump_lists_paths
        for path in get_jump_lists_paths():
            if path.exists() and is_safe_to_delete(path, exclusions):
                result.bytes_freed += _dir_size(path)
        return

    for path in resolve_target_paths(target_id):
        if not is_safe_to_delete(path, exclusions):
            result.skipped += 1
            continue
        size = _dir_size(path) if path.is_dir() else _file_size(path)
        result.bytes_freed += size
        result.details.append({"target": target_id, "path": str(path), "size": size})


def _clean_target(target_id: str, exclusions: list[str], result: CleanResult) -> None:
    if target_id == "recycle_bin":
        _empty_recycle_bin(result)
        return
    if target_id == "dns_cache":
        _flush_dns(result)
        return
    if target_id == "clipboard_history":
        _clear_clipboard_history(result)
        return
    if target_id in PATTERN_TARGETS:
        _clean_pattern_cache(target_id, exclusions, result)
        return
    if target_id == "recent_files":
        _clean_recent_files(exclusions, result)
        return
    if target_id == "jump_lists":
        _clean_jump_lists(exclusions, result)
        return

    for path in resolve_target_paths(target_id):
        if target_id == "windows_old":
            _delete_entire_folder(path, exclusions, result)
        elif path.is_dir():
            _delete_folder_contents(path, exclusions, result)
        elif path.is_file():
            _delete_file(path, exclusions, result)


class CleanerEngine:
    """Runs cleanup with progress callbacks."""

    def __init__(self, exclusions: list[str] | None = None):
        self.exclusions = exclusions or []
        self._cancel = threading.Event()

    def cancel(self):
        self._cancel.set()

    def scan(
        self,
        selected_targets: list[str],
        progress_cb: Callable[[str, float], None] | None = None,
    ) -> CleanResult:
        result = CleanResult()
        total = max(len(selected_targets), 1)

        for i, target_id in enumerate(selected_targets):
            if self._cancel.is_set():
                break
            if progress_cb:
                progress_cb(target_id, (i + 1) / total)
            _scan_target(target_id, self.exclusions, result)

        return result

    def clean(
        self,
        selected_targets: list[str],
        progress_cb: Callable[[str, float], None] | None = None,
    ) -> CleanResult:
        result = CleanResult()
        total = max(len(selected_targets), 1)

        for i, target_id in enumerate(selected_targets):
            if self._cancel.is_set():
                break
            if progress_cb:
                progress_cb(target_id, (i + 1) / total)
            _clean_target(target_id, self.exclusions, result)

        return result


def format_bytes(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} {unit}"
        size /= 1024
    return f"{size:.1f} PB"