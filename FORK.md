# This fork against the original

This is a fork of [dwarkeshsp/clocktower](https://github.com/dwarkeshsp/clocktower) that extends the engine beyond
Trouble Brewing (Bad Moon Rising, then Sects & Violets, then custom scripts). This file is the ledger of every
change against the original, grouped into the pull requests they would become. It belongs to the fork only: it is
never part of a pull request, but each pull request's description starts from its entry here.

## Comparing with the original

The original is the `upstream` remote (fetch only; its push URL is disabled). The fork's `main` stays identical to
the original's `main`; work happens on branches.

```sh
git fetch upstream main
git log --oneline upstream/main..HEAD      # every commit this branch adds
git diff --stat upstream/main              # every file it changes
git log --oneline HEAD..upstream/main      # new upstream work to bring in
```

Forked at `9fa9773` (2026-11-05). Last compared: 2026-11-06, upstream unchanged since the fork.

## Rules for every change (from the original's CONTRIBUTING.md)

- One logical change per commit, with a message saying what changed and why.
- No test calls a paid API; `pyflakes clocktower tests` is clean; single quotes, 120-column lines, standard
  library first; ask before adding a dependency.
- Trouble Brewing is frozen at protocol v17. A change that alters how it plays is a proposal (issue, calibration
  batch, version bump), never a silent change. A change that should not alter play shows it: `python -m clocktower
  fingerprint --check` replays 1,100 recorded games and must report all identical.
- New scripts are new protocols, written to their own folders and rated separately; they never change TB games.
- The original's pull request template is the checklist for each pull request.

## Changes, grouped into future pull requests

| # | Pull request | Commits | Changes TB play? | Evidence | Status |
|---|---|---|---|---|---|
| 1 | Unbreak CI: drop an unused import that fails pyflakes | `6e45305` | No | pyflakes clean | Local |
| 2 | Replay fingerprints (`python -m clocktower fingerprint`) | `4db5cc5` | No | Deterministic over two runs; covers every TB character 420-520 times | Local |
| 3 | Characters as data, on a script-independent core; TPI's official data pinned | `a4e2ee4`, `abbfdcc`, `08ca1d0`, `435f793` | No | All 1,100 fingerprints identical; prompt byte-identical; 34 old checkpoints resume identically | Local. Large: open an issue first |
| 4 | Scripts as a concept, and a script-independent core (deaths, protection, states with durations, night choices, public abilities, setup choices, victory overrides) | `6e9d30f`, `bc9cf13`, `7019ae2`, `278f4f9`, `a713a90` | No | All 1,100 fingerprints identical; TB prompt and schema byte-identical; `tests/test_core.py` | Local. Needed for any script beyond TB |
| 5 | The Storyteller judge (`judge.py`, `--judge`) | `baab6d7` | No (TB never uses it) | `tests/test_judge.py`: four rulebook and wiki situations, a recorded model answer | Local |
| 6 | Bad Moon Rising: all 25 characters (`bmr.py`), the BMR prompt, the omniscient judge, BMR fingerprints | `753bbec`, `e651767`, `37482a4`, `dbfbe81`, `dc35a34` | No (a new protocol, `bmr-v1`) | 353 tests; 1,100 BMR fingerprints; 2,200 random games at every size with no crash | Local. A proposal to the original author: open an issue first |
| 7 | The owner's review of the BMR rulings, applied; a circular-import fix | `9bd130d`, `6b98fb2` | No (BMR only: its fingerprints re-recorded) | 360 tests | Local, with PR 6 |
| 8 | Sects & Violets: all 25 characters (`snv.py`), madness, character changes, the Vortox, visits to the Storyteller, the S&V prompt and fingerprints | `dd94b5e`, `d22266c`, `b7a7423`, `2be822a` | No (a new protocol, `snv-v1`) | 510 tests; 1,100 S&V fingerprints; 2,200 random games per Storyteller mode with no crash | Local. With the BMR proposal |
| 9 | Custom scripts and experimental characters. Batch 0: real custom scripts load (odd ids, homebrew entries, Travellers, Fabled and Loric kept but not in play), the jinx framework (`Script.jinxed`, `carousel.py`) and the seven jinxes between built characters, the custom-script prompt, `smoke`, the synthetic `carousel-1`. Batch 1: thirteen experimental characters (Banshee, Damsel, Steward, Nightwatchman, Al-Hadikhia, Magician, Golem, Summoner, Ojo, Fisherman, Plague Doctor, Hatter, Politician) and their seventeen jinxes with built characters; the corpus scripts deadpeople, wonders, binarysupernovae and djinnsbargain play end to end; the synthetic `carousel-2`. Batch 2 (`carousel2.py`): fifteen more (Pixie, High Priestess, Poppy Grower, Shugenja, Balloonist, General, Preacher, Cannibal, Puzzlemaster, Heretic, Marionette, Widow, Goblin, Kazali, Leviathan) and their thirty-three jinxes with built characters; the Carousel Script Collection's martianvampires plays end to end; the synthetic `carousel-3`. Batch 3 (`carousel3.py`): thirteen more (Village Idiot, Acrobat, Lycanthrope, Alchemist, Zealot, Organ Grinder, Noble, Farmer, Harpy, Boffin, Boomdandy, Fearmonger, Xaan; Lil' Monsta left for the owner) and their eighteen jinxes with built characters; monkeydomath and the World Championship's seat7 play end to end; the fuzzer's checks for them; the synthetic `carousel-4` | `80042dd`, `fe867b4`, `ca3864b`, `f1468aa` | No (TB, BMR and S&V hold no jinx and none of the new characters; custom scripts are protocol `custom-<id>`) | 759 tests; 1,100 TB, BMR, S&V, `carousel-1`, `-2` and `-3` fingerprints identical each; 1,100 `carousel-4` fingerprints; 2,200 random games each (scripted and rules judge) of `carousel-1` to `-4`, the five World Championship scripts, martianvampires and monkeydomath with no crash; 10,000 fuzzer games | Local. With the BMR proposal; 81 rulings in `docs/carousel-rulings.md` |
| - | Fork documents (`docs/open-decisions.md`, `docs/bmr-rulings.md`, `docs/snv-rulings.md`, `docs/carousel-rulings.md`, `docs/readiness.md`, `docs/review/`, this file) | `cf4cba9`, `94c2c24`, `9ed458d`, `19d8c9b` and later | No | - | Fork only, or part of the BMR proposal |

Found on the way, not yet changed (each changes TB play, so each is a proposal): at 5-6 players with a Baron the
Washerwoman can be the only Townsfolk, and the game stops with "illegal Storyteller value" (5 of the 1,100 recorded
games); the audit's TB findings (the Butler's master learns they were asked early; a failed vote's count is forgotten;
the Chef can't get the almanac's "1" for a Recluse between two evil players; a Mayor bounce can't land on a Soldier).

## The plan in progress (Bad Moon Rising)

Signed off 2026-11-06. Trouble Brewing play does not change at any step.

- **Phase 0, housekeeping:** this ledger and the `upstream` remote; long lines; seats keep their dealt team's
  model on resume; the Storyteller judge design in `docs/open-decisions.md`. *Done.*
- **Phase 1, scripts:** a game takes a script (official script JSON format), default TB; `--script tb|bmr`; BMR is
  its own protocol and folder; a BMR player prompt drafted for review. *Done.*
- **Phase 2, mechanics in the core:** several deaths a night and protection from several sources; dawn in seat
  order; apparent death and resurrection; executions that don't kill; drunkenness and poison from many sources with
  durations; new night-choice shapes; public, day and on-death abilities; setup modifiers and win conditions as
  checks; game records; messages to the Demon at night. Designed for later: registration per observer and check,
  abilities separate from character tokens, a jinx step, players who don't count, a Storyteller visit move.
  *Done, except the Storyteller visit move: no BMR character uses it, so it waits for Sects & Violets (the Savant
  and Artist) rather than adding code nothing exercises.*
- **Phase 3, the Storyteller judge:** scripted, rules, dry-run and model modes; reads only what a Storyteller would;
  code picks from its ranking; rulings logged; a test set with known rulings. *Done. The default judge model is
  claude-haiku-4-5, the cheapest the engine prices; Haiku 5.5 needs adding to llm.py first, by CONTRIBUTING's
  process for a new model.*
- **Phase 4, the 25 BMR characters:** one entry each, with rules tests from the almanac's examples and default
  Storyteller weights for review; the Gossip last. *Done; 35 rulings to review in `docs/bmr-rulings.md`.*
- **Added on the owner's direction: the omniscient judge** (`docs/open-decisions.md`, section 2b). *Done; five
  questions on it there.*
- **Phase 5, checking:** thousands of free random-bot BMR games, fingerprints, the Goon's conversion rate, a
  readiness note for Sects & Violets and custom scripts. *Done: `docs/readiness.md`.*

Not without a separate yes: games with paid models; changes to TB play; the social changes (live voting and the
like); Sects & Violets, custom scripts, Travellers and Fabled; anything on the original repository.
