import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from music_engine.engine import NoteEvent
from music_engine.refinement import replace_events_in_window


class RefinementTests(unittest.TestCase):
    def test_replaces_only_events_inside_window(self):
        existing = [
            NoteEvent(60, 0.0, 0.2),
            NoteEvent(62, 1.0, 0.2),
            NoteEvent(64, 2.0, 0.2),
            NoteEvent(65, 3.0, 0.2),
        ]
        replacement = [
            NoteEvent(63, 1.1, 0.2),
            NoteEvent(66, 2.1, 0.2),
        ]
        result = replace_events_in_window(existing, replacement, 1.0, 3.0)
        self.assertEqual([n.pitch for n in result], [60, 63, 66, 65])

    def test_outside_replacement_events_are_ignored(self):
        existing = [NoteEvent(60, 0.0, 0.2)]
        replacement = [
            NoteEvent(61, 0.5, 0.2),
            NoteEvent(62, 1.5, 0.2),
        ]
        result = replace_events_in_window(existing, replacement, 1.0, 2.0)
        self.assertEqual([n.pitch for n in result], [60, 62])

    def test_invalid_window_rejected(self):
        with self.assertRaises(ValueError):
            replace_events_in_window([], [], 2.0, 1.0)


if __name__ == "__main__":
    unittest.main()
