"""
Трекер активности - читает активное окно каждую секунду.
Два состояния: active / afk.
AFK считается по бездействию клавиатуры/мыши (GetLastInputInfo),
не зависит от того, что происходит на экране (в т.ч. видео/музыка) —
если человек не трогал клаву/мышь AFK_TIMEOUT секунд, это AFK.
"""
import time
import threading
import ctypes
import ctypes.wintypes
import os
import json
from datetime import datetime
from collections import deque

user32   = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
psapi    = ctypes.windll.psapi

# Явно задаём restype/argtypes для функций, которые возвращают/принимают
# HWND и хендлы. Без этого ctypes по умолчанию трактует возврат как
# 32-битный c_int и на 64-битном Python может обрезать/криво прочитать
# значение хендла — из-за этого GetForegroundWindow() (и всё, что от
# него зависит: заголовок окна, PID, имя процесса) время от времени
# читалось неверно, try/except ниже это молча проглатывал и подставлял
# запасной вариант "Рабочий стол" — отсюда и трей, который вечно
# показывал "Together — Рабочий стол" независимо от реального активного
# окна.
user32.GetForegroundWindow.restype = ctypes.wintypes.HWND
user32.GetForegroundWindow.argtypes = []
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextLengthW.argtypes = [ctypes.wintypes.HWND]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.restype = ctypes.wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.DWORD)]
kernel32.OpenProcess.restype = ctypes.wintypes.HANDLE
kernel32.OpenProcess.argtypes = [ctypes.wintypes.DWORD, ctypes.wintypes.BOOL, ctypes.wintypes.DWORD]
kernel32.CloseHandle.restype = ctypes.wintypes.BOOL
kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
psapi.GetModuleFileNameExW.restype = ctypes.wintypes.DWORD
psapi.GetModuleFileNameExW.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.HMODULE,
                                        ctypes.wintypes.LPWSTR, ctypes.wintypes.DWORD]
kernel32.GetTickCount.restype = ctypes.wintypes.DWORD
kernel32.GetTickCount.argtypes = []
user32.GetLastInputInfo.restype = ctypes.wintypes.BOOL
user32.GetLastInputInfo.argtypes = [ctypes.c_void_p]

from core.app_maps import APP_NAMES, BROWSER_PROCESSES, CATEGORIES
from core.paths import data_path

AFK_TIMEOUT = 600   # 10 минут без ввода клавы/мыши → AFK


class LASTINPUTINFO(ctypes.Structure):
    """
    Win32-структура для GetLastInputInfo — НЕ входит в стандартный
    ctypes.wintypes (там её никогда и не было), а код раньше обращался
    к ctypes.wintypes.LASTINPUTINFO(), которого просто не существует.
    Это падало с AttributeError на КАЖДОМ вызове _get_idle_seconds(),
    исключение молча ловилось и возвращался 0 — то есть idle всегда
    считался нулевым, и статус всегда был "active", даже если человек
    час не трогал клавиатуру/мышь. Отсюда и "был AFK час, а показало
    100% активности". Объявляем структуру руками — она полностью
    описана в MSDN: cbSize (размер структуры) + dwTime (тик последнего
    ввода в миллисекундах, тот же счётчик, что у GetTickCount).
    """
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_uint),
    ]


def _settings_path():
    return data_path("settings.json")


def load_settings():
    settings = {}
    try:
        with open(_settings_path(), "r", encoding="utf-8") as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {}
    except Exception as e:
        try:
            log_path = os.path.join(os.path.dirname(_settings_path()), "network_debug.log")
            with open(log_path, "a", encoding="utf-8") as lf:
                import time
                lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                         f"SETTINGS_JSON_BROKEN error={e}\n")
        except Exception:
            pass
        settings = {}

    # Убеждаемся, что у устройства есть уникальный device_id (генерируется 1 раз)
    if not settings.get("device_id"):
        import uuid
        settings["device_id"] = "dev_" + uuid.uuid4().hex[:12]
        try:
            with open(_settings_path(), "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    return settings


class ActivityTracker:
    def __init__(self):
        self.current = {
            "app": "—", "title": "", "category": "idle",
            "since": datetime.now(),
            "status": "active",   # active | afk
        }
        self.history  = deque(maxlen=100)
        self._lock    = threading.Lock()
        self._running = False
        self._on_change_callbacks = []

        # Счётчики времени за сессию
        self._time_active   = 0
        self._time_afk      = 0
        self._session_start = datetime.now()
        self._session_db_id = None   # id строки в sessions — для UPDATE вместо повторного INSERT
        self._last_checkpoint = time.time()

        # Ручной режим AFK («Я отошёл») с умным авто-выходом
        self._manual_afk = False
        self._manual_afk_time = 0
        self._grace_period = 30   # 30 секунд защитный интервал при нажатии

    def toggle_manual_afk(self):
        with self._lock:
            self._manual_afk = not self._manual_afk
            self._manual_afk_time = time.time() if self._manual_afk else 0
            new_status = "afk" if self._manual_afk else "active"
            self.current["status"] = new_status
            self.current["afk"] = (new_status == "afk")
            current_copy = dict(self.current)
        for cb in self._on_change_callbacks:
            try: cb(current_copy)
            except Exception: pass
        return self._manual_afk

    def is_manual_afk(self):
        with self._lock:
            return self._manual_afk

    def on_change(self, cb):
        self._on_change_callbacks.append(cb)

    def get_current(self):
        with self._lock:
            return dict(self.current)

    def get_history(self):
        with self._lock:
            return list(self.history)

    def get_time_stats(self):
        with self._lock:
            return {
                "active":   self._time_active,
                "afk":      self._time_afk,
                "total":    self._time_active,
                "session_start": self._session_start.isoformat(),
            }

    def get_session_start(self):
        return self._session_start

    def start(self):
        self._running  = True
        prev_app    = None
        prev_title  = None
        prev_status = None

        while self._running:
            try:
                proc_name, app, title, exe_path = self._get_active_window()
                idle_secs = self._get_idle_seconds()
                status    = self._calc_status(idle_secs, app, title)

                settings = load_settings()
                if settings.get("private_mode") and proc_name.lower() in BROWSER_PROCESSES:
                    title = ""

                changed = (app != prev_app or title != prev_title or status != prev_status)

                if changed:
                    now = datetime.now()
                    category = CATEGORIES.get(app)
                    if not category or category == "other":
                        from core.classifier import classify_executable
                        _, category = classify_executable(exe_path, app, category)

                    with self._lock:
                        if prev_app and prev_app != "—":
                            time_spent = (now - self.current["since"]).total_seconds()
                            if prev_app == app and time_spent < 5:
                                pass
                            else:
                                self.history.appendleft({
                                     "app":       prev_app,
                                     "title":     prev_title,
                                     "category":  CATEGORIES.get(prev_app, "other"),
                                     "timestamp": self.current["since"],
                                 })
                        self.current = {
                            "app":      app,
                            "title":    title,
                            "category": category,
                            "since":    now,
                            "status":   status,
                            "afk":      status == "afk",
                        }
                    prev_app    = app
                    prev_title  = title
                    prev_status = status
                    for cb in self._on_change_callbacks:
                        try: cb(self.current)
                        except Exception: pass
                else:
                    with self._lock:
                        self.current["status"] = status
                        self.current["afk"]    = status == "afk"

                with self._lock:
                    if status == "active":
                        self._time_active += 1
                    else:
                        self._time_afk    += 1

            except Exception:
                pass

            if time.time() - self._last_checkpoint >= 300:  # раз в 5 минут
                self._checkpoint_session()
                self._last_checkpoint = time.time()

            time.sleep(1)

    def stop(self):
        self._running = False
        self._log_checkpoint("stop() called — финальный чекпоинт")
        self._checkpoint_session()

    def _log_checkpoint(self, msg):
        try:
            log_path = data_path("ai_debug.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] SESSION_CHECKPOINT: {msg}\n")
        except Exception:
            pass

    def _checkpoint_session(self):
        """
        Сохраняет/обновляет ТЕКУЩУЮ сессию в БД. Раньше сохранение шло
        только внутри stop(), а stop() вызывается только при явном
        "Закрыть" из трея — если человек просто выключил ПК или закрыл
        окно (уходит в трей, не завершая процесс), это сохранение вообще
        никогда не срабатывало, и БД оставалась пустой. Теперь это
        чекпоинт: вызывается и раз в 5 минут во время работы, и при
        реальном закрытии — теряем максимум последние ~5 минут данных
        при аварийном завершении (крах, обесточивание и т.п.), а не всю
        сессию целиком.
        """
        with self._lock:
            active, afk = self._time_active, self._time_afk
        watching = 0  # состояние "watching" убрано, колонка в БД оставлена для совместимости

        if active < 30:
            self._log_checkpoint(f"пропущен — слишком мало данных (active={active})")
            return

        conn = None
        try:
            import sqlite3
            db_path = data_path("stats.db")
            conn = sqlite3.connect(db_path, timeout=10)

            # Проверяем, нет ли уже таблицы sessions с ДРУГОЙ (несовместимой)
            # структуре — например, оставшейся от более раннего варианта
            # этой фичи. CREATE TABLE IF NOT EXISTS её не тронет, а INSERT
            # потом просто упадёт с "no column named active_seconds".
            # Переименовываем старую (не удаляем!) и создаём новую с нуля.
            existing_cols = [r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()]
            if existing_cols and "active_seconds" not in existing_cols:
                conn.execute("ALTER TABLE sessions RENAME TO sessions_legacy")
                self._log_checkpoint(
                    f"обнаружена несовместимая старая таблица sessions "
                    f"(колонки: {existing_cols}) — переименована в sessions_legacy, "
                    f"данные не потеряны, создаю новую таблицу"
                )

            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    ended_at TEXT NOT NULL,
                    active_seconds INTEGER NOT NULL,
                    watching_seconds INTEGER NOT NULL,
                    afk_seconds INTEGER NOT NULL
                )
            """)
            now_iso = datetime.now().isoformat()

            if self._session_db_id is None:
                cur = conn.execute("""
                    INSERT INTO sessions
                    (started_at, ended_at, active_seconds, watching_seconds, afk_seconds)
                    VALUES (?, ?, ?, ?, ?)
                """, (self._session_start.isoformat(), now_iso, active, watching, afk))
                self._session_db_id = cur.lastrowid
                self._log_checkpoint(f"INSERT новой строки id={self._session_db_id} "
                                      f"(active={active}, watching={watching}, afk={afk})")
            else:
                conn.execute("""
                    UPDATE sessions
                    SET ended_at = ?, active_seconds = ?, watching_seconds = ?, afk_seconds = ?
                    WHERE id = ?
                """, (now_iso, active, watching, afk, self._session_db_id))
                self._log_checkpoint(f"UPDATE строки id={self._session_db_id} "
                                      f"(active={active}, watching={watching}, afk={afk})")

            conn.commit()
        except Exception as e:
            self._log_checkpoint(f"ОШИБКА при записи: {e}")
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def get_session_history(self, limit=10):
        conn = None
        try:
            import sqlite3
            db_path = data_path("stats.db")
            conn = sqlite3.connect(db_path, timeout=10)
            rows = conn.execute("""
                SELECT started_at, ended_at, active_seconds, watching_seconds, afk_seconds
                FROM sessions
                ORDER BY id DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [
                {
                    "started_at": r[0], "ended_at": r[1],
                    "active": r[2], "watching": r[3], "afk": r[4],
                }
                for r in rows
            ]
        except Exception:
            return []
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def _calc_status(self, idle_secs, app, title):
        # 1. Если включён ручной режим AFK («Я отошёл»):
        if self._manual_afk:
            # Умный выход из AFK:
            # Если прошло больше grace_period (30 сек) с момента нажатия,
            # и пользователь вернулся за ПК (пошевелил мышь или нажал клавишу: idle_secs < 2 сек)
            if (time.time() - self._manual_afk_time) > self._grace_period and idle_secs < 2.0:
                self._manual_afk = False
                return "active"
            return "afk"

        # 2. Автоматический режим (по умолчанию):
        # Единственный критерий — бездействие клавиатуры/мыши AFK_TIMEOUT секунд (10 минут).
        return "active" if idle_secs < AFK_TIMEOUT else "afk"

    def _get_idle_seconds(self):
        try:
            li = LASTINPUTINFO()
            li.cbSize = ctypes.sizeof(LASTINPUTINFO)
            if not user32.GetLastInputInfo(ctypes.byref(li)):
                return 0
            millis = kernel32.GetTickCount() - li.dwTime
            if millis < 0:
                # GetTickCount — 32-битный счётчик миллисекунд с момента
                # старта Windows, переполняется примерно раз в 49.7 дня —
                # без этой поправки в момент переполнения idle_secs на
                # мгновение уходил в минус и ломал сравнение с AFK_TIMEOUT
                millis += 2**32
            return millis / 1000.0
        except Exception:
            return 0

    def _get_active_window(self):
        try:
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return "explorer.exe", "Рабочий стол", ""

            length = user32.GetWindowTextLengthW(hwnd)
            title  = ""
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value

            pid = ctypes.wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            proc_name, full_path = self._get_process_info(pid.value)
            app_name = APP_NAMES.get(proc_name.lower(), self._clean_process_name(proc_name))
            clean_title = self._clean_title(title, app_name)
            return proc_name, app_name, clean_title, full_path
        except Exception as e:
            self._log_checkpoint(f"_get_active_window ОШИБКА: {e!r}")
            return "explorer.exe", "Рабочий стол", "", ""

    def _get_process_info(self, pid):
        try:
            handle = kernel32.OpenProcess(0x0400 | 0x0010, False, pid)
            if not handle:
                return "unknown.exe", ""
            buf  = ctypes.create_unicode_buffer(260)
            size = ctypes.wintypes.DWORD(260)
            ctypes.windll.psapi.GetModuleFileNameExW(handle, None, buf, size)
            kernel32.CloseHandle(handle)
            full = buf.value or ""
            return os.path.basename(full) if full else "unknown.exe", full
        except Exception:
            return "unknown.exe", ""

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
