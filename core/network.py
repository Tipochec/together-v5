"""
Сетевой модуль - связь между двумя ПК через сокеты
"""
import json, threading, time, socket, os
from .chat import ChatManager
from datetime import datetime

PORT = 39721
RECONNECT_DELAY = 5
OFFLINE_TIMEOUT = 15    # секунд без пакета от партнёра — "сырое" подозрение на оффлайн
RECONNECT_GRACE = 30    # ещё столько секунд ждём подтверждения, прежде чем
                         # считать партнёра ДЕЙСТВИТЕЛЬНО оффлайн (фильтр от
                         # обычных сетевых морганий VPN — не создаём фантомные
                         # "перезаходы" в статусе/логе из-за секундного обрыва)


def _settings_path():
    return os.path.join(os.path.dirname(__file__), "..", "settings.json")


def load_settings():
    try:
        with open(_settings_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


class NetworkManager:
    def __init__(self, tracker):
        self.tracker = tracker
        self.chat = ChatManager()
        self.partner_data = None
        self._lock = threading.Lock()
        self._on_partner_update = []
        self._on_status_change = []
        self._on_message = []
        self._running = False
        self._connected = False   # для колбэка on_status_change (эдж-детект)
        self._last_seen = 0       # timestamp последнего ЛЮБОГО пакета от партнёра
        self._client_socket = None
        self._session_start = None       # когда партнёр зашёл в сеть (timestamp)
        self._last_offline_at = None     # когда партнёр последний раз вышел (timestamp)
        self._last_session_minutes = 0   # сколько длилась предыдущая сессия онлайна
        self._pending_offline_since = None  # с какого момента подозреваем обрыв (ещё не подтверждён)

    def on_partner_update(self, cb): self._on_partner_update.append(cb)
    def on_status_change(self, cb):  self._on_status_change.append(cb)
    
    def on_message(self, cb):
        self._on_message.append(cb)

    def get_partner_data(self):
        with self._lock:
            return dict(self.partner_data) if self.partner_data else None

    def get_chat_history(self, limit=50):
        return self.chat.get_messages(limit=limit)

    def clear_chat_history(self):
        self.chat.clear_all()
    
    def _raw_alive(self):
        """"Сырая" проверка — был ли пакет за последние OFFLINE_TIMEOUT секунд.
        Может моргать сама по себе при коротких обрывах сети/VPN."""
        return (time.time() - self._last_seen) < OFFLINE_TIMEOUT

    def is_connected(self):
        # Стабильный, подтверждённый статус (см. _watch_connection) —
        # именно он используется в интерфейсе, логе сессий и колбэках трея.
        # Короткие обрывы связи (короче RECONNECT_GRACE) сюда не долетают.
        return self._connected

    def start(self):
        self._running = True
        threading.Thread(target=self._run_server, daemon=True).start()
        threading.Thread(target=self._run_client, daemon=True).start()
        threading.Thread(target=self._watch_connection, daemon=True).start()

    def _watch_connection(self):
        # Раз в секунду проверяем статус. Смена "оба онлайн" → "оффлайн"
        # подтверждается не сразу — иначе секундное моргание VPN/сети
        # создавало фантомные "перезаходы" в логе, хотя партнёр никуда
        # не уходил. Обратно "в сеть" — наоборот, признаём мгновенно
        # (тут ложных срабатываний не бывает: раз пакет пришёл — значит
        # партнёр точно на связи).
        while self._running:
            raw = self._raw_alive()

            if raw:
                self._pending_offline_since = None
                if not self._connected:
                    self._connected = True
                    self._session_start = time.time()
                    for cb in self._on_status_change:
                        try:
                            cb(True)
                        except Exception:
                            pass

            elif self._connected:
                if self._pending_offline_since is None:
                    self._pending_offline_since = time.time()
                elif time.time() - self._pending_offline_since >= RECONNECT_GRACE:
                    # Обрыв подтверждён — партнёр действительно ушёл
                    self._connected = False
                    self._pending_offline_since = None
                    self._last_offline_at = time.time()
                    if self._session_start:
                        self._last_session_minutes = int(
                            (self._last_offline_at - self._session_start) / 60
                        )
                    self._session_start = None
                    for cb in self._on_status_change:
                        try:
                            cb(False)
                        except Exception:
                            pass

            time.sleep(1)

    def get_partner_status(self):
        """
        Один текущий статус партнёра (а не список событий):
        - онлайн → с какого времени (честно, из ЕЁ переданного online_since —
          не из момента, когда МЫ заметили её пакеты, иначе наш собственный
          перезапуск приложения сбрасывал бы её время входа)
        - оффлайн → с какого времени + сколько длилась прошлая сессия
        """
        if self._connected:
            since_str = "?"
            with self._lock:
                reported = (self.partner_data or {}).get("online_since")
            if reported:
                try:
                    since_str = datetime.fromisoformat(reported).strftime("%H:%M")
                except Exception:
                    pass
            if since_str == "?" and self._session_start:
                # partner_data ещё не пришёл (только что подключились) —
                # временно показываем локальную оценку, обновится на
                # следующем тике, когда придёт её пакет
                since_str = datetime.fromtimestamp(self._session_start).strftime("%H:%M")
            return {"online": True, "since": since_str}
        elif self._last_offline_at:
            return {
                "online": False,
                "since": datetime.fromtimestamp(self._last_offline_at).strftime("%H:%M"),
                "last_session_minutes": self._last_session_minutes,
            }
        return None  # ещё ни разу не было на связи с момента запуска

    def stop(self):
        self._running = False
        if self._client_socket:
            try: self._client_socket.close()
            except Exception: pass

    def update_settings(self, **kwargs):
        pass  # Настройки читаются из файла динамически

    # ── Сервер ────────────────────────────────────────────────
    def _run_server(self):
        while self._running:
            try:
                srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                srv.bind(("0.0.0.0", PORT))
                srv.listen(1)
                srv.settimeout(2.0)
                while self._running:
                    try:
                        conn, addr = srv.accept()
                        threading.Thread(
                            target=self._handle_conn, args=(conn,), daemon=True
                        ).start()
                    except socket.timeout:
                        continue
                srv.close()
            except Exception:
                time.sleep(3)

    def _handle_conn(self, conn):
        conn.settimeout(10.0)
        send_t = threading.Thread(target=self._send_loop, args=(conn,), daemon=True)
        send_t.start()
        self._recv_loop(conn)

    # ── Клиент ────────────────────────────────────────────────
    def _run_client(self):
        while self._running:
            s = load_settings()
            ip = s.get("ip", "").strip()
            if not ip:
                time.sleep(5)
                continue
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect((ip, PORT))
                sock.settimeout(10.0)
                self._client_socket = sock
                send_t = threading.Thread(target=self._send_loop, args=(sock,), daemon=True)
                send_t.start()
                self._recv_loop(sock)
            except Exception:
                pass
            finally:
                if self._client_socket:
                    try: self._client_socket.close()
                    except Exception: pass
                    self._client_socket = None
            time.sleep(RECONNECT_DELAY)

    # ── Общение ───────────────────────────────────────────────
    def _send_loop(self, sock):
        while self._running:
            try:
                payload = self._build_payload()
                sock.sendall((json.dumps(payload, ensure_ascii=False) + "\n").encode())
            except Exception:
                break
            time.sleep(2)

    def _recv_loop(self, conn):
        buf = ""
        while self._running:
            try:
                chunk = conn.recv(4096).decode("utf-8")
                if not chunk:
                    break
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    if line.strip():
                        self._process(line.strip())
            except socket.timeout:
                continue
            except Exception:
                break

    def _build_payload(self):
        s = load_settings()
        current = self.tracker.get_current()
        history = self.tracker.get_history()[:10]
        return {
            "type": "activity",
            "name": s.get("name") or "Партнёр",
            "gender": s.get("gender") or "male",
            "avatar": s.get("avatar") or "",
            "app":  current.get("app", "—"),
            "title": current.get("title", ""),
            "category": current.get("category", "other"),
            "afk":  current.get("afk", False),
            "since": current.get("since", datetime.now()).isoformat(),
            # Моё СОБСТВЕННОЕ время запуска приложения — партнёр покажет
            # у себя именно его как "в сети с", а не момент, когда ОН меня
            # обнаружил (это чинит баг с ложным сбросом времени входа при
            # перезапуске приложения на стороне того, кто СМОТРИТ статус)
            "online_since": self.tracker.get_session_start().isoformat(),
            "history": [
                {
                    "app":   h.get("app","—"),
                    "title": h.get("title",""),
                    "time":  h["timestamp"].strftime("%H:%M") if h.get("timestamp") else "—",
                    "ts":    h["timestamp"].isoformat() if h.get("timestamp") else "0",
                    "category": h.get("category","other"),
                }
                for h in history
            ],
        }
        
    def send_message(self, text):
        text = text.strip()

        if not text:
            return

        settings = load_settings()

        packet = {
            "type": "message",
            "sender": settings.get("name") or "Я",
            "text": text[:1000],
            "time": datetime.now().isoformat()
        }

        self.chat.add_message(
            sender=packet["sender"],
            text=packet["text"],
            incoming=False
        )

        if self._client_socket:
            try:
                self._client_socket.sendall(
                    (json.dumps(packet, ensure_ascii=False) + "\n").encode()
                )
            except Exception:
                pass

    def _process(self, raw):
        try:
            data = json.loads(raw)

            packet_type = data.get("type")

            if packet_type == "activity":
                self._process_activity(data)

            elif packet_type == "message":
                self._process_message(data)

        except Exception:
            pass


    def _process_activity(self, data):
        with self._lock:
            self.partner_data = data
        self._last_seen = time.time()

        for cb in self._on_partner_update:
            try:
                cb(data)
            except Exception:
                pass


    def _process_message(self, data):
        self._last_seen = time.time()
        self.chat.add_message(
            sender=data.get("sender") or "Партнёр",
            text=data.get("text", "")[:1000],
            incoming=True
        )

        for cb in self._on_message:
            try:
                cb(data)
            except Exception:
                pass
    
    def _set_connected(self, val):
        # Оставлено для обратной совместимости, если что-то извне ещё
        # дёргает этот метод напрямую — но основная логика теперь в
        # _watch_connection() выше, основанной на _last_seen.
        if self._connected != val:
            self._connected = val
            for cb in self._on_status_change:
                try: cb(val)
                except Exception: pass
