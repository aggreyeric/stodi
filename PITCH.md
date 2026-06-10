# Stodi — Business Case

**One-liner:** A syllabus-grounded autonomous study agent that lives in the
student's messaging app and runs their spaced-repetition retention loop —
starting with WAEC, the exam 1M+ West African students sit every year.

---

## 1. Problem

- Every year **1,000,000+ candidates** across Nigeria, Ghana, Sierra Leone,
  Liberia and The Gambia sit the WASSCE. One exam gates university admission
  and most formal employment.
- Students study hard and **forget most of it** — revision is unstructured,
  tutoring is expensive, and failure means a paid retake and a lost year.
- Existing AI study tools (NotebookLM, StudyFetch, Turbolearn) are
  **reactive**: the student must open an app, upload material, and drive
  every session. The students who most need structure never do that.

## 2. Insight

Retention is a scheduling problem, not a content problem. The product isn't
"answers on demand" — it's an agent that **knows what you know, predicts
when you'll forget it, and texts you first**. Delivery inside the messaging
app the student already opens 50× a day is what makes the loop stick.

## 3. Product (working today)

Telegram bot + FastAPI service over a 5-agent ADK system (orchestrator +
curriculum / tutor / retention / grader), grounded on official-syllabus
exam packs (WAEC Maths: 25 topics, 25 questions · English: 19 topics, 20
questions, incl. essay marking rubrics). Per-student mastery persists across
sessions; a drip scheduler builds personalized morning quizzes from each
student's weakest topics. 59/59 deterministic eval checks pass ([EVALS.md](EVALS.md)).

## 4. Market

| Layer | Who | Size (annual) |
|---|---|---|
| TAM | West African high-stakes exam candidates (WASSCE + JAMB + NECO + BECE) | ~4–5M candidates/yr |
| SAM | WASSCE + JAMB candidates with smartphone + messaging access | ~2M |
| SOM (24 mo) | Nigeria + Ghana WASSCE candidates reachable via creator/school channels | 100k students, 5–8% paid |

The engine is exam-agnostic: each new exam is a **content pack, not a
rebuild** — WAEC → JAMB → NECO → language certifications. Each pack is a new
SKU on the same agents.

## 5. Business model

| Tier | Price (assumption) | What's included |
|---|---|---|
| Free | ₦0 | 1 subject, daily 3-question drip, weekly progress report |
| Premium | **₦1,500/mo (~$1)** or ₦6,000/exam season | All subjects, unlimited tutoring + essay grading, mock exams, parent report |
| School (B2B) | ₦500/student/term | Cohort dashboards for teachers, bulk onboarding |
| Sponsored | NGO/state pays | Scholarship cohorts (CSR budgets already fund exam fees) |

Anchors: WASSCE registration is ~₦18k–28k; urban private lessons run
₦5k–20k/month. ₦1,500/month is in the "airtime decision" range, payable via
mobile money.

## 6. Unit economics (assumption-driven — tune in the open)

Cost driver is Gemini 2.5 Flash ($0.30/M input, $2.50/M output tokens).

| Profile | LLM calls/day | Tokens/mo (in/out) | COGS/mo |
|---|---|---|---|
| Free user (drip + grading only) | ~8 | 0.5M / 0.06M | **~$0.30** |
| Premium user (drip + daily tutoring) | ~30 | 1.8M / 0.23M | **~$1.10** |

At ₦1,500 (~$1.00) premium with a 1,500₦/$ FX assumption, margin is thin on
the heaviest users — the lever is already in the architecture: routing and
drip formatting move to **Flash-Lite** (≈3–6× cheaper), pushing premium COGS
to ~$0.45–0.60 → **40–55% gross margin**, improving every Gemini price cut.
Free-tier COGS (~$0.30) is the CAC: cheaper than any paid acquisition in the
region.

## 7. Distribution (the unfair advantage)

1. **Owned audience:** Stodi is built in public on the SABI AI & Automation
   YouTube channel (@sabicoder) — the build series doubles as the launch
   funnel, so CAC for the pilot cohort is ≈ ₦0.
2. **Class-rep ambassadors:** one student per class invites the WhatsApp/
   Telegram study group; the drip quiz is inherently shareable ("what did
   Stodi send you today?").
3. **Exam-season virality:** Jan–May panic window before the May/June
   WASSCE; daily streaks + mock-exam countdowns time the upgrade prompt.
4. **Schools/NGOs:** B2B tier sold on the cohort dashboard; state education
   budgets and CSR programs already pay exam fees for cohorts.

## 8. Moat

- **Content flywheel:** licensed/curated exam packs with marking schemes are
  tedious to assemble and compound per exam board — generic LLM wrappers
  can't match examiner-style grading without them.
- **Retention data:** months of per-topic mastery history make Stodi's drips
  smarter and switching costly — the agent literally knows the student.
- **Channel-native:** no app install, data-light, works on the phones
  students actually have.

## 9. Why now

Gemini Flash-class pricing makes per-student AI viable at African EdTech
price points for the first time; messaging penetration is near-universal
among exam candidates; and agent frameworks (ADK + A2A + MCP) make the
multi-agent retention loop a weekend-deployable Cloud Run service instead of
a platform build.

## 10. Roadmap

**Now:** WAEC Maths + English live on Telegram · Cloud Run + Scheduler
deploy · Vertex AI Search grounding over the full corpus.
**Next (90 days):** WhatsApp Business API channel · JAMB pack · 500-student
pilot with published retention metrics.
**Later:** voice drills for Oral English · school dashboards · NECO/BECE/
language-cert packs · A2A discovery + MCP tool surface so other education
agents can call Stodi's curriculum and grading as a service.

---

*Numbers marked as assumptions are deliberately conservative and meant to be
tuned with real pilot data. Before the panel, re-verify: current WASSCE
candidature per country, JAMB UTME registration counts, current Gemini
pricing, and the NGN/USD rate.*
