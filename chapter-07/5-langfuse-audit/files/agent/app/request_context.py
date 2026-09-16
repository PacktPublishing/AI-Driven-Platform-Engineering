"""Per-request context for hooks. main.py sets session_id and user_id from
the InvokeRequest; LangfuseStrandsHook reads them when a trace starts."""

import contextvars

session_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "session_id", default="default"
)
user_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_id", default=None
)
