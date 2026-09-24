from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Iterable

from .engine import NoteEvent, Position, TabNote, Tuning, get_profile, group_simultaneous_events, possible_voicings


@dataclass(frozen=True)
class FingeringAnchor:
    chord_index: int
    pitch: int
    string_index: int
    fret: int


@dataclass(frozen=True)
class CorrectionRecord:
    job_id: str
    chord_index: int
    pitch: int
    old_string_index: int
    old_fret: int
    new_string_index: int
    new_fret: int
    tuning_name: str
    profile: str
    capo: int
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)


def validate_anchor(anchor: FingeringAnchor, tuning: Tuning) -> None:
    if not 0 <= anchor.string_index < len(tuning.open_pitches):
        raise ValueError("String index is outside the instrument range")
    if not 0 <= anchor.fret <= tuning.max_fret:
        raise ValueError("Fret is outside the instrument range")
    sounding_pitch = tuning.open_pitches[anchor.string_index] + tuning.capo + anchor.fret
    if sounding_pitch != anchor.pitch:
        raise ValueError(
            f"String {anchor.string_index} fret {anchor.fret} sounds MIDI {sounding_pitch}, "
            f"not corrected pitch {anchor.pitch}"
        )


def _intrinsic(voicing, profile) -> float:
    fretted = [p.fret for p in voicing.positions if p.fret > 0]
    span = max(fretted) - min(fretted) if len(fretted) > 1 else 0
    center = sum(fretted) / len(fretted) if fretted else 0.0
    strings = sorted(p.string_index for p in voicing.positions)
    cost = profile.fret_span_weight * span + profile.position_weight * center
    cost -= profile.open_string_bonus * sum(1 for p in voicing.positions if p.fret == 0)
    if len(strings) > 1:
        cost += profile.string_gap_weight * sum(max(0, b - a - 1) for a, b in zip(strings, strings[1:]))
    return cost


def _transition(prev, cur, profile) -> float:
    cost = _intrinsic(cur, profile)
    if prev is None:
        return cost
    pf = [p.fret for p in prev.positions if p.fret > 0]
    cf = [p.fret for p in cur.positions if p.fret > 0]
    pc = sum(pf) / len(pf) if pf else 0.0
    cc = sum(cf) / len(cf) if cf else 0.0
    cost += profile.center_move_weight * abs(cc - pc)
    prev_strings = {p.string_index for p in prev.positions}
    cur_strings = {p.string_index for p in cur.positions}
    cost -= profile.string_reuse_bonus * len(prev_strings & cur_strings)
    return cost


def optimize_with_anchors(
    events: Iterable[NoteEvent],
    tuning: Tuning,
    anchors: Iterable[FingeringAnchor],
    profile: str = "original_like",
    onset_tolerance: float = 0.035,
    max_candidates_per_group: int = 256,
) -> list[TabNote]:
    selected_profile = get_profile(profile)
    groups = group_simultaneous_events(events, onset_tolerance=onset_tolerance)
    if not groups:
        return []

    by_group: dict[int, list[FingeringAnchor]] = {}
    for anchor in anchors:
        validate_anchor(anchor, tuning)
        by_group.setdefault(anchor.chord_index, []).append(anchor)

    candidates = []
    for idx, group in enumerate(groups):
        voicings = possible_voicings(
            group,
            tuning,
            max_fret_span=selected_profile.max_fret_span,
            max_candidates=max_candidates_per_group,
            profile=selected_profile,
        )
        required = by_group.get(idx, [])
        if required:
            def matches(voicing) -> bool:
                assignments = {
                    (event.pitch, pos.string_index, pos.fret)
                    for event, pos in zip(group.events, voicing.positions)
                }
                return all(
                    (a.pitch, a.string_index, a.fret) in assignments
                    for a in required
                )
            voicings = [v for v in voicings if matches(v)]
        if not voicings:
            raise ValueError(f"No playable voicing remains for chord {idx} after applying corrections")
        candidates.append(voicings)

    dp = [{v: (_transition(None, v, selected_profile), None) for v in candidates[0]}]
    for idx in range(1, len(groups)):
        layer = {}
        for cur in candidates[idx]:
            best_cost = float("inf")
            best_prev = None
            for prev, (prev_cost, _) in dp[idx - 1].items():
                cost = prev_cost + _transition(prev, cur, selected_profile)
                if cost < best_cost:
                    best_cost, best_prev = cost, prev
            layer[cur] = (best_cost, best_prev)
        dp.append(layer)

    last = min(dp[-1], key=lambda v: dp[-1][v][0])
    chosen = [last]
    for idx in range(len(dp) - 1, 0, -1):
        chosen.append(dp[idx][chosen[-1]][1])
    chosen.reverse()

    result = []
    for chord_index, (group, voicing) in enumerate(zip(groups, chosen)):
        for event, position in zip(group.events, voicing.positions):
            result.append(
                TabNote(
                    event.pitch, event.start, event.duration,
                    position.string_index, position.fret,
                    event.confidence, chord_index,
                )
            )
    return sorted(result, key=lambda n: (n.start, n.string_index, n.pitch))


def build_correction_record(
    job_id: str,
    old: TabNote,
    anchor: FingeringAnchor,
    tuning: Tuning,
    profile: str,
) -> CorrectionRecord:
    return CorrectionRecord(
        job_id=job_id,
        chord_index=old.chord_index,
        pitch=old.pitch,
        old_string_index=old.string_index,
        old_fret=old.fret,
        new_string_index=anchor.string_index,
        new_fret=anchor.fret,
        tuning_name=tuning.name,
        profile=profile,
        capo=tuning.capo,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
