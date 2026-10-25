'use strict';
const assert=require('node:assert/strict');
const test=require('node:test');
const notation=require('../pitch-notation.js');
const {LESSONS,MNEMONICS}=require('../pitch-tutorials.js');

test('the requested sayings name the actual staff lines and spaces, bottom to top',()=>{
 const patterns=[
  ['trebleLines','treble',[0,2,4,6,8],'EGBDF','Every Good Boy Does Fine'],
  ['trebleSpaces','treble',[1,3,5,7],'FACE','FACE'],
  ['bassLines','bass',[0,2,4,6,8],'GBDFA','Great Big Dreams For America'],
  ['bassSpaces','bass',[1,3,5,7],'ACEG','All Cows Eat Grass']
 ];
 for(const [id,clef,pitches,letters,words]of patterns){
  assert.deepEqual(MNEMONICS[id],{letters,words});
  assert.equal(pitches.map(pitch=>notation.letter({clef,pitch})).join(''),letters);
  if(words.includes(' '))assert.equal(words.split(' ').map(word=>word[0]).join(''),letters);
 }
});

test('each lesson scaffolds worked examples, guided attempts, and a three-question quiz',()=>{
 assert.deepEqual(LESSONS.map(lesson=>lesson.id),['treble','bass','grand']);
 for(const lesson of LESSONS){
  assert.equal(lesson.steps.length,7);
  assert.equal(lesson.quiz.length,3);
  assert.ok(lesson.steps.findIndex(step=>step.answer)>0,'an example comes before the first question');
  assert.ok(lesson.steps.some(step=>step.answer),'each lesson has guided practice');
  for(const step of [...lesson.steps,...lesson.quiz]){
   assert.ok(step.title&&step.text);
   assert.ok(!/\b[A-G][0-9]\b/.test(step.title+' '+step.text),'beginner UI has no octave numbers');
   if(!step.answer)continue;
   assert.ok(step.choices.includes(step.answer));
   assert.equal(new Set(step.choices).size,step.choices.length);
   assert.ok(step.hint,'a wrong answer receives a useful hint');
   if(step.answer.length===1){
    assert.ok(step.note,'letter questions show a note');
    assert.equal(notation.letter(step.note),step.answer,lesson.id+': '+step.title);
   }
  }
 }
});

test('middle C examples connect both clefs with the same pitch and a real ledger line',()=>{
 const examples=LESSONS.find(lesson=>lesson.id==='grand').steps.filter(step=>step.middleC);
 assert.ok(examples.some(step=>step.note.clef==='bass'));
 assert.ok(examples.some(step=>step.note.clef==='treble'));
 for(const example of examples){
  assert.equal(notation.midi(example.note),60);
  assert.equal(notation.letter(example.note),'C');
  assert.equal(notation.noteY(example.note,'grand'),notation.geometry('grand').middleC);
  assert.ok(notation.ledgerLines(example.note,'grand').includes(notation.geometry('grand').middleC));
 }
});
