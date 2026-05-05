"""Langfuse client setup. We use the Python SDK directly (which speaks the
v2 ingestion API) rather than OTLP — Langfuse v2 hasn't shipped the OTel
collector endpoint yet. For v3+ this can switch to OTLP and the rest of
this module becomes a one-liner.

The trace lifecycle is wired up by the LangfuseStrandsHook in
hooks_langfuse.py, which subscribes to Strands hook events and emits one
trace per /invoke with one nested span per tool call.
"""

from __future__ import annotations

import logging

from .settings import settings

logger = logging.getLogger("agent.telemetry")

_client = None


def configure() -> None:
    global _client
    if not settings.langfuse_enabled:
        logger.info("telemetry: langfuse disabled (env vars not set)")
        return

    from langfuse import Langfuse

    _client = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )
    logger.info(
        "telemetry: langfuse client active",
        extra={"host": settings.langfuse_host, "agent_id": settings.agent_id},
    )


def client():
    return _client


def flush() -> None:
    if _client is not None:
        _client.flush()
