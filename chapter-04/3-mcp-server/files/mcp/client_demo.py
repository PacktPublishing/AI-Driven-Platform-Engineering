"""A minimal MCP client, so you can exercise the server without Claude Desktop
or Cursor. It launches the server over stdio (exactly as a real MCP host would),
lists the tools it exposes, and calls `list_deployments`.

    python client_demo.py                 # all deployments
    python client_demo.py --unhealthy     # only unhealthy ones (the demo)

This is the same handshake an AI host performs: connect, discover tools, call a
tool, read structured results.
"""
from __future__ import annotations

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main(only_unhealthy: bool) -> None:
    params = StdioServerParameters(command=sys.executable, args=["-m", "app.server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Tools exposed by the server:")
            for t in tools.tools:
                print(f"  - {t.name}: {t.description.splitlines()[0]}")
            print()

            args = {"only_unhealthy": only_unhealthy}
            print(f"Calling list_deployments({args}) ...\n")
            result = await session.call_tool("list_deployments", args)
            for block in result.content:
                if block.type == "text":
                    print(block.text)


if __name__ == "__main__":
    asyncio.run(main(only_unhealthy="--unhealthy" in sys.argv))
