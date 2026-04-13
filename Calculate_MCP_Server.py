# mcp_server.py — using standalone fastmcp package
# Install: pip install fastmcp
# Run:     python mcp_server.py

from fastmcp import FastMCP

mcp = FastMCP("math-tools")


@mcp.tool
def add(a: float, b: float) -> float:
    """Add two numbers together."""
    return a + b


@mcp.tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers together."""
    return a * b


@mcp.tool
def get_weather_summary(city: str) -> str:
    """Get a mock weather summary for a city."""
    return f"Weather in {city}: 22°C, partly cloudy, humidity 60%."


if __name__ == "__main__":
    # Starts HTTP server on http://localhost:8001/mcp
    mcp.run(transport="streamable-http", host="localhost", port=8001)