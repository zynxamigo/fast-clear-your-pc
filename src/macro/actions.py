"""Macro action definitions — params schema only (names come from i18n)."""

ACTION_DEFINITIONS: dict[str, list[str]] = {
    # Shell & commands
    "run_command": ["command"],
    "run_cmd": ["command"],
    "run_batch": ["path"],
    # Apps & processes
    "open_app": ["path"],
    "open_url": ["url"],
    "open_folder": ["path"],
    "close_app": ["process_name"],
    "kill_process": ["pid"],
    "kill_process_by_name": ["process_name"],
    # Files & folders
    "create_folder": ["path"],
    "delete_folder": ["path"],
    "create_file": ["path", "content"],
    "delete_file": ["path"],
    "append_file": ["path", "content"],
    "copy_file": ["source", "destination"],
    "move_file": ["source", "destination"],
    "rename_file": ["source", "destination"],
    "zip_folder": ["folder", "zip_path"],
    "unzip_file": ["zip_path", "destination"],
    # Registry & environment
    "set_registry": ["hive", "key", "name", "value", "type"],
    "delete_registry": ["hive", "key", "name"],
    "set_env_var": ["name", "value"],
    "delete_env_var": ["name"],
    # Shortcuts & desktop
    "create_shortcut": ["target", "shortcut_path"],
    "delete_shortcut": ["shortcut_path"],
    "set_wallpaper": ["image_path"],
    # Services
    "toggle_service": ["service_name", "action"],
    "start_service": ["service_name"],
    "stop_service": ["service_name"],
    "restart_service": ["service_name"],
    # Notifications & UI
    "notification": ["title", "message"],
    "message_box": ["title", "message", "type"],
    "play_sound": ["sound_path"],
    "beep": ["frequency", "duration_ms"],
    # Power & session
    "wait": ["seconds"],
    "lock_screen": [],
    "sleep_pc": [],
    "hibernate_pc": [],
    "shutdown_pc": ["delay_seconds"],
    "restart_pc": ["delay_seconds"],
    "logoff_user": [],
    # Clipboard
    "set_clipboard": ["text"],
    "clear_clipboard": [],
    # Network
    "flush_dns": [],
    "enable_wifi": [],
    "disable_wifi": [],
    "download_file": ["url", "save_path"],
    "http_request": ["url"],
    # System tweaks
    "empty_recycle_bin": [],
    "screenshot": ["save_path"],
    "minimize_all": [],
    "set_volume": ["level"],
    "mute_volume": ["mute"],
    "add_startup": ["name", "command"],
    "remove_startup": ["name"],
    "create_task": ["task_name", "command", "schedule"],
    "delete_task": ["task_name"],
    "send_keys": ["keys"],
    "enable_dark_mode": [],
    "disable_dark_mode": [],
    "open_control_panel": ["item"],
    "refresh_explorer": [],
    "clear_temp_macro": [],
    "set_datetime": ["datetime"],
    "block_input": ["seconds"],
    "unblock_input": [],
}

TRIGGER_IDS = ("manual", "startup", "schedule", "battery_low", "wifi_connected", "app_opened")