"""Minimal MCP smoke test: initialize + tools/list against mcp-server-datahub over stdio."""
import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> int:
    params = StdioServerParameters(
        command="uvx",
        args=["mcp-server-datahub@latest"],
        env={
            **os.environ,
            "DATAHUB_GMS_URL": os.environ.get("DATAHUB_GMS_URL", "http://localhost:8080"),
            "DATAHUB_GMS_TOKEN": os.environ.get("DATAHUB_GMS_TOKEN", ""),
        },
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"initialize OK: server={init.server_info.name} v{init.server_info.version} "
                  f"protocol={init.protocol_version}")
            tools = await session.list_tools()
            print(f"tools/list OK: {len(tools.tools)} tools")
            for t in tools.tools:
                desc = (t.description or "").strip().splitlines()[0][:100]
                print(f"  - {t.name}: {desc}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
