"""Profile store backends.

The store maps student_id -> profile dict. Profiles are the per-student
mastery/history that makes Stodi's "we remember you" promise real. Before
this, profiles lived in a module-global dict and died on every restart.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from pathlib import Path
from typing import Protocol

from stodi.config import settings

logger = logging.getLogger("stodi.persistence")


class ProfileStore(Protocol):
    """Storage contract for student profiles."""

    def get(self, student_id: str) -> dict | None: ...
    def put(self, student_id: str, profile: dict) -> None: ...
    def all(self) -> dict[str, dict]: ...


# ─── In-memory (tests / ephemeral) ───────────────────────────

class MemoryStore:
    """In-process store. Fast, but lost on restart. Use for tests."""

    def __init__(self) -> None:
        self._data: dict[str, dict] = {}
        self._lock = threading.Lock()

    def get(self, student_id: str) -> dict | None:
        with self._lock:
            p = self._data.get(student_id)
            return json.loads(json.dumps(p)) if p is not None else None

    def put(self, student_id: str, profile: dict) -> None:
        with self._lock:
            self._data[student_id] = json.loads(json.dumps(profile))

    def all(self) -> dict[str, dict]:
        with self._lock:
            return json.loads(json.dumps(self._data))


# ─── JSON file (default local backend) ───────────────────────

class JSONFileStore:
    """File-backed store. Survives restarts, no external deps.

    Loads the whole file into memory and flushes atomically on write.
    Fine for the demo and small cohorts; swap to Firestore for scale.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._data: dict[str, dict] = self._load()

    def _load(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not read profile store %s: %s", self.path, e)
            return {}

    def _flush(self) -> None:
        # Atomic write: tmp file in same dir, then replace.
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise

    def get(self, student_id: str) -> dict | None:
        with self._lock:
            p = self._data.get(student_id)
            return json.loads(json.dumps(p)) if p is not None else None

    def put(self, student_id: str, profile: dict) -> None:
        with self._lock:
            self._data[student_id] = json.loads(json.dumps(profile))
            self._flush()

    def all(self) -> dict[str, dict]:
        with self._lock:
            return json.loads(json.dumps(self._data))


# ─── Firestore (production backend) ──────────────────────────

class FirestoreStore:
    """Google Cloud Firestore backend. Lazy-imports the client.

    Each student is a document in settings.FIRESTORE_COLLECTION.
    """

    def __init__(self, collection: str | None = None, project: str | None = None) -> None:
        from google.cloud import firestore  # lazy: only needed in prod

        self._client = firestore.Client(project=project or settings.GOOGLE_CLOUD_PROJECT)
        self._col = self._client.collection(collection or settings.FIRESTORE_COLLECTION)

    def get(self, student_id: str) -> dict | None:
        doc = self._col.document(student_id).get()
        return doc.to_dict() if doc.exists else None

    def put(self, student_id: str, profile: dict) -> None:
        self._col.document(student_id).set(profile)

    def all(self) -> dict[str, dict]:
        return {doc.id: doc.to_dict() for doc in self._col.stream()}


# ─── Factory ─────────────────────────────────────────────────

_store: ProfileStore | None = None


def get_store() -> ProfileStore:
    """Return the singleton store chosen by settings.STORE_BACKEND."""
    global _store
    if _store is not None:
        return _store

    backend = settings.STORE_BACKEND
    if backend == "memory":
        _store = MemoryStore()
    elif backend == "firestore":
        try:
            _store = FirestoreStore()
            logger.info("Using Firestore profile store (collection=%s)", settings.FIRESTORE_COLLECTION)
        except Exception as e:
            logger.warning("Firestore unavailable (%s); falling back to JSON file store", e)
            _store = JSONFileStore(settings.DATA_DIR / "profiles.json")
    else:  # "json" (default)
        _store = JSONFileStore(settings.DATA_DIR / "profiles.json")
        logger.info("Using JSON file profile store at %s", settings.DATA_DIR / "profiles.json")

    return _store


def reset_store_for_tests(store: ProfileStore | None = None) -> None:
    """Swap the singleton (tests only)."""
    global _store
    _store = store
