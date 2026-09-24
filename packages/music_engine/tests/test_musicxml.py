import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from music_engine.engine import Tuning
from music_engine.musicxml import export_musicxml, export_drum_musicxml
from music_engine.rhythm import QuantizedTabNote, RhythmConfig, TimeSignature


class MusicXMLTests(unittest.TestCase):
    def test_standard_only_score_has_no_tab_staff(self):
        notes = [
            QuantizedTabNote(
                pitch=60,
                onset_tick=0,
                duration_ticks=480,
                string_index=0,
                fret=0,
                confidence=0.9,
                chord_index=0,
                original_start=0.0,
                original_duration=0.5,
            )
        ]
        cfg = RhythmConfig(
            bpm=120.0,
            time_signature=TimeSignature(4, 4),
            divisions=480,
            subdivision=4,
        )
        xml = export_musicxml(
            notes,
            cfg,
            Tuning("Piano", (21,)),
            title="Piano Test",
            standard_only=True,
        )
        self.assertIn("<sign>G</sign>", xml)
        self.assertNotIn("<sign>TAB</sign>", xml)
        self.assertNotIn("<technical>", xml)
        self.assertIn("<part-name>Piano</part-name>", xml)


    def test_drum_score_uses_percussion_clef(self):
        cfg = RhythmConfig(
            bpm=120.0,
            time_signature=TimeSignature(4, 4),
            divisions=480,
            subdivision=4,
        )
        xml = export_drum_musicxml(
            [
                {"drum": "kick", "start": 0.0, "confidence": 0.95, "midi_note": 36},
                {"drum": "hihat", "start": 0.5, "confidence": 0.90, "midi_note": 42},
            ],
            cfg,
            title="Drum Test",
        )
        self.assertIn("<sign>percussion</sign>", xml)
        self.assertIn("<midi-unpitched>36</midi-unpitched>", xml)
        self.assertIn("<notehead>x</notehead>", xml)
        self.assertNotIn("<sign>TAB</sign>", xml)


if __name__ == "__main__":
    unittest.main()
