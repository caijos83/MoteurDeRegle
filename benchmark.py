"""
Benchmark DMN Light — Python pur vs moteur Mojo
Mesure le temps d'évaluation sur N itérations pour comparer les deux moteurs.

Usage :
    python benchmark.py              # 10 000 itérations
    python benchmark.py --n 50000   # personnalisé
"""

import sys
import io
import time
import subprocess
import argparse
from pathlib import Path

# Force UTF-8 sur la console Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))

from Backend.bridge.engine_bridge import (
    _evaluate_python_fallback,
    _run_native,
    _run_docker,
    _serialize_request,
    _parse_response,
)

# ── Table de décision de test (scoring crédit, 20 règles) ─────────────────────
TABLE = {
    "id": "bench-001",
    "name": "ScoringCredit",
    "hit_policy": "COLLECT SUM",
    "columns": [
        {"name": "age",     "type": "number", "role": "input"},
        {"name": "revenu",  "type": "number", "role": "input"},
        {"name": "anciennete", "type": "number", "role": "input"},
        {"name": "score",   "type": "number", "role": "output"},
    ],
    "rules": [
        {"conditions": {"age": ">= 18"},       "output": {"score": "10"}},
        {"conditions": {"age": ">= 25"},       "output": {"score": "5"}},
        {"conditions": {"age": ">= 35"},       "output": {"score": "5"}},
        {"conditions": {"revenu": ">= 1500"},  "output": {"score": "15"}},
        {"conditions": {"revenu": ">= 2500"},  "output": {"score": "10"}},
        {"conditions": {"revenu": ">= 4000"},  "output": {"score": "10"}},
        {"conditions": {"anciennete": ">= 1"}, "output": {"score": "10"}},
        {"conditions": {"anciennete": ">= 3"}, "output": {"score": "10"}},
        {"conditions": {"anciennete": ">= 5"}, "output": {"score": "5"}},
        {"conditions": {"anciennete": ">= 10"},"output": {"score": "5"}},
        {"conditions": {"age": ">= 18", "revenu": ">= 2500"}, "output": {"score": "5"}},
        {"conditions": {"age": ">= 25", "revenu": ">= 2500"}, "output": {"score": "5"}},
        {"conditions": {"age": ">= 35", "revenu": ">= 4000"}, "output": {"score": "5"}},
        {"conditions": {"revenu": ">= 2500", "anciennete": ">= 3"}, "output": {"score": "5"}},
        {"conditions": {"revenu": ">= 4000", "anciennete": ">= 5"}, "output": {"score": "5"}},
        {"conditions": {"age": "[25..35]"},    "output": {"score": "3"}},
        {"conditions": {"revenu": "[2000..3000]"}, "output": {"score": "3"}},
        {"conditions": {"anciennete": "[2..4]"}, "output": {"score": "3"}},
        {"conditions": {"age": ">= 18", "revenu": ">= 1500", "anciennete": ">= 1"}, "output": {"score": "10"}},
        {"conditions": {"age": ">= 25", "revenu": ">= 2500", "anciennete": ">= 3"}, "output": {"score": "10"}},
    ],
}

INPUTS = {"age": "30", "revenu": "3000", "anciennete": "4"}

# ── Couleurs terminal ──────────────────────────────────────────────────────────
GREEN  = "\033[92m"
BLUE   = "\033[94m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def detect_mojo():
    """Détecte quel moteur Mojo est disponible."""
    payload = _serialize_request(TABLE, INPUTS)
    if _run_native(payload) is not None:
        return "native"
    if _run_docker(payload) is not None:
        return "docker"
    return None


def run_benchmark_python(n: int) -> tuple[float, dict]:
    """Benchmark Python pur : n évaluations complètes."""
    # Warm-up
    for _ in range(min(100, n)):
        _evaluate_python_fallback(TABLE, INPUTS)

    start = time.perf_counter()
    result = None
    for _ in range(n):
        result = _evaluate_python_fallback(TABLE, INPUTS)
    elapsed = time.perf_counter() - start
    return elapsed, result


def run_benchmark_mojo(n: int, mode: str) -> tuple[float, dict]:
    """Benchmark Mojo (natif ou Docker) : n évaluations complètes."""
    run_fn = _run_native if mode == "native" else _run_docker
    payload = _serialize_request(TABLE, INPUTS)

    # Warm-up (particulièrement important pour Docker : premier appel lent)
    warmup = min(20, n)
    for _ in range(warmup):
        run_fn(payload)

    start = time.perf_counter()
    result = None
    for _ in range(n):
        stdout = run_fn(payload)
        result = _parse_response(stdout, TABLE)
    elapsed = time.perf_counter() - start
    return elapsed, result


def print_bar(label: str, elapsed: float, n: int, color: str, ref_ms: float = None):
    """Affiche une ligne de résultat avec barre visuelle."""
    total_ms  = elapsed * 1000
    per_call_us = (elapsed / n) * 1_000_000
    bar_len   = int(total_ms / ref_ms * 30) if ref_ms else 30
    bar_len   = max(1, min(bar_len, 60))
    bar       = "█" * bar_len
    print(f"  {color}{BOLD}{label:<22}{RESET}  {color}{bar:<62}{RESET}  "
          f"{total_ms:8.1f} ms total  |  {per_call_us:6.2f} µs/appel")


def main():
    parser = argparse.ArgumentParser(description="Benchmark DMN Light : Python vs Mojo")
    parser.add_argument("--n", type=int, default=10_000,
                        help="Nombre d'itérations (défaut : 10 000)")
    args = parser.parse_args()
    n = args.n

    print(f"\n{BOLD}{'═' * 80}{RESET}")
    print(f"{BOLD}  DMN Light — Benchmark : Python pur vs Moteur Mojo{RESET}")
    print(f"{BOLD}{'═' * 80}{RESET}")
    print(f"\n  Table    : {TABLE['name']} ({len(TABLE['rules'])} règles, hit policy {TABLE['hit_policy']})")
    print(f"  Inputs   : age=30, revenu=3000, anciennete=4")
    print(f"  Itérations : {n:,}")

    # Détection Mojo
    print(f"\n{BLUE}  Détection du moteur Mojo...{RESET}", end="", flush=True)
    mojo_mode = detect_mojo()
    if mojo_mode:
        label = "binaire natif" if mojo_mode == "native" else "Docker"
        print(f"\r  Moteur Mojo détecté : {GREEN}{BOLD}{label}{RESET}            ")
    else:
        print(f"\r  {YELLOW}Moteur Mojo non disponible — comparaison impossible.{RESET}")
        print(f"  {YELLOW}Conseil : lancez 'docker compose build mojo-engine' puis réessayez.{RESET}")
        print(f"\n  Lancement du benchmark Python seul...\n")

    # Benchmark Python
    print(f"\n{BLUE}  [1/2] Benchmark Python pur...{RESET}", end="", flush=True)
    py_time, py_result = run_benchmark_python(n)
    print(f"\r  [1/2] Benchmark Python pur : {GREEN}OK{RESET}                     ")

    # Benchmark Mojo (si disponible)
    mojo_time = None
    mojo_result = None
    if mojo_mode:
        mode_label = "natif" if mojo_mode == "native" else "Docker"
        print(f"  [2/2] Benchmark Mojo ({mode_label})...", end="", flush=True)
        mojo_time, mojo_result = run_benchmark_mojo(n, mojo_mode)
        print(f"\r  [2/2] Benchmark Mojo ({mode_label}) : {GREEN}OK{RESET}                     ")

    # Résultats
    print(f"\n{BOLD}{'─' * 80}{RESET}")
    print(f"{BOLD}  Résultats ({n:,} évaluations){RESET}")
    print(f"{BOLD}{'─' * 80}{RESET}\n")

    ref = py_time * 1000
    print_bar("Python pur", py_time, n, RED, ref)

    if mojo_time is not None:
        print_bar(f"Mojo ({mojo_mode})", mojo_time, n, GREEN, ref)
        speedup = py_time / mojo_time
        gain_pct = (1 - mojo_time / py_time) * 100

        print(f"\n  {BOLD}Résultat :{RESET}")
        print(f"  ┌─────────────────────────────────────────────┐")
        print(f"  │  Mojo est {GREEN}{BOLD}{speedup:.1f}×{RESET} plus rapide que Python pur  │")
        print(f"  │  Gain de performance : {GREEN}{BOLD}{gain_pct:.0f}%{RESET}                  │")
        print(f"  └─────────────────────────────────────────────┘")

        # Vérification cohérence des résultats
        if py_result and mojo_result:
            py_score  = py_result.get("result", "?")
            mojo_score = mojo_result.get("result", "?")
            match = "✓" if str(py_score) == str(mojo_score) else "✗"
            print(f"\n  Cohérence résultats : {match}  (Python={py_score}, Mojo={mojo_score})")
    else:
        py_per_call = (py_time / n) * 1_000_000
        print(f"\n  Python pur : {py_time*1000:.1f} ms total  ({py_per_call:.2f} µs/appel)")
        print(f"\n  {YELLOW}Pour comparer avec Mojo :{RESET}")
        print(f"    docker compose build mojo-engine")
        print(f"    python benchmark.py")

    print(f"\n{BOLD}{'═' * 80}{RESET}\n")


if __name__ == "__main__":
    main()
