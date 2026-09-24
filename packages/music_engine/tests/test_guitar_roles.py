import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from music_engine.engine import NoteEvent
from music_engine.guitar_roles import split_guitar_roles


class GuitarRoleTests(unittest.TestCase):
    def test_polyphonic_chords_go_to_rhythm_and_high_melody_to_lead(self):
        events = [
            NoteEvent(40, 0.0, 0.5, confidence=.95),
            NoteEvent(47, 0.0, 0.5, confidence=.95),
            NoteEvent(52, 0.0, 0.5, confidence=.95),
            NoteEvent(64, 0.6, 0.45, confidence=.9),
            NoteEvent(67, 1.0, 0.45, confidence=.9),
            NoteEvent(69, 1.4, 0.45, confidence=.9),
            NoteEvent(71, 1.8, 0.45, confidence=.9),
        ]
        split = split_guitar_roles(events)
        rhythm_pitches = {e.pitch for e in split.rhythm}
        lead_pitches = {e.pitch for e in split.lead}
        self.assertTrue({40, 47, 52}.issubset(rhythm_pitches))
        self.assertTrue({64, 67, 69, 71}.intersection(lead_pitches))
        self.assertGreater(split.confidence, 0.2)
        self.assertTrue(any("not source-separated" in line for line in split.explanation))

    def test_empty_input_is_safe(self):
        split = split_guitar_roles([])
        self.assertEqual(split.rhythm, ())
        self.assertEqual(split.lead, ())
        self.assertEqual(split.confidence, 0.0)


if __name__ == "__main__":
    unittest.main()
