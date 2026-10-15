"""
Модуль автообновления Together через GitHub Releases.
"""
import os
import sys
import json
import time
import tempfile
import threading
import subprocess
import urllib.request
import urllib.error

from core.paths import is_frozen
from core.version import APP_VERSION, GITHUB_REPO


def parse_version(v_str):
    """Преобразует строку версии вроде 'v1.2.3' или '1.2' в кортеж чисел (1, 2, 3)."""
    if not v_str:
        return (0, 0, 0)
    cleaned = v_str.strip().lstrip("vV")
    parts = []
    for p in cleaned.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            break
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def is_newer(remote_ver_str, local_ver_str=APP_VERSION):
    """Возвращает True, если remote_ver_str новее local_ver_str."""
    return parse_version(remote_ver_str) > parse_version(local_ver_str)


def check_updates():
    """
    Проверяет наличие свежего релиза на GitHub.
    Возвращает dict с информацией об обновлении.
    """
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"Together-App/{APP_VERSION}",
            "Accept": "application/vnd.github.v3+json",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=6.0) as resp:
            if resp.status != 200:
                return {
                    "has_update": False,
                    "error": f"Сервер вернул код {resp.status}",
                    "current_version": APP_VERSION,
                }
            data = json.loads(resp.read().decode("utf-8"))

        remote_tag = data.get("tag_name") or ""
        remote_name = data.get("name") or remote_tag
        body = data.get("body") or ""
        assets = data.get("assets") or []

        # Ищем exe файл среди вложений релиза
        exe_asset = None
        for a in assets:
            name = a.get("name", "")
            if name.lower().endswith(".exe"):
                exe_asset = a
                break

        download_url = exe_asset.get("browser_download_url") if exe_asset else None
        has_new = is_newer(remote_tag, APP_VERSION) and (download_url is not None)

        return {
            "has_update": has_new,
            "current_version": APP_VERSION,
            "latest_version": remote_tag.lstrip("vV"),
            "release_name": remote_name,
            "release_notes": body,
            "download_url": download_url,
            "asset_name": exe_asset.get("name") if exe_asset else None,
            "asset_size": exe_asset.get("size") if exe_asset else 0,
        }
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {
                "has_update": False,
                "error": "Релизы на GitHub пока не опубликованы",
                "current_version": APP_VERSION,
            }
        return {
            "has_update": False,
            "error": f"Ошибка сети: HTTP {e.code}",
            "current_version": APP_VERSION,
        }
    except Exception as e:
        return {
            "has_update": False,
            "error": f"Не удалось проверить обновления: {e}",
            "current_version": APP_VERSION,
        }


def apply_update(download_url, progress_callback=None):
    """
    Скачивает обновление по download_url и запускает процесс самозамены.
    Если запущено не из .exe (dev-режим), скачивает файл и сообщает об этом.
    """
    target_exe = os.path.abspath(sys.executable)
    temp_dir = tempfile.gettempdir()
    download_target = os.path.join(temp_dir, f"Together_update_{int(time.time())}.exe")

    req = urllib.request.Request(
        download_url,
        headers={"User-Agent": f"Together-App/{APP_VERSION}"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 65536
            with open(download_target, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        pct = int((downloaded / total_size) * 100)
                        try:
                            progress_callback(pct)
                        except Exception:
                            pass

        if not is_frozen() or not target_exe.lower().endswith(".exe"):
            return {
                "success": True,
                "dev_mode": True,
                "message": f"Обновление скачано в {download_target}. В режиме разработки авто-замена .exe отключена."
            }

        # Создаём bat-скрипт, который подождёт завершения текущего процесса,
        # заменит старый .exe на новый и запустит обновлённое приложение.
        bat_path = os.path.join(temp_dir, f"together_updater_{int(time.time())}.bat")
        bat_content = f"""@echo off
chcp 65001 >nul
echo Обновление Together...
timeout /t 1 /nobreak >nul
:retry
move /y "{download_target}" "{target_exe}" >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto retry
)
start "" "{target_exe}"
del "%~f0"
"""
        with open(bat_path, "w", encoding="utf-8") as bf:
            bf.write(bat_content)

        # Запускаем bat-скрипт в полностью скрытом окне (CREATE_NO_WINDOW = 0x08000000)
        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen(["cmd.exe", "/c", bat_path], creationflags=CREATE_NO_WINDOW)

        # Даём скрипту запуститься и немедленно выходим
        def _delayed_exit():
            time.sleep(0.5)
            os._exit(0)

        threading.Thread(target=_delayed_exit, daemon=True).start()
        return {"success": True, "restarting": True}

    except Exception as e:
        if os.path.exists(download_target):
            try:
                os.remove(download_target)
            except Exception:
                pass
        return {"success": False, "error": str(e)}
