"""
Couche d'accès TerminusDB.
Encapsule toutes les opérations sur la base Graph-Document.
Fallback en mémoire pour les tests unitaires.
"""

import os
import re
import json
import datetime
from pathlib import Path

# Refuse tout table_id qui n'est pas un UUID v4 valide — prévient la traversée de chemin
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)

TERMINUS_URL = os.getenv("TERMINUS_URL", "http://localhost:6363")
TERMINUS_USER = os.getenv("TERMINUS_USER", "admin")
TERMINUS_PASS = os.getenv("TERMINUS_PASS", "root")
TERMINUS_DB = os.getenv("TERMINUS_DB", "dmn_light")

# Fallback JSON sur disque si TerminusDB non disponible (dev/tests)
_FALLBACK_DIR = Path(__file__).parent.parent.parent.parent / ".data"


class TerminusDBClient:
    def __init__(self):
        self._client = None
        self._use_fallback = False
        self._connect()

    def _connect(self):
        try:
            from terminusdb_client import Client
            self._client = Client(TERMINUS_URL)
            self._client.connect(user=TERMINUS_USER, password=TERMINUS_PASS, db=TERMINUS_DB)
        except Exception:
            self._use_fallback = True
            _FALLBACK_DIR.mkdir(exist_ok=True)

    # ------------------------------------------------------------------
    def _load_with_timestamps(self, path: Path) -> dict:
        data = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
        if "created_at" not in data or "updated_at" not in data:
            # Tables créées avant l'ajout des timestamps : on retombe sur la
            # date de modification du fichier plutôt que de laisser le champ vide.
            mtime = datetime.datetime.fromtimestamp(
                path.stat().st_mtime, tz=datetime.timezone.utc
            ).isoformat()
            data.setdefault("created_at", mtime)
            data.setdefault("updated_at", mtime)
        return data

    def list_tables(self) -> list[dict]:
        if self._use_fallback:
            tables = []
            for f in _FALLBACK_DIR.glob("*.json"):
                try:
                    tables.append(self._load_with_timestamps(f))
                except json.JSONDecodeError:
                    continue
            return tables
        # TODO: requête TerminusDB WOQL pour lister les documents Table
        return []

    def get_table(self, table_id: str) -> dict | None:
        if not _UUID_RE.match(table_id):
            return None
        if self._use_fallback:
            path = _FALLBACK_DIR / f"{table_id}.json"
            if path.exists():
                return self._load_with_timestamps(path)
            return None
        # TODO: requête WOQL get document by id
        return None

    def save_table(self, table: dict):
        table_id = table.get("id", "")
        if not _UUID_RE.match(table_id):
            return
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        table.setdefault("created_at", now)
        table["updated_at"] = now
        if self._use_fallback:
            path = _FALLBACK_DIR / f"{table_id}.json"
            path.write_text(json.dumps(table, ensure_ascii=False, indent=2), encoding="utf-8")
            return
        # TODO: upsert document TerminusDB
        pass

    def delete_table(self, table_id: str):
        if not _UUID_RE.match(table_id):
            return
        if self._use_fallback:
            path = _FALLBACK_DIR / f"{table_id}.json"
            if path.exists():
                path.unlink()
            return
        # TODO: delete document TerminusDB
        pass
