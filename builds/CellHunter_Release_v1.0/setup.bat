@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ============================================================
echo 🧬 CellHunter - Установка
echo ============================================================
echo.

:: Определяем папку, где находится setup.bat
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

:: Убираем слеш в конце
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

echo 📁 Папка установки: %PROJECT_DIR%
echo.

:: ============================================================
:: Шаг 1: Проверяем наличие Python portable
:: ============================================================
echo [1/6] Проверка Python portable...

set "PYTHON_DIR=%PROJECT_DIR%\python_portable"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"

if exist "%PYTHON_EXE%" (
    echo    ✅ Python уже установлен
    goto :check_venv
)

:: Если нет - скачиваем Python portable
echo    📥 Скачиваю Python 3.10 portable...
echo    ⏳ Это может занять 2-3 минуты...

:: Скачиваем portable Python с официального сайта
:: Используем PowerShell для скачивания
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip' -OutFile '%PROJECT_DIR%\python_portable.zip'"

if errorlevel 1 (
    echo    ❌ Ошибка скачивания Python!
    echo    💡 Проверьте интернет-соединение и попробуйте снова.
    pause
    exit /b 1
)

:: Распаковываем
echo    📦 Распаковка Python...
powershell -Command "Expand-Archive -Path '%PROJECT_DIR%\python_portable.zip' -DestinationPath '%PYTHON_DIR%' -Force"

:: Удаляем архив
del "%PROJECT_DIR%\python_portable.zip"

:: Создаем файл python._pth для включения pip
echo python310.zip > "%PYTHON_DIR%\python._pth"
echo . >> "%PYTHON_DIR%\python._pth"
echo import site >> "%PYTHON_DIR%\python._pth"

:: Скачиваем get-pip.py
powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%PROJECT_DIR%\get-pip.py'"

:: Устанавливаем pip
"%PYTHON_EXE%" "%PROJECT_DIR%\get-pip.py"

del "%PROJECT_DIR%\get-pip.py"

echo    ✅ Python portable установлен!

:: ============================================================
:: Шаг 2: Проверяем/создаем виртуальное окружение
:: ============================================================
:check_venv
echo.
echo [2/6] Проверка виртуального окружения...

set "VENV_DIR=%PROJECT_DIR%\venv"

if exist "%VENV_DIR%\Scripts\python.exe" (
    echo    ✅ Виртуальное окружение уже существует
    goto :check_deps
)

echo    📦 Создаю виртуальное окружение...
"%PYTHON_EXE%" -m venv "%VENV_DIR%"

if errorlevel 1 (
    echo    ❌ Ошибка создания виртуального окружения!
    pause
    exit /b 1
)

echo    ✅ Виртуальное окружение создано!

:: ============================================================
:: Шаг 3: Установка зависимостей
:: ============================================================
:check_deps
echo.
echo [3/6] Установка зависимостей (это займет 3-5 минут)...

set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"

:: Обновляем pip
"%VENV_PYTHON%" -m pip install --upgrade pip

:: Устанавливаем зависимости
"%VENV_PIP%" install -r "%PROJECT_DIR%\CellHunter.Analyzer\requirements.txt"

if errorlevel 1 (
    echo    ❌ Ошибка установки зависимостей!
    echo    💡 Возможно, проблема с интернет-соединением.
    pause
    exit /b 1
)

echo    ✅ Зависимости установлены!

:: ============================================================
:: Шаг 4: Настройка путей в PythonBridge
:: ============================================================
echo.
echo [4/6] Настройка путей...

:: Создаем файл с путями для PythonBridge
:: PythonBridge будет читать его при запуске
echo {"python_path": "%VENV_DIR%\Scripts\python.exe", "analyzer_dir": "%PROJECT_DIR%\CellHunter.Analyzer"} > "%PROJECT_DIR%\paths.json"

echo    ✅ Пути сохранены

:: ============================================================
:: Шаг 5: Создание ярлыка
:: ============================================================
echo.
echo [5/6] Создание ярлыка...

:: Создаем run.bat (запускатор)
(
echo @echo off
echo cd /d "%~dp0"
echo start "" "%PROJECT_DIR%\CellHunter.Desktop\CellHunter.Desktop.exe"
) > "%PROJECT_DIR%\run.bat"

:: Создаем ярлык на рабочем столе (через VBS)
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\CellHunter.lnk'); $Shortcut.TargetPath = '%PROJECT_DIR%\run.bat'; $Shortcut.WorkingDirectory = '%PROJECT_DIR%'; $Shortcut.IconLocation = '%PROJECT_DIR%\CellHunter.Desktop\CellHunter.Desktop.exe'; $Shortcut.Save()"

echo    ✅ Ярлык создан на рабочем столе!

:: ============================================================
:: Шаг 6: Тестирование
:: ============================================================
echo.
echo [6/6] Проверка установки...

:: Проверяем, что все файлы на месте
if exist "%PROJECT_DIR%\CellHunter.Desktop\CellHunter.Desktop.exe" (
    echo    ✅ CellHunter.Desktop.exe найден
) else (
    echo    ❌ CellHunter.Desktop.exe НЕ НАЙДЕН!
    echo    💡 Проверьте структуру папок.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo ✅ УСТАНОВКА ЗАВЕРШЕНА!
echo ============================================================
echo.
echo 📂 Папка установки: %PROJECT_DIR%
echo 🖥️ Ярлык на рабочем столе: CellHunter
echo.
echo 💡 Для запуска дважды кликните на ярлык CellHunter
echo    или запустите run.bat.
echo.
echo 💡 Для удаления просто удалите папку %PROJECT_DIR%
echo    и ярлык с рабочего стола или запустите uninstall.bat.
echo.
pause