import pathlib, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from music_engine.engine import NoteEvent, TabNote
from music_engine.techniques import detect_technique_hints

class TechniqueTests(unittest.TestCase):
    def test_bend_from_pitch_curve(self):
        events=[NoteEvent(64,0,0.5,pitch_bends=(0.0,0.2,0.8,1.0))]
        tab=[TabNote(64,0,0.5,5,0,1.0,0)]
        hints=detect_technique_hints(events,tab)
        self.assertEqual(hints[0].kind,'bend')

    def test_legato_candidate_same_string(self):
        events=[NoteEvent(60,0,0.2),NoteEvent(62,0.22,0.2)]
        tab=[TabNote(60,0,0.2,2,5,1,0),TabNote(62,0.22,0.2,2,7,1,1)]
        hints=detect_technique_hints(events,tab)
        self.assertEqual(hints[0].kind,'hammer_on_candidate')

if __name__=='__main__': unittest.main()
