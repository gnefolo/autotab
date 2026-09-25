from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import median
from typing import Iterable

from .engine import NoteEvent, Tuning, possible_positions


@dataclass(frozen=True)
class EnsembleDecision:
    origin: str
    decision: str
    score: float
    pitch: int
    start: float
    duration: float
    confidence: float
    reasons: tuple[str, ...]
    primary_index: int | None = None
    secondary_index: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class EnsembleReview:
    confirmed: int
    primary_only: int
    secondary_only: int
    keep: int
    review: int
    reject: int
    safe_note_count: int
    decisions: tuple[EnsembleDecision, ...]
    safe_events: tuple[NoteEvent, ...]

    def to_dict(self, include_events: bool = True) -> dict:
        payload = {
            "confirmed": self.confirmed,
            "primary_only": self.primary_only,
            "secondary_only": self.secondary_only,
            "keep": self.keep,
            "review": self.review,
            "reject": self.reject,
            "safe_note_count": self.safe_note_count,
            "decisions": [row.to_dict() for row in self.decisions],
        }
        if include_events:
            payload["safe_events"] = [asdict(event) for event in self.safe_events]
        return payload


def _musical_context(
    event: NoteEvent,
    all_events: list[NoteEvent],
    tuning: Tuning,
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    if possible_positions(event.pitch, tuning):
        score += 0.16
        reasons.append("physically_playable")
    else:
        score -= 0.42
        reasons.append("outside_selected_tuning")

    if event.duration >= 0.18:
        score += 0.09
        reasons.append("stable_duration")
    elif event.duration >= 0.07:
        score += 0.04
        reasons.append("non_micro_duration")
    else:
        score -= 0.14
        reasons.append("micro_note")

    simultaneous = [
        other
        for other in all_events
        if other is not event and abs(other.start - event.start) <= 0.035
    ]
    if simultaneous and len(simultaneous) <= 5:
        score += 0.07
        reasons.append("plausible_chord_context")
    elif len(simultaneous) > 5:
        score -= 0.12
        reasons.append("excessive_polyphony")

    melodic = False
    for other in all_events:
        if other is event:
            continue
        dt = abs(other.start - event.start)
        if 0.04 < dt <= 0.70 and abs(other.pitch - event.pitch) <= 12:
            melodic = True
            break
    if melodic:
        score += 0.09
        reasons.append("melodic_neighbor")

    return score, reasons


def _match_models(
    primary: list[NoteEvent],
    secondary: list[NoteEvent],
    onset_tolerance: float,
) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    used_secondary: set[int] = set()
    matches: list[tuple[int, int]] = []

    for pi, note in enumerate(primary):
        best_index = None
        best_cost = float("inf")
        for si, other in enumerate(secondary):
            if si in used_secondary or note.pitch != other.pitch:
                continue
            onset_error = abs(note.start - other.start)
            if onset_error > onset_tolerance:
                continue
            cost = onset_error + 0.12 * abs(note.duration - other.duration)
            if cost < best_cost:
                best_cost = cost
                best_index = si
        if best_index is not None:
            used_secondary.add(best_index)
            matches.append((pi, best_index))

    matched_primary = {pi for pi, _ in matches}
    primary_only = [i for i in range(len(primary)) if i not in matched_primary]
    secondary_only = [i for i in range(len(secondary)) if i not in used_secondary]
    return matches, primary_only, secondary_only


def build_disagreement_aware_ensemble(
    primary: Iterable[NoteEvent],
    secondary: Iterable[NoteEvent],
    tuning: Tuning,
    onset_tolerance: float = 0.08,
) -> EnsembleReview:
    primary_rows = sorted(list(primary), key=lambda e: (e.start, e.pitch))
    secondary_rows = sorted(list(secondary), key=lambda e: (e.start, e.pitch))
    matches, primary_only, secondary_only = _match_models(
        primary_rows,
        secondary_rows,
        onset_tolerance,
    )

    decisions: list[EnsembleDecision] = []
    safe_events: list[NoteEvent] = []

    for pi, si in matches:
        a = primary_rows[pi]
        b = secondary_rows[si]
        starts = [a.start, b.start]
        durations = [a.duration, b.duration]
        merged = NoteEvent(
            pitch=a.pitch,
            start=float(median(starts)),
            duration=max(0.001, float(median(durations))),
            velocity=max(a.velocity, b.velocity),
            confidence=round(min(0.99, 0.82 + 0.10 * a.confidence + 0.07 * b.confidence), 4),
            pitch_bends=a.pitch_bends or b.pitch_bends,
        )
        reasons = ["confirmed_by_both_models"]
        if possible_positions(merged.pitch, tuning):
            reasons.append("physically_playable")
        safe_events.append(merged)
        decisions.append(
            EnsembleDecision(
                origin="confirmed",
                decision="keep",
                score=0.98,
                pitch=merged.pitch,
                start=round(merged.start, 4),
                duration=round(merged.duration, 4),
                confidence=merged.confidence,
                reasons=tuple(reasons),
                primary_index=pi,
                secondary_index=si,
            )
        )

    for pi in primary_only:
        event = primary_rows[pi]
        context_score, reasons = _musical_context(event, primary_rows, tuning)
        score = 0.48 * event.confidence + 0.18 + context_score
        if event.confidence >= 0.82:
            score += 0.08
            reasons.append("high_primary_confidence")
        elif event.confidence < 0.52:
            score -= 0.10
            reasons.append("low_primary_confidence")
        score = max(0.0, min(1.0, score))

        if score >= 0.72:
            decision = "keep"
            safe_events.append(event)
        elif score >= 0.52:
            decision = "review"
        else:
            decision = "reject"

        decisions.append(
            EnsembleDecision(
                origin="primary_only",
                decision=decision,
                score=round(score, 4),
                pitch=event.pitch,
                start=round(event.start, 4),
                duration=round(event.duration, 4),
                confidence=round(event.confidence, 4),
                reasons=tuple(reasons),
                primary_index=pi,
            )
        )

    for si in secondary_only:
        event = secondary_rows[si]
        context_score, reasons = _musical_context(event, secondary_rows, tuning)
        score = 0.28 * event.confidence + 0.16 + context_score

        nearby_primary = any(
            abs(other.start - event.start) <= onset_tolerance
            and 1 <= abs(other.pitch - event.pitch) <= 2
            for other in primary_rows
        )
        if nearby_primary:
            score += 0.07
            reasons.append("near_primary_pitch_disagreement")

        score = max(0.0, min(1.0, score))
        # The second-opinion model is currently less trusted for polyphonic
        # strumming. Recovery therefore requires unusually strong evidence.
        if score >= 0.86:
            decision = "keep"
            safe_events.append(event)
        elif score >= 0.58:
            decision = "review"
        else:
            decision = "reject"

        decisions.append(
            EnsembleDecision(
                origin="secondary_only",
                decision=decision,
                score=round(score, 4),
                pitch=event.pitch,
                start=round(event.start, 4),
                duration=round(event.duration, 4),
                confidence=round(event.confidence, 4),
                reasons=tuple(reasons),
                secondary_index=si,
            )
        )

    # Deduplicate any merged/recovered collisions conservatively.
    deduped: list[NoteEvent] = []
    for event in sorted(safe_events, key=lambda e: (e.start, e.pitch)):
        duplicate = next(
            (
                existing
                for existing in reversed(deduped[-12:])
                if existing.pitch == event.pitch
                and abs(existing.start - event.start) <= 0.04
            ),
            None,
        )
        if duplicate is None:
            deduped.append(event)

    counts = {
        "keep": sum(1 for row in decisions if row.decision == "keep"),
        "review": sum(1 for row in decisions if row.decision == "review"),
        "reject": sum(1 for row in decisions if row.decision == "reject"),
    }
    return EnsembleReview(
        confirmed=len(matches),
        primary_only=len(primary_only),
        secondary_only=len(secondary_only),
        keep=counts["keep"],
        review=counts["review"],
        reject=counts["reject"],
        safe_note_count=len(deduped),
        decisions=tuple(sorted(decisions, key=lambda row: (row.start, row.pitch, row.origin))),
        safe_events=tuple(deduped),
    )
