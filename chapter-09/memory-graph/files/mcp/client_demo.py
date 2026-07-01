"""Call the living-memory-graph server over stdio, with no AI host required.

Launches app/server.py the same way an MCP host would, then exercises the tools so you can
see the graph answer questions directly.

    python client_demo.py                 # a guided tour
    python client_demo.py --search rag    # search for a term
    python client_demo.py --node mcp      # dump one node + its connections
"""

from __future__ import annotations

import argparse
import asyncio
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = StdioServerParameters(command="python", args=["-m", "app.server"])


def _print(title: str, payload) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(payload, indent=2, default=str))


async def _call(session: ClientSession, tool: str, **args):
    result = await session.call_tool(tool, args)
    # FastMCP returns tool output as text content; decode the JSON we produced.
    text = "".join(getattr(c, "text", "") for c in result.content)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


async def run(args: argparse.Namespace) -> None:
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            if args.search:
                _print(f"search_memory({args.search!r})",
                       await _call(session, "search_memory", query=args.search))
                return
            if args.node:
                _print(f"get_node({args.node!r})",
                       await _call(session, "get_node", node_id=args.node))
                return

            # Default: a short guided tour of the graph.
            _print("graph_stats()", await _call(session, "graph_stats"))
            _print("search_memory('curated context we can download')",
                   await _call(session, "search_memory",
                               query="curated context we can download"))
            _print("get_node('downloadable-brains')",
                   await _call(session, "get_node", node_id="downloadable-brains"))
            _print("neighbors('agentic-harness', depth=1)",
                   await _call(session, "neighbors", node_id="agentic-harness", depth=1))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--search", help="keyword search the graph")
    p.add_argument("--node", help="dump one node by id")
    asyncio.run(run(p.parse_args()))
