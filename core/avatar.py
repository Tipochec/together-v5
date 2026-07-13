"""
Обработка аватарки: приводим загруженную картинку к квадрату небольшого
размера и кодируем в base64 data URI.

Почему data URI прямо в settings.json, а не отдельный файл на диске:
аватарку нужно ещё и показать у партнёра, а у нас нет отдельного протокола
передачи файлов — только сокет с JSON-пакетами (см. network.py). Поэтому
аватарка едет тем же пакетом активности, что и статус "чем занят" —
и должна быть маленькой (см. AVATAR_SIZE/JPEG_QUALITY), иначе раздует
трафик, гоняемый каждые 2 секунды.
"""
import base64
import io

try:
    from PIL import Image
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

AVATAR_SIZE  = 128   # итоговая сторона квадрата в пикселях
JPEG_QUALITY = 78    # компромисс размер/качество


def make_avatar_data_uri(path):
    """
    Открывает изображение по пути path, обрезает его по центру до квадрата,
    ресайзит и возвращает готовую строку data:image/jpeg;base64,...
    Возвращает None, если Pillow не установлен или файл не открылся.
    """
    if not _PIL_OK:
        return None
    try:
        img = Image.open(path)
        img = img.convert("RGB")

        w, h = img.size
        side = min(w, h)
        left = (w - side) // 2
        top  = (h - side) // 2
        img  = img.crop((left, top, left + side, top + side))
        img  = img.resize((AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=JPEG_QUALITY)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"
    except Exception:
        return None
