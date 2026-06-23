"""
Hit Policy COLLECT SUM — somme les outputs numériques de toutes les règles qui matchent.
"""

from std.collections import Dict, List

from evaluator import Rule, match_rule


fn evaluate_collect_sum(
    rules: List[Rule],
    inputs: Dict[String, String],
    output_columns: List[String],
) raises -> Tuple[Float64, Int]:
    """
    Parcourt toutes les règles.
    Pour chaque règle qui matche, additionne les valeurs des colonnes de sortie.
    Retourne (total, nombre de règles matchées).
    """
    var total: Float64 = 0.0
    var matched_count: Int = 0
    for i in range(len(rules)):
        if match_rule(rules[i].conditions, inputs):
            matched_count += 1
            for j in range(len(output_columns)):
                var col = output_columns[j]
                if col in rules[i].output:
                    total += atof(rules[i].output[col])
    return (total, matched_count)
