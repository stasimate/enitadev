# Enita

Enita è un simulatore personalizzato basato sull'IA per imparare le lingue. Lo schermo è diviso in due: a sinistra la **teoria**, a destra la **pratica**, con esercizi generati e corretti dall'IA.
Quando sbagli, il feedback ti riporta alla regola esatta nel pannello di teoria.

Progetto Personale Senior, AITHO GenAI Academy. Stack: **datapizza-ai** (Agent, tools, Memory, ContextTracing, MCP) · FastAPI · Angular 22 + Tailwind v4.

- Analisi funzionale: [`docs/ANALISI_FUNZIONALE.md`](docs/ANALISI_FUNZIONALE.md)
- Regole per gli agenti di coding: [`AGENTS.md`](AGENTS.md)

> Stato: **M0, scaffold**. L'app parte e mostra lo split screen. Agente, esercizi ed eval arrivano con le milestone M1–M5 (vedi §8 dell'analisi).

## Requisiti

- Python 3.12 e [uv](https://docs.astral.sh/uv/)
- Node 24 LTS (`nvm use`, vedi `.nvmrc`)
- Una chiave API per almeno un provider: OpenAI, Google Gemini o Anthropic. In alternativa, Ollama in locale.
- Docker (facoltativo)

## Configurazione

```bash
cp .env.example .env
```

Nel file `.env` imposta `ENITA_PROVIDER`, `ENITA_MODEL` e la chiave del provider scelto.

## Avvio in sviluppo

Backend (http://localhost:8000):

```bash
cd backend
uv sync
uv run uvicorn enita.main:app --reload --port 8000
```

Frontend (http://localhost:4200, inoltra `/api` al backend):

```bash
cd frontend
npm ci
npm start
```

## Test

```bash
cd backend && uv run pytest && uv run ruff check .
```

```bash
cd frontend && npm test -- --watch=false
```

## Struttura

```
content/en/topics/   schede di teoria (markdown)
backend/enita/       API, agente Tutor, MCP server, guardrail, storage
backend/evals/       eval set con verdetto pass/fail
frontend/            UI split screen (Angular + Tailwind)
docs/                analisi funzionale
```
