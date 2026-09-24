from __future__ import annotations
from collections import defaultdict
from xml.etree import ElementTree as ET

from .engine import Tuning
from .rhythm import QuantizedTabNote, RhythmConfig, seconds_to_ticks, split_note_at_measures

_PITCH_CLASS = {
    0: ("C", 0), 1: ("C", 1), 2: ("D", 0), 3: ("D", 1),
    4: ("E", 0), 5: ("F", 0), 6: ("F", 1), 7: ("G", 0),
    8: ("G", 1), 9: ("A", 0), 10: ("A", 1), 11: ("B", 0),
}


def midi_pitch_components(midi: int) -> tuple[str, int, int]:
    step, alter = _PITCH_CLASS[midi % 12]
    octave = midi // 12 - 1
    return step, alter, octave


def _duration_type(duration: int, divisions: int) -> str | None:
    return {4*divisions:"whole",2*divisions:"half",divisions:"quarter",divisions//2:"eighth",divisions//4:"16th",divisions//8:"32nd"}.get(duration)


def _sub(parent: ET.Element, tag: str, text: str | int | float | None = None, **attrs) -> ET.Element:
    node = ET.SubElement(parent, tag, {k.replace("_", "-"): str(v) for k, v in attrs.items()})
    if text is not None:
        node.text = str(text)
    return node


def _write_pitch(note_el: ET.Element, midi: int) -> None:
    pitch = _sub(note_el, "pitch")
    step, alter, octave = midi_pitch_components(midi)
    _sub(pitch, "step", step)
    if alter:
        _sub(pitch, "alter", alter)
    _sub(pitch, "octave", octave)


def _write_tie(note_el: ET.Element, start: bool, stop: bool) -> None:
    if start: _sub(note_el, "tie", type="start")
    if stop: _sub(note_el, "tie", type="stop")
    if start or stop:
        notations = _sub(note_el, "notations")
        if start: _sub(notations, "tied", type="start")
        if stop: _sub(notations, "tied", type="stop")


def _write_note(parent: ET.Element, note: QuantizedTabNote, duration: int, staff: int, chord: bool, tie_start: bool, tie_stop: bool, include_technical: bool, divisions: int, total_strings: int) -> None:
    el = _sub(parent, "note")
    if chord: _sub(el, "chord")
    _write_pitch(el, note.pitch)
    _sub(el, "duration", duration)
    _sub(el, "voice", 1)
    typ = _duration_type(duration, divisions)
    if typ: _sub(el, "type", typ)
    _sub(el, "staff", staff)
    _write_tie(el, tie_start, tie_stop)
    if include_technical:
        notations = el.find("notations") or _sub(el, "notations")
        technical = _sub(notations, "technical")
        _sub(technical, "string", total_strings - note.string_index)
        _sub(technical, "fret", note.fret)


def _write_rest(parent: ET.Element, duration: int, staff: int, divisions: int) -> None:
    if duration <= 0: return
    el = _sub(parent, "note")
    _sub(el, "rest")
    _sub(el, "duration", duration)
    _sub(el, "voice", 1)
    typ = _duration_type(duration, divisions)
    if typ: _sub(el, "type", typ)
    _sub(el, "staff", staff)


def _staff_tuning(attributes: ET.Element, tuning: Tuning, staff_number: int = 2) -> None:
    details = _sub(attributes, "staff-details", number=str(staff_number))
    _sub(details, "staff-lines", len(tuning.open_pitches))
    if tuning.capo:
        _sub(details, "capo", tuning.capo)
    for line, midi in enumerate(reversed(tuning.open_pitches), start=1):
        st = _sub(details, "staff-tuning", line=line)
        step, alter, octave = midi_pitch_components(midi)
        _sub(st, "tuning-step", step)
        if alter: _sub(st, "tuning-alter", alter)
        _sub(st, "tuning-octave", octave)


def export_musicxml(
    notes: list[QuantizedTabNote],
    config: RhythmConfig,
    tuning: Tuning,
    title: str = "AutoTab Transcription",
    tab_only: bool = False,
    standard_only: bool = False,
) -> str:
    root = ET.Element("score-partwise", version="4.0")
    work = _sub(root, "work"); _sub(work, "work-title", title)
    identification = _sub(root, "identification")
    encoding = _sub(identification, "encoding"); _sub(encoding, "software", "AutoTab")
    part_list = _sub(root, "part-list")
    score_part = _sub(part_list, "score-part", id="P1"); _sub(score_part, "part-name", tuning.name)
    part = _sub(root, "part", id="P1")
    measure_ticks = config.measure_ticks
    fragments = defaultdict(list)
    max_measure = 0
    for note in notes:
        pieces = split_note_at_measures(note, measure_ticks)
        for idx, (measure_index, local_onset, duration) in enumerate(pieces):
            fragments[measure_index].append((note, local_onset, duration, idx < len(pieces)-1, idx > 0))
            max_measure = max(max_measure, measure_index)
    for measure_index in range(max_measure + 1 if notes else 1):
        measure = _sub(part, "measure", number=measure_index+1)
        if measure_index == 0:
            attributes = _sub(measure, "attributes")
            _sub(attributes, "divisions", config.divisions)
            key = _sub(attributes, "key"); _sub(key, "fifths", 0)
            time = _sub(attributes, "time"); _sub(time, "beats", config.time_signature.beats); _sub(time, "beat-type", config.time_signature.beat_type)
            if standard_only:
                _sub(attributes, "staves", 1)
                clef1 = _sub(attributes, "clef", number="1"); _sub(clef1, "sign", "G"); _sub(clef1, "line", 2)
            elif tab_only:
                _sub(attributes, "staves", 1)
                clef1 = _sub(attributes, "clef", number="1"); _sub(clef1, "sign", "TAB"); _sub(clef1, "line", 5)
                _staff_tuning(attributes, tuning, staff_number=1)
            else:
                _sub(attributes, "staves", 2)
                clef1 = _sub(attributes, "clef", number="1"); _sub(clef1, "sign", "G"); _sub(clef1, "line", 2)
                clef2 = _sub(attributes, "clef", number="2"); _sub(clef2, "sign", "TAB"); _sub(clef2, "line", 5)
                _staff_tuning(attributes, tuning, staff_number=2)
            direction = _sub(measure, "direction", placement="above")
            direction_type = _sub(direction, "direction-type")
            metronome = _sub(direction_type, "metronome"); _sub(metronome, "beat-unit", "quarter"); _sub(metronome, "per-minute", config.bpm)
            _sub(direction, "sound", tempo=config.bpm)
        local = fragments.get(measure_index, [])
        by_onset = defaultdict(list)
        for note, onset, duration, tie_start, tie_stop in local:
            by_onset[onset].append((note, duration, tie_start, tie_stop))
        def write_staff(staff: int, tab: bool) -> None:
            cursor = 0
            for onset in sorted(by_onset):
                chord_notes = sorted(by_onset[onset], key=lambda x: (x[0].pitch, x[0].string_index))
                if onset > cursor:
                    _write_rest(measure, onset-cursor, staff, config.divisions); cursor = onset
                max_duration = 0
                for i, (note, duration, tie_start, tie_stop) in enumerate(chord_notes):
                    _write_note(measure, note, duration, staff, i>0, tie_start, tie_stop, tab, config.divisions, len(tuning.open_pitches))
                    max_duration = max(max_duration, duration)
                cursor = max(cursor, onset + max_duration)
            if cursor < measure_ticks:
                _write_rest(measure, measure_ticks-cursor, staff, config.divisions)
        if standard_only:
            write_staff(1, False)
        elif tab_only:
            write_staff(1, True)
        else:
            write_staff(1, False)
            backup = _sub(measure, "backup"); _sub(backup, "duration", measure_ticks)
            write_staff(2, True)
    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n' + ET.tostring(root, encoding="unicode")


_DRUM_DISPLAY = {
    "kick": ("F", 3, "normal"),
    "snare": ("C", 5, "normal"),
    "tom": ("A", 4, "normal"),
    "hihat": ("G", 5, "x"),
    "cymbal": ("A", 5, "x"),
}


def export_drum_musicxml(
    events: list[dict],
    config: RhythmConfig,
    title: str = "AutoTab Drums",
) -> str:
    root = ET.Element("score-partwise", version="4.0")
    work = _sub(root, "work")
    _sub(work, "work-title", title)
    identification = _sub(root, "identification")
    encoding = _sub(identification, "encoding")
    _sub(encoding, "software", "AutoTab")

    part_list = _sub(root, "part-list")
    score_part = _sub(part_list, "score-part", id="P1")
    _sub(score_part, "part-name", "Drums")

    used = sorted({int(event.get("midi_note", 38)) for event in events})
    for midi_note in used:
        score_inst = _sub(score_part, "score-instrument", id=f"P1-I{midi_note}")
        _sub(score_inst, "instrument-name", f"GM Drum {midi_note}")
        midi_inst = _sub(score_part, "midi-instrument", id=f"P1-I{midi_note}")
        _sub(midi_inst, "midi-channel", 10)
        _sub(midi_inst, "midi-unpitched", midi_note)

    part = _sub(root, "part", id="P1")
    measure_ticks = config.measure_ticks
    grid = max(1, config.grid_ticks)

    quantized: list[tuple[int, dict]] = []
    for event in events:
        raw = seconds_to_ticks(float(event.get("start", 0.0)), config)
        onset = max(0, int(round(raw / grid) * grid))
        quantized.append((onset, event))

    max_tick = max((tick for tick, _ in quantized), default=0)
    max_measure = max_tick // measure_ticks

    grouped: dict[int, list[tuple[int, dict]]] = defaultdict(list)
    for tick, event in quantized:
        grouped[tick // measure_ticks].append((tick % measure_ticks, event))

    for measure_index in range(max_measure + 1 if events else 1):
        measure = _sub(part, "measure", number=measure_index + 1)
        if measure_index == 0:
            attributes = _sub(measure, "attributes")
            _sub(attributes, "divisions", config.divisions)
            time = _sub(attributes, "time")
            _sub(time, "beats", config.time_signature.beats)
            _sub(time, "beat-type", config.time_signature.beat_type)
            clef = _sub(attributes, "clef")
            _sub(clef, "sign", "percussion")
            _sub(clef, "line", 2)

            direction = _sub(measure, "direction", placement="above")
            direction_type = _sub(direction, "direction-type")
            metronome = _sub(direction_type, "metronome")
            _sub(metronome, "beat-unit", "quarter")
            _sub(metronome, "per-minute", config.bpm)
            _sub(direction, "sound", tempo=config.bpm)

        cursor = 0
        by_onset: dict[int, list[dict]] = defaultdict(list)
        for onset, event in grouped.get(measure_index, []):
            by_onset[onset].append(event)

        for onset in sorted(by_onset):
            if onset > cursor:
                _write_rest(measure, onset - cursor, 1, config.divisions)
                cursor = onset

            for i, event in enumerate(by_onset[onset]):
                drum = str(event.get("drum", "snare"))
                step, octave, notehead = _DRUM_DISPLAY.get(drum, _DRUM_DISPLAY["snare"])
                midi_note = int(event.get("midi_note", 38))
                note_el = _sub(measure, "note")
                if i > 0:
                    _sub(note_el, "chord")
                unpitched = _sub(note_el, "unpitched")
                _sub(unpitched, "display-step", step)
                _sub(unpitched, "display-octave", octave)
                _sub(note_el, "duration", grid)
                _sub(note_el, "instrument", id=f"P1-I{midi_note}")
                _sub(note_el, "voice", 1)
                typ = _duration_type(grid, config.divisions)
                if typ:
                    _sub(note_el, "type", typ)
                if notehead == "x":
                    _sub(note_el, "notehead", "x")
                _sub(note_el, "staff", 1)

            cursor = max(cursor, onset + grid)

        if cursor < measure_ticks:
            _write_rest(measure, measure_ticks - cursor, 1, config.divisions)

    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n' + ET.tostring(root, encoding="unicode")
