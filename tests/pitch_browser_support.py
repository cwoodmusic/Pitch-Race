"""Play the real Pitch Race iframe and Arcade at their production origins.

Only the HTML served by this fixture gains state setup helpers. Production files
have no test setters, and all external services (including Firebase) are blocked.
"""
import json
import mimetypes
import os
from pathlib import Path
import sys
import unittest
from urllib.parse import unquote, urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARCADE_ROOT = Path(os.environ.get('CODA_ARCADE_ROOT', ROOT.parent / 'coda-arcade'))
sys.dont_write_bytecode = True
sys.path.insert(0, str(ARCADE_ROOT / 'tests'))
from world_navigation_helpers import open_cabinet, open_destination

ORIGIN = 'https://cwoodmusic.github.io'
WORLD = ORIGIN + '/coda-arcade/world-preview.html'
PITCH = ORIGIN + '/Pitch-Race/'

FIXTURE = r'''
window.__pitchTones=[];
const fixtureTone=tone;
tone=(frequency,...args)=>{window.__pitchTones.push(frequency);return fixtureTone(frequency,...args)};
window.__pitchScoreOffers=[];
const fixtureScoreOffer=offerHighScore;
offerHighScore=(...args)=>{window.__pitchScoreOffers.push(args.slice(0,2));return fixtureScoreOffer(...args)};
window.__pitchFixture={
  snapshot:()=>({state,mode:gameMode,staff:getStaffMode(),level:challengeLevel,
    practice:challengePractice,dev:devMode,run:window.codaPitchRun,
    correct:player.correct,misses:player.miss,score:player.score,
    remaining,hold:levelHold&&{elapsed:levelHold.elapsed,required:levelHold.required},
    checkpoint:levelProgress.snapshot(),tracker:pitchRuns.getState()}),
  freeze:()=>cancelAnimationFrame(raf),
  note:(note={})=>{
    cancelAnimationFrame(raf);levelHold=null;levelHeldPointer=null;
    const n={pitch:0,clef:getStaffMode()==='bass'?'bass':'treble',kind:'quarter',
      x:380,visibleTime:2,activeTime:1,starter:false,...note};
    player.notes=[n];player.pending=0;
    draw($('playerStaff'),player,'#315bd1');return noteLetter(n);
  },
  expire:()=>{
    cancelAnimationFrame(raf);
    loop(startTime+(gameMode==='levels'?durationForLevel(challengeLevel):60)*1000+1);
  },
  advanceHold:seconds=>{
    cancelAnimationFrame(raf);step(player,seconds);
  },
  sample:count=>{
    cancelAnimationFrame(raf);player.notes=[];
    for(let i=0;i<count;i++)spawn(player);
    return player.notes.map(note=>({...note,letter:noteLetter(note),frequency:noteFrequency(note)}));
  }
};
'''


class PitchBrowserCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'),
            args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required'])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 1000})
        self.errors, self.missing, self.external_writes = [], [], []
        self.context.route('https://**/*', self.block_external)
        self.context.route(ORIGIN + '/**', self.route_checkout)
        self.context.add_init_script('''
          window.__messages=[];
          addEventListener('message',event=>{
            if(event.data?.coda===1)window.__messages.push({data:event.data,origin:event.origin});
          });
          if(location.pathname.startsWith('/coda-arcade/'))
            localStorage.setItem('codaArcadeFXV1','off');
        ''')
        self.page = self.context.new_page()
        self.page.set_default_timeout(15000)
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))

    def tearDown(self):
        outcome = self._outcome.result
        if any(case is self for case, _ in outcome.errors + outcome.failures):
            for frame in self.page.frames:
                if '/Pitch-Race/' in frame.url:
                    try:
                        print('\nPitch failure state:', json.dumps(frame.evaluate(
                            'window.__pitchFixture?.snapshot()'), sort_keys=True))
                    except Exception:
                        pass
        self.context.close()
        self.assertEqual(self.errors, [], 'Uncaught browser errors')
        self.assertEqual(self.missing, [], 'Missing local resources')
        self.assertEqual(self.external_writes, [], 'No live Firebase/service writes')

    def block_external(self, route):
        if route.request.method not in ('GET', 'HEAD', 'OPTIONS'):
            self.external_writes.append(route.request.url)
        route.abort()

    def route_checkout(self, route):
        path = unquote(urlparse(route.request.url).path)
        if path == '/favicon.ico':
            return route.fulfill(status=204)
        if path.startswith('/Pitch-Race/'):
            base, relative = ROOT, path.removeprefix('/Pitch-Race/')
        elif path.startswith('/coda-arcade/'):
            base, relative = ARCADE_ROOT, path.removeprefix('/coda-arcade/')
        else:
            return route.abort()
        file = (base / (relative or 'index.html')).resolve()
        if not file.is_relative_to(base.resolve()) or not file.is_file():
            self.missing.append(path)
            return route.fulfill(status=404, body='Missing local test resource')
        if base == ROOT and file.name == 'index.html':
            html = file.read_text()
            marker = 'initializeOnlineScores();})();'
            if html.count(marker) != 1:
                raise AssertionError('The test fixture could not locate the gameplay closure')
            html = html.replace(marker, 'initializeOnlineScores();' + FIXTURE + '})();')
            return route.fulfill(body=html, content_type='text/html')
        return route.fulfill(path=str(file), content_type=mimetypes.guess_type(str(file))[0]
                            or 'application/octet-stream')

    def load_world(self):
        self.page.goto(WORLD, wait_until='domcontentloaded')
        self.page.wait_for_function('window.CodaDeveloperConsole?.ready()&&window.CodaArcadeQA?.notes()')

    def cabinet(self):
        open_cabinet(self.page, 0)
        self.page.wait_for_function('''()=>{
          const game=document.querySelector('#gameiframe').contentWindow;
          return game.__pitchFixture&&game.CodaBridge.getState().connected;
        }''')
        return self.page.locator('#gameiframe').element_handle().content_frame()

    def load_pitch(self):
        self.page.goto(PITCH, wait_until='domcontentloaded')
        self.page.wait_for_function('window.__pitchFixture')
        return self.page

    def seed_checkpoint(self, level):
        self.context.add_init_script('''(()=>{const level=LEVEL;
          if(location.pathname.startsWith('/Pitch-Race/'))localStorage.setItem(
            'pitchRaceLevelProgressV1',JSON.stringify({version:1,bestCompleted:level}));
        })();'''.replace('LEVEL', str(level)))

    def start(self, frame, mode='levels', staff=None):
        frame.locator('#' + mode + 'Card').click()
        if staff is not None:
            frame.locator('#menuStaff').select_option(staff)
        frame.locator('#menuPlay').click()
        frame.wait_for_function('window.__pitchFixture.snapshot().state==="running"')
        frame.evaluate('window.__pitchFixture.freeze()')

    def answer(self, frame, note=None, key=False, wrong=False):
        letter = frame.evaluate('note=>window.__pitchFixture.note(note)', note or {})
        if wrong:
            letter = 'A' if letter != 'A' else 'B'
        if key:
            frame.locator('#playerStaff').click()
            self.page.keyboard.press(letter.lower())
        else:
            frame.locator('#answers').get_by_role('button', name=letter, exact=True).click()
        return letter

    def expire(self, frame):
        frame.evaluate('window.__pitchFixture.expire()')
        frame.wait_for_function('window.__pitchFixture.snapshot().state==="finished"')
        if frame.locator('#initialsOverlay').is_visible():
            frame.locator('#initialsSkip').click()
        frame.locator('#resultsOverlay').wait_for(state='visible')

    def totals(self):
        return self.page.evaluate('''()=>({notes:CodaArcadeQA.notes().balance,
          xp:CodaArcadeQA.progression().xp,
          rewards:CodaArcadeQA.progression().achievementRewards.map(item=>item.id),
          events:CodaArcadeQA.progression().recent.map(item=>item.id)})''')

    def reports(self):
        return self.page.evaluate('window.__messages.filter(m=>m.data.type==="result").map(m=>m.data)')

    def journal(self):
        return self.page.evaluate('JSON.parse(localStorage.getItem("codaPlayerProgressV1")).events')

    def home(self, frame):
        frame.locator('#resultsMenu' if frame.locator('#resultsOverlay').is_visible() else '#home').click()
        if frame.locator('#initialsOverlay').is_visible():
            frame.locator('#initialsSkip').click()


__all__ = ['PitchBrowserCase', 'PITCH', 'ORIGIN', 'open_destination']
