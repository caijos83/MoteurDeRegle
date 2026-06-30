"""
Hit Policy FIRST — retourne le résultat de la première règle qui matche.
"""

from std.collections import Dict, List

from evaluator import Rule, match_rule


fn evaluate_first(rules: List[Rule], inputs: Dict[String, String]) raises -> Dict[String, String]:
    """
    Parcourt les règles dans l'ordre.
    Retourne l'output de la première règle dont les conditions matchent les inputs.
    Retourne un dict vide si aucune règle ne matche.
    """
    for i in range(len(rules)):
        if match_rule(rules[i].conditions, inputs):
            return rules[i].output.copy()
    return Dict[String, String]()
