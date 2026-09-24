import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from audio_pipeline.source_selection import select_guitar_source
from music_engine.engine import NoteEvent


class SourceSelectionTests(unittest.TestCase):
    def test_prefers_stable_candidate_over_noisy_dense_candidate(self):
        stable = [
            NoteEvent(60, 0.0, 0.30, confidence=0.92),
            NoteEvent(62, 0.5, 0.30, confidence=0.91),
            NoteEvent(64, 1.0, 0.30, confidence=0.90),
            NoteEvent(65, 1.5, 0.30, confidence=0.91),
        ]
        noisy = [
            NoteEvent(60 + (i % 5), i * 0.05, 0.03, confidence=0.58)
            for i in range(40)
        ]
        result = select_guitar_source({"guitar": stable, "guitar_alt": noisy})
        self.assertEqual(result.selected_source, "guitar")

    def test_dedicated_guitar_wins_deterministic_tie(self):
        a = [
            NoteEvent(60, 0.0, 0.25, confidence=0.9),
            NoteEvent(62, 0.5, 0.25, confidence=0.9),
        ]
        b = [
            NoteEvent(60, 0.0, 0.25, confidence=0.9),
            NoteEvent(62, 0.5, 0.25, confidence=0.9),
        ]
        result = select_guitar_source({"guitar": a, "guitar_alt": b})
        self.assertEqual(result.selected_source, "guitar")

    def test_empty_candidate_does_not_win(self):
        usable = [
            NoteEvent(60, 0.0, 0.25, confidence=0.8),
            NoteEvent(64, 0.5, 0.25, confidence=0.82),
        ]
        result = select_guitar_source({"guitar": [], "guitar_alt": usable})
        self.assertEqual(result.selected_source, "guitar_alt")


if __name__ == "__main__":
    unittest.main()
