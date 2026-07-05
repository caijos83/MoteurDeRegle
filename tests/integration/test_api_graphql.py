"""
Tests d'intégration GraphQL — vérifie queries et mutations via httpx ASGI.
"""

import pytest
import pytest_asyncio
import httpx
from API.rest.main import app

GRAPHQL = "/graphql"

_GQL_LIST = {"query": "{ tables { id name hitPolicy } }"}
_GQL_TYPES = {"query": "{ columnTypes }"}

_CREATE_MUTATION = """
mutation {
  createTable(input: {
    name: "GQLTest",
    hitPolicy: "FIRST",
    columns: [
      { name: "age", type: "number", role: "input" },
      { name: "result", type: "text", role: "output" }
    ]
  }) { id name hitPolicy }
}
"""

_DELETE_MUTATION = """
mutation DeleteTable($id: String!) {
  deleteTable(id: $id)
}
"""

_EVALUATE_MUTATION = """
mutation Eval($id: String!, $inputs: String!) {
  evaluateTable(tableId: $id, inputsJson: $inputs) { result hitPolicy }
}
"""


@pytest_asyncio.fixture
async def client():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest_asyncio.fixture
async def gql_table(client):
    r = await client.post(GRAPHQL, json={"query": _CREATE_MUTATION})
    assert r.status_code == 200
    data = r.json()["data"]["createTable"]
    yield data
    await client.post(GRAPHQL, json={
        "query": _DELETE_MUTATION,
        "variables": {"id": data["id"]},
    })


# ── Queries ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gql_list_tables(client):
    r = await client.post(GRAPHQL, json=_GQL_LIST)
    assert r.status_code == 200
    assert "errors" not in r.json()
    assert isinstance(r.json()["data"]["tables"], list)


@pytest.mark.asyncio
async def test_gql_column_types(client):
    r = await client.post(GRAPHQL, json=_GQL_TYPES)
    assert r.status_code == 200
    types = r.json()["data"]["columnTypes"]
    assert "number" in types
    assert "text" in types
    assert "boolean" in types


@pytest.mark.asyncio
async def test_gql_get_table(client, gql_table):
    query = f'{{ table(id: "{gql_table["id"]}") {{ id name }} }}'
    r = await client.post(GRAPHQL, json={"query": query})
    assert r.status_code == 200
    assert "errors" not in r.json()
    assert r.json()["data"]["table"]["name"] == "GQLTest"


# ── Mutations ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gql_create_and_delete_table(client):
    r = await client.post(GRAPHQL, json={"query": _CREATE_MUTATION})
    assert r.status_code == 200
    created = r.json()["data"]["createTable"]
    assert created["name"] == "GQLTest"
    assert created["hitPolicy"] == "FIRST"

    r_del = await client.post(GRAPHQL, json={
        "query": _DELETE_MUTATION,
        "variables": {"id": created["id"]},
    })
    assert r_del.status_code == 200
    assert r_del.json()["data"]["deleteTable"] is True


@pytest.mark.asyncio
async def test_gql_evaluate(client, gql_table):
    import json
    # Ajoute une règle via REST pour pouvoir évaluer
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        await c.put(
            f"/api/v1/tables/{gql_table['id']}",
            json={"rules": [
                {"conditions": {"age": ">= 18"}, "output": {"result": "OK"}},
            ]},
        )

    inputs_str = json.dumps({"age": 20})
    r = await client.post(GRAPHQL, json={
        "query": _EVALUATE_MUTATION,
        "variables": {"id": gql_table["id"], "inputs": inputs_str},
    })
    assert r.status_code == 200
    assert "errors" not in r.json()
