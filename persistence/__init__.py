"""Persistence layer — student profiles survive restarts.

Pluggable backends:
  - JSONFileStore  (default): file-backed, works locally, survives restart
  - FirestoreStore (prod):    Google Cloud Firestore
  - MemoryStore    (tests):   in-process only

Use `get_store()` — it picks the backend from settings.STORE_BACKEND.
"""

from stodi.persistence.store import (
    ProfileStore,
    JSONFileStore,
    MemoryStore,
    get_store,
)

__all__ = ["ProfileStore", "JSONFileStore", "MemoryStore", "get_store"]
