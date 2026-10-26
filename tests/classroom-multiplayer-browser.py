"""Classroom Create/Join uses room-only Firebase doubles after an explicit click.

Two actual game frames share an in-memory room service. No deployed Firebase
account, room, or leaderboard is accessed.
"""
import sys
import unittest
from urllib.parse import urlparse

sys.dont_write_bytecode=True
from pitch_browser_support import PitchBrowserCase,ORIGIN,PITCH

HOST=ORIGIN+'/coda-arcade/pitch-multiplayer-fixture.html'
SDK=r'''(()=>{
 const server=parent.__roomServer||(parent.__roomServer={data:{},listeners:[],log:[],serial:0});
 const uid='temporary-player-'+(++server.serial),clone=x=>JSON.parse(JSON.stringify(x));
 const read=path=>path.split('/').reduce((v,k)=>v?.[k],server.data)??null;
 const write=(path,value)=>{const keys=path.split('/');let target=server.data;for(const key of keys.slice(0,-1))target=target[key]||(target[key]={});target[keys.at(-1)]=clone(value);};
 const snapshot=path=>({val:()=>path==='.info/serverTimeOffset'?0:clone(read(path)),forEach(){}});
 const notify=()=>{for(const item of server.listeners.slice())if(item.active)queueMicrotask(()=>{if(item.active)item.fn(snapshot(item.path));});};
 const reference=path=>({
   child:key=>reference(path+'/'+key),
   once:async()=>{server.log.push(['read',uid,path]);return snapshot(path);},
   on:(event,fn)=>{server.log.push(['listen',uid,path]);server.listeners.push({path,fn,active:true});queueMicrotask(()=>fn(snapshot(path)));},
   off:(event,fn)=>{for(const item of server.listeners)if(item.path===path&&item.fn===fn)item.active=false;},
   transaction:async updater=>{const value=updater(clone(read(path)));if(value===undefined)return{committed:false};server.log.push(['write',uid,path]);write(path,value);notify();return{committed:true,snapshot:snapshot(path)};},
   update:async values=>{server.log.push(['write',uid,path]);for(const[key,value]of Object.entries(values))write(path+'/'+key,value);notify();}
 });
 const auth={currentUser:null,setPersistence:async value=>{server.log.push(['persistence',uid,value]);},
   signInAnonymously:async()=>{server.log.push(['signin',uid]);if(parent.__deferAuth)await new Promise(resolve=>parent.__releaseAuth=resolve);auth.currentUser={uid};return{user:auth.currentUser};}};
 const authFactory=()=>auth;authFactory.Auth={Persistence:{NONE:'none'}};
 window.firebase={apps:[],initializeApp(){this.apps.push({});},auth:authFactory,database:()=>({ref:reference})};
 firebase.database.ServerValue={TIMESTAMP:1234};
})()'''


class ClassroomMultiplayerTests(PitchBrowserCase):
    def setUp(self):
        self.sdk_requests=[];self.hold_sdk=False;self.held_route=None;self.fail_sdk=False
        super().setUp()

    def route_checkout(self,route):
        if urlparse(route.request.url).path=='/coda-arcade/pitch-multiplayer-fixture.html':
            return route.fulfill(content_type='text/html',body='''<!doctype html><meta charset="utf-8">
<script>window.ARCADE_ACCOUNTS_CONFIG={mode:'classroom',classroom:{privacy:true,enabled:true}};</script>
<iframe id="host" style="width:1400px;height:1000px" src="/Pitch-Race/?classroom=1"></iframe>
<iframe id="guest" style="width:1400px;height:1000px" src="/Pitch-Race/?classroom=1"></iframe>''')
        return super().route_checkout(route)

    def block_external(self,route):
        if route.request.url.startswith('https://www.gstatic.com/firebasejs/'):
            self.sdk_requests.append(route.request.url)
            if self.fail_sdk:
                self.fail_sdk=False;return route.abort()
            if self.hold_sdk:
                self.hold_sdk=False;self.held_route=route;return
            return self.serve_sdk(route)
        return super().block_external(route)

    def serve_sdk(self,route):
        route.fulfill(content_type='text/javascript',body=SDK if 'firebase-app-' in route.request.url else '')

    def frames(self):
        self.page.goto(HOST,wait_until='domcontentloaded')
        result=[]
        for selector in ['#host','#guest']:
            frame=self.page.locator(selector).element_handle().content_frame()
            frame.wait_for_function('window.__pitchFixture')
            result.append(frame)
        return result

    def lobby(self,frame):
        frame.locator('#multiCard').click();frame.locator('#menuPlay').click()
        frame.locator('#multiCreate').wait_for(state='visible')

    def logs(self):return self.page.evaluate('window.__roomServer?.log||[]')

    def assert_private(self):
        self.assertFalse(any('leaderboards/' in str(entry) for entry in self.logs()))
        for frame in self.page.frames[1:]:
            self.assertTrue(frame.locator('#highScoresButton').is_hidden())
            self.assertTrue(frame.locator('#initialsOverlay').is_hidden())

    def test_multiplayer_lobby_is_available_without_sdk_or_accounts_before_create(self):
        host,guest=self.frames()
        for frame in [host,guest]:
            self.assertTrue(frame.evaluate('CodaGamePrivacy.enabled'))
            self.lobby(frame)
            self.assertFalse(frame.evaluate('Boolean(window.firebase)'))
        self.assertEqual(self.sdk_requests,[]);self.assertEqual(self.logs(),[])
        self.assert_private()

    def test_two_classroom_frames_create_join_ready_and_start_without_public_scores(self):
        host,guest=self.frames();self.lobby(host);self.lobby(guest)
        host.locator('#multiCreate').click();host.wait_for_function('document.querySelector("#multiCode").textContent!=="----"')
        code=host.locator('#multiCode').inner_text();self.assertRegex(code,r'^[A-Z]{4}$')
        guest.locator('#multiJoinCode').fill(code);guest.locator('#multiJoin').click()
        guest.wait_for_function('!document.querySelector("#multiWaiting").classList.contains("hidden")')
        host.locator('#multiReady').click();guest.locator('#multiReady').click()
        host.locator('#multiStart').wait_for(state='visible')
        host.wait_for_function('!document.querySelector("#multiStart").disabled')
        host.locator('#multiStart').click()
        for frame in [host,guest]:frame.wait_for_function('__pitchFixture.snapshot().state==="running"')
        logs=self.logs();self.assertEqual(len([entry for entry in logs if entry[0]=='signin']),2)
        self.assertEqual([entry[2] for entry in logs if entry[0]=='persistence'],['none','none'])
        self.assertTrue(all(entry[2].startswith('rooms/') or entry[2]=='.info/serverTimeOffset' for entry in logs if entry[0] in ('read','write','listen')))
        self.assert_private()

    def test_leaving_while_sdk_loads_never_signs_in_or_creates_room(self):
        host,_=self.frames();self.lobby(host);self.hold_sdk=True
        host.locator('#multiCreate').click()
        self.page.wait_for_function('document.querySelector("#host").contentDocument.querySelector("script[src*=firebase-app]")')
        host.locator('#multiHome').click()
        for _ in range(100):
            if self.held_route is not None:break
            self.page.wait_for_timeout(10)
        self.assertIsNotNone(self.held_route)
        self.serve_sdk(self.held_route);self.held_route=None
        host.wait_for_function('window.firebase')
        self.page.wait_for_timeout(50)
        self.assertFalse(any(entry[0] in ('signin','write') for entry in self.logs()))
        self.assertTrue(host.locator('#mainMenu').is_visible());self.assert_private()

    def test_leaving_during_anonymous_signin_never_creates_room(self):
        host,_=self.frames();self.lobby(host);self.page.evaluate('window.__deferAuth=true')
        host.locator('#multiCreate').click();self.page.wait_for_function('typeof window.__releaseAuth==="function"')
        host.locator('#multiHome').click();self.page.evaluate('__releaseAuth()')
        self.page.wait_for_timeout(50)
        self.assertFalse(any(entry[0]=='write' for entry in self.logs()))
        self.assertTrue(host.locator('#mainMenu').is_visible());self.assert_private()

    def test_failed_sdk_load_can_be_retried_from_create(self):
        host,_=self.frames();self.lobby(host);self.fail_sdk=True
        host.locator('#multiCreate').click();host.wait_for_function('document.querySelector("#multiStatus").textContent.includes("Could not create")')
        self.assertTrue(host.locator('#multiCreate').is_enabled())
        host.locator('#multiCreate').click();host.wait_for_function('document.querySelector("#multiCode").textContent!=="----"')
        self.assertEqual(len([entry for entry in self.logs() if entry[0]=='signin']),1)
        self.assert_private()


if __name__=='__main__':unittest.main(verbosity=2)
