"""Grounding service — local corpus now, Vertex AI Search when provisioned.

Two layers:
  1. Local corpus search over the Exam Pack JSON  — always available, returns
     structured past-question objects. This is the reliable default.
  2. Vertex AI Search over the indexed corpus (RAG) — activated automatically
     once settings.VERTEX_SEARCH_DATASTORE is set. Adds a grounded natural-
     language answer alongside the structured results.

`ground_search()` is the single entry point the Curriculum Agent calls.
"""

from __future__ import annotations

import logging

from google import genai
from google.genai import types

from stodi.config import settings
from stodi.config.exam_pack import load_exam_pack

logger = logging.getLogger("stodi.grounding")


# ─── Local corpus search (default) ───────────────────────────

def search_local_corpus(
    exam_board: str,
    subject: str,
    query: str,
    topic_id: str | None = None,
    limit: int = 5,
) -> dict:
    """Keyword-rank past questions in the local exam pack JSON."""
    try:
        pack = load_exam_pack(exam_board, subject)
    except FileNotFoundError:
        return {"error": f"No pack found for {exam_board}/{subject}"}

    candidates = pack.past_questions.questions
    if topic_id:
        candidates = [q for q in candidates if q.topic_id == topic_id]

    query_lower = query.lower()
    words = query_lower.split()
    scored = []
    for q in candidates:
        score = 0
        qtext = q.question_text.lower()
        if query_lower in qtext:
            score += 10
        for word in words:
            if word in qtext:
                score += 1
            if q.marking_scheme and word in q.marking_scheme.lower():
                score += 1
        scored.append((score, q))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [q for _, q in scored[:limit]]

    return {
        "source": "local_corpus",
        "exam_board": exam_board,
        "subject": subject,
        "query": query,
        "results": [
            {
                "id": q.id,
                "year": q.year,
                "topic_id": q.topic_id,
                "type": q.question_type,
                "question": q.question_text,
                "options": q.options,
                "marking_scheme": q.marking_scheme,
                "marks": q.marks,
            }
            for q in results
        ],
        "count": len(results),
    }


# ─── Vertex AI Search grounding (when configured) ────────────

def _genai_client() -> genai.Client:
    if settings.USE_VERTEXAI:
        return genai.Client(
            vertexai=True,
            project=settings.GOOGLE_CLOUD_PROJECT,
            location=settings.GOOGLE_CLOUD_LOCATION,
        )
    return genai.Client(api_key=settings.GOOGLE_API_KEY)


def vertex_search(query: str) -> dict | None:
    """Query the Vertex AI Search data store for a grounded answer.

    Returns None if no data store is configured. Returns an error dict on
    failure so the caller can fall back to local results.
    """
    if not settings.VERTEX_SEARCH_DATASTORE:
        return None
    try:
        client = _genai_client()
        response = client.models.generate_content(
            model=settings.MODEL,
            contents=query,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        retrieval=types.Retrieval(
                            vertex_ai_search=types.VertexAISearch(
                                datastore=settings.VERTEX_SEARCH_DATASTORE,
                            )
                        )
                    )
                ],
            ),
        )
        return {"grounded_answer": response.text, "source": "vertex_ai_search"}
    except Exception as e:  # noqa: BLE001 — degrade gracefully
        logger.warning("Vertex AI Search failed, using local corpus: %s", e)
        return {"error": str(e), "source": "vertex_ai_search_error"}


# ─── Unified entry point ─────────────────────────────────────

def ground_search(
    exam_board: str,
    subject: str,
    query: str,
    topic_id: str | None = None,
    limit: int = 5,
) -> dict:
    """Return structured local results, enriched with a Vertex grounded
    answer when a data store is configured."""
    result = search_local_corpus(exam_board, subject, query, topic_id, limit)
    vx = vertex_search(query)
    if vx and "grounded_answer" in vx:
        result["grounded_answer"] = vx["grounded_answer"]
        result["grounding"] = "vertex_ai_search"
    return result


# ─── Google Search grounding (general knowledge) ─────────────

def search_with_google_grounding(query: str) -> dict:
    """Gemini with built-in Google Search grounding (general queries)."""
    client = _genai_client()
    response = client.models.generate_content(
        model=settings.MODEL,
        contents=query,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )
    grounding_chunks = []
    try:
        for candidate in response.candidates:
            gm = getattr(candidate, "grounding_metadata", None)
            for chunk in getattr(gm, "grounding_chunks", []) or []:
                web = getattr(chunk, "web", None)
                grounding_chunks.append(
                    {"web": getattr(web, "uri", None), "title": getattr(web, "title", None)}
                )
    except Exception:  # noqa: BLE001
        pass
    return {
        "source": "google_search_grounding",
        "query": query,
        "answer": response.text,
        "grounding_chunks": grounding_chunks,
        "grounded": True,
    }
