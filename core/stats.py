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
SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "..", "settings.json")

# Общий источник — раньше здесь были свои копии словарей, которые
# расходились с tracker.py. Теперь один источник правды в app_maps.py.
from core.app_maps import APP_NAMES, CATEGORIES

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


def _extra_ignore_processes():
    """
    Пользователь может добавить свои процессы для игнора в settings.json:
    "extra_ignore_processes": ["rvrvpnfui.exe", "someghost.exe"]
    Так решается проблема разных авто-стартующих программ на разных ПК
    (например RVRVPNFUI), не трогая код.
    """
    try:
        import json
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            s = json.load(f)
        extra = s.get("extra_ignore_processes", [])
        return {p.strip().lower() for p in extra if p.strip()}
    except Exception:
        return set()


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
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
        ignore_extra = _extra_ignore_processes()

        user32  = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        psapi   = ctypes.windll.psapi

        def enum_callback(hwnd, _):
            try:
                # Только видимые окна с заголовком
                if not user32.IsWindowVisible(hwnd):
                    return True
                # Свёрнутые (IsIconic) окна не считаем — например калькулятор,
                # который "закрыли", но UWP-контейнер продолжает висеть свёрнутым
                if user32.IsIconic(hwnd):
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length == 0:
                    return True

                # Окна-призраки: формально видимые, но с нулевым/точечным размером —
                # реально пользователь их не видит и не взаимодействует с ними
                rect = ctypes.wintypes.RECT()
                if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                    w = rect.right - rect.left
                    h = rect.bottom - rect.top
                    if w <= 1 or h <= 1:
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
                if not proc or proc in IGNORE_PROCESSES or proc in ignore_extra:
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
        ignore_extra = _extra_ignore_processes()

        def enum_callback(hwnd, _):
            try:
                visible = bool(user32.IsWindowVisible(hwnd))
                iconic  = bool(user32.IsIconic(hwnd))
                length  = user32.GetWindowTextLengthW(hwnd)
                title   = ""
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value

                rect = ctypes.wintypes.RECT()
                zero_size = False
                if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                    zero_size = (rect.right - rect.left) <= 1 or (rect.bottom - rect.top) <= 1

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
                    reason = None
                    if iconic:
                        reason = "свёрнуто"
                    elif zero_size:
                        reason = "нулевой размер (окно-призрак)"
                    elif proc in IGNORE_PROCESSES:
                        reason = "в базовом списке игнора"
                    elif proc in ignore_extra:
                        reason = "в вашем extra_ignore_processes"

                    results.append({
                        "proc": proc, "title": title[:40],
                        "ignored": reason is not None,
                        "reason": reason,
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

    def get_all_time(self, limit=30):
        """Суммарное время по каждому приложению за ВСЕ дни, что есть в базе
        (не только сегодня/неделя) — топ-N по убыванию. Каждый день у
        приложения своя строка (see app_time UNIQUE(date, app)), поэтому
        общий итог считается через SUM(seconds) с группировкой по app."""
        with get_db() as conn:
            rows = conn.execute("""
                SELECT app, category, SUM(seconds) as seconds
                FROM app_time
                GROUP BY app ORDER BY seconds DESC LIMIT ?
            """, (limit,)).fetchall()
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
