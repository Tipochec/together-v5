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

_tracker = None
_network = None
_window  = None
_stats   = None
_chat_window = None
_window_visible = False  # окно создаётся hidden=True, см. run_webview_loop


class WindowAPI:
    def get_state(self):
        from core.tracker import load_settings
        s         = load_settings()
        current   = _tracker.get_current()
        history   = _tracker.get_history()
        partner   = _network.get_partner_data() if _network else None
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
            },
            "my_history":  fmt(history, "you"),
            "partner":     partner,
            "connected":   connected,
            "time_stats":  _tracker.get_time_stats(),
        }

    def get_settings(self):
        import socket as sk
        from core.tracker import load_settings
        from core.autostart import is_autostart_enabled
        s = load_settings()
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

    def get_ai_log(self, lines=40):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ai_debug.log")
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.readlines()
            return "".join(content[-lines:])
        except FileNotFoundError:
            return ""
        except Exception as e:
            return f"ошибка чтения лога: {e}"

    def hide_window(self):
        global _window_visible
        _window_visible = False
        if _window:
            _window.hide()

    def minimize_window(self):
        global _window_visible
        _window_visible = False
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
        return _network.get_chat_history() if _network else []



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
    global _window_visible
    _window_visible = True
    if _window:
        _window.show()
        
def open_chat_window():
    global _chat_window

    _chat_window = webview.create_window(
        title="Together • Чат",
        html=CHAT_HTML,
        js_api=WindowAPI(),
        width=380,
        height=580,
        resizable=False,
        frameless=True,
        easy_drag=True,
        background_color="#0f0f13",
    )

    if _chat_window:
        try:
            _chat_window.show()
            return
        except Exception:
            pass

    _chat_window = webview.create_window(
        "Чат",
        html=CHAT_HTML,
        width=420,
        height=620,
        resizable=False,
        frameless=False,
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
        width=480,
        height=600,
        resizable=False,
        frameless=True,
        easy_drag=True,
        background_color="#0f0f13",
        hidden=True,
    )

    def _on_incoming_message(data):
        sender = data.get("sender", "Партнёр")
        text   = data.get("text", "")

        # Если открыто окно чата — перерисовываем список сообщений
        if _chat_window:
            try:
                _chat_window.evaluate_js("loadChat();")
            except Exception:
                pass

        if _window_visible:
            # Главное окно на экране — красивый toast внутри интерфейса
            if _window:
                try:
                    sender_js = json.dumps(sender)
                    text_js   = json.dumps(text)
                    _window.evaluate_js(f"showChatToast({sender_js}, {text_js})")
                except Exception:
                    pass
        else:
            # Окно свёрнуто/в трее — показывать внутри интерфейса некому,
            # используем настоящее системное Windows-уведомление
            from core.notifications import notify_chat_message
            notify_chat_message(sender, text)

    network.on_message(_on_incoming_message)

    def hide_from_taskbar():
        import ctypes
        hwnd = ctypes.windll.user32.FindWindowW(None, "Together")
        if hwnd:
            GWL_EXSTYLE     = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_APPWINDOW  = 0x00040000
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = (style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

    threading.Timer(1.5, hide_from_taskbar).start()

    webview.start(debug=False)
    os._exit(0)
