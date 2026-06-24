"""Interface gráfica principal — PC Cleaner Macro."""
import json
import threading
import tkinter as tk
import uuid
from tkinter import filedialog, messagebox, ttk

from src.cleaner.engine import CleanerEngine, format_bytes
from src.cleaner.safety import SAFE_CLEAN_TARGETS, is_protected_path
from src.config import EXCLUSIONS_FILE, MACROS_FILE
from src.macro.engine import AVAILABLE_ACTIONS, AVAILABLE_TRIGGERS, Macro, MacroAction, MacroEngine


class PCCleanerApp:
    """Aplicativo principal com abas de Limpeza, Exclusões e Macros."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PC Cleaner Macro")
        self.root.geometry("900x650")
        self.root.minsize(800, 550)

        self.exclusions = self._load_exclusions()
        self.macro_engine = MacroEngine(MACROS_FILE)
        self.cleaner = CleanerEngine(self.exclusions)
        self.target_vars: dict[str, tk.BooleanVar] = {}

        self._setup_style()
        self._build_ui()

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

    def _build_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self._build_clean_tab(notebook)
        self._build_exclusions_tab(notebook)
        self._build_macros_tab(notebook)
        self._build_about_tab(notebook)

    # ── Aba Limpeza ──────────────────────────────────────────

    def _build_clean_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text="  Limpeza  ")

        ttk.Label(frame, text="Limpeza Segura do PC", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(
            frame,
            text="Remove apenas lixo temporário. System32 e pastas críticas são SEMPRE protegidas.",
            wraplength=850,
        ).pack(anchor=tk.W, pady=(0, 10))

        targets_frame = ttk.LabelFrame(frame, text="O que limpar", padding=8)
        targets_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(targets_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(targets_frame, orient=tk.VERTICAL, command=canvas.yview)
        inner = ttk.Frame(canvas)

        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for target in SAFE_CLEAN_TARGETS:
            var = tk.BooleanVar(value=True)
            self.target_vars[target["id"]] = var
            ttk.Checkbutton(inner, text=target["name"], variable=var).pack(anchor=tk.W, pady=2)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="Analisar espaço", command=self._scan).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Limpar agora", command=self._clean).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Selecionar tudo", command=self._select_all).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Desmarcar tudo", command=self._deselect_all).pack(side=tk.LEFT, padx=4)

        self.progress = ttk.Progressbar(frame, mode="determinate")
        self.progress.pack(fill=tk.X, pady=4)

        self.status_label = ttk.Label(frame, text="Pronto para analisar ou limpar.")
        self.status_label.pack(anchor=tk.W)

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
            messagebox.showwarning("Aviso", "Selecione pelo menos um item para analisar.")
            return

        self.log_text.delete("1.0", tk.END)
        self.result_label.config(text="")
        self.progress["value"] = 0
        self.status_label.config(text="Analisando...")

        def run():
            def progress(msg, pct):
                self.root.after(0, lambda: self._update_progress(msg, pct))

            result = CleanerEngine(self.exclusions).scan(targets, progress)
            self.root.after(0, lambda: self._show_scan_result(result))

        threading.Thread(target=run, daemon=True).start()

    def _clean(self):
        targets = self._get_selected_targets()
        if not targets:
            messagebox.showwarning("Aviso", "Selecione pelo menos um item para limpar.")
            return

        if not messagebox.askyesno(
            "Confirmar limpeza",
            "Deseja executar a limpeza?\n\nPastas protegidas (System32, Windows, etc.) "
            "e seus itens de exclusão NÃO serão afetados.",
        ):
            return

        self.log_text.delete("1.0", tk.END)
        self.result_label.config(text="")
        self.progress["value"] = 0
        self.status_label.config(text="Limpando...")

        def run():
            def progress(msg, pct):
                self.root.after(0, lambda: self._update_progress(msg, pct))

            result = CleanerEngine(self.exclusions).clean(targets, progress)
            self.root.after(0, lambda: self._show_clean_result(result))

        threading.Thread(target=run, daemon=True).start()

    def _update_progress(self, msg: str, pct: float):
        self.status_label.config(text=msg)
        self.progress["value"] = pct * 100

    def _show_scan_result(self, result):
        self.status_label.config(text="Análise concluída.")
        self.progress["value"] = 100
        self.result_label.config(
            text=f"Espaço recuperável: {format_bytes(result.bytes_freed)}"
        )
        self._log(f"Análise: {format_bytes(result.bytes_freed)} podem ser liberados")
        self._log(f"Itens ignorados (protegidos): {result.skipped}")

    def _show_clean_result(self, result):
        self.status_label.config(text="Limpeza concluída!")
        self.progress["value"] = 100
        self.result_label.config(
            text=f"Espaço liberado: {format_bytes(result.bytes_freed)}"
        )
        self._log(f"Arquivos removidos: {result.files_deleted}")
        self._log(f"Pastas removidas: {result.folders_deleted}")
        self._log(f"Espaço liberado: {format_bytes(result.bytes_freed)}")
        self._log(f"Itens protegidos/ignorados: {result.skipped}")
        if result.errors:
            self._log(f"Erros: {len(result.errors)}")
            for err in result.errors[:10]:
                self._log(f"  - {err}")

        messagebox.showinfo(
            "Limpeza concluída",
            f"Espaço liberado: {format_bytes(result.bytes_freed)}\n"
            f"Arquivos: {result.files_deleted} | Pastas: {result.folders_deleted}",
        )

    # ── Aba Exclusões ────────────────────────────────────────

    def _build_exclusions_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text="  Exclusões  ")

        ttk.Label(frame, text="Proteger pastas, arquivos e apps", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(
            frame,
            text="Itens nesta lista NUNCA serão apagados durante a limpeza. "
            "System32 já é protegido automaticamente.",
            wraplength=850,
        ).pack(anchor=tk.W, pady=(0, 10))

        list_frame = ttk.LabelFrame(frame, text="Itens protegidos", padding=8)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.excl_listbox = tk.Listbox(list_frame, font=("Segoe UI", 10))
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.excl_listbox.yview)
        self.excl_listbox.configure(yscrollcommand=scroll.set)
        self.excl_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._refresh_exclusions_list()

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="Adicionar pasta", command=self._add_exclusion_folder).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Adicionar arquivo", command=self._add_exclusion_file).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Adicionar app (.exe)", command=self._add_exclusion_app).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Remover selecionado", command=self._remove_exclusion).pack(side=tk.LEFT, padx=4)

        ttk.Label(
            frame,
            text="Proteção automática: System32, SysWOW64, Windows, Program Files, DLLs, drivers e mais.",
            style="Danger.TLabel",
        ).pack(anchor=tk.W)

    def _refresh_exclusions_list(self):
        self.excl_listbox.delete(0, tk.END)
        for path in self.exclusions:
            self.excl_listbox.insert(tk.END, path)

    def _add_exclusion_folder(self):
        path = filedialog.askdirectory(title="Selecione pasta para proteger")
        if path:
            self._add_exclusion(path)

    def _add_exclusion_file(self):
        path = filedialog.askopenfilename(title="Selecione arquivo para proteger")
        if path:
            self._add_exclusion(path)

    def _add_exclusion_app(self):
        path = filedialog.askopenfilename(
            title="Selecione aplicativo (.exe)",
            filetypes=[("Executáveis", "*.exe"), ("Todos", "*.*")],
        )
        if path:
            app_dir = str(__import__("pathlib").Path(path).parent)
            self._add_exclusion(app_dir)

    def _add_exclusion(self, path: str):
        if is_protected_path(path):
            messagebox.showinfo(
                "Já protegido",
                "Este caminho já é protegido automaticamente pelo sistema.",
            )
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
        idx = sel[0]
        del self.exclusions[idx]
        self._save_exclusions()
        self._refresh_exclusions_list()
        self.cleaner = CleanerEngine(self.exclusions)

    # ── Aba Macros ─────────────────────────────────────────

    def _build_macros_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text="  Macros  ")

        ttk.Label(frame, text="Macros do Sistema (estilo Android)", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(
            frame,
            text="Crie automações para modificar o sistema, criar pastas, alterar registro, "
            "abrir apps e muito mais — como o MacroDroid no Android.",
            wraplength=850,
        ).pack(anchor=tk.W, pady=(0, 10))

        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(paned, text="Minhas Macros", padding=8)
        paned.add(left, weight=1)

        self.macro_listbox = tk.Listbox(left, font=("Segoe UI", 10))
        self.macro_listbox.pack(fill=tk.BOTH, expand=True)
        self.macro_listbox.bind("<<ListboxSelect>>", self._on_macro_select)

        macro_btns = ttk.Frame(left)
        macro_btns.pack(fill=tk.X, pady=4)
        ttk.Button(macro_btns, text="Nova macro", command=self._new_macro).pack(side=tk.LEFT, padx=2)
        ttk.Button(macro_btns, text="Executar", command=self._run_macro).pack(side=tk.LEFT, padx=2)
        ttk.Button(macro_btns, text="Excluir", command=self._delete_macro).pack(side=tk.LEFT, padx=2)

        right = ttk.LabelFrame(paned, text="Editor de Macro", padding=8)
        paned.add(right, weight=2)

        ttk.Label(right, text="Nome:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.macro_name_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.macro_name_var, width=40).grid(row=0, column=1, sticky=tk.W, pady=2)

        ttk.Label(right, text="Gatilho:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.macro_trigger_var = tk.StringVar(value="manual")
        trigger_combo = ttk.Combobox(
            right,
            textvariable=self.macro_trigger_var,
            values=list(AVAILABLE_TRIGGERS.keys()),
            state="readonly",
            width=20,
        )
        trigger_combo.grid(row=1, column=1, sticky=tk.W, pady=2)

        ttk.Label(right, text="Ações:", style="Header.TLabel").grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(8, 2))

        action_frame = ttk.Frame(right)
        action_frame.grid(row=3, column=0, columnspan=2, sticky=tk.NSEW)

        self.action_listbox = tk.Listbox(action_frame, height=6, font=("Consolas", 9))
        self.action_listbox.pack(fill=tk.BOTH, expand=True)

        add_frame = ttk.Frame(right)
        add_frame.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=4)

        self.action_type_var = tk.StringVar()
        action_combo = ttk.Combobox(
            add_frame,
            textvariable=self.action_type_var,
            values=list(AVAILABLE_ACTIONS.keys()),
            state="readonly",
            width=20,
        )
        action_combo.pack(side=tk.LEFT, padx=2)
        action_combo.bind("<<ComboboxSelected>>", self._on_action_type_change)

        self.action_params_frame = ttk.Frame(add_frame)
        self.action_params_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.action_param_vars: dict[str, tk.StringVar] = {}

        ttk.Button(add_frame, text="Adicionar ação", command=self._add_action_to_macro).pack(side=tk.LEFT, padx=4)
        ttk.Button(add_frame, text="Salvar macro", command=self._save_macro).pack(side=tk.LEFT, padx=4)

        ttk.Label(right, text="Log:", style="Header.TLabel").grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(8, 2))
        self.macro_log = tk.Text(right, height=5, wrap=tk.WORD, font=("Consolas", 9))
        self.macro_log.grid(row=6, column=0, columnspan=2, sticky=tk.NSEW)

        right.rowconfigure(6, weight=1)
        right.columnconfigure(1, weight=1)

        self._current_macro_id: str | None = None
        self._current_actions: list[dict] = []
        self._refresh_macro_list()

    def _refresh_macro_list(self):
        self.macro_listbox.delete(0, tk.END)
        for m in self.macro_engine.macros:
            status = "✓" if m.enabled else "✗"
            self.macro_listbox.insert(tk.END, f"{status} {m.name} ({m.trigger})")

    def _new_macro(self):
        self._current_macro_id = str(uuid.uuid4())[:8]
        self.macro_name_var.set("Nova Macro")
        self.macro_trigger_var.set("manual")
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
        self.macro_trigger_var.set(macro.trigger)
        self._current_actions = [
            {"action_type": a.action_type, "params": a.params} for a in macro.actions
        ]
        self.action_listbox.delete(0, tk.END)
        for a in self._current_actions:
            self.action_listbox.insert(tk.END, f"{a['action_type']}: {a['params']}")

    def _on_action_type_change(self, _event=None):
        for w in self.action_params_frame.winfo_children():
            w.destroy()
        self.action_param_vars.clear()

        action_type = self.action_type_var.get()
        if not action_type or action_type not in AVAILABLE_ACTIONS:
            return

        info = AVAILABLE_ACTIONS[action_type]
        for i, param in enumerate(info["params"]):
            ttk.Label(self.action_params_frame, text=f"{param}:").grid(row=0, column=i * 2, padx=2)
            var = tk.StringVar()
            self.action_param_vars[param] = var
            ttk.Entry(self.action_params_frame, textvariable=var, width=15).grid(row=0, column=i * 2 + 1, padx=2)

    def _add_action_to_macro(self):
        action_type = self.action_type_var.get()
        if not action_type:
            return
        params = {k: v.get() for k, v in self.action_param_vars.items()}
        action = {"action_type": action_type, "params": params}
        self._current_actions.append(action)
        self.action_listbox.insert(tk.END, f"{action_type}: {params}")

    def _save_macro(self):
        name = self.macro_name_var.get().strip()
        if not name:
            messagebox.showwarning("Aviso", "Dê um nome à macro.")
            return
        if not self._current_actions:
            messagebox.showwarning("Aviso", "Adicione pelo menos uma ação.")
            return

        macro_id = self._current_macro_id or str(uuid.uuid4())[:8]
        actions = [MacroAction(**a) for a in self._current_actions]
        macro = Macro(
            id=macro_id,
            name=name,
            trigger=self.macro_trigger_var.get(),
            actions=actions,
        )

        existing = self.macro_engine.get_macro(macro_id)
        if existing:
            self.macro_engine.macros = [
                macro if m.id == macro_id else m for m in self.macro_engine.macros
            ]
        else:
            self.macro_engine.add_macro(macro)

        self.macro_engine.save()
        self._refresh_macro_list()
        messagebox.showinfo("Salvo", f"Macro '{name}' salva com sucesso!")

    def _run_macro(self):
        sel = self.macro_listbox.curselection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione uma macro para executar.")
            return

        macro = self.macro_engine.macros[sel[0]]
        self.macro_log.delete("1.0", tk.END)
        self.macro_log.insert(tk.END, f"Executando: {macro.name}\n")

        def run():
            def log(msg):
                self.root.after(0, lambda: self.macro_log.insert(tk.END, msg + "\n"))

            result = self.macro_engine.execute(macro, log)
            status = "Sucesso" if result.success else "Com erros"
            self.root.after(0, lambda: self.macro_log.insert(tk.END, f"\n--- {status} ---\n"))

        threading.Thread(target=run, daemon=True).start()

    def _delete_macro(self):
        sel = self.macro_listbox.curselection()
        if not sel:
            return
        macro = self.macro_engine.macros[sel[0]]
        if messagebox.askyesno("Confirmar", f"Excluir macro '{macro.name}'?"):
            self.macro_engine.remove_macro(macro.id)
            self._refresh_macro_list()

    # ── Aba Sobre ────────────────────────────────────────────

    def _build_about_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text="  Sobre  ")

        about_text = """PC Cleaner Macro v1.0.0

Limpeza segura do Windows com proteção total do sistema.

Recursos:
• Limpeza de temp, cache, lixeira, navegadores e mais
• Exclusões personalizadas (pastas, arquivos, apps)
• Proteção obrigatória de System32 e pastas críticas
• Macros do sistema estilo Android (MacroDroid)
• Relatório de espaço liberado

Desenvolvido com Python + Tkinter.
"""
        ttk.Label(frame, text=about_text, justify=tk.LEFT, font=("Segoe UI", 10)).pack(anchor=tk.W)

    def run(self):
        self.root.mainloop()