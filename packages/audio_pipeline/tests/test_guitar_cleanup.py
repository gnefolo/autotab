import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from audio_pipeline.adapters import GuitarCleanupTranscriber, Transcriber
from music_engine.engine import NoteEvent


class DirtyTranscriber(Transcriber):
    def transcribe(self, audio_path):
        return [
            NoteEvent(60, 0.00, 0.40, confidence=0.90),
            NoteEvent(60, 0.03, 0.38, confidence=0.70),
            NoteEvent(61, 0.50, 0.02, confidence=0.40),
            NoteEvent(40, 1.00, 0.30, confidence=0.95),
            NoteEvent(45, 1.00, 0.30, confidence=0.94),
            NoteEvent(50, 1.00, 0.30, confidence=0.93),
            NoteEvent(55, 1.00, 0.30, confidence=0.92),
            NoteEvent(59, 1.00, 0.30, confidence=0.91),
            NoteEvent(64, 1.00, 0.30, confidence=0.90),
            NoteEvent(67, 1.00, 0.30, confidence=0.20),
        ]


class GuitarCleanupTests(unittest.TestCase):
    def test_cleanup_removes_duplicate_retrigger(self):
        result = GuitarCleanupTranscriber(DirtyTranscriber()).transcribe(pathlib.Path("x.wav"))
        self.assertEqual(sum(1 for n in result if n.pitch == 60), 1)

    def test_cleanup_removes_short_low_confidence_note(self):
        result = GuitarCleanupTranscriber(DirtyTranscriber()).transcribe(pathlib.Path("x.wav"))
        self.assertNotIn(61, [n.pitch for n in result])

    def test_cleanup_caps_impossible_polyphony_to_six(self):
        result = GuitarCleanupTranscriber(DirtyTranscriber()).transcribe(pathlib.Path("x.wav"))
        cluster = [n for n in result if abs(n.start - 1.0) <= 0.035]
        self.assertEqual(len(cluster), 6)
        self.assertNotIn(67, [n.pitch for n in cluster])


if __name__ == "__main__":
    unittest.main()
