# Enita — Analisi funzionale

> Progetto Personale Senior · AITHO GenAI Academy · Blocco 3
> Versione 0.1 · 23/11/2026 · Stato: MVP in sviluppo, consegna **oggi**

## 1. Visione

**Enita** è un simulatore personalizzato per imparare le lingue, guidato dall'IA.
Lo schermo è diviso in due (split screen):

| Sinistra — **Teoria** | Destra — **Pratica** |
|---|---|
| Scheda dell'argomento: regola, esempi, eccezioni, errori tipici degli italofoni | Esercizi generati e corretti dall'IA, con feedback che rimanda alla regola a sinistra |

Il valore sta nel legame tra le due metà: quando sbagli un esercizio, a sinistra
si evidenzia la regola che hai violato e l'IA ti spiega l'errore sul tuo caso.

### Scope MVP

- Lingua dell'interfaccia e delle spiegazioni: **italiano**.
- Lingua target: **inglese**, livelli CEFR A1–B1.
- Un solo utente locale, senza login.
- Teoria **statica** (schede markdown curate). Il **RAG** sulle stesse schede arriva dopo, in modo incrementale.

### Fuori scope (per ora)

Multi-utente e autenticazione, audio/pronuncia, altre lingue target, app mobile,
gamification avanzata.

## 2. Attori

| Attore | Descrizione |
|---|---|
| **Studente** | Unico utente. Sceglie un argomento, studia la teoria, fa esercizi, vede i progressi. |
| **Tutor IA** | Agente datapizza-ai. Genera gli esercizi, corregge le risposte aperte, spiega gli errori. |
| **Autore contenuti** | Lo sviluppatore. Scrive le schede di teoria in `content/en/topics/*.md`. |

## 3. Requisiti funzionali

Priorità: **M** = must (minimo per la consegna), **S** = should, **C** = could.

### 3.1 Navigazione e teoria (pannello sinistro)

| ID | Requisito | Pri |
|---|---|---|
| RF-01 | L'utente vede l'elenco degli argomenti raggruppati per livello CEFR (A1, A2, B1). | M |
| RF-02 | Selezionando un argomento, a sinistra compare la scheda di teoria (markdown renderizzato). | M |
| RF-03 | La scheda ha sezioni fisse: *Regola*, *Esempi*, *Attenzione (errori tipici)*, *Riepilogo*. Ogni sezione ha un id ancorabile. | M |
| RF-04 | Quando un esercizio viene corretto, la sezione della regola citata nel feedback viene evidenziata e portata in vista. | S |
| RF-05 | Pulsante **"Spiegami meglio"**: l'IA rispiega la regola in modo più semplice, partendo dagli errori recenti dell'utente. Con RAG attivo, la risposta cita le schede usate. | C |

### 3.2 Esercizi (pannello destro)

| ID | Requisito | Pri |
|---|---|---|
| RF-10 | Per l'argomento selezionato l'utente chiede un nuovo esercizio. Il Tutor IA lo genera in base all'argomento, al livello e agli errori passati. | M |
| RF-11 | Tipi di esercizio: **completamento** (fill-in-the-blank), **scelta multipla**, **traduzione IT→EN**, **correzione di frase**. | M (primi 2), S (gli altri) |
| RF-12 | Gli esercizi chiusi (completamento, scelta multipla) sono corretti **in modo deterministico** confrontando la risposta con le soluzioni attese. All'IA resta solo la spiegazione. | M |
| RF-13 | Gli esercizi aperti (traduzione, correzione) sono corretti dall'IA con una rubrica: esito `correct` / `partial` / `wrong`, punteggio 0–1, spiegazione in italiano, riferimento alla regola (`topic_id#sezione`). | S |
| RF-14 | Il feedback mostra sempre: esito, risposta corretta, spiegazione breve e link alla regola a sinistra. | M |
| RF-15 | Ogni tentativo è salvato (argomento, tipo, risposta, esito, regola violata). | M |

### 3.3 Personalizzazione e progressi

| ID | Requisito | Pri |
|---|---|---|
| RF-20 | Il sistema mantiene un **profilo studente persistente**: livello stimato e accuratezza per argomento, errori ricorrenti. | M |
| RF-21 | La generazione degli esercizi usa il profilo e insiste sugli errori ricorrenti (memory persistente). | S |
| RF-22 | Una vista "Progressi" mostra l'accuratezza per argomento. | C |

### 3.4 Configurazione

| ID | Requisito | Pri |
|---|---|---|
| RF-30 | Il provider LLM si sceglie da configurazione: `openai` \| `google` \| `anthropic` \| `ollama`. Il codice applicativo resta invariato. | M |
| RF-31 | Routing opzionale: un modello economico per generare esercizi chiusi, uno più forte per correggere quelli aperti. | C |

## 4. Requisiti non funzionali (allineati al brief)

| ID | Requisito | Voce del brief |
|---|---|---|
| RNF-01 | Agente costruito con `datapizza.agents.Agent`, client multi-provider, tool calling, memory persistente (SQLite più `datapizza.memory.Memory` per la sessione). | LLM & Agent core |
| RNF-02 | Architettura **single-agent con tool esposti da un MCP server** (motivazione al §5). | Orchestrazione |
| RNF-03 | Almeno un **guardrail**: validazione dell'input (risposta dello studente) e dell'output (correzione dell'IA) del tool `check_answer`. | Sicurezza |
| RNF-04 | **Audit trail** con `datapizza.tracing.ContextTracing` su ogni generazione e correzione. | Governance |
| RNF-05 | **Eval** con verdetto pass/fail: 8 task di correzione e trajectory, soglia ≥ 7/8. | Affidabilità |
| RNF-06 | **Timeout** sul tool critico (correzione IA, 20 s). Allo scadere: fallback deterministico o messaggio "riprova". | S14 |
| RNF-07 | **Dockerfile** che builda e parte in locale. `docker compose up` avvia backend e frontend. | Produzione / S15 |
| RNF-08 | README con installazione e avvio. Il progetto è completo solo se gira. | Produzione |
| RNF-09 | UI accessibile (WCAG AA: contrasto, focus visibile, ARIA), stile brutalista e minimal con font monospace (§7). | — |
| RNF-10 | Nessun segreto nel repo: le chiavi API stanno in `.env`, in git c'è solo `.env.example`. | Sicurezza |

## 5. Architettura

### 5.1 Scelta: single-agent + MCP

> **Motivazione (una riga, come chiede il brief):** il flusso è un'unica conversazione
> pedagogica (genera → correggi → spiega) con pochi tool e poca latenza tollerata,
> quindi un solo agente Tutor basta. I tool vivono in un **MCP server** così che i
> contenuti e i progressi siano riutilizzabili anche da un altro host (Claude Desktop, Cursor).

Un'evoluzione multi-agente (DagPipeline *generatore → verificatore* degli esercizi),
confrontata con la baseline single-agent su costo e step, è un extra di "Cosa alza il livello".

### 5.2 Componenti

```
┌──────────────── Frontend (Angular 22 + Tailwind v4) ───────────────┐
│  TopBar: argomento · livello · provider                            │
│  ┌──────── TheoryPane ────────┐  ┌──────── PracticePane ────────┐  │
│  │ scheda markdown            │  │ esercizio · input · feedback │  │
│  │ sezione evidenziata  ◀─────┼──┼── rule_ref                   │  │
│  └────────────────────────────┘  └──────────────────────────────┘  │
└──────────────────────────┬─────────────────────────────────────────┘
                           │ REST/JSON
┌──────────────────────────▼──── Backend (FastAPI, Python 3.12) ─────┐
│  api/        endpoint REST                                         │
│  agent/      Tutor = datapizza Agent + client factory (4 provider) │
│  guardrails/ validazione input/output                              │
│  tracing     ContextTracing → audit log                            │
│  storage/    SQLite: profilo, tentativi                            │
└──────────────────────────┬─────────────────────────────────────────┘
                           │ MCP (stdio)  via datapizza.tools.mcp_client.MCPClient
┌──────────────────────────▼──── enita-mcp (MCP server) ─────────────┐
│  get_theory_card(topic_id)        ← S12: il tool unico iniziale    │
│  get_learner_profile()            ← memory persistente             │
│  record_attempt(...)                                               │
│  search_grammar(query)            ← fase RAG (Qdrant, hybrid)      │
└──────────────────────────┬─────────────────────────────────────────┘
                           ▼
          content/en/topics/*.md   ·   data/enita.db (SQLite)
```

### 5.3 API REST (backend)

| Metodo | Path | Descrizione |
|---|---|---|
| GET | `/api/health` | Stato del servizio e provider attivo |
| GET | `/api/topics` | Elenco argomenti `{id, title, level}` |
| GET | `/api/topics/{id}` | Scheda di teoria `{id, title, level, sections[], markdown}` |
| POST | `/api/exercises` | `{topic_id, type?}` → esercizio `{id, type, prompt, options?, topic_id}` |
| POST | `/api/exercises/{id}/answer` | `{answer}` → feedback `{verdict, score, correct_answer, explanation, rule_ref}` |
| POST | `/api/topics/{id}/explain` | Spiegazione personalizzata (RF-05) |
| GET | `/api/progress` | Accuratezza per argomento |

### 5.4 Modello dati

- **Topic** (file markdown con front matter YAML): `id`, `title`, `level`, `tags`, sezioni `## Regola`, `## Esempi`, `## Attenzione`, `## Riepilogo`.
- **Exercise**: `id`, `topic_id`, `type`, `prompt`, `options[]`, `expected[]` (soluzioni accettate, mai inviate al frontend), `rule_ref`.
- **Attempt**: `id`, `exercise_id`, `topic_id`, `answer`, `verdict`, `score`, `rule_ref`, `created_at`.
- **LearnerProfile** (derivato dai tentativi): accuratezza per argomento, top errori per `rule_ref`.

### 5.5 Flusso principale

1. L'utente sceglie un argomento → `GET /topics/{id}` → la teoria compare a sinistra.
2. "Nuovo esercizio" → il Tutor chiama `get_theory_card` e `get_learner_profile` tramite MCP e genera un esercizio JSON. Il guardrail di output valida lo schema.
3. L'utente risponde → guardrail di input (lunghezza, caratteri, pattern di prompt injection).
4. Correzione: deterministica per gli esercizi chiusi, IA con rubrica e timeout per quelli aperti. Il guardrail di output controlla che `rule_ref` esista nella scheda.
5. `record_attempt` → il profilo si aggiorna, il feedback compare a destra e la regola si evidenzia a sinistra.
6. Ogni passo finisce in ContextTracing (audit trail).

## 6. Sicurezza, valutazione, produzione

- **Guardrail di input**: la risposta dello studente è testo non fidato e arriva dentro il prompt di correzione. Va limitata in lunghezza (≤ 300 caratteri), ripulita, delimitata nel prompt come dato (mai come istruzione) e confrontata con pattern di injection noti ("ignore previous instructions", "you are now"…). Se un pattern scatta, l'esito è `wrong` e l'evento finisce nell'audit.
- **Guardrail di output**: l'output del Tutor è validato con Pydantic (schema `Feedback` / `Exercise`). Se non è valido si fa un solo retry, poi un errore gestito. `rule_ref` deve esistere tra le sezioni della scheda.
- **Lethal trifecta**: il Tutor non ha tool di rete né di scrittura esterna. Legge solo contenuti curati e scrive solo i tentativi locali, quindi manca la gamba dell'esfiltrazione.
- **Eval** (`evals/`): 8 casi `(esercizio, risposta, esito atteso)` più un controllo di trajectory (il Tutor ha chiamato `get_theory_card` prima di correggere). Comando: `uv run python -m evals.run`, exit code ≠ 0 se il risultato è < 7/8. In seguito diventa un gate in CI.
- **RAGAS** (fase RAG): faithfulness e context precision su "Spiegami meglio".
- **Docker**: un'immagine per il backend (uv) e una per il frontend (build Angular servita da nginx), più `compose.yaml`.

## 7. Linee guida UI

Stile **brutalista · minimal · retro**.

- Font unico: **JetBrains Mono** (Google Fonts), pesi 400/700.
- Palette: carta `#F4F1EA`, inchiostro `#111111`, un solo accento `#FF4D00`. Stati: ok `#1F7A3A`, errore `#C8102E`. Modalità scura invertita.
- Bordi 2px neri pieni, **nessun border-radius**, ombre dure `4px 4px 0 #111`, nessun gradiente.
- Layout: griglia a 2 colonne 50/50 su desktop (≥ 1024px), separate da un bordo spesso. Sotto i 1024px le due metà si impilano e si passa dall'una all'altra con tab `[TEORIA] [PRATICA]`.
- Etichette in maiuscolo tra parentesi quadre (`[ NUOVO ESERCIZIO ]`), cursore lampeggiante come dettaglio retro.
- Focus visibile (outline accento 3px), contrasto AA.

## 8. Piano di lavoro (oggi)

Ogni milestone deve chiudersi con qualcosa che gira.

| # | Milestone | Copre | Stima |
|---|---|---|---|
| M0 | Repo, analisi, AGENTS.md, scaffold FE e BE | — | fatto |
| M1 | Schede teoria (6 argomenti A1–B1), API topics, UI split screen con teoria | RF-01..03 | 1h |
| M2 | Tutor agent multi-provider + MCP server con `get_theory_card`, generazione ed esercizi chiusi | RF-10..12, RF-30, S12 | 1.5h |
| M3 | SQLite tentativi e profilo, guardrail input/output, ContextTracing | RF-15, RF-20, S13 | 1h |
| M4 | Eval (8 task) + timeout sulla correzione IA | S14 | 1h |
| M5 | Dockerfile + compose + README | S15 | 45m |
| M6 | *(se avanza tempo)* esercizi aperti, "Spiegami meglio", RAG su Qdrant + RAGAS | RF-05, RF-13 | 2h |

## 9. Decisioni prese

| Decisione | Scelta | Motivo |
|---|---|---|
| Lingue | UI in italiano, target inglese | Scope MVP, contenuti facili da verificare |
| Teoria | Statica, poi RAG sulle stesse schede | Demo sempre funzionante, nessun lavoro buttato |
| Correzione | Deterministica per gli esercizi chiusi, IA per quelli aperti | Affidabilità e costo |
| Architettura | Single-agent + MCP server | Flusso unico, tool riusabili da altri host |
| Provider | OpenAI, Gemini, Anthropic, Ollama tramite factory | Multi-provider richiesto dal brief |
| Persistenza | SQLite | Zero infrastruttura, sufficiente per un utente |

## 10. Domande aperte

- Provider predefinito per la demo (suggerito: OpenAI `gpt-4o-mini` o Gemini Flash, Ollama come fallback). Ollama oggi non è installato su questa macchina.
- Vuoi anche un'immagine Docker unica (FE servito da FastAPI) per semplificare la demo?
