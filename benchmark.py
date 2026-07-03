"""
Benchmark DMN Light — Python pur vs Moteur Mojo (calcul interne)

Méthodologie :
  Python  : N évaluations en boucle Python pure, temps mesuré côté Python.
  Mojo    : UN seul docker run, N évaluations en boucle Mojo native (mode
            BENCHMARK), temps mesuré PAR MOJO lui-même — aucun overhead IPC.

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


def detect_mojo():
    payload = _serialize_request(TABLE, INPUTS)
    if _run_native(payload) is not None:
        return "native"
    if _run_docker(payload) is not None:
        return "docker"
    return None


def run_benchmark_python(n: int) -> float:
    """Retourne le temps moyen par appel en secondes."""
    for _ in range(min(500, n)):
        _evaluate_python_fallback(TABLE, INPUTS)
    start = time.perf_counter()
    for _ in range(n):
        _evaluate_python_fallback(TABLE, INPUTS)
    return (time.perf_counter() - start) / n


def _build_batch_payload(n_bench: int) -> str:
    """Construit le payload avec la ligne BENCHMARK en tête."""
    base = _serialize_request(TABLE, INPUTS)
    return f"BENCHMARK\t{n_bench}\n" + base


def run_benchmark_mojo_batch(n_bench: int = 50_000) -> float | None:
    """
    Lance UN seul conteneur Docker, exécute n_bench évaluations en interne.
    Mojo mesure son propre temps (perf_counter Python via interop).
    Retourne le temps moyen par évaluation (secondes), ou None si indisponible.
    """
    payload = _build_batch_payload(n_bench)
    stdout = _run_docker(payload)
    if stdout is None:
        return None
    for line in stdout.strip().split("\n"):
        parts = line.split("\t")
        if parts[0] == "BENCH_TIME" and len(parts) >= 2:
            try:
                return float(parts[1]) / n_bench
            except ValueError:
                return None
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=50_000,
                        help="Nombre d'itérations Python (défaut: 50000)")
    parser.add_argument("--mojo-n", type=int, default=50_000,
                        help="Nombre d'itérations Mojo internes (défaut: 50000)")
    args = parser.parse_args()
    n_py   = args.n
    n_mojo = args.mojo_n

    print(f"\n{BOLD}{'=' * 72}{RESET}")
    print(f"{BOLD}  DMN Light — Benchmark : Python pur vs Moteur Mojo{RESET}")
    print(f"{BOLD}{'=' * 72}{RESET}")
    print(f"\n  Table  : {TABLE['name']} ({len(TABLE['rules'])} règles, {TABLE['hit_policy']})")
    print(f"  Inputs : age=30, revenu=3000, anciennete=4")

    print(f"\n{BLUE}  Détection moteur Mojo...{RESET}", end="", flush=True)
    mojo_mode = detect_mojo()
    if mojo_mode:
        label = "binaire natif" if mojo_mode == "native" else "Docker"
        print(f"\r  Moteur Mojo détecté : {GREEN}{BOLD}{label}{RESET}                        ")
    else:
        print(f"\r  {YELLOW}Mojo non disponible — Docker manquant ou image non construite.{RESET}")

    # ── 1. Python pur ──────────────────────────────────────────────────────────
    print(f"\n{BLUE}  [1/2] Python pur ({n_py:,} itérations)...{RESET}", end="", flush=True)
    py_per_call = run_benchmark_python(n_py)
    py_us = py_per_call * 1_000_000
    print(f"\r  [1/2] Python pur : {GREEN}OK{RESET} — {py_us:.2f} µs/appel              ")

    if not mojo_mode:
        print(f"\n  {YELLOW}Pour la comparaison Mojo, lancez :{RESET}")
        print(f"  {YELLOW}  docker compose build mojo-engine{RESET}")
        print(f"\n{BOLD}{'=' * 72}{RESET}\n")
        return

    # ── 2. Mojo (calcul interne, 1 seul docker run) ────────────────────────────
    print(f"  [2/2] Mojo interne ({n_mojo:,} itérations en 1 docker run)...", end="", flush=True)
    mojo_per_call = run_benchmark_mojo_batch(n_mojo)

    if mojo_per_call is None:
        print(f"\r  [2/2] {RED}Erreur : le moteur Mojo n'a pas retourné BENCH_TIME.{RESET}")
        print(f"         Assurez-vous que l'image Docker est à jour :")
        print(f"         docker compose build mojo-engine")
        print(f"\n{BOLD}{'=' * 72}{RESET}\n")
        return

    mojo_us = mojo_per_call * 1_000_000
    print(f"\r  [2/2] Mojo interne : {GREEN}OK{RESET} — {mojo_us:.2f} µs/appel              ")

    speedup = py_us / mojo_us
    gain    = (1 - mojo_us / py_us) * 100

    # ── Résultats ──────────────────────────────────────────────────────────────
    color = GREEN if speedup >= 1 else YELLOW
    print(f"\n{BOLD}{'─' * 72}{RESET}")
    print(f"{BOLD}  Résultats ({n_py:,} iters Python / {n_mojo:,} iters Mojo){RESET}")
    print(f"{BOLD}{'─' * 72}{RESET}")
    print(f"""
  Méthode                    Temps/appel     Note
  ──────────────────────────────────────────────────────────────────
  {RED}Python pur (interprété){RESET}    {RED}{py_us:>8.2f} µs{RESET}     boucle Python
  {GREEN}{BOLD}Mojo   (natif compilé){RESET}     {GREEN}{BOLD}{mojo_us:>8.2f} µs{RESET}     calcul interne (sans IPC)
  ──────────────────────────────────────────────────────────────────
  {color}{BOLD}Mojo est {speedup:.1f}x plus rapide que Python  (gain {gain:.0f}%){RESET}
""")

    note = (
        "Note : ce benchmark isole le calcul pur. En production, chaque appel\n"
        "  passe par le bridge Python -> Docker (~1.5 s démarrage) ou -> binaire\n"
        "  natif compilé (~µs). Voir Backend/bridge/engine_bridge.py."
    )
    print(f"  {YELLOW}{note}{RESET}")

    # ── Vérification cohérence ─────────────────────────────────────────────────
    py_res    = _evaluate_python_fallback(TABLE, INPUTS)
    mojo_out  = _run_docker(_serialize_request(TABLE, INPUTS))
    mojo_res  = _parse_response(mojo_out, TABLE) if mojo_out else {}
    py_score  = py_res.get("result", "?")
    mojo_score = mojo_res.get("result", "?")
    ok  = str(py_score) == str(mojo_score)
    sym = f"{GREEN}OK{RESET}" if ok else f"{RED}DIFFERENT{RESET}"
    print(f"\n  Résultats identiques : {sym}  (Python={py_score}, Mojo={mojo_score})")
    print(f"\n{BOLD}{'=' * 72}{RESET}\n")


if __name__ == "__main__":
    main()
