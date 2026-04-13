"""
Page 6 — Dual MCP Agent (stdio + HTTP)
Demonstrates: running an agent with one stdio MCP server and one HTTP MCP server simultaneously.
"""

import asyncio
import os
import sys
import threading
import queue

import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(page_title="Dual MCP Agent", page_icon="🔀", layout="wide")

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Sora:wght@300;400;600;700&display=swap');
:root {
    --bg: #0d0f14; --surface: #161923; --border: #242836;
    --accent: #6c8eff; --accent2: #a78bfa; --green: #34d399;
    --red: #f87171; --yellow: #fbbf24; --text: #e2e8f0; --muted: #64748b;
    --font-mono: 'JetBrains Mono', monospace; --font-sans: 'Sora', sans-serif;
}
html, body, [class*="css"] { font-family: var(--font-sans) !important; background-color: var(--bg) !important; color: var(--text) !important; }
section[data-testid="stSidebar"] { background: var(--surface) !important; border-right: 1px solid var(--border) !important; }
.stButton > button { background: linear-gradient(135deg, var(--accent), var(--accent2)) !important; color: #fff !important; border: none !important; border-radius: 8px !important; font-weight: 600 !important; transition: opacity .2s !important; }
.stButton > button:hover { opacity: .85 !important; }
.stTextInput > div > div > input, .stTextArea > div > div > textarea { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; color: var(--text) !important; font-family: var(--font-mono) !important; font-size: 13px !important; }
.event-tool-call { background:#0f172a; border-left:3px solid #6c8eff; border-radius:6px; padding:10px 14px; margin:6px 0; font-family:'JetBrains Mono',monospace; font-size:12px; }
.event-tool-result { background:#0f1a0f; border-left:3px solid #34d399; border-radius:6px; padding:10px 14px; margin:6px 0; font-family:'JetBrains Mono',monospace; font-size:12px; }
.event-mcp-init { background:#1a1200; border-left:3px solid #fbbf24; border-radius:6px; padding:10px 14px; margin:6px 0; font-size:12px; }
.event-error { background:#1f0a0a; border-left:3px solid #f87171; border-radius:6px; padding:10px 14px; margin:6px 0; }
.badge { display:inline-block; padding:2px 8px; border-radius:20px; font-size:11px; font-weight:600; margin-right:6px; }
.badge-tool { background:#1e2a4a; color:#6c8eff; }
.badge-result { background:#0d2a1a; color:#34d399; }
.badge-mcp { background:#2a1e00; color:#fbbf24; }
.badge-error { background:#2a0d0d; color:#f87171; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("### 🔑 API Key")
api_key = st.sidebar.text_input(
    "ANTHROPIC_API_KEY",
    value=os.environ.get("ANTHROPIC_API_KEY", ""),
    type="password",
)
if api_key:
    os.environ["ANTHROPIC_API_KEY"] = api_key
else:
    st.sidebar.warning("Enter your API key to run the agent.")

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ MCP Server Config")

fs_root = st.sidebar.text_input(
    "stdio MCP — Filesystem root",
    value=os.path.expanduser("~"),
    help="The Python stdio MCP server will expose this directory.",
)

http_url = st.sidebar.text_input(
    "HTTP MCP — Server URL",
    value="https://code.claude.com/docs/mcp",
    help="Remote MCP endpoint (HTTP transport).",
)

http_auth = st.sidebar.text_input(
    "HTTP MCP — Auth token (optional)",
    value="",
    type="password",
    placeholder="Bearer sk-...",
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
**Transport types**
```python
# stdio — subprocess
{"type": "stdio",
 "command": "python",
 "args": ["fs_mcp_server.py"],
 "env": {"FS_ROOT": "..."}}

# http — remote
{"type": "http",
 "url": "https://..."}
```
""")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="border-bottom:1px solid #242836; padding-bottom:20px; margin-bottom:28px;">
  <h2 style="margin:0;">🔀 Dual MCP Agent</h2>
  <p style="color:#64748b; margin:4px 0 0;">
    One agent · two MCP transports — <strong>stdio</strong> (filesystem) + <strong>HTTP</strong> (remote docs)
  </p>
</div>
""", unsafe_allow_html=True)

# ── Server status badges ──────────────────────────────────────────────────────
c1, c2 = st.columns(2)
c1.markdown(f"""
<div style="background:#161923;border:1px solid #1a3a2a;border-radius:10px;padding:16px;text-align:center;">
  <div style="font-size:24px;">📁</div>
  <div style="font-weight:600;margin:6px 0 2px;">Filesystem MCP</div>
  <div style="font-size:11px;color:#64748b;margin-bottom:8px;">stdio · Python subprocess</div>
  <div style="font-size:11px;color:#94a3b8;font-family:monospace;">{fs_root}</div>
</div>
""", unsafe_allow_html=True)

c2.markdown(f"""
<div style="background:#161923;border:1px solid #1a2a3a;border-radius:10px;padding:16px;text-align:center;">
  <div style="font-size:24px;">🌐</div>
  <div style="font-weight:600;margin:6px 0 2px;">Remote Docs MCP</div>
  <div style="font-size:11px;color:#64748b;margin-bottom:8px;">HTTP · no subprocess</div>
  <div style="font-size:11px;color:#94a3b8;font-family:monospace;overflow:hidden;text-overflow:ellipsis;">{http_url}</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Quick prompts ─────────────────────────────────────────────────────────────
st.markdown("#### Quick prompts")
quick = [
    f"List all Python files in {fs_root} and summarise what each one does",
    "What are Claude Code hooks and how do I use them? (use the docs MCP)",
    f"Read the README in {fs_root} and explain the project",
    "List files here and explain what the Claude Agent SDK query() function does",
]
cols = st.columns(2)
chosen = None
for i, q in enumerate(quick):
    if cols[i % 2].button(q, use_container_width=True, key=f"quick_{i}"):
        chosen = q

# ── Prompt input ──────────────────────────────────────────────────────────────
prompt = st.text_area(
    "Your prompt:",
    value=chosen or "",
    placeholder="Ask something that spans both servers — e.g. list files here AND explain what Claude hooks are",
    height=100,
)

run = st.button(
    "▶ Run Dual MCP Agent",
    disabled=not api_key,
    use_container_width=True,
)

# ── Agent logic ───────────────────────────────────────────────────────────────

def _run_agent(prompt: str, fs_root: str, http_url: str, http_auth: str, result_queue: queue.Queue):
    """Run the dual-MCP agent in a background thread."""

    async def _async_run():
        try:
            from claude_agent_sdk import query, ClaudeAgentOptions
        except ImportError:
            result_queue.put(("error", "`claude_agent_sdk` not installed."))
            result_queue.put(None)
            return

        venv_py   = os.path.join(os.path.dirname(__file__), ".venv", "bin", "python")
        python    = venv_py if os.path.exists(venv_py) else sys.executable
        fs_script = os.path.join(os.path.dirname(__file__), "fs_mcp_server.py")

        stdio_cfg: dict = {
            "type":    "stdio",
            "command": python,
            "args":    [fs_script],
            "env":     {"FS_ROOT": fs_root},
        }

        http_cfg: dict = {"type": "http", "url": http_url}
        if http_auth:
            http_cfg["headers"] = {"Authorization": http_auth}

        options = ClaudeAgentOptions(
            mcp_servers={"fs": stdio_cfg, "docs": http_cfg},
            allowed_tools=["mcp__fs__*", "mcp__docs__*"],
        )

        try:
            async for msg in query(prompt=prompt, options=options):
                result_queue.put(("msg", msg))
        except Exception as exc:
            result_queue.put(("error", str(exc)))
        finally:
            result_queue.put(None)   # sentinel

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_async_run())
    finally:
        loop.close()


def _render_msg(msg, container):
    """Render one SDK message into the Streamlit container."""
    import json

    cls_name = type(msg).__name__
    kind     = cls_name.lower().replace("message", "")

    if kind == "system":
        data    = getattr(msg, "data", {}) or {}
        subtype = data.get("subtype") or getattr(msg, "subtype", "")
        if subtype == "init":
            servers = data.get("mcp_servers") or getattr(msg, "mcp_servers", [])
            names, statuses = [], []
            for s in servers:
                names.append(s.get("name", "?") if isinstance(s, dict) else getattr(s, "name", "?"))
                statuses.append(s.get("status", "?") if isinstance(s, dict) else getattr(s, "status", "?"))
            server_list = ", ".join(
                f'{"✓" if st == "connected" else "✗"} {n}'
                for n, st in zip(names, statuses)
            )
            container.markdown(f"""
<div class="event-mcp-init">
  <span class="badge badge-mcp">🔗 MCP INIT</span> {server_list}
</div>""", unsafe_allow_html=True)

    elif kind == "assistant":
        for block in getattr(msg, "content", []):
            btype = getattr(block, "type", "") or type(block).__name__.lower()
            if btype in ("text", "textblock"):
                text = getattr(block, "text", "")
                if text:
                    container.markdown(text)
            elif btype in ("tool_use", "tooluse", "tooluseblock"):
                args_str = json.dumps(getattr(block, "input", {}), indent=2)
                container.markdown(f"""
<div class="event-tool-call">
  <span class="badge badge-tool">⚡ TOOL CALL</span>
  <strong>{block.name}</strong>
  <pre style="margin:8px 0 0;color:#94a3b8;">{args_str}</pre>
</div>""", unsafe_allow_html=True)

    elif kind == "user":
        for block in getattr(msg, "content", []):
            btype = type(block).__name__.lower()
            if "toolresult" in btype:
                raw   = getattr(block, "content", "") or ""
                text  = raw if isinstance(raw, str) else str(raw)
                short = text[:500] + ("…" if len(text) > 500 else "")
                container.markdown(f"""
<div class="event-tool-result">
  <span class="badge badge-result">✓ RESULT</span>
  <pre style="margin:6px 0 0;color:#86efac;">{short}</pre>
</div>""", unsafe_allow_html=True)

    elif kind == "result":
        subtype = getattr(msg, "subtype", "")
        result  = getattr(msg, "result", "")
        cost    = getattr(msg, "total_cost_usd", None)
        if subtype == "success":
            if result:
                container.markdown(result)
            cost_str = f"&nbsp;&nbsp;<span style='color:#64748b;font-size:12px;'>cost: ${cost:.4f}</span>" if cost else ""
            container.markdown(
                f"<div style='margin-top:16px;color:#34d399;font-weight:600;'>✓ Agent finished{cost_str}</div>",
                unsafe_allow_html=True,
            )
        else:
            container.markdown(f"""
<div class="event-error">
  <span class="badge badge-error">✗ ERROR</span> subtype={subtype}
</div>""", unsafe_allow_html=True)


# ── Execution ─────────────────────────────────────────────────────────────────

if run and prompt and api_key:
    st.markdown("---")
    st.markdown("#### Agent Output")
    output = st.container()

    rq: queue.Queue = queue.Queue()
    t = threading.Thread(
        target=_run_agent,
        args=(prompt, fs_root, http_url, http_auth, rq),
        daemon=True,
    )
    t.start()

    with st.spinner("Dual MCP agent running…"):
        while True:
            item = rq.get()
            if item is None:
                break
            kind, payload = item
            if kind == "msg":
                _render_msg(payload, output)
            elif kind == "error":
                output.markdown(f"""
<div class="event-error">
  <span class="badge badge-error">✗ ERROR</span> {payload}
</div>""", unsafe_allow_html=True)
