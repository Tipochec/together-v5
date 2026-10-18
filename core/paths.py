"""
Единая точка правды о путях к данным приложения.

Зачем это нужно: раньше все модули считали пути как
os.path.dirname(__file__)/.. — это работает, только пока приложение
запущено из исходников (python main.py). После сборки в exe через
PyInstaller __file__ модулей указывает ВНУТРЬ временной директории
распаковки (у --onefile это _MEIPASS — создаётся заново при КАЖДОМ
запуске и удаляется при закрытии). Если писать settings.json/stats.db
туда — все настройки, IP партнёра и история чата будут слетать при
каждом перезапуске собранного .exe.

Разделяем два вида путей:
  - data_dir() / data_path(...) — то, что нужно ПИСАТЬ и что должно
    переживать перезапуски. В собранном .exe — это %APPDATA%\\Together
    (стандартная практика для Windows-приложений, не зависит от того,
    куда пользователь закинул сам .exe). При запуске из исходников —
    просто корень проекта, как было раньше (ничего не ломает при
    разработке).
  - resource_path(...) — файлы, которые только ЧИТАЮТСЯ и зашиты
    внутрь сборки (звук уведомления и т.п.). Достаются из _MEIPASS в
    собранном .exe, иначе из корня проекта.
"""
import os
import sys


def _project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def is_frozen():
    return bool(getattr(sys, "frozen", False))


def is_test_instance():
    # Явные флаги командной строки
    if "--test" in sys.argv or "--dev" in sys.argv or "--multi" in sys.argv:
        return True
    # Если файл называется Together_Test.exe или содержит test в имени файла
    exe_name = os.path.basename(sys.executable or "").lower()
    if "test" in exe_name:
        return True
    # Маркерный файл .test рядом с exe
    try:
        exe_dir = os.path.dirname(os.path.abspath(sys.executable or sys.argv[0]))
        if os.path.exists(os.path.join(exe_dir, ".test")) or os.path.exists(os.path.join(exe_dir, "test_mode.txt")):
            return True
    except Exception:
        pass
    return False


def data_dir():
    if is_frozen():
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        sub = "Together_Test" if is_test_instance() else "Together"
        path = os.path.join(base, sub)
    else:
        path = _project_root()
    os.makedirs(path, exist_ok=True)

    # Если это тестовая копия и у неё ещё нет settings.json, копируем из основной
    if is_test_instance():
        test_settings = os.path.join(path, "settings.json")
        main_settings = os.path.join(os.environ.get("APPDATA") or "", "Together", "settings.json")
        if not os.path.exists(test_settings) and os.path.exists(main_settings):
            try:
                import json
                with open(main_settings, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                import uuid
                cfg["device_id"] = "dev_test_" + uuid.uuid4().hex[:10]
                with open(test_settings, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    return path


def data_path(*parts):
    return os.path.join(data_dir(), *parts)


def resource_path(*parts):
    if is_frozen():
        base = getattr(sys, "_MEIPASS", _project_root())
    else:
        base = _project_root()
    return os.path.join(base, *parts)
