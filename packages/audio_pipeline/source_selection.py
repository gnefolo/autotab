from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from music_engine.accuracy import confidence_summary
from music_engine.engine import NoteEvent


@dataclass(frozen=True)
class SourceCandidateScore:
    source: str
    score: float
    note_count: int
    mean_confidence: float
    low_confidence_ratio: float
    micro_note_ratio: float
    notes_per_second: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SourceSelection:
    selected_source: str
    scores: tuple[SourceCandidateScore, ...]

    def to_dict(self) -> dict:
        return {
            "selected_source": self.selected_source,
            "scores": [row.to_dict() for row in self.scores],
        }


def _score_candidate(source: str, events: Sequence[NoteEvent], max_count: int) -> SourceCandidateScore:
    if not events:
        return SourceCandidateScore(
            source=source,
            score=0.0,
            note_count=0,
            mean_confidence=0.0,
            low_confidence_ratio=1.0,
            micro_note_ratio=1.0,
            notes_per_second=0.0,
        )

    summary = confidence_summary(events)
    duration = max(e.start + e.duration for e in events) - min(e.start for e in events)
    duration = max(duration, 0.25)
    density = len(events) / duration
    micro_ratio = sum(1 for e in events if e.duration < 0.07) / len(events)
    count_ratio = len(events) / max(1, max_count)

    # Agreement-derived confidence from the multi-pass transcriber dominates.
    # Penalize the two artifact patterns we see most often: very short events and
    # implausibly dense note streams. A small completeness bonus prevents a very
    # sparse candidate from winning only because it kept a handful of safe notes.
    density_penalty = min(0.20, max(0.0, density - 9.0) * 0.018)
    score = (
        0.72 * float(summary["mean_confidence"])
        - 0.28 * float(summary["low_confidence_ratio"])
        - 0.16 * micro_ratio
        - density_penalty
        + 0.08 * count_ratio
    )
    score = max(0.0, min(1.0, score))

    return SourceCandidateScore(
        source=source,
        score=round(score, 4),
        note_count=len(events),
        mean_confidence=round(float(summary["mean_confidence"]), 4),
        low_confidence_ratio=round(float(summary["low_confidence_ratio"]), 4),
        micro_note_ratio=round(micro_ratio, 4),
        notes_per_second=round(density, 3),
    )


def select_guitar_source(
    candidates: Mapping[str, Sequence[NoteEvent]],
) -> SourceSelection:
    if not candidates:
        raise ValueError("At least one guitar source candidate is required")

    max_count = max((len(events) for events in candidates.values()), default=0)
    scores = tuple(
        _score_candidate(source, list(events), max_count)
        for source, events in candidates.items()
    )

    # Deterministic tie-break: prefer the dedicated six-stem guitar source.
    selected = max(
        scores,
        key=lambda row: (
            row.score,
            row.mean_confidence,
            row.note_count,
            1 if row.source == "guitar" else 0,
        ),
    )
    return SourceSelection(selected_source=selected.source, scores=scores)
