"""
Couche d'accès TerminusDB.
Encapsule toutes les opérations sur la base Graph-Document.
Fallback JSON sur disque si TerminusDB est non disponible (dev / tests).
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

TERMINUS_URL  = os.getenv("TERMINUS_URL",  "http://localhost:6363")
TERMINUS_USER = os.getenv("TERMINUS_USER", "admin")
TERMINUS_PASS = os.getenv("TERMINUS_PASS", "root")
TERMINUS_DB   = os.getenv("TERMINUS_DB",   "dmn_light")

# Fallback JSON sur disque si TerminusDB non disponible (dev/tests)
_FALLBACK_DIR = Path(__file__).parent.parent.parent.parent / ".data"

# Schéma TerminusDB pour le type DecisionTable.
# "sys:JSON" permet de stocker columns et rules comme du JSON arbitraire.
_SCHEMA_DOC = {
    "@type": "Class",
    "@id": "DecisionTable",
    "name": "xsd:string",
    "hit_policy": "xsd:string",
    "columns": "sys:JSON",
    "rules": "sys:JSON",
    "created_at": {"@type": "Optional", "@class": "xsd:string"},
    "updated_at": {"@type": "Optional", "@class": "xsd:string"},
}


class TerminusDBClient:
    def __init__(self):
        self._client = None
        self._use_fallback = False
        self._connect()

    # ── Connexion & initialisation ────────────────────────────────────────────

    def _connect(self):
        try:
            from terminusdb_client import Client
            self._client = Client(TERMINUS_URL)
            try:
                # Connexion directe à la base cible (cas nominal)
                self._client.connect(
                    user=TERMINUS_USER, password=TERMINUS_PASS, db=TERMINUS_DB
                )
            except Exception:
                # La base n'existe pas encore — connexion sans DB puis création
                self._client.connect(user=TERMINUS_USER, password=TERMINUS_PASS)
                self._client.create_database(
                    TERMINUS_DB, label="DMN Light", include_schema=True
                )
            self._ensure_schema()
        except Exception:
            self._use_fallback = True
            _FALLBACK_DIR.mkdir(exist_ok=True)

    def _ensure_schema(self):
        """Insère le type DecisionTable dans le schéma si absent."""
        try:
            self._client.get_document("DecisionTable", graph_type="schema")
        except Exception:
            self._client.insert_document(_SCHEMA_DOC, graph_type="schema")

    # ── Conversion TerminusDB ↔ dict interne ──────────────────────────────────

    @staticmethod
    def _to_terminus_doc(table: dict) -> dict:
        doc = {
            "@type": "DecisionTable",
            "@id": f"DecisionTable/{table['id']}",
            "name": table["name"],
            "hit_policy": table["hit_policy"],
            "columns": table.get("columns", []),
            "rules": table.get("rules", []),
        }
        if "created_at" in table:
            doc["created_at"] = table["created_at"]
        if "updated_at" in table:
            doc["updated_at"] = table["updated_at"]
        return doc

    @staticmethod
    def _from_terminus_doc(doc: dict) -> dict:
        raw_id = doc.get("@id", "")
        table_id = raw_id.removeprefix("DecisionTable/")
        return {
            "id": table_id,
            "name": doc.get("name", ""),
            "hit_policy": doc.get("hit_policy", "FIRST"),
            "columns": doc.get("columns", []),
            "rules": doc.get("rules", []),
            "created_at": doc.get("created_at"),
            "updated_at": doc.get("updated_at"),
        }

    # ── Fallback helpers ───────────────────────────────────────────────────────

    def _load_with_timestamps(self, path: Path) -> dict:
        data = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
        if "created_at" not in data or "updated_at" not in data:
            mtime = datetime.datetime.fromtimestamp(
                path.stat().st_mtime, tz=datetime.timezone.utc
            ).isoformat()
            data.setdefault("created_at", mtime)
            data.setdefault("updated_at", mtime)
        return data

    # ── API publique ───────────────────────────────────────────────────────────

    def list_tables(self) -> list[dict]:
        if self._use_fallback:
            tables = []
            for f in _FALLBACK_DIR.glob("*.json"):
                try:
                    tables.append(self._load_with_timestamps(f))
                except json.JSONDecodeError:
                    continue
            return tables
        docs = list(self._client.query_document({"@type": "DecisionTable"}))
        return [self._from_terminus_doc(d) for d in docs]

    def get_table(self, table_id: str) -> dict | None:
        if not _UUID_RE.match(table_id):
            return None
        if self._use_fallback:
            path = _FALLBACK_DIR / f"{table_id}.json"
            if path.exists():
                return self._load_with_timestamps(path)
            return None
        try:
            doc = self._client.get_document(f"DecisionTable/{table_id}")
            return self._from_terminus_doc(doc)
        except Exception:
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
            path.write_text(
                json.dumps(table, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return
        doc = self._to_terminus_doc(table)
        # Upsert : replace si le document existe déjà, insert sinon
        try:
            self._client.get_document(f"DecisionTable/{table_id}")
            self._client.replace_document(doc)
        except Exception:
            self._client.insert_document(doc)

    def delete_table(self, table_id: str):
        if not _UUID_RE.match(table_id):
            return
        if self._use_fallback:
            path = _FALLBACK_DIR / f"{table_id}.json"
            if path.exists():
                path.unlink()
            return
        self._client.delete_document(f"DecisionTable/{table_id}")
