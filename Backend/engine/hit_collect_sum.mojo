"""
Hit Policy COLLECT SUM — somme les outputs numériques de toutes les règles qui matchent.
"""

from collections import Dict, List
from .evaluator import match_rule


fn evaluate_collect_sum(
    rules: List[Dict[String, String]],
    inputs: Dict[String, String],
    output_column: String
) -> Float64:
    """
    Parcourt toutes les règles.
    Somme les valeurs numériques de output_column pour chaque règle qui matche.
    """
    var total: Float64 = 0.0
    for rule in rules:
        let conditions = rule["conditions"]
        if match_rule(conditions, inputs):
            let output = rule["output"]
            if output_column in output:
                # TODO: convertir output[output_column] en Float64
                total += 0.0
    return total
