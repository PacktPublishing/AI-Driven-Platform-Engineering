"""Strands hook that wires agent events to Langfuse traces.

Lifecycle:
  - BeforeInvocationEvent  -> start a Langfuse trace (one per /invoke call)
  - BeforeToolCallEvent    -> start a span under that trace
  - AfterToolCallEvent     -> end the span
  - AfterInvocationEvent   -> finalize the trace

Per-message text isn't reliably accessible from Strands' AgentEvents in
v1.38, so we focus on the structural skeleton: the user sees a trace per
session with one span per tool call, with timings, names, and arguments.
That's already enough to debug behavior and reason about cost.
"""

from __future__ import annotations

import logging
from typing import Any

from strands.hooks import (
    AfterInvocationEvent,
    AfterToolCallEvent,
    BeforeInvocationEvent,
    BeforeToolCallEvent,
    HookProvider,
    HookRegistry,
)

from . import request_context, telemetry
from .settings import settings

logger = logging.getLogger("agent.langfuse")


class LangfuseStrandsHook(HookProvider):
    def __init__(self) -> None:
        self._traces: dict[int, Any] = {}
        self._spans: dict[int, Any] = {}

    def register_hooks(self, registry: HookRegistry) -> None:
        client = telemetry.client()
        if client is None:
            return
        registry.add_callback(BeforeInvocationEvent, self._before_invoke)
        registry.add_callback(AfterInvocationEvent, self._after_invoke)
        registry.add_callback(BeforeToolCallEvent, self._before_tool)
        registry.add_callback(AfterToolCallEvent, self._after_tool)

    def _agent_key(self, event: Any) -> int:
        return id(getattr(event, "agent", event))

    def _before_invoke(self, event: BeforeInvocationEvent) -> None:
        client = telemetry.client()
        if client is None:
            return
        try:
            trace = client.trace(
                name=f"{settings.agent_id}.invoke",
                session_id=request_context.session_id.get(),
                user_id=request_context.user_id.get(),
                metadata={"agent_id": settings.agent_id},
            )
            self._traces[self._agent_key(event)] = trace
        except Exception as e:
            logger.warning("langfuse before_invoke failed: %s", e)

    def _after_invoke(self, event: AfterInvocationEvent) -> None:
        client = telemetry.client()
        if client is None:
            return
        try:
            trace = self._traces.pop(self._agent_key(event), None)
            if trace:
                trace.update(output={"completed": True})
            client.flush()
        except Exception as e:
            logger.warning("langfuse after_invoke failed: %s", e)

    def _before_tool(self, event: BeforeToolCallEvent) -> None:
        if event.selected_tool is None:
            return
        try:
            trace = self._traces.get(self._agent_key(event))
            if not trace:
                return
            span = trace.span(
                name=f"tool:{event.selected_tool.tool_name}",
                input=event.tool_use.get("input", {}),
            )
            self._spans[id(event.tool_use)] = span
        except Exception as e:
            logger.warning("langfuse before_tool failed: %s", e)

    def _after_tool(self, event: AfterToolCallEvent) -> None:
        try:
            tool_use = getattr(event, "tool_use", None)
            span = self._spans.pop(id(tool_use), None) if tool_use else None
            if span:
                span.end(output={"ok": getattr(event, "exception", None) is None})
        except Exception as e:
            logger.warning("langfuse after_tool failed: %s", e)
