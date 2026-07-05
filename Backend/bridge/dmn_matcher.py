"""
Logique de matching DMN — source unique de vérité.
Importée par engine_bridge.py (fallback Python) et Frontend/views/simulate.py (affichage).

Signature : match_condition(expr, value, col_type="text")
  - expr     : expression DMN (">= 18", "[1..10]", '["A","B"]', "true", …)
  - value    : valeur à tester
  - col_type : "number" | "text" | "boolean"
"""

import json


def match_condition(expr: str, value, col_type: str = "text") -> bool:
    """
    Évalue si `value` satisfait l'expression DMN `expr`.
    Condition vide ou "—" → toujours vrai (critère ignoré, sémantique DMN).
    """
    if not expr or str(expr).strip() in ("", "—"):
        return True
    expr = str(expr).strip()
    val_str = str(value)

    # Opérateur != — traité avant les checks de type (valide pour tous les types)
    if expr.startswith("!="):
        tail = expr[2:].strip()
        if col_type == "number":
            try:
                return float(val_str) != float(tail)
            except ValueError:
                return val_str != tail
        return val_str != tail  # text et boolean : comparaison string

    if col_type == "boolean":
        return val_str.lower() == expr.lower()

    if col_type == "number":
        try:
            num = float(val_str)
            # Intervalle [a..b] ou [a..b[
            if expr.startswith("[") and ".." in expr:
                semi_open = expr.endswith("[")
                inner = expr.strip("[]")
                lo_s, hi_s = inner.split("..")
                lo = float(lo_s.strip())
                hi = float(hi_s.rstrip("[").strip())
                return lo <= num < hi if semi_open else lo <= num <= hi
            # Opérateurs (ordre important : >= avant >)
            for op, fn in [
                (">=", lambda x: num >= x), ("<=", lambda x: num <= x),
                (">",  lambda x: num >  x), ("<",  lambda x: num <  x),
                ("=",  lambda x: num == x),
            ]:
                if expr.startswith(op):
                    return fn(float(expr[len(op):].strip()))
            return num == float(expr)
        except (ValueError, IndexError):
            return False

    # text (type par défaut)
    # Liste ["v1","v2"]
    if expr.startswith("["):
        try:
            items = json.loads(expr)
            return val_str in [str(i) for i in items]
        except (json.JSONDecodeError, ValueError):
            return False
    # Opérateur = explicite
    if expr.startswith("="):
        return val_str == expr[1:].strip()
    # Égalité directe — case-sensitive (conforme DMN)
    return val_str == expr


def rule_matches(rule: dict, inputs: dict, col_types: dict | None = None) -> bool:
    """
    Vérifie si toutes les conditions d'une règle matchent les inputs.
    col_types: {nom_colonne: type} — si None, "text" est utilisé par défaut.
    Condition absente → critère ignoré (toujours vrai).
    """
    types = col_types or {}
    for col_name, expr in rule.get("conditions", {}).items():
        col_type = types.get(col_name, "text")
        value = inputs.get(col_name, "")
        if not match_condition(expr, value, col_type):
            return False
    return True
