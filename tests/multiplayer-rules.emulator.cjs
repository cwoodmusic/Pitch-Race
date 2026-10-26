'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const path=require('node:path'),{createRequire}=require('node:module');
const baseline=require('./fixtures/multiplayer-rules-before.json');
const {mergeMultiplayerRules}=require('../tools/merge-multiplayer-rules.cjs');
const requireTools=createRequire(path.join(process.env.CODA_FIREBASE_TEST_TOOLS||'/tmp/coda-classroom-emulator','package.json'));
const {initializeTestEnvironment,assertSucceeds,assertFails}=requireTools('@firebase/rules-unit-testing');
const address=process.env.FIREBASE_DATABASE_EMULATOR_HOST||'';
if(!/^127\.0\.0\.1:\d+$/.test(address)||process.env.GCLOUD_PROJECT!=='demo-coda-pitch-rules')throw Error('Only the explicit loopback demo-coda-pitch-rules emulator is permitted.');
const [host,portText]=address.split(':');let env;
const player=uid=>({uid,initials:'AAA',ready:false,score:0,streak:0,bestStreak:0,miss:0,level:1,notes:[],round:0,finished:false});
const room=(staff='treble')=>({hostUid:'host',control:{status:'waiting',startAt:0,round:0},createdAt:{'.sv':'timestamp'},settings:{duration:90,noteValues:'all',speed:'normal',staff,penalties:true,combos:true},players:{host:player('host')}});
const ref=(uid,p)=>env.authenticatedContext(uid).database().ref(p);
async function rules(merged=true){
 if(env)await env.cleanup();
 env=await initializeTestEnvironment({projectId:'demo-coda-pitch-rules',database:{host,port:Number(portText),rules:JSON.stringify(merged?mergeMultiplayerRules(baseline):baseline)}});
 await env.clearDatabase();
}
test.after(async()=>{if(env)await env.cleanup();});
test('old deployed validation rejects current staff and extended-note payloads',async()=>{
 await rules(false);
 await assertFails(ref('host','rooms/OLDS').set(room()));
 const old=room();delete old.settings.staff;
 await assertSucceeds(ref('host','rooms/OLDN').set(old));
 await assertFails(ref('host','rooms/OLDN/players/host/notes').set([{pitch:-2,x:380}]));
 await assertFails(ref('host','rooms/OLDN/players/host/notes').set([{pitch:10,x:380}]));
});
test('new validation accepts existing Create wire, staff selection, and both ledger-note bounds',async()=>{
 await rules();
 for(const [index,staff]of ['treble','bass','grand'].entries())await assertSucceeds(ref('host','rooms/NEW'+index).set(room(staff)));
 await assertSucceeds(ref('host','rooms/NEW0/settings/staff').set('grand'));
 await assertSucceeds(ref('host','rooms/NEW0/players/host/notes').set([{pitch:-2,x:0,clef:'bass',kind:'quarter'},{pitch:10,x:920,clef:'treble',kind:'eighth'}]));
 await assertSucceeds(ref('guest','rooms/NEW0/players/guest').transaction(current=>current===null?player('guest'):undefined));
 await assertSucceeds(ref('guest','rooms/NEW0/players/guest/notes').set([{pitch:-2,x:380},{pitch:10,x:500}]));
});
test('bad staff values, note bounds/types, and unknown settings are still rejected',async()=>{
 await rules();await assertSucceeds(ref('host','rooms/BOUNDS').set(room()));
 for(const staff of ['alto','',3,true])await assertFails(ref('host','rooms/BOUNDS/settings/staff').set(staff));
 for(const pitch of [-3,11,'3',false])await assertFails(ref('host','rooms/BOUNDS/players/host/notes').set([{pitch,x:380}]));
 await assertFails(ref('host','rooms/BOUNDS/settings/secret').set(true));
 await assertFails(ref('host','rooms/BOUNDS/players/host/notes').set([{pitch:3,x:921}]));
});
test('room access guards still reject cross-player writes, non-host rules, unauthenticated access, and deletion',async()=>{
 await rules();await assertSucceeds(ref('host','rooms/GUARD').set(room()));
 await assertSucceeds(ref('guest','rooms/GUARD/players/guest').set(player('guest')));
 await assertFails(ref('guest','rooms/GUARD/players/host/score').set(100));
 await assertFails(ref('host','rooms/GUARD/players/guest/score').set(100));
 await assertFails(ref('other','rooms/GUARD/players/guest/score').set(100));
 await assertFails(ref('guest','rooms/GUARD/settings/staff').set('bass'));
 await assertFails(ref('guest','rooms/GUARD/control/status').set('running'));
 await assertFails(ref('host','rooms/GUARD').remove());
 await assertFails(env.unauthenticatedContext().database().ref('rooms/GUARD').get());
 await assertFails(env.unauthenticatedContext().database().ref('rooms/ANON').set(room()));
 const actual=(await ref('host','rooms/GUARD').get()).val();assert.equal(actual.players.host.score,0);assert.equal(actual.settings.staff,'treble');
});
