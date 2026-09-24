from __future__ import annotations

from typing import Iterable

from .engine import NoteEvent


def replace_events_in_window(
    existing: Iterable[NoteEvent],
    replacement: Iterable[NoteEvent],
    start: float,
    end: float,
) -> list[NoteEvent]:
    if start < 0 or end <= start:
        raise ValueError("Invalid refinement window")

    kept = [
        event
        for event in existing
        if not (start <= event.start < end)
    ]
    inserted = [
        event
        for event in replacement
        if start <= event.start < end
    ]
    return sorted(
        [*kept, *inserted],
        key=lambda event: (event.start, event.pitch),
    )
