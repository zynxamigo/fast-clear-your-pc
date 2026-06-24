# Fast Clear Your PC (PC Cleaner Macro)

A **safe Windows cleanup** app with **system macros** (Android MacroDroid style). Removes temporary junk without touching critical folders like `System32`.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Windows](https://img.shields.io/badge/Windows-10%2F11-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## Features

### Safe Cleanup
- **46 cleanup options** — temp files, browser/app/dev caches, logs, dumps and more
- **Never deletes** `System32`, `SysWOW64`, `Windows`, `Program Files` or other critical paths
- Blocks deletion of DLLs, drivers (`.sys`) and system executables
- Shows **how much space was freed** after cleanup

### Custom Exclusions
- Protect folders, files or entire apps from cleanup
- Add them in the **Exclusions** tab — they will never be affected

### System Macros (Android-style)
**50+ automation actions**, including:
- Run PowerShell / CMD / batch commands
- Open apps, URLs, folders
- Kill / close processes
- Create, delete, copy, move, rename, zip files and folders
- Edit Windows Registry
- Environment variables
- Shortcuts and wallpaper
- Windows services (start/stop/restart)
- Notifications and message boxes
- Lock, sleep, hibernate, shutdown, restart, logoff
- Clipboard, DNS flush, Wi-Fi toggle
- Screenshots, volume control, dark mode
- Startup programs, scheduled tasks
- Download files, HTTP requests, send keystrokes
- And much more...

### Multi-Language
- **English**
- **Português**
- **System Language** — follows your Windows display language automatically

---

## Download & Install

### Option 1 — Download from GitHub (recommended)

1. Open the repository:
2. Click the green **Code** button
3. Select **Download ZIP**
4. Extract to a folder, e.g.:
5. Done! You only need Python installed.
### Option 2 — Clone with Git

```bash
git clone https://github.com/zynxamigo/fast-clear-your-pc.git
cd fast-clear-your-pc
```

---

## Requirements

- **Windows 10 or 11**
- **Python 3.10+** — [Download Python](https://www.python.org/downloads/)

> During Python installation, check **"Add Python to PATH"**.

---

## How to Use

### Launch the app

**Easy way:** double-click `run.bat`

**From terminal:**
```bash
cd fast-clear-your-pc
python main.py
```

### Change language

Use the dropdown at the top of the window:
- **System Language** — auto-detects from Windows
- **English**
- **Português**

You can also change it in the **Settings** tab.

### Run cleanup

1. Open the **Cleanup** tab
2. Check what you want to clean (or leave all checked)
3. Click **Analyze space** to preview recoverable space
4. Click **Clean now** to run
5. See the **space freed** report on screen

### Protect folders/apps

1. Go to **Exclusions**
2. Click **Add folder**, **Add file** or **Add app**
3. Select what to protect
4. Those items will never be deleted during cleanup

### Create macros

1. Go to **Macros**
2. Click **New macro**
3. Name it and pick a trigger (manual, on startup, scheduled, etc.)
4. Select an action from **50+ options** (e.g. `create_folder`, `open_app`, `shutdown_pc`)
5. Fill in parameters and click **Add action**
6. Click **Save macro**
7. Select the macro and click **Run**

---

## Safety Protections

The app **always protects** automatically:

| Protected | Reason |
|-----------|--------|
| `C:\Windows\System32` | Windows core — **mandatory** |
| `C:\Windows\SysWOW64` | 32-bit compatibility |
| `C:\Windows` | Operating system |
| `C:\Program Files` | Installed programs |
| `.dll`, `.sys`, `.drv` | Libraries and drivers |
| Exclusion list items | User choice |

---

## Project Structure

```
fast-clear-your-pc/
├── main.py              # Entry point
├── run.bat              # Windows shortcut
├── requirements.txt
├── README.md
├── data/                # Saved settings
│   ├── exclusions.json
│   ├── macros.json
│   └── settings.json
└── src/
    ├── i18n/            # Multi-language support
    ├── cleaner/         # Cleanup engine
    ├── macro/           # Macro engine (50+ actions)
    └── gui/             # Graphical interface
```

---

## Publish to GitHub (for developers)

```bash
cd fast-clear-your-pc
git remote add origin https://github.com/zynxamigo/fast-clear-your-pc.git
git branch -M main
git push -u origin main
```

---

## License

MIT — free to use.

---

## Support

Found a bug? Open an [Issue on GitHub](https://github.com/zynxamigo/fast-clear-your-pc/issues).
