/* Pitch Race results: one completed run, one detached Arcade report. */
(function(root,factory){
 const api=factory();
 if(typeof module==='object'&&module.exports)module.exports=api;
 if(root){root.PitchRaceProgress=api;root.CodaBridge=api.createMessageBridge(root);}
})(typeof window!=='undefined'?window:null,function(){
 'use strict';
 const ORIGINS=Object.freeze(['https://cwoodmusic.github.io','https://music-arcade.aquajelly16.chatgpt.site','https://www.coda-aracde.com']);
 const copy=value=>JSON.parse(JSON.stringify(value));
 const count=value=>Number.isSafeInteger(value)&&value>=0?value:0;
 function randomId(){return globalThis.crypto?.randomUUID?.()||Date.now().toString(36)+'-'+Math.random().toString(36).slice(2);}
 function createMessageBridge(win){
  const allowed=new Set(ORIGINS),seen=new Set();let origin='',token='',pending=[];
  function send(payload){if(win.parent===win)return false;if(token){win.parent.postMessage({...payload,coda:1,token,game:'pitch'},origin);return true;}if(pending.length<32){pending.push(payload);return true;}return false;}
  function receive(event){
   const value=event.data;
   if(event.source!==win.parent||!allowed.has(event.origin)||!value||value.coda!==1||value.type!=='init'||value.game!=='pitch'||typeof value.token!=='string'||!value.token.length||value.token.length>100)return;
   origin=event.origin;token=value.token;const queued=pending;pending=[];queued.forEach(send);
  }
  win.addEventListener('message',receive);
  if(win.parent!==win)for(const target of allowed)win.parent.postMessage({coda:1,type:'ready',game:'pitch'},target);
  return {
   id:()=>win.crypto?.randomUUID?.()||randomId(),
   report(runId,result){
    if(win.parent===win||typeof runId!=='string'||!runId.length||runId.length>128||seen.has(runId)||!result||typeof result!=='object')return false;
    let detached;try{detached=copy(result);}catch{return false;}
    if(!send({type:'result',runId,result:detached}))return false;
    seen.add(runId);return true;
   },
   getState:()=>({connected:!!token,pending:pending.length}),
   destroy(){win.removeEventListener('message',receive);pending=[];}
  };
 }
 function createRunTracker(options={}){
  const id=options.id||randomId;let run=null;
  const freshClef=()=>({correct:0,misses:0,bestStreak:0,streak:0});
  function begin(settings={}){
   run={id:id(),mode:settings.mode,staff:['treble','bass','grand'].includes(settings.staff)?settings.staff:'treble',level:count(settings.level),eligible:!settings.practice,finished:false,clefs:{treble:freshClef(),bass:freshClef()}};
   return run.id;
  }
  function noteCorrect(note){
   if(!run||run.finished)return;
   const clef=note?.clef==='bass'?'bass':'treble',stats=run.clefs[clef];
   stats.correct++;stats.streak++;stats.bestStreak=Math.max(stats.bestStreak,stats.streak);
  }
  function noteMiss(note){
   if(!run||run.finished)return;
   run.clefs[note?.clef==='bass'?'bass':'treble'].misses++;
   for(const stats of Object.values(run.clefs))stats.streak=0;
  }
  function finish(metrics={}){
   if(!run||run.finished)return null;
   run.finished=true;if(!run.eligible)return null;
   const clefStats={};for(const [clef,{correct,misses,bestStreak}]of Object.entries(run.clefs))clefStats[clef]={correct,misses,bestStreak};
   const result={mode:run.mode,score:count(metrics.score),correct:count(metrics.correct),misses:count(metrics.misses),streak:count(metrics.streak),won:metrics.won===true,perfect:count(metrics.correct)>0&&count(metrics.misses)===0,staff:run.staff,clefStats,completedLevel:run.mode==='levels'&&metrics.passed===true?run.level:0};
   return {runId:run.id,result};
  }
  return {begin,noteCorrect,noteMiss,finish,markPractice(){if(run)run.eligible=false;},cancel(){run=null;},isEligible:()=>!!run?.eligible,getState:()=>run?copy(run):null};
 }
 function createCountdown(options={}){
  const schedule=options.schedule||setTimeout,cancel=options.cancel||clearTimeout;let generation=0,timer=null;
  function stop(){generation++;if(timer!==null)cancel(timer);timer=null;}
  function start(settings={}){
   stop();const owner=generation;let remaining=count(settings.steps??3);
   const tick=()=>{
    if(owner!==generation||settings.valid?.()===false)return;
    if(remaining>0){settings.onTick?.(remaining--);timer=schedule(tick,settings.interval??750);}
    else{timer=null;settings.onComplete?.();}
   };
   tick();
  }
  return {start,cancel:stop};
 }
 const LEVEL_PROGRESS_KEY='pitchRaceLevelProgressV1';
 function createLevelProgress(options={}){
  let storage=options.storage,bestCompleted=0,error='';
  if(!storage&&typeof window!=='undefined')try{storage=window.localStorage;}catch{error='Progress could not be saved on this device.';}
  try{
   const value=JSON.parse(storage?.getItem(LEVEL_PROGRESS_KEY)||'null');
   if(value?.version===1&&Number.isSafeInteger(value.bestCompleted)&&value.bestCompleted>=0&&value.bestCompleted<=999)bestCompleted=value.bestCompleted;
  }catch{error='Saved progress could not be read on this device.';}
  function complete(level,eligible=true){
   if(!eligible||!Number.isSafeInteger(level)||level<1||level>999)return {ok:false,ignored:true,...snapshot()};
   bestCompleted=Math.max(bestCompleted,level);
   try{if(!storage)throw Error('Storage unavailable');storage.setItem(LEVEL_PROGRESS_KEY,JSON.stringify({version:1,bestCompleted}));error='';return {ok:true,...snapshot()};}
   catch{error='Progress could not be saved on this device.';return {ok:false,...snapshot()};}
  }
  function snapshot(){return {bestCompleted,nextLevel:bestCompleted+1,error};}
  return {complete,snapshot};
 }
 return Object.freeze({ORIGINS,LEVEL_PROGRESS_KEY,createMessageBridge,createRunTracker,createCountdown,createLevelProgress});
});
