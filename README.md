# Pitch Race

A static browser game for learning note names. Serve this directory with Python 3 (`python3 -m http.server 8005`) or another static server; no dependency installation or build is needed.

Level mode starts with treble clef (1–10), introduces bass clef (11–20), and uses grand staff from level 21. Other modes offer a staff selector; multiplayer uses the host's choice. Half and whole notes use the existing hold controls. Each Level Challenge mistake deducts one point, with scores never going below zero. Level progress saves on this browser, with Continue, Retry, and Restart at Level 1.

The **Learn the staves** lessons teach lines, spaces, and middle C with guided practice and short quizzes. Read each pattern upward from the bottom:

- Treble lines: Every Good Boy Does Fine (E G B D F)
- Treble spaces: FACE
- Bass lines: Great Big Dreams For America (G B D F A)
- Bass spaces: All Cows Eat Grass (A C E G)

When launched through the Coda Arcade cabinet, completed runs report Notes, XP, level milestones, and clef mastery evidence to the arcade. Standalone play does not grant arcade rewards. Developer practice does not earn rewards, save level checkpoints, or submit leaderboard scores, even if developer mode is later hidden during that challenge. Lessons do not report race results.

Firebase configuration and rules are unchanged. Existing online leaderboards and multiplayer still use their deployed Firebase service.

## Validation

With Node, Python Playwright, and Chromium installed:

```sh
node --test tests/*.test.cjs tests/*.test.js
python3 tests/arcade-integration-browser.py
python3 tests/notation-tutorial-browser.py
python3 tests/audio-lifecycle-browser.py
```

The arcade integration suite expects the `coda-arcade` checkout beside this directory. Browser fixtures add hooks only to the test-served HTML; the deployed game has no test shortcut API. Tests block external services and do not write live Firebase scores or rooms.

## Classroom privacy

Launch with `?classroom=1` (or embed in Coda with classroom privacy on) to keep scores and rewards inside the parent arcade profile. This mode does not load Firebase SDKs, create game-level anonymous accounts, read or submit public leaderboards, ask for initials, or offer online multiplayer. Externally hosted background recordings are also off; native note, countdown and result sounds remain. Same-origin classroom frames inherit their parent's scoped progress store before the game reads local progress. Standalone play without the flag retains its existing online features.

Privacy regression checks: `python3 tests/classroom-privacy-browser.py` (expects the `coda-arcade`, `musictriad`, and `rhythmroom` checkouts beside this directory). External services are blocked; standalone SDK behavior uses a local test double.
