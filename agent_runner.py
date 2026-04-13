"""
utils/agent_runner.py
Async bridge + message parsing helpers shared across all pages.
"""

import asyncio
import threading
from typing import AsyncIterator, Generator
from dataclasses import dataclass, field


# ── Message dataclass ─────────────────────────────────────────────────────────

@dataclass
class AgentEvent:
    """Normalised event from the Agent SDK message stream."""
    kind: str          # "text" | "tool_call" | "tool_result" | "error" | "done" | "mcp_init"
    content: str = ""
    tool_name: str = ""
    meta: dict = field(default_factory=dict)


# ── Message parser ────────────────────────────────────────────────────────────

def parse_message(msg) -> list[AgentEvent]:
    """
    Convert a raw claude_agent_sdk message into a list of AgentEvents.
    Handles: AssistantMessage, ResultMessage, SystemMessage, ErrorMessage.
    """
    events: list[AgentEvent] = []
    msg_type = getattr(msg, "type", None)

    if msg_type == "system":
        subtype = getattr(msg, "subtype", "")
        if subtype == "init":
            servers = getattr(msg, "mcp_servers", [])
            events.append(AgentEvent(
                kind="mcp_init",
                content=f"Connected MCP servers: {[s.name if hasattr(s,'name') else str(s) for s in servers]}",
                meta={"servers": servers}
            ))

    elif msg_type == "assistant":
        message = getattr(msg, "message", None)
        if message:
            for block in getattr(message, "content", []):
                btype = getattr(block, "type", "")
                if btype == "text":
                    events.append(AgentEvent(kind="text", content=block.text))
                elif btype == "tool_use":
                    import json
                    events.append(AgentEvent(
                        kind="tool_call",
                        tool_name=block.name,
                        content=json.dumps(getattr(block, "input", {}), indent=2),
                        meta={"id": block.id}
                    ))

    elif msg_type == "tool_result":
        content_blocks = getattr(msg, "content", [])
        text = " ".join(
            b.text for b in content_blocks if getattr(b, "type", "") == "text"
        )
        events.append(AgentEvent(kind="tool_result", content=text))

    elif msg_type == "result":
        subtype = getattr(msg, "subtype", "")
        if subtype == "success":
            result = getattr(msg, "result", "")
            if result:
                events.append(AgentEvent(kind="text", content=result))
            events.append(AgentEvent(kind="done", content="✅ Agent finished"))
        else:
            events.append(AgentEvent(kind="error", content=f"Agent error: {subtype}"))

    return events


# ── Thread-safe async runner ──────────────────────────────────────────────────

def run_agent_sync(
    coro_factory,          # callable returning an async-generator
) -> Generator[AgentEvent, None, None]:
    """
    Run an async agent coroutine from synchronous Streamlit code.
    Yields AgentEvents one by one.

    Usage:
        for event in run_agent_sync(lambda: query(prompt, options=...)):
            ...
    """
    import queue

    q: queue.Queue = queue.Queue()
    _SENTINEL = object()

    def worker():
        async def _run():
            try:
                async for msg in coro_factory():
                    for event in parse_message(msg):
                        q.put(event)
            except Exception as exc:
                q.put(AgentEvent(kind="error", content=str(exc)))
            finally:
                q.put(_SENTINEL)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_run())
        finally:
            loop.close()

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    while True:
        item = q.get()
        if item is _SENTINEL:
            break
        yield item


# ── Streamlit UI helpers ──────────────────────────────────────────────────────

import streamlit as st

STYLE = """
<style>
.event-tool-call {
    background:#0f172a; border-left:3px solid #6c8eff;
    border-radius:6px; padding:10px 14px; margin:6px 0;
    font-family:'JetBrains Mono',monospace; font-size:12px;
}
.event-tool-result {
    background:#0f1a0f; border-left:3px solid #34d399;
    border-radius:6px; padding:10px 14px; margin:6px 0;
    font-family:'JetBrains Mono',monospace; font-size:12px;
}
.event-mcp-init {
    background:#1a1200; border-left:3px solid #fbbf24;
    border-radius:6px; padding:10px 14px; margin:6px 0;
    font-size:12px;
}
.event-error {
    background:#1f0a0a; border-left:3px solid #f87171;
    border-radius:6px; padding:10px 14px; margin:6px 0;
}
.badge {
    display:inline-block; padding:2px 8px; border-radius:20px;
    font-size:11px; font-weight:600; margin-right:6px;
}
.badge-tool  { background:#1e2a4a; color:#6c8eff; }
.badge-result{ background:#0d2a1a; color:#34d399; }
.badge-mcp   { background:#2a1e00; color:#fbbf24; }
.badge-error { background:#2a0d0d; color:#f87171; }
</style>
"""

def inject_styles():
    st.markdown(STYLE, unsafe_allow_html=True)


def render_event(event: AgentEvent, container=None):
    """Render a single AgentEvent in the Streamlit UI."""
    target = container or st

    if event.kind == "text":
        target.markdown(event.content)

    elif event.kind == "tool_call":
        target.markdown(f"""
<div class="event-tool-call">
  <span class="badge badge-tool">⚡ TOOL CALL</span>
  <strong>{event.tool_name}</strong><br>
  <pre style="margin:8px 0 0; color:#94a3b8;">{event.content}</pre>
</div>
""", unsafe_allow_html=True)

    elif event.kind == "tool_result":
        short = event.content[:300] + ("…" if len(event.content) > 300 else "")
        target.markdown(f"""
<div class="event-tool-result">
  <span class="badge badge-result">✓ RESULT</span>
  <pre style="margin:6px 0 0; color:#86efac;">{short}</pre>
</div>
""", unsafe_allow_html=True)

    elif event.kind == "mcp_init":
        target.markdown(f"""
<div class="event-mcp-init">
  <span class="badge badge-mcp">🔗 MCP</span> {event.content}
</div>
""", unsafe_allow_html=True)

    elif event.kind == "error":
        target.markdown(f"""
<div class="event-error">
  <span class="badge badge-error">✗ ERROR</span> {event.content}
</div>
""", unsafe_allow_html=True)

    elif event.kind == "done":
        target.success(event.content)


def sidebar_api_key() -> str | None:
    """Render API key input in sidebar, return key or None."""
    import os
    st.sidebar.markdown("### 🔑 API Key")
    key = st.sidebar.text_input(
        "ANTHROPIC_API_KEY",
        value=os.environ.get("ANTHROPIC_API_KEY", ""),
        type="password",
        help="Your Anthropic API key. Set ANTHROPIC_API_KEY env var to pre-fill.",
    )
    if key:
        os.environ["ANTHROPIC_API_KEY"] = key
        return key
    st.sidebar.warning("Enter your API key to run agents.")
    return None
