"""
Together Relay & Offline Buffer Server (Ретранслятор и оффлайн-буфер для Together).

Функции:
1. Защита комнат (Pairing Key + Device Binding):
   - В комнату допускаются максимум 2 уникальных устройства (device_id).
   - При попытке 3-го левого устройства подключиться к комнате — отказ в доступе.
2. Оффлайн-очередь сообщений (Inbox buffer):
   - Если партнёр оффлайн, сервер сохраняет сообщения в локальную базу SQLite (relay.db).
   - Как только партнёр заходит в сеть — сообщения мгновенно доставляются ему и удаляются из базы.
3. Ретрансляция в реальном времени (Real-time relay):
   - Пересылка активности, сердечек и мгновенных сообщений без задержек.
"""
import asyncio
import json
import logging
import sqlite3
import os

PORT = 39722
HOST = "0.0.0.0"
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "relay.db")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Хранилище активных соединений в памяти:
# ROOM_CLIENTS[room_key] = { device_id: writer }
ROOM_CLIENTS = {}
# WRITER_TO_CLIENT[writer] = (room_key, device_id)
WRITER_TO_CLIENT = {}


def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        # Таблица привязки комнат к устройствам (максимум 2 устройства на room_key)
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
        conn.commit()


def authorize_device(room_key: str, device_id: str) -> bool:
    """
    Проверяет, разрешено ли устройству войти в комнату.
    Если в комнате зарегистрировано меньше 2 устройств — регистрирует новое.
    Если уже зарегистрировано 2 других устройства — запрещает вход.
    """
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

        # Комната уже заполнена двумя другими устройствами
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
    """Достаёт все оффлайн-сообщения для этого устройства или комнаты и удаляет их"""
    messages = []
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        # Либо сообщение конкретно для этого device_id, либо для комнаты (если target_device_id не был известен)
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
    logging.info(f"Новое TCP-соединение от {peer}")

    current_room = None
    current_device = None

    try:
        while True:
            line = await reader.readline()
            if not line:
                break

            try:
                data = json.loads(line.decode("utf-8").strip())
            except Exception:
                continue

            msg_type = data.get("type")
            room_key = (data.get("pairing_key") or "").strip()
            device_id = (data.get("device_id") or "").strip()

            if not room_key:
                continue

            # Обработка входа / авторизации устройства
            if current_room != room_key or current_device != device_id:
                if not authorize_device(room_key, device_id):
                    logging.warning(f"Отказ в доступе: устройство {device_id} не входит в доверенные для комнаты '{room_key}'")
                    err_msg = json.dumps({
                        "type": "error",
                        "code": "ROOM_FULL",
                        "message": "Комната уже занята двумя другими устройствами. Проверьте ключ подключения."
                    }, ensure_ascii=False) + "\n"
                    writer.write(err_msg.encode("utf-8"))
                    await writer.drain()
                    break

                # Отвязываем от старой комнаты, если сменилась
                if current_room and current_room in ROOM_CLIENTS:
                    ROOM_CLIENTS[current_room].pop(current_device, None)

                current_room = room_key
                current_device = device_id
                if current_room not in ROOM_CLIENTS:
                    ROOM_CLIENTS[current_room] = {}
                ROOM_CLIENTS[current_room][current_device] = writer
                WRITER_TO_CLIENT[writer] = (current_room, current_device)

                reg_confirm = json.dumps({
                    "type": "registered",
                    "pairing_key": current_room,
                    "device_id": current_device
                }, ensure_ascii=False) + "\n"
                writer.write(reg_confirm.encode("utf-8"))
                await writer.drain()

                # Проверяем и отправляем накопившиеся оффлайн-сообщения
                queued_msgs = fetch_and_clear_offline_messages(current_room, current_device)
                if queued_msgs:
                    logging.info(f"Доставляем {len(queued_msgs)} оффлайн-сообщений устройству {current_device}")
                    for qm in queued_msgs:
                        writer.write((qm + "\n").encode("utf-8"))
                    await writer.drain()

            # ВСЕГДА гарантируем, что активное соединение зарегистрировано в комнате
            if current_room:
                if current_room not in ROOM_CLIENTS:
                    ROOM_CLIENTS[current_room] = {}
                if ROOM_CLIENTS[current_room].get(current_device) is not writer:
                    ROOM_CLIENTS[current_room][current_device] = writer
                    WRITER_TO_CLIENT[writer] = (current_room, current_device)

            # Обработка ping/pong для проверки живости связи
            if msg_type == "ping":
                try:
                    pong_msg = json.dumps({"type": "pong"}, ensure_ascii=False) + "\n"
                    writer.write(pong_msg.encode("utf-8"))
                    await writer.drain()
                except Exception:
                    pass
                continue

            # Обработка пакета чата (message)
            if msg_type == "message":
                payload_str = json.dumps(data, ensure_ascii=False)
                # Ищем партнёра в комнате
                room_conns = ROOM_CLIENTS.get(current_room, {})
                sent_to_online = False

                for other_dev, other_writer in list(room_conns.items()):
                    if other_dev != current_device:
                        try:
                            other_writer.write((payload_str + "\n").encode("utf-8"))
                            await other_writer.drain()
                            sent_to_online = True
                        except Exception as write_err:
                            logging.warning(f"Ошибка отправки сообщения клиенту {other_dev}: {write_err}")
                            ROOM_CLIENTS[current_room].pop(other_dev, None)
                            try:
                                other_writer.close()
                            except Exception:
                                pass

                # Если партнёр сейчас не в сети — сохраняем в оффлайн-буфер на сервере!
                if not sent_to_online:
                    # Выясняем device_id партнёра (если он уже привязан к комнате)
                    known_devices = get_room_devices(current_room)
                    partner_dev = next((d for d in known_devices if d != current_device), None)
                    save_offline_message(current_room, partner_dev, payload_str)
                    logging.info(f"Партнёр оффлайн. Сообщение сохранено в оффлайн-буфер комнаты '{current_room}'")

            # Ретрансляция других пакетов (activity, heart) только в реальном времени
            elif current_room and current_room in ROOM_CLIENTS:
                payload = (json.dumps(data, ensure_ascii=False) + "\n").encode("utf-8")
                for other_dev, other_writer in list(ROOM_CLIENTS[current_room].items()):
                    if other_dev != current_device:
                        try:
                            other_writer.write(payload)
                            await other_writer.drain()
                        except Exception as write_err:
                            logging.warning(f"Ошибка отправки пакета {msg_type} клиенту {other_dev}: {write_err}")
                            ROOM_CLIENTS[current_room].pop(other_dev, None)
                            try:
                                other_writer.close()
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
                # Уведомляем партнёра об оффлайне
                offline_notice = (json.dumps({
                    "type": "partner_offline",
                    "pairing_key": c_room,
                    "device_id": c_dev
                }) + "\n").encode("utf-8")
                for other_writer in list(ROOM_CLIENTS[c_room].values()):
                    try:
                        other_writer.write(offline_notice)
                        await other_writer.drain()
                    except Exception:
                        pass
                if not ROOM_CLIENTS[c_room]:
                    del ROOM_CLIENTS[c_room]

        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def main():
    init_db()
    server = await asyncio.start_server(handle_client, HOST, PORT)
    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    logging.info(f"Together Relay & Buffer Server запущен на {addrs}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Сервер остановлен.")
