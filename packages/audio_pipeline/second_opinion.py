from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from music_engine.engine import NoteEvent


@dataclass(frozen=True)
class ModelAgreement:
    primary_notes: int
    secondary_notes: int
    matched_notes: int
    primary_support_ratio: float
    secondary_support_ratio: float
    agreement_f1: float
    disagreements: tuple[dict, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def compare_transcriptions(
    primary: Iterable[NoteEvent],
    secondary: Iterable[NoteEvent],
    onset_tolerance: float = 0.08,
    max_disagreements: int = 120,
) -> ModelAgreement:
    a = list(primary)
    b = list(secondary)
    used_b: set[int] = set()
    matches = 0
    disagreements: list[dict] = []

    for i, note in enumerate(a):
        best_j = None
        best_distance = float("inf")
        for j, other in enumerate(b):
            if j in used_b or other.pitch != note.pitch:
                continue
            distance = abs(other.start - note.start)
            if distance <= onset_tolerance and distance < best_distance:
                best_distance = distance
                best_j = j

        if best_j is not None:
            used_b.add(best_j)
            matches += 1
        elif len(disagreements) < max_disagreements:
            disagreements.append(
                {
                    "side": "primary_only",
                    "pitch": note.pitch,
                    "start": round(note.start, 4),
                    "duration": round(note.duration, 4),
                    "confidence": round(note.confidence, 4),
                }
            )

    for j, note in enumerate(b):
        if j not in used_b and len(disagreements) < max_disagreements:
            disagreements.append(
                {
                    "side": "secondary_only",
                    "pitch": note.pitch,
                    "start": round(note.start, 4),
                    "duration": round(note.duration, 4),
                    "confidence": round(note.confidence, 4),
                }
            )

    support_a = matches / len(a) if a else (1.0 if not b else 0.0)
    support_b = matches / len(b) if b else (1.0 if not a else 0.0)
    f1 = (
        2 * support_a * support_b / (support_a + support_b)
        if support_a + support_b > 0
        else 0.0
    )

    return ModelAgreement(
        primary_notes=len(a),
        secondary_notes=len(b),
        matched_notes=matches,
        primary_support_ratio=round(support_a, 4),
        secondary_support_ratio=round(support_b, 4),
        agreement_f1=round(f1, 4),
        disagreements=tuple(disagreements),
    )
