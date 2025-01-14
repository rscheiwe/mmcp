from typing import Dict, Any, Annotated
import httpx
from mcp.types import Tool, TextContent
from .base import BaseTool
from pydantic import BaseModel, Field


class WeatherInput(BaseModel):
    city: str = Field(..., description="The city to get weather for")
    api_key: str = Field(..., description="Your WeatherAPI API key")


class WeatherTool(BaseTool):
    name = "get_weather"
    description = "Get current weather for a location"
    
    @staticmethod
    async def execute(arguments: WeatherInput) -> list[TextContent]:
        city = arguments.city
        api_key = arguments.api_key
        
        # Stub to represent a real API call
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(
        #         f"https://api.weatherapi.com/v1/current.json",
        #         params={"q": city, "key": api_key}
        #     )
        #     data = response.json()
        
        data = {"current": {"temp_c": 20}}
            
        return [TextContent(
            type="text",
            text=f"Current weather in {city}: {data['current']['temp_c']}°C"
        )]

    @staticmethod
    def get_schema() -> Tool:
        return Tool(
            name=WeatherTool.name,
            description=WeatherTool.description,
            inputSchema=WeatherInput.model_json_schema()
        )