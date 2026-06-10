"""Retention Agent — spaced repetition, mastery tracking, drip quizzes.

Responsibilities:
  - Track per-topic mastery for each student
  - Schedule spaced-repetition drips via Cloud Scheduler
  - Decide what to surface and when
  - Adapt difficulty based on performance history
  - Build personalized drip quizzes for autonomous push

This agent is the key differentiator vs NotebookLM/EdTech:
  NotebookLM waits for you. Stodi comes to you.
"""

from google.adk import Agent

from stodi.config import settings

from stodi.tools.agent_tools import (
    get_student_profile,
    update_student_mastery,
    get_next_review,
    get_progress_report,
)
from stodi.tools.drip_scheduler import (
    get_review_interval,
    is_due_for_review,
    build_drip_quiz,
    format_drip_message,
    get_students_due_now,
)


def schedule_drip(student_id: str, hours: int = 24) -> dict:
    """Schedule the next drip quiz for a student based on their weakest topics."""
    return {"action": "schedule_drip", "student_id": student_id, "hours": hours}


retention_agent = Agent(
    name="retention_agent",
    model=settings.MODEL,
    description=(
        "Tracks per-topic mastery, schedules spaced-repetition drips, "
        "decides what to surface and when. Has persistent memory per student. "
        "Can build personalized drip quizzes for autonomous push. "
        "Use for: mastery lookup, update, scheduling, progress reports, drip quizzes."
    ),
    instruction=(
        "You are the Retention Agent for Stodi. Your job is to make sure "
        "students NEVER forget what they've learned.\n\n"

        "═══ YOUR TOOLS ═══\n\n"
        "- GET_STUDENT_PROFILE: Full student history, mastery, preferences.\n"
        "- UPDATE_STUDENT_MASTERY: Record a quiz result → update mastery %.\n"
        "- GET_NEXT_REVIEW: Smart topic selection (weakest + longest gap).\n"
        "- GET_PROGRESS_REPORT: Summary for 'how am I doing?' queries.\n"
        "- GET_REVIEW_INTERVAL: How many hours until a topic needs review.\n"
        "- IS_DUE_FOR_REVIEW: Check if a specific topic is due now.\n"
        "- BUILD_DRIP_QUIZ: Create a personalized quiz for a student.\n"
        "- FORMAT_DRIP_MESSAGE: Format quiz into a friendly push notification.\n"
        "- GET_STUDENTS_DUE_NOW: Find all students who need review now.\n\n"

        "═══ SPACED-REPETITION INTERVALS ═══\n\n"
        "  weak (<50%)     → review in 24h\n"
        "  medium (50-79%) → review in 48h\n"
        "  mastered (80%+) → review in 72h\n"
        "  expert (95%+)   → review in 1 week\n\n"

        "═══ DRIP QUIZ STRATEGY ═══\n\n"
        "When building a drip quiz:\n"
        "  1. Pick the student's 2 weakest DUE topics → 1 question each\n"
        "  2. Pick 1 question from a STRONG topic → morale booster 💪\n"
        "  3. Never quiz on a topic mastered in the last 24h\n"
        "  4. Keep the message SHORT and friendly\n\n"

        "═══ MASTERY UPDATE RULES ═══\n\n"
        "- Weighted average: 70% old mastery + 30% new score (gradual)\n"
        "- Prioritize weakest topics for drip quizzes\n"
        "- Mix in easy questions to keep morale up\n"
        "- When reporting progress, be encouraging but honest\n\n"

        "═══ FORMAT RULES ═══\n\n"
        "- Keep responses SHORT — this is Telegram/WhatsApp\n"
        "- Use emojis: 📊 (stats), 📈 (improving), ⚠️ (needs work), "
        "💪 (strong), 🎯 (on track)\n"
        "- Progress reports should be scannable, not essays\n"
        "- Always end with a suggested next action"
    ),
    tools=[
        get_student_profile,
        update_student_mastery,
        get_next_review,
        get_progress_report,
        get_review_interval,
        is_due_for_review,
        build_drip_quiz,
        format_drip_message,
        get_students_due_now,
        schedule_drip,
    ],
)
