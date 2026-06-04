"""
Hit Policy FIRST — retourne le résultat de la première règle qui matche.
"""

from collections import Dict, List
from .evaluator import match_rule


fn evaluate_first(
    rules: List[Dict[String, String]],
    inputs: Dict[String, String]
) -> Dict[String, String]:
    """
    Parcourt les règles dans l'ordre.
    Retourne l'output de la première règle dont les conditions matchent les inputs.
    Retourne un dict vide si aucune règle ne matche.
    """
    for rule in rules:
        let conditions = rule["conditions"]
        if match_rule(conditions, inputs):
            return rule["output"]
    return Dict[String, String]()
