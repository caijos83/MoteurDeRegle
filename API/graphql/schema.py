"""
Schéma GraphQL Strawberry — mêmes fonctionnalités que le REST.
"""

import strawberry
from typing import Optional
from ..rest.db.terminusdb import TerminusDBClient
from Backend.bridge.engine_bridge import evaluate as engine_evaluate

db = TerminusDBClient()


@strawberry.type
class ColumnType:
    name: str
    type: str
    role: str


@strawberry.type
class DecisionTable:
    id: str
    name: str
    hit_policy: str
    columns: strawberry.scalars.JSON
    rules: strawberry.scalars.JSON


@strawberry.type
class EvaluateResult:
    result: Optional[strawberry.scalars.JSON]
    hit_policy: str
    matched_rules: Optional[int] = None


@strawberry.input
class ColumnInput:
    name: str
    type: str
    role: str


@strawberry.input
class CreateTableInput:
    name: str
    hit_policy: str
    columns: list[ColumnInput]


@strawberry.type
class Query:
    @strawberry.field
    def tables(self) -> list[DecisionTable]:
        return [DecisionTable(**t) for t in db.list_tables()]

    @strawberry.field
    def table(self, id: str) -> Optional[DecisionTable]:
        t = db.get_table(id)
        if t:
            return DecisionTable(**t)
        return None

    @strawberry.field
    def column_types(self) -> list[str]:
        return ["number", "text", "boolean"]


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_table(self, input: CreateTableInput) -> DecisionTable:
        import uuid
        table = {
            "id": str(uuid.uuid4()),
            "name": input.name,
            "hit_policy": input.hit_policy,
            "columns": [{"name": c.name, "type": c.type, "role": c.role} for c in input.columns],
            "rules": [],
        }
        db.save_table(table)
        return DecisionTable(**table)

    @strawberry.mutation
    def delete_table(self, id: str) -> bool:
        if not db.get_table(id):
            return False
        db.delete_table(id)
        return True

    @strawberry.mutation
    def evaluate_table(self, table_id: str, inputs_json: str) -> EvaluateResult:
        import json
        table = db.get_table(table_id)
        if not table:
            raise ValueError("Table introuvable")
        inputs = json.loads(inputs_json)
        result = engine_evaluate(table, inputs)
        return EvaluateResult(**result)


schema = strawberry.Schema(query=Query, mutation=Mutation)
