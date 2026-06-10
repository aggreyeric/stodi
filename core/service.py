"""Channel-agnostic service layer.

Everything a channel needs:
  - handle_message(user_id, text)  → reply string
  - ocr_image(image_bytes, mime)   → extracted text
  - switch_pack(user_id, board, subject)
  - get_progress(user_id)

The ADK Runner, session handling, and Gemini calls live here once — not
duplicated in every channel adapter.
"""

from __future__ import annotations

import logging

from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from stodi.config import settings, pack_state
from stodi.agents.orchestrator import root_agent
from stodi.tools.agent_tools import set_student_pack, get_progress_report

logger = logging.getLogger("stodi.core")

_session_service = InMemorySessionService()
_user_sessions: dict[str, str] = {}

_runner = Runner(
    agent=root_agent,
    app_name="stodi",
    session_service=_session_service,
)


async def _get_or_create_session(user_id: str) -> str:
    if user_id not in _user_sessions:
        session = await _session_service.create_session(app_name="stodi", user_id=user_id)
        # Seed session state with the user's stored pack choice (per-session isolation).
        try:
            from stodi.tools.agent_tools import get_student_profile

            profile = get_student_profile(user_id)
            session.state["active_pack"] = [
                profile.get("current_exam_board", settings.DEFAULT_EXAM_BOARD),
                profile.get("current_subject", settings.DEFAULT_SUBJECT),
            ]
        except Exception as e:  # noqa: BLE001
            logger.debug("Could not seed session pack state: %s", e)
        _user_sessions[user_id] = session.id
    return _user_sessions[user_id]


def _seed_default_pack(user_id: str) -> None:
    """Best-effort: make this user's pack the process default for the turn.

    Belt-and-suspenders alongside session state, so non-agent tool paths and
    any code that reads the default still see the right subject.
    """
    try:
        from stodi.tools.agent_tools import get_student_profile

        profile = get_student_profile(user_id)
        pack_state.set_default_pack(
            profile.get("current_exam_board", settings.DEFAULT_EXAM_BOARD),
            profile.get("current_subject", settings.DEFAULT_SUBJECT),
        )
    except FileNotFoundError:
        pack_state.set_default_pack(settings.DEFAULT_EXAM_BOARD, settings.DEFAULT_SUBJECT)
    except Exception as e:  # noqa: BLE001
        logger.debug("Could not seed default pack: %s", e)


async def handle_message(user_id: str, text: str) -> str:
    """Send a message to Stodi and return its reply."""
    user_id = str(user_id)
    _seed_default_pack(user_id)
    session_id = await _get_or_create_session(user_id)

    content = types.Content(role="user", parts=[types.Part(text=text)])
    reply = ""
    try:
        async for event in _runner.run_async(
            user_id=user_id, session_id=session_id, new_message=content
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        reply += part.text
    except Exception as e:  # noqa: BLE001 — a model hiccup must never 500 a student
        logger.warning("Model call failed for %s: %s", user_id, e)
        if reply:
            return reply
        if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
            return "Whew, everyone's studying at once! 😅 Give me a few seconds and ask again."
        return "Hmm, something glitched on my side. Ask me again? 🔁"
    return reply or "Hmm, I couldn't process that. Try again?"


def switch_pack(user_id: str, exam_board: str, subject: str) -> dict:
    """Persist the user's exam/subject choice and load the pack."""
    user_id = str(user_id)
    # Persist the choice. The next turn's _seed_default_pack() (and session
    # seeding on session creation) will pick it up — no need to poke the live
    # session object here (its API is async).
    set_student_pack(user_id, exam_board, subject)
    pack_state.set_default_pack(exam_board, subject)
    pack = pack_state.load_cached(exam_board, subject)
    return {
        "status": "loaded",
        "pack": pack.name,
        "topics": len(pack.syllabus.topics),
        "questions": len(pack.past_questions.questions),
    }


def get_progress(user_id: str) -> dict:
    """Structured progress report for a user (powers dashboards)."""
    return get_progress_report(str(user_id))


def ocr_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """Extract text from an image via Gemini multimodal."""
    from stodi.tools.grounding import _genai_client

    client = _genai_client()
    response = client.models.generate_content(
        model=settings.MODEL,
        contents=[
            "You are an OCR assistant for a WAEC exam-prep bot called Stodi. "
            "Extract all text from this image. If it's a math problem, preserve "
            "the mathematical notation. If it's a handwritten answer, transcribe it exactly.",
            types.Part.from_bytes(data=bytes(image_bytes), mime_type=mime_type),
        ],
    )
    return response.text or ""
