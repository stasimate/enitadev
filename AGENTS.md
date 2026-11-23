# AGENTS.md — Enita

Instructions for AI coding agents (Claude Code, GitHub Copilot, Cursor…) working in this repo.
Read this file fully before changing code. The functional spec is
[`docs/ANALISI_FUNZIONALE.md`](docs/ANALISI_FUNZIONALE.md) (in Italian); requirement IDs
(`RF-xx`, `RNF-xx`) referenced below come from there.

## What Enita is

An AI-driven language-learning simulator. **Split screen**: left = theory card, right =
AI-generated and AI-checked exercises. When an answer is wrong, the feedback points to the
exact rule (`rule_ref`) and the left pane highlights it.

- UI and explanations language: **Italian**. Target language: **English** (CEFR A1–B1).
- Single local user, no auth.
- Theory is **static markdown** first, RAG over the same files later.

## Repository layout

```
enitadev/
├── AGENTS.md                 ← this file
├── README.md                 ← install & run (must stay accurate)
├── docs/ANALISI_FUNZIONALE.md
├── content/en/topics/*.md    ← theory cards (source of truth for theory and rule_refs)
├── backend/                  ← Python 3.12, uv, FastAPI, datapizza-ai
│   ├── enita/
│   │   ├── api/              ← FastAPI routers (thin: no business logic)
│   │   ├── agent/            ← Tutor agent, LLM client factory, prompts
│   │   ├── mcp_server/       ← MCP server exposing Enita tools (stdio)
│   │   ├── guardrails/       ← input/output validation
│   │   ├── content/          ← markdown card loader/parser
│   │   ├── storage/          ← SQLite repository (attempts, profile)
│   │   ├── models.py         ← Pydantic schemas shared by API/agent/MCP
│   │   ├── settings.py       ← pydantic-settings, reads .env
│   │   └── main.py           ← FastAPI app factory
│   ├── evals/                ← eval set + runner (pass/fail exit code)
│   └── tests/
└── frontend/                 ← Angular 22 + Tailwind v4 (has its own AGENTS.md)
```

## Commands

| Task | Command (from the given dir) |
|---|---|
| Backend install | `backend/`: `uv sync` |
| Backend dev server | `backend/`: `uv run uvicorn enita.main:app --reload --port 8000` |
| MCP server (stdio) | `backend/`: `uv run python -m enita.mcp_server` |
| Backend tests | `backend/`: `uv run pytest` |
| Lint | `backend/`: `uv run ruff check .` |
| Evals (gate) | `backend/`: `uv run python -m evals.run` (exit ≠ 0 if score < 7/8) |
| Node version | root: `nvm use` (`.nvmrc` = 24; Angular 22 needs Node ≥ 24.15 or ≥ 22.22.3) |
| Frontend install | `frontend/`: `npm ci` |
| Frontend dev | `frontend/`: `npm start` → http://localhost:4200, proxies `/api` to :8000 |
| Frontend build | `frontend/`: `npm run build` |
| Frontend tests | `frontend/`: `npm test` |
| Everything | root: `docker compose up --build` |

Before saying a task is done: run the tests/build for the part you touched. If it
doesn't run, it isn't done (brief: "il progetto si considera completato solo se gira").

## Backend rules

- **Framework: datapizza-ai** (installed `datapizza-ai` 0.1.x). Use the real APIs:
  - Agent: `from datapizza.agents import Agent`
  - Tools: `from datapizza.tools import tool` (decorator)
  - MCP client: `from datapizza.tools.mcp_client import MCPClient`. Use it as an
    `async with MCPClient(command=..., args=[...]) as c: tools = await c.a_list_tools()`
    context manager for the stdio server.
  - Memory: `from datapizza.memory import Memory`
  - Tracing: `from datapizza.tracing import ContextTracing`
  - Clients: `datapizza.clients.openai.OpenAIClient`, `datapizza.clients.google.GoogleClient`,
    `datapizza.clients.anthropic.AnthropicClient`, `datapizza.clients.openai_like.OpenAILikeClient`
    (Ollama at `http://localhost:11434/v1`).
  - When unsure of a signature, **read the installed source** in
    `backend/.venv/lib/python3.12/site-packages/datapizza/`. Don't guess. The course lessons
    are the reference for usage patterns.
- MCP server: official `mcp` SDK (v2.x). Each tool has a typed signature, a docstring and
  Pydantic I/O.
- **LLM provider is never hardcoded.** Always go through `enita.agent.clients.get_client()`,
  which reads `ENITA_PROVIDER` / `ENITA_MODEL` (RF-30).
- **Closed exercises (fill-in, multiple choice) are checked deterministically**
  (normalize: lowercase, trim, collapse spaces, straight quotes). The LLM only explains.
  Never let the LLM decide correctness when an expected answer exists (RF-12).
- `Exercise.expected` must **never** be sent to the frontend. API response models exclude it.
- Every LLM output that drives app logic is parsed into a Pydantic model (structured output
  or JSON plus validation). On failure: retry once, then return a handled error. Never `eval`
  model output.
- Every `rule_ref` has the form `<topic_id>#<section-slug>` and must exist in the cards
  (the output guardrail checks this).
- Wrap every agent run in `ContextTracing` (audit trail, RNF-04).
- The LLM correction tool has a **timeout** (`ENITA_LLM_TIMEOUT_S`, default 20s) with a
  graceful fallback (RNF-06).
- Persistence: SQLite at `backend/data/enita.db` (gitignored), through `enita.storage` only.
- Style: type hints everywhere, small pure functions, `ruff` clean, line length 100.

## Security rules (non-negotiable)

- The student's answer is **untrusted input**. It goes into prompts only inside a clearly
  delimited data block, after `guardrails.validate_answer()` (length ≤ 300, control chars
  stripped, injection patterns flagged).
- The Tutor has no network/web tools and no filesystem write tools. Don't add any: that
  would complete the lethal trifecta.
- Secrets only in `.env` (gitignored). Update `.env.example` when adding a setting.
  Never commit keys, never log them.

## Content rules (`content/en/topics/*.md`)

- One file per topic, filename = `id` (kebab-case, e.g. `present-simple.md`).
- YAML front matter: `id`, `title` (Italian), `level` (A1|A2|B1), `tags`.
- Exactly these H2 sections, in order: `## Regola`, `## Esempi`, `## Attenzione`,
  `## Riepilogo`. Section slugs (`regola`, `esempi`, `attenzione`, `riepilogo`) are the
  `rule_ref` anchors.
- Explanations in Italian, examples in English with an Italian gloss. Write original
  content. Don't copy copyrighted textbooks.

## Frontend rules

Follow `frontend/AGENTS.md` (Angular 22 best practices: standalone, signals, OnPush by default, Signal Forms, native
control flow, `inject()`, WCAG AA). In addition:

- Use the Angular CLI generators (`npx ng generate component …`).
- Feature structure under `src/app/`: `core/` (api service, models), `features/theory/`,
  `features/practice/`, `shared/ui/` (brutalist primitives: button, panel, badge).
- All HTTP goes through `core/api.service.ts`. Types mirror backend Pydantic models in
  `core/models.ts`.
- **Design system: brutalist · minimal · retro.**
  - Font: JetBrains Mono only (loaded in `index.html`), set in Tailwind `@theme` as `--font-mono`.
  - Colors only via the theme tokens in `src/styles.css` (`paper`, `ink`, `accent`, `ok`,
    `err`). No ad-hoc hex in templates.
  - `border-2 border-ink`, **no rounded corners**, hard shadow `shadow-brutal`
    (`4px 4px 0 var(--color-ink)`), no gradients, no blur.
  - Uppercase bracketed labels for actions: `[ NUOVO ESERCIZIO ]`.
  - Split screen: `lg:grid-cols-2` 50/50. Below `lg`, use tabs `[TEORIA] [PRATICA]`.
- Tailwind v4: config lives in CSS (`@theme`), there is no `tailwind.config.js`.

## Workflow

- Work in small, runnable increments matching the milestones in the spec (§8).
- Commit messages: imperative, prefixed by area: `backend: …`, `frontend: …`, `content: …`,
  `docs: …`, `evals: …`, `infra: …`.
- When you add or change an endpoint, update §5.3 of the spec and `core/models.ts`.
- When you make an architectural decision, add a row to §9 "Decisioni prese".
- Ask the human before: adding a new external service, changing the architecture
  (e.g. going multi-agent), or deleting content cards.
