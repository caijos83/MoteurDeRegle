"""
Serveur MCP (Model Context Protocol) — expose le moteur DMN Light comme outils.

Standard ouvert Anthropic/MCP (Apache 2.0).
Compatible : Claude Desktop, VS Code Copilot, Cursor, tout agent MCP.
Déploiement local via stdio — aucun réseau exposé.

Lancer : python API/mcp/server.py
"""

import sys
import json
import uuid
from pathlib import Path

# Ajoute la racine du projet au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from API.rest.db.terminusdb import TerminusDBClient
from Backend.bridge.engine_bridge import evaluate as engine_evaluate

db = TerminusDBClient()
app = Server("dmn-light-engine")


# ------------------------------------------------------------------
# Déclaration des outils MCP
# ------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """Déclare les 8 outils DMN exposés aux agents MCP (schémas JSON inclus)."""
    return [
        types.Tool(
            name="dmn_get_column_types",
            description="Retourne les types de colonnes supportés : number, text, boolean",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="dmn_list_tables",
            description="Liste toutes les tables de décision existantes",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="dmn_get_table",
            description="Retourne le détail d'une table de décision par son id",
            inputSchema={
                "type": "object",
                "properties": {"id": {"type": "string", "description": "UUID de la table"}},
                "required": ["id"],
            },
        ),
        types.Tool(
            name="dmn_create_table",
            description=(
                "Crée une nouvelle table de décision. "
                "hit_policy : 'FIRST' ou 'COLLECT SUM'. "
                "columns : liste de {name, type (number/text/boolean), role (input/output)}."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "hit_policy": {"type": "string", "enum": ["FIRST", "COLLECT SUM"]},
                    "columns": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"type": "string", "enum": ["number", "text", "boolean"]},
                                "role": {"type": "string", "enum": ["input", "output"]},
                            },
                            "required": ["name", "type", "role"],
                        },
                    },
                },
                "required": ["name", "hit_policy", "columns"],
            },
        ),
        types.Tool(
            name="dmn_add_column",
            description="Ajoute une colonne à une table existante",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_id": {"type": "string"},
                    "name": {"type": "string"},
                    "type": {"type": "string", "enum": ["number", "text", "boolean"]},
                    "role": {"type": "string", "enum": ["input", "output"]},
                },
                "required": ["table_id", "name", "type", "role"],
            },
        ),
        types.Tool(
            name="dmn_add_rule",
            description=(
                "Ajoute une règle à une table. "
                "conditions : {col: expr} — expr supporte >, <, >=, <=, =, !=, [a..b], [\"v1\",\"v2\"]. "
                "output : {col: valeur}."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "table_id": {"type": "string"},
                    "conditions": {"type": "object"},
                    "output": {"type": "object"},
                },
                "required": ["table_id", "conditions", "output"],
            },
        ),
        types.Tool(
            name="dmn_evaluate",
            description="Évalue des inputs contre une table et retourne la décision ou le score",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_id": {"type": "string"},
                    "inputs": {
                        "type": "object",
                        "description": "Valeurs d'input {nom_colonne: valeur}",
                    },
                },
                "required": ["table_id", "inputs"],
            },
        ),
        types.Tool(
            name="dmn_delete_table",
            description="Supprime une table de décision",
            inputSchema={
                "type": "object",
                "properties": {"id": {"type": "string"}},
                "required": ["id"],
            },
        ),
    ]


# ------------------------------------------------------------------
# Implémentation des outils MCP
# ------------------------------------------------------------------

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """
    Dispatch des appels d'outils MCP vers les opérations DMN correspondantes.
    Entrées : name — nom de l'outil, arguments — paramètres de l'appel.
    Retour : liste avec un TextContent JSON (résultat ou {"error": ...}).
    """

    def ok(data) -> list[types.TextContent]:
        """Sérialise data en JSON et le retourne comme réponse MCP valide."""
        return [types.TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]

    def err(msg: str) -> list[types.TextContent]:
        """Retourne une réponse MCP d'erreur avec le message donné."""
        return [types.TextContent(type="text", text=json.dumps({"error": msg}))]

    if name == "dmn_get_column_types":
        return ok({"types": ["number", "text", "boolean"]})

    if name == "dmn_list_tables":
        return ok(db.list_tables())

    if name == "dmn_get_table":
        table = db.get_table(arguments["id"])
        if not table:
            return err("Table introuvable")
        return ok(table)

    if name == "dmn_create_table":
        table = {
            "id": str(uuid.uuid4()),
            "name": arguments["name"],
            "hit_policy": arguments["hit_policy"],
            "columns": arguments["columns"],
            "rules": [],
        }
        db.save_table(table)
        return ok(table)

    if name == "dmn_add_column":
        table = db.get_table(arguments["table_id"])
        if not table:
            return err("Table introuvable")
        table["columns"].append({
            "name": arguments["name"],
            "type": arguments["type"],
            "role": arguments["role"],
        })
        db.save_table(table)
        return ok(table)

    if name == "dmn_add_rule":
        table = db.get_table(arguments["table_id"])
        if not table:
            return err("Table introuvable")
        table["rules"].append({
            "conditions": arguments["conditions"],
            "output": arguments["output"],
        })
        db.save_table(table)
        return ok(table)

    if name == "dmn_evaluate":
        table = db.get_table(arguments["table_id"])
        if not table:
            return err("Table introuvable")
        inputs = {k: str(v) for k, v in arguments["inputs"].items()}
        result = engine_evaluate(table, inputs)
        return ok(result)

    if name == "dmn_delete_table":
        if not db.get_table(arguments["id"]):
            return err("Table introuvable")
        db.delete_table(arguments["id"])
        return ok({"deleted": arguments["id"]})

    return err(f"Outil inconnu : {name}")


# ------------------------------------------------------------------
# Démarrage
# ------------------------------------------------------------------

async def main():
    """Point d'entrée asyncio — démarre le serveur MCP en mode stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
