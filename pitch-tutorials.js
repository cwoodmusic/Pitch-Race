/* Small, unhurried reading lessons. Tutorial answers never touch race scores. */
(function(root,factory){
 'use strict';const api=factory();
 if(typeof module==='object'&&module.exports)module.exports=api;
 if(root)root.PitchRaceTutorials=api;
})(typeof window==='undefined'?null:window,function(){
 'use strict';
 const MNEMONICS=Object.freeze({
  trebleLines:Object.freeze({letters:'EGBDF',words:'Every Good Boy Does Fine'}),
  trebleSpaces:Object.freeze({letters:'FACE',words:'FACE'}),
  bassLines:Object.freeze({letters:'GBDFA',words:'Great Big Dreams For America'}),
  bassSpaces:Object.freeze({letters:'ACEG',words:'All Cows Eat Grass'})
 });
 const note=(clef,pitch)=>Object.freeze({clef,pitch,kind:'quarter'});
 const LESSONS=Object.freeze([
  {id:'treble',title:'Treble clef',summary:'Find letters on the lines and in the spaces.',steps:[
   {title:'Meet the treble staff',text:'A staff has five lines and four spaces. A note can sit on a line or in a space. Start at the bottom and work upward.',staff:'treble',guide:'all',hint:'First, look for the five long lines.'},
   {title:'Treble lines: E G B D F',text:'Say “Every Good Boy Does Fine.” The first letter of each word names a line, from the bottom to the top.',staff:'treble',guide:'lines',mnemonic:'trebleLines'},
   {title:'Your turn: a line note',text:'This note sits on the bottom line. What is its letter?',staff:'treble',note:note('treble',0),answer:'E',choices:['E','G','B'],hint:'Start with the first word: Every.',accessible:'A note on the lowest line of the treble staff.'},
   {title:'Treble spaces spell FACE',text:'Read the spaces from bottom to top: F, A, C, E. They spell FACE. These letters go between the lines.',staff:'treble',guide:'spaces',mnemonic:'trebleSpaces'},
   {title:'Your turn: a space note',text:'This note sits in the second space from the bottom. What is its letter?',staff:'treble',note:note('treble',3),answer:'A',choices:['F','A','C'],hint:'Count the spaces upward: F, then A.',accessible:'A note in the second space from the bottom of the treble staff.'},
   {title:'Try one more line',text:'This note sits on the top line. Use the last word of “Every Good Boy Does Fine.”',staff:'treble',note:note('treble',8),answer:'F',choices:['D','E','F'],hint:'The last word is Fine.',accessible:'A note on the highest line of the treble staff.'},
   {title:'You have two useful patterns',text:'For lines, use “Every Good Boy Does Fine.” For spaces, use FACE. Always begin at the bottom. Next, try three short questions.',staff:'treble',guide:'all'}
  ],quiz:[
   {title:'Treble quiz · 1 of 3',text:'What letter is on the bottom line?',staff:'treble',note:note('treble',0),answer:'E',choices:['E','F','G'],hint:'Every is the first word of the line saying.',accessible:'A note on the lowest line of the treble staff.'},
   {title:'Treble quiz · 2 of 3',text:'What letter is in the bottom space?',staff:'treble',note:note('treble',1),answer:'F',choices:['A','F','E'],hint:'The spaces spell FACE. Begin with F.',accessible:'A note in the lowest space of the treble staff.'},
   {title:'Treble quiz · 3 of 3',text:'Name the note on the middle line.',staff:'treble',note:note('treble',4),answer:'B',choices:['G','D','B'],hint:'Every, Good, Boy: the third line begins with B.',accessible:'A note on the middle line of the treble staff.'}
  ]},
  {id:'bass',title:'Bass clef',summary:'Read lower notes using two new sayings.',steps:[
   {title:'Meet the bass staff',text:'The bass clef is often used for lower notes. It has five lines and four spaces too. Its two dots sit around the F line.',staff:'bass',note:note('bass',6),guide:'f-line'},
   {title:'Bass lines: G B D F A',text:'Say “Great Big Dreams For America.” Use the first letter of each word, starting on the bottom line and moving upward.',staff:'bass',guide:'lines',mnemonic:'bassLines'},
   {title:'Your turn: the bottom line',text:'Which letter belongs on this bottom line?',staff:'bass',note:note('bass',0),answer:'G',choices:['E','G','A'],hint:'Start with Great.',accessible:'A note on the lowest line of the bass staff.'},
   {title:'Bass spaces: A C E G',text:'Say “All Cows Eat Grass.” The first letters name the spaces from the bottom to the top.',staff:'bass',guide:'spaces',mnemonic:'bassSpaces'},
   {title:'Your turn: the bottom space',text:'Which letter belongs in this bottom space?',staff:'bass',note:note('bass',1),answer:'A',choices:['A','C','G'],hint:'The first word is All.',accessible:'A note in the lowest space of the bass staff.'},
   {title:'Find the middle line',text:'Use “Great Big Dreams For America.” What letter is on the middle line?',staff:'bass',note:note('bass',4),answer:'D',choices:['B','D','F'],hint:'The third word is Dreams.',accessible:'A note on the middle line of the bass staff.'},
   {title:'Look at the clef first',text:'The same staff position has a different letter in each clef. Check the clef, then choose the line saying or the space saying. Now try three questions.',staff:'bass',guide:'all'}
  ],quiz:[
   {title:'Bass quiz · 1 of 3',text:'Name the note on the bottom line.',staff:'bass',note:note('bass',0),answer:'G',choices:['G','E','B'],hint:'Great is the first word of the bass-line saying.',accessible:'A note on the lowest line of the bass staff.'},
   {title:'Bass quiz · 2 of 3',text:'Which letter is on the line between the bass clef’s two dots?',staff:'bass',note:note('bass',6),answer:'F',choices:['D','A','F'],hint:'Great, Big, Dreams, For: the fourth line is F.',accessible:'A note on the fourth line from the bottom of the bass staff, between the clef dots.'},
   {title:'Bass quiz · 3 of 3',text:'What letter is in the second space from the bottom?',staff:'bass',note:note('bass',3),answer:'C',choices:['A','C','E'],hint:'All Cows: the second space begins with C.',accessible:'A note in the second space from the bottom of the bass staff.'}
  ]},
  {id:'grand',title:'Grand staff & middle C',summary:'Join treble and bass, with middle C between them.',steps:[
   {title:'Two staves work together',text:'A grand staff joins a treble staff above a bass staff. The curly brace shows that they belong together. Check which staff your note is on.',staff:'grand',guide:'clefs'},
   {title:'Meet middle C',text:'Middle C sits between the two staves. Its short extra line is called a ledger line. It is still just one note: C.',staff:'grand',note:note('treble',-2),middleC:true,hear:true},
   {title:'The same C in bass clef',text:'Middle C can also be written just above the bass staff, using a short ledger line. It makes the same sound as the middle C you just saw.',staff:'grand',note:note('bass',10),middleC:true,hear:true},
   {title:'First, choose the clef',text:'This note is on the lower staff. Which clef should you read?',staff:'grand',note:note('bass',4),answer:'Bass',choices:['Treble','Bass'],hint:'The grand staff puts bass below treble.',accessible:'A note on the lower staff of a grand staff.'},
   {title:'Then, name the note',text:'This note is on the second line from the bottom of the upper staff. What is its letter?',staff:'grand',note:note('treble',2),answer:'G',choices:['E','G','B'],hint:'Use the treble-line saying: Every Good…',accessible:'A note on the second line from the bottom of the upper treble staff.'},
   {title:'Your turn: middle C',text:'Name the note on the short ledger line between the staves.',staff:'grand',note:note('treble',-2),middleC:true,answer:'C',choices:['C','D','F'],hint:'This is the connecting note you just learned.',accessible:'A note on the short ledger line between the treble and bass staves.'},
   {title:'You can read both staves',text:'Check the clef. Check whether the note is on a line or in a space. Use the matching saying. Middle C connects the two staves. Ready for three questions?',staff:'grand',guide:'clefs'}
  ],quiz:[
   {title:'Grand staff quiz · 1 of 3',text:'Which clef is on the upper staff?',staff:'grand',guide:'upper',answer:'Treble',choices:['Bass','Treble'],hint:'Treble is above bass on a grand staff.'},
   {title:'Grand staff quiz · 2 of 3',text:'Name this note on the bottom line of the lower staff.',staff:'grand',note:note('bass',0),answer:'G',choices:['E','G','A'],hint:'Use the bass-line saying: Great Big Dreams For America.',accessible:'A note on the lowest line of the lower bass staff.'},
   {title:'Grand staff quiz · 3 of 3',text:'Which note sits on this short ledger line between the staves?',staff:'grand',note:note('bass',10),middleC:true,answer:'C',choices:['F','B','C'],hint:'The note that connects the staves is middle C.',accessible:'A note on the ledger line between the treble and bass staves.'}
  ]}
 ].map(lesson=>Object.freeze({...lesson,steps:Object.freeze(lesson.steps.map(Object.freeze)),quiz:Object.freeze(lesson.quiz.map(Object.freeze))})));
 const KEY='pitchRaceTutorialsV1';
 function create(api={}){
  const host=api.host;if(!host)throw Error('Pitch tutorials need a host.');
  const doc=host.ownerDocument,win=doc.defaultView,notation=api.notation||win.CodaPitchNotation;
  if(!notation?.drawStaff||!notation?.drawNote)throw Error('Pitch tutorials need the pitch notation renderer.');
  const listen=[],launchers=Array.from(doc.querySelectorAll('[data-pitch-tutorials-open]'));
  let opened=false,lesson=null,step=0,phase='home',correct=0,answered=false,attempts=0,priorFocus=null,disposed=false,completed=new Set(),storage=api.storage;
  if(storage===undefined)try{storage=win.localStorage;}catch{storage=null;}
  try{const saved=JSON.parse(storage?.getItem(KEY)||'null');for(const id of saved?.completed||[])if(LESSONS.some(item=>item.id===id))completed.add(id);}catch{}
  const add=(target,name,fn,options)=>{target.addEventListener(name,fn,options);listen.push(()=>target.removeEventListener(name,fn,options));};
  host.hidden=true;host.classList.add('pitch-tutorials-backdrop');
  host.innerHTML='<section class="pitch-tutorials-panel" role="dialog" aria-modal="true" aria-labelledby="pitchTutorialTitle"><header class="pitch-tutorials-heading"><div><p class="pitch-tutorials-kicker">LEARN TO READ THE STAFF</p><h2 id="pitchTutorialTitle">Pitch-reading tutorials</h2></div><button type="button" id="pitchTutorialClose" aria-label="Close pitch tutorials">Close</button></header><div id="pitchTutorialProgress" class="pitch-tutorials-progress"></div><div class="pitch-tutorials-body"><div><p id="pitchTutorialText" class="pitch-tutorials-text"></p><p id="pitchTutorialMnemonic" class="pitch-tutorials-mnemonic" hidden></p><div id="pitchTutorialChoices" class="pitch-tutorials-choices"></div><p id="pitchTutorialFeedback" class="pitch-tutorials-feedback" role="status" aria-live="polite"></p></div><div id="pitchTutorialExample" class="pitch-tutorials-example"></div></div><footer class="pitch-tutorials-footer"><button type="button" id="pitchTutorialAll">All lessons</button><button type="button" id="pitchTutorialHear" hidden>Hear middle C</button><button type="button" id="pitchTutorialNext">Next</button></footer></section>';
  const el=id=>host.querySelector('#'+id),panel=host.querySelector('.pitch-tutorials-panel');
  function canOpen(){let state;try{state=api.getState?.();}catch{return false;}const value=typeof state==='string'?state:state?.state;return !['running','countdown'].includes(value);}
  function current(){return lesson&&['lesson','quiz'].includes(phase)?(phase==='quiz'?lesson.quiz[step]:lesson.steps[step]):null;}
  function setText(id,value){el(id).textContent=value||'';}
  function button(label,callback){const b=doc.createElement('button');b.type='button';b.textContent=label;b.onclick=callback;return b;}
  function drawExample(item){
   const area=el('pitchTutorialExample');area.replaceChildren();if(!item){area.hidden=true;return;}area.hidden=false;
   const width=Math.max(260,Math.min(620,Math.round(area.clientWidth||430))),svg=doc.createElementNS('http://www.w3.org/2000/svg','svg');
   const geometry=notation.drawStaff(svg,item.staff,{width,hitLine:false}),staves=geometry.staves;
   svg.setAttribute('aria-label',item.accessible||('A '+(item.staff==='grand'?'grand staff':item.staff+' staff')+' example.'));area.append(svg);
   const shape=(tag,attrs)=>{const node=doc.createElementNS(svg.namespaceURI,tag);for(const [name,value]of Object.entries(attrs))node.setAttribute(name,String(value));svg.append(node);return node;};
   if(item.guide){
    for(const stave of staves){
     if(item.guide==='upper'&&stave.clef!=='treble')continue;
     if(['clefs','upper'].includes(item.guide)){
      shape('rect',{x:5,y:stave.top-15,width:width-10,height:stave.bottom-stave.top+30,fill:stave.clef==='treble'?'#e2f2ff':'#f4eaff',opacity:.35,rx:8});
      const label=shape('text',{x:width-15,y:stave.top-4,fill:'#28477a','font-size':14,'text-anchor':'end','font-weight':750});label.textContent=stave.clef==='treble'?'Treble · upper':'Bass · lower';
      continue;
     }
     const indices=item.guide==='f-line'?[6]:item.guide==='spaces'?[1,3,5,7]:item.guide==='lines'?[0,2,4,6,8]:[0,1,2,3,4,5,6,7,8];
     for(const pitch of indices){const example={clef:stave.clef,pitch,kind:'quarter'},y=notation.noteY(example,item.staff),line=pitch%2===0;
      shape('line',{y1:y,x1:100,x2:width-35,y2:y,stroke:line?'#3c78ba':'#8c55ab','stroke-width':line?3:2,opacity:.3});
      const label=shape('text',{x:width-17,y:y+5,fill:line?'#235f9e':'#7c399a','font-size':15,'text-anchor':'middle','font-weight':800});label.textContent=notation.letter(example);
     }
    }
   }
   if(item.note){const node=notation.drawNote(svg,{...item.note,x:width*.55},{staff:item.staff,x:width*.55,color:'#2854bb',label:false});if(node){node.removeAttribute('aria-label');node.querySelectorAll('title').forEach(title=>title.remove());}
    if(item.middleC){const y=notation.noteY(item.note,item.staff);shape('circle',{cx:width*.55,cy:y,r:17,fill:'none',stroke:'#e2aa2c','stroke-width':3});if(!item.answer){const label=shape('text',{x:width*.55+30,y:y+5,fill:'#6e5014','font-size':14,'font-weight':750});label.textContent='Middle C';}}
   }
  }
  function renderHome(){
   lesson=null;phase='home';step=correct=attempts=0;answered=false;setText('pitchTutorialTitle','Pitch-reading tutorials');setText('pitchTutorialProgress','Choose a lesson. Go at your own pace.');setText('pitchTutorialText','Learn one small idea, try it, then answer three short questions. Nothing here changes your race score.');el('pitchTutorialMnemonic').hidden=true;setText('pitchTutorialFeedback','');el('pitchTutorialChoices').replaceChildren();
   for(const item of LESSONS){const b=button((completed.has(item.id)?'✓ ':'')+item.title,()=>start(item.id));b.dataset.pitchLesson=item.id;const details=doc.createElement('small');details.textContent=item.summary;b.append(details);el('pitchTutorialChoices').append(b);}
   el('pitchTutorialNext').hidden=el('pitchTutorialAll').hidden=el('pitchTutorialHear').hidden=true;drawExample(null);panel.scrollTop=0;
  }
  function render(){
   if(!lesson){renderHome();return;}
   const item=current();answered=false;setText('pitchTutorialTitle',item.title);setText('pitchTutorialProgress',phase==='quiz'?'Short quiz · '+(step+1)+' / '+lesson.quiz.length:'Lesson · '+(step+1)+' / '+lesson.steps.length);setText('pitchTutorialText',item.text);setText('pitchTutorialFeedback','');
   const mnemonic=MNEMONICS[item.mnemonic];el('pitchTutorialMnemonic').hidden=!mnemonic;if(mnemonic)setText('pitchTutorialMnemonic',mnemonic.words+'\n'+mnemonic.letters.split('').join(' · ')+'\nBottom → top');
   el('pitchTutorialChoices').replaceChildren();
   if(item.answer)for(const choice of item.choices){const b=button(choice,()=>answer(choice));b.dataset.answer=choice;b.setAttribute('aria-keyshortcuts',choice.length===1?choice:String(item.choices.indexOf(choice)+1));el('pitchTutorialChoices').append(b);}
   el('pitchTutorialNext').hidden=false;el('pitchTutorialNext').disabled=!!item.answer;el('pitchTutorialNext').textContent=phase==='quiz'?(step===lesson.quiz.length-1?'Finish quiz':'Next question'):step===lesson.steps.length-1?'Try the quiz':'Next';
   el('pitchTutorialAll').hidden=false;el('pitchTutorialHear').hidden=!item.hear||typeof api.hearNote!=='function';drawExample(item);panel.scrollTop=0;
  }
  function start(id){const found=LESSONS.find(item=>item.id===id);if(!found)return false;lesson=found;phase='lesson';step=correct=attempts=0;render();return true;}
  function answer(value){const item=current();if(!opened||!item?.answer||answered)return false;attempts++;
   if(String(value).toLowerCase()!==item.answer.toLowerCase()){setText('pitchTutorialFeedback','Try again. '+item.hint);el('pitchTutorialFeedback').dataset.kind='hint';return false;}
   answered=true;if(phase==='quiz')correct++;setText('pitchTutorialFeedback',phase==='quiz'?'Correct!':'Yes! That’s right.');el('pitchTutorialFeedback').dataset.kind='correct';el('pitchTutorialNext').disabled=false;for(const b of el('pitchTutorialChoices').querySelectorAll('button')){b.disabled=true;if(b.dataset.answer===item.answer)b.classList.add('is-correct');}return true;
  }
  function finish(){
   const id=lesson.id;completed.add(id);try{storage?.setItem(KEY,JSON.stringify({version:1,completed:[...completed]}));}catch{}
   phase='complete';setText('pitchTutorialTitle',lesson.title+' · complete');setText('pitchTutorialProgress','3 / 3 questions answered');setText('pitchTutorialText','Well done! You used the staff patterns to answer all three questions. You can review this lesson whenever you want.');el('pitchTutorialMnemonic').hidden=true;setText('pitchTutorialFeedback','Ready to use this in a race? Start slowly and check the clef first.');el('pitchTutorialChoices').replaceChildren();drawExample(null);el('pitchTutorialHear').hidden=true;el('pitchTutorialNext').hidden=false;el('pitchTutorialNext').disabled=false;el('pitchTutorialNext').textContent='Choose another lesson';panel.scrollTop=0;try{api.onComplete?.(id);}catch{}
  }
  function next(){if(phase==='complete'){renderHome();return;}if(!lesson)return;const item=current();if(item.answer&&!answered)return;if(phase==='lesson'&&step===lesson.steps.length-1){phase='quiz';step=correct=0;render();return;}if(phase==='quiz'&&step===lesson.quiz.length-1){finish();return;}step++;render();}
  function syncLaunchers(){const disabled=!canOpen();for(const b of launchers){b.disabled=disabled;b.title=disabled?'Finish or reset the race before opening tutorials.':'Learn treble clef, bass clef, and the grand staff.';}if(opened&&disabled)close(false);}
  function open(id){if(disposed||!canOpen())return false;priorFocus=doc.activeElement;opened=true;host.hidden=false;syncLaunchers();if(id)start(id);else renderHome();el('pitchTutorialClose').focus({preventScroll:true});return true;}
  function close(restore=true){if(!opened)return;opened=false;host.hidden=true;try{api.onClose?.();}catch{}if(restore&&priorFocus?.isConnected)priorFocus.focus({preventScroll:true});}
  add(el('pitchTutorialClose'),'click',()=>close());add(el('pitchTutorialAll'),'click',renderHome);add(el('pitchTutorialNext'),'click',next);add(el('pitchTutorialHear'),'click',()=>{const item=current();if(item?.note)api.hearNote?.({...item.note});});
  add(host,'click',event=>{if(event.target===host)close();});for(const b of launchers)add(b,'click',()=>open());
  add(win,'keydown',event=>{if(!opened)return;if(event.key==='Escape'){event.preventDefault();event.stopImmediatePropagation();close();return;}
   if(event.key==='Tab'){const controls=[...host.querySelectorAll('button:not(:disabled)')].filter(b=>b.getClientRects().length);const first=controls[0],last=controls.at(-1);if(!host.contains(doc.activeElement)){event.preventDefault();(event.shiftKey?last:first)?.focus();}else if(event.shiftKey&&doc.activeElement===first){event.preventDefault();last?.focus();}else if(!event.shiftKey&&doc.activeElement===last){event.preventDefault();first?.focus();}return;}
   const item=current();if(item?.answer&&!answered&&!event.ctrlKey&&!event.metaKey&&!event.altKey){const choices=item.choices,match=/^[1-9]$/.test(event.key)?choices[Number(event.key)-1]:choices.find(choice=>choice.length===1&&choice.toUpperCase()===event.key.toUpperCase());if(match){event.preventDefault();event.stopImmediatePropagation();answer(match);}}
  },{capture:true});
  add(win,'resize',()=>{if(opened&&lesson&&phase!=='complete')drawExample(current());});const timer=win.setInterval(syncLaunchers,150);syncLaunchers();
  return{open,close,start,answer,next,getState:()=>({open:opened,lesson:lesson?.id||null,step,phase,question:current()?.answer?{answer:current().answer,choices:[...current().choices]}:null,correct,total:lesson?.quiz.length||0,answered,attempts,completed:[...completed]}),destroy(){if(disposed)return;close(false);disposed=true;win.clearInterval(timer);listen.forEach(remove=>remove());host.replaceChildren();}};
 }
 return Object.freeze({KEY,MNEMONICS,LESSONS,create});
});
