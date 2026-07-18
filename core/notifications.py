"""
Звуковое уведомление о новом сообщении в чате.

Раньше тут был системный Windows toast (через winotify) — убрали, потому
что Windows toast штука капризная (фокус-ассистент, антивирус, политики
уведомлений для непроверенных приложений — мог просто не показываться
без объяснения причин, без ошибок в коде). Плюс визуально это "засоряло"
интерфейс.

winsound — встроенный модуль Python на Windows, ничего доустанавливать
не нужно. Звук всегда один — свой файл sound/alarm.wav, без возможности
подменить его через настройки (раньше был выбор своего .wav / системного
звука Windows через настройки — убрали по просьбе, звук уведомления
теперь не настраивается и не "гуляет" между устройствами с разной
Windows-темой звуков).
"""
import os
from core.paths import resource_path

try:
    import winsound
    _AVAILABLE = True
except ImportError:
    # Не-Windows система (например при разработке/тестах) — просто молчим
    _AVAILABLE = False

_SOUND_PATH = resource_path("sound", "alarm.wav")


def play_chat_sound():
    """Проигрывает звук уведомления. Не блокирует поток (SND_ASYNC)."""
    if not _AVAILABLE:
        return

    if os.path.isfile(_SOUND_PATH):
        try:
            winsound.PlaySound(_SOUND_PATH, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return
        except Exception:
            pass  # если файл почему-то не проигрался — падаем на системный звук ниже

    try:
        # Подстраховка на случай, если sound/alarm.wav вдруг отсутствует
        # (например, случайно не попал в сборку .exe) — звук уведомления
        # молчать не должен, лучше стандартный "динь" Windows, чем ничего.
        winsound.PlaySound(
            "SystemAsterisk",
            winsound.SND_ALIAS | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
        )
    except Exception:
        # Уведомления не критичны — не должны ронять поток сети
        pass
