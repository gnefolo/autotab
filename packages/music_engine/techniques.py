from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable

from .engine import NoteEvent, TabNote


@dataclass(frozen=True)
class TechniqueHint:
    note_index: int
    kind: str
    confidence: float
    value: float | None = None
    source: str = "heuristic"

    def to_dict(self) -> dict:
        return asdict(self)


def _bend_stats(values: tuple[float, ...]) -> tuple[float, int]:
    if not values:
        return 0.0, 0
    lo, hi = min(values), max(values)
    crossings = 0
    prev = 0
    mean = sum(values) / len(values)
    for value in values:
        sign = 1 if value > mean else -1 if value < mean else 0
        if prev and sign and sign != prev:
            crossings += 1
        if sign:
            prev = sign
    return hi - lo, crossings


def detect_technique_hints(events: Iterable[NoteEvent], tab_notes: Iterable[TabNote]) -> list[TechniqueHint]:
    events_list = list(events)
    tab_list = list(tab_notes)
    hints: list[TechniqueHint] = []
    matched: list[NoteEvent | None] = []
    for tab in tab_list:
        candidates = [e for e in events_list if e.pitch == tab.pitch]
        event = min(candidates, key=lambda e: abs(e.start - tab.start)) if candidates else None
        matched.append(event)
    for idx, event in enumerate(matched):
        if event is None or not event.pitch_bends:
            continue
        span, crossings = _bend_stats(event.pitch_bends)
        if span >= 0.75:
            hints.append(TechniqueHint(idx, "bend", min(0.98, 0.62 + span * 0.08), round(span, 3)))
        elif span >= 0.20 and crossings >= 3:
            hints.append(TechniqueHint(idx, "vibrato", min(0.94, 0.55 + crossings * 0.04), round(span, 3)))
    for idx in range(1, len(tab_list)):
        prev, cur = tab_list[idx - 1], tab_list[idx]
        gap = cur.start - (prev.start + prev.duration)
        interval = cur.fret - prev.fret
        if prev.string_index != cur.string_index or abs(interval) > 5 or abs(interval) < 1:
            continue
        if -0.025 <= gap <= 0.11:
            kind = "hammer_on_candidate" if interval > 0 else "pull_off_candidate"
            confidence = 0.58 if gap <= 0.06 else 0.48
            hints.append(TechniqueHint(idx, kind, confidence, abs(interval)))
        elif gap < 0 and abs(interval) >= 2:
            hints.append(TechniqueHint(idx, "slide_candidate", 0.52, abs(interval)))
    return hints
