# Manuel d'installation — DMN Light Engine

Projet M1 MIAGE 2025/2026, Université Paris Cité.

Ce manuel décrit l'installation complète de l'application sur un poste de
développement (Windows, macOS ou Linux).

## 1. Prérequis

| Outil           | Version minimale | Rôle                                      |
|-----------------|-------------------|--------------------------------------------|
| Python          | 3.10              | API, IHM, pont vers le moteur Mojo         |
| Docker Desktop  | récent            | TerminusDB + moteur Mojo conteneurisé      |
| Git              | —                 | récupération du code source                |

Le moteur Mojo n'a pas besoin d'être installé en natif : il est packagé dans
une image Docker (voir §4). Installer Mojo en local (WSL2 + pixi) est
seulement utile pour les membres de l'équipe qui modifient le code `.mojo`
lui-même (voir §6, optionnel).

## 2. Récupérer le projet

```bash
git clone https://github.com/caijos83/MoteurDeRegle.git
cd MoteurDeRegle
```

## 3. Installer les dépendances Python

```bash
pip install -r requirements.txt
```

Dépendances principales : `fastapi`, `uvicorn`, `strawberry-graphql` (GraphQL),
`mcp` (serveur MCP), `terminusdb-client`, `streamlit`, `pytest`.

## 4. Configurer l'environnement

Copier le fichier d'exemple et l'adapter si besoin (ports, URL de l'API) :

```bash
cp .env.example .env
```

Variables disponibles dans `.env` :

| Variable        | Défaut                              | Description                          |
|-----------------|--------------------------------------|----------------------------------------|
| `API_BASE_URL`  | `http://localhost:8000/api/v1`       | URL utilisée par l'IHM pour appeler l'API |
| `API_PORT`      | `8000`                               | Port de l'API REST/GraphQL             |
| `UI_PORT`       | `8501`                               | Port de l'IHM Streamlit                |
| `BROWSER_PATH`  | détection automatique                | Navigateur ouvert par `run.py`         |

## 5. Démarrer TerminusDB et le moteur Mojo (Docker)

Démarrer Docker Desktop, puis depuis la racine du projet :

```bash
# Construire l'image du moteur Mojo (une fois, ou après modification du code .mojo)
docker compose build mojo-engine

# Démarrer la base de données TerminusDB (service persistant)
docker compose up -d terminusdb
```

> Si TerminusDB n'est pas joignable, l'application bascule automatiquement
> sur un stockage de secours en fichiers JSON dans `.data/` — pratique pour
> développer sans Docker, mais à éviter pour la recette finale.

Le service `mojo-engine` n'est **pas** un serveur réseau : c'est un outil
ponctuel (`docker run --rm -i dmn-mojo-engine`) invoqué automatiquement par
l'API à chaque évaluation. Il n'apparaît donc pas dans `docker compose up`
(profil `build-only` dans `docker-compose.yml`).

## 6. Lancer l'application

```bash
python run.py
```

Ce script démarre dans l'ordre :
1. l'API REST + GraphQL (`uvicorn API.rest.main:app`) sur le port `8000`,
2. l'IHM Streamlit (`streamlit run Frontend/app.py`) sur le port `8501`,
3. ouvre automatiquement un navigateur sur `http://localhost:8501`.

`Ctrl+C` dans le terminal arrête les deux processus proprement.

## 7. Vérifier l'installation

| Composant        | URL                                      |
|-------------------|-------------------------------------------|
| IHM               | http://localhost:8501                    |
| API REST (docs)  | http://localhost:8000/docs               |
| API GraphQL       | http://localhost:8000/graphql (GraphiQL) |
| Healthcheck API   | http://localhost:8000/health             |

Le moteur DMN lui-même est testé en exécutant la suite de tests :

```bash
pytest
```

## 8. (Optionnel) Modifier le moteur Mojo en local avec WSL

Réservé aux personnes qui modifient les fichiers `Backend/engine/*.mojo`.
Le code utilise la version **0.26.2.0** de Mojo (épinglée dans
`Backend/engine/Dockerfile` — les versions ≥ 1.0 ont supprimé le mot-clé `fn`
et cassent la compilation).

```bash
wsl --install                       # si WSL2 n'est pas déjà installé
wsl
curl -fsSL https://pixi.sh/install.sh | sh
pixi init mojo-dev -c https://conda.modular.com/max/ -c conda-forge
cd mojo-dev && pixi add mojo==0.26.2.0
pixi run mojo build Backend/engine/main.mojo -o Backend/engine/evaluator
```

Le binaire généré est un ELF Linux : il fonctionne tel quel sous WSL/Linux,
mais pas depuis un interpréteur Python Windows natif (erreur `WinError 193`).
Le pont Python (`Backend/bridge/engine_bridge.py`) gère cela automatiquement :
binaire natif → conteneur Docker → fallback Python pur (voir
`docs/ADR/ADR-005-mojo-docker.md`).

Après modification du code Mojo, reconstruire l'image Docker pour que les
autres membres de l'équipe (et l'API) voient le changement :

```bash
docker compose build mojo-engine
```

## 9. Serveur MCP (optionnel — intégration agent IA)

Pour connecter le moteur DMN à un agent compatible MCP (Claude Desktop, VS
Code Copilot, etc.) :

```bash
python API/mcp/server.py
```

Voir `API/mcp/README.md` pour la configuration côté client (Claude Desktop,
VS Code).

## 10. Dépannage

| Symptôme                                            | Cause probable                                  | Solution                                                  |
|------------------------------------------------------|--------------------------------------------------|--------------------------------------------------------------|
| `docker: error during connect`                       | Docker Desktop n'est pas démarré                | Lancer Docker Desktop, attendre l'icône "running"          |
| Évaluation toujours via le fallback Python            | Image `dmn-mojo-engine` non construite          | `docker compose build mojo-engine`                          |
| Port 8000 ou 8501 déjà utilisé                       | Une autre instance tourne déjà                  | Changer `API_PORT`/`UI_PORT` dans `.env`, ou fermer l'autre process |
| IHM affiche "Connexion à l'API en cours…" en boucle   | L'API n'est pas démarrée ou a planté             | Vérifier le terminal de `run.py`, relancer                  |
| `WinError 193` lors de l'évaluation                   | Tentative d'exécuter le binaire Mojo natif (ELF Linux) depuis Windows | Normal : le pont bascule automatiquement sur Docker/fallback |
