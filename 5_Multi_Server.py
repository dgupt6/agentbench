"""
Page 5 — Multi-Server Agent
Demonstrates: combining in-process SDK MCP server + external stdio server
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from utils.agent_runner import run_agent_sync, render_event, inject_styles, sidebar_api_key

st.set_page_config(page_title="Multi-Server Agent", page_icon="🔗", layout="wide")
inject_styles()

# ── Sidebar ───────────────────────────────────────────────────────────────────
api_key = sidebar_api_key()

st.sidebar.markdown("---")
st.sidebar.markdown("### Active Servers")
use_calculator = st.sidebar.checkbox("🧮 Calculator (in-process)", value=True)
use_filesystem = st.sidebar.checkbox("📁 Filesystem (stdio)", value=True)

if use_filesystem:
    directory = st.sidebar.text_input("Filesystem root", value=os.path.expanduser("~/"))
else:
    directory = "~/"

st.sidebar.markdown("---")
st.sidebar.markdown("""
**Key insight:** You can mix server types freely.
```python
options = ClaudeAgentOptions(
    mcp_servers={
        "calc": sdk_server,     # in-process
        "fs":   stdio_config,   # subprocess
        "docs": http_config,    # remote HTTP
    }
)
```
""")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="border-bottom:1px solid #242836; padding-bottom:20px; margin-bottom:28px;">
  <h2 style="margin:0;">🔗 Multi-Server Agent</h2>
  <p style="color:#64748b; margin:4px 0 0;">
    Combine in-process SDK tools + external stdio MCP servers in one agent
  </p>
</div>
""", unsafe_allow_html=True)

# ── Server status cards ───────────────────────────────────────────────────────
c1, c2 = st.columns(2)

def status_card(col, icon, name, transport, active):
    color = "#34d399" if active else "#475569"
    badge = "ACTIVE" if active else "DISABLED"
    col.markdown(f"""
    <div style="
        background:#161923; border:1px solid {'#1a3a2a' if active else '#242836'};
        border-radius:10px; padding:16px; text-align:center;
    ">
      <div style="font-size:24px;">{icon}</div>
      <div style="font-weight:600; margin:6px 0 2px;">{name}</div>
      <div style="font-size:11px; color:#64748b; margin-bottom:8px;">{transport}</div>
      <span style="
          background:{'#0d2a1a' if active else '#1a1f2e'};
          color:{color}; padding:2px 10px; border-radius:20px;
          font-size:11px; font-weight:600;
      ">{badge}</span>
    </div>
    """, unsafe_allow_html=True)

status_card(c1, "🧮", "Calculator MCP", "In-process (SDK)", use_calculator)
status_card(c2, "📁", "Filesystem MCP", f"stdio — {directory}", use_filesystem)

st.markdown("<br>", unsafe_allow_html=True)

with st.expander("📄 View SDK code", expanded=False):
    st.code('''
from claude_agent_sdk import (
    tool, create_sdk_mcp_server,
    ClaudeAgentOptions, query
)

# ── In-process server ─────────────────────────────
@tool("add",      "Add two numbers",      {"a": float, "b": float})
async def add(args):
    return {"content": [{"type":"text","text":str(args["a"]+args["b"])}]}

@tool("multiply", "Multiply two numbers", {"a": float, "b": float})
async def multiply(args):
    return {"content": [{"type":"text","text":str(args["a"]*args["b"])}]}

calc_server = create_sdk_mcp_server(
    name="calculator", tools=[add, multiply]
)

# ── External stdio server ─────────────────────────
fs_config = {
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "~/"],
}

# ── Combine both ──────────────────────────────────
options = ClaudeAgentOptions(
    mcp_servers={
        "calc": calc_server,   # in-process
        "fs":   fs_config,     # subprocess
    },
    allowed_tools=[
        "mcp__calc__add",
        "mcp__calc__multiply",
        "mcp__fs__*",
    ],
)

async for msg in query(prompt=user_prompt, options=options):
    ...
''', language="python")

# ── Quick prompts ─────────────────────────────────────────────────────────────
st.markdown("#### Quick prompts")
multi_prompts = [
    f"Count the Python files in {directory} and multiply that count by 100",
    f"List files in {directory} then calculate total if each were worth $4.50",
    "What is 7 × 8? Also, what directory am I working in?",
    f"Find README files in {directory} and add up the number of lines (estimate: use multiply)",
]
cols = st.columns(2)
chosen = None
for i, q in enumerate(multi_prompts):
    if cols[i % 2].button(q, use_container_width=True):
        chosen = q

prompt = st.text_area(
    "Or type your own prompt (can reference both calculator and files):",
    value=chosen or "",
    placeholder="e.g. Count files in ~/Desktop and multiply by 42",
    height=80,
)

run = st.button(
    "▶ Run Multi-Server Agent",
    disabled=not api_key or not (use_calculator or use_filesystem),
    use_container_width=True,
)

if run and prompt and api_key:
    st.markdown("---")
    st.markdown("#### Agent Output")

    try:
        from claude_agent_sdk import (
            tool, create_sdk_mcp_server,
            ClaudeAgentOptions, query,
        )
    except ImportError:
        st.error("`claude_agent_sdk` not installed. Run: `pip install claude-agent-sdk`")
        st.stop()

    mcp_servers = {}
    allowed_tools = []

    if use_calculator:
        @tool("add",      "Add two numbers",      {"a": float, "b": float})
        async def add(args):
            return {"content": [{"type": "text", "text": str(args["a"] + args["b"])}]}

        @tool("multiply", "Multiply two numbers", {"a": float, "b": float})
        async def multiply(args):
            return {"content": [{"type": "text", "text": str(args["a"] * args["b"])}]}

        @tool("subtract", "Subtract b from a",    {"a": float, "b": float})
        async def subtract(args):
            return {"content": [{"type": "text", "text": str(args["a"] - args["b"])}]}

        calc_server = create_sdk_mcp_server(
            name="calculator", tools=[add, multiply, subtract]
        )
        mcp_servers["calc"] = calc_server
        allowed_tools += ["mcp__calc__add", "mcp__calc__multiply", "mcp__calc__subtract"]

    if use_filesystem:
        mcp_servers["fs"] = {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", directory],
        }
        allowed_tools.append("mcp__fs__*")

    options = ClaudeAgentOptions(
        mcp_servers=mcp_servers,
        allowed_tools=allowed_tools,
    )

    output_area = st.container()
    with st.spinner("Multi-server agent running…"):
        for event in run_agent_sync(
            lambda: query(prompt=prompt, options=options)
        ):
            render_event(event, output_area)
