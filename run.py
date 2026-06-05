"""
Lanceur — démarre l'API et le frontend, puis ouvre l'application.
Usage : py run.py
"""

import subprocess
import sys
import os
import time
import signal

EDGE   = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

API_CMD = [sys.executable, "-m", "uvicorn", "API.rest.main:app", "--port", "8000"]
UI_CMD  = [
    sys.executable, "-m", "streamlit", "run", "Frontend/app.py",
    "--server.port", "8501",
    "--server.headless", "true",
    "--server.runOnSave", "false",
    "--browser.gatherUsageStats", "false",
]

def open_app():
    url = "http://localhost:8501"
    if os.path.exists(EDGE):
        subprocess.Popen([EDGE, f"--app={url}", "--new-window"])
    elif os.path.exists(CHROME):
        subprocess.Popen([CHROME, f"--app={url}", "--new-window"])
    else:
        import webbrowser
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
