"""
Agent IA DMN — boucle tool use avec Claude (Anthropic SDK).
Expose run_agent(messages) → {response, tool_calls}.
"""

import os
import json
import anthropic

from API.rest.db.terminusdb import TerminusDBClient
from Backend.bridge.engine_bridge import evaluate

db = TerminusDBClient()

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


SYSTEM_PROMPT = """Tu es Agent DMN, un assistant expert en tables de décision DMN (Decision Model and Notation).
Tu peux lister les tables, consulter leur schéma, évaluer des scénarios et créer des règles.
Réponds toujours en français. Sois concis et précis.
Quand tu appelles un outil, indique brièvement ce que tu fais."""

TOOLS = [
    {
        "name": "list_tables",
        "description": "Liste toutes les tables de décision disponibles avec leur politique et nombre de règles. Appelle cet outil quand l'utilisateur veut voir les tables existantes.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_table_schema",
        "description": "Obtient le schéma complet d'une table (colonnes, types, rôles, règles, politique). Appelle cet outil avant d'évaluer ou de créer une règle pour connaître la structure exacte.",
        "input_schema": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Nom ou identifiant (UUID) de la table de décision"
                }
            },
            "required": ["table_name"]
        }
    },
    {
        "name": "evaluate_table",
        "description": "Évalue des valeurs d'entrée contre une table de décision et retourne le résultat. Appelle cet outil pour simuler une décision ou calculer un score.",
        "input_schema": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Nom ou identifiant de la table de décision"
                },
                "inputs": {
                    "type": "object",
                    "description": "Valeurs d'entrée. Ex: {\"age\": 25, \"revenu\": 3000}"
                }
            },
            "required": ["table_name", "inputs"]
        }
    },
    {
        "name": "create_rule",
        "description": "Ajoute une nouvelle règle à une table de décision existante. Appelle cet outil quand l'utilisateur veut créer ou ajouter une règle métier.",
        "input_schema": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Nom ou identifiant de la table de décision"
                },
                "conditions": {
                    "type": "object",
                    "description": "Conditions de la règle. Ex: {\"age\": \"< 18\", \"revenu\": \"< 1000\"}"
                },
                "outputs": {
                    "type": "object",
                    "description": "Sorties si la règle s'applique. Ex: {\"decision\": \"REFUSE\", \"score\": \"-20\"}"
                }
            },
            "required": ["table_name", "conditions", "outputs"]
        }
    }
]


def _find_table(table_name: str) -> dict | None:
    tables = db.list_tables()
    for t in tables:
        if t.get("id") == table_name:
            return t
    for t in tables:
        if t.get("name", "").lower() == table_name.lower():
            return t
    return None


def _execute_tool(name: str, tool_input: dict) -> dict:
    if name == "list_tables":
        tables = db.list_tables()
        return {
            "tables": [
                {
                    "id": t["id"],
                    "name": t["name"],
                    "hit_policy": t["hit_policy"],
                    "nb_rules": len(t.get("rules", [])),
                    "nb_columns": len(t.get("columns", []))
                }
                for t in tables
            ]
        }

    if name == "get_table_schema":
        table = _find_table(tool_input["table_name"])
        if not table:
            return {"error": f"Table '{tool_input['table_name']}' introuvable."}
        return {
            "id": table["id"],
            "name": table["name"],
            "hit_policy": table["hit_policy"],
            "columns": table.get("columns", []),
            "rules": table.get("rules", [])
        }

    if name == "evaluate_table":
        table = _find_table(tool_input["table_name"])
        if not table:
            return {"error": f"Table '{tool_input['table_name']}' introuvable."}
        inputs = {k: str(v) for k, v in tool_input["inputs"].items()}
        return evaluate(table, inputs)

    if name == "create_rule":
        table = _find_table(tool_input["table_name"])
        if not table:
            return {"error": f"Table '{tool_input['table_name']}' introuvable."}
        new_rule = {
            "conditions": tool_input["conditions"],
            "output": tool_input["outputs"]
        }
        rules = table.get("rules", [])
        table["rules"] = rules + [new_rule]
        db.save_table(table)
        return {
            "success": True,
            "message": f"Règle ajoutée à « {table['name']} ». Total : {len(table['rules'])} règle(s).",
            "rule": new_rule
        }

    return {"error": f"Outil inconnu : {name}"}


def run_agent(messages: list[dict]) -> dict:
    """
    Lance l'agent DMN avec boucle tool use.
    Entrée  : messages = [{"role": "user"|"assistant", "content": str}, ...]
    Sortie  : {"response": str, "tool_calls": [{"name", "input", "result"}, ...]}
    """
    client = _get_client()
    tool_calls_log: list[dict] = []

    # Copie pour ne pas muter l'historique appelant
    api_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

    while True:
        response = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=api_messages
        )

        if response.stop_reason == "end_turn":
            text = next((b.text for b in response.content if b.type == "text"), "")
            return {"response": text, "tool_calls": tool_calls_log}

        if response.stop_reason == "tool_use":
            # Sérialise les blocs assistant pour le prochain tour
            assistant_content = []
            for b in response.content:
                if b.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": b.id,
                        "name": b.name,
                        "input": b.input
                    })
                elif b.type == "text":
                    assistant_content.append({"type": "text", "text": b.text})
            api_messages.append({"role": "assistant", "content": assistant_content})

            # Exécute chaque outil et collecte les résultats
            tool_results = []
            for b in response.content:
                if b.type != "tool_use":
                    continue
                result = _execute_tool(b.name, b.input)
                tool_calls_log.append({
                    "name": b.name,
                    "input": b.input,
                    "result": result
                })
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": b.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

            api_messages.append({"role": "user", "content": tool_results})

        else:
            # stop_reason inattendu (refusal, max_tokens…)
            text = next((b.text for b in response.content if b.type == "text"), "")
            return {"response": text, "tool_calls": tool_calls_log}
