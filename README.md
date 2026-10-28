# Pitch Race

A static browser game for learning note names. Serve this directory with Python 3 (`python3 -m http.server 8005`) or another static server; no dependency installation or build is needed.

Level mode starts with treble clef (1–10), introduces bass clef (11–20), and uses grand staff from level 21. Other modes offer a staff selector; multiplayer uses the host's choice. Half and whole notes use the existing hold controls. Each Level Challenge mistake deducts one point, with scores never going below zero. Level progress saves on this browser, with Continue, Retry, and Restart at Level 1.

In every race mode, each three cumulative mistakes freeze your notes in place for three seconds. Wrong answers and missed notes both count; a correct answer does not reset the count. Answers are disabled during the freeze, and no new notes appear until it ends. Race timers and opponents keep going. The freeze applies in multiplayer even when the host turns off optional wrong-note penalties. Endless Challenge resumes after each freeze; choose **Finish run** to complete it and receive the usual results and eligible arcade rewards.

The **Learn the staves** lessons teach lines, spaces, and middle C with guided practice and short quizzes. Read each pattern upward from the bottom:

- Treble lines: Every Good Boy Does Fine (E G B D F)
- Treble spaces: FACE
- Bass lines: Great Big Dreams For America (G B D F A)
- Bass spaces: All Cows Eat Grass (A C E G)

When launched through the Coda Arcade cabinet, completed runs report Notes, XP, level milestones, and clef mastery evidence to the arcade. Standalone play does not grant arcade rewards. Developer practice does not earn rewards, save level checkpoints, or submit leaderboard scores, even if developer mode is later hidden during that challenge. Lessons do not report race results.

Firebase project configuration is unchanged. Online leaderboards and multiplayer still use their existing Firebase service; the narrow multiplayer validation compatibility change is described below.

## Validation

With Node, Python Playwright, and Chromium installed:

```sh
node --test tests/*.test.cjs tests/*.test.js
python3 tests/arcade-integration-browser.py
python3 tests/notation-tutorial-browser.py
python3 tests/note-freeze-browser.py
python3 tests/audio-lifecycle-browser.py
python3 tests/multiplayer-lifecycle-browser.py
```

The arcade integration suite expects the `coda-arcade` checkout beside this directory. Browser fixtures add hooks only to the test-served HTML; the deployed game has no test shortcut API. Tests block external services and do not write live Firebase scores or rooms.

## Classroom privacy

Launch with `?classroom=1` (or embed in Coda with classroom privacy on) to keep scores and rewards inside the parent arcade profile. Solo play does not load Firebase SDKs or create game-level accounts. Public leaderboards and high-score initials stay off. Multiplayer Race is available: choose Create Race or Join Race to connect using a temporary anonymous game session and a four-letter room code. Classroom multiplayer uses in-memory authentication, so it does not store a game login on the device. Externally hosted background recordings are also off; native note, countdown and result sounds remain. Same-origin classroom frames inherit their parent's scoped progress store before the game reads local progress. Standalone play without the flag retains its existing online features.

Privacy regression checks: `python3 tests/classroom-privacy-browser.py` (expects the `coda-arcade`, `musictriad`, and `rhythmroom` checkouts beside this directory). External services are blocked; standalone SDK behavior uses a local test double.

Multiplayer lobby requests are cancelled when you leave or reopen the lobby. A
late sign-in, room read, or transaction cannot reconnect an abandoned lobby. If
a room closes or your membership ends during a race, playback and score syncing
stop and the game returns to the join/create screen. The multiplayer lifecycle
checks use in-memory service doubles and make no live database changes.

## Multiplayer rule compatibility

The current room payload includes the host's staff choice (`treble`, `bass`, or
`grand`), and ledger notes can have staff positions from −2 through 10.
`multiplayer-rules.fragment.json` permits those existing values. It changes only
these two validation leaves; it does not loosen room ownership, player writes,
settings access, or any other database namespace.

Never deploy the fragment as the full database rules. Save a fresh complete
rules snapshot, then generate a candidate with:

```sh
node tools/merge-multiplayer-rules.cjs current-full-rules.json merged-full-rules.json
node --test tests/multiplayer-rules.test.cjs
node tools/test-multiplayer-rules.cjs
```

Review the complete merge before publishing it. The merger preserves unrelated
nodes and refuses an unrecognized preexisting staff or note validator. The
emulator runner uses only the loopback `demo-coda-pitch-rules` project, the
isolated Firebase toolchain in `/tmp/coda-classroom-emulator` (override with
`CODA_FIREBASE_TEST_TOOLS`), and the sibling Coda Arcade loopback preloader. Its
regressions first reproduce the old validation failures, then check accepted
staff/ledger notes, rejected invalid values, and unchanged cross-player guards.
No deployed credentials or real rooms are used by these tests.
