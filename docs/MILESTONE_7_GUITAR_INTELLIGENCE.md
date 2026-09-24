# Milestone 7 — Guitar Intelligence (v0.7)

AutoTab now adds a musical reasoning layer above pitch-to-fret conversion.

## Implemented

- chord recognition from simultaneous pitch classes
- common chord qualities: major/minor/power/sus/dim/aug/6/7/maj7/m7/m7b5/add9
- slash-chord / inversion labels from the actual bass pitch
- probable barre detection from same-fret multi-string shapes
- first-pass finger assignment (0=open, 1=index/barre, 2–4 remaining frets)
- capo-aware fretboard geometry
- MusicXML capo metadata
- 7-string Standard preset
- 8-string Standard preset
- custom tuning support for 4–8 strings
- playing profiles:
  - Original-like
  - Easy
  - Rhythm
  - Lead
- profile-specific fingering costs and maximum hand span
- API endpoint `POST /intelligence`
- advanced retune with profile/capo/custom tuning
- player controls for profile, capo and custom MIDI tuning
- chord/barre/finger summaries in the practice player

## Architectural rule

Detected pitches remain canonical. Capo, tuning and playing profile affect only the fingering solution and notation layer. Changing any of them does not rerun source separation or AMT.

## Current limitations

Chord naming is template-based and intentionally conservative. Extensions such as 9/11/13, omitted tones and enharmonic spelling by musical key need a harmonic-context model.

Barre and finger assignments are playability heuristics, not computer-vision reconstruction of the performer's actual hand.

Custom tuning currently uses MIDI note numbers at the API/UI boundary. A note-name parser (e.g. D2,A2,D3,G3,B3,E4) is planned.
