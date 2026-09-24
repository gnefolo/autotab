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

    def separate(self, audio_path: Path, output_dir: Path) -> dict[str, Path]:
        """Run Demucs as a replaceable baseline separator.

        This adapter deliberately shells out to the CLI so the orchestration layer
        is not coupled to Demucs internals. Install Demucs in the worker image.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        # Always invoke Demucs through the same Python interpreter that runs
        # AutoTab. This avoids PATH mismatches between the core venv, ML venv,
        # Homebrew and system Python on macOS.
        models = [self.model]
        if self.fallback_model and self.fallback_model != self.model:
            models.append(self.fallback_model)

        failures: list[str] = []
        for model in models:
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
                failures.append(
                    f"{model}: stdout={stdout!r} stderr={stderr!r}"
                )
                continue

            song_dir = output_dir / model / audio_path.stem
            stems: dict[str, Path] = {}
            if song_dir.exists():
                for p in song_dir.glob("*.wav"):
                    stems[p.stem] = p
            if stems:
                return stems
            failures.append(f"{model}: produced no stems under {song_dir}")

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
