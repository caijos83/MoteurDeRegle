"""
Lanceur — démarre l'API et le frontend, puis ouvre l'application.
Usage : py run.py
"""

import subprocess
import sys
import os
import time
import shutil
import webbrowser
from dotenv import load_dotenv

load_dotenv()

API_PORT = os.getenv("API_PORT", "8000")
UI_PORT  = os.getenv("UI_PORT",  "8501")

API_CMD = [sys.executable, "-m", "uvicorn", "API.rest.main:app", "--port", API_PORT]
UI_CMD  = [
    sys.executable, "-m", "streamlit", "run", "Frontend/app.py",
    "--server.port", UI_PORT,
    "--server.headless", "true",
    "--server.runOnSave", "false",
    "--browser.gatherUsageStats", "false",
]

def _find_browser():
    custom = os.getenv("BROWSER_PATH")
    if custom:
        return custom
    for name in ("msedge", "microsoft-edge", "chrome", "google-chrome", "chromium"):
        path = shutil.which(name)
        if path:
            return path
    return None

def open_app():
    url = f"http://localhost:{UI_PORT}"
    browser = _find_browser()
    if browser:
        subprocess.Popen([browser, f"--app={url}", "--new-window"])
    else:
        webbrowser.open(url)

if __name__ == "__main__":
    print("Démarrage de l'API...")
    api = subprocess.Popen(API_CMD, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)

    print("Démarrage de l'interface...")
    ui = subprocess.Popen(UI_CMD, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)

    print("Attente du démarrage (3 s)...")
    time.sleep(3)

    print("Ouverture de l'application...")
    open_app()

    print("Application lancée. Fermez cette fenêtre pour tout arrêter.")
    try:
        ui.wait()
    except KeyboardInterrupt:
        pass
    finally:
        api.terminate()
        ui.terminate()
