"""
Автоматическое определение категории приложения через Gemini API.
Используется только для неизвестных приложений — результат кешируется
в JSON-файл, чтобы повторно не делать запросы.
"""
import json
import os
import threading
import urllib.request
import urllib.error

GEMINI_API_KEY = ""  # ← Вставь свой ключ сюда (или через settings.json)
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash-lite:generateContent?key="
)

CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "ai_categories_cache.json")

VALID_CATEGORIES = [
    "gaming", "browser", "chat", "music", "video",
    "work", "streaming", "torrent", "photo", "vpn",
    "archive", "other"
]

_cache = None
_cache_lock = threading.Lock()


def _load_cache():
    global _cache
    if _cache is not None:
        return _cache
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            _cache = json.load(f)
    except Exception:
        _cache = {}
    return _cache


def _save_cache():
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(_cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_api_key():
    """Берём ключ из settings.json если он там есть, иначе из константы выше"""
    try:
        from core.tracker import load_settings
        s = load_settings()
        return s.get("gemini_api_key", "") or GEMINI_API_KEY
    except Exception:
        return GEMINI_API_KEY


def classify_app(process_name, window_title=""):
    """
    Определяет категорию приложения по имени процесса.
    Возвращает категорию из VALID_CATEGORIES, или "other" при ошибке.
    Результат кешируется по process_name — повторный вызов мгновенный.
    """
    key = process_name.lower().strip()

    with _cache_lock:
        cache = _load_cache()
        if key in cache:
            return cache[key]

    api_key = get_api_key()
    if not api_key:
        # Без ключа — не можем спросить нейронку, считаем "other"
        with _cache_lock:
            cache[key] = "other"
            _save_cache()
        return "other"

    category = _ask_gemini(process_name, window_title, api_key)

    with _cache_lock:
        cache[key] = category
        _save_cache()

    return category


def _ask_gemini(process_name, window_title, api_key):
    prompt = (
        f"Процесс Windows: \"{process_name}\". "
        f"Заголовок окна: \"{window_title}\". "
        f"К какой категории относится эта программа? "
        f"Варианты строго одним словом из списка: "
        f"{', '.join(VALID_CATEGORIES)}. "
        f"Ответь только одним словом без пояснений."
    )

    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 10},
    }).encode("utf-8")

    req = urllib.request.Request(
        GEMINI_URL + api_key,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = (
                data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                    .strip()
                    .lower()
            )
            # Берём только первое слово, на случай если модель добавила текст
            text = text.split()[0].strip(".,!?") if text else ""
            if text in VALID_CATEGORIES:
                return text
            return "other"
    except urllib.error.HTTPError as e:
        print(f"Gemini API error: {e.code}")
        return "other"
    except Exception as e:
        print(f"Gemini classify error: {e}")
        return "other"


def classify_app_async(process_name, window_title, callback):
    """
    Асинхронная версия — не блокирует трекер пока ждём ответ от API.
    callback(category) вызывается когда результат готов.
    """
    def worker():
        category = classify_app(process_name, window_title)
        try:
            callback(category)
        except Exception:
            pass

    threading.Thread(target=worker, daemon=True).start()
