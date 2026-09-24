import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from music_engine.engine import NoteEvent
from music_engine.riff_consistency import harmonize_repeated_riffs


class RiffConsistencyTests(unittest.TestCase):
    def test_low_confidence_outlier_is_corrected_when_two_repeats_agree(self):
        base = [
            (60, 0.00, 0.20, 0.95),
            (62, 0.25, 0.20, 0.95),
            (64, 0.50, 0.20, 0.95),
            (65, 0.75, 0.20, 0.95),
            (67, 1.00, 0.20, 0.95),
        ]
        events = []
        for offset in (0.0, 2.0, 4.0):
            for i, (pitch, start, duration, confidence) in enumerate(base):
                p = pitch
                c = confidence
                if offset == 4.0 and i == 2:
                    p = 63
                    c = 0.50
                events.append(NoteEvent(p, start + offset, duration, confidence=c))

        result = harmonize_repeated_riffs(events)
        pitches = [e.pitch for e in result.events]
        self.assertEqual(pitches[12], 64)
        self.assertEqual(len(result.corrections), 1)
        self.assertEqual(result.corrections[0].old_pitch, 63)
        self.assertEqual(result.corrections[0].new_pitch, 64)

    def test_high_confidence_variation_is_preserved(self):
        events = []
        for offset, third_pitch, conf in (
            (0.0, 64, 0.95),
            (2.0, 64, 0.95),
            (4.0, 65, 0.92),
        ):
            phrase = [60, 62, third_pitch, 65, 67]
            for i, pitch in enumerate(phrase):
                events.append(NoteEvent(pitch, offset + i * 0.25, 0.20, confidence=conf))

        result = harmonize_repeated_riffs(events)
        self.assertIn(65, [e.pitch for e in result.events[10:15]])
        self.assertEqual(len(result.corrections), 0)

    def test_large_pitch_variation_is_preserved(self):
        events = []
        for offset, third_pitch, conf in (
            (0.0, 64, 0.95),
            (2.0, 64, 0.95),
            (4.0, 69, 0.40),
        ):
            phrase = [60, 62, third_pitch, 65, 67]
            for i, pitch in enumerate(phrase):
                events.append(NoteEvent(pitch, offset + i * 0.25, 0.20, confidence=conf))

        result = harmonize_repeated_riffs(events)
        self.assertIn(69, [e.pitch for e in result.events[10:15]])
        self.assertEqual(len(result.corrections), 0)


if __name__ == "__main__":
    unittest.main()
