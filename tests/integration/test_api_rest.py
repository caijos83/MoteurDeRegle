"""
Tests d'intégration REST — appellent l'API FastAPI en mémoire via httpx.AsyncClient.
Aucun serveur externe requis : on utilise le transport ASGI de httpx.
"""

import pytest
import pytest_asyncio
import httpx
from API.rest.main import app

BASE = "/api/v1"

_TABLE_PAYLOAD = {
    "name": "TestIntegration",
    "hit_policy": "FIRST",
    "columns": [
        {"name": "age",      "type": "number", "role": "input"},
        {"name": "decision", "type": "text",   "role": "output"},
    ],
}

_RULES = [
    {"conditions": {"age": ">= 18"}, "output": {"decision": "MAJEUR"}},
    {"conditions": {"age": "< 18"},  "output": {"decision": "MINEUR"}},
]


@pytest_asyncio.fixture
async def client():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest_asyncio.fixture
async def created_table(client):
    """Crée une table et la supprime après le test."""
    r = await client.post(f"{BASE}/tables", json=_TABLE_PAYLOAD)
    assert r.status_code == 201
    table = r.json()
    yield table
    await client.delete(f"{BASE}/tables/{table['id']}")


# ── /health ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── CRUD tables ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_table(client):
    r = await client.post(f"{BASE}/tables", json=_TABLE_PAYLOAD)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "TestIntegration"
    assert data["hit_policy"] == "FIRST"
    assert len(data["columns"]) == 2
    await client.delete(f"{BASE}/tables/{data['id']}")


@pytest.mark.asyncio
async def test_list_tables(client, created_table):
    r = await client.get(f"{BASE}/tables")
    assert r.status_code == 200
    ids = [t["id"] for t in r.json()]
    assert created_table["id"] in ids


@pytest.mark.asyncio
async def test_get_table(client, created_table):
    r = await client.get(f"{BASE}/tables/{created_table['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created_table["id"]


@pytest.mark.asyncio
async def test_get_table_not_found(client):
    r = await client.get(f"{BASE}/tables/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_table_rules(client, created_table):
    r = await client.put(
        f"{BASE}/tables/{created_table['id']}",
        json={"rules": _RULES},
    )
    assert r.status_code == 200
    assert len(r.json()["rules"]) == 2


@pytest.mark.asyncio
async def test_delete_table(client):
    r = await client.post(f"{BASE}/tables", json=_TABLE_PAYLOAD)
    tid = r.json()["id"]
    r_del = await client.delete(f"{BASE}/tables/{tid}")
    assert r_del.status_code == 204
    r_get = await client.get(f"{BASE}/tables/{tid}")
    assert r_get.status_code == 404


# ── Évaluation ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_evaluate_first_match(client, created_table):
    # Ajoute les règles d'abord
    await client.put(
        f"{BASE}/tables/{created_table['id']}",
        json={"rules": _RULES},
    )
    r = await client.post(
        f"{BASE}/tables/{created_table['id']}/evaluate",
        json={"inputs": {"age": 25}},
    )
    assert r.status_code == 200
    result = r.json()["result"]
    assert result.get("decision") == "MAJEUR"


@pytest.mark.asyncio
async def test_evaluate_first_no_match(client, created_table):
    await client.put(
        f"{BASE}/tables/{created_table['id']}",
        json={"rules": _RULES},
    )
    r = await client.post(
        f"{BASE}/tables/{created_table['id']}/evaluate",
        json={"inputs": {"age": 10}},
    )
    assert r.status_code == 200
    assert r.json()["result"].get("decision") == "MINEUR"


@pytest.mark.asyncio
async def test_evaluate_collect_sum(client):
    payload = {
        "name": "ScoreTest",
        "hit_policy": "COLLECT SUM",
        "columns": [
            {"name": "score", "type": "number", "role": "output"},
        ],
        "rules": [
            {"conditions": {}, "output": {"score": "10"}},
            {"conditions": {}, "output": {"score": "5"}},
        ],
    }
    r = await client.post(f"{BASE}/tables", json=payload)
    assert r.status_code == 201
    tid = r.json()["id"]

    r_eval = await client.post(
        f"{BASE}/tables/{tid}/evaluate",
        json={"inputs": {}},
    )
    assert r_eval.status_code == 200
    await client.delete(f"{BASE}/tables/{tid}")
