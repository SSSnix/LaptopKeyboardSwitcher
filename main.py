import customtkinter as ctk
import winreg
import ctypes
import sys
import os
from tkinter import messagebox


class KeyboardApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        else:
            self.iconbitmap(default='shell32.dll,44')
        self.title("Laptop Keyboard Switcher v1.1")
        self.geometry("400x380")
        self.registry_path = r"SYSTEM\CurrentControlSet\Services\i8042prt"

        self.main_frame = ctk.CTkFrame(self, corner_radius=15)
        self.main_frame.pack(pady=20, padx=20, fill="both", expand=True)

        self.label = ctk.CTkLabel(self.main_frame, text="Keyboard Control", font=("Segoe UI", 24, "bold"))
        self.label.pack(pady=(20, 10))
        self.is_enabled = self.get_keyboard_status()

        self.status_indicator = ctk.CTkLabel(
            self.main_frame,
            text="● ACTIVE" if self.is_enabled else "○ DISABLED",
            text_color="#2ecc71" if self.is_enabled else "#e74c3c",
            font=("Segoe UI", 14, "bold")
        )
        self.status_indicator.pack(pady=5)
        self.switch_var = ctk.BooleanVar(value=self.is_enabled)
        self.switch = ctk.CTkSwitch(
            self.main_frame,
            text="Enabled" if self.is_enabled else "Disabled",
            command=self.toggle_keyboard,
            variable=self.switch_var,
            font=("Segoe UI", 16)
        )
        self.switch.pack(pady=30)
        self.hint = ctk.CTkLabel(self.main_frame, text="Reboot required to apply", font=("Segoe UI", 11, "italic"),
                                 text_color="gray")
        self.hint.pack(side="bottom", pady=15)

    def get_external_keyboards_list(self):
        try:
            import wmi
            c = wmi.WMI()
            found_devices = []

            for kb in c.Win32_Keyboard():
                device_id = kb.DeviceID.upper()
                # Игнорируем встроенную PS/2 клавиатуру
                if "ACPI" in device_id or "PNP0303" in device_id:
                    continue

                if "USB" in device_id or "HID" in device_id:
                    name = kb.Caption or kb.Description
                    found_devices.append(f"- {name} (ID: {kb.DeviceID[:15]}...)")

            return found_devices
        except:
            return []

    def toggle_keyboard(self):
        new_state = self.switch_var.get()

        if not new_state:  # Если выключаем
            external_kbs = self.get_external_keyboards_list()

            if len(external_kbs) <= 1:
                devices_str = "\n".join(external_kbs) if external_kbs else "None"
                confirm = messagebox.askyesno(
                    "Warning!",
                    f"Only these external devices found:\n{devices_str}\n\n"
                    "If these are just mice, you won't be able to type!\n"
                    "Proceed with disabling internal keyboard?"
                )
                if not confirm:
                    self.switch_var.set(True)
                    return

        self.apply_changes(new_state)

    def apply_changes(self, state):
        value_to_set = 3 if state else 4
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, self.registry_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "Start", 0, winreg.REG_DWORD, value_to_set)

            self.status_indicator.configure(
                text="● ACTIVE" if state else "○ DISABLED",
                text_color="#2ecc71" if state else "#e74c3c"
            )
            self.switch.configure(text="Enabled" if state else "Disabled")

            if not state:
                answer = messagebox.askyesno(
                    "Требуется перезагрузка",
                    "Чтобы отключить встроенную клавиатуру, необходимо перезагрузить компьютер.\n\n"
                    "Перезагрузить сейчас?"
                )
                if answer:
                    os.system("shutdown /r /t 1")
        except PermissionError:
            messagebox.showerror("Ошибка", "Запустите приложение от имени администратора!")
            self.switch_var.set(not state)

    def get_keyboard_status(self):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, self.registry_path) as key:
                value, _ = winreg.QueryValueEx(key, "Start")
                return value != 4
        except:
            return True


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def set_app_id():
    myappid = 'sssnix.keyboardswitcher.v1.1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

if __name__ == "__main__":
    set_app_id()
    if is_admin():
        app = KeyboardApp()
        app.mainloop()
    else:
        script = os.path.abspath(sys.argv[0])
        params = " ".join(sys.argv[1:])
        executable = sys.executable.replace("python.exe", "pythonw.exe")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, f'"{script}" {params}', None, 1)