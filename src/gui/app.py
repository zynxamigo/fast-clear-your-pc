"""Main GUI — PC Cleaner Macro with multi-language support."""
import json
import threading
import tkinter as tk
import uuid
from tkinter import filedialog, messagebox, ttk

from src.cleaner.engine import CleanerEngine, format_bytes
from src.cleaner.safety import SAFE_CLEAN_TARGETS, is_protected_path
from src.config import EXCLUSIONS_FILE, MACROS_FILE
from src.i18n import I18n
from src.macro.actions import (
    ACTION_DEFINITIONS,
    EXE_BROWSE_PARAMS,
    FILE_BROWSE_PARAMS,
    SOUND_BROWSE_PARAMS,
    TRIGGER_IDS,
)
from src.macro.sounds import WINDOWS_SOUND_EVENTS
from src.macro.engine import Macro, MacroAction, MacroEngine


class PCCleanerApp:
    """Main app with Cleanup, Exclusions, Macros and Settings tabs."""

    def __init__(self):
        self.i18n = I18n()
        self.root = tk.Tk()
        self.root.geometry("920x680")
        self.root.minsize(820, 580)

        self.exclusions = self._load_exclusions()
        self.macro_engine = MacroEngine(MACROS_FILE, self.i18n)
        self.cleaner = CleanerEngine(self.exclusions)
        self.target_vars: dict[str, tk.BooleanVar] = {}
        self.target_checkboxes: list[tuple[str, ttk.Checkbutton]] = []
        self._action_key_to_label: dict[str, str] = {}
        self._label_to_action_key: dict[str, str] = {}

        self._labels: dict[str, tk.Widget] = {}
        self._buttons: dict[str, ttk.Button] = {}
        self._frames: dict[str, ttk.LabelFrame] = {}
        self.notebook: ttk.Notebook | None = None

        self._setup_style()
        self._build_top_bar()
        self._build_ui()
        self.i18n.on_change(self._apply_language)
        self._apply_language()

    def _t(self, key: str, **kwargs) -> str:
        return self.i18n.t(key, **kwargs)

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Header.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Success.TLabel", font=("Segoe UI", 12, "bold"), foreground="#2e7d32")
        style.configure("Danger.TLabel", foreground="#c62828")

    def _load_exclusions(self) -> list[str]:
        if EXCLUSIONS_FILE.exists():
            try:
                data = json.loads(EXCLUSIONS_FILE.read_text(encoding="utf-8"))
                return data.get("paths", [])
            except json.JSONDecodeError:
                pass
        return []

    def _save_exclusions(self):
        EXCLUSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        EXCLUSIONS_FILE.write_text(
            json.dumps({"paths": self.exclusions}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _build_top_bar(self):
        bar = ttk.Frame(self.root, padding=(8, 6))
        bar.pack(fill=tk.X)
        self._labels["lang_label"] = ttk.Label(bar, text="")
        self._labels["lang_label"].pack(side=tk.LEFT)
        self.lang_var = tk.StringVar()
        self.lang_combo = ttk.Combobox(bar, textvariable=self.lang_var, state="readonly", width=22)
        self.lang_combo.pack(side=tk.LEFT, padx=6)
        self.lang_combo.bind("<<ComboboxSelected>>", self._on_language_change)
        self._lang_display_to_code: dict[str, str] = {}
        self._lang_code_to_display: dict[str, str] = {}

    def _on_language_change(self, _event=None):
        code = self._lang_display_to_code.get(self.lang_var.get(), "system")
        self.i18n.set_language(code)
        if hasattr(self, "settings_lang_var"):
            self.settings_lang_var.set(code)

    def _build_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self._build_clean_tab()
        self._build_exclusions_tab()
        self._build_macros_tab()
        self._build_settings_tab()
        self._build_about_tab()

    def _apply_language(self):
        self.root.title(self._t("app.title"))
        self._labels["lang_label"].config(text=self._t("lang.label"))

        self._lang_display_to_code.clear()
        self._lang_code_to_display.clear()
        displays = []
        for code, label in self.i18n.get_language_options():
            self._lang_display_to_code[label] = code
            self._lang_code_to_display[code] = label
            displays.append(label)
        self.lang_combo["values"] = displays
        self.lang_var.set(self._lang_code_to_display.get(self.i18n.preference, displays[0]))

        if hasattr(self, "_settings_radio_labels"):
            for code, rb in self._settings_radio_labels.items():
                rb.config(text=self._lang_code_to_display.get(code, code))

        if self.notebook:
            self.notebook.tab(0, text=f"  {self._t('tab.clean')}  ")
            self.notebook.tab(1, text=f"  {self._t('tab.exclusions')}  ")
            self.notebook.tab(2, text=f"  {self._t('tab.macros')}  ")
            self.notebook.tab(3, text=f"  {self._t('tab.settings')}  ")
            self.notebook.tab(4, text=f"  {self._t('tab.about')}  ")

        for key, widget in self._labels.items():
            mapping = {
                "clean_title": "clean.title",
                "clean_sub": "clean.subtitle",
                "status": "clean.ready",
                "excl_title": "excl.title",
                "excl_sub": "excl.subtitle",
                "excl_auto": "excl.auto_protect",
                "macro_title": "macro.title",
                "macro_sub": "macro.subtitle",
                "macro_name_lbl": "macro.name",
                "macro_trigger_lbl": "macro.trigger",
                "macro_actions_lbl": "macro.actions",
                "macro_log_lbl": "macro.log",
                "macro_search_lbl": "macro.search",
                "settings_title": "settings.title",
                "settings_lang": "settings.language",
                "settings_hint": "settings.language_hint",
                "about_text": "about.text",
            }
            if key in mapping:
                widget.config(text=self._t(mapping[key]))

        for key, widget in self._buttons.items():
            mapping = {
                "scan": "clean.scan", "clean": "clean.run",
                "sel_all": "clean.select_all", "desel_all": "clean.deselect_all",
                "excl_folder": "excl.add_folder", "excl_file": "excl.add_file",
                "excl_app": "excl.add_app", "excl_remove": "excl.remove",
                "macro_new": "macro.new", "macro_run": "macro.run", "macro_del": "macro.delete",
                "macro_add": "macro.add_action", "macro_save": "macro.save",
                "tpl_app_sound": "macro.tpl_app_sound",
                "tpl_plug_sound": "macro.tpl_plug_sound",
                "tpl_unplug_sound": "macro.tpl_unplug_sound",
            }
            if key in mapping:
                widget.config(text=self._t(mapping[key]))

        for key, widget in self._frames.items():
            mapping = {
                "clean_what": "clean.what",
                "excl_list": "excl.list",
                "macro_my": "macro.my_macros",
                "macro_editor": "macro.editor",
            }
            if key in mapping:
                widget.config(text=self._t(mapping[key]))

        for tid, cb in self.target_checkboxes:
            cb.config(text=self._t(f"target.{tid}"))

        self._rebuild_action_combo()
        self._rebuild_trigger_combo()
        self.macro_engine.i18n = self.i18n

    def _rebuild_action_combo(self):
        self._action_key_to_label.clear()
        self._label_to_action_key.clear()
        self._all_action_labels = []
        for key in sorted(ACTION_DEFINITIONS.keys()):
            label = self._t(f"action.{key}")
            self._action_key_to_label[key] = label
            self._label_to_action_key[label] = key
            self._all_action_labels.append(label)
        if hasattr(self, "action_combo"):
            self._filter_action_combo()

    def _filter_action_combo(self):
        if not hasattr(self, "_all_action_labels"):
            return
        query = self.action_search_var.get().lower().strip() if hasattr(self, "action_search_var") else ""
        current_key = self._get_selected_action_key()
        if query:
            labels = [l for l in self._all_action_labels if query in l.lower() or query in self._label_to_action_key.get(l, "")]
        else:
            labels = self._all_action_labels
        self.action_combo["values"] = labels
        if current_key and current_key in self._action_key_to_label:
            lbl = self._action_key_to_label[current_key]
            if lbl in labels:
                self.action_type_var.set(lbl)

    def _rebuild_trigger_combo(self):
        if hasattr(self, "trigger_combo"):
            labels = [self._t(f"trigger.{t}") for t in TRIGGER_IDS]
            self._trigger_labels = dict(zip(TRIGGER_IDS, labels))
            self._trigger_keys = {v: k for k, v in self._trigger_labels.items()}
            current = self.macro_trigger_var.get()
            self.trigger_combo["values"] = labels
            if current in TRIGGER_IDS:
                self.macro_trigger_var.set(self._trigger_labels[current])

    def _get_selected_action_key(self) -> str | None:
        label = self.action_type_var.get()
        return self._label_to_action_key.get(label)

    def _get_selected_trigger_key(self) -> str:
        label = self.macro_trigger_var.get()
        if hasattr(self, "_trigger_keys"):
            return self._trigger_keys.get(label, "manual")
        return "manual"

    # ── Cleanup tab ──────────────────────────────────────────

    def _build_clean_tab(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Cleanup")

        self._labels["clean_title"] = ttk.Label(frame, style="Title.TLabel")
        self._labels["clean_title"].pack(anchor=tk.W)
        self._labels["clean_sub"] = ttk.Label(frame, wraplength=860)
        self._labels["clean_sub"].pack(anchor=tk.W, pady=(0, 10))

        self._frames["clean_what"] = ttk.LabelFrame(frame, padding=8)
        self._frames["clean_what"].pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(self._frames["clean_what"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self._frames["clean_what"], orient=tk.VERTICAL, command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        risky_defaults_off = {"windows_old"}
        for target in SAFE_CLEAN_TARGETS:
            var = tk.BooleanVar(value=target["id"] not in risky_defaults_off)
            self.target_vars[target["id"]] = var
            cb = ttk.Checkbutton(inner, variable=var)
            cb.pack(anchor=tk.W, pady=2)
            self.target_checkboxes.append((target["id"], cb))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        self._buttons["scan"] = ttk.Button(btn_frame, command=self._scan)
        self._buttons["scan"].pack(side=tk.LEFT, padx=4)
        self._buttons["clean"] = ttk.Button(btn_frame, command=self._clean)
        self._buttons["clean"].pack(side=tk.LEFT, padx=4)
        self._buttons["sel_all"] = ttk.Button(btn_frame, command=self._select_all)
        self._buttons["sel_all"].pack(side=tk.LEFT, padx=4)
        self._buttons["desel_all"] = ttk.Button(btn_frame, command=self._deselect_all)
        self._buttons["desel_all"].pack(side=tk.LEFT, padx=4)

        self.progress = ttk.Progressbar(frame, mode="determinate")
        self.progress.pack(fill=tk.X, pady=4)
        self._labels["status"] = ttk.Label(frame)
        self._labels["status"].pack(anchor=tk.W)
        self.result_label = ttk.Label(frame, text="", style="Success.TLabel")
        self.result_label.pack(anchor=tk.W, pady=4)
        self.log_text = tk.Text(frame, height=8, wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=4)

    def _get_selected_targets(self) -> list[str]:
        return [tid for tid, var in self.target_vars.items() if var.get()]

    def _select_all(self):
        for var in self.target_vars.values():
            var.set(True)

    def _deselect_all(self):
        for var in self.target_vars.values():
            var.set(False)

    def _log(self, msg: str):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def _scan(self):
        targets = self._get_selected_targets()
        if not targets:
            messagebox.showwarning(self._t("warn.title"), self._t("clean.warn_select"))
            return
        self.log_text.delete("1.0", tk.END)
        self.result_label.config(text="")
        self.progress["value"] = 0
        self._labels["status"].config(text=self._t("clean.analyzing"))

        def run():
            result = CleanerEngine(self.exclusions).scan(targets, lambda m, p: self.root.after(0, lambda: self._update_progress(m, p)))
            self.root.after(0, lambda: self._show_scan_result(result))

        threading.Thread(target=run, daemon=True).start()

    def _clean(self):
        targets = self._get_selected_targets()
        if not targets:
            messagebox.showwarning(self._t("warn.title"), self._t("clean.warn_select_clean"))
            return
        if not messagebox.askyesno(self._t("clean.confirm_title"), self._t("clean.confirm_msg")):
            return
        self.log_text.delete("1.0", tk.END)
        self.result_label.config(text="")
        self.progress["value"] = 0
        self._labels["status"].config(text=self._t("clean.cleaning"))

        def run():
            result = CleanerEngine(self.exclusions).clean(targets, lambda m, p: self.root.after(0, lambda: self._update_progress(m, p)))
            self.root.after(0, lambda: self._show_clean_result(result))

        threading.Thread(target=run, daemon=True).start()

    def _update_progress(self, msg: str, pct: float):
        self._labels["status"].config(text=msg)
        self.progress["value"] = pct * 100

    def _show_scan_result(self, result):
        self._labels["status"].config(text=self._t("clean.done"))
        self.progress["value"] = 100
        self.result_label.config(text=self._t("clean.recoverable", size=format_bytes(result.bytes_freed)))
        self._log(self._t("clean.log_scan", size=format_bytes(result.bytes_freed)))
        self._log(self._t("clean.log_skipped", count=result.skipped))

    def _show_clean_result(self, result):
        self._labels["status"].config(text=self._t("clean.done_clean"))
        self.progress["value"] = 100
        self.result_label.config(text=self._t("clean.freed", size=format_bytes(result.bytes_freed)))
        self._log(self._t("clean.log_files", count=result.files_deleted))
        self._log(self._t("clean.log_folders", count=result.folders_deleted))
        self._log(self._t("clean.log_freed", size=format_bytes(result.bytes_freed)))
        self._log(self._t("clean.log_skipped", count=result.skipped))
        if result.errors:
            self._log(self._t("clean.log_errors", count=len(result.errors)))
            for err in result.errors[:10]:
                self._log(f"  - {err}")
        messagebox.showinfo(
            self._t("clean.result_title"),
            self._t("clean.result_msg", size=format_bytes(result.bytes_freed), files=result.files_deleted, folders=result.folders_deleted),
        )

    # ── Exclusions tab ───────────────────────────────────────

    def _build_exclusions_tab(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Exclusions")

        self._labels["excl_title"] = ttk.Label(frame, style="Title.TLabel")
        self._labels["excl_title"].pack(anchor=tk.W)
        self._labels["excl_sub"] = ttk.Label(frame, wraplength=860)
        self._labels["excl_sub"].pack(anchor=tk.W, pady=(0, 10))

        self._frames["excl_list"] = ttk.LabelFrame(frame, padding=8)
        self._frames["excl_list"].pack(fill=tk.BOTH, expand=True)
        self.excl_listbox = tk.Listbox(self._frames["excl_list"], font=("Segoe UI", 10))
        scroll = ttk.Scrollbar(self._frames["excl_list"], orient=tk.VERTICAL, command=self.excl_listbox.yview)
        self.excl_listbox.configure(yscrollcommand=scroll.set)
        self.excl_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._refresh_exclusions_list()

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        self._buttons["excl_folder"] = ttk.Button(btn_frame, command=self._add_exclusion_folder)
        self._buttons["excl_folder"].pack(side=tk.LEFT, padx=4)
        self._buttons["excl_file"] = ttk.Button(btn_frame, command=self._add_exclusion_file)
        self._buttons["excl_file"].pack(side=tk.LEFT, padx=4)
        self._buttons["excl_app"] = ttk.Button(btn_frame, command=self._add_exclusion_app)
        self._buttons["excl_app"].pack(side=tk.LEFT, padx=4)
        self._buttons["excl_remove"] = ttk.Button(btn_frame, command=self._remove_exclusion)
        self._buttons["excl_remove"].pack(side=tk.LEFT, padx=4)

        self._labels["excl_auto"] = ttk.Label(frame, style="Danger.TLabel")
        self._labels["excl_auto"].pack(anchor=tk.W)

    def _refresh_exclusions_list(self):
        self.excl_listbox.delete(0, tk.END)
        for path in self.exclusions:
            self.excl_listbox.insert(tk.END, path)

    def _add_exclusion_folder(self):
        path = filedialog.askdirectory(title=self._t("excl.dialog_folder"))
        if path:
            self._add_exclusion(path)

    def _add_exclusion_file(self):
        path = filedialog.askopenfilename(title=self._t("excl.dialog_file"))
        if path:
            self._add_exclusion(path)

    def _add_exclusion_app(self):
        path = filedialog.askopenfilename(
            title=self._t("excl.dialog_app"),
            filetypes=[(self._t("excl.filetypes_exe"), "*.exe"), (self._t("excl.filetypes_all"), "*.*")],
        )
        if path:
            self._add_exclusion(str(__import__("pathlib").Path(path).parent))

    def _add_exclusion(self, path: str):
        if is_protected_path(path):
            messagebox.showinfo(self._t("excl.already"), self._t("excl.already_msg"))
            return
        if path not in self.exclusions:
            self.exclusions.append(path)
            self._save_exclusions()
            self._refresh_exclusions_list()
            self.cleaner = CleanerEngine(self.exclusions)

    def _remove_exclusion(self):
        sel = self.excl_listbox.curselection()
        if not sel:
            return
        del self.exclusions[sel[0]]
        self._save_exclusions()
        self._refresh_exclusions_list()
        self.cleaner = CleanerEngine(self.exclusions)

    # ── Macros tab ───────────────────────────────────────────

    def _build_macros_tab(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Macros")

        self._labels["macro_title"] = ttk.Label(frame, style="Title.TLabel")
        self._labels["macro_title"].pack(anchor=tk.W)
        self._labels["macro_sub"] = ttk.Label(frame, wraplength=860)
        self._labels["macro_sub"].pack(anchor=tk.W, pady=(0, 10))

        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(paned, padding=8)
        self._frames["macro_my"] = left
        paned.add(left, weight=1)

        self.macro_listbox = tk.Listbox(left, font=("Segoe UI", 10))
        self.macro_listbox.pack(fill=tk.BOTH, expand=True)
        self.macro_listbox.bind("<<ListboxSelect>>", self._on_macro_select)

        macro_btns = ttk.Frame(left)
        macro_btns.pack(fill=tk.X, pady=4)
        self._buttons["macro_new"] = ttk.Button(macro_btns, command=self._new_macro)
        self._buttons["macro_new"].pack(side=tk.LEFT, padx=2)
        self._buttons["macro_run"] = ttk.Button(macro_btns, command=self._run_macro)
        self._buttons["macro_run"].pack(side=tk.LEFT, padx=2)
        self._buttons["macro_del"] = ttk.Button(macro_btns, command=self._delete_macro)
        self._buttons["macro_del"].pack(side=tk.LEFT, padx=2)

        right = ttk.LabelFrame(paned, padding=8)
        self._frames["macro_editor"] = right
        paned.add(right, weight=2)

        self._labels["macro_name_lbl"] = ttk.Label(right)
        self._labels["macro_name_lbl"].grid(row=0, column=0, sticky=tk.W, pady=2)
        self.macro_name_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.macro_name_var, width=40).grid(row=0, column=1, sticky=tk.W, pady=2)

        self._labels["macro_trigger_lbl"] = ttk.Label(right)
        self._labels["macro_trigger_lbl"].grid(row=1, column=0, sticky=tk.W, pady=2)
        self.macro_trigger_var = tk.StringVar()
        self.trigger_combo = ttk.Combobox(right, textvariable=self.macro_trigger_var, state="readonly", width=28)
        self.trigger_combo.grid(row=1, column=1, sticky=tk.W, pady=2)

        self._labels["macro_actions_lbl"] = ttk.Label(right, style="Header.TLabel")
        self._labels["macro_actions_lbl"].grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(8, 2))

        action_frame = ttk.Frame(right)
        action_frame.grid(row=3, column=0, columnspan=2, sticky=tk.NSEW)
        self.action_listbox = tk.Listbox(action_frame, height=6, font=("Consolas", 9))
        self.action_listbox.pack(fill=tk.BOTH, expand=True)

        search_frame = ttk.Frame(right)
        search_frame.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=4)
        self._labels["macro_search_lbl"] = ttk.Label(search_frame)
        self._labels["macro_search_lbl"].pack(side=tk.LEFT)
        self.action_search_var = tk.StringVar()
        self.action_search_var.trace_add("write", lambda *_: self._filter_action_combo())
        ttk.Entry(search_frame, textvariable=self.action_search_var, width=30).pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)

        tpl_frame = ttk.Frame(right)
        tpl_frame.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=2)
        self._buttons["tpl_app_sound"] = ttk.Button(tpl_frame, command=self._template_app_with_sound)
        self._buttons["tpl_app_sound"].pack(side=tk.LEFT, padx=2)
        self._buttons["tpl_plug_sound"] = ttk.Button(tpl_frame, command=self._template_plug_sound)
        self._buttons["tpl_plug_sound"].pack(side=tk.LEFT, padx=2)
        self._buttons["tpl_unplug_sound"] = ttk.Button(tpl_frame, command=self._template_unplug_sound)
        self._buttons["tpl_unplug_sound"].pack(side=tk.LEFT, padx=2)

        add_frame = ttk.Frame(right)
        add_frame.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=4)

        self.action_type_var = tk.StringVar()
        self.action_combo = ttk.Combobox(add_frame, textvariable=self.action_type_var, state="readonly", width=28)
        self.action_combo.pack(side=tk.LEFT, padx=2)
        self.action_combo.bind("<<ComboboxSelected>>", self._on_action_type_change)

        self.action_params_frame = ttk.Frame(add_frame)
        self.action_params_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.action_param_vars: dict[str, tk.StringVar] = {}

        self._buttons["macro_add"] = ttk.Button(add_frame, command=self._add_action_to_macro)
        self._buttons["macro_add"].pack(side=tk.LEFT, padx=4)
        self._buttons["macro_save"] = ttk.Button(add_frame, command=self._save_macro)
        self._buttons["macro_save"].pack(side=tk.LEFT, padx=4)

        self._labels["macro_log_lbl"] = ttk.Label(right, style="Header.TLabel")
        self._labels["macro_log_lbl"].grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=(8, 2))
        self.macro_log = tk.Text(right, height=5, wrap=tk.WORD, font=("Consolas", 9))
        self.macro_log.grid(row=8, column=0, columnspan=2, sticky=tk.NSEW)
        right.rowconfigure(8, weight=1)
        right.columnconfigure(1, weight=1)

        self._current_macro_id: str | None = None
        self._current_actions: list[dict] = []
        self._refresh_macro_list()

    def _refresh_macro_list(self):
        self.macro_listbox.delete(0, tk.END)
        for m in self.macro_engine.macros:
            status = "+" if m.enabled else "-"
            trigger = self._t(f"trigger.{m.trigger}") if m.trigger in TRIGGER_IDS else m.trigger
            self.macro_listbox.insert(tk.END, f"{status} {m.name} ({trigger})")

    def _new_macro(self):
        self._current_macro_id = str(uuid.uuid4())[:8]
        self.macro_name_var.set(self._t("macro.new_default"))
        if hasattr(self, "_trigger_labels"):
            self.macro_trigger_var.set(self._trigger_labels["manual"])
        self._current_actions = []
        self.action_listbox.delete(0, tk.END)
        self.macro_log.delete("1.0", tk.END)

    def _on_macro_select(self, _event=None):
        sel = self.macro_listbox.curselection()
        if not sel:
            return
        macro = self.macro_engine.macros[sel[0]]
        self._current_macro_id = macro.id
        self.macro_name_var.set(macro.name)
        if hasattr(self, "_trigger_labels") and macro.trigger in self._trigger_labels:
            self.macro_trigger_var.set(self._trigger_labels[macro.trigger])
        self._current_actions = [{"action_type": a.action_type, "params": a.params} for a in macro.actions]
        self.action_listbox.delete(0, tk.END)
        for a in self._current_actions:
            label = self._t(f"action.{a['action_type']}")
            self.action_listbox.insert(tk.END, f"{label}: {a['params']}")

    def _browse_param(self, param: str, var: tk.StringVar):
        if param in SOUND_BROWSE_PARAMS:
            path = filedialog.askopenfilename(
                title=self._t("macro.browse_sound"),
                filetypes=[(self._t("macro.filetypes_sound"), "*.wav *.mp3 *.ogg"), (self._t("excl.filetypes_all"), "*.*")],
            )
        elif param in EXE_BROWSE_PARAMS and self._get_selected_action_key() in ("open_app", "open_app_with_sound"):
            path = filedialog.askopenfilename(
                title=self._t("macro.browse_app"),
                filetypes=[(self._t("excl.filetypes_exe"), "*.exe"), (self._t("excl.filetypes_all"), "*.*")],
            )
        else:
            path = filedialog.askopenfilename(title=self._t("macro.browse_file"))
        if path:
            var.set(path)

    def _on_action_type_change(self, _event=None):
        for w in self.action_params_frame.winfo_children():
            w.destroy()
        self.action_param_vars.clear()
        action_key = self._get_selected_action_key()
        if not action_key or action_key not in ACTION_DEFINITIONS:
            return
        for i, param in enumerate(ACTION_DEFINITIONS[action_key]):
            col = i * 3
            ttk.Label(self.action_params_frame, text=f"{param}:").grid(row=0, column=col, padx=2)
            var = tk.StringVar()
            self.action_param_vars[param] = var
            if param == "sound_event":
                combo = ttk.Combobox(
                    self.action_params_frame, textvariable=var,
                    values=list(WINDOWS_SOUND_EVENTS.keys()), width=16,
                )
                combo.grid(row=0, column=col + 1, padx=2)
                if action_key == "set_device_connect_sound":
                    var.set("device_connect")
                elif action_key == "set_device_disconnect_sound":
                    var.set("device_disconnect")
            elif param == "mode":
                ttk.Combobox(
                    self.action_params_frame, textvariable=var,
                    values=["simultaneous", "sound_first", "app_first"], width=14,
                ).grid(row=0, column=col + 1, padx=2)
                var.set("simultaneous")
            else:
                ttk.Entry(self.action_params_frame, textvariable=var, width=14).grid(row=0, column=col + 1, padx=2)
            if param in FILE_BROWSE_PARAMS or param in SOUND_BROWSE_PARAMS:
                ttk.Button(
                    self.action_params_frame, text="...",
                    width=2, command=lambda v=var, p=param: self._browse_param(p, v),
                ).grid(row=0, column=col + 2, padx=1)

    def _template_app_with_sound(self):
        self.macro_name_var.set(self._t("macro.tpl_app_sound_name"))
        self._current_actions = [{
            "action_type": "open_app_with_sound",
            "params": {"path": "C:\\Windows\\notepad.exe", "sound_path": r"C:\Windows\Media\Windows Notify.wav", "mode": "sound_first", "delay_ms": "300"},
        }]
        self.action_listbox.delete(0, tk.END)
        self.action_listbox.insert(tk.END, self._t("action.open_app_with_sound") + ": notepad + sound")

    def _template_plug_sound(self):
        self.macro_name_var.set(self._t("macro.tpl_plug_name"))
        self._current_actions = [{
            "action_type": "set_device_connect_sound",
            "params": {"wav_path": r"C:\Windows\Media\Windows Hardware Insert.wav"},
        }]
        self.action_listbox.delete(0, tk.END)
        self.action_listbox.insert(tk.END, self._t("action.set_device_connect_sound"))

    def _template_unplug_sound(self):
        self.macro_name_var.set(self._t("macro.tpl_unplug_name"))
        self._current_actions = [{
            "action_type": "set_device_disconnect_sound",
            "params": {"wav_path": r"C:\Windows\Media\Windows Hardware Remove.wav"},
        }]
        self.action_listbox.delete(0, tk.END)
        self.action_listbox.insert(tk.END, self._t("action.set_device_disconnect_sound"))

    def _add_action_to_macro(self):
        action_key = self._get_selected_action_key()
        if not action_key:
            return
        params = {k: v.get() for k, v in self.action_param_vars.items()}
        action = {"action_type": action_key, "params": params}
        self._current_actions.append(action)
        label = self._t(f"action.{action_key}")
        self.action_listbox.insert(tk.END, f"{label}: {params}")

    def _save_macro(self):
        name = self.macro_name_var.get().strip()
        if not name:
            messagebox.showwarning(self._t("warn.title"), self._t("macro.warn_name"))
            return
        if not self._current_actions:
            messagebox.showwarning(self._t("warn.title"), self._t("macro.warn_actions"))
            return
        macro_id = self._current_macro_id or str(uuid.uuid4())[:8]
        actions = [MacroAction(**a) for a in self._current_actions]
        macro = Macro(id=macro_id, name=name, trigger=self._get_selected_trigger_key(), actions=actions)
        existing = self.macro_engine.get_macro(macro_id)
        if existing:
            self.macro_engine.macros = [macro if m.id == macro_id else m for m in self.macro_engine.macros]
        else:
            self.macro_engine.add_macro(macro)
        self.macro_engine.save()
        self._refresh_macro_list()
        messagebox.showinfo(self._t("macro.saved"), self._t("macro.saved_msg", name=name))

    def _run_macro(self):
        sel = self.macro_listbox.curselection()
        if not sel:
            messagebox.showwarning(self._t("warn.title"), self._t("macro.warn_select"))
            return
        macro = self.macro_engine.macros[sel[0]]
        self.macro_log.delete("1.0", tk.END)
        self.macro_log.insert(tk.END, self._t("macro.running", name=macro.name) + "\n")

        def run():
            result = self.macro_engine.execute(macro, lambda msg: self.root.after(0, lambda m=msg: self.macro_log.insert(tk.END, m + "\n")))
            status = self._t("macro.success") if result.success else self._t("macro.with_errors")
            self.root.after(0, lambda: self.macro_log.insert(tk.END, f"\n--- {status} ---\n"))

        threading.Thread(target=run, daemon=True).start()

    def _delete_macro(self):
        sel = self.macro_listbox.curselection()
        if not sel:
            return
        macro = self.macro_engine.macros[sel[0]]
        if messagebox.askyesno(self._t("macro.confirm_title"), self._t("macro.confirm_delete", name=macro.name)):
            self.macro_engine.remove_macro(macro.id)
            self._refresh_macro_list()

    # ── Settings tab ─────────────────────────────────────────

    def _build_settings_tab(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Settings")

        self._labels["settings_title"] = ttk.Label(frame, style="Title.TLabel")
        self._labels["settings_title"].pack(anchor=tk.W)
        self._labels["settings_lang"] = ttk.Label(frame, style="Header.TLabel")
        self._labels["settings_lang"].pack(anchor=tk.W, pady=(10, 4))
        self._labels["settings_hint"] = ttk.Label(frame, wraplength=860)
        self._labels["settings_hint"].pack(anchor=tk.W, pady=(0, 10))

        lang_frame = ttk.Frame(frame)
        lang_frame.pack(anchor=tk.W)
        self.settings_lang_var = tk.StringVar(value=self.i18n.preference)
        self._settings_radio_labels: dict[str, ttk.Radiobutton] = {}
        for code, _ in self.i18n.get_language_options():
            rb = ttk.Radiobutton(
                lang_frame, variable=self.settings_lang_var, value=code,
                command=self._on_settings_language,
            )
            rb.pack(anchor=tk.W, pady=2)
            self._settings_radio_labels[code] = rb

    def _on_settings_language(self):
        code = self.settings_lang_var.get()
        self.i18n.set_language(code)
        if code in self._lang_code_to_display:
            self.lang_var.set(self._lang_code_to_display[code])

    # ── About tab ────────────────────────────────────────────

    def _build_about_tab(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="About")
        self._labels["about_text"] = ttk.Label(frame, justify=tk.LEFT, font=("Segoe UI", 10))
        self._labels["about_text"].pack(anchor=tk.W)

    def run(self):
        self.root.mainloop()