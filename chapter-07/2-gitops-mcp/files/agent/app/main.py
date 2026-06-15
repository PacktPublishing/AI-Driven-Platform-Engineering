import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel
from pythonjsonlogger import jsonlogger

from .agent import build_agent
from .mcp_clients import start_clients, stop_clients

logger = logging.getLogger("agent")
handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    start_clients()
    yield
    stop_clients()


app = FastAPI(title="Agentic Platform Runtime", lifespan=lifespan)


class InvokeRequest(BaseModel):
    intent: str
    session_id: str = "default"
    user_id: str | None = None


class InvokeResponse(BaseModel):
    session_id: str
    response: str


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(req: InvokeRequest) -> InvokeResponse:
    logger.info("invoke", extra={"session_id": req.session_id, "user_id": req.user_id})
    agent = build_agent(session_id=req.session_id)
    result = agent(req.intent)
    return InvokeResponse(session_id=req.session_id, response=str(result))
