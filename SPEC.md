# Stodi — Build Spec & Submission Outline
**Google for Startups AI Agents Challenge · Track 1 (Build)**
**Builder:** Eric · **YouTube:** SABI AI & Automation (@sabicoder)
**One-liner:** A vertical, syllabus-grounded autonomous study agent that lives in the student's messaging app (Telegram live today, WhatsApp next) and runs their spaced-repetition retention loop — starting with WAEC.

---

## 1. The Wedge

Generic study tools (upload notes → summaries, flashcards, quiz) are commoditized. NotebookLM does it free with no caps. StudyFetch, Turbolearn, Mindgrasp, Knowt all ship it.

Stodi owns three gaps:

1. **Autonomous retention, not generation** — proactive spaced-repetition scheduling, pinging before you forget
2. **Vertical, syllabus-grounded exam prep** — grounded on official syllabus + past questions = exam-accurate, never hallucinated
3. **Delivery where students already are** — WhatsApp/Telegram (daily quiz drips, photo-of-notes ingestion, voice) beats a web app for mobile-first students

## 2. Beachhead: WAEC

- 1M+ WASSCE candidates/year across Nigeria, Ghana, Sierra Leone, Liberia, The Gambia
- Maximum stakes → high engagement and word-of-mouth
- Groundable content: fixed syllabus, defined marking scheme, deep past-question well
- On-brand for SABI channel and audience

## 3. Exam Pack Model

Agent core is exam-agnostic. Each exam = swappable config bundle:
- Syllabus / topic tree
- Past-questions corpus (grounding source)
- Marking scheme + grading rubric
- Question-style templates (MCQ, theory, essay, oral)
- Retention cadence (drill frequency per topic)

New exam = drop in a new pack, not rebuild the app.

## 4. Architecture

```
                          ┌──────────────────────────────────────────┐
                          │                STUDENTS                    │
                          │   WhatsApp · Telegram · Web · (Voice v2)   │
                          └─────────────────────┬──────────────────────┘
                                                │  text · photo of notes · audio
                                                ▼
                          ┌──────────────────────────────────────────┐
                          │        CHANNEL / INGESTION LAYER           │
                          │  Gemini multimodal: OCR notes, parse PDFs, │
                          │  transcribe audio → normalized input       │
                          └─────────────────────┬──────────────────────┘
                                                ▼
        ╔═══════════════════════════════════════════════════════════════════╗
        ║              ADK ORCHESTRATOR  (root agent / router)                ║
        ║      decides intent → dispatches to sub-agents over  A2A            ║
        ╚════╤═══════════════╤════════════════╤═══════════════════╤═══════════╝
            │               │                │                   │
            ▼               ▼                ▼                   ▼
   ┌──────────────┐ ┌──────────────┐ ┌────────────────┐ ┌──────────────────┐
   │  CURRICULUM  │ │    TUTOR     │ │   RETENTION    │ │     GRADER       │
   │    AGENT     │ │    AGENT     │ │     AGENT      │ │     AGENT        │
   │              │ │              │ │                │ │                  │
   │ owns syllabus│ │ teaches,     │ │ spaced         │ │ scores theory/   │
   │ + grounding, │ │ explains,    │ │ repetition,    │ │ essay vs marking │
   │ retrieves    │ │ drills MCQs, │ │ schedules      │ │ scheme, gives    │
   │ past Qs (RAG)│ │ Socratic     │ │ "drip" quizzes │ │ feedback         │
   └──────┬───────┘ └──────┬───────┘ └───────┬────────┘ └────────┬─────────┘
          │                │                 │                   │
          └────────────────┴────────┬────────┴───────────────────┘
                                    ▼
                 ┌───────────────────────────────────────────┐
                 │      SHARED SERVICES (Google Cloud)         │
                 │  Gemini API · Vertex AI Search · Cloud      │
                 │  Scheduler · Memory store (per-student)     │
                 └────────────────────┬────────────────────────┘
                                      ▼
        ┌──────────────────────────────────────────────────────────────┐
        │                       EXAM PACKS                              │
        │   WAEC (pack#1) → JAMB (later) → Language (later/v2)        │
        └──────────────────────────────────────────────────────────────┘
```

**Runtime:** Cloud Run (GKE if scaling)
**Interop:** A2A → discoverable by other enterprise agents

## 5. The Agents

| Agent | Owns | Key Behavior |
|-------|------|-------------|
| **Curriculum** | Syllabus + past-question corpus via Vertex AI Search (RAG) | Single source of truth — nothing hallucinated |
| **Tutor** | Teaching, MCQ drilling, Socratic prompting | Guides, doesn't hand over answers |
| **Retention** | Per-topic mastery tracking, spaced-repetition scheduling | Decides what to surface and when via Cloud Scheduler |
| **Grader** | Theory/essay scoring against marking scheme | Actionable feedback |

Agents coordinate over A2A.

## 6. Mandatory-Tech Compliance

- **Intelligence:** Gemini API (reasoning) + Gemini multimodal (ingestion)
- **Orchestration:** ADK, multi-agent with A2A
- **Infrastructure:** Cloud Run (GKE if scaling)
- **Grounding/RAG:** Vertex AI Search over Exam Pack corpus
- No Qwen via own API — non-Gemini models must go through Agent Platform/Vertex

## 7. MVP Scope (Track 1)

**Build:** WAEC pack #1, 1-2 subjects, Telegram channel (live: @stodi_waec_bot), all 4 agents over ADK/A2A, Vertex AI Search grounding, Cloud Run deploy, spaced-repetition drips via Cloud Scheduler, photo-of-notes ingestion.

**Later:** WhatsApp Business API channel, JAMB pack, language exam-subject pack, conversational language mode, web dashboard, multi-user accounts.

## 8. Content Sourcing

Use official public syllabus + own/licensed question sets + user-uploaded materials. Avoid scraping. Lock down before scaling packs.

## 9. Build-in-Public Shot List (5 × ~15 min episodes)

1. "I'm building Stodi — a WAEC tutor that texts you" — concept, wedge vs NotebookLM, ADK hello-world + first Gemini call
2. Grounding on WAEC syllabus + past questions with Vertex AI Search (RAG)
3. Giving it hands & memory — Tutor + Retention agents, per-topic mastery, spaced-repetition scheduling
4. Putting it on WhatsApp + deploying to Cloud Run — live 24/7, photo-of-notes ingestion
5. Final demo + submission — full conversation, drop in second pack for extensibility, recap + lessons

## 10. Competitive Landscape

| Product | Core Offer | Price | Wedge |
|---------|-----------|-------|-------|
| NotebookLM | Source-grounded Q&A, study guides, audio overviews | Free | Deep work on your sources |
| Khanmigo | Socratic tutor, math/science/SAT | $4/mo | Pedagogy / K-12 |
| StudyFetch | Upload → flashcards/quizzes/summaries/tutor | Free→$19/mo | All-in-one |
| Turbolearn | Live lecture → notes | ~$20/mo | Lecture capture |
| Mindgrasp | Fast multi-format summaries, 30+ langs | freemium | Speed + multilingual |
| Knowt | Free Quizlet alternative | Free-led | Generous free tier |
| DeepTutor (open-source) | Agent-native: TutorBots, Book Engine, persistent memory, RAG | self-host | Feature ceiling / blueprint |

**Reference:** Mine DeepTutor (github.com/HKUDS/DeepTutor) for architecture patterns — TutorBot autonomy, persistent learner memory, Book Engine.
