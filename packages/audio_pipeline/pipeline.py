from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable
import json

from music_engine.engine import NoteEvent, TabNote, get_tuning, optimize_polyphonic_fingering_robust
from music_engine.rhythm import TimeSignature, quantize_tab_notes
from music_engine.musicxml import export_musicxml
from music_engine.techniques import detect_technique_hints
from .adapters import Separator, Transcriber


@dataclass
class PipelineResult:
    stems: dict[str, str]
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
        progress(55, "transcribing")

        # Current MVP chooses a guitar stem when supplied. With 4-stem Demucs,
        # guitar usually remains in `other`; instrument-recognition comes next.
        stem_path = stems.get(preferred_stem) or stems.get("other")
        if stem_path is None:
            stem_path = next(iter(stems.values()))

        notes = self.transcriber.transcribe(stem_path)
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
