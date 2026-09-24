from __future__ import annotations

import json
import pathlib
import importlib.util
import shutil
import subprocess
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
    Tuning,
    get_profile,
    group_simultaneous_events,
    get_tuning,
    make_custom_tuning,
    optimize_polyphonic_fingering,
    optimize_polyphonic_fingering_robust,
    with_capo,
)
from music_engine.corrections import (
    FingeringAnchor,
    build_correction_record,
    optimize_with_anchors,
)
from music_engine.intelligence import analyze_guitar_intelligence
from music_engine.learned_ranker import LearnedRankerModel, optimize_polyphonic_fingering_learned, train_pairwise_ranker
from music_engine.rhythm import TimeSignature, quantize_tab_notes
from music_engine.musicxml import export_musicxml, export_drum_musicxml
from music_engine.tuning_intelligence import suggest_tunings
from music_engine.accuracy import confidence_summary, evaluate_note_events

from .schemas import NotationRequest, TabNoteOut, TabRequest
from .services.jobs import JobService

UPLOADS = ROOT / "artifacts" / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)
JOBS = JobService(ROOT / "artifacts" / "jobs")

app = FastAPI(title="AutoTab API", version="0.16.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RetuneRequest(BaseModel):
    part: str = "guitar"
    tuning: str = "guitar_standard"
    profile: str = "original_like"
    capo: int = Field(default=0, ge=0, le=12)
    custom_open_pitches: list[int] | None = None
    custom_name: str = "Custom tuning"
    use_learned_ranker: bool = False
    ranker_strength: float = Field(default=0.55, ge=0.0, le=2.0)


class BenchmarkNote(BaseModel):
    pitch: int = Field(ge=0, le=127)
    start: float = Field(ge=0)
    duration: float = Field(gt=0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class BenchmarkRequest(BaseModel):
    part: str = "guitar"
    onset_tolerance: float = Field(default=0.08, gt=0.0, le=0.5)
    reference: list[BenchmarkNote]


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





def _drum_proxy(events: list[dict]) -> list[TabNote]:
    proxy: list[TabNote] = []
    grouped: list[tuple[float, list[dict]]] = []
    for event in sorted(events, key=lambda row: float(row.get("start", 0.0))):
        start = float(event.get("start", 0.0))
        if not grouped or abs(grouped[-1][0] - start) > 0.035:
            grouped.append((start, [event]))
        else:
            grouped[-1][1].append(event)

    for chord_index, (start, rows) in enumerate(grouped):
        for row in rows:
            proxy.append(
                TabNote(
                    pitch=int(row.get("midi_note", 38)),
                    start=start,
                    duration=0.08,
                    string_index=0,
                    fret=0,
                    confidence=float(row.get("confidence", 0.8)),
                    chord_index=chord_index,
                )
            )
    return proxy


def _score_proxy(events: list[NoteEvent]) -> list[TabNote]:
    proxy: list[TabNote] = []
    for chord_index, group in enumerate(group_simultaneous_events(events)):
        for event in group.events:
            proxy.append(
                TabNote(
                    pitch=event.pitch,
                    start=event.start,
                    duration=event.duration,
                    string_index=0,
                    fret=0,
                    confidence=event.confidence,
                    chord_index=chord_index,
                )
            )
    return proxy


def _part_events(job, part: str) -> list[NoteEvent]:
    tracks = job.result.get("tracks", {}) if job.result else {}
    if tracks:
        if part not in tracks:
            raise HTTPException(status_code=422, detail=f"part '{part}' is not available")
        return [NoteEvent(**note) for note in tracks[part].get("notes", [])]
    if part != job.result.get("selected_part", "guitar"):
        raise HTTPException(status_code=422, detail=f"part '{part}' is not available")
    return [NoteEvent(**note) for note in job.result.get("notes", [])]


def _corrections_path(job_id: str, part: str = "guitar") -> pathlib.Path:
    filename = "corrections.jsonl" if part == "guitar" else f"corrections-{part}.jsonl"
    path = JOBS.root / job_id / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _read_corrections(job_id: str, part: str = "guitar") -> list[dict]:
    path = _corrections_path(job_id, part)
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _append_correction(job_id: str, row: dict, part: str = "guitar") -> None:
    with _corrections_path(job_id, part).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _ranker_path() -> pathlib.Path:
    path = ROOT / "artifacts" / "models" / "fingering_ranker.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_ranker() -> LearnedRankerModel | None:
    path = _ranker_path()
    if not path.exists():
        return None
    return LearnedRankerModel.from_dict(json.loads(path.read_text(encoding="utf-8")))


def _save_ranker(model: LearnedRankerModel) -> None:
    _ranker_path().write_text(json.dumps(model.to_dict(), indent=2), encoding="utf-8")


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.16.0"}


@app.get("/diagnostics/ml")
def diagnostics_ml():
    details = {
        "python": sys.version.split()[0],
        "python_executable": sys.executable,
        "demucs_import": importlib.util.find_spec("demucs") is not None,
        "basic_pitch_import": importlib.util.find_spec("basic_pitch") is not None,
        "ffmpeg": shutil.which("ffmpeg"),
        "preferred_demucs_model": "htdemucs_6s",
        "fallback_demucs_model": "htdemucs",
    }
    if details["demucs_import"]:
        try:
            probe = subprocess.run(
                [sys.executable, "-m", "demucs", "--help"],
                capture_output=True,
                text=True,
                timeout=20,
            )
            details["demucs_cli_ok"] = probe.returncode == 0
            if probe.returncode != 0:
                details["demucs_cli_error"] = (probe.stderr or probe.stdout or "")[-2000:]
        except Exception as exc:
            details["demucs_cli_ok"] = False
            details["demucs_cli_error"] = str(exc)
    else:
        details["demucs_cli_ok"] = False

    ready = (
        details["demucs_import"]
        and details["basic_pitch_import"]
        and bool(details["ffmpeg"])
        and details["demucs_cli_ok"]
    )
    return {"ready": ready, **details}


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



@app.get("/jobs/{job_id}/confidence")
def job_confidence(job_id: str, part: str = "guitar"):
    job = JOBS.get(job_id)
    if job is None or not job.result:
        raise HTTPException(status_code=404, detail="result not ready")
    tracks = job.result.get("tracks", {})
    track = tracks.get(part)
    if track is None:
        raise HTTPException(status_code=404, detail=f"part '{part}' not found")
    if track.get("kind") == "drums":
        events = track.get("events", [])
        if not events:
            return {"job_id": job_id, "part": part, "note_count": 0, "windows": [], "weak_windows": []}
        pseudo = [
            NoteEvent(
                pitch=int(row.get("midi_note", 38)),
                start=float(row.get("start", 0.0)),
                duration=0.08,
                confidence=float(row.get("confidence", 0.8)),
            )
            for row in events
        ]
        summary = confidence_summary(pseudo)
    else:
        summary = track.get("confidence") or confidence_summary(
            [NoteEvent(**row) for row in track.get("notes", [])]
        )
    return {"job_id": job_id, "part": part, **summary}


@app.post("/jobs/{job_id}/benchmark")
def benchmark_job(job_id: str, payload: BenchmarkRequest):
    job = JOBS.get(job_id)
    if job is None or not job.result:
        raise HTTPException(status_code=404, detail="result not ready")
    if payload.part == "drums":
        raise HTTPException(status_code=422, detail="drum benchmark uses a separate event schema")
    prediction = _part_events(job, payload.part)
    reference = [
        NoteEvent(
            pitch=row.pitch,
            start=row.start,
            duration=row.duration,
            confidence=row.confidence,
        )
        for row in payload.reference
    ]
    metrics = evaluate_note_events(
        reference,
        prediction,
        onset_tolerance=payload.onset_tolerance,
    )
    result = {
        "job_id": job_id,
        "part": payload.part,
        "onset_tolerance": payload.onset_tolerance,
        "metrics": metrics.to_dict(),
    }
    benchmark_path = JOBS.root / job_id / f"benchmark-{payload.part}.json"
    benchmark_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


@app.get("/jobs/{job_id}/parts")
def job_parts(job_id: str):
    job = JOBS.get(job_id)
    if job is None or not job.result:
        raise HTTPException(status_code=404, detail="result not ready")
    tracks = job.result.get("tracks", {})
    if not tracks:
        selected = job.result.get("selected_part", "guitar")
        return {"job_id": job_id, "parts": [{"id": selected, "stem": None, "note_count": len(job.result.get("notes", []))}]}
    return {
        "job_id": job_id,
        "parts": [
            {
                "id": key,
                "kind": value.get("kind", "strings"),
                "stem": value.get("stem"),
                "note_count": len(value.get("notes", [])) if value.get("kind") != "drums" else len(value.get("events", [])),
                "virtual": bool(value.get("virtual", False)),
                "role_confidence": value.get("role_confidence"),
                "role_explanation": value.get("role_explanation", []),
            }
            for key, value in tracks.items()
        ],
    }


@app.get("/jobs/{job_id}/tuning-suggestions")
def tuning_suggestions(job_id: str, family: str = "guitar", part: str = "guitar", limit: int = 5):
    job = JOBS.get(job_id)
    if job is None or not job.result:
        raise HTTPException(status_code=404, detail="result not ready")
    if family not in {"guitar", "bass", "all"}:
        raise HTTPException(status_code=422, detail="family must be guitar, bass or all")
    if part in {"piano", "drums"}:
        return {
            "job_id": job_id,
            "family": family,
            "part": part,
            "suggestions": [],
            "disclaimer": "This part does not use string tuning compatibility.",
        }
    events = _part_events(job, part)
    suggestions = suggest_tunings(events, family=family, limit=limit)
    return {
        "job_id": job_id,
        "family": family,
        "part": part,
        "suggestions": [item.to_dict() for item in suggestions],
        "disclaimer": "Compatibility is inferred from transcribed pitches and ergonomics; it is not proof of the recorded instrument's original tuning.",
    }


@app.get("/jobs/{job_id}/musicxml")
def get_musicxml(job_id: str, view: str = "full"):
    job = JOBS.get(job_id)
    if job is None or not job.result:
        raise HTTPException(status_code=404, detail="result not ready")
    if view not in {"full", "tab"}:
        raise HTTPException(status_code=422, detail="view must be full or tab")
    key = "musicxml_tab" if view == "tab" else "musicxml"
    source = job.result.get(key) or job.result.get("musicxml")
    path = pathlib.Path(source)
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

    if payload.part == "drums":
        track = job.result.get("tracks", {}).get("drums", {})
        drum_events = track.get("events", [])
        proxy = _drum_proxy(drum_events)
        rhythm = job.result.get("rhythm", {})
        cfg, quantized = quantize_tab_notes(
            proxy,
            bpm=rhythm.get("bpm"),
            time_signature=TimeSignature(
                rhythm.get("beats", 4), rhythm.get("beat_type", 4)
            ),
            subdivision=rhythm.get("subdivision", 4),
        )
        xml = export_drum_musicxml(drum_events, cfg, title="AutoTab Drums")
        out = JOBS.root / job_id / "score-drums.musicxml"
        out.write_text(xml, encoding="utf-8")
        job.result.update(
            {
                "selected_part": "drums",
                "notes": [],
                "drum_events": drum_events,
                "tab": [],
                "quantized_tab": [note.__dict__ for note in quantized],
                "tuning": "drums",
                "profile": "percussion",
                "capo": 0,
                "musicxml": str(out),
                "musicxml_tab": str(out),
                "intelligence": {},
                "ranker": {"enabled": False, "examples": 0},
                "techniques": [],
                "correction_count": 0,
            }
        )
        return job.__dict__

    events = _part_events(job, payload.part)

    if payload.part == "piano":
        proxy = _score_proxy(events)
        rhythm = job.result.get("rhythm", {})
        cfg, quantized = quantize_tab_notes(
            proxy,
            bpm=rhythm.get("bpm"),
            time_signature=TimeSignature(
                rhythm.get("beats", 4), rhythm.get("beat_type", 4)
            ),
            subdivision=rhythm.get("subdivision", 4),
        )
        piano_tuning = Tuning("Piano", (21,))
        xml = export_musicxml(
            quantized,
            cfg,
            piano_tuning,
            title="AutoTab Piano",
            standard_only=True,
        )
        out = JOBS.root / job_id / "score-piano.musicxml"
        out.write_text(xml, encoding="utf-8")
        job.result.update(
            {
                "selected_part": "piano",
                "notes": [note.__dict__ for note in events],
                "tab": [],
                "quantized_tab": [note.__dict__ for note in quantized],
                "tuning": "piano",
                "profile": "score",
                "capo": 0,
                "musicxml": str(out),
                "musicxml_tab": str(out),
                "intelligence": {},
                "ranker": {"enabled": False, "examples": 0},
                "techniques": [],
                "correction_count": 0,
            }
        )
        return job.__dict__

    tuning = resolve_setup(
        payload.tuning,
        payload.capo,
        payload.custom_open_pitches,
        payload.custom_name,
    )
    get_profile(payload.profile)

    model = _load_ranker() if payload.use_learned_ranker and payload.part.startswith("guitar") else None
    if model is not None and model.examples > 0:
        tab = optimize_polyphonic_fingering_learned(
            events, tuning, model, profile=payload.profile, strength=payload.ranker_strength
        )
        ranker_meta = {"enabled": True, "examples": model.examples, "version": model.version, "strength": payload.ranker_strength}
    else:
        tab, robust_diagnostics = optimize_polyphonic_fingering_robust(
            events, tuning, profile=payload.profile
        )
        ranker_meta = {
            "enabled": False,
            "examples": model.examples if model else 0,
            "robust_fingering": robust_diagnostics.__dict__,
        }

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
    tab_xml = export_musicxml(
        quantized,
        cfg,
        tuning,
        title="AutoTab TAB",
        tab_only=True,
    )
    safe_name = payload.tuning if not payload.custom_open_pitches else "custom"
    out = (
        JOBS.root
        / job_id
        / f"score-{payload.part}-{safe_name}-capo{payload.capo}-{payload.profile}.musicxml"
    )
    tab_out = (
        JOBS.root
        / job_id
        / f"score-{payload.part}-{safe_name}-capo{payload.capo}-{payload.profile}-tab.musicxml"
    )
    out.write_text(xml, encoding="utf-8")
    tab_out.write_text(tab_xml, encoding="utf-8")

    job.result.update(
        {
            "selected_part": payload.part,
            "notes": [note.__dict__ for note in events],
            "tab": [note.__dict__ for note in tab],
            "quantized_tab": [note.__dict__ for note in quantized],
            "tuning": payload.tuning,
            "profile": payload.profile,
            "capo": payload.capo,
            "musicxml": str(out),
            "musicxml_tab": str(tab_out),
            "intelligence": analyze_guitar_intelligence(tab),
            "ranker": ranker_meta,
        }
    )
    return job.__dict__


@app.get("/jobs/{job_id}/corrections")
def get_corrections(job_id: str, part: str = "guitar"):
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {"job_id": job_id, "part": part, "corrections": _read_corrections(job_id, part)}


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

    events = _part_events(job, payload.part)
    if job.result.get("selected_part", payload.part) != payload.part:
        raise HTTPException(
            status_code=422,
            detail="generate TAB for this instrument part before editing its fingering",
        )
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

    history = _read_corrections(job_id, payload.part)
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
    tab_xml = export_musicxml(
        quantized,
        cfg,
        tuning,
        title="AutoTab TAB Corrected",
        tab_only=True,
    )
    out = JOBS.root / job_id / f"score-{payload.part}-corrected.musicxml"
    tab_out = JOBS.root / job_id / f"score-{payload.part}-corrected-tab.musicxml"
    out.write_text(xml, encoding="utf-8")
    tab_out.write_text(tab_xml, encoding="utf-8")

    record = build_correction_record(
        job_id, target, requested, tuning, payload.profile
    )
    _append_correction(job_id, record.to_dict(), payload.part)

    job.result.update(
        {
            "selected_part": payload.part,
            "notes": [note.__dict__ for note in events],
            "tab": [note.__dict__ for note in tab],
            "quantized_tab": [note.__dict__ for note in quantized],
            "musicxml": str(out),
            "musicxml_tab": str(tab_out),
            "profile": payload.profile,
            "capo": payload.capo,
            "intelligence": analyze_guitar_intelligence(tab),
            "correction_count": len(_read_corrections(job_id, payload.part)),
        }
    )
    return job.__dict__


@app.delete("/jobs/{job_id}/corrections")
def reset_corrections(job_id: str, part: str = "guitar"):
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    path = _corrections_path(job_id, part)
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



@app.post("/ranker/train")
def train_ranker():
    dataset = corrections_dataset()["records"]
    model = train_pairwise_ranker(dataset)
    _save_ranker(model)
    return model.to_dict()


@app.get("/ranker/status")
def ranker_status():
    model = _load_ranker()
    if model is None:
        return {"trained": False, "examples": 0}
    return {"trained": model.examples > 0, **model.to_dict()}
