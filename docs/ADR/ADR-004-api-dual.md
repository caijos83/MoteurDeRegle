# ADR-004 — API duale : REST + GraphQL

**Date :** 2026-04  
**Statut :** Accepté  
**Auteurs :** Équipe M1 MIAGE

## Contexte

Le cahier des charges impose deux interfaces API : REST et GraphQL.
Les deux doivent offrir les mêmes fonctionnalités (CRUD tables + évaluation).

## Alternatives envisagées

| Option             | Avantages                         | Inconvénients                        |
|--------------------|-----------------------------------|--------------------------------------|
| REST seul          | Simple, bien connu                | Ne répond pas au CDC                 |
| GraphQL seul       | Flexible, sur-mesure              | Ne répond pas au CDC                 |
| **REST + GraphQL** | CDC respecté, double compétence   | Duplication partielle de logique     |
| gRPC               | Très performant                   | Moins adapté à l'IHM web, hors CDC   |

## Décision

Implémenter **FastAPI** pour le REST et **Strawberry** pour le GraphQL, montés sur le même
processus FastAPI (Strawberry s'intègre nativement à FastAPI).

## Arguments

- **FastAPI** : async natif, documentation OpenAPI automatique, typage Python strict.
- **Strawberry** : GraphQL Python moderne, intégration FastAPI one-liner, génère le schéma depuis les types Python.
- La logique métier est dans une couche service commune (`API/rest/services/`), les deux API l'appellent.
- Pas de duplication de la logique DMN, seulement des couches transport différentes.

## Structure

```
API/
├── rest/
│   ├── main.py              # FastAPI app (monte aussi Strawberry)
│   ├── routes/
│   │   ├── tables.py        # POST/GET/PUT/DELETE /tables
│   │   └── evaluate.py      # POST /tables/{id}/evaluate
│   └── db/
│       └── terminusdb.py    # Accès TerminusDB
└── graphql/
    └── schema.py            # Strawberry schema (queries + mutations)
```

## Conséquences

- Un seul `uvicorn` sert REST (`/api/v1/`) et GraphQL (`/graphql`).
- L'endpoint GraphQL inclut GraphiQL (explorateur interactif) en mode dev.
- Les tests d'intégration couvrent les deux interfaces.
