from pydantic import BaseModel, Field


class NoteEventIn(BaseModel):
    pitch: int = Field(ge=0, le=127)
    start: float = Field(ge=0)
    duration: float = Field(gt=0)
    velocity: int = Field(default=90, ge=1, le=127)
    confidence: float = Field(default=1.0, ge=0, le=1)
    pitch_bends: tuple[float, ...] = ()


class TabRequest(BaseModel):
    tuning: str
    notes: list[NoteEventIn]


class NotationRequest(TabRequest):
    bpm: float | None = Field(default=None, gt=0, le=400)
    beats: int = Field(default=4, ge=1, le=16)
    beat_type: int = Field(default=4)
    subdivision: int = Field(default=4, ge=1, le=16)
    title: str = "AutoTab Transcription"


class TabNoteOut(BaseModel):
    pitch: int
    start: float
    duration: float
    string_index: int
    fret: int
    confidence: float
    chord_index: int
