import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")


def list_tables():
    try:
        r = requests.get(f"{API_BASE}/tables", timeout=5)
        return r.json() if r.ok else []
    except requests.RequestException:
        return []


def create_table(table_data):
    try:
        r = requests.post(f"{API_BASE}/tables", json=table_data, timeout=5)
        return r.status_code in (200, 201)
    except requests.RequestException:
        return False


def evaluate_table(table_id, inputs):
    try:
        r = requests.post(f"{API_BASE}/tables/{table_id}/evaluate", json={"inputs": inputs}, timeout=5)
        return r.json() if r.ok else None
    except requests.RequestException:
        return None
