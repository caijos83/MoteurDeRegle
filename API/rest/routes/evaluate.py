"""
POST /tables/{id}/evaluate — évaluation d'une table avec des inputs
"""

import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db.terminusdb import TerminusDBClient
from Backend.bridge.engine_bridge import evaluate

router = APIRouter(tags=["evaluate"])
db = TerminusDBClient()


class EvaluateRequest(BaseModel):
    inputs: dict[str, str | int | float | bool]


@router.post("/tables/{table_id}/evaluate")
def evaluate_table(table_id: str, body: EvaluateRequest):
    table = db.get_table(table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table introuvable")

    # Validation des colonnes d'input
    input_cols = {c["name"] for c in table["columns"] if c["role"] == "input"}
    missing = input_cols - set(body.inputs.keys())
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Colonnes d'input manquantes : {', '.join(sorted(missing))}"
        )

    t0 = time.perf_counter()
    result = evaluate(table, {k: str(v) for k, v in body.inputs.items()})
    elapsed_ms = (time.perf_counter() - t0) * 1000

    engine = result.get("engine", "unknown")
    n_rules = len(table.get("rules", []))
    print(
        f"\033[36m[EVAL]\033[0m  table={table.get('name', table_id)!r}"
        f"  policy={table.get('hit_policy')}"
        f"  rules={n_rules}"
        f"  engine={engine}"
        f"  \033[33m{elapsed_ms:.1f}ms\033[0m",
        flush=True,
    )
    return result
