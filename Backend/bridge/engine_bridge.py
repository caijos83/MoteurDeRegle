"""
Pont Python ↔ Mojo pour le moteur d'évaluation DMN.
Appelle le binaire Mojo compilé via subprocess avec JSON en stdin/stdout.
"""

import json
import subprocess
from pathlib import Path

MOJO_BINARY = Path(__file__).parent.parent / "engine" / "evaluator"


def evaluate(table: dict, inputs: dict) -> dict:
    """
    Évalue des inputs contre une table de décision via le moteur Mojo.

    Args:
        table:  table de décision (dict Python)
        inputs: valeurs d'entrée {colonne: valeur}

    Returns:
        dict avec "result" (valeur ou score) et optionnellement "matched_rules"
    """
    payload = json.dumps({"table": table, "inputs": inputs})

    try:
        result = subprocess.run(
            [str(MOJO_BINARY)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Mojo engine error: {result.stderr}")
        return json.loads(result.stdout)
    except FileNotFoundError:
        # Fallback Python pur pour le développement avant compilation Mojo
        return _evaluate_python_fallback(table, inputs)


def _evaluate_python_fallback(table: dict, inputs: dict) -> dict:
    """
    Implémentation Python pure du moteur — utilisée en dev / tests
    avant que le binaire Mojo soit compilé.
    """
    hit_policy = table.get("hit_policy", "FIRST")
    rules = table.get("rules", [])

    if hit_policy == "FIRST":
        for rule in rules:
            if _rule_matches(rule["conditions"], inputs):
                return {"result": rule["output"], "hit_policy": "FIRST"}
        return {"result": None, "hit_policy": "FIRST"}

    elif hit_policy == "COLLECT SUM":
        total = 0.0
        matched = []
        output_cols = [c["name"] for c in table["columns"] if c["role"] == "output"]
        for rule in rules:
            if _rule_matches(rule["conditions"], inputs):
                for col in output_cols:
                    total += float(rule["output"].get(col, 0))
                matched.append(rule)
        return {"result": total, "matched_rules": len(matched), "hit_policy": "COLLECT SUM"}

    raise ValueError(f"Hit policy non supportée : {hit_policy}")


def _rule_matches(conditions: dict, inputs: dict) -> bool:
    """Vérifie si toutes les conditions d'une règle matchent les inputs."""
    for col, expr in conditions.items():
        if col not in inputs:
            return False
        if not _match_condition(str(inputs[col]), str(expr)):
            return False
    return True


def _match_condition(value: str, expr: str) -> bool:
    """Évalue une expression DMN sur une valeur."""
    expr = expr.strip()

    # Intervalle [a..b]
    if expr.startswith("[") and ".." in expr:
        parts = expr.strip("[]").split("..")
        try:
            v = float(value)
            low, high = float(parts[0]), float(parts[1].rstrip("["))
            if expr.endswith("["):
                return low <= v < high
            return low <= v <= high
        except ValueError:
            return False

    # Liste ["v1","v2"]
    if expr.startswith("[") and expr.endswith("]"):
        try:
            items = json.loads(expr)
            return value in [str(i) for i in items]
        except json.JSONDecodeError:
            return False

    # Comparaisons
    try:
        v = float(value)
        if expr.startswith(">="):
            return v >= float(expr[2:].strip())
        if expr.startswith("<="):
            return v <= float(expr[2:].strip())
        if expr.startswith(">"):
            return v > float(expr[1:].strip())
        if expr.startswith("<"):
            return v < float(expr[1:].strip())
    except ValueError:
        pass

    if expr.startswith("!="):
        return value != expr[2:].strip()
    if expr.startswith("="):
        return value == expr[1:].strip()

    return value == expr
