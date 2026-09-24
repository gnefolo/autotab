import pathlib
import sys
import unittest
from xml.etree import ElementTree as ET

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from music_engine.engine import TabNote, get_tuning
from music_engine.rhythm import TimeSignature, estimate_bpm, quantize_tab_notes
from music_engine.musicxml import export_musicxml


class RhythmEngineTests(unittest.TestCase):
    def test_quantizes_quarter_notes_at_120_bpm(self):
        notes = [
            TabNote(60, 0.00, 0.48, 2, 10, 0.9, 0),
            TabNote(62, 0.51, 0.47, 2, 12, 0.9, 1),
            TabNote(64, 1.01, 0.49, 1, 5, 0.9, 2),
        ]
        cfg, q = quantize_tab_notes(notes, bpm=120.0)
        self.assertEqual(cfg.divisions, 480)
        self.assertEqual([n.onset_tick for n in q], [0, 480, 960])
        self.assertEqual([n.duration_ticks for n in q], [480, 480, 480])

    def test_chord_members_share_quantized_onset(self):
        notes = [
            TabNote(50, 1.000, 0.5, 2, 0, 0.9, 4),
            TabNote(57, 1.018, 0.5, 3, 2, 0.9, 4),
            TabNote(62, 1.027, 0.5, 4, 3, 0.9, 4),
        ]
        _, q = quantize_tab_notes(notes, bpm=120.0)
        self.assertEqual(len({n.onset_tick for n in q}), 1)

    def test_estimate_bpm_from_regular_onsets(self):
        notes = [TabNote(60, i * 0.5, 0.2, 0, 0, 1.0, i) for i in range(6)]
        self.assertAlmostEqual(estimate_bpm(notes), 120.0, places=1)

    def test_musicxml_contains_standard_and_tab_staves(self):
        notes = [
            TabNote(38, 0.0, 0.5, 0, 0, 1.0, 0),
            TabNote(45, 0.0, 0.5, 1, 0, 1.0, 0),
            TabNote(50, 0.0, 0.5, 2, 0, 1.0, 0),
        ]
        cfg, q = quantize_tab_notes(notes, bpm=120.0, time_signature=TimeSignature(4, 4))
        xml = export_musicxml(q, cfg, get_tuning("guitar_drop_d"), title="Drop D Test")
        root = ET.fromstring(xml.split("?>", 1)[1])
        self.assertEqual(root.tag, "score-partwise")
        self.assertIsNotNone(root.find(".//clef[@number='2']/sign[.='TAB']"))
        self.assertEqual(root.findtext(".//staff-details[@number='2']/staff-lines"), "6")
        strings = [x.text for x in root.findall(".//technical/string")]
        frets = [x.text for x in root.findall(".//technical/fret")]
        self.assertEqual(strings[:3], ["6", "5", "4"])
        self.assertEqual(frets[:3], ["0", "0", "0"])

    def test_note_crossing_barline_is_tied(self):
        note = TabNote(64, 1.75, 0.75, 5, 0, 1.0, 0)
        cfg, q = quantize_tab_notes([note], bpm=120.0)
        xml = export_musicxml(q, cfg, get_tuning("guitar_standard"))
        self.assertIn('tie type="start"', xml)
        self.assertIn('tie type="stop"', xml)


if __name__ == "__main__":
    unittest.main()
