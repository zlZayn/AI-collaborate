# AI Collaborate

Multi-agent LLM orchestration with automated planning, parallel dispatch, and synthesis.

## Structure

```text
├── orchestrator.py                  # main harness: plan -> dispatch -> loop
├── config_orchestrator.json         # orchestrator config (gitignored)
├── config_orchestrator_example.json # orchestrator config example
├── mini_panel.py                    # minimal multi-agent chain (no planner)
├── config_mini_panel.json           # mini_panel config (gitignored)
├── config_mini_panel_example.json   # mini_panel config example
├── lib/
│   ├── client.py                    # LLM client wrapper
│   ├── planner.py                   # plan parsing + schema validation
│   ├── dispatcher.py                # staged dispatch runner
│   ├── context.py                   # context builder (loop mode)
│   ├── summarizer.py                # final synthesis
│   ├── constants.py                 # shared status constants
│   ├── log.py                       # logging utilities
│   └── safe_name.py                 # filename sanitizer
├── docs/
│   ├── naming_proposal.md           # naming conventions
│   └── stage_dispatch_plan.md       # stage dispatch design
└── output/                          # all run outputs (gitignored)
```

## Setup

1. Copy an example config and remove the `_example` suffix:

   ```bash
   cp config_orchestrator_example.json config_orchestrator.json
   # or
   cp config_mini_panel_example.json config_mini_panel.json
   ```

2. Open the copied file and fill in your API key and other settings.

## Usage

```bash
# orchestrator (multi-agent with planning)
python orchestrator.py

# mini_panel (minimal multi-agent chain)
python mini_panel.py
```

## Key Design

**Staged dispatch.** Same-stage agents run in parallel; stages execute sequentially. Later stages see context from earlier ones. Unlimited stages and agents per stage — Planner decides the right decomposition depth. Dispatch runs in a background thread so the interactive loop starts immediately — `/status` works during execution.

**Bridge context.** Between stages, a lightweight LLM call (configurable via `pipeline.bridge`) reads all prior-stage outputs and produces a focused context summary for the next stage. Bridge output is saved to disk and recorded in `state.json`. If no bridge config is present, falls back to simple truncation.

**Status lifecycle.** Each run transitions through four states: `pending` -> `running` -> `done` / `error`. `/status` displays counts and per-agent marks (`+` done, `-` running, `!` error, space pending).

**Error isolation.** Per-agent API failures are caught and marked as `error` — they never contaminate bridge context or summary. If all agents in a stage fail, the pipeline stops to avoid wasting downstream calls. Plan failure (3 retries exhausted) exits cleanly without entering the interactive loop.

**Plan validation with retry.** Planner output is parsed as strict JSON and validated (required fields, model pool membership, value ranges). On failure, specific errors are fed back conversationally, up to 3 retries.

**Human framing.** All prompts use human terms — colleagues, not "AI agents". Agents receive tasks without knowing the sender is another model, keeping outputs role-appropriate.
