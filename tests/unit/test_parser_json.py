"""
SCRUM-66 — Tests du parser JSON (validation des tables de décision)
Teste la validation Pydantic des modèles Column, Rule, TableCreate.
"""
import pytest
from pydantic import ValidationError

from API.rest.routes.tables import Column, Rule, TableCreate


# ─────────────────────────────────────────────
# Tests Column
# ─────────────────────────────────────────────
class TestColumnParser:
    def test_colonne_valide_input(self):
        col = Column(name="age", type="number", role="input")
        assert col.name == "age"
        assert col.type == "number"
        assert col.role == "input"

    def test_colonne_valide_output(self):
        col = Column(name="decision", type="text", role="output")
        assert col.role == "output"

    def test_type_invalide(self):
        with pytest.raises(ValidationError):
            Column(name="age", type="entier", role="input")  # type inconnu

    def test_role_invalide(self):
        with pytest.raises(ValidationError):
            Column(name="age", type="number", role="condition")  # role inconnu

    def test_type_boolean(self):
        col = Column(name="actif", type="boolean", role="input")
        assert col.type == "boolean"

    def test_nom_manquant(self):
        with pytest.raises(ValidationError):
            Column(type="number", role="input")


# ─────────────────────────────────────────────
# Tests Rule
# ─────────────────────────────────────────────
class TestRuleParser:
    def test_regle_valide(self):
        rule = Rule(
            conditions={"age": ">= 18"},
            output={"decision": "MAJEUR"}
        )
        assert rule.conditions["age"] == ">= 18"
        assert rule.output["decision"] == "MAJEUR"

    def test_regle_conditions_vides(self):
        # Une règle sans conditions est valide (match-all)
        rule = Rule(conditions={}, output={"decision": "DEFAULT"})
        assert rule.conditions == {}

    def test_regle_output_vide(self):
        with pytest.raises(ValidationError):
            Rule(conditions={"age": "> 0"})  # output manquant

    def test_regle_conditions_multiples(self):
        rule = Rule(
            conditions={"age": ">= 18", "statut": "premium"},
            output={"score": "100"}
        )
        assert len(rule.conditions) == 2

    def test_regle_valeurs_numeriques_en_string(self):
        rule = Rule(
            conditions={"score": "[0..100]"},
            output={"niveau": "OK"}
        )
        assert rule.conditions["score"] == "[0..100]"


# ─────────────────────────────────────────────
# Tests TableCreate
# ─────────────────────────────────────────────
class TestTableCreateParser:
    def _table_valide(self):
        return {
            "name": "TestTable",
            "hit_policy": "FIRST",
            "columns": [
                {"name": "age", "type": "number", "role": "input"},
                {"name": "decision", "type": "text", "role": "output"},
            ],
            "rules": [
                {"conditions": {"age": ">= 18"}, "output": {"decision": "MAJEUR"}},
            ]
        }

    def test_table_valide_first(self):
        table = TableCreate(**self._table_valide())
        assert table.name == "TestTable"
        assert table.hit_policy == "FIRST"
        assert len(table.columns) == 2
        assert len(table.rules) == 1

    def test_table_valide_collect_sum(self):
        data = self._table_valide()
        data["hit_policy"] = "COLLECT SUM"
        table = TableCreate(**data)
        assert table.hit_policy == "COLLECT SUM"

    def test_hit_policy_invalide(self):
        data = self._table_valide()
        data["hit_policy"] = "UNIQUE"  # non supportée
        with pytest.raises(ValidationError):
            TableCreate(**data)

    def test_nom_manquant(self):
        data = self._table_valide()
        del data["name"]
        with pytest.raises(ValidationError):
            TableCreate(**data)

    def test_colonnes_manquantes(self):
        data = self._table_valide()
        del data["columns"]
        with pytest.raises(ValidationError):
            TableCreate(**data)

    def test_rules_optionnelles(self):
        data = self._table_valide()
        del data["rules"]
        table = TableCreate(**data)
        assert table.rules == []

    def test_table_sans_colonnes_vide(self):
        data = self._table_valide()
        data["columns"] = []
        table = TableCreate(**data)
        assert table.columns == []

    def test_colonne_type_invalide_dans_table(self):
        data = self._table_valide()
        data["columns"][0]["type"] = "float"  # non supporté
        with pytest.raises(ValidationError):
            TableCreate(**data)

    def test_plusieurs_colonnes_output(self):
        data = self._table_valide()
        data["columns"].append({"name": "score", "type": "number", "role": "output"})
        table = TableCreate(**data)
        assert len([c for c in table.columns if c.role == "output"]) == 2

    def test_table_collect_sum_avec_plusieurs_regles(self):
        data = {
            "name": "Scoring",
            "hit_policy": "COLLECT SUM",
            "columns": [
                {"name": "statut", "type": "text", "role": "input"},
                {"name": "score", "type": "number", "role": "output"},
            ],
            "rules": [
                {"conditions": {"statut": "premium"}, "output": {"score": "10"}},
                {"conditions": {"statut": "premium"}, "output": {"score": "5"}},
            ]
        }
        table = TableCreate(**data)
        assert len(table.rules) == 2
