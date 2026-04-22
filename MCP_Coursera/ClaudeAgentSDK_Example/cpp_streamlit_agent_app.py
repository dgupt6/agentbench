"""
cpp_agent_app.py  —  Streamlit UI for the C++ Multi-Agent Pipeline
Run with:  streamlit run cpp_agent_app.py
"""

import asyncio
import os
import textwrap
import threading
import queue as Q
from dataclasses import dataclass, field

import streamlit as st

st.set_page_config(
    page_title="C++ Agent Pipeline",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');

:root {
  --bg:       #0b0d11;
  --surface:  #13161d;
  --border:   #1f2433;
  --accent:   #00d4aa;
  --accent2:  #4d9eff;
  --orange:   #ff8c42;
  --red:      #ff5252;
  --yellow:   #ffd166;
  --text:     #dde3f0;
  --muted:    #5a6480;
  --mono:     'IBM Plex Mono', monospace;
  --sans:     'IBM Plex Sans', sans-serif;
}
html, body, [class*="css"] {
  font-family: var(--sans) !important;
  background: var(--bg) !important;
  color: var(--text) !important;
}
section[data-testid="stSidebar"] {
  background: var(--surface) !important;
  border-right: 1px solid var(--border) !important;
}
/* inputs */
.stTextInput>div>div>input,
.stTextArea>div>div>textarea {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 6px !important;
  color: var(--text) !important;
  font-family: var(--mono) !important;
  font-size: 12.5px !important;
}
/* buttons */
.stButton>button {
  background: linear-gradient(135deg, #00d4aa18, #4d9eff18) !important;
  border: 1px solid var(--accent) !important;
  color: var(--accent) !important;
  font-family: var(--sans) !important;
  font-weight: 600 !important;
  border-radius: 6px !important;
  letter-spacing: .04em !important;
  transition: all .2s !important;
}
.stButton>button:hover {
  background: linear-gradient(135deg, #00d4aa30, #4d9eff30) !important;
}
div[data-testid="stHorizontalBlock"] { gap: 12px !important; }
code, pre { font-family: var(--mono) !important; }
hr { border-color: var(--border) !important; }
.stSpinner>div { border-top-color: var(--accent) !important; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("""
<div style="padding:4px 0 16px;">
  <div style="font-size:22px; font-weight:700; letter-spacing:-.02em;">
    ⚙️ C++ Agent Pipeline
  </div>
  <div style="color:#5a6480; font-size:12px; margin-top:4px;">
    Claude Agent SDK · Two Subagents
  </div>
</div>
""", unsafe_allow_html=True)

api_key = st.sidebar.text_input(
    "ANTHROPIC_API_KEY",
    value=os.environ.get("ANTHROPIC_API_KEY", ""),
    type="password",
)
if api_key:
    os.environ["ANTHROPIC_API_KEY"] = api_key

st.sidebar.markdown("---")
st.sidebar.markdown("### Agent Models")
gen_model  = st.sidebar.selectbox("Generator model",  ["sonnet", "opus", "haiku"], index=0)
rev_model  = st.sidebar.selectbox("Reviewer model",   ["opus", "sonnet", "haiku"], index=0)
max_turns  = st.sidebar.slider("Max turns", 10, 40, 20)

st.sidebar.markdown("---")
st.sidebar.markdown("""
### Pipeline
```
Orchestrator (sonnet)
    │
    ├─► cpp-code-generator
    │       writes transform.h
    │       writes transform.cpp
    │       writes main_example.cpp
    │
    └─► cpp-code-reviewer
            reviews all 3 files
            scores + feedback
```
""")


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="
  background:linear-gradient(135deg,#13161d,#161d2a);
  border:1px solid #1f2433; border-radius:14px;
  padding:32px 40px; margin-bottom:28px; position:relative; overflow:hidden;
">
  <div style="
    position:absolute;top:-50px;right:-50px;
    width:180px;height:180px;
    background:radial-gradient(circle,rgba(0,212,170,.12) 0%,transparent 70%);
    border-radius:50%;
  "></div>
  <h1 style="margin:0;font-size:26px;font-weight:700;letter-spacing:-.02em;">
    C++ Multi-Subagent Pipeline
  </h1>
  <p style="margin:8px 0 0;color:#5a6480;font-size:14px;max-width:560px;line-height:1.6;">
    Define an input struct and output struct — the <strong style="color:#00d4aa">generator agent</strong>
    writes the transformation code, then the <strong style="color:#4d9eff">reviewer agent</strong>
    audits it for bugs, safety, and style.
  </p>
</div>
""", unsafe_allow_html=True)


# ── Default examples ──────────────────────────────────────────────────────────
DEFAULT_INPUT = """\
struct SensorReading {
    std::string sensor_id;
    double      raw_value;       // raw ADC reading 0–4095
    double      temperature_c;  // ambient temperature
    int64_t     timestamp_ms;   // Unix epoch ms
    bool        is_calibrated;
};"""

DEFAULT_OUTPUT = """\
struct NormalizedReading {
    std::string sensor_id;
    double      normalized_value; // raw mapped to [0.0, 1.0]
    double      corrected_value;  // temperature-compensated
    std::string iso_timestamp;    // ISO-8601 UTC string
    std::string quality_label;    // "GOOD" | "DEGRADED" | "BAD"
};"""

DEFAULT_DESC = """\
- normalized_value = raw_value / 4095.0
- corrected_value  = normalized_value minus (temperature_c - 25.0)*0.002, clamped [0,1]
- iso_timestamp    = convert timestamp_ms to ISO-8601 UTC string
- quality_label:
    "GOOD"     if is_calibrated AND corrected_value in [0.05, 0.95]
    "DEGRADED" if not calibrated OR value near edges [0.01,0.05)|(0.95,0.99]
    "BAD"      otherwise"""


# ── Input form ────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 📥 Input Struct")
    input_struct = st.text_area(
        "input_struct",
        value=DEFAULT_INPUT,
        height=200,
        label_visibility="collapsed",
    )

with col2:
    st.markdown("#### 📤 Output Struct")
    output_struct = st.text_area(
        "output_struct",
        value=DEFAULT_OUTPUT,
        height=200,
        label_visibility="collapsed",
    )

st.markdown("#### 📝 Transformation Description")
description = st.text_area(
    "description",
    value=DEFAULT_DESC,
    height=130,
    label_visibility="collapsed",
    placeholder="Describe in plain English what each field should contain…",
)

run_btn = st.button(
    "▶  Run Pipeline  (Generate → Review)",
    disabled=not api_key,
    use_container_width=True,
)


# ── Agent runner (thread-safe async bridge) ───────────────────────────────────
@dataclass
class PipelineEvent:
    kind: str       # "spawn" | "text" | "done" | "error"
    content: str = ""
    agent: str = ""


def run_pipeline_sync(input_s, output_s, desc, gen_m, rev_m, turns) -> Q.Queue:
    """Spawn pipeline in background thread; return a queue of PipelineEvents."""
    q: Q.Queue = Q.Queue()
    SENTINEL = object()

    def worker():
        async def _run():
            try:
                from claude_agent_sdk import (
                    AgentDefinition, ClaudeAgentOptions, query,
                    AssistantMessage, ResultMessage, TextBlock,
                )

                generator_agent = AgentDefinition(
                    description=(
                        "Use this agent when you need to generate C++ source code "
                        "from a given input struct and output struct definition. "
                        "It writes transform.h, transform.cpp, and main_example.cpp."
                    ),
                    prompt=textwrap.dedent(f"""\
                        You are a senior C++ engineer (C++17/20).

                        Produce exactly three files for the transformation function:

                        1. transform.h   — #pragma once, includes, both struct
                           definitions, and the function declaration:
                             OutputStruct transform(const InputStruct& input);

                        2. transform.cpp — full implementation, each field mapping
                           commented, proper edge-case handling.

                        3. main_example.cpp — minimal main() with a sample call
                           and std::cout of every output field.

                        Rules:
                        • const-ref inputs, value-return output
                        • std::string over char*; no raw new/delete
                        • Doxygen comments on every function
                        • Wrap each file in a labelled code fence:
                            ```cpp  // transform.h
                            ...
                            ```
                    """),
                    tools=[],
                    model=gen_m,
                )

                reviewer_agent = AgentDefinition(
                    description=(
                        "Use this agent to review C++ code for correctness, "
                        "memory safety, performance, and modern C++ best practices. "
                        "Returns structured feedback with severity ratings and score."
                    ),
                    prompt=textwrap.dedent("""\
                        You are a C++ code review expert (CppCoreGuidelines / Google Style).

                        Produce a structured review with these EXACT sections:

                        ## Summary
                        One-paragraph overall assessment.

                        ## ✅ Strengths
                        Bullet list of what the code does well.

                        ## 🐛 Bugs & Correctness Issues
                        SEVERITY [CRITICAL|HIGH|MEDIUM|LOW] — file — description — fix

                        ## ⚠️ Memory & Resource Safety
                        RAII violations, leaks, dangling refs, UB.

                        ## ⚡ Performance
                        Unnecessary copies, missed moves, suboptimal algorithms.

                        ## 🎨 Style & Readability
                        Naming, comments, magic numbers, formatting.

                        ## 🔧 Top 3 Fixes
                        Concrete, copy-pasteable code snippets.

                        ## Score
                        Overall: X/10
                        Correctness X/10 | Safety X/10 | Performance X/10 | Style X/10
                    """),
                    tools=[],
                    model=rev_m,
                )

                options = ClaudeAgentOptions(
                    system_prompt=textwrap.dedent("""\
                        You are a C++ development orchestrator.

                        PIPELINE (follow in order):

                        STEP 1 — delegate to cpp-code-generator agent with the
                                 InputStruct, OutputStruct, and description.
                                 Capture all three generated files.

                        STEP 2 — delegate to cpp-code-reviewer agent with the
                                 FULL text of all three files from Step 1.

                        STEP 3 — produce a final report:
                          ### Generated Code
                          (all three files)

                          ### Code Review
                          (full review output)

                          ### Next Steps
                          (3 bullet points before merging)

                        Complete all steps before responding.
                    """),
                    agents=[generator_agent, reviewer_agent],
                    allowed_tools=["Task"],
                    model="sonnet",
                    max_turns=turns,
                )

                prompt = textwrap.dedent(f"""\
                    Generate a C++ transformation function and review it.

                    ## Input Struct
                    ```cpp
                    {input_s.strip()}
                    ```

                    ## Output Struct
                    ```cpp
                    {output_s.strip()}
                    ```

                    ## Transformation Description
                    {desc.strip()}

                    Follow the full pipeline: generate → review → final report.
                """)

                final_text = ""
                async for msg in query(prompt=prompt, options=options):
                    msg_type = getattr(msg, "type", None)

                    # Detect subagent spawns
                    if msg_type == "assistant":
                        for block in getattr(
                            getattr(msg, "message", None), "content", []
                        ):
                            if getattr(block, "type", "") == "tool_use" and block.name == "Task":
                                inp = getattr(block, "input", {})
                                agent_name = inp.get("agent", "subagent")
                                preview = str(inp.get("prompt", ""))[:80]
                                q.put(PipelineEvent(
                                    kind="spawn",
                                    agent=agent_name,
                                    content=preview,
                                ))
                        # Capture text
                        text = "".join(
                            b.text for b in getattr(
                                getattr(msg, "message", None), "content", []
                            )
                            if getattr(b, "type", "") == "text"
                        )
                        if text:
                            final_text = text

                    if msg_type == "result":
                        sub = getattr(msg, "subtype", "")
                        if sub == "success":
                            result = getattr(msg, "result", "") or final_text
                            q.put(PipelineEvent(kind="done", content=result))
                        else:
                            q.put(PipelineEvent(kind="error", content=sub))

            except Exception as exc:
                q.put(PipelineEvent(kind="error", content=str(exc)))
            finally:
                q.put(SENTINEL)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_run())
        finally:
            loop.close()

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    def drain():
        while True:
            item = q.get()
            if item is SENTINEL:
                break
            yield item

    return drain()


# ── Run ───────────────────────────────────────────────────────────────────────
if run_btn and api_key:
    st.markdown("---")

    # Agent status strip
    status_col1, status_col2, status_col3 = st.columns(3)

    def agent_card(col, icon, label, color, state):
        col.markdown(f"""
        <div style="
          background:#13161d; border:1px solid {color}40;
          border-radius:10px; padding:14px; text-align:center;
        ">
          <div style="font-size:22px;">{icon}</div>
          <div style="font-weight:600; font-size:12px; margin:4px 0 2px;">{label}</div>
          <span style="
            background:{color}15; color:{color};
            padding:2px 10px; border-radius:20px; font-size:10px; font-weight:700;
          ">{state}</span>
        </div>
        """, unsafe_allow_html=True)

    orch_box  = status_col1.empty()
    gen_box   = status_col2.empty()
    rev_box   = status_col3.empty()

    def refresh_cards(orch_s, gen_s, rev_s):
        with orch_box.container():
            agent_card(status_col1, "🎯", "Orchestrator", "#4d9eff", orch_s)
        with gen_box.container():
            agent_card(status_col2, "⚙️", "cpp-code-generator", "#00d4aa", gen_s)
        with rev_box.container():
            agent_card(status_col3, "🔍", "cpp-code-reviewer", "#ff8c42", rev_s)

    refresh_cards("RUNNING", "WAITING", "WAITING")

    log_area    = st.empty()
    result_area = st.container()
    log_lines   = []

    def add_log(line: str):
        log_lines.append(line)
        log_area.markdown(
            "<div style='background:#0b0d11;border:1px solid #1f2433;"
            "border-radius:8px;padding:12px 16px;font-family:IBM Plex Mono,monospace;"
            f"font-size:11.5px;color:#5a6480;max-height:160px;overflow:auto;'>"
            + "<br>".join(log_lines[-12:]) + "</div>",
            unsafe_allow_html=True,
        )

    add_log("⏳  Pipeline starting…")

    gen_done = False
    rev_done = False
    final_output = ""

    with st.spinner("Agents working…"):
        for event in run_pipeline_sync(
            input_struct, output_struct, description,
            gen_model, rev_model, max_turns
        ):
            if event.kind == "spawn":
                name = event.agent.lower()
                add_log(f"⚡ Spawning [{event.agent}] → {event.content}…")
                if "generator" in name or "gen" in name:
                    refresh_cards("RUNNING", "RUNNING", "WAITING")
                elif "reviewer" in name or "review" in name:
                    gen_done = True
                    refresh_cards("RUNNING", "DONE ✓", "RUNNING")

            elif event.kind == "done":
                final_output = event.content
                add_log("✅  Pipeline complete")
                refresh_cards("DONE ✓", "DONE ✓", "DONE ✓")

            elif event.kind == "error":
                add_log(f"❌  Error: {event.content}")
                st.error(f"Pipeline error: {event.content}")

    # ── Render output ──────────────────────────────────────────────────────
    if final_output:
        st.markdown("---")
        st.markdown("## 📋 Pipeline Output")

        # Split into Generated Code vs Review sections if possible
        if "### Generated Code" in final_output or "### Code Review" in final_output:
            parts = final_output.split("### ")
            for part in parts:
                if not part.strip():
                    continue
                lines = part.strip().splitlines()
                section_title = lines[0].strip()
                section_body  = "\n".join(lines[1:]).strip()

                icon = {
                    "Generated Code": "⚙️",
                    "Code Review":    "🔍",
                    "Next Steps":     "🚀",
                }.get(section_title, "📄")

                with st.expander(f"{icon}  {section_title}", expanded=True):
                    st.markdown(section_body)
        else:
            st.markdown(final_output)
