import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from music_engine.corrections import FingeringAnchor, optimize_with_anchors, validate_anchor
from music_engine.engine import NoteEvent, get_tuning


class CorrectionTests(unittest.TestCase):
    def test_valid_anchor_is_respected(self):
        tuning = get_tuning("guitar_standard")
        events = [NoteEvent(64, 0.0, 0.5)]
        anchor = FingeringAnchor(chord_index=0, pitch=64, string_index=4, fret=5)
        tab = optimize_with_anchors(events, tuning, [anchor])
        self.assertEqual(len(tab), 1)
        self.assertEqual((tab[0].string_index, tab[0].fret), (4, 5))

    def test_impossible_anchor_is_rejected(self):
        tuning = get_tuning("guitar_standard")
        anchor = FingeringAnchor(chord_index=0, pitch=64, string_index=0, fret=0)
        with self.assertRaises(ValueError):
            validate_anchor(anchor, tuning)

    def test_multiple_anchors_freeze_distant_chords(self):
        tuning = get_tuning("guitar_standard")
        events = [
            NoteEvent(40, 0.0, 0.2),
            NoteEvent(64, 0.5, 0.2),
            NoteEvent(45, 1.0, 0.2),
        ]
        anchors = [
            FingeringAnchor(0, 40, 0, 0),
            FingeringAnchor(1, 64, 4, 5),
            FingeringAnchor(2, 45, 1, 0),
        ]
        tab = optimize_with_anchors(events, tuning, anchors)
        shape = {(n.chord_index, n.pitch): (n.string_index, n.fret) for n in tab}
        self.assertEqual(shape[(0, 40)], (0, 0))
        self.assertEqual(shape[(1, 64)], (4, 5))
        self.assertEqual(shape[(2, 45)], (1, 0))


if __name__ == "__main__":
    unittest.main()
