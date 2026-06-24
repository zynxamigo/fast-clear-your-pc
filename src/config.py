"""Configurações globais do PC Cleaner Macro."""
from pathlib import Path

APP_NAME = "PC Cleaner Macro"
APP_VERSION = "1.2.0"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EXCLUSIONS_FILE = DATA_DIR / "exclusions.json"
MACROS_FILE = DATA_DIR / "macros.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)