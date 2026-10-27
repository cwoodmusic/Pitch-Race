/* Classroom progress stays private; multiplayer connects only when requested. */
(function(root){
 'use strict';
 let enabled=false,testMode=false,inheritedStorage=false;
 try{enabled=new URLSearchParams(root.location.search).get('classroom')==='1';}catch{}
 try{
  const parent=root.parent;
  if(parent!==root&&parent.location.origin===root.location.origin){
   testMode=parent.CodaDeveloperTestMode?.isEnabled?.()===true;if(testMode)enabled=true;
   const config=parent.ARCADE_ACCOUNTS_CONFIG;
   if(config?.mode==='classroom'||config?.classroom?.privacy===true||config?.classroom?.enabled===true)enabled=true;
   const scoped=parent.localStorage;
   if(scoped&&(scoped.__codaClassroomScoped===true||testMode)){enabled=true;Object.defineProperty(root,'localStorage',{configurable:true,get:()=>scoped});inheritedStorage=true;}
  }
 }catch{}
 // Only an enabled, same-origin parent can request this sandbox. A query
 // parameter or a cross-origin frame cannot turn off ordinary online play.
 if(testMode){
  const doc=root.document,policy=doc.createElement('meta');policy.httpEquiv='Content-Security-Policy';policy.content="connect-src 'self'; form-action 'none'";policy.dataset.codaTestMode='';doc.head.append(policy);
  doc.documentElement.dataset.codaTestMode='true';
  if(!inheritedStorage){
   const values=new Map(),memory={__codaClassroomScoped:true,get length(){return values.size;},key:index=>[...values.keys()][index]??null,getItem:key=>values.get(String(key))??null,setItem:(key,value)=>values.set(String(key),String(value)),removeItem:key=>values.delete(String(key)),clear:()=>values.clear()};
   Object.defineProperty(root,'localStorage',{configurable:true,get:()=>memory});
  }
  const online='#multiCard,#multiCreate,#multiJoin,#multiReady,#multiStart,#highScoresButton,#initialsSave,#vsClassmate,#tournamentMode,#createRoom,#showJoin,#joinNow,#createTournament,#showTournamentJoin,#joinTournamentNow,#startTournament,#playTournamentMatch';
  const block=event=>{if(event.type==='keydown'&&!['Enter',' '].includes(event.key))return;if(!event.target?.closest?.(online))return;event.preventDefault();event.stopImmediatePropagation();};
  doc.addEventListener('click',block,true);doc.addEventListener('keydown',block,true);
  const show=()=>{
   if(!doc.body)return;
   if(!doc.getElementById('codaTestModeNotice')){const notice=doc.createElement('p');notice.id='codaTestModeNotice';notice.setAttribute('role','status');notice.textContent='Test mode uses local play';notice.style.cssText='margin:8px auto;padding:10px 14px;max-width:960px;border:1px solid #73b8ac;border-radius:8px;background:#183d40;color:#effff9;font:600 14px/1.4 system-ui';doc.body.prepend(notice);}
   for(const node of doc.querySelectorAll(online)){if('disabled'in node&&!node.disabled)node.disabled=true;if(node.getAttribute('aria-disabled')!=='true')node.setAttribute('aria-disabled','true');node.title='Test mode uses local play';}
  };
  if(doc.readyState==='loading')doc.addEventListener('DOMContentLoaded',show,{once:true});else show();
  if(typeof root.MutationObserver==='function')new root.MutationObserver(show).observe(doc.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['disabled','aria-disabled']});
 }
 if(enabled)root.document.documentElement.dataset.classroom='true';
 let loading=null;
 function loadFirebaseSDK(options={}){
  if(testMode)return Promise.resolve(false);
  if(enabled&&options.multiplayer!==true)return Promise.resolve(false);
  if(loading)return loading;
  loading=(async()=>{
   for(const name of ['app','auth','database']){
    const loaded=await new Promise(resolve=>{
     const script=root.document.createElement('script');
     script.src='https://www.gstatic.com/firebasejs/10.14.1/firebase-'+name+'-compat.js';
     script.onload=()=>resolve(true);script.onerror=()=>resolve(false);
     root.document.head.append(script);
    });
    if(!loaded)return false;
   }
   return true;
  })();
  loading.then(loaded=>{if(!loaded)loading=null;});
  return loading;
 }
 root.CodaGamePrivacy=Object.freeze({enabled,testMode,loadFirebaseSDK});
})(window);
