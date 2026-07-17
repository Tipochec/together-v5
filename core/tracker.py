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

from core.app_maps import APP_NAMES, BROWSER_PROCESSES, CATEGORIES

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
    return os.path.join(os.path.dirname(__file__), "..", "settings.json")


def load_settings():
    try:
        with open(_settings_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        # Битый JSON (например неэкранированный \ в пути) раньше молча
        # обнулял ВСЕ настройки без единого следа — теперь хотя бы видно
        # в логе, что settings.json невалиден и почему
        try:
            log_path = os.path.join(os.path.dirname(_settings_path()), "ai_debug.log")
            with open(log_path, "a", encoding="utf-8") as lf:
                import time
                lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                         f"SETTINGS_JSON_BROKEN error={e} — все настройки временно сброшены на дефолт!\n")
        except Exception:
            pass
        return {}


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
        prev_app   = None
        prev_title = None

        while self._running:
            try:
                proc_name, app, title = self._get_active_window()
                idle_secs = self._get_idle_seconds()
                status    = self._calc_status(idle_secs, app, title)

                settings = load_settings()
                if settings.get("private_mode") and proc_name.lower() in BROWSER_PROCESSES:
                    title = ""

                changed = (app != prev_app or title != prev_title)

                if changed:
                    now = datetime.now()
                    category = CATEGORIES.get(app)
                    if category is None:
                        category = self._get_ai_category(app, title)

                    with self._lock:
                        if prev_app and prev_app != "—":
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
                    prev_app   = app
                    prev_title = title
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
            log_path = os.path.join(os.path.dirname(__file__), "..", "ai_debug.log")
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

        try:
            import sqlite3
            db_path = os.path.join(os.path.dirname(__file__), "..", "stats.db")
            # timeout — сколько ждать, если файл БД сейчас занят другим
            # потоком (stats.py тоже пишет в тот же stats.db каждую
            # секунду) — раньше таймаута не было явно указано, и при
            # совпадении по времени запись могла тихо не пройти
            conn = sqlite3.connect(db_path, timeout=10)

            # Проверяем, нет ли уже таблицы sessions с ДРУГОЙ (несовместимой)
            # структурой — например, оставшейся от более раннего варианта
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
            conn.close()
        except Exception as e:
            self._log_checkpoint(f"ОШИБКА при записи: {e}")

    def get_session_history(self, limit=10):
        try:
            import sqlite3
            db_path = os.path.join(os.path.dirname(__file__), "..", "stats.db")
            conn = sqlite3.connect(db_path, timeout=10)
            rows = conn.execute("""
                SELECT started_at, ended_at, active_seconds, watching_seconds, afk_seconds
                FROM sessions
                ORDER BY id DESC
                LIMIT ?
            """, (limit,)).fetchall()
            conn.close()
            return [
                {
                    "started_at": r[0], "ended_at": r[1],
                    "active": r[2], "watching": r[3], "afk": r[4],
                }
                for r in rows
            ]
        except Exception:
            return []

    def _calc_status(self, idle_secs, app, title):
        # Единственный критерий — бездействие клавиатуры/мыши.
        # Что при этом происходит на экране (ютуб, фильм, музыка) —
        # не имеет значения: сидит человек и правда смотрит или
        # отошёл на час, оставив видео включённым — с точки зрения
        # трекера активности это AFK.
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
            proc_name = self._get_process_name(pid.value)
            app_name  = APP_NAMES.get(proc_name.lower(), self._clean_process_name(proc_name))
            clean_title = self._clean_title(title, app_name)
            return proc_name, app_name, clean_title
        except Exception:
            return "explorer.exe", "Рабочий стол", ""

    def _get_process_name(self, pid):
        try:
            handle = kernel32.OpenProcess(0x0400 | 0x0010, False, pid)
            if not handle:
                return "unknown.exe"
            buf  = ctypes.create_unicode_buffer(260)
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

    def _get_ai_category(self, app_name, title):
        try:
            from core.ai_classify import classify_app, _load_cache
            key = app_name.lower().strip()
            cache = _load_cache()
            if key in cache:
                return cache[key]

            def worker():
                classify_app(app_name, title)
            threading.Thread(target=worker, daemon=True).start()
            return "other"
        except Exception:
            return "other"
