"""
fs_mcp_server.py
----------------
Minimal Python stdio MCP server that exposes three filesystem tools:
  • list_directory  — list files/dirs in a path
  • read_file       — read text content of a file
  • file_info       — size, modified time, type of a path

Run by dual_mcp_agent.py as a subprocess (stdio transport).
"""

import asyncio
import json
import os
import stat
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

app = Server("fs-server")

ROOT = os.environ.get("FS_ROOT", os.path.expanduser("~"))


def _safe_path(path: str) -> str:
    """Resolve path; keep it inside ROOT."""
    full = os.path.realpath(os.path.join(ROOT, path.lstrip("/")))
    if not full.startswith(os.path.realpath(ROOT)):
        raise ValueError(f"Path outside root: {path}")
    return full


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="list_directory",
            description="List files and subdirectories at a given path (relative to the root).",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to list. Use '.' or '' for root.",
                        "default": ".",
                    }
                },
            },
        ),
        types.Tool(
            name="read_file",
            description="Read the text content of a file (max 8 KB).",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path."}
                },
                "required": ["path"],
            },
        ),
        types.Tool(
            name="file_info",
            description="Return size, modification time, and type (file/directory) for a path.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path."}
                },
                "required": ["path"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        if name == "list_directory":
            path = arguments.get("path", ".")
            full = _safe_path(path)
            entries = sorted(os.listdir(full))
            lines = []
            for e in entries:
                ep = os.path.join(full, e)
                tag = "/" if os.path.isdir(ep) else ""
                lines.append(f"{e}{tag}")
            result = f"Contents of {full} ({len(lines)} entries):\n" + "\n".join(lines)

        elif name == "read_file":
            full = _safe_path(arguments["path"])
            with open(full, "r", errors="replace") as f:
                content = f.read(8192)
            truncated = len(content) == 8192
            result = content + ("\n[truncated at 8 KB]" if truncated else "")

        elif name == "file_info":
            full = _safe_path(arguments["path"])
            s = os.stat(full)
            result = json.dumps({
                "path":     full,
                "type":     "directory" if stat.S_ISDIR(s.st_mode) else "file",
                "size_bytes": s.st_size,
                "modified": datetime.fromtimestamp(s.st_mtime).isoformat(),
            }, indent=2)

        else:
            result = f"Unknown tool: {name}"

    except Exception as exc:
        result = f"Error: {exc}"

    return [types.TextContent(type="text", text=result)]


async def main():
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
