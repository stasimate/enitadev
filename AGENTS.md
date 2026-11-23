# AGENTS.md — Enita

This file gives instructions to AI coding agents (Claude Code, GitHub Copilot, Cursor and
others) that work in this repository. Read all of this file before you change the code.

The functional specification is [`docs/FUNCTIONAL_ANALYSIS.md`](docs/FUNCTIONAL_ANALYSIS.md).
The requirement IDs in this file (`RF-xx`, `RNF-xx`) come from that specification.

## What Enita is

Enita is a simulator that helps you learn a language. AI controls the simulator.

- The screen has two parts (**split screen**). The left part shows a theory card. The right
  part shows exercises that the AI makes and checks.
- When an answer is wrong, the feedback refers to the rule (`rule_ref`). The left part
  highlights that rule.
- The UI text and the explanations are in **Italian**. The target language is **English**
  (CEFR A1 to B1).
- There is one local user. There is no authentication.
- The theory is **static markdown** first. RAG on the same files comes later.

## Repository layout

```
enitadev/
├── AGENTS.md                 ← this file
├── README.md                 ← install and start (keep it correct)
├── docs/FUNCTIONAL_ANALYSIS.md
├── content/en/topics/*.md    ← theory cards (source of truth for theory and rule_refs)
├── backend/                  ← Python 3.12, uv, FastAPI, datapizza-ai
│   ├── enita/
│   │   ├── api/              ← FastAPI routers (thin, no business logic)
│   │   ├── agent/            ← tutor agent, LLM client factory, prompts
│   │   ├── mcp_server/       ← MCP server with the Enita tools (stdio)
│   │   ├── guardrails/       ← input and output validation
│   │   ├── content/          ← loader and parser for the markdown cards
│   │   ├── storage/          ← SQLite (exercises, attempts, audit) in db.py
│   │   ├── practice/         ← use cases: make an exercise, check an answer
│   │   ├── audit.py          ← ContextTracing spans → audit record
│   │   ├── models.py         ← Pydantic schemas for the API, the agent and MCP
│   │   ├── settings.py       ← pydantic-settings, reads .env
│   │   └── main.py           ← FastAPI app factory
│   ├── evals/                ← eval set and runner (pass or fail exit code)
│   └── tests/
└── frontend/                 ← Angular 22 + Tailwind v4 (has its own AGENTS.md)
```

## Commands

| Task | Directory | Command |
|---|---|---|
| Install the backend | `backend/` | `uv sync` |
| Start the backend (development) | `backend/` | `uv run uvicorn enita.main:app --reload --port 8000` |
| Start the MCP server (stdio) | `backend/` | `uv run python -m enita.mcp_server` |
| Run the backend tests | `backend/` | `uv run pytest` |
| Run the linter | `backend/` | `uv run ruff check .` |
| Run the evals (gate) | `backend/` | `uv run python -m evals.run` (exit code is not 0 if the score is less than 7/8) |
| Set the Node version | root | `nvm use` (`.nvmrc` = 24. Angular 22 requires Node 24.15 or later.) |
| Install the frontend | `frontend/` | `npm ci` |
| Start the frontend (development) | `frontend/` | `npm start` → http://localhost:4200. The proxy sends `/api` to port 8000. |
| Build the frontend | `frontend/` | `npm run build` |
| Run the frontend tests | `frontend/` | `npm test` |
| Start all (one image: FastAPI serves the API and the Angular build) | root | `docker compose up --build` → http://localhost:8000 |
| Start development in Docker (hot reload) | root | `docker compose -f compose.dev.yaml up` → http://localhost:4200 |

Docker is the default runtime. The host has Docker through **colima** (`colima start`).
You can run all the parts in Docker. You do not need Python or Node on the host.

Before you say that a task is complete, run the tests and the build for the part that you
changed. If the part does not operate, the task is not complete. (The brief says: "il
progetto si considera completato solo se gira".)

### Test rules

Write **only the tests that are strictly necessary**. A test is necessary when it protects:

- logic that decides a result (answer check, rule checks, pipeline decision and retry),
- a contract between parts (API responses, the MCP tool, the store state),
- a security rule (the solution is never sent to the frontend, guardrails).

Do not write tests that only show that a component renders or that a class exists.
Do not write a test for code that the framework already tests.

## Documentation rules

- Write all documentation in **English** and obey **ASD-STE100** (Simplified Technical
  English). This includes `README.md`, `docs/`, this file, docstrings, code comments and
  commit messages.
- Use these STE rules:
  - Write one instruction in each sentence. Use the imperative for instructions.
  - Procedural sentences: 20 words or fewer. Descriptive sentences: 25 words or fewer.
  - Use the active voice. Use the simple tenses (present, past, future).
  - Use one word for one meaning. Use the same term for the same thing in all documents.
  - Do not use phrasal verbs when a single verb is available ("start", not "start up").
  - Use articles ("the", "a") where possible. Use a list for a sequence of steps.
  - A paragraph has a maximum of six sentences.
- Exceptions: the theory cards (`content/`) and the UI text are in Italian because they are
  product content. Quotes from the Italian brief stay in Italian.
- The chat with the project owner is in Italian.

## Backend rules

- The framework is **datapizza-ai** (installed version `datapizza-ai` 0.1.x). Use the real APIs:
  - Agent: `from datapizza.agents import Agent`
  - Tools: `from datapizza.tools import tool` (decorator)
  - MCP client: `from datapizza.tools.mcp_client import MCPClient`. For the stdio server,
    use the client as a context manager:
    `async with MCPClient(command=..., args=[...]) as c: tools = await c.a_list_tools()`
  - Memory: `from datapizza.memory import Memory`
  - Tracing: `from datapizza.tracing import ContextTracing`
  - Clients: `datapizza.clients.openai.OpenAIClient`, `datapizza.clients.google.GoogleClient`,
    `datapizza.clients.anthropic.AnthropicClient`, `datapizza.clients.openai_like.OpenAILikeClient`
    (Ollama at `http://localhost:11434/v1`).
  - If you are not sure about a signature, **read the installed source** in
    `backend/.venv/lib/python3.12/site-packages/datapizza/`. Do not guess. The course lessons
    are the reference for usage patterns.
- MCP server: use the official `mcp` SDK **1.x** (`mcp.server.fastmcp.FastMCP`). Each tool
  has a typed signature and a docstring. Do not upgrade to `mcp` 2.x: the datapizza
  `MCPClient` (datapizza-ai-core 0.1.3) does not operate with it.
- Exercise generation is multi-agent (`enita/agent/pipeline.py`): a DagPipeline with
  writer → (rules check ∥ verifier) → decision. The writer gets the theory only through the
  MCP tool `get_theory_card`. The retry loop is outside the DAG.
- **Do not hardcode the LLM provider.** Always use `enita.agent.clients.get_client()`. This
  function reads `ENITA_PROVIDER` and `ENITA_MODEL` (RF-30).
- **Check closed exercises (fill in the blank, multiple choice) with fixed rules.**
  Normalize the answer first: lowercase, trim, one space between words, straight quotes.
  The LLM only writes the explanation. When an expected answer exists, the LLM must not
  decide if the answer is correct (RF-12).
- **Never** send `Exercise.expected` to the frontend. The API response models exclude it.
- Parse into a Pydantic model each LLM output that controls the application logic. Use
  structured output, or JSON and validation. If the parse fails, try again one time. Then
  return a controlled error. Never `eval` the model output.
- Each `rule_ref` has the format `<topic_id>#<section-slug>`. It must exist in the cards.
  The output guardrail checks this.
- Put each agent run in `ContextTracing` (audit trail, RNF-04).
- The LLM correction tool has a **timeout** (`ENITA_LLM_TIMEOUT_S`, default 20 s) and a
  controlled fallback (RNF-06).
- Persistence: SQLite at `backend/data/enita.db` (git ignores it). Use only `enita.storage.db.Database`
  to access it.
- Style: type hints on all code, small pure functions, no `ruff` errors, line length 100.

## Security rules (mandatory)

- Never put raw student answers in an LLM prompt or in an MCP tool result. The learner
  profile contains aggregates only.
- The student answer is **not trusted input**. Before a prompt contains it, call
  `guardrails.validate_answer()`. This function limits the length to 300, removes control
  characters and flags injection patterns. In the prompt, put the answer in a block for data.
- The tutor has no network tools, no web tools and no tools that write to the file system.
  Do not add these tools: they complete the lethal trifecta.
- Put secrets only in `.env` (git ignores it). When you add a setting, update `.env.example`.
  Never commit keys. Never write keys to the log.

## Content rules (`content/en/topics/*.md`)

- Use one file for each topic. The filename is the `id` (kebab-case, for example
  `present-simple.md`).
- The YAML front matter has `id`, `title` (Italian), `level` (A1, A2 or B1) and `tags`.
- Use these H2 sections, in this sequence: `## Regola`, `## Esempi`, `## Attenzione`,
  `## Riepilogo`. The section slugs (`regola`, `esempi`, `attenzione`, `riepilogo`) are the
  `rule_ref` anchors.
- Write the explanations in Italian. Write the examples in English, with an Italian
  translation. Write original content. Do not copy textbooks that have copyright.

## Frontend rules

Obey `frontend/AGENTS.md` (Angular 22 best practices: standalone components, signals, OnPush
by default, Signal Forms, native control flow, `inject()`, WCAG AA). Also obey these rules:

- Use the Angular CLI generators (`npx ng generate component …`).
- Use this structure in `src/app/`. Do not add other top-level folders.
  - `core/`: singletons for all the application. `api.ts` (the only HTTP access) and
    `models.ts` (types that are the same as the backend Pydantic models).
  - `features/<feature>/`: one folder for each feature (`theory/`, `practice/`). A feature
    has one store (`<feature>-store.ts`, signals) and its components.
  - `shared/`: reusable parts with no feature logic: `pipes/`, `ui/` (brutalist primitives:
    button, panel, badge).
- **One component has one responsibility.** Examples: `TopicSelect` only selects a topic.
  `TheoryCard` only shows a card. `App` only arranges the layout.
  - A component receives data with `input()` and sends events with `output()` / `model()`.
  - A component does not call HTTP. The feature store calls `core/api.ts`.
  - If a component does two things, divide it into two components.
- **Design system: brutalist · minimal · retro.**
  - Font: JetBrains Mono only (`index.html` loads it). The Tailwind `@theme` sets it as
    `--font-mono`.
  - Use only the theme tokens in `src/styles.css` for colors (`paper`, `ink`, `accent`, `ok`,
    `err`). Do not write hex values in templates.
  - Use `border-2 border-ink` and the hard shadow `shadow-brutal`
    (`4px 4px 0 var(--color-ink)`). **No rounded corners.** No gradients. No blur.
  - Action labels are in capital letters, between square brackets: `[ NUOVO ESERCIZIO ]`.
  - Split screen: `lg:grid-cols-2`, 50/50. On screens narrower than `lg`, use the tabs
    `[TEORIA] [PRATICA]`.
- Tailwind v4: the configuration is in CSS (`@theme`). There is no `tailwind.config.js`.

## Workflow

- Work in small increments that operate. Follow the milestones in the specification (§8).
- Commit messages: use **Conventional Commits** (`type(scope): description`, imperative
  mood). Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `build`, `ci`.
  Scopes: `backend`, `frontend`, `content`, `evals`, `infra`. Example:
  `feat(backend): add the exercise verifier agent`.
- Do not add a `Co-Authored-By` line or other AI attribution to commits.
- When you add or change an endpoint, update §5.3 of the specification and `frontend/src/app/core/models.ts`.
- When you make an architecture decision, add a row to §9 "Decisions" of the specification.
- Ask the project owner before you add an external service, change the architecture (for
  example, to multi-agent) or delete content cards.
