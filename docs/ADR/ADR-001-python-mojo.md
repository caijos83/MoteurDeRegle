# ADR-001 — Choix des langages : Python + Mojo

**Date :** 2026-04  
**Statut :** Accepté  
**Auteurs :** Équipe M1 MIAGE

## Contexte

Le moteur DMN Light doit être léger, performant et local. Il doit fonctionner sur
n'importe quel laptop sans dépendance cloud. L'encadrant impose une démarche Green IT.

## Alternatives envisagées

| Option          | Avantages                        | Inconvénients                           |
|-----------------|----------------------------------|-----------------------------------------|
| Java pur        | Mature, performant               | Lourd, consommation élevée, JVM requise |
| Python pur      | Facile, rapide à développer      | Lent pour évaluation de règles en masse |
| JavaScript/Node | Universel, riche en libs         | Consommation mémoire, pas Green IT      |
| **Python + Mojo**  | Python pour UI/API, Mojo pour calcul | Mojo récent, moins de docs          |

## Décision

Utiliser **Python** pour l'IHM, l'API REST/GraphQL et le serveur MCP.
Utiliser **Mojo** pour le moteur d'évaluation des règles (hit policies FIRST et COLLECT SUM).

## Arguments

- Mojo (sorti 2023) compile en code natif, performance proche du C, syntaxe Python-like.
- La séparation des responsabilités permet d'optimiser uniquement la partie calcul.
- Green IT : Mojo réduit la consommation CPU/mémoire vs JVM Java.
- Python est le langage standard pour les APIs web légères (FastAPI).

## Conséquences

- Le pont Python ↔ Mojo doit être minimal (serialisation JSON simple).
- Mesurer la latence du pont pour valider le gain réel.
- Documentation Mojo en cours de maturation — prévoir du temps de R&D.
