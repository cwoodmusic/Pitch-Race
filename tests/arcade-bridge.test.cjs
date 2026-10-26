const test=require('node:test');
const assert=require('node:assert/strict');
const {createMessageBridge,createRunTracker,createCountdown,createLevelProgress,LEVEL_PROGRESS_KEY,ORIGINS}=require('../arcade-bridge.js');

function tracker(){let serial=0;return createRunTracker({id:()=>`run-${++serial}`});}
const metrics={score:35,correct:20,misses:0,streak:20,won:true};

test('completed modes preserve their outcome, staff, and stable run ID exactly once',()=>{
 for(const mode of ['classic','endless','levels','multi']){
  const run=tracker(),id=run.begin({mode,staff:'grand',level:40});
  run.noteCorrect({clef:'bass'});
  const report=run.finish({...metrics,passed:mode==='levels'});
  assert.equal(report.runId,id);assert.equal(report.result.mode,mode);assert.equal(report.result.staff,'grand');
  assert.equal(report.result.won,true);assert.equal(report.result.perfect,true);
  assert.equal(report.result.completedLevel,mode==='levels'?40:0);
  assert.deepEqual(report.result.clefStats,{treble:{correct:0,misses:0,bestStreak:0},bass:{correct:1,misses:0,bestStreak:1}});
  assert.equal(run.finish(metrics),null);
  assert.notEqual(run.begin({mode}),id);
 }
});

test('failed levels never infer previous completion and level metadata is captured at run start',()=>{
 const run=tracker(),settings={mode:'levels',staff:'bass',level:50};run.begin(settings);settings.level=51;settings.staff='treble';
 const failed=run.finish({...metrics,won:false,passed:false,misses:2});
 assert.equal(failed.result.completedLevel,0);assert.equal(failed.result.won,false);assert.equal(failed.result.perfect,false);assert.equal(failed.result.staff,'bass');
 run.begin({mode:'levels',level:10});assert.equal(run.finish({...metrics,passed:true}).result.completedLevel,10);
});

test('developer runs and developer enablement stay ineligible; cancellation cannot report',()=>{
 const run=tracker();run.begin({mode:'levels',level:50,practice:true});assert.equal(run.isEligible(),false);assert.equal(run.finish({...metrics,passed:true}),null);
 run.begin({mode:'classic'});run.noteCorrect({clef:'bass'});run.markPractice();assert.equal(run.finish(metrics),null);
 run.begin({mode:'endless'});run.cancel();assert.equal(run.finish(metrics),null);
 run.begin({mode:'classic'});assert.ok(run.finish(metrics),'A new normal run is eligible again');
});

test('clef metrics use finished notes and any clef mistake breaks both clef streaks',()=>{
 const run=tracker();run.begin({mode:'classic',staff:'grand'});
 for(let i=0;i<12;i++)run.noteCorrect({clef:'bass'});
 run.noteCorrect({clef:'treble'});run.noteMiss({clef:'treble'});
 for(let i=0;i<8;i++)run.noteCorrect({clef:'bass'});
 run.noteMiss({clef:'bass'});
 const result=run.finish({...metrics,correct:21,misses:2,streak:13}).result;
 assert.deepEqual(result.clefStats,{treble:{correct:1,misses:1,bestStreak:1},bass:{correct:20,misses:1,bestStreak:12}});
 run.noteCorrect({clef:'bass'});assert.equal(run.getState().clefs.bass.correct,20,'Finished results cannot absorb later input');
});

test('a new countdown rejects stale callbacks even when a new countdown is active',()=>{
 let now=0;const timers=[],events=[];
 const countdown=createCountdown({schedule:(fn,ms)=>{const item={fn,at:now+ms};timers.push(item);return item;},cancel:()=>{}});
 const advance=until=>{while(true){timers.sort((a,b)=>a.at-b.at);if(!timers[0]||timers[0].at>until)break;const task=timers.shift();now=task.at;task.fn();}now=until;};
 const start=()=>countdown.start({onTick:n=>events.push([now,n]),onComplete:()=>events.push([now,'go'])});
 start();advance(1000);countdown.cancel();start();advance(3250);
 assert.deepEqual(events.filter(item=>item[1]==='go'),[[3250,'go']]);
 start();countdown.cancel();advance(6000);assert.equal(events.filter(item=>item[1]==='go').length,1);
});

function frame(standalone=false){const messages=[],listeners=new Map(),parent={postMessage:(data,origin)=>messages.push({data,origin})};const win={parent,crypto:{randomUUID:()=> 'unique-run'},addEventListener:(name,fn)=>listeners.set(name,fn),removeEventListener:(name)=>listeners.delete(name)};if(standalone)win.parent=win;return {win,parent,messages,receive:event=>listeners.get('message')?.(event)};}

test('bridge checks parent, origin, game and token; queued snapshots and duplicate reports stay safe',()=>{
 const env=frame(),bridge=createMessageBridge(env.win),result={...metrics,mode:'classic'};
 assert.equal(env.messages.length,ORIGINS.length);assert.ok(env.messages.every(item=>item.data.game==='pitch'&&item.data.type==='ready'));
 assert.equal(bridge.report('run-1',result),true);result.score=999;assert.equal(bridge.report('run-1',result),false);
 const good={source:env.parent,origin:ORIGINS[0],data:{coda:1,type:'init',game:'pitch',token:'arcade-session'}};
 for(const bad of [{...good,source:{}},{...good,origin:'https://wrong.example'},{...good,data:{...good.data,game:'triad'}},{...good,data:{...good.data,token:''}},{...good,data:{...good.data,token:'x'.repeat(101)}}])env.receive(bad);
 assert.equal(bridge.getState().connected,false);env.receive(good);
 const sent=env.messages.at(-1);assert.equal(sent.origin,ORIGINS[0]);assert.equal(sent.data.token,'arcade-session');assert.equal(sent.data.result.score,35);assert.equal(sent.data.runId,'run-1');
 const original=bridge.report;let hooked=0;bridge.report=(...args)=>{hooked++;return original(...args);};assert.equal(bridge.report('run-2',metrics),true);assert.equal(hooked,1,'Arcade can wrap the public same-origin reporting hook');
 assert.equal(bridge.report('',metrics),false);assert.equal(bridge.report('x'.repeat(129),metrics),false);bridge.destroy();
});

test('standalone runs do not send to or wait for a parent',()=>{
 const env=frame(true),bridge=createMessageBridge(env.win);assert.equal(bridge.id(),'unique-run');assert.equal(bridge.report('run-1',metrics),false);assert.deepEqual(env.messages,[]);assert.equal(bridge.getState().pending,0);
});

test('the custom arcade domain and existing origins retain an exact trusted-parent handshake',()=>{
 assert.deepEqual(ORIGINS,['https://cwoodmusic.github.io','https://music-arcade.aquajelly16.chatgpt.site','https://www.coda-arcade.com']);
 for(const origin of ORIGINS){
  const env=frame(),bridge=createMessageBridge(env.win);
  bridge.report('domain-run',metrics);
  const good={source:env.parent,origin,data:{coda:1,type:'init',game:'pitch',token:'domain-session'}};
  for(const untrusted of ['http://www.coda-arcade.com','https://www.coda-arcade.com.evil.invalid','https://coda-arcade.com','https://www.coda-arcade.com:444','https://cwoodmusic.github.io.evil.invalid'])env.receive({...good,origin:untrusted});
  env.receive({...good,source:{}});env.receive({...good,data:{...good.data,game:'triad'}});
  env.receive({...good,data:{...good.data,token:''}});env.receive({...good,data:{...good.data,token:'x'.repeat(101)}});
  assert.equal(bridge.getState().connected,false);assert.equal(env.messages.filter(m=>m.data.type==='result').length,0);
  env.receive(good);
  const reports=env.messages.filter(m=>m.data.type==='result');assert.equal(reports.length,1);
  assert.equal(reports[0].origin,origin);assert.equal(reports[0].data.token,'domain-session');
  assert.equal(reports[0].data.game,'pitch');assert.equal(reports[0].data.runId,'domain-run');
  bridge.destroy();
 }
});

test('normal completed levels persist a checkpoint without replaying completion events',()=>{
 const values=new Map(),storage={getItem:key=>values.get(key)||null,setItem:(key,value)=>values.set(key,value)};
 const progress=createLevelProgress({storage});assert.equal(progress.snapshot().nextLevel,1);
 assert.equal(progress.complete(10).ok,true);assert.equal(progress.snapshot().nextLevel,11);
 assert.equal(progress.complete(50,false).ignored,true,'Developer practice does not save');
 progress.complete(3);assert.equal(progress.snapshot().bestCompleted,10,'Replay cannot lower the checkpoint');
 assert.deepEqual(JSON.parse(values.get(LEVEL_PROGRESS_KEY)),{version:1,bestCompleted:10});
 const loaded=createLevelProgress({storage});assert.equal(loaded.snapshot().nextLevel,11);
 assert.equal(loaded.complete(1000).ignored,true);
});

test('unavailable checkpoint storage reports the failure while play can still continue',()=>{
 const progress=createLevelProgress({storage:{getItem:()=>null,setItem:()=>{throw Error('blocked');}}});
 const result=progress.complete(20);assert.equal(result.ok,false);assert.match(result.error,/could not be saved/);assert.equal(progress.snapshot().nextLevel,21);
 for(const value of [{version:1,bestCompleted:-1},{version:1,bestCompleted:1000},{version:1,bestCompleted:4.5},{version:2,bestCompleted:20}]){
  assert.equal(createLevelProgress({storage:{getItem:()=>JSON.stringify(value)}}).snapshot().bestCompleted,0);
 }
});
