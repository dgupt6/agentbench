"""
cpp_multi_agent.py
──────────────────
Two-subagent pipeline using Claude Agent SDK:

  SubAgent 1 — cpp-code-generator
      Takes a C++ input struct + output struct definition and generates
      a complete, idiomatic C++ function that transforms input → output.

  SubAgent 2 — cpp-code-reviewer
      Reviews C++ code for correctness, memory safety, style, and
      best practices; returns structured feedback.

Orchestrator flow:
  1. User provides InputStruct, OutputStruct, and a description.
  2. Orchestrator calls cpp-code-generator → gets generated .cpp/.h files.
  3. Orchestrator calls cpp-code-reviewer  → reviews the generated code.
  4. Final report is printed to stdout.
"""

import asyncio
import os
import textwrap
from pathlib import Path

from claude_agent_sdk import (
    AgentDefinition,
    ClaudeAgentOptions,
    query,
    AssistantMessage,
    ResultMessage,
    TextBlock,
)


# ── Subagent definitions ──────────────────────────────────────────────────────

CPP_GENERATOR_AGENT = AgentDefinition(
    # Claude reads this description to decide WHEN to delegate to this agent.
    description=(
        "Use this agent when you need to generate C++ source code from a given "
        "input struct and output struct definition. It writes the transformation "
        "function, header file, and a usage example."
    ),
    prompt=textwrap.dedent("""\
        You are a senior C++ engineer specialising in modern C++ (C++17/20).

        You will be given:
          • An INPUT struct definition (name + fields)
          • An OUTPUT struct definition (name + fields)
          • A short description of what the transformation should do

        Your job is to produce THREE artefacts:

        1. HEADER FILE  (transform.h)
           - #pragma once guard
           - All required #includes
           - Both struct definitions (or forward declarations)
           - Declaration of the transform function:
               OutputStruct transform(const InputStruct& input);

        2. SOURCE FILE  (transform.cpp)
           - #include "transform.h"
           - Full implementation of transform()
           - Each field mapping commented with a one-liner explaining the logic
           - Proper handling of edge cases (empty strings, zero values, nulls)

        3. USAGE EXAMPLE  (main_example.cpp)
           - A minimal main() that constructs a sample InputStruct,
             calls transform(), and prints every field of the result

        Rules:
          • Use const-references for inputs, value-return for output
          • Prefer std::string over char*
          • No raw new/delete — use value types or smart pointers
          • No external dependencies beyond the C++ standard library
          • Every function must have a Doxygen-style comment block
          • Wrap output in clearly labelled code fences:
              ```cpp  // transform.h
              ...
              ```
              ```cpp  // transform.cpp
              ...
              ```
              ```cpp  // main_example.cpp
              ...
              ```
    """),
    tools=[],          # pure generation — no filesystem tools needed
    model="sonnet",
)


CPP_REVIEWER_AGENT = AgentDefinition(
    description=(
        "Use this agent to review C++ code for correctness, memory safety, "
        "performance, style, and adherence to modern C++ best practices. "
        "Provide structured, actionable feedback."
    ),
    prompt=textwrap.dedent("""\
        You are a C++ code review expert with deep knowledge of:
          • Modern C++ (C++11/14/17/20) idioms and best practices
          • Memory safety and RAII principles
          • Performance and zero-cost abstractions
          • Google C++ Style Guide and CppCoreGuidelines

        You will receive C++ source code to review.

        Produce a structured review with these EXACT sections:

        ## Summary
        One paragraph overall assessment (quality, readability, correctness).

        ## ✅ Strengths
        Bullet list of what the code does well.

        ## 🐛 Bugs & Correctness Issues
        Each issue on its own line:
          SEVERITY [CRITICAL|HIGH|MEDIUM|LOW] — file:line — description — suggested fix

        ## ⚠️  Memory & Resource Safety
        Any RAII violations, leaks, dangling references, or undefined behaviour.

        ## ⚡ Performance
        Unnecessary copies, missed move semantics, suboptimal algorithms.

        ## 🎨 Style & Readability
        Naming, comments, formatting, magic numbers, etc.

        ## 🔧 Recommended Changes
        Concrete, copy-pasteable code snippets for the top 3 most impactful fixes.

        ## Score
        Overall: X/10  (where 10 = production-ready, no changes needed)
        Breakdown: Correctness X/10 | Safety X/10 | Performance X/10 | Style X/10

        Be constructive, specific, and reference line numbers where possible.
    """),
    tools=[],          # pure analysis
    model="opus",      # deeper reasoning for thorough review
)


# ── Orchestrator options ──────────────────────────────────────────────────────

def build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=textwrap.dedent("""\
            You are a C++ development orchestrator.

            When given a task involving C++ struct transformation, follow this pipeline:

            STEP 1 — Code Generation
              Delegate to the cpp-code-generator agent with the exact InputStruct
              definition, OutputStruct definition, and transformation description.
              Wait for the complete header + source + example files.

            STEP 2 — Code Review
              Pass ALL generated code from Step 1 to the cpp-code-reviewer agent.
              Include the full file contents in the delegation prompt.

            STEP 3 — Final Report
              Combine both outputs into a final report with these sections:
                ### Generated Code
                (paste the three files from Step 1)

                ### Code Review
                (paste the full review from Step 2)

                ### Next Steps
                (2-3 bullet points on what to do before merging)

            Always complete all three steps before responding to the user.
        """),
        agents=[
            CPP_GENERATOR_AGENT,
            CPP_REVIEWER_AGENT,
        ],
        # Task MUST be in allowed_tools for subagents to be spawned
        allowed_tools=["Task"],
        model="sonnet",
        max_turns=20,   # enough turns for orchestrator → generator → reviewer → report
    )


# ── Message helpers ───────────────────────────────────────────────────────────

def extract_text(msg) -> str:
    """Pull plain text out of any SDK message type."""
    if isinstance(msg, AssistantMessage):
        return "".join(
            block.text
            for block in msg.content
            if isinstance(block, TextBlock)
        )
    if isinstance(msg, ResultMessage) and msg.subtype == "success":
        return msg.result or ""
    return ""


def print_banner(title: str) -> None:
    width = 70
    print("\n" + "═" * width)
    print(f"  {title}")
    print("═" * width)


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def run_pipeline(
    input_struct: str,
    output_struct: str,
    description: str,
) -> None:
    """
    Run the full generate → review pipeline.

    Args:
        input_struct:  C++ struct definition of the input type.
        output_struct: C++ struct definition of the output type.
        description:   Plain-English description of the transformation logic.
    """
    prompt = textwrap.dedent(f"""\
        Generate a C++ transformation function and then review the generated code.

        ## Input Struct
        ```cpp
        {input_struct.strip()}
        ```

        ## Output Struct
        ```cpp
        {output_struct.strip()}
        ```

        ## Transformation Description
        {description.strip()}

        Follow the full pipeline: generate → review → final report.
    """)

    print_banner("🤖  C++ Multi-Agent Pipeline  |  Claude Agent SDK")
    print(f"\n📥  Input  → {_first_line(input_struct)}")
    print(f"📤  Output → {_first_line(output_struct)}")
    print(f"📝  Task   → {description[:80]}{'…' if len(description) > 80 else ''}")
    print("\n⏳  Running agents…\n")

    options = build_options()
    final_text = ""

    async for msg in query(prompt=prompt, options=options):
        msg_type = getattr(msg, "type", None)

        # Show subagent spawn events
        if msg_type == "system":
            subtype = getattr(msg, "subtype", "")
            if subtype == "init":
                servers = getattr(msg, "mcp_servers", [])
                if servers:
                    print(f"  🔗 MCP servers: {[s.name for s in servers]}")

        # Track subagent task progress
        if msg_type == "assistant":
            for block in getattr(getattr(msg, "message", None), "content", []):
                if getattr(block, "type", "") == "tool_use":
                    name = block.name
                    if name == "Task":
                        inp = getattr(block, "input", {})
                        agent = inp.get("agent", "subagent")
                        desc = str(inp.get("prompt", ""))[:60]
                        print(f"  ⚡ Spawning [{agent}] — {desc}…")

        # Capture final result
        text = extract_text(msg)
        if text:
            final_text = text   # keep last non-empty text

        # Error handling
        if msg_type == "result" and getattr(msg, "subtype", "") != "success":
            print(f"\n❌  Agent error: {getattr(msg, 'subtype', 'unknown')}")
            return

    print_banner("📋  Final Report")
    print(final_text if final_text else "(no output received)")


def _first_line(s: str) -> str:
    return s.strip().splitlines()[0] if s.strip() else ""


# ── Example inputs ────────────────────────────────────────────────────────────

INPUT_STRUCT = """\
struct SensorReading {
    std::string sensor_id;
    double      raw_value;        // raw ADC reading 0–4095
    double      temperature_c;   // ambient temperature at time of reading
    int64_t     timestamp_ms;    // Unix epoch milliseconds
    bool        is_calibrated;
};
"""

OUTPUT_STRUCT = """\
struct NormalizedReading {
    std::string sensor_id;
    double      normalized_value; // raw_value mapped to [0.0, 1.0]
    double      corrected_value;  // normalized + temperature compensation
    std::string iso_timestamp;    // ISO-8601 string, e.g. "2024-01-15T10:30:00Z"
    std::string quality_label;    // "GOOD" | "DEGRADED" | "BAD"
};
"""

DESCRIPTION = """\
Convert a raw SensorReading into a NormalizedReading:
- normalized_value = raw_value / 4095.0
- corrected_value  = normalized_value adjusted by a linear temperature
  coefficient: subtract (temperature_c - 25.0) * 0.002 per degree deviation
  from 25 °C reference, then clamp to [0.0, 1.0]
- iso_timestamp    = convert timestamp_ms (Unix ms) to ISO-8601 UTC string
- quality_label:
    "GOOD"     if is_calibrated AND corrected_value in [0.05, 0.95]
    "DEGRADED" if not is_calibrated OR corrected_value in [0.01, 0.05) ∪ (0.95, 0.99]
    "BAD"      otherwise
"""


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is not set.\n"
            "Run: export ANTHROPIC_API_KEY=sk-ant-..."
        )

    asyncio.run(
        run_pipeline(
            input_struct=INPUT_STRUCT,
            output_struct=OUTPUT_STRUCT,
            description=DESCRIPTION,
        )
    )
