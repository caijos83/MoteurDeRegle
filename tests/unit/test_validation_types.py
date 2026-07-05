"""
SCRUM-62 — Tests de validation des types
Teste que les types number, text, boolean sont correctement validés
dans les colonnes et les règles de la table de décision.
"""
import pytest
from pydantic import ValidationError

from API.rest.routes.tables import Column, Rule, TableCreate
from Backend.bridge.engine_bridge import _evaluate_python_fallback
from Backend.bridge.dmn_matcher import match_condition as _match_condition


# ─────────────────────────────────────────────
# Tests validation du type "number"
# ─────────────────────────────────────────────
class TestTypeNumber:
    def test_colonne_number_valide(self):
        col = Column(name="age", type="number", role="input")
        assert col.type == "number"

    def test_number_accepte_entier(self):
        assert _match_condition(">= 18", "18", "number")

    def test_number_accepte_decimal(self):
        assert _match_condition(">= 18", "18.5", "number")

    def test_number_intervalle(self):
        assert _match_condition("[0..100]", "50", "number")
        assert not _match_condition("[0..100]", "150", "number")

    def test_number_valeur_negative(self):
        assert _match_condition("< 0", "-5", "number")
        assert not _match_condition(">= 0", "-5", "number")

    def test_number_zero(self):
        assert _match_condition("= 0", "0", "number")
        assert not _match_condition("> 0", "0", "number")


# ─────────────────────────────────────────────
# Tests validation du type "text"
# ─────────────────────────────────────────────
class TestTypeText:
    def test_colonne_text_valide(self):
        col = Column(name="statut", type="text", role="input")
        assert col.type == "text"

    def test_text_egalite_directe(self):
        assert _match_condition("premium", "premium", "text")
        assert not _match_condition("premium", "basic", "text")

    def test_text_liste_valeurs(self):
        assert _match_condition('["or", "and", "not"]', "or", "text")
        assert not _match_condition('["or", "and", "not"]', "xor", "text")

    def test_text_different(self):
        assert _match_condition("!= premium", "basic", "text")
        assert not _match_condition("!= premium", "premium", "text")

    def test_text_case_sensitive(self):
        assert not _match_condition("premium", "Premium", "text")
        assert not _match_condition("premium", "PREMIUM", "text")


# ─────────────────────────────────────────────
# Tests validation du type "boolean"
# ─────────────────────────────────────────────
class TestTypeBoolean:
    def test_colonne_boolean_valide(self):
        col = Column(name="actif", type="boolean", role="input")
        assert col.type == "boolean"

    def test_boolean_true(self):
        assert _match_condition("true", "true", "boolean")
        assert not _match_condition("true", "false", "boolean")

    def test_boolean_false(self):
        assert _match_condition("false", "false", "boolean")
        assert not _match_condition("false", "true", "boolean")

    def test_boolean_different(self):
        assert _match_condition("!= true", "false", "boolean")


# ─────────────────────────────────────────────
# Tests types invalides
# ─────────────────────────────────────────────
class TestTypesInvalides:
    def test_type_float_refuse(self):
        with pytest.raises(ValidationError):
            Column(name="prix", type="float", role="input")

    def test_type_integer_refuse(self):
        with pytest.raises(ValidationError):
            Column(name="age", type="integer", role="input")

    def test_type_date_refuse(self):
        with pytest.raises(ValidationError):
            Column(name="date", type="date", role="input")

    def test_type_vide_refuse(self):
        with pytest.raises(ValidationError):
            Column(name="col", type="", role="input")


# ─────────────────────────────────────────────
# Tests cohérence types dans une table complète
# ─────────────────────────────────────────────
class TestTypesTableComplete:
    def test_table_avec_tous_les_types(self):
        table = TableCreate(
            name="TestTypes",
            hit_policy="FIRST",
            columns=[
                {"name": "age",   "type": "number",  "role": "input"},
                {"name": "actif", "type": "boolean", "role": "input"},
                {"name": "nom",   "type": "text",    "role": "input"},
                {"name": "score", "type": "number",  "role": "output"},
            ],
            rules=[]
        )
        types = [c.type for c in table.columns]
        assert "number" in types
        assert "boolean" in types
        assert "text" in types

    def test_evaluation_type_number_dans_moteur(self):
        table = {
            "hit_policy": "FIRST",
            "columns": [
                {"name": "score", "type": "number", "role": "input"},
                {"name": "niveau", "type": "text", "role": "output"},
            ],
            "rules": [
                {"conditions": {"score": ">= 90"}, "output": {"niveau": "A"}},
                {"conditions": {"score": ">= 70"}, "output": {"niveau": "B"}},
                {"conditions": {"score": "< 70"},  "output": {"niveau": "C"}},
            ]
        }
        assert _evaluate_python_fallback(table, {"score": "95"})["result"]["niveau"] == "A"
        assert _evaluate_python_fallback(table, {"score": "75"})["result"]["niveau"] == "B"
        assert _evaluate_python_fallback(table, {"score": "60"})["result"]["niveau"] == "C"

    def test_evaluation_type_text_dans_moteur(self):
        table = {
            "hit_policy": "FIRST",
            "columns": [
                {"name": "statut", "type": "text", "role": "input"},
                {"name": "remise", "type": "number", "role": "output"},
            ],
            "rules": [
                {"conditions": {"statut": "premium"}, "output": {"remise": "20"}},
                {"conditions": {"statut": "basic"},   "output": {"remise": "5"}},
            ]
        }
        assert _evaluate_python_fallback(table, {"statut": "premium"})["result"]["remise"] == "20"
        assert _evaluate_python_fallback(table, {"statut": "basic"})["result"]["remise"] == "5"

    def test_evaluation_type_boolean_dans_moteur(self):
        table = {
            "hit_policy": "FIRST",
            "columns": [
                {"name": "actif", "type": "boolean", "role": "input"},
                {"name": "acces", "type": "text",    "role": "output"},
            ],
            "rules": [
                {"conditions": {"actif": "true"},  "output": {"acces": "AUTORISE"}},
                {"conditions": {"actif": "false"}, "output": {"acces": "REFUSE"}},
            ]
        }
        assert _evaluate_python_fallback(table, {"actif": "true"})["result"]["acces"] == "AUTORISE"
        assert _evaluate_python_fallback(table, {"actif": "false"})["result"]["acces"] == "REFUSE"
