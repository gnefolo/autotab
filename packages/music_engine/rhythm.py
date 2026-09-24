from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from statistics import median
from typing import Iterable

from .engine import TabNote


@dataclass(frozen=True)
class TimeSignature:
    beats: int = 4
    beat_type: int = 4


@dataclass(frozen=True)
class RhythmConfig:
    bpm: float = 120.0
    time_signature: TimeSignature = TimeSignature()
    divisions: int = 480
    subdivision: int = 4

    @property
    def quarter_seconds(self) -> float:
        return 60.0 / self.bpm

    @property
    def grid_ticks(self) -> int:
        return max(1, self.divisions // self.subdivision)

    @property
    def measure_ticks(self) -> int:
        return int(self.time_signature.beats * self.divisions * (4 / self.time_signature.beat_type))


@dataclass(frozen=True)
class QuantizedTabNote:
    pitch: int
    onset_tick: int
    duration_ticks: int
    string_index: int
    fret: int
    confidence: float
    chord_index: int
    original_start: float
    original_duration: float

    @property
    def end_tick(self) -> int:
        return self.onset_tick + self.duration_ticks


def estimate_bpm(tab_notes: Iterable[TabNote], fallback: float = 120.0) -> float:
    onsets = sorted({round(n.start, 4) for n in tab_notes})
    if len(onsets) < 3:
        return fallback
    iois = [b - a for a, b in zip(onsets, onsets[1:]) if 0.12 <= b - a <= 2.5]
    if not iois:
        return fallback
    candidates: list[float] = []
    for ioi in iois:
        bpm = 60.0 / ioi
        while bpm < 70:
            bpm *= 2
        while bpm > 180:
            bpm /= 2
        if 50 <= bpm <= 220 and isfinite(bpm):
            candidates.append(bpm)
    if not candidates:
        return fallback
    return round(float(median(candidates)), 2)


def seconds_to_ticks(seconds: float, config: RhythmConfig) -> float:
    return seconds / config.quarter_seconds * config.divisions


def _round_to_grid(raw_ticks: float, grid_ticks: int) -> int:
    return int(round(raw_ticks / grid_ticks) * grid_ticks)


def quantize_tab_notes(notes: Iterable[TabNote], bpm: float | None = None, time_signature: TimeSignature | None = None, divisions: int = 480, subdivision: int = 4) -> tuple[RhythmConfig, list[QuantizedTabNote]]:
    ordered = sorted(notes, key=lambda n: (n.start, n.chord_index, n.string_index))
    if not ordered:
        cfg = RhythmConfig(bpm=bpm or 120.0, time_signature=time_signature or TimeSignature(), divisions=divisions, subdivision=subdivision)
        return cfg, []
    actual_bpm = bpm if bpm and bpm > 0 else estimate_bpm(ordered)
    cfg = RhythmConfig(bpm=actual_bpm, time_signature=time_signature or TimeSignature(), divisions=divisions, subdivision=subdivision)
    chord_starts: dict[int, float] = {}
    for n in ordered:
        chord_starts[n.chord_index] = min(chord_starts.get(n.chord_index, n.start), n.start)
    chord_ticks = {idx: max(0, _round_to_grid(seconds_to_ticks(start, cfg), cfg.grid_ticks)) for idx, start in chord_starts.items()}
    next_onset_by_chord: dict[int, int] = {}
    ordered_chords = sorted(chord_ticks.items(), key=lambda item: item[1])
    for i, (idx, onset) in enumerate(ordered_chords[:-1]):
        next_onset_by_chord[idx] = ordered_chords[i + 1][1]
    out: list[QuantizedTabNote] = []
    for n in ordered:
        duration = max(cfg.grid_ticks, _round_to_grid(seconds_to_ticks(n.duration, cfg), cfg.grid_ticks))
        next_onset = next_onset_by_chord.get(n.chord_index)
        if next_onset is not None and next_onset > chord_ticks[n.chord_index]:
            duration = min(duration, next_onset - chord_ticks[n.chord_index])
        out.append(QuantizedTabNote(n.pitch, chord_ticks[n.chord_index], duration, n.string_index, n.fret, n.confidence, n.chord_index, n.start, n.duration))
    return cfg, out


def split_note_at_measures(note: QuantizedTabNote, measure_ticks: int) -> list[tuple[int, int, int]]:
    pieces: list[tuple[int, int, int]] = []
    cursor = note.onset_tick
    remaining = note.duration_ticks
    while remaining > 0:
        measure_index = cursor // measure_ticks
        local_onset = cursor % measure_ticks
        room = measure_ticks - local_onset
        duration = min(remaining, room)
        pieces.append((measure_index, local_onset, duration))
        cursor += duration
        remaining -= duration
    return pieces
