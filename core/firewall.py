"""
Автоматическая настройка Брандмауэра Windows для входящих подключений.

Почему это нужно: порт 39721 слушается на 0.0.0.0, но по умолчанию
Брандмауэр Windows блокирует входящие TCP-подключения к нему, если для
приложения нет явного разрешающего правила — особенно на сетевом
профиле "Общедоступная сеть", в который часто попадают VPN-адаптеры
вроде ZeroTier/Radmin/Hamachi.

Без этого правила картина ровно такая, с какой мы столкнулись на
практике: у тебя всё "подключено" и партнёр виден в интерфейсе, потому
что ТВОЙ клиент успешно достучался до НЕГО. Но ЕГО клиент, пытаясь
достучаться до ТЕБЯ, утыкается в твой файрвол — SYN-пакет молча
отбрасывается, ping при этом проходит (ICMP почти всегда разрешён), и
у партнёра в логе просто TimeoutError без единого намёка на причину.
Внешне — "у меня входящие сообщения не доходят", хотя проблема на
стороне ПОЛУЧАТЕЛЯ, не отправителя.

Раньше пользователю приходилось лезть в настройки Windows руками. Само
диалоговое окно "Разрешить приложению работать через брандмауэр?",
которое Windows обычно показывает при первом входящем соединении,
здесь ПРИЛОЖЕНИЕ НЕ ВИДИТ — main.spec собирается с console=False (окно
без консоли), и в такой конфигурации это системное окно легко
пропустить или случайно закрыть не глядя, особенно нетехническому
человеку.

netsh advfirewall firewall add rule требует прав администратора,
поэтому пытаемся добавить правило через одноразовый elevated-процесс —
пользователь увидит стандартный UAC-запрос ("Разрешить этому
приложению вносить изменения?"), как при установке любой обычной
программы, один раз за всё время использования настроек.
"""
import subprocess
import sys

from core.paths import is_frozen

RULE_NAME = "Together (app)"
PORT = 39721


def _no_window_kwargs():
    """Чтобы вызов netsh (не элевейтед — для show rule) не мигал чёрным
    консольным окном поверх интерфейса приложения."""
    kwargs = {}
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kwargs


def _exe_path():
    """Путь к процессу, для которого создаётся правило. В собранном
    .exe — это сам исполняемый файл. В режиме разработки — python.exe,
    которым запущен main.py (правило по имени файла иначе не будет
    соответствовать реально слушающему порт процессу)."""
    return sys.executable


def rule_exists():
    """Проверка наличия правила НЕ требует прав администратора."""
    try:
        result = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", f"name={RULE_NAME}"],
            capture_output=True, text=True, timeout=10,
            **_no_window_kwargs(),
        )
        return result.returncode == 0 and "No rules match" not in result.stdout
    except Exception:
        return False


def add_rule_elevated():
    """
    Добавляет правило через UAC (ShellExecuteW с verb='runas').

    ShellExecuteW возвращает управление сразу после запуска процесса,
    не дожидаясь его завершения, поэтому здесь нет "успеха" в смысле
    "правило точно добавлено" — есть только "elevated-процесс успешно
    стартовал" (возврат > 32) либо "пользователь нажал 'Нет' в UAC"
    (Windows в этом случае возвращает код ошибки ERROR_ACCESS_DENIED=5).
    Итоговый факт наличия правила потом отдельно проверяется rule_exists().
    """
    try:
        import ctypes
        exe = _exe_path()
        params = (
            f'advfirewall firewall add rule name="{RULE_NAME}" '
            f'dir=in action=allow program="{exe}" protocol=TCP '
            f'localport={PORT} profile=any enable=yes'
        )
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", "netsh", params, None, 0
        )
        return int(result) > 32
    except Exception as e:
        print(f"Брандмауэр: не удалось запустить elevated-процесс — {e}")
        return False


def ensure_firewall_rule_once():
    """
    Вызывается один раз при старте приложения (в отдельном потоке —
    UAC-диалог, если появится, не должен блокировать открытие окна).

    Пытается настроить брандмауэр сам, но не чаще одного раза за всё
    время жизни settings.json — если пользователь один раз отказал в
    UAC (или добавление не удалось по другой причине), мы не долбим
    его этим диалогом на каждом запуске. Повторить попытку осознанно
    можно кнопкой "Настроить брандмауэр" в настройках (см. ui/window.py
    WindowAPI.setup_firewall).
    """
    if not is_frozen():
        # В режиме разработки (python.exe из консоли) файрвол обычно уже
        # разрешён — интерпретатор используется для множества других
        # задач, и лишний UAC-запрос тут скорее мешает, чем помогает.
        return

    from core.tracker import load_settings, _settings_path
    import json

    settings = load_settings()
    if settings.get("_firewall_setup_attempted"):
        return

    if not rule_exists():
        add_rule_elevated()

    settings["_firewall_setup_attempted"] = True
    try:
        with open(_settings_path(), "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Брандмауэр: не удалось сохранить флаг попытки настройки — {e}")
