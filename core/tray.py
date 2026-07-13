"""
Иконка в трее
"""
import sys
import builtins

try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw
except ImportError:
    print("pip install pystray pillow")
    sys.exit(1)

# Глобальный флаг для корректного завершения
_quit_flag = False


class TrayApp:
    def __init__(self, tracker, network=None):
        self.tracker = tracker
        self.network = network
        self._icon = None
        self.tracker.on_change(self._on_activity_change)
        if network:
            network.on_status_change(self._on_connection_change)

    def run(self):
        image = self._create_icon_image()
        self._icon = pystray.Icon(
            name="Together",
            icon=image,
            title="Together",
            menu=self._build_menu()
        )
        self._icon.run()

    def _build_menu(self):
        connected = self.network.is_connected() if self.network else False
        conn_text = "🟢 Партнёр онлайн" if connected else "🔴 Ожидание партнёра"
        return pystray.Menu(
            item("💑 Открыть Together", self._open_window, default=True),
            pystray.Menu.SEPARATOR,
            item(self._get_status_text, lambda: None, enabled=False),
            item(conn_text, lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            item("❌ Закрыть", self._quit),
        )

    def _get_status_text(self, icon=None, item=None):
        current = self.tracker.get_current()
        if current.get("afk"):
            return "😴 AFK"
        return f"▶ {current.get('app', '—')}"

    def _on_activity_change(self, activity):
        if self._icon:
            app = activity.get("app", "—")
            status = "AFK" if activity.get("afk") else app
            self._icon.title = f"Together — {status}"
            self._icon.menu = self._build_menu()

    def _on_connection_change(self, connected):
        if self._icon:
            self._icon.menu = self._build_menu()

    def _open_window(self, icon=None, item=None):
        cb = getattr(builtins, "_together_open_window", None)
        if cb:
            cb()

    def _quit(self, icon=None, item=None):
        # Сначала останавливаем иконку трея
        if self._icon:
            self._icon.stop()
        # А дальше всей остановкой (tracker/network/stats + сохранение
        # сессии) занимается _do_quit() в window.py — раньше он вызывался
        # ЗДЕСЬ ЖЕ отдельно, и получалось двойное выполнение одного и того
        # же кода (видно в логе как два подряд "stop() called")
        cb = getattr(builtins, "_together_quit", None)
        if cb:
            cb()

    def _create_icon_image(self, size=64):
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        m = 4
        draw.ellipse([m, m, size-m, size-m], fill=(83, 74, 183, 255))
        cx, cy = size//2, size//2
        r = size//8
        o = size//10
        draw.ellipse([cx-o-r*2, cy-r-4, cx-o, cy+r-4], fill=(255,255,255,255))
        draw.ellipse([cx+o-r*2, cy-r-4, cx+o, cy+r-4], fill=(255,255,255,255))
        draw.polygon([(cx-o-r, cy+r-6),(cx+o+r, cy+r-6),(cx, cy+r*3-2)], fill=(255,255,255,255))
        return img
