"""Exam Pack — swappable configuration bundle for any exam.

Each exam (WAEC, JAMB, etc.) is a drop-in pack containing:
  - Syllabus / topic tree
  - Past-questions corpus (grounding source)
  - Marking scheme + grading rubric
  - Question-style templates (MCQ, theory, essay, oral)
  - Retention cadence (drill frequency per topic)
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


# ─── Topic tree ───────────────────────────────────────────────

class Topic(BaseModel):
    """A single topic in the syllabus tree."""
    id: str
    name: str
    parent_id: str | None = None
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    weight: float = Field(
        1.0,
        description="Relative weight in the exam (e.g. marks allocation).",
    )


class Syllabus(BaseModel):
    """Full syllabus for one subject."""
    subject: str
    exam_board: str  # e.g. "WAEC", "JAMB"
    topics: list[Topic]
    total_marks: int = 100


# ─── Past questions ───────────────────────────────────────────

class PastQuestion(BaseModel):
    """A single past-question entry."""
    id: str
    year: int
    subject: str
    topic_id: str
    question_type: Literal["mcq", "theory", "essay", "oral"]
    question_text: str
    options: list[str] | None = None  # for MCQ
    correct_answer: str | None = None
    marking_scheme: str | None = None  # for theory/essay
    marks: int = 1


class PastQuestionCorpus(BaseModel):
    """Collection of past questions for grounding."""
    subject: str
    exam_board: str
    questions: list[PastQuestion]


# ─── Retention config ────────────────────────────────────────

class RetentionCadence(BaseModel):
    """Spaced-repetition scheduling per topic difficulty."""
    easy_interval_hours: int = 72     # 3 days
    medium_interval_hours: int = 48   # 2 days
    hard_interval_hours: int = 24     # 1 day
    max_questions_per_drip: int = 5
    drip_time: str = "08:00"          # when to send daily drip (local time)


# ─── The full Exam Pack ──────────────────────────────────────

class ExamPack(BaseModel):
    """
    Swappable config bundle — the 'and more' layer.

    Drop in a new pack (JAMB, language cert, etc.) without
    touching the agent code.
    """
    name: str                          # e.g. "WAEC Mathematics"
    exam_board: str                    # e.g. "WAEC"
    subject: str                       # e.g. "Mathematics"
    version: str = "1.0"
    syllabus: Syllabus
    past_questions: PastQuestionCorpus
    retention: RetentionCadence = Field(default_factory=RetentionCadence)

    # paths (resolved at load time)
    data_dir: Path | None = None

    class Config:
        arbitrary_types_allowed = True


# ─── Loader ───────────────────────────────────────────────────

PACKS_DIR = Path(__file__).resolve().parent.parent / "exam_packs"


def load_exam_pack(exam_board: str, subject: str) -> ExamPack:
    """Load an exam pack from the exam_packs/ directory.

    Expected structure:
        exam_packs/
          waec/
            mathematics/
              pack.json        ← ExamPack JSON
              past_questions/  ← PDFs, text files
            english/
              pack.json
    """
    pack_path = PACKS_DIR / exam_board.lower() / subject.lower() / "pack.json"
    if not pack_path.exists():
        raise FileNotFoundError(f"Exam pack not found: {pack_path}")

    import json
    with open(pack_path) as f:
        data = json.load(f)

    pack = ExamPack(**data)
    pack.data_dir = pack_path.parent
    return pack
