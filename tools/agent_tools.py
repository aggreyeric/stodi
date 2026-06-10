"""Agent Tools — real tools that make Stodi's agents actually work.

These are function tools registered with ADK agents so they can
DO things, not just talk about things.
"""

import re
from datetime import datetime

from stodi.tools.safe_math import safe_eval


# ═══════════════════════════════════════════════════════════════
# 1. CALCULATOR — math tutor needs to compute, not guess
# ═══════════════════════════════════════════════════════════════

def calculate(expression: str) -> dict:
    """Evaluate a mathematical expression safely (no code execution).

    Supports: +, -, *, /, **, sqrt, log, sin, cos, tan, pi, e,
    combinations (comb), permutations (perm), factorial, abs, round.

    Args:
        expression: Math expression like "log2(8) + log2(16)"
                   or "sqrt(144)" or "5**2 + 3*7"
    """
    expr = expression.strip()

    # Normalize a few common notations into function/operator form.
    replacements = {
        "√": "sqrt",
        "π": "pi",
        "²": "**2",
        "³": "**3",
        "×": "*",
        "÷": "/",
        "^": "**",
    }
    for old, new in replacements.items():
        expr = expr.replace(old, new)

    try:
        result = safe_eval(expr)
        if isinstance(result, float):
            if result == int(result):
                result = int(result)
            else:
                result = round(result, 6)
        return {"expression": expression, "result": result, "status": "success"}
    except ZeroDivisionError:
        return {"expression": expression, "result": "undefined (division by zero)", "status": "error"}
    except (ValueError, SyntaxError, TypeError, OverflowError) as e:
        return {"expression": expression, "result": f"Could not evaluate: {e}", "status": "error"}


# ═══════════════════════════════════════════════════════════════
# 2. MEMORY — per-student persistence across sessions
# ═══════════════════════════════════════════════════════════════
#
# Backed by the persistence layer (JSON file by default, Firestore in prod)
# so mastery survives restarts — this is what makes "we remember you" true.

def _new_profile(student_id: str) -> dict:
    now = datetime.now().isoformat()
    return {
        "student_id": student_id,
        "created_at": now,
        "current_subject": "mathematics",
        "current_exam_board": "waec",
        "mastery": {},  # topic_id → {"pct": 0-100, "attempts": N, "last_review": date}
        "total_quizzes": 0,
        "total_correct": 0,
        "streak_days": 0,
        "last_active": now,
        "weak_topics": [],
        "strong_topics": [],
    }


def get_student_profile(student_id: str) -> dict:
    """Retrieve a student's full profile — mastery, history, preferences."""
    from stodi.persistence import get_store

    store = get_store()
    profile = store.get(student_id)
    if profile is None:
        profile = _new_profile(student_id)
        store.put(student_id, profile)
    return profile


def set_student_pack(student_id: str, exam_board: str, subject: str) -> dict:
    """Persist the student's chosen exam board + subject."""
    from stodi.persistence import get_store

    profile = get_student_profile(student_id)
    profile["current_exam_board"] = exam_board.lower()
    profile["current_subject"] = subject.lower()
    profile["last_active"] = datetime.now().isoformat()
    get_store().put(student_id, profile)
    return {"student_id": student_id, "exam_board": exam_board, "subject": subject}


def update_student_mastery(
    student_id: str,
    topic_id: str,
    score: float,
    max_score: float,
) -> dict:
    """Update a student's mastery for a topic after answering."""
    from stodi.persistence import get_store

    profile = get_student_profile(student_id)
    pct = round((score / max_score) * 100) if max_score > 0 else 0

    if topic_id not in profile["mastery"]:
        profile["mastery"][topic_id] = {
            "pct": pct,
            "attempts": 1,
            "last_review": datetime.now().isoformat(),
            "history": [pct],
        }
    else:
        m = profile["mastery"][topic_id]
        # Weighted average: 70% old + 30% new (gradual improvement)
        m["pct"] = round(0.7 * m["pct"] + 0.3 * pct)
        m["attempts"] += 1
        m["last_review"] = datetime.now().isoformat()
        m["history"].append(pct)

    # Update aggregates
    profile["total_quizzes"] += 1
    if pct >= 80:
        profile["total_correct"] += 1
    profile["last_active"] = datetime.now().isoformat()

    # Recalculate weak/strong topics
    profile["weak_topics"] = [
        tid for tid, m in profile["mastery"].items() if m["pct"] < 50
    ]
    profile["strong_topics"] = [
        tid for tid, m in profile["mastery"].items() if m["pct"] >= 80
    ]

    get_store().put(student_id, profile)

    return {
        "topic_id": topic_id,
        "mastery_pct": profile["mastery"][topic_id]["pct"],
        "status": "mastered" if pct >= 80 else "review_soon" if pct >= 50 else "weak",
        "attempts": profile["mastery"][topic_id]["attempts"],
    }


def get_next_review(student_id: str, limit: int = 3) -> dict:
    """Get topics due for review, sorted by urgency.

    Priority: weakest + longest since last review.
    """
    from stodi.config import pack_state
    pack = pack_state.resolve_pack(student_id=student_id)
    profile = get_student_profile(student_id)

    if not profile["mastery"]:
        # New student — return high-weight topics
        if pack:
            topics = sorted(
                pack.syllabus.topics,
                key=lambda t: t.weight,
                reverse=True,
            )[:limit]
            return {
                "student_id": student_id,
                "review_topics": [
                    {"id": t.id, "name": t.name, "reason": "high weight, not yet studied"}
                    for t in topics
                ],
                "count": len(topics),
            }
        return {"student_id": student_id, "review_topics": [], "count": 0}

    # Sort: lowest mastery first, then oldest review first
    scored = []
    for tid, m in profile["mastery"].items():
        last = datetime.fromisoformat(m["last_review"])
        hours_since = (datetime.now() - last).total_seconds() / 3600
        urgency = (100 - m["pct"]) + hours_since  # lower mastery + longer gap = higher urgency
        scored.append((urgency, tid))

    scored.sort(reverse=True)
    top_ids = [tid for _, tid in scored[:limit]]

    # Build response with topic names
    topic_map = {}
    if pack:
        topic_map = {t.id: t.name for t in pack.syllabus.topics}

    return {
        "student_id": student_id,
        "review_topics": [
            {
                "id": tid,
                "name": topic_map.get(tid, tid),
                "mastery": profile["mastery"][tid]["pct"],
                "attempts": profile["mastery"][tid]["attempts"],
                "reason": f"mastery at {profile['mastery'][tid]['pct']}%, needs review",
            }
            for tid in top_ids
        ],
        "count": len(top_ids),
    }


def get_progress_report(student_id: str) -> dict:
    """Generate a student progress report — summary for status queries."""
    profile = get_student_profile(student_id)

    total = len(profile["mastery"])
    if total == 0:
        return {
            "student_id": student_id,
            "status": "new_student",
            "message": "No topics studied yet. Let's start! 📚",
        }

    avg_mastery = sum(m["pct"] for m in profile["mastery"].values()) / total
    accuracy = (
        round(profile["total_correct"] / profile["total_quizzes"] * 100)
        if profile["total_quizzes"] > 0
        else 0
    )

    return {
        "student_id": student_id,
        "topics_studied": total,
        "average_mastery": round(avg_mastery),
        "total_quizzes": profile["total_quizzes"],
        "accuracy": accuracy,
        "weak_topics": len(profile["weak_topics"]),
        "strong_topics": len(profile["strong_topics"]),
        "streak_days": profile["streak_days"],
    }


# ═══════════════════════════════════════════════════════════════
# 3. QUESTION GENERATOR — grounded variations from past Qs
# ═══════════════════════════════════════════════════════════════

def generate_variation(question_text: str, topic: str, question_type: str = "mcq") -> dict:
    """Request a variation of a past question.

    This is a prompt for the Tutor agent's LLM to generate a
    grounded variation — NOT hallucinated content. The agent uses
    the original question + marking scheme as constraints.
    """
    return {
        "action": "generate_variation",
        "original": question_text,
        "topic": topic,
        "type": question_type,
        "instruction": (
            f"Create a NEW question on '{topic}' that tests the same concept "
            f"as this past question but with different numbers/context. "
            f"Keep the same difficulty and format ({question_type}). "
            f"Include the answer and working."
        ),
    }


# ═══════════════════════════════════════════════════════════════
# 4. FORMATTER — clean output for messaging
# ═══════════════════════════════════════════════════════════════

def format_quiz_message(questions: list[dict], subject: str) -> dict:
    """Format a list of questions into a clean message for Telegram/WhatsApp."""
    lines = [f"📝 **{subject} Quiz**\n"]

    for i, q in enumerate(questions, 1):
        lines.append(f"**Q{i}.** {q['question_text']}")
        if q.get("options"):
            for opt in q["options"]:
                lines.append(f"   {opt}")
        lines.append("")

    lines.append("Reply with your answers! (e.g., '1C 2A 3B')")
    return {"formatted_message": "\n".join(lines)}


def format_feedback_message(
    question: str,
    student_answer: str,
    correct: bool,
    correct_answer: str | None = None,
    explanation: str | None = None,
    mastery_update: dict | None = None,
) -> dict:
    """Format grading feedback into a clean message."""
    if correct:
        msg = "✅ **Correct!**\n\n"
    else:
        msg = "❌ **Not quite.**\n\n"

    msg += f"**Your answer:** {student_answer}\n"

    if not correct and correct_answer:
        msg += f"**Correct answer:** {correct_answer}\n"

    if explanation:
        msg += f"\n💡 {explanation}\n"

    if mastery_update:
        emoji = "📈" if mastery_update["mastery_pct"] >= 80 else "📊" if mastery_update["mastery_pct"] >= 50 else "🔧"
        msg += f"\n{emoji} Topic mastery: {mastery_update['mastery_pct']}%"

    return {"formatted_message": msg}
