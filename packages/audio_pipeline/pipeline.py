from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable
import json

from music_engine.engine import NoteEvent, TabNote, get_tuning, optimize_polyphonic_fingering_robust
from music_engine.rhythm import TimeSignature, quantize_tab_notes
from music_engine.musicxml import export_musicxml
from music_engine.techniques import detect_technique_hints
from music_engine.guitar_roles import split_guitar_roles
from music_engine.riff_consistency import harmonize_repeated_riffs
from music_engine.accuracy import confidence_summary
from .adapters import Separator, Transcriber
from .source_selection import select_guitar_source


@dataclass
class PipelineResult:
    stems: dict[str, str]
    tracks: dict[str, dict]
    selected_part: str
    notes: list[dict]
    tab: list[dict]
    quantized_tab: list[dict]
    tuning: str
    rhythm: dict
    musicxml: str
    techniques: list[dict]
    fingering_diagnostics: dict

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


@dataclass
class AudioPipeline:
    separator: Separator
    transcriber: Transcriber
    bass_transcriber: Transcriber | None = None
    piano_transcriber: Transcriber | None = None
    drum_transcriber: object | None = None

    def run(
        self,
        audio_path: Path,
        work_dir: Path,
        tuning_key: str = "guitar_standard",
        preferred_stem: str = "guitar",
        bpm: float | None = None,
        beats: int = 4,
        beat_type: int = 4,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> PipelineResult:
        def progress(value: int, stage: str) -> None:
            if progress_callback is not None:
                progress_callback(value, stage)

        work_dir.mkdir(parents=True, exist_ok=True)
        progress(25, "separating")
        stems = self.separator.separate(audio_path, work_dir / "stems")
        progress(55, "transcribing_guitar")

        # Milestone 11 baseline: route Demucs stems into independent pitched
        # instrument parts. Demucs htdemucs exposes bass directly; guitar is
        # still contained in "other" until a guitar-specific separator is added.
        tracks: dict[str, dict] = {}

        guitar_stem = stems.get(preferred_stem) or stems.get("other")
        if guitar_stem is not None:
            candidate_paths: dict[str, Path] = {
                "guitar" if preferred_stem in stems else "other": guitar_stem
            }
            if stems.get("guitar_alt") is not None:
                candidate_paths["guitar_alt"] = stems["guitar_alt"]

            candidate_notes: dict[str, list[NoteEvent]] = {}
            for source_name, source_path in candidate_paths.items():
                progress(
                    55 if source_name != "guitar_alt" else 61,
                    f"transcribing_{source_name}",
                )
                candidate_notes[source_name] = self.transcriber.transcribe(source_path)

            source_selection = select_guitar_source(candidate_notes)
            selected_source = source_selection.selected_source
            selected_path = candidate_paths[selected_source]
            raw_guitar_notes = candidate_notes[selected_source]

            riff_consistency = harmonize_repeated_riffs(raw_guitar_notes)
            guitar_notes = list(riff_consistency.events)
            tracks["guitar"] = {
                "part": "guitar",
                "kind": "strings",
                "stem": selected_source,
                "source_path": str(selected_path),
                "notes": [asdict(n) for n in guitar_notes],
                "confidence": confidence_summary(guitar_notes),
                "transcription_engine": getattr(self.transcriber, "name", self.transcriber.__class__.__name__),
                "source_selection": source_selection.to_dict(),
                "riff_consistency": {
                    "correction_count": len(riff_consistency.corrections),
                    "corrections": [asdict(row) for row in riff_consistency.corrections],
                },
            }

            role_split = split_guitar_roles(guitar_notes)
            if len(role_split.rhythm) >= 4:
                tracks["guitar_rhythm"] = {
                    "part": "guitar_rhythm",
                    "kind": "strings",
                    "virtual": True,
                    "stem": "guitar" if preferred_stem in stems else "other",
                    "source_path": str(guitar_stem),
                    "notes": [asdict(n) for n in role_split.rhythm],
                    "confidence": confidence_summary(role_split.rhythm),
                    "role_confidence": role_split.confidence,
                    "role_explanation": list(role_split.explanation),
                }
            if len(role_split.lead) >= 4:
                tracks["guitar_lead"] = {
                    "part": "guitar_lead",
                    "kind": "strings",
                    "virtual": True,
                    "stem": "guitar" if preferred_stem in stems else "other",
                    "source_path": str(guitar_stem),
                    "notes": [asdict(n) for n in role_split.lead],
                    "confidence": confidence_summary(role_split.lead),
                    "role_confidence": role_split.confidence,
                    "role_explanation": list(role_split.explanation),
                }

        bass_stem = stems.get("bass")
        if bass_stem is not None:
            progress(65, "transcribing_bass")
            bass_engine = self.bass_transcriber or self.transcriber
            bass_notes = bass_engine.transcribe(bass_stem)
            tracks["bass"] = {
                "part": "bass",
                "kind": "strings",
                "stem": "bass",
                "source_path": str(bass_stem),
                "notes": [asdict(n) for n in bass_notes],
                "confidence": confidence_summary(bass_notes),
            }


        piano_stem = stems.get("piano")
        if piano_stem is not None and self.piano_transcriber is not None:
            progress(70, "transcribing_piano")
            piano_notes = self.piano_transcriber.transcribe(piano_stem)
            tracks["piano"] = {
                "part": "piano",
                "kind": "score",
                "stem": "piano",
                "source_path": str(piano_stem),
                "notes": [asdict(n) for n in piano_notes],
                "confidence": confidence_summary(piano_notes),
            }



        drum_stem = stems.get("drums")
        if drum_stem is not None and self.drum_transcriber is not None:
            progress(72, "transcribing_drums")
            drum_events = self.drum_transcriber.transcribe(drum_stem)
            tracks["drums"] = {
                "part": "drums",
                "kind": "drums",
                "stem": "drums",
                "source_path": str(drum_stem),
                "events": [event.to_dict() for event in drum_events],
                "notes": [],
            }


        if not tracks:
            fallback_stem = next(iter(stems.values()))
            fallback_notes = self.transcriber.transcribe(fallback_stem)
            tracks["guitar"] = {
                "part": "guitar",
                "kind": "strings",
                "stem": next(iter(stems.keys())),
                "source_path": str(fallback_stem),
                "notes": [asdict(n) for n in fallback_notes],
                "confidence": confidence_summary(fallback_notes),
            }

        selected_part = "guitar" if "guitar" in tracks else next(iter(tracks))
        notes = [NoteEvent(**row) for row in tracks[selected_part]["notes"]]

        progress(75, "fingering")
        tuning = get_tuning(tuning_key)
        tab, fingering_diagnostics = optimize_polyphonic_fingering_robust(notes, tuning)
        rhythm_cfg, quantized = quantize_tab_notes(
            tab,
            bpm=bpm,
            time_signature=TimeSignature(beats, beat_type),
        )
        musicxml_text = export_musicxml(
            quantized,
            rhythm_cfg,
            tuning,
            title=audio_path.stem,
        )
        techniques = detect_technique_hints(notes, tab)
        musicxml_path = work_dir / "score.musicxml"
        musicxml_path.write_text(musicxml_text, encoding="utf-8")

        result = PipelineResult(
            stems={k: str(v) for k, v in stems.items()},
            tracks=tracks,
            selected_part=selected_part,
            notes=[asdict(n) for n in notes],
            tab=[asdict(t) for t in tab],
            quantized_tab=[asdict(n) for n in quantized],
            tuning=tuning_key,
            rhythm={
                "bpm": rhythm_cfg.bpm,
                "beats": rhythm_cfg.time_signature.beats,
                "beat_type": rhythm_cfg.time_signature.beat_type,
                "divisions": rhythm_cfg.divisions,
                "subdivision": rhythm_cfg.subdivision,
                "measure_ticks": rhythm_cfg.measure_ticks,
            },
            musicxml=str(musicxml_path),
            techniques=[t.to_dict() for t in techniques],
            fingering_diagnostics=asdict(fingering_diagnostics),
        )
        result.write_json(work_dir / "result.json")
        progress(95, "finalizing")
        return result
