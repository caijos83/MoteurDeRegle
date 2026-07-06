"""
CRUD tables de décision — POST/GET/PUT/DELETE /tables
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal
from datetime import datetime, timezone
import uuid

from ..db.terminusdb import TerminusDBClient

router = APIRouter(tags=["tables"])
db = TerminusDBClient()


def _now() -> str:
    """Retourne la date/heure UTC actuelle au format jj/mm/aaaa hh:mm."""
    return datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")


class Column(BaseModel):
    name: str
    type: Literal["number", "text", "boolean"]
    role: Literal["input", "output"]


class Rule(BaseModel):
    conditions: dict[str, str]
    output: dict[str, str]


class TableCreate(BaseModel):
    name: str
    hit_policy: Literal["FIRST", "COLLECT SUM"]
    columns: list[Column]
    rules: list[Rule] = []


class TableUpdate(BaseModel):
    name: str | None = None
    hit_policy: Literal["FIRST", "COLLECT SUM"] | None = None
    columns: list[Column] | None = None
    rules: list[Rule] | None = None


@router.get("/tables")
def list_tables():
    """Retourne la liste de toutes les tables de décision stockées."""
    return db.list_tables()


@router.get("/tables/{table_id}")
def get_table(table_id: str):
    """
    Retourne une table par son UUID. 404 si introuvable.
    Entrée : table_id — UUID valide de la table.
    """
    table = db.get_table(table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table introuvable")
    return table


@router.post("/tables", status_code=201)
def create_table(body: TableCreate):
    """
    Crée une nouvelle table de décision avec un UUID généré automatiquement.
    Entrée : body — nom, hit_policy, colonnes (et règles optionnelles).
    Retour : dict de la table créée (201).
    """
    table_id = str(uuid.uuid4())
    table = {"id": table_id, "updated_at": _now(), **body.model_dump()}
    db.save_table(table)
    return table


@router.put("/tables/{table_id}")
def update_table(table_id: str, body: TableUpdate):
    """
    Mise à jour partielle d'une table (seuls les champs fournis sont modifiés).
    Entrées : table_id — UUID, body — champs à modifier (tous optionnels).
    Retour : dict de la table mise à jour. 404 si la table n'existe pas.
    """
    existing = db.get_table(table_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Table introuvable")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updated = {**existing, **updates, "updated_at": _now()}
    db.save_table(updated)
    return updated


@router.delete("/tables/{table_id}", status_code=204)
def delete_table(table_id: str):
    """
    Supprime définitivement une table. 404 si introuvable.
    Entrée : table_id — UUID de la table à supprimer. Retour : 204 No Content.
    """
    if not db.get_table(table_id):
        raise HTTPException(status_code=404, detail="Table introuvable")
    db.delete_table(table_id)
