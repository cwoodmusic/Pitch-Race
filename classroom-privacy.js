/* Classroom games report progress to the parent, without separate cloud users. */
(function(root){
 'use strict';
 let enabled=false;
 try{enabled=new URLSearchParams(root.location.search).get('classroom')==='1';}catch{}
 try{
  const parent=root.parent;
  if(parent!==root&&parent.location.origin===root.location.origin){
   const config=parent.ARCADE_ACCOUNTS_CONFIG;
   if(config?.mode==='classroom'||config?.classroom?.privacy===true||config?.classroom?.enabled===true)enabled=true;
   const scoped=parent.localStorage;
   if(scoped?.__codaClassroomScoped===true){enabled=true;Object.defineProperty(root,'localStorage',{configurable:true,get:()=>scoped});}
  }
 }catch{}
 if(enabled)root.document.documentElement.dataset.classroom='true';
 let loading=null;
 function loadFirebaseSDK(){
  if(enabled)return Promise.resolve(false);
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
  return loading;
 }
 root.CodaGamePrivacy=Object.freeze({enabled,loadFirebaseSDK});
})(window);
