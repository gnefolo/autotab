from __future__ import annotations
from dataclasses import asdict, dataclass
from collections import defaultdict
from typing import Iterable

from .engine import TabNote

NOTE_NAMES = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")
CHORD_TEMPLATES = {
    "major": {0, 4, 7}, "minor": {0, 3, 7}, "power": {0, 7},
    "dim": {0, 3, 6}, "aug": {0, 4, 8}, "sus2": {0, 2, 7},
    "sus4": {0, 5, 7}, "7": {0, 4, 7, 10}, "maj7": {0, 4, 7, 11},
    "m7": {0, 3, 7, 10}, "mMaj7": {0, 3, 7, 11}, "dim7": {0, 3, 6, 9},
    "m7b5": {0, 3, 6, 10}, "6": {0, 4, 7, 9}, "m6": {0, 3, 7, 9},
    "add9": {0, 2, 4, 7},
}
SUFFIX = {"major":"", "minor":"m", "power":"5"}


@dataclass(frozen=True)
class ChordAnalysis:
    chord_index: int
    name: str
    root: str | None
    quality: str | None
    bass: str
    inversion: int | None
    confidence: float
    pitch_classes: tuple[int, ...]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Barre:
    chord_index: int
    fret: int
    first_string: int
    last_string: int
    string_count: int
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class FingerAssignment:
    chord_index: int
    pitch: int
    string_index: int
    fret: int
    finger: int

    def to_dict(self) -> dict:
        return asdict(self)


def analyze_chord(pitches: Iterable[int], chord_index: int = 0) -> ChordAnalysis:
    raw = sorted(set(int(p) for p in pitches))
    if not raw:
        return ChordAnalysis(chord_index, "N.C.", None, None, "N.C.", None, 0.0, ())
    pcs = tuple(sorted({p % 12 for p in raw}))
    bass_pc = min(raw) % 12
    best = None
    for root in pcs:
        intervals = {(pc - root) % 12 for pc in pcs}
        for quality, template in CHORD_TEMPLATES.items():
            missing = len(template - intervals)
            extra = len(intervals - template)
            score = 1.0 - 0.22 * missing - 0.08 * extra
            if missing == 0:
                score += 0.08
            candidate = (score, -extra, -missing, root, quality, template)
            if best is None or candidate > best:
                best = candidate
    assert best is not None
    score, _, _, root, quality, template = best
    root_name = NOTE_NAMES[root]
    bass_name = NOTE_NAMES[bass_pc]
    suffix = SUFFIX.get(quality, quality)
    name = f"{root_name}{suffix}"
    inversion = None
    ordered_intervals = sorted(template)
    bass_interval = (bass_pc - root) % 12
    if bass_interval in ordered_intervals:
        inversion = ordered_intervals.index(bass_interval)
    if bass_pc != root:
        name += f"/{bass_name}"
    return ChordAnalysis(chord_index, name, root_name, quality, bass_name, inversion, round(max(0.0, min(1.0, score)), 3), pcs)


def analyze_progression(tab_notes: Iterable[TabNote]) -> list[ChordAnalysis]:
    groups: dict[int, list[TabNote]] = defaultdict(list)
    for note in tab_notes:
        groups[note.chord_index].append(note)
    return [analyze_chord((n.pitch for n in groups[idx]), idx) for idx in sorted(groups)]


def detect_barres(tab_notes: Iterable[TabNote]) -> list[Barre]:
    groups: dict[int, list[TabNote]] = defaultdict(list)
    for note in tab_notes:
        groups[note.chord_index].append(note)
    result: list[Barre] = []
    for idx, notes in groups.items():
        by_fret: dict[int, list[int]] = defaultdict(list)
        for n in notes:
            if n.fret > 0:
                by_fret[n.fret].append(n.string_index)
        for fret, strings in by_fret.items():
            uniq = sorted(set(strings))
            if len(uniq) < 2:
                continue
            span = uniq[-1] - uniq[0] + 1
            density = len(uniq) / span
            if span >= 2 and density >= 0.66:
                confidence = min(0.95, 0.58 + 0.08 * len(uniq) + 0.12 * density)
                result.append(Barre(idx, fret, uniq[0], uniq[-1], len(uniq), round(confidence, 3)))
    return sorted(result, key=lambda b: (b.chord_index, b.fret))


def assign_fingers(tab_notes: Iterable[TabNote]) -> list[FingerAssignment]:
    notes = list(tab_notes)
    barres = {(b.chord_index, b.fret): b for b in detect_barres(notes)}
    groups: dict[int, list[TabNote]] = defaultdict(list)
    for note in notes:
        groups[note.chord_index].append(note)
    result: list[FingerAssignment] = []
    for idx in sorted(groups):
        chord = groups[idx]
        frets = sorted({n.fret for n in chord if n.fret > 0})
        rank = {f: min(4, i + 1) for i, f in enumerate(frets)}
        for n in chord:
            if n.fret == 0:
                finger = 0
            elif (idx, n.fret) in barres:
                finger = 1
            else:
                finger = rank[n.fret]
            result.append(FingerAssignment(idx, n.pitch, n.string_index, n.fret, finger))
    return result


def analyze_guitar_intelligence(tab_notes: Iterable[TabNote]) -> dict:
    notes = list(tab_notes)
    return {
        "chords": [x.to_dict() for x in analyze_progression(notes)],
        "barres": [x.to_dict() for x in detect_barres(notes)],
        "fingers": [x.to_dict() for x in assign_fingers(notes)],
    }
