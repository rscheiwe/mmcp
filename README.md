# mMCP

## Motivation
`mmcp` is inspired by Anthropic's MCP-based `create-python-server` with the following changes:

- Microservices architecture
- Docker baked-in for immediate deployment
- CLI tooling for ease-of-use (e.g., `mmcp add tool`)
- Added support for Poetry

The purpose of this project is to provide a more streamlined and user-friendly experience for creating SSE-specific MCP servers, foregrounding deployment options in order to make it easier to get started with MCP. In sum, it began and ended as a means to satisfy my own needs from the MCP.

## Quickstart

```bash
>> pip install mmcp
>> mmcp create-mmcp --name my-mmcp-server
>> cd my-mmcp-server
>> mmcp run server
```

To add a tool, use the following command:

```bash
>> mmcp add tool --name my-tool
```

Refer to the project structure for more information, where `mmcp add tool` will add a tool to the `tools/` directory.

```
- MY_MMCP_SERVER/
  - src/
    - my_mmcp_server/
      - prompts/      # Prompt-definition code
      - resources/    # Resource-definition code
      - services/     # Service-layer code
        - __init__.py
        - prompts.py
        - resources.py
        - tools.py
      - tools/        # Tool-definition code
        - __init__.py
        - base.py
        - my_tool.py  # <-- Added by `mmcp add tool --name my_tool`
      - __init__.py
      - app.py
      - server.py
  - tests/
  - .env
  - docker-compose.yml
  - Dockerfile        # Docker image definition
  - pyproject.toml
  - README.md
```

The `services/` layer orchestrates the `mcp`-specific decorators, employed generically via `server.py`:

```python
@server.list_tools()
async def handle_list_tools():
    return await tool_service.list_tools()

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None):
    return await tool_service.execute_tool(name, arguments or {})

```

where `@server` is:

```python
from mcp.server import Server

# Create the server instance
server = Server("my_mmcp_server")
```

## Usage

To run the project, use the following command:

```bash
>> mmcp run server
```

which launches the server via `poetry run python -m my_server.server`.

A common pattern to route calls to the server via an endpoint. 

Suppose your server is running on `http://127.0.0.1:8080/sse`:

```python
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
# ...fastapi setup
# ...


@router.get("/mcp-list-tools")
async def mcp_list_tools():
    async with sse_client(url="http://127.0.0.1:8080/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()

            return tools


@router.post("/mcp-call-tool")
async def mcp_call_tool(tool_name: str, parameters: Dict[str, Any]):
    async with sse_client(url="http://127.0.0.1:8080/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # # Call the fetch tool
            # result = await session.call_tool("fetch", {"url": "https://example.com"})
            result = await session.call_tool(tool_name, parameters)

            return result
```

**Note:** More extensive documentation and usage is on the way.

## Development

To run the project, use the following command:

```bash
>> poetry install --no-cache
>> poetry shell
>> poetry run mmcp create-mmcp --name my_project
```

To build and run the project, use the following command:

```bash
>> cd path/to/your/mmcp
>> python -m build
>> pip install "path/.../dist/mmcp-0.1.0.whl"
```

## License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

**NOTE**

This project is based on [create-python-server](https://github.com/modelcontextprotocol/create-python-server) by Anthropic, PBC.

This project is not affiliated with Anthropic, PBC., and does not reflect my views or opinions on the strengths or weaknesses of Anthropic's MCP.
