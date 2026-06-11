"""
Автозапуск с Windows через реестр.
Добавляет приложение в HKCU -> Software -> Microsoft -> Windows -> CurrentVersion -> Run
Работает без прав администратора.
"""
import sys
import os


def setup_autostart(app_name="Together", enable=True):
    try:
        import winreg
    except ImportError:
        return

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            key_path,
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
        )
        if enable:
            if getattr(sys, 'frozen', False):
                exe_path = f'"{sys.executable}"'
            else:
                pythonw = sys.executable.replace("python.exe", "pythonw.exe")
                script = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..", "main.py")
                )
                exe_path = f'"{pythonw}" "{script}"'
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Автозапуск: не удалось настроить — {e}")


def is_autostart_enabled(app_name="Together"):
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_QUERY_VALUE
        )
        try:
            winreg.QueryValueEx(key, app_name)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False
