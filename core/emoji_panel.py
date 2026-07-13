"""
Открытие системной панели эмодзи Windows (сочетание Win + .) программно,
по клику на кнопку смайлика в чате — чтобы не приходилось нажимать
сочетание клавиш руками.

Работает через SendInput: имитируем нажатие Win, затем ".", затем отпускаем
оба — с точки зрения Windows это неотличимо от реального нажатия клавиш,
поэтому системная панель эмодзи открывается как обычно, привязываясь
к тому текстовому полю, которое сейчас в фокусе.
"""
import ctypes

try:
    user32 = ctypes.windll.user32
    _AVAILABLE = True
except Exception:
    _AVAILABLE = False

VK_LWIN       = 0x5B
VK_OEM_PERIOD = 0xBE   # клавиша "."

KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD  = 1

PUL = ctypes.POINTER(ctypes.c_ulong)


class _KeyBdInput(ctypes.Structure):
    _fields_ = [
        ("wVk",         ctypes.c_ushort),
        ("wScan",       ctypes.c_ushort),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", PUL),
    ]


class _Input_I(ctypes.Union):
    _fields_ = [("ki", _KeyBdInput)]


class _Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", _Input_I)]


def _send_key(vk, key_up=False):
    extra = ctypes.c_ulong(0)
    flags = KEYEVENTF_KEYUP if key_up else 0
    ii_ = _Input_I()
    ii_.ki = _KeyBdInput(vk, 0, flags, 0, ctypes.pointer(extra))
    inp = _Input(ctypes.c_ulong(INPUT_KEYBOARD), ii_)
    user32.SendInput(1, ctypes.pointer(inp), ctypes.sizeof(inp))


def open_emoji_panel():
    """Имитирует Win + . — открывает системную панель эмодзи Windows."""
    if not _AVAILABLE:
        return False
    try:
        _send_key(VK_LWIN)
        _send_key(VK_OEM_PERIOD)
        _send_key(VK_OEM_PERIOD, key_up=True)
        _send_key(VK_LWIN, key_up=True)
        return True
    except Exception:
        return False
