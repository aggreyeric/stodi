# Stodi — Evals

Judges' note: most agent submissions stop at "it runs." Stodi ships with a
repeatable eval harness ([evals/run_evals.py](evals/run_evals.py)) covering
content integrity, deterministic grading, tool safety, the retention engine,
and two LLM-judged suites over the real ADK agents.

Run it:

```bash
PYTHONPATH=.. venv/bin/python -m stodi.evals.run_evals
```

Results land in `evals/results.json`.

## Current results

Run: 2026-06-12 · `gemini-3.5-flash` on Vertex AI (global endpoint) · store=memory (no student data touched)

| Suite | What it proves | Result |
|---|---|---|
| `pack_integrity` | Every pack loads; every MCQ answer key is a real option; every question maps to a real syllabus topic; every theory/essay question has a marking scheme | **10/10** |
| `mcq_grading` | `grade_mcq()` over **every MCQ in both packs** — exact key, lowercase, padded whitespace, and a wrong answer per question | **29/29** |
| `calculator` | WAEC-style computations (logs, indices, trig area, mensuration, determinants) return exact values; injection attempts (`__import__`, attribute access, division by zero, factorial bombs) are **rejected** | **13/13** |
| `retention` | Mastery updates, weak/strong classification, weighted averaging (70/30), weakest-topic-first review queue, progress aggregates | **7/7** |
| `grading_llm` | Grader agent vs examiner-labelled marks (full / partial / zero credit) on 10 held-out answers — **9/10 exact-match, 10/10 within ±1 mark** | **10/10** |
| `routing_llm` | Orchestrator routes 8 intents (learn / quiz / grade / status) to the correct sub-agent over real ADK transfers | **8/8** |

**77/77 checks pass — including the live-LLM suites on Vertex AI.** The
harness probes credential access and skips the LLM suites with the reason
printed rather than over-claiming, so it runs green in CI with no secrets.

## Why these suites

- **Grounding is the product claim.** "Exam-accurate, never hallucinated"
  only holds if the corpus itself is consistent — `pack_integrity` enforces
  it on every pack, so a bad answer key can never ship silently. (It already
  caught one: a concord question whose key disagreed with its own marking
  scheme — fixed in pack v1.1.)
- **Grading must be trustworthy before it's autonomous.** MCQ grading is
  deterministic code, tested exhaustively. Theory/essay grading is the LLM's
  job, so it's measured against examiner-labelled answers with explicit
  partial-credit cases, not vibes.
- **The calculator is a safety surface.** It evaluates student-supplied
  text, so the suite asserts both correctness and rejection of code
  execution.
- **Retention is the wedge.** The spaced-repetition engine is plain Python —
  the suite pins its semantics (what counts as weak, what surfaces first).

## Guardrails (enforced in code, verified here)

- No `eval()` anywhere — `tools/safe_math.py` walks a whitelisted AST.
- Evals force `STODI_STORE=memory` and `STODI_DRIP_DRY_RUN=true`: they can
  never touch real student profiles or message real students.
- Tutor agent is instructed Socratic-first: guide, don't hand over answers.
- Grounding falls back to the local pack corpus when Vertex AI Search is not
  provisioned — the bot never claims cloud grounding it doesn't have.
