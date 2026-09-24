import pathlib, sys, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from music_engine.engine import NoteEvent, TabNote, get_tuning, make_custom_tuning, possible_positions, with_capo, optimize_polyphonic_fingering
from music_engine.intelligence import analyze_chord, detect_barres, assign_fingers

class IntelligenceTests(unittest.TestCase):
    def test_c_major_first_inversion(self):
        chord = analyze_chord([52, 55, 60], 2)
        self.assertEqual(chord.name, "C/E")
        self.assertEqual(chord.quality, "major")
        self.assertEqual(chord.inversion, 1)

    def test_barre_detection(self):
        notes = [
            TabNote(53,0,1,0,1,1,0), TabNote(58,0,1,1,1,1,0),
            TabNote(63,0,1,2,1,1,0), TabNote(68,0,1,3,1,1,0),
        ]
        bars = detect_barres(notes)
        self.assertEqual(len(bars), 1)
        self.assertEqual(bars[0].fret, 1)
        fingers = assign_fingers(notes)
        self.assertTrue(all(x.finger == 1 for x in fingers))

    def test_capo_transposes_open_strings(self):
        t = with_capo(get_tuning("guitar_standard"), 2)
        self.assertIn((0,0), {(p.string_index,p.fret) for p in possible_positions(42,t)})
        self.assertNotIn((0,0), {(p.string_index,p.fret) for p in possible_positions(40,t)})

    def test_custom_eight_string(self):
        t = make_custom_tuning([28,35,40,45,50,55,59,64], name="Drop E 8")
        self.assertEqual(len(t.open_pitches), 8)

    def test_eight_string_preset_has_low_fsharp(self):
        t = get_tuning("guitar_standard_8")
        self.assertIn((0,0), {(p.string_index,p.fret) for p in possible_positions(30,t)})

    def test_easy_profile_keeps_span_constrained(self):
        events=[NoteEvent(52,0,1),NoteEvent(59,0,1),NoteEvent(64,0,1)]
        tab=optimize_polyphonic_fingering(events,get_tuning("guitar_standard"),profile="easy")
        frets=[n.fret for n in tab if n.fret>0]
        self.assertLessEqual(max(frets)-min(frets),4)

if __name__ == '__main__': unittest.main()
