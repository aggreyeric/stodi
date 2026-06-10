"""Stodi Exam-Pack MCP server.

Exposes the exam-pack registry over the Model Context Protocol (stdio), so
ANY MCP-capable agent — Stodi's own Curriculum agent via ADK's McpToolset,
Claude, Gemini CLI, or a partner's education agent — can securely discover
and read exam packs without touching Stodi internals.

This is deliberately dependency-light: it reads pack JSON straight from
exam_packs/ and imports nothing from the stodi package, so the subprocess
starts fast and can run standalone:

    python stodi/mcp_server.py            # stdio transport
"""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

PACKS_DIR = Path(__file__).resolve().parent / "exam_packs"

mcp = FastMCP("stodi-exam-packs")


def _load(exam_board: str, subject: str) -> dict | None:
    path = PACKS_DIR / exam_board.lower() / subject.lower() / "pack.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@mcp.tool()
def list_packs() -> dict:
    """List every exam pack available in the registry (board, subject, size)."""
    packs = []
    for pack_file in sorted(PACKS_DIR.glob("*/*/pack.json")):
        try:
            data = json.loads(pack_file.read_text(encoding="utf-8"))
            packs.append({
                "exam_board": data.get("exam_board"),
                "subject": data.get("subject"),
                "name": data.get("name"),
                "version": data.get("version"),
                "topics": len(data.get("syllabus", {}).get("topics", [])),
                "questions": len(data.get("past_questions", {}).get("questions", [])),
            })
        except (json.JSONDecodeError, OSError):
            continue
    return {"packs": packs, "count": len(packs)}


@mcp.tool()
def pack_manifest(exam_board: str, subject: str) -> dict:
    """Get one pack's manifest: full topic tree with ids, difficulty, weights."""
    data = _load(exam_board, subject)
    if data is None:
        return {"error": f"No pack for {exam_board}/{subject}. Use list_packs."}
    syl = data.get("syllabus", {})
    return {
        "name": data.get("name"),
        "version": data.get("version"),
        "total_marks": syl.get("total_marks"),
        "topics": syl.get("topics", []),
        "retention_cadence": data.get("retention", {}),
    }


@mcp.tool()
def pack_questions(exam_board: str, subject: str, topic_id: str = "", limit: int = 5) -> dict:
    """Fetch grounded questions (with answers + marking schemes) from a pack,
    optionally filtered by syllabus topic_id."""
    data = _load(exam_board, subject)
    if data is None:
        return {"error": f"No pack for {exam_board}/{subject}. Use list_packs."}
    questions = data.get("past_questions", {}).get("questions", [])
    if topic_id:
        questions = [q for q in questions if q.get("topic_id") == topic_id]
    return {"count": min(limit, len(questions)), "questions": questions[:limit]}


if __name__ == "__main__":
    mcp.run()
