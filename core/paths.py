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


def data_dir():
    if is_frozen():
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        path = os.path.join(base, "Together")
    else:
        path = _project_root()
    os.makedirs(path, exist_ok=True)
    return path


def data_path(*parts):
    return os.path.join(data_dir(), *parts)


def resource_path(*parts):
    if is_frozen():
        base = getattr(sys, "_MEIPASS", _project_root())
    else:
        base = _project_root()
    return os.path.join(base, *parts)
