# ADR-006 — Docker comme couche de portabilité pour Mojo et TerminusDB

**Date :** 2026-07  
**Statut :** Accepté  
**Auteurs :** Équipe M1 MIAGE

## Contexte

Le projet repose sur deux composants dont l'installation locale est complexe ou impossible
selon le système d'exploitation du développeur :

- **Mojo** : pas de toolchain native Windows. Le binaire compilé via WSL (Linux ELF) échoue
  avec `WinError 193` sur un Python Windows natif.
- **TerminusDB** : fourni uniquement sous forme de serveur (pas de bibliothèque embarquable),
  nécessite un daemon actif sur le port 6363.

L'équipe travaille sur des machines hétérogènes (Windows, possiblement macOS/Linux).
L'objectif est que chaque membre puisse faire tourner l'application complète sans
configuration manuelle complexe.

## Alternatives envisagées

| Option | Avantages | Inconvénients |
|---|---|---|
| Installation native de chaque outil | Pas de surcouche | Non reproductible ; Mojo impossible sur Windows natif |
| WSL obligatoire (Windows) | Accès aux outils Linux | Lourd (~10 Go), non portable macOS, config par dev |
| **Docker Desktop** | Build reproductible, cross-plateforme, un seul prérequis | Occupe ~4 Go sur disque |
| Fallback Python uniquement | Zéro prérequis | Mojo jamais testé, TerminusDB jamais utilisé |

## Décision

Utiliser **Docker Desktop** comme unique prérequis d'infrastructure, avec :

- **TerminusDB** : `docker run -p 6363:6363 terminusdb/terminusdb-server`
- **Moteur Mojo** : image `dmn-mojo-engine` construite depuis `Backend/engine/Dockerfile`

Les deux composants restent **optionnels** grâce aux fallbacks automatiques du bridge Python :

```
Mojo natif → Mojo Docker → Python pur (fallback)
TerminusDB → JSON fichiers locaux (.data/)
```

## Arguments

- **Un seul prérequis** : Docker Desktop couvre les deux besoins (Mojo + TerminusDB)
  au lieu d'installer deux outils distincts.
- **Reproductibilité** : le comportement est identique sur tous les postes de l'équipe.
- **Optionnel par conception** : sans Docker, l'application fonctionne complètement
  en mode dégradé (Python fallback + JSON). Aucune erreur bloquante.
- **Démo garantie** : le jour de la soutenance, un seul PC avec Docker Desktop suffit
  pour démontrer le moteur Mojo réel et la persistance TerminusDB.

## Conséquences

- Chaque développeur installe Docker Desktop une seule fois.
- Commandes de démarrage :
  ```bash
  docker start terminusdb          # ou docker run ... au premier lancement
  docker compose build mojo-engine # une seule fois
  python -m uvicorn API.rest.main:app --port 8000
  python -m streamlit run Frontend/app.py
  ```
- Les tests unitaires et d'intégration fonctionnent **sans Docker** (fallbacks actifs).
- La CI/CD peut tourner sans Docker (même logique de fallback).
- Sans Docker, les tables sont stockées dans `.data/` (gitignore) — données non partagées
  entre membres de l'équipe.
