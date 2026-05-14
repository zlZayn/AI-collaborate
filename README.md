# AI Collaborate

Multi-agent LLM orchestration with automated planning, parallel dispatch, and synthesis.

## Structure

```text
├── orchestrator.py              # main harness: plan -> dispatch -> loop
├── ai_explainer.py              # standalone single-question panel
├── config_orchestrator.json     # orchestrator config
├── config.json                  # ai_explainer config
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

# simple panel (fixed 3-perspective chain)
python ai_explainer.py
```

Edit `config_orchestrator.json` or `config.json` before running.

## Key Design

**Per-agent temperature.** The planner assigns each agent a temperature (0.0--1.0) based on task nature — factual extraction, balanced analysis, or creative发散. The summary always runs at temperature 0 for deterministic output.

**Strict plan validation with retry.** Planner output is parsed as strict JSON and validated against the schema (required fields, model pool membership, value ranges). On failure, specific errors are fed back to the model conversationally, up to 3 retries. No silent fallbacks.

**Human-collaboration framing.** Prompts are written as if a human manager is briefing human colleagues — no "you are an AI assistant" identity language. Agents receive tasks without knowing the sender is another model, keeping outputs natural and role-appropriate.
