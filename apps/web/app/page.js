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

export default function Home() {
  const [file,setFile]=useState(null), [tuning,setTuning]=useState('guitar_drop_d');
  const [profile,setProfile]=useState('original_like'), [capo,setCapo]=useState(0), [custom,setCustom]=useState('');
  const [useRanker,setUseRanker]=useState(false), [rankerStrength,setRankerStrength]=useState(0.55), [rankerStatus,setRankerStatus]=useState(null);
  const [message,setMessage]=useState(''), [job,setJob]=useState(null), [speed,setSpeed]=useState(1);
  const [loopA,setLoopA]=useState(null), [loopB,setLoopB]=useState(null), [current,setCurrent]=useState(0);
  const [mix,setMix]=useState({original:{volume:1,muted:false}}), [solo,setSolo]=useState(null);
  const [selected,setSelected]=useState(null), [editString,setEditString]=useState(0), [editFret,setEditFret]=useState(0), [radius,setRadius]=useState(2);
  const timer=useRef(null), audio=useRef(null), stemAudios=useRef({}), scoreHost=useRef(null), osmd=useRef(null), cursorIndex=useRef(-1);
  const filename=useMemo(()=>file?.name||'No track selected',[file]);
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
      if(data.status==='completed'){ setMessage('Analysis complete'); stopPolling(); return; }
      if(data.status==='failed'){ setMessage('Analysis failed'); stopPolling(); return; }
      setMessage(`${data.status} · ${data.progress}%`); timer.current=setTimeout(()=>poll(id),900);
    }catch{ setMessage('Cannot reach AutoTab API'); stopPolling(); }
  }
  async function upload(){
    if(!file)return; stopPolling(); setJob(null); setSelected(null); setMessage('Uploading…');
    const fd=new FormData(); fd.append('file',file); fd.append('tuning',tuning);
    try{
      const res=await fetch(`${API}/tracks`,{method:'POST',body:fd});
      if(!res.ok) throw new Error();
      const data=await res.json(); setJob(data); poll(data.job_id);
    }catch{ setMessage('Upload failed. Start the API on localhost:8000.'); }
  }
  async function retune(){
    if(!job?.id)return; setMessage('Rebuilding TAB…');
    const res=await fetch(`${API}/jobs/${job.id}/retune`,{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(setupPayload())
    });
    if(!res.ok){setMessage('Retune failed');return;}
    const data=await res.json(); setJob(data); setSelected(null); setMessage('TAB regenerated without re-analysing audio');
  }
  function chooseNote(n){
    setSelected(n);
    setEditString(n.string_index);
    setEditFret(n.fret);
    if(audio.current) seek(n.start);
  }
  async function saveCorrection(){
    if(!job?.id||!selected)return;
    setMessage('Applying correction and re-optimizing nearby voicings…');
    const payload={...setupPayload(),chord_index:selected.chord_index,pitch:selected.pitch,string_index:Number(editString),fret:Number(editFret),neighborhood_radius:Number(radius)};
    const res=await fetch(`${API}/jobs/${job.id}/corrections`,{
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)
    });
    const data=await res.json();
    if(!res.ok){setMessage(data.detail||'Correction rejected');return;}
    setJob(data);
    const updated=(data.result?.tab||[]).find(n=>n.chord_index===selected.chord_index&&n.pitch===selected.pitch);
    setSelected(updated||null);
    setMessage('Correction saved · local fingering re-optimized');
  }
  async function clearCorrectionHistory(){
    if(!job?.id)return;
    const res=await fetch(`${API}/jobs/${job.id}/corrections`,{method:'DELETE'});
    if(res.ok){ setJob(prev=>({...prev,result:{...prev.result,correction_count:0}})); setMessage('Correction history cleared'); }
  }

  useEffect(()=>()=>stopPolling(),[]);
  useEffect(()=>{ fetch(`${API}/ranker/status`).then(r=>r.json()).then(setRankerStatus).catch(()=>{}); },[]);
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
    <div className="topbar"><div className="brand">AUTOTAB</div><div className="badge">MVP 0.9 · LEARNED FINGERING RANKER</div></div>
    <section className="hero"><h1>Turn audio into something you can actually play.</h1><p>Transcribe, retune, practise, correct the fingering and turn every edit into reusable training data.</p></section>
    <div className="grid">
      <aside className="panel">
        <div className="sectionTitle">Analyze track</div><div className="label">Audio</div>
        <input className="field" type="file" accept="audio/*" onChange={e=>setFile(e.target.files?.[0]||null)}/><div className="small" style={{marginTop:8}}>{filename}</div>
        <div className="label" style={{marginTop:18}}>Instrument tuning</div>
        <select className="field" value={tuning} onChange={e=>setTuning(e.target.value)}>{tunings.map(([id,l])=><option key={id} value={id}>{l}</option>)}</select>
        <div className="label" style={{marginTop:14}}>Playing profile</div>
        <select className="field" value={profile} onChange={e=>setProfile(e.target.value)}><option value="original_like">Original-like</option><option value="easy">Easy</option><option value="rhythm">Rhythm</option><option value="lead">Lead</option></select>
        <div className="row" style={{marginTop:14}}><div><div className="label">Capo</div><input className="field" type="number" min="0" max="12" value={capo} onChange={e=>setCapo(Number(e.target.value))}/></div><div><div className="label">Custom tuning · MIDI</div><input className="field" placeholder="38,45,50,55,59,64" value={custom} onChange={e=>setCustom(e.target.value)}/></div></div>
        <div className="mixer" style={{marginTop:14}}><div className="label">Learned ranker</div><label className="small"><input type="checkbox" checked={useRanker} onChange={e=>setUseRanker(e.target.checked)}/> Use learned fingering preferences</label><input style={{width:'100%',marginTop:8}} type="range" min="0" max="1.5" step="0.05" value={rankerStrength} onChange={e=>setRankerStrength(Number(e.target.value))}/><div className="small">Strength {rankerStrength.toFixed(2)} · {rankerStatus?.examples||0} training corrections</div><button className="btn secondary" style={{marginTop:8}} onClick={async()=>{const r=await fetch(`${API}/ranker/train`,{method:'POST'});const d=await r.json();setRankerStatus(d);setMessage(`Ranker trained on ${d.examples||0} corrections`);}}>Train / refresh ranker</button></div>
        <button className="btn" disabled={!file} onClick={upload} style={{marginTop:16}}>Analyze track</button>
        {ready&&<button className="btn secondary" onClick={retune} style={{marginTop:8}}>Regenerate TAB</button>}
        <div className={`status ${job?.status==='failed'?'error':''}`}>{message}</div>
        {ready&&<>
          <div className="label" style={{marginTop:22}}>Analysis</div>
          <div className="meta"><span className="pill">{job.result.rhythm.bpm} BPM</span><span className="pill">{job.result.tab?.length||0} notes</span><span className="pill">{profile}</span><span className="pill">Capo {capo}</span><span className="pill">{correctionCount} corrections</span></div>
          <div className="label" style={{marginTop:18}}>Detected chords</div>
          <div className="meta">{(job.result.intelligence?.chords||[]).slice(0,12).map(c=><span className="pill" key={c.chord_index}>{c.name}</span>)}</div>
        </>}
      </aside>

      <section className="panel">
        <div className="sectionTitle">Practice player</div>
        {!ready?<div className="small">Upload a track to generate synchronized notation + TAB.</div>:<>
          <audio ref={audio} src={`${API}/jobs/${job.id}/audio`} onTimeUpdate={onTime} onLoadedMetadata={()=>setCurrent(0)} />
          {stemNames.map(name=><audio key={name} ref={el=>{stemAudios.current[name]=el;}} src={`${API}/jobs/${job.id}/stems/${encodeURIComponent(name)}`}/>)}
          <div className="player"><button onClick={togglePlayback}>▶︎ / ❚❚</button><span className="time">{fmt(current)} / {fmt(duration)}</span><input className="range" type="range" min="0" max={duration||1} step="0.01" value={Math.min(current,duration||1)} onChange={e=>seek(e.target.value)}/><select value={speed} onChange={e=>setSpeed(Number(e.target.value))}>{[.5,.75,1,1.25,1.5,2].map(x=><option key={x} value={x}>{x}×</option>)}</select><button onClick={()=>setLoopA(current)}>A {loopA==null?'—':fmt(loopA)}</button><button onClick={()=>setLoopB(current)}>B {loopB==null?'—':fmt(loopB)}</button><button onClick={()=>{setLoopA(null);setLoopB(null)}}>Clear loop</button></div>
          <div className="mixer"><div className="label">Stem mixer</div>{['original',...stemNames].map(name=><div className="mixRow" key={name}><span className="mixName">{name}</span><input type="range" min="0" max="1" step="0.01" value={mix[name]?.volume??1} onChange={e=>applyMix(name,{volume:Number(e.target.value)})}/><span className="mixValue">{Math.round((mix[name]?.volume??1)*100)}%</span><button className={mix[name]?.muted?'active':''} onClick={()=>applyMix(name,{muted:!mix[name]?.muted})}>M</button><button className={solo===name?'active':''} onClick={()=>setSolo(solo===name?null:name)}>S</button></div>)}</div>

          <div className="label">Correction editor</div>
          <div className="small" style={{marginBottom:8}}>Select a note. AutoTab validates that the chosen string/fret produces the same pitch, freezes distant chords and re-optimizes only the local neighborhood.</div>
          <div style={{maxHeight:220,overflow:'auto',border:'1px solid #29313a',borderRadius:10,marginBottom:10}}>
            {(job.result.tab||[]).slice(0,160).map((n,i)=><button key={`${n.chord_index}-${n.pitch}-${i}`} onClick={()=>chooseNote(n)} style={{width:'100%',display:'grid',gridTemplateColumns:'70px 70px 1fr 1fr',gap:8,padding:'8px 10px',background:selected?.chord_index===n.chord_index&&selected?.pitch===n.pitch?'#202832':'transparent',color:'#fff',border:0,borderBottom:'1px solid #20262d',textAlign:'left',cursor:'pointer'}}><span>#{n.chord_index}</span><span>MIDI {n.pitch}</span><span>string {n.string_index+1}</span><span>fret {n.fret}</span></button>)}
          </div>
          {selected&&<div className="mixer">
            <div className="label">Edit chord #{selected.chord_index} · MIDI {selected.pitch}</div>
            <div className="row"><div><div className="label">String index</div><input className="field" type="number" min="0" max="7" value={editString} onChange={e=>setEditString(Number(e.target.value))}/></div><div><div className="label">Fret</div><input className="field" type="number" min="0" max="24" value={editFret} onChange={e=>setEditFret(Number(e.target.value))}/></div><div><div className="label">Local radius</div><input className="field" type="number" min="0" max="12" value={radius} onChange={e=>setRadius(Number(e.target.value))}/></div></div>
            <button className="btn" style={{marginTop:10}} onClick={saveCorrection}>Save correction</button>
            {correctionCount>0&&<button className="btn secondary" style={{marginTop:8}} onClick={clearCorrectionHistory}>Clear correction history</button>}
          </div>}

          <div className="scoreWrap"><div ref={scoreHost}/></div>
        </>}
      </section>
    </div>
  </main>;
}
