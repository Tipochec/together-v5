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


def setup_autostart_once(app_name="Together"):
    """Включает автозапуск САМ только один раз за всю жизнь настроек —
    при самом первом запуске приложения (чтобы новым пользователям
    автозапуск был включён по умолчанию, как и задумывалось).

    Раньше main() вызывал setup_autostart() БЕЗ УСЛОВИЙ на каждом
    старте, а у setup_autostart enable=True по умолчанию — из-за этого
    реестр перезаписывался обратно на "включено" даже если пользователь
    только что выключил тумблер в настройках (toggle_autostart в
    ui/window.py). Внешне выглядело так, будто выключить автозапуск
    вообще невозможно: он "сам включался обратно" при каждом перезаходе
    в приложение. Теперь при старте мы трогаем реестр только если это
    вообще первый запуск (флаг ещё не сохранён в settings.json) — во
    всех остальных случаях автозапуском распоряжается исключительно
    пользователь через переключатель в настройках, старт приложения его
    больше не трогает.
    """
    from core.tracker import load_settings, _settings_path
    import json

    settings = load_settings()
    if settings.get("_autostart_initialized"):
        return

    setup_autostart(app_name=app_name, enable=True)

    settings["_autostart_initialized"] = True
    try:
        with open(_settings_path(), "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Автозапуск: не удалось сохранить флаг первого запуска — {e}")


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
