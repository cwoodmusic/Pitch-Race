"""Answer-line waits and mistake freezes through real Pitch Race input and frames.

Run: python3 tests/note-freeze-browser.py
The test-served HTML has a virtual monotonic clock and local state setup hooks.
Production HTML is unchanged by the fixture, and all external services are blocked.
"""
import sys
import unittest
from urllib.parse import urlparse

sys.dont_write_bytecode = True
from pitch_browser_support import PitchBrowserCase, FIXTURE, ROOT


FREEZE_FIXTURE = r'''
const freezeRealNow=performance.now.bind(performance),freezeRealDate=Date.now.bind(Date);
let freezeTestNow=null,freezeTestDate=0;
Object.defineProperty(performance,'now',{value:()=>freezeTestNow??freezeRealNow()});
Date.now=()=>freezeTestNow===null?freezeRealDate():freezeTestDate+freezeTestNow;
window.__freezeTest={
 takeClock(){
  const now=performance.now(),date=Date.now();
  freezeTestNow=now;freezeTestDate=date-now;cancelAnimationFrame(raf);
 },
 prepare(options={}){
  reset();cancelAnimationFrame(raf);pitchCountdown.cancel();soundOn=false;musicEnabled=false;
  freezeTestNow=10000;freezeTestDate=1700000000000;
  gameMode=options.mode||'classic';selectedStaff=options.staff||'treble';
  challengeLevel=options.level||1;
  multiRules={...MULTI_DEFAULTS,noteValues:options.values||'quarter',staff:options.staff||'treble',penalties:options.penalties!==false};
  multiOffset=0;multiStartAt=Date.now();multiRoomRef=null;
  state='running';startTime=last=freezeTestNow;levelTick=0;
  remaining=gameMode==='endless'?0:gameMode==='levels'?durationForLevel(challengeLevel):gameMode==='multi'?multiRules.duration:60;
  beginPitchRun();
  $('mainMenu').classList.add('hidden');$('gameScreen').classList.remove('hidden');
  $('gameScreen').classList.toggle('endless-mode',gameMode==='endless');
  $('gameScreen').classList.toggle('level-mode',gameMode==='levels');
  $('gameScreen').classList.toggle('multiplayer-mode',gameMode==='multi');
  $('start').disabled=false;setDisabled(false);syncStaffControls();
  player.spawn=cpu.spawn=100;player.pending=cpu.pending=0;cpuWait=100;
  cpu.notes=[{pitch:0,clef:'treble',kind:'quarter',x:700,visibleTime:2,activeTime:2,starter:false}];
  this.note(options.note);return this.snapshot();
 },
 note(options={}){
  const n={pitch:0,clef:getStaffMode()==='bass'?'bass':'treble',kind:'quarter',x:600,visibleTime:2,activeTime:2,starter:false,...options};
  player.notes=[n];draw($('playerStaff'),player,'#315bd1');updateLabels();
  return noteLetter(n);
 },
 queue(notes){player.notes=notes.map(n=>({pitch:0,clef:'treble',kind:'quarter',visibleTime:2,activeTime:2,starter:false,...n}));return this.snapshot();},
 massMisses(count){
  player.notes=Array.from({length:count},()=>({pitch:0,clef:'treble',kind:'quarter',x:98,visibleTime:2,activeTime:2,starter:false}));
  this.advance(.001);return this.snapshot();
 },
 advance(seconds){
  const until=freezeTestNow+seconds*1000;
  while(freezeTestNow<until){
   freezeTestNow=Math.min(until,freezeTestNow+25);
   cancelAnimationFrame(raf);loop(freezeTestNow);cancelAnimationFrame(raf);
  }
  return this.snapshot();
 },
 reset(){reset();return this.snapshot();},
 nearEnd(){startTime=freezeTestNow-59500;return this.snapshot();},
 counters(pending,spawn){player.pending=pending;player.spawn=spawn;},
 direct(letter){answer(letter);levelPress(letter,'test');return this.snapshot();},
 snapshot(){return{
  mode:gameMode,state,now:freezeTestNow,frozen:isNoteFrozen(),waiting:waitingAtAnswerLine(),until:noteFreezeUntil,
  score:player.score,correct:player.correct,misses:player.miss,remaining,
  notes:player.notes.map(n=>({...n})),cpuNotes:cpu.notes.map(n=>({...n})),
  pending:player.pending,spawn:player.spawn,
  hold:levelHold&&{elapsed:levelHold.elapsed,required:levelHold.required},
  disabled:[...$('answers').querySelectorAll('button')].map(b=>b.disabled),
  status:$('freezeStatus').textContent,statusHidden:!$('freezeStatus').getClientRects().length,
  letter:player.notes[0]?noteLetter(player.notes[0]):null
 };}
};
'''


class NoteFreezeTests(PitchBrowserCase):
    def route_checkout(self, route):
        if urlparse(route.request.url).path in ('/Pitch-Race/', '/Pitch-Race/index.html'):
            html = (ROOT / 'index.html').read_text()
            marker = 'initializeOnlineScores();})();'
            if html.count(marker) != 1:
                raise AssertionError('Cannot locate gameplay closure for local fixture')
            html = html.replace(marker, 'initializeOnlineScores();' + FIXTURE + FREEZE_FIXTURE + '})();')
            return route.fulfill(body=html, content_type='text/html')
        return super().route_checkout(route)

    def prepare(self, **options):
        self.load_pitch()
        return self.page.evaluate('options=>__freezeTest.prepare(options)', options)

    def snapshot(self):
        return self.page.evaluate('__freezeTest.snapshot()')

    def advance(self, seconds):
        return self.page.evaluate('seconds=>__freezeTest.advance(seconds)', seconds)

    def key(self, wrong=False):
        letter = self.snapshot()['letter']
        if wrong:
            letter = 'A' if letter != 'A' else 'B'
        self.page.keyboard.press(letter.lower())
        return self.snapshot()

    def wrongs(self, count):
        for _ in range(count):
            self.key(wrong=True)
        return self.snapshot()

    def assert_unchanged(self, before, after):
        for key in ('score', 'correct', 'misses', 'notes', 'pending', 'spawn'):
            self.assertEqual(after[key], before[key], key + ' must pause during the freeze')

    def test_other_modes_freeze_exactly_three_seconds_and_reject_spam(self):
        variants = [
            dict(mode='classic', staff='bass'),
            dict(mode='levels', level=21),
            dict(mode='multi', values='quarter', staff='treble'),
            dict(mode='multi', values='holds', staff='bass', penalties=False),
            dict(mode='multi', values='all', staff='grand', penalties=False),
        ]
        for options in variants:
            with self.subTest(**options):
                self.prepare(**options)
                two = self.wrongs(2)
                self.assertFalse(two['frozen'])
                self.assertEqual(two['misses'], 2)
                letter = 'A' if two['letter'] != 'A' else 'B'
                self.page.locator('#answers').get_by_role('button', name=letter, exact=True).click()
                frozen = self.snapshot()
                self.assertTrue(frozen['frozen'])
                self.assertEqual(frozen['misses'], 3)
                self.assertEqual(frozen['state'], 'running')
                self.assertTrue(all(frozen['disabled']))
                self.assertIn('3', frozen['status'])
                self.assertFalse(frozen['statusHidden'])
                self.page.locator('#playerStaff').click()
                for letter in 'ABCDEFG' * 2:
                    self.page.keyboard.press(letter.lower())
                    button = self.page.locator('#answers').get_by_role('button', name=letter, exact=True)
                    box = button.bounding_box()
                    self.page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                    button.dispatch_event('click')
                self.page.evaluate('letter=>__freezeTest.direct(letter)', frozen['letter'])
                almost = self.advance(2.999)
                self.assertTrue(almost['frozen'])
                self.assert_unchanged(frozen, almost)
                if options['mode'] == 'classic':
                    self.assertLess(almost['cpuNotes'][0]['x'], frozen['cpuNotes'][0]['x'])
                self.assertAlmostEqual(almost['remaining'], frozen['remaining'] - 2.999, places=5)
                resumed = self.advance(.002)
                self.assertFalse(resumed['frozen'])
                self.assertTrue(all(not value for value in resumed['disabled']))
                self.assertTrue(resumed['statusHidden'])
                self.assertLess(resumed['notes'][0]['x'], frozen['notes'][0]['x'])
                self.assertEqual(self.key()['correct'], frozen['correct'] + 1)

    def test_correct_answers_between_mistakes_do_not_bypass_repeated_freezes(self):
        self.prepare(mode='classic')
        self.wrongs(2)
        self.assertEqual(self.key()['correct'], 1)
        self.page.evaluate('__freezeTest.note()')
        self.assertTrue(self.wrongs(1)['frozen'])
        self.advance(3.001)
        self.assertEqual(self.key()['correct'], 2)
        self.page.evaluate('__freezeTest.note()')
        self.wrongs(1)
        self.key()
        self.page.evaluate('__freezeTest.note()')
        self.assertFalse(self.wrongs(1)['frozen'])
        second = self.wrongs(1)
        self.assertEqual(second['misses'], 6)
        self.assertTrue(second['frozen'])
        self.assertEqual(second['state'], 'running')

    def test_pending_spawns_pause_and_held_notes_require_a_fresh_press_after_resume(self):
        for mode in ('levels', 'multi'):
            with self.subTest(mode=mode):
                self.prepare(mode=mode, values='holds', note={'kind': 'half'})
                self.page.evaluate('__freezeTest.counters(.4,1.5)')
                frozen = self.wrongs(3)
                self.assert_unchanged(frozen, self.advance(1.5))
                self.page.keyboard.down(frozen['letter'].lower())
                self.assertIsNone(self.snapshot()['hold'])
                self.advance(1.501)
                self.assertEqual(self.snapshot()['correct'], 0)
                self.page.keyboard.up(frozen['letter'].lower())
                self.page.keyboard.down(frozen['letter'].lower())
                self.assertIsNotNone(self.snapshot()['hold'])
                self.advance(.7)
                self.page.keyboard.up(frozen['letter'].lower())
                self.assertEqual(self.snapshot()['correct'], 1)

    def test_reaching_the_answer_line_waits_without_misses_and_keeps_input_available(self):
        variants = [dict(mode='classic', staff='bass'), dict(mode='levels', level=21), dict(mode='multi', values='quarter'),
                    dict(mode='multi', values='holds', penalties=False),
                    dict(mode='multi', values='all', staff='grand')]
        for options in variants:
            with self.subTest(**options):
                self.prepare(**options)
                self.page.evaluate('__freezeTest.queue([{x:99},{x:280}])')
                self.page.evaluate('__freezeTest.counters(.4,1.5)')
                waiting = self.advance(.05)
                self.assertTrue(waiting['waiting'])
                self.assertFalse(waiting['frozen'])
                self.assertEqual(waiting['notes'][0]['x'], 98)
                self.assertEqual(waiting['misses'], 0)
                self.assertTrue(all(not value for value in waiting['disabled']))
                self.assertIn('red line', waiting['status'])
                # The note center must stop on the actual rendered answer line,
                # on every staff and at any responsive width.
                self.assertTrue(self.page.evaluate("""()=>{
                  const staff=document.querySelector('#playerStaff');
                  return Number(staff.querySelector('[data-symbol="notehead"]').dataset.x)
                    ===Number(staff.querySelector('[data-symbol="answer-line"]').getAttribute('x1'));
                }"""))
                later = self.advance(1.2)
                self.assert_unchanged(waiting, later)
                if options['mode'] == 'classic':
                    self.assertLess(later['cpuNotes'][0]['x'], waiting['cpuNotes'][0]['x'])
                self.assertAlmostEqual(later['remaining'], waiting['remaining'] - 1.2, places=5)
                if options['mode'] == 'classic' or options.get('values') == 'holds':
                    self.page.locator('#answers').get_by_role('button', name=later['letter'], exact=True).click()
                    self.assertEqual(self.snapshot()['correct'], 1)
                else:
                    self.assertEqual(self.key()['correct'], 1)
                resumed = self.advance(.05)
                self.assertFalse(resumed['waiting'])
                self.assertLess(resumed['notes'][0]['x'], waiting['notes'][1]['x'])
                self.assertEqual(resumed['misses'], 0)

    def test_wrong_answers_at_the_line_keep_the_existing_three_mistake_freeze(self):
        self.prepare(mode='classic', note={'x':99})
        waiting = self.advance(.05)
        one = self.wrongs(1)
        self.assertTrue(one['waiting']);self.assertFalse(one['frozen'])
        self.assertEqual(one['misses'], 1)
        self.assertEqual(self.advance(.5)['notes'], waiting['notes'])
        frozen = self.wrongs(2)
        self.assertTrue(frozen['frozen']);self.assertTrue(all(frozen['disabled']))
        self.assertEqual(self.key()['correct'], 0)
        thawed = self.advance(3.001)
        self.assertFalse(thawed['frozen']);self.assertTrue(thawed['waiting'])
        self.assertTrue(all(not value for value in thawed['disabled']))
        self.assertEqual(self.key()['correct'], 1)
        self.assertFalse(self.snapshot()['waiting'])

    def test_held_answers_can_complete_or_be_retried_while_the_line_stops_motion(self):
        for kind, seconds in [('half', .7), ('whole', 1.4)]:
            with self.subTest(kind=kind):
                self.prepare(mode='levels')
                self.page.evaluate('kind=>__freezeTest.queue([{x:99,kind},{x:300}])', kind)
                waiting = self.advance(.05)
                letter = waiting['letter'].lower()
                self.page.keyboard.down(letter)
                partly = self.advance(.2)
                self.assertIsNotNone(partly['hold'])
                self.assertEqual(partly['notes'], waiting['notes'])
                self.page.keyboard.up(letter)
                self.assertIsNone(self.snapshot()['hold'])
                self.assertTrue(self.snapshot()['waiting'])
                self.assertEqual(self.snapshot()['misses'], 0)
                self.page.keyboard.down(letter)
                completed = self.advance(seconds)
                self.page.keyboard.up(letter)
                self.assertEqual(completed['correct'], 1)
                self.assertLess(completed['notes'][0]['x'], waiting['notes'][1]['x'])
                self.assertFalse(completed['waiting'])

    def test_multiple_due_notes_never_auto_miss_or_bypass_the_answer_gate(self):
        for mode in ('classic', 'levels', 'multi'):
            with self.subTest(mode=mode):
                self.prepare(mode=mode, values='all')
                waiting = self.page.evaluate('__freezeTest.massMisses(5)')
                self.assertFalse(waiting['frozen'])
                self.assertTrue(waiting['waiting'])
                self.assertEqual(waiting['misses'], 0)
                self.assertEqual(len(waiting['notes']), 5)
                self.assertTrue(all(note['x'] >= 98 for note in waiting['notes']))
                self.assert_unchanged(waiting, self.advance(1))
                for correct in range(1, 6):
                    self.assertEqual(self.key()['correct'], correct)
                    self.advance(2)
                    self.assertEqual(self.snapshot()['misses'], 0)

    def test_endless_unanswered_notes_record_misses_without_stopping_motion_or_spawns(self):
        self.prepare(mode='endless', staff='grand')
        self.page.evaluate('__freezeTest.queue([{x:99},{x:340}])')
        self.page.evaluate('__freezeTest.counters(.4,1.5)')
        after = self.advance(.05)
        self.assertEqual(after['misses'], 1)
        self.assertEqual(len(after['notes']), 1)
        self.assertLess(after['notes'][0]['x'], 340)
        self.assertLess(after['pending'], .4)
        self.assertFalse(after['waiting']);self.assertFalse(after['frozen'])
        self.assertTrue(after['statusHidden'])
        self.assertTrue(all(not value for value in after['disabled']))
        spawned = self.advance(.5)
        self.assertEqual(spawned['pending'], 0)
        self.assertGreater(len(spawned['notes']), 1,
                           'Endless spawning continues after an unanswered note passes the line')
        self.assertGreater(spawned['remaining'], after['remaining'])
        # Repeated real automatic misses must never trigger the three-mistake
        # lock that remains in the other race modes.
        for expected in range(2, 7):
            self.page.evaluate('__freezeTest.note({x:99})')
            missed = self.advance(.05)
            self.assertEqual(missed['misses'], expected)
            self.assertFalse(missed['frozen']);self.assertFalse(missed['waiting'])
            self.assertTrue(all(not value for value in missed['disabled']))
        self.assertEqual(missed['state'], 'running')
        self.assertEqual(missed['correct'], 0)

    def test_endless_manual_mistakes_never_lock_answers_or_stop_the_queue(self):
        self.prepare(mode='endless')
        for expected in (3, 6):
            mistakes = self.wrongs(3)
            self.assertEqual(mistakes['misses'], expected)
            self.assertFalse(mistakes['frozen']);self.assertFalse(mistakes['waiting'])
            self.assertTrue(mistakes['statusHidden'])
            self.assertTrue(all(not value for value in mistakes['disabled']))
            moving = self.advance(.2)
            self.assertLess(moving['notes'][0]['x'], mistakes['notes'][0]['x'])
            self.assertLess(moving['spawn'], mistakes['spawn'])
            self.assertFalse(moving['frozen'])
        self.page.locator('#answers').get_by_role('button', name=moving['letter'], exact=True).click()
        self.assertEqual(self.snapshot()['correct'], 1,
                         'Answer controls remain usable after six Endless mistakes')
        self.assertEqual(self.snapshot()['state'], 'running')

    def test_endless_half_and_whole_notes_keep_their_normal_hold_controls(self):
        for kind, seconds in [('half', .7), ('whole', 1.4)]:
            with self.subTest(kind=kind):
                self.prepare(mode='endless')
                self.page.evaluate('kind=>__freezeTest.queue([{x:600,kind},{x:850}])', kind)
                self.page.evaluate('__freezeTest.counters(.4,1.5)')
                letter = self.snapshot()['letter'].lower()
                self.page.keyboard.down(letter)
                partly = self.advance(.2)
                self.assertIsNotNone(partly['hold'])
                self.assertLess(partly['pending'], .4)
                self.assertFalse(partly['frozen']);self.assertFalse(partly['waiting'])
                self.page.keyboard.up(letter)
                self.assertIsNone(self.snapshot()['hold'])
                self.assertEqual(self.snapshot()['correct'], 0)
                self.page.keyboard.down(letter)
                completed = self.advance(seconds)
                self.page.keyboard.up(letter)
                self.assertEqual(completed['correct'], 1)
                self.assertEqual(completed['misses'], 0)
                self.assertFalse(completed['waiting']);self.assertFalse(completed['frozen'])

    def test_reset_and_a_new_mode_clear_the_old_freeze(self):
        self.prepare(mode='classic')
        self.assertTrue(self.wrongs(3)['frozen'])
        reset = self.page.evaluate('__freezeTest.reset()')
        self.assertFalse(reset['frozen'])
        self.assertTrue(reset['statusHidden'])
        self.assertTrue(all(reset['disabled']))
        self.advance(5)
        self.assertTrue(all(self.snapshot()['disabled']))
        fresh = self.page.evaluate('__freezeTest.prepare({mode:"levels"})')
        self.assertFalse(fresh['frozen'])
        self.assertEqual(fresh['misses'], 0)
        self.assertEqual(self.key()['correct'], 1)

    def test_race_can_end_during_freeze_without_later_reenabling_answers(self):
        self.prepare(mode='classic')
        self.page.evaluate('__freezeTest.nearEnd()')
        self.wrongs(3)
        finished = self.advance(.6)
        self.assertEqual(finished['state'], 'finished')
        self.assertTrue(all(finished['disabled']))
        self.advance(4)
        self.assertTrue(all(self.snapshot()['disabled']))

    def test_endless_can_be_finished_from_the_real_menu_after_mistakes_without_a_freeze(self):
        self.load_pitch()
        self.start(self.page, mode='endless')
        self.assertFalse(self.page.locator('#lifeHearts').is_visible(),
                         'Endless must not advertise a three-mistake freeze countdown')
        self.page.evaluate('__freezeTest.takeClock();__freezeTest.note()')
        self.assertEqual(self.key()['correct'], 1)
        self.page.evaluate('__freezeTest.note()')
        mistakes = self.wrongs(6)
        self.assertFalse(mistakes['frozen'])
        self.assertTrue(all(not value for value in mistakes['disabled']))
        self.page.locator('#endlessFinish').click()
        self.page.locator('#resultsOverlay').wait_for(state='visible')
        ended = self.snapshot()
        self.assertEqual(ended['state'], 'finished')
        self.assertEqual(ended['correct'], 1)
        self.assertEqual(ended['misses'], 6)
        self.assertTrue(all(ended['disabled']))
        self.assertFalse(ended['frozen'])
        self.assertTrue(ended['statusHidden'])
        self.assertNotIn('Three mistakes', self.page.locator('#resultsSubtitle').inner_text())


if __name__ == '__main__':
    unittest.main(verbosity=2)
