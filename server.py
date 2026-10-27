"""
Together Relay, Offline Buffer & Live Monitoring Server.

Функции:
1. Ретранслятор активности и чата (Real-time TCP Relay).
2. Защита комнат (максимум 2 устройства на room_key).
3. Оффлайн-буфер сообщений (SQLite relay.db).
4. Автоматическое отслеживание пользователей (Имя, Версия, IP, Время, Пакеты).
5. Встроенный веб-дашборд (Web Monitoring Dashboard) на порту 39720.
"""
import asyncio
import json
import logging
import sqlite3
import os
import time
from datetime import datetime
import urllib.parse

PORT = 39722             # Порт для клиентов Together (TCP)
DASHBOARD_PORT = 39720   # Порт веб-дашборда (HTTP)
HOST = "0.0.0.0"
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "relay.db")
DASHBOARD_PASS = "together2026"  # Пароль для входа в дашборд

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Память активных соединений:
# ROOM_CLIENTS[room_key] = { device_id: { "writer": writer, "ip": ip, "name": name, "version": ver, "since": time.time() } }
ROOM_CLIENTS = {}
WRITER_TO_CLIENT = {}

# Глобальные счетчики сессии:
SERVER_START_TIME = time.time()
STATS_COUNTERS = {
    "total_messages": 0,
    "total_activities": 0,
    "total_hearts": 0,
    "blocked_scanners": 0,
}


def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        # Таблица комнат и привязки (максимум 2 устройства)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS room_devices (
                room_key TEXT NOT NULL,
                device_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (room_key, device_id)
            )
        """)
        # Таблица оффлайн-сообщений
        conn.execute("""
            CREATE TABLE IF NOT EXISTS offline_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_key TEXT NOT NULL,
                target_device_id TEXT,
                payload TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Таблица детальной информации об устройствах и пользователях
        conn.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                room_key TEXT NOT NULL,
                user_name TEXT,
                app_version TEXT,
                ip_address TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                packets_count INTEGER DEFAULT 0
            )
        """)
        # Таблица аудита событий (последние события)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                ip TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Автоматически мигрируем старые устройства из room_devices в devices
        conn.execute("""
            INSERT OR IGNORE INTO devices (device_id, room_key, user_name, app_version, ip_address, first_seen, last_seen, packets_count)
            SELECT device_id, room_key, 'Раннее устройство', 'старая версия', '', created_at, created_at, 1
            FROM room_devices
        """)
        conn.commit()


def log_event(event_type: str, ip: str, details: str):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                "INSERT INTO audit_events (event_type, ip, details) VALUES (?, ?, ?)",
                (event_type, ip, details)
            )
            # Храним только последние 200 событий, чтобы база не разрасталась
            conn.execute("DELETE FROM audit_events WHERE id NOT IN (SELECT id FROM audit_events ORDER BY id DESC LIMIT 200)")
            conn.commit()
    except Exception:
        pass


def update_device_record(device_id: str, room_key: str, user_name: str = None, app_version: str = None, ip_address: str = None, inc_packets: int = 0):
    if not device_id or not room_key:
        return
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT device_id, user_name, app_version, ip_address, packets_count FROM devices WHERE device_id = ?", (device_id,))
        row = cur.fetchone()
        if row:
            name = user_name or row[1] or "Пользователь"
            ver = app_version or row[2] or "unknown"
            ip = ip_address or row[3] or ""
            pkts = (row[4] or 0) + inc_packets
            cur.execute("""
                UPDATE devices 
                SET room_key = ?, user_name = ?, app_version = ?, ip_address = ?, last_seen = ?, packets_count = ?
                WHERE device_id = ?
            """, (room_key, name, ver, ip, now_str, pkts, device_id))
        else:
            cur.execute("""
                INSERT INTO devices (device_id, room_key, user_name, app_version, ip_address, first_seen, last_seen, packets_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (device_id, room_key, user_name or "Пользователь", app_version or "unknown", ip_address or "", now_str, now_str, inc_packets))
        conn.commit()


def authorize_device(room_key: str, device_id: str) -> bool:
    if not room_key or not device_id:
        return False

    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT device_id FROM room_devices WHERE room_key = ?", (room_key,))
        devices = [row[0] for row in cur.fetchall()]

        if device_id in devices:
            return True

        if len(devices) < 2:
            cur.execute("INSERT OR IGNORE INTO room_devices (room_key, device_id) VALUES (?, ?)", (room_key, device_id))
            conn.commit()
            logging.info(f"Устройство {device_id} привязано к комнате '{room_key}' (устройств: {len(devices) + 1}/2)")
            return True

        return False


def get_room_devices(room_key: str):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT device_id FROM room_devices WHERE room_key = ?", (room_key,))
        return [row[0] for row in cur.fetchall()]


def save_offline_message(room_key: str, target_device_id: str, payload_str: str):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO offline_messages (room_key, target_device_id, payload) VALUES (?, ?, ?)",
            (room_key, target_device_id, payload_str)
        )
        conn.commit()


def fetch_and_clear_offline_messages(room_key: str, device_id: str):
    messages = []
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, payload FROM offline_messages
            WHERE room_key = ? AND (target_device_id = ? OR target_device_id IS NULL OR target_device_id = '')
            ORDER BY id ASC
        """, (room_key, device_id))
        rows = cur.fetchall()
        if rows:
            ids = [r[0] for r in rows]
            messages = [r[1] for r in rows]
            cur.execute(f"DELETE FROM offline_messages WHERE id IN ({','.join(['?']*len(ids))})", ids)
            conn.commit()
    return messages


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    peer = writer.get_extra_info("peername")
    peer_ip = peer[0] if peer else "unknown"
    logging.info(f"Новое TCP-соединение от {peer}")

    current_room = None
    current_device = None
    first_packet = True

    try:
        while True:
            line = await reader.readline()
            if not line:
                break

            try:
                data = json.loads(line.decode("utf-8").strip())
            except Exception:
                # Если первый же пакет не JSON — это интернет-сканер (Shodan/Censys)
                if first_packet:
                    STATS_COUNTERS["blocked_scanners"] += 1
                    log_event("scanner", peer_ip, "Невалидный TCP-запрос (отсечён сканер портов)")
                    logging.warning(f"Отсечён сканер портов с {peer_ip}")
                break

            first_packet = False
            msg_type = data.get("type")
            room_key = (data.get("pairing_key") or "").strip()
            device_id = (data.get("device_id") or "").strip()
            user_name = data.get("name")
            app_version = data.get("version")

            if not room_key:
                continue

            # Обработка входа / регистрации устройства
            if current_room != room_key or current_device != device_id:
                if not authorize_device(room_key, device_id):
                    logging.warning(f"Отказ в доступе: устройство {device_id} не входит в доверенные для комнаты '{room_key}'")
                    log_event("denied", peer_ip, f"Отказ устройству {device_id} (комната '{room_key}' заполнена)")
                    err_msg = json.dumps({
                        "type": "error",
                        "code": "ROOM_FULL",
                        "message": "Комната уже занята двумя другими устройствами. Проверьте ключ подключения."
                    }, ensure_ascii=False) + "\n"
                    writer.write(err_msg.encode("utf-8"))
                    await writer.drain()
                    break

                # Отвязываем от старой комнаты при смене
                if current_room and current_room in ROOM_CLIENTS:
                    ROOM_CLIENTS[current_room].pop(current_device, None)

                current_room = room_key
                current_device = device_id
                if current_room not in ROOM_CLIENTS:
                    ROOM_CLIENTS[current_room] = {}
                ROOM_CLIENTS[current_room][current_device] = {
                    "writer": writer,
                    "ip": peer_ip,
                    "name": user_name or "Пользователь",
                    "version": app_version or "unknown",
                    "since": time.time()
                }
                WRITER_TO_CLIENT[writer] = (current_room, current_device)

                update_device_record(current_device, current_room, user_name, app_version, peer_ip, inc_packets=1)
                log_event("connect", peer_ip, f"Вошел пользователь '{user_name or 'Пользователь'}' (v{app_version or '?'}) в комнату '{current_room}'")

                reg_confirm = json.dumps({
                    "type": "registered",
                    "pairing_key": current_room,
                    "device_id": current_device
                }, ensure_ascii=False) + "\n"
                writer.write(reg_confirm.encode("utf-8"))
                await writer.drain()

                # Доставка накопившихся оффлайн-сообщений
                queued_msgs = fetch_and_clear_offline_messages(current_room, current_device)
                if queued_msgs:
                    logging.info(f"Доставляем {len(queued_msgs)} оффлайн-сообщений устройству {current_device}")
                    for qm in queued_msgs:
                        writer.write((qm + "\n").encode("utf-8"))
                    await writer.drain()

            # Обновляем метаданные и запись в БД
            if current_room and current_device:
                if current_room not in ROOM_CLIENTS:
                    ROOM_CLIENTS[current_room] = {}
                if current_device in ROOM_CLIENTS[current_room]:
                    if user_name:
                        ROOM_CLIENTS[current_room][current_device]["name"] = user_name
                    if app_version:
                        ROOM_CLIENTS[current_room][current_device]["version"] = app_version
                else:
                    ROOM_CLIENTS[current_room][current_device] = {
                        "writer": writer,
                        "ip": peer_ip,
                        "name": user_name or "Пользователь",
                        "version": app_version or "unknown",
                        "since": time.time()
                    }
                WRITER_TO_CLIENT[writer] = (current_room, current_device)
                update_device_record(current_device, current_room, user_name, app_version, peer_ip, inc_packets=1)

            # Обработка ping/pong
            if msg_type == "ping":
                try:
                    pong_msg = json.dumps({"type": "pong"}, ensure_ascii=False) + "\n"
                    writer.write(pong_msg.encode("utf-8"))
                    await writer.drain()
                except Exception:
                    pass
                continue

            # Обработка сообщений чата
            if msg_type == "message":
                STATS_COUNTERS["total_messages"] += 1
                payload_str = json.dumps(data, ensure_ascii=False)
                room_conns = ROOM_CLIENTS.get(current_room, {})
                sent_to_online = False

                for other_dev, dev_info in list(room_conns.items()):
                    if other_dev != current_device:
                        try:
                            dev_info["writer"].write((payload_str + "\n").encode("utf-8"))
                            await dev_info["writer"].drain()
                            sent_to_online = True
                        except Exception as write_err:
                            logging.warning(f"Ошибка отправки сообщения клиенту {other_dev}: {write_err}")
                            ROOM_CLIENTS[current_room].pop(other_dev, None)
                            try:
                                dev_info["writer"].close()
                            except Exception:
                                pass

                if not sent_to_online:
                    known_devices = get_room_devices(current_room)
                    partner_dev = next((d for d in known_devices if d != current_device), None)
                    save_offline_message(current_room, partner_dev, payload_str)
                    log_event("message", peer_ip, f"Сообщение сохранено в оффлайн-буфер для комнаты '{current_room}'")
                else:
                    log_event("message", peer_ip, f"Сообщение переслано онлайн-партнёру в комнате '{current_room}'")

            # Ретрансляция активности и сердечек
            elif current_room and current_room in ROOM_CLIENTS:
                if msg_type == "heart":
                    STATS_COUNTERS["total_hearts"] += 1
                    log_event("heart", peer_ip, f"Сердечко (ОХАЁ) от '{user_name or '?'}' в комнате '{current_room}'")
                elif msg_type == "activity":
                    STATS_COUNTERS["total_activities"] += 1

                payload = (json.dumps(data, ensure_ascii=False) + "\n").encode("utf-8")
                for other_dev, dev_info in list(ROOM_CLIENTS[current_room].items()):
                    if other_dev != current_device:
                        try:
                            dev_info["writer"].write(payload)
                            await dev_info["writer"].drain()
                        except Exception as write_err:
                            logging.warning(f"Ошибка отправки пакета {msg_type} клиенту {other_dev}: {write_err}")
                            ROOM_CLIENTS[current_room].pop(other_dev, None)
                            try:
                                dev_info["writer"].close()
                            except Exception:
                                pass

    except asyncio.CancelledError:
        pass
    except Exception as e:
        logging.warning(f"Ошибка соединения с {peer}: {e}")
    finally:
        logging.info(f"Клиент {peer} (dev={current_device}) отключился")
        if writer in WRITER_TO_CLIENT:
            c_room, c_dev = WRITER_TO_CLIENT.pop(writer)
            if c_room in ROOM_CLIENTS:
                ROOM_CLIENTS[c_room].pop(c_dev, None)
                offline_notice = (json.dumps({
                    "type": "partner_offline",
                    "pairing_key": c_room,
                    "device_id": c_dev
                }) + "\n").encode("utf-8")
                for dev_info in list(ROOM_CLIENTS[c_room].values()):
                    try:
                        dev_info["writer"].write(offline_notice)
                        await dev_info["writer"].drain()
                    except Exception:
                        pass
                if not ROOM_CLIENTS[c_room]:
                    del ROOM_CLIENTS[c_room]
                log_event("disconnect", peer_ip, f"Отключился dev={c_dev} из комнаты '{c_room}'")

        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


# -------------------------------------------------------------
# ВЕБ-ДАШБОРД (HTTP СЕРВЕР НА ЧИСТОМ ASYNCIO)
# -------------------------------------------------------------

def get_stats_data():
    online_count = sum(len(devs) for devs in ROOM_CLIENTS.values())
    active_rooms = len(ROOM_CLIENTS)

    devices_list = []
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM devices ORDER BY last_seen DESC LIMIT 100")
        for row in cur.fetchall():
            d = dict(row)
            room = d.get("room_key")
            dev_id = d.get("device_id")
            # Проверяем, онлайн ли устройство прямо сейчас
            is_online = bool(room in ROOM_CLIENTS and dev_id in ROOM_CLIENTS[room])
            d["is_online"] = is_online
            if is_online:
                info = ROOM_CLIENTS[room][dev_id]
                d["online_sec"] = int(time.time() - info.get("since", time.time()))
                d["current_ip"] = info.get("ip", d.get("ip_address"))
            else:
                d["online_sec"] = 0
                d["current_ip"] = d.get("ip_address")
            devices_list.append(d)

        cur.execute("SELECT * FROM audit_events ORDER BY id DESC LIMIT 30")
        events = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT COUNT(DISTINCT room_key) FROM room_devices")
        total_rooms_row = cur.fetchone()
        total_rooms = total_rooms_row[0] if total_rooms_row else 0

    uptime_sec = int(time.time() - SERVER_START_TIME)
    uptime_str = f"{uptime_sec // 3600}ч {(uptime_sec % 3600) // 60}м"

    return {
        "online_users": online_count,
        "active_rooms": active_rooms,
        "total_rooms": total_rooms,
        "total_devices": len(devices_list),
        "total_messages": STATS_COUNTERS["total_messages"],
        "total_activities": STATS_COUNTERS["total_activities"],
        "total_hearts": STATS_COUNTERS["total_hearts"],
        "blocked_scanners": STATS_COUNTERS["blocked_scanners"],
        "uptime": uptime_str,
        "devices": devices_list,
        "events": events
    }


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Together Relay Dashboard</title>
<style>
  :root {
    --bg: #0e0d13;
    --card-bg: #17151e;
    --border: rgba(255,255,255,0.08);
    --text: #e8e6f0;
    --text-dim: rgba(255,255,255,0.5);
    --accent: #a89ef0;
    --accent-glow: rgba(168,158,240,0.25);
    --pink: #d4537e;
    --green: #10b981;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  body { background: var(--bg); color: var(--text); padding: 24px 16px; min-height: 100vh; }
  .container { max-width: 1040px; margin: 0 auto; }
  
  header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid var(--border); }
  .logo { display: flex; align-items: center; gap: 10px; font-size: 20px; font-weight: 700; color: #fff; }
  .logo span { color: var(--pink); font-size: 22px; }
  .server-status { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.3); border-radius: 20px; font-size: 12px; color: #34d399; font-weight: 500; }
  .dot-pulse { width: 8px; height: 8px; border-radius: 50%; background: #10b981; box-shadow: 0 0 8px #10b981; animation: pulse 1.8s infinite; }
  @keyframes pulse { 0%,100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.5; transform: scale(1.2); } }

  .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; margin-bottom: 24px; }
  .metric-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 14px; padding: 16px; position: relative; overflow: hidden; }
  .metric-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #6c5ce7, var(--pink)); }
  .metric-title { font-size: 12px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
  .metric-val { font-size: 28px; font-weight: 700; color: #fff; }
  .metric-sub { font-size: 11px; color: var(--text-dim); margin-top: 4px; }

  .section { background: var(--card-bg); border: 1px solid var(--border); border-radius: 14px; padding: 18px; margin-bottom: 24px; }
  .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
  .section-title { font-size: 15px; font-weight: 600; color: #fff; }

  table { width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; }
  th { padding: 10px 12px; color: var(--text-dim); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border); }
  td { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.04); vertical-align: middle; }
  tr:last-child td { border-bottom: none; }
  tr:hover { background: rgba(255,255,255,0.02); }

  .badge-online { display: inline-flex; align-items: center; gap: 5px; padding: 3px 8px; border-radius: 12px; background: rgba(16,185,129,0.15); color: #34d399; font-size: 11.5px; font-weight: 600; }
  .badge-offline { display: inline-flex; align-items: center; gap: 5px; padding: 3px 8px; border-radius: 12px; background: rgba(255,255,255,0.06); color: var(--text-dim); font-size: 11.5px; }
  .badge-ver { padding: 2px 6px; background: rgba(108,92,231,0.25); border: 0.5px solid rgba(108,92,231,0.45); color: #c4b5fd; border-radius: 6px; font-size: 11px; font-family: monospace; }
  .key-pill { font-family: monospace; background: rgba(0,0,0,0.35); padding: 3px 6px; border-radius: 6px; color: #f472b6; font-size: 11.5px; }
  .ip-text { font-family: monospace; color: #93c5fd; font-size: 11.5px; }

  .event-feed { display: flex; flex-direction: column; gap: 8px; max-height: 280px; overflow-y: auto; }
  .event-item { display: flex; gap: 10px; font-size: 12px; padding: 6px 10px; background: rgba(0,0,0,0.25); border-radius: 8px; border-left: 3px solid #6c5ce7; }
  .event-item.connect { border-color: #10b981; }
  .event-item.message { border-color: #3b82f6; }
  .event-item.heart { border-color: var(--pink); }
  .event-item.scanner { border-color: #eab308; }
  .event-time { color: var(--text-dim); min-width: 60px; font-family: monospace; }
  .event-ip { color: #93c5fd; font-family: monospace; min-width: 95px; }
  .event-desc { color: var(--text); flex: 1; }

  .login-card { max-width: 380px; margin: 100px auto; background: var(--card-bg); border: 1px solid var(--border); border-radius: 16px; padding: 28px; text-align: center; }
  .login-input { width: 100%; padding: 10px 14px; background: rgba(0,0,0,0.3); border: 1px solid var(--border); border-radius: 8px; color: #fff; font-size: 14px; margin: 16px 0; outline: none; text-align: center; }
  .login-btn { width: 100%; padding: 10px; background: linear-gradient(135deg, #6c5ce7, var(--pink)); border: none; border-radius: 8px; color: #fff; font-size: 14px; font-weight: 600; cursor: pointer; }
</style>
</head>
<body>
<div class="container" id="app">
  <div id="login-view" style="display:none">
    <div class="login-card">
      <div class="logo" style="justify-content:center;margin-bottom:8px"><span>♥</span> Together Monitoring</div>
      <p style="font-size:12.5px;color:var(--text-dim)">Введите пароль администратора для доступа к дашборду</p>
      <input type="password" id="pass-input" class="login-input" placeholder="Пароль" onkeyup="if(event.key==='Enter')login()"/>
      <button class="login-btn" onclick="login()">Войти</button>
      <div id="login-err" style="color:var(--pink);font-size:11.5px;margin-top:10px;display:none">Неверный пароль</div>
    </div>
  </div>

  <div id="dashboard-view" style="display:none">
    <header>
      <div class="logo"><span>♥</span> Together Relay Dashboard</div>
      <div style="display:flex;align-items:center;gap:12px">
        <span class="server-status"><span class="dot-pulse"></span> Сервер в сети (<span id="stat-uptime">0ч 0м</span>)</span>
        <button onclick="logout()" style="background:transparent;border:none;color:var(--text-dim);font-size:12px;cursor:pointer">Выйти</button>
      </div>
    </header>

    <div class="metrics-grid">
      <div class="metric-card">
        <div class="metric-title">Онлайн сейчас</div>
        <div class="metric-val" id="stat-online" style="color:#34d399">0</div>
        <div class="metric-sub"><span id="stat-active-rooms">0</span> комнат активно</div>
      </div>
      <div class="metric-card">
        <div class="metric-title">Всего пользователей</div>
        <div class="metric-val" id="stat-total-devs">0</div>
        <div class="metric-sub"><span id="stat-total-rooms">0</span> комнат создано</div>
      </div>
      <div class="metric-card">
        <div class="metric-title">Сообщений / Активность</div>
        <div class="metric-val" id="stat-messages">0</div>
        <div class="metric-sub"><span id="stat-hearts">0</span> сердечек ❤️</div>
      </div>
      <div class="metric-card">
        <div class="metric-title">Отсечено сканеров</div>
        <div class="metric-val" id="stat-scanners" style="color:#fbbf24">0</div>
        <div class="metric-sub">интернет-боты и пробы</div>
      </div>
    </div>

    <div class="section">
      <div class="section-header">
        <div class="section-title">👥 Зарегистрированные пользователи и устройства</div>
      </div>
      <div style="overflow-x:auto">
        <table>
          <thead>
            <tr>
              <th>Статус</th>
              <th>Имя</th>
              <th>Версия</th>
              <th>IP-адрес</th>
              <th>Комната</th>
              <th>Сообщений</th>
              <th>Последняя активность</th>
            </tr>
          </thead>
          <tbody id="devices-tbody">
            <tr><td colspan="7" style="text-align:center;color:var(--text-dim);padding:24px">Загрузка данных...</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="section">
      <div class="section-header">
        <div class="section-title">⚡ Живой лог событий (Real-time feed)</div>
      </div>
      <div class="event-feed" id="events-feed">
        <div style="color:var(--text-dim);font-size:12px">Ожидание событий...</div>
      </div>
    </div>
  </div>
</div>

<script>
let _authKey = localStorage.getItem('together_dash_pass') || '';
const urlParams = new URLSearchParams(window.location.search);
if (urlParams.get('key')) {
  _authKey = urlParams.get('key');
  localStorage.setItem('together_dash_pass', _authKey);
}

function login() {
  const p = document.getElementById('pass-input').value;
  if (!p) return;
  fetchStats(p).then(ok => {
    if (ok) {
      _authKey = p;
      localStorage.setItem('together_dash_pass', p);
      showDashboard();
    } else {
      document.getElementById('login-err').style.display = 'block';
    }
  });
}

function logout() {
  localStorage.removeItem('together_dash_pass');
  location.reload();
}

function showDashboard() {
  document.getElementById('login-view').style.display = 'none';
  document.getElementById('dashboard-view').style.display = 'block';
  pollStats();
}

async function fetchStats(pass) {
  try {
    const res = await fetch('/api/stats?pass=' + encodeURIComponent(pass));
    if (res.status === 200) {
      const data = await res.json();
      renderStats(data);
      return true;
    }
    return false;
  } catch(e) {
    return false;
  }
}

function renderStats(d) {
  document.getElementById('stat-online').textContent = d.online_users;
  document.getElementById('stat-active-rooms').textContent = d.active_rooms;
  document.getElementById('stat-total-devs').textContent = d.total_devices;
  document.getElementById('stat-total-rooms').textContent = d.total_rooms;
  document.getElementById('stat-messages').textContent = d.total_messages;
  document.getElementById('stat-hearts').textContent = d.total_hearts;
  document.getElementById('stat-scanners').textContent = d.blocked_scanners;
  document.getElementById('stat-uptime').textContent = d.uptime;

  const tbody = document.getElementById('devices-tbody');
  if (!d.devices || !d.devices.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-dim);padding:20px">Нет зарегистрированных устройств</td></tr>';
  } else {
    tbody.innerHTML = d.devices.map(dev => {
      const statusBadge = dev.is_online
        ? `<span class="badge-online">🟢 Онлайн (${Math.floor(dev.online_sec/60)}м)</span>`
        : `<span class="badge-offline">⚪ Оффлайн</span>`;
      return `<tr>
        <td>${statusBadge}</td>
        <td><b>${escapeHtml(dev.user_name || 'Без имени')}</b></td>
        <td><span class="badge-ver">v${escapeHtml(dev.app_version || '?')}</span></td>
        <td><span class="ip-text">${escapeHtml(dev.current_ip || dev.ip_address || '-')}</span></td>
        <td><span class="key-pill">${escapeHtml(dev.room_key)}</span></td>
        <td>${dev.packets_count || 0}</td>
        <td style="color:var(--text-dim);font-size:11.5px">${escapeHtml(dev.last_seen || '-')}</td>
      </tr>`;
    }).join('');
  }

  const feed = document.getElementById('events-feed');
  if (d.events && d.events.length) {
    feed.innerHTML = d.events.map(ev => {
      const timeStr = (ev.created_at || '').split(' ')[1] || ev.created_at;
      return `<div class="event-item ${ev.event_type}">
        <span class="event-time">${timeStr}</span>
        <span class="event-ip">${escapeHtml(ev.ip || '')}</span>
        <span class="event-desc">${escapeHtml(ev.details || '')}</span>
      </div>`;
    }).join('');
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function pollStats() {
  fetchStats(_authKey);
  setInterval(() => {
    fetchStats(_authKey);
  }, 3500);
}

if (_authKey) {
  fetchStats(_authKey).then(ok => {
    if (ok) showDashboard();
    else document.getElementById('login-view').style.display = 'block';
  });
} else {
  document.getElementById('login-view').style.display = 'block';
}
</script>
</body>
</html>
"""


async def handle_http_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        req_line = await reader.readline()
        if not req_line:
            writer.close()
            return
        
        parts = req_line.decode("utf-8", errors="ignore").split()
        if len(parts) < 2:
            writer.close()
            return

        method, path = parts[0], parts[1]
        
        # Считываем оставшиеся заголовки
        headers = {}
        while True:
            line = await reader.readline()
            if not line or line in (b"\r\n", b"\n"):
                break
            h_line = line.decode("utf-8", errors="ignore")
            if ":" in h_line:
                k, v = h_line.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        parsed = urllib.parse.urlparse(path)
        qparams = urllib.parse.parse_qs(parsed.query)

        # Обработка /api/stats
        if parsed.path == "/api/stats":
            pass_provided = qparams.get("pass", [""])[0]
            if pass_provided != DASHBOARD_PASS:
                resp = b"HTTP/1.1 403 Forbidden\r\nContent-Type: application/json\r\n\r\n{\"error\": \"Invalid password\"}"
                writer.write(resp)
                await writer.drain()
            else:
                data = json.dumps(get_stats_data(), ensure_ascii=False).encode("utf-8")
                header = f"HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\nContent-Length: {len(data)}\r\nConnection: close\r\n\r\n"
                writer.write(header.encode("utf-8") + data)
                await writer.drain()

        # Обработка главной страницы дашборда
        else:
            html_bytes = DASHBOARD_HTML.encode("utf-8")
            header = f"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: {len(html_bytes)}\r\nConnection: close\r\n\r\n"
            writer.write(header.encode("utf-8") + html_bytes)
            await writer.drain()

    except Exception:
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def main():
    init_db()
    
    # 1. Запуск TCP Relay Server
    relay_server = await asyncio.start_server(handle_client, HOST, PORT)
    relay_addrs = ", ".join(str(s.getsockname()) for s in relay_server.sockets)
    logging.info(f"Together TCP Relay Server запущен на {relay_addrs}")

    # 2. Запуск HTTP Dashboard Server
    dash_server = await asyncio.start_server(handle_http_client, HOST, DASHBOARD_PORT)
    dash_addrs = ", ".join(str(s.getsockname()) for s in dash_server.sockets)
    logging.info(f"Together Web Dashboard доступен на {dash_addrs} (порт {DASHBOARD_PORT})")

    async with relay_server, dash_server:
        await asyncio.gather(
            relay_server.serve_forever(),
            dash_server.serve_forever()
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Сервер остановлен.")
