@echo off
title GRIDX v4.0 Global AI Edition
echo ============================================================
echo   GRIDX v4.0 - ONE GRID. EVERY SOLUTION.
echo ============================================================
if not exist venv python -m venv venv --system-site-packages
call venv\Scripts\activate
pip install -r requirements.txt --quiet
python manage.py makemigrations users services
python manage.py migrate
echo [OK] Launching server at http://127.0.0.1:8000 ...
start http://127.0.0.1:8000
python manage.py runserver
pause
