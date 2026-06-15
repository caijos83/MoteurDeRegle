# ADR-003 — Interface Agent IA : MCP Server

**Date :** 2026-04  
**Statut :** Accepté  
**Auteurs :** Équipe M1 MIAGE

## Contexte

L'encadrant demande d'intégrer un agent IA (« One Agent ») dans la version Bêta,
avec le moteur DMN exposé comme Tool. Il faut une interface standard pour connecter
n'importe quel agent IA au moteur, sans dépendance propriétaire.

## Alternatives envisagées

| Option                      | Standard     | Support agents              | Inconvénients                  |
|-----------------------------|--------------|-----------------------------|--------------------------------|
| SDK propriétaire Anthropic  | Non          | Claude uniquement           | Vendor lock-in                 |
| OpenAI Function Calling     | Non          | OpenAI uniquement           | Vendor lock-in                 |
| REST API custom             | Partiel      | Tout (via wrapper)          | Chaque agent doit être adapté  |
| **MCP (Model Context Protocol)** | Oui (Anthropic, 2024) | Claude, VS Code Copilot, et tout agent MCP-compatible | Relativement récent |

## Décision

Implémenter un **serveur MCP** (`API/mcp/server.py`) exposant le moteur DMN comme outils MCP.

## Arguments

- MCP est un standard ouvert (Apache 2.0) publié par Anthropic, adopté par VS Code, Cursor, Zed, OpenAI.
- Google a annoncé le support de MCP dans Gemini / Vertex AI.
- Un seul serveur MCP = compatible avec tout client MCP, sans réécriture.
- Déploiement local via stdio (pas de réseau, pas d'auth, Green IT).
- Le SDK Python officiel `mcp` permet d'implémenter un serveur en ~50 lignes.

## Outils MCP exposés

- `dmn_list_tables` — liste toutes les tables
- `dmn_get_table(id)` — détail d'une table
- `dmn_create_table(name, hit_policy, columns)` — créer une table
- `dmn_add_column(table_id, column)` — ajouter une colonne
- `dmn_add_rule(table_id, conditions, output)` — ajouter une règle
- `dmn_evaluate(table_id, inputs)` — évaluer des inputs
- `dmn_delete_table(id)` — supprimer une table
- `dmn_get_column_types()` — types de colonnes supportés

## Conséquences

- Le serveur MCP tourne en local (stdio), aucun port réseau exposé.
- `API/mcp/README.md` documente la configuration pour Claude Desktop et VS Code.
- Compatible avec l'architecture One Agent (LLM + Memory + Guardrails) demandée par l'encadrant.
