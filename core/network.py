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

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "network_debug.log")
HEALTH_LOG_INTERVAL = 300  # раз в 5 минут пишем в лог "всё ок" / текущий статус

_log_lock = threading.Lock()
_last_throttled = {}
_throttle_counts = {}   # key -> сколько раз событие было подавлено с последнего вывода
_throttle_lock = threading.Lock()


def _log(msg):
    """Пишет строку с таймстампом в network_debug.log (и в stdout — видно
    при запуске из консоли). Тот же формат, что и у _log в ai_classify.py,
    для единообразия."""
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    try:
        with _log_lock:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception:
        pass


def _log_throttled(key, msg, min_interval=60):
    """Как _log(), но не чаще одного раза в min_interval секунд для одного
    и того же key. Нужно для событий, которые могут повторяться очень часто
    подряд (например: сеть/VPN легли на час — без троттлинга попытки
    переподключения раз в RECONNECT_DELAY=5 сек залили бы лог тысячами
    одинаковых строк за это время).

    Подавленные повторы не пропадают молча — их количество копится и
    дописывается к следующей прошедшей строке ("повторилось ещё N раз"),
    иначе по логу выглядело бы так, будто проблема случилась один раз,
    хотя на деле была целая серия обрывов подряд — это сбивало с толку
    при разборе реального инцидента."""
    now = time.time()
    with _throttle_lock:
        last = _last_throttled.get(key, 0)
        if now - last < min_interval:
            _throttle_counts[key] = _throttle_counts.get(key, 0) + 1
            return
        repeated = _throttle_counts.pop(key, 0)
        _last_throttled[key] = now
    if repeated:
        msg = f"{msg} [повторилось ещё {repeated} раз за последнюю минуту]"
    _log(msg)


def get_network_log(lines=200):
    """Последние N строк лога — используется UI (кнопка в настройках)."""
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            content = f.readlines()
        return "".join(content[-lines:])
    except FileNotFoundError:
        return ""
    except Exception as e:
        return f"ошибка чтения лога: {e}"


def _settings_path():
    return os.path.join(os.path.dirname(__file__), "..", "settings.json")


def load_settings():
    try:
        with open(_settings_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _enable_keepalive(sock, idle=5, interval=3, count=3):
    """Включает агрессивный TCP keepalive на сокете.

    Без этого "тихий" обрыв связи (VPN/сеть моргнули без честного FIN/RST —
    типичная история для ZeroTier/RadminVPN при смене сети, сне ноутбука,
    NAT-таймауте) остаётся незамеченным ОС очень долго: sendall() в
    полу-мёртвый сокет может отрабатывать без ошибки (данные просто уходят
    в никуда), пока ядро само не решит, что пора считать соединение
    мёртвым — а это может занять много МИНУТ, а не секунд. Из-за этого
    и был баг "чат перестаёт доходить в одну сторону, но через какое-то
    время сам оживает" — второй эффект как раз и есть момент, когда ОС
    наконец обнаруживает обрыв, heartbeat/_send_raw() ловит ошибку,
    закрывает мёртвый сокет, а _run_client переподключается.

    С keepalive ОС сама шлёт зондирующие пакеты и обнаруживает обрыв за
    ~idle + interval*count секунд (тут ~14 сек — совпадает по порядку
    величины с уже существующим OFFLINE_TIMEOUT).
    """
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    except Exception:
        pass
    try:
        if hasattr(socket, "TCP_KEEPIDLE"):
            # Linux
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, idle)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, count)
        elif hasattr(socket, "TCP_KEEPALIVE"):
            # macOS
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPALIVE, idle)
        elif hasattr(socket, "SIO_KEEPALIVE_VALS"):
            # Windows — основная целевая платформа этого приложения
            # (значения в миллисекундах: время простоя, интервал зондов)
            sock.ioctl(
                socket.SIO_KEEPALIVE_VALS,
                (1, idle * 1000, interval * 1000)
            )
    except Exception:
        pass


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
        self._send_lock = threading.Lock()  # защита от одновременной записи в
                                             # сокет из _send_loop (heartbeat раз в
                                             # 2 сек) и send_message() параллельно
        self._session_start = None       # когда партнёр зашёл в сеть (timestamp)
        self._last_offline_at = None     # когда партнёр последний раз вышел (timestamp)
        self._last_session_minutes = 0   # сколько длилась предыдущая сессия онлайна
        self._pending_offline_since = None  # с какого момента подозреваем обрыв (ещё не подтверждён)
        self._msgs_sent = 0               # сколько сообщений чата ушло в сеть (для лога здоровья)
        self._msgs_received = 0           # сколько сообщений чата пришло от партнёра
        self._connect_failures = 0        # подряд неудачных попыток клиента подключиться
        self._last_health_log = time.time()

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
                    _log("STATUS: партнёр в сети")
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
                    _log(f"STATUS: партнёр вышел из сети (сессия длилась {self._last_session_minutes} мин)")
                    for cb in self._on_status_change:
                        try:
                            cb(False)
                        except Exception:
                            pass

            if time.time() - self._last_health_log >= HEALTH_LOG_INTERVAL:
                self._last_health_log = time.time()
                self._log_health()

            time.sleep(1)

    def _log_health(self):
        """Периодическая запись в лог, что всё в порядке (или явно не в
        порядке) — чтобы по логу можно было понять, было ли приложение
        вообще живо и что оно видело, даже если никто не жаловался."""
        if self._connected:
            uptime_min = int((time.time() - self._session_start) / 60) if self._session_start else 0
            _log(
                f"HEALTH: всё в порядке — партнёр на связи уже {uptime_min} мин, "
                f"сообщений отправлено={self._msgs_sent} получено={self._msgs_received}"
            )
        else:
            _log(
                f"HEALTH: партнёр НЕ на связи, пытаемся переподключиться "
                f"(неудачных попыток клиента подряд: {self._connect_failures})"
            )

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
        self._close_client_socket()

    def _close_client_socket(self, sock_hint=None):
        """
        Единая точка закрытия исходящего клиентского сокета.

        sock_hint — если передан, закрываем только если это ТОТ ЖЕ объект,
        что сейчас лежит в self._client_socket. Нужно, чтобы поток с устаревшей
        ссылкой на старый сокет (например упавший _send_loop, который уже
        какое-то время как заблокирован в sendall) не мог случайно прибить
        новый сокет, который _run_client успел переоткрыть за это время.

        Раньше закрытие/обнуление self._client_socket происходило только в
        finally-блоке _run_client — но управление попадало туда лишь когда
        _recv_loop() реально завершался с исключением. При «тихом» обрыве
        связи (сеть/VPN моргнули без честного FIN/RST) recv() просто уходит
        в бесконечные таймауты и continue, соединение годами считалось
        живым — из-за этого send_message() слал в мёртвый сокет и подвисал
        на socket-таймауте (10-20 сек), а сам сокет так и оставался
        «рабочим» для всех последующих сообщений вплоть до перезапуска
        приложения. Теперь любой, кто первым обнаружит обрыв (heartbeat в
        _send_loop ИЛИ отправка сообщения), сразу закрывает и обнуляет
        сокет — следующая попытка отправки уже не виснет, а корректно
        считает, что связи нет, и _run_client переподключается по таймеру.
        """
        with self._send_lock:
            sock = self._client_socket
            if sock is None:
                return
            if sock_hint is not None and sock is not sock_hint:
                return
            self._client_socket = None
        try:
            sock.close()
        except Exception:
            pass

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
                _log(f"SERVER: слушаем входящие подключения на порту {PORT}")
                while self._running:
                    try:
                        conn, addr = srv.accept()
                        threading.Thread(
                            target=self._handle_conn, args=(conn, addr), daemon=True
                        ).start()
                    except socket.timeout:
                        continue
                srv.close()
            except Exception as e:
                _log_throttled(
                    "server_bind_error",
                    f"SERVER: не удалось запустить сервер на порту {PORT} — "
                    f"{type(e).__name__}: {e}"
                )
                time.sleep(3)

    def _handle_conn(self, conn, addr):
        _enable_keepalive(conn)
        conn.settimeout(10.0)
        peer = addr[0] if addr else "?"
        _log(f"SERVER: входящее подключение от {peer}")
        send_t = threading.Thread(target=self._send_loop, args=(conn,), daemon=True)
        send_t.start()
        self._recv_loop(conn, label=f"SERVER<-{peer}")
        _log(f"SERVER: соединение от {peer} закрыто")

    # ── Клиент ────────────────────────────────────────────────
    def _run_client(self):
        while self._running:
            s = load_settings()
            ip = s.get("ip", "").strip()
            if not ip:
                time.sleep(5)
                continue
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect((ip, PORT))
                _enable_keepalive(sock)
                sock.settimeout(10.0)
                self._client_socket = sock
                if self._connect_failures:
                    _log(f"CLIENT: снова подключились к {ip}:{PORT} "
                         f"(после {self._connect_failures} неудачных попыток)")
                else:
                    _log(f"CLIENT: подключились к {ip}:{PORT}")
                self._connect_failures = 0
                send_t = threading.Thread(target=self._send_loop, args=(sock,), daemon=True)
                send_t.start()
                self._recv_loop(sock, label=f"CLIENT->{ip}")
            except Exception as e:
                self._connect_failures += 1
                _log_throttled(
                    "client_connect_fail",
                    f"CLIENT: не удаётся подключиться к {ip}:{PORT} — "
                    f"{type(e).__name__}: {e} (попыток подряд: {self._connect_failures})"
                )
            finally:
                if sock is not None:
                    self._close_client_socket(sock_hint=sock)
            time.sleep(RECONNECT_DELAY)

    # ── Общение ───────────────────────────────────────────────
    def _send_raw(self, sock, payload_dict):
        """
        Единая точка записи в исходящий клиентский сокет — используется и
        heartbeat'ом (_send_loop, раз в 2 сек), и отправкой сообщений
        (send_message). Лок нужен, чтобы два потока не писали в один сокет
        одновременно: sendall() не атомарен, и при параллельном вызове из
        двух потоков строки JSON двух разных пакетов теоретически могут
        перемежаться в байтовом потоке и сломать построчный парсинг на
        стороне партнёра (_recv_loop бьёт буфер по "\\n").

        При любой ошибке сразу закрываем и обнуляем self._client_socket
        через _close_client_socket() — раньше это делалось только в
        finally _run_client, а туда управление попадало лишь после того,
        как _recv_loop() падал с исключением. При "тихом" обрыве связи
        (VPN моргнул без честного FIN/RST) recv() просто уходил в вечные
        таймауты и не падал — сокет годами считался рабочим, и КАЖДАЯ
        следующая попытка отправки сообщения заново повисала на
        socket-таймауте (10-20 сек), пока не перезапустишь приложение.
        Теперь первая же неудачная запись сразу помечает соединение
        мёртвым — все последующие вызовы видят self._client_socket=None
        и не пытаются писать в него, а _run_client переподключается сам
        по таймеру (RECONNECT_DELAY).
        """
        try:
            with self._send_lock:
                sock.sendall(
                    (json.dumps(payload_dict, ensure_ascii=False) + "\n").encode()
                )
            return True
        except Exception as e:
            _log(
                f"SEND: ошибка отправки пакета type={payload_dict.get('type', '?')} — "
                f"{type(e).__name__}: {e} — закрываю сокет"
            )
            self._close_client_socket(sock_hint=sock)
            return False

    def _send_loop(self, sock):
        while self._running:
            payload = self._build_payload()
            if not self._send_raw(sock, payload):
                break
            time.sleep(2)

    def _recv_loop(self, conn, label="conn"):
        # ВАЖНО: буфер держим в БАЙТАХ и декодируем в UTF-8 только уже
        # полностью собранную строку (после разделителя \n), а не сырой
        # кусок из recv() как есть. TCP режет поток на пакеты произвольно,
        # не заботясь о границах символов — если recv(4096) обрывается
        # ровно посередине многобайтового символа (а кириллица в JSON
        # почти в каждом пакете), decode() всего чанка целиком падает с
        # UnicodeDecodeError. Раньше это ловилось общим except как "обрыв
        # связи" и рвало абсолютно рабочее соединение на пустом месте —
        # разделитель \n (0x0A) физически не может встретиться внутри
        # многобайтовой UTF-8 последовательности, так что резать по нему
        # в байтах всегда безопасно, а декодировать нужно только то, что
        # уже точно целая строка целиком.
        buf = b""
        while self._running:
            try:
                chunk = conn.recv(4096)
                if not chunk:
                    _log(f"{label}: партнёр закрыл соединение штатно (пустой пакет)")
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if not line.strip():
                        continue
                    try:
                        text = line.decode("utf-8")
                    except UnicodeDecodeError as e:
                        _log_throttled(
                            f"decode_error:{label}",
                            f"{label}: не удалось декодировать строку ({type(e).__name__}: {e}) — пропускаю пакет"
                        )
                        continue
                    self._process(text.strip())
            except socket.timeout:
                continue
            except Exception as e:
                _log_throttled(
                    f"recv_error:{label}",
                    f"{label}: ошибка чтения из сокета — {type(e).__name__}: {e}"
                )
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

        # Сохраняем локально сразу — мгновенный отклик в UI, независимо от
        # состояния сети (у каждого своя локальная копия истории чата).
        self.chat.add_message(
            sender=packet["sender"],
            text=packet["text"],
            incoming=False
        )

        # Реальная отправка по сети — в отдельном потоке, не в потоке
        # вызова. WindowAPI.send_message() дёргается СИНХРОННО из JS-моста
        # pywebview (см. ui/window.py), поэтому раньше блокирующий sendall()
        # на подвисшем сокете морозил всё окно на 10-20 сек. Теперь UI
        # отпускается сразу; результат отправки на него не влияет — при
        # неудаче _send_raw() сам закроет мёртвый сокет (см. его докстринг),
        # и следующее сообщение уже не наступит на те же грабли.
        sock = self._client_socket
        if sock:
            self._msgs_sent += 1
            threading.Thread(
                target=self._send_raw, args=(sock, packet), daemon=True
            ).start()
        else:
            # партнёр сейчас не на связи — сообщение осталось только
            # локально, это ожидаемо (видно по статусу подключения в трее/окне).
            _log("MSG: партнёр не на связи — сообщение сохранено только локально")

    def _process(self, raw):
        try:
            data = json.loads(raw)

            packet_type = data.get("type")

            if packet_type == "activity":
                self._process_activity(data)

            elif packet_type == "message":
                self._process_message(data)

            else:
                _log_throttled(
                    "unknown_packet_type",
                    f"RECV: неизвестный тип пакета: {packet_type!r}"
                )

        except Exception as e:
            _log_throttled(
                "bad_packet",
                f"RECV: не удалось разобрать пакет ({type(e).__name__}: {e}), "
                f"raw={raw[:200]!r}"
            )


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
        self._msgs_received += 1
        text = data.get("text", "")[:1000]
        _log(f"MSG: получено сообщение от {data.get('sender') or 'Партнёр'} ({len(text)} симв.)")
        self.chat.add_message(
            sender=data.get("sender") or "Партнёр",
            text=text,
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
