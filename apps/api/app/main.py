from __future__ import annotations
import pathlib
import sys
import uuid
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages"))

from music_engine.engine import NoteEvent, TUNINGS, get_tuning, optimize_polyphonic_fingering
from music_engine.rhythm import TimeSignature, quantize_tab_notes
from music_engine.musicxml import export_musicxml
from .schemas import TabRequest, NotationRequest, TabNoteOut
from .services.jobs import JobService

UPLOADS = ROOT / "artifacts" / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)
JOBS = JobService(ROOT / "artifacts" / "jobs")

app = FastAPI(title="AutoTab API", version="0.6.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RetuneRequest(BaseModel):
    tuning: str

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.6.0"}

@app.get("/tunings")
def tunings():
    return [{"id": k, "name": v.name, "open_pitches": v.open_pitches, "max_fret": v.max_fret} for k, v in TUNINGS.items()]

@app.post("/tab/optimize", response_model=list[TabNoteOut])
def tab_optimize(payload: TabRequest):
    tuning = get_tuning(payload.tuning)
    events = [NoteEvent(**n.model_dump()) for n in payload.notes]
    return [TabNoteOut(**x.__dict__) for x in optimize_polyphonic_fingering(events, tuning)]

@app.post("/notation")
def notation(payload: NotationRequest):
    tuning = get_tuning(payload.tuning)
    events = [NoteEvent(**n.model_dump()) for n in payload.notes]
    tab = optimize_polyphonic_fingering(events, tuning)
    cfg, quantized = quantize_tab_notes(tab, bpm=payload.bpm, time_signature=TimeSignature(payload.beats, payload.beat_type), subdivision=payload.subdivision)
    xml = export_musicxml(quantized, cfg, tuning, title=payload.title)
    return {"rhythm": {"bpm": cfg.bpm, "beats": cfg.time_signature.beats, "beat_type": cfg.time_signature.beat_type, "divisions": cfg.divisions, "subdivision": cfg.subdivision, "measure_ticks": cfg.measure_ticks}, "tab": [x.__dict__ for x in tab], "quantized_tab": [x.__dict__ for x in quantized], "musicxml": xml}

@app.post("/tracks")
async def upload_track(file: UploadFile = File(...), tuning: str = Form("guitar_standard"), dev_passthrough: bool = Form(False)):
    get_tuning(tuning)
    suffix = pathlib.Path(file.filename or "track.wav").suffix.lower() or ".wav"
    source = UPLOADS / f"{uuid.uuid4()}{suffix}"
    source.write_bytes(await file.read())
    job = JOBS.create(source, tuning, dev_passthrough=dev_passthrough)
    return {"job_id": job.id, "id": job.id, "status": job.status}

@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = JOBS.get(job_id)
    if job is None: raise HTTPException(status_code=404, detail="job not found")
    return job.__dict__

@app.get("/jobs/{job_id}/musicxml")
def get_musicxml(job_id: str):
    job = JOBS.get(job_id)
    if job is None or not job.result: raise HTTPException(status_code=404, detail="result not ready")
    path = pathlib.Path(job.result["musicxml"])
    if not path.exists(): raise HTTPException(status_code=404, detail="MusicXML not found")
    return FileResponse(path, media_type="application/vnd.recordare.musicxml+xml", filename="autotab.musicxml")

@app.get("/jobs/{job_id}/audio")
def get_audio(job_id: str):
    job = JOBS.get(job_id)
    if job is None or not job.source_path: raise HTTPException(status_code=404, detail="audio not found")
    path = pathlib.Path(job.source_path)
    if not path.exists(): raise HTTPException(status_code=404, detail="audio not found")
    return FileResponse(path)

@app.get("/jobs/{job_id}/stems/{stem_name}")
def get_stem(job_id: str, stem_name: str):
    job = JOBS.get(job_id)
    if job is None or not job.result: raise HTTPException(status_code=404, detail="result not ready")
    stems = job.result.get("stems", {})
    if stem_name not in stems: raise HTTPException(status_code=404, detail="stem not found")
    path = pathlib.Path(stems[stem_name])
    if not path.exists(): raise HTTPException(status_code=404, detail="stem not found")
    return FileResponse(path)

@app.post("/jobs/{job_id}/retune")
def retune_job(job_id: str, payload: RetuneRequest):
    job = JOBS.get(job_id)
    if job is None or not job.result: raise HTTPException(status_code=404, detail="result not ready")
    tuning = get_tuning(payload.tuning)
    events = [NoteEvent(**n) for n in job.result.get("notes", [])]
    tab = optimize_polyphonic_fingering(events, tuning)
    rhythm = job.result.get("rhythm", {})
    cfg, quantized = quantize_tab_notes(tab, bpm=rhythm.get("bpm"), time_signature=TimeSignature(rhythm.get("beats",4), rhythm.get("beat_type",4)), subdivision=rhythm.get("subdivision",4))
    xml = export_musicxml(quantized, cfg, tuning, title="AutoTab Retuned")
    out = JOBS.root / job_id / f"score-{payload.tuning}.musicxml"
    out.write_text(xml, encoding="utf-8")
    job.result.update({"tab":[x.__dict__ for x in tab], "quantized_tab":[x.__dict__ for x in quantized], "tuning":payload.tuning, "musicxml":str(out)})
    return job.__dict__
