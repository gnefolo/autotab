from __future__ import annotations
from dataclasses import dataclass
from itertools import product
from typing import Iterable, Optional


@dataclass(frozen=True)
class Tuning:
    name: str
    open_pitches: tuple[int, ...]
    max_fret: int = 24


@dataclass(frozen=True)
class NoteEvent:
    pitch: int
    start: float
    duration: float
    velocity: int = 90
    confidence: float = 1.0
    pitch_bends: tuple[float, ...] = ()


@dataclass(frozen=True)
class Position:
    string_index: int
    fret: int


@dataclass(frozen=True)
class TabNote:
    pitch: int
    start: float
    duration: float
    string_index: int
    fret: int
    confidence: float
    chord_index: int = 0


@dataclass(frozen=True)
class NoteGroup:
    start: float
    events: tuple[NoteEvent, ...]


@dataclass(frozen=True)
class Voicing:
    positions: tuple[Position, ...]

    @property
    def fretted_frets(self) -> tuple[int, ...]:
        return tuple(p.fret for p in self.positions if p.fret > 0)

    @property
    def fret_span(self) -> int:
        frets = self.fretted_frets
        return max(frets) - min(frets) if len(frets) > 1 else 0

    @property
    def center_fret(self) -> float:
        frets = self.fretted_frets
        return sum(frets) / len(frets) if frets else 0.0


TUNINGS: dict[str, Tuning] = {
    "guitar_standard": Tuning("Guitar Standard EADGBE", (40, 45, 50, 55, 59, 64)),
    "guitar_eb": Tuning("Guitar Eb Standard", (39, 44, 49, 54, 58, 63)),
    "guitar_d_standard": Tuning("Guitar D Standard", (38, 43, 48, 53, 57, 62)),
    "guitar_drop_d": Tuning("Guitar Drop D", (38, 45, 50, 55, 59, 64)),
    "guitar_drop_c_sharp": Tuning("Guitar Drop C#", (37, 44, 49, 54, 58, 63)),
    "guitar_drop_c": Tuning("Guitar Drop C", (36, 43, 48, 53, 57, 62)),
    "bass_standard_4": Tuning("Bass Standard EADG", (28, 33, 38, 43)),
    "bass_drop_d_4": Tuning("Bass Drop D", (26, 33, 38, 43)),
    "bass_standard_5": Tuning("5-string Bass BEADG", (23, 28, 33, 38, 43)),
}


def get_tuning(key: str) -> Tuning:
    try:
        return TUNINGS[key]
    except KeyError as exc:
        raise ValueError(f"Unknown tuning: {key}") from exc


def possible_positions(pitch: int, tuning: Tuning) -> list[Position]:
    positions: list[Position] = []
    for string_index, open_pitch in enumerate(tuning.open_pitches):
        fret = pitch - open_pitch
        if 0 <= fret <= tuning.max_fret:
            positions.append(Position(string_index=string_index, fret=fret))
    return positions


def group_simultaneous_events(events: Iterable[NoteEvent], onset_tolerance: float = 0.035) -> list[NoteGroup]:
    ordered = sorted(events, key=lambda e: (e.start, e.pitch))
    if not ordered:
        return []
    groups: list[list[NoteEvent]] = []
    anchor = ordered[0].start
    current: list[NoteEvent] = [ordered[0]]
    for event in ordered[1:]:
        if event.start - anchor <= onset_tolerance:
            current.append(event)
        else:
            groups.append(current)
            current = [event]
            anchor = event.start
    groups.append(current)
    result: list[NoteGroup] = []
    for group in groups:
        by_pitch: dict[int, NoteEvent] = {}
        for event in group:
            existing = by_pitch.get(event.pitch)
            if existing is None or event.confidence > existing.confidence:
                by_pitch[event.pitch] = event
        deduped = tuple(sorted(by_pitch.values(), key=lambda e: e.pitch))
        result.append(NoteGroup(start=min(e.start for e in deduped), events=deduped))
    return result


def _voicing_intrinsic_cost(voicing: Voicing) -> float:
    positions = voicing.positions
    if not positions:
        return 0.0
    fretted = voicing.fretted_frets
    cost = 0.0
    cost += 1.35 * voicing.fret_span
    if voicing.fret_span > 4:
        cost += 8.0 + (voicing.fret_span - 4) * 4.0
    cost += voicing.center_fret * 0.09
    cost -= 0.18 * sum(1 for p in positions if p.fret == 0)
    strings = sorted(p.string_index for p in positions)
    if len(strings) > 1:
        gaps = [b - a for a, b in zip(strings, strings[1:])]
        cost += 0.3 * sum(max(0, gap - 1) for gap in gaps)
    if any(p.fret == 0 for p in positions) and fretted and max(fretted) >= 9:
        cost += 2.5
    return cost


def possible_voicings(group: NoteGroup, tuning: Tuning, max_fret_span: int = 5, max_candidates: int = 256) -> list[Voicing]:
    if len(group.events) > len(tuning.open_pitches):
        return []
    per_note: list[list[Position]] = []
    for event in group.events:
        positions = possible_positions(event.pitch, tuning)
        if not positions:
            return []
        per_note.append(positions)
    candidates: list[Voicing] = []
    for combo in product(*per_note):
        strings = [p.string_index for p in combo]
        if len(set(strings)) != len(strings):
            continue
        voicing = Voicing(tuple(combo))
        if voicing.fret_span > max_fret_span:
            continue
        candidates.append(voicing)
    candidates.sort(key=_voicing_intrinsic_cost)
    return candidates[:max_candidates]


def transition_cost(prev: Optional[Position], cur: Position) -> float:
    if prev is None:
        return cur.fret * 0.06
    fret_move = abs(cur.fret - prev.fret)
    string_move = abs(cur.string_index - prev.string_index)
    cost = 0.85 * fret_move + 0.55 * string_move
    if fret_move > 5:
        cost += (fret_move - 5) * 1.4
    if string_move > 2:
        cost += (string_move - 2) * 0.8
    if cur.fret == 0:
        cost -= 0.25
    return cost


def _voicing_transition_cost(prev: Optional[Voicing], cur: Voicing) -> float:
    cost = _voicing_intrinsic_cost(cur)
    if prev is None:
        return cost
    center_move = abs(cur.center_fret - prev.center_fret)
    cost += 1.0 * center_move
    if center_move > 5:
        cost += (center_move - 5) * 1.6
    prev_strings = {p.string_index for p in prev.positions}
    cur_strings = {p.string_index for p in cur.positions}
    cost -= 0.16 * len(prev_strings & cur_strings)
    prev_sc = sum(prev_strings) / len(prev_strings)
    cur_sc = sum(cur_strings) / len(cur_strings)
    cost += 0.28 * abs(cur_sc - prev_sc)
    return cost


def optimize_polyphonic_fingering(events: Iterable[NoteEvent], tuning: Tuning, onset_tolerance: float = 0.035, max_fret_span: int = 5, max_candidates_per_group: int = 256) -> list[TabNote]:
    groups = group_simultaneous_events(events, onset_tolerance=onset_tolerance)
    if not groups:
        return []
    candidates: list[list[Voicing]] = []
    for group in groups:
        voicings = possible_voicings(group, tuning, max_fret_span=max_fret_span, max_candidates=max_candidates_per_group)
        if not voicings:
            pitches = [e.pitch for e in group.events]
            raise ValueError(f"No playable voicing for pitches {pitches} in {tuning.name} within fret span {max_fret_span}")
        candidates.append(voicings)
    dp: list[dict[Voicing, tuple[float, Optional[Voicing]]]] = []
    dp.append({v: (_voicing_transition_cost(None, v), None) for v in candidates[0]})
    for i in range(1, len(groups)):
        layer: dict[Voicing, tuple[float, Optional[Voicing]]] = {}
        for cur in candidates[i]:
            best_cost = float("inf")
            best_prev: Optional[Voicing] = None
            for prev, (prev_cost, _) in dp[i - 1].items():
                cost = prev_cost + _voicing_transition_cost(prev, cur)
                if cost < best_cost:
                    best_cost = cost
                    best_prev = prev
            layer[cur] = (best_cost, best_prev)
        dp.append(layer)
    last = min(dp[-1], key=lambda v: dp[-1][v][0])
    chosen: list[Voicing] = [last]
    for i in range(len(dp) - 1, 0, -1):
        prev = dp[i][chosen[-1]][1]
        assert prev is not None
        chosen.append(prev)
    chosen.reverse()
    result: list[TabNote] = []
    for chord_index, (group, voicing) in enumerate(zip(groups, chosen)):
        for event, position in zip(group.events, voicing.positions):
            result.append(TabNote(event.pitch, event.start, event.duration, position.string_index, position.fret, event.confidence, chord_index))
    return sorted(result, key=lambda n: (n.start, n.string_index, n.pitch))


def optimize_fingering(events: Iterable[NoteEvent], tuning: Tuning) -> list[TabNote]:
    ordered = sorted(events, key=lambda e: (e.start, e.pitch))
    if not ordered:
        return []
    candidates: list[list[Position]] = []
    for event in ordered:
        pos = possible_positions(event.pitch, tuning)
        if not pos:
            raise ValueError(f"Pitch {event.pitch} is not playable in {tuning.name} within {tuning.max_fret} frets")
        candidates.append(pos)
    dp: list[dict[Position, tuple[float, Optional[Position]]]] = []
    dp.append({p: (transition_cost(None, p), None) for p in candidates[0]})
    for i in range(1, len(ordered)):
        layer: dict[Position, tuple[float, Optional[Position]]] = {}
        for cur in candidates[i]:
            best_cost = float("inf")
            best_prev: Optional[Position] = None
            for prev, (prev_cost, _) in dp[i - 1].items():
                cost = prev_cost + transition_cost(prev, cur)
                if cost < best_cost:
                    best_cost = cost
                    best_prev = prev
            layer[cur] = (best_cost, best_prev)
        dp.append(layer)
    last_pos = min(dp[-1], key=lambda p: dp[-1][p][0])
    chosen: list[Position] = [last_pos]
    for i in range(len(dp) - 1, 0, -1):
        prev = dp[i][chosen[-1]][1]
        assert prev is not None
        chosen.append(prev)
    chosen.reverse()
    return [TabNote(e.pitch, e.start, e.duration, p.string_index, p.fret, e.confidence, i) for i, (e, p) in enumerate(zip(ordered, chosen))]
