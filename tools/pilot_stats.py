"""Pilot traction report — turns the profile store into panel-ready numbers.

Reads every student profile and prints the metrics that evidence the
business case: cohort size, activity, quiz volume, accuracy, mastery
movement, weak-topic distribution.

Run against the live store:
    PYTHONPATH=.. venv/bin/python -m stodi.tools.pilot_stats
    PYTHONPATH=.. venv/bin/python -m stodi.tools.pilot_stats --json
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timedelta


def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def collect_stats() -> dict:
    from stodi.persistence import get_store

    profiles = get_store().all()
    now = datetime.now()

    students = len(profiles)
    active_24h = active_7d = 0
    total_quizzes = total_correct = 0
    mastery_values: list[int] = []
    improved = 0          # students whose latest topic score beats their first
    weak_counter: Counter[str] = Counter()
    per_student = []

    for sid, p in profiles.items():
        last = _parse(p.get("last_active"))
        if last and now - last <= timedelta(hours=24):
            active_24h += 1
        if last and now - last <= timedelta(days=7):
            active_7d += 1

        total_quizzes += p.get("total_quizzes", 0)
        total_correct += p.get("total_correct", 0)

        mastery = p.get("mastery", {})
        topic_pcts = [m.get("pct", 0) for m in mastery.values()]
        mastery_values.extend(topic_pcts)

        deltas = [
            m["history"][-1] - m["history"][0]
            for m in mastery.values()
            if len(m.get("history", [])) >= 2
        ]
        if deltas and sum(deltas) / len(deltas) > 0:
            improved += 1

        weak_counter.update(p.get("weak_topics", []))

        per_student.append({
            "student_id": sid,
            "topics": len(mastery),
            "quizzes": p.get("total_quizzes", 0),
            "avg_mastery": round(sum(topic_pcts) / len(topic_pcts)) if topic_pcts else 0,
            "weak_topics": len(p.get("weak_topics", [])),
            "last_active": p.get("last_active", "—"),
        })

    return {
        "generated_at": now.isoformat(),
        "students": students,
        "active_24h": active_24h,
        "active_7d": active_7d,
        "total_quizzes": total_quizzes,
        "quiz_accuracy_pct": round(total_correct / total_quizzes * 100) if total_quizzes else 0,
        "avg_topic_mastery_pct": round(sum(mastery_values) / len(mastery_values)) if mastery_values else 0,
        "students_improving_pct": round(improved / students * 100) if students else 0,
        "top_weak_topics": weak_counter.most_common(5),
        "per_student": sorted(per_student, key=lambda s: -s["quizzes"]),
    }


def main() -> int:
    stats = collect_stats()

    if "--json" in sys.argv:
        print(json.dumps(stats, indent=2))
        return 0

    print("Stodi — Pilot Traction Report")
    print("=" * 46)
    print(f"Students enrolled        {stats['students']}")
    print(f"Active last 24h          {stats['active_24h']}")
    print(f"Active last 7 days       {stats['active_7d']}")
    print(f"Quizzes answered         {stats['total_quizzes']}")
    print(f"Quiz accuracy            {stats['quiz_accuracy_pct']}%")
    print(f"Avg topic mastery        {stats['avg_topic_mastery_pct']}%")
    print(f"Students improving       {stats['students_improving_pct']}%")
    if stats["top_weak_topics"]:
        weak = ", ".join(f"{t} ({n})" for t, n in stats["top_weak_topics"])
        print(f"Most-failed topics       {weak}")
    print("-" * 46)
    for s in stats["per_student"][:20]:
        print(
            f"  {s['student_id']:<16} topics={s['topics']:<3} quizzes={s['quizzes']:<4} "
            f"mastery={s['avg_mastery']:>3}%  weak={s['weak_topics']}"
        )
    if stats["students"] == 0:
        print("  (no students yet — share the bot link and re-run)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
