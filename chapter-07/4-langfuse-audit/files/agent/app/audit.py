"""Hash-chained append-only audit log.

Every tool call the agent makes is recorded as a JSON line. Each record's
`prev_hash` is the SHA-256 of the previous record's full text. Tampering
with any record invalidates every record after it — the property the
chapter calls *immutability*.

This is a debug log promoted to an audit log by intent: it lives on a
PVC the agent can write to but the platform team can replicate elsewhere
(Object Lock, hash chain witness, whatever the threat model needs).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from strands.hooks import AfterToolCallEvent, BeforeToolCallEvent, HookProvider, HookRegistry

logger = logging.getLogger("agent.audit")

_GENESIS = "0" * 64


class AuditLog:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._last_hash = self._read_last_hash()

    def _read_last_hash(self) -> str:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return _GENESIS
        with self.path.open("rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            block = min(8192, size)
            f.seek(-block, os.SEEK_END)
            tail = f.read().decode("utf-8", errors="replace").splitlines()
        for line in reversed(tail):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                return rec.get("hash", _GENESIS)
            except json.JSONDecodeError:
                continue
        return _GENESIS

    def append(self, payload: dict[str, Any]) -> str:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            **payload,
        }
        with self._lock:
            record["prev_hash"] = self._last_hash
            body = json.dumps(record, sort_keys=True, separators=(",", ":"))
            digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
            line = json.dumps({**record, "hash": digest}, sort_keys=True, separators=(",", ":"))
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
            self._last_hash = digest
        return digest


class AuditHook(HookProvider):
    """Strands hook that appends one audit record per tool call (before + after)."""

    def __init__(self, log: AuditLog, agent_id: str):
        self._log = log
        self._agent_id = agent_id

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeToolCallEvent, self._before_tool)
        registry.add_callback(AfterToolCallEvent, self._after_tool)

    def _before_tool(self, event: BeforeToolCallEvent) -> None:
        if event.selected_tool is None:
            return
        try:
            digest = self._log.append(
                {
                    "phase": "before_tool",
                    "agent_id": self._agent_id,
                    "tool": event.selected_tool.tool_name,
                    "tool_args": list((event.tool_use.get("input", {}) or {}).keys()),
                }
            )
            logger.info("audit.before", extra={"digest": digest})
        except Exception as e:
            logger.warning("audit.before failed: %s", e)

    def _after_tool(self, event: AfterToolCallEvent) -> None:
        try:
            tool_name = (
                event.selected_tool.tool_name if getattr(event, "selected_tool", None) else "?"
            )
            digest = self._log.append(
                {
                    "phase": "after_tool",
                    "agent_id": self._agent_id,
                    "tool": tool_name,
                    "ok": getattr(event, "exception", None) is None,
                }
            )
            logger.info("audit.after", extra={"digest": digest})
        except Exception as e:
            logger.warning("audit.after failed: %s", e)
