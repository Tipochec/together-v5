"""
Трекер активности - читает активное окно каждую секунду
"""
import time
import threading
import ctypes
import ctypes.wintypes
import os
import json
from datetime import datetime
from collections import deque

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

APP_NAMES = {
    "chrome.exe":         "Google Chrome",
    "firefox.exe":        "Firefox",
    "msedge.exe":         "Microsoft Edge",
    "opera.exe":          "Opera",
    "brave.exe":          "Brave",
    "vivaldi.exe":        "Vivaldi",
    "steam.exe":          "Steam",
    "steamwebhelper.exe": "Steam",
    "cs2.exe":            "CS2",
    "dota2.exe":          "Dota 2",
    "discord.exe":        "Discord",
    "telegram.exe":       "Telegram",
    "code.exe":           "VS Code",
    "pycharm64.exe":      "PyCharm",
    "spotify.exe":        "Spotify",
    "vlc.exe":            "VLC",
    "explorer.exe":       "Рабочий стол",
    "idea64.exe":         "IntelliJ IDEA",
    "figma.exe":          "Figma",
    "slack.exe":          "Slack",
    "zoom.exe":           "Zoom",
    "obs64.exe":          "OBS Studio",
    "photoshop.exe":      "Photoshop",
}

BROWSER_PROCESSES = {
    "chrome.exe", "firefox.exe", "msedge.exe",
    "opera.exe", "brave.exe", "vivaldi.exe",
}

CATEGORIES = {
    "Google Chrome": "browser", "Firefox": "browser",
    "Microsoft Edge": "browser", "Opera": "browser",
    "Brave": "browser", "Vivaldi": "browser",
    "Steam": "gaming", "CS2": "gaming", "Dota 2": "gaming",
    "Discord": "chat", "Telegram": "chat", "Slack": "chat", "Zoom": "chat",
    "Spotify": "music", "VLC": "video",
    "VS Code": "work", "PyCharm": "work", "IntelliJ IDEA": "work",
    "Figma": "work", "Photoshop": "work",
    "OBS Studio": "streaming",
    "Рабочий стол": "idle",
}

AFK_TIMEOUT = 300


def _settings_path():
    return os.path.join(os.path.dirname(__file__), "..", "settings.json")


def load_settings():
    path = _settings_path()
    # Если settings.json нет — создаём из шаблона
    if not os.path.exists(path):
        default_path = os.path.join(os.path.dirname(path), "settings.default.json")
        try:
            with open(default_path, "r", encoding="utf-8") as f:
                defaults = json.load(f)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(defaults, f, ensure_ascii=False, indent=2)
            return defaults
        except Exception:
            return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


class ActivityTracker:
    def __init__(self):
        self.current = {
            "app": "—", "title": "", "category": "idle",
            "since": datetime.now(), "afk": False,
        }
        self.history = deque(maxlen=50)
        self._lock = threading.Lock()
        self._running = False
        self._on_change_callbacks = []

    def on_change(self, cb):
        self._on_change_callbacks.append(cb)

    def get_current(self):
        with self._lock:
            return dict(self.current)

    def get_history(self):
        with self._lock:
            return list(self.history)

    def start(self):
        self._running = True
        prev_app = None
        prev_title = None

        while self._running:
            try:
                proc_name, app, title = self._get_active_window()
                afk = self._check_afk()

                # Приватный режим — скрываем вкладку браузера
                settings = load_settings()
                private = settings.get("private_mode", False)
                if private and proc_name.lower() in BROWSER_PROCESSES:
                    title = ""

                changed = (app != prev_app or title != prev_title)

                if changed:
                    now = datetime.now()
                    with self._lock:
                        if prev_app and prev_app != "—":
                            self.history.appendleft({
                                "app": prev_app,
                                "title": prev_title,
                                "category": CATEGORIES.get(prev_app, "other"),
                                "timestamp": self.current["since"],
                            })
                        self.current = {
                            "app": app, "title": title,
                            "category": CATEGORIES.get(app, "other"),
                            "since": now, "afk": afk,
                        }
                    prev_app = app
                    prev_title = title
                    for cb in self._on_change_callbacks:
                        try:
                            cb(self.current)
                        except Exception:
                            pass
                else:
                    with self._lock:
                        self.current["afk"] = afk

            except Exception:
                pass

            time.sleep(1)

    def stop(self):
        self._running = False

    def _get_active_window(self):
        try:
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return "explorer.exe", "Рабочий стол", ""

            length = user32.GetWindowTextLengthW(hwnd)
            title = ""
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value

            pid = ctypes.wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            proc_name = self._get_process_name(pid.value)
            app_name = APP_NAMES.get(proc_name.lower(), self._clean_process_name(proc_name))
            clean_title = self._clean_title(title, app_name)

            return proc_name, app_name, clean_title
        except Exception:
            return "explorer.exe", "Рабочий стол", ""

    def _get_process_name(self, pid):
        try:
            handle = kernel32.OpenProcess(0x0400 | 0x0010, False, pid)
            if not handle:
                return "unknown.exe"
            buf = ctypes.create_unicode_buffer(260)
            size = ctypes.wintypes.DWORD(260)
            ctypes.windll.psapi.GetModuleFileNameExW(handle, None, buf, size)
            kernel32.CloseHandle(handle)
            return os.path.basename(buf.value) if buf.value else "unknown.exe"
        except Exception:
            return "unknown.exe"

    def _clean_title(self, title, app_name):
        if not title:
            return ""
        for suffix in [" \u2014 Google Chrome", " - Google Chrome",
                       " \u2014 Mozilla Firefox", " - Mozilla Firefox",
                       " \u2014 Microsoft Edge", " - Microsoft Edge",
                       " \u2014 Opera", " - Opera", " - Brave"]:
            if title.endswith(suffix):
                title = title[:-len(suffix)]
                break
        return title[:120]

    def _clean_process_name(self, name):
        return name.replace(".exe", "").replace(".EXE", "").capitalize() or "Неизвестно"

    def _check_afk(self):
        try:
            li = ctypes.wintypes.LASTINPUTINFO()
            li.cbSize = ctypes.sizeof(li)
            ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li))
            elapsed = (kernel32.GetTickCount() - li.dwTime) / 1000.0
            return elapsed > AFK_TIMEOUT
        except Exception:
            return False
