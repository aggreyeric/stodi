"""Offline tests for the fixed capabilities — no GCP, no network.

Run:  PYTHONPATH=<parent> pytest stodi/tests/ -q
"""

import os
import tempfile

import pytest

os.environ.setdefault("GOOGLE_API_KEY", "test")
os.environ.setdefault("STODI_STORE", "memory")

from stodi.tools.safe_math import safe_eval
from stodi.tools.agent_tools import calculate
from stodi.persistence.store import JSONFileStore, MemoryStore
from stodi.persistence import store as store_mod
from stodi.config import pack_state
from stodi.tools.drip_scheduler import get_review_interval, is_due_for_review


# ─── Safe calculator ─────────────────────────────────────────

def test_safe_eval_basic():
    assert safe_eval("5**2 + 3*7") == 46
    assert safe_eval("sqrt(144)") == 12
    assert safe_eval("log2(8) + log2(16)") == 7
    assert safe_eval("comb(5, 2)") == 10


def test_safe_eval_blocks_code_execution():
    # The old eval() would have been a vector for these.
    for bad in [
        "__import__('os').system('echo hi')",
        "(1).__class__.__mro__",
        "open('/etc/passwd')",
        "[x for x in range(3)]",
    ]:
        with pytest.raises((ValueError, SyntaxError)):
            safe_eval(bad)


def test_safe_eval_guards_blowups():
    with pytest.raises(ValueError):
        safe_eval("factorial(100000)")
    with pytest.raises(ValueError):
        safe_eval("2 ** 100000")


def test_calculate_wrapper_shapes():
    ok = calculate("2+2")
    assert ok["status"] == "success" and ok["result"] == 4
    bad = calculate("foobar(3)")
    assert bad["status"] == "error"
    div = calculate("1/0")
    assert div["status"] == "error"


# ─── Persistence survives "restart" ──────────────────────────

def test_jsonfilestore_persists_across_instances():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "profiles.json")
        s1 = JSONFileStore(path)
        s1.put("u1", {"student_id": "u1", "mastery": {"A4": {"pct": 80}}})
        # Simulate a process restart: brand new instance, same file.
        s2 = JSONFileStore(path)
        loaded = s2.get("u1")
        assert loaded is not None
        assert loaded["mastery"]["A4"]["pct"] == 80
        assert "u1" in s2.all()


def test_store_returns_copies_not_references():
    s = MemoryStore()
    s.put("u1", {"x": 1})
    got = s.get("u1")
    got["x"] = 999
    assert s.get("u1")["x"] == 1  # mutation must not leak back


# ─── Per-student pack resolution (the clobber fix) ───────────

def test_packs_are_isolated_per_student():
    # Two students on different subjects must resolve different packs.
    store = MemoryStore()
    store_mod.reset_store_for_tests(store)
    store.put("math_user", {"student_id": "math_user", "current_exam_board": "waec", "current_subject": "mathematics"})
    store.put("eng_user", {"student_id": "eng_user", "current_exam_board": "waec", "current_subject": "english"})

    pm = pack_state.resolve_pack(student_id="math_user")
    pe = pack_state.resolve_pack(student_id="eng_user")
    assert pm is not None and pe is not None
    assert "math" in pm.subject.lower()
    assert "english" in pe.subject.lower()
    assert pm.subject != pe.subject  # genuinely different packs, no clobber
    store_mod.reset_store_for_tests(None)


def test_session_state_pack_takes_precedence():
    class FakeCtx:
        state = {"active_pack": ["waec", "english"]}

    pack = pack_state.resolve_pack(tool_context=FakeCtx())
    assert pack is not None and "english" in pack.subject.lower()


# ─── Spaced-repetition intervals ─────────────────────────────

def test_review_intervals():
    assert get_review_interval(10) == 24
    assert get_review_interval(60) == 48
    assert get_review_interval(85) == 72
    assert get_review_interval(99) == 168


def test_is_due_for_review_new_topic():
    assert is_due_for_review({"pct": 0}) is True  # never reviewed → due
