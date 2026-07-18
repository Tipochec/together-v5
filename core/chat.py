import sqlite3
import threading
import os
from datetime import datetime
from core.paths import data_path


DB_PATH = data_path("stats.db")


class ChatManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self):
        return sqlite3.connect(DB_PATH, timeout=10)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    text TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    incoming INTEGER NOT NULL,
                    is_read INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.commit()

    def add_message(self, sender, text, incoming):
        with self._lock:
            with self._connect() as conn:
                conn.execute("""
                    INSERT INTO messages
                    (sender, text, created_at, incoming)
                    VALUES (?, ?, ?, ?)
                """, (
                    sender,
                    text,
                    datetime.now().isoformat(),
                    int(incoming)
                ))
                conn.commit()

    def get_messages(self, limit=100):
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT sender, text, created_at, incoming
                FROM messages
                ORDER BY id DESC
                LIMIT ?
            """, (limit,)).fetchall()

        rows.reverse()

        return [
            {
                "sender": r[0],
                "text": r[1],
                "time": r[2],
                "incoming": bool(r[3])
            }
            for r in rows
        ]

    def mark_all_read(self):
        with self._connect() as conn:
            conn.execute("UPDATE messages SET is_read = 1")
            conn.commit()

    def clear_all(self):
        """Удаляет ВСЮ локальную историю чата. У партнёра его копия не трогается —
        у каждого своя независимая база, это осознанно (чат для мимолётных
        сообщений, а не архив переписки)."""
        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM messages")
                conn.commit()

    def get_last_messages(self, limit=50):
        return self.get_messages(limit)