from typing import List, Dict, Any
import mcp.types as types
from ..tools.base import BaseTool
from ..app import server


class ToolService:
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}

    def register_tool(self, tool: BaseTool):
        self.tools[tool.name] = tool

    
    async def list_tools(self) -> List[types.Tool]:
        """List available tools exposed by this MCP server.
    
        Returns:
            list[types.Tool]: List of Tool objects describing the available tools and their schemas.
            {% if with_examples %}Currently includes 'get_weather' for a dummy weather API tool.{% else %}
            No tools configured by default.{% endif %}
        """
        return [
            tool.get_schema() 
            for tool in self.tools.values()
        ]

    async def execute_tool(
        self, 
        name: str, 
        arguments: Dict[str, Any]
    ) -> List[types.TextContent]:
        """Execute a specific tool.
        
        Args:
            name (str): The name of the tool to execute.
            arguments (Dict[str, Any]): The arguments to pass to the tool.
        
        Returns:
            List[types.TextContent]: The output of the tool execution.
        """
        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")
            
        tool = self.tools[name]
        return await tool.execute(arguments)
    