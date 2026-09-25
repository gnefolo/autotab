from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import sys

from music_engine.engine import NoteEvent


class Separator(ABC):
    @abstractmethod
    def separate(self, audio_path: Path, output_dir: Path) -> dict[str, Path]:
        raise NotImplementedError


class Transcriber(ABC):
    @abstractmethod
    def transcribe(self, audio_path: Path) -> list[NoteEvent]:
        raise NotImplementedError


@dataclass
class PassthroughSeparator(Separator):
    """Development adapter: treats the uploaded file as a guitar stem."""
    stem_name: str = "guitar"

    def separate(self, audio_path: Path, output_dir: Path) -> dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / f"{self.stem_name}{audio_path.suffix.lower()}"
        shutil.copy2(audio_path, target)
        return {self.stem_name: target}


@dataclass
class DemucsSeparator(Separator):
    model: str = "htdemucs_6s"
    fallback_model: str | None = "htdemucs"
    device: str | None = None
    collect_fallback_guitar_candidate: bool = True

    def separate(self, audio_path: Path, output_dir: Path) -> dict[str, Path]:
        """Run the preferred Demucs model and optionally collect a second guitar source."""
        output_dir.mkdir(parents=True, exist_ok=True)

        def run_model(model: str) -> tuple[dict[str, Path], str | None]:
            cmd = [sys.executable, "-m", "demucs", "-n", model, "-o", str(output_dir)]
            if self.device:
                cmd += ["-d", self.device]
            cmd.append(str(audio_path))
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
            except FileNotFoundError as exc:
                raise RuntimeError(
                    f"Python executable not found while launching Demucs: {sys.executable}"
                ) from exc
            except subprocess.CalledProcessError as exc:
                stdout = (exc.stdout or "")[-3000:]
                stderr = (exc.stderr or "")[-5000:]
                return {}, f"{model}: stdout={stdout!r} stderr={stderr!r}"

            song_dir = output_dir / model / audio_path.stem
            stems: dict[str, Path] = {}
            if song_dir.exists():
                for p in song_dir.glob("*.wav"):
                    stems[p.stem] = p
            if not stems:
                return {}, f"{model}: produced no stems under {song_dir}"
            return stems, None

        failures: list[str] = []
        primary, error = run_model(self.model)
        if error:
            failures.append(error)

        fallback: dict[str, Path] = {}
        if self.fallback_model and (
            not primary or self.collect_fallback_guitar_candidate
        ):
            fallback, error = run_model(self.fallback_model)
            if error:
                failures.append(error)

        if primary:
            result = dict(primary)
            if fallback.get("other") is not None:
                result["guitar_alt"] = fallback["other"]
            return result

        if fallback:
            return fallback

        raise RuntimeError(
            "Demucs failed for all configured models. " + " | ".join(failures)
        )


@dataclass
class BasicPitchTranscriber(Transcriber):
    minimum_frequency: float | None = 70.0
    maximum_frequency: float | None = 1400.0
    onset_threshold: float = 0.5
    frame_threshold: float = 0.3

    def transcribe(self, audio_path: Path) -> list[NoteEvent]:
        try:
            from basic_pitch import ICASSP_2022_MODEL_PATH
            from basic_pitch.inference import predict
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Basic Pitch dependency import failed: "
                f"{exc}. The package may be installed but its runtime dependencies are incomplete."
            ) from exc
        except ImportError as exc:
            raise RuntimeError(
                f"Basic Pitch import failed: {exc}"
            ) from exc

        # Pass the model path explicitly. This avoids API-version ambiguity and
        # lets Basic Pitch choose among installed TF/CoreML/TFLite/ONNX runtimes.
        _, _, note_events = predict(
            str(audio_path),
            ICASSP_2022_MODEL_PATH,
            onset_threshold=self.onset_threshold,
            frame_threshold=self.frame_threshold,
            minimum_frequency=self.minimum_frequency,
            maximum_frequency=self.maximum_frequency,
        )

        result: list[NoteEvent] = []
        for event in note_events:
            start, end, pitch, amplitude, _pitch_bends = event
            result.append(
                NoteEvent(
                    pitch=int(pitch),
                    start=float(start),
                    duration=max(0.001, float(end) - float(start)),
                    velocity=max(1, min(127, int(round(float(amplitude) * 127)))),
                    confidence=max(0.0, min(1.0, float(amplitude))),
                    pitch_bends=tuple(float(x) for x in (_pitch_bends or [])),
                )
            )
        return result


@dataclass
class ConsensusTranscriber(Transcriber):
    transcribers: tuple[Transcriber, ...]
    onset_tolerance: float = 0.07
    minimum_support: int = 2
    high_confidence_singleton: float = 0.88
    name: str = "consensus"

    def transcribe(self, audio_path: Path) -> list[NoteEvent]:
        if not self.transcribers:
            return []

        runs = [list(t.transcribe(audio_path)) for t in self.transcribers]
        candidates: list[tuple[int, NoteEvent]] = []
        for run_index, events in enumerate(runs):
            for event in events:
                candidates.append((run_index, event))

        clusters: list[list[tuple[int, NoteEvent]]] = []
        for run_index, event in sorted(
            candidates,
            key=lambda item: (item[1].pitch, item[1].start, item[0]),
        ):
            best_cluster = None
            best_distance = float("inf")
            for cluster in clusters:
                exemplar = cluster[0][1]
                if exemplar.pitch != event.pitch:
                    continue
                if any(existing_run == run_index for existing_run, _ in cluster):
                    continue
                center = sum(e.start for _, e in cluster) / len(cluster)
                distance = abs(event.start - center)
                if distance <= self.onset_tolerance and distance < best_distance:
                    best_cluster = cluster
                    best_distance = distance
            if best_cluster is None:
                clusters.append([(run_index, event)])
            else:
                best_cluster.append((run_index, event))

        merged: list[NoteEvent] = []
        run_count = len(self.transcribers)
        for cluster in clusters:
            support = len({run_index for run_index, _ in cluster})
            confidences = [event.confidence for _, event in cluster]
            max_confidence = max(confidences)
            if support < self.minimum_support and max_confidence < self.high_confidence_singleton:
                continue

            events = [event for _, event in cluster]
            starts = sorted(event.start for event in events)
            durations = sorted(event.duration for event in events)
            velocities = sorted(event.velocity for event in events)
            middle = len(events) // 2

            def median_value(values):
                if len(values) % 2:
                    return float(values[middle])
                return float(values[middle - 1] + values[middle]) / 2.0

            support_ratio = support / run_count
            mean_confidence = sum(confidences) / len(confidences)
            consensus_confidence = min(
                1.0,
                0.65 * support_ratio + 0.35 * mean_confidence,
            )
            bends = max(events, key=lambda event: event.confidence).pitch_bends

            merged.append(
                NoteEvent(
                    pitch=events[0].pitch,
                    start=median_value(starts),
                    duration=max(0.001, median_value(durations)),
                    velocity=max(1, min(127, int(round(median_value(velocities))))),
                    confidence=round(consensus_confidence, 4),
                    pitch_bends=bends,
                )
            )

        return sorted(merged, key=lambda event: (event.start, event.pitch))


@dataclass
class GuitarCleanupTranscriber(Transcriber):
    base: Transcriber
    min_duration: float = 0.045
    low_confidence_threshold: float = 0.62
    duplicate_tolerance: float = 0.055
    cluster_tolerance: float = 0.035
    max_polyphony: int = 6
    name: str = "guitar-consensus-cleanup"

    def transcribe(self, audio_path: Path) -> list[NoteEvent]:
        events = sorted(self.base.transcribe(audio_path), key=lambda e: (e.start, e.pitch))

        cleaned: list[NoteEvent] = []
        for event in events:
            if (
                event.duration < self.min_duration
                and event.confidence < self.low_confidence_threshold
            ):
                continue

            duplicate_index = None
            for i in range(len(cleaned) - 1, -1, -1):
                prev = cleaned[i]
                if event.start - prev.start > self.duplicate_tolerance:
                    break
                if (
                    prev.pitch == event.pitch
                    and abs(event.start - prev.start) <= self.duplicate_tolerance
                ):
                    duplicate_index = i
                    break

            if duplicate_index is not None:
                prev = cleaned[duplicate_index]
                if event.confidence > prev.confidence:
                    cleaned[duplicate_index] = event
                continue

            cleaned.append(event)

        # Guitar cannot physically sound more notes than strings at one instant.
        # Keep the strongest six when AMT emits an obviously impossible cluster.
        out: list[NoteEvent] = []
        i = 0
        while i < len(cleaned):
            cluster = [cleaned[i]]
            j = i + 1
            while j < len(cleaned) and cleaned[j].start - cleaned[i].start <= self.cluster_tolerance:
                cluster.append(cleaned[j])
                j += 1

            if len(cluster) > self.max_polyphony:
                cluster = sorted(
                    cluster,
                    key=lambda e: (e.confidence, e.duration),
                    reverse=True,
                )[: self.max_polyphony]
                cluster.sort(key=lambda e: (e.start, e.pitch))

            out.extend(cluster)
            i = j

        return sorted(out, key=lambda e: (e.start, e.pitch))


def build_guitar_transcriber(mode: str = "balanced") -> Transcriber:
    presets = {
        "precise": {
            "thresholds": ((0.48, 0.30), (0.58, 0.36), (0.68, 0.44)),
            "singleton": 0.94,
            "min_duration": 0.055,
            "cleanup_confidence": 0.68,
        },
        "balanced": {
            "thresholds": ((0.38, 0.24), (0.50, 0.30), (0.62, 0.38)),
            "singleton": 0.90,
            "min_duration": 0.045,
            "cleanup_confidence": 0.62,
        },
        "sensitive": {
            "thresholds": ((0.30, 0.20), (0.42, 0.26), (0.54, 0.32)),
            "singleton": 0.84,
            "min_duration": 0.035,
            "cleanup_confidence": 0.55,
        },
    }
    if mode not in presets:
        raise ValueError(f"Unknown guitar transcription mode: {mode}")

    cfg = presets[mode]
    passes = tuple(
        BasicPitchTranscriber(
            minimum_frequency=70.0,
            maximum_frequency=1400.0,
            onset_threshold=onset,
            frame_threshold=frame,
        )
        for onset, frame in cfg["thresholds"]
    )
    consensus = ConsensusTranscriber(
        transcribers=passes,
        onset_tolerance=0.07,
        minimum_support=2,
        high_confidence_singleton=cfg["singleton"],
        name=f"basic-pitch-3pass-{mode}",
    )
    return GuitarCleanupTranscriber(
        base=consensus,
        min_duration=cfg["min_duration"],
        low_confidence_threshold=cfg["cleanup_confidence"],
        name=f"basic-pitch-3pass-{mode}+cleanup",
    )


@dataclass
class HFGuitarTranscriber(Transcriber):
    device: str = "auto"
    batch_size: int = 8
    name: str = "hf-midi-transcription:guitar"

    def transcribe(self, audio_path: Path) -> list[NoteEvent]:
        try:
            from hf_midi_transcription import MidiTranscriptionModel
            import pretty_midi
        except Exception as exc:
            raise RuntimeError(
                "Guitar-specific AMT is not installed. Start AutoTab with "
                "./start-autotab.sh --ml --guitar-model"
            ) from exc

        with tempfile.TemporaryDirectory(prefix="autotab-hf-guitar-") as td:
            midi_path = Path(td) / "guitar.mid"
            model = MidiTranscriptionModel(
                instrument="guitar",
                device=self.device,
                batch_size=self.batch_size,
            )
            model.transcribe(str(audio_path), str(midi_path))

            midi = pretty_midi.PrettyMIDI(str(midi_path))
            result: list[NoteEvent] = []
            for instrument in midi.instruments:
                if instrument.is_drum:
                    continue
                for note in instrument.notes:
                    duration = max(0.001, float(note.end) - float(note.start))
                    velocity = max(1, min(127, int(note.velocity)))
                    result.append(
                        NoteEvent(
                            pitch=int(note.pitch),
                            start=float(note.start),
                            duration=duration,
                            velocity=velocity,
                            confidence=max(0.25, min(1.0, velocity / 127.0)),
                            pitch_bends=(),
                        )
                    )

        return sorted(result, key=lambda event: (event.start, event.pitch))
