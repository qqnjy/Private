@echo off
cd /d "%~dp0backend"
call venv\Scripts\activate.bat
python auto_scrape_all.py
pause
