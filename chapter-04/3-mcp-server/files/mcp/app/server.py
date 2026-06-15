"""The MCP server — the §4.10 example, made real.

The chapter wraps a "list deployments" API as an MCP tool. Here that tool
queries the *live* cluster instead of a static REST endpoint. Run it the way
the chapter describes — over stdio, launched by an MCP host (Claude Desktop,
Cursor, or the demo client in this lab):

    python -m app.server

Each `@mcp.tool()` becomes a tool the model can call. The model never touches
Kubernetes directly; it asks the tool, the tool returns structured JSON, the
model reasons over it.
"""
from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import k8s

mcp = FastMCP("platform-cluster")


@mcp.tool()
def list_deployments(namespace: Optional[str] = None, only_unhealthy: bool = False) -> list[dict]:
    """List Kubernetes deployments and their live health.

    Args:
        namespace: Limit to one namespace. Omit for all namespaces.
        only_unhealthy: If true, return only deployments whose ready replica
            count is below desired (i.e. something is wrong right now).

    Returns a list of objects with: namespace, name, desired, ready, available,
    healthy, owner, and pod_reasons (e.g. ["CrashLoopBackOff"]) when unhealthy.
    """
    return k8s.list_deployments(namespace=namespace, only_unhealthy=only_unhealthy)


if __name__ == "__main__":
    # STDIO transport — an MCP host launches this process and speaks MCP over
    # stdin/stdout, exactly as in the chapter's example.
    mcp.run(transport="stdio")
