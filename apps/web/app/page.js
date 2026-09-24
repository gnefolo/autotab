'use client';
import { useEffect, useMemo, useRef, useState } from 'react';

const tunings = [
  ['guitar_standard', 'Standard · E A D G B E'], ['guitar_drop_d', 'Drop D · D A D G B E'],
  ['guitar_eb', 'Eb Standard'], ['guitar_d_standard', 'D Standard'],
  ['guitar_drop_c_sharp', 'Drop C#'], ['guitar_drop_c', 'Drop C'],
  ['bass_standard_4', 'Bass Standard · E A D G'], ['bass_drop_d_4', 'Bass Drop D'],
  ['bass_standard_5', '5-string Bass · B E A D G'],\n  ['guitar_standard_7', '7-string Standard · B E A D G B E'], ['guitar_standard_8', '8-string Standard · F# B E A D G B E'],
];
const API = process.env.NEXT_PUBLIC_AUTOTAB_API || 'http://localhost:8000';
const fmt = s => `${Math.floor((s||0)/60)}:${String(Math.floor((s||0)%60)).padStart(2,'0')}`;

export default function Home() {
  const [file,setFile]=useState(null), [tuning,setTuning]=useState('guitar_drop_d');\n  const [profile,setProfile]=useState('original_like'), [capo,setCapo]=useState(0), [custom,setCustom]=useState('');
  const [message,setMessage]=useState(''), [job,setJob]=useState(null), [speed,setSpeed]=useState(1);
  const [loopA,setLoopA]=useState(null), [loopB,setLoopB]=useState(null), [current,setCurrent]=useState(0);
  const [mix,setMix]=useState({original:{volume:1,muted:false}}), [solo,setSolo]=useState(null);
  const timer=useRef(null), audio=useRef(null), stemAudios=useRef({}), scoreHost=useRef(null), osmd=useRef(null), cursorIndex=useRef(-1);
  const filename=useMemo(()=>file?.name||'No track selected',[file]);
  const ready=job?.status==='completed'&&job?.result;
  const duration=audio.current?.duration||0;
  const stemNames=ready?Object.keys(job.result.stems||{}):[];

  function stopPolling(){ if(timer.current) clearTimeout(timer.current); timer.current=null; }
  async function poll(id){
    try{ const res=await fetch(`${API}/jobs/${id}`); const data=await res.json(); setJob(data);
      if(data.status==='completed'){ setMessage('Analysis complete'); stopPolling(); return; }
      if(data.status==='failed'){ setMessage('Analysis failed'); stopPolling(); return; }
      setMessage(`${data.status} · ${data.progress}%`); timer.current=setTimeout(()=>poll(id),900);
    }catch{ setMessage('Cannot reach AutoTab API'); stopPolling(); }
  }
  async function upload(){ if(!file)return; stopPolling(); setJob(null); setMessage('Uploading…');
    const fd=new FormData(); fd.append('file',file); fd.append('tuning',tuning);
    try{ const res=await fetch(`${API}/tracks`,{method:'POST',body:fd}); if(!res.ok) throw new Error(); const data=await res.json(); setJob(data); poll(data.job_id); }
    catch{ setMessage('Upload failed. Start the API on localhost:8000.'); }
  }
  async function retune(){ if(!job?.id)return; setMessage('Rebuilding TAB for new tuning…');
    const res=await fetch(`${API}/jobs/${job.id}/retune`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tuning,profile,capo,custom_open_pitches:custom.trim()?custom.split(',').map(x=>Number(x.trim())):null,custom_name:'Custom tuning'})});
    if(!res.ok){setMessage('Retune failed');return;} const data=await res.json(); setJob(data); setMessage('TAB regenerated without re-analysing audio');
  }

  useEffect(()=>()=>stopPolling(),[]);
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
    (async()=>{ const {OpenSheetMusicDisplay}=await import('opensheetmusicdisplay'); if(cancelled)return;
      scoreHost.current.innerHTML=''; const viewer=new OpenSheetMusicDisplay(scoreHost.current,{autoResize:true,drawingParameters:'compacttight',drawTitle:true});
      await viewer.load(`${API}/jobs/${job.id}/musicxml?ts=${Date.now()}`); await viewer.render();
      viewer.cursor.show(); viewer.cursor.reset(); osmd.current=viewer; cursorIndex.current=-1;
    })().catch(e=>setMessage(`Score render error: ${e.message}`));
    return()=>{cancelled=true;};
  },[ready,job?.id,job?.result?.tuning]);

  function effectiveMuted(name){ return solo ? name!==solo : !!mix[name]?.muted; }
  function applyMix(name,patch){ setMix(prev=>({...prev,[name]:{...(prev[name]||{volume:1,muted:false}),...patch}})); }
  function syncStemTransport(master){
    Object.entries(stemAudios.current).forEach(([name,a])=>{ if(!a)return; a.volume=Math.max(0,Math.min(1,mix[name]?.volume??1)); a.muted=effectiveMuted(name); a.playbackRate=speed;
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
  function onTime(){ const a=audio.current;if(!a)return; if(loopA!=null&&loopB!=null&&a.currentTime>=loopB){a.currentTime=loopA;Object.values(stemAudios.current).forEach(s=>{if(s)s.currentTime=loopA;});} syncStemTransport(a); setCurrent(a.currentTime); syncCursor(a.currentTime); }
  function seek(v){ const value=Number(v); if(audio.current){audio.current.currentTime=value; setCurrent(value);syncCursor(value);Object.values(stemAudios.current).forEach(a=>{if(a)a.currentTime=value;});} }
  const techniques=ready?(job.result.techniques||[]):[];

  return <main className="shell">
    <div className="topbar"><div className="brand">AUTOTAB</div><div className="badge">MVP 0.7 · GUITAR INTELLIGENCE</div></div>
    <section className="hero"><h1>Turn audio into something you can actually play.</h1><p>Separate, transcribe, quantize, retune and practise against synchronized score + TAB, with independent stem mixing.</p></section>
    <div className="grid">
      <aside className="panel">
        <div className="sectionTitle">Analyze track</div><div className="label">Audio</div>
        <input className="field" type="file" accept="audio/*" onChange={e=>setFile(e.target.files?.[0]||null)}/><div className="small" style={{marginTop:8}}>{filename}</div>
        <div className="label" style={{marginTop:18}}>Instrument tuning</div><select className="field" value={tuning} onChange={e=>setTuning(e.target.value)}>{tunings.map(([id,l])=><option key={id} value={id}>{l}</option>)}</select>
        <div className="label" style={{marginTop:14}}>Playing profile</div><select className="field" value={profile} onChange={e=>setProfile(e.target.value)}><option value="original_like">Original-like</option><option value="easy">Easy</option><option value="rhythm">Rhythm</option><option value="lead">Lead</option></select>
        <div className="row" style={{marginTop:14}}><div><div className="label">Capo</div><input className="field" type="number" min="0" max="12" value={capo} onChange={e=>setCapo(Number(e.target.value))}/></div><div><div className="label">Custom tuning · MIDI</div><input className="field" placeholder="e.g. 38,45,50,55,59,64" value={custom} onChange={e=>setCustom(e.target.value)}/></div></div>
        <button className="btn" disabled={!file} onClick={upload} style={{marginTop:16}}>Analyze track</button>
        {ready&&<button className="btn secondary" onClick={retune} style={{marginTop:8}}>Regenerate TAB in this tuning</button>}
        <div className={`status ${job?.status==='failed'?'error':''}`}>{message}</div>
        {ready&&<><div className="label" style={{marginTop:22}}>Analysis</div><div className="meta"><span className="pill">{job.result.rhythm.bpm} BPM</span><span className="pill">{job.result.rhythm.beats}/{job.result.rhythm.beat_type}</span><span className="pill">{job.result.tab?.length||0} notes</span><span className="pill">{techniques.length} technique hints</span><span className="pill">{profile}</span><span className="pill">Capo {capo}</span></div>
          <div className="label" style={{marginTop:18}}>Detected chords</div><div className="meta">{(job.result.intelligence?.chords||[]).slice(0,12).map(c=><span className="pill" key={c.chord_index}>{c.name}</span>)}</div>
          <div className="small">{(job.result.intelligence?.barres||[]).length} probable barre shape(s) · {(job.result.intelligence?.fingers||[]).length} finger assignments</div>
          <div className="label" style={{marginTop:18}}>Technique hints</div><div className="techList">{techniques.length?techniques.slice(0,12).map((t,i)=><div className="tech" key={`${t.note_index}-${t.kind}-${i}`}><b>{t.kind.replaceAll('_',' ')}</b><span>{Math.round(t.confidence*100)}%</span></div>):<div className="small">No high-confidence technique hints detected.</div>}</div>
          <div className="small" style={{marginTop:10}}>Technique labels are conservative hints. Bend/vibrato use pitch-curve evidence; legato/slide remain candidates until the dedicated audio classifier is added.</div></>}
      </aside>
      <section className="panel">
        <div className="sectionTitle">Practice player</div>
        {!ready?<div className="small">Upload a track to generate synchronized notation + TAB.</div>:<>
          <audio ref={audio} src={`${API}/jobs/${job.id}/audio`} onTimeUpdate={onTime} onLoadedMetadata={()=>setCurrent(0)} />
          {stemNames.map(name=><audio key={name} ref={el=>{stemAudios.current[name]=el;}} src={`${API}/jobs/${job.id}/stems/${encodeURIComponent(name)}`}/>)}
          <div className="player"><button onClick={togglePlayback}>▶︎ / ❚❚</button><span className="time">{fmt(current)} / {fmt(duration)}</span><input className="range" type="range" min="0" max={duration||1} step="0.01" value={Math.min(current,duration||1)} onChange={e=>seek(e.target.value)}/><select value={speed} onChange={e=>setSpeed(Number(e.target.value))}>{[.5,.75,1,1.25,1.5,2].map(x=><option key={x} value={x}>{x}×</option>)}</select><button onClick={()=>setLoopA(current)}>A {loopA==null?'—':fmt(loopA)}</button><button onClick={()=>setLoopB(current)}>B {loopB==null?'—':fmt(loopB)}</button><button onClick={()=>{setLoopA(null);setLoopB(null)}}>Clear loop</button></div>
          <div className="mixer"><div className="label">Stem mixer</div>{['original',...stemNames].map(name=><div className="mixRow" key={name}><span className="mixName">{name}</span><input type="range" min="0" max="1" step="0.01" value={mix[name]?.volume??1} onChange={e=>applyMix(name,{volume:Number(e.target.value)})}/><span className="mixValue">{Math.round((mix[name]?.volume??1)*100)}%</span><button className={mix[name]?.muted?'active':''} onClick={()=>applyMix(name,{muted:!mix[name]?.muted})}>M</button><button className={solo===name?'active':''} onClick={()=>setSolo(solo===name?null:name)}>S</button></div>)}</div>
          <div className="scoreWrap"><div ref={scoreHost}/></div>
        </>}
      </section>
    </div>
  </main>;
}
