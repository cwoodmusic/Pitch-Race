#!/usr/bin/env node
/* Merge two validation leaves into a fresh full-rules snapshot. Never deploy
 * multiplayer-rules.fragment.json by itself: unrelated namespaces must remain. */
'use strict';
const fs=require('node:fs');
const path=require('node:path');
const fragment=require('../multiplayer-rules.fragment.json');
const legacy=require('../tests/fixtures/multiplayer-rules-before.json');
const playerNote=node=>node.players.$role.notes.$i;
function mergeMultiplayerRules(current){
 const merged=structuredClone(current),room=merged?.rules?.rooms?.$code;
 if(!room?.settings||!room.players?.$role?.notes?.$i)throw Error('Current full rules must contain the existing Pitch rooms schema.');
 const update=fragment.rooms.$code,oldNote=playerNote(legacy.rules.rooms.$code)['.validate'];
 const note=playerNote(room)['.validate'],newNote=playerNote(update)['.validate'];
 if(note!==oldNote&&note!==newNote)throw Error('Unrecognized note validation; review current rules before merging.');
 const staff=room.settings.staff;
 if(staff!==undefined&&JSON.stringify(staff)!==JSON.stringify(update.settings.staff))throw Error('Unrecognized staff validation; review current rules before merging.');
 room.settings.staff=structuredClone(update.settings.staff);
 playerNote(room)['.validate']=newNote;
 return merged;
}
if(require.main===module){
 const [input,output,...extra]=process.argv.slice(2);
 if(!input||!output||extra.length){process.stderr.write('Usage: node tools/merge-multiplayer-rules.cjs CURRENT_FULL_RULES.json MERGED_FULL_RULES.json\n');process.exitCode=1;}
 else try{
  if(path.resolve(input)===path.resolve(output))throw Error('Keep the original full-rules snapshot as a backup.');
  const merged=mergeMultiplayerRules(JSON.parse(fs.readFileSync(input,'utf8')));
  fs.writeFileSync(output,JSON.stringify(merged,null,2)+'\n',{mode:0o600});
  process.stdout.write('Wrote the two-field compatibility merge. Review before deploying.\n');
 }catch(error){process.stderr.write(error.message+'\n');process.exitCode=1;}
}
module.exports={mergeMultiplayerRules};
