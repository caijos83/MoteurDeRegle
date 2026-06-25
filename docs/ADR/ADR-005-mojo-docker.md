# ADR-005 — Conteneurisation du moteur Mojo

**Date :** 2026-06  
**Statut :** Accepté  
**Auteurs :** Équipe M1 MIAGE

## Contexte

Mojo n'a pas de toolchain native Windows : le binaire `evaluator` est compilé via WSL
(Linux ELF). Exécuté depuis un interpréteur Python Windows natif, `subprocess.run`
échoue avec `WinError 193` (« n'est pas une application Win32 valide »). Chaque
développeur sur Windows doit donc soit installer WSL + Mojo localement, soit
ne jamais tester la branche réelle du moteur (et retomber silencieusement sur
le fallback Python pur).

## Alternatives envisagées

| Option                          | Avantages                          | Inconvénients                              |
|----------------------------------|-------------------------------------|---------------------------------------------|
| Exiger WSL + Mojo sur chaque poste | Pas de Docker supplémentaire     | Installation lourde et non reproductible par dev |
| Binaire Linux commité dans le repo | Simple                          | Toujours inexécutable nativement sous Windows ; pas reproductible si le code source change |
| **Conteneur Docker (image `dmn-mojo-engine`)** | Build reproductible, exécutable depuis Windows/macOS/Linux via Docker Desktop | Léger surcoût de démarrage par appel (`docker run`) |

## Décision

Empaqueter le moteur Mojo dans une image Docker (`Backend/engine/Dockerfile`), construite
avec **pixi** (outil d'installation recommandé par Modular) sur une base `ubuntu:22.04` +
`clang` (requis par `mojo build` pour l'édition de liens).

Le bridge Python (`Backend/bridge/engine_bridge.py`) essaie, dans l'ordre :
1. le binaire natif local (`Backend/engine/evaluator`) — le plus rapide,
2. le conteneur Docker (`docker run --rm -i dmn-mojo-engine`) — portable,
3. le fallback Python pur — toujours disponible (dev/tests/CI sans Docker).

## Arguments

- **Version épinglée** : `pixi add mojo==0.26.2.0` (version utilisée en local par l'équipe).
  Mojo ≥ 1.0 a supprimé le mot-clé `fn` (remplacé par `def`) ; prendre la dernière version
  casserait la compilation du code existant. Vérifié par un build réel (`docker build`)
  qui échoue explicitement sur ce point avec `mojo` non épinglé.
- Le service `mojo-engine` dans `docker-compose.yml` utilise `profiles: ["build-only"]` :
  ce n'est pas un serveur réseau (il lit stdin/écrit stdout puis sort), donc il ne doit
  pas démarrer avec `docker compose up`. Il sert uniquement à builder l'image :
  `docker compose build mojo-engine`.
- Le bridge distingue "outil indisponible" (OSError → palier suivant) de "le binaire a
  tourné mais a échoué" (code retour non nul → `RuntimeError`, signal d'un vrai bug Mojo
  qu'il ne faut pas masquer en tombant sur le fallback Python).

## Conséquences

- Build : `docker compose build mojo-engine` (ou `docker build -t dmn-mojo-engine Backend/engine`).
- Aucune installation WSL/Mojo requise pour les développeurs qui ont seulement Docker Desktop.
- Si la version Mojo locale de l'équipe change, mettre à jour `MOJO_VERSION` dans le
  Dockerfile (argument `ARG MOJO_VERSION=0.26.2.0`) et re-builder l'image.
- Tests effectués : hit policy FIRST (`age >= 18` / `< 18`) et COLLECT SUM
  (somme de deux règles `premium`) validés directement via le conteneur et via le bridge
  Python avec le binaire natif absent.
