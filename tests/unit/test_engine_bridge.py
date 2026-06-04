"""
Tests unitaires du pont Python (fallback engine) — TDD.
"""

import pytest
from Backend.bridge.engine_bridge import (
    _evaluate_python_fallback,
    _rule_matches,
    _match_condition,
)

TABLE_FIRST = {
    "id": "test-1",
    "name": "TestFirst",
    "hit_policy": "FIRST",
    "columns": [
        {"name": "age", "type": "number", "role": "input"},
        {"name": "decision", "type": "text", "role": "output"},
    ],
    "rules": [
        {"conditions": {"age": ">= 18"}, "output": {"decision": "MAJEUR"}},
        {"conditions": {"age": "< 18"}, "output": {"decision": "MINEUR"}},
    ],
}

TABLE_SUM = {
    "id": "test-2",
    "name": "TestSum",
    "hit_policy": "COLLECT SUM",
    "columns": [
        {"name": "statut", "type": "text", "role": "input"},
        {"name": "score", "type": "number", "role": "output"},
    ],
    "rules": [
        {"conditions": {"statut": "premium"}, "output": {"score": "10"}},
        {"conditions": {"statut": "premium"}, "output": {"score": "5"}},
        {"conditions": {"statut": "basic"}, "output": {"score": "2"}},
    ],
}


class TestMatchCondition:
    def test_egal(self):
        assert _match_condition("18", "= 18")
        assert not _match_condition("17", "= 18")

    def test_superieur(self):
        assert _match_condition("25", "> 18")
        assert not _match_condition("18", "> 18")

    def test_superieur_egal(self):
        assert _match_condition("18", ">= 18")
        assert _match_condition("25", ">= 18")
        assert not _match_condition("17", ">= 18")

    def test_inferieur(self):
        assert _match_condition("17", "< 18")
        assert not _match_condition("18", "< 18")

    def test_different(self):
        assert _match_condition("5", "!= 18")
        assert not _match_condition("18", "!= 18")

    def test_intervalle_ferme(self):
        assert _match_condition("5", "[1..10]")
        assert _match_condition("1", "[1..10]")
        assert _match_condition("10", "[1..10]")
        assert not _match_condition("11", "[1..10]")

    def test_intervalle_semi_ouvert(self):
        assert _match_condition("5", "[1..10[")
        assert not _match_condition("10", "[1..10[")

    def test_liste(self):
        assert _match_condition("A", '["A","B","C"]')
        assert not _match_condition("D", '["A","B","C"]')

    def test_egalite_directe(self):
        assert _match_condition("premium", "premium")
        assert not _match_condition("basic", "premium")


class TestHitFirst:
    def test_premiere_regle_matchante(self):
        result = _evaluate_python_fallback(TABLE_FIRST, {"age": "25"})
        assert result["result"]["decision"] == "MAJEUR"

    def test_deuxieme_regle(self):
        result = _evaluate_python_fallback(TABLE_FIRST, {"age": "15"})
        assert result["result"]["decision"] == "MINEUR"

    def test_aucune_regle(self):
        result = _evaluate_python_fallback(TABLE_FIRST, {"age": "0"})
        # age=0 matche "< 18"
        assert result["result"]["decision"] == "MINEUR"


class TestHitCollectSum:
    def test_somme_deux_regles(self):
        result = _evaluate_python_fallback(TABLE_SUM, {"statut": "premium"})
        assert result["result"] == 15.0
        assert result["matched_rules"] == 2

    def test_une_regle(self):
        result = _evaluate_python_fallback(TABLE_SUM, {"statut": "basic"})
        assert result["result"] == 2.0
        assert result["matched_rules"] == 1
