import os, sys, shutil, subprocess, zipfile
from pathlib import Path

PROJECT_ROOT = Path("gridx_project")
PROJECT_ROOT.mkdir(exist_ok=True)

print("[INFO] Building GRIDX v4.0 Global AI Edition inside gridx_project/ ...")

(PROJECT_ROOT / "prompts").mkdir(exist_ok=True)
(PROJECT_ROOT / "services/ai").mkdir(parents=True, exist_ok=True)
(PROJECT_ROOT / "static/css").mkdir(parents=True, exist_ok=True)
(PROJECT_ROOT / "static/js").mkdir(parents=True, exist_ok=True)
(PROJECT_ROOT / "templates/components").mkdir(parents=True, exist_ok=True)
(PROJECT_ROOT / "templates/pages").mkdir(parents=True, exist_ok=True)

(PROJECT_ROOT / "requirements.txt").write_text("Django>=5.0,<5.2\ndjangorestframework>=3.15.0\ndjango-cors-headers>=4.3.1\npython-dotenv>=1.0.1\nrequests>=2.31.0\ngunicorn>=21.2.0\nwhitenoise>=6.6.0\nPillow>=10.2.0\n", encoding="utf-8")
(PROJECT_ROOT / ".env.example").write_text("SECRET_KEY=secure-key\nDEBUG=True\nGROQ_API_KEY=\n", encoding="utf-8")
(PROJECT_ROOT / ".gitignore").write_text("venv/\n*.pyc\ndb.sqlite3\nmedia/\n*.zip\n", encoding="utf-8")

bat_code = """@echo off
title GRIDX v4.0 Global AI Edition
echo ============================================================
echo   GRIDX v4.0 - ONE GRID. EVERY SOLUTION.
echo ============================================================
if not exist venv python -m venv venv --system-site-packages
call venv\\Scripts\\activate
pip install -r requirements.txt --quiet
python manage.py makemigrations users services
python manage.py migrate
echo [OK] Launching server at http://127.0.0.1:8000 ...
start http://127.0.0.1:8000
python manage.py runserver
pause
"""
(PROJECT_ROOT / "start_gridx.bat").write_text(bat_code, encoding="ascii")
print("[SUCCESS] GRIDX v4.0 setup script created successfully.")
