import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel
from pythonjsonlogger import jsonlogger

from . import request_context, telemetry
from .platform_coordinator import create_coordinator
from .mcp_clients import start_clients, stop_clients

logger = logging.getLogger("agent")
handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    telemetry.configure()
    start_clients()
    yield
    stop_clients()
    telemetry.flush()


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
    session_token = request_context.session_id.set(req.session_id)
    user_token = request_context.user_id.set(req.user_id)
    try:
        agent = create_coordinator(session_id=req.session_id)
        result = agent(req.intent)
        return InvokeResponse(session_id=req.session_id, response=str(result))
    finally:
        request_context.user_id.reset(user_token)
        request_context.session_id.reset(session_token)
