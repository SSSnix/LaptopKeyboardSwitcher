import customtkinter as ctk
import winreg
import ctypes
import sys
import os
import threading
from tkinter import messagebox
from typing import List, Tuple, Optional

# --- Constants ---
REG_PATH = r"SYSTEM\CurrentControlSet\Services\i8042prt"
REG_VALUE_NAME = "Start"
SERVICE_ENABLED = 3      # SERVICE_DEMAND_START
SERVICE_DISABLED = 4     # SERVICE_DISABLED

# WinAPI Constants for Raw Input
RIDI_DEVICENAME = 0x20000007
RIM_TYPEKEYBOARD = 1

# Reboot flags
EWX_REBOOT = 0x00000002
EWX_FORCEIFHUNG = 0x00000010
EWX_HYBRID_SHUTDOWN = 0x00400000  # Fast Startup support

# Localization (Easy to extend)
STRINGS = {
    "en": {
        "title": "KB-Switcher",
        "header": "Keyboard Control",
        "status_active": "● ACTIVE",
        "status_disabled": "○ DISABLED",
        "switch_on": "Enabled",
        "switch_off": "Disabled",
        "hint": "Reboot required to apply changes",
        "working": "Working...",
        "warn_title": "Warning!",
        "warn_text": "Only {count} external keyboard(s) detected:\n{devices}\n\nIf these are just mice or macro pads, you won't be able to type!\nProceed with disabling internal keyboard?",
        "no_ext_kb": "No external keyboards detected.",
        "error_admin": "Administrator rights required!\nPlease run the app as Administrator.",
        "error_registry": "Failed to access registry:\n{error}",
        "reboot_prompt": "A reboot is required to apply changes.\nReboot now?",
        "rebooting": "Rebooting...",
    },
    "ru": {
        "title": "KB-Switcher",
        "header": "Управление клавиатурой",
        "status_active": "● АКТИВНА",
        "status_disabled": "○ ОТКЛЮЧЕНА",
        "switch_on": "Включена",
        "switch_off": "Выключена",
        "hint": "Требуется перезагрузка для применения",
        "working": "Выполнение...",
        "warn_title": "Внимание!",
        "warn_text": "Обнаружено {count} внешних клавиатур(ы):\n{devices}\n\nЕсли это мыши или макропэды, ввод станет невозможен!\nПродолжить отключение встроенной клавиатуры?",
        "no_ext_kb": "Внешние клавиатуры не обнаружены.",
        "error_admin": "Требуются права администратора!\nЗапустите приложение от имени администратора.",
        "error_registry": "Ошибка доступа к реестру:\n{error}",
        "reboot_prompt": "Для применения изменений требуется перезагрузка.\nПерезагрузить сейчас?",
        "rebooting": "Перезагрузка...",
    }
}

# Detect system language for default (simple heuristic)
DEFAULT_LANG = "ru" if "ru" in (os.getenv("LANG", "") + os.getenv("LANGUAGE", "")).lower() else "en"


def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS  # type: ignore
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def set_app_id():
    myappid = 'sssnix.KB-Switcher.v1.2'
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass


class KeyboardService:
    """Encapsulates low-level system interactions (Registry, WinAPI)."""

    @staticmethod
    def get_keyboard_status() -> bool:
        """Returns True if keyboard service is enabled (Start != 4)."""
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, REG_PATH, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, REG_VALUE_NAME)
                return value != SERVICE_DISABLED
        except FileNotFoundError:
            return True  # Default to enabled if key missing
        except Exception:
            return True

    @staticmethod
    def set_keyboard_state(enabled: bool) -> Tuple[bool, Optional[str]]:
        """Sets keyboard service start type. Returns (success, error_message)."""
        value_to_set = SERVICE_ENABLED if enabled else SERVICE_DISABLED
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, REG_VALUE_NAME, 0, winreg.REG_DWORD, value_to_set)
            return True, None
        except PermissionError:
            return False, "Permission denied. Run as Administrator."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_external_keyboards() -> List[str]:
        """
        Uses Raw Input API (GetRawInputDeviceList) to list active HID Keyboards.
        Fast, no WMI dependency. Returns list of device names/paths.
        """
        devices = []
        try:
            # 1. Get count
            n_devices = ctypes.c_uint(0)
            ctypes.windll.user32.GetRawInputDeviceList(None, ctypes.byref(n_devices), ctypes.sizeof(ctypes.wintypes.HANDLE))
            if n_devices.value == 0:
                return []

            # 2. Get list
            p_raw_input_device_list = (ctypes.wintypes.RAWINPUTDEVICELIST * n_devices.value)()
            got = ctypes.windll.user32.GetRawInputDeviceList(
                ctypes.byref(p_raw_input_device_list),
                ctypes.byref(n_devices),
                ctypes.sizeof(ctypes.wintypes.RAWINPUTDEVICELIST)
            )
            if got == -1:
                return []

            # 3. Iterate and filter Keyboards (Type == 1)
            for i in range(n_devices.value):
                rid = p_raw_input_device_list[i]
                if rid.dwType == RIM_TYPEKEYBOARD:
                    # Get Device Name length
                    size = ctypes.c_uint(0)
                    ctypes.windll.user32.GetRawInputDeviceInfoW(
                        rid.hDevice, RIDI_DEVICENAME, None, ctypes.byref(size)
                    )
                    if size.value > 0:
                        # Get Device Name
                        buffer = ctypes.create_unicode_buffer(size.value)
                        ctypes.windll.user32.GetRawInputDeviceInfoW(
                            rid.hDevice, RIDI_DEVICENAME, buffer, ctypes.byref(size)
                        )
                        # Format: \\?\HID#VID_XXXX&PID_XXXX#...#{...}
                        # Extract friendly part
                        name = buffer.value
                        # Clean up a bit for display
                        if "#" in name:
                            parts = name.split("#")
                            # Usually VID/PID is in part 1 or 2
                            dev_id = parts[1] if len(parts) > 1 else name
                            devices.append(f"- HID Device ({dev_id})")
                        else:
                            devices.append(f"- {name}")

        except Exception:
            # Silently fail, return empty list (safe side: assume no external kb)
            pass
        return devices

    @staticmethod
    def reboot_system():
        """Initiates immediate reboot using ExitWindowsEx."""
        # Enable required privilege: SE_SHUTDOWN_NAME
        # For simplicity in a small tool, we rely on the process token having it (Admin usually does).
        # Proper way: AdjustTokenPrivileges. But ExitWindowsEx often works for Admin.
        ctypes.windll.user32.ExitWindowsEx(EWX_REBOOT | EWX_FORCEIFHUNG | EWX_HYBRID_SHUTDOWN, 0)


class KeyboardApp(ctk.CTk):
    def __init__(self, lang: str = DEFAULT_LANG):
        super().__init__()
        self.lang = lang
        self.t = STRINGS[self.lang]

        # Window Setup
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        self.title(self.t["title"])
        self.resizable(False, False)

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = 420
        window_height = 400
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2 - 50
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # State
        self.is_enabled = KeyboardService.get_keyboard_status()
        self._operation_lock = threading.Lock()
        self._is_working = False

        # UI
        self._setup_ui()
        self._update_ui_state()

    def _setup_ui(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=15)
        self.main_frame.pack(pady=20, padx=20, fill="both", expand=True)

        # Header
        self.label = ctk.CTkLabel(self.main_frame, text=self.t["header"], font=("Segoe UI", 24, "bold"))
        self.label.pack(pady=(25, 10))

        # Status Indicator
        self.status_indicator = ctk.CTkLabel(
            self.main_frame,
            text="",
            font=("Segoe UI", 16, "bold")
        )
        self.status_indicator.pack(pady=5)

        # Switch
        self.switch_var = ctk.BooleanVar(value=self.is_enabled)
        self.switch = ctk.CTkSwitch(
            self.main_frame,
            text="",
            command=self._on_switch_toggle,
            variable=self.switch_var,
            font=("Segoe UI", 16),
            switch_width=60,
            switch_height=30,
            corner_radius=15
        )
        self.switch.pack(pady=30)

        # Progress Spinner (Hidden initially)
        self.spinner = ctk.CTkProgressBar(self.main_frame, mode="indeterminate", width=200)
        # self.spinner.pack(pady=10) # Pack when needed

        # Hint
        self.hint = ctk.CTkLabel(
            self.main_frame,
            text=self.t["hint"],
            font=("Segoe UI", 11, "italic"),
            text_color="gray"
        )
        self.hint.pack(side="bottom", pady=15)

    def _update_ui_state(self):
        """Updates labels, colors, switch text based on self.is_enabled and working state."""
        if self._is_working:
            status_text = self.t["working"]
            text_color = "#f39c12"  # Orange
            self.switch.configure(state="disabled", text="")
            if not self.spinner.winfo_ismapped():
                self.spinner.pack(pady=10)
                self.spinner.start()
        else:
            self.spinner.stop()
            self.spinner.pack_forget()
            self.switch.configure(state="normal")

            if self.is_enabled:
                status_text = self.t["status_active"]
                text_color = "#2ecc71"  # Green
                self.switch.configure(text=self.t["switch_on"])
            else:
                status_text = self.t["status_disabled"]
                text_color = "#e74c3c"  # Red
                self.switch.configure(text=self.t["switch_off"])

            self.status_indicator.configure(text=status_text, text_color=text_color)

    def _set_working(self, working: bool):
        self._is_working = working
        self._update_ui_state()

    def _on_switch_toggle(self):
        """Handles switch click. Runs safety check in background."""
        if self._is_working:
            return

        new_state = self.switch_var.get()

        # If user tries to DISABLE (new_state == False), run safety check
        if not new_state:
            self._set_working(True)
            threading.Thread(target=self._safety_check_and_apply, args=(new_state,), daemon=True).start()
        else:
            # Enabling is safe, apply directly
            self._apply_changes(new_state)

    def _safety_check_and_apply(self, target_state: bool):
        """Background thread: Check external keyboards -> Show Dialog (Main Thread) -> Apply."""
        ext_kbs = KeyboardService.get_external_keyboards()

        # Schedule UI interaction on main thread
        self.after(0, lambda: self._show_warning_dialog(ext_kbs, target_state))

    def _show_warning_dialog(self, ext_kbs: List[str], target_state: bool):
        """Runs on Main Thread."""
        self._set_working(False)  # Stop spinner while dialog is open

        proceed = True
        if len(ext_kbs) <= 1:
            devices_str = "\n".join(ext_kbs) if ext_kbs else self.t["no_ext_kb"]
            count = len(ext_kbs)
            msg = self.t["warn_text"].format(count=count, devices=devices_str)
            proceed = messagebox.askyesno(self.t["warn_title"], msg, parent=self)

        if not proceed:
            # Revert switch visually
            self.switch_var.set(not target_state)
            self._update_ui_state()
            return

        # User confirmed -> Apply
        self._apply_changes(target_state)

    def _apply_changes(self, state: bool):
        """Applies registry change (Background) -> Updates UI (Main) -> Reboot Prompt."""
        self._set_working(True)

        def worker():
            success, error = KeyboardService.set_keyboard_state(state)
            self.after(0, lambda: self._on_apply_result(success, error, state))

        threading.Thread(target=worker, daemon=True).start()

    def _on_apply_result(self, success: bool, error: Optional[str], state: bool):
        self._set_working(False)

        if not success:
            messagebox.showerror(self.t["error_admin"] if "Permission" in (error or "") else "Error",
                                 self.t["error_registry"].format(error=error) if error else "Unknown error", parent=self)
            self.switch_var.set(not state)  # Revert switch
            self.is_enabled = not state
            self._update_ui_state()
            return

        # Success
        self.is_enabled = state
        self._update_ui_state()

        if not state:  # If disabled, ask for reboot
            answer = messagebox.askyesno(self.t["warn_title"], self.t["reboot_prompt"], parent=self)
            if answer:
                self.hint.configure(text=self.t["rebooting"], text_color="#e74c3c")
                self.update_idletasks()
                KeyboardService.reboot_system()


def main():
    set_app_id()

    if is_admin():
        ctk.set_appearance_mode("System")  # "Dark", "Light", "System"
        ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"
        app = KeyboardApp()
        app.mainloop()
    else:
        # Re-launch as Admin
        script = os.path.abspath(sys.argv[0])
        params = " ".join(f'"{arg}"' for arg in sys.argv[1:])
        # Use pythonw.exe to avoid console window flash if possible
        executable = sys.executable
        if "python.exe" in executable.lower():
            executable = executable.replace("python.exe", "pythonw.exe")

        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", executable, f'"{script}" {params}', None, 1
        )
        sys.exit(0)


if __name__ == "__main__":
    main()
