import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

async def mcp_list_tools():
    async with sse_client(url="http://127.0.0.1:8080/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            return tools

async def main():
    tools = await mcp_list_tools()
    print(tools)

if __name__ == "__main__":
    asyncio.run(main())
