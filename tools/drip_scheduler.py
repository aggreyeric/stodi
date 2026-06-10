"""Drip Scheduler — autonomous spaced-repetition quiz delivery.

This is the engine behind Flow 4 from FLOW.md:
  Cloud Scheduler fires → Retention picks weakest topics → pushes quiz

Two modes:
  1. CLOUD_SCHEDULER (production): HTTP endpoint on Cloud Run, triggered
     by Google Cloud Scheduler at configured times.
  2. LOCAL_POLLER (dev/demo): Runs in-process, checks every N minutes
     for students due for review.

The scheduler is the KEY differentiator vs NotebookLM/EdTech:
  - NotebookLM waits for you to come back. Stodi comes to you.
  - StudyFetch gives the same quiz to everyone. Stodi personalizes.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("stodi.drip")

# ═══════════════════════════════════════════════════════════════
# 1. SPACED-REPETITION INTERVALS
# ═══════════════════════════════════════════════════════════════

# Mastery → hours until next review
INTERVALS = {
    "weak": 24,       # <50% mastery → review tomorrow
    "medium": 48,     # 50-79% → review in 2 days
    "strong": 72,     # 80%+ → review in 3 days
    "mastered": 168,  # 95%+ → review in 1 week
}


def get_review_interval(mastery_pct: int) -> int:
    """Return hours until next review based on mastery level."""
    if mastery_pct >= 95:
        return INTERVALS["mastered"]
    elif mastery_pct >= 80:
        return INTERVALS["strong"]
    elif mastery_pct >= 50:
        return INTERVALS["medium"]
    else:
        return INTERVALS["weak"]


def is_due_for_review(topic_mastery: dict) -> bool:
    """Check if a topic is due for review now."""
    if "last_review" not in topic_mastery:
        return True  # Never reviewed → definitely due

    last = datetime.fromisoformat(topic_mastery["last_review"])
    interval_hours = get_review_interval(topic_mastery["pct"])
    next_due = last + timedelta(hours=interval_hours)

    return datetime.now() >= next_due


# ═══════════════════════════════════════════════════════════════
# 2. DRIP QUIZ BUILDER
# ═══════════════════════════════════════════════════════════════

def build_drip_quiz(student_id: str, num_questions: int = 3) -> dict:
    """Build a personalized drip quiz for a student.

    Strategy:
      - 2/3 questions from weakest due topics (spaced rep)
      - 1/3 questions from stronger topics (retention check)
      - At least 1 easy question for morale

    Returns:
      dict with quiz content ready to send via Telegram/WhatsApp.
    """
    from stodi.tools.agent_tools import get_student_profile, get_next_review
    from stodi.config import pack_state
    from stodi.agents.curriculum import questions_for_topic

    profile = get_student_profile(student_id)
    pack = pack_state.resolve_pack(student_id=student_id)  # the student's own pack
    review = get_next_review(student_id, limit=5)  # Get more than needed for selection

    if not review["review_topics"] or pack is None:
        return {
            "student_id": student_id,
            "status": "no_topics",
            "message": "Nothing to review yet — keep studying! 📚",
        }

    def _one_question(topic_id: str) -> dict | None:
        qs = questions_for_topic(pack, topic_id, limit=1)
        return qs[0] if qs else None

    # Sort by mastery (weakest first)
    topics = sorted(review["review_topics"], key=lambda t: t.get("mastery", 0))

    # Pick questions: 2 weak + 1 morale booster
    selected = []
    for topic in topics[:2]:  # Weakest 2
        q = _one_question(topic["id"])
        if q:
            q["reason"] = f"Review: {topic['name']} ({topic.get('mastery', 0)}% mastery)"
            selected.append(q)

    # Morale booster: pick from strongest topic if available
    if len(topics) > 2 and profile["strong_topics"]:
        q = _one_question(profile["strong_topics"][0])
        if q:
            q["reason"] = "💪 Confidence boost — you know this one!"
            selected.append(q)

    # If we didn't get enough, pad with whatever we have
    if len(selected) < num_questions:
        for topic in topics[2:]:
            if len(selected) >= num_questions:
                break
            q = _one_question(topic["id"])
            if q:
                q["reason"] = f"Practice: {topic['name']}"
                selected.append(q)

    return {
        "student_id": student_id,
        "status": "ready",
        "quiz": selected,
        "count": len(selected),
        "subject": pack.subject,
        "generated_at": datetime.now().isoformat(),
    }


def format_drip_message(quiz: dict) -> str:
    """Format a drip quiz into a friendly push notification message."""
    if quiz["status"] != "ready":
        return quiz.get("message", "")

    subject = quiz.get("subject", "").title()
    questions = quiz["quiz"]

    lines = [f"☀️ **Good morning! Time for your {subject} drill.**\n"]

    for i, q in enumerate(questions, 1):
        lines.append(f"**Q{i}.** {q.get('question_text', q.get('text', 'Loading...'))}")
        if q.get("options"):
            for opt in q["options"]:
                lines.append(f"   {opt}")
        lines.append("")

    lines.append("Reply with your answers! (e.g., '1C 2A 3B')")
    lines.append("Or type **skip** to do it later.")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 3. DUE STUDENTS CHECK (for scheduler trigger)
# ═══════════════════════════════════════════════════════════════

def get_students_due_now() -> list[dict]:
    """Return all students who have topics due for review right now.

    Used by Cloud Scheduler endpoint or local poller.
    """
    from stodi.persistence import get_store

    due_students = []
    for sid, profile in get_store().all().items():
        due_topics = []
        for tid, mastery in profile.get("mastery", {}).items():
            if is_due_for_review(mastery):
                due_topics.append({
                    "topic_id": tid,
                    "mastery": mastery["pct"],
                })

        if due_topics:
            due_students.append({
                "student_id": sid,
                "due_topics": due_topics,
                "due_count": len(due_topics),
            })

    return due_students


# ═══════════════════════════════════════════════════════════════
# 4. LOCAL POLLER (dev/demo mode)
# ═══════════════════════════════════════════════════════════════

async def run_drip_poller(
    interval_minutes: int = 60,
    telegram_bot=None,
    dry_run: bool = False,
) -> None:
    """Background task that checks for due students and sends drip quizzes.

    Args:
        interval_minutes: How often to check (default: 60 min)
        telegram_bot: Active python-telegram-bot Application instance
        dry_run: If True, logs but doesn't send messages
    """
    import asyncio

    logger.info(f"🕰️ Drip poller started (every {interval_minutes} min)")

    while True:
        try:
            due = get_students_due_now()
            if due:
                logger.info(f"📬 {len(due)} students due for review")
                for student in due:
                    quiz = build_drip_quiz(student["student_id"])
                    message = format_drip_message(quiz)

                    if dry_run:
                        logger.info(f"[DRY RUN] Would send to {student['student_id']}: {message[:80]}...")
                    elif telegram_bot:
                        # Send via Telegram
                        try:
                            await telegram_bot.bot.send_message(
                                chat_id=int(student["student_id"]),
                                text=message,
                                parse_mode="Markdown",
                            )
                            logger.info(f"✅ Sent drip quiz to {student['student_id']}")
                        except Exception as e:
                            logger.error(f"❌ Failed to send to {student['student_id']}: {e}")
                    else:
                        logger.info(f"No bot configured. Quiz for {student['student_id']}: {message[:80]}...")
            else:
                logger.info("📭 No students due for review")

        except Exception as e:
            logger.error(f"Drip poller error: {e}")

        await asyncio.sleep(interval_minutes * 60)


# ═══════════════════════════════════════════════════════════════
# 5. CLOUD RUN ENDPOINT (production)
# ═══════════════════════════════════════════════════════════════

def create_drip_endpoint():
    """Create a FastAPI endpoint for Cloud Scheduler to trigger.

    Usage in Cloud Run:
        POST /drip
        Authorization: Bearer <service-account-token>

    Google Cloud Scheduler config:
        - Target: Cloud Run URL
        - Schedule: "0 8 * * *" (daily at 08:00)
        - Time zone: Africa/Lagos (WAT)
    """
    try:
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
    except ImportError:
        logger.warning("FastAPI not installed. Install with: pip install fastapi uvicorn")
        return None

    app = FastAPI(title="Stodi Drip Scheduler")

    @app.post("/drip")
    async def drip_endpoint(request: Request):
        """Cloud Scheduler triggers this → sends drip quizzes to all due students."""
        logger.info("📬 Drip triggered by Cloud Scheduler")

        due = get_students_due_now()
        results = []

        for student in due:
            quiz = build_drip_quiz(student["student_id"])
            results.append({
                "student_id": student["student_id"],
                "status": quiz["status"],
                "questions_sent": quiz["count"],
            })

        return JSONResponse({
            "triggered_at": datetime.now().isoformat(),
            "students_notified": len(results),
            "details": results,
        })

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "stodi-drip-scheduler"}

    return app
