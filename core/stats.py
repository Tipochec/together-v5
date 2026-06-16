"""
Статистика времени в приложениях — SQLite.
Фокус-окно → для карточек активности (tracker.py).
Все открытые процессы → для статистики времени.
"""
import sqlite3
import os
import threading
import ctypes
import ctypes.wintypes
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "stats.db")

# Те же маппинги что в tracker.py
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
    "idea64.exe":         "IntelliJ IDEA",
    "figma.exe":          "Figma",
    "slack.exe":          "Slack",
    "zoom.exe":           "Zoom",
    "obs64.exe":          "OBS Studio",
    "photoshop.exe":      "Photoshop",
}

CATEGORIES = {
    "Google Chrome": "browser", "Firefox": "browser",
    "Microsoft Edge": "browser", "Opera": "browser",
    "Brave": "browser", "Vivaldi": "browser",
    "Steam": "gaming", "CS2": "gaming", "Dota 2": "gaming",
    "Xr_3da": "gaming", "Isaac-ng": "gaming",
    "Java": "tlauncher", "Javaw": "tlauncher",
    "Discord": "chat", "Telegram": "chat", "Slack": "chat", "Zoom": "chat",
    "Spotify": "music", "VLC": "video", "Яндекс музыка": "music",
    "VS Code": "work", "PyCharm": "work", "IntelliJ IDEA": "work",
    "Figma": "work", "Photoshop": "work", "Wps": "work",
    "OBS Studio": "streaming",
    "Qbittorrent": "torrent",
    "Photos": "photo",
    "V2raytun": "vpn",
    "7zfm": "archive", "Winrar": "archive",
}

# Процессы которые не считаем (системные, фоновые, невидимые пользователю)
IGNORE_PROCESSES = {
    "explorer.exe", "searchhost.exe", "searchindexer.exe",
    "taskhostw.exe", "sihost.exe", "ctfmon.exe", "rundll32.exe",
    "dllhost.exe", "conhost.exe", "svchost.exe", "lsass.exe",
    "winlogon.exe", "csrss.exe", "wininit.exe", "services.exe",
    "spoolsv.exe", "msiexec.exe", "backgroundtaskhost.exe",
    "runtimebroker.exe", "shellexperiencehost.exe", "startmenuexperiencehost.exe",
    "systemsettings.exe", "fontdrvhost.exe", "dwm.exe", "nvcontainer.exe",
    "pythonw.exe", "python.exe", "together.exe",
    "textinputhost.exe", "lockapp.exe", "applicationframehost.exe",
    "smartscreen.exe", "securityhealthsystray.exe", "nvdisplay.container.exe",
    "widgets.exe", "widgetservice.exe", "useroobebroker.exe",
    "wudfhost.exe", "registry.exe", "memcompression.exe",
    "ngentask.exe", "wmiprvse.exe", "taskmgr.exe", "pt2500csm.exe", "calculatorapp.exe", "nvidia overlay.exe",
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_time (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                date      TEXT NOT NULL,
                app       TEXT NOT NULL,
                category  TEXT NOT NULL,
                seconds   INTEGER DEFAULT 0,
                UNIQUE(date, app)
            )
        """)
        conn.commit()


class StatsTracker:
    def __init__(self, tracker):
        self.tracker = tracker  # нужен только для AFK проверки
        self._running = False
        init_db()

    def start(self):
        import time
        self._running = True
        while self._running:
            try:
                # Не считаем если AFK
                current = self.tracker.get_current()
                if not current.get("afk", False):
                    apps = self._get_open_apps()
                    if apps:
                        self._record_batch(apps)
            except Exception:
                pass
            time.sleep(1)

    def stop(self):
        self._running = False

    def _get_open_apps(self):
        """
        Возвращает множество уникальных приложений которые сейчас открыты.
        Использует EnumWindows чтобы получить все видимые окна.
        """
        found = {}  # app_name → category

        user32  = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        psapi   = ctypes.windll.psapi

        def enum_callback(hwnd, _):
            try:
                # Только видимые окна с заголовком
                if not user32.IsWindowVisible(hwnd):
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length == 0:
                    return True

                # Получаем PID
                pid = ctypes.wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

                # Получаем имя процесса
                handle = kernel32.OpenProcess(0x0400 | 0x0010, False, pid.value)
                if not handle:
                    return True
                buf = ctypes.create_unicode_buffer(260)
                sz  = ctypes.wintypes.DWORD(260)
                psapi.GetModuleFileNameExW(handle, None, buf, sz)
                kernel32.CloseHandle(handle)

                proc = os.path.basename(buf.value).lower() if buf.value else ""
                if not proc or proc in IGNORE_PROCESSES:
                    return True

                # Маппим на читаемое имя если знаем, иначе берём имя процесса как есть
                app_name = APP_NAMES.get(proc)
                if not app_name:
                    app_name = proc.replace(".exe", "").replace(".EXE", "").capitalize()

                if app_name not in found:
                    found[app_name] = self._get_category(app_name)

            except Exception:
                pass
            return True

        # EnumWindows принимает callback
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_callback), 0)

        return found

    def _get_category(self, app_name):
        """
        Категория для известных — из словаря CATEGORIES.
        Для неизвестных — спрашиваем AI (с кешем), пока ответа нет — "other".
        """
        cat = CATEGORIES.get(app_name)
        if cat:
            return cat

        try:
            from core.ai_classify import _load_cache, classify_app
            key = app_name.lower().strip()
            cache = _load_cache()
            if key in cache:
                return cache[key]

            # Не в кеше — запускаем в фоне, сейчас "other"
            def worker():
                classify_app(app_name, "")
            threading.Thread(target=worker, daemon=True).start()
            return "other"
        except Exception:
            return "other"

    def debug_scan(self):
        """
        Диагностика — показывает ВСЕ видимые окна с их процессами,
        даже те что отфильтрованы. Помогает понять почему что-то не попадает.
        """
        results = []
        user32   = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        psapi    = ctypes.windll.psapi

        def enum_callback(hwnd, _):
            try:
                visible = bool(user32.IsWindowVisible(hwnd))
                length  = user32.GetWindowTextLengthW(hwnd)
                title   = ""
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value

                pid = ctypes.wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                handle = kernel32.OpenProcess(0x0400 | 0x0010, False, pid.value)
                proc = "?"
                if handle:
                    buf2 = ctypes.create_unicode_buffer(260)
                    sz   = ctypes.wintypes.DWORD(260)
                    psapi.GetModuleFileNameExW(handle, None, buf2, sz)
                    kernel32.CloseHandle(handle)
                    proc = os.path.basename(buf2.value).lower() if buf2.value else "?"

                if visible and length > 0:
                    ignored = proc in IGNORE_PROCESSES
                    results.append({
                        "proc": proc, "title": title[:40],
                        "ignored": ignored,
                    })
            except Exception:
                pass
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
        return results

    def _record_batch(self, apps):
        """Прибавляем 1 секунду ко всем открытым приложениям"""
        today = date.today().isoformat()
        try:
            with get_db() as conn:
                for app_name, category in apps.items():
                    conn.execute("""
                        INSERT INTO app_time (date, app, category, seconds)
                        VALUES (?, ?, ?, 1)
                        ON CONFLICT(date, app) DO UPDATE SET seconds = seconds + 1
                    """, (today, app_name, category))
                conn.commit()
        except Exception:
            pass

    # ── Запросы для UI ────────────────────────────────────────

    def get_today(self):
        today = date.today().isoformat()
        with get_db() as conn:
            rows = conn.execute("""
                SELECT app, category, seconds
                FROM app_time WHERE date = ?
                ORDER BY seconds DESC LIMIT 10
            """, (today,)).fetchall()
        return [dict(r) for r in rows]

    def get_week(self):
        with get_db() as conn:
            rows = conn.execute("""
                SELECT app, category, SUM(seconds) as seconds
                FROM app_time
                WHERE date >= date('now', '-7 days')
                GROUP BY app ORDER BY seconds DESC LIMIT 10
            """).fetchall()
        return [dict(r) for r in rows]

    def get_category_totals(self):
        today = date.today().isoformat()
        with get_db() as conn:
            rows = conn.execute("""
                SELECT category, SUM(seconds) as seconds
                FROM app_time WHERE date = ?
                GROUP BY category ORDER BY seconds DESC
            """, (today,)).fetchall()
        return [dict(r) for r in rows]


def fmt_time(seconds):
    if seconds < 60: return f"{seconds}с"
    m = seconds // 60
    if m < 60: return f"{m}м"
    h = m // 60
    return f"{h}ч {m%60}м" if m % 60 else f"{h}ч"
