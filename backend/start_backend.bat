@echo off
venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8000
