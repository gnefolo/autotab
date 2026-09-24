from __future__ import annotations

import json
import pathlib
import sys
import uuid

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages"))

from music_engine.engine import (
    NoteEvent,
    PROFILES,
    TUNINGS,
    TabNote,
    get_profile,
    get_tuning,
    make_custom_tuning,
    optimize_polyphonic_fingering,
    with_capo,
)
from music_engine.corrections import (
    FingeringAnchor,
    build_correction_record,
    optimize_with_anchors,
)
from music_engine.intelligence import analyze_guitar_intelligence
from music_engine.rhythm import TimeSignature, quantize_tab_notes
from music_engine.musicxml import export_musicxml

from .schemas import NotationRequest, TabNoteOut, TabRequest
from .services.jobs import JobService

UPLOADS = ROOT / "artifacts" / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)
JOBS = JobService(ROOT / "artifacts" / "jobs")

app = FastAPI(title="AutoTab API", version="0.8.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RetuneRequest(BaseModel):
    tuning: str = "guitar_standard"
    profile: str = "original_like"
    capo: int = Field(default=0, ge=0, le=12)
    custom_open_pitches: list[int] | None = None
    custom_name: str = "Custom tuning"


class CorrectionRequest(RetuneRequest):
    chord_index: int = Field(ge=0)
    pitch: int = Field(ge=0, le=127)
    string_index: int = Field(ge=0)
    fret: int = Field(ge=0)
    neighborhood_radius: int = Field(default=2, ge=0, le=12)


def resolve_setup(
    tuning_key: str,
    capo: int = 0,
    custom_open_pitches: list[int] | None = None,
    custom_name: str = "Custom tuning",
):
    if custom_open_pitches:
        return make_custom_tuning(custom_open_pitches, name=custom_name, capo=capo)
    return with_capo(get_tuning(tuning_key), capo)


def _corrections_path(job_id: str) -> pathlib.Path:
    path = JOBS.root / job_id / "corrections.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _read_corrections(job_id: str) -> list[dict]:
    path = _corrections_path(job_id)
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _append_correction(job_id: str, row: dict) -> None:
    with _corrections_path(job_id).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.8.0"}


@app.get("/tunings")
def tunings():
    return [
        {
            "id": key,
            "name": value.name,
            "open_pitches": value.open_pitches,
            "max_fret": value.max_fret,
        }
        for key, value in TUNINGS.items()
    ]


@app.get("/profiles")
def profiles():
    return [
        {"id": key, "name": value.name, "max_fret_span": value.max_fret_span}
        for key, value in PROFILES.items()
    ]


@app.post("/tab/optimize", response_model=list[TabNoteOut])
def tab_optimize(payload: TabRequest):
    tuning = resolve_setup(
        payload.tuning,
        payload.capo,
        payload.custom_open_pitches,
        payload.custom_name,
    )
    get_profile(payload.profile)
    events = [NoteEvent(**note.model_dump()) for note in payload.notes]
    return [
        TabNoteOut(**tab_note.__dict__)
        for tab_note in optimize_polyphonic_fingering(
            events, tuning, profile=payload.profile
        )
    ]


@app.post("/intelligence")
def intelligence(payload: TabRequest):
    tuning = resolve_setup(
        payload.tuning,
        payload.capo,
        payload.custom_open_pitches,
        payload.custom_name,
    )
    get_profile(payload.profile)
    events = [NoteEvent(**note.model_dump()) for note in payload.notes]
    tab = optimize_polyphonic_fingering(events, tuning, profile=payload.profile)
    return {
        "setup": {
            "name": tuning.name,
            "open_pitches": tuning.open_pitches,
            "capo": tuning.capo,
            "profile": payload.profile,
        },
        "tab": [note.__dict__ for note in tab],
        "intelligence": analyze_guitar_intelligence(tab),
    }


@app.post("/notation")
def notation(payload: NotationRequest):
    tuning = resolve_setup(
        payload.tuning,
        payload.capo,
        payload.custom_open_pitches,
        payload.custom_name,
    )
    get_profile(payload.profile)
    events = [NoteEvent(**note.model_dump()) for note in payload.notes]
    tab = optimize_polyphonic_fingering(events, tuning, profile=payload.profile)
    cfg, quantized = quantize_tab_notes(
        tab,
        bpm=payload.bpm,
        time_signature=TimeSignature(payload.beats, payload.beat_type),
        subdivision=payload.subdivision,
    )
    xml = export_musicxml(quantized, cfg, tuning, title=payload.title)
    return {
        "rhythm": {
            "bpm": cfg.bpm,
            "beats": cfg.time_signature.beats,
            "beat_type": cfg.time_signature.beat_type,
            "divisions": cfg.divisions,
            "subdivision": cfg.subdivision,
            "measure_ticks": cfg.measure_ticks,
        },
        "setup": {
            "name": tuning.name,
            "open_pitches": tuning.open_pitches,
            "capo": tuning.capo,
            "profile": payload.profile,
        },
        "tab": [note.__dict__ for note in tab],
        "intelligence": analyze_guitar_intelligence(tab),
        "quantized_tab": [note.__dict__ for note in quantized],
        "musicxml": xml,
    }


@app.post("/tracks")
async def upload_track(
    file: UploadFile = File(...),
    tuning: str = Form("guitar_standard"),
    dev_passthrough: bool = Form(False),
):
    get_tuning(tuning)
    suffix = pathlib.Path(file.filename or "track.wav").suffix.lower() or ".wav"
    source = UPLOADS / f"{uuid.uuid4()}{suffix}"
    source.write_bytes(await file.read())
    job = JOBS.create(source, tuning, dev_passthrough=dev_passthrough)
    return {"job_id": job.id, "id": job.id, "status": job.status}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job.__dict__


@app.get("/jobs/{job_id}/musicxml")
def get_musicxml(job_id: str):
    job = JOBS.get(job_id)
    if job is None or not job.result:
        raise HTTPException(status_code=404, detail="result not ready")
    path = pathlib.Path(job.result["musicxml"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="MusicXML not found")
    return FileResponse(
        path,
        media_type="application/vnd.recordare.musicxml+xml",
        filename="autotab.musicxml",
    )


@app.get("/jobs/{job_id}/audio")
def get_audio(job_id: str):
    job = JOBS.get(job_id)
    if job is None or not job.source_path:
        raise HTTPException(status_code=404, detail="audio not found")
    path = pathlib.Path(job.source_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="audio not found")
    return FileResponse(path)


@app.get("/jobs/{job_id}/stems/{stem_name}")
def get_stem(job_id: str, stem_name: str):
    job = JOBS.get(job_id)
    if job is None or not job.result:
        raise HTTPException(status_code=404, detail="result not ready")
    stems = job.result.get("stems", {})
    if stem_name not in stems:
        raise HTTPException(status_code=404, detail="stem not found")
    path = pathlib.Path(stems[stem_name])
    if not path.exists():
        raise HTTPException(status_code=404, detail="stem not found")
    return FileResponse(path)


@app.post("/jobs/{job_id}/retune")
def retune_job(job_id: str, payload: RetuneRequest):
    job = JOBS.get(job_id)
    if job is None or not job.result:
        raise HTTPException(status_code=404, detail="result not ready")

    tuning = resolve_setup(
        payload.tuning,
        payload.capo,
        payload.custom_open_pitches,
        payload.custom_name,
    )
    get_profile(payload.profile)

    events = [NoteEvent(**note) for note in job.result.get("notes", [])]
    tab = optimize_polyphonic_fingering(events, tuning, profile=payload.profile)

    rhythm = job.result.get("rhythm", {})
    cfg, quantized = quantize_tab_notes(
        tab,
        bpm=rhythm.get("bpm"),
        time_signature=TimeSignature(
            rhythm.get("beats", 4), rhythm.get("beat_type", 4)
        ),
        subdivision=rhythm.get("subdivision", 4),
    )
    xml = export_musicxml(quantized, cfg, tuning, title="AutoTab Retuned")
    safe_name = payload.tuning if not payload.custom_open_pitches else "custom"
    out = (
        JOBS.root
        / job_id
        / f"score-{safe_name}-capo{payload.capo}-{payload.profile}.musicxml"
    )
    out.write_text(xml, encoding="utf-8")

    job.result.update(
        {
            "tab": [note.__dict__ for note in tab],
            "quantized_tab": [note.__dict__ for note in quantized],
            "tuning": payload.tuning,
            "profile": payload.profile,
            "capo": payload.capo,
            "musicxml": str(out),
            "intelligence": analyze_guitar_intelligence(tab),
        }
    )
    return job.__dict__


@app.get("/jobs/{job_id}/corrections")
def get_corrections(job_id: str):
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {"job_id": job_id, "corrections": _read_corrections(job_id)}


@app.post("/jobs/{job_id}/corrections")
def apply_correction(job_id: str, payload: CorrectionRequest):
    job = JOBS.get(job_id)
    if job is None or not job.result:
        raise HTTPException(status_code=404, detail="result not ready")

    tuning = resolve_setup(
        payload.tuning,
        payload.capo,
        payload.custom_open_pitches,
        payload.custom_name,
    )
    get_profile(payload.profile)

    events = [NoteEvent(**note) for note in job.result.get("notes", [])]
    current_tab = [TabNote(**note) for note in job.result.get("tab", [])]

    target = next(
        (
            note
            for note in current_tab
            if note.chord_index == payload.chord_index
            and note.pitch == payload.pitch
        ),
        None,
    )
    if target is None:
        raise HTTPException(status_code=404, detail="target TAB note not found")

    requested = FingeringAnchor(
        chord_index=payload.chord_index,
        pitch=payload.pitch,
        string_index=payload.string_index,
        fret=payload.fret,
    )

    history = _read_corrections(job_id)
    anchors: list[FingeringAnchor] = [
        FingeringAnchor(
            chord_index=row["chord_index"],
            pitch=row["pitch"],
            string_index=row["new_string_index"],
            fret=row["new_fret"],
        )
        for row in history
    ]

    lo = max(0, payload.chord_index - payload.neighborhood_radius)
    hi = payload.chord_index + payload.neighborhood_radius

    # Freeze everything outside the local neighborhood. The selected chord and
    # its nearby voicings stay free so the optimizer can preserve playability.
    for note in current_tab:
        if note.chord_index < lo or note.chord_index > hi:
            anchors.append(
                FingeringAnchor(
                    chord_index=note.chord_index,
                    pitch=note.pitch,
                    string_index=note.string_index,
                    fret=note.fret,
                )
            )

    # The newest correction replaces any older correction for the same note.
    anchors = [
        anchor
        for anchor in anchors
        if not (
            anchor.chord_index == requested.chord_index
            and anchor.pitch == requested.pitch
        )
    ]
    anchors.append(requested)

    try:
        tab = optimize_with_anchors(
            events,
            tuning,
            anchors,
            profile=payload.profile,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    rhythm = job.result.get("rhythm", {})
    cfg, quantized = quantize_tab_notes(
        tab,
        bpm=rhythm.get("bpm"),
        time_signature=TimeSignature(
            rhythm.get("beats", 4), rhythm.get("beat_type", 4)
        ),
        subdivision=rhythm.get("subdivision", 4),
    )
    xml = export_musicxml(quantized, cfg, tuning, title="AutoTab Corrected")
    out = JOBS.root / job_id / "score-corrected.musicxml"
    out.write_text(xml, encoding="utf-8")

    record = build_correction_record(
        job_id, target, requested, tuning, payload.profile
    )
    _append_correction(job_id, record.to_dict())

    job.result.update(
        {
            "tab": [note.__dict__ for note in tab],
            "quantized_tab": [note.__dict__ for note in quantized],
            "musicxml": str(out),
            "profile": payload.profile,
            "capo": payload.capo,
            "intelligence": analyze_guitar_intelligence(tab),
            "correction_count": len(_read_corrections(job_id)),
        }
    )
    return job.__dict__


@app.delete("/jobs/{job_id}/corrections")
def reset_corrections(job_id: str):
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    path = _corrections_path(job_id)
    if path.exists():
        path.unlink()
    if job.result is not None:
        job.result["correction_count"] = 0
    return {"job_id": job_id, "correction_count": 0}


@app.get("/corrections/dataset")
def corrections_dataset():
    rows: list[dict] = []
    if JOBS.root.exists():
        for path in sorted(JOBS.root.glob("*/corrections.jsonl")):
            job_id = path.parent.name
            rows.extend(_read_corrections(job_id))
    return {"count": len(rows), "records": rows}
