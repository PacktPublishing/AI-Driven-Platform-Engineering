"""Connect to the living-memory-graph MCP server and render the graph.

Proves the round trip: it launches app/server.py exactly as an MCP host would, pulls the
graph *through the protocol* (graph_stats + the memory://graph resource), then writes a
Mermaid diagram and a print-ready SVG (light theme, edge labels, crossing reduction). No
third-party rendering deps.

    python render_graph.py           # writes figures/figure-9-1-living-memory-graph.{mmd,svg}
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = StdioServerParameters(command="python", args=["-m", "app.server"])
OUT = Path(__file__).resolve().parent.parent.parent / "figures"
STEM = "figure-9-1-living-memory-graph"

# Print-friendly accent colors (readable on white, distinguishable in grayscale by label too).
TYPE_COLOR = {
    "concept": "#3B6EA5", "decision": "#E08214", "pattern": "#2E8B57",
    "threat": "#C0392B", "tool": "#8E44AD", "metric": "#7F6A4E", "lesson": "#1B9E9E",
}
# Distinct, print-legible relationship palette (kept visually separate from node accents).
REL_COLOR = {
    "depends_on": "#2563EB", "enables": "#D97706", "mitigates": "#0D9488",
    "supersedes": "#DC2626", "caused_by": "#9333EA", "introduced_in": "#64748B",
    "relates_to": "#C7CDD6",
}
REL_ORDER = ["depends_on", "enables", "mitigates", "supersedes", "caused_by",
             "introduced_in", "relates_to"]


async def fetch_graph() -> dict:
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            stats = await session.call_tool("graph_stats", {})
            print("Connected over MCP. graph_stats() ->",
                  "".join(getattr(c, "text", "") for c in stats.content))
            res = await session.read_resource("memory://graph")
            body = "".join(getattr(c, "text", "") for c in res.contents)
            return json.loads(body)


def to_mermaid(graph: dict) -> str:
    lines = ["graph LR"]
    for n in graph["nodes"]:
        lines.append(f'  {n["id"].replace("-", "_")}["{n["title"]}"]')
    for e in graph["edges"]:
        lines.append(f'  {e["from"].replace("-", "_")} -->|{e["rel"]}| {e["to"].replace("-", "_")}')
    return "\n".join(lines) + "\n"


def _wrap(text: str, width: int = 24, max_lines: int = 2) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= width:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
        if len(lines) == max_lines - 1 and len(f"{cur}") >= width:
            break
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][:width - 1] + "…"
    return lines


def _order_rows(graph: dict, columns: list[int], by_ch: dict) -> dict:
    """Barycenter sweeps to reduce edge crossings: order nodes in each column by the mean
    row of their neighbors in adjacent columns."""
    adj: dict[str, list[str]] = {n["id"]: [] for n in graph["nodes"]}
    for e in graph["edges"]:
        adj[e["from"]].append(e["to"])
        adj[e["to"]].append(e["from"])
    order = {ch: [n["id"] for n in sorted(by_ch[ch], key=lambda x: x["title"])] for ch in columns}
    row = {nid: i for ch in columns for i, nid in enumerate(order[ch])}
    for sweep in range(6):
        seq = columns if sweep % 2 == 0 else list(reversed(columns))
        for ch in seq:
            bary = []
            for nid in order[ch]:
                ns = [row[o] for o in adj[nid] if o in row]
                bary.append((sum(ns) / len(ns) if ns else row[nid], nid))
            order[ch] = [nid for _, nid in sorted(bary, key=lambda t: t[0])]
            for i, nid in enumerate(order[ch]):
                row[nid] = i
    return order


def to_svg(graph: dict) -> str:
    nodes = {n["id"]: n for n in graph["nodes"]}
    by_ch: dict[int, list] = {}
    for n in graph["nodes"]:
        by_ch.setdefault(n.get("chapter", 0), []).append(n)
    columns = sorted(by_ch)
    order = _order_rows(graph, columns, by_ch)

    col_w, row_h, bw, bh = 250, 96, 196, 60
    left, top = 44, 150
    max_rows = max(len(v) for v in by_ch.values())
    width = left * 2 + col_w * (len(columns) - 1) + bw
    height = top + row_h * max_rows + 110

    pos = {}
    for ci, ch in enumerate(columns):
        cx = left + ci * col_w
        for ri, nid in enumerate(order[ch]):
            pos[nid] = (cx, top + ri * row_h)

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
         f'viewBox="0 0 {width} {height}" font-family="Helvetica,Arial,sans-serif">']
    s.append(f'<rect width="{width}" height="{height}" fill="#ffffff"/>')
    # arrow markers per relation color
    s.append("<defs>")
    for rel, col in REL_COLOR.items():
        s.append(f'<marker id="a_{rel}" markerWidth="7" markerHeight="7" refX="6" refY="3" '
                 f'orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="{col}"/></marker>')
    s.append("</defs>")
    # title block
    s.append(f'<text x="{left}" y="46" fill="#111827" font-size="24" font-weight="700">'
             f'The Living Memory Graph</text>')
    s.append(f'<text x="{left}" y="72" fill="#6B7280" font-size="14">'
             f'The book’s knowledge as a typed graph — {len(nodes)} nodes, '
             f'{len(graph["edges"])} relationships, served over MCP</text>')
    # chapter headers + faint column separators
    for ci, ch in enumerate(columns):
        cx = left + ci * col_w
        s.append(f'<text x="{cx + bw/2}" y="{top - 24}" fill="#9CA3AF" font-size="13" '
                 f'font-weight="600" text-anchor="middle">CHAPTER {ch}</text>')

    def anchor(a, b):
        (x1, y1), (x2, y2) = pos[a], pos[b]
        if x2 >= x1:
            return (x1 + bw, y1 + bh / 2), (x2, y2 + bh / 2)
        return (x1, y1 + bh / 2), (x2 + bw, y2 + bh / 2)

    # edges under nodes — colored by relationship type, weak "relates_to" de-emphasized
    for e in graph["edges"]:
        if e["from"] not in pos or e["to"] not in pos:
            continue
        (sx, sy), (tx, ty) = anchor(e["from"], e["to"])
        rel = e["rel"]
        col = REL_COLOR.get(rel, "#C7CDD6")
        dx = max(40, abs(tx - sx) * 0.4)
        c1x = sx + dx if tx >= sx else sx - dx
        c2x = tx - dx if tx >= sx else tx + dx
        weak = rel == "relates_to"
        dash = ' stroke-dasharray="4 4"' if weak else ""
        s.append(f'<path d="M{sx:.0f},{sy:.0f} C{c1x:.0f},{sy:.0f} {c2x:.0f},{ty:.0f} '
                 f'{tx:.0f},{ty:.0f}" fill="none" stroke="{col}" '
                 f'stroke-width="{1.3 if weak else 1.8}" '
                 f'stroke-opacity="{0.4 if weak else 0.8}"{dash} '
                 f'marker-end="url(#a_{rel})"/>')

    # nodes
    for nid, (x, y) in pos.items():
        n = nodes[nid]
        col = TYPE_COLOR.get(n["type"], "#6B7280")
        s.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="8" fill="#ffffff" '
                 f'stroke="#E5E7EB" stroke-width="1.2"/>')
        s.append(f'<rect x="{x}" y="{y}" width="5" height="{bh}" rx="2.5" fill="{col}"/>')
        lines = _wrap(n["title"], 24, 2)
        ty0 = y + (20 if len(lines) == 2 else 26)
        for i, ln in enumerate(lines):
            s.append(f'<text x="{x + 14}" y="{ty0 + i*15:.0f}" fill="#111827" font-size="12.5" '
                     f'font-weight="600">{ln}</text>')
        s.append(f'<text x="{x + 14}" y="{y + bh - 9}" fill="{col}" font-size="10" '
                 f'font-weight="700" letter-spacing="0.5">{n["type"].upper()}</text>')

    # legend — node types (boxes) and relationships (colored arrows)
    ly = height - 84
    s.append(f'<text x="{left}" y="{ly - 8}" fill="#6B7280" font-size="11" '
             f'font-weight="700">NODE TYPES</text>')
    for i, (t, c) in enumerate(TYPE_COLOR.items()):
        lx = left + i * 118
        s.append(f'<rect x="{lx}" y="{ly}" width="14" height="14" rx="3" fill="{c}"/>')
        s.append(f'<text x="{lx + 20}" y="{ly + 11}" fill="#374151" font-size="11">{t}</text>')
    ry = ly + 42
    s.append(f'<text x="{left}" y="{ry - 8}" fill="#6B7280" font-size="11" '
             f'font-weight="700">RELATIONSHIPS</text>')
    for i, rel in enumerate(REL_ORDER):
        c = REL_COLOR[rel]
        lx = left + i * 150
        weak = rel == "relates_to"
        dash = ' stroke-dasharray="4 4"' if weak else ""
        s.append(f'<line x1="{lx}" y1="{ry + 6}" x2="{lx + 26}" y2="{ry + 6}" stroke="{c}" '
                 f'stroke-width="{1.3 if weak else 2}"{dash} marker-end="url(#a_{rel})"/>')
        s.append(f'<text x="{lx + 34}" y="{ry + 10}" fill="#374151" font-size="11">{rel}</text>')
    s.append("</svg>")
    return "\n".join(s)


async def main() -> None:
    OUT.mkdir(exist_ok=True)
    graph = await fetch_graph()
    (OUT / f"{STEM}.mmd").write_text(to_mermaid(graph))
    (OUT / f"{STEM}.svg").write_text(to_svg(graph))
    print(f"Wrote {OUT/(STEM+'.svg')} and {OUT/(STEM+'.mmd')}")


if __name__ == "__main__":
    asyncio.run(main())
