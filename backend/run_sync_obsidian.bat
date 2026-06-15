@echo off
echo 正在從 Supabase 同步粉絲團數據到 Obsidian...
cd /d "c:\Users\winniexue\.gemini\antigravity-ide\scratch\IGS\粉絲團數據追蹤\backend"
call venv\Scripts\activate
python sync_obsidian.py
timeout /t 5
