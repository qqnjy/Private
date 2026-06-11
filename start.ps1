Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\venv\Scripts\python -m uvicorn main:app --reload --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm run dev"
