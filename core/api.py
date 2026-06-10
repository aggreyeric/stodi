"""FastAPI surface over the Stodi core.

This is the HTTP front door for:
  - the Quasar/Vue web + mobile client  (POST /chat, GET /progress)
  - Cloud Scheduler drip trigger          (POST /drip)
  - health checks / Cloud Run             (GET /health)

Run locally:   uvicorn stodi.core.api:app --reload --port 8080
Deploy:        Cloud Run (see DEPLOY.md)
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from stodi.config import settings, pack_state
from stodi.core import service
from stodi.tools.drip_scheduler import get_students_due_now, build_drip_quiz, format_drip_message

logger = logging.getLogger("stodi.api")

app = FastAPI(title="Stodi API", version="1.0")

# CORS so the Quasar dev server / deployed PWA can call us.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your web origin in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    pack_state.set_default_pack(settings.DEFAULT_EXAM_BOARD, settings.DEFAULT_SUBJECT)
    logger.info("Stodi API up. Config: %s", settings.summary())


# ─── Schemas ─────────────────────────────────────────────────

class ChatIn(BaseModel):
    user_id: str
    message: str


class ChatOut(BaseModel):
    reply: str


class SwitchIn(BaseModel):
    user_id: str
    exam_board: str = "waec"
    subject: str = "mathematics"


# ─── Auth ────────────────────────────────────────────────────

def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """Gate LLM-spending routes when STODI_API_KEY is configured.

    A public Cloud Run URL must not be a free credit faucet: with the key
    set, /chat, /switch, /progress and /drip all 401 without the header.
    /health stays open for Cloud Run probes and judges' first click.
    """
    if settings.API_KEY and x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key header")


# ─── Routes ──────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "stodi", "config": settings.summary()}


@app.post("/chat", response_model=ChatOut, dependencies=[Depends(require_api_key)])
async def chat(body: ChatIn) -> ChatOut:
    reply = await service.handle_message(body.user_id, body.message)
    return ChatOut(reply=reply)


@app.post("/switch", dependencies=[Depends(require_api_key)])
def switch(body: SwitchIn) -> dict:
    return service.switch_pack(body.user_id, body.exam_board, body.subject)


@app.get("/progress/{user_id}", dependencies=[Depends(require_api_key)])
def progress(user_id: str) -> dict:
    return service.get_progress(user_id)


@app.post("/drip", dependencies=[Depends(require_api_key)])
def drip() -> dict:
    """Cloud Scheduler hits this. Builds personalized drips for due students.

    Returns the computed payloads. Actual delivery is done by the channel
    adapter (the Telegram bot sends them); a web/PWA client polls /progress.
    """
    due = get_students_due_now()
    results = []
    for student in due:
        quiz = build_drip_quiz(student["student_id"])
        results.append(
            {
                "student_id": student["student_id"],
                "status": quiz["status"],
                "questions": quiz.get("count", 0),
                "message": format_drip_message(quiz) if quiz["status"] == "ready" else None,
            }
        )
    return {
        "triggered_at": datetime.now().isoformat(),
        "students_due": len(results),
        "dry_run": settings.DRIP_DRY_RUN,
        "details": results,
    }
