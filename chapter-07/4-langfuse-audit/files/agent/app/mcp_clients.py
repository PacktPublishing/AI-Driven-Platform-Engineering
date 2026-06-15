"""Connections to domain MCP servers.

The chapter argues that production agents have one MCP server per platform
domain (catalog, gitops, cluster-ops, observability). The reference build
implements one — gitops-mcp — and stops there. The plumbing here would be
identical for additional domains; copy the pattern.
"""

from __future__ import annotations

import logging

from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient

from .settings import settings

logger = logging.getLogger("agent.mcp")

_gitops_client: MCPClient | None = None
_gitops_tools: list = []


def start_clients() -> None:
    """Start MCP clients and load their tool schemas. Called once at startup."""
    global _gitops_client, _gitops_tools

    if not settings.mcp_gitops_url:
        logger.info("mcp_gitops_url not configured, skipping gitops-mcp")
        return

    logger.info("starting gitops-mcp client", extra={"url": settings.mcp_gitops_url})
    _gitops_client = MCPClient(
        lambda: streamablehttp_client(f"{settings.mcp_gitops_url}/mcp")
    )
    _gitops_client.start()
    _gitops_tools = _gitops_client.list_tools_sync()
    logger.info(
        "gitops-mcp tools loaded",
        extra={"count": len(_gitops_tools), "names": [t.tool_name for t in _gitops_tools]},
    )


def stop_clients() -> None:
    """Stop all MCP clients. Called at shutdown."""
    global _gitops_client
    if _gitops_client is not None:
        try:
            _gitops_client.stop(None, None, None)
        except Exception as e:
            logger.warning("error stopping gitops client: %s", e)
        _gitops_client = None


def gitops_tools() -> list:
    """Return the list of MCPAgentTool instances exposed by gitops-mcp."""
    return list(_gitops_tools)
