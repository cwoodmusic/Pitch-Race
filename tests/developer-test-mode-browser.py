"""All three real cabinets honor a same-origin developer sandbox parent.

Static games run locally. Network attempts are intercepted, and CSP probes use
reserved .invalid hosts; no Firebase account or deployed database is contacted.
"""
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
import unittest
from urllib.parse import parse_qs, urlparse
from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True
WORKSPACE = Path(__file__).resolve().parents[2]
GAMES = ('Pitch-Race', 'musictriad', 'rhythmroom')


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/sandbox-fixture':
            query = parse_qs(parsed.query)
            game = query.get('game', ['Pitch-Race'])[0]
            if game not in GAMES:
                return self.send_error(404)
            enabled = query.get('enabled', ['1'])[0] == '1'
            cross = query.get('cross', ['0'])[0] == '1'
            broken = query.get('broken', ['0'])[0] == '1'
            src = ('http://localhost:' + str(self.server.server_port) if cross else '') + '/' + game + '/index.html'
            if not enabled or cross:
                src += '?classroom=1'
            body = '''<!doctype html><title>Local developer sandbox fixture</title><script>
window.__nativeStore=localStorage;__nativeStore.setItem('real-player-marker','keep');
const values=new Map([['sandbox-marker','temporary']]);
window.__memory={get length(){return values.size},key:i=>[...values.keys()][i]??null,
 getItem:key=>values.get(String(key))??null,setItem:(key,value)=>values.set(String(key),String(value)),
 removeItem:key=>values.delete(String(key)),clear:()=>values.clear()};
Object.defineProperty(window,'localStorage',{configurable:true,get:()=>{if(BROKEN)throw Error('Parent storage is unavailable');return __memory;}});
window.CodaDeveloperTestMode={isEnabled:()=>ENABLED};
window.ARCADE_ACCOUNTS_CONFIG={mode:'legacy',classroom:{enabled:false,privacy:false}};
</script><iframe id="game" width="1400" height="1000" src="SOURCE"></iframe>'''
            body = body.replace('ENABLED', str(enabled).lower()).replace('BROKEN', str(broken).lower()).replace('SOURCE', src)
            data = body.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            return self.wfile.write(data)
        return super().do_GET()


class DeveloperTestModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(WORKSPACE)))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = 'http://127.0.0.1:' + str(cls.server.server_port)
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width':1440,'height':1100})
        self.external, self.errors = [], []
        self.context.route('https://**/*', self.block_external)
        self.page = self.context.new_page()
        self.page.on('pageerror', lambda error:self.errors.append(str(error)))
        self.page.set_default_timeout(10000)

    def block_external(self, route):
        self.external.append(route.request.url)
        # Explicit lazy-SDK tests remain isolated, with no account/network SDK.
        if route.request.url.startswith('https://www.gstatic.com/firebasejs/'):
            return route.fulfill(content_type='text/javascript', body='window.__allowedSDK=(window.__allowedSDK||0)+1;')
        return route.abort()

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def frame(self, game, enabled=True, cross=False, broken=False):
        self.page.goto(self.base + '/sandbox-fixture?game=' + game + '&enabled=' + str(int(enabled)) + '&cross=' + str(int(cross)) + '&broken=' + str(int(broken)), wait_until='load')
        frame = self.page.locator('#game').element_handle().content_frame()
        frame.wait_for_function('window.CodaGamePrivacy')
        return frame

    def test_all_cabinets_inherit_the_temporary_store_and_keep_real_progress_untouched(self):
        for game in GAMES:
            with self.subTest(game=game):
                frame = self.frame(game)
                self.assertTrue(frame.evaluate('CodaGamePrivacy.enabled&&CodaGamePrivacy.testMode'))
                self.assertEqual(frame.locator('#codaTestModeNotice').inner_text(), 'Test mode uses local play')
                self.assertEqual(frame.evaluate('localStorage.getItem("sandbox-marker")'), 'temporary')
                self.assertIsNone(frame.evaluate('localStorage.getItem("real-player-marker")'))
                frame.evaluate('localStorage.setItem("sandbox-game-result","temporary-result")')
                self.assertEqual(self.page.evaluate('localStorage.getItem("sandbox-game-result")'), 'temporary-result')
                self.assertIsNone(self.page.evaluate('__nativeStore.getItem("sandbox-game-result")'))
                self.assertEqual(self.page.evaluate('__nativeStore.getItem("real-player-marker")'), 'keep')
                self.assertFalse(frame.evaluate('CodaGamePrivacy.loadFirebaseSDK({multiplayer:true})'))
                self.assertFalse(frame.evaluate('Boolean(window.firebase)'))
        self.assertEqual(self.external, [])

    def test_unavailable_parent_storage_falls_back_to_private_memory_instead_of_real_saves(self):
        for game in GAMES:
            with self.subTest(game=game):
                frame = self.frame(game, broken=True)
                self.assertTrue(frame.evaluate('CodaGamePrivacy.testMode&&localStorage.__codaClassroomScoped'))
                self.assertIsNone(frame.evaluate('localStorage.getItem("real-player-marker")'))
                frame.evaluate('localStorage.setItem("fallback-result","sandbox-only")')
                self.assertEqual(frame.evaluate('localStorage.getItem("fallback-result")'), 'sandbox-only')
                self.assertIsNone(self.page.evaluate('__nativeStore.getItem("fallback-result")'))
                self.assertFalse(frame.evaluate('CodaGamePrivacy.loadFirebaseSDK({multiplayer:true})'))
        self.assertEqual(self.external, [])

    def test_csp_blocks_external_fetch_websocket_and_form_posts_but_allows_local_assets(self):
        for game in GAMES:
            with self.subTest(game=game):
                frame = self.frame(game)
                result = frame.evaluate('''async()=>{
                  window.__violations=[];addEventListener('securitypolicyviolation',event=>__violations.push(event.effectiveDirective));
                  const local=await fetch('/Pitch-Race/classroom-privacy.js');
                  let blocked=false;try{await fetch('https://firebase.invalid/write',{method:'POST',body:'sandbox'});}catch{blocked=true;}
                  try{const socket=new WebSocket('wss://firebase.invalid/socket');socket.onerror=()=>{};setTimeout(()=>socket.close(),50);}catch{}
                  const form=document.createElement('form');form.action='https://firebase.invalid/post';form.method='POST';document.body.append(form);form.submit();
                  await new Promise(resolve=>setTimeout(resolve,100));return {local:local.ok,blocked,violations:__violations};
                }''')
                self.assertTrue(result['local'])
                self.assertTrue(result['blocked'])
                self.assertIn('connect-src', result['violations'])
                self.assertIn('form-action', result['violations'])
        self.assertEqual(self.external, [])

    def test_online_actions_remain_blocked_even_if_a_game_rerender_reenables_its_button(self):
        for game, selector, expression in [('Pitch-Race','#multiCard',"document.querySelector('#multiCard').getAttribute('aria-pressed')"), ('musictriad','#vsClassmate','gameMode')]:
            with self.subTest(game=game):
                frame = self.frame(game)
                node = frame.locator(selector)
                self.assertEqual(node.get_attribute('aria-disabled'), 'true')
                initial = frame.evaluate(expression)
                node.evaluate('node=>{node.disabled=false;node.click();}')
                self.assertEqual(frame.evaluate(expression), initial)
                self.assertFalse(frame.evaluate('CodaGamePrivacy.loadFirebaseSDK({multiplayer:true})'))
        self.assertEqual(self.external, [])

    def test_ordinary_same_origin_classroom_play_keeps_its_existing_lazy_multiplayer_loader(self):
        for game in ('Pitch-Race','musictriad'):
            with self.subTest(game=game):
                frame = self.frame(game, enabled=False)
                self.assertFalse(frame.evaluate('CodaGamePrivacy.testMode'))
                self.assertEqual(frame.locator('meta[http-equiv="Content-Security-Policy"]').count(), 0)
                self.assertEqual(frame.locator('#codaTestModeNotice').count(), 0)
                self.assertTrue(frame.evaluate('CodaGamePrivacy.loadFirebaseSDK({multiplayer:true})'))
                self.assertEqual(frame.evaluate('__allowedSDK'), 3)

    def test_cross_origin_parents_and_standalone_url_flags_cannot_activate_test_mode(self):
        for game in GAMES:
            with self.subTest(game=game):
                frame = self.frame(game, cross=True)
                self.assertFalse(frame.evaluate('CodaGamePrivacy.testMode'))
                self.assertEqual(frame.locator('meta[http-equiv="Content-Security-Policy"]').count(), 0)
                self.page.goto(self.base + '/' + game + '/index.html?classroom=1&developer-test=1', wait_until='load')
                self.assertFalse(self.page.evaluate('CodaGamePrivacy.testMode'))
                self.assertEqual(self.page.locator('#codaTestModeNotice').count(), 0)
        self.assertEqual(self.external, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
