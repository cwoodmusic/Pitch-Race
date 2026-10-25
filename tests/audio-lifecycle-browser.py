"""Pitch audio lifecycle regressions, using Chromium and a local WAV only.

Run: python tests/audio-lifecycle-browser.py
Requires the Python playwright package and Chromium (CHROMIUM may override its path).
Firebase and recording hosts are blocked; tests never submit online scores or rooms.
"""
import io
import math
import os
from pathlib import Path
import struct
import threading
import unittest
import wave
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HOOK = """
window.__pitchAudioTest={
  musicPlayer,musicPlayTrack,musicStop,playFinish,playCombo,start,reset,toggleSound,
  running:()=>{state='running'},
  snapshot:()=>({state,soundOn,musicEnabled,musicPaused:musicPlayer.paused,
    musicCurrent:musicCurrent?.id||null,voices:activeEffects.size})
};
"""
INSTRUMENT = """
<script>
window.__audioStops=[];
const originalOscillator=AudioContext.prototype.createOscillator;
AudioContext.prototype.createOscillator=function(){
  const oscillator=originalOscillator.call(this),stop=oscillator.stop.bind(oscillator);
  const record={immediateStops:0};window.__audioStops.push(record);
  oscillator.stop=(when)=>{if(when===undefined)record.immediateStops++;return stop(when)};
  return oscillator;
};
</script>
"""


def wav_bytes():
    target = io.BytesIO()
    with wave.open(target, 'wb') as recording:
        recording.setnchannels(1)
        recording.setsampwidth(2)
        recording.setframerate(8000)
        recording.writeframes(b''.join(
            struct.pack('<h', int(1000 * math.sin(2 * math.pi * 220 * i / 8000)))
            for i in range(8000 * 5)))
    return target.getvalue()


WAV = wav_bytes()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.path == '/audit.wav':
            self.send_response(200)
            self.send_header('Content-Type', 'audio/wav')
            self.send_header('Content-Length', str(len(WAV)))
            self.end_headers()
            self.wfile.write(WAV)
        elif self.path in ('/', '/index.html'):
            source = (ROOT / 'index.html').read_text()
            before, after = source.rsplit('})();', 1)
            source = (before + HOOK + '})();' + after).replace('<head>', '<head>' + INSTRUMENT, 1)
            data = source.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            super().do_GET()

    def log_message(self, *_args):
        pass


class AudioLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.origin = 'http://127.0.0.1:' + str(cls.server.server_port)
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            executable_path=os.environ.get('CHROMIUM', '/usr/bin/chromium'),
            headless=True,
            args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required'])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.context = self.browser.new_context()
        self.context.route('**/*', lambda route: route.continue_()
                           if route.request.url.startswith(self.origin + '/') else route.abort())
        self.page = self.context.new_page()
        self.page.goto(self.origin)
        self.page.wait_for_function('!!window.__pitchAudioTest')

    def tearDown(self):
        self.context.close()

    def local_music(self, extra=''):
        self.page.evaluate("""extra=>{
            __pitchAudioTest.running();
            __pitchAudioTest.musicPlayTrack({id:'local-test',url:'/audit.wav',
                title:'Local test',composer:'Test',start:1});
            if(extra==='off')document.querySelector('#musicToggle').click();
            if(extra==='stop')__pitchAudioTest.musicStop();
        }""", extra)

    def test_music_off_during_metadata_never_starts_playback(self):
        self.local_music('off')
        self.page.wait_for_function('__pitchAudioTest.musicPlayer.readyState>=1')
        state = self.page.evaluate('__pitchAudioTest.snapshot()')
        self.assertFalse(state['musicEnabled'])
        self.assertTrue(state['musicPaused'])
        # Turning it back on must still complete the pending start-offset seek.
        self.page.evaluate("document.querySelector('#musicToggle').click()")
        self.page.wait_for_function('!__pitchAudioTest.musicPlayer.paused && __pitchAudioTest.musicPlayer.currentTime>=1')

    def test_music_stop_invalidates_pending_metadata(self):
        self.local_music('stop')
        self.page.wait_for_timeout(250)
        state = self.page.evaluate('__pitchAudioTest.snapshot()')
        self.assertTrue(state['musicPaused'])
        self.assertIsNone(state['musicCurrent'])
        self.assertIsNone(self.page.evaluate("__pitchAudioTest.musicPlayer.getAttribute('src')"))

    def test_new_game_stops_every_old_fanfare_source(self):
        result = self.page.evaluate("""()=>{
            __pitchAudioTest.playFinish(true);
            const old=__audioStops.slice();
            __pitchAudioTest.start();
            return {stopped:old.map(v=>v.immediateStops),...__pitchAudioTest.snapshot()};
        }""")
        self.assertEqual(result['stopped'], [1, 1, 1, 1])
        self.assertEqual(result['state'], 'countdown')
        self.assertEqual(result['voices'], 1)  # Fresh countdown cue only.

    def test_sound_off_cancels_scheduled_fanfare_sources(self):
        result = self.page.evaluate("""()=>{
            __pitchAudioTest.playFinish(true);
            __pitchAudioTest.toggleSound();
            return {stopped:__audioStops.map(v=>v.immediateStops),...__pitchAudioTest.snapshot()};
        }""")
        self.assertFalse(result['soundOn'])
        self.assertEqual(result['voices'], 0)
        self.assertEqual(result['stopped'], [1, 1, 1, 1])

    def test_finish_replaces_pending_combo_effects(self):
        result = self.page.evaluate("""()=>{
            __pitchAudioTest.playCombo(false);
            const old=__audioStops.slice();
            __pitchAudioTest.playFinish(true);
            return {stopped:old.map(v=>v.immediateStops),voices:__pitchAudioTest.snapshot().voices};
        }""")
        self.assertEqual(result['stopped'], [1, 1, 1, 1])
        self.assertEqual(result['voices'], 4)

    def test_finished_sources_release_their_tracking_entries(self):
        self.page.evaluate('__pitchAudioTest.playFinish(true)')
        self.page.wait_for_function('__pitchAudioTest.snapshot().voices===0', timeout=3000)


if __name__ == '__main__':
    unittest.main(verbosity=2)
