import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from music_engine.engine import NoteEvent, get_tuning, optimize_fingering, possible_positions


class EngineTests(unittest.TestCase):
    def test_middle_e_has_multiple_positions(self):
        tuning = get_tuning("guitar_standard")
        positions = possible_positions(64, tuning)
        pairs = {(p.string_index, p.fret) for p in positions}
        self.assertIn((5, 0), pairs)
        self.assertIn((4, 5), pairs)
        self.assertIn((3, 9), pairs)

    def test_drop_d_exposes_low_d_open_string(self):
        drop_d = get_tuning("guitar_drop_d")
        standard = get_tuning("guitar_standard")
        self.assertIn((0, 0), {(p.string_index, p.fret) for p in possible_positions(38, drop_d)})
        self.assertNotIn((0, 0), {(p.string_index, p.fret) for p in possible_positions(38, standard)})

    def test_optimizer_returns_same_musical_pitches(self):
        tuning = get_tuning("guitar_drop_d")
        events = [
            NoteEvent(38, 0.0, 0.5),
            NoteEvent(45, 0.5, 0.5),
            NoteEvent(50, 1.0, 0.5),
            NoteEvent(52, 1.5, 0.5),
        ]
        tab = optimize_fingering(events, tuning)
        self.assertEqual([n.pitch for n in tab], [38, 45, 50, 52])
        self.assertEqual((tab[0].string_index, tab[0].fret), (0, 0))


if __name__ == "__main__":
    unittest.main()
