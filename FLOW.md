
   S T U D I   —   A G E N T I C   F L O W
   ═══════════════════════════════════════════


 ══════════════════════════════════════════════════════════════
   F L O W   1 :   S T U D E N T   A S K S   A   Q U E S T I O N
 ══════════════════════════════════════════════════════════════

   Student                    Orchestrator               Sub-Agents
   ─────────                  ─────────────              ─────────

       "What is            ┌──────────────┐
        logarithm?"  ──────▸│   classify    │
                            │    intent     │
                            │              │
                            │  "learn"     │
                            └──────┬───────┘
                                   │
                          transfer to agent
                                   │
                                   ▼
                            ┌──────────────┐     ┌──────────────────┐
                            │  CURRICULUM  │────▸│  search syllabus  │
                            │    AGENT     │     │  fetch past Qs    │
                            └──────┬───────┘     └──────────────────┘
                                   │
                          grounded content
                                   │
                                   ▼
                            ┌──────────────┐     ┌──────────────────┐
                            │    TUTOR     │────▸│  Socratic explain │
                            │    AGENT     │     │  guide, don't tell│
                            └──────┬───────┘     └──────────────────┘
                                   │
                            formatted reply
                                   │
                                   ▼
                            ┌──────────────┐
                            │   ORCHESTR.  │──────▸  "A logarithm is the
                            └──────────────┘         power to which a
                                                     base must be raised...
                                                     Want a drill? 💪"



 ══════════════════════════════════════════════════════════════
   F L O W   2 :   Q U I Z   &   G R A D E
 ══════════════════════════════════════════════════════════════

   Student                    Orchestrator               Sub-Agents
   ─────────                  ─────────────              ─────────

       "Quiz me"        ┌──────────────┐
                   ────▸│   classify    │
                        │    intent     │
                        │              │
                        │  "quiz"      │
                        └──────┬───────┘
                               │
                               ▼
                        ┌──────────────┐     ┌──────────────────┐
                        │  CURRICULUM  │────▸│  fetch past Q     │
                        │    AGENT     │     │  + marking scheme │
                        └──────┬───────┘     └──────────────────┘
                               │
                               ▼
                        ┌──────────────┐     ┌──────────────────┐
                        │    TUTOR     │────▸│  format MCQ       │
                        │    AGENT     │     │  present options   │
                        └──────┬───────┘     └──────────────────┘
                               │
                   ┌───────────┘
                   │
                   ▼
    "The answer     ┌──────────────┐
     is C"     ────▸│   classify    │
                   │    intent     │
                   │              │
                   │  "grade"     │
                   └──────┬───────┘
                          │
                          ▼
                   ┌──────────────┐     ┌──────────────────┐
                   │   CURRICULUM │────▸│  get marking      │
                   │    AGENT     │     │    scheme          │
                   └──────┬───────┘     └──────────────────┘
                          │
                          ▼
                   ┌──────────────┐     ┌──────────────────┐
                   │    GRADER    │────▸│  score answer     │
                   │    AGENT     │     │  vs scheme        │
                   └──────┬───────┘     └──────────────────┘
                          │
                          ▼
                   ┌──────────────┐     ┌──────────────────┐
                   │  RETENTION   │────▸│  update mastery   │
                   │    AGENT     │     │  schedule review  │
                   └──────┬───────┘     └──────────────────┘
                          │
                          ▼
                   "✅ Correct! log₂8 = 3,
                    log₂16 = 4, total = 7.
                    Mastery updated 📈"



 ══════════════════════════════════════════════════════════════
   F L O W   3 :   P H O T O   O F   N O T E S
 ══════════════════════════════════════════════════════════════

   Student                    Ingestion                  Sub-Agents
   ─────────                  ─────────                  ─────────

       [photo of         ┌──────────────┐
        handwritten] ────▸│    GEMINI     │
                          │  multimodal   │
                          │              │
                          │  OCR → text  │
                          └──────┬───────┘
                                 │
                                 ▼
                          ┌──────────────┐
                          │  ORCHESTR.   │──▸  (routes extracted text
                          └──────┬───────┘     through Flow 1 or 2)
                                 │
                                 ▼
                          "I read your notes.
                           You covered log rules.
                           Want me to quiz you?"



 ══════════════════════════════════════════════════════════════
   F L O W   4 :   A U T O N O M O U S   D R I P
 ══════════════════════════════════════════════════════════════

   (no student action — Stodi initiates)

   Cloud Scheduler                Sub-Agents               Student
   ──────────────                 ─────────                ────────

       fires daily          ┌──────────────┐
       at 08:00        ────▸│  RETENTION   │
                          │    AGENT      │
                          │              │
                          │ who's due?   │
                          │ what's weak? │
                          └──────┬───────┘
                                 │
                        weakest 3 topics
                                 │
                                 ▼
                          ┌──────────────┐     ┌──────────────────┐
                          │  CURRICULUM  │────▸│  fetch Qs for     │
                          │    AGENT     │     │  weak topics      │
                          └──────┬───────┘     └──────────────────┘
                                 │
                                 ▼
                          ┌──────────────┐     ┌──────────────────┐
                          │    TUTOR     │────▸│  format quiz      │
                          │    AGENT     │     │  add 1 easy Q 😉  │
                          └──────┬───────┘     └──────────────────┘
                                 │
                                 ▼
                          ┌──────────────┐
                          │  TELEGRAM /  │──────▸ "☀️ Morning! Quick
                          │  WHATSAPP    │        drill — 3 questions
                          └──────────────┘        on your weak spots.
                                                  Ready? 💪"



 ══════════════════════════════════════════════════════════════
   I N T E N T   R O U T I N G
 ══════════════════════════════════════════════════════════════

   Student message                 Classified intent        Route to
   ──────────────                  ─────────────────        ────────

   "Explain trigonometry"      ──▸  learn               ──▸ Curriculum → Tutor
   "Quiz me on algebra"        ──▸  quiz                ──▸ Curriculum → Tutor
   "The answer is B"           ──▸  grade               ──▸ Curriculum → Grader → Retention
   "How am I doing?"           ──▸  status              ──▸ Retention
   [photo of notes]            ──▸  upload              ──▸ Gemini OCR → learn/quiz
   "/start"                    ──▸  onboarding          ──▸ Orchestrator direct
   "/maths" or "/english"      ──▸  switch_pack         ──▸ Curriculum (load_pack)
   "anything else"             ──▸  learn (default)     ──▸ Curriculum → Tutor



 ══════════════════════════════════════════════════════════════
   A G E N T   C O L L A B O R A T I O N   M A P
 ══════════════════════════════════════════════════════════════

                     ┌──────────────────────────┐
                     │      ORCHESTRATOR         │
                     │      (root agent)         │
                     │                           │
                     │  • classify intent        │
                     │  • route to sub-agents    │
                     │  • synthesize responses   │
                     │  • manage session state   │
                     └─────────┬─────────────────┘
                               │
            ┌──────────────────┼──────────────────────┐
            │                  │                      │
            ▼                  ▼                      ▼
   ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐
   │  CURRICULUM    │  │     TUTOR      │  │    RETENTION       │
   │                │  │                │  │                    │
   │  ground truth  │  │  pedagogy      │  │  memory            │
   │  ────────────  │  │  ────────────  │  │  ────────────────  │
   │  syllabus      │◄─┤  teach         │◄─┤  track mastery     │
   │  past Qs       │  │  drill         │  │  schedule drips    │
   │  marking scheme│──┤  Socratic      │──┤  adapt intervals   │
   │                │  │                │  │                    │
   └───────┬────────┘  └───────┬────────┘  └────────┬───────────┘
           │                   │                     │
           │           ┌───────┘                     │
           │           │                             │
           │           ▼                             │
           │   ┌────────────────┐                    │
           │   │    GRADER      │                    │
           │   │                │                    │
           │   │  evaluation    │                    │
           │   │  ────────────  │                    │
           ├──▸│  score theory  │                    │
           │   │  score essays  │──┐                 │
           │   │  grade MCQs    │  │                 │
           │   └────────────────┘  │                 │
           │                       │                 │
           │    marking scheme ────┘    scores ──────┘
           │    from curriculum        feed into
           │                           mastery tracking
           │
           ▼
    ┌──────────────────────────────────────────────────┐
    │              E X A M   P A C K                    │
    │                                                   │
    │   WAEC ──▸ JAMB ──▸ NECO ──▸ IELTS ──▸ ...      │
    │                                                   │
    │   Drop in a pack. Don't rebuild the agent.       │
    └──────────────────────────────────────────────────┘

