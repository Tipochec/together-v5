"""
Главное окно через pywebview — главный поток.
"""
import json, sys, os, threading
from .html import HTML
from ui.chat_html import HTML as CHAT_HTML
from .styles import CSS
from .script import JS
from datetime import datetime

try:
    import webview
except ImportError:
    print("pip install pywebview")
    sys.exit(1)

# ВАЖНО: easy_drag=True — это отдельный от -webkit-app-region встроенный
# механизм pywebview, который двигает окно по зажатию в ЛЮБОЙ точке,
# игнорируя CSS no-drag. Именно из-за него зажатие текста в чате двигало
# окно вместо выделения. Отключаем easy_drag и переходим на нативный
# drag-region pywebview: двигать окно можно только за элемент с классом
# "pywebview-drag-region" (см. .titlebar в html.py и chat_html.py), а
# DIRECT_TARGET_ONLY=True гарантирует, что дети этого элемента (кнопки
# в титлбаре) НЕ наследуют драг и кликаются как обычно.
webview.settings["DRAG_REGION_DIRECT_TARGET_ONLY"] = True

_tracker = None
_network = None
_window  = None
_stats   = None
_chat_window = None
_quitting = False  # True только когда реально выходим из приложения (трей → Закрыть)
_is_window_hidden = True
_pending_heart = None


class WindowAPI:
    def get_state(self):
        from core.tracker import load_settings
        s = load_settings()
        current = _tracker.get_current()
        history = _tracker.get_history()
        partner = _network.get_partner_data() if _network else None
        connected = _network.is_connected()     if _network else False

        def fmt(items, who):
            return [{
                "app":   h.get("app","—"),
                "title": h.get("title",""),
                "time":  h["timestamp"].strftime("%H:%M") if h.get("timestamp") else "—",
                "ts":    h["timestamp"].isoformat()       if h.get("timestamp") else "0",
                "who":   who,
            } for h in items[:10]]

        return {
            "my": {
                "app":      current.get("app","—"),
                "title":    current.get("title",""),
                "since":    current.get("since", datetime.now()).isoformat(),
                "category": current.get("category","other"),
                "afk":        current.get("afk", False),
                "status":     current.get("status", "active"),
                "manual_afk": _tracker.is_manual_afk() if _tracker else False,
                "name":       s.get("name") or "Я",
                "gender":   s.get("gender") or "male",
                "avatar":   s.get("avatar") or "",
            },
            "my_history":  fmt(history, "you"),
            "partner":     partner,
            "connected":   connected,
            "my_online_since": _tracker.get_session_start().strftime("%H:%M") if _tracker else "—",
            "partner_status": _network.get_partner_status() if _network else None,
            "time_stats":  _tracker.get_time_stats(),
        }

    def get_settings(self):
        from core.tracker import load_settings
        from core.autostart import is_autostart_enabled
        s = load_settings()
        s["autostart"] = is_autostart_enabled()
        return s

    def save_settings(self, data):
        from core.tracker import load_settings, _settings_path
        try:
            # Ключ подключения часто копируют/вставляют откуда-то (из
            # сообщения, заметки) — если туда случайно затесался пробел
            # или перенос строки, он ломает сверку pairing_key на приёме
            # у партнёра (см. core/network.py). Чистим прямо при
            # сохранении, чтобы в settings.json всегда лежал чистый ключ.
            if "pairing_key" in data and isinstance(data["pairing_key"], str):
                data["pairing_key"] = data["pairing_key"].strip()
            current = load_settings()
            current.update(data)
            with open(_settings_path(), "w", encoding="utf-8") as f:
                json.dump(current, f, ensure_ascii=False, indent=2)
            from core.network import _log
            _log(f"SETTINGS: настройки успешно обновлены: name='{current.get('name')}', gender='{current.get('gender')}', key_len={len(current.get('pairing_key', ''))}")
            if _network:
                _network.reconnect("сохранение настроек")
        except Exception as e:
            print("save_settings error:", e)
        return True

    def get_sound_volumes(self):
        from core.notifications import get_chat_volume, get_heart_volume
        return {
            "chat": get_chat_volume(),
            "heart": get_heart_volume(),
        }

    def set_sound_volume(self, kind, volume):
        from core.notifications import set_chat_volume, set_heart_volume
        from core.tracker import load_settings, _settings_path
        try:
            vol = max(0, min(100, int(volume)))
            current = load_settings()
            if kind == "heart":
                set_heart_volume(vol)
                current["volume_heart"] = vol
            else:
                set_chat_volume(vol)
                current["volume_chat"] = vol
            with open(_settings_path(), "w", encoding="utf-8") as f:
                json.dump(current, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print("set_sound_volume error:", e)
            return False

    def test_sound(self, kind, volume=None):
        from core.notifications import play_chat_sound, play_heart_sound
        try:
            vol = int(volume) if volume is not None else None
        except (ValueError, TypeError):
            vol = None
        if kind == "heart":
            play_heart_sound(vol)
        else:
            play_chat_sound(vol)
        return True

    def copy_to_clipboard(self, text):
        return True

    def pick_avatar(self):
        """
        Открывает системный диалог выбора файла, обрезает картинку в квадрат
        и сохраняет как data URI прямо в settings.json (см. core/avatar.py —
        там же объяснение почему не отдельный файл). Возвращает готовую
        строку data:image/... для мгновенного превью в интерфейсе, либо
        None, если пользователь отменил выбор или файл не открылся.
        """
        global _window
        if not _window:
            return None
        try:
            result = _window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=("Изображения (*.png;*.jpg;*.jpeg;*.webp;*.bmp)",),
            )
            if not result:
                return None
            path = result[0]

            from core.avatar import make_avatar_data_uri
            data_uri = make_avatar_data_uri(path)
            if not data_uri:
                return None

            from core.tracker import load_settings, _settings_path
            current = load_settings()
            current["avatar"] = data_uri
            with open(_settings_path(), "w", encoding="utf-8") as f:
                json.dump(current, f, ensure_ascii=False, indent=2)
            return data_uri
        except Exception as e:
            print("pick_avatar error:", e)
            return None

    def remove_avatar(self):
        from core.tracker import load_settings, _settings_path
        try:
            current = load_settings()
            current["avatar"] = ""
            with open(_settings_path(), "w", encoding="utf-8") as f:
                json.dump(current, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("remove_avatar error:", e)
        return True

    def get_time_stats(self):
        if not _tracker:
            return {"active": 0, "afk": 0, "total": 0}
        return _tracker.get_time_stats()

    def get_session_history(self):
        if not _tracker:
            return []
        return _tracker.get_session_history(limit=10)

    def get_stats(self, period):
        from core.stats import apply_customizations
        if not _stats:
            return {"apps": [], "categories": [], "total": 0}
        if period == "week":
            apps = _stats.get_week()
        elif period == "all":
            apps = _stats.get_all_time(limit=30)
        else:
            apps = _stats.get_today()

        # Переименование/цвет/категория, выставленные вручную в окне
        # статистики, и исключённые приложения — применяются здесь одним
        # местом для ВСЕХ периодов (раньше "сегодня" считало категории
        # отдельным SQL-запросом мимо этой логики, и правки не были видны
        # на вкладке "сегодня").
        apps = apply_customizations(apps)

        cats_raw = {}
        for a in apps:
            c = a["category"]
            cats_raw[c] = cats_raw.get(c, 0) + a["seconds"]
        categories = [{"category": k, "seconds": v}
                      for k, v in sorted(cats_raw.items(), key=lambda x: -x[1])]
        total = sum(a["seconds"] for a in apps)
        return {"apps": apps, "categories": categories, "total": total}

    def delete_stat(self, app_name):
        """Полностью убирает приложение из статистики — за все даты, а не
        только за сегодня (кнопка ✕ у строки в статистике)."""
        if not _stats:
            return False
        return _stats.delete_app(app_name)

    def get_stat_customization(self, app_name):
        """Текущие ручные настройки приложения (для предзаполнения окна
        редактирования) — имя, цвет, категория, исключено ли."""
        from core.stats import get_app_customizations
        return get_app_customizations().get(app_name, {})

    def save_stat_customization(self, app_name, data):
        """
        Сохраняет переименование/цвет/категорию/исключение для приложения —
        одно окно на всё, как и просили. data: {display_name, color,
        category, excluded}. Поле excluded=true немедленно останавливает
        дальнейший учёт этого приложения (core/stats.py
        StatsTracker._get_open_apps) и прячет уже накопленную историю из
        статистики (core/stats.py apply_customizations), но не удаляет её
        физически из базы — если потом снять исключение, накопленное ранее
        время снова появится.
        """
        from core.stats import save_app_customization
        save_app_customization(app_name, data)
        return True

    def get_custom_categories(self):
        """
        Категории, добавленные самим пользователем (кнопка "+ своя
        категория" в окне редактирования приложения в статистике) — в
        settings.json, ключ "custom_categories": {ключ: {name, color}}.
        Встроенные категории (игры/браузер/музыка и т.д.) остаются
        зашитыми в JS (CAT_NAMES/CAT_COLORS) — это только пользовательские
        добавления поверх них.
        """
        from core.tracker import load_settings
        return load_settings().get("custom_categories", {})

    def add_custom_category(self, name, color):
        """
        Создаёт новую категорию с уникальным ключом на основе введённого
        названия. Ключ — чисто технический идентификатор: используем
        "custom_N", само название хранится отдельно и показывается
        пользователю как есть."""
        from core.tracker import load_settings, _settings_path
        name = (name or "").strip()
        if not name:
            return None
        settings = load_settings()
        custom = settings.get("custom_categories", {}) or {}
        n = 1
        while f"custom_{n}" in custom:
            n += 1
        key = f"custom_{n}"
        custom[key] = {"name": name, "color": color or "#a89ef0"}
        settings["custom_categories"] = custom
        try:
            with open(_settings_path(), "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception:
            return None
        return {"key": key, "name": name, "color": custom[key]["color"]}
      
    def open_chat(self):
      open_chat_window()

    def debug_scan(self):
        if not _stats:
            return []
        return _stats.debug_scan()

    def get_network_log(self, lines=20):
        from core.network import get_network_log as _get_log
        return _get_log(lines)

    def reconnect_network(self):
        if _network:
            _network.reconnect("кнопка в настройках")
            return True
        return False

    def get_app_version(self):
        from core.version import APP_VERSION
        return APP_VERSION

    def check_for_updates(self):
        from core.updater import check_updates
        return check_updates()

    def apply_update(self, download_url):
        from core.updater import apply_update as _apply
        def _prog(pct):
            if _window:
                try:
                    _window.evaluate_js(f"onUpdateProgress({pct});")
                except Exception:
                    pass
        return _apply(download_url, progress_callback=_prog)

    def hide_window(self):
        global _is_window_hidden
        _is_window_hidden = True
        if _window:
            try:
                _window.evaluate_js("onWindowHidden();")
            except Exception:
                pass
            _window.hide()

    def minimize_window(self):
        global _is_window_hidden
        _is_window_hidden = True
        if _window:
            try:
                _window.evaluate_js("onWindowHidden();")
            except Exception:
                pass
            _window.minimize()

    def send_heart(self):
        if _network:
            return _network.send_heart()
        return False

    def toggle_afk(self):
        if _tracker:
            return _tracker.toggle_manual_afk()
        return False

    def quit_app(self):
        _do_quit()
        
    def close_chat(self):
        global _chat_window

        if _chat_window:
            _chat_window.destroy()
            _chat_window = None

    def get_chat_history(self):
        if not _network:
            return []
        history = _network.get_chat_history()
        return history

    def clear_chat(self):
        if _network:
            _network.clear_chat_history()
        return True

    def refresh_chat(self):
        if _chat_window:
            try:
                _chat_window.evaluate_js("loadChat();")
            except Exception:
                pass
            
    def send_message(self, text, reply_to_uid=None, reply_sender=None, reply_text=None):
        _network.send_message(text, reply_to_uid=reply_to_uid,
                               reply_sender=reply_sender, reply_text=reply_text)
        return True

    def toggle_autostart(self):
        from core.autostart import setup_autostart, is_autostart_enabled
        enabled = is_autostart_enabled()
        setup_autostart(enable=not enabled)
        return not enabled



def _do_quit():
    global _quitting
    _quitting = True
    _tracker.stop()
    if _network:
        _network.stop()
    if _stats:
        _stats.stop()
    if _chat_window:
       _chat_window.destroy()
    if _window:
        _window.destroy()


def open_window():
    global _is_window_hidden, _pending_heart
    _is_window_hidden = False
    if _window:
        try:
            _window.show()
            _window.restore()
        except Exception:
            pass
        try:
            import ctypes
            hwnd = ctypes.windll.user32.FindWindowW(None, "Together")
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 9)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
        try:
            _window.evaluate_js("onWindowRestored();")
        except Exception:
            pass
        if _pending_heart:
            sender = _pending_heart
            _pending_heart = None
            try:
                import json
                js_sender = json.dumps(sender, ensure_ascii=False)
                threading.Timer(0.25, lambda: _window.evaluate_js(f"triggerHeartCelebration({js_sender});")).start()
            except Exception:
                pass
        
def open_chat_window():
    global _chat_window

    # Окно чата уже открыто — просто показываем и выходим,
    # НЕ создаём второе (раньше тут плодились дубли-окна, и закрыть
    # можно было только последнее созданное — старые становились "сиротами")
    if _chat_window:
        try:
            _chat_window.show()
            return
        except Exception:
            _chat_window = None  # окно было уничтожено снаружи — создадим заново

    from core.paths import is_test_instance
    chat_title = "Together (Тест) • Чат" if is_test_instance() else "Together • Чат"
    _chat_window = webview.create_window(
        title=chat_title,
        html=CHAT_HTML,
        js_api=WindowAPI(),
        width=380,
        height=580,
        resizable=False,
        frameless=True,
        easy_drag=False,
        background_color="#0f0f13",
    )

    def on_closed():
        global _chat_window
        _chat_window = None

    _chat_window.events.closed += on_closed


def run_webview_loop(tracker, network, stats=None):
    global _tracker, _network, _window, _stats, _chat_window, _is_window_hidden
    import builtins
    import sys

    _tracker = tracker
    _network = network
    _stats   = stats
    builtins._together_open_window = open_window
    builtins._together_quit        = _do_quit

    start_hidden = ("--autostart" in sys.argv) and ("--show" not in sys.argv)
    _is_window_hidden = start_hidden

    from core.paths import is_test_instance
    win_title = "Together (Тест)" if is_test_instance() else "Together"

    from core.tracker import load_settings
    from core.notifications import set_chat_volume, set_heart_volume
    try:
        s = load_settings()
        if "volume_chat" in s:
            set_chat_volume(s["volume_chat"])
        if "volume_heart" in s:
            set_heart_volume(s["volume_heart"])
    except Exception:
        pass

    api = WindowAPI()
    _window = webview.create_window(
        title=win_title,
        html=HTML,
        js_api=api,
        width=520,
        height=600,
        resizable=False,
        frameless=True,
        easy_drag=False,
        background_color="#0f0f13",
        hidden=start_hidden,
    )

    def _on_incoming_message(data):
        # Если открыто окно чата — перерисовываем список сообщений
        if _chat_window:
            try:
                _chat_window.evaluate_js("loadChat();")
            except Exception:
                pass
        else:
            # Окно чата не открыто — зажигаем красную точку на кнопке 💬
            if _window:
                try:
                    _window.evaluate_js("setChatBadge(true)")
                except Exception:
                    pass

        # Звуковое уведомление — без визуального попапа, не засоряет интерфейс
        from core.notifications import play_chat_sound
        play_chat_sound()

        # Мигание иконки в таскбаре, если окно сейчас не в фокусе —
        # аналог того, как это делают Discord/Telegram
        _flash_taskbar_if_unfocused()

    network.on_message(_on_incoming_message)

    def _on_incoming_heart(data):
        global _pending_heart, _is_window_hidden
        sender = data.get("sender") or "Партнёр"
        import json
        js_sender = json.dumps(sender, ensure_ascii=False)
        if _window:
            if _is_window_hidden:
                _pending_heart = sender
                try:
                    _window.evaluate_js(f"queuePendingHeart({js_sender});")
                except Exception:
                    pass
            else:
                try:
                    _window.evaluate_js(f"onHeartReceived({js_sender});")
                except Exception:
                    _pending_heart = sender
        if _chat_window:
            try:
                _chat_window.evaluate_js(f"onHeartReceived({js_sender});")
            except Exception:
                pass
        from core.notifications import play_heart_sound
        play_heart_sound()
        _flash_taskbar_if_unfocused()

    network.on_heart(_on_incoming_heart)

    def _flash_taskbar_if_unfocused():
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.FindWindowW(None, "Together")
            if not hwnd:
                return
            if user32.GetForegroundWindow() == hwnd:
                return  # окно и так в фокусе — мигать незачем

            class FLASHWINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_uint),
                    ("hwnd", ctypes.c_void_p),
                    ("dwFlags", ctypes.c_uint),
                    ("uCount", ctypes.c_uint),
                    ("dwTimeout", ctypes.c_uint),
                ]

            FLASHW_TRAY = 0x00000002
            FLASHW_TIMERNOFG = 0x0000000C  # мигать пока пользователь не откроет окно

            info = FLASHWINFO(
                ctypes.sizeof(FLASHWINFO), hwnd,
                FLASHW_TRAY | FLASHW_TIMERNOFG, 0, 0,
            )
            user32.FlashWindowEx(ctypes.byref(info))
        except Exception:
            pass

    def _on_main_closing():
        # Если это настоящий выход (трей → "Закрыть") — не мешаем,
        # даём окну закрыться по-настоящему, иначе процесс зависнет
        # навсегда (webview.start() никогда не вернёт управление)
        if _quitting:
            return True

        # А это — случайное системное закрытие (превью в таскбаре,
        # Alt+F4 и т.д.) — вот тут прячем в трей вместо закрытия
        threading.Timer(0.05, lambda: _window and _window.hide()).start()
        return False

    _window.events.closing += _on_main_closing

    webview.start(debug=False)
    os._exit(0)
