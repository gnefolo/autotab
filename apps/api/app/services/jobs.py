from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
import threading
import traceback
import uuid

from audio_pipeline.adapters import BasicPitchTranscriber, DemucsSeparator, PassthroughSeparator
from audio_pipeline.pipeline import AudioPipeline


@dataclass
class Job:
    id: str
    source_path: str | None = None
    status: str = "queued"
    progress: int = 0
    result: dict | None = None
    error: str | None = None
    stage: str = "queued"


class JobService:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=1)

    def create(self, source: Path, tuning: str, dev_passthrough: bool = False) -> Job:
        job = Job(id=str(uuid.uuid4()), source_path=str(source))
        with self.lock:
            self.jobs[job.id] = job
        self.pool.submit(self._run, job.id, source, tuning, dev_passthrough)
        return job

    def get(self, job_id: str) -> Job | None:
        with self.lock:
            return self.jobs.get(job_id)

    def _set(self, job_id: str, **changes):
        with self.lock:
            job = self.jobs[job_id]
            for key, value in changes.items():
                setattr(job, key, value)

    def _run(self, job_id: str, source: Path, tuning: str, dev_passthrough: bool):
        try:
            self._set(job_id, status="processing", progress=10, stage="preparing")
            separator = PassthroughSeparator() if dev_passthrough else DemucsSeparator()
            pipeline = AudioPipeline(
                separator,
                BasicPitchTranscriber(minimum_frequency=70.0, maximum_frequency=1400.0),
                bass_transcriber=BasicPitchTranscriber(minimum_frequency=30.0, maximum_frequency=500.0),
            )

            def on_progress(value: int, stage: str):
                self._set(job_id, progress=value, stage=stage)

            result = pipeline.run(
                source,
                self.root / job_id,
                tuning,
                progress_callback=on_progress,
            )
            self._set(job_id, status="completed", progress=100, stage="completed", result=result.__dict__)
        except Exception as exc:
            self._set(
                job_id,
                status="failed",
                error=f"{exc}\n{traceback.format_exc(limit=4)}",
            )
