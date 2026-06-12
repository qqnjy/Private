module.exports = {
  apps: [
    {
      name: "data_tracker_backend",
      script: "venv/Scripts/python.exe",
      args: "start.py",
      cwd: "c:/Users/winniexue/.gemini/antigravity-ide/scratch/IGS/粉絲團數據追蹤/backend",
      windowsHide: true,
      env: {
        PYTHONIOENCODING: "utf-8"
      }
    },
    {
      name: "data_tracker_frontend",
      script: "node_modules/vite/bin/vite.js",
      args: "--host",
      cwd: "c:/Users/winniexue/.gemini/antigravity-ide/scratch/IGS/粉絲團數據追蹤",
      windowsHide: true
    }
  ]
};
