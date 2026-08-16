@echo off
chcp 65001 > nul

:: Определяем папку, где находится run.bat
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

:: Убираем слеш в конце
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

:: Пути к Python и анализатору
set "PYTHON_PATH=%PROJECT_DIR%\venv\Scripts\python.exe"
set "ANALYZER_DIR=%PROJECT_DIR%\CellHunter.Analyzer"

:: Проверяем, что Python существует
if not exist "%PYTHON_PATH%" (
    echo ❌ Python не найден!
    echo 💡 Пожалуйста, запустите setup.bat сначала.
    pause
    exit /b 1
)

:: Проверяем, что CellHunter.Desktop.exe существует
if not exist "%PROJECT_DIR%\CellHunter.Desktop\CellHunter.Desktop.exe" (
    echo ❌ CellHunter.Desktop.exe не найден!
    pause
    exit /b 1
)

:: Запускаем CellHunter.Desktop.exe с путями в аргументах
:: или через paths.json (если реализовано)
start "" "%PROJECT_DIR%\CellHunter.Desktop\CellHunter.Desktop.exe"