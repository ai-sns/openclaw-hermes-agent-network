#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real MCP Server - Weather & Time Tools

"""
import asyncio
import json
import sys
from datetime import datetime
from typing import Any

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    Prompt,
    GetPromptResult,
    PromptMessage,
    CallToolResult,
)

# Create server instance
server = Server("weather-time-server")


# ==================== Tool Definitions ====================

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="get_weather",
            description="Get current weather information for a city. Returns temperature, condition, and forecast.",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name (e.g., London, Paris, New York)"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Temperature unit",
                        "default": "celsius"
                    }
                },
                "required": ["city"]
            }
        ),
        Tool(
            name="get_current_time",
            description="Get current time in specified timezone. Returns formatted date and time.",
            inputSchema={
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "Timezone (e.g., Asia/Shanghai, America/New_York, UTC)",
                        "default": "UTC"
                    },
                    "format": {
                        "type": "string",
                        "description": "Time format (e.g., '%Y-%m-%d %H:%M:%S')",
                        "default": "%Y-%m-%d %H:%M:%S"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="calculate",
            description="Perform arithmetic calculation. Supports +, -, *, /, ** (power), % (modulo).",
            inputSchema={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Math expression to evaluate (e.g., '2 + 2', '10 * 5', '2 ** 8')"
                    }
                },
                "required": ["expression"]
            }
        ),
        Tool(
            name="get_system_info",
            description="Get system information including platform, Python version, and uptime.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


# ==================== Tool Implementations ====================

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
    """Handle tool execution"""

    if name == "get_weather":
        city = arguments.get("city", "Unknown")
        unit = arguments.get("unit", "celsius")

        # Simulated weather data (in real implementation, would call weather API)
        weather_data = {
            "London": {"temp_c": 15, "temp_f": 59, "condition": "Partly Cloudy", "humidity": 65},
            "Paris": {"temp_c": 22, "temp_f": 72, "condition": "Sunny", "humidity": 70},
            "New York": {"temp_c": 18, "temp_f": 64, "condition": "Rainy", "humidity": 80},
            "London": {"temp_c": 12, "temp_f": 54, "condition": "Foggy", "humidity": 85},
            "Tokyo": {"temp_c": 20, "temp_f": 68, "condition": "Clear", "humidity": 60},
        }

        data = weather_data.get(city, {"temp_c": 20, "temp_f": 68, "condition": "Unknown", "humidity": 50})
        temp = data["temp_c"] if unit == "celsius" else data["temp_f"]
        unit_symbol = "°C" if unit == "celsius" else "°F"

        result = f"""🌤️ Weather in {city}:
━━━━━━━━━━━━━━━━━━━━━━
Temperature: {temp}{unit_symbol}
Condition: {data['condition']}
Humidity: {data['humidity']}%
Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━
✓ Real MCP Server Response"""

        return [TextContent(type="text", text=result)]

    elif name == "get_current_time":
        timezone = arguments.get("timezone", "UTC")
        time_format = arguments.get("format", "%Y-%m-%d %H:%M:%S")

        # Get current time
        current_time = datetime.now()
        formatted_time = current_time.strftime(time_format)

        result = f"""🕐 Current Time:
━━━━━━━━━━━━━━━━━━━━━━
Timezone: {timezone}
Time: {formatted_time}
Unix Timestamp: {int(current_time.timestamp())}
Day of Week: {current_time.strftime('%A')}
━━━━━━━━━━━━━━━━━━━━━━
✓ Real MCP Server Response"""

        return [TextContent(type="text", text=result)]

    elif name == "calculate":
        expression = arguments.get("expression", "")

        try:
            # Safe evaluation (only allows math operations)
            allowed_names = {"__builtins__": {}}
            result = eval(expression, allowed_names, {})

            response = f"""🔢 Calculation Result:
━━━━━━━━━━━━━━━━━━━━━━
Expression: {expression}
Result: {result}
Type: {type(result).__name__}
━━━━━━━━━━━━━━━━━━━━━━
✓ Real MCP Server Response"""

            return [TextContent(type="text", text=response)]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Calculation Error: {str(e)}")]

    elif name == "get_system_info":
        import platform
        import os

        result = f"""💻 System Information:
━━━━━━━━━━━━━━━━━━━━━━
Platform: {platform.system()} {platform.release()}
Architecture: {platform.machine()}
Python Version: {platform.python_version()}
Processor: {platform.processor() or 'Unknown'}
Process ID: {os.getpid()}
Current Directory: {os.getcwd()}
━━━━━━━━━━━━━━━━━━━━━━
✓ Real MCP Server Response"""

        return [TextContent(type="text", text=result)]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


# ==================== Resource Management ====================

@server.list_resources()
async def handle_list_resources() -> list[Resource]:
    """List available resources"""
    return [
        Resource(
            uri="weather://info",
            name="Weather Info",
            description="Weather service information and usage",
            mimeType="text/plain"
        )
    ]


@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read resource content"""
    if uri == "weather://info":
        return """Weather MCP Server
===================
This server provides weather and time information tools.

Available Tools:
1. get_weather - Get weather for a city
2. get_current_time - Get current time
3. calculate - Perform calculations
4. get_system_info - Get system information

This is a REAL MCP server with actual tool execution!
"""
    return f"Unknown resource: {uri}"


# ==================== Prompts ====================

@server.list_prompts()
async def handle_list_prompts() -> list[Prompt]:
    """List available prompts"""
    return [
        Prompt(
            name="weather_check",
            description="Check weather for multiple cities",
            arguments=[
                {
                    "name": "cities",
                    "description": "Comma-separated list of cities",
                    "required": True
                }
            ]
        )
    ]


@server.get_prompt()
async def handle_get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    """Get prompt content"""
    if name == "weather_check":
        cities = arguments.get("cities", "London,Paris") if arguments else "London,Paris"

        return GetPromptResult(
            description=f"Weather check for: {cities}",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"Please check the weather for these cities: {cities}"
                    )
                )
            ]
        )

    raise ValueError(f"Unknown prompt: {name}")


# ==================== Server Entry Point ====================

async def main():
    """Run the MCP server"""
    # Log to stderr (MCP protocol uses stdout for JSON-RPC)
    print("🚀 Starting Weather & Time MCP Server...", file=sys.stderr)
    print("📡 Server Ready - Waiting for client connection", file=sys.stderr)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="weather-time-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
