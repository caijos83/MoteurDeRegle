"""
Pont Python ↔ Mojo pour le moteur d'évaluation DMN.
Appelle le binaire Mojo compilé via subprocess, avec un protocole texte en
stdin/stdout (Mojo n'a pas de module JSON dans sa stdlib — voir le docstring
de Backend/engine/main.mojo pour le format exact des champs).
"""

import json
import subprocess
from pathlib import Path

from .dmn_matcher import match_condition, rule_matches as _rule_matches_canonical

MOJO_BINARY = Path(__file__).parent.parent / "engine" / "evaluator"
MOJO_DOCKER_IMAGE = "dmn-mojo-engine"  # construite via Backend/engine/Dockerfile


def evaluate(table: dict, inputs: dict) -> dict:
    """
    Évalue des inputs contre une table de décision via le moteur Mojo.

    Trois paliers, du plus rapide au plus portable :
    1. binaire natif compilé localement (Backend/engine/evaluator)
    2. conteneur Docker (dmn-mojo-engine) — portable, résout les binaires
       Linux inexécutables sur un autre OS
    3. fallback Python pur — toujours disponible, pour le dev/tests

    Args:
        table:  table de décision (dict Python)
        inputs: valeurs d'entrée {colonne: valeur}

    Returns:
        dict avec "result" (valeur ou score) et optionnellement "matched_rules"
    """
    payload = _serialize_request(table, inputs)

    for engine_name, run_fn in [("mojo-native", _run_native), ("mojo-docker", _run_docker)]:
        stdout = run_fn(payload)
        if stdout is not None:
            result = _parse_response(stdout, table)
            result["engine"] = engine_name
            return result

    result = _evaluate_python_fallback(table, inputs)
    result["engine"] = "python-fallback"
    return result


def _run_native(payload: str) -> str | None:
    """
    Exécute le binaire compilé localement.
    Retourne None si l'OS ne peut pas l'exécuter (absent, ou ELF Linux compilé
    via WSL appelé depuis un interpréteur Python Windows natif -> WinError 193)
    — dans ce cas on essaie le palier suivant. Si le binaire tourne mais
    échoue réellement, on laisse remonter l'erreur (signal d'un vrai bug).
    """
    try:
        result = subprocess.run(
            [str(MOJO_BINARY)], input=payload, capture_output=True, text=True, timeout=5,
        )
    except OSError:
        return None
    if result.returncode != 0:
        raise RuntimeError(f"Mojo engine error: {result.stderr}")
    return result.stdout


def _run_docker(payload: str) -> str | None:
    """
    Exécute le moteur dans le conteneur `dmn-mojo-engine` (voir
    Backend/engine/Dockerfile et docker-compose.yml). Retourne None si Docker
    n'est pas installé, le daemon n'est pas démarré, ou l'image n'a pas été
    construite (`docker compose build mojo-engine`) — on bascule alors sur le
    fallback Python pur.
    """
    try:
        result = subprocess.run(
            ["docker", "run", "--rm", "-i", MOJO_DOCKER_IMAGE],
            input=payload, capture_output=True, text=True, timeout=15,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout


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
    col_types = {c["name"]: c["type"] for c in table.get("columns", [])}

    if hit_policy == "FIRST":
        for rule in rules:
            if _rule_matches(rule["conditions"], inputs, col_types):
                return {"result": rule["output"], "hit_policy": "FIRST"}
        return {"result": None, "hit_policy": "FIRST"}

    elif hit_policy == "COLLECT SUM":
        total = 0.0
        matched = []
        output_cols = [c["name"] for c in table["columns"] if c["role"] == "output"]
        for rule in rules:
            if _rule_matches(rule["conditions"], inputs, col_types):
                for col in output_cols:
                    total += float(rule["output"].get(col, 0))
                matched.append(rule)
        return {"result": total, "matched_rules": len(matched), "hit_policy": "COLLECT SUM"}

    raise ValueError(f"Hit policy non supportée : {hit_policy}")


def _rule_matches(conditions: dict, inputs: dict, col_types: dict | None = None) -> bool:
    """Délègue au module canonique dmn_matcher."""
    return _rule_matches_canonical({"conditions": conditions}, inputs, col_types)
