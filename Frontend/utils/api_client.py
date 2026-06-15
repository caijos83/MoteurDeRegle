import requests

API_BASE = "http://localhost:8000/api/v1"

def list_tables():
    try:
        r = requests.get(f"{API_BASE}/tables")
        return r.json() if r.ok else []
    except:
        return []

def create_table(table_data):
    try:
        r = requests.post(f"{API_BASE}/tables", json=table_data)
        return r.status_code in (200, 201)
    except:
        return False

def evaluate_table(table_id, inputs):
    try:
        r = requests.post(f"{API_BASE}/tables/{table_id}/evaluate", json={"inputs": inputs})
        return r.json() if r.ok else None
    except:
        return None