'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const baseline=require('./fixtures/multiplayer-rules-before.json');
const fragment=require('../multiplayer-rules.fragment.json');
const {mergeMultiplayerRules}=require('../tools/merge-multiplayer-rules.cjs');
test('compatibility merge changes only staff validation and note pitch range',()=>{
 const original=structuredClone(baseline);
 original.rules.classroomV1={'.read':false,privateProfiles:{'.write':false}};
 original.rules.leaderboards={'.read':true,'.write':'auth != null'};
 const before=structuredClone(original),next=mergeMultiplayerRules(original);
 assert.deepEqual(original,before,'Input backup is immutable');
 const desired=structuredClone(before),room=desired.rules.rooms.$code;
 room.settings.staff=fragment.rooms.$code.settings.staff;
 room.players.$role.notes.$i['.validate']=fragment.rooms.$code.players.$role.notes.$i['.validate'];
 assert.deepEqual(next,desired);
 assert.deepEqual(mergeMultiplayerRules(next),next,'Applying again is safe');
});
test('note compatibility preserves all predicates except the two pitch bounds',()=>{
 const before=baseline.rules.rooms.$code.players.$role.notes.$i['.validate'];
 const after=fragment.rooms.$code.players.$role.notes.$i['.validate'];
 assert.equal(after,before.replace("pitch').val() >= 0","pitch').val() >= -2").replace("pitch').val() <= 8","pitch').val() <= 10"));
 assert.equal(fragment.rooms.$code.settings.staff['.validate'],"newData.isString() && (newData.val() === 'treble' || newData.val() === 'bass' || newData.val() === 'grand')");
});
test('merger refuses unknown schemas rather than overwriting changed access rules',()=>{
 assert.throws(()=>mergeMultiplayerRules({rules:{}}),/existing Pitch rooms/);
 let changed=structuredClone(baseline);changed.rules.rooms.$code.players.$role.notes.$i['.validate']='true';
 assert.throws(()=>mergeMultiplayerRules(changed),/Unrecognized note/);
 changed=structuredClone(baseline);changed.rules.rooms.$code.settings.staff={'.validate':true};
 assert.throws(()=>mergeMultiplayerRules(changed),/Unrecognized staff/);
});
