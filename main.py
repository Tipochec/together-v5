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
from core.tray import TrayApp
from core.stats import StatsTracker

_MUTEX_NAME = "Together_App_SingleInstance_Mutex_9f3c2a"
_instance_mutex = None  # держим ссылку на хендл, чтобы он не закрылся раньше времени


def _acquire_single_instance_lock():
    """Не даёт запустить второй экземпляр приложения одновременно.
    Тестовый билд использует свой отдельный мьютекс, чтобы работать параллельно с основным.
    """
    global _instance_mutex
    try:
        import ctypes
        from core.paths import is_test_instance
        mutex_name = "Together_Test_SingleInstance_Mutex_9f3c2a" if is_test_instance() else _MUTEX_NAME
        ERROR_ALREADY_EXISTS = 183
        _instance_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
        if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            return False
        return True
    except Exception:
        # Не Windows / ctypes недоступен — не блокируем запуск, просто
        # не можем гарантировать единственность экземпляра.
        return True


def _warn_already_running():
    from core.paths import is_test_instance
    prefix = "Together (Тест)" if is_test_instance() else "Together"
    msg = f"{prefix} уже запущен — проверьте трей (значок в правом нижнем углу) или диспетчер задач."
    print(msg)
    try:
        import ctypes
        hwnd = ctypes.windll.user32.FindWindowW(None, prefix)
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            return
        ctypes.windll.user32.MessageBoxW(0, msg, prefix, 0x30)  # MB_ICONWARNING
    except Exception:
        pass


def main():
    from core.paths import is_test_instance
    if not is_test_instance():
        setup_autostart_once()

    tracker = ActivityTracker()
    network = NetworkManager(tracker)
    stats   = StatsTracker(tracker)

    # При клиент-серверной архитектуре через VPS входящие порты больше не слушаются,
    # поэтому правило брандмауэра и UAC-запросы больше не требуются!

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
