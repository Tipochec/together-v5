"""
Умный классификатор приложений на основе метаданных Windows,
путей установки (Steam, Epic, лаунчеры) и расширенной базы.
Работает полностью автономно, быстро и без внешних API.
"""
import os
import ctypes
import ctypes.wintypes

# Кэш: exe_path -> (display_name, category)
_CLASSIFY_CACHE = {}

# Папки, в которых 100% находятся игры
GAME_PATH_KEYWORDS = (
    "\\steamapps\\common\\",
    "\\epic games\\",
    "\\riot games\\",
    "\\gog galaxy\\games\\",
    "\\ea games\\",
    "\\ubisoft\\ubisoft game launcher\\games\\",
    "\\battlenet\\",
    "\\battle.net\\",
    "\\xboxgames\\",
    "\\vk play\\",
    "\\games\\",
    "\\игры\\",
)

# Разработчики / компании, производящие софт определённой категории
COMPANY_RULES = {
    # Игры
    "gaming": (
        "valve", "electronic arts", "ubisoft", "bethesda", "rockstar",
        "blizzard", "cd projekt", "epic games", "riot games", "sega",
        "capcom", "square enix", "bandai namco", "mihoyo", "cognosphere",
        "wargaming", "gaijin", "battlestate", "re-logic", "mojang",
        "larian studios", "paradox interactive", "fromsoftware", "2k games",
    ),
    # Работа и разработка
    "work": (
        "jetbrains", "microsoft visual studio", "adobe", "autodesk",
        "figma", "blender foundation", "sublime hq", "github",
        "docker", "postman", "unity technologies", "oracle",
    ),
    # Общение
    "chat": (
        "telegram", "discord", "slack", "zoom video", "skype",
        "viber media", "whatsapp",
    ),
    # Музыка и медиа
    "music": (
        "spotify", "yandex music", "яндекс музыка", "deezer",
    ),
    "video": (
        "videolan", "obs project",
    ),
}

# Ключевые слова в описании программы (FileDescription / ProductName)
DESCRIPTION_KEYWORDS = {
    "gaming": ("game", "игры", "launcher", "steam", "unreal engine", "unity player"),
    "chat": ("messenger", "chat", "мессенджер", "чат", "call", "communication"),
    "music": ("music", "player", "плеер", "audio", "музыка", "sound"),
    "video": ("video", "видео", "stream", "obs", "cinema", "player"),
    "work": ("ide", "editor", "compiler", "office", "документ", "spreadsheet", "cad"),
    "torrent": ("torrent", "торрент", "bittorrent"),
    "archive": ("archiver", "archive", "7-zip", "winrar", "zip"),
    "vpn": ("vpn", "proxy", "tunnel", "v2ray", "xray"),
}


def _get_file_version_info(filepath: str):
    """Извлекает FileDescription, CompanyName, ProductName из .exe через WinAPI."""
    info = {"description": "", "company": "", "product": ""}
    if not filepath or not os.path.isfile(filepath):
        return info
    try:
        size = ctypes.windll.version.GetFileVersionInfoSizeW(filepath, None)
        if not size:
            return info
        buf = ctypes.create_string_buffer(size)
        if not ctypes.windll.version.GetFileVersionInfoW(filepath, 0, size, buf):
            return info

        for lang in ("040904b0", "041904b0", "000004b0", "040904e4", "041904e4", "04090000", "04190000"):
            def query(key):
                sub = f"\\StringFileInfo\\{lang}\\{key}"
                lp_buffer = ctypes.c_void_p()
                u_len = ctypes.c_uint()
                if ctypes.windll.version.VerQueryValueW(buf, sub, ctypes.byref(lp_buffer), ctypes.byref(u_len)) and u_len.value > 1:
                    return ctypes.wstring_at(lp_buffer.value, u_len.value - 1).strip()
                return ""
            desc = query("FileDescription")
            comp = query("CompanyName")
            prod = query("ProductName")
            if desc or comp or prod:
                return {"description": desc, "company": comp, "product": prod}
    except Exception:
        pass
    return info


def classify_executable(exe_path: str, default_app_name: str, known_category: str = None) -> tuple[str, str]:
    """
    Определяет отображаемое имя и категорию процесса по его пути и метаданным.
    Возвращает: (display_name, category)
    """
    if not exe_path:
        return default_app_name, known_category or "other"

    norm_path = os.path.normpath(exe_path).lower()
    if norm_path in _CLASSIFY_CACHE:
        return _CLASSIFY_CACHE[norm_path]

    # Если уже есть точная известная категория (из app_maps)
    if known_category and known_category != "other":
        _CLASSIFY_CACHE[norm_path] = (default_app_name, known_category)
        return default_app_name, known_category

    # 1. Проверка путей известных игровых магазинов
    for game_keyword in GAME_PATH_KEYWORDS:
        if game_keyword in norm_path:
            _CLASSIFY_CACHE[norm_path] = (default_app_name, "gaming")
            return default_app_name, "gaming"

    # 2. Чтение метаданных .exe файла
    meta = _get_file_version_info(exe_path)
    desc = meta["description"].lower()
    company = meta["company"].lower()
    product = meta["product"].lower()

    detected_category = None

    # Проверка разработчика/компании
    for cat, companies in COMPANY_RULES.items():
        if any(c in company for c in companies):
            detected_category = cat
            break

    # Проверка ключевых слов в описании / названии продукта
    if not detected_category:
        combined = f"{desc} {product}"
        for cat, keywords in DESCRIPTION_KEYWORDS.items():
            if any(k in combined for k in keywords):
                detected_category = cat
                break

    category = detected_category or known_category or "other"
    _CLASSIFY_CACHE[norm_path] = (default_app_name, category)
    return default_app_name, category


# =====================================================================
# Решение 4 (Шаблон): Загрузка и синхронизация категорий с сервера
# =====================================================================
import json
import threading
from core.paths import data_path

REMOTE_CACHE_PATH = data_path("server_categories.json")
_remote_categories_cache = {}


def load_cached_server_categories():
    """Загружает локально сохранённые категории, ранее полученные с сервера."""
    global _remote_categories_cache
    if os.path.isfile(REMOTE_CACHE_PATH):
        try:
            with open(REMOTE_CACHE_PATH, "r", encoding="utf-8") as f:
                _remote_categories_cache = json.load(f)
        except Exception:
            _remote_categories_cache = {}
    return _remote_categories_cache


def sync_categories_with_server(server_url: str):
    """
    Фоновый запрос к серверу за свежим глобальным списком категорий.
    Когда поднимешь сервер, достаточно передать сюда адрес эндпоинта,
    например: http://your-server.com/api/categories
    """
    def _worker():
        global _remote_categories_cache
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{server_url.rstrip('/')}/api/categories",
                headers={"User-Agent": "Together-App"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if isinstance(data, dict):
                        _remote_categories_cache.update(data)
                        with open(REMOTE_CACHE_PATH, "w", encoding="utf-8") as f:
                            json.dump(_remote_categories_cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # Сервер пока недоступен или не поднят — тихо пропускаем

    threading.Thread(target=_worker, daemon=True).start()
