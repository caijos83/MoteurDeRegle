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

    if sys.platform == "darwin":
        mac_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
        for path in mac_paths:
            if os.path.exists(path):
                return path
        return None

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
    elif sys.platform == "darwin":
        applescript = f'''
        tell application "Safari"
            make new document with properties {{URL:"{url}"}}
            activate
        end tell
        '''
        os.system(f"osascript -e '{applescript}'")
    else:
        webbrowser.open(url)

def _stop(api, ui):
    print("\nArrêt en cours...")
    for p in (api, ui):
        try:
            p.terminate()
            p.wait(timeout=5)
        except Exception:
            p.kill()

if __name__ == "__main__":
    # Détecter si on est sur Windows pour les flags de création de processus
    creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0

    print("Démarrage de l'API...")
    # On ajoute le creation_flags uniquement si on est sous Windows
    api = subprocess.Popen(API_CMD, creationflags=creation_flags)

    print("Démarrage de l'interface...")
    ui = subprocess.Popen(UI_CMD, creationflags=creation_flags)

    print("Application lancée. Fermez ce terminal pour tout arrêter.")
    time.sleep(4)
    open_app()

    print("Application lancée. Appuyez sur Ctrl+C pour tout arrêter.")
    # Garder le script en vie
    try:
        api.wait()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _stop(api, ui)

        api.terminate()
        ui.terminate()