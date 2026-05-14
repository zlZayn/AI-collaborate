# AI Collaborate

Multi-agent LLM orchestration with automated planning, parallel dispatch, and synthesis.

## Structure

```text
├── orchestrator.py              # main harness: plan -> dispatch -> loop
├── config_orchestrator.json     # orchestrator config (gitignored)
├── config_orchestrator_example.json  # orchestrator config example
├── mini_panel.py                # minimal multi-agent chain (no planner)
├── config_mini_panel.json       # mini_panel config (gitignored)
├── config_mini_panel_example.json  # mini_panel config example
├── lib/
│   ├── client.py                # LLM client wrapper
│   ├── planner.py               # plan parsing + schema validation
│   ├── dispatcher.py            # background task runner
│   ├── context.py               # context builder
│   └── summarizer.py            # final synthesis
└── output/                      # all run outputs (gitignored)
```

## Usage

```bash
# orchestrator (multi-agent with planning)
python orchestrator.py

# mini_panel (minimal multi-agent chain)
python mini_panel.py
```

Edit `config_orchestrator.json` or `config_mini_panel.json` before running. Copy the example files as starting points.

## Key Design

**Per-stage temperature.** Plan model runs at 0.2 for consistent JSON output. Chat model at 0.7 for balanced conversation. Planner assigns each agent a temperature (0.0--1.0) based on task nature. Summary always at 0 for deterministic synthesis.

**Strict plan validation with retry.** Planner output is parsed as strict JSON and validated against the schema (required fields, model pool membership, value ranges). On failure, specific errors are fed back to the model conversationally, up to 3 retries. No silent fallbacks.

**Human-collaboration framing.** Prompts are written as if a human manager is briefing human colleagues — no "you are an AI assistant" identity language. Agents receive tasks without knowing the sender is another model, keeping outputs natural and role-appropriate.
