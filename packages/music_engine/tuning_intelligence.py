from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from .engine import NoteEvent, TUNINGS, Tuning, possible_positions


@dataclass(frozen=True)
class TuningCompatibility:
    tuning_id: str
    name: str
    family: str
    score: float
    coverage: float
    playable_notes: int
    total_notes: int
    out_of_range_notes: tuple[int, ...]
    lowest_open_pitch: int
    lowest_observed_pitch: int | None
    mean_min_fret: float
    open_string_ratio: float
    explanation: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def tuning_family(tuning_id: str) -> str:
    return "bass" if tuning_id.startswith("bass_") else "guitar"


def _event_weight(event: NoteEvent) -> float:
    # Confidence dominates; a small duration term keeps long, stable notes useful
    # without letting one sustained note overwhelm the analysis.
    confidence = max(0.05, min(1.0, float(event.confidence)))
    duration = max(0.02, min(1.5, float(event.duration)))
    return confidence * (1.0 + 0.20 * duration)


def score_tuning_compatibility(
    events: Iterable[NoteEvent],
    tuning_id: str,
    tuning: Tuning,
) -> TuningCompatibility:
    rows = list(events)
    total = len(rows)
    lowest_observed = min((e.pitch for e in rows), default=None)
    if not rows:
        return TuningCompatibility(
            tuning_id=tuning_id,
            name=tuning.name,
            family=tuning_family(tuning_id),
            score=0.0,
            coverage=0.0,
            playable_notes=0,
            total_notes=0,
            out_of_range_notes=(),
            lowest_open_pitch=min(tuning.open_pitches) + tuning.capo,
            lowest_observed_pitch=None,
            mean_min_fret=0.0,
            open_string_ratio=0.0,
            explanation=("No note events available.",),
        )

    total_weight = 0.0
    playable_weight = 0.0
    min_frets: list[int] = []
    open_hits = 0
    out_of_range: list[int] = []

    for event in rows:
        weight = _event_weight(event)
        total_weight += weight
        positions = possible_positions(event.pitch, tuning)
        if not positions:
            out_of_range.append(event.pitch)
            continue
        playable_weight += weight
        min_fret = min(p.fret for p in positions)
        min_frets.append(min_fret)
        if any(p.fret == 0 for p in positions):
            open_hits += 1

    coverage = playable_weight / total_weight if total_weight else 0.0
    mean_min_fret = sum(min_frets) / len(min_frets) if min_frets else float(tuning.max_fret)
    open_ratio = open_hits / len(min_frets) if min_frets else 0.0

    lowest_open = min(tuning.open_pitches) + tuning.capo
    low_gap = 0 if lowest_observed is None else max(0, lowest_open - lowest_observed)

    # Score is deliberately explainable rather than pretending to identify the
    # recorded tuning with certainty. Coverage is dominant; ergonomic evidence
    # breaks ties between tunings that can technically play the same pitches.
    score = (
        100.0 * coverage
        - 1.20 * mean_min_fret
        + 8.0 * open_ratio
        - 4.0 * low_gap
    )
    score = max(0.0, min(100.0, score))

    explanation: list[str] = []
    if coverage >= 0.995:
        explanation.append("All weighted note events are inside the instrument range.")
    elif coverage >= 0.95:
        explanation.append("Almost all weighted note events are playable.")
    else:
        explanation.append("Some detected notes fall outside this tuning's playable range.")

    if open_ratio >= 0.08:
        explanation.append("The transcription aligns with several open-string pitches.")
    if mean_min_fret <= 3.5:
        explanation.append("Detected pitches can be reached mostly in low fret positions.")
    elif mean_min_fret >= 8.0:
        explanation.append("Many detected pitches require relatively high fret positions.")
    if low_gap > 0:
        explanation.append(
            f"The lowest detected pitch is {low_gap} semitone(s) below the lowest open string."
        )

    return TuningCompatibility(
        tuning_id=tuning_id,
        name=tuning.name,
        family=tuning_family(tuning_id),
        score=round(score, 2),
        coverage=round(coverage, 4),
        playable_notes=len(min_frets),
        total_notes=total,
        out_of_range_notes=tuple(sorted(set(out_of_range))),
        lowest_open_pitch=lowest_open,
        lowest_observed_pitch=lowest_observed,
        mean_min_fret=round(mean_min_fret, 2),
        open_string_ratio=round(open_ratio, 4),
        explanation=tuple(explanation),
    )


def suggest_tunings(
    events: Iterable[NoteEvent],
    family: str = "guitar",
    limit: int = 5,
) -> list[TuningCompatibility]:
    rows = list(events)
    candidates = [
        (key, tuning)
        for key, tuning in TUNINGS.items()
        if family == "all" or tuning_family(key) == family
    ]
    scored = [score_tuning_compatibility(rows, key, tuning) for key, tuning in candidates]
    scored.sort(
        key=lambda item: (
            -item.score,
            -item.coverage,
            item.mean_min_fret,
            item.tuning_id,
        )
    )
    return scored[: max(1, limit)]
