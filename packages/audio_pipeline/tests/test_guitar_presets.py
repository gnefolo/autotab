import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from audio_pipeline.adapters import GuitarCleanupTranscriber, build_guitar_transcriber


class GuitarPresetTests(unittest.TestCase):
    def test_all_presets_build_cleanup_transcribers(self):
        for mode in ("precise", "balanced", "sensitive"):
            transcriber = build_guitar_transcriber(mode)
            self.assertIsInstance(transcriber, GuitarCleanupTranscriber)
            self.assertIn(mode, transcriber.name)

    def test_precise_is_stricter_than_sensitive(self):
        precise = build_guitar_transcriber("precise")
        sensitive = build_guitar_transcriber("sensitive")
        self.assertGreater(precise.min_duration, sensitive.min_duration)
        self.assertGreater(
            precise.low_confidence_threshold,
            sensitive.low_confidence_threshold,
        )
        self.assertGreater(
            precise.base.high_confidence_singleton,
            sensitive.base.high_confidence_singleton,
        )

    def test_unknown_preset_is_rejected(self):
        with self.assertRaises(ValueError):
            build_guitar_transcriber("unknown")


if __name__ == "__main__":
    unittest.main()
