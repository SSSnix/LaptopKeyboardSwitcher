# ⌨️ Laptop Keyboard Switcher (KB-Switcher)

A simple Python utility to **hardware-disable** the built-in laptop keyboard via Windows Registry. Perfect if you use an external keyboard placed directly on the laptop chassis.

## ✨ Features
- **Permanent Disable**: Keyboard stays disabled across reboots.
- **Modern UI**: Dark/Light mode support, Windows 11 style via `CustomTkinter`.
- **Safe Operation**: Modifies the `i8042prt` (PS/2 Keyboard Port) service start type — no driver deletion.
- **Smart Safety Check**: Detects active external HID keyboards (USB/Bluetooth) instantly via WinAPI (no WMI lag) and warns if none are found.
- **UAC Aware**: Auto-requests Admin rights on launch.
- **No Heavy Dependencies**: Removed `wmi`/`pywin32` bloat. Pure `ctypes` + `winreg`.

## 🚀 How to Use
1. Download or build `KB-Switcher.exe`.
2. Run the app (Admin rights required — prompted automatically).
3. Toggle the switch to **Disabled**.
4. **Reboot** the laptop (prompted by app) to stop Windows from initializing the built-in keyboard.

## 🛠 Build from Source

### Prerequisites
- Python 3.10+
- `pip install -r requirements.txt`
- `pip install pyinstaller`

### Build Command
