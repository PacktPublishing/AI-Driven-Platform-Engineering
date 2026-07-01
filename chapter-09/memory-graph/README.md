# The Living Memory Graph

This is Chapter 9 made real — and unlike the other labs, it doesn't end when the chapter does.

Chapter 4 taught two questions: RAG answers *"how was this solved before?"* and MCP answers
*"what is true right now?"* This lab adds a third: **"what does the team already know, and how
does it connect?"** — served as a curated knowledge graph that a local, MCP-native agent can
connect to and reason over. It is the concrete, shippable form of *context-as-a-module*: curated
context, versioned in git, extended by pull request, and queried over MCP.

We seed it with the book itself — the concepts, decisions, patterns, threats, and tools from all
nine chapters, wired together with typed edges. Then we keep adding to it. Your agent gets a
working appendix that keeps teaching after the last page.

## What you build (well, run)

A [FastMCP server](./files/mcp/app/server.py) over a [curated graph](./files/mcp/graph/graph.json).
It runs over **stdio**, the way MCP hosts (Claude Desktop, Cursor) and open-source harnesses
(Goose, Hermes, OpenClaw) launch servers.

It exposes the graph as tools:

| Tool | Answers |
|---|---|
| `search_memory(query)` | "What do we know about X?" — keyword search across the graph |
| `get_node(id)` | One idea in full, plus everything it connects to |
| `neighbors(id, depth)` | "What relates to X?" — traverse outward |
| `list_nodes(chapter, type)` | Browse by chapter or by type (concept, decision, pattern, threat, tool…) |
| `graph_stats()` | Coverage at a glance |

…and as MCP **resources** (`memory://graph`, `memory://node/{id}`) for hosts that browse.

## Step 1: Set up the environment

```bash
cd files/mcp
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Step 2: Query the graph (no AI host required)

A tiny demo client launches the server over stdio and calls the tools, so you can see it work
before wiring any AI host:

```bash
python client_demo.py                       # a guided tour
python client_demo.py --search "downloadable brains"
python client_demo.py --node context-as-module
```

## Step 3: Connect your own agent

Point any MCP host at the server. The stdio command is `python -m app.server` (run from
`files/mcp`). For example, in a Claude Desktop / Cursor MCP config:

```json
{
  "mcpServers": {
    "living-memory-graph": {
      "command": "python",
      "args": ["-m", "app.server"],
      "cwd": "<path-to>/chapter-09/memory-graph/files/mcp"
    }
  }
}
```

Now ask your agent things like *"According to the book's memory graph, what mitigates prompt
injection, and which chapter introduced it?"* — and watch it traverse the graph instead of
guessing.

## Step 4: Extend it (this is the point)

The graph is one file: [`graph/graph.json`](./files/mcp/graph/graph.json). Add a node, add a few
edges, open a pull request. That's the whole ritual. `node` types are
`concept | decision | lesson | pattern | threat | tool | metric`; `edge` types are
`introduced_in | depends_on | relates_to | supersedes | mitigates | enables | caused_by`.
Restart the server to pick up changes.

As the field moves, we — and you — keep adding what we learn. That is what makes it *living*.

## A note on trust

A shared brain is only as safe as its provenance. Chapter 8's memory-poisoning threat applies
directly here: curated context is valuable precisely because someone curated it, so treat
contributions the way you treat any dependency — review the PR, know the author, pin a version.
That discipline is what separates a knowledge graph you can trust from a rumor mill.
