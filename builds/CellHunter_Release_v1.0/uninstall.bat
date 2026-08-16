@echo off
chcp 65001 > nul

echo ============================================================
echo 🧬 CellHunter - Удаление
echo ============================================================
echo.
echo ⚠️ ВНИМАНИЕ: Это удалит ВСЕ файлы CellHunter!
echo.

set /p confirm="Удалить CellHunter? (y/n): "

if /i not "%confirm%"=="y" (
    echo ❌ Отмена
    pause
    exit /b 0
)

:: Удаляем папку проекта (на уровень выше)
cd /d "%~dp0.."
set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

echo 📂 Удаление: %PROJECT_DIR%...
cd /d "%~dp0.."
rmdir /s /q "%PROJECT_DIR%"

:: Удаляем ярлык
if exist "%USERPROFILE%\Desktop\CellHunter.lnk" (
    del "%USERPROFILE%\Desktop\CellHunter.lnk"
    echo ✅ Ярлык удален
)

echo ✅ CellHunter удален!
pause