"""Curriculum Agent — owns the active Exam Pack.

Responsibilities:
  - Syllabus lookup (topic tree)
  - Past-question retrieval (RAG: Vertex AI Search when provisioned, else local)
  - Single source of truth so nothing is hallucinated
  - Grounding: every answer the system gives traces back to here

The active pack is resolved per session/student via config.pack_state — no
shared module global, so concurrent users don't clobber each other.
"""

import sys
from pathlib import Path

from google.adk import Agent
from google.adk.tools import ToolContext
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from stodi.config import settings
from stodi.config.exam_pack import ExamPack
from stodi.config import pack_state
from stodi.tools.grounding import ground_search
from stodi.tools.extended_tools import read_document, FORMULAS
from stodi.tools.content_ingestion import (
    ingest_past_questions_pdf,
    ingest_syllabus_spreadsheet,
    build_exam_pack,
)

_NO_PACK = {"error": "No exam pack loaded. Initialize with load_pack()."}


# ─── Pure helpers (usable without an agent / tool_context) ────

def questions_for_topic(pack: ExamPack, topic_id: str, limit: int = 5) -> list[dict]:
    """Return past questions for a topic from a given pack."""
    return [
        q.model_dump()
        for q in pack.past_questions.questions
        if q.topic_id == topic_id
    ][:limit]


# ─── Agent tools ─────────────────────────────────────────────

def lookup_topic(topic_name: str, tool_context: ToolContext = None) -> dict:
    """Look up a topic in the active syllabus by name (fuzzy match)."""
    pack = pack_state.resolve_pack(tool_context)
    if not pack:
        return _NO_PACK
    matches = [
        t.model_dump()
        for t in pack.syllabus.topics
        if topic_name.lower() in t.name.lower()
    ]
    return {"matches": matches, "count": len(matches)}


def get_past_questions(topic_id: str, limit: int = 5, tool_context: ToolContext = None) -> dict:
    """Retrieve past questions for a given topic (grounded)."""
    pack = pack_state.resolve_pack(tool_context)
    if not pack:
        return _NO_PACK
    questions = questions_for_topic(pack, topic_id, limit)
    return {"questions": questions, "count": len(questions)}


def search_questions(
    query: str,
    topic_id: str | None = None,
    limit: int = 5,
    tool_context: ToolContext = None,
) -> dict:
    """Semantic/keyword search across the exam pack corpus.

    Uses Vertex AI Search when a data store is configured, otherwise the
    local corpus. Returns ranked, grounded results.
    """
    pack = pack_state.resolve_pack(tool_context)
    if not pack:
        return _NO_PACK
    return ground_search(
        exam_board=pack.exam_board.lower(),
        subject=pack.subject.lower(),
        query=query,
        topic_id=topic_id,
        limit=limit,
    )


def get_marking_scheme(question_id: str, tool_context: ToolContext = None) -> dict:
    """Fetch the marking scheme for a specific past question."""
    pack = pack_state.resolve_pack(tool_context)
    if not pack:
        return _NO_PACK
    for q in pack.past_questions.questions:
        if q.id == question_id:
            return {
                "question_id": q.id,
                "year": q.year,
                "topic_id": q.topic_id,
                "marking_scheme": q.marking_scheme,
                "marks": q.marks,
            }
    return {"error": f"Question {question_id} not found."}


def get_syllabus_summary(tool_context: ToolContext = None) -> dict:
    """Return a summary of the active syllabus — topics grouped by difficulty."""
    pack = pack_state.resolve_pack(tool_context)
    if not pack:
        return _NO_PACK
    by_difficulty = {"easy": [], "medium": [], "hard": []}
    for t in pack.syllabus.topics:
        by_difficulty[t.difficulty].append({"id": t.id, "name": t.name, "weight": t.weight})
    return {
        "subject": pack.syllabus.subject,
        "exam_board": pack.syllabus.exam_board,
        "total_topics": len(pack.syllabus.topics),
        "total_questions": len(pack.past_questions.questions),
        "by_difficulty": by_difficulty,
    }


def load_pack(
    exam_board: str = "waec",
    subject: str = "mathematics",
    tool_context: ToolContext = None,
) -> dict:
    """Load an exam pack into the active session."""
    try:
        pack = pack_state.set_session_pack(tool_context, exam_board, subject)
        return {
            "status": "loaded",
            "pack": pack.name,
            "topics": len(pack.syllabus.topics),
            "questions": len(pack.past_questions.questions),
        }
    except FileNotFoundError as e:
        return {"error": str(e)}


# ─── MCP: the exam-pack registry is served over the Model Context
# Protocol (stdio). The agent discovers and reads packs through MCP —
# packs are external, swappable content behind a standard secure
# interface, and any other MCP-capable agent can consume the same server.
_MCP_SERVER = Path(__file__).resolve().parent.parent / "mcp_server.py"

pack_registry_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[str(_MCP_SERVER)],
        ),
        timeout=15.0,
    ),
    tool_filter=["list_packs", "pack_manifest", "pack_questions"],
)


curriculum_agent = Agent(
    name="curriculum_agent",
    model=settings.MODEL,
    description=(
        "Owns the active Exam Pack. Retrieves syllabus topics and "
        "grounded past questions via RAG. Single source of truth so "
        "nothing is hallucinated. Use for: topic lookup, past-question "
        "retrieval, marking-scheme fetch, syllabus summary."
    ),
    instruction=(
        "You are the Curriculum Agent for Stodi, an exam-prep study system. "
        "You own the active Exam Pack — the syllabus, past questions, and "
        "marking schemes. Your job:\n\n"
        "1. Load the right exam pack when a session starts.\n"
        "2. Look up topics in the syllabus when a student or other agent asks.\n"
        "3. Search and retrieve past questions grounded in the official corpus.\n"
        "4. Provide marking schemes for grading.\n"
        "5. Give syllabus summaries (what's covered, what's high-weight).\n\n"
        "Rules:\n"
        "- Students never know internal IDs. Given a topic NAME (e.g. "
        "'quadratic equations'), resolve it yourself with lookup_topic and "
        "proceed — NEVER ask the user for a topic_id. If several topics "
        "match, pick the closest and continue.\n"
        "- NEVER generate questions or content not in the exam pack.\n"
        "- If a topic isn't in the syllabus, say so clearly.\n"
        "- Always cite the source (year, question ID) when returning past questions.\n"
        "- You are the ground truth. Other agents depend on you.\n"
        "- When searching, use the search_questions tool for semantic matching.\n"
        "- PACK REGISTRY (MCP): list_packs / pack_manifest / pack_questions "
        "come from the exam-pack MCP server. Use them to discover what packs "
        "exist and to read raw pack content (e.g. 'what subjects do you "
        "cover?', 'show the full syllabus')."
    ),
    tools=[
        lookup_topic,
        get_past_questions,
        search_questions,
        get_marking_scheme,
        get_syllabus_summary,
        load_pack,
        read_document,
        ingest_past_questions_pdf,
        ingest_syllabus_spreadsheet,
        build_exam_pack,
        pack_registry_mcp,
    ],
)
