"""
SCRUM-68 — Tests API REST
Teste les endpoints /tables et /tables/{id}/evaluate via TestClient FastAPI.
Utilise le fallback JSON (pas besoin de TerminusDB).
"""
import pytest
import sys
import shutil
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, "/home/cerinekerrar01/projet_ppd/MoteurDeRegle")

from API.rest.main import app

client = TestClient(app)

# Table de test réutilisée dans plusieurs tests
TABLE_VALIDE = {
    "name": "TestAPI",
    "hit_policy": "FIRST",
    "columns": [
        {"name": "age", "type": "number", "role": "input"},
        {"name": "decision", "type": "text", "role": "output"},
    ],
    "rules": [
        {"conditions": {"age": ">= 18"}, "output": {"decision": "MAJEUR"}},
        {"conditions": {"age": "< 18"},  "output": {"decision": "MINEUR"}},
    ]
}


# ─────────────────────────────────────────────
# Tests POST /tables — Création
# ─────────────────────────────────────────────
class TestCreateTable:
    def test_creation_table_valide(self):
        response = client.post("/api/v1/tables", json=TABLE_VALIDE)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "TestAPI"
        assert data["hit_policy"] == "FIRST"

    def test_creation_sans_nom(self):
        body = {**TABLE_VALIDE}
        del body["name"]
        response = client.post("/api/v1/tables", json=body)
        assert response.status_code == 422

    def test_creation_hit_policy_invalide(self):
        body = {**TABLE_VALIDE, "hit_policy": "UNIQUE"}
        response = client.post("/api/v1/tables", json=body)
        assert response.status_code == 422

    def test_creation_sans_colonnes(self):
        body = {**TABLE_VALIDE}
        del body["columns"]
        response = client.post("/api/v1/tables", json=body)
        assert response.status_code == 422

    def test_creation_sans_regles(self):
        body = {k: v for k, v in TABLE_VALIDE.items() if k != "rules"}
        response = client.post("/api/v1/tables", json=body)
        assert response.status_code == 201
        assert response.json()["rules"] == []


# ─────────────────────────────────────────────
# Tests GET /tables — Liste
# ─────────────────────────────────────────────
class TestListTables:
    def test_liste_retourne_liste(self):
        response = client.get("/api/v1/tables")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ─────────────────────────────────────────────
# Tests GET /tables/{id} — Récupération
# ─────────────────────────────────────────────
class TestGetTable:
    def test_get_table_existante(self):
        # Créer d'abord une table
        created = client.post("/api/v1/tables", json=TABLE_VALIDE).json()
        table_id = created["id"]

        response = client.get(f"/api/v1/tables/{table_id}")
        assert response.status_code == 200
        assert response.json()["id"] == table_id

    def test_get_table_inexistante(self):
        response = client.get("/api/v1/tables/id-qui-nexiste-pas")
        assert response.status_code == 404
        assert response.json()["detail"] == "Table introuvable"


# ─────────────────────────────────────────────
# Tests PUT /tables/{id} — Mise à jour
# ─────────────────────────────────────────────
class TestUpdateTable:
    def test_update_nom(self):
        created = client.post("/api/v1/tables", json=TABLE_VALIDE).json()
        table_id = created["id"]

        response = client.put(f"/api/v1/tables/{table_id}", json={"name": "NouveauNom"})
        assert response.status_code == 200
        assert response.json()["name"] == "NouveauNom"

    def test_update_table_inexistante(self):
        response = client.put("/api/v1/tables/id-inexistant", json={"name": "Test"})
        assert response.status_code == 404


# ─────────────────────────────────────────────
# Tests DELETE /tables/{id} — Suppression
# ─────────────────────────────────────────────
class TestDeleteTable:
    def test_delete_table_existante(self):
        created = client.post("/api/v1/tables", json=TABLE_VALIDE).json()
        table_id = created["id"]

        response = client.delete(f"/api/v1/tables/{table_id}")
        assert response.status_code == 204

        # Vérifier qu'elle n'existe plus
        response = client.get(f"/api/v1/tables/{table_id}")
        assert response.status_code == 404

    def test_delete_table_inexistante(self):
        response = client.delete("/api/v1/tables/id-inexistant")
        assert response.status_code == 404


# ─────────────────────────────────────────────
# Tests POST /tables/{id}/evaluate — Évaluation
# ─────────────────────────────────────────────
class TestEvaluateTable:
    def test_evaluate_majeur(self):
        created = client.post("/api/v1/tables", json=TABLE_VALIDE).json()
        table_id = created["id"]

        response = client.post(
            f"/api/v1/tables/{table_id}/evaluate",
            json={"inputs": {"age": 25}}
        )
        assert response.status_code == 200
        assert response.json()["result"]["decision"] == "MAJEUR"

    def test_evaluate_mineur(self):
        created = client.post("/api/v1/tables", json=TABLE_VALIDE).json()
        table_id = created["id"]

        response = client.post(
            f"/api/v1/tables/{table_id}/evaluate",
            json={"inputs": {"age": 15}}
        )
        assert response.status_code == 200
        assert response.json()["result"]["decision"] == "MINEUR"

    def test_evaluate_table_inexistante(self):
        response = client.post(
            "/api/v1/tables/id-inexistant/evaluate",
            json={"inputs": {"age": 25}}
        )
        assert response.status_code == 404

    def test_evaluate_input_manquant(self):
        created = client.post("/api/v1/tables", json=TABLE_VALIDE).json()
        table_id = created["id"]

        response = client.post(
            f"/api/v1/tables/{table_id}/evaluate",
            json={"inputs": {}}  # age manquant
        )
        assert response.status_code == 422

    def test_evaluate_collect_sum(self):
        table_sum = {
            "name": "TestSum",
            "hit_policy": "COLLECT SUM",
            "columns": [
                {"name": "statut", "type": "text",   "role": "input"},
                {"name": "score",  "type": "number", "role": "output"},
            ],
            "rules": [
                {"conditions": {"statut": "premium"}, "output": {"score": "10"}},
                {"conditions": {"statut": "premium"}, "output": {"score": "5"}},
            ]
        }
        created = client.post("/api/v1/tables", json=table_sum).json()
        table_id = created["id"]

        response = client.post(
            f"/api/v1/tables/{table_id}/evaluate",
            json={"inputs": {"statut": "premium"}}
        )
        assert response.status_code == 200
        assert response.json()["result"] == 15.0


# ─────────────────────────────────────────────
# Test health check
# ─────────────────────────────────────────────
class TestHealth:
    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
