"""
Статистика времени в приложениях — SQLite база данных.
Записывает сколько времени провёл в каждом приложении за каждый день.
"""
import sqlite3
import os
import threading
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "stats.db")


def get_db():
    """Подключение к БД (создаёт если нет)"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Создаём таблицы при первом запуске"""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_time (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                date      TEXT NOT NULL,          -- "2024-01-15"
                app       TEXT NOT NULL,          -- "CS2"
                category  TEXT NOT NULL,          -- "gaming"
                seconds   INTEGER DEFAULT 0,      -- накопленное время в секундах
                UNIQUE(date, app)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                date       TEXT NOT NULL,
                app        TEXT NOT NULL,
                category   TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at   TEXT,
                seconds    INTEGER DEFAULT 0
            )
        """)
        conn.commit()


class StatsTracker:
    """
    Подписывается на трекер активности и пишет время в БД.
    Каждую секунду прибавляет 1 к текущему приложению.
    """
    def __init__(self, tracker):
        self.tracker = tracker
        self._lock = threading.Lock()
        self._running = False
        self._current_app = None
        self._current_cat = None
        self._session_start = None
        init_db()

    def start(self):
        import time
        self._running = True
        while self._running:
            try:
                current = self.tracker.get_current()
                app = current.get("app", "—")
                cat = current.get("category", "other")
                afk = current.get("afk", False)

                # Не считаем AFK и рабочий стол
                if not afk and app not in ("—", "Рабочий стол"):
                    self._record(app, cat)
            except Exception:
                pass
            time.sleep(1)

    def stop(self):
        self._running = False

    def _record(self, app, category):
        """Прибавляем 1 секунду к приложению за сегодня"""
        today = date.today().isoformat()
        try:
            with get_db() as conn:
                conn.execute("""
                    INSERT INTO app_time (date, app, category, seconds)
                    VALUES (?, ?, ?, 1)
                    ON CONFLICT(date, app) DO UPDATE SET seconds = seconds + 1
                """, (today, app, category))
                conn.commit()
        except Exception:
            pass

    # ── Запросы для UI ────────────────────────────────────────

    def get_today(self):
        """Топ приложений за сегодня"""
        today = date.today().isoformat()
        with get_db() as conn:
            rows = conn.execute("""
                SELECT app, category, seconds
                FROM app_time
                WHERE date = ?
                ORDER BY seconds DESC
                LIMIT 10
            """, (today,)).fetchall()
        return [dict(r) for r in rows]

    def get_week(self):
        """Топ приложений за последние 7 дней"""
        with get_db() as conn:
            rows = conn.execute("""
                SELECT app, category, SUM(seconds) as seconds
                FROM app_time
                WHERE date >= date('now', '-7 days')
                GROUP BY app
                ORDER BY seconds DESC
                LIMIT 10
            """).fetchall()
        return [dict(r) for r in rows]

    def get_daily_totals(self):
        """Общее время по дням за последние 7 дней"""
        with get_db() as conn:
            rows = conn.execute("""
                SELECT date, SUM(seconds) as seconds
                FROM app_time
                WHERE date >= date('now', '-7 days')
                GROUP BY date
                ORDER BY date ASC
            """).fetchall()
        return [dict(r) for r in rows]

    def get_category_totals(self):
        """Время по категориям за сегодня"""
        today = date.today().isoformat()
        with get_db() as conn:
            rows = conn.execute("""
                SELECT category, SUM(seconds) as seconds
                FROM app_time
                WHERE date = ?
                GROUP BY category
                ORDER BY seconds DESC
            """, (today,)).fetchall()
        return [dict(r) for r in rows]


def fmt_time(seconds):
    """Форматируем секунды в читаемый вид: 1ч 23м"""
    if seconds < 60:
        return f"{seconds}с"
    m = seconds // 60
    if m < 60:
        return f"{m}м"
    h = m // 60
    m = m % 60
    return f"{h}ч {m}м" if m else f"{h}ч"
