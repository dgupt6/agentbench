# C++ Multi-Subagent Pipeline

Two-subagent Claude Agent SDK example that generates and reviews C++ transformation code.

## Files

```
cpp_agent/
├── cpp_multi_agent.py   # Pure Python CLI pipeline
├── cpp_agent_app.py     # Streamlit UI version
└── README.md
```

## Setup

```bash
pip install claude-agent-sdk streamlit
export ANTHROPIC_API_KEY=sk-ant-...
```

## Run CLI

```bash
python cpp_multi_agent.py
```

## Run Streamlit UI

```bash
streamlit run cpp_agent_app.py
```

## Architecture

```
Orchestrator (claude-sonnet)
    │  allowed_tools: ["Task"]
    │
    ├─► AgentDefinition: cpp-code-generator  (sonnet)
    │       tools: []
    │       → transform.h
    │       → transform.cpp
    │       → main_example.cpp
    │
    └─► AgentDefinition: cpp-code-reviewer   (opus)
            tools: []
            → structured review with severity ratings
            → score out of 10
```

## Key SDK Concepts

```python
from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, query

# Define subagents
generator = AgentDefinition(
    description="When to use this agent (Claude reads this to decide)",
    prompt="System prompt / persona for this subagent",
    tools=[],          # which tools this subagent can use
    model="sonnet",    # each subagent can use a different model
)

# Orchestrator options
options = ClaudeAgentOptions(
    system_prompt="Orchestration instructions...",
    agents=[generator, reviewer],
    allowed_tools=["Task"],   # REQUIRED: enables subagent spawning
    model="sonnet",
)

# Run
async for msg in query(prompt="...", options=options):
    ...
```
