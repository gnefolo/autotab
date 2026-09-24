import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from music_engine.engine import (
    NoteEvent,
    get_tuning,
    group_simultaneous_events,
    optimize_polyphonic_fingering,
    optimize_polyphonic_fingering_robust,
    possible_voicings,
)


class PolyphonicEngineTests(unittest.TestCase):
    def test_near_simultaneous_notes_become_one_group(self):
        events = [
            NoteEvent(50, 1.000, 0.5),
            NoteEvent(57, 1.012, 0.5),
            NoteEvent(62, 1.026, 0.5),
            NoteEvent(64, 1.100, 0.5),
        ]
        groups = group_simultaneous_events(events, onset_tolerance=0.035)
        self.assertEqual(len(groups), 2)
        self.assertEqual([e.pitch for e in groups[0].events], [50, 57, 62])

    def test_voicing_never_uses_same_string_twice(self):
        tuning = get_tuning("guitar_standard")
        group = group_simultaneous_events([
            NoteEvent(52, 0.0, 1.0),
            NoteEvent(59, 0.0, 1.0),
            NoteEvent(64, 0.0, 1.0),
        ])[0]
        voicings = possible_voicings(group, tuning)
        self.assertTrue(voicings)
        for voicing in voicings:
            strings = [p.string_index for p in voicing.positions]
            self.assertEqual(len(strings), len(set(strings)))

    def test_drop_d_power_chord_prefers_compact_shape(self):
        tuning = get_tuning("guitar_drop_d")
        events = [
            NoteEvent(38, 0.000, 0.8),
            NoteEvent(45, 0.006, 0.8),
            NoteEvent(50, 0.010, 0.8),
        ]
        tab = optimize_polyphonic_fingering(events, tuning)
        shape = {(n.string_index, n.fret) for n in tab}
        self.assertEqual(shape, {(0, 0), (1, 0), (2, 0)})
        self.assertEqual(len({n.chord_index for n in tab}), 1)

    def test_standard_and_drop_d_retab_same_pitches(self):
        events = [
            NoteEvent(50, 0.0, 0.5),
            NoteEvent(57, 0.0, 0.5),
            NoteEvent(62, 0.0, 0.5),
        ]
        drop = optimize_polyphonic_fingering(events, get_tuning("guitar_drop_d"))
        standard = optimize_polyphonic_fingering(events, get_tuning("guitar_standard"))
        self.assertEqual(sorted(n.pitch for n in drop), sorted(n.pitch for n in standard))
        self.assertNotEqual(
            {(n.string_index, n.fret) for n in drop},
            {(n.string_index, n.fret) for n in standard},
        )

    def test_robust_fingering_filters_note_below_tuning_range(self):
        tuning = get_tuning("guitar_eb")
        events = [
            NoteEvent(37, 0.0, 0.4, confidence=0.4),
            NoteEvent(53, 0.0, 0.4, confidence=0.9),
            NoteEvent(56, 0.0, 0.4, confidence=0.9),
        ]
        tab, diagnostics = optimize_polyphonic_fingering_robust(events, tuning)
        self.assertEqual(sorted(n.pitch for n in tab), [53, 56])
        self.assertEqual(diagnostics.input_notes, 3)
        self.assertEqual(len(diagnostics.filtered_out_of_range), 1)
        self.assertEqual(diagnostics.filtered_out_of_range[0][0], 37)

    def test_impossible_seven_note_chord_is_rejected_on_six_strings(self):
        tuning = get_tuning("guitar_standard")
        events = [NoteEvent(p, 0.0, 1.0) for p in [40, 45, 50, 55, 59, 64, 67]]
        with self.assertRaises(ValueError):
            optimize_polyphonic_fingering(events, tuning)


if __name__ == "__main__":
    unittest.main()
