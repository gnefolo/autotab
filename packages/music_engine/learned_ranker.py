from __future__ import annotations

from dataclasses import asdict, dataclass
from math import exp
from typing import Iterable

from .engine import NoteGroup, Tuning, Voicing


FEATURE_NAMES = (
    "bias",
    "fret_norm",
    "string_norm",
    "open_string",
    "high_fret",
    "center_string_distance",
    "pitch_class_norm",
    "capo_norm",
)


@dataclass
class LearnedRankerModel:
    weights: list[float]
    examples: int
    epochs: int
    learning_rate: float
    l2: float
    version: str = "pairwise-linear-v1"

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["feature_names"] = list(FEATURE_NAMES)
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "LearnedRankerModel":
        return cls(
            weights=[float(x) for x in payload["weights"]],
            examples=int(payload.get("examples", 0)),
            epochs=int(payload.get("epochs", 0)),
            learning_rate=float(payload.get("learning_rate", 0.05)),
            l2=float(payload.get("l2", 0.001)),
            version=str(payload.get("version", "pairwise-linear-v1")),
        )


def position_features(
    pitch: int,
    string_index: int,
    fret: int,
    string_count: int,
    capo: int,
) -> list[float]:
    string_den = max(1, string_count - 1)
    string_norm = string_index / string_den
    return [
        1.0,
        min(fret, 24) / 24.0,
        string_norm,
        1.0 if fret == 0 else 0.0,
        max(0, fret - 12) / 12.0,
        abs(string_norm - 0.5),
        (pitch % 12) / 11.0,
        capo / 12.0,
    ]


def _dot(a: Iterable[float], b: Iterable[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _sigmoid(value: float) -> float:
    value = max(-30.0, min(30.0, value))
    return 1.0 / (1.0 + exp(-value))


def correction_pair(record: dict, string_count: int = 6) -> tuple[list[float], list[float]]:
    pitch = int(record["pitch"])
    capo = int(record.get("capo", 0))
    positive = position_features(
        pitch,
        int(record["new_string_index"]),
        int(record["new_fret"]),
        string_count,
        capo,
    )
    negative = position_features(
        pitch,
        int(record["old_string_index"]),
        int(record["old_fret"]),
        string_count,
        capo,
    )
    return positive, negative


def train_pairwise_ranker(
    records: Iterable[dict],
    epochs: int = 120,
    learning_rate: float = 0.08,
    l2: float = 0.002,
) -> LearnedRankerModel:
    pairs = []
    for record in records:
        if (
            record.get("old_string_index") == record.get("new_string_index")
            and record.get("old_fret") == record.get("new_fret")
        ):
            continue
        max_string = max(
            int(record.get("old_string_index", 0)),
            int(record.get("new_string_index", 0)),
        )
        string_count = max(6, max_string + 1)
        pairs.append(correction_pair(record, string_count))

    weights = [0.0] * len(FEATURE_NAMES)
    if not pairs:
        return LearnedRankerModel(weights, 0, epochs, learning_rate, l2)

    for _ in range(epochs):
        for positive, negative in pairs:
            diff = [p - n for p, n in zip(positive, negative)]
            probability = _sigmoid(_dot(weights, diff))
            gradient_scale = 1.0 - probability
            for idx, value in enumerate(diff):
                weights[idx] += learning_rate * (
                    gradient_scale * value - l2 * weights[idx]
                )

    return LearnedRankerModel(weights, len(pairs), epochs, learning_rate, l2)


def position_preference_score(
    model: LearnedRankerModel,
    pitch: int,
    string_index: int,
    fret: int,
    tuning: Tuning,
) -> float:
    features = position_features(
        pitch,
        string_index,
        fret,
        len(tuning.open_pitches),
        tuning.capo,
    )
    return _dot(model.weights, features)


def voicing_learned_cost(
    model: LearnedRankerModel,
    group: NoteGroup,
    voicing: Voicing,
    tuning: Tuning,
    strength: float = 0.55,
) -> float:
    if model.examples <= 0:
        return 0.0
    scores = [
        position_preference_score(
            model,
            event.pitch,
            position.string_index,
            position.fret,
            tuning,
        )
        for event, position in zip(group.events, voicing.positions)
    ]
    return -strength * (sum(scores) / max(1, len(scores)))


def optimize_polyphonic_fingering_learned(
    events,
    tuning: Tuning,
    model: LearnedRankerModel,
    profile: str = "original_like",
    strength: float = 0.55,
    onset_tolerance: float = 0.035,
    max_candidates_per_group: int = 256,
):
    from .engine import TabNote, get_profile, group_simultaneous_events, possible_voicings

    selected_profile = get_profile(profile)
    groups = group_simultaneous_events(events, onset_tolerance=onset_tolerance)
    if not groups:
        return []

    candidates = []
    for group in groups:
        voicings = possible_voicings(
            group,
            tuning,
            max_fret_span=selected_profile.max_fret_span,
            max_candidates=max_candidates_per_group,
            profile=selected_profile,
        )
        if not voicings:
            raise ValueError("No playable voicing for learned-ranker optimization")
        candidates.append(voicings)

    def heuristic_intrinsic(voicing):
        fretted = [p.fret for p in voicing.positions if p.fret > 0]
        span = max(fretted) - min(fretted) if len(fretted) > 1 else 0
        center = sum(fretted) / len(fretted) if fretted else 0.0
        strings = sorted(p.string_index for p in voicing.positions)
        cost = selected_profile.fret_span_weight * span
        cost += selected_profile.position_weight * center
        cost -= selected_profile.open_string_bonus * sum(
            1 for p in voicing.positions if p.fret == 0
        )
        if len(strings) > 1:
            cost += selected_profile.string_gap_weight * sum(
                max(0, b - a - 1) for a, b in zip(strings, strings[1:])
            )
        return cost

    def total_cost(group, previous, current):
        cost = heuristic_intrinsic(current)
        cost += voicing_learned_cost(
            model, group, current, tuning, strength=strength
        )
        if previous is not None:
            pf = [p.fret for p in previous.positions if p.fret > 0]
            cf = [p.fret for p in current.positions if p.fret > 0]
            pc = sum(pf) / len(pf) if pf else 0.0
            cc = sum(cf) / len(cf) if cf else 0.0
            cost += selected_profile.center_move_weight * abs(cc - pc)
            prev_strings = {p.string_index for p in previous.positions}
            cur_strings = {p.string_index for p in current.positions}
            cost -= selected_profile.string_reuse_bonus * len(
                prev_strings & cur_strings
            )
        return cost

    dp = [
        {
            voicing: (total_cost(groups[0], None, voicing), None)
            for voicing in candidates[0]
        }
    ]
    for idx in range(1, len(groups)):
        layer = {}
        for current in candidates[idx]:
            best_cost = float("inf")
            best_previous = None
            for previous, (previous_cost, _) in dp[idx - 1].items():
                candidate_cost = previous_cost + total_cost(
                    groups[idx], previous, current
                )
                if candidate_cost < best_cost:
                    best_cost = candidate_cost
                    best_previous = previous
            layer[current] = (best_cost, best_previous)
        dp.append(layer)

    last = min(dp[-1], key=lambda voicing: dp[-1][voicing][0])
    chosen = [last]
    for idx in range(len(dp) - 1, 0, -1):
        chosen.append(dp[idx][chosen[-1]][1])
    chosen.reverse()

    result = []
    for chord_index, (group, voicing) in enumerate(zip(groups, chosen)):
        for event, position in zip(group.events, voicing.positions):
            result.append(
                TabNote(
                    event.pitch,
                    event.start,
                    event.duration,
                    position.string_index,
                    position.fret,
                    event.confidence,
                    chord_index,
                )
            )
    return sorted(
        result, key=lambda note: (note.start, note.string_index, note.pitch)
    )
