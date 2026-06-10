# Stodi — the study agent that texts first

A syllabus-grounded **autonomous study agent for any high-stakes exam**.
It lives in the student's messaging app, tracks per-topic mastery, and runs
their spaced-repetition loop — it knows what you know, predicts when you'll
forget it, and **texts you before you do**. Every exam is a swappable
content pack on the same agent core; **WAEC/WASSCE is pack #1, live today**
— JAMB, NECO, and any other syllabus are content drops, not rebuilds.

**Live demo:** [t.me/stodi_waec_bot](https://t.me/stodi_waec_bot) (Telegram · WhatsApp next)
**Live API (Cloud Run):** https://stodi-api-3cg5degnzq-uc.a.run.app — try [`/health`](https://stodi-api-3cg5degnzq-uc.a.run.app/health), `POST /chat`
**Challenge:** Google for Startups AI Agents Challenge · Track 1 (Build)
**Built in public:** SABI AI & Automation ([@sabicoder](https://youtube.com/@sabicoder))

## How it works

```
Student (Telegram/WhatsApp: text · photo of notes · voice)
        │
        ▼
ADK ORCHESTRATOR (root agent — classifies intent, routes, synthesizes)
   ├── CURRICULUM agent   syllabus + past-Q corpus + marking schemes (RAG)
   ├── TUTOR agent        Socratic teaching, MCQ drills — never dumps answers
   ├── RETENTION agent    per-topic mastery, spaced-repetition scheduling
   └── GRADER agent       examiner-style scoring with partial credit
        │
        ▼
Google Cloud: Gemini 2.5 Flash · Vertex AI Search · Cloud Run · Cloud Scheduler · Firestore
        │
        ▼
EXAM PACKS — swappable content bundles (WAEC live · JAMB next · NECO later)
```

Every exam is a **pack, not a rebuild**: syllabus tree, question corpus with
marking schemes, and drill cadence in one JSON bundle
([exam_packs/](exam_packs/)). WAEC Mathematics (25 topics / 25 questions)
and English (19 topics / 20 questions, essay rubrics) ship today.

## Quickstart

```bash
python -m venv venv && venv/bin/pip install -r requirements.txt
cp .env.example .env          # fill in your keys

# Telegram bot (the product):
PYTHONPATH=.. venv/bin/python -m stodi.telegram_bot

# API (web clients + Cloud Scheduler):
PYTHONPATH=.. venv/bin/uvicorn stodi.core.api:app --reload --port 8080

# Tests + evals:
PYTHONPATH=.. STODI_STORE=memory venv/bin/python -m pytest tests/ -q
PYTHONPATH=.. venv/bin/python -m stodi.evals.run_evals     # 59/59 deterministic checks

# Deploy (Cloud Run + Firestore + Scheduler, one shot):
./deploy.sh
```

## MCP & security

The exam-pack registry is a real **MCP server** ([mcp_server.py](mcp_server.py),
stdio): `list_packs` · `pack_manifest` · `pack_questions`. Stodi's Curriculum
agent mounts it via ADK's `McpToolset`, and any other MCP-capable agent can
mount the same server — packs are swappable external content behind a
standard protocol.

Security: the Telegram bot **long-polls** (no inbound endpoint; bot-token
auth). The Cloud Run API key-gates every credit-spending route via
`X-API-Key` (`STODI_API_KEY` env) — `/health` is the only open route. Model
429s degrade to a friendly retry message, never a 500.

## Evals & guardrails

**77/77 checks green** — pack integrity (every answer key validated),
exhaustive MCQ grading, injection-proof calculator, retention semantics,
**examiner-labelled LLM grading (9/10 exact-match) and intent routing (8/8)
on Vertex AI**. See [EVALS.md](EVALS.md).

## Repo guide

| Doc | What's in it |
|---|---|
| [MISSION.md](MISSION.md) | Mission, wedge, beachhead, MVP scope |
| [SPEC.md](SPEC.md) | Build spec & mandatory-tech compliance |
| [ARCH.md](ARCH.md) / [FLOW.md](FLOW.md) | Architecture & agentic flows |
| [PITCH.md](PITCH.md) | Business case: market, pricing, unit economics, GTM |
| [SUBMISSION.md](SUBMISSION.md) | Challenge submission narrative |
| [EVALS.md](EVALS.md) | Eval methodology + results |
| [DEPLOY.md](DEPLOY.md) | Cloud wiring & one-shot deploy |
| [deck/stodi_pitch.pptx](deck/stodi_pitch.pptx) | 12-slide panel deck |

Code: [agents/](agents/) (5 ADK agents) · [tools/](tools/) (calculator,
grounding, drip scheduler, pilot stats) · [core/](core/) (channel-agnostic
service + FastAPI) · [config/](config/) (settings, exam-pack loader) ·
[persistence/](persistence/) (JSON / Firestore / memory stores) ·
[evals/](evals/) (harness + datasets).
