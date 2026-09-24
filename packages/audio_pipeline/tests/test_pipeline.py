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




class MultiSeparator(Separator):
    def separate(self, audio_path, output_dir):
        output_dir.mkdir(parents=True, exist_ok=True)
        guitar = output_dir / "other.wav"
        bass = output_dir / "bass.wav"
        guitar.write_bytes(b"guitar")
        bass.write_bytes(b"bass")
        return {"other": guitar, "bass": bass}


class GuitarTranscriber(Transcriber):
    def transcribe(self, audio_path):
        return [
            NoteEvent(40, 0.0, 0.25, confidence=.95),
            NoteEvent(45, 0.25, 0.25, confidence=.94),
        ]


class BassTranscriber(Transcriber):
    def transcribe(self, audio_path):
        return [
            NoteEvent(28, 0.0, 0.5, confidence=.96),
            NoteEvent(33, 0.5, 0.5, confidence=.92),
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
            self.assertIn("guitar", result.tracks)
            self.assertEqual(result.selected_part, "guitar")

    def test_multi_instrument_tracks_are_transcribed_independently(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            source = td / "song.wav"
            source.write_bytes(b"audio")
            pipeline = AudioPipeline(
                MultiSeparator(),
                GuitarTranscriber(),
                bass_transcriber=BassTranscriber(),
            )
            result = pipeline.run(source, td / "work", "guitar_standard")
            self.assertEqual(set(result.tracks), {"guitar", "bass"})
            self.assertEqual(
                [row["pitch"] for row in result.tracks["guitar"]["notes"]],
                [40, 45],
            )
            self.assertEqual(
                [row["pitch"] for row in result.tracks["bass"]["notes"]],
                [28, 33],
            )
            self.assertEqual(result.tracks["guitar"]["stem"], "other")
            self.assertEqual(result.tracks["bass"]["stem"], "bass")


if __name__ == "__main__":
    unittest.main()
