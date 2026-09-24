# Milestone 5 — Practice Player

## Goal
Turn the transcription pipeline into a usable practice experience rather than a static export.

## Implemented

1. MusicXML rendering through OpenSheetMusicDisplay.
2. Standard notation and TAB displayed together.
3. Original audio playback via `/jobs/{id}/audio`.
4. Score cursor synchronized from the canonical `original_start` note timestamps.
5. Playback rate controls: 0.5x, 0.75x, 1x, 1.25x, 1.5x, 2x.
6. A/B loop controls.
7. Retuning through `POST /jobs/{id}/retune` without rerunning audio separation or transcription.
8. Direct MusicXML endpoint: `/jobs/{id}/musicxml`.
9. Stem endpoint: `/jobs/{id}/stems/{stem_name}` for the next mixer iteration.

## Synchronization model
The audio clock remains authoritative. The player maps `currentTime` to unique chord onsets in `quantized_tab` and advances the OSMD cursor accordingly. This is intentionally simple for the MVP and preserves the original audio timestamps even after rhythmic quantization.

## Next refinement

- true multi-stem mixer with gain/mute/solo;
- waveform overview;
- scroll-follow score viewport;
- metronome/count-in;
- selectable bars and loop-by-measure;
- keyboard shortcuts;
- technique symbols and articulations;
- robust tempo map rather than one global BPM;
- worker queue + persistent database/object storage.
