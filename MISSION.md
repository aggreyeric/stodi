
   ███████╗████████╗ █████╗ ██████╗ ███████╗██╗
   ██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║
   ███████╗   ██║   ███████║██████╔╝███████╗██║
   ╚════██║   ██║   ██╔══██║██╔══██╗╚════██║██║
   ███████║   ██║   ██║  ██║██║  ██║███████║██║
   ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝

   A syllabus-grounded autonomous study agent for ANY
   high-stakes exam. Lives in your messaging app, runs
   your spaced-repetition retention loop. Every exam is
   a swappable pack — WAEC is pack #1, live today.
   (Telegram: @stodi_waec_bot · WhatsApp next)


 ══════════════════════════════════════════════════════════
   M I S S I O N
 ══════════════════════════════════════════════════════════

   Eliminate forgetting.

   Every year, over 1 million students across West Africa
   sit the WASSCE — one exam that determines their future.

   They study hard. They forget most of it.

   Stodi fixes the broken loop:
   not more content, not more flashcards —
   an agent that knows what you know,
   knows when you'll forget it,
   and texts you before you do.

   ┌──────────────────────────────────────────────────┐
   │                                                    │
   │   Study  ──▸  Stodi remembers  ──▸  You retain   │
   │                                                    │
   │   You forget ──▸ Stodi catches you ──▸ Quiz drip  │
   │                                                    │
   │   You struggle ──▸ Stodi adapts  ──▸ You master   │
   │                                                    │
   └──────────────────────────────────────────────────┘


 ══════════════════════════════════════════════════════════
   W H Y   S T O D I   W I N S
 ══════════════════════════════════════════════════════════

   The field:                               Stodi's answer:

   ┌─────────────────────┐                 ┌─────────────────────────┐
   │  NotebookLM         │                 │  Not Q&A — autonomous   │
   │  = ask, get answer  │       ──▸       │  retention. We ping     │
   │  (you drive)        │                 │  you. You don't drive.  │
   └─────────────────────┘                 └─────────────────────────┘

   ┌─────────────────────┐                 ┌─────────────────────────┐
   │  StudyFetch etc.    │                 │  Grounded on official   │
   │  = generate stuff   │       ──▸       │  syllabus + past Qs.    │
   │  (generic content)  │                 │  Exam-accurate. Always. │
   └─────────────────────┘                 └─────────────────────────┘

   ┌─────────────────────┐                 ┌─────────────────────────┐
   │  Web apps           │                 │  WhatsApp. Where the    │
   │  = go to the tool   │       ──▸       │  students already are.  │
   │  (desktop-first)    │                 │  Mobile-first. Daily.   │
   └─────────────────────┘                 └─────────────────────────┘


 ══════════════════════════════════════════════════════════
   B E A C H H E A D
 ══════════════════════════════════════════════════════════

   ┌──────────────────────────────────────────────────────────────────┐
   │                                                                  │
   │   WAEC / WASSCE                                                  │
   │                                                                  │
   │   🇳🇬 Nigeria   🇬🇭 Ghana   🇸🇱 Sierra Leone                      │
   │   🇱🇷 Liberia   🇬🇲 The Gambia                                    │
   │                                                                  │
   │   1,000,000+  candidates per year                                │
   │   1            exam determines their future                      │
   │   0            autonomous study agents built for them            │
   │                                                                  │
   └──────────────────────────────────────────────────────────────────┘


 ══════════════════════════════════════════════════════════
   E X A M   P A C K   M O D E L
 ══════════════════════════════════════════════════════════

   The engine is exam-agnostic.
   Each exam = one swappable pack.

   ┌─────────────────────────────────────────────────────────────┐
   │                                                             │
   │   WAEC ──now──▸ JAMB ──later──▸ Language ──v2──▸ ...       │
   │                                                             │
   │   Every pack contains:                                      │
   │   ┌──────────────────┐  ┌────────────────────┐             │
   │   │ • syllabus/tree  │  │ • marking scheme   │             │
   │   │ • past-Q corpus  │  │ • Q-style templates│             │
   │   │ • drill cadence  │  │ • grading rubric   │             │
   │   └──────────────────┘  └────────────────────┘             │
   │                                                             │
   │   Drop in a pack. Don't rebuild the app.                   │
   │                                                             │
   └─────────────────────────────────────────────────────────────┘


 ══════════════════════════════════════════════════════════
   A R C H I T E C T U R E   (4 agents, 1 orchestrator)
 ══════════════════════════════════════════════════════════
   (full diagram → ARCH.md)

   Student ──▸ Ingestion ──▸ ADK Orchestrator ──┬──▸ Curriculum
                                                 ├──▸ Tutor
                                                 ├──▸ Retention
                                                 └──▸ Grader
                                                       │
                                                       ▼
                                              Google Cloud Stack
                                          Gemini · Vertex · Scheduler
                                                       │
                                                       ▼
                                                  Exam Packs


 ══════════════════════════════════════════════════════════
   M V P   S C O P E
 ══════════════════════════════════════════════════════════

   ☑  WAEC Exam Pack — Mathematics (25 topics, 25 questions)
   ☑  WAEC Exam Pack — English (19 topics, 20 questions, essay rubrics)
   ☑  Telegram channel (text + photo ingestion) — @stodi_waec_bot
   ☐  WhatsApp channel (next — service layer is channel-agnostic)
   ☑  Curriculum Agent (RAG-grounded, syllabus + past-Q retrieval, marking scheme)
   ☑  Tutor Agent (Socratic + MCQ drills)
   ☑  Retention Agent (spaced-repetition scheduling, mastery tracking)
   ☑  Grader Agent (marking-scheme scoring, MCQ + theory + essay)
   ☑  ADK Orchestrator with sub-agent routing (A2A wired)
   ☑  Eval harness — 77/77 green incl. LLM grading + routing (EVALS.md)
   ☑  Business case + pitch deck (PITCH.md · deck/stodi_pitch.pptx)
   ☑  Demo video + pilot playbook prepared
   ☑  Dockerfile + one-shot deploy script (deploy.sh)
   ☑  Cloud Run LIVE — stodi-api-3cg5degnzq-uc.a.run.app (+ Firestore)
   ☑  Cloud Scheduler — daily drip 08:00 Africa/Lagos (dry-run gated)
   ☐  Vertex AI Search grounding  — data store provisioning (console step)
   ☐  Build-in-public: 5 episodes on YouTube


 ══════════════════════════════════════════════════════════
   S U B M I S S I O N
 ══════════════════════════════════════════════════════════

   Challenge:   Google for Startups AI Agents Challenge
   Track:       1 — Build
   Builder:     Eric
   YouTube:     SABI AI & Automation (@sabicoder)
   Repo:        local git ready — push to GitHub before submitting
   Live demo:   t.me/stodi_waec_bot (Telegram)
   Live API:    https://stodi-api-3cg5degnzq-uc.a.run.app  (Cloud Run)
   Narrative:   SUBMISSION.md · Business case: PITCH.md · Evals: EVALS.md

