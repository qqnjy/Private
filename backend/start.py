import uvicorn
import sys
import os

if sys.stdout is None:
    # Running under pythonw.exe, redirect stdout and stderr to a file
    log_file = open("backend_output.log", "a", encoding="utf-8")
    sys.stdout = log_file
    sys.stderr = log_file

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
