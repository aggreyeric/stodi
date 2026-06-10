# Stodi — Submission Narrative

**Google for Startups AI Agents Challenge · Track 1 (Build)**
**Builder:** Eric · YouTube: SABI AI & Automation (@sabicoder)

**One-liner:** An autonomous retention agent for any high-stakes exam —
the engine is exam-agnostic (each exam is a swappable content pack);
WAEC/WASSCE is the live beachhead pack.

---

## Problem

Over one million students across five West African countries sit the WASSCE
every year; the result gates university admission and formal employment.
They don't lack content — they lack **retention**. Revision is unstructured,
private tutoring is unaffordable for most, and every existing AI study tool
is reactive: the student has to show up, upload, and drive. The students who
most need structure never drive.

## Insight

Forgetting is predictable, so studying can be autonomous. Instead of a
chatbot that waits, Stodi is an agent that **owns the student's retention
loop**: it tracks per-topic mastery, schedules spaced-repetition reviews,
and initiates contact — a personalized quiz in the student's messaging app
each morning, built from their weakest topics, graded against the official
marking scheme, feeding the next schedule. The student's only job is to
reply.

## What we built

A 5-agent ADK system behind one orchestrator, deployed as a single service:

- **Orchestrator (root):** classifies intent, routes over ADK sub-agent
  transfer, synthesizes channel-friendly replies.
- **Curriculum agent:** single source of truth — official syllabus tree +
  question corpus + marking schemes, retrieved (Vertex AI Search when
  provisioned, local corpus fallback — it never claims grounding it doesn't
  have).
- **Tutor agent:** Socratic teaching and MCQ drills; guides, never dumps
  answers.
- **Retention agent:** per-topic mastery model (weighted moving average),
  urgency-ranked review queue, drip scheduling.
- **Grader agent:** examiner-style scoring with partial credit against the
  pack's marking scheme, including essay rubrics.

**Exam Pack model:** every exam is a swappable content bundle (syllabus,
question corpus, marking schemes, drill cadence). WAEC Mathematics (25
topics / 25 questions) and English (19 topics / 20 questions, essay rubrics
included) ship today; JAMB is a content drop, not a rebuild.

**Channels:** Telegram bot live today (text + photo-of-notes via Gemini
multimodal OCR); the service layer is channel-agnostic and WhatsApp Business
API is the next adapter. A FastAPI surface (`/chat`, `/progress`, `/drip`,
`/health`) serves web clients and Cloud Scheduler.

## Mandatory tech

| Requirement | How Stodi uses it |
|---|---|
| Gemini | **Gemini 3.5 Flash** on Vertex AI (global endpoint) powers all five agents + multimodal OCR ingestion; model id is env-switchable (`STODI_MODEL`) |
| ADK multi-agent | Root agent + 4 sub-agents over ADK transfer (A2A-style delegation) |
| Cloud Run | **Live:** https://stodi-api-3cg5degnzq-uc.a.run.app (`/health`, `/chat`, `/progress`, `/drip`) |
| Cloud Scheduler | **Live:** fires `/drip` daily at 08:00 Africa/Lagos for autonomous quizzes |
| Firestore | **Live:** durable per-student mastery profiles (JSON-file fallback for local dev) |
| Vertex AI Search | RAG grounding over the exam-pack corpus (config-gated; local-corpus grounding until the data store is provisioned) |
| **MCP (live)** | The exam-pack registry is an **MCP server** (`mcp_server.py`, stdio): `list_packs` / `pack_manifest` / `pack_questions`. The Curriculum agent consumes it via ADK's `McpToolset` — packs are external, swappable content behind a standard protocol, and any MCP-capable agent (Gemini CLI, Claude, a partner's tutor) can mount the same server |

## Security

- **Bot ↔ Telegram:** the bot **long-polls** Telegram's API authenticated by
  the bot token — there is no inbound webhook, no public bot endpoint to
  attack.
- **Public API:** Cloud Run routes that spend model credits (`/chat`,
  `/switch`, `/progress`, `/drip`) require an `X-API-Key` header
  (`STODI_API_KEY` env); `/health` stays open. Judges receive the key via
  the submission's testing-access field. A stranger with the URL gets 401,
  not our Gemini bill.
- **Cloud Scheduler** calls `/drip` with the same header; drips are
  additionally `DRY_RUN`-gated.
- **Model-call hygiene:** 429/exhaustion degrades to a friendly retry
  message (never a 500); the calculator is AST-whitelisted (no `eval`);
  evals are store-isolated and can never touch student data.

## Results / evidence

- **77/77 eval checks pass** ([EVALS.md](EVALS.md)): pack integrity (every
  answer key valid), exhaustive MCQ grading, calculator correctness **and
  injection rejection**, retention-engine semantics — plus the live-LLM
  suites on Vertex AI: the Grader matches examiner-labelled marks **exactly
  on 9/10 held-out answers (10/10 within ±1 mark)** including partial and
  zero credit, and the orchestrator routes **8/8 intents** to the correct
  sub-agent over real ADK transfers.
- The integrity suite already caught a real bug — an answer key that
  contradicted its own marking scheme — before any student saw it. That is
  the point: when your pitch is "exam-accurate," correctness must be
  enforced by CI, not vibes.
- Safety by construction: no `eval()` (AST-whitelisted calculator), evals
  can't touch student data, drip dry-run gating, Socratic no-answer-dumping
  instruction, grounded-or-silent retrieval.

## Roadmap

90 days: WhatsApp channel, JAMB pack, 500-student pilot with published
retention metrics. Later: Oral-English voice drills, school dashboards,
NECO/BECE packs, marketplace listing for the MCP pack registry + A2A
discovery.

Business case — market, pricing, unit economics, distribution: [PITCH.md](PITCH.md).
Architecture detail: [ARCH.md](ARCH.md) · Flows: [FLOW.md](FLOW.md) · Deploy: [DEPLOY.md](DEPLOY.md).
