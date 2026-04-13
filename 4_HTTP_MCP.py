"""
Page 4 — HTTP MCP (Remote server over HTTP transport)
Demonstrates: connecting to a remote MCP server via HTTP URL
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from utils.agent_runner import run_agent_sync, render_event, inject_styles, sidebar_api_key

st.set_page_config(page_title="HTTP MCP", page_icon="🌐", layout="wide")
inject_styles()

# ── Sidebar ───────────────────────────────────────────────────────────────────
api_key = sidebar_api_key()

st.sidebar.markdown("---")
st.sidebar.markdown("### About HTTP MCP")
st.sidebar.markdown("""
HTTP MCP connects to a remote server without any subprocess.

```python
options = ClaudeAgentOptions(
    mcp_servers={
        "remote-server": {
            "type": "http",
            "url": "https://your-mcp.example.com/mcp",
            "headers": {
                "Authorization": "Bearer TOKEN"
            }
        }
    },
    allowed_tools=["mcp__remote-server__*"]
)
```
""")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="border-bottom:1px solid #242836; padding-bottom:20px; margin-bottom:28px;">
  <h2 style="margin:0;">🌐 HTTP MCP — Remote Server</h2>
  <p style="color:#64748b; margin:4px 0 0;">
    Connect to any remote MCP server over HTTP (no subprocess required)
  </p>
</div>
""", unsafe_allow_html=True)

# ── Connection config ─────────────────────────────────────────────────────────
st.markdown("#### Server Configuration")

preset = st.selectbox("Preset server", [
    "Claude Code Docs (official)",
    "Custom URL",
])

if preset == "Claude Code Docs (official)":
    mcp_url    = "https://code.claude.com/docs/mcp"
    server_key = "claude-code-docs"
    auth_header = ""
    default_prompt = "Use the docs MCP server to explain what hooks are in the Claude Agent SDK"
else:
    mcp_url    = st.text_input("MCP server URL", placeholder="https://your-mcp.example.com/mcp")
    server_key = st.text_input("Server name (used in tool names)", value="remote")
    auth_header = st.text_input("Authorization header (optional)", placeholder="Bearer sk-...")
    default_prompt = ""

with st.expander("📄 View SDK code", expanded=False):
    auth_snippet = f'"Authorization": "{auth_header}"' if auth_header else "# no auth"
    st.code(f'''
from claude_agent_sdk import query, ClaudeAgentOptions

options = ClaudeAgentOptions(
    mcp_servers={{
        "{server_key}": {{
            "type": "http",
            "url": "{mcp_url}",
            "headers": {{
                {auth_snippet}
            }},
        }}
    }},
    allowed_tools=["mcp__{server_key}__*"],  # wildcard — allow all tools
)

async for msg in query(prompt=user_prompt, options=options):
    if msg.type == "system" and msg.subtype == "init":
        failed = [s for s in msg.mcp_servers if s.status != "connected"]
        if failed:
            print("Failed servers:", failed)
    ...
''', language="python")

# ── Prompt ────────────────────────────────────────────────────────────────────
prompt = st.text_area(
    "Prompt:",
    value=default_prompt,
    placeholder="What would you like the agent to do?",
    height=80,
)

run = st.button("▶ Run Agent", disabled=not api_key, use_container_width=True)

if run and prompt and api_key:
    if not mcp_url:
        st.error("Please enter an MCP server URL.")
        st.stop()

    st.markdown("---")
    st.markdown("#### Agent Output")

    try:
        from claude_agent_sdk import query, ClaudeAgentOptions
    except ImportError:
        st.error("`claude_agent_sdk` not installed. Run: `pip install claude-agent-sdk`")
        st.stop()

    server_config = {"type": "http", "url": mcp_url}
    if auth_header:
        server_config["headers"] = {"Authorization": auth_header}

    options = ClaudeAgentOptions(
        mcp_servers={server_key: server_config},
        allowed_tools=[f"mcp__{server_key}__*"],
    )

    output_area = st.container()
    with st.spinner(f"Connecting to {mcp_url}…"):
        for event in run_agent_sync(
            lambda: query(prompt=prompt, options=options)
        ):
            render_event(event, output_area)
