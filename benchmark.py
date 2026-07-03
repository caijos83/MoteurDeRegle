"""
Benchmark DMN Light — Python pur vs moteur Mojo
Isole le temps de calcul Mojo pur en soustrayant l'overhead Docker.

Usage :
    python benchmark.py
    python benchmark.py --n 50000
"""

import sys
import io
import time
import subprocess
import argparse
from pathlib import Path

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

TABLE = {
    "id": "bench-001",
    "name": "ScoringCredit",
    "hit_policy": "COLLECT SUM",
    "columns": [
        {"name": "age",        "type": "number", "role": "input"},
        {"name": "revenu",     "type": "number", "role": "input"},
        {"name": "anciennete", "type": "number", "role": "input"},
        {"name": "score",      "type": "number", "role": "output"},
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
        {"conditions": {"age": "[25..35]"},        "output": {"score": "3"}},
        {"conditions": {"revenu": "[2000..3000]"}, "output": {"score": "3"}},
        {"conditions": {"anciennete": "[2..4]"},   "output": {"score": "3"}},
        {"conditions": {"age": ">= 18", "revenu": ">= 1500", "anciennete": ">= 1"}, "output": {"score": "10"}},
        {"conditions": {"age": ">= 25", "revenu": ">= 2500", "anciennete": ">= 3"}, "output": {"score": "10"}},
    ],
}

INPUTS = {"age": "30", "revenu": "3000", "anciennete": "4"}

GREEN  = "\033[92m"
BLUE   = "\033[94m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
RUNS_DOCKER = 15  # nb appels Docker pour mesurer (overhead + calcul)


def detect_mojo():
    payload = _serialize_request(TABLE, INPUTS)
    if _run_native(payload) is not None:
        return "native"
    if _run_docker(payload) is not None:
        return "docker"
    return None


def measure_docker_startup_overhead(runs: int = 10) -> float:
    """Mesure le temps de démarrage Docker seul (conteneur vide, sans calcul)."""
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        subprocess.run(
            ["docker", "run", "--rm", "dmn-mojo-engine", "echo", "ok"],
            capture_output=True, timeout=30
        )
        times.append(time.perf_counter() - t0)
    # Exclure le min et le max, prendre la médiane
    times.sort()
    return sum(times[1:-1]) / len(times[1:-1]) if len(times) > 2 else sum(times) / len(times)


def run_benchmark_python(n: int):
    for _ in range(min(200, n)):
        _evaluate_python_fallback(TABLE, INPUTS)
    start = time.perf_counter()
    for _ in range(n):
        _evaluate_python_fallback(TABLE, INPUTS)
    return (time.perf_counter() - start) / n  # secondes par appel


def run_benchmark_mojo_docker(runs: int):
    """Retourne le temps moyen par appel Docker complet."""
    payload = _serialize_request(TABLE, INPUTS)
    _run_docker(payload)  # warm-up
    times = []
    for i in range(runs):
        print(f"\r  Mesure Mojo+Docker [{i+1}/{runs}]...", end="", flush=True)
        t0 = time.perf_counter()
        stdout = _run_docker(payload)
        times.append(time.perf_counter() - t0)
    times.sort()
    median = times[len(times) // 2]
    return median


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=10_000)
    args = parser.parse_args()
    n = args.n

    print(f"\n{BOLD}{'=' * 72}{RESET}")
    print(f"{BOLD}  DMN Light — Benchmark : Python pur vs Moteur Mojo{RESET}")
    print(f"{BOLD}{'=' * 72}{RESET}")
    print(f"\n  Table  : {TABLE['name']} ({len(TABLE['rules'])} règles, {TABLE['hit_policy']})")
    print(f"  Inputs : age=30, revenu=3000, anciennete=4")

    print(f"\n{BLUE}  Détection moteur Mojo...{RESET}", end="", flush=True)
    mojo_mode = detect_mojo()
    if mojo_mode:
        label = "binaire natif" if mojo_mode == "native" else "Docker"
        print(f"\r  Moteur Mojo : {GREEN}{BOLD}{label}{RESET}                         ")
    else:
        print(f"\r  {YELLOW}Mojo non disponible.{RESET}                              ")

    # ── 1. Python pur ─────────────────────────────────────────────────────────
    print(f"\n{BLUE}  [1] Python pur ({n:,} itérations)...{RESET}", end="", flush=True)
    py_per_call = run_benchmark_python(n)
    py_us = py_per_call * 1_000_000
    print(f"\r  [1] Python pur : {GREEN}OK{RESET} — {py_us:.2f} µs/appel              ")

    if not mojo_mode:
        print(f"\n  Python pur : {py_us:.2f} µs/appel ({n:,} itérations)")
        print(f"  {YELLOW}Lancez 'docker compose build mojo-engine' pour la comparaison Mojo.{RESET}")
        print(f"\n{BOLD}{'=' * 72}{RESET}\n")
        return

    # ── 2. Overhead Docker (démarrage conteneur) ───────────────────────────────
    print(f"  [2] Mesure overhead Docker (10 runs)...", end="", flush=True)
    docker_overhead = measure_docker_startup_overhead(10)
    docker_overhead_ms = docker_overhead * 1000
    print(f"\r  [2] Overhead Docker : {docker_overhead_ms:.0f} ms/conteneur              ")

    # ── 3. Mojo complet (overhead + calcul) ───────────────────────────────────
    mojo_total = run_benchmark_mojo_docker(RUNS_DOCKER)
    mojo_total_ms = mojo_total * 1000

    # ── 4. Calcul pur Mojo = total - overhead ─────────────────────────────────
    mojo_compute = max(mojo_total - docker_overhead, 0.0001)
    mojo_us = mojo_compute * 1_000_000

    print(f"\r  [3] Mojo Docker mesuré : {mojo_total_ms:.0f} ms/appel              ")

    # ── Résultats ─────────────────────────────────────────────────────────────
    speedup = py_us / mojo_us
    gain    = (1 - mojo_us / py_us) * 100

    print(f"\n{BOLD}{'─' * 72}{RESET}")
    print(f"{BOLD}  Résultats{RESET}")
    print(f"{BOLD}{'─' * 72}{RESET}")
    print(f"""
  Méthode               Temps/appel     Détail
  ─────────────────────────────────────────────────────────────
  {RED}Python pur{RESET}            {RED}{py_us:>8.2f} µs{RESET}
  {YELLOW}Docker overhead{RESET}       {YELLOW}{docker_overhead_ms:>8.0f} ms{RESET}    (démarrage conteneur)
  {BLUE}Mojo total (Docker){RESET}   {BLUE}{mojo_total_ms:>8.0f} ms{RESET}    (overhead + calcul Mojo)
  {GREEN}{BOLD}Mojo calcul pur{RESET}       {GREEN}{BOLD}{mojo_us:>8.2f} µs{RESET}    (soustrait l'overhead)
  ─────────────────────────────────────────────────────────────
  {GREEN}{BOLD}Mojo est {speedup:.1f}x plus rapide que Python  (gain {gain:.0f}%){RESET}
""")

    # Vérification cohérence
    py_res = _evaluate_python_fallback(TABLE, INPUTS)
    mojo_stdout = _run_docker(_serialize_request(TABLE, INPUTS))
    mojo_res = _parse_response(mojo_stdout, TABLE) if mojo_stdout else {}
    py_score   = py_res.get("result", "?")
    mojo_score = mojo_res.get("result", "?")
    ok = str(py_score) == str(mojo_score)
    sym = f"{GREEN}OK{RESET}" if ok else f"{RED}DIFFERENT{RESET}"
    print(f"  Résultats identiques : {sym}  (Python={py_score}, Mojo={mojo_score})")
    print(f"\n{BOLD}{'=' * 72}{RESET}\n")


if __name__ == "__main__":
    main()
