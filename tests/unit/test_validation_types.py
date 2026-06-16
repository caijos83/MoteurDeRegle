"""
SCRUM-62 — Tests de validation des types
Teste que les types number, text, boolean sont correctement validés
dans les colonnes et les règles de la table de décision.
"""
import pytest
from pydantic import ValidationError
import sys
sys.path.insert(0, "/home/cerinekerrar01/projet_ppd/MoteurDeRegle")

from API.rest.routes.tables import Column, Rule, TableCreate
from Backend.bridge.engine_bridge import _evaluate_python_fallback


# ─────────────────────────────────────────────
# Tests validation du type "number"
# ─────────────────────────────────────────────
class TestTypeNumber:
    def test_colonne_number_valide(self):
        col = Column(name="age", type="number", role="input")
        assert col.type == "number"

    def test_number_accepte_entier(self):
        """Un entier doit matcher une condition numérique."""
        from Backend.bridge.engine_bridge import _match_condition
        assert _match_condition("18", ">= 18")

    def test_number_accepte_decimal(self):
        from Backend.bridge.engine_bridge import _match_condition
        assert _match_condition("18.5", ">= 18")

    def test_number_intervalle(self):
        from Backend.bridge.engine_bridge import _match_condition
        assert _match_condition("50", "[0..100]")
        assert not _match_condition("150", "[0..100]")

    def test_number_valeur_negative(self):
        from Backend.bridge.engine_bridge import _match_condition
        assert _match_condition("-5", "< 0")
        assert not _match_condition("-5", ">= 0")

    def test_number_zero(self):
        from Backend.bridge.engine_bridge import _match_condition
        assert _match_condition("0", "= 0")
        assert not _match_condition("0", "> 0")


# ─────────────────────────────────────────────
# Tests validation du type "text"
# ─────────────────────────────────────────────
class TestTypeText:
    def test_colonne_text_valide(self):
        col = Column(name="statut", type="text", role="input")
        assert col.type == "text"

    def test_text_egalite_directe(self):
        from Backend.bridge.engine_bridge import _match_condition
        assert _match_condition("premium", "premium")
        assert not _match_condition("basic", "premium")

    def test_text_liste_valeurs(self):
        from Backend.bridge.engine_bridge import _match_condition
        assert _match_condition("or", '["or", "and", "not"]')
        assert not _match_condition("xor", '["or", "and", "not"]')

    def test_text_different(self):
        from Backend.bridge.engine_bridge import _match_condition
        assert _match_condition("basic", "!= premium")
        assert not _match_condition("premium", "!= premium")

    def test_text_case_sensitive(self):
        from Backend.bridge.engine_bridge import _match_condition
        assert not _match_condition("Premium", "premium")
        assert not _match_condition("PREMIUM", "premium")


# ─────────────────────────────────────────────
# Tests validation du type "boolean"
# ─────────────────────────────────────────────
class TestTypeBoolean:
    def test_colonne_boolean_valide(self):
        col = Column(name="actif", type="boolean", role="input")
        assert col.type == "boolean"

    def test_boolean_true(self):
        from Backend.bridge.engine_bridge import _match_condition
        assert _match_condition("true", "true")
        assert not _match_condition("false", "true")

    def test_boolean_false(self):
        from Backend.bridge.engine_bridge import _match_condition
        assert _match_condition("false", "false")
        assert not _match_condition("true", "false")

    def test_boolean_different(self):
        from Backend.bridge.engine_bridge import _match_condition
        assert _match_condition("false", "!= true")


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
