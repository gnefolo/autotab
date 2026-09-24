#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))

from music_engine.accuracy import evaluate_note_events
from music_engine.engine import NoteEvent


def load_events(path: pathlib.Path) -> list[NoteEvent]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data["notes"] if isinstance(data, dict) and "notes" in data else data
    return [
        NoteEvent(
            pitch=int(row["pitch"]),
            start=float(row["start"]),
            duration=float(row["duration"]),
            velocity=int(row.get("velocity", 90)),
            confidence=float(row.get("confidence", 1.0)),
            pitch_bends=tuple(float(x) for x in row.get("pitch_bends", [])),
        )
        for row in rows
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare AutoTab note events against ground-truth note events."
    )
    parser.add_argument("reference", type=pathlib.Path)
    parser.add_argument("prediction", type=pathlib.Path)
    parser.add_argument("--onset-tolerance", type=float, default=0.08)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    reference = load_events(args.reference)
    prediction = load_events(args.prediction)
    metrics = evaluate_note_events(
        reference,
        prediction,
        onset_tolerance=args.onset_tolerance,
    ).to_dict()

    if args.as_json:
        print(json.dumps(metrics, indent=2))
    else:
        print(f"Reference notes : {metrics['reference_notes']}")
        print(f"Predicted notes : {metrics['predicted_notes']}")
        print(f"Matched notes   : {metrics['matched_notes']}")
        print(f"Precision       : {metrics['precision']:.4f}")
        print(f"Recall          : {metrics['recall']:.4f}")
        print(f"F1              : {metrics['f1']:.4f}")
        print(f"Onset MAE       : {metrics['onset_mae_ms']} ms")
        print(f"Duration MAE    : {metrics['duration_mae_ms']} ms")
        print(f"False positives : {metrics['false_positives']}")
        print(f"False negatives : {metrics['false_negatives']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
