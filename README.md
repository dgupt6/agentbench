# Claude Agent SDK + MCP — Streamlit Demo

A multi-page Streamlit app demonstrating every MCP connection pattern
from the Claude Agent SDK.

## Project Structure

```
claude-agent-streamlit/
├── app.py                    # Home page + architecture overview
├── requirements.txt
├── utils/
│   └── agent_runner.py       # Async bridge, message parser, UI helpers
└── pages/
    ├── 1_Calculator_MCP.py   # In-process @tool decorator
    ├── 2_Filesystem_MCP.py   # stdio external MCP server
    ├── 3_GitHub_MCP.py       # stdio + env var injection
    ├── 4_HTTP_MCP.py         # Remote HTTP MCP server
    └── 5_Multi_Server.py     # Combine in-process + stdio
```

## Setup

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Install Node MCP servers (for Filesystem & GitHub demos)
npm install -g @modelcontextprotocol/server-filesystem
npm install -g @modelcontextprotocol/server-github

# 3. Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# 4. Run the app
streamlit run app.py
```

## Pages

| Page | MCP Type | Transport |
|------|----------|-----------|
| 🧮 Calculator MCP | In-process SDK tools | In-process (no subprocess) |
| 📁 Filesystem MCP | External MCP server | stdio (subprocess) |
| 🐙 GitHub MCP | External MCP server | stdio + env vars |
| 🌐 HTTP MCP | Remote MCP server | HTTP (no subprocess) |
| 🔗 Multi-Server | SDK + External | Mixed |

## Key Concepts

### In-Process Tools (`@tool` decorator)
```python
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool("add", "Add two numbers", {"a": float, "b": float})
async def add(args):
    return {"content": [{"type": "text", "text": str(args["a"] + args["b"])}]}

server = create_sdk_mcp_server(name="calculator", tools=[add])
```

### External stdio Server
```python
options = ClaudeAgentOptions(
    mcp_servers={
        "filesystem": {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        }
    },
    allowed_tools=["mcp__filesystem__*"]
)
```

### HTTP Server
```python
options = ClaudeAgentOptions(
    mcp_servers={
        "remote": {
            "type": "http",
            "url": "https://your-mcp.example.com/mcp"
        }
    },
    allowed_tools=["mcp__remote__*"]
)
```

### Async Bridge for Streamlit
Streamlit runs synchronously, but the Agent SDK is async.
`utils/agent_runner.py` provides `run_agent_sync()` which spins up
a background thread with its own event loop:

```python
for event in run_agent_sync(lambda: query(prompt=..., options=...)):
    render_event(event, container)
```
