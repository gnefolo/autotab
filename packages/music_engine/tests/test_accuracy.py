import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from music_engine.accuracy import confidence_summary, evaluate_note_events
from music_engine.engine import NoteEvent


class AccuracyTests(unittest.TestCase):
    def test_perfect_transcription_scores_one(self):
        reference = [
            NoteEvent(60, 0.0, 0.5, confidence=1.0),
            NoteEvent(64, 0.5, 0.5, confidence=1.0),
        ]
        metrics = evaluate_note_events(reference, reference)
        self.assertEqual(metrics.precision, 1.0)
        self.assertEqual(metrics.recall, 1.0)
        self.assertEqual(metrics.f1, 1.0)
        self.assertEqual(metrics.false_positives, 0)
        self.assertEqual(metrics.false_negatives, 0)

    def test_wrong_pitch_counts_as_fp_and_fn(self):
        reference = [NoteEvent(60, 0.0, 0.5)]
        prediction = [NoteEvent(61, 0.0, 0.5)]
        metrics = evaluate_note_events(reference, prediction)
        self.assertEqual(metrics.f1, 0.0)
        self.assertEqual(metrics.false_positives, 1)
        self.assertEqual(metrics.false_negatives, 1)

    def test_onset_tolerance_is_enforced(self):
        reference = [NoteEvent(60, 1.0, 0.5)]
        prediction = [NoteEvent(60, 1.06, 0.5)]
        permissive = evaluate_note_events(reference, prediction, onset_tolerance=0.08)
        strict = evaluate_note_events(reference, prediction, onset_tolerance=0.03)
        self.assertEqual(permissive.matched_notes, 1)
        self.assertEqual(strict.matched_notes, 0)

    def test_confidence_summary_finds_weak_window(self):
        events = [
            NoteEvent(60, 0.1, 0.2, confidence=0.92),
            NoteEvent(62, 0.6, 0.2, confidence=0.88),
            NoteEvent(64, 2.1, 0.2, confidence=0.31),
            NoteEvent(65, 2.4, 0.2, confidence=0.40),
        ]
        summary = confidence_summary(events, window_seconds=2.0)
        self.assertEqual(summary["note_count"], 4)
        self.assertEqual(summary["low_confidence_notes"], 2)
        self.assertEqual(len(summary["weak_windows"]), 1)
        self.assertEqual(summary["weak_windows"][0]["start"], 2.0)


if __name__ == "__main__":
    unittest.main()
