"""
dual_mcp_agent.py
-----------------
Standalone Claude Agent SDK program that wires up two MCP servers:
  • stdio  — @modelcontextprotocol/server-filesystem  (subprocess / stdin-stdout)
  • http   — Claude Code docs MCP  (remote HTTP, no subprocess)

The SDK drives the Claude Code CLI under the hood; it handles the full
tool-use loop automatically.

Usage
-----
    # Basic (uses defaults)
    python dual_mcp_agent.py "List Python files in the current dir and explain what hooks are"

    # Custom filesystem root
    FS_ROOT=~/projects python dual_mcp_agent.py "your prompt"

    # Custom HTTP MCP endpoint
    HTTP_MCP_URL=https://your-mcp.example.com/mcp python dual_mcp_agent.py "your prompt"

Prerequisites
-------------
    npm install -g @modelcontextprotocol/server-filesystem
    export ANTHROPIC_API_KEY="sk-ant-..."
"""

import asyncio
import json
import os
import sys


# ── Config ─────────────────────────────────────────────────────────────────────

FS_ROOT      = os.environ.get("FS_ROOT",       os.path.expanduser("~"))
HTTP_MCP_URL = os.environ.get("echo",  "https://code.claude.com/docs/mcp")
HTTP_AUTH    = os.environ.get("HTTP_MCP_AUTH", "")          # optional Bearer token


# ── Terminal colours ───────────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
DIM    = "\033[2m"


def _label(text: str, color: str) -> str:
    return f"{BOLD}{color}[{text}]{RESET}"


# ── Event printer ──────────────────────────────────────────────────────────────

def print_event(msg) -> None:
    """Parse a raw SDK message and print it in a readable terminal format.

    The SDK uses class-based message types (SystemMessage, AssistantMessage,
    UserMessage, ResultMessage) rather than a .type string attribute, so we
    derive the kind from the class name.
    """
    # e.g. "SystemMessage" -> "system", "AssistantMessage" -> "assistant"
    cls_name  = type(msg).__name__                          # "AssistantMessage"
    msg_kind  = cls_name.lower().replace("message", "")    # "assistant"

    if msg_kind == "system":
        data    = getattr(msg, "data", {}) or {}
        subtype = data.get("subtype") or getattr(msg, "subtype", "")
        if subtype == "init":
            servers  = data.get("mcp_servers") or getattr(msg, "mcp_servers", [])
            print(f"\n{_label('MCP INIT', YELLOW)} connected servers:")
            for s in servers:
                name   = s.get("name", str(s)) if isinstance(s, dict) else getattr(s, "name", str(s))
                status = s.get("status", "?")  if isinstance(s, dict) else getattr(s, "status", "?")
                icon   = "✓" if status == "connected" else "✗"
                color  = GREEN if status == "connected" else RED
                print(f"   {color}{icon}{RESET}  {name}  {DIM}({status}){RESET}")
            print()

    elif msg_kind == "assistant":
        # content lives directly on msg, not on msg.message
        for block in getattr(msg, "content", []):
            btype = getattr(block, "type", "") or type(block).__name__.lower()
            if btype in ("text", "textblock"):
                text = getattr(block, "text", "")
                if text:
                    print(f"\n{_label('ASSISTANT', CYAN)}\n{text}")
            elif btype in ("tool_use", "tooluse", "tooluseblock"):
                input_str = json.dumps(getattr(block, "input", {}), indent=2)
                print(f"\n{_label('TOOL CALL', CYAN)}  {BOLD}{block.name}{RESET}")
                for line in input_str.splitlines():
                    print(f"   {DIM}{line}{RESET}")
            # skip ThinkingBlock silently

    elif msg_kind == "user":
        # tool results come back as UserMessage with ToolResultBlock items
        for block in getattr(msg, "content", []):
            btype = type(block).__name__.lower()
            if "toolresult" in btype:
                raw   = getattr(block, "content", "") or ""
                text  = raw if isinstance(raw, str) else str(raw)
                short = text[:400] + ("…" if len(text) > 400 else "")
                print(f"\n{_label('TOOL RESULT', GREEN)}")
                for line in short.splitlines():
                    print(f"   {DIM}{line}{RESET}")

    elif msg_kind == "result":
        subtype = getattr(msg, "subtype", "")
        result  = getattr(msg, "result", "")
        cost    = getattr(msg, "total_cost_usd", None)
        if subtype == "success":
            if result:
                print(f"\n{_label('RESULT', GREEN)}\n{result}")
            cost_str = f"  {DIM}(cost: ${cost:.4f}){RESET}" if cost else ""
            print(f"\n{GREEN}{BOLD}✓ Agent finished successfully.{RESET}{cost_str}\n")
        else:
            print(f"\n{_label('ERROR', RED)} subtype={subtype}\n")


# ── Agent ──────────────────────────────────────────────────────────────────────

async def run(prompt: str) -> None:
    try:
        from claude_agent_sdk import query, ClaudeAgentOptions
    except ImportError:
        sys.exit("claude-agent-sdk is not installed.  Run: pip install claude-agent-sdk")

    # ── Server 1: stdio — Python filesystem MCP server ────────────────────────
    venv_python = os.path.join(os.path.dirname(__file__), ".venv", "bin", "python")
    python_bin  = venv_python if os.path.exists(venv_python) else sys.executable
    server_script = os.path.join(os.path.dirname(__file__), "fs_mcp_server.py")

    stdio_server = {
        "type":    "stdio",
        "command": python_bin,
        "args":    [server_script],
        "env":     {"FS_ROOT": FS_ROOT},
    }

    # ── Server 2: HTTP — remote MCP (Claude Code docs) ────────────────────────
    http_server: dict = {"type": "http", "url": HTTP_MCP_URL}
    if HTTP_AUTH:
        http_server["headers"] = {"Authorization": HTTP_AUTH}

    options = ClaudeAgentOptions(
        mcp_servers={
            "fs":   stdio_server,   # stdio transport
            "docs": http_server,    # HTTP transport
        },
        allowed_tools=[
            "mcp__fs__*",           # all filesystem tools
            "mcp__docs__*",         # all docs tools
        ],
    )

    print(f"\n{BOLD}Prompt:{RESET} {prompt}")
    print(f"{DIM}stdio MCP root : {FS_ROOT}{RESET}")
    print(f"{DIM}HTTP  MCP url  : {HTTP_MCP_URL}{RESET}\n")
    print("─" * 60)

    async for msg in query(prompt=prompt, options=options):
        print_event(msg)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Error: ANTHROPIC_API_KEY environment variable is not set.")

    if len(sys.argv) > 1:
        user_prompt = " ".join(sys.argv[1:])
    else:
        user_prompt = input("Enter your prompt: ").strip()
        if not user_prompt:
            sys.exit("No prompt provided.")

    asyncio.run(run(user_prompt))
