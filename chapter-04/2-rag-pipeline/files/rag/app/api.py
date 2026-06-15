"""The RAG API — the 'Orchestration Layer' from the chapter's six-part anatomy.

POST /ask {"question": "..."} runs the full loop: embed the question, retrieve
the nearest chunks from pgvector, hand them to the LLM with a grounding prompt,
and return the answer plus the exact sources it was built from.

Run locally:
    uvicorn app.api:app --reload --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from . import llm, store
from .embeddings import get_embedder
from .settings import settings

# Loaded once at startup (the embedder downloads/loads a model — not per request).
_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    _state["embedder"] = get_embedder(settings)
    _state["conn"] = store.connect(settings)
    yield
    conn = _state.get("conn")
    if conn is not None:
        conn.close()


app = FastAPI(title="Chapter 4 RAG API", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str
    top_k: int | None = None


class Source(BaseModel):
    source: str
    doc_type: str
    title: str
    owner: str
    score: float


class AskResponse(BaseModel):
    question: str
    answer: str | None
    generation_provider: str
    sources: list[Source]


@app.get("/healthz")
def healthz() -> dict:
    return {
        "status": "ok",
        "chunks": store.count(_state["conn"]),
        "generation_provider": llm.active_provider(settings),
        "embeddings_provider": settings.embeddings_provider,
    }


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    top_k = req.top_k or settings.top_k
    query_vec = _state["embedder"].embed([req.question])[0]
    retrieved = store.search(_state["conn"], query_vec, top_k)

    answer = llm.generate(settings, req.question, retrieved)
    if answer is None and llm.active_provider(settings) == "none":
        answer = (
            "[generation disabled — no LLM credentials configured] "
            "Returning the retrieved context only. Set up Bedrock or "
            "ANTHROPIC_API_KEY to get a synthesized answer."
        )

    return AskResponse(
        question=req.question,
        answer=answer,
        generation_provider=llm.active_provider(settings),
        sources=[
            Source(source=r.source, doc_type=r.doc_type, title=r.title, owner=r.owner, score=round(r.score, 3))
            for r in retrieved
        ],
    )
