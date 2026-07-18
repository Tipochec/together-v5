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
                "afk":      current.get("afk", False),
                "status":    current.get("status", "active"),
                "name":     s.get("name") or "Я",
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
        import socket as sk
        from core.tracker import load_settings
        from core.autostart import is_autostart_enabled
        s = load_settings()
        manual_ip = (s.get("my_ip_override") or "").strip()
        if manual_ip:
            zt_ip = manual_ip
        else:
            try:
                addrs = sk.getaddrinfo(sk.gethostname(), None)
                zt_ip = next((a[4][0] for a in addrs if a[4][0].startswith("10.")), "—")
            except Exception:
                zt_ip = "—"
        s["my_ip"]    = zt_ip
        s["autostart"] = is_autostart_enabled()
        return s

    def save_settings(self, data):
        from core.tracker import load_settings, _settings_path
        try:
            current = load_settings()
            current.update(data)
            with open(_settings_path(), "w", encoding="utf-8") as f:
                json.dump(current, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("save_settings error:", e)
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
        from core.stats import fmt_time
        if not _stats:
            return {"apps": [], "categories": [], "total": 0}
        if period == "week":
            apps = _stats.get_week()
            cats_raw = {}
            for a in apps:
                c = a["category"]
                cats_raw[c] = cats_raw.get(c, 0) + a["seconds"]
            categories = [{"category": k, "seconds": v}
                          for k, v in sorted(cats_raw.items(), key=lambda x: -x[1])]
        elif period == "all":
            apps = _stats.get_all_time(limit=30)
            cats_raw = {}
            for a in apps:
                c = a["category"]
                cats_raw[c] = cats_raw.get(c, 0) + a["seconds"]
            categories = [{"category": k, "seconds": v}
                          for k, v in sorted(cats_raw.items(), key=lambda x: -x[1])]
        else:
            apps       = _stats.get_today()
            categories = _stats.get_category_totals()
        total = sum(a["seconds"] for a in apps)
        return {"apps": apps, "categories": categories, "total": total}
      
    def open_chat(self):
      open_chat_window()

    def debug_scan(self):
        if not _stats:
            return []
        return _stats.debug_scan()

    def get_network_log(self, lines=20):
        from core.network import get_network_log as _get_log
        return _get_log(lines)

    def hide_window(self):
        if _window:
            _window.hide()

    def minimize_window(self):
        if _window:
            _window.minimize()

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
            
    def send_message(self, text):
        _network.send_message(text)
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
    if _window:
        _window.show()
        
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

    _chat_window = webview.create_window(
        title="Together • Чат",
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
    global _tracker, _network, _window, _stats, _chat_window
    import builtins

    _tracker = tracker
    _network = network
    _stats   = stats
    builtins._together_open_window = open_window
    builtins._together_quit        = _do_quit

    api = WindowAPI()
    _window = webview.create_window(
        title="Together",
        html=HTML,
        js_api=api,
        width=520,
        height=600,
        resizable=False,
        frameless=True,
        easy_drag=False,
        background_color="#0f0f13",
        hidden=True,
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
