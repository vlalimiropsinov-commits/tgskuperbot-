@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .env (
  echo Файл .env не найден. Переименуй .env.example в .env и вставь токен.
  pause
  exit /b 1
)
if not exist venv (
  echo Создаю виртуальное окружение...
  py -3.11 -m venv venv || python -m venv venv
  call venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  pip install -r requirements.txt
) else (
  call venv\Scripts\activate.bat
)
python bot.py
pause
