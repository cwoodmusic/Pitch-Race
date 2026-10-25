"""Run: python tests/arcade-integration-browser.py (requires sibling coda-arcade)."""
import sys
import unittest

sys.dont_write_bytecode = True
from pitch_browser_support import PitchBrowserCase, PITCH, open_destination


class ArcadeIntegrationTests(PitchBrowserCase):
    def test_passed_level_milestones_reward_the_actual_level_once_and_continue(self):
        self.load_world()
        frame = self.cabinet()
        for level, cosmetic in [(10, 'pitchlaurel10'), (20, 'pitchlaurel20'),
                                (30, 'pitchlaurel30'), (40, 'pitchcrown40'), (50, 'starlight')]:
            with self.subTest(level=level):
                # A real saved checkpoint enters the normal next level, never dev mode.
                frame.evaluate('''level=>localStorage.setItem('pitchRaceLevelProgressV1',
                  JSON.stringify({version:1,bestCompleted:level-1}))''', level)
                frame.goto(PITCH, wait_until='domcontentloaded')
                frame.wait_for_function('window.__pitchFixture')
                self.start(frame)
                state = frame.evaluate('window.__pitchFixture.snapshot()')
                self.assertEqual(state['level'], level)
                self.assertEqual(state['staff'], 'treble' if level <= 10 else 'bass' if level <= 20 else 'grand')
                target = int(frame.locator('#challengeTarget').inner_text())
                before = self.totals()
                index = 0
                while frame.evaluate('window.__pitchFixture.snapshot().score') < target:
                    self.answer(frame, {'clef': 'bass' if level > 10 and (level <= 20 or index % 2) else 'treble'})
                    index += 1
                self.expire(frame)
                self.page.wait_for_function('id=>CodaArcadeQA.progression().achievementRewards.some(i=>i.id===id)', arg=cosmetic)
                report = self.reports()[-1]
                self.assertEqual(report['result']['completedLevel'], level)
                self.assertTrue(report['result']['won'])
                self.assertEqual(report['result']['correct'], index)
                after = self.totals()
                self.assertEqual(after['notes'] - before['notes'], 16)
                achievement = 'achievement:pitch-level-' + str(level)
                matching = [event for event in self.journal() if event['id'] == achievement]
                self.assertEqual(len(matching), 1)
                self.assertEqual(matching[0]['xp'], 250 if level == 50 else 50)
                self.assertGreater(after['xp'], before['xp'])
                # Both local duplicate completion and a raw iframe replay stay deduplicated.
                frame.evaluate('''report=>{
                  CodaBridge.report(report.runId,report.result);
                  parent.postMessage(report,location.origin);
                  window.__pitchFixture.expire();
                }''', report)
                self.page.wait_for_timeout(80)
                self.assertEqual(self.totals(), after)
                checkpoint = frame.evaluate('JSON.parse(localStorage.getItem("pitchRaceLevelProgressV1"))')
                self.assertEqual(checkpoint['bestCompleted'], level)
                frame.locator('#resultsMenu').click()
                if frame.locator('#initialsOverlay').is_visible():
                    frame.locator('#initialsSkip').click()
                self.assertIn(str(level + 1), frame.locator('#menuPlay').inner_text())
                self.assertIn('Level ' + str(level + 1), frame.locator('#levelProgressSummary').inner_text())
                # The checkpoint survives child reload and still offers Continue.
                frame.goto(PITCH, wait_until='domcontentloaded')
                frame.locator('#levelsCard').click()
                self.assertIn(str(level + 1), frame.locator('#menuPlay').inner_text())
        persisted = self.totals()
        self.load_world()
        self.assertEqual(self.totals(), persisted)
        frame = self.cabinet()
        frame.evaluate('report=>CodaBridge.report(report.runId,report.result)', report)
        self.page.wait_for_timeout(100)
        self.assertEqual(self.totals(), persisted, 'Run IDs stay deduplicated after both documents reload')

    def test_failed_level_reports_zero_completion_and_retry_preserves_checkpoint(self):
        self.seed_checkpoint(9)
        self.load_world()
        frame = self.cabinet()
        self.start(frame)
        self.answer(frame, wrong=True)
        self.answer(frame)
        self.expire(frame)
        self.page.wait_for_function('window.__messages.some(m=>m.data.type==="result")')
        report = self.reports()[-1]['result']
        self.assertFalse(report['won'])
        self.assertEqual(report['completedLevel'], 0)
        self.assertEqual(report['misses'], 1)
        self.assertNotIn('pitchlaurel10', self.totals()['rewards'])
        self.assertEqual(frame.evaluate('window.__pitchFixture.snapshot().checkpoint.bestCompleted'), 9)
        frame.locator('#resultsReplay').click()
        frame.wait_for_function('window.__pitchFixture.snapshot().state==="running"')
        frame.evaluate('window.__pitchFixture.freeze()')
        self.assertEqual(frame.evaluate('window.__pitchFixture.snapshot().level'), 10)
        self.home(frame)
        frame.locator('#restartLevels').click()
        frame.wait_for_function('window.__pitchFixture.snapshot().state==="running"')
        self.assertEqual(frame.evaluate('window.__pitchFixture.snapshot().level'), 1)
        self.assertEqual(frame.evaluate('window.__pitchFixture.snapshot().checkpoint.bestCompleted'), 9)

    def test_developer_start_and_toggle_off_cannot_award_or_save(self):
        self.load_world()
        frame = self.cabinet()
        before = self.totals()
        for developer_start in [True, False]:
            with self.subTest(developer_start=developer_start):
                if developer_start:
                    frame.locator('#classicCard').click()
                    self.page.keyboard.press('Control+Alt+d')
                    frame.locator('#devLevelInput').fill('50')
                self.start(frame)
                if not developer_start:
                    self.page.keyboard.press('Control+Alt+d')
                self.page.keyboard.press('Control+Alt+d')
                self.assertFalse(frame.evaluate('window.__pitchFixture.snapshot().dev'))
                for _ in range(26):
                    self.answer(frame)
                self.expire(frame)
                self.page.wait_for_timeout(80)
                self.assertEqual(self.reports(), [])
                self.assertEqual(self.totals(), before)
                self.assertEqual(frame.evaluate('window.__pitchFixture.snapshot().checkpoint.bestCompleted'), 0)
                self.assertFalse(frame.locator('#initialsOverlay').is_visible())
                frame.locator('#resultsMenu').click()
                self.assertEqual(frame.evaluate('window.__pitchScoreOffers'), [])
        self.assertEqual(self.external_writes, [])

    def test_bass_and_grand_real_answers_unlock_exclusive_rewards_and_dedupe(self):
        self.load_world()
        open_destination(self.page, 'boutique')
        self.page.get_by_label('Accessories', exact=True).select_option('bassclefpin')
        self.page.get_by_role('button', name='Save my look', exact=True).click()
        self.assertIn('still locked', self.page.locator('.boutique-actions [role="status"]').inner_text())
        self.assertNotEqual(self.page.evaluate('CodaArcadeQA.characters().player.appearance.accessory'), 'bassclefpin')
        self.page.locator('#panelClose').click()
        frame = self.cabinet()
        self.start(frame, mode='classic', staff='bass')
        for _ in range(20):
            self.answer(frame, {'clef': 'bass'})
        self.expire(frame)
        self.page.wait_for_function('CodaArcadeQA.progression().achievementRewards.some(i=>i.id==="basslaurel")')
        report = self.reports()[-1]
        self.assertEqual(report['result']['clefStats']['bass'], {'correct': 20, 'misses': 0, 'bestStreak': 20})
        self.assertEqual(report['result']['clefStats']['treble']['correct'], 0)
        self.assertTrue({'bassclefpin', 'basslaurel'}.issubset(self.totals()['rewards']))
        xp = {event['id']: event['xp'] for event in self.journal()}
        self.assertEqual(xp['achievement:pitch-bass-reader'], 100)
        self.assertEqual(xp['achievement:pitch-bass-streak'], 150)
        self.home(frame)
        self.start(frame, mode='classic', staff='grand')
        for index in range(20):
            self.answer(frame, {'clef': 'bass' if index % 2 else 'treble'})
        self.expire(frame)
        self.page.wait_for_function('CodaArcadeQA.progression().achievementRewards.some(i=>i.id==="grandstaffcrown")')
        self.assertTrue({'grandstaffbadge', 'grandstaffcrown'}.issubset(self.totals()['rewards']))
        xp = {event['id']: event['xp'] for event in self.journal()}
        self.assertEqual(xp['achievement:pitch-grand-reader'], 150)
        self.assertEqual(xp['achievement:pitch-grand-perfect'], 250)
        self.page.locator('#returnworld').click()
        open_destination(self.page, 'boutique')
        self.page.get_by_label('Accessories', exact=True).select_option('bassclefpin')
        self.page.get_by_role('button', name='Save my look', exact=True).click()
        self.assertEqual(self.page.evaluate('CodaArcadeQA.characters().player.appearance.accessory'), 'bassclefpin')

    def test_treble_miss_breaks_bass_streak_and_grand_miss_prevents_perfect_reward(self):
        self.load_world()
        frame = self.cabinet()
        self.start(frame, mode='classic', staff='grand')
        for _ in range(10):
            self.answer(frame, {'clef': 'bass'})
        self.answer(frame, {'clef': 'treble'}, wrong=True)
        for _ in range(10):
            self.answer(frame, {'clef': 'bass'})
            self.answer(frame, {'clef': 'treble'})
        self.expire(frame)
        self.page.wait_for_function('CodaArcadeQA.progression().achievementRewards.some(i=>i.id==="grandstaffbadge")')
        rewards = self.totals()['rewards']
        self.assertIn('bassclefpin', rewards)
        self.assertNotIn('basslaurel', rewards)
        self.assertNotIn('grandstaffcrown', rewards)
        report = self.reports()[-1]['result']
        self.assertEqual(report['clefStats']['bass']['bestStreak'], 10)
        self.assertEqual(report['clefStats']['treble']['misses'], 1)

    def test_countdown_reset_owns_its_timers_and_parent_rejects_wrong_token(self):
        self.load_world()
        frame = self.cabinet()
        frame.locator('#levelsCard').click()
        frame.locator('#menuPlay').click()
        self.page.wait_for_timeout(650)
        frame.locator('#reset').click()
        frame.locator('#start').click()
        self.page.wait_for_timeout(1700)
        self.assertEqual(frame.evaluate('window.__pitchFixture.snapshot().state'), 'countdown')
        frame.wait_for_function('window.__pitchFixture.snapshot().state==="running"')
        frame.evaluate('window.__pitchFixture.freeze()')
        before = self.totals()
        frame.evaluate('''()=>{
          const init=window.__messages.findLast(m=>m.data.type==='init').data;
          const result={mode:'levels',correct:30,misses:0,streak:30,won:true,completedLevel:50};
          parent.postMessage({coda:1,type:'result',game:'pitch',token:'wrong',runId:'tampered',result},location.origin);
          parent.dispatchEvent(new MessageEvent('message',{source:parent,origin:location.origin,
            data:{coda:1,type:'result',game:'pitch',token:init.token,runId:'bad-source',result}}));
        }''')
        self.page.wait_for_timeout(100)
        self.assertEqual(self.totals(), before)
        received = len(self.reports())
        frame.locator('#reset').click()
        self.page.wait_for_timeout(850)
        self.assertEqual(frame.evaluate('window.__pitchFixture.snapshot().state'), 'idle')
        self.assertEqual(len(self.reports()), received)


if __name__ == '__main__':
    unittest.main(verbosity=2)
