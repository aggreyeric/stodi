"""Stodi Extended Tools — making the agents genuinely useful.

Inspired by QwenPaw tool patterns but built for Stodi's exam-prep domain:
  - LaTeX rendering for math (Telegram-native)
  - PDF/image reading (syllabus ingestion)
  - Study sheet generation
  - Progress report export
"""

import os
import re
import math
import json
from pathlib import Path
from datetime import datetime


# ═══════════════════════════════════════════════════════════════
# 1. LATEX / MATH RENDERING
#    Telegram supports LaTeX-style display with code blocks.
#    For actual image rendering, we generate PNG via matplotlib.
# ═══════════════════════════════════════════════════════════════

def render_math(expression: str, display_mode: bool = True) -> dict:
    """Render a math expression as a PNG image for Telegram.

    Uses matplotlib's LaTeX renderer to create clean math images.
    Falls back to formatted text if rendering fails.

    Args:
        expression: LaTeX expression like "x^2 + 3x - 4 = 0"
                    or "frac{a}{b}" or "sqrt{x^2 + y^2}"
        display_mode: True for display (centered), False for inline
    """
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        # Wrap in display math if not already
        if display_mode and not expression.startswith('$$'):
            latex = f'$${expression}$$'
        elif not display_mode and not expression.startswith('$'):
            latex = f'${expression}$'
        else:
            latex = expression

        fig, ax = plt.subplots(figsize=(4, 1.2))
        ax.text(0.5, 0.5, latex, fontsize=20, ha='center', va='center',
                transform=ax.transAxes)
        ax.axis('off')
        fig.patch.set_alpha(0)

        # Save to temp file
        out_path = f"/tmp/stodi_math_{datetime.now().strftime('%H%M%S')}.png"
        fig.savefig(out_path, dpi=150, bbox_inches='tight', pad_inches=0.1,
                    transparent=True)
        plt.close(fig)

        return {
            "status": "rendered",
            "image_path": out_path,
            "latex": expression,
        }
    except ImportError:
        return {
            "status": "text_fallback",
            "text": f"```{expression}```",
            "note": "matplotlib not installed, using code block",
        }
    except Exception as e:
        return {
            "status": "text_fallback",
            "text": f"```{expression}```",
            "note": f"Render error: {e}",
        }


def format_math_for_telegram(expression: str) -> dict:
    """Format math expression for Telegram's monospace display.

    Converts LaTeX to Unicode math symbols that display cleanly
    on Telegram without needing images.

    Args:
        expression: Math expression in LaTeX or plain text
    """
    replacements = {
        r'\\frac\{([^}]+)\}\{([^}]+)\}': r'(\1)/(\2)',
        r'\\sqrt\{([^}]+)\}': r'√(\1)',
        r'\\cdot': '·',
        r'\\times': '×',
        r'\\div': '÷',
        r'\\pm': '±',
        r'\\neq': '≠',
        r'\\leq': '≤',
        r'\\geq': '≥',
        r'\\approx': '≈',
        r'\\infty': '∞',
        r'\\theta': 'θ',
        r'\\alpha': 'α',
        r'\\beta': 'β',
        r'\\gamma': 'γ',
        r'\\pi': 'π',
        r'\\sigma': 'σ',
        r'\\Delta': 'Δ',
        r'\\sum': 'Σ',
        r'\\prod': '∏',
        r'\\int': '∫',
        r'\\log': 'log',
        r'\\ln': 'ln',
        r'\\sin': 'sin',
        r'\\cos': 'cos',
        r'\\tan': 'tan',
        r'\\angle': '∠',
        r'\\degree': '°',
        r'\\rightarrow': '→',
        r'\\leftarrow': '←',
    }

    result = expression
    for pattern, replacement in replacements.items():
        result = re.sub(pattern, replacement, result)

    # Clean up remaining LaTeX braces
    result = result.replace('{', '').replace('}', '')

    return {"formatted": result, "original": expression}


# ═══════════════════════════════════════════════════════════════
# 2. SYLLABUS / PDF READER
#    Read uploaded syllabus files and extract topics
# ═══════════════════════════════════════════════════════════════

def read_document(file_path: str) -> dict:
    """Read a document (PDF, TXT, MD) and extract text content.

    Used when students upload syllabus PDFs or notes.

    Args:
        file_path: Path to the document file
    """
    path = Path(file_path).expanduser()
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    suffix = path.suffix.lower()

    try:
        if suffix in ('.txt', '.md', '.csv'):
            text = path.read_text(encoding='utf-8', errors='replace')
        elif suffix == '.pdf':
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(str(path))
                text = "\n".join(page.get_text() for page in doc)
                doc.close()
            except ImportError:
                # Fallback: read raw bytes (limited)
                text = path.read_text(encoding='utf-8', errors='replace')
        elif suffix in ('.docx', '.doc'):
            try:
                from docx import Document
                doc = Document(str(path))
                text = "\n".join(p.text for p in doc.paragraphs)
            except ImportError:
                return {"error": "python-docx not installed. pip install python-docx"}
        else:
            return {"error": f"Unsupported file type: {suffix}"}

        # Truncate for safety
        max_chars = 50000
        truncated = len(text) > max_chars
        if truncated:
            text = text[:max_chars]

        return {
            "file": str(path),
            "type": suffix,
            "chars": len(text),
            "truncated": truncated,
            "content": text,
        }
    except Exception as e:
        return {"error": f"Failed to read: {e}"}


# ═══════════════════════════════════════════════════════════════
# 3. STUDY SHEET GENERATOR
#    Generate structured study materials from exam pack data
# ═══════════════════════════════════════════════════════════════

def generate_study_sheet(
    student_id: str,
    topic_ids: list[str] | None = None,
    output_format: str = "text",
) -> dict:
    """Generate a personalized study sheet for a student.

    Includes: weak topics, key formulas, past questions to practice.

    Args:
        student_id: The student's ID
        topic_ids: Specific topics to include (None = all weak topics)
        output_format: "text" for messaging, "json" for structured data
    """
    from stodi.tools.agent_tools import get_student_profile, get_next_review
    from stodi.config import pack_state

    profile = get_student_profile(student_id)
    pack = pack_state.resolve_pack(student_id=student_id)

    if topic_ids is None:
        review = get_next_review(student_id, limit=5)
        topic_ids = [t["id"] for t in review.get("review_topics", [])]

    if not pack:
        return {"error": "No exam pack loaded"}

    topic_map = {t.id: t for t in pack.syllabus.topics}
    questions = pack.past_questions.questions

    lines = [f"📚 Study Sheet — {pack.name}", "═" * 35, ""]

    for tid in topic_ids:
        if tid in topic_map:
            topic = topic_map[tid]
            mastery = profile["mastery"].get(tid, {})
            pct = mastery.get("pct", 0)

            lines.append(f"▸ {topic.name} (mastery: {pct}%)")
            lines.append(f"  Difficulty: {topic.difficulty} | Weight: {topic.weight}")

            # Find related past questions
            related = [q for q in questions if q.topic_id == tid][:2]
            if related:
                lines.append("  Practice questions:")
                for q in related:
                    lines.append(f"    • [{q.year}] {q.question_text[:80]}...")
            lines.append("")

    # Footer with stats
    progress = profile
    lines.append("─" * 35)
    lines.append(f"Topics studied: {len(progress['mastery'])}")
    lines.append(f"Total quizzes: {progress['total_quizzes']}")
    lines.append(f"Weak topics: {len(progress['weak_topics'])}")
    lines.append(f"Strong topics: {len(progress['strong_topics'])}")

    result = "\n".join(lines)

    if output_format == "json":
        return {"format": "json", "data": lines}
    return {"format": "text", "content": result}


# ═══════════════════════════════════════════════════════════════
# 4. FORMULA REFERENCE
#    Quick formula lookup by topic — the cheat sheet agent
# ═══════════════════════════════════════════════════════════════

FORMULAS = {
    "A4": {  # Logarithms
        "name": "Logarithms",
        "formulas": [
            "log_a(x) = y  ⟺  a^y = x",
            "log_a(xy) = log_a(x) + log_a(y)",
            "log_a(x/y) = log_a(x) − log_a(y)",
            "log_a(xⁿ) = n·log_a(x)",
            "log_a(x) = log_b(x) / log_b(a)   [change of base]",
        ],
    },
    "A5": {  # Sequence and Series
        "name": "Sequences & Series",
        "formulas": [
            "AP: T_n = a + (n−1)d,  S_n = n/2 · [2a + (n−1)d]",
            "GP: T_n = ar^(n−1),  S_n = a(r^n − 1)/(r − 1)",
            "S∞ = a/(1−r)  when |r| < 1",
        ],
    },
    "B3": {  # Quadratic Equations
        "name": "Quadratic Equations",
        "formulas": [
            "ax² + bx + c = 0",
            "x = (−b ± √(b²−4ac)) / 2a",
            "Sum of roots = −b/a",
            "Product of roots = c/a",
            "Discriminant Δ = b²−4ac: >0 two real, =0 repeated, <0 complex",
        ],
    },
    "C5": {  # Trigonometry
        "name": "Trigonometry",
        "formulas": [
            "sin θ = opp/hyp,  cos θ = adj/hyp,  tan θ = opp/adj",
            "sin²θ + cos²θ = 1",
            "Area = ½ab sin C",
            "a/sin A = b/sin B = c/sin C  (sine rule)",
            "a² = b² + c² − 2bc cos A  (cosine rule)",
        ],
    },
    "C6": {  # Mensuration
        "name": "Mensuration",
        "formulas": [
            "Circle: A = πr², C = 2πr",
            "Sphere: V = 4/3·πr³, A = 4πr²",
            "Cone: V = 1/3·πr²h, curved A = πrl",
            "Cylinder: V = πr²h, curved A = 2πrh",
            "Trapezium: A = ½(a+b)h",
        ],
    },
    "C7": {  # Coordinate Geometry
        "name": "Coordinate Geometry",
        "formulas": [
            "Midpoint = ((x₁+x₂)/2, (y₁+y₂)/2)",
            "Distance = √((x₂−x₁)² + (y₂−y₁)²)",
            "Gradient m = (y₂−y₁)/(x₂−x₁)",
            "y − y₁ = m(x − x₁)  (point-slope form)",
        ],
    },
    "D1": {  # Statistics
        "name": "Statistics",
        "formulas": [
            "Mean x̄ = Σx / n",
            "Median = middle value (sorted)",
            "Mode = most frequent value",
            "Range = max − min",
            "Variance σ² = Σ(x−x̄)² / n",
            "Standard deviation σ = √(variance)",
        ],
    },
    "D2": {  # Probability
        "name": "Probability",
        "formulas": [
            "P(A) = n(A) / n(S)",
            "P(A∪B) = P(A) + P(B) − P(A∩B)",
            "P(A∩B) = P(A) × P(B)  [independent]",
            "P(A|B) = P(A∩B) / P(B)",
            "nCr = n! / (r!(n−r)!)",
        ],
    },
    "E2": {  # Matrices
        "name": "Matrices",
        "formulas": [
            "Determinant 2×2: |A| = ad − bc  for [[a,b],[c,d]]",
            "Inverse: A⁻¹ = 1/|A| × [[d,−b],[−c,a]]",
            "Matrix mult: (AB)ᵢⱼ = Σ aᵢₖ · bₖⱼ",
        ],
    },
}


def get_formulas(topic_id: str) -> dict:
    """Get key formulas for a topic — the quick reference card.

    Args:
        topic_id: The topic ID from the syllabus (e.g. "C5" for Trigonometry)
    """
    if topic_id in FORMULAS:
        data = FORMULAS[topic_id]
        return {
            "topic_id": topic_id,
            "topic_name": data["name"],
            "formulas": data["formulas"],
            "count": len(data["formulas"]),
        }

    # Fallback: search by partial match
    for tid, data in FORMULAS.items():
        if topic_id.lower() in data["name"].lower():
            return {
                "topic_id": tid,
                "topic_name": data["name"],
                "formulas": data["formulas"],
                "count": len(data["formulas"]),
            }

    return {"error": f"No formulas found for topic {topic_id}"}
