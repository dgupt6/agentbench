# agent_client.py
# Claude Agent SDK connecting to the HTTP MCP server.
# This example demonstrates how to use the Claude Agent SDK to connect to an 
# external MCP server over HTTP to Calculate_MCP_Server.py, 
# which defines some simple math and weather tools. 
# Install deps:
#   pip install claude-agent-sdk
#   Node.js 18+ must be installed (required by the bundled Claude Code CLI)
#
# Set env var:  export ANTHROPIC_API_KEY=sk-ant-...
# Run with:     python agent_client.py

import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def main():
    options = ClaudeAgentOptions(
        # Connect to our local HTTP MCP server
        mcp_servers={
            "math-tools": {
                "type": "http",
                "url": "http://localhost:8001/mcp",
            }
        },
        # Pre-approve all tools from this server (pattern: mcp__<server>__<tool>)
        allowed_tools=[
            "mcp__math-tools__add",
            "mcp__math-tools__multiply",
            "mcp__math-tools__get_weather_summary",
        ],
        # Keep it focused — no file system access needed here
        permission_mode="acceptEdits",
    )

    prompt = (
        "Use the math tools to: "
        "1) Add 47 and 38, "
        "2) Multiply the result by 3, "
        "3) Get the weather for Denver. "
        "Summarise all three answers."
    )

    print(f"Prompt: {prompt}\n{'='*50}")

    async for message in query(prompt=prompt, options=options):
        # message types: system, assistant, tool_use, tool_result, result
        msg_type = getattr(message, "type", None)

        if msg_type == "system":
            # Check MCP server connection status on startup
            subtype = getattr(message, "subtype", None)
            if subtype == "init":
                mcp_status = getattr(message, "mcp_servers", {})
                for name, info in mcp_status.items():
                    status = info.get("status", "unknown")
                    print(f"[MCP] '{name}' → {status}")
                print()

        elif msg_type == "assistant":
            # Claude's reasoning / text response
            content = getattr(message, "message", None)
            if content:
                for block in content.get("content", []):
                    if block.get("type") == "text":
                        print(f"[Claude] {block['text']}")

        elif msg_type == "result":
            # Final result from the agent loop
            subtype = getattr(message, "subtype", None)
            if subtype == "success":
                print(f"\n[Done] {message.result}")
            else:
                print(f"\n[Error] {subtype}: {getattr(message, 'error', '')}")


if __name__ == "__main__":
    asyncio.run(main())