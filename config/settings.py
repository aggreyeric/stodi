"""Central configuration — single source of truth for env-driven settings.

Everything that used to be hardcoded (project IDs, locations, flags) now
lives here and is read from the environment. Import `settings` and use it;
never hardcode a project ID in a handler again.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


# ─── Google Cloud / Gemini ───────────────────────────────────
GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")
GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "stodi-498317")
GOOGLE_CLOUD_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
USE_VERTEXAI: bool = _flag("GOOGLE_GENAI_USE_VERTEXAI", True)
MODEL: str = os.getenv("STODI_MODEL", "gemini-2.5-flash")

# ─── Vertex AI Search (RAG grounding) ────────────────────────
# Only active once a data store is provisioned and this is set.
# Format: projects/<p>/locations/<l>/collections/default_collection/dataStores/<id>
VERTEX_SEARCH_DATASTORE: str | None = os.getenv("VERTEX_SEARCH_DATASTORE") or None

# ─── Channels ────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")

# ─── API security ────────────────────────────────────────────
# When set, every state-changing/LLM route on the HTTP API requires the
# X-API-Key header — so a public Cloud Run URL can't be used to burn
# model credits. Unset = open (local dev). The Telegram bot is unaffected:
# it long-polls Telegram with the bot token and never exposes an endpoint.
API_KEY: str | None = os.getenv("STODI_API_KEY") or None

# ─── Persistence ─────────────────────────────────────────────
# json (default, file-backed, survives restart) | firestore | memory
STORE_BACKEND: str = os.getenv("STODI_STORE", "json").strip().lower()
_PKG_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR: Path = Path(os.getenv("STODI_DATA_DIR", str(_PKG_ROOT / "data")))
FIRESTORE_COLLECTION: str = os.getenv("STODI_FIRESTORE_COLLECTION", "stodi_students")

# ─── Drip scheduler ──────────────────────────────────────────
DRIP_DRY_RUN: bool = _flag("STODI_DRIP_DRY_RUN", True)
DRIP_INTERVAL_MINUTES: int = int(os.getenv("STODI_DRIP_INTERVAL_MINUTES", "60"))
DRIP_TIMEZONE: str = os.getenv("STODI_DRIP_TZ", "Africa/Lagos")

# ─── Defaults ────────────────────────────────────────────────
DEFAULT_EXAM_BOARD: str = os.getenv("STODI_DEFAULT_BOARD", "waec")
DEFAULT_SUBJECT: str = os.getenv("STODI_DEFAULT_SUBJECT", "mathematics")


def summary() -> dict:
    """Non-secret view of the active config — safe to log on boot."""
    return {
        "project": GOOGLE_CLOUD_PROJECT,
        "location": GOOGLE_CLOUD_LOCATION,
        "use_vertexai": USE_VERTEXAI,
        "model": MODEL,
        "vertex_search": bool(VERTEX_SEARCH_DATASTORE),
        "store": STORE_BACKEND,
        "data_dir": str(DATA_DIR),
        "drip_dry_run": DRIP_DRY_RUN,
        "telegram_configured": bool(TELEGRAM_BOT_TOKEN),
    }
