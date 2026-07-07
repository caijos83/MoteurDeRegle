"""
SCRUM-69 — Tests IHM
Teste la couche api_client.py utilisée par le Frontend Streamlit.
On simule les appels HTTP avec unittest.mock pour ne pas dépendre
d'un serveur en cours d'exécution.
"""
import pytest
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, "/home/cerinekerrar01/projet_ppd/MoteurDeRegle")
sys.path.insert(0, "/home/cerinekerrar01/projet_ppd/MoteurDeRegle/Frontend")

from utils.api_client import list_tables, create_table, evaluate_table


# ─────────────────────────────────────────────
# Tests list_tables
# ─────────────────────────────────────────────
class TestListTables:
    def test_retourne_liste_tables(self):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = [
            {"id": "1", "name": "Table1"},
            {"id": "2", "name": "Table2"},
        ]
        with patch("utils.api_client.requests.get", return_value=mock_response):
            result = list_tables()
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "Table1"

    def test_retourne_liste_vide_si_erreur(self):
        mock_response = MagicMock()
        mock_response.ok = False
        with patch("utils.api_client.requests.get", return_value=mock_response):
            result = list_tables()
        assert result == []

    def test_retourne_liste_vide_si_serveur_injoignable(self):
        with patch("utils.api_client.requests.get", side_effect=Exception("Connexion refusée")):
            result = list_tables()
        assert result == []

    def test_retourne_liste_vide(self):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = []
        with patch("utils.api_client.requests.get", return_value=mock_response):
            result = list_tables()
        assert result == []


# ─────────────────────────────────────────────
# Tests create_table
# ─────────────────────────────────────────────
class TestCreateTable:
    def _table_valide(self):
        return {
            "name": "TestIHM",
            "hit_policy": "FIRST",
            "columns": [
                {"name": "age", "type": "number", "role": "input"},
                {"name": "decision", "type": "text", "role": "output"},
            ],
            "rules": []
        }

    def test_creation_reussie_201(self):
        mock_response = MagicMock()
        mock_response.status_code = 201
        with patch("utils.api_client.requests.post", return_value=mock_response):
            result = create_table(self._table_valide())
        assert result is True

    def test_creation_reussie_200(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch("utils.api_client.requests.post", return_value=mock_response):
            result = create_table(self._table_valide())
        assert result is True

    def test_creation_echouee_422(self):
        mock_response = MagicMock()
        mock_response.status_code = 422
        with patch("utils.api_client.requests.post", return_value=mock_response):
            result = create_table({})
        assert result is False

    def test_creation_echouee_serveur_injoignable(self):
        with patch("utils.api_client.requests.post", side_effect=Exception("Timeout")):
            result = create_table(self._table_valide())
        assert result is False


# ─────────────────────────────────────────────
# Tests evaluate_table
# ─────────────────────────────────────────────
class TestEvaluateTable:
    def test_evaluation_reussie(self):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "result": {"decision": "MAJEUR"},
            "hit_policy": "FIRST"
        }
        with patch("utils.api_client.requests.post", return_value=mock_response):
            result = evaluate_table("table-123", {"age": "25"})
        assert result is not None
        assert result["result"]["decision"] == "MAJEUR"

    def test_evaluation_table_inexistante(self):
        mock_response = MagicMock()
        mock_response.ok = False
        with patch("utils.api_client.requests.post", return_value=mock_response):
            result = evaluate_table("id-inexistant", {"age": "25"})
        assert result is None

    def test_evaluation_serveur_injoignable(self):
        with patch("utils.api_client.requests.post", side_effect=Exception("Timeout")):
            result = evaluate_table("table-123", {"age": "25"})
        assert result is None

    def test_evaluation_collect_sum(self):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "result": 15.0,
            "matched_rules": 2,
            "hit_policy": "COLLECT SUM"
        }
        with patch("utils.api_client.requests.post", return_value=mock_response):
            result = evaluate_table("table-456", {"statut": "premium"})
        assert result["result"] == 15.0
        assert result["matched_rules"] == 2

    def test_evaluation_inputs_vides(self):
        mock_response = MagicMock()
        mock_response.ok = False
        with patch("utils.api_client.requests.post", return_value=mock_response):
            result = evaluate_table("table-123", {})
        assert result is None
