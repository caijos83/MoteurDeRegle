"""
DMN Light — primitives de correspondance règle/inputs.

Ce fichier ne contient que la logique pure de matching (aucune E/S, aucune
connaissance des hit policies). Le point d'entrée du binaire est `main.mojo`,
qui importe ce module ainsi que `hit_first` et `hit_collect_sum` — séparer
les deux évite un import circulaire (les hit policies important déjà
`evaluator` pour réutiliser `Rule`/`match_rule`).
"""

from std.collections import Dict, List


struct Rule(Copyable, Movable):
    var conditions: Dict[String, String]
    var output: Dict[String, String]

    fn __init__(out self, var conditions: Dict[String, String], var output: Dict[String, String]):
        self.conditions = conditions^
        self.output = output^


fn unquote(value: String) -> String:
    """Retire les guillemets entourant une valeur de liste JSON (`"v1"` -> `v1`)."""
    var t = String(value.strip())
    if len(t) >= 2 and t.startswith('"') and t.endswith('"'):
        return String(t.removeprefix('"').removesuffix('"'))
    return t


fn match_rule(conditions: Dict[String, String], inputs: Dict[String, String]) raises -> Bool:
    """Vérifie si toutes les conditions d'une règle matchent les inputs donnés."""
    for entry in conditions.items():
        if entry.key not in inputs:
            return False
        if not match_condition(inputs[entry.key], entry.value):
            return False
    return True


fn match_condition(value: String, expr_in: String) -> Bool:
    """
    Évalue une condition DMN sur une valeur.
    Opérateurs supportés : >, <, >=, <=, =, !=, [a..b], [a..b[, ["v1","v2"]
    """
    var expr = String(expr_in.strip())

    # Intervalle semi-ouvert [a..b[ (vérifié avant le cas générique liste)
    if expr.startswith("[") and (".." in expr) and expr.endswith("["):
        return match_interval(value, expr, False)

    # Intervalle fermé [a..b]
    if expr.startswith("[") and (".." in expr) and expr.endswith("]"):
        return match_interval(value, expr, True)

    # Appartenance à liste ["v1","v2"]
    if expr.startswith("[") and expr.endswith("]"):
        return match_list(value, expr)

    if expr.startswith(">="):
        return compare_numeric(value, String(expr.removeprefix(">=").strip()), ">=")
    if expr.startswith("<="):
        return compare_numeric(value, String(expr.removeprefix("<=").strip()), "<=")
    if expr.startswith(">"):
        return compare_numeric(value, String(expr.removeprefix(">").strip()), ">")
    if expr.startswith("<"):
        return compare_numeric(value, String(expr.removeprefix("<").strip()), "<")
    if expr.startswith("!="):
        return value != String(expr.removeprefix("!=").strip())
    if expr.startswith("="):
        return value == String(expr.removeprefix("=").strip())

    return value == expr


fn match_interval(value: String, expr: String, inclusive_end: Bool) -> Bool:
    """Évalue si une valeur numérique est dans un intervalle [a..b] ou [a..b[."""
    var body: String
    if inclusive_end:
        body = String(expr.removeprefix("[").removesuffix("]"))
    else:
        body = String(expr.removeprefix("[").removesuffix("["))
    var parts = body.split("..")
    if len(parts) != 2:
        return False
    try:
        var v = atof(value)
        var low = atof(String(parts[0].strip()))
        var high = atof(String(parts[1].strip()))
        if inclusive_end:
            return v >= low and v <= high
        return v >= low and v < high
    except:
        return False


fn match_list(value: String, expr: String) -> Bool:
    """Évalue si une valeur est dans une liste ["v1","v2"]."""
    var body = String(expr.removeprefix("[").removesuffix("]"))
    var items = body.split(",")
    for i in range(len(items)):
        if unquote(String(items[i])) == value:
            return True
    return False


fn compare_numeric(value: String, threshold: String, op: String) -> Bool:
    """Comparaison numérique."""
    try:
        var v = atof(value)
        var t = atof(threshold)
        if op == ">=":
            return v >= t
        if op == "<=":
            return v <= t
        if op == ">":
            return v > t
        if op == "<":
            return v < t
        return False
    except:
        return False
