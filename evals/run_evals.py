"""Stodi eval harness.

Six suites. Four are deterministic and run with no credentials; two drive
Gemini through the real ADK agents and are skipped (with the reason printed)
when no working credential is available.

  1. pack_integrity   — every pack loads, every MCQ key is valid, every
                        question maps to a real syllabus topic
  2. mcq_grading      — grade_mcq() over every MCQ in every pack, plus
                        case/whitespace variants and wrong-answer checks
  3. calculator       — calculate() against known WAEC-style computations
  4. retention        — mastery updates, weak/strong classification,
                        review-queue ordering
  5. grading_llm      — Grader agent vs. examiner-labelled answers
                        (evals/datasets/grading_cases.json)
  6. routing_llm      — orchestrator routes messages to the right sub-agent
                        (evals/datasets/routing_cases.json)

Run:  PYTHONPATH=.. venv/bin/python -m stodi.evals.run_evals
Results are printed and written to evals/results.json.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Evals must never touch real student data and never send drips.
os.environ["STODI_STORE"] = "memory"
os.environ.setdefault("STODI_DRIP_DRY_RUN", "true")

EVALS_DIR = Path(__file__).resolve().parent
DATASETS = EVALS_DIR / "datasets"

PACKS = [("waec", "mathematics"), ("waec", "english")]


def _case(case_id: str, passed: bool, detail: str = "") -> dict:
    return {"id": case_id, "passed": bool(passed), "detail": detail}


# ─── Suite 1: pack integrity ─────────────────────────────────

def suite_pack_integrity() -> list[dict]:
    from stodi.config.exam_pack import load_exam_pack

    results = []
    for board, subject in PACKS:
        pack = load_exam_pack(board, subject)
        topic_ids = {t.id for t in pack.syllabus.topics}
        qs = pack.past_questions.questions

        results.append(_case(f"{subject}:loads", True, f"{len(qs)} questions, {len(topic_ids)} topics"))
        results.append(_case(
            f"{subject}:unique_ids",
            len(qs) == len({q.id for q in qs}),
            "duplicate question ids" if len(qs) != len({q.id for q in qs}) else "",
        ))

        bad_topic = [q.id for q in qs if q.topic_id not in topic_ids]
        results.append(_case(f"{subject}:topic_links", not bad_topic, str(bad_topic)))

        bad_key = []
        for q in qs:
            if q.question_type == "mcq":
                letters = [o.split(".")[0].strip() for o in (q.options or [])]
                if not q.options or q.correct_answer not in letters:
                    bad_key.append(q.id)
        results.append(_case(f"{subject}:mcq_answer_keys", not bad_key, str(bad_key)))

        no_scheme = [
            q.id for q in qs
            if q.question_type in ("theory", "essay") and not q.marking_scheme
        ]
        results.append(_case(f"{subject}:marking_schemes", not no_scheme, str(no_scheme)))
    return results


# ─── Suite 2: MCQ grading ────────────────────────────────────

def suite_mcq_grading() -> list[dict]:
    from stodi.agents.grader import grade_mcq
    from stodi.config.exam_pack import load_exam_pack

    results = []
    for board, subject in PACKS:
        pack = load_exam_pack(board, subject)
        for q in pack.past_questions.questions:
            if q.question_type != "mcq":
                continue
            key = q.correct_answer
            wrong = next(
                o.split(".")[0].strip() for o in q.options
                if o.split(".")[0].strip() != key
            )
            checks = [
                grade_mcq(key, key, q.id)["correct"] is True,
                grade_mcq(key.lower(), key, q.id)["correct"] is True,
                grade_mcq(f"  {key} ", key, q.id)["correct"] is True,
                grade_mcq(wrong, key, q.id)["correct"] is False,
            ]
            results.append(_case(f"mcq:{q.id}", all(checks)))
    return results


# ─── Suite 3: calculator ─────────────────────────────────────

CALC_CASES = [
    ("log2(8) + log2(16)", 7),                      # WAEC-MATH-2022-01
    ("sqrt(144)", 12),
    ("27**(2/3)", 9),                                # indices
    ("0.5 * 5 * 7 * sin(radians(60))", 15.155445),   # triangle area
    ("(22/7) * 7**2 * 10", 1540),                    # cylinder volume
    ("2**5", 32),
    ("(2*4) - (3*1)", 5),                            # 2x2 determinant
    ("5² + 3×7", 46),                                # unicode normalization
    ("√(144)", 12),                                  # unicode sqrt
]

CALC_REJECTS = [
    "__import__('os').system('id')",
    "().__class__",
    "1/0",
    "factorial(99999)",
]


def suite_calculator() -> list[dict]:
    from stodi.tools.agent_tools import calculate

    results = []
    for expr, expected in CALC_CASES:
        out = calculate(expr)
        ok = out["status"] == "success" and abs(float(out["result"]) - expected) < 1e-4
        results.append(_case(f"calc:{expr}", ok, f"got {out['result']}"))
    for expr in CALC_REJECTS:
        out = calculate(expr)
        results.append(_case(f"calc-reject:{expr[:24]}", out["status"] == "error", f"got {out['result']}"))
    return results


# ─── Suite 4: retention / mastery ────────────────────────────

def suite_retention() -> list[dict]:
    from stodi.tools.agent_tools import (
        get_next_review,
        get_progress_report,
        get_student_profile,
        update_student_mastery,
    )

    sid = "eval-student"
    results = []

    profile = get_student_profile(sid)
    results.append(_case("retention:new_profile", profile["mastery"] == {} and profile["total_quizzes"] == 0))

    # Low score → weak topic
    upd = update_student_mastery(sid, "B3", score=1, max_score=3)
    results.append(_case("retention:weak_status", upd["status"] == "weak", f"got {upd['status']}"))

    # High score → strong topic
    upd = update_student_mastery(sid, "A4", score=3, max_score=3)
    results.append(_case("retention:mastered_status", upd["status"] == "mastered", f"got {upd['status']}"))

    profile = get_student_profile(sid)
    results.append(_case(
        "retention:weak_strong_lists",
        "B3" in profile["weak_topics"] and "A4" in profile["strong_topics"],
        f"weak={profile['weak_topics']} strong={profile['strong_topics']}",
    ))

    # Weighted average: 100 then 0 → 0.7*100 + 0.3*0 = 70
    update_student_mastery(sid, "D1", score=2, max_score=2)
    upd = update_student_mastery(sid, "D1", score=0, max_score=2)
    results.append(_case("retention:weighted_average", upd["mastery_pct"] == 70, f"got {upd['mastery_pct']}"))

    # Review queue surfaces the weakest topic first
    review = get_next_review(sid, limit=3)
    first = review["review_topics"][0]["id"] if review["review_topics"] else None
    results.append(_case("retention:weakest_first", first == "B3", f"got {first}"))

    report = get_progress_report(sid)
    results.append(_case(
        "retention:progress_report",
        report["topics_studied"] == 3 and report["total_quizzes"] == 4,
        str(report),
    ))
    return results


# ─── LLM gate ────────────────────────────────────────────────

def llm_available() -> tuple[bool, str]:
    try:
        from google import genai
        from stodi.config import settings

        if settings.USE_VERTEXAI:
            client = genai.Client(
                vertexai=True,
                project=settings.GOOGLE_CLOUD_PROJECT,
                location=settings.GOOGLE_CLOUD_LOCATION,
            )
        else:
            client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        client.models.generate_content(model=settings.MODEL, contents="ping")
        return True, "ok"
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:200]


# ─── Suite 5: grading accuracy (LLM) ─────────────────────────

async def _run_agent(agent, message: str, user_id: str) -> tuple[str, set[str]]:
    """Send one message through an ADK Runner; return (text, participating agents)."""
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name="stodi-evals", session_service=session_service)
    session = await session_service.create_session(app_name="stodi-evals", user_id=user_id)

    text, participants = "", set()
    content = types.Content(role="user", parts=[types.Part(text=message)])
    async for event in runner.run_async(user_id=user_id, session_id=session.id, new_message=content):
        if event.author:
            participants.add(event.author)
        try:
            for call in event.get_function_calls():
                if call.name == "transfer_to_agent":
                    participants.add((call.args or {}).get("agent_name", ""))
        except Exception:  # noqa: BLE001
            pass
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    text += part.text
    return text, participants


async def suite_grading_llm() -> list[dict]:
    from stodi.agents.grader import grader_agent

    cases = json.loads((DATASETS / "grading_cases.json").read_text())["cases"]
    results = []
    for case in cases:
        prompt = (
            "Grade this student answer strictly against the official marking scheme.\n\n"
            f"QUESTION: {case['question_text']}\n"
            f"MARKING SCHEME: {case['marking_scheme']}\n"
            f"MAX MARKS: {case['max_marks']}\n"
            f"STUDENT ANSWER: {case['student_answer']}\n\n"
            'Respond ONLY with JSON: {"marks_awarded": <integer>, "justification": "<one sentence>"}'
        )
        try:
            text, _ = await _run_agent(grader_agent, prompt, f"eval-{case['id']}")
            m = re.search(r'"marks_awarded"\s*:\s*(\d+)', text) or re.search(r"\b(\d+)\s*/\s*\d+", text) or re.search(r"\b(\d+)\b", text)
            awarded = int(m.group(1)) if m else -1
            ok = abs(awarded - case["expected_marks"]) <= case["tolerance"]
            results.append(_case(
                case["id"], ok,
                f"awarded {awarded}, expected {case['expected_marks']}±{case['tolerance']}",
            ))
        except Exception as e:  # noqa: BLE001
            results.append(_case(case["id"], False, f"error: {str(e)[:120]}"))
    return results


# ─── Suite 6: intent routing (LLM) ───────────────────────────

async def suite_routing_llm() -> list[dict]:
    from stodi.agents.orchestrator import root_agent

    cases = json.loads((DATASETS / "routing_cases.json").read_text())["cases"]
    results = []
    for case in cases:
        try:
            _, participants = await _run_agent(root_agent, case["message"], f"eval-{case['id']}")
            hit = participants & set(case["acceptable_agents"])
            results.append(_case(
                case["id"], bool(hit),
                f"participants={sorted(participants)} acceptable={case['acceptable_agents']}",
            ))
        except Exception as e:  # noqa: BLE001
            results.append(_case(case["id"], False, f"error: {str(e)[:120]}"))
    return results


# ─── Runner ──────────────────────────────────────────────────

def summarize(name: str, results: list[dict]) -> dict:
    passed = sum(1 for r in results if r["passed"])
    return {"suite": name, "passed": passed, "total": len(results), "cases": results}


def main() -> int:
    # Importing the stodi package pulls in the agent chain (and settings)
    # before this module's env override can run, so the STODI_STORE env var
    # may already be frozen to its .env value. Pin the in-memory store
    # directly — evals must never be able to touch real student profiles.
    from stodi.persistence import MemoryStore
    from stodi.persistence.store import reset_store_for_tests

    reset_store_for_tests(MemoryStore())

    out: dict = {"run_at": datetime.now().isoformat(), "suites": []}

    print("Stodi evals\n" + "=" * 50)
    for name, fn in [
        ("pack_integrity", suite_pack_integrity),
        ("mcq_grading", suite_mcq_grading),
        ("calculator", suite_calculator),
        ("retention", suite_retention),
    ]:
        summary = summarize(name, fn())
        out["suites"].append(summary)
        print(f"{name:18} {summary['passed']}/{summary['total']} passed")
        for r in summary["cases"]:
            if not r["passed"]:
                print(f"  FAIL {r['id']}: {r['detail']}")

    ok, reason = llm_available()
    if ok:
        for name, fn in [("grading_llm", suite_grading_llm), ("routing_llm", suite_routing_llm)]:
            summary = summarize(name, asyncio.run(fn()))
            out["suites"].append(summary)
            print(f"{name:18} {summary['passed']}/{summary['total']} passed")
            for r in summary["cases"]:
                if not r["passed"]:
                    print(f"  FAIL {r['id']}: {r['detail']}")
    else:
        out["llm_suites_skipped"] = reason
        print(f"grading_llm        SKIPPED (no LLM access: {reason[:80]})")
        print(f"routing_llm        SKIPPED (no LLM access: {reason[:80]})")

    (EVALS_DIR / "results.json").write_text(json.dumps(out, indent=2))
    print("=" * 50)
    total_passed = sum(s["passed"] for s in out["suites"])
    total = sum(s["total"] for s in out["suites"])
    print(f"TOTAL: {total_passed}/{total} passed → evals/results.json")
    return 0 if total_passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
