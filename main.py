import customtkinter as ctk
import winreg
import ctypes
import sys
import os

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class KeyboardApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Laptop Keyboard Switcher")
        self.geometry("400x320")
        self.resizable(False, False)

        if os.path.exists("icon.ico"):
            self.iconbitmap("icon.ico")

        self.registry_path = r"SYSTEM\CurrentControlSet\Services\i8042prt"

        # Контейнер для центрирования
        self.main_frame = ctk.CTkFrame(self, corner_radius=15)
        self.main_frame.pack(pady=20, padx=20, fill="both", expand=True)

        self.label = ctk.CTkLabel(self.main_frame, text="Keyboard Control", font=("Segoe UI", 24, "bold"))
        self.label.pack(pady=(20, 10))

        # Состояние из реестра
        self.is_enabled = self.get_keyboard_status()

        self.status_indicator = ctk.CTkLabel(
            self.main_frame,
            text="● ACTIVE" if self.is_enabled else "○ DISABLED",
            text_color="#2ecc71" if self.is_enabled else "#e74c3c",
            font=("Segoe UI", 14, "bold")
        )
        self.status_indicator.pack(pady=5)

        # Свитч
        self.switch_var = ctk.BooleanVar(value=self.is_enabled)
        self.switch = ctk.CTkSwitch(
            self.main_frame,
            text=self.get_switch_text(self.is_enabled),
            command=self.toggle_keyboard,
            variable=self.switch_var,
            font=("Segoe UI", 16)
        )
        self.switch.pack(pady=30)

        self.hint = ctk.CTkLabel(
            self.main_frame,
            text="Reboot required to apply changes",
            font=("Segoe UI", 11, "italic"),
            text_color="gray"
        )
        self.hint.pack(side="bottom", pady=15)

    def get_keyboard_status(self):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, self.registry_path) as key:
                value, _ = winreg.QueryValueEx(key, "Start")
                return value != 4
        except:
            return True

    def get_switch_text(self, enabled):
        return "Enabled" if enabled else "Disabled"

    def toggle_keyboard(self):
        new_state = self.switch_var.get()
        value_to_set = 3 if new_state else 4

        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, self.registry_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "Start", 0, winreg.REG_DWORD, value_to_set)

            # Обновляем UI
            self.status_indicator.configure(
                text="● ACTIVE" if new_state else "○ DISABLED",
                text_color="#2ecc71" if new_state else "#e74c3c"
            )
            self.switch.configure(text=self.get_switch_text(new_state))

        except PermissionError:
            self.switch_var.set(not new_state)


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def set_app_id():
    # Создаем уникальный ID для вашего приложения
    # Формат: 'mycompany.myproduct.subproduct.version'
    myappid = 'sssnix.keyboardswitcher.v1.0'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

if __name__ == "__main__":
    set_app_id()
    if is_admin():
        app = KeyboardApp()
        app.mainloop()
    else:
        script = os.path.abspath(sys.argv[0])
        params = " ".join(sys.argv[1:])
        # Используем pythonw.exe для скрытия лишних окон venv
        executable = sys.executable.replace("python.exe", "pythonw.exe")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, f'"{script}" {params}', None, 1)