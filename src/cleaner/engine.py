"""Motor de limpeza segura do PC."""
import os
import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .safety import (
    SAFE_CLEAN_TARGETS,
    get_browser_cache_paths,
    get_installer_cache_paths,
    get_recent_files_path,
    get_thumbnail_cache_path,
    get_user_temp_paths,
    is_safe_to_delete,
)


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


def _empty_recycle_bin(result: CleanResult) -> None:
    try:
        subprocess.run(
            ["powershell", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
            capture_output=True,
            timeout=120,
        )
        result.details.append({"target": "recycle_bin", "status": "ok"})
    except Exception as e:
        result.errors.append(f"Lixeira: {e}")


def _clean_thumbnail_cache(exclusions: list[str], result: CleanResult) -> None:
    thumb_path = get_thumbnail_cache_path()
    if not thumb_path or not thumb_path.exists():
        return
    for item in thumb_path.glob("thumbcache_*.db"):
        _delete_file(item, exclusions, result)
    for item in thumb_path.glob("iconcache_*.db"):
        _delete_file(item, exclusions, result)


def _clean_recent_files(exclusions: list[str], result: CleanResult) -> None:
    recent = get_recent_files_path()
    if not recent or not recent.exists():
        return
    for item in recent.iterdir():
        if item.suffix.lower() == ".lnk":
            _delete_file(item, exclusions, result)


def _resolve_target_paths(target_id: str) -> list[Path]:
    paths = []
    if target_id == "user_temp":
        paths.extend(get_user_temp_paths())
    elif target_id == "chrome_cache":
        paths.extend(get_browser_cache_paths()["chrome"])
    elif target_id == "edge_cache":
        paths.extend(get_browser_cache_paths()["edge"])
    elif target_id == "firefox_cache":
        paths.extend(get_browser_cache_paths()["firefox"])
    elif target_id == "thumbnail_cache":
        p = get_thumbnail_cache_path()
        if p:
            paths.append(p)
    elif target_id == "recent_files":
        p = get_recent_files_path()
        if p:
            paths.append(p)
    elif target_id == "installer_cache":
        paths.extend(get_installer_cache_paths())
    else:
        for t in SAFE_CLEAN_TARGETS:
            if t["id"] == target_id and t["path"]:
                paths.append(Path(t["path"]))
    return [p for p in paths if p.exists()]


class CleanerEngine:
    """Executa limpeza com callbacks de progresso."""

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
        """Simula limpeza — apenas calcula espaço recuperável."""
        result = CleanResult()
        total = len(selected_targets)

        for i, target_id in enumerate(selected_targets):
            if self._cancel.is_set():
                break
            if progress_cb:
                progress_cb(f"Analisando: {target_id}", (i + 1) / total)

            if target_id == "recycle_bin":
                result.details.append({"target": target_id, "size": "variável"})
                continue

            for path in _resolve_target_paths(target_id):
                if not is_safe_to_delete(path, self.exclusions):
                    result.skipped += 1
                    continue
                size = _dir_size(path) if path.is_dir() else _file_size(path)
                result.bytes_freed += size
                result.details.append({"target": target_id, "path": str(path), "size": size})

        return result

    def clean(
        self,
        selected_targets: list[str],
        progress_cb: Callable[[str, float], None] | None = None,
    ) -> CleanResult:
        """Executa limpeza real."""
        result = CleanResult()
        total = len(selected_targets)

        for i, target_id in enumerate(selected_targets):
            if self._cancel.is_set():
                break
            if progress_cb:
                progress_cb(f"Limpando: {target_id}", (i + 1) / total)

            if target_id == "recycle_bin":
                _empty_recycle_bin(result)
                continue
            if target_id == "thumbnail_cache":
                _clean_thumbnail_cache(self.exclusions, result)
                continue
            if target_id == "recent_files":
                _clean_recent_files(self.exclusions, result)
                continue

            for path in _resolve_target_paths(target_id):
                if path.is_dir():
                    _delete_folder_contents(path, self.exclusions, result)
                elif path.is_file():
                    _delete_file(path, self.exclusions, result)

        return result


def format_bytes(size: int) -> str:
    """Formata bytes em unidade legível."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} {unit}"
        size /= 1024
    return f"{size:.1f} PB"