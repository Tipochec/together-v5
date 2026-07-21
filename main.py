"""
Together - приложение для пар
"""
import threading
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.tracker import ActivityTracker
from core.network import NetworkManager
from core.autostart import setup_autostart_once
from core.firewall import ensure_firewall_rule_once
from core.tray import TrayApp
from core.stats import StatsTracker

_MUTEX_NAME = "Together_App_SingleInstance_Mutex_9f3c2a"
_instance_mutex = None  # держим ссылку на хендл, чтобы он не закрылся раньше времени


def _acquire_single_instance_lock():
    """Не даёт запустить второй экземпляр приложения одновременно.

    Без этой защиты случайный повторный запуск (например, второе окно
    консоли с `python main.py`, пока предыдущий процесс всё ещё висит в
    трее — приложение сворачивается, а не завершается при закрытии окна)
    поднимает второй набор серверного/клиентского сокетов на том же
    порту 39721. На Windows SO_REUSEADDR ведёт себя не так, как на Linux,
    и может позволить второму процессу перехватить порт первого —
    входящие подключения от партнёра начинают непредсказуемо доставаться
    то одному, то другому процессу, а исходящие сообщения расходятся по
    двум независимым, не знающим друг о друге копиям сети. Со стороны
    это выглядит как рандомное "то доходит, то нет".

    Используем именованный Windows-мьютекс — он живёт в ядре ОС и
    гарантированно освобождается при завершении процесса, даже если тот
    упал аварийно (в отличие от, например, lock-файла на диске).
    """
    global _instance_mutex
    try:
        import ctypes
        ERROR_ALREADY_EXISTS = 183
        _instance_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, _MUTEX_NAME)
        if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            return False
        return True
    except Exception:
        # Не Windows / ctypes недоступен — не блокируем запуск, просто
        # не можем гарантировать единственность экземпляра.
        return True


def _warn_already_running():
    msg = "Together уже запущен — проверьте трей (значок в правом нижнем углу) или диспетчер задач."
    print(msg)
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, msg, "Together", 0x30)  # MB_ICONWARNING
    except Exception:
        pass


def main():
    setup_autostart_once()

    tracker = ActivityTracker()
    network = NetworkManager(tracker)
    stats   = StatsTracker(tracker)

    # Разрешающее правило брандмауэра для входящих подключений на
    # PORT (см. core/firewall.py) — без него сообщения партнёра к тебе
    # тонут в TCP timeout без единой строки в ЕГО логе, хотя у тебя всё
    # выглядит подключённым. Запускаем в отдельном потоке — вызов может
    # показать системный UAC-диалог (одноразово, как при установке
    # обычной программы), и это не должно морозить запуск окна.
    threading.Thread(target=ensure_firewall_rule_once, daemon=True).start()

    app = TrayApp(tracker, network)
    threading.Thread(target=app.run,       daemon=True).start()
    threading.Thread(target=tracker.start, daemon=True).start()
    threading.Thread(target=network.start, daemon=True).start()
    threading.Thread(target=stats.start,   daemon=True).start()

    from ui.window import run_webview_loop
    run_webview_loop(tracker, network, stats)


if __name__ == "__main__":
    if not _acquire_single_instance_lock():
        _warn_already_running()
        sys.exit(0)
    main()
