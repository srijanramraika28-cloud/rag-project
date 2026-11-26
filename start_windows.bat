@echo off
cd /d "%~dp0"
if not exist .venv (
  echo Creating Python virtual environment...
  py -3 -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env (
  copy .env.example .env
  echo A new .env file has been created. Add your NVIDIA API key now.
  notepad .env
  pause
)
echo Starting SmartDoc AI at http://localhost:8000 ...
python -m uvicorn backend.main:app --reload
