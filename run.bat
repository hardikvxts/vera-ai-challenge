@echo off
echo ========================================================
echo Starting Vera AI Challenge Bot...
echo ========================================================
cd /d "%~dp0"
call .venv\Scripts\activate.bat
start http://127.0.0.1:8000/docs
uvicorn app:app --reload --port 8000
pause
