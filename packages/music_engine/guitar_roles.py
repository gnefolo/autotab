from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Iterable

from .engine import NoteEvent, group_simultaneous_events


@dataclass(frozen=True)
class GuitarRoleSplit:
    rhythm: tuple[NoteEvent, ...]
    lead: tuple[NoteEvent, ...]
    confidence: float
    explanation: tuple[str, ...]


def split_guitar_roles(
    events: Iterable[NoteEvent],
    onset_tolerance: float = 0.035,
) -> GuitarRoleSplit:
    rows = sorted(list(events), key=lambda e: (e.start, e.pitch))
    if not rows:
        return GuitarRoleSplit((), (), 0.0, ("No guitar note events available.",))

    groups = group_simultaneous_events(rows, onset_tolerance=onset_tolerance)
    median_pitch = float(median([e.pitch for e in rows]))
    median_duration = float(median([e.duration for e in rows]))

    rhythm: list[NoteEvent] = []
    lead: list[NoteEvent] = []
    ambiguous_singletons: list[NoteEvent] = []

    for group in groups:
        if len(group.events) >= 2:
            rhythm.extend(group.events)
            continue

        event = group.events[0]
        high_register = event.pitch >= median_pitch + 3
        sustained = event.duration >= max(0.18, median_duration * 1.25)

        if high_register or sustained:
            lead.append(event)
        else:
            ambiguous_singletons.append(event)

    # Detect melodic runs among otherwise ambiguous singleton notes.
    for i, event in enumerate(ambiguous_singletons):
        prev = ambiguous_singletons[i - 1] if i > 0 else None
        nxt = ambiguous_singletons[i + 1] if i + 1 < len(ambiguous_singletons) else None
        linked = False
        if prev is not None and 0.0 <= event.start - prev.start <= 0.65:
            linked = abs(event.pitch - prev.pitch) <= 9
        if nxt is not None and 0.0 <= nxt.start - event.start <= 0.65:
            linked = linked or abs(nxt.pitch - event.pitch) <= 9
        if linked and event.pitch >= median_pitch:
            lead.append(event)
        else:
            rhythm.append(event)

    # If a song is almost entirely monophonic, expose a useful lead view rather
    # than returning an empty virtual track. This is still marked as inferred.
    if len(lead) < 4 and len(rows) >= 12:
        candidates = sorted(
            [e for e in rhythm if e.pitch >= median_pitch],
            key=lambda e: (e.pitch, e.duration, e.confidence),
            reverse=True,
        )
        promote_count = min(max(4 - len(lead), len(rows) // 8), len(candidates))
        promoted = set(id(e) for e in candidates[:promote_count])
        lead.extend([e for e in rhythm if id(e) in promoted])
        rhythm = [e for e in rhythm if id(e) not in promoted]

    lead.sort(key=lambda e: (e.start, e.pitch))
    rhythm.sort(key=lambda e: (e.start, e.pitch))

    chord_events = sum(len(g.events) for g in groups if len(g.events) >= 2)
    structured = (chord_events + len(lead)) / max(1, len(rows))
    confidence = max(0.2, min(0.9, 0.35 + 0.5 * structured))

    explanation = (
        "Polyphonic onset groups are assigned to rhythm guitar.",
        "Higher-register, sustained and melodic singleton runs are assigned to lead guitar.",
        "The split is inferred from one guitar stem; it is not source-separated Guitar 1 / Guitar 2 audio.",
    )
    return GuitarRoleSplit(
        rhythm=tuple(rhythm),
        lead=tuple(lead),
        confidence=round(confidence, 3),
        explanation=explanation,
    )
