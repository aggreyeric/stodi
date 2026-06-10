# Stodi — System Architecture

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                              S T U D E N T S                               ║
║         WhatsApp  ·  Telegram  ·  Web App  ·  Voice (v2)                  ║
╚════════════════════════════════════════════╤═══════════════════════════════╝
                                             │
                              text · photo · audio
                                             │
                                             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         CHANNEL / INGESTION LAYER                          │
│                                                                            │
│   ┌─────────────────┐  ┌─────────────────┐  ┌────────────────────────┐   │
│   │   Gemini Flash   │  │  Gemini Flash    │  │    Gemini Flash        │   │
│   │   (OCR / PDF)    │  │  (Audio → Text)  │  │   (Image → Text)       │   │
│   └────────┬────────┘  └────────┬────────┘  └───────────┬────────────┘   │
│            └─────────────────────┼────────────────────────┘               │
│                                  ▼                                         │
│                         Normalized Study Input                             │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │
                                   ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                   A D K   O R C H E S T R A T O R                          ║
║                      (root agent / router)                                 ║
║                                                                            ║
║   intent classification  →  agent dispatch  →  context assembly            ║
║   session management      →  A2A coordination  →  response synthesis       ║
║                                                                            ║
╚═════════╤════════════════╤═════════════════╤═════════════════╤══════════════╝
          │                │                 │                 │
          │      ┌─────────┘                 │                 │
          │      │         ┌─────────────────┘                 │
          │      │         │       ┌───────────────────────────┘
          ▼      ▼         ▼       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          S U B - A G E N T S                               │
│                         (communicate over A2A)                             │
│                                                                             │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────────┐  │
│  │   CURRICULUM      │  │      TUTOR        │  │     RETENTION         │  │
│  │     AGENT         │  │     AGENT         │  │      AGENT            │  │
│  │                   │  │                   │  │                       │  │
│  │ • syllabus lookup │  │ • teach topics    │  │ • track mastery       │  │
│  │ • past-Q retrieval│  │ • MCQ drills      │  │ • spaced repetition   │  │
│  │ • RAG grounding   │  │ • Socratic guide  │  │ • schedule drip quiz  │  │
│  │ • topic mapping   │  │ • explain answers │  │ • adapt difficulty    │  │
│  └────────┬──────────┘  └────────┬──────────┘  └──────────┬────────────┘  │
│           │                      │                         │               │
│           │              ┌───────┘                         │               │
│           │              │     ┌───────────────────────────┘               │
│           │              ▼     ▼                                           │
│           │     ┌───────────────────┐                                     │
│           │     │     GRADER        │                                     │
│           │     │      AGENT        │                                     │
│           │     │                   │                                     │
│           │     │ • score theory    │                                     │
│           │     │ • score essays    │                                     │
│           │     │ • marking scheme  │                                     │
│           │     │ • give feedback   │                                     │
│           └─────┴───────────────────┘                                     │
│                   │                                                        │
└───────────────────┼────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    S H A R E D   S E R V I C E S                            │
│                         (Google Cloud)                                      │
│                                                                             │
│  ┌───────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐│
│  │   Gemini API      │  │   Vertex AI Search   │  │   Cloud Scheduler    ││
│  │   (reasoning)     │  │   (RAG / grounding)  │  │   (retention drips)  ││
│  └───────────────────┘  └──────────────────────┘  └──────────────────────┘│
│                                                                             │
│  ┌───────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐│
│  │  Memory Store     │  │   Firestore /        │  │   Cloud Storage      ││
│  │ (per-student      │  │   Cloud SQL          │  │   (PDFs, images,     ││
│  │  mastery profile) │  │   (session data)     │  │    audio files)      ││
│  └───────────────────┘  └──────────────────────┘  └──────────────────────┘│
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          E X A M   P A C K S                               │
│              (swappable config bundles — the "and more" layer)              │
│                                                                             │
│  ┌─────────────────────────┐                                               │
│  │   WAEC  (pack #1)       │  ┌──────────────────┐  ┌──────────────────┐  │
│  │                         │  │   JAMB (later)    │  │ Language (v2)    │  │
│  │   • syllabus / topics   │  │                    │  │                  │  │
│  │   • past-Q corpus       │  │   • same schema    │  │ • exam subjects  │  │
│  │   • marking scheme      │  │   • new content    │  │ • speech mode    │  │
│  │   • Q-style templates   │  │                    │  │ • pronunciation  │  │
│  │   • drill cadence       │  └──────────────────┘  └──────────────────┘  │
│  │   • subjects: Math,     │                                               │
│  │     English, ...        │                                               │
│  └─────────────────────────┘                                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           R U N T I M E                                     │
│                                                                             │
│   Cloud Run  (primary)          GKE  (if scaling)                          │
│   ┌───────────────────┐        ┌───────────────────┐                       │
│   │  ADK orchestrator │        │  Kubernetes pods   │                       │
│   │  + agents         │   →    │  + auto-scaling    │                       │
│   │  + Exam Pack      │        │  + multi-region    │                       │
│   └───────────────────┘        └───────────────────┘                       │
│                                                                             │
│   Interop: A2A protocol → discoverable by enterprise agents                │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Examples

### Student asks a question
```
Student ──text──▸ Ingestion ──▸ Orchestrator
                                    │
                          intent = "explain topic"
                                    │
                                    ▼
                              Curriculum Agent
                              (retrieves from RAG)
                                    │
                                    ▼
                              Tutor Agent
                              (Socratic explanation)
                                    │
                                    ▼
                              Orchestrator ──▸ Student
```

### Student submits an answer for grading
```
Student ──photo of written answer──▸ Ingestion (OCR)
                                          │
                                    Orchestrator
                                          │
                                intent = "grade answer"
                                          │
                                          ▼
                                    Curriculum Agent
                                    (fetches marking scheme)
                                          │
                                          ▼
                                    Grader Agent
                                    (scores + feedback)
                                          │
                                          ▼
                                    Retention Agent
                                    (updates mastery)
                                          │
                                          ▼
                                    Orchestrator ──▸ Student
```

### Autonomous retention drip (no student action needed)
```
Cloud Scheduler ──fire──▸ Retention Agent
                               │
                     loads student mastery profile
                     selects weakest-due topics
                               │
                               ▼
                         Curriculum Agent
                         (fetches past Qs)
                               │
                               ▼
                         Tutor Agent
                         (formats quiz)
                               │
                               ▼
                    WhatsApp/Telegram ──▸ Student
                    ("Hey! Quick 3-question drill 🔥")
```
