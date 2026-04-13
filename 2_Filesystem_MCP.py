"""
Page 2 — Filesystem MCP (stdio external server)
Demonstrates: external MCP server via subprocess (stdio transport)
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from utils.agent_runner import run_agent_sync, render_event, inject_styles, sidebar_api_key

st.set_page_config(page_title="Filesystem MCP", page_icon="📁", layout="wide")
inject_styles()

# ── Sidebar ───────────────────────────────────────────────────────────────────
api_key = sidebar_api_key()

st.sidebar.markdown("---")
st.sidebar.markdown("### Prerequisites")
st.sidebar.code("npm install -g @modelcontextprotocol/server-filesystem", language="bash")
st.sidebar.markdown("### About")
st.sidebar.markdown("""
**stdio MCP** spawns an external process and communicates over stdin/stdout.

```python
options = ClaudeAgentOptions(
    mcp_servers={
        "filesystem": {
            "type": "stdio",
            "command": "npx",
            "args": ["-y",
              "@modelcontextprotocol/server-filesystem",
              "/path/to/dir"]
        }
    },
    allowed_tools=["mcp__filesystem__*"]
)
```
""")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="border-bottom:1px solid #242836; padding-bottom:20px; margin-bottom:28px;">
  <h2 style="margin:0;">📁 Filesystem MCP — stdio External Server</h2>
  <p style="color:#64748b; margin:4px 0 0;">
    Connect to <code>@modelcontextprotocol/server-filesystem</code> via subprocess
  </p>
</div>
""", unsafe_allow_html=True)

# ── Config ────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([3, 1])
with col1:
    directory = st.text_input(
        "Directory to expose to the agent:",
        value=os.path.expanduser("~/"),
        help="The MCP server will only have access to this directory.",
    )
with col2:
    max_files = st.number_input("Max file results", min_value=5, max_value=50, value=10)

with st.expander("📄 View SDK code", expanded=False):
    st.code(f'''
from claude_agent_sdk import query, ClaudeAgentOptions

options = ClaudeAgentOptions(
    mcp_servers={{
        "filesystem": {{
            "type": "stdio",
            "command": "npx",
            "args": ["-y",
                     "@modelcontextprotocol/server-filesystem",
                     "{directory}"],
        }}
    }},
    allowed_tools=["mcp__filesystem__*"],
)

async for msg in query(prompt=user_prompt, options=options):
    ...
''', language="python")

# ── Quick prompts ─────────────────────────────────────────────────────────────
st.markdown("#### Quick prompts")
quick = [
    f"List all Python files in {directory}",
    f"What are the largest files in {directory}?",
    f"Find any README files and summarize the first one",
    f"How many files and directories are in {directory}?",
]
cols = st.columns(2)
chosen = None
for i, q in enumerate(quick):
    if cols[i % 2].button(q, use_container_width=True):
        chosen = q

prompt = st.text_area(
    "Or type your own prompt:",
    value=chosen or "",
    placeholder="e.g. Find all .json files and list their names",
    height=80,
)

run = st.button("▶ Run Agent", disabled=not api_key, use_container_width=True)

if run and prompt and api_key:
    st.markdown("---")
    st.markdown("#### Agent Output")

    try:
        from claude_agent_sdk import query, ClaudeAgentOptions
    except ImportError:
        st.error("`claude_agent_sdk` not installed. Run: `pip install claude-agent-sdk`")
        st.stop()

    options = ClaudeAgentOptions(
        mcp_servers={
            "filesystem": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", directory],
            }
        },
        allowed_tools=["mcp__filesystem__*"],
    )

    output_area = st.container()
    with st.spinner("Agent + Filesystem MCP running…"):
        for event in run_agent_sync(
            lambda: query(prompt=prompt, options=options)
        ):
            render_event(event, output_area)
