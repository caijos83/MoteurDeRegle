"""
Point d'entrée FastAPI — monte REST et GraphQL sur le même serveur.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import strawberry
from strawberry.fastapi import GraphQLRouter

from .routes.tables import router as tables_router
from .routes.evaluate import router as evaluate_router
from ..graphql.schema import schema

app = FastAPI(
    title="DMN Light Engine API",
    description="Moteur de règles DMN Light — REST + GraphQL",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST routes
app.include_router(tables_router, prefix="/api/v1")
app.include_router(evaluate_router, prefix="/api/v1")

# GraphQL (Strawberry)
graphql_app = GraphQLRouter(schema, graphiql=True)
app.include_router(graphql_app, prefix="/graphql")


@app.get("/health")
def health():
    return {"status": "ok", "engine": "DMN Light"}
