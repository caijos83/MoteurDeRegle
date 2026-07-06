# DMNLight — Moteur de Règles DMN

> Projet académique M1 MIAGE 2025/2026 — Université Paris Cité
> Encadrant : **Gilles Pierre POIROT**

---

## Équipe

- AKLI Cylia
- BENMAMAS Melissa
- CAI Joséphine
- CAPRICORNE Séfora
- TIEN Marina

---

## Contexte du projet

**DMNLight** est un moteur de règles métier basé sur le standard **DMN** *(Decision Model and Notation, norme OMG)*. Il permet de :

- Créer des **tables de décision** structurées (colonnes typées, règles conditionnelles)
- Évaluer des données en entrée pour obtenir un **résultat automatique**
- Exposer le moteur via une **API REST**, une **API GraphQL** et un **serveur MCP** (compatible avec tout agent IA)

Le moteur d'évaluation est écrit en **Mojo** (langage système haute performance de Modular), avec un pont Python et un fallback Python pur pour le développement sans compilation.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  IHM  (Streamlit — Frontend/app.py)                     │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP REST
┌──────────────────────▼──────────────────────────────────┐
│  API REST  (FastAPI — API/rest/main.py)                  │
│  API GraphQL  (Strawberry — API/graphql/schema.py)       │
│  MCP Server  (API/mcp/server.py)                         │
└──────────┬──────────────────────────┬───────────────────┘
           │                          │
┌──────────▼──────────┐  ┌───────────▼───────────────────┐
│  Moteur Mojo        │  │  TerminusDB (Graph-Document)   │
│  Backend/engine/    │  │  docker run -p 6363:6363 ...   │
│  + Python fallback  │  │  Fallback : .data/*.json       │
└─────────────────────┘  └───────────────────────────────┘
```

---

## Stack technique

| Couche | Technologie | Fichier principal |
|---|---|---|
| Frontend | Python / Streamlit | `Frontend/app.py` |
| API REST | Python / FastAPI | `API/rest/main.py` |
| API GraphQL | Python / Strawberry | `API/graphql/schema.py` |
| MCP Server | Python / mcp SDK | `API/mcp/server.py` |
| Moteur | Mojo | `Backend/engine/evaluator.mojo` |
| Pont Python-Mojo | Python | `Backend/bridge/engine_bridge.py` |
| Matching DMN | Python | `Backend/bridge/dmn_matcher.py` |
| Base de données | TerminusDB | `API/rest/db/terminusdb.py` |

---

## Structure des dossiers

```
MoteurDeRegle/
│
├── README.md                        ← ce fichier
├── requirements.txt                 ← dépendances Python
├── render.yaml                      ← config déploiement Render (API cloud)
│
├── docs/
│   ├── ADR/                         ← 6 décisions d'architecture documentées
│   ├── exemples/                    ← tables JSON prêtes à importer
│   └── Manuel_Utilisation_DMNLight.docx
│
├── Frontend/
│   ├── app.py                       ← point d'entrée Streamlit (routing)
│   ├── components/
│   │   └── navbar.py                ← barre de navigation
│   ├── views/
│   │   ├── tables.py                ← liste des tables
│   │   ├── table_detail.py          ← détail d'une table
│   │   ├── new_table.py             ← création d'une table
│   │   ├── manage_rules.py          ← édition des règles
│   │   ├── simulate.py              ← simulation / test
│   │   ├── home.py                  ← page d'accueil
│   │   └── api_docs.py              ← documentation API intégrée
│   └── utils/
│       └── api.py                   ← client HTTP + helpers UI
│
├── API/
│   ├── rest/
│   │   ├── main.py                  ← app FastAPI (REST + GraphQL)
│   │   ├── routes/
│   │   │   ├── tables.py            ← CRUD /tables
│   │   │   └── evaluate.py          ← POST /tables/{id}/evaluate
│   │   └── db/
│   │       └── terminusdb.py        ← couche TerminusDB + fallback JSON
│   ├── graphql/
│   │   └── schema.py                ← schéma Strawberry GraphQL
│   └── mcp/
│       ├── server.py                ← serveur MCP stdio
│       └── README.md                ← config Claude Desktop
│
├── Backend/
│   ├── engine/
│   │   ├── evaluator.mojo           ← point d'entrée Mojo (stdin/stdout)
│   │   ├── hit_first.mojo           ← hit policy FIRST
│   │   ├── hit_collect_sum.mojo     ← hit policy COLLECT SUM
│   │   └── Dockerfile               ← image dmn-mojo-engine
│   └── bridge/
│       ├── engine_bridge.py         ← pont Python ↔ Mojo (3 paliers)
│       └── dmn_matcher.py           ← logique matching DMN (source unique)
│
└── tests/
    ├── unit/                        ← 58 tests unitaires pytest
    │   ├── test_engine_bridge.py
    │   ├── test_validation_types.py
    │   └── test_parser_json.py
    └── integration/                 ← 15 tests d'intégration REST + GraphQL
        ├── test_api_rest.py
        └── test_api_graphql.py
```

---

## Prérequis

- **Python 3.11+** — [python.org](https://www.python.org/downloads/)
- **Docker Desktop** *(optionnel)* — pour TerminusDB et le moteur Mojo natif

---

## Installation

```bash
# 1. Cloner le dépôt
git clone https://github.com/caijos83/MoteurDeRegle.git
cd MoteurDeRegle

# 2. Installer les dépendances Python
pip install -r requirements.txt
```

---

## Lancer l'application

### Mode développement — sans Docker (recommandé pour commencer)

Les tables sont stockées dans `.data/` (fichiers JSON locaux). Aucune configuration nécessaire.

```bash
# Terminal 1 — API REST + GraphQL
python -m uvicorn API.rest.main:app --reload --port 8000

# Terminal 2 — Interface Streamlit
python -m streamlit run Frontend/app.py
```

Ouvrir **http://localhost:8501** dans le navigateur.

### Mode complet — avec Docker (TerminusDB + moteur Mojo)

```bash
# 1. Démarrer TerminusDB (première fois)
docker run -d --name terminusdb -p 6363:6363 \
  -e TERMINUSDB_ADMIN_PASS=root terminusdb/terminusdb-server

# Relancer après un reboot :
# docker start terminusdb

# 2. Construire l'image du moteur Mojo (une seule fois)
docker build -t dmn-mojo-engine Backend/engine

# 3. Lancer l'API et le frontend
python -m uvicorn API.rest.main:app --reload --port 8000
python -m streamlit run Frontend/app.py
```

> Au premier démarrage, l'API crée automatiquement la base `dmn_light` et le schéma dans TerminusDB.

---

## Lancer les tests

```bash
# Tous les tests
python -m pytest

# Avec détail
python -m pytest -v

# Unitaires uniquement
python -m pytest tests/unit/ -v

# Intégration uniquement
python -m pytest tests/integration/ -v
```

**Résultat attendu : 73 tests, 0 échec.**

Les tests d'intégration utilisent l'API en mémoire (pas besoin que le serveur soit lancé).

---

## Compiler le moteur Mojo

> Nécessite Docker Desktop installé.

```bash
# Construire l'image (compile evaluator.mojo à l'intérieur)
docker build -t dmn-mojo-engine Backend/engine
```

Le bridge Python (`Backend/bridge/engine_bridge.py`) essaie les moteurs dans cet ordre :

1. **Binaire natif** `Backend/engine/evaluator` — le plus rapide
2. **Image Docker** `dmn-mojo-engine` — portable (Windows, macOS, Linux)
3. **Fallback Python pur** — toujours disponible, utilisé en développement et tests

---

## Fichiers clés à lire en priorité

| Objectif | Fichier |
|---|---|
| Comprendre le routing de l'IHM | `Frontend/app.py` |
| Comprendre l'évaluation DMN | `Backend/bridge/dmn_matcher.py` |
| Comprendre le pont Mojo/Python | `Backend/bridge/engine_bridge.py` |
| Voir la couche base de données | `API/rest/db/terminusdb.py` |
| Voir les endpoints REST | `API/rest/routes/tables.py` + `evaluate.py` |
| Comprendre les décisions d'archi | `docs/ADR/` |

---

## API REST

Documentation interactive Swagger : **http://localhost:8000/docs**  
GraphQL playground : **http://localhost:8000/graphql**

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/tables` | Lister toutes les tables |
| `POST` | `/api/v1/tables` | Créer une table |
| `GET` | `/api/v1/tables/{id}` | Obtenir une table |
| `PUT` | `/api/v1/tables/{id}` | Modifier une table |
| `DELETE` | `/api/v1/tables/{id}` | Supprimer une table |
| `POST` | `/api/v1/tables/{id}/evaluate` | Évaluer des inputs |
| `GET` | `/api/v1/column-types` | Types de colonnes supportés |

---

## Format JSON d'une table

```json
{
  "name": "EligibiliteCredit",
  "hit_policy": "FIRST",
  "columns": [
    {"name": "age",      "type": "number", "role": "input"},
    {"name": "revenu",   "type": "number", "role": "input"},
    {"name": "decision", "type": "text",   "role": "output"}
  ],
  "rules": [
    {"conditions": {"age": "< 18"},                        "output": {"decision": "REFUSE"}},
    {"conditions": {"age": ">= 18", "revenu": ">= 2000"}, "output": {"decision": "ACCEPTE"}},
    {"conditions": {},                                     "output": {"decision": "REFUSE"}}
  ]
}
```

Des exemples prêts à l'emploi sont disponibles dans `docs/exemples/`.

---

## Hit Policies supportées

| Policy | Comportement |
|---|---|
| `FIRST` | Retourne le résultat de la **première** règle qui correspond, s'arrête là |
| `COLLECT SUM` | **Additionne** les outputs numériques de toutes les règles qui correspondent |

## Types et opérateurs DMN

| Type | Exemples d'expressions |
|---|---|
| `number` | `> 18`   `>= 1000`   `< 0`   `= 42`   `!= 5`   `[18..65]`   `[0..100[` |
| `text` | `premium`   `= actif`   `!= inactif`   `["A","B","C"]` |
| `boolean` | `true`   `false` |

> Une condition **vide** est toujours vraie — la règle s'applique sans restriction sur cette colonne.

---

## MCP Server (intégration agents IA)

Le serveur MCP expose le moteur DMN comme outils pour tout agent compatible MCP
(Claude Desktop, VS Code Copilot, OpenAI, Google Gemini via A2A).

```bash
python API/mcp/server.py
```

Outils exposés : `dmn_list_tables`, `dmn_get_table`, `dmn_create_table`,
`dmn_add_rule`, `dmn_evaluate`, `dmn_delete_table`.

Voir `API/mcp/README.md` pour la configuration Claude Desktop.

---

## Décisions d'architecture (ADR)

| ADR | Sujet |
|---|---|
| [ADR-001](docs/ADR/ADR-001-python-mojo.md) | Choix Python + Mojo pour le moteur |
| [ADR-002](docs/ADR/ADR-002-terminusdb.md) | Choix TerminusDB comme base de données |
| [ADR-003](docs/ADR/ADR-003-mcp-server.md) | Exposition via MCP Server |
| [ADR-004](docs/ADR/ADR-004-api-dual.md) | API duale REST + GraphQL |
| [ADR-005](docs/ADR/ADR-005-mojo-docker.md) | Conteneurisation du moteur Mojo |
| [ADR-006](docs/ADR/ADR-006-docker-portabilite.md) | Docker comme couche de portabilité |

---

## Déploiement cloud

- **API** → [Render](https://render.com) (free tier) — configuration dans `render.yaml`
- **Frontend** → [Streamlit Community Cloud](https://share.streamlit.io) — fichier `Frontend/app.py`, secret `API_BASE_URL`

Voir `.streamlit/secrets.toml.example` pour la configuration des secrets.
