# Enita — Functional analysis

> Personal Senior Project · AITHO GenAI Academy · Block 3
> Version 0.2 · 2026-11-23 · Status: MVP in development. Delivery date: today.
> Writing standard: ASD-STE100 (Simplified Technical English).

## 1. Vision

Enita is a simulator that helps you learn a language. Artificial intelligence (AI) controls
the simulator.

The screen has two parts (split screen):

| Left part: **Theory** | Right part: **Practice** |
|---|---|
| The card for the topic. The card shows the rule, examples, exceptions and the usual errors of Italian speakers. | Exercises. The AI makes the exercises and checks the answers. The feedback refers to the rule in the left part. |

The connection between the two parts is the important function. If you make an error in an
exercise, the left part highlights the rule that you did not obey. The AI then explains the
error in your answer.

### MVP scope

- The language of the user interface (UI) and of the explanations is **Italian**.
- The language that the user learns (target language) is **English**, CEFR levels A1 to B1.
- There is one local user. There is no login.
- The theory is **static**: markdown cards that a person writes and checks.
- Retrieval-augmented generation (**RAG**) on the same cards comes later, in small steps.

### Out of scope (for now)

- More than one user and authentication
- Audio and pronunciation
- Other target languages
- A mobile app
- Advanced game functions (points, badges)

## 2. Actors

| Actor | Description |
|---|---|
| **Student** | The only user. The student selects a topic, reads the theory, does exercises and sees the progress. |
| **AI tutor** | An agent that uses datapizza-ai. The tutor makes exercises, checks open answers and explains errors. |
| **Content author** | The developer. The developer writes the theory cards in `content/en/topics/*.md`. |

## 3. Functional requirements

Priority: **M** = must (minimum for delivery), **S** = should, **C** = could.

### 3.1 Navigation and theory (left part)

| ID | Requirement | Pri |
|---|---|---|
| RF-01 | The UI shows the list of topics. The UI groups the topics by CEFR level (A1, A2, B1). | M |
| RF-02 | When the user selects a topic, the left part shows the theory card (rendered markdown). | M |
| RF-03 | The card has four fixed sections: *Regola* (rule), *Esempi* (examples), *Attenzione* (usual errors), *Riepilogo* (summary). Each section has an anchor id. | M |
| RF-04 | When the system checks an exercise, the UI highlights the section that the feedback refers to. The UI scrolls to this section. | S |
| RF-05 | A **"Spiegami meglio"** (explain better) button. The AI explains the rule again in simpler words. The AI uses the recent errors of the user. When RAG is active, the answer shows the cards that the AI used. | C |

### 3.2 Exercises (right part)

| ID | Requirement | Pri |
|---|---|---|
| RF-10 | For the selected topic, the user asks for a new exercise. The AI tutor makes the exercise from the topic, the level and the past errors. | M |
| RF-11 | Exercise types: **fill in the blank**, **multiple choice**, **translation from Italian to English**, **sentence correction**. | M (first 2), S (other 2) |
| RF-12 | The system checks closed exercises (fill in the blank, multiple choice) **with fixed rules**. It compares the answer with the list of correct answers. The AI only writes the explanation. | M |
| RF-13 | The AI checks open exercises (translation, sentence correction) with a scoring guide (rubric). The output is: result `correct` / `partial` / `wrong`, score 0 to 1, explanation in Italian, rule reference (`topic_id#section`). | S |
| RF-14 | The feedback always shows the result, the correct answer, a short explanation and a link to the rule in the left part. | M |
| RF-15 | The system keeps a record of each attempt: topic, exercise type, answer, result and the rule that the user did not obey. | M |

### 3.3 Personalization and progress

| ID | Requirement | Pri |
|---|---|---|
| RF-20 | The system keeps a **permanent student profile**: the estimated level, the accuracy for each topic and the errors that occur frequently. | M |
| RF-21 | The AI uses the profile when it makes exercises. It gives more exercises on the frequent errors (permanent memory). | S |
| RF-22 | A "Progress" view shows the accuracy for each topic. | C |

### 3.4 Configuration

| ID | Requirement | Pri |
|---|---|---|
| RF-30 | You select the LLM provider in the configuration: `openai` \| `google` \| `anthropic` \| `ollama`. You do not change the application code. | M |
| RF-31 | Optional routing: a low-cost model makes closed exercises. A stronger model checks open exercises. | C |

## 4. Non-functional requirements (aligned with the project brief)

| ID | Requirement | Brief item |
|---|---|---|
| RNF-01 | The agent uses `datapizza.agents.Agent`, a client for more than one provider, tool calling and permanent memory (SQLite, plus `datapizza.memory.Memory` for the session). | LLM and agent core |
| RNF-02 | The architecture is **one agent, with tools that an MCP server supplies**. Refer to §5. | Orchestration |
| RNF-03 | There is a minimum of one **guardrail**. It validates the input (the student answer) and the output (the AI correction) of the tool `check_answer`. | Security |
| RNF-04 | `datapizza.tracing.ContextTracing` records an **audit trail** for each exercise and each correction. | Governance |
| RNF-05 | An **eval** gives a pass or fail result: 8 correction and trajectory tasks. The pass limit is 7 of 8. | Reliability |
| RNF-06 | The critical tool (AI correction) has a **timeout** of 20 s. When the time ends, the system uses the fixed-rule check, or it tells the user to try again. | S14 |
| RNF-07 | One **Dockerfile** builds one image and starts the application on the local computer. FastAPI serves the API and the Angular build. `docker compose up` starts the image. | Production / S15 |
| RNF-08 | The README tells how to install and start the application. The project is complete only when it operates. | Production |
| RNF-09 | The UI is accessible (WCAG AA: contrast, visible focus, ARIA). The style is brutalist and minimal, with a monospace font (§7). | — |
| RNF-10 | The repository contains no secrets. The API keys are in `.env`. Git contains only `.env.example`. | Security |

## 5. Architecture

### 5.1 Decision: one agent and an MCP server

> **Reason:** The flow is one teaching conversation (make an exercise, check it, explain it).
> The flow has few tools and must have low latency. Thus, one tutor agent is sufficient.
> An **MCP server** supplies the tools. Other hosts (Claude Desktop, Cursor) can then also
> use the content and the progress data.

A multi-agent version (DagPipeline: one agent makes the exercise, one agent verifies it) is
possible later. Compare it with the one-agent baseline (cost and steps). This is an item of
"Cosa alza il livello" in the brief.

### 5.2 Components

```
┌──────────────── Frontend (Angular 22 + Tailwind v4) ───────────────┐
│  TopBar: topic · level · provider                                  │
│  ┌──────── TheoryPane ────────┐  ┌──────── PracticePane ────────┐  │
│  │ markdown card              │  │ exercise · input · feedback  │  │
│  │ highlighted section  ◀─────┼──┼── rule_ref                   │  │
│  └────────────────────────────┘  └──────────────────────────────┘  │
└──────────────────────────┬─────────────────────────────────────────┘
                           │ REST/JSON
┌──────────────────────────▼──── Backend (FastAPI, Python 3.12) ─────┐
│  api/        REST endpoints                                        │
│  agent/      Tutor = datapizza Agent + client factory (4 providers)│
│  guardrails/ input and output validation                           │
│  tracing     ContextTracing → audit log                            │
│  storage/    SQLite: profile, attempts                             │
└──────────────────────────┬─────────────────────────────────────────┘
                           │ MCP (stdio) through datapizza.tools.mcp_client.MCPClient
┌──────────────────────────▼──── enita-mcp (MCP server) ─────────────┐
│  get_theory_card(topic_id)        ← S12: the first and only tool   │
│  get_learner_profile()            ← permanent memory               │
│  record_attempt(...)                                               │
│  search_grammar(query)            ← RAG phase (Qdrant, hybrid)     │
└──────────────────────────┬─────────────────────────────────────────┘
                           ▼
          content/en/topics/*.md   ·   data/enita.db (SQLite)
```

### 5.3 REST API (backend)

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Status of the service and the active provider |
| GET | `/api/topics` | List of topics `{id, title, level}` |
| GET | `/api/topics/{id}` | Theory card `{id, title, level, sections[], markdown}` |
| POST | `/api/exercises` | `{topic_id, type?}` → exercise `{id, type, prompt, options?, topic_id}` |
| POST | `/api/exercises/{id}/answer` | `{answer}` → feedback `{verdict, score, correct_answer, explanation, rule_ref}` |
| POST | `/api/topics/{id}/explain` | Personal explanation (RF-05) |
| GET | `/api/progress` | Accuracy for each topic |

### 5.4 Data model

- **Topic** (markdown file with YAML front matter): `id`, `title`, `level`, `tags`, and the sections `## Regola`, `## Esempi`, `## Attenzione`, `## Riepilogo`.
- **Exercise**: `id`, `topic_id`, `type`, `prompt`, `options[]`, `expected[]`, `rule_ref`. `expected[]` is the list of correct answers. The backend never sends it to the frontend.
- **Attempt**: `id`, `exercise_id`, `topic_id`, `answer`, `verdict`, `score`, `rule_ref`, `created_at`.
- **LearnerProfile** (calculated from the attempts): the accuracy for each topic and the most frequent errors for each `rule_ref`.

### 5.5 Main flow

1. The user selects a topic. The frontend calls `GET /topics/{id}`. The left part shows the theory.
2. The user pushes "New exercise". The tutor calls `get_theory_card` and `get_learner_profile` through MCP. The tutor makes an exercise in JSON. The output guardrail validates the schema.
3. The user writes an answer. The input guardrail checks the length, the characters and the known prompt-injection patterns.
4. The system checks the answer. Closed exercises use fixed rules. Open exercises use the AI, with a rubric and a timeout. The output guardrail makes sure that `rule_ref` is a section of the card.
5. The system calls `record_attempt` and updates the profile. The right part shows the feedback. The left part highlights the rule.
6. ContextTracing records each step (audit trail).

## 6. Security, evaluation and production

- **Input guardrail.** The student answer is not trusted text. The correction prompt contains it. Thus:
  - Limit the length to 300 characters.
  - Remove control characters.
  - Put the answer in the prompt in a block for data, not for instructions.
  - Compare the answer with known injection patterns ("ignore previous instructions", "you are now", …). If a pattern matches, the result is `wrong` and the audit trail records the event.
- **Output guardrail.** Pydantic validates the tutor output (schemas `Feedback` and `Exercise`). If the output is not valid, the system tries again one time. Then it returns a controlled error. `rule_ref` must be a section of the card.
- **Lethal trifecta.** The tutor has no network tools and no tools that write to external systems. It reads only checked content. It writes only local attempts. Thus, the tutor has no path to send data out (exfiltration).
- **Eval** (`evals/`): 8 cases `(exercise, answer, expected result)` and one trajectory check. The trajectory check makes sure that the tutor calls `get_theory_card` before it checks an answer. Command: `uv run python -m evals.run`. The exit code is not 0 when the result is less than 7 of 8. Later, CI uses this eval as a gate.
- **RAGAS** (RAG phase): faithfulness and context precision for "Spiegami meglio".
- **Docker**: one image with a multi-stage build. Stage 1 (Node 24) builds the Angular application. Stage 2 (Python 3.12, uv) installs the backend and copies the Angular build. FastAPI serves the API at `/api` and the static frontend at `/`. `compose.yaml` starts the image and reads `.env`.

## 7. UI guidelines

Style: **brutalist · minimal · retro**.

- One font only: **JetBrains Mono** (Google Fonts), weights 400 and 700.
- Colors: paper `#F4F1EA`, ink `#111111`, one accent `#FF4D00`. Status colors: correct `#1F7A3A`, error `#C8102E`. Dark mode inverts paper and ink.
- Borders: 2 px solid black. **No rounded corners.** Hard shadows `4px 4px 0 #111`. No gradients.
- Layout: two columns, 50/50, on desktop screens (1024 px and wider). A thick border divides the two parts. On screens narrower than 1024 px, the two parts are tabs: `[TEORIA] [PRATICA]`.
- Action labels are in capital letters, between square brackets: `[ NUOVO ESERCIZIO ]`. A cursor that blinks is the retro detail.
- The focus is always visible (accent outline, 3 px). The contrast agrees with WCAG AA.

## 8. Work plan (today)

Each milestone must end with a part that operates.

| # | Milestone | Covers | Estimate |
|---|---|---|---|
| M0 | Repository, analysis, AGENTS.md, frontend and backend scaffold | — | done |
| M1 | Theory cards (6 topics, A1 to B1), topics API, split-screen UI with the theory | RF-01..03 | 1 h |
| M2 | Tutor agent for more than one provider, MCP server with `get_theory_card`, generation and closed exercises | RF-10..12, RF-30, S12 | 1.5 h |
| M3 | SQLite for attempts and profile, input and output guardrails, ContextTracing | RF-15, RF-20, S13 | 1 h |
| M4 | Eval (8 tasks) and timeout on the AI correction | S14 | 1 h |
| M5 | Dockerfile, compose and README | S15 | 45 min |
| M6 | *(if time is available)* open exercises, "Spiegami meglio", RAG on Qdrant and RAGAS | RF-05, RF-13 | 2 h |

## 9. Decisions

| Decision | Selection | Reason |
|---|---|---|
| Languages | UI in Italian, target language English | MVP scope. It is easy to verify the content. |
| Theory | Static first, then RAG on the same cards | The demo always operates. No work is lost. |
| Correction | Fixed rules for closed exercises, AI for open exercises | Reliability and cost |
| Architecture | One agent and an MCP server | One flow. Other hosts can use the tools. |
| Provider | OpenAI, Gemini, Anthropic, Ollama through a factory | The brief requires more than one provider. |
| Persistence | SQLite | No infrastructure. It is sufficient for one user. |
| Frontend runtime | Angular 22.3 on Node 24 (`.nvmrc`) | Angular 22 requires Node 24.15 or later. It installs with npm 11 and no `legacy-peer-deps`. |
| Documentation | English, ASD-STE100 | Requirement of the project owner. The chat stays in Italian. |
| Default provider | OpenAI `gpt-4o-mini` | Decision of the project owner. The other providers stay available through `ENITA_PROVIDER`. |
| Deployment | One Docker image. FastAPI serves the API and the Angular build. | One container is simpler for the demo. There is no CORS configuration in production. |

## 10. Open questions

There are no open questions now.
