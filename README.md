# Enita

Enita is a simulator that helps you learn a language. Artificial intelligence (AI) controls
the simulator. The screen has two parts. The left part shows the **theory**. The right part
shows the **practice**: exercises that the AI makes and checks. When you make an error, the
feedback shows the applicable rule in the theory part.

Personal Senior Project, AITHO GenAI Academy.
Stack: **datapizza-ai** (Agent, tools, Memory, ContextTracing, MCP) · FastAPI · Angular 22 + Tailwind v4.

- Functional analysis: [`docs/FUNCTIONAL_ANALYSIS.md`](docs/FUNCTIONAL_ANALYSIS.md)
- Rules for AI coding agents: [`AGENTS.md`](AGENTS.md)

> Status: **M2 complete**. The theory cards and the AI exercises operate in the split screen.
> Guardrails, audit trail, evals and the final Docker checks come with milestones M3 to M5
> (refer to §8 of the functional analysis).

## Quick start with Docker

Docker is the recommended runtime. On macOS, you can use [colima](https://github.com/abiosoft/colima).

1. Start the Docker runtime (colima only):

   ```bash
   colima start
   ```

2. Copy the example configuration:

   ```bash
   cp .env.example .env
   ```

3. Build the image and start the application. Then open http://localhost:8000.

   ```bash
   docker compose up --build
   ```

For development in Docker with hot reload, start the dev stack. Then open http://localhost:4200.

```bash
docker compose -f compose.dev.yaml up
```

## Requirements

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- Node 24 LTS. The file `.nvmrc` sets the version. Use `nvm use`.
- An API key for one or more providers: OpenAI, Google Gemini or Anthropic. As an alternative, use Ollama on the local computer.
- Docker (optional)

## Configuration

1. Copy the example file:

   ```bash
   cp .env.example .env
   ```

2. In `.env`, set `ENITA_PROVIDER`, `ENITA_MODEL` and the API key of the provider.

## Start for development without Docker

1. Start the backend (http://localhost:8000):

   ```bash
   cd backend
   uv sync
   uv run uvicorn enita.main:app --reload --port 8000
   ```

2. Start the frontend (http://localhost:4200). The frontend sends the `/api` requests to the backend.

   ```bash
   nvm use
   cd frontend
   npm ci
   npm start
   ```

## Tests

1. Run the backend tests and the linter:

   ```bash
   cd backend && uv run pytest && uv run ruff check .
   ```

2. Run the frontend tests:

   ```bash
   cd frontend && npm test -- --watch=false
   ```

## Structure

```
content/en/topics/   theory cards (markdown)
backend/enita/       API, tutor agent, MCP server, guardrails, storage
backend/evals/       eval set with a pass or fail result
frontend/            split-screen UI (Angular + Tailwind)
docs/                functional analysis
```
