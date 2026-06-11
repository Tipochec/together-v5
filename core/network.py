"""
Сетевой модуль - связь между двумя ПК через сокеты
"""
import json, threading, time, socket, os
from datetime import datetime

PORT = 39721
RECONNECT_DELAY = 5


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
        self.partner_data = None
        self._partner_last_seen = 0   # timestamp последнего пакета
        self._lock = threading.Lock()
        self._on_partner_update = []
        self._on_status_change = []
        self._running = False
        self._connected = False
        self._client_socket = None

    def on_partner_update(self, cb): self._on_partner_update.append(cb)
    def on_status_change(self, cb):  self._on_status_change.append(cb)

    def get_partner_data(self):
        with self._lock:
            # Если данных нет или они старше 15 секунд — офлайн
            if not self.partner_data:
                return None
            if time.time() - self._partner_last_seen > 15:
                return None
            return dict(self.partner_data)

    def is_connected(self):
        return self.partner_data is not None and (time.time() - self._partner_last_seen) < 15

    def start(self):
        self._running = True
        threading.Thread(target=self._run_server, daemon=True).start()
        threading.Thread(target=self._run_client, daemon=True).start()

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
        self._set_connected(False)

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
                self._set_connected(True)
                send_t = threading.Thread(target=self._send_loop, args=(sock,), daemon=True)
                send_t.start()
                self._recv_loop(sock)
            except Exception:
                pass
            finally:
                self._set_connected(False)
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
            "name": s.get("name", "Партнёр"),
            "app":  current.get("app", "—"),
            "title": current.get("title", ""),
            "category": current.get("category", "other"),
            "afk":  current.get("afk", False),
            "since": current.get("since", datetime.now()).isoformat(),
            "history": [
                {
                    "app":   h.get("app","—"),
                    "title": h.get("title",""),
                    "time":  h["timestamp"].strftime("%H:%M") if h.get("timestamp") else "—",
                    "category": h.get("category","other"),
                }
                for h in history
            ],
        }

    def _process(self, raw):
        try:
            data = json.loads(raw)
            if data.get("type") == "activity":
                with self._lock:
                    self.partner_data = data
                    self._partner_last_seen = time.time()
                for cb in self._on_partner_update:
                    try: cb(data)
                    except Exception: pass
        except Exception:
            pass

    def _set_connected(self, val):
        if self._connected != val:
            self._connected = val
            for cb in self._on_status_change:
                try: cb(val)
                except Exception: pass
