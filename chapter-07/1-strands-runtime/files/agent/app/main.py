import logging

from fastapi import FastAPI
from pydantic import BaseModel
from pythonjsonlogger import jsonlogger

from .agent import build_agent

logger = logging.getLogger("agent")
handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

app = FastAPI(title="Agentic Platform Runtime")


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
