"""Multiplayer cancellation and room loss with in-memory Firebase doubles.

The real menu, callbacks and race loop run in Chromium. External services are
blocked; no account or deployed room is created, joined, or changed.
"""
import sys
import unittest
from urllib.parse import urlparse

sys.dont_write_bytecode = True
from pitch_browser_support import PitchBrowserCase, FIXTURE, ROOT

MULTIPLAYER_FIXTURE = r'''
window.__multiAudit={configure(options={}){
 const log=window.__multiAuditLog={reads:[],writes:[],listeners:[],off:0},uid='local-test-user';
 let resolveAuth,resolveTransaction,resolveRead;
 const room={hostUid:uid,control:{status:'waiting',startAt:0,round:0},settings:{...MULTI_DEFAULTS},players:{host:multiPlayerData(uid)}};
 const snapshot=value=>({val:()=>value});
 const reference=path=>({
  child:child=>reference(path+'/'+child),
  once:()=>{log.reads.push(path);return options.deferRead?new Promise(resolve=>{resolveRead=()=>resolve(snapshot({...room,hostUid:'other-host'}));}):Promise.resolve(snapshot(room));},
  transaction:updater=>{log.writes.push(path);const value=updater(null);if(path.split('/').length===2)log.created=value;
   return options.deferTransaction?new Promise(resolve=>{resolveTransaction=()=>resolve({committed:true});}):Promise.resolve({committed:true});},
  update:async value=>{log.writes.push(path);},
  on:(event,fn)=>{log.listeners.push({path,fn,active:true});},
  off:(event,fn)=>{log.off++;for(const entry of log.listeners)if(entry.path===path&&entry.fn===fn)entry.active=false;}
 });
 db={ref:reference};auth={currentUser:options.deferAuth?null:{uid},signInAnonymously:()=>new Promise(resolve=>{resolveAuth=()=>{auth.currentUser={uid};resolve();};})};
 window.firebase={database:{ServerValue:{TIMESTAMP:0}}};
 window.__multiAudit.resolveAuth=()=>resolveAuth();
 window.__multiAudit.resolveTransaction=()=>resolveTransaction();
 window.__multiAudit.resolveRead=()=>resolveRead();
 window.__multiAudit.emit=value=>{for(const entry of log.listeners.slice())if(entry.active)entry.fn(snapshot(value));};
 window.__multiAudit.runningRoom=()=>({...room,control:{status:'running',startAt:Date.now()-5000,round:1}});
 return true;
}};
window.__multiAudit.snapshot=()=>({state,mode:gameMode,room:multiRoom,role:multiRole,
 activeListeners:__multiAuditLog.listeners.filter(entry=>entry.active).length,
 writes:__multiAuditLog.writes.slice(),menu:!$('mainMenu').classList.contains('hidden'),
 lobby:!$('multiLobby').classList.contains('hidden'),entry:!$('multiEntry').classList.contains('hidden'),
 run:window.codaPitchRun||null,voices:activeEffects.size,music:musicCurrent?.id||null});
'''


class MultiplayerLifecycleTests(PitchBrowserCase):
    def route_checkout(self, route):
        if urlparse(route.request.url).path in ('/Pitch-Race/', '/Pitch-Race/index.html'):
            source = (ROOT/'index.html').read_text()
            marker = 'initializeOnlineScores();})();'
            source = source.replace(marker, 'initializeOnlineScores();'+FIXTURE+MULTIPLAYER_FIXTURE+'})();')
            return route.fulfill(body=source, content_type='text/html')
        return super().route_checkout(route)

    def lobby(self, **options):
        self.load_pitch()
        self.page.evaluate('options=>__multiAudit.configure(options)', options)
        self.page.locator('#multiCard').click()
        self.page.locator('#menuPlay').click()
        self.page.locator('#multiCreate').wait_for(state='visible')

    def snapshot(self):
        return self.page.evaluate('__multiAudit.snapshot()')

    def test_leaving_during_sign_in_cannot_create_or_attach_a_room(self):
        self.lobby(deferAuth=True)
        self.page.locator('#multiCreate').click()
        self.page.locator('#multiHome').click()
        self.page.evaluate('__multiAudit.resolveAuth()')
        self.page.wait_for_timeout(50)
        result = self.snapshot()
        self.assertEqual(result['room'], '')
        self.assertEqual(result['activeListeners'], 0)
        self.assertEqual(result['writes'], [])
        self.assertTrue(result['menu'])

    def test_leaving_after_create_was_sent_cannot_resubscribe_on_completion(self):
        self.lobby(deferTransaction=True)
        self.page.locator('#multiCreate').click()
        self.page.wait_for_function('__multiAuditLog.writes.length===1')
        self.page.locator('#multiHome').click()
        self.page.evaluate('__multiAudit.resolveTransaction()')
        self.page.wait_for_timeout(50)
        self.assertEqual(self.snapshot()['room'], '')
        self.assertEqual(self.snapshot()['activeListeners'], 0)

    def test_reopening_the_lobby_does_not_revive_an_older_create_request(self):
        self.lobby(deferTransaction=True)
        self.page.locator('#multiCreate').click()
        self.assertTrue(self.page.locator('#multiCreate').is_disabled())
        self.assertTrue(self.page.locator('#multiJoin').is_disabled())
        self.page.locator('#multiHome').click()
        self.page.locator('#multiCard').click()
        self.page.locator('#menuPlay').click()
        self.assertTrue(self.page.locator('#multiCreate').is_enabled())
        self.assertTrue(self.page.locator('#multiJoin').is_enabled())
        self.page.evaluate('__multiAudit.resolveTransaction()')
        self.page.wait_for_timeout(50)
        result = self.snapshot()
        self.assertEqual(result['room'], '')
        self.assertEqual(result['activeListeners'], 0)
        self.assertTrue(result['lobby'])
        self.assertTrue(result['entry'])

    def test_leaving_during_join_read_cannot_claim_a_guest_seat(self):
        self.lobby(deferRead=True)
        self.page.locator('#multiJoinCode').fill('ABCD')
        self.page.locator('#multiJoin').click()
        self.page.wait_for_function('__multiAuditLog.reads.length===1')
        self.page.locator('#multiHome').click()
        self.page.evaluate('__multiAudit.resolveRead()')
        self.page.wait_for_timeout(50)
        self.assertEqual(self.snapshot()['room'], '')
        self.assertEqual(self.snapshot()['writes'], [])
        self.assertEqual(self.snapshot()['activeListeners'], 0)

    def test_deleted_room_and_lost_membership_stop_the_race_and_detach(self):
        for loss in ('deleted', 'membership'):
            with self.subTest(loss=loss):
                self.lobby()
                self.page.locator('#multiCreate').click()
                self.page.wait_for_function('__multiAudit.snapshot().activeListeners===1')
                self.page.evaluate('__multiAudit.emit(__multiAudit.runningRoom())')
                self.page.wait_for_function('__pitchFixture.snapshot().state==="running"')
                self.page.evaluate("loss=>__multiAudit.emit(loss==='deleted'?null:{...__multiAudit.runningRoom(),players:{host:{uid:'another-user'}}})", loss)
                result = self.snapshot()
                self.assertEqual(result['state'], 'idle')
                self.assertEqual(result['room'], '')
                self.assertEqual(result['activeListeners'], 0)
                self.assertIsNone(result['run'])
                self.assertEqual(result['voices'], 0)
                self.assertIsNone(result['music'])
                self.assertTrue(result['lobby'])
                self.assertTrue(result['entry'])
                writes = len(result['writes'])
                self.page.wait_for_timeout(300)
                self.assertEqual(len(self.snapshot()['writes']), writes,
                                 'A closed room must not keep receiving score updates')
                self.assertIn('closed' if loss == 'deleted' else 'no longer',
                              self.page.locator('#multiStatus').inner_text())


if __name__ == '__main__':
    unittest.main(verbosity=2)
