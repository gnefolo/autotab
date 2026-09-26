import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from music_engine.engine import NoteEvent, get_tuning
from music_engine.ensemble_validation import build_disagreement_aware_ensemble


class EnsembleValidationTests(unittest.TestCase):
    def test_confirmed_notes_are_kept(self):
        tuning = get_tuning("guitar_standard")
        primary = [NoteEvent(60, 0.0, 0.3, confidence=0.8)]
        secondary = [NoteEvent(60, 0.02, 0.28, confidence=0.7)]
        review = build_disagreement_aware_ensemble(primary, secondary, tuning)
        self.assertEqual(review.confirmed, 1)
        self.assertEqual(review.keep, 1)
        self.assertEqual(review.safe_note_count, 1)
        self.assertEqual(review.safe_events[0].pitch, 60)

    def test_weak_primary_micro_note_is_not_kept(self):
        tuning = get_tuning("guitar_standard")
        primary = [NoteEvent(61, 0.0, 0.02, confidence=0.25)]
        secondary = []
        review = build_disagreement_aware_ensemble(primary, secondary, tuning)
        self.assertEqual(review.confirmed, 0)
        self.assertEqual(review.primary_only, 1)
        self.assertEqual(review.safe_note_count, 0)
        self.assertEqual(review.decisions[0].decision, "reject")

    def test_strong_primary_playable_note_can_survive_without_secondary(self):
        tuning = get_tuning("guitar_standard")
        primary = [
            NoteEvent(64, 0.0, 0.35, confidence=0.95),
            NoteEvent(67, 0.4, 0.30, confidence=0.95),
        ]
        secondary = []
        review = build_disagreement_aware_ensemble(primary, secondary, tuning)
        self.assertGreaterEqual(review.keep, 1)
        self.assertGreaterEqual(review.safe_note_count, 1)

    def test_secondary_only_recovery_is_conservative(self):
        tuning = get_tuning("guitar_standard")
        primary = [NoteEvent(60, 0.0, 0.30, confidence=0.9)]
        secondary = [
            NoteEvent(60, 0.0, 0.30, confidence=0.9),
            NoteEvent(72, 1.0, 0.04, confidence=0.35),
        ]
        review = build_disagreement_aware_ensemble(primary, secondary, tuning)
        secondary_decisions = [d for d in review.decisions if d.origin == "secondary_only"]
        self.assertEqual(len(secondary_decisions), 1)
        self.assertNotEqual(secondary_decisions[0].decision, "keep")

    def test_secondary_only_is_never_auto_kept(self):
        tuning = get_tuning("guitar_standard")
        primary = []
        secondary = [
            NoteEvent(64, 0.0, 0.30, confidence=0.99),
            NoteEvent(67, 0.4, 0.30, confidence=0.99),
            NoteEvent(69, 0.8, 0.30, confidence=0.99),
        ]
        review = build_disagreement_aware_ensemble(primary, secondary, tuning)
        self.assertEqual(review.safe_note_count, 0)
        self.assertEqual(review.keep, 0)
        self.assertTrue(all(d.decision in {"review", "reject"} for d in review.decisions))

    def test_low_context_primary_only_does_not_enter_safe_set(self):
        tuning = get_tuning("guitar_standard")
        primary = [
            NoteEvent(64, 0.0, 0.05, confidence=0.84),
            NoteEvent(72, 4.0, 0.05, confidence=0.84),
        ]
        review = build_disagreement_aware_ensemble(primary, [], tuning)
        self.assertEqual(review.safe_note_count, 0)
        self.assertEqual(review.keep, 0)

    def test_out_of_range_primary_note_is_penalized(self):
        tuning = get_tuning("guitar_standard")
        primary = [NoteEvent(30, 0.0, 0.20, confidence=0.5)]
        secondary = []
        review = build_disagreement_aware_ensemble(primary, secondary, tuning)
        self.assertEqual(review.safe_note_count, 0)
        self.assertIn("outside_selected_tuning", review.decisions[0].reasons)


if __name__ == "__main__":
    unittest.main()
