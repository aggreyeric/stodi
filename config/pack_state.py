"""Active-pack resolution — per session / per student, not one global.

Before this, a single module global `CURRENT_PACK` was shared across every
user: if user A switched to English while user B was on Maths, B's next
turn silently used English. Now:

  - Packs are loaded once and cached by (board, subject).
  - The active pack is resolved per call, with this precedence:
        1. ADK session state  (tool_context.state["active_pack"])  ← agent path
        2. the student's stored profile choice                     ← drip / batch path
        3. a process default                                       ← fallback
"""

from __future__ import annotations

import logging

from stodi.config.exam_pack import ExamPack, load_exam_pack

logger = logging.getLogger("stodi.pack")

_CACHE: dict[tuple[str, str], ExamPack] = {}
_default_key: tuple[str, str] | None = None


def _key(board: str, subject: str) -> tuple[str, str]:
    return (board.lower(), subject.lower())


def load_cached(board: str, subject: str) -> ExamPack:
    """Load a pack, caching by (board, subject)."""
    k = _key(board, subject)
    if k not in _CACHE:
        _CACHE[k] = load_exam_pack(board, subject)
    return _CACHE[k]


def set_default_pack(board: str, subject: str) -> ExamPack:
    """Set the process-wide fallback pack (used when no session/student context)."""
    global _default_key
    pack = load_cached(board, subject)
    _default_key = _key(board, subject)
    return pack


def pack_for_student(student_id: str) -> ExamPack | None:
    """Resolve the pack from the student's stored subject/board choice."""
    from stodi.persistence import get_store

    profile = get_store().get(student_id)
    if not profile:
        return None
    board = profile.get("current_exam_board")
    subject = profile.get("current_subject")
    if not board or not subject:
        return None
    try:
        return load_cached(board, subject)
    except FileNotFoundError:
        return None


def _state_key(tool_context) -> tuple[str, str] | None:
    if tool_context is None:
        return None
    state = getattr(tool_context, "state", None)
    if not state:
        return None
    val = state.get("active_pack")
    if isinstance(val, (list, tuple)) and len(val) == 2:
        return (str(val[0]).lower(), str(val[1]).lower())
    return None


def resolve_pack(tool_context=None, student_id: str | None = None) -> ExamPack | None:
    """Return the active pack for this context, applying precedence order."""
    # 1. explicit session state (agent path)
    k = _state_key(tool_context)
    if k:
        try:
            return load_cached(*k)
        except FileNotFoundError:
            pass
    # 2. the student's stored choice (batch / drip path)
    if student_id:
        p = pack_for_student(student_id)
        if p:
            return p
    # 3. process default
    if _default_key:
        return _CACHE.get(_default_key)
    return None


def set_session_pack(tool_context, board: str, subject: str) -> ExamPack:
    """Record the active pack into ADK session state (per-session isolation)."""
    pack = load_cached(board, subject)
    state = getattr(tool_context, "state", None) if tool_context is not None else None
    if state is not None:
        state["active_pack"] = [board.lower(), subject.lower()]
    else:
        set_default_pack(board, subject)
    return pack
