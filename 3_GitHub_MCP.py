"""
Page 3 — GitHub MCP
Demonstrates: external stdio MCP server with environment variable injection
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from utils.agent_runner import run_agent_sync, render_event, inject_styles, sidebar_api_key

st.set_page_config(page_title="GitHub MCP", page_icon="🐙", layout="wide")
inject_styles()

# ── Sidebar ───────────────────────────────────────────────────────────────────
api_key = sidebar_api_key()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🐙 GitHub Token")
gh_token = st.sidebar.text_input(
    "GITHUB_TOKEN",
    value=os.environ.get("GITHUB_TOKEN", ""),
    type="password",
    help="Personal access token with `repo` scope",
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Prerequisites")
st.sidebar.code("npm install -g @modelcontextprotocol/server-github", language="bash")
st.sidebar.markdown("""
Get a token at:
[github.com/settings/tokens](https://github.com/settings/tokens)
(needs `repo` + `read:org` scopes)
""")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="border-bottom:1px solid #242836; padding-bottom:20px; margin-bottom:28px;">
  <h2 style="margin:0;">🐙 GitHub MCP</h2>
  <p style="color:#64748b; margin:4px 0 0;">
    Query repos, issues & PRs via <code>@modelcontextprotocol/server-github</code>
  </p>
</div>
""", unsafe_allow_html=True)

if not gh_token:
    st.warning("⚠️ Enter your GitHub token in the sidebar to use this demo.")

# ── Repo config ───────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    repo_owner = st.text_input("Owner / Org", value="anthropics")
with col2:
    repo_name = st.text_input("Repository", value="claude-agent-sdk-python")

full_repo = f"{repo_owner}/{repo_name}"

with st.expander("📄 View SDK code", expanded=False):
    st.code(f'''
import os
from claude_agent_sdk import query, ClaudeAgentOptions

options = ClaudeAgentOptions(
    mcp_servers={{
        "github": {{
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {{"GITHUB_TOKEN": os.environ["GITHUB_TOKEN"]}},
        }}
    }},
    allowed_tools=["mcp__github__*"],
)

async for msg in query(
    prompt="List the 5 most recent issues in {full_repo}",
    options=options
):
    # Check init message for connection status
    if msg.type == "system" and msg.subtype == "init":
        for server in msg.mcp_servers:
            print(f"{{server.name}}: {{server.status}}")
    ...
''', language="python")

# ── Quick prompts ─────────────────────────────────────────────────────────────
st.markdown("#### Quick prompts")
quick = [
    f"List the 5 most recent open issues in {full_repo}",
    f"Show the 3 latest pull requests in {full_repo}",
    f"Summarize the README of {full_repo}",
    f"What are the most recent commits in {full_repo}?",
]
cols = st.columns(2)
chosen = None
for i, q in enumerate(quick):
    if cols[i % 2].button(q, use_container_width=True):
        chosen = q

prompt = st.text_area(
    "Or type your own GitHub question:",
    value=chosen or "",
    placeholder=f"e.g. What are the open issues in {full_repo}?",
    height=80,
)

run = st.button("▶ Run Agent", disabled=not (api_key and gh_token), use_container_width=True)

if run and prompt and api_key and gh_token:
    st.markdown("---")
    st.markdown("#### Agent Output")

    try:
        from claude_agent_sdk import query, ClaudeAgentOptions
    except ImportError:
        st.error("`claude_agent_sdk` not installed. Run: `pip install claude-agent-sdk`")
        st.stop()

    options = ClaudeAgentOptions(
        mcp_servers={
            "github": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_TOKEN": gh_token},
            }
        },
        allowed_tools=["mcp__github__*"],
    )

    output_area = st.container()
    with st.spinner("Agent + GitHub MCP running…"):
        for event in run_agent_sync(
            lambda: query(prompt=prompt, options=options)
        ):
            render_event(event, output_area)
