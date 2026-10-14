@echo off
title GRIDX v2.0 - Enterprise Roadside and Indoor Dispatch Network
echo ============================================================
echo   GRIDX v2.0 - ONE GRID. EVERY SOLUTION. (Refined Edition)
echo ============================================================
if not exist .env (
    copy .env.example .env >nul
)
if not exist venv (
    python -m venv venv --system-site-packages
)
call venv\Scripts\activate
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt --quiet
python manage.py makemigrations users services
python manage.py migrate
echo.
echo [OK] Launching GRIDX v2.0 at http://127.0.0.1:8000 ...
start http://127.0.0.1:8000
python manage.py runserver
pause
