"""
Claude Agent SDK + MCP Server — Streamlit Demo
Main entry point
"""

import streamlit as st

st.set_page_config(
    page_title="Claude Agent + MCP",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Shared CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Sora:wght@300;400;600;700&display=swap');

:root {
    --bg:        #0d0f14;
    --surface:   #161923;
    --border:    #242836;
    --accent:    #6c8eff;
    --accent2:   #a78bfa;
    --green:     #34d399;
    --red:       #f87171;
    --yellow:    #fbbf24;
    --text:      #e2e8f0;
    --muted:     #64748b;
    --font-mono: 'JetBrains Mono', monospace;
    --font-sans: 'Sora', sans-serif;
}

html, body, [class*="css"] {
    font-family: var(--font-sans) !important;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}

/* sidebar */
section[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] * { font-family: var(--font-sans) !important; }

/* buttons */
.stButton > button {
    background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: var(--font-sans) !important;
    font-weight: 600 !important;
    transition: opacity .2s !important;
}
.stButton > button:hover { opacity: .85 !important; }

/* text inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
    font-family: var(--font-mono) !important;
    font-size: 13px !important;
}

/* selectbox */
.stSelectbox > div > div {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
}

/* code blocks */
code, pre {
    font-family: var(--font-mono) !important;
    background: #0a0c10 !important;
    border-radius: 6px !important;
}

/* metric cards */
[data-testid="metric-container"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 16px !important;
}

/* dividers */
hr { border-color: var(--border) !important; }

/* spinner */
.stSpinner > div { border-top-color: var(--accent) !important; }

/* alerts */
.stAlert { border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ── Hero ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="
    background: linear-gradient(135deg, #161923 0%, #1a1f2e 100%);
    border: 1px solid #242836;
    border-radius: 16px;
    padding: 40px 48px;
    margin-bottom: 32px;
    position: relative;
    overflow: hidden;
">
  <div style="
      position:absolute; top:-60px; right:-60px;
      width:220px; height:220px;
      background: radial-gradient(circle, rgba(108,142,255,.18) 0%, transparent 70%);
      border-radius:50%;
  "></div>
  <div style="
      position:absolute; bottom:-40px; left:30%;
      width:160px; height:160px;
      background: radial-gradient(circle, rgba(167,139,250,.12) 0%, transparent 70%);
      border-radius:50%;
  "></div>

  <div style="display:flex; align-items:center; gap:16px; margin-bottom:12px;">
    <span style="font-size:36px;">🤖</span>
    <h1 style="margin:0; font-size:28px; font-weight:700;
               background:linear-gradient(135deg,#6c8eff,#a78bfa);
               -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
      Claude Agent SDK + MCP
    </h1>
  </div>
  <p style="margin:0; color:#94a3b8; font-size:15px; max-width:640px; line-height:1.6;">
    Build and test autonomous Claude agents that connect to Model Context Protocol servers.
    Choose a demo from the sidebar to get started.
  </p>
</div>
""", unsafe_allow_html=True)

# ── Cards grid ───────────────────────────────────────────────────────────────
demos = [
    ("🧮", "Calculator MCP",     "In-process tools via @tool decorator",          "pages/1_Calculator_MCP.py"),
    ("📁", "Filesystem MCP",     "Browse & read files via stdio MCP server",      "pages/2_Filesystem_MCP.py"),
    ("🐙", "GitHub MCP",         "Query repos, issues & PRs via GitHub MCP",      "pages/3_GitHub_MCP.py"),
    ("🌐", "HTTP MCP",           "Connect to any remote MCP over HTTP",           "pages/4_HTTP_MCP.py"),
    ("🔗", "Multi-Server Agent", "Combine internal + external MCP servers",        "pages/5_Multi_Server.py"),
]

cols = st.columns(len(demos))
for col, (icon, title, desc, _) in zip(cols, demos):
    col.markdown(f"""
    <div style="
        background: #161923;
        border: 1px solid #242836;
        border-radius: 12px;
        padding: 20px 16px;
        text-align: center;
        height: 130px;
        display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        gap: 8px;
    ">
      <div style="font-size:28px;">{icon}</div>
      <div style="font-weight:600; font-size:13px; color:#e2e8f0;">{title}</div>
      <div style="font-size:11px; color:#64748b; line-height:1.4;">{desc}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Architecture diagram ─────────────────────────────────────────────────────
st.markdown("### Architecture")
st.markdown("""
```
┌─────────────────────────────────────────────────────────────────┐
│                      Streamlit App (Python)                     │
│                                                                 │
│  ┌──────────────┐   query() / ClaudeSDKClient                  │
│  │   UI Layer   │ ─────────────────────────────────────────┐   │
│  │  (st.chat)   │                                          ▼   │
│  └──────────────┘   ┌──────────────────────────────────────┐   │
│                     │       Claude Agent SDK               │   │
│                     │   (claude_agent_sdk package)         │   │
│                     └──────────────┬───────────────────────┘   │
│                                    │ manages tool loop          │
│              ┌─────────────────────┼──────────────────┐        │
│              ▼                     ▼                   ▼        │
│   ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐  │
│   │  In-Process MCP  │  │  stdio MCP Server│  │ HTTP MCP   │  │
│   │  (@tool / SDK)   │  │  (subprocess)    │  │ (remote)   │  │
│   └──────────────────┘  └──────────────────┘  └────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```
""")

st.markdown("---")
st.caption("👈 Select a demo from the sidebar  •  Set your `ANTHROPIC_API_KEY` env var before running")
