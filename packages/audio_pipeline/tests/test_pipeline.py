import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from audio_pipeline.adapters import Separator, Transcriber
from audio_pipeline.pipeline import AudioPipeline
from music_engine.engine import NoteEvent


class FakeSeparator(Separator):
    def separate(self, audio_path, output_dir):
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / "guitar.wav"
        target.write_bytes(b"fake")
        return {"guitar": target}


class FakeTranscriber(Transcriber):
    def transcribe(self, audio_path):
        return [
            NoteEvent(40, 0.0, 0.25, confidence=.95),
            NoteEvent(45, 0.25, 0.25, confidence=.94),
            NoteEvent(47, 0.50, 0.25, confidence=.91),
        ]


class PipelineTests(unittest.TestCase):
    def test_end_to_end_contract(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            source = td / "song.wav"
            source.write_bytes(b"audio")
            pipeline = AudioPipeline(FakeSeparator(), FakeTranscriber())
            result = pipeline.run(source, td / "work", "guitar_standard")
            self.assertEqual(len(result.notes), 3)
            self.assertEqual(len(result.tab), 3)
            self.assertTrue((td / "work" / "result.json").exists())
            self.assertTrue((td / "work" / "score.musicxml").exists())
            self.assertEqual(result.tab[0]["pitch"], 40)
            self.assertIn("bpm", result.rhythm)
            self.assertEqual(result.musicxml, str(td / "work" / "score.musicxml"))


if __name__ == "__main__":
    unittest.main()
