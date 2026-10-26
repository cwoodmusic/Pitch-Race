"""Actual game frames keep classroom progress private from public services.

The fixture serves all three sibling games at their real public origin and
records requests while blocking external services. Public-mode SDK behavior is
checked with a local Firebase test double, never a live account or database.
"""
import importlib.util
import json
import mimetypes
from pathlib import Path
import sys
import unittest
from urllib.parse import parse_qs, unquote, urlparse

sys.dont_write_bytecode = True
from pitch_browser_support import PitchBrowserCase, FIXTURE, ORIGIN, PITCH

WORKSPACE = Path(__file__).resolve().parents[2]
ROOTS = {'Pitch-Race': WORKSPACE/'Pitch-Race', 'musictriad': WORKSPACE/'musictriad',
         'rhythmroom': WORKSPACE/'rhythmroom'}
GAMES = {'pitch':'Pitch-Race', 'triad':'musictriad', 'rhythm':'rhythmroom'}
HOST = ORIGIN+'/coda-arcade/classroom-game-fixture.html'

PUBLIC_FIREBASE = r'''(()=>{
 const log=window.__firebaseTest={signins:0,reads:[],listeners:[]};
 const snapshot={val:()=>0,forEach:()=>{}};
 const db={ref:path=>({once:async()=>{log.reads.push(path);return snapshot;},
   on:()=>log.listeners.push(path)})};
 const auth={currentUser:null,signInAnonymously:async()=>{log.signins++;auth.currentUser={uid:'test-user'};}};
 window.firebase={apps:[],initializeApp(){this.apps.push({});},database:()=>db,auth:()=>auth};
 window.firebase.database.ServerValue={TIMESTAMP:0};
})()'''

PITCH_PROBE = r'''
window.__privacyGuardProbe=async()=>{
 const before=gameMode;
 await offerHighScore({score:999,streak:10},'classic');await submitInitials();await openScores();
 return {before,after:gameMode,scoresHidden:$('scoresOverlay').classList.contains('hidden'),
   initialsHidden:$('initialsOverlay').classList.contains('hidden'),lobbyHidden:$('multiLobby').classList.contains('hidden')};
};
'''


class ClassroomPrivacyTests(PitchBrowserCase):
    def setUp(self):
        self.sdk_double=False
        self.requests=[]
        super().setUp()
        self.context.on('request',lambda request:self.requests.append(request.url))

    def route_checkout(self,route):
        parsed=urlparse(route.request.url)
        if parsed.path=='/coda-arcade/classroom-game-fixture.html':
            query=parse_qs(parsed.query);game=query.get('game',['pitch'])[0]
            flag=query.get('flag',['1'])[0]=='1';parent_mode=query.get('parent',['1'])[0]=='1'
            privacy=query.get('privacy',['0'])[0]=='1';scoped=query.get('scoped',['0'])[0]=='1'
            config={'mode':'classroom' if privacy else 'legacy','classroom':{'enabled':parent_mode,'privacy':privacy}}
            src='/'+GAMES[game]+'/' + ('?classroom=1' if flag else '')
            body='''<!doctype html><title>Private classroom game fixture</title>
<script>window.ARCADE_ACCOUNTS_CONFIG=__CONFIG_VALUE__;window.__reports=[];
if(__SCOPED_VALUE__){
 window.__fixtureRawStorage=localStorage;__fixtureRawStorage.setItem('private-origin-marker','another profile');
 const stores=new Map();window.__installFixtureProfile=id=>{
  const values=stores.get(id)||new Map([['profile-marker',id]]);stores.set(id,values);
  const storage={__codaClassroomScoped:true,get length(){return values.size},key:i=>[...values.keys()][i]??null,
   getItem:key=>values.get(String(key))??null,setItem:(key,value)=>values.set(String(key),String(value)),
   removeItem:key=>values.delete(String(key)),clear:()=>values.clear()};
  Object.defineProperty(window,'localStorage',{configurable:true,get:()=>storage});
 };__installFixtureProfile('student-a');
}
addEventListener('message',event=>{const frame=document.querySelector('iframe');
 if(event.origin!==location.origin||event.source!==frame?.contentWindow||!event.data?.coda)return;
 if(event.data.type==='ready')frame.contentWindow.postMessage({coda:1,type:'init',game:GAME,token:'private-classroom-test'},location.origin);
 if(event.data.type==='result')window.__reports.push(event.data);
});</script><iframe id="game" style="width:1400px;height:1000px;border:0" src="SOURCE"></iframe>'''
            body=body.replace('__CONFIG_VALUE__',json.dumps(config)).replace('__SCOPED_VALUE__',str(scoped).lower()).replace('GAME',json.dumps(game)).replace('SOURCE',src)
            return route.fulfill(body=body,content_type='text/html')
        for folder,root in ROOTS.items():
            prefix='/'+folder+'/'
            if parsed.path.startswith(prefix):
                relative=unquote(parsed.path.removeprefix(prefix)) or 'index.html'
                file=(root/relative).resolve()
                if not file.is_relative_to(root) or not file.is_file():
                    self.missing.append(parsed.path);return route.fulfill(status=404,body='Missing test resource')
                if folder=='Pitch-Race' and file.name=='index.html':
                    text=file.read_text();marker='initializeOnlineScores();})();'
                    assert text.count(marker)==1
                    text=text.replace(marker,'initializeOnlineScores();'+FIXTURE+PITCH_PROBE+'})();')
                    return route.fulfill(body=text,content_type='text/html')
                return route.fulfill(path=str(file),content_type=mimetypes.guess_type(str(file))[0] or 'application/octet-stream')
        if parsed.path=='/favicon.ico':return route.fulfill(status=204)
        return route.abort()

    def block_external(self,route):
        if self.sdk_double and route.request.url.startswith('https://www.gstatic.com/firebasejs/'):
            return route.fulfill(body=PUBLIC_FIREBASE if 'firebase-app-' in route.request.url else '',content_type='text/javascript')
        return super().block_external(route)

    def host(self,game,flag=True,parent=True,privacy=False,scoped=False):
        self.page.goto(HOST+f'?game={game}&flag={int(flag)}&parent={int(parent)}&privacy={int(privacy)}&scoped={int(scoped)}',wait_until='domcontentloaded')
        frame=self.page.locator('#game').element_handle().content_frame()
        frame.wait_for_function('window.CodaBridge')
        if game in ('pitch','triad'):frame.wait_for_function('window.CodaGamePrivacy')
        return frame

    def assert_no_cloud_requests(self):
        external=[url for url in self.requests if not url.startswith(ORIGIN+'/') and not url.startswith(('data:','blob:'))]
        self.assertEqual(external,[],'Classroom frames must not load SDKs or contact public services')
        self.assertEqual(self.external_writes,[])

    def test_pitch_classroom_solo_has_no_sdk_initials_or_public_score_side_effects(self):
        frame=self.host('pitch',parent=False)
        self.assertTrue(frame.evaluate('CodaGamePrivacy.enabled'))
        self.assertFalse(frame.evaluate('Boolean(window.firebase)'))
        self.assertTrue(frame.locator('#highScoresButton').is_hidden())
        self.assertTrue(frame.locator('#multiCard').is_visible())
        guard=frame.evaluate('window.__privacyGuardProbe()')
        self.assertEqual(guard,{'before':'classic','after':'classic',
                                'scoresHidden':True,'initialsHidden':True,'lobbyHidden':True})
        offers_after_direct_probe=frame.evaluate('window.__pitchScoreOffers.length')
        self.start(frame,mode='classic');self.answer(frame);self.expire(frame)
        self.page.wait_for_function('__reports.length===1')
        self.assertEqual(self.page.evaluate('__reports[0].result.correct'),1)
        self.assertEqual(self.page.evaluate('__reports[0].result.score'),1)
        self.assertTrue(frame.locator('#initialsOverlay').is_hidden())
        self.assertEqual(frame.evaluate('window.__pitchScoreOffers.length'),offers_after_direct_probe)
        self.assert_no_cloud_requests()

    def test_enabled_parent_enforces_classroom_privacy_without_query_flag(self):
        for game in ['pitch','triad']:
            with self.subTest(game=game):
                frame=self.host(game,flag=False)
                self.assertTrue(frame.evaluate('CodaGamePrivacy.enabled'))
                self.assertFalse(frame.evaluate('Boolean(window.firebase)'))
                self.assert_no_cloud_requests()

    def test_privacy_policy_still_blocks_services_while_enrollment_is_disabled(self):
        for game in ['pitch','triad']:
            with self.subTest(game=game):
                frame=self.host(game,flag=False,parent=False,privacy=True)
                self.assertTrue(frame.evaluate('CodaGamePrivacy.enabled'))
                self.assertFalse(frame.evaluate('Boolean(window.firebase)'))
                self.assert_no_cloud_requests()

    def test_all_game_frames_inherit_the_captured_scoped_store_and_never_redirect_to_another_student(self):
        for game in ['pitch','triad','rhythm']:
            with self.subTest(game=game):
                frame=self.host(game,flag=False,parent=False,privacy=True,scoped=True)
                self.assertTrue(frame.evaluate('localStorage.__codaClassroomScoped===true'))
                self.assertEqual(frame.evaluate('localStorage.getItem("profile-marker")'),'student-a')
                self.assertIsNone(frame.evaluate('localStorage.getItem("private-origin-marker")'))
                frame.evaluate('localStorage.setItem("game-result","student-a-progress")')
                self.assertEqual(self.page.evaluate('localStorage.getItem("game-result")'),'student-a-progress')
                self.page.evaluate('__installFixtureProfile("student-b")')
                self.assertEqual(self.page.evaluate('localStorage.getItem("profile-marker")'),'student-b')
                self.assertEqual(frame.evaluate('localStorage.getItem("profile-marker")'),'student-a')
                frame.evaluate('localStorage.setItem("game-result","old-frame-write")')
                self.assertIsNone(self.page.evaluate('localStorage.getItem("game-result")'))
                self.assertIsNone(self.page.evaluate('__fixtureRawStorage.getItem("game-result")'))
                self.assert_no_cloud_requests()

    def test_triad_private_advanced_tie_and_win_keep_the_parent_bridge(self):
        frame=self.host('triad',parent=False)
        frame.locator('label.mode-toggle').click();frame.locator('#vsComputer').click()
        for selector in ['#vsClassmate','#tournamentMode']:self.assertTrue(frame.locator(selector).is_disabled())
        self.assertFalse(frame.evaluate('Boolean(window.firebase)'))
        frame.evaluate('''()=>{
          cancelTriadAnimations();codaTriadReset();
          const mine=[0,1,2,3,4,6,9];
          board=Array.from({length:16},(_,i)=>i===5?null:{owner:mine.includes(i)?0:1,e:Array(4).fill('qn'),meter:'4/4'});
          hands=[[{owner:0,e:Array(4).fill('qn'),meter:'4/4'}],[]];turn=0;busy=false;endSoundPlayed=false;selected=null;render();
        }''')
        first_id=frame.evaluate('codaTriadState.id')
        frame.locator('#hand .pick').first.click();frame.locator('#board .slot').nth(5).click()
        frame.wait_for_function('document.querySelectorAll("#board .slot.empty").length===16')
        self.assertEqual(frame.locator('#hand .pick').count(),5)
        self.assertEqual(frame.evaluate('codaTriadState.id'),first_id)
        self.assertEqual(self.page.evaluate('__reports'),[])
        frame.evaluate('''()=>{
          cancelTriadAnimations();board=Array.from({length:16},(_,i)=>i===5?null:{owner:i===15?1:0,e:Array(4).fill('qn'),meter:'4/4'});
          hands=[[{owner:0,e:Array(4).fill('qn'),meter:'4/4'}],[]];turn=0;busy=false;selected=null;render();
        }''')
        frame.locator('#hand .pick').first.click();frame.locator('#board .slot').nth(5).click()
        self.page.wait_for_function('__reports.length===1')
        result=self.page.evaluate('__reports[0]')
        self.assertEqual(result['runId'],first_id);self.assertTrue(result['result']['won'])
        self.assertEqual(result['result']['rules'],'advanced')
        self.assertIn('You win',frame.locator('#status').inner_text())
        self.assert_no_cloud_requests()

    def test_standalone_online_sdk_bootstrap_remains_available_without_classroom_mode(self):
        self.sdk_double=True
        for game in ['pitch','triad']:
            with self.subTest(game=game):
                self.page.goto(ORIGIN+'/'+GAMES[game]+'/',wait_until='domcontentloaded')
                self.page.wait_for_function('window.CodaGameFirebaseReady')
                self.assertTrue(self.page.evaluate('CodaGameFirebaseReady'))
                self.assertFalse(self.page.evaluate('CodaGamePrivacy.enabled'))
                if game=='pitch':
                    self.page.wait_for_function('window.__firebaseTest.signins===1')
                    self.assertEqual(self.page.evaluate('__firebaseTest.reads'),['leaderboards/classic','leaderboards/endless','leaderboards/levels'])
                    self.assertTrue(self.page.locator('#highScoresButton').is_visible())
                    self.assertTrue(self.page.locator('#multiCard').is_visible())
                else:
                    self.assertTrue(self.page.locator('#vsClassmate').is_visible())
                    self.assertTrue(self.page.locator('#tournamentMode').is_visible())
                    self.page.evaluate('initFirebase()')
                    self.assertEqual(self.page.evaluate('__firebaseTest.signins'),1)

    def test_rhythm_room_already_keeps_classroom_play_local_and_reports_private_progress(self):
        spec=importlib.util.spec_from_file_location('rhythm_audio_probe',ROOTS['rhythmroom']/'tests/rhythm-count-in-browser.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.context.add_init_script(module.AUDIO_PROBE)
        frame=self.host('rhythm')
        frame.locator('#choose-tap').click();frame.locator('#count').uncheck()
        for checkbox in frame.locator('#choices input[type=checkbox]').all():checkbox.set_checked(checkbox.get_attribute('id')=='choose-quarter')
        frame.locator('#play').click();frame.wait_for_function('running&&!loading&&ctx&&snareBuffer')
        frame.evaluate("__audioTestTime=origin+11*(60/+$('tempo').value)")
        frame.wait_for_timeout(40)
        targets=frame.evaluate('({start:tapRound.start,targets:tapRound.targets})')
        for target in targets['targets']:
            frame.evaluate('time=>__audioTestTime=time',targets['start']+target)
            frame.locator('#tap-pad').click()
        frame.evaluate("__audioTestTime=origin+20*(60/+$('tempo').value)")
        self.page.wait_for_function('__reports.length===1')
        self.assertTrue(self.page.evaluate('__reports[0].result.perfect'))
        frame.locator('#stop').click()
        self.assert_no_cloud_requests()


if __name__=='__main__':unittest.main(verbosity=2)
