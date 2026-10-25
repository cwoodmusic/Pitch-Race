'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const notation=require('../pitch-notation.js');

test('treble and bass lines and spaces have their actual musical names',()=>{
 const names=(clef,indices)=>indices.map(pitch=>notation.letter({clef,pitch})).join('');
 assert.equal(names('treble',[0,2,4,6,8]),'EGBDF');
 assert.equal(names('treble',[1,3,5,7]),'FACE');
 assert.equal(names('bass',[0,2,4,6,8]),'GBDFA');
 assert.equal(names('bass',[1,3,5,7]),'ACEG');
 assert.equal(notation.letter({pitch:0}),'E','legacy note without clef remains treble');
});

test('each clef plays its real octave, with Middle C shared',()=>{
 assert.equal(notation.midi({clef:'treble',pitch:0}),64);
 assert.equal(notation.midi({clef:'bass',pitch:0}),43);
 assert.ok(Math.abs(notation.frequency({clef:'bass',pitch:0})-97.998859)<.0001);
 assert.equal(notation.midi({clef:'treble',pitch:3}),69);
 assert.equal(notation.frequency({clef:'treble',pitch:3}),440);
 for(const note of [{clef:'treble',pitch:-2},{clef:'bass',pitch:10}]){
  assert.equal(notation.letter(note),'C');
  assert.equal(notation.midi(note),60);
  assert.ok(Math.abs(notation.frequency(note)-261.625565)<.0001);
 }
 assert.equal(notation.letter({clef:'treble',pitch:-1}),'D');
 assert.equal(notation.letter({clef:'bass',pitch:9}),'B');
});

test('grand staff has ten lines with Middle C between the two staves',()=>{
 const grand=notation.geometry('grand');
 assert.deepEqual(grand.staves,[{clef:'treble',top:30,bottom:118},{clef:'bass',top:162,bottom:250}]);
 assert.equal(notation.noteY({clef:'treble',pitch:0},'grand'),118);
 assert.equal(notation.noteY({clef:'bass',pitch:0},'grand'),250);
 for(const note of [{clef:'treble',pitch:-2},{clef:'bass',pitch:10}]){
  assert.equal(notation.noteY(note,'grand'),140);
  assert.deepEqual(notation.ledgerLines(note,'grand'),[140]);
 }
 assert.deepEqual(notation.ledgerLines({clef:'treble',pitch:-1},'grand'),[]);
 assert.deepEqual(notation.ledgerLines({clef:'bass',pitch:9},'grand'),[]);
 assert.deepEqual(notation.ledgerLines({clef:'treble',pitch:12},'grand'),[8,-14]);
});

test('curriculum introduces bass at eleven and both staves at twenty-one',()=>{
 assert.equal(notation.levelStaff(1),'treble');
 assert.equal(notation.levelStaff(10),'treble');
 assert.equal(notation.levelStaff(11),'bass');
 assert.equal(notation.levelStaff(20),'bass');
 assert.equal(notation.levelStaff(21),'grand');
 assert.equal(notation.levelStaff(50),'grand');
 const counts={treble:0,bass:0};
 for(let i=0;i<50;i++)counts[notation.chooseClef('grand',i)]++;
 assert.deepEqual(counts,{treble:25,bass:25});
 assert.equal(notation.chooseClef('bass',4),'bass');
 assert.equal(notation.normalizeStaff('invalid'),'treble');
});

test('horizontal projection preserves the answer line and visible entry at mobile widths',()=>{
 for(const width of [513,550,640,920]){
  assert.equal(notation.projectX(98,width),98);
  assert.ok(Math.abs(notation.projectX(890,width)-(width-30))<.00001);
  assert.ok(notation.projectX(500,width)>98);
  assert.ok(notation.projectX(500,width)<width-30);
 }
});
