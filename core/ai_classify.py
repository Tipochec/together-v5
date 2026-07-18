"""
Автоматическое определение категории приложения через OpenRouter API.
Используется только для неизвестных приложений — результат кешируется
в JSON-файл, чтобы повторно не делать запросы.

Раньше тут был Gemini, но он заблокирован в РФ на уровне IP без VPN —
убрали его совсем, оставили только OpenRouter (не заблокирован).
"""
import json
import os
import threading
import time
import urllib.request
import urllib.error
from core.paths import data_path

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# "openrouter/free" — авто-роутер, сам выбирает доступную бесплатную модель.
# Так надёжнее, чем хардкодить конкретный slug — бесплатные модели у
# OpenRouter периодически переименовываются/убираются без предупреждения.
DEFAULT_MODEL  = "openrouter/free"

CACHE_PATH = data_path("ai_categories_cache.json")
LOG_PATH   = data_path("ai_debug.log")

VALID_CATEGORIES = [
    "gaming", "browser", "chat", "music", "video",
    "work", "streaming", "torrent", "photo", "vpn",
    "archive", "other"
]

_cache = None
_cache_lock = threading.Lock()
_log_lock = threading.Lock()


def _log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    try:
        with _log_lock:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception:
        pass


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


def _settings():
    try:
        from core.tracker import load_settings
        return load_settings()
    except Exception:
        return {}


def classify_app(process_name, window_title=""):
    """
    Определяет категорию приложения по имени процесса через OpenRouter.
    Возвращает категорию из VALID_CATEGORIES, или "other" при ошибке.
    Результат кешируется по process_name — повторный вызов мгновенный.
    """
    key = process_name.lower().strip()

    with _cache_lock:
        cache = _load_cache()
        if key in cache:
            return cache[key]

    s = _settings()
    api_key = s.get("openrouter_api_key", "")
    model = s.get("openrouter_model") or DEFAULT_MODEL

    if not api_key:
        _log(f"NO_KEY process={process_name!r} — openrouter_api_key не задан в settings.json, категория=other")
        category = "other"
    else:
        category = _ask_openrouter(process_name, window_title, api_key, model)
        if category is None:
            category = "other"

    with _cache_lock:
        cache[key] = category
        _save_cache()

    return category


def _ask_openrouter(process_name, window_title, api_key, model):
    prompt = (
        f"Процесс Windows: \"{process_name}\". Заголовок окна: \"{window_title}\". "
        f"К какой категории относится эта программа? Варианты строго одним словом из списка: "
        f"{', '.join(VALID_CATEGORIES)}. Ответь только одним словом без пояснений."
    )
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 10,
        "temperature": 0,
    }).encode("utf-8")

    req = urllib.request.Request(
        OPENROUTER_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["choices"][0]["message"]["content"].strip().lower()
            text = text.split()[0].strip(".,!?") if text else ""
            if text in VALID_CATEGORIES:
                return text
            _log(f"OPENROUTER_UNEXPECTED process={process_name!r} raw_answer={text!r} → other")
            return "other"
    except urllib.error.HTTPError as e:
        body_text = ""
        try:
            body_text = e.read().decode("utf-8")[:200]
        except Exception:
            pass
        if e.code == 403:
            _log(f"OPENROUTER_HTTP_ERROR process={process_name!r} code=403 body={body_text!r} "
                 f"(похоже на региональную блокировку OpenRouter — см. новости про ограничения "
                 f"для российских аккаунтов с мая 2026, тут VPN тоже может понадобиться)")
        elif e.code == 404:
            _log(f"OPENROUTER_HTTP_ERROR process={process_name!r} code=404 body={body_text!r} "
                 f"(модель '{model}' не найдена — возможно её переименовали/убрали, "
                 f"попробуйте openrouter/free)")
        else:
            _log(f"OPENROUTER_HTTP_ERROR process={process_name!r} code={e.code} body={body_text!r}")
        return "other"
    except urllib.error.URLError as e:
        _log(f"OPENROUTER_OFFLINE process={process_name!r} error={e}")
        return None
    except Exception as e:
        _log(f"OPENROUTER_ERROR process={process_name!r} error={e}")
        return None


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
