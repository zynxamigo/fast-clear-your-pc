#!/usr/bin/env python3
"""PC Cleaner Macro — Limpeza segura + Macros do sistema."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.gui.app import PCCleanerApp


def main():
    app = PCCleanerApp()
    app.run()


if __name__ == "__main__":
    main()