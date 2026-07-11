"""
Windows toast-уведомления — используются ТОЛЬКО когда главное окно
приложения свёрнуто или спрятано в трей (то есть красивый toast внутри
интерфейса физически некому показать, юзер его не увидит).

Если winotify не установлен или отправка не удалась — тихо ничего не
делаем, приложение не должно падать из-за уведомлений.
"""
import os

try:
    from winotify import Notification
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

_ICON_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "icon.ico")


def notify_chat_message(sender, text):
    """Показывает системный toast о новом сообщении в чате."""
    if not _AVAILABLE:
        return
    try:
        preview = (text or "")[:120]
        toast = Notification(
            app_id="Together",
            title=f"💬 {sender}",
            msg=preview,
            icon=_ICON_PATH if os.path.exists(_ICON_PATH) else "",
        )
        toast.show()
    except Exception:
        # Уведомления — не критичная функция, ошибка тут не должна
        # ронять поток сети/трекера
        pass
