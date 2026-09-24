# Milestone 4 — Rhythm + MusicXML (v0.4)

AutoTab now converts second-based TAB events into a musical timeline and exports standard notation + tablature as MusicXML.

## Implemented

- onset-based BPM fallback estimator
- explicit BPM override
- 4/4 fallback with configurable time signature
- tick-based internal timing (`480` divisions / quarter note)
- configurable rhythmic subdivision (default: sixteenth-note grid)
- chord-safe onset quantization using `chord_index`
- minimum non-zero note duration
- bar/measure calculation
- cross-bar note splitting with MusicXML ties
- MusicXML 4.0 export
- standard notation staff + TAB staff in one part
- tuning metadata in `<staff-tuning>`
- string/fret technical notation
- generated `score.musicxml` for every audio pipeline job
- `/notation` API endpoint for note-event -> TAB -> quantization -> MusicXML without audio inference
- frontend job polling and notation metadata display

## Current deliberate limitations

The v0.4 notation layer uses one rhythmic voice per staff. Sustains that overlap a later onset are clipped to the next onset so the MusicXML timeline remains deterministic. True multi-voice guitar notation, tuplets, swing and tempo maps are future refinements.

The BPM estimator is intentionally conservative. Production should use an audio beat/downbeat tracker and feed its tempo map into this layer. The current estimator is a useful fallback and deterministic test surface.

## Acceptance tests

- 120 BPM quarter-note sequence quantizes to 0/480/960 ticks.
- chord members retain one exact quantized onset.
- regular 500 ms onsets estimate ~120 BPM.
- Drop-D D5 exports strings 6/5/4 at fret 0 on the TAB staff.
- a note crossing a barline receives tie start/stop.
- audio pipeline writes both `result.json` and `score.musicxml`.
