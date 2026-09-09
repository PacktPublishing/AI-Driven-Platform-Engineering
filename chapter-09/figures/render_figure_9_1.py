"""Render Figure 9.1 — continuous modernization as a reconciliation loop.

Draws a print-ready SVG in the same visual language as Figure 9.2 (see
../memory-graph/files/mcp/render_graph.py): white cards with a left accent bar, an
uppercase role label, a title block, and a legend. No third-party rendering deps.

    python render_figure_9_1.py     # writes figure-9-1-continuous-modernization-loop.svg
"""

from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parent
STEM = "figure-9-1-continuous-modernization-loop"

# Same print-friendly accent palette as Figure 9.2, reused by role.
ROLE_COLOR = {
    "desired state": "#3B6EA5",   # concept blue
    "actual state": "#2E8B57",    # pattern green
    "control": "#E08214",         # decision orange
    "agent step": "#8E44AD",      # tool purple
    "verification": "#1B9E9E",    # lesson teal
}
ROLE_ORDER = ["desired state", "actual state", "control", "agent step", "verification"]

EDGE_SOLID = "#475569"
EDGE_DASH = "#94A3B8"

BW, BH, RX = 214, 66, 8
COL = [44, 320, 596, 872]
ROW = [150, 292, 434, 576]

# id: (col, row, title, role)
NODES = {
    "bench":    (0, 0, "Benchmark the skill|LLM-as-a-judge gates every change", "verification"),
    "skill":    (1, 0, "SKILL.md|the standard, written down", "desired state"),
    "repo":     (0, 1, "The repository|what is actually running", "actual state"),
    "analysis": (1, 1, "Analysis|the findings you chose to look for", "control"),
    "gate":     (2, 1, "Does the target platform exist,|and is somebody operating it?", "control"),
    "apply":    (3, 1, "Agent applies the procedure|code and infrastructure diff", "agent step"),
    "build":    (2, 2, "Platform team builds|and operates the target", "control"),
    "review":   (3, 2, "Policy gate|and human review", "control"),
    "merge":    (3, 3, "Merge and deploy", "actual state"),
    "rescan":   (1, 3, "Re-analyze|a measurement, not an assertion", "verification"),
}

# (from, to, label, dashed)
EDGES = [
    ("bench", "skill", "", True),
    ("skill", "analysis", "desired", False),
    ("repo", "analysis", "actual", False),
    ("analysis", "gate", "findings", False),
    ("gate", "apply", "yes", False),
    ("gate", "build", "no", False),
    ("build", "apply", "", False),
    ("apply", "review", "", False),
    ("review", "merge", "", False),
    ("merge", "rescan", "", False),
    ("rescan", "repo", "the estate has moved", False),
    ("rescan", "skill", "what the loop learned", True),
]

WIDTH = COL[-1] + BW + 44
HEIGHT = ROW[-1] + BH + 118


def esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def box(nid: str) -> tuple[float, float]:
    c, r, *_ = NODES[nid]
    return COL[c], ROW[r]


def anchors(a: str, b: str) -> tuple[tuple[float, float], tuple[float, float]]:
    """Pick the side of each card that faces the other, so arrows never cross a box."""
    ax, ay = box(a)
    bx, by = box(b)
    acx, acy = ax + BW / 2, ay + BH / 2
    bcx, bcy = bx + BW / 2, by + BH / 2
    if abs(bcx - acx) >= abs(bcy - acy):          # mostly horizontal
        if bcx > acx:
            return (ax + BW, acy), (bx, bcy)
        return (ax, acy), (bx + BW, bcy)
    if bcy > acy:                                  # mostly vertical
        return (acx, ay + BH), (bcx, by)
    return (acx, ay), (bcx, by + BH)


def render() -> str:
    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" font-family="Helvetica,Arial,sans-serif">',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#ffffff"/>',
        '<defs>'
        f'<marker id="a_solid" markerWidth="8" markerHeight="8" refX="7" refY="3.5" '
        f'orient="auto"><path d="M0,0 L7,3.5 L0,7 Z" fill="{EDGE_SOLID}"/></marker>'
        f'<marker id="a_dash" markerWidth="8" markerHeight="8" refX="7" refY="3.5" '
        f'orient="auto"><path d="M0,0 L7,3.5 L0,7 Z" fill="{EDGE_DASH}"/></marker>'
        '</defs>',
        f'<text x="44" y="46" fill="#111827" font-size="24" font-weight="700">'
        f'Continuous Modernization</text>',
        f'<text x="44" y="72" fill="#6B7280" font-size="14">'
        f'A vended standard operating procedure, reconciled against a repository '
        f'the way an Operator reconciles a cluster</text>',
    ]

    # edges first, so cards sit on top of them
    for a, b, label, dashed in EDGES:
        col = EDGE_DASH if dashed else EDGE_SOLID
        dash = ' stroke-dasharray="5 5"' if dashed else ""
        marker = "dash" if dashed else "solid"

        if (a, b) == ("rescan", "skill"):
            # The long feedback run. Routed up the corridor to the right of column 1 so it
            # does not pass straight through the Analysis card.
            sx, sy = COL[1] + BW, ROW[3] + BH / 2
            tx, ty = COL[1] + BW, ROW[0] + BH / 2
            bulge = COL[2] - 13
            s.append(
                f'<path d="M{sx:.0f},{sy:.0f} C{bulge:.0f},{sy:.0f} {bulge:.0f},{ty:.0f} '
                f'{tx:.0f},{ty:.0f}" fill="none" stroke="{col}" stroke-width="1.8" '
                f'stroke-opacity="0.85"{dash} marker-end="url(#a_{marker})"/>'
            )
            s.append(
                f'<text x="{COL[1] + BW - 14:.0f}" y="{(sy + ty) / 2:.0f}" fill="#6B7280" '
                f'font-size="11" font-style="italic" text-anchor="end">{esc(label)}</text>'
            )
            continue

        (sx, sy), (tx, ty) = anchors(a, b)
        horiz = abs(tx - sx) >= abs(ty - sy)
        if horiz:
            d = max(34, abs(tx - sx) * 0.42)
            c1 = (sx + d if tx >= sx else sx - d, sy)
            c2 = (tx - d if tx >= sx else tx + d, ty)
        else:
            d = max(34, abs(ty - sy) * 0.42)
            c1 = (sx, sy + d if ty >= sy else sy - d)
            c2 = (tx, ty - d if ty >= sy else ty + d)
        s.append(
            f'<path d="M{sx:.0f},{sy:.0f} C{c1[0]:.0f},{c1[1]:.0f} {c2[0]:.0f},{c2[1]:.0f} '
            f'{tx:.0f},{ty:.0f}" fill="none" stroke="{col}" stroke-width="1.8" '
            f'stroke-opacity="0.85"{dash} marker-end="url(#a_{marker})"/>'
        )
        if label:
            mx, my = (sx + tx) / 2, (sy + ty) / 2
            if horiz:
                s.append(
                    f'<text x="{mx:.0f}" y="{my - 8:.0f}" fill="#6B7280" font-size="11" '
                    f'font-style="italic" text-anchor="middle">{esc(label)}</text>'
                )
            else:
                s.append(
                    f'<text x="{mx + 9:.0f}" y="{my + 4:.0f}" fill="#6B7280" font-size="11" '
                    f'font-style="italic" text-anchor="start">{esc(label)}</text>'
                )

    # cards
    for nid, (c, r, title, role) in NODES.items():
        x, y = COL[c], ROW[r]
        col = ROLE_COLOR[role]
        lines = title.split("|")
        s.append(f'<rect x="{x}" y="{y}" width="{BW}" height="{BH}" rx="{RX}" fill="#ffffff" '
                 f'stroke="#E5E7EB" stroke-width="1.2"/>')
        s.append(f'<rect x="{x}" y="{y}" width="5" height="{BH}" rx="2.5" fill="{col}"/>')
        y0 = y + (20 if len(lines) > 1 else 26)
        s.append(f'<text x="{x + 14}" y="{y0}" fill="#111827" font-size="12.5" '
                 f'font-weight="600">{esc(lines[0])}</text>')
        if len(lines) > 1:
            s.append(f'<text x="{x + 14}" y="{y0 + 15}" fill="#4B5563" font-size="11.5">'
                     f'{esc(lines[1])}</text>')
        s.append(f'<text x="{x + 14}" y="{y + BH - 9}" fill="{col}" font-size="10" '
                 f'font-weight="700" letter-spacing="0.5">{role.upper()}</text>')

    # legend
    ly = HEIGHT - 66
    s.append(f'<text x="44" y="{ly - 8}" fill="#6B7280" font-size="11" font-weight="700">'
             f'WHAT EACH BOX IS</text>')
    for i, role in enumerate(ROLE_ORDER):
        lx = 44 + i * 168
        s.append(f'<rect x="{lx}" y="{ly}" width="14" height="14" rx="3" '
                 f'fill="{ROLE_COLOR[role]}"/>')
        s.append(f'<text x="{lx + 20}" y="{ly + 11}" fill="#374151" font-size="11">{role}</text>')
    s.append(f'<line x1="44" y1="{ly + 34}" x2="70" y2="{ly + 34}" stroke="{EDGE_DASH}" '
             f'stroke-width="1.8" stroke-dasharray="5 5" marker-end="url(#a_dash)"/>')
    s.append(f'<text x="78" y="{ly + 38}" fill="#374151" font-size="11">'
             f'feedback — what the loop teaches the standard</text>')
    s.append("</svg>")
    return "\n".join(s)


if __name__ == "__main__":
    (OUT / f"{STEM}.svg").write_text(render())
    print(f"Wrote {OUT / (STEM + '.svg')}  ({WIDTH}x{HEIGHT})")
