import sqlite3
import threading
import os
import uuid
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
            # Поля для "ответить на сообщение" — добавлены позже, поэтому
            # через ALTER TABLE, чтобы у людей с уже существующей базой
            # ничего не потерялось. msg_uid — не то же самое, что id: id
            # у каждого свой, локальный, автоинкрементный, и у отправителя
            # с получателем НЕ совпадает (это два независимых файла БД на
            # двух разных компьютерах) — а msg_uid генерируется один раз
            # на отправляющей стороне и едет вместе с сообщением по сети,
            # поэтому именно на него можно сослаться из reply_to_uid и
            # получить одинаковый результат что у себя, что у партнёра.
            # reply_sender/reply_text — снимок текста сообщения, на которое
            # отвечают, сделанный В МОМЕНТ ответа: даже если исходное
            # сообщение потом удалят из истории (например "очистить чат" —
            # см. clear_all), сама цитата в ответе не потеряется.
            existing_cols = {row[1] for row in
                             conn.execute("PRAGMA table_info(messages)").fetchall()}
            for col_def in [
                ("msg_uid", "TEXT"),
                ("reply_to_uid", "TEXT"),
                ("reply_sender", "TEXT"),
                ("reply_text", "TEXT"),
            ]:
                col_name, col_type = col_def
                if col_name not in existing_cols:
                    conn.execute(f"ALTER TABLE messages ADD COLUMN {col_name} {col_type}")
            conn.commit()

    def add_message(self, sender, text, incoming, msg_uid=None,
                     reply_to_uid=None, reply_sender=None, reply_text=None):
        # msg_uid должен быть один и тот же и в локальной записи
        # отправителя, и в пакете, который улетает партнёру — поэтому
        # генерируем его здесь только если он ещё не передан (входящие
        # сообщения приносят msg_uid партнёра с собой, свои собственные —
        # генерируются заранее в network.py ДО вызова add_message, чтобы
        # тот же uid ушёл и в сеть).
        msg_uid = msg_uid or uuid.uuid4().hex
        with self._lock:
            with self._connect() as conn:
                conn.execute("""
                    INSERT INTO messages
                    (sender, text, created_at, incoming, msg_uid,
                     reply_to_uid, reply_sender, reply_text)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    sender,
                    text,
                    datetime.now().isoformat(),
                    int(incoming),
                    msg_uid,
                    reply_to_uid,
                    reply_sender,
                    reply_text,
                ))
                conn.commit()
        return msg_uid

    def get_messages(self, limit=100):
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT sender, text, created_at, incoming, msg_uid,
                       reply_to_uid, reply_sender, reply_text
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
                "incoming": bool(r[3]),
                "msg_uid": r[4],
                "reply_to_uid": r[5],
                "reply_sender": r[6],
                "reply_text": r[7],
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