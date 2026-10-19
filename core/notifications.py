"""
Звуковые уведомления и микшер громкости.

Масштабирование громкости (0-100%) создаёт предрассчитанные WAV-файлы в папке данных
(alarm_vol.wav и heart_vol.wav). Воспроизведение осуществляется нативно через
winsound.PlaySound(path, SND_FILENAME | SND_ASYNC) — с нулевой задержкой, без очереди
и с мгновенным прерыванием предыдущего звука при повторной отправке.
"""
import os
import wave
import array
from core.paths import resource_path, data_path

try:
    import winsound
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

_ORIG_CHAT_PATH = resource_path("sound", "alarm.wav")
_ORIG_HEART_PATH = resource_path("sound", "heart.wav")

_CHAT_VOLUME = 80
_HEART_VOLUME = 80

_VOL_CHAT_PATH = data_path("alarm_vol.wav")
_VOL_HEART_PATH = data_path("heart_vol.wav")


def _generate_scaled_wav(src_path: str, dst_path: str, volume_pct: int) -> bool:
    """Генерирует масштабированный по громкости WAV-файл."""
    if volume_pct <= 0 or not os.path.isfile(src_path):
        return False

    if volume_pct >= 100:
        try:
            with open(src_path, "rb") as sf, open(dst_path, "wb") as df:
                df.write(sf.read())
            return True
        except Exception:
            return False

    try:
        with wave.open(src_path, "rb") as w:
            params = w.getparams()
            raw_frames = w.readframes(w.getnframes())

        samples = array.array("h", raw_frames)
        factor = max(0.0, min(1.0, volume_pct / 100.0))
        for i in range(len(samples)):
            samples[i] = int(samples[i] * factor)

        with wave.open(dst_path, "wb") as ow:
            ow.setparams(params)
            ow.writeframes(samples.tobytes())
        return True
    except Exception as e:
        print(f"Error generating scaled wav for {src_path}: {e}")
        return False


def get_chat_volume() -> int:
    return _CHAT_VOLUME


def set_chat_volume(volume: int):
    global _CHAT_VOLUME
    try:
        _CHAT_VOLUME = max(0, min(100, int(volume)))
        if _CHAT_VOLUME > 0:
            _generate_scaled_wav(_ORIG_CHAT_PATH, _VOL_CHAT_PATH, _CHAT_VOLUME)
    except (ValueError, TypeError):
        pass


def get_heart_volume() -> int:
    return _HEART_VOLUME


def set_heart_volume(volume: int):
    global _HEART_VOLUME
    try:
        _HEART_VOLUME = max(0, min(100, int(volume)))
        if _HEART_VOLUME > 0:
            _generate_scaled_wav(_ORIG_HEART_PATH, _VOL_HEART_PATH, _HEART_VOLUME)
    except (ValueError, TypeError):
        pass


def play_chat_sound(volume_pct: int = None):
    """
    Воспроизводит звук уведомления чата асинхронно без задержки.
    Повторный вызов мгновенно перезапускает звук без очереди.
    """
    if not _AVAILABLE:
        return

    vol = _CHAT_VOLUME if volume_pct is None else volume_pct
    if vol <= 0:
        return

    # Если передан специфический volume (например, при тесте в микшере)
    play_path = _VOL_CHAT_PATH
    if volume_pct is not None and volume_pct != _CHAT_VOLUME:
        temp_test_path = data_path("test_alarm.wav")
        if _generate_scaled_wav(_ORIG_CHAT_PATH, temp_test_path, volume_pct):
            play_path = temp_test_path

    if not os.path.isfile(play_path):
        _generate_scaled_wav(_ORIG_CHAT_PATH, _VOL_CHAT_PATH, vol)
        play_path = _VOL_CHAT_PATH if os.path.isfile(_VOL_CHAT_PATH) else _ORIG_CHAT_PATH

    try:
        winsound.PlaySound(play_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception as e:
        print(f"play_chat_sound error: {e}")


def play_heart_sound(volume_pct: int = None):
    """
    Воспроизводит звук сердечка асинхронно без задержки.
    Повторный вызов мгновенно перезапускает звук без очереди.
    """
    if not _AVAILABLE:
        return

    vol = _HEART_VOLUME if volume_pct is None else volume_pct
    if vol <= 0:
        return

    # Если передан специфический volume (например, при тесте в микшере)
    play_path = _VOL_HEART_PATH
    if volume_pct is not None and volume_pct != _HEART_VOLUME:
        temp_test_path = data_path("test_heart.wav")
        if _generate_scaled_wav(_ORIG_HEART_PATH, temp_test_path, volume_pct):
            play_path = temp_test_path

    if not os.path.isfile(play_path):
        _generate_scaled_wav(_ORIG_HEART_PATH, _VOL_HEART_PATH, vol)
        play_path = _VOL_HEART_PATH if os.path.isfile(_VOL_HEART_PATH) else _ORIG_HEART_PATH

    try:
        winsound.PlaySound(play_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception as e:
        print(f"play_heart_sound error: {e}")
