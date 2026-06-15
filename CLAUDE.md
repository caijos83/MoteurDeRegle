# MoteurDeRegle — DMN Light Engine

Projet académique M1 MIAGE 2025/2026, Université Paris Cité.
Encadrant : Gilles Pierre POIROT.
Équipe : AKLI Cylia, BENMAMAS Melissa, CAI Joséphine, CAPRICORNE Séfora, TIEN Marina.

## Architecture

```
IHM (Streamlit/Python) ↔ API (FastAPI REST + Strawberry GraphQL) ↔ Moteur (Mojo) ↔ TerminusDB
                                        ↕
                               MCP Server (stdio)   ← tout agent IA peut s'y connecter
```

## Stack technique

| Couche      | Techno              | Rôle                                    |
|-------------|---------------------|-----------------------------------------|
| Frontend    | Python / Streamlit  | IHM édition et exécution des tables     |
| API REST    | Python / FastAPI    | CRUD tables + évaluation                |
| API GraphQL | Python / Strawberry | Mêmes fonctions en GraphQL              |
| MCP Server  | Python / mcp SDK    | Exposition DMN comme Tool pour agents   |
| Moteur      | Mojo                | Évaluation des règles (FIRST, C+)       |
| Base        | TerminusDB          | Stockage JSON Graph-Document            |

## Structure des dossiers

```
MoteurDeRegle/
├── CLAUDE.md
├── docs/
│   └── ADR/                  # Architecture Decision Records
├── Backend/
│   ├── engine/               # Code Mojo (*.mojo)
│   │   ├── evaluator.mojo
│   │   ├── hit_first.mojo
│   │   └── hit_collect_sum.mojo
│   ├── bridge/               # Pont Python ↔ Mojo
│   │   └── engine_bridge.py
│   └── tests/                # Tests BDD/TDD du moteur
├── API/
│   ├── rest/                 # FastAPI
│   │   ├── main.py
│   │   ├── routes/
│   │   └── db/
│   ├── graphql/              # Strawberry GraphQL
│   │   └── schema.py
│   └── mcp/                  # MCP Server (standard Anthropic/MCP)
│       ├── server.py
│       └── tools/
└── Frontend/
    ├── app.py                # Streamlit
    └── components/
```

## MCP — interface standard

Le serveur MCP (`API/mcp/server.py`) expose le moteur DMN comme outils MCP.
Tout agent compatible MCP (Claude Desktop, VS Code Copilot, OpenAI, Google Gemini via A2A)
peut s'y connecter **sans modification** via stdio ou HTTP local.

Outils MCP exposés :
- `dmn_list_tables` — lister les tables
- `dmn_get_table` — obtenir une table par id
- `dmn_create_table` — créer une table (nom, hit_policy, colonnes)
- `dmn_add_column` — ajouter une colonne à une table
- `dmn_add_rule` — ajouter une règle
- `dmn_evaluate` — évaluer des inputs contre une table
- `dmn_delete_table` — supprimer une table
- `dmn_get_column_types` — obtenir les types supportés

Lancer le serveur MCP : `python API/mcp/server.py`
Config Claude Desktop : voir `API/mcp/README.md`

## Hit Policies supportées

| Policy      | Comportement                                          |
|-------------|-------------------------------------------------------|
| FIRST       | Retourne le résultat de la 1re règle qui matche       |
| COLLECT SUM | Somme les outputs de toutes les règles qui matchent   |

## Types de colonnes supportés

- `number` — comparaisons numériques : `>`, `<`, `=`, `!=`, intervalle `[a..b]`
- `text` — égalité, appartenance à liste `["a","b"]`
- `boolean` — `true` / `false`

## Opérateurs

`>`, `<`, `>=`, `<=`, `=`, `!=`, `[a..b]` (intervalle fermé), `[a..b[` (semi-ouvert), `["v1","v2"]` (liste)

## Format JSON d'une table de décision

```json
{
  "id": "uuid",
  "name": "EligibiliteCredit",
  "hit_policy": "FIRST",
  "columns": [
    {"name": "age", "type": "number", "role": "input"},
    {"name": "revenu", "type": "number", "role": "input"},
    {"name": "decision", "type": "text", "role": "output"}
  ],
  "rules": [
    {"conditions": {"age": ">= 18", "revenu": ">= 2000"}, "output": {"decision": "ACCEPTE"}},
    {"conditions": {"age": "< 18"}, "output": {"decision": "REFUSE"}}
  ]
}
```

## ADR

Les décisions d'architecture sont documentées dans `docs/ADR/`.
Format : contexte → alternatives → décision → arguments.
Chaque ADR est une fiche Markdown à côté du code.

## Tests

- **BDD** : scénarios Gherkin dans `tests/features/` (pytest-bdd)
- **TDD** : tests unitaires pytest dans `tests/unit/`
- Lancer : `pytest`

## Déploiement local

Aucune dépendance cloud. Tout tourne en local :
```bash
# TerminusDB
docker run -p 6363:6363 terminusdb/terminusdb-server

# API + MCP
uvicorn API.rest.main:app --port 8000
python API/mcp/server.py

# Frontend
streamlit run Frontend/app.py
```

## Commandes utiles

```bash
# Installer les dépendances
pip install -r requirements.txt

# Tests
pytest

# Lancer l'API REST
uvicorn API.rest.main:app --reload

# Lancer le serveur MCP
python API/mcp/server.py

# Lancer l'IHM
streamlit run Frontend/app.py
```