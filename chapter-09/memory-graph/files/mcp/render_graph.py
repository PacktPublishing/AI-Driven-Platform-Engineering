"""Connect to the living-memory-graph MCP server and render the graph.

Proves the round trip: it launches app/server.py exactly as an MCP host would, pulls the
graph *through the protocol* (graph_stats + the memory://graph resource), then writes a
Mermaid diagram and a standalone SVG you can open. No third-party rendering deps.

    python render_graph.py           # writes figures/memory-graph.mmd and .svg
"""

from __future__ import annotations

import asyncio
import json
import math
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = StdioServerParameters(command="python", args=["-m", "app.server"])
OUT = Path(__file__).resolve().parent.parent.parent / "figures"

TYPE_COLOR = {
    "concept": "#4C78A8", "decision": "#F58518", "pattern": "#54A24B",
    "threat": "#E45756", "tool": "#B279A2", "metric": "#9D755D", "lesson": "#72B7B2",
}


async def fetch_graph() -> dict:
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # 1) prove tools work
            stats = await session.call_tool("graph_stats", {})
            stats_text = "".join(getattr(c, "text", "") for c in stats.content)
            print("Connected over MCP. graph_stats() ->", stats_text)
            # 2) pull the whole graph through the resource interface
            res = await session.read_resource("memory://graph")
            body = "".join(getattr(c, "text", "") for c in res.contents)
            return json.loads(body)


def to_mermaid(graph: dict) -> str:
    lines = ["graph LR"]
    for n in graph["nodes"]:
        nid = n["id"].replace("-", "_")
        lines.append(f'  {nid}["{n["title"]}"]')
    for e in graph["edges"]:
        a = e["from"].replace("-", "_")
        b = e["to"].replace("-", "_")
        lines.append(f'  {a} -->|{e["rel"]}| {b}')
    return "\n".join(lines) + "\n"


def to_svg(graph: dict) -> str:
    # Layout: one column per chapter, nodes stacked within the column.
    nodes = graph["nodes"]
    by_ch: dict[int, list] = {}
    for n in nodes:
        by_ch.setdefault(n.get("chapter", 0), []).append(n)
    chapters = sorted(by_ch)
    col_w, row_h, bw, bh = 240, 70, 190, 40
    top = 90
    max_rows = max(len(v) for v in by_ch.values())
    width = 60 + col_w * len(chapters)
    height = top + row_h * max_rows + 40

    pos = {}
    for ci, ch in enumerate(chapters):
        cx = 60 + ci * col_w
        for ri, n in enumerate(sorted(by_ch[ch], key=lambda x: x["title"])):
            pos[n["id"]] = (cx, top + ri * row_h)

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'font-family="Helvetica,Arial,sans-serif" font-size="11">']
    svg.append(f'<rect width="{width}" height="{height}" fill="#0d1117"/>')
    svg.append('<defs><marker id="arw" markerWidth="8" markerHeight="8" refX="7" refY="3" '
               'orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#6e7681"/></marker></defs>')
    svg.append(f'<text x="30" y="40" fill="#e6edf3" font-size="20" font-weight="bold">'
               f'AI-Driven Platform Engineering — Living Memory Graph</text>')
    svg.append(f'<text x="30" y="62" fill="#8b949e">{len(nodes)} nodes · '
               f'{len(graph["edges"])} edges · pulled live over MCP</text>')
    # chapter column headers
    for ci, ch in enumerate(chapters):
        cx = 60 + ci * col_w
        svg.append(f'<text x="{cx + bw/2}" y="{top - 18}" fill="#8b949e" '
                   f'text-anchor="middle">Ch {ch}</text>')
    # edges (curved), drawn under nodes
    for e in graph["edges"]:
        if e["from"] not in pos or e["to"] not in pos:
            continue
        x1, y1 = pos[e["from"]]; x2, y2 = pos[e["to"]]
        sx, sy = x1 + bw, y1 + bh / 2
        tx, ty = x2, y2 + bh / 2
        mx = (sx + tx) / 2
        svg.append(f'<path d="M{sx},{sy} C{mx},{sy} {mx},{ty} {tx},{ty}" '
                   f'fill="none" stroke="#30363d" stroke-width="1" marker-end="url(#arw)"/>')
    # nodes
    for n in nodes:
        x, y = pos[n["id"]]
        color = TYPE_COLOR.get(n["type"], "#6e7681")
        title = n["title"] if len(n["title"]) <= 26 else n["title"][:24] + "…"
        svg.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="6" '
                   f'fill="{color}" opacity="0.92"/>')
        svg.append(f'<text x="{x + 8}" y="{y + 17}" fill="#fff" font-weight="bold">{title}</text>')
        svg.append(f'<text x="{x + 8}" y="{y + 32}" fill="#e6edf3" opacity="0.85">{n["type"]}</text>')
    # legend
    lx = 30
    for i, (t, c) in enumerate(TYPE_COLOR.items()):
        ly = height - 22
        svg.append(f'<rect x="{lx + i*110}" y="{ly}" width="12" height="12" rx="2" fill="{c}"/>')
        svg.append(f'<text x="{lx + i*110 + 18}" y="{ly + 11}" fill="#8b949e">{t}</text>')
    svg.append("</svg>")
    return "\n".join(svg)


async def main() -> None:
    OUT.mkdir(exist_ok=True)
    graph = await fetch_graph()
    (OUT / "memory-graph.mmd").write_text(to_mermaid(graph))
    (OUT / "memory-graph.svg").write_text(to_svg(graph))
    print(f"Wrote {OUT/'memory-graph.mmd'} and {OUT/'memory-graph.svg'}")


if __name__ == "__main__":
    asyncio.run(main())
