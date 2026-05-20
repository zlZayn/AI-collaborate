# AI Collaborate

Multi-agent LLM orchestration with automated planning, parallel dispatch, and synthesis.

## Structure

```text
├── orchestrator.py                  # main harness: plan -> dispatch -> loop
├── run_web.py                       # web interface launcher
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
│   ├── broadcaster.py               # SSE event bus
│   ├── constants.py                 # shared status constants
│   ├── log.py                       # logging utilities
│   └── safe_name.py                 # filename sanitizer
├── web/
│   ├── server.py                    # HTTP + SSE server (stdlib only)
│   ├── runner.py                    # web runner reusing lib modules
│   ├── index.html                   # single-page UI
│   └── static/                      # marked.js, KaTeX (local)
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

# web interface
python run_web.py
# open http://localhost:8080
```

## Key Design

**Staged dispatch.** Same-stage agents run in parallel; stages execute sequentially. Later stages see context from earlier ones. Unlimited stages and agents per stage — Planner decides the right decomposition depth. Dispatch runs in a background thread so the interactive loop starts immediately — `/status` works during execution.

**Bridge context.** Between stages, a lightweight LLM call (configurable via `pipeline.bridge`) reads all prior-stage outputs and produces a focused context summary for the next stage. Bridge output is saved to disk and recorded in `state.json`. If no bridge config is present, falls back to simple truncation.

**Status lifecycle.** Each run transitions through four states: `pending` -> `running` -> `done` / `error`. Status is persisted in `state.json` (including `status`, `summary_status`, `summary`, `continues`), so Web UI survives page refresh and server restart. `/status` displays counts, per-agent marks (`+` done, `-` running, `!` error, space pending), and continues.

**Error isolation.** Per-agent API failures are caught and marked as `error` — they never contaminate bridge context or summary. If all agents in a stage fail, the pipeline stops to avoid wasting downstream calls. Plan failure (3 retries exhausted) exits cleanly without entering the interactive loop.

**Plan validation with retry.** Planner output is parsed as strict JSON and validated (required fields, model pool membership, value ranges). On failure, specific errors are fed back conversationally, up to 3 retries.

**Human framing.** All prompts use human terms — colleagues, not "AI agents". Agents receive tasks without knowing the sender is another model, keeping outputs role-appropriate.

## Web Interface

`python run_web.py` starts an HTTP server (default port 8080, configurable via `web_port` in config). Enter a goal in the bottom input bar — same workflow as CLI, displayed as collapsible cards. Content is read from local files on disk (not SSE chunks) for reliability. Markdown and TeX (`$...$` / `$$...$$`) render via bundled marked.js and KaTeX. Original CLI (`orchestrator.py`) is unchanged.

**Unified card system.** Stage, Agent, Bridge, Summary, Continue share a single CSS card base with variant modifiers. All icons are inline SVG (16x16, stroke-based) — no emoji. Four status states (done/running/error/pending) each have a distinct SVG shape with coordinated animations.

**State recovery.** `state.json` is the single source of truth. Page refresh restores all cards, continues, and summary. Empty state shows a clickable history list (`/api/runs`). Loading a historical run restores the full view including summary and followup capability.

**Followup (continue).** After summary completes, type a followup question. A continue card appears immediately with streaming content. Continue entries are persisted in `state.json` with their own status lifecycle.
