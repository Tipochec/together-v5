@echo off
chcp 65001 >nul
echo ============================================
echo   Сборка Together.exe через PyInstaller
echo ============================================

python -m PyInstaller --clean --noconfirm together.spec

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Не удалось собрать Together.exe
    pause
    exit /b 1
)

echo.
echo ============================================
echo   [УСПЕХ] Файл собран в: dist\Together.exe
echo ============================================
pause
