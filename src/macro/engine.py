"""Motor de macros do sistema — estilo Android MacroDroid."""
import json
import os
import subprocess
import winreg
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

# Ações disponíveis (como blocos no Android Macro)
AVAILABLE_ACTIONS = {
    "run_command": {
        "name": "Executar comando",
        "params": ["command"],
        "description": "Executa um comando no PowerShell/CMD",
    },
    "open_app": {
        "name": "Abrir aplicativo",
        "params": ["path"],
        "description": "Abre um programa ou arquivo",
    },
    "create_folder": {
        "name": "Criar pasta",
        "params": ["path"],
        "description": "Cria uma nova pasta no sistema",
    },
    "create_file": {
        "name": "Criar arquivo",
        "params": ["path", "content"],
        "description": "Cria um arquivo de texto",
    },
    "set_registry": {
        "name": "Modificar registro",
        "params": ["hive", "key", "name", "value", "type"],
        "description": "Altera valor no Registro do Windows",
    },
    "delete_file": {
        "name": "Apagar arquivo",
        "params": ["path"],
        "description": "Apaga um arquivo específico (com proteção)",
    },
    "copy_file": {
        "name": "Copiar arquivo",
        "params": ["source", "destination"],
        "description": "Copia um arquivo para outro local",
    },
    "move_file": {
        "name": "Mover arquivo",
        "params": ["source", "destination"],
        "description": "Move um arquivo para outro local",
    },
    "set_env_var": {
        "name": "Variável de ambiente",
        "params": ["name", "value", "user"],
        "description": "Define variável de ambiente do usuário",
    },
    "create_shortcut": {
        "name": "Criar atalho",
        "params": ["target", "shortcut_path"],
        "description": "Cria atalho na área de trabalho ou pasta",
    },
    "toggle_service": {
        "name": "Serviço do Windows",
        "params": ["service_name", "action"],
        "description": "Inicia, para ou reinicia um serviço",
    },
    "notification": {
        "name": "Notificação",
        "params": ["title", "message"],
        "description": "Exibe mensagem de notificação",
    },
    "wait": {
        "name": "Aguardar",
        "params": ["seconds"],
        "description": "Pausa a macro por X segundos",
    },
}

# Gatilhos disponíveis
AVAILABLE_TRIGGERS = {
    "manual": {"name": "Manual", "description": "Executar ao clicar no botão"},
    "startup": {"name": "Ao iniciar o PC", "description": "Executa quando o Windows inicia"},
    "schedule": {"name": "Agendado", "description": "Executa em horário definido (HH:MM)"},
}

HIVE_MAP = {
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
    "HKCR": winreg.HKEY_CLASSES_ROOT,
}

TYPE_MAP = {
    "REG_SZ": winreg.REG_SZ,
    "REG_DWORD": winreg.REG_DWORD,
    "REG_EXPAND_SZ": winreg.REG_EXPAND_SZ,
}


@dataclass
class MacroAction:
    action_type: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Macro:
    id: str
    name: str
    trigger: str = "manual"
    trigger_params: dict[str, Any] = field(default_factory=dict)
    actions: list[MacroAction] = field(default_factory=list)
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MacroResult:
    success: bool
    messages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _is_macro_path_safe(path: str) -> bool:
    """Proteção para macros — não toca system32."""
    from src.cleaner.safety import is_protected_path
    return not is_protected_path(path)


class MacroEngine:
    """Executa e gerencia macros do sistema."""

    def __init__(self, macros_file: Path):
        self.macros_file = macros_file
        self.macros: list[Macro] = []
        self._load()

    def _load(self):
        if self.macros_file.exists():
            try:
                data = json.loads(self.macros_file.read_text(encoding="utf-8"))
                self.macros = [
                    Macro(
                        id=m["id"],
                        name=m["name"],
                        trigger=m.get("trigger", "manual"),
                        trigger_params=m.get("trigger_params", {}),
                        actions=[MacroAction(**a) for a in m.get("actions", [])],
                        enabled=m.get("enabled", True),
                        created_at=m.get("created_at", ""),
                    )
                    for m in data
                ]
            except (json.JSONDecodeError, KeyError):
                self.macros = []

    def save(self):
        data = [
            {
                "id": m.id,
                "name": m.name,
                "trigger": m.trigger,
                "trigger_params": m.trigger_params,
                "actions": [{"action_type": a.action_type, "params": a.params} for a in m.actions],
                "enabled": m.enabled,
                "created_at": m.created_at,
            }
            for m in self.macros
        ]
        self.macros_file.parent.mkdir(parents=True, exist_ok=True)
        self.macros_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_macro(self, macro: Macro):
        self.macros.append(macro)
        self.save()

    def remove_macro(self, macro_id: str):
        self.macros = [m for m in self.macros if m.id != macro_id]
        self.save()

    def get_macro(self, macro_id: str) -> Macro | None:
        return next((m for m in self.macros if m.id == macro_id), None)

    def execute(
        self,
        macro: Macro,
        log_cb: Callable[[str], None] | None = None,
    ) -> MacroResult:
        result = MacroResult(success=True)

        for action in macro.actions:
            try:
                msg = self._run_action(action)
                result.messages.append(msg)
                if log_cb:
                    log_cb(msg)
            except Exception as e:
                result.success = False
                err = f"[{action.action_type}] Erro: {e}"
                result.errors.append(err)
                if log_cb:
                    log_cb(err)

        return result

    def _run_action(self, action: MacroAction) -> str:
        p = action.params
        t = action.action_type

        if t == "run_command":
            cmd = p.get("command", "")
            subprocess.run(
                ["powershell", "-Command", cmd],
                capture_output=True,
                timeout=300,
            )
            return f"Comando executado: {cmd[:50]}..."

        if t == "open_app":
            path = p.get("path", "")
            os.startfile(path)
            return f"Aplicativo aberto: {path}"

        if t == "create_folder":
            path = Path(p.get("path", ""))
            if not _is_macro_path_safe(str(path)):
                raise PermissionError("Caminho protegido pelo sistema")
            path.mkdir(parents=True, exist_ok=True)
            return f"Pasta criada: {path}"

        if t == "create_file":
            path = Path(p.get("path", ""))
            if not _is_macro_path_safe(str(path.parent)):
                raise PermissionError("Caminho protegido pelo sistema")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(p.get("content", ""), encoding="utf-8")
            return f"Arquivo criado: {path}"

        if t == "set_registry":
            hive = HIVE_MAP.get(p.get("hive", "HKCU"), winreg.HKEY_CURRENT_USER)
            key_path = p.get("key", "")
            with winreg.CreateKey(hive, key_path) as key:
                val_type = TYPE_MAP.get(p.get("type", "REG_SZ"), winreg.REG_SZ)
                value = p.get("value", "")
                if val_type == winreg.REG_DWORD:
                    value = int(value)
                winreg.SetValueEx(key, p.get("name", ""), 0, val_type, value)
            return f"Registro alterado: {p.get('hive')}\\{key_path}"

        if t == "delete_file":
            path = Path(p.get("path", ""))
            if not _is_macro_path_safe(str(path)):
                raise PermissionError("Arquivo em área protegida — bloqueado")
            if path.exists():
                path.unlink()
            return f"Arquivo apagado: {path}"

        if t == "copy_file":
            src, dst = Path(p.get("source", "")), Path(p.get("destination", ""))
            if not _is_macro_path_safe(str(src)) or not _is_macro_path_safe(str(dst.parent)):
                raise PermissionError("Caminho protegido")
            import shutil
            shutil.copy2(src, dst)
            return f"Copiado: {src} → {dst}"

        if t == "move_file":
            src, dst = Path(p.get("source", "")), Path(p.get("destination", ""))
            if not _is_macro_path_safe(str(src)) or not _is_macro_path_safe(str(dst.parent)):
                raise PermissionError("Caminho protegido")
            import shutil
            shutil.move(str(src), str(dst))
            return f"Movido: {src} → {dst}"

        if t == "set_env_var":
            name, value = p.get("name", ""), p.get("value", "")
            subprocess.run(
                ["setx", name, value],
                capture_output=True,
                timeout=30,
            )
            return f"Variável definida: {name}={value}"

        if t == "create_shortcut":
            target = p.get("target", "")
            shortcut = p.get("shortcut_path", "")
            ps = f'$ws=New-Object -ComObject WScript.Shell;$s=$ws.CreateShortcut("{shortcut}");$s.TargetPath="{target}";$s.Save()'
            subprocess.run(["powershell", "-Command", ps], capture_output=True, timeout=30)
            return f"Atalho criado: {shortcut}"

        if t == "toggle_service":
            svc, act = p.get("service_name", ""), p.get("action", "start")
            subprocess.run(
                ["sc", act, svc],
                capture_output=True,
                timeout=60,
            )
            return f"Serviço {svc}: {act}"

        if t == "notification":
            title = p.get("title", "PC Cleaner Macro")
            message = p.get("message", "")
            ps = f'[System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms")|Out-Null;[System.Windows.Forms.MessageBox]::Show("{message}","{title}")'
            subprocess.run(["powershell", "-Command", ps], capture_output=True, timeout=30)
            return f"Notificação: {title}"

        if t == "wait":
            import time
            secs = float(p.get("seconds", 1))
            time.sleep(secs)
            return f"Aguardou {secs}s"

        raise ValueError(f"Ação desconhecida: {t}")