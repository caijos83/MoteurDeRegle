"""
DMN Light — Moteur d'évaluation des règles.
Reçoit une table JSON et des inputs, retourne le résultat selon la hit policy.
"""

from collections import Dict, List
import json


fn evaluate(table_json: String, inputs_json: String) -> String:
    """
    Point d'entrée principal.
    table_json  : table de décision sérialisée en JSON
    inputs_json : valeurs d'input sérialisées en JSON
    Retourne    : résultat JSON {"result": ..., "matched_rules": [...]}
    """
    # TODO: implémenter le parsing JSON Mojo
    # TODO: dispatcher selon hit_policy (FIRST ou COLLECT_SUM)
    return '{"result": null, "error": "not implemented"}'


fn match_rule(rule: Dict[String, String], inputs: Dict[String, String]) -> Bool:
    """Vérifie si une règle matche les inputs donnés."""
    for condition in rule.items():
        let col = condition[0]
        let expr = condition[1]
        if col not in inputs:
            return False
        if not match_condition(inputs[col], expr):
            return False
    return True


fn match_condition(value: String, expr: String) -> Bool:
    """
    Évalue une condition DMN sur une valeur.
    Opérateurs supportés : >, <, >=, <=, =, !=, [a..b], ["v1","v2"]
    """
    let trimmed = expr.strip()

    # Intervalle fermé [a..b]
    if trimmed.startswith("[") and ".." in trimmed and trimmed.endswith("]"):
        return match_interval(value, trimmed, inclusive_start=True, inclusive_end=True)

    # Intervalle semi-ouvert [a..b[
    if trimmed.startswith("[") and ".." in trimmed and trimmed.endswith("["):
        return match_interval(value, trimmed, inclusive_start=True, inclusive_end=False)

    # Appartenance à liste ["v1","v2"]
    if trimmed.startswith("[") and trimmed.endswith("]"):
        return match_list(value, trimmed)

    # Opérateurs de comparaison
    if trimmed.startswith(">="):
        return compare_numeric(value, trimmed[2:].strip(), ">=")
    if trimmed.startswith("<="):
        return compare_numeric(value, trimmed[2:].strip(), "<=")
    if trimmed.startswith(">"):
        return compare_numeric(value, trimmed[1:].strip(), ">")
    if trimmed.startswith("<"):
        return compare_numeric(value, trimmed[1:].strip(), "<")
    if trimmed.startswith("!="):
        return value != trimmed[2:].strip()
    if trimmed.startswith("="):
        return value == trimmed[1:].strip()

    # Égalité directe
    return value == trimmed


fn match_interval(value: String, expr: String, inclusive_start: Bool, inclusive_end: Bool) -> Bool:
    """Évalue si une valeur numérique est dans un intervalle [a..b]."""
    # TODO: parser les bornes et comparer
    return False


fn match_list(value: String, expr: String) -> Bool:
    """Évalue si une valeur est dans une liste ["v1","v2"]."""
    # TODO: parser la liste JSON et vérifier l'appartenance
    return False


fn compare_numeric(value: String, threshold: String, op: String) -> Bool:
    """Comparaison numérique."""
    # TODO: convertir en Float64 et comparer
    return False
