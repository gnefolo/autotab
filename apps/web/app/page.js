'use client';
import { useEffect, useMemo, useRef, useState } from 'react';

const tunings = [
  ['guitar_standard', 'Standard · E A D G B E'],
  ['guitar_drop_d', 'Drop D · D A D G B E'],
  ['guitar_eb', 'Eb Standard'],
  ['guitar_d_standard', 'D Standard'],
  ['guitar_drop_c_sharp', 'Drop C#'],
  ['guitar_drop_c', 'Drop C'],
  ['guitar_standard_7', '7-string Standard · B E A D G B E'],
  ['guitar_standard_8', '8-string Standard · F# B E A D G B E'],
  ['bass_standard_4', 'Bass Standard · E A D G'],
  ['bass_drop_d_4', 'Bass Drop D'],
  ['bass_standard_5', '5-string Bass · B E A D G'],
];

const API = process.env.NEXT_PUBLIC_AUTOTAB_API || 'http://localhost:8000';
const fmt = s => `${Math.floor((s || 0) / 60)}:${String(Math.floor((s || 0) % 60)).padStart(2, '0')}`;

const COPY = {
  it: {
    tagline: 'Da audio a TAB suonabile.',
    uploadTitle: 'Carica un brano',
    uploadBody: 'AutoTab separa le tracce, trascrive le note e prepara una base musicale neutra. Le impostazioni dello strumento vengono scelte dopo.',
    chooseFile: 'Scegli file audio',
    replaceFile: 'Cambia file',
    noTrack: 'Nessun brano selezionato',
    analyze: 'Analizza traccia',
    analyzing: 'Analisi',
    complete: 'Analisi completata',
    failed: 'Analisi fallita',
    uploadFail: 'Upload fallito. Verifica che AutoTab sia avviato.',
    apiFail: 'Impossibile raggiungere AutoTab API.',
    setup: 'Impostazioni strumento',
    setupBody: 'Scegli come vuoi suonare il brano. La TAB viene rigenerata dalle note già trascritte, senza rianalizzare l’audio.',
    tuning: 'Accordatura',
    profile: 'Profilo',
    capo: 'Capotasto',
    custom: 'Custom tuning · MIDI',
    apply: 'Genera TAB',
    regenerate: 'Rigenera TAB',
    applying: 'Generazione TAB…',
    retuneFail: 'Rigenerazione TAB fallita',
    retuned: 'TAB rigenerata',
    part: 'Parte',
    guitarPart: 'Chitarra',
    bassPart: 'Basso',
    pianoPart: 'Piano / Tastiere',
    generateScore: 'Genera partitura',
    pianoMode: 'Modalità partitura',
    pianoModeHelp: 'Per Piano/Keys AutoTab genera notazione standard dalle note trascritte. Accordatura, capo e fingering non si applicano.',
    partHelp: 'Scegli la parte strumentale da trasformare in TAB.',
    suggestions: 'Compatibilità accordatura',
    suggestionsHelp: 'Stima di compatibilità fisica con le note trascritte, non identificazione certa dell’accordatura originale.',
    guitar: 'Chitarra',
    bass: 'Basso',
    coverage: 'copertura',
    select: 'Usa',
    noSuggestions: 'Nessun suggerimento disponibile',
    learned: 'Ranker appreso',
    useLearned: 'Usa preferenze apprese',
    strength: 'Forza',
    corrections: 'correzioni',
    profileOriginal: 'Original-like',
    profileEasy: 'Facile',
    profileRhythm: 'Ritmica',
    profileLead: 'Solista',
    score: 'Partitura + TAB',
    inspector: 'Inspector',
    detectedChords: 'Accordi rilevati',
    analysis: 'Analisi',
    notes: 'note',
    filtered: 'filtrate',
    correction: 'Correzione fingering',
    correctionHelp: 'Seleziona una nota dalla lista per correggere corda e tasto.',
    string: 'Corda',
    fret: 'Tasto',
    radius: 'Raggio locale',
    saveCorrection: 'Salva correzione',
    clearCorrections: 'Azzera storico',
    correctionApplying: 'Applicazione correzione…',
    correctionRejected: 'Correzione rifiutata',
    correctionSaved: 'Correzione salvata',
    correctionsCleared: 'Storico correzioni azzerato',
    transport: 'Transport',
    mixer: 'Stem mixer',
    original: 'Originale',
    clearLoop: 'Reset loop',
    newTrack: 'Nuovo brano',
    settings: 'Setup',
    ready: 'READY',
    processing: 'PROCESSING',
    failedState: 'FAILED',
    noScore: 'Genera la TAB per aprire il workspace.',
    bpm: 'BPM',
    selectedNote: 'Nota selezionata',
    noNote: 'Nessuna nota selezionata',
    midi: 'MIDI',
    chord: 'Chord',
    technique: 'Tecniche',
    fullScore: 'Partitura + TAB',
    tabOnly: 'Solo TAB',
    songAudio: 'Canzone',
    tabAudio: 'TAB',
    hideSetup: 'Nascondi setup',
    showSetup: 'Mostra setup',
    hideInspector: 'Nascondi inspector',
    showInspector: 'Mostra inspector',
    listen: 'Ascolto',
    zoom: 'Zoom',
    fit: 'Adatta',
    measuresPerLine: 'Misure/riga',
  },
  en: {
    tagline: 'From audio to playable TAB.',
    uploadTitle: 'Upload a song',
    uploadBody: 'AutoTab separates stems, transcribes notes and creates a neutral musical base. Instrument settings are chosen afterwards.',
    chooseFile: 'Choose audio file',
    replaceFile: 'Change file',
    noTrack: 'No track selected',
    analyze: 'Analyze track',
    analyzing: 'Analysis',
    complete: 'Analysis complete',
    failed: 'Analysis failed',
    uploadFail: 'Upload failed. Make sure AutoTab is running.',
    apiFail: 'Cannot reach AutoTab API.',
    setup: 'Instrument setup',
    setupBody: 'Choose how you want to play the song. TAB is regenerated from the existing transcription without analyzing the audio again.',
    tuning: 'Tuning',
    profile: 'Profile',
    capo: 'Capo',
    custom: 'Custom tuning · MIDI',
    apply: 'Generate TAB',
    regenerate: 'Regenerate TAB',
    applying: 'Generating TAB…',
    retuneFail: 'TAB regeneration failed',
    retuned: 'TAB regenerated',
    part: 'Part',
    guitarPart: 'Guitar',
    bassPart: 'Bass',
    pianoPart: 'Piano / Keys',
    generateScore: 'Generate score',
    pianoMode: 'Score mode',
    pianoModeHelp: 'For Piano/Keys AutoTab generates standard notation from the transcription. Tuning, capo and string fingering do not apply.',
    partHelp: 'Choose the instrument part to turn into TAB.',
    suggestions: 'Tuning compatibility',
    suggestionsHelp: 'Physical compatibility estimate against transcribed notes, not certain identification of the original recorded tuning.',
    guitar: 'Guitar',
    bass: 'Bass',
    coverage: 'coverage',
    select: 'Use',
    noSuggestions: 'No suggestions available',
    learned: 'Learned ranker',
    useLearned: 'Use learned preferences',
    strength: 'Strength',
    corrections: 'corrections',
    profileOriginal: 'Original-like',
    profileEasy: 'Easy',
    profileRhythm: 'Rhythm',
    profileLead: 'Lead',
    score: 'Score + TAB',
    inspector: 'Inspector',
    detectedChords: 'Detected chords',
    analysis: 'Analysis',
    notes: 'notes',
    filtered: 'filtered',
    correction: 'Fingering correction',
    correctionHelp: 'Select a note from the list to correct its string and fret.',
    string: 'String',
    fret: 'Fret',
    radius: 'Local radius',
    saveCorrection: 'Save correction',
    clearCorrections: 'Clear history',
    correctionApplying: 'Applying correction…',
    correctionRejected: 'Correction rejected',
    correctionSaved: 'Correction saved',
    correctionsCleared: 'Correction history cleared',
    transport: 'Transport',
    mixer: 'Stem mixer',
    original: 'Original',
    clearLoop: 'Reset loop',
    newTrack: 'New track',
    settings: 'Setup',
    ready: 'READY',
    processing: 'PROCESSING',
    failedState: 'FAILED',
    noScore: 'Generate TAB to open the workspace.',
    bpm: 'BPM',
    selectedNote: 'Selected note',
    noNote: 'No note selected',
    midi: 'MIDI',
    chord: 'Chord',
    technique: 'Techniques',
    fullScore: 'Score + TAB',
    tabOnly: 'TAB only',
    songAudio: 'Song',
    tabAudio: 'TAB',
    hideSetup: 'Hide setup',
    showSetup: 'Show setup',
    hideInspector: 'Hide inspector',
    showInspector: 'Show inspector',
    listen: 'Listen',
    zoom: 'Zoom',
    fit: 'Fit',
    measuresPerLine: 'Measures/line',
  }
};

export default function Home() {
  const [lang, setLang] = useState('it');
  const [setupApplied, setSetupApplied] = useState(false);
  const [file, setFile] = useState(null);
  const [tuning, setTuning] = useState('guitar_standard');
  const [instrumentFamily, setInstrumentFamily] = useState('guitar');
  const [availableParts, setAvailableParts] = useState([]);
  const [selectedPart, setSelectedPart] = useState('guitar');
  const [tuningSuggestions, setTuningSuggestions] = useState([]);
  const [profile, setProfile] = useState('original_like');
  const [capo, setCapo] = useState(0);
  const [custom, setCustom] = useState('');
  const [useRanker, setUseRanker] = useState(false);
  const [rankerStrength, setRankerStrength] = useState(0.55);
  const [rankerStatus, setRankerStatus] = useState(null);
  const [message, setMessage] = useState('');
  const [job, setJob] = useState(null);
  const [speed, setSpeed] = useState(1);
  const [loopA, setLoopA] = useState(null);
  const [loopB, setLoopB] = useState(null);
  const [current, setCurrent] = useState(0);
  const [duration, setDuration] = useState(0);
  const [mix, setMix] = useState({ original: { volume: 1, muted: false } });
  const [solo, setSolo] = useState(null);
  const [selected, setSelected] = useState(null);
  const [editString, setEditString] = useState(0);
  const [editFret, setEditFret] = useState(0);
  const [radius, setRadius] = useState(2);
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);
  const [scoreView, setScoreView] = useState('tab');
  const [listenMode, setListenMode] = useState('song');
  const [scoreZoom, setScoreZoom] = useState(1.08);
  const [measuresPerLine, setMeasuresPerLine] = useState(4);

  const timer = useRef(null);
  const audio = useRef(null);
  const stemAudios = useRef({});
  const scoreHost = useRef(null);
  const osmd = useRef(null);
  const cursorIndex = useRef(-1);
  const synthContext = useRef(null);
  const synthNodes = useRef([]);
  const synthInterval = useRef(null);
  const synthScheduledUntil = useRef(0);
  const listenModeRef = useRef('song');
  const scoreRenderTimer = useRef(null);
  const scoreRenderWidth = useRef(0);
  const scoreLoadKey = useRef('');

  const t = COPY[lang];
  const filename = useMemo(() => file?.name || t.noTrack, [file, t.noTrack]);
  const ready = job?.status === 'completed' && job?.result;
  const stemNames = ready ? Object.keys(job.result.stems || {}) : [];
  const correctionCount = ready ? (job.result.correction_count || 0) : 0;
  const diagnostics = ready ? (job.result.fingering_diagnostics || job.result.ranker?.robust_fingering || {}) : {};
  const techniques = ready ? (job.result.techniques || []) : [];


  function partLabel(partId) {
    if (partId === 'bass') return t.bassPart;
    if (partId === 'piano') return t.pianoPart;
    return t.guitarPart;
  }

  function setupPayload() {
    return {
      part: selectedPart,
      tuning,
      profile,
      capo,
      custom_open_pitches: custom.trim() ? custom.split(',').map(x => Number(x.trim())) : null,
      custom_name: 'Custom tuning',
      use_learned_ranker: useRanker,
      ranker_strength: rankerStrength,
    };
  }

  function stopPolling() {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
  }

  async function poll(id) {
    try {
      const res = await fetch(`${API}/jobs/${id}`);
      const data = await res.json();
      setJob(data);
      if (data.status === 'completed') {
        setMessage(t.complete);
        stopPolling();
        return;
      }
      if (data.status === 'failed') {
        setMessage(`${t.failed}: ${data.stage || 'unknown'} · ${data.error || ''}`);
        stopPolling();
        return;
      }
      setMessage(`${data.stage || data.status} · ${data.progress}%`);
      timer.current = setTimeout(() => poll(id), 900);
    } catch {
      setMessage(t.apiFail);
      stopPolling();
    }
  }

  async function upload() {
    if (!file) return;
    stopPolling();
    setJob(null);
    setSelected(null);
    setSetupApplied(false);
    setMessage(t.analyzing);
    const fd = new FormData();
    fd.append('file', file);
    fd.append('tuning', 'guitar_standard');
    try {
      const res = await fetch(`${API}/tracks`, { method: 'POST', body: fd });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setJob(data);
      poll(data.job_id);
    } catch {
      setMessage(t.uploadFail);
    }
  }

  async function retune() {
    if (!job?.id) return;
    setMessage(t.applying);
    const res = await fetch(`${API}/jobs/${job.id}/retune`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(setupPayload()),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setMessage(data.detail || t.retuneFail);
      return;
    }
    const data = await res.json();
    setJob(data);
    setSelected(null);
    setSetupApplied(true);
    setMessage(t.retuned);
  }

  function resetProject() {
    stopPolling();
    if (audio.current) audio.current.pause();
    Object.values(stemAudios.current).forEach(a => a?.pause());
    setFile(null);
    setJob(null);
    setSetupApplied(false);
    setMessage('');
    setSelected(null);
    setCurrent(0);
    setDuration(0);
    setLoopA(null);
    setLoopB(null);
    setTuningSuggestions([]);
    setAvailableParts([]);
    setSelectedPart('guitar');
    setInstrumentFamily('guitar');
    setLeftOpen(true);
    setRightOpen(true);
    setScoreView('tab');
    setListenMode('song');
    listenModeRef.current = 'song';
    setScoreZoom(1.08);
    setMeasuresPerLine(4);
    stopTabSynth();
  }

  function chooseNote(n) {
    setSelected(n);
    setEditString(n.string_index);
    setEditFret(n.fret);
    if (audio.current) seek(n.start);
  }

  async function saveCorrection() {
    if (!job?.id || !selected) return;
    setMessage(t.correctionApplying);
    const payload = {
      ...setupPayload(),
      chord_index: selected.chord_index,
      pitch: selected.pitch,
      string_index: Number(editString),
      fret: Number(editFret),
      neighborhood_radius: Number(radius),
    };
    const res = await fetch(`${API}/jobs/${job.id}/corrections`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      setMessage(data.detail || t.correctionRejected);
      return;
    }
    setJob(data);
    const updated = (data.result?.tab || []).find(
      n => n.chord_index === selected.chord_index && n.pitch === selected.pitch
    );
    setSelected(updated || null);
    setMessage(t.correctionSaved);
  }

  async function clearCorrectionHistory() {
    if (!job?.id) return;
    const res = await fetch(`${API}/jobs/${job.id}/corrections?part=${selectedPart}`, { method: 'DELETE' });
    if (res.ok) {
      setJob(prev => ({ ...prev, result: { ...prev.result, correction_count: 0 } }));
      setMessage(t.correctionsCleared);
    }
  }

  useEffect(() => {
    const saved = window.localStorage.getItem('autotab-lang');
    if (saved === 'it' || saved === 'en') setLang(saved);
    return () => {
      stopPolling();
      stopTabSynth();
      if (synthContext.current) synthContext.current.close().catch(() => {});
    };
  }, []);

  useEffect(() => {
    window.localStorage.setItem('autotab-lang', lang);
    document.documentElement.lang = lang;
  }, [lang]);

  useEffect(() => {
    fetch(`${API}/ranker/status`).then(r => r.json()).then(setRankerStatus).catch(() => {});
  }, []);

  useEffect(() => {
    if (!ready || setupApplied) return;
    fetch(`${API}/jobs/${job.id}/parts`)
      .then(r => r.json())
      .then(d => {
        const parts = d.parts || [];
        setAvailableParts(parts);
        if (parts.length && !parts.some(p => p.id === selectedPart)) {
          setSelectedPart(parts[0].id);
        }
      })
      .catch(() => setAvailableParts([]));
  }, [ready, setupApplied, job?.id]);

  useEffect(() => {
    if (selectedPart === 'bass') {
      setInstrumentFamily('bass');
      if (!tuning.startsWith('bass_')) setTuning('bass_standard_4');
    } else if (selectedPart === 'guitar') {
      setInstrumentFamily('guitar');
      if (tuning.startsWith('bass_') || tuning === 'piano') setTuning('guitar_standard');
    } else if (selectedPart === 'piano') {
      setScoreView('full');
      setUseRanker(false);
      setRightOpen(false);
    }
  }, [selectedPart]);

  useEffect(() => {
    if (!ready || setupApplied) return;
    if (selectedPart === 'piano') {
      setTuningSuggestions([]);
      return;
    }
    fetch(`${API}/jobs/${job.id}/tuning-suggestions?family=${instrumentFamily}&part=${selectedPart}&limit=5`)
      .then(r => r.json())
      .then(d => setTuningSuggestions(d.suggestions || []))
      .catch(() => setTuningSuggestions([]));
  }, [ready, setupApplied, job?.id, instrumentFamily, selectedPart]);

  useEffect(() => {
    if (audio.current) audio.current.playbackRate = speed;
    Object.values(stemAudios.current).forEach(a => { if (a) a.playbackRate = speed; });
    if (listenMode === 'tab' && audio.current && !audio.current.paused) {
      stopTabSynth();
      synthScheduledUntil.current = audio.current.currentTime;
      startTabSynth();
    }
  }, [speed]);

  useEffect(() => {
    if (!ready) return;
    const next = { original: mix.original || { volume: 1, muted: false } };
    stemNames.forEach(name => {
      next[name] = mix[name] || {
        volume: name === 'other' || name === 'guitar' ? 1 : 0.35,
        muted: false,
      };
    });
    setMix(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, job?.id]);

  useEffect(() => {
    if (!ready || !setupApplied || !scoreHost.current) return;
    let cancelled = false;

    (async () => {
      const { OpenSheetMusicDisplay } = await import('opensheetmusicdisplay');
      if (cancelled || !scoreHost.current) return;

      const loadKey = `${job.id}:${scoreView}:${job.result?.musicxml}:${job.result?.musicxml_tab}:${correctionCount}`;
      let viewer = osmd.current;

      if (!viewer || scoreLoadKey.current !== loadKey) {
        scoreHost.current.innerHTML = '';
        viewer = new OpenSheetMusicDisplay(scoreHost.current, {
          autoResize: false,
          backend: 'svg',
          drawingParameters: 'compacttight',
          drawTitle: false,
          followCursor: true,
        });
        osmd.current = viewer;
        scoreLoadKey.current = loadKey;
        await viewer.load(`${API}/jobs/${job.id}/musicxml?view=${scoreView}&ts=${Date.now()}`);
      }

      if (cancelled) return;

      const width = scoreHost.current.clientWidth || 1000;
      const adaptiveMeasures = scoreView === 'tab'
        ? (width < 820 ? 3 : width < 1180 ? 4 : width < 1500 ? 5 : 6)
        : (width < 820 ? 2 : width < 1180 ? 3 : width < 1500 ? 4 : 5);

      setMeasuresPerLine(adaptiveMeasures);
      viewer.Zoom = scoreZoom;

      const rules = viewer.EngravingRules;
      rules.PageLeftMargin = 0.6;
      rules.PageRightMargin = 0.6;
      rules.PageTopMargin = 0.5;
      rules.PageBottomMargin = 1.2;
      rules.SystemLeftMargin = 0.0;
      rules.SystemRightMargin = 0.0;
      rules.MinimumDistanceBetweenSystems = scoreView === 'tab' ? 6.5 : 7.5;
      rules.MinSkyBottomDistBetweenSystems = scoreView === 'tab' ? 4.0 : 4.8;
      rules.BetweenStaffDistance = scoreView === 'tab' ? 3.8 : 5.0;
      rules.TabStaffInterlineHeight = scoreView === 'tab' ? 1.34 : 1.22;
      rules.TabStaffInterlineHeightForBboxes = scoreView === 'tab' ? 1.52 : 1.40;
      rules.RenderXMeasuresPerLineAkaSystem = adaptiveMeasures;
      rules.StretchLastSystemLine = false;
      rules.LastSystemMaxScalingFactor = 1.08;

      await viewer.render();
      if (cancelled) return;

      scoreRenderWidth.current = width;
      viewer.cursor.show();
      viewer.cursor.reset();
      cursorIndex.current = -1;
    })().catch(e => setMessage(`Score render error: ${e.message}`));

    return () => { cancelled = true; };
  }, [
    ready,
    setupApplied,
    job?.id,
    job?.result?.musicxml,
    job?.result?.musicxml_tab,
    correctionCount,
    scoreView,
  ]);

  useEffect(() => {
    if (!ready || !setupApplied || !osmd.current || !scoreHost.current) return;
    const viewer = osmd.current;
    viewer.Zoom = scoreZoom;
    clearTimeout(scoreRenderTimer.current);
    scoreRenderTimer.current = setTimeout(() => {
      try {
        viewer.render();
      } catch (error) {
        setMessage(`Score render error: ${error?.message || error}`);
      }
    }, 40);
    return () => clearTimeout(scoreRenderTimer.current);
  }, [scoreZoom, ready, setupApplied]);

  useEffect(() => {
    if (!ready || !setupApplied) return;

    function stableReflow() {
      if (!osmd.current || !scoreHost.current) return;
      const width = scoreHost.current.clientWidth || 0;
      if (!width || Math.abs(width - scoreRenderWidth.current) < 24) return;

      scoreRenderWidth.current = width;
      const adaptiveMeasures = scoreView === 'tab'
        ? (width < 820 ? 3 : width < 1180 ? 4 : width < 1500 ? 5 : 6)
        : (width < 820 ? 2 : width < 1180 ? 3 : width < 1500 ? 4 : 5);

      setMeasuresPerLine(adaptiveMeasures);
      osmd.current.EngravingRules.RenderXMeasuresPerLineAkaSystem = adaptiveMeasures;
      clearTimeout(scoreRenderTimer.current);
      scoreRenderTimer.current = setTimeout(() => {
        try {
          osmd.current?.render();
        } catch (error) {
          setMessage(`Score render error: ${error?.message || error}`);
        }
      }, 140);
    }

    const afterPanelAnimation = setTimeout(stableReflow, 180);
    window.addEventListener('resize', stableReflow);
    return () => {
      clearTimeout(afterPanelAnimation);
      clearTimeout(scoreRenderTimer.current);
      window.removeEventListener('resize', stableReflow);
    };
  }, [leftOpen, rightOpen, scoreView, ready, setupApplied]);

  function getSynthContext() {
    if (!synthContext.current) {
      synthContext.current = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (synthContext.current.state === 'suspended') synthContext.current.resume();
    return synthContext.current;
  }

  function stopTabSynth() {
    if (synthInterval.current) {
      clearInterval(synthInterval.current);
      synthInterval.current = null;
    }
    synthNodes.current.forEach(node => {
      try { node.stop(); } catch {}
      try { node.disconnect(); } catch {}
    });
    synthNodes.current = [];
  }

  function scheduleTabWindow() {
    const master = audio.current;
    const notes = job?.result?.tab || [];
    if (!master || master.paused || listenModeRef.current !== 'tab' || !notes.length) return;
    const ctx = getSynthContext();
    const songNow = master.currentTime;
    const from = Math.max(songNow - 0.02, synthScheduledUntil.current);
    const to = songNow + Math.max(1.5, 2.5 * speed);
    if (to <= from) return;

    notes
      .filter(note => note.start >= from && note.start < to)
      .forEach(note => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        const frequency = 440 * Math.pow(2, (note.pitch - 69) / 12);
        const when = ctx.currentTime + Math.max(0, (note.start - songNow) / speed);
        const duration = Math.max(0.04, Math.min(2.0, (note.duration || 0.15) / speed));
        const level = 0.035 + 0.055 * Math.max(0.15, Math.min(1, note.confidence ?? 0.8));

        osc.type = 'triangle';
        osc.frequency.setValueAtTime(frequency, when);
        gain.gain.setValueAtTime(0.0001, when);
        gain.gain.exponentialRampToValueAtTime(level, when + 0.008);
        gain.gain.exponentialRampToValueAtTime(0.0001, when + duration);

        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(when);
        osc.stop(when + duration + 0.02);
        synthNodes.current.push(osc);
      });

    synthScheduledUntil.current = to;
    synthNodes.current = synthNodes.current.filter(node => {
      try { return node.context === ctx; } catch { return false; }
    });
  }

  function startTabSynth() {
    stopTabSynth();
    synthScheduledUntil.current = audio.current?.currentTime || 0;
    scheduleTabWindow();
    synthInterval.current = setInterval(scheduleTabWindow, 450);
  }

  function changeListenMode(mode) {
    listenModeRef.current = mode;
    setListenMode(mode);
    const master = audio.current;
    if (!master) return;
    if (mode === 'tab') {
      master.muted = true;
      Object.values(stemAudios.current).forEach(a => { if (a) a.pause(); });
      if (!master.paused) {
        setTimeout(() => {
          synthScheduledUntil.current = master.currentTime;
          startTabSynth();
        }, 0);
      }
    } else {
      stopTabSynth();
      master.muted = effectiveMuted('original');
      if (!master.paused) {
        syncStemTransport(master);
        Object.values(stemAudios.current).forEach(a => a?.play().catch(() => {}));
      }
    }
  }

  function effectiveMuted(name) {
    return solo ? name !== solo : !!mix[name]?.muted;
  }

  function applyMix(name, patch) {
    setMix(prev => ({
      ...prev,
      [name]: { ...(prev[name] || { volume: 1, muted: false }), ...patch },
    }));
  }

  function syncStemTransport(master) {
    Object.entries(stemAudios.current).forEach(([name, a]) => {
      if (!a) return;
      a.volume = Math.max(0, Math.min(1, mix[name]?.volume ?? 1));
      a.muted = effectiveMuted(name);
      a.playbackRate = speed;
      if (Math.abs(a.currentTime - master.currentTime) > 0.08) a.currentTime = master.currentTime;
    });
  }

  async function togglePlayback() {
    const master = audio.current;
    if (!master) return;
    master.volume = Math.max(0, Math.min(1, mix.original?.volume ?? 1));

    if (master.paused) {
      if (listenModeRef.current === 'tab') {
        master.muted = true;
        Object.values(stemAudios.current).forEach(a => a?.pause());
        await master.play();
        startTabSynth();
      } else {
        stopTabSynth();
        master.muted = effectiveMuted('original');
        syncStemTransport(master);
        await Promise.allSettled([
          master.play(),
          ...Object.values(stemAudios.current).map(a => a?.play()),
        ]);
      }
    } else {
      master.pause();
      Object.values(stemAudios.current).forEach(a => a?.pause());
      stopTabSynth();
    }
  }

  function syncCursor(time) {
    const q = job?.result?.quantized_tab || [];
    if (!osmd.current || !q.length) return;
    const onsets = [...new Set(q.map(n => n.original_start))].sort((a, b) => a - b);
    let idx = onsets.findIndex(x => x > time);
    idx = idx === -1 ? onsets.length - 1 : Math.max(0, idx - 1);
    if (idx === cursorIndex.current) return;
    osmd.current.cursor.reset();
    for (let i = 0; i < idx; i++) osmd.current.cursor.next();
    osmd.current.cursor.show();
    cursorIndex.current = idx;

    const cursorEl = scoreHost.current?.querySelector('.osmd-cursor');
    const scroller = scoreHost.current?.closest('.scoreCanvas');
    if (cursorEl && scroller) {
      const cursorRect = cursorEl.getBoundingClientRect();
      const scrollRect = scroller.getBoundingClientRect();
      const upper = scrollRect.top + 90;
      const lower = scrollRect.bottom - 120;
      if (cursorRect.top < upper || cursorRect.bottom > lower) {
        cursorEl.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
      }
    }
  }

  function onTime() {
    const a = audio.current;
    if (!a) return;
    if (loopA != null && loopB != null && a.currentTime >= loopB) {
      a.currentTime = loopA;
      Object.values(stemAudios.current).forEach(s => { if (s) s.currentTime = loopA; });
      if (listenMode === 'tab') {
        stopTabSynth();
        synthScheduledUntil.current = loopA;
        startTabSynth();
      }
    }
    if (listenModeRef.current === 'song') syncStemTransport(a);
    setCurrent(a.currentTime);
    syncCursor(a.currentTime);
  }

  function seek(value) {
    const next = Number(value);
    if (!audio.current) return;
    audio.current.currentTime = next;
    setCurrent(next);
    syncCursor(next);
    Object.values(stemAudios.current).forEach(a => { if (a) a.currentTime = next; });
    if (listenModeRef.current === 'tab' && !audio.current.paused) {
      stopTabSynth();
      synthScheduledUntil.current = next;
      startTabSynth();
    }
  }

  function fitScore() {
    setScoreZoom(scoreView === 'tab' ? 1.16 : 1.08);
  }

  const statusLabel = job?.status === 'failed'
    ? t.failedState
    : job?.status === 'processing'
      ? t.processing
      : ready
        ? t.ready
        : 'IDLE';

  return (
    <main className={`appRoot ${setupApplied ? 'workspaceMode' : ''}`}>
      <header className="appTopbar">
        <div className="brandBlock">
          <div className="brandMark">A</div>
          <div>
            <div className="brandName">AUTOTAB</div>
            <div className="brandTagline">{t.tagline}</div>
          </div>
        </div>

        <div className="projectIdentity">
          {file && <span className="projectFile">{file.name}</span>}
          <span className={`systemState state-${job?.status || 'idle'}`}>{statusLabel}</span>
        </div>

        <div className="topbarActions">
          {file && <button className="topAction" onClick={resetProject}>{t.newTrack}</button>}
          <div className="languageToggle">
            <button className={lang === 'it' ? 'active' : ''} onClick={() => setLang('it')}>IT</button>
            <button className={lang === 'en' ? 'active' : ''} onClick={() => setLang('en')}>EN</button>
          </div>
          <span className="versionTag">0.13</span>
        </div>
      </header>

      {!ready && (
        <section className="ingestScreen">
          <div className="ingestIntro">
            <span className="sectionKicker">01 / INPUT</span>
            <h1>{t.uploadTitle}</h1>
            <p>{t.uploadBody}</p>
          </div>

          <div className="uploadZone">
            <input
              id="audio-upload"
              className="nativeFileInput"
              type="file"
              accept="audio/*"
              onChange={e => setFile(e.target.files?.[0] || null)}
            />
            <label className="uploadTarget" htmlFor="audio-upload">
              <span className="uploadGlyph">＋</span>
              <span className="uploadPrimary">{file ? t.replaceFile : t.chooseFile}</span>
              <span className="uploadFilename">{filename}</span>
            </label>

            <button className="primaryAction" disabled={!file || job?.status === 'processing'} onClick={upload}>
              {job?.status === 'processing' ? `${t.analyzing} · ${job.progress || 0}%` : t.analyze}
            </button>

            {job?.status === 'processing' && (
              <div className="analysisProgress">
                <div className="progressMeta">
                  <span>{job.stage || t.analyzing}</span>
                  <span>{job.progress || 0}%</span>
                </div>
                <div className="progressTrack">
                  <div style={{ width: `${job.progress || 0}%` }} />
                </div>
              </div>
            )}

            {message && <div className={`systemMessage ${job?.status === 'failed' ? 'error' : ''}`}>{message}</div>}
          </div>
        </section>
      )}

      {ready && !setupApplied && (
        <section className="setupScreen">
          <aside className="setupRail">
            <span className="sectionKicker">02 / {t.settings.toUpperCase()}</span>
            <h1>{t.setup}</h1>
            <p>{t.setupBody}</p>

            {availableParts.length > 0 && (
              <div className="controlGroup">
                <label>{t.part}</label>
                <div className="segmented partSelector">
                  {availableParts.map(part => (
                    <button
                      key={part.id}
                      className={selectedPart === part.id ? 'active' : ''}
                      onClick={() => setSelectedPart(part.id)}
                    >
                      {partLabel(part.id)}
                      <small>{part.note_count} {t.notes}</small>
                    </button>
                  ))}
                </div>
                <div className="microCopy">{t.partHelp}</div>
              </div>
            )}

            {selectedPart === 'piano' ? (
              <div className="pianoModeCard">
                <div className="sectionLabel">{t.pianoMode}</div>
                <p className="microCopy">{t.pianoModeHelp}</p>
              </div>
            ) : <>
            <div className="controlGroup">
              <label>{t.tuning}</label>
              <select value={tuning} onChange={e => setTuning(e.target.value)}>
                {tunings.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
              </select>
            </div>

            <div className="controlGroup">
              <label>{t.profile}</label>
              <select value={profile} onChange={e => setProfile(e.target.value)}>
                <option value="original_like">{t.profileOriginal}</option>
                <option value="easy">{t.profileEasy}</option>
                <option value="rhythm">{t.profileRhythm}</option>
                <option value="lead">{t.profileLead}</option>
              </select>
            </div>

            <div className="splitControls">
              <div className="controlGroup">
                <label>{t.capo}</label>
                <input type="number" min="0" max="12" value={capo} onChange={e => setCapo(Number(e.target.value))} />
              </div>
              <div className="controlGroup">
                <label>{t.custom}</label>
                <input placeholder="38,45,50,55,59,64" value={custom} onChange={e => setCustom(e.target.value)} />
              </div>
            </div>

            {selectedPart === 'guitar' && <div className="rankerControl">
              <label className="checkRow">
                <input type="checkbox" checked={useRanker} onChange={e => setUseRanker(e.target.checked)} />
                <span>{t.useLearned}</span>
              </label>
              <input
                className="slider"
                type="range"
                min="0"
                max="1.5"
                step="0.05"
                value={rankerStrength}
                onChange={e => setRankerStrength(Number(e.target.value))}
              />
              <div className="microMeta">{t.strength} {rankerStrength.toFixed(2)} · {rankerStatus?.examples || 0} {t.corrections}</div>
            </div>}</>}

            <button className="primaryAction" onClick={retune}>{selectedPart === 'piano' ? t.generateScore : t.apply}</button>
            {message && <div className="systemMessage">{message}</div>}
          </aside>

          {selectedPart === 'piano' ? (
            <section className="compatibilityWorkspace pianoWorkspace">
              <div className="workspaceHeader">
                <div>
                  <span className="sectionKicker">PIANO / KEYS</span>
                  <h2>{t.pianoMode}</h2>
                </div>
                <div className="partStatus"><span>{t.part}</span><strong>{t.pianoPart}</strong></div>
              </div>
              <p className="workspaceHint">{t.pianoModeHelp}</p>
              <div className="pianoSummary">
                <span>{availableParts.find(p => p.id === 'piano')?.note_count || 0}</span>
                <small>{t.notes}</small>
              </div>
            </section>
          ) : <section className="compatibilityWorkspace">
            <div className="workspaceHeader">
              <div>
                <span className="sectionKicker">TUNING INTELLIGENCE</span>
                <h2>{t.suggestions}</h2>
              </div>
              <div className="partStatus">
                <span>{t.part}</span>
                <strong>{partLabel(selectedPart)}</strong>
              </div>
            </div>

            <p className="workspaceHint">{t.suggestionsHelp}</p>

            <div className="compatibilityTable">
              <div className="compatibilityHead">
                <span>#</span>
                <span>{t.tuning}</span>
                <span>Score</span>
                <span>{t.coverage}</span>
                <span></span>
              </div>
              {tuningSuggestions.length === 0 && <div className="emptyRow">{t.noSuggestions}</div>}
              {tuningSuggestions.map((item, index) => (
                <button
                  key={item.tuning_id}
                  className={`compatibilityRow ${tuning === item.tuning_id ? 'selected' : ''}`}
                  onClick={() => setTuning(item.tuning_id)}
                >
                  <span className="rankCell">{String(index + 1).padStart(2, '0')}</span>
                  <span className="tuningCell">
                    <strong>{item.name}</strong>
                    <small>{item.lowest_observed_pitch != null ? `low MIDI ${item.lowest_observed_pitch}` : ''}</small>
                  </span>
                  <span className="scoreCell">{item.score}</span>
                  <span className="coverageCell">
                    <span>{Math.round((item.coverage || 0) * 100)}%</span>
                    <span className="coverageBar"><i style={{ width: `${Math.round((item.coverage || 0) * 100)}%` }} /></span>
                  </span>
                  <span className="useCell">{t.select}</span>
                </button>
              ))}
            </div>
          </section>}
        </section>
      )}

      {ready && setupApplied && (
        <section className={`workspaceShell ${!leftOpen ? 'leftCollapsed' : ''} ${!rightOpen ? 'rightCollapsed' : ''}`}>
          {leftOpen && <aside className="leftSidebar">
            <div className="panelHeader">
              <span className="sectionKicker">02 / {t.settings.toUpperCase()}</span>
              <strong>{t.setup}</strong>
            </div>

            <div className="sidebarBody">
              {availableParts.length > 1 && (
                <div className="controlGroup">
                  <label>{t.part}</label>
                  <select
                    value={selectedPart}
                    onChange={e => setSelectedPart(e.target.value)}
                  >
                    {availableParts.map(part => (
                      <option key={part.id} value={part.id}>
                        {partLabel(part.id)}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              {selectedPart !== 'piano' && <>
              <div className="controlGroup">
                <label>{t.tuning}</label>
                <select value={tuning} onChange={e => setTuning(e.target.value)}>
                  {tunings.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
                </select>
              </div>

              <div className="controlGroup">
                <label>{t.profile}</label>
                <select value={profile} onChange={e => setProfile(e.target.value)}>
                  <option value="original_like">{t.profileOriginal}</option>
                  <option value="easy">{t.profileEasy}</option>
                  <option value="rhythm">{t.profileRhythm}</option>
                  <option value="lead">{t.profileLead}</option>
                </select>
              </div>

              <div className="splitControls verticalSplit">
                <div className="controlGroup">
                  <label>{t.capo}</label>
                  <input type="number" min="0" max="12" value={capo} onChange={e => setCapo(Number(e.target.value))} />
                </div>
                <div className="controlGroup">
                  <label>{t.custom}</label>
                  <input value={custom} onChange={e => setCustom(e.target.value)} />
                </div>
              </div>

              </>}
              <button className="secondaryAction" onClick={retune}>
                {selectedPart === 'piano' ? t.generateScore : t.regenerate}
              </button>

              <div className="sidebarSection">
                <div className="sectionLabel">{t.analysis}</div>
                <div className="statGrid">
                  <div><span>{t.bpm}</span><strong>{job.result.rhythm?.bpm || '—'}</strong></div>
                  <div><span>{t.notes}</span><strong>{selectedPart === 'piano' ? (job.result.notes?.length || 0) : (job.result.tab?.length || 0)}</strong></div>
                  <div><span>{t.filtered}</span><strong>{diagnostics.filtered_out_of_range?.length || 0}</strong></div>
                  <div><span>{t.corrections}</span><strong>{correctionCount}</strong></div>
                </div>
              </div>

              <div className="sidebarSection">
                <div className="sectionLabel">{t.detectedChords}</div>
                <div className="chordList">
                  {(job.result.intelligence?.chords || []).slice(0, 16).map(c => (
                    <span key={c.chord_index}>{c.name}</span>
                  ))}
                </div>
              </div>

              {message && <div className="systemMessage compact">{message}</div>}
            </div>
          </aside>}

          <section className="scoreWorkspace">
            <div className="scoreToolbar">
              <div className="toolbarIdentity">
                <span className="sectionKicker">03 / WORKSPACE</span>
                <strong>{scoreView === 'tab' ? t.tabOnly : t.fullScore}</strong>
              </div>

              <div className="workspaceControls">
                <button className="panelToggle" onClick={() => setLeftOpen(v => !v)}>
                  {leftOpen ? '◀' : '▶'} {leftOpen ? t.hideSetup : t.showSetup}
                </button>

                {selectedPart !== 'piano' && <div className="viewToggle">
                  <button className={scoreView === 'tab' ? 'active' : ''} onClick={() => setScoreView('tab')}>{t.tabOnly}</button>
                  <button className={scoreView === 'full' ? 'active' : ''} onClick={() => setScoreView('full')}>{t.fullScore}</button>
                </div>}

                <div className="zoomControls">
                  <button onClick={() => setScoreZoom(z => Math.max(0.82, Number((z - 0.08).toFixed(2))))}>−</button>
                  <span>{Math.round(scoreZoom * 100)}%</span>
                  <button onClick={() => setScoreZoom(z => Math.min(1.48, Number((z + 0.08).toFixed(2))))}>＋</button>
                  <button className="fitButton" onClick={fitScore}>{t.fit}</button>
                </div>

                <button className="panelToggle" onClick={() => setRightOpen(v => !v)}>
                  {rightOpen ? t.hideInspector : t.showInspector} {rightOpen ? '▶' : '◀'}
                </button>
              </div>

              <div className="scoreMeta">
                <span>{partLabel(selectedPart)}</span>
                {selectedPart !== 'piano' && <span>{tuning.replaceAll('_', ' ')}</span>}
                {selectedPart !== 'piano' && <span>{profile}</span>}
                {selectedPart !== 'piano' && <span>Capo {capo}</span>}
                <span>{measuresPerLine} {t.measuresPerLine}</span>
              </div>
            </div>
            <div className="scoreCanvas">
              <div ref={scoreHost} />
            </div>
          </section>

          {rightOpen && selectedPart !== 'piano' && <aside className="rightInspector">
            <div className="panelHeader">
              <span className="sectionKicker">INSPECTOR</span>
              <strong>{t.inspector}</strong>
            </div>

            <div className="inspectorBody">
              <div className="inspectorSection">
                <div className="sectionLabel">{t.selectedNote}</div>
                {!selected && <div className="emptyInspector">{t.noNote}</div>}
                {selected && (
                  <>
                    <div className="selectedNoteSummary">
                      <div><span>{t.midi}</span><strong>{selected.pitch}</strong></div>
                      <div><span>{t.string}</span><strong>{selected.string_index + 1}</strong></div>
                      <div><span>{t.fret}</span><strong>{selected.fret}</strong></div>
                      <div><span>#</span><strong>{selected.chord_index}</strong></div>
                    </div>
                    <div className="editGrid">
                      <div className="controlGroup">
                        <label>{t.string}</label>
                        <input type="number" min="0" max="7" value={editString} onChange={e => setEditString(Number(e.target.value))} />
                      </div>
                      <div className="controlGroup">
                        <label>{t.fret}</label>
                        <input type="number" min="0" max="24" value={editFret} onChange={e => setEditFret(Number(e.target.value))} />
                      </div>
                      <div className="controlGroup span2">
                        <label>{t.radius}</label>
                        <input type="number" min="0" max="12" value={radius} onChange={e => setRadius(Number(e.target.value))} />
                      </div>
                    </div>
                    <button className="primaryAction smallAction" onClick={saveCorrection}>{t.saveCorrection}</button>
                    {correctionCount > 0 && <button className="textAction" onClick={clearCorrectionHistory}>{t.clearCorrections}</button>}
                  </>
                )}
              </div>

              <div className="inspectorSection noteBrowserSection">
                <div className="sectionLabel">{t.correction}</div>
                <p className="microCopy">{t.correctionHelp}</p>
                <div className="noteBrowser">
                  {(job.result.tab || []).slice(0, 220).map((n, i) => (
                    <button
                      key={`${n.chord_index}-${n.pitch}-${i}`}
                      className={selected?.chord_index === n.chord_index && selected?.pitch === n.pitch ? 'active' : ''}
                      onClick={() => chooseNote(n)}
                    >
                      <span>#{n.chord_index}</span>
                      <span>M{n.pitch}</span>
                      <span>S{n.string_index + 1}</span>
                      <span>F{n.fret}</span>
                    </button>
                  ))}
                </div>
              </div>

              {techniques.length > 0 && (
                <div className="inspectorSection">
                  <div className="sectionLabel">{t.technique}</div>
                  <div className="techniqueList">
                    {techniques.slice(0, 12).map((tech, i) => (
                      <div key={i}>
                        <strong>{tech.technique || tech.type || 'hint'}</strong>
                        <span>{tech.chord_index != null ? `#${tech.chord_index}` : ''}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </aside>}

          <footer className="bottomDock">
            <audio
              ref={audio}
              src={`${API}/jobs/${job.id}/audio`}
              onTimeUpdate={onTime}
              onLoadedMetadata={e => {
                setCurrent(0);
                setDuration(Number.isFinite(e.currentTarget.duration) ? e.currentTarget.duration : 0);
              }}
            />
            {stemNames.map(name => (
              <audio
                key={name}
                ref={el => { stemAudios.current[name] = el; }}
                src={`${API}/jobs/${job.id}/stems/${encodeURIComponent(name)}`}
              />
            ))}

            <div className="transportBar">
              <button className="playButton" onClick={togglePlayback}>▶︎</button>
              <div className="listenToggle" title={t.listen}>
                <button className={listenMode === 'song' ? 'active' : ''} onClick={() => changeListenMode('song')}>{t.songAudio}</button>
                <button className={listenMode === 'tab' ? 'active' : ''} onClick={() => changeListenMode('tab')}>{t.tabAudio}</button>
              </div>
              <span className="timeReadout">{fmt(current)}</span>
              <input
                className="timeline"
                type="range"
                min="0"
                max={duration || 1}
                step="0.01"
                value={Math.min(current, duration || 1)}
                onChange={e => seek(e.target.value)}
              />
              <span className="timeReadout">{fmt(duration)}</span>
              <select className="speedSelect" value={speed} onChange={e => setSpeed(Number(e.target.value))}>
                {[0.5, 0.75, 1, 1.25, 1.5, 2].map(x => <option key={x} value={x}>{x}×</option>)}
              </select>
              <button className="transportButton" onClick={() => setLoopA(current)}>A {loopA == null ? '—' : fmt(loopA)}</button>
              <button className="transportButton" onClick={() => setLoopB(current)}>B {loopB == null ? '—' : fmt(loopB)}</button>
              <button className="transportButton" onClick={() => { setLoopA(null); setLoopB(null); }}>{t.clearLoop}</button>
            </div>

            <div className={`stemStrip ${listenMode === 'tab' ? 'disabledMix' : ''}`}>
              {['original', ...stemNames].map(name => (
                <div className="stemChannel" key={name}>
                  <span className="stemName">{name === 'original' ? t.original : name}</span>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={mix[name]?.volume ?? 1}
                    onChange={e => applyMix(name, { volume: Number(e.target.value) })}
                  />
                  <span className="stemLevel">{Math.round((mix[name]?.volume ?? 1) * 100)}</span>
                  <button className={mix[name]?.muted ? 'active' : ''} onClick={() => applyMix(name, { muted: !mix[name]?.muted })}>M</button>
                  <button className={solo === name ? 'active' : ''} onClick={() => setSolo(solo === name ? null : name)}>S</button>
                </div>
              ))}
            </div>
          </footer>
        </section>
      )}
    </main>
  );
}
