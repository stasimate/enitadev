# Enita

Enita is a simulator that helps Italian speakers learn English. Artificial intelligence (AI)
controls the simulator. The screen has two parts:

- The left part shows the **theory**: a card for each grammar topic (CEFR A1 to B1).
- The right part shows the **practice**: exercises that AI agents make and verify, in five
  types (fill in the blank, multiple choice, reorder, transform, find the error), one at a
  time or in a session of 10 with a summary.

When you make an error, the feedback shows the rule that you did not obey. The theory part
highlights that rule.

Personal Senior Project, AITHO GenAI Academy.
Stack: **datapizza-ai** (Agent, tools, DagPipeline, ContextTracing, MCP) · FastAPI · SQLite ·
Angular 22 + Tailwind v4 · Docker.

- Functional analysis: [`docs/FUNCTIONAL_ANALYSIS.md`](docs/FUNCTIONAL_ANALYSIS.md)
- Rules for AI coding agents: [`AGENTS.md`](AGENTS.md)

> Status: **M5 complete**. All the minimum items of the project brief operate.
> The last eval run passed (refer to [`backend/evals/last_report.json`](backend/evals/last_report.json)).

## What the system does

| Brief item | How Enita does it |
|---|---|
| LLM and agent core | Two datapizza `Agent`s (writer and verifier) with structured output. A client factory for OpenAI, Google, Anthropic and Ollama. Permanent memory in SQLite (learner profile). |
| Orchestration | Multi-agent `DagPipeline`: writer → (fixed-rule check ∥ verifier) → decision, with a retry loop. An MCP server supplies the tools `get_theory_card` and `get_learner_profile`. |
| Security and governance | Input guardrail on the student answer, output guardrail on the writer. `ContextTracing` audit trail in SQLite (`GET /api/audit`). No raw student answer goes into an LLM prompt. |
| Reliability | Review eval (11 cases, gate 10/11) and trajectory eval (3 real generations, gate 3/3). Timeouts on the generation (45 s) and on MCP tool calls (10 s). |
| Production | One Docker image (FastAPI serves the API and the Angular build). A Docker dev stack with hot reload. GitHub Actions CI with the evals as a gate for the Docker build. |

```
Angular (split screen) ──REST──▶ FastAPI ──▶ DagPipeline: writer ─┬─▶ fixed rules ─┐
                                    │                             └─▶ verifier ────┴─▶ decision
                                    │            │ MCP (stdio)
                                    ▼            ▼
                                 SQLite     enita-mcp: get_theory_card, get_learner_profile
                        (exercises, attempts,          │
                              audit)                   ▼
                                               content/en/topics/*.md
```

## Quick start with Docker

Docker is the recommended runtime. On macOS, you can use [colima](https://github.com/abiosoft/colima).

1. Start the Docker runtime (colima only):

   ```bash
   colima start
   ```

2. Copy the example configuration. Then, in `.env`, set `OPENAI_API_KEY`.

   ```bash
   cp .env.example .env
   ```

3. Build the image and start the application. Then open http://localhost:8000.

   ```bash
   docker compose up --build
   ```

For development in Docker with hot reload, start the dev stack. Then open http://localhost:4200.
You do not need Python or Node on the host.

```bash
docker compose -f compose.dev.yaml up
```

## Configuration

All the settings are in `.env` (refer to [`.env.example`](.env.example)).

| Setting | Default | Description |
|---|---|---|
| `ENITA_PROVIDER` | `openai` | `openai`, `google`, `anthropic` or `ollama` |
| `ENITA_MODEL` | `gpt-4.1-mini` | The model of the agents |
| `ENITA_WRITER_MODEL`, `ENITA_VERIFIER_MODEL` | empty | Optional model routing for each agent |
| `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY` | empty | The key of the selected provider |
| `ENITA_GENERATION_TIMEOUT_S` | `45` | Timeout of one exercise generation |
| `ENITA_MCP_TIMEOUT_S` | `10` | Timeout of one MCP tool call |
| `ENITA_POOL_SIZE` | `2` | Exercises prepared in advance for each topic (0 disables it) |

## Start for development without Docker

Requirements: Python 3.12 with [uv](https://docs.astral.sh/uv/), and Node 24 LTS (`.nvmrc`).

1. Start the backend (http://localhost:8000):

   ```bash
   cd backend && uv sync && uv run uvicorn enita.main:app --reload --port 8000
   ```

2. Start the frontend (http://localhost:4200). The frontend sends the `/api` requests to the backend.

   ```bash
   nvm use && cd frontend && npm ci && npm start
   ```

## Tests and evals

1. Run the backend tests and the linter:

   ```bash
   cd backend && uv run pytest && uv run ruff check .
   ```

2. Run the frontend tests:

   ```bash
   cd frontend && npm test -- --watch=false
   ```

3. Run the evals with the real LLM (an API key in `.env` is necessary). The run writes
   `backend/evals/last_report.json`. The exit code is 0 only if all gates pass.

   ```bash
   cd backend && uv run python -m evals.run
   ```

## CI

The workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on each push:

- backend lint and tests, frontend build and tests;
- on `main` (release) or a manual run: the evals, then the Docker build and a health check.

To run the eval gate on GitHub, add the repository secret `OPENAI_API_KEY`
(Settings → Secrets and variables → Actions).

## Use the MCP server from another host

The Enita MCP server operates also with other MCP hosts, for example Claude Desktop or Cursor.
It gives the theory cards and the learner progress.

1. Install the backend:

   ```bash
   cd backend && uv sync
   ```

2. Add this server to the MCP configuration of the host (for Claude Desktop:
   `claude_desktop_config.json`). Replace `<repo>` with the absolute path of this repository.

   ```json
   {
     "mcpServers": {
       "enita": {
         "command": "uv",
         "args": ["--directory", "<repo>/backend", "run", "python", "-m", "enita.mcp_server"]
       }
     }
   }
   ```

3. Restart the host. Then ask, for example: "Use get_theory_card to explain present-perfect."

## Branches and commits

- Do the work on `develop`. Merge `develop` into `main` for a release.
- Commit messages use [Conventional Commits](https://www.conventionalcommits.org/).

## Structure

```
content/en/topics/   theory cards (markdown, Italian explanations)
backend/enita/       API, agents and pipeline, MCP server, guardrails, storage, audit
backend/evals/       review eval and trajectory eval with pass or fail gates
backend/tests/       the necessary unit and contract tests
frontend/            split-screen UI (Angular + Tailwind): core/, features/, shared/
docs/                functional analysis
```
