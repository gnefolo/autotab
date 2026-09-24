from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import subprocess
import tempfile
import wave


@dataclass(frozen=True)
class DrumEvent:
    drum: str
    start: float
    confidence: float
    midi_note: int

    def to_dict(self) -> dict:
        return asdict(self)


GM_DRUM_NOTES = {
    "kick": 36,
    "snare": 38,
    "hihat": 42,
    "tom": 45,
    "cymbal": 49,
}


def classify_drum_bands(
    low: float,
    low_mid: float,
    mid: float,
    high: float,
    sustained_ratio: float = 0.0,
) -> str:
    total = max(1e-12, low + low_mid + mid + high)
    low_r = low / total
    low_mid_r = low_mid / total
    mid_r = mid / total
    high_r = high / total

    if low_r >= 0.46:
        return "kick"
    if high_r >= 0.46:
        return "cymbal" if sustained_ratio >= 0.42 else "hihat"
    if low_mid_r >= 0.38 and low_mid_r > mid_r:
        return "tom"
    return "snare"


@dataclass
class DrumTranscriber:
    sample_rate: int = 22050
    onset_threshold_sigma: float = 2.2
    refractory_seconds: float = 0.065

    def transcribe(self, audio_path: Path) -> list[DrumEvent]:
        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError(
                "Drum transcription requires NumPy from the ML environment."
            ) from exc

        with tempfile.TemporaryDirectory(prefix="autotab-drums-") as td:
            mono_path = Path(td) / "drums-mono.wav"
            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(audio_path),
                "-ac", "1", "-ar", str(self.sample_rate),
                "-c:a", "pcm_s16le", str(mono_path),
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
            except (FileNotFoundError, subprocess.CalledProcessError) as exc:
                detail = getattr(exc, "stderr", "") or str(exc)
                raise RuntimeError(f"FFmpeg drum preprocessing failed: {detail}") from exc

            with wave.open(str(mono_path), "rb") as wf:
                raw = wf.readframes(wf.getnframes())
                sr = wf.getframerate()

        samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
        if samples.size < 2048 or float(np.max(np.abs(samples))) < 1e-5:
            return []

        frame = 1024
        hop = 256
        window = np.hanning(frame).astype(np.float32)
        count = 1 + (len(samples) - frame) // hop
        if count <= 2:
            return []

        rms = np.empty(count, dtype=np.float32)
        spectra = []
        for i in range(count):
            chunk = samples[i * hop:i * hop + frame] * window
            rms[i] = float(np.sqrt(np.mean(chunk * chunk) + 1e-12))
            spectra.append(np.abs(np.fft.rfft(chunk)))
        spectra = np.asarray(spectra)

        onset = np.maximum(0.0, np.diff(rms, prepend=rms[0]))
        baseline = float(np.median(onset))
        spread = float(np.std(onset))
        threshold = baseline + self.onset_threshold_sigma * max(spread, 1e-6)
        refractory_frames = max(1, int(self.refractory_seconds * sr / hop))

        candidates: list[int] = []
        last = -refractory_frames
        for i in range(1, count - 1):
            if (
                onset[i] >= threshold
                and onset[i] >= onset[i - 1]
                and onset[i] >= onset[i + 1]
                and i - last >= refractory_frames
            ):
                candidates.append(i)
                last = i

        freqs = np.fft.rfftfreq(frame, d=1.0 / sr)
        masks = {
            "low": (freqs >= 35) & (freqs < 150),
            "low_mid": (freqs >= 150) & (freqs < 650),
            "mid": (freqs >= 650) & (freqs < 4500),
            "high": (freqs >= 4500) & (freqs <= sr / 2),
        }

        events: list[DrumEvent] = []
        for idx in candidates:
            spec = spectra[idx] ** 2
            energies = {
                name: float(spec[mask].sum())
                for name, mask in masks.items()
            }
            future = rms[idx:min(count, idx + max(2, int(0.18 * sr / hop)))]
            sustained = float(np.mean(future) / max(rms[idx], 1e-8)) if future.size else 0.0
            drum = classify_drum_bands(
                energies["low"],
                energies["low_mid"],
                energies["mid"],
                energies["high"],
                sustained_ratio=sustained,
            )
            strength = float(onset[idx] / max(threshold, 1e-8))
            confidence = max(0.25, min(0.99, 0.45 + 0.18 * strength))
            events.append(
                DrumEvent(
                    drum=drum,
                    start=round(idx * hop / sr, 5),
                    confidence=round(confidence, 4),
                    midi_note=GM_DRUM_NOTES[drum],
                )
            )

        return events
