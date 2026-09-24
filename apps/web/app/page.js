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
const fmt = s => `${Math.floor((s||0)/60)}:${String(Math.floor((s||0)%60)).padStart(2,'0')}`;

const COPY = {
  it: {
    hero:"Carica un brano. AutoTab lo analizza e poi ti lascia scegliere come vuoi suonarlo.",
    uploadTitle:"1 · Carica e analizza",
    audio:"Brano audio",
    noTrack:"Nessun brano selezionato",
    analyze:"Analizza traccia",
    analyzing:"Analisi in corso",
    setupTitle:"2 · Impostazioni strumento",
    setupHelp:"L'audio è stato analizzato. Ora scegli accordatura, profilo e capotasto: AutoTab rigenera la TAB senza rianalizzare il brano.",
    tuning:"Accordatura",
    profile:"Profilo",
    capo:"Capotasto",
    custom:"Accordatura custom · MIDI",
    apply:"Applica impostazioni e genera TAB",
    regenerate:"Rigenera TAB",
    practice:"3 · Suona e correggi",
    analysis:"Analisi",
    detectedChords:"Accordi rilevati",
    mixer:"Mixer stem",
    correction:"Editor correzioni",
    correctionHelp:"Seleziona una nota e correggi corda/tasto. AutoTab mantiene la stessa altezza musicale e riottimizza localmente.",
    string:"Corda",
    fret:"Tasto",
    radius:"Raggio locale",
    saveCorrection:"Salva correzione",
    clearCorrections:"Azzera storico correzioni",
    noReady:"Carica e analizza un brano per iniziare.",
    complete:"Analisi completata",
    uploadFail:"Upload fallito. Avvia l'API su localhost:8000.",
    retuneFail:"Rigenerazione TAB fallita",
    retuned:"TAB rigenerata senza rianalizzare l'audio",
    applying:"Applicazione impostazioni…",
    upload:"Caricamento…",
    apiFail:"Impossibile raggiungere l'API AutoTab",
    failed:"Analisi fallita",
    original:"Originale",
    clearLoop:"Azzera loop",
    learned:"Ranker appreso",
    useLearned:"Usa preferenze apprese",
    train:"Allena / aggiorna ranker",
    corrections:"correzioni",
    notes:"note",
    step:"PASSO",
    strength:"Forza",
    correctionApplying:"Applicazione correzione e riottimizzazione locale…",
    correctionRejected:"Correzione rifiutata",
    correctionSaved:"Correzione salvata · fingering locale riottimizzato",
    correctionsCleared:"Storico correzioni azzerato",
    profileOriginal:"Original-like",
    profileEasy:"Facile",
    profileRhythm:"Ritmica",
    profileLead:"Solista",
    suggestions:"Compatibilità accordatura",
    suggestionsHelp:"AutoTab confronta le note trascritte con le accordature disponibili. È un suggerimento di compatibilità, non la prova dell'accordatura originale.",
    guitar:"Chitarra",
    bass:"Basso",
    compatible:"compatibile",
    select:"Seleziona",
    noSuggestions:"Nessun suggerimento disponibile",
  },
  en: {
    hero:"Upload a song. AutoTab analyzes it first, then lets you decide how you want to play it.",
    uploadTitle:"1 · Upload & analyze",
    audio:"Audio track",
    noTrack:"No track selected",
    analyze:"Analyze track",
    analyzing:"Analyzing",
    setupTitle:"2 · Instrument setup",
    setupHelp:"The audio has been analyzed. Now choose tuning, playing profile and capo: AutoTab regenerates TAB without analyzing the song again.",
    tuning:"Tuning",
    profile:"Playing profile",
    capo:"Capo",
    custom:"Custom tuning · MIDI",
    apply:"Apply setup and generate TAB",
    regenerate:"Regenerate TAB",
    practice:"3 · Practice & correct",
    analysis:"Analysis",
    detectedChords:"Detected chords",
    mixer:"Stem mixer",
    correction:"Correction editor",
    correctionHelp:"Select a note and correct string/fret. AutoTab preserves the musical pitch and re-optimizes locally.",
    string:"String",
    fret:"Fret",
    radius:"Local radius",
    saveCorrection:"Save correction",
    clearCorrections:"Clear correction history",
    noReady:"Upload and analyze a track to begin.",
    complete:"Analysis complete",
    uploadFail:"Upload failed. Start the API on localhost:8000.",
    retuneFail:"TAB regeneration failed",
    retuned:"TAB regenerated without re-analyzing audio",
    applying:"Applying setup…",
    upload:"Uploading…",
    apiFail:"Cannot reach AutoTab API",
    failed:"Analysis failed",
    original:"Original",
    clearLoop:"Clear loop",
    learned:"Learned ranker",
    useLearned:"Use learned fingering preferences",
    train:"Train / refresh ranker",
    corrections:"corrections",
    notes:"notes",
    step:"STEP",
    strength:"Strength",
    correctionApplying:"Applying correction and re-optimizing nearby voicings…",
    correctionRejected:"Correction rejected",
    correctionSaved:"Correction saved · local fingering re-optimized",
    correctionsCleared:"Correction history cleared",
    profileOriginal:"Original-like",
    profileEasy:"Easy",
    profileRhythm:"Rhythm",
    profileLead:"Lead",
    suggestions:"Tuning compatibility",
    suggestionsHelp:"AutoTab compares the transcribed pitches with available tunings. This is a compatibility suggestion, not proof of the original recorded tuning.",
    guitar:"Guitar",
    bass:"Bass",
    compatible:"compatible",
    select:"Select",
    noSuggestions:"No suggestions available",
  }
};

export default function Home() {
  const [lang,setLang]=useState('it');
  const [setupApplied,setSetupApplied]=useState(false);
  const [file,setFile]=useState(null), [tuning,setTuning]=useState('guitar_standard');
  const [instrumentFamily,setInstrumentFamily]=useState('guitar'), [tuningSuggestions,setTuningSuggestions]=useState([]);
  const [profile,setProfile]=useState('original_like'), [capo,setCapo]=useState(0), [custom,setCustom]=useState('');
  const [useRanker,setUseRanker]=useState(false), [rankerStrength,setRankerStrength]=useState(0.55), [rankerStatus,setRankerStatus]=useState(null);
  const [message,setMessage]=useState(''), [job,setJob]=useState(null), [speed,setSpeed]=useState(1);
  const [loopA,setLoopA]=useState(null), [loopB,setLoopB]=useState(null), [current,setCurrent]=useState(0);
  const [mix,setMix]=useState({original:{volume:1,muted:false}}), [solo,setSolo]=useState(null);
  const [selected,setSelected]=useState(null), [editString,setEditString]=useState(0), [editFret,setEditFret]=useState(0), [radius,setRadius]=useState(2);
  const timer=useRef(null), audio=useRef(null), stemAudios=useRef({}), scoreHost=useRef(null), osmd=useRef(null), cursorIndex=useRef(-1);
  const t=COPY[lang];
  const filename=useMemo(()=>file?.name||t.noTrack,[file,t.noTrack]);
  const ready=job?.status==='completed'&&job?.result;
  const duration=audio.current?.duration||0;
  const stemNames=ready?Object.keys(job.result.stems||{}):[];
  const techniques=ready?(job.result.techniques||[]):[];
  const correctionCount=ready?(job.result.correction_count||0):0;

  function setupPayload(){
    return {
      tuning, profile, capo,
      custom_open_pitches: custom.trim()?custom.split(',').map(x=>Number(x.trim())):null,
      custom_name:'Custom tuning', use_learned_ranker:useRanker, ranker_strength:rankerStrength
    };
  }
  function stopPolling(){ if(timer.current) clearTimeout(timer.current); timer.current=null; }
  async function poll(id){
    try{
      const res=await fetch(`${API}/jobs/${id}`); const data=await res.json(); setJob(data);
      if(data.status==='completed'){ setMessage(t.complete); stopPolling(); return; }
      if(data.status==='failed'){ setMessage(`${t.failed}: ${data.stage||'unknown stage'} · ${data.error||'No technical details available'}`); stopPolling(); return; }
      setMessage(`${data.stage||data.status} · ${data.progress}%`); timer.current=setTimeout(()=>poll(id),900);
    }catch{ setMessage(t.apiFail); stopPolling(); }
  }
  async function upload(){
    if(!file)return; stopPolling(); setJob(null); setSelected(null); setSetupApplied(false); setMessage(t.upload);
    const fd=new FormData(); fd.append('file',file); fd.append('tuning','guitar_standard');
    try{
      const res=await fetch(`${API}/tracks`,{method:'POST',body:fd});
      if(!res.ok) throw new Error();
      const data=await res.json(); setJob(data); poll(data.job_id);
    }catch{ setMessage(t.uploadFail); }
  }
  async function retune(){
    if(!job?.id)return; setMessage(t.applying);
    const res=await fetch(`${API}/jobs/${job.id}/retune`,{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(setupPayload())
    });
    if(!res.ok){setMessage(t.retuneFail);return;}
    const data=await res.json(); setJob(data); setSelected(null); setSetupApplied(true); setMessage(t.retuned);
  }
  function chooseNote(n){
    setSelected(n);
    setEditString(n.string_index);
    setEditFret(n.fret);
    if(audio.current) seek(n.start);
  }
  async function saveCorrection(){
    if(!job?.id||!selected)return;
    setMessage(t.correctionApplying);
    const payload={...setupPayload(),chord_index:selected.chord_index,pitch:selected.pitch,string_index:Number(editString),fret:Number(editFret),neighborhood_radius:Number(radius)};
    const res=await fetch(`${API}/jobs/${job.id}/corrections`,{
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)
    });
    const data=await res.json();
    if(!res.ok){setMessage(data.detail||t.correctionRejected);return;}
    setJob(data);
    const updated=(data.result?.tab||[]).find(n=>n.chord_index===selected.chord_index&&n.pitch===selected.pitch);
    setSelected(updated||null);
    setMessage(t.correctionSaved);
  }
  async function clearCorrectionHistory(){
    if(!job?.id)return;
    const res=await fetch(`${API}/jobs/${job.id}/corrections`,{method:'DELETE'});
    if(res.ok){ setJob(prev=>({...prev,result:{...prev.result,correction_count:0}})); setMessage(t.correctionsCleared); }
  }

  useEffect(()=>{ const saved=window.localStorage.getItem('autotab-lang'); if(saved==='it'||saved==='en') setLang(saved); return()=>stopPolling(); },[]);
  useEffect(()=>{ window.localStorage.setItem('autotab-lang',lang); document.documentElement.lang=lang; },[lang]);
  useEffect(()=>{ fetch(`${API}/ranker/status`).then(r=>r.json()).then(setRankerStatus).catch(()=>{}); },[]);
  useEffect(()=>{
    if(!ready||setupApplied)return;
    fetch(API + "/jobs/" + job.id + "/tuning-suggestions?family=" + instrumentFamily + "&limit=5")
      .then(r=>r.json())
      .then(d=>setTuningSuggestions(d.suggestions||[]))
      .catch(()=>setTuningSuggestions([]));
  },[ready,setupApplied,job?.id,instrumentFamily]);

  useEffect(()=>{ if(audio.current) audio.current.playbackRate=speed; Object.values(stemAudios.current).forEach(a=>{if(a)a.playbackRate=speed;}); },[speed]);
  useEffect(()=>{
    if(!ready)return;
    const next={original:mix.original||{volume:1,muted:false}};
    stemNames.forEach(name=>next[name]=mix[name]||{volume:name==='other'||name==='guitar'?1:.35,muted:false});
    setMix(next);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  },[ready,job?.id]);
  useEffect(()=>{
    if(!ready||!scoreHost.current)return;
    let cancelled=false;
    (async()=>{
      const {OpenSheetMusicDisplay}=await import('opensheetmusicdisplay'); if(cancelled)return;
      scoreHost.current.innerHTML='';
      const viewer=new OpenSheetMusicDisplay(scoreHost.current,{autoResize:true,drawingParameters:'compacttight',drawTitle:true});
      await viewer.load(`${API}/jobs/${job.id}/musicxml?ts=${Date.now()}`);
      await viewer.render();
      viewer.cursor.show(); viewer.cursor.reset(); osmd.current=viewer; cursorIndex.current=-1;
    })().catch(e=>setMessage(`Score render error: ${e.message}`));
    return()=>{cancelled=true;};
  },[ready,job?.id,job?.result?.tuning,job?.result?.musicxml,correctionCount]);

  function effectiveMuted(name){ return solo ? name!==solo : !!mix[name]?.muted; }
  function applyMix(name,patch){ setMix(prev=>({...prev,[name]:{...(prev[name]||{volume:1,muted:false}),...patch}})); }
  function syncStemTransport(master){
    Object.entries(stemAudios.current).forEach(([name,a])=>{
      if(!a)return; a.volume=Math.max(0,Math.min(1,mix[name]?.volume??1)); a.muted=effectiveMuted(name); a.playbackRate=speed;
      if(Math.abs(a.currentTime-master.currentTime)>.08) a.currentTime=master.currentTime;
    });
  }
  async function togglePlayback(){
    const master=audio.current;if(!master)return;
    master.volume=Math.max(0,Math.min(1,mix.original?.volume??1)); master.muted=effectiveMuted('original');
    if(master.paused){ syncStemTransport(master); await Promise.allSettled([master.play(),...Object.values(stemAudios.current).map(a=>a?.play())]); }
    else { master.pause(); Object.values(stemAudios.current).forEach(a=>a?.pause()); }
  }
  function syncCursor(t){
    const q=job?.result?.quantized_tab||[]; if(!osmd.current||!q.length)return;
    const onsets=[...new Set(q.map(n=>n.original_start))].sort((a,b)=>a-b);
    let idx=onsets.findIndex(x=>x>t); idx=idx===-1?onsets.length-1:Math.max(0,idx-1);
    if(idx===cursorIndex.current)return;
    osmd.current.cursor.reset(); for(let i=0;i<idx;i++) osmd.current.cursor.next(); osmd.current.cursor.show(); cursorIndex.current=idx;
  }
  function onTime(){
    const a=audio.current;if(!a)return;
    if(loopA!=null&&loopB!=null&&a.currentTime>=loopB){a.currentTime=loopA;Object.values(stemAudios.current).forEach(s=>{if(s)s.currentTime=loopA;});}
    syncStemTransport(a); setCurrent(a.currentTime); syncCursor(a.currentTime);
  }
  function seek(v){
    const value=Number(v);
    if(audio.current){audio.current.currentTime=value;setCurrent(value);syncCursor(value);Object.values(stemAudios.current).forEach(a=>{if(a)a.currentTime=value;});}
  }

  return <main className="shell">
    <div className="topbar">
      <div className="brand">AUTOTAB</div>
      <div className="topActions">
        <div className="langSwitch">
          <button className={lang==='it'?'active':''} onClick={()=>setLang('it')}>IT</button>
          <button className={lang==='en'?'active':''} onClick={()=>setLang('en')}>EN</button>
        </div>
        <div className="badge">MVP 0.9</div>
      </div>
    </div>

    <section className="hero">
      <h1>AutoTab</h1>
      <p>{t.hero}</p>
    </section>

    {!ready && <section className="panel uploadPanel">
      <div className="stepEyebrow">{t.step} 1</div>
      <div className="sectionTitle">{t.uploadTitle}</div>
      <div className="label">{t.audio}</div>
      <input className="field" type="file" accept="audio/*" onChange={e=>setFile(e.target.files?.[0]||null)}/>
      <div className="small" style={{marginTop:8}}>{filename}</div>
      <button className="btn" disabled={!file || job?.status==='processing'} onClick={upload} style={{marginTop:16}}>
        {job?.status==='processing' ? `${t.analyzing} · ${job.progress||0}%` : t.analyze}
      </button>
      {message && <div className={`status ${job?.status==='failed'?'error':''}`}>{message}</div>}
      {job?.status==='processing' && <div className="progressBar"><div style={{width:`${job.progress||0}%`}}/></div>}
    </section>}

    {ready && !setupApplied && <section className="panel setupPanel">
      <div className="stepEyebrow">{t.step} 2</div>
      <div className="sectionTitle">{t.setupTitle}</div>
      <p className="small setupHelp">{t.setupHelp}</p>

      <div className="suggestionBox">
        <div className="label">{t.suggestions}</div>
        <div className="small" style={{marginBottom:10}}>{t.suggestionsHelp}</div>
        <div className="familySwitch">
          <button className={instrumentFamily==='guitar'?'active':''} onClick={()=>setInstrumentFamily('guitar')}>{t.guitar}</button>
          <button className={instrumentFamily==='bass'?'active':''} onClick={()=>setInstrumentFamily('bass')}>{t.bass}</button>
        </div>
        <div className="suggestionList">
          {tuningSuggestions.length===0 && <div className="small">{t.noSuggestions}</div>}
          {tuningSuggestions.map((item,i)=><button key={item.tuning_id} className={`suggestionCard ${tuning===item.tuning_id?'selected':''}`} onClick={()=>setTuning(item.tuning_id)}>
            <div>
              <strong>{i+1}. {item.name}</strong>
              <div className="small">{Math.round((item.coverage||0)*100)}% {t.compatible} · score {item.score}</div>
            </div>
            <span>{t.select}</span>
          </button>)}
        </div>
      </div>

      <div className="setupGrid">
        <div>
          <div className="label">{t.tuning}</div>
          <select className="field" value={tuning} onChange={e=>setTuning(e.target.value)}>
            {tunings.map(([id,l])=><option key={id} value={id}>{l}</option>)}
          </select>
        </div>
        <div>
          <div className="label">{t.profile}</div>
          <select className="field" value={profile} onChange={e=>setProfile(e.target.value)}>
            <option value="original_like">{t.profileOriginal}</option>
            <option value="easy">{t.profileEasy}</option>
            <option value="rhythm">{t.profileRhythm}</option>
            <option value="lead">{t.profileLead}</option>
          </select>
        </div>
        <div>
          <div className="label">{t.capo}</div>
          <input className="field" type="number" min="0" max="12" value={capo} onChange={e=>setCapo(Number(e.target.value))}/>
        </div>
        <div>
          <div className="label">{t.custom}</div>
          <input className="field" placeholder="38,45,50,55,59,64" value={custom} onChange={e=>setCustom(e.target.value)}/>
        </div>
      </div>

      <div className="mixer compactBox">
        <div className="label">{t.learned}</div>
        <label className="small"><input type="checkbox" checked={useRanker} onChange={e=>setUseRanker(e.target.checked)}/> {t.useLearned}</label>
        <input style={{width:'100%',marginTop:8}} type="range" min="0" max="1.5" step="0.05" value={rankerStrength} onChange={e=>setRankerStrength(Number(e.target.value))}/>
        <div className="small">{t.strength} {rankerStrength.toFixed(2)} · {rankerStatus?.examples||0} {t.corrections}</div>
      </div>

      <button className="btn" onClick={retune}>{t.apply}</button>
      {message && <div className="status">{message}</div>}
    </section>}

    {ready && setupApplied && <div className="grid">
      <aside className="panel">
        <div className="stepEyebrow">{t.step} 2</div>
        <div className="sectionTitle">{t.setupTitle}</div>

        <div className="label">{t.tuning}</div>
        <select className="field" value={tuning} onChange={e=>setTuning(e.target.value)}>
          {tunings.map(([id,l])=><option key={id} value={id}>{l}</option>)}
        </select>

        <div className="label" style={{marginTop:14}}>{t.profile}</div>
        <select className="field" value={profile} onChange={e=>setProfile(e.target.value)}>
          <option value="original_like">Original-like</option>
          <option value="easy">Easy</option>
          <option value="rhythm">Rhythm</option>
          <option value="lead">Lead</option>
        </select>

        <div className="row" style={{marginTop:14}}>
          <div><div className="label">{t.capo}</div><input className="field" type="number" min="0" max="12" value={capo} onChange={e=>setCapo(Number(e.target.value))}/></div>
          <div><div className="label">{t.custom}</div><input className="field" value={custom} onChange={e=>setCustom(e.target.value)}/></div>
        </div>

        <button className="btn secondary" onClick={retune} style={{marginTop:12}}>{t.regenerate}</button>

        <div className="label" style={{marginTop:22}}>{t.analysis}</div>
        <div className="meta">
          <span className="pill">{job.result.rhythm.bpm} BPM</span>
          <span className="pill">{job.result.tab?.length||0} {t.notes}</span>
          <span className="pill">{profile}</span>
          <span className="pill">{t.capo} {capo}</span>
          <span className="pill">{correctionCount} {t.corrections}</span>
        </div>

        <div className="label" style={{marginTop:18}}>{t.detectedChords}</div>
        <div className="meta">{(job.result.intelligence?.chords||[]).slice(0,12).map(c=><span className="pill" key={c.chord_index}>{c.name}</span>)}</div>
        {message && <div className="status">{message}</div>}
      </aside>

      <section className="panel">
        <div className="stepEyebrow">{t.step} 3</div>
        <div className="sectionTitle">{t.practice}</div>

        <audio ref={audio} src={`${API}/jobs/${job.id}/audio`} onTimeUpdate={onTime} onLoadedMetadata={()=>setCurrent(0)} />
        {stemNames.map(name=><audio key={name} ref={el=>{stemAudios.current[name]=el;}} src={`${API}/jobs/${job.id}/stems/${encodeURIComponent(name)}`}/>)}

        <div className="player">
          <button onClick={togglePlayback}>▶︎ / ❚❚</button>
          <span className="time">{fmt(current)} / {fmt(duration)}</span>
          <input className="range" type="range" min="0" max={duration||1} step="0.01" value={Math.min(current,duration||1)} onChange={e=>seek(e.target.value)}/>
          <select value={speed} onChange={e=>setSpeed(Number(e.target.value))}>{[.5,.75,1,1.25,1.5,2].map(x=><option key={x} value={x}>{x}×</option>)}</select>
          <button onClick={()=>setLoopA(current)}>A {loopA==null?'—':fmt(loopA)}</button>
          <button onClick={()=>setLoopB(current)}>B {loopB==null?'—':fmt(loopB)}</button>
          <button onClick={()=>{setLoopA(null);setLoopB(null)}}>{t.clearLoop}</button>
        </div>

        <div className="mixer">
          <div className="label">{t.mixer}</div>
          {['original',...stemNames].map(name=><div className="mixRow" key={name}>
            <span className="mixName">{name==='original'?t.original:name}</span>
            <input type="range" min="0" max="1" step="0.01" value={mix[name]?.volume??1} onChange={e=>applyMix(name,{volume:Number(e.target.value)})}/>
            <span className="mixValue">{Math.round((mix[name]?.volume??1)*100)}%</span>
            <button className={mix[name]?.muted?'active':''} onClick={()=>applyMix(name,{muted:!mix[name]?.muted})}>M</button>
            <button className={solo===name?'active':''} onClick={()=>setSolo(solo===name?null:name)}>S</button>
          </div>)}
        </div>

        <div className="scoreWrap"><div ref={scoreHost}/></div>

        <div style={{marginTop:18}}>
          <div className="label">{t.correction}</div>
          <div className="small" style={{marginBottom:8}}>{t.correctionHelp}</div>
          <div style={{maxHeight:220,overflow:'auto',border:'1px solid #29313a',borderRadius:10,marginBottom:10}}>
            {(job.result.tab||[]).slice(0,160).map((n,i)=><button key={`${n.chord_index}-${n.pitch}-${i}`} onClick={()=>chooseNote(n)} style={{width:'100%',display:'grid',gridTemplateColumns:'70px 70px 1fr 1fr',gap:8,padding:'8px 10px',background:selected?.chord_index===n.chord_index&&selected?.pitch===n.pitch?'#202832':'transparent',color:'#fff',border:0,borderBottom:'1px solid #20262d',textAlign:'left',cursor:'pointer'}}>
              <span>#{n.chord_index}</span><span>MIDI {n.pitch}</span><span>{t.string} {n.string_index+1}</span><span>{t.fret} {n.fret}</span>
            </button>)}
          </div>
          {selected&&<div className="mixer">
            <div className="label">#{selected.chord_index} · MIDI {selected.pitch}</div>
            <div className="row">
              <div><div className="label">{t.string}</div><input className="field" type="number" min="0" max="7" value={editString} onChange={e=>setEditString(Number(e.target.value))}/></div>
              <div><div className="label">{t.fret}</div><input className="field" type="number" min="0" max="24" value={editFret} onChange={e=>setEditFret(Number(e.target.value))}/></div>
              <div><div className="label">{t.radius}</div><input className="field" type="number" min="0" max="12" value={radius} onChange={e=>setRadius(Number(e.target.value))}/></div>
            </div>
            <button className="btn" style={{marginTop:10}} onClick={saveCorrection}>{t.saveCorrection}</button>
            {correctionCount>0&&<button className="btn secondary" style={{marginTop:8}} onClick={clearCorrectionHistory}>{t.clearCorrections}</button>}
          </div>}
        </div>
      </section>
    </div>}
  </main>;
}