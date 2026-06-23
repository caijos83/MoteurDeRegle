"""
Pont Python ↔ Mojo pour le moteur d'évaluation DMN.
Appelle le binaire Mojo compilé via subprocess, avec un protocole texte en
stdin/stdout (Mojo n'a pas de module JSON dans sa stdlib — voir le docstring
de Backend/engine/main.mojo pour le format exact des champs).
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
    payload = _serialize_request(table, inputs)

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
        return _parse_response(result.stdout, table)
    except OSError:
        # Fallback Python pur : binaire absent (FileNotFoundError), ou présent
        # mais inexécutable depuis cet OS (ex. binaire Linux compilé via WSL
        # appelé depuis un interpréteur Python Windows natif -> WinError 193).
        return _evaluate_python_fallback(table, inputs)


def _serialize_request(table: dict, inputs: dict) -> str:
    """Sérialise la table + les inputs dans le protocole texte lu par main.mojo."""
    hit_policy = table.get("hit_policy", "FIRST").replace(" ", "_")
    output_cols = [c["name"] for c in table["columns"] if c["role"] == "output"]
    rules = table.get("rules", [])

    lines = [
        f"HIT_POLICY\t{hit_policy}",
        "OUTPUT_COLUMNS\t" + "\t".join(output_cols),
        f"RULES\t{len(rules)}",
    ]
    for rule in rules:
        cond_fields = "\t".join(f"{k}={v}" for k, v in rule["conditions"].items())
        out_fields = "\t".join(f"{k}={v}" for k, v in rule["output"].items())
        lines.append(f"CONDITIONS\t{cond_fields}" if cond_fields else "CONDITIONS")
        lines.append(f"OUTPUT\t{out_fields}" if out_fields else "OUTPUT")
    input_fields = "\t".join(f"{k}={v}" for k, v in inputs.items())
    lines.append(f"INPUTS\t{input_fields}" if input_fields else "INPUTS")
    return "\n".join(lines) + "\n"


def _parse_response(stdout: str, table: dict) -> dict:
    """Parse la réponse texte de main.mojo en dict {"result": ..., ...}."""
    hit_policy = table.get("hit_policy", "FIRST")
    fields = {}
    output = {}
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        tag = parts[0]
        if tag == "OUTPUT":
            for field in parts[1:]:
                k, _, v = field.partition("=")
                output[k] = v
        elif len(parts) >= 2:
            fields[tag] = parts[1]

    if hit_policy == "COLLECT SUM":
        return {
            "result": float(fields.get("TOTAL", 0.0)),
            "matched_rules": int(fields.get("MATCHED_COUNT", 0)),
            "hit_policy": hit_policy,
        }

    matched = fields.get("MATCHED") == "1"
    return {"result": output if matched else None, "hit_policy": hit_policy}


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
