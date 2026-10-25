"""Run: python tests/notation-tutorial-browser.py; real rendered SVG and input."""
import sys
import unittest

sys.dont_write_bytecode = True
from pitch_browser_support import PitchBrowserCase


class NotationTutorialTests(PitchBrowserCase):
    def test_bass_positions_letters_keyboard_and_actual_note_frequencies(self):
        frame = self.load_pitch()
        self.assertEqual(frame.locator('#menuStaff').input_value(), 'treble')
        for mode in ['classic', 'endless']:
            frame.locator('#' + mode + 'Card').click()
            self.assertEqual(frame.locator('#menuStaff option').evaluate_all('(items)=>items.map(i=>i.value)'), ['treble', 'bass', 'grand'])
        self.start(frame, mode='classic', staff='bass')
        self.assertTrue(frame.locator('#staffChoice').is_disabled())
        self.assertEqual(frame.locator('#playerStaff').get_attribute('data-staff'), 'bass')
        self.assertEqual(frame.locator('#playerStaff [data-symbol="bass-clef"]').count(), 1)
        self.assertEqual(frame.locator('#playerStaff [data-symbol="treble-clef"]').count(), 0)
        for pitch, letter, y, midi, frequency in [(0, 'G', 118, 43, 97.998859), (8, 'A', 30, 57, 220.0), (10, 'C', 8, 60, 261.625565)]:
            with self.subTest(pitch=pitch):
                frame.evaluate('n=>window.__pitchFixture.note(n)', {'pitch': pitch, 'clef': 'bass'})
                note = frame.locator('#playerStaff [data-note]')
                self.assertEqual(note.get_attribute('data-letter'), letter)
                self.assertEqual(int(note.get_attribute('data-midi')), midi)
                self.assertEqual(float(note.locator('[data-symbol="notehead"]').get_attribute('data-y')), y)
                self.assertEqual(note.locator('[data-symbol="ledger-line"]').count(), 1 if pitch == 10 else 0)
                frame.locator('#playerStaff').click()
                frame.evaluate('window.__pitchTones=[]')
                before = frame.evaluate('window.__pitchFixture.snapshot().correct')
                self.page.keyboard.press(letter.lower())
                self.assertEqual(frame.evaluate('window.__pitchFixture.snapshot().correct'), before + 1)
                tones = frame.evaluate('window.__pitchTones')
                self.assertAlmostEqual(tones[0], frequency, places=3)
                self.assertAlmostEqual(tones[1], frequency * 2, places=3)
        frame.locator('#reset').click()
        self.assertFalse(frame.locator('#staffChoice').is_disabled())
        frame.locator('#staffChoice').select_option('grand')
        self.assertEqual(frame.locator('#playerStaff').get_attribute('data-staff'), 'grand')

    def test_grand_staff_has_two_staves_balanced_notes_and_shared_middle_c(self):
        frame = self.load_pitch()
        self.start(frame, mode='classic', staff='grand')
        self.assertEqual(frame.locator('#playerStaff g[data-clef]').count(), 2)
        self.assertEqual(frame.locator('#playerStaff [data-symbol="grand-brace"]').count(), 1)
        samples = frame.evaluate('window.__pitchFixture.sample(100)')
        self.assertEqual(sum(n['clef'] == 'bass' for n in samples), 50)
        self.assertEqual(sum(n['clef'] == 'treble' for n in samples), 50)
        middle = [n for n in samples if n['pitch'] in (-2, 10)]
        self.assertTrue(any(n['clef'] == 'bass' and n['pitch'] == 10 for n in middle))
        self.assertTrue(any(n['clef'] == 'treble' and n['pitch'] == -2 for n in middle))
        for note in middle:
            self.assertEqual(note['letter'], 'C')
            self.assertAlmostEqual(note['frequency'], 261.625565, places=3)
        for clef, pitch in [('treble', -2), ('bass', 10)]:
            frame.evaluate('n=>window.__pitchFixture.note(n)', {'pitch': pitch, 'clef': clef})
            note = frame.locator('#playerStaff [data-note]')
            self.assertEqual(note.get_attribute('data-midi'), '60')
            self.assertEqual(note.locator('[data-symbol="notehead"]').get_attribute('data-y'), '140')
            ledger = note.locator('[data-symbol="ledger-line"]')
            self.assertEqual(ledger.count(), 1)
            self.assertEqual(ledger.get_attribute('y1'), '140')
            self.answer(frame, {'pitch': pitch, 'clef': clef}, key=True)
        self.assertEqual(frame.evaluate('window.__pitchFixture.snapshot().correct'), 2)
        frame.evaluate('window.__pitchFixture.note({pitch:-2,clef:"treble"})')
        self.page.screenshot(path='/tmp/pitch44-grand-desktop.png', full_page=True)

    def test_long_bass_note_uses_real_key_hold_and_quarters_are_single_taps(self):
        self.seed_checkpoint(10)
        frame = self.load_pitch()
        self.start(frame)
        self.assertEqual(frame.evaluate('window.__pitchFixture.snapshot().staff'), 'bass')
        self.assertTrue(frame.locator('#menuStaff').is_disabled())
        frame.evaluate('window.__pitchFixture.note({pitch:0,clef:"bass",kind:"half"})')
        frame.locator('#playerStaff').click()
        self.page.keyboard.down('g')
        self.assertEqual(frame.evaluate('window.__pitchFixture.snapshot().correct'), 0)
        self.assertIsNotNone(frame.evaluate('window.__pitchFixture.snapshot().hold'))
        frame.evaluate('window.__pitchFixture.advanceHold(.68)')
        self.page.keyboard.up('g')
        self.assertEqual(frame.evaluate('window.__pitchFixture.snapshot().correct'), 1)
        self.answer(frame, {'pitch': 0, 'clef': 'bass', 'kind': 'quarter'})
        self.assertEqual(frame.evaluate('window.__pitchFixture.snapshot().correct'), 2)

    def test_mobile_staff_and_controls_remain_readable_without_timer_clipping(self):
        frame = self.load_pitch()
        for width, height in [(320, 700), (390, 844), (844, 390)]:
            with self.subTest(width=width, height=height):
                self.page.set_viewport_size({'width': width, 'height': height})
                self.start(frame, mode='classic', staff='grand')
                self.answer(frame, {'clef': 'bass', 'pitch': 0})
                geometry = frame.evaluate('''()=>{
                  const svg=document.querySelector('#playerStaff'),r=svg.getBoundingClientRect(),
                    box=svg.viewBox.baseVal,timer=document.querySelector('#timer').getBoundingClientRect(),
                    panel=svg.closest('.panel').getBoundingClientRect();
                  return {scroll:document.documentElement.scrollWidth,viewport:innerWidth,
                    space:r.width/box.width*22,timerRight:timer.right,panelRight:panel.right,
                    keys:[...document.querySelectorAll('#answers button')].map(b=>({
                      width:b.getBoundingClientRect().width,height:b.getBoundingClientRect().height}))};
                }''')
                self.assertLessEqual(geometry['scroll'], geometry['viewport'])
                self.assertGreaterEqual(geometry['space'], 11)
                self.assertLessEqual(geometry['timerRight'], geometry['panelRight'])
                for key in geometry['keys']:
                    self.assertGreaterEqual(key['width'], 44)
                    self.assertGreaterEqual(key['height'], 44)
                if width == 320:
                    self.page.screenshot(path='/tmp/pitch44-grand-phone.png', full_page=True)
                self.home(frame)

    def test_scaffolded_lessons_quizzes_and_middle_c_never_award_or_launch_a_race(self):
        self.load_world()
        frame = self.cabinet()
        before = self.totals()
        cases = [
            ('treble', {2: 'E', 4: 'A', 5: 'F'}, ['E', 'F', 'B'],
             ['Every Good Boy Does Fine', 'FACE']),
            ('bass', {2: 'G', 4: 'A', 5: 'D'}, ['G', 'F', 'C'],
             ['Great Big Dreams For America', 'All Cows Eat Grass']),
            ('grand', {3: 'Bass', 4: 'G', 5: 'C'}, ['Treble', 'G', 'C'],
             ['ledger line', 'Middle C'])]
        for lesson, checks, quiz, required_text in cases:
            with self.subTest(lesson=lesson):
                frame.locator('#pitchTutorialsButton').click()
                frame.locator('[data-pitch-lesson="' + lesson + '"]').click()
                seen = []
                for step in range(7):
                    state = frame.evaluate('window.pitchTutorials.getState()')
                    self.assertEqual((state['phase'], state['step']), ('lesson', step))
                    seen.append(frame.locator('.pitch-tutorials-panel').inner_text())
                    self.assertEqual(frame.locator('#pitchTutorialExample svg').count(), 1)
                    if lesson == 'bass' and step == 1:
                        self.page.screenshot(path='/tmp/pitch44-tutorial-mnemonic.png', full_page=True)
                    if lesson == 'grand' and step in (1, 2):
                        note = frame.locator('#pitchTutorialExample [data-note]')
                        self.assertEqual(note.get_attribute('data-midi'), '60')
                        self.assertEqual(note.locator('[data-symbol="ledger-line"]').get_attribute('y1'), '140')
                        frame.evaluate('window.__pitchTones=[]')
                        frame.locator('#pitchTutorialHear').click()
                        self.assertAlmostEqual(frame.evaluate('window.__pitchTones[0]'), 261.625565, places=3)
                    if step in checks:
                        self.assertTrue(frame.locator('#pitchTutorialNext').is_disabled())
                        frame.locator('#pitchTutorialChoices [data-answer="' + checks[step] + '"]').click()
                        self.assertFalse(frame.locator('#pitchTutorialNext').is_disabled())
                    frame.locator('#pitchTutorialNext').click()
                for question, answer in enumerate(quiz):
                    state = frame.evaluate('window.pitchTutorials.getState()')
                    self.assertEqual((state['phase'], state['step']), ('quiz', question))
                    self.assertTrue(frame.locator('#pitchTutorialNext').is_disabled())
                    wrong = frame.locator('#pitchTutorialChoices button').evaluate_all(
                        '(buttons)=>buttons.map(b=>b.dataset.answer)', [])
                    wrong = next(choice for choice in wrong if choice != answer)
                    frame.locator('#pitchTutorialChoices [data-answer="' + wrong + '"]').click()
                    self.assertIn('Try again', frame.locator('#pitchTutorialFeedback').inner_text())
                    self.assertTrue(frame.locator('#pitchTutorialNext').is_disabled())
                    self.assertEqual(frame.evaluate('window.pitchTutorials.getState().correct'), question)
                    frame.locator('#pitchTutorialChoices [data-answer="' + answer + '"]').click()
                    frame.locator('#pitchTutorialNext').click()
                state = frame.evaluate('window.pitchTutorials.getState()')
                self.assertEqual(state['phase'], 'complete')
                self.assertEqual(state['correct'], 3)
                self.assertIn(lesson, state['completed'])
                for text in required_text:
                    self.assertIn(text, '\n'.join(seen))
                self.assertNotRegex('\n'.join(seen), r'\b[A-G][0-9]\b')
                self.page.keyboard.press('Escape')
                self.assertTrue(frame.locator('#pitchTutorialsHost').is_hidden())
                self.assertEqual(frame.evaluate('document.activeElement.id'), 'pitchTutorialsButton')
                self.assertEqual(frame.evaluate('window.__pitchFixture.snapshot().state'), 'idle')
                self.assertEqual(self.totals(), before)
                self.assertEqual(self.reports(), [])
        saved = frame.evaluate('JSON.parse(localStorage.getItem("pitchRaceTutorialsV1"))')
        self.assertCountEqual(saved['completed'], ['treble', 'bass', 'grand'])
        self.start(frame, mode='classic')
        self.assertFalse(frame.evaluate('window.pitchTutorials.open("bass")'))
        self.assertTrue(frame.locator('#pitchTutorialsHost').is_hidden())
        self.assertTrue(frame.locator('#pitchGameTutorialsButton').is_disabled())

    def test_mobile_tutorial_modal_has_readable_diagrams_and_reachable_controls(self):
        frame = self.load_pitch()
        for width, height in [(320, 700), (390, 844), (844, 390)]:
            with self.subTest(width=width, height=height):
                self.page.set_viewport_size({'width': width, 'height': height})
                frame.locator('#pitchTutorialsButton').click()
                frame.locator('[data-pitch-lesson="grand"]').click()
                frame.locator('#pitchTutorialNext').click()
                geometry = frame.evaluate('''()=>{
                  const panel=document.querySelector('.pitch-tutorials-panel'),r=panel.getBoundingClientRect(),
                    svg=document.querySelector('#pitchTutorialExample svg'),s=svg.getBoundingClientRect();
                  return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,
                    viewport:{width:innerWidth,height:innerHeight},scroll:panel.scrollWidth,
                    width:panel.clientWidth,font:parseFloat(getComputedStyle(document.querySelector('#pitchTutorialText')).fontSize),
                    space:s.width/svg.viewBox.baseVal.width*22,
                    controls:[...panel.querySelectorAll('button')].filter(b=>b.getClientRects().length).map(b=>({
                      width:b.getBoundingClientRect().width,height:b.getBoundingClientRect().height}))};
                }''')
                self.assertGreaterEqual(geometry['left'], 0)
                self.assertLessEqual(geometry['right'], width)
                self.assertGreaterEqual(geometry['top'], 0)
                self.assertLessEqual(geometry['bottom'], height)
                self.assertLessEqual(geometry['scroll'], geometry['width'])
                self.assertGreaterEqual(geometry['font'], 16)
                self.assertGreaterEqual(geometry['space'], 11)
                for control in geometry['controls']:
                    self.assertGreaterEqual(control['width'], 44)
                    self.assertGreaterEqual(control['height'], 44)
                frame.locator('#pitchTutorialNext').click()
                frame.locator('#pitchTutorialNext').click()
                # At the two-word clef question both answers remain reachable.
                self.assertEqual(frame.locator('#pitchTutorialChoices button').count(), 2)
                frame.locator('#pitchTutorialChoices [data-answer="Bass"]').click()
                frame.locator('#pitchTutorialClose').click()


if __name__ == '__main__':
    unittest.main(verbosity=2)
