"""
Page 1 — Calculator MCP (In-Process Tools)
Demonstrates: @tool decorator + create_sdk_mcp_server + ClaudeAgentOptions
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from utils.agent_runner import run_agent_sync, render_event, inject_styles, sidebar_api_key

st.set_page_config(page_title="Calculator MCP", page_icon="🧮", layout="wide")
inject_styles()

# ── Sidebar ───────────────────────────────────────────────────────────────────
api_key = sidebar_api_key()

st.sidebar.markdown("---")
st.sidebar.markdown("### About this demo")
st.sidebar.markdown("""
**In-Process MCP** runs tools directly inside your Python app — no subprocess needed.

```python
@tool("add", "Add two numbers",
      {"a": float, "b": float})
async def add(args):
    return {"content": [
        {"type": "text",
         "text": str(args["a"]+args["b"])}
    ]}
```
""")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="border-bottom:1px solid #242836; padding-bottom:20px; margin-bottom:28px;">
  <h2 style="margin:0;">🧮 Calculator MCP — In-Process Tools</h2>
  <p style="color:#64748b; margin:4px 0 0;">
    Custom tools via <code>@tool</code> decorator + <code>create_sdk_mcp_server()</code>
  </p>
</div>
""", unsafe_allow_html=True)

# ── Code preview ──────────────────────────────────────────────────────────────
with st.expander("📄 View SDK code", expanded=False):
    st.code('''
from claude_agent_sdk import (
    tool, create_sdk_mcp_server,
    ClaudeAgentOptions, query
)

@tool("add", "Add two numbers", {"a": float, "b": float})
async def add(args):
    result = args["a"] + args["b"]
    return {"content": [{"type": "text", "text": str(result)}]}

@tool("subtract", "Subtract b from a", {"a": float, "b": float})
async def subtract(args):
    result = args["a"] - args["b"]
    return {"content": [{"type": "text", "text": str(result)}]}

@tool("multiply", "Multiply two numbers", {"a": float, "b": float})
async def multiply(args):
    result = args["a"] * args["b"]
    return {"content": [{"type": "text", "text": str(result)}]}

@tool("divide", "Divide a by b", {"a": float, "b": float})
async def divide(args):
    if args["b"] == 0:
        return {"content": [{"type": "text", "text": "Error: division by zero"}]}
    return {"content": [{"type": "text", "text": str(args["a"] / args["b"])}]}

calculator = create_sdk_mcp_server(
    name="calculator",
    version="1.0.0",
    tools=[add, subtract, multiply, divide]
)

options = ClaudeAgentOptions(
    mcp_servers={"calc": calculator},
    allowed_tools=["mcp__calc__add","mcp__calc__subtract",
                   "mcp__calc__multiply","mcp__calc__divide"],
)

async for msg in query(prompt=user_prompt, options=options):
    ...
''', language="python")

# ── Quick prompts ─────────────────────────────────────────────────────────────
st.markdown("#### Quick prompts")
quick = [
    "What is (123 + 456) × 7?",
    "Divide 1000 by 8, then subtract 25",
    "Calculate the area of a rectangle 14.5 × 9.3",
    "If I have 500 and spend 37.5 twice, how much is left?",
]
cols = st.columns(len(quick))
chosen = None
for col, q in zip(cols, quick):
    if col.button(q, use_container_width=True):
        chosen = q

# ── Prompt input ──────────────────────────────────────────────────────────────
prompt = st.text_input(
    "Or type your own math question:",
    value=chosen or "",
    placeholder="e.g. What is 42 × 13 + 7?",
)

run = st.button("▶ Run Agent", disabled=not api_key, use_container_width=True)

# ── Run ───────────────────────────────────────────────────────────────────────
if run and prompt and api_key:
    st.markdown("---")
    st.markdown("#### Agent Output")

    # Import here so missing package gives a clear error
    try:
        from claude_agent_sdk import (
            tool, create_sdk_mcp_server, ClaudeAgentOptions, query
        )
    except ImportError:
        st.error("`claude_agent_sdk` not installed. Run: `pip install claude-agent-sdk`")
        st.stop()

    # ── Define in-process tools ───────────────────────────────────────────────
    @tool("add", "Add two numbers", {"a": float, "b": float})
    async def add(args):
        return {"content": [{"type": "text", "text": str(args["a"] + args["b"])}]}

    @tool("subtract", "Subtract b from a", {"a": float, "b": float})
    async def subtract(args):
        return {"content": [{"type": "text", "text": str(args["a"] - args["b"])}]}

    @tool("multiply", "Multiply two numbers", {"a": float, "b": float})
    async def multiply(args):
        return {"content": [{"type": "text", "text": str(args["a"] * args["b"])}]}

    @tool("divide", "Divide a by b", {"a": float, "b": float})
    async def divide(args):
        if args["b"] == 0:
            return {"content": [{"type": "text", "text": "Error: division by zero"}]}
        return {"content": [{"type": "text", "text": str(args["a"] / args["b"])}]}

    calculator = create_sdk_mcp_server(
        name="calculator",
        version="1.0.0",
        tools=[add, subtract, multiply, divide],
    )

    options = ClaudeAgentOptions(
        mcp_servers={"calc": calculator},
        allowed_tools=[
            "mcp__calc__add", "mcp__calc__subtract",
            "mcp__calc__multiply", "mcp__calc__divide",
        ],
    )

    output_area = st.container()
    with st.spinner("Agent running…"):
        for event in run_agent_sync(
            lambda: query(prompt=prompt, options=options)
        ):
            render_event(event, output_area)
