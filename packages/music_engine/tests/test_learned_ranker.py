import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from music_engine.engine import NoteEvent, get_tuning
from music_engine.learned_ranker import (
    position_preference_score,
    train_pairwise_ranker,
    optimize_polyphonic_fingering_learned,
)


class LearnedRankerTests(unittest.TestCase):
    def test_empty_dataset_is_neutral(self):
        model = train_pairwise_ranker([])
        self.assertEqual(model.examples, 0)
        self.assertTrue(all(abs(w) < 1e-12 for w in model.weights))

    def test_correction_teaches_new_position_preference(self):
        records = [{
            "pitch": 64,
            "old_string_index": 5,
            "old_fret": 0,
            "new_string_index": 4,
            "new_fret": 5,
            "capo": 0,
        }]
        model = train_pairwise_ranker(records, epochs=200)
        tuning = get_tuning("guitar_standard")
        corrected = position_preference_score(model, 64, 4, 5, tuning)
        original = position_preference_score(model, 64, 5, 0, tuning)
        self.assertGreater(corrected, original)

    def test_learned_optimizer_still_preserves_pitch(self):
        records = [{
            "pitch": 64,
            "old_string_index": 5,
            "old_fret": 0,
            "new_string_index": 4,
            "new_fret": 5,
            "capo": 0,
        }]
        model = train_pairwise_ranker(records, epochs=200)
        tab = optimize_polyphonic_fingering_learned(
            [NoteEvent(64, 0.0, 0.5)],
            get_tuning("guitar_standard"),
            model,
            strength=1.5,
        )
        self.assertEqual(tab[0].pitch, 64)
        sounding = (
            get_tuning("guitar_standard").open_pitches[tab[0].string_index]
            + tab[0].fret
        )
        self.assertEqual(sounding, 64)


if __name__ == "__main__":
    unittest.main()
