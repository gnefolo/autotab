import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from audio_pipeline.second_opinion import compare_transcriptions
from music_engine.engine import NoteEvent


class SecondOpinionTests(unittest.TestCase):
    def test_exact_agreement_scores_one(self):
        a = [
            NoteEvent(60, 0.0, 0.4),
            NoteEvent(64, 0.5, 0.4),
        ]
        result = compare_transcriptions(a, a)
        self.assertEqual(result.agreement_f1, 1.0)
        self.assertEqual(result.matched_notes, 2)
        self.assertEqual(len(result.disagreements), 0)

    def test_pitch_disagreement_is_reported(self):
        primary = [NoteEvent(60, 0.0, 0.4)]
        secondary = [NoteEvent(61, 0.0, 0.4)]
        result = compare_transcriptions(primary, secondary)
        self.assertEqual(result.matched_notes, 0)
        self.assertEqual(result.agreement_f1, 0.0)
        self.assertEqual(len(result.disagreements), 2)

    def test_onset_tolerance_matches_close_events(self):
        primary = [NoteEvent(60, 1.0, 0.4)]
        secondary = [NoteEvent(60, 1.05, 0.4)]
        result = compare_transcriptions(primary, secondary, onset_tolerance=0.08)
        self.assertEqual(result.matched_notes, 1)

    def test_onset_outside_tolerance_is_disagreement(self):
        primary = [NoteEvent(60, 1.0, 0.4)]
        secondary = [NoteEvent(60, 1.2, 0.4)]
        result = compare_transcriptions(primary, secondary, onset_tolerance=0.08)
        self.assertEqual(result.matched_notes, 0)


if __name__ == "__main__":
    unittest.main()
