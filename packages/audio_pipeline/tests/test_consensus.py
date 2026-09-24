import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from audio_pipeline.adapters import ConsensusTranscriber, Transcriber
from music_engine.engine import NoteEvent


class RunA(Transcriber):
    def transcribe(self, audio_path):
        return [
            NoteEvent(60, 0.00, 0.40, confidence=0.80),
            NoteEvent(64, 0.50, 0.30, confidence=0.82),
            NoteEvent(67, 1.00, 0.30, confidence=0.55),
        ]


class RunB(Transcriber):
    def transcribe(self, audio_path):
        return [
            NoteEvent(60, 0.02, 0.42, confidence=0.76),
            NoteEvent(64, 0.54, 0.28, confidence=0.79),
            NoteEvent(69, 1.50, 0.20, confidence=0.40),
        ]


class RunC(Transcriber):
    def transcribe(self, audio_path):
        return [
            NoteEvent(60, 0.01, 0.39, confidence=0.84),
            NoteEvent(64, 0.49, 0.31, confidence=0.81),
            NoteEvent(72, 2.00, 0.20, confidence=0.95),
        ]


class ConsensusTests(unittest.TestCase):
    def test_consensus_keeps_supported_notes_and_drops_weak_singletons(self):
        transcriber = ConsensusTranscriber(
            transcribers=(RunA(), RunB(), RunC()),
            onset_tolerance=0.07,
            minimum_support=2,
            high_confidence_singleton=0.90,
        )
        result = transcriber.transcribe(pathlib.Path("dummy.wav"))
        pitches = [n.pitch for n in result]
        self.assertIn(60, pitches)
        self.assertIn(64, pitches)
        self.assertNotIn(67, pitches)
        self.assertNotIn(69, pitches)
        self.assertIn(72, pitches)

    def test_consensus_uses_median_timing(self):
        transcriber = ConsensusTranscriber(
            transcribers=(RunA(), RunB(), RunC()),
            onset_tolerance=0.07,
            minimum_support=2,
        )
        result = transcriber.transcribe(pathlib.Path("dummy.wav"))
        note60 = next(n for n in result if n.pitch == 60)
        self.assertAlmostEqual(note60.start, 0.01, places=3)

    def test_consensus_confidence_rewards_support(self):
        transcriber = ConsensusTranscriber(
            transcribers=(RunA(), RunB(), RunC()),
            onset_tolerance=0.07,
            minimum_support=2,
        )
        result = transcriber.transcribe(pathlib.Path("dummy.wav"))
        note60 = next(n for n in result if n.pitch == 60)
        self.assertGreater(note60.confidence, 0.85)


if __name__ == "__main__":
    unittest.main()
