from abc import ABC, abstractmethod
from typing import Dict, Any, List
from mcp.types import Tool, TextContent


class BaseTool(ABC):
    name: str
    description: str

    @staticmethod
    @abstractmethod
    async def execute(arguments: Dict[str, Any]) -> List[TextContent]:
        pass

    @staticmethod
    @abstractmethod
    def get_schema() -> Tool:
        pass