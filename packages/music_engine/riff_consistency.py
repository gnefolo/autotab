from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .engine import NoteEvent


@dataclass(frozen=True)
class RiffCorrection:
    event_index: int
    old_pitch: int
    new_pitch: int
    support: int
    confidence: float


@dataclass(frozen=True)
class RiffConsistencyResult:
    events: tuple[NoteEvent, ...]
    corrections: tuple[RiffCorrection, ...]


def _rhythm_signature(window: list[NoteEvent], quantum: float) -> tuple[int, ...]:
    start = window[0].start
    return tuple(int(round((event.start - start) / quantum)) for event in window)


def harmonize_repeated_riffs(
    events: Iterable[NoteEvent],
    window_size: int = 5,
    rhythm_quantum: float = 0.05,
    minimum_occurrences: int = 3,
    low_confidence_threshold: float = 0.72,
) -> RiffConsistencyResult:
    rows = sorted(list(events), key=lambda e: (e.start, e.pitch))
    if len(rows) < window_size * minimum_occurrences:
        return RiffConsistencyResult(tuple(rows), ())

    corrected = list(rows)
    corrections: dict[int, RiffCorrection] = {}

    # For each position in a short phrase, make that position a wildcard.
    # Repeated phrases that are identical everywhere else land in the same bucket.
    for wildcard_pos in range(window_size):
        buckets: dict[tuple, list[tuple[int, list[NoteEvent]]]] = {}

        for start_idx in range(0, len(rows) - window_size + 1):
            window = rows[start_idx:start_idx + window_size]
            rhythm = _rhythm_signature(window, rhythm_quantum)
            masked_pitches = tuple(
                None if i == wildcard_pos else event.pitch
                for i, event in enumerate(window)
            )
            # Include coarse duration shape so unrelated phrases with the same
            # onset rhythm are much less likely to collide.
            durations = tuple(
                int(round(event.duration / rhythm_quantum))
                for event in window
            )
            key = (rhythm, masked_pitches, durations)
            buckets.setdefault(key, []).append((start_idx, window))

        for occurrences in buckets.values():
            # Require independent repeated phrases, not overlapping sliding windows.
            independent: list[tuple[int, list[NoteEvent]]] = []
            last_end = -1
            for start_idx, window in occurrences:
                if start_idx >= last_end:
                    independent.append((start_idx, window))
                    last_end = start_idx + window_size
            if len(independent) < minimum_occurrences:
                continue

            pitch_votes: dict[int, int] = {}
            for _, window in independent:
                pitch = window[wildcard_pos].pitch
                pitch_votes[pitch] = pitch_votes.get(pitch, 0) + 1

            majority_pitch, support = max(
                pitch_votes.items(),
                key=lambda item: (item[1], -item[0]),
            )
            if support < minimum_occurrences - 1:
                continue

            for start_idx, window in independent:
                event = window[wildcard_pos]
                event_idx = start_idx + wildcard_pos
                if event.pitch == majority_pitch:
                    continue
                if event.confidence > low_confidence_threshold:
                    continue
                # Only correct small AMT disagreements. Large jumps can indicate
                # a legitimate variation of the riff.
                if abs(event.pitch - majority_pitch) > 2:
                    continue

                replacement = NoteEvent(
                    pitch=majority_pitch,
                    start=event.start,
                    duration=event.duration,
                    velocity=event.velocity,
                    confidence=max(
                        event.confidence,
                        min(0.92, 0.62 + 0.08 * support),
                    ),
                    pitch_bends=event.pitch_bends,
                )
                corrected[event_idx] = replacement
                corrections[event_idx] = RiffCorrection(
                    event_index=event_idx,
                    old_pitch=event.pitch,
                    new_pitch=majority_pitch,
                    support=support,
                    confidence=event.confidence,
                )

    return RiffConsistencyResult(
        events=tuple(corrected),
        corrections=tuple(
            corrections[index]
            for index in sorted(corrections)
        ),
    )
