"""
Together - приложение для пар
"""
import threading
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.tracker import ActivityTracker
from core.network import NetworkManager
from core.autostart import setup_autostart
from core.tray import TrayApp

def main():
    setup_autostart()

    tracker = ActivityTracker()
    network = NetworkManager(tracker)

    # Трей запускаем в отдельном потоке
    app = TrayApp(tracker, network)
    threading.Thread(target=app.run, daemon=True).start()

    # Трекер в отдельном потоке
    threading.Thread(target=tracker.start, daemon=True).start()

    # Сеть в отдельном потоке
    threading.Thread(target=network.start, daemon=True).start()

    # Главный поток держим для pywebview
    # Запускаем webview loop — он будет ждать команд от трея
    from ui.window import run_webview_loop
    run_webview_loop(tracker, network)

if __name__ == "__main__":
    main()
