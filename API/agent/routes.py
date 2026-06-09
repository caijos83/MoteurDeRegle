"""
POST /api/v1/agent/chat — point d'entrée REST pour l'agent IA DMN.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .agent import run_agent

router = APIRouter(tags=["agent"])


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


@router.post("/agent/chat")
def chat(body: ChatRequest):
    if not body.messages:
        raise HTTPException(status_code=422, detail="La liste de messages est vide.")
    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    try:
        result = run_agent(messages)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return result
