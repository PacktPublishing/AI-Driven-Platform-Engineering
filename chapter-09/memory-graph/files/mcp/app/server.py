"""Living Memory Graph — an MCP server over the book's curated context.

This is Chapter 9 made real. Where Chapter 4's server answered "what is true right now?"
about a live cluster, this one answers "what does the team already know, and how does it
connect?" over a curated, PR-extensible knowledge graph.

It exposes the graph as MCP **tools** (search, get, neighbors, paths) and as MCP
**resources** (browse the whole graph or a single node). A local MCP-native agent — Claude
Desktop, Cursor, or an open-source harness such as Goose, Hermes, or OpenClaw — can connect
over stdio and reason over the book's knowledge as it grows.

Run it the way any MCP host launches a server: over stdio. See the README for wiring, or use
client_demo.py to call it with no AI host at all.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from mcp.server.fastmcp import FastMCP

GRAPH_PATH = Path(__file__).resolve().parent.parent / "graph" / "graph.json"

mcp = FastMCP("living-memory-graph")


@lru_cache(maxsize=1)
def _graph() -> dict:
    """Load and index the graph once. Restart the server to pick up graph.json edits."""
    data = json.loads(GRAPH_PATH.read_text())
    nodes = {n["id"]: n for n in data.get("nodes", [])}
    edges = data.get("edges", [])
    return {"meta": data.get("meta", {}), "nodes": nodes, "edges": edges}


def _node_text(node: dict) -> str:
    return " ".join(
        str(node.get(k, ""))
        for k in ("title", "summary", "body", "type")
    ) + " " + " ".join(node.get("tags", []))


def _edges_of(node_id: str) -> list[dict]:
    g = _graph()
    out = []
    for e in g["edges"]:
        if e["from"] == node_id:
            out.append({"rel": e["rel"], "direction": "out", "to": e["to"],
                        "title": g["nodes"].get(e["to"], {}).get("title", e["to"])})
        elif e["to"] == node_id:
            out.append({"rel": e["rel"], "direction": "in", "from": e["from"],
                        "title": g["nodes"].get(e["from"], {}).get("title", e["from"])})
    return out


@mcp.tool()
def search_memory(query: str, limit: int = 8) -> list[dict]:
    """Search the memory graph by keyword across titles, summaries, bodies, and tags.

    Returns the best-matching nodes with a short summary and their id — use get_node for detail.
    """
    terms = [t for t in re.findall(r"\w+", query.lower()) if t]
    scored = []
    for node in _graph()["nodes"].values():
        text = _node_text(node).lower()
        score = sum(text.count(t) for t in terms)
        # a title hit is worth more than a body hit
        score += 3 * sum(node.get("title", "").lower().count(t) for t in terms)
        if score:
            scored.append((score, node))
    scored.sort(key=lambda s: s[0], reverse=True)
    return [
        {"id": n["id"], "title": n["title"], "type": n["type"],
         "chapter": n.get("chapter"), "summary": n.get("summary", "")}
        for _, n in scored[:limit]
    ]


@mcp.tool()
def get_node(node_id: str) -> dict:
    """Get a single node's full content plus its immediate connections (in and out)."""
    node = _graph()["nodes"].get(node_id)
    if not node:
        return {"error": f"unknown node '{node_id}'", "hint": "use search_memory or list_nodes"}
    return {**node, "connections": _edges_of(node_id)}


@mcp.tool()
def neighbors(node_id: str, depth: int = 1) -> dict:
    """Traverse outward from a node up to `depth` hops. Great for 'what relates to X?'."""
    g = _graph()
    if node_id not in g["nodes"]:
        return {"error": f"unknown node '{node_id}'"}
    seen = {node_id}
    frontier = {node_id}
    for _ in range(max(1, depth)):
        nxt = set()
        for nid in frontier:
            for e in _edges_of(nid):
                other = e.get("to") or e.get("from")
                if other and other not in seen:
                    seen.add(other)
                    nxt.add(other)
        frontier = nxt
    return {
        "root": node_id,
        "nodes": [{"id": i, "title": g["nodes"][i]["title"], "type": g["nodes"][i]["type"]}
                  for i in sorted(seen)],
    }


@mcp.tool()
def list_nodes(chapter: int | None = None, node_type: str | None = None) -> list[dict]:
    """List nodes, optionally filtered by chapter number or node type (concept, decision,
    lesson, pattern, threat, tool, metric)."""
    out = []
    for n in _graph()["nodes"].values():
        if chapter is not None and n.get("chapter") != chapter:
            continue
        if node_type is not None and n.get("type") != node_type:
            continue
        out.append({"id": n["id"], "title": n["title"], "type": n["type"],
                    "chapter": n.get("chapter")})
    return sorted(out, key=lambda n: (n["chapter"] or 0, n["title"]))


@mcp.tool()
def graph_stats() -> dict:
    """Summarize the graph: version, node/edge counts, and coverage by chapter and type."""
    g = _graph()
    by_ch: dict = {}
    by_type: dict = {}
    for n in g["nodes"].values():
        by_ch[n.get("chapter")] = by_ch.get(n.get("chapter"), 0) + 1
        by_type[n["type"]] = by_type.get(n["type"], 0) + 1
    return {
        "version": g["meta"].get("version"),
        "nodes": len(g["nodes"]),
        "edges": len(g["edges"]),
        "by_chapter": dict(sorted(by_ch.items(), key=lambda x: x[0] or 0)),
        "by_type": by_type,
    }


@mcp.resource("memory://graph")
def graph_resource() -> str:
    """The whole graph as JSON, for hosts that browse MCP resources."""
    return GRAPH_PATH.read_text()


@mcp.resource("memory://node/{node_id}")
def node_resource(node_id: str) -> str:
    """A single node (with connections) as JSON."""
    return json.dumps(get_node(node_id), indent=2)


if __name__ == "__main__":
    mcp.run()
