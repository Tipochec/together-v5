"""
Звуковое уведомление о новом сообщении в чате.

Раньше тут был системный Windows toast (через winotify) — убрали, потому
что Windows toast штука капризная (фокус-ассистент, антивирус, политики
уведомлений для непроверенных приложений — мог просто не показываться
без объяснения причин, без ошибок в коде). Плюс визуально это "засоряло"
интерфейс.

winsound — встроенный модуль Python на Windows, ничего доустанавливать
не нужно. Поддерживается свой .wav файл через settings.json
("custom_sound_path") — если файла нет/не указан — играет системный звук.
"""
import os

try:
    import winsound
    _AVAILABLE = True
except ImportError:
    # Не-Windows система (например при разработке/тестах) — просто молчим
    _AVAILABLE = False


def _settings():
    try:
        from core.tracker import load_settings
        return load_settings()
    except Exception:
        return {}


def play_chat_sound():
    """Проигрывает звук уведомления. Не блокирует поток (SND_ASYNC)."""
    if not _AVAILABLE:
        return

    custom_path = _settings().get("custom_sound_path", "").strip()
    if custom_path and custom_path.lower().endswith(".wav"):
        if not os.path.isabs(custom_path):
            project_root = os.path.join(os.path.dirname(__file__), "..")
            custom_path = os.path.join(project_root, custom_path)
        if os.path.isfile(custom_path):
            try:
                winsound.PlaySound(custom_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                return
            except Exception:
                pass  # если свой файл не проигрался — падаем на системный звук ниже

    try:
        # SystemAsterisk — стандартный "динь" звук уведомления Windows,
        # настраивается пользователем в Панели управления → Звуки
        winsound.PlaySound(
            "SystemAsterisk",
            winsound.SND_ALIAS | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
        )
    except Exception:
        # Уведомления не критичны — не должны ронять поток сети
        pass
