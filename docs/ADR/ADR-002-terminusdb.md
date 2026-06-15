# ADR-002 — Stockage : TerminusDB

**Date :** 2026-04  
**Statut :** Accepté  
**Auteurs :** Équipe M1 MIAGE

## Contexte

Les tables de décision sont des structures JSON semi-structurées avec des colonnes
variables par table. Un stockage flexible est nécessaire. Contrainte : local, open-source, gratuit.

## Alternatives envisagées

| Option        | Avantages                          | Inconvénients                          |
|---------------|------------------------------------|----------------------------------------|
| PostgreSQL    | Mature, JSONB puissant             | Relationnelle, schema rigide           |
| MongoDB       | Schéma-less, natif JSON            | Daemon lourd, license SSPL récente     |
| SQLite        | Zéro infra, embarqué               | Pas de graph, requêtes JSON limitées   |
| JSON fichiers | Ultra simple                       | Pas de requêtes, pas de transactions   |
| **TerminusDB**| Graph-Document, schéma flexible, local | Moins connue, docs à apprendre    |

## Décision

Utiliser **TerminusDB** en mode local (Docker ou binaire natif).

## Arguments

- Imposé par le cahier des charges (encadrant).
- Format Graph-Document adapté au stockage de tables JSON avec colonnes variables.
- API Python officielle (`terminusdb-client`).
- Versionning natif des données (utile pour l'historique des tables).
- Open-source Apache 2.0.

## Conséquences

- Installer TerminusDB localement : `docker run -p 6363:6363 terminusdb/terminusdb-server`
- La couche `API/rest/db/terminusdb.py` encapsule toutes les interactions.
- Prévoir un fallback JSON fichiers pour les tests unitaires (mock).
