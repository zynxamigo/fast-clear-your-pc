"""Internationalization manager with system language detection."""
import ctypes
import json
import locale
from pathlib import Path

from src.config import SETTINGS_FILE
from src.i18n.locales.en import TRANSLATIONS as EN
from src.i18n.locales.pt import TRANSLATIONS as PT

LOCALES = {"en": EN, "pt": PT}
SUPPORTED = ("en", "pt")


def detect_system_language() -> str:
    """Detect Windows display language."""
    try:
        lid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        primary = lid & 0x3FF
        if primary in (0x16, 0x22):  # Portuguese (BR/PT)
            return "pt"
    except Exception:
        pass
    try:
        loc = locale.getdefaultlocale()[0] or "en_US"
        if loc.lower().startswith("pt"):
            return "pt"
    except Exception:
        pass
    return "en"


class I18n:
    """Translation helper with system-language support."""

    def __init__(self, language: str = "system"):
        self._preference = language
        self._callbacks: list = []
        self._load_settings()

    def _load_settings(self):
        if SETTINGS_FILE.exists():
            try:
                data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                self._preference = data.get("language", "system")
            except (json.JSONDecodeError, OSError):
                pass

    def save_settings(self):
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if SETTINGS_FILE.exists():
            try:
                data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        data["language"] = self._preference
        SETTINGS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @property
    def preference(self) -> str:
        return self._preference

    @property
    def active_language(self) -> str:
        if self._preference == "system":
            return detect_system_language()
        return self._preference if self._preference in SUPPORTED else "en"

    def set_language(self, language: str):
        if language in ("system", *SUPPORTED):
            self._preference = language
            self.save_settings()
            for cb in self._callbacks:
                cb()

    def on_change(self, callback):
        self._callbacks.append(callback)

    def t(self, key: str, **kwargs) -> str:
        lang = self.active_language
        text = LOCALES.get(lang, EN).get(key) or EN.get(key) or key
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError):
                return text
        return text

    def get_language_options(self) -> list[tuple[str, str]]:
        return [
            ("system", self.t("lang.system")),
            ("en", self.t("lang.en")),
            ("pt", self.t("lang.pt")),
        ]