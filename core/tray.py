"""
Иконка в трее
"""
import sys
import os
import builtins

try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw
except ImportError:
    print("pip install pystray pillow")
    sys.exit(1)

from core.paths import resource_path

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
        # Раньше сюда добавлялись ещё две строки с текущим приложением и
        # статусом партнёра (enabled=False, клик по ним ничего не делал) —
        # это дублировало подсказку при наведении на иконку и только
        # засоряло меню. Убраны; актуальный статус по-прежнему виден в
        # title иконки при наведении, его обновляет _on_activity_change.
        return pystray.Menu(
            item("💑 Открыть Together", self._open_window, default=True),
            pystray.Menu.SEPARATOR,
            item("❌ Закрыть", self._quit),
        )

    def _on_activity_change(self, activity):
        if self._icon:
            # Раньше title менялся на "Together — <статус>" при каждой
            # смене активности — по просьбе оставляем просто "Together"
            # в подсказке трея, статус там больше не отображается.
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
        # Свой логотип — положи файл assets/icon.png (квадратный,
        # рекомендуется 256x256, с прозрачным фоном) рядом с main.py.
        # Если файла нет — используется сгенерированная заглушка ниже.
        custom_path = resource_path("assets", "icon.png")
        if os.path.isfile(custom_path):
            try:
                return Image.open(custom_path).convert("RGBA")
            except Exception:
                pass  # битый/неподдерживаемый файл — падаем на заглушку

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
