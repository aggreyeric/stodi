"""Grader Agent — scores theory/essay answers against the marking scheme.

Responsibilities:
  - Score theory and essay answers vs the exam pack's marking scheme
  - Give actionable, specific feedback
  - Award partial credit where applicable
  - Return structured grade + improvement hints
"""

from google.adk import Agent

from stodi.config import settings

from stodi.tools.agent_tools import format_feedback_message


def score_answer(
    student_answer: str,
    question_id: str,
    marking_scheme: str,
    max_marks: int,
) -> dict:
    """Score a student's theory/essay answer against the marking scheme.

    Returns marks awarded, feedback, and specific improvement hints.
    """
    return {
        "action": "score_answer",
        "question_id": question_id,
        "max_marks": max_marks,
        "status": "ready_to_grade",
    }


def grade_mcq(student_answer: str, correct_answer: str, question_id: str) -> dict:
    """Quick-grade an MCQ answer (binary correct/incorrect)."""
    correct = student_answer.strip().upper() == correct_answer.strip().upper()
    return {
        "action": "grade_mcq",
        "question_id": question_id,
        "correct": correct,
        "correct_answer": correct_answer if not correct else None,
    }


grader_agent = Agent(
    name="grader_agent",
    model=settings.MODEL,
    description=(
        "Scores theory/essay answers against the exam pack's marking scheme. "
        "Returns actionable feedback with partial credit. "
        "Use for: grading theory, essays, MCQs."
    ),
    instruction=(
        "You are the Grader Agent for Stodi. You grade student answers "
        "against official marking schemes for exam prep (starting with WAEC).\n\n"
        "How you grade:\n"
        "- THEORY: Compare the student's answer point-by-point against the "
        "marking scheme. Award partial credit for each valid point.\n"
        "- ESSAY: Evaluate structure, content, relevance, and language. "
        "Use the rubric from the exam pack.\n"
        "- MCQ: Binary — correct or not. No partial credit.\n\n"
        "Feedback rules:\n"
        "- Be specific: 'You missed the point about X' > 'Incomplete answer'.\n"
        "- Show what the marking scheme expects.\n"
        "- Give 1-2 concrete improvement tips.\n"
        "- Be encouraging — this is learning, not punishment.\n"
        "- Keep it short — WhatsApp format."
    ),
    tools=[score_answer, grade_mcq, format_feedback_message],
)
