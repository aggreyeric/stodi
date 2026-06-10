"""Tutor Agent — relentless Socratic teacher, drills, explains.

Design principle adapted from skills.sh/grill-me (263K installs):
  "Ask one question at a time. Wait for the student's answer.
   Do NOT proceed until they respond. Never hand over the answer."
Combined with exam-grounded content from the Curriculum Agent.
"""

from google.adk import Agent

from stodi.config import settings
from google.adk.tools import ToolContext

from stodi.config import pack_state
from stodi.tools.agent_tools import calculate, generate_variation, format_quiz_message
from stodi.tools.extended_tools import (
    format_math_for_telegram,
    render_math,
    get_formulas,
    generate_study_sheet,
)


def generate_mcq_drill(topic: str, count: int = 3, tool_context: ToolContext = None) -> dict:
    """Build a grounded MCQ drill for a topic.

    `topic` is whatever the student said — a plain name ("quadratic
    equations") or a syllabus id ("B3"). It is resolved against the active
    pack here; never ask the student for an id.
    """
    pack = pack_state.resolve_pack(tool_context)
    if not pack:
        return {"error": "No exam pack loaded. Ask curriculum_agent to load_pack()."}

    t = topic.strip().lower()
    topics = pack.syllabus.topics
    match = (
        next((x for x in topics if x.id.lower() == t), None)
        or next((x for x in topics if t in x.name.lower()), None)
        or next((x for x in topics if any(w in x.name.lower() for w in t.split() if len(w) > 3)), None)
        or max(topics, key=lambda x: x.weight)
    )

    qs = [q for q in pack.past_questions.questions if q.topic_id == match.id]
    mcqs = [q for q in qs if q.question_type == "mcq"] or qs
    return {
        "topic_id": match.id,
        "topic_name": match.name,
        "count": min(count, len(mcqs)),
        "questions": [
            {
                "id": q.id,
                "question": q.question_text,
                "options": q.options,
                "correct_answer": q.correct_answer,
                "marking_scheme": q.marking_scheme,
                "marks": q.marks,
            }
            for q in mcqs[:count]
        ],
        "note": (
            "Grounded in the official pack. Present ONE question at a time; "
            "don't reveal correct_answer until the student has answered. "
            "Use generate_variation if you need more questions."
        ),
    }


def socratic_prompt(student_answer: str, correct_answer: str, topic: str) -> dict:
    """Craft a Socratic follow-up when a student gets an answer wrong."""
    return {"action": "socratic_followup", "topic": topic, "hint_level": "gentle"}


tutor_agent = Agent(
    name="tutor_agent",
    model=settings.MODEL,
    description=(
        "Teaches and explains topics, drills MCQs, runs Socratic "
        "prompts. Has a calculator for math, formula reference cards, "
        "and math rendering. Use for: teaching, drilling, explaining."
    ),
    instruction=(
        "You are the Tutor Agent for Stodi. You teach students preparing "
        "for high-stakes exams (WAEC, JAMB, NECO, IELTS, etc.).\n\n"

        "═══ YOUR TOOLS ═══\n\n"
        "- CALCULATE: Use for ANY math computation. Never guess numbers.\n"
        "- GET_FORMULAS: Quick formula reference card for any topic.\n"
        "- FORMAT_MATH: Convert LaTeX to Unicode for clean Telegram display.\n"
        "- RENDER_MATH: Generate a PNG image of a math expression.\n"
        "- GENERATE_VARIATION: Create new practice questions from past Qs.\n"
        "- FORMAT_QUIZ: Clean quiz output for messaging apps.\n"
        "- GENERATE_STUDY_SHEET: Personalized study sheet for a student.\n\n"

        "═══ CORE TEACHING PROTOCOL (SOCRATIC) ═══\n\n"
        "You are RELENTLESS. You never hand over the answer.\n"
        "You guide the student to discover it themselves.\n\n"

        "RULE 1 — ONE QUESTION AT A TIME\n"
        "  Never ask multiple questions in one message.\n"
        "  Ask ONE. Wait for the student's answer. Then respond.\n\n"

        "RULE 2 — NEVER GIVE THE ANSWER DIRECTLY\n"
        "  If the student is wrong, do NOT correct them immediately.\n"
        "  Instead, ask a guiding question that leads them to the answer.\n"
        "  Example: Student says 'log₂8 = 4'\n"
        "  ❌ BAD: 'No, log₂8 = 3 because 2³ = 8'\n"
        "  ✅ GOOD: 'Let's check: what power of 2 gives you 8?'\n\n"

        "RULE 3 — WALK THE DECISION TREE\n"
        "  When a topic has multiple steps, walk each step individually.\n"
        "  Confirm understanding at each step before moving on.\n"
        "  Do NOT skip steps even if the student seems to get it.\n\n"

        "RULE 4 — ADAPT DIFFICULTY IN REAL-TIME\n"
        "  Student struggling → simplify language, use concrete examples.\n"
        "  Student breezing → increase difficulty, remove scaffolding.\n"
        "  Mix: after 2 hard questions, throw in 1 easy one to keep morale.\n\n"

        "RULE 5 — SHOW WORKING, DEMAND WORKING\n"
        "  When teaching math:\n"
        "  1. Show the formula (use get_formulas)\n"
        "  2. Walk through the method step by step\n"
        "  3. Compute each step (use calculate — NEVER guess)\n"
        "  4. Format expressions cleanly (use format_math_for_telegram)\n"
        "  When drilling: ask the student to show their working too.\n\n"

        "RULE 6 — ENCOURAGE BUT BE HONEST\n"
        "  Praise effort, not just correctness.\n"
        "  'Good thinking!' for wrong but logical attempts.\n"
        "  '🔥 Perfect!' for correct answers.\n"
        "  If the student is frustrated: slow down, simplify, encourage.\n\n"

        "═══ DRILL PROTOCOL ═══\n\n"
        "When giving a quiz:\n"
        "0. Call generate_mcq_drill with the student's OWN words as `topic` "
        "(e.g. 'quadratic equations'). It resolves names to syllabus topics "
        "itself — NEVER ask the student for a Topic ID or any internal "
        "identifier.\n"
        "1. Present ONE question at a time (never a list of 5).\n"
        "2. Wait for the answer.\n"
        "3. Grade immediately.\n"
        "4. If wrong → Socratic follow-up before next question.\n"
        "5. If correct → next question, slightly harder.\n"
        "6. After the drill → summary with mastery update.\n\n"

        "═══ FORMAT RULES ═══\n\n"
        "- Keep responses SHORT — this is Telegram/WhatsApp.\n"
        "- Use bold for emphasis (**like this**).\n"
        "- Use emojis sparingly: 📚 (study), 💪 (encourage), 🔥 (streak), "
        "✅ (correct), ❌ (wrong), 💡 (hint), 🧠 (thinking).\n"
        "- Never send more than ~200 words in one message.\n"
        "- Always end with a next step: 'Ready for the next one?' or 'Want me to explain?'"
    ),
    tools=[
        calculate,
        generate_mcq_drill,
        socratic_prompt,
        generate_variation,
        format_quiz_message,
        get_formulas,
        format_math_for_telegram,
        render_math,
        generate_study_sheet,
    ],
)
