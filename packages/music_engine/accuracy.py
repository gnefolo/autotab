from __future__ import annotations

from dataclasses import asdict, dataclass
from math import inf
from typing import Iterable

from .engine import NoteEvent


@dataclass(frozen=True)
class NoteMatch:
    reference_index: int
    prediction_index: int
    pitch: int
    onset_error: float
    duration_error: float


@dataclass(frozen=True)
class AccuracyMetrics:
    reference_notes: int
    predicted_notes: int
    matched_notes: int
    precision: float
    recall: float
    f1: float
    onset_mae_ms: float | None
    duration_mae_ms: float | None
    false_positives: int
    false_negatives: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ConfidenceWindow:
    start: float
    end: float
    note_count: int
    mean_confidence: float
    low_confidence_notes: int
    score: float

    def to_dict(self) -> dict:
        return asdict(self)


def match_note_events(
    reference: Iterable[NoteEvent],
    prediction: Iterable[NoteEvent],
    onset_tolerance: float = 0.08,
) -> tuple[list[NoteMatch], list[int], list[int]]:
    refs = list(reference)
    preds = list(prediction)
    used_predictions: set[int] = set()
    matches: list[NoteMatch] = []

    for ri, ref in enumerate(refs):
        best_pi = None
        best_cost = inf
        for pi, pred in enumerate(preds):
            if pi in used_predictions or pred.pitch != ref.pitch:
                continue
            onset_error = abs(pred.start - ref.start)
            if onset_error > onset_tolerance:
                continue
            duration_error = abs(pred.duration - ref.duration)
            cost = onset_error + 0.15 * duration_error
            if cost < best_cost:
                best_cost = cost
                best_pi = pi

        if best_pi is not None:
            pred = preds[best_pi]
            used_predictions.add(best_pi)
            matches.append(
                NoteMatch(
                    reference_index=ri,
                    prediction_index=best_pi,
                    pitch=ref.pitch,
                    onset_error=abs(pred.start - ref.start),
                    duration_error=abs(pred.duration - ref.duration),
                )
            )

    matched_ref = {m.reference_index for m in matches}
    false_negative_indices = [i for i in range(len(refs)) if i not in matched_ref]
    false_positive_indices = [i for i in range(len(preds)) if i not in used_predictions]
    return matches, false_positive_indices, false_negative_indices


def evaluate_note_events(
    reference: Iterable[NoteEvent],
    prediction: Iterable[NoteEvent],
    onset_tolerance: float = 0.08,
) -> AccuracyMetrics:
    refs = list(reference)
    preds = list(prediction)
    matches, fp, fn = match_note_events(refs, preds, onset_tolerance=onset_tolerance)
    matched = len(matches)

    precision = matched / len(preds) if preds else (1.0 if not refs else 0.0)
    recall = matched / len(refs) if refs else (1.0 if not preds else 0.0)
    f1 = (
        2.0 * precision * recall / (precision + recall)
        if precision + recall > 0
        else 0.0
    )

    onset_mae = (
        sum(m.onset_error for m in matches) / matched * 1000.0
        if matched
        else None
    )
    duration_mae = (
        sum(m.duration_error for m in matches) / matched * 1000.0
        if matched
        else None
    )

    return AccuracyMetrics(
        reference_notes=len(refs),
        predicted_notes=len(preds),
        matched_notes=matched,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        onset_mae_ms=round(onset_mae, 2) if onset_mae is not None else None,
        duration_mae_ms=round(duration_mae, 2) if duration_mae is not None else None,
        false_positives=len(fp),
        false_negatives=len(fn),
    )


def confidence_windows(
    events: Iterable[NoteEvent],
    window_seconds: float = 2.0,
    low_threshold: float = 0.55,
) -> list[ConfidenceWindow]:
    rows = list(events)
    if not rows:
        return []
    end_time = max(e.start + e.duration for e in rows)
    windows: list[ConfidenceWindow] = []
    start = 0.0

    while start <= end_time + 1e-9:
        end = start + window_seconds
        local = [e for e in rows if start <= e.start < end]
        if local:
            mean_conf = sum(e.confidence for e in local) / len(local)
            low_count = sum(1 for e in local if e.confidence < low_threshold)
            density_penalty = min(0.22, max(0, len(local) - 16) * 0.008)
            low_ratio = low_count / len(local)
            score = max(
                0.0,
                min(1.0, mean_conf - 0.30 * low_ratio - density_penalty),
            )
            windows.append(
                ConfidenceWindow(
                    start=round(start, 3),
                    end=round(end, 3),
                    note_count=len(local),
                    mean_confidence=round(mean_conf, 4),
                    low_confidence_notes=low_count,
                    score=round(score, 4),
                )
            )
        start = end

    return windows


def confidence_summary(
    events: Iterable[NoteEvent],
    window_seconds: float = 2.0,
    low_threshold: float = 0.55,
) -> dict:
    rows = list(events)
    windows = confidence_windows(
        rows,
        window_seconds=window_seconds,
        low_threshold=low_threshold,
    )
    if not rows:
        return {
            "note_count": 0,
            "mean_confidence": 0.0,
            "low_confidence_notes": 0,
            "low_confidence_ratio": 0.0,
            "window_seconds": window_seconds,
            "windows": [],
            "weak_windows": [],
        }

    mean_conf = sum(e.confidence for e in rows) / len(rows)
    low_count = sum(1 for e in rows if e.confidence < low_threshold)
    weak = [w.to_dict() for w in windows if w.score < 0.60]

    return {
        "note_count": len(rows),
        "mean_confidence": round(mean_conf, 4),
        "low_confidence_notes": low_count,
        "low_confidence_ratio": round(low_count / len(rows), 4),
        "window_seconds": window_seconds,
        "windows": [w.to_dict() for w in windows],
        "weak_windows": weak,
    }
