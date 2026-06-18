@echo off
chcp 65001 >nul
cd /d "c:\Users\winniexue\.gemini\antigravity-ide\scratch\IGS\粉絲團數據追蹤\backend"
call venv\Scripts\activate
python auto_scrape_all.py
