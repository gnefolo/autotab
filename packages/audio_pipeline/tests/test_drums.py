import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from audio_pipeline.drums import classify_drum_bands


class DrumClassificationTests(unittest.TestCase):
    def test_kick_from_low_band(self):
        self.assertEqual(classify_drum_bands(10, 2, 1, 0.5), "kick")

    def test_hihat_from_short_high_band(self):
        self.assertEqual(classify_drum_bands(0.5, 1, 2, 10, sustained_ratio=0.2), "hihat")

    def test_cymbal_from_sustained_high_band(self):
        self.assertEqual(classify_drum_bands(0.5, 1, 2, 10, sustained_ratio=0.7), "cymbal")

    def test_tom_from_low_mid_band(self):
        self.assertEqual(classify_drum_bands(1, 8, 2, 1), "tom")

    def test_snare_is_default_mid_broadband_class(self):
        self.assertEqual(classify_drum_bands(1, 2, 6, 3), "snare")


if __name__ == "__main__":
    unittest.main()
