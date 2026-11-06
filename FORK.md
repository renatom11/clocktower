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
| - | Fork documents (`docs/open-decisions.md`, this file) | `cf4cba9` and later | No | - | Fork only, or part of a BMR proposal |

Found on the way, not yet changed (each changes TB play, so each is a proposal): at 5-6 players with a Baron the
Washerwoman can be the only Townsfolk, and the game stops with "illegal Storyteller value" (5 of the 1,100 recorded
games); the audit's TB findings (the Butler's master learns they were asked early; a failed vote's count is forgotten;
the Chef can't get the almanac's "1" for a Recluse between two evil players; a Mayor bounce can't land on a Soldier).

## The plan in progress (Bad Moon Rising)

Signed off 2026-11-06. Trouble Brewing play does not change at any step.

- **Phase 0, housekeeping:** this ledger and the `upstream` remote; long lines; seats keep their dealt team's
  model on resume; the Storyteller judge design in `docs/open-decisions.md`. *Done.*
- **Phase 1, scripts:** a game takes a script (official script JSON format), default TB; `--script tb|bmr`; BMR is
  its own protocol and folder; a BMR player prompt drafted for review.
- **Phase 2, mechanics in the core:** several deaths a night and protection from several sources; dawn in seat
  order; apparent death and resurrection; executions that don't kill; drunkenness and poison from many sources with
  durations; new night-choice shapes; public, day and on-death abilities; setup modifiers and win conditions as
  checks; game records; messages to the Demon at night. Designed for later: registration per observer and check,
  abilities separate from character tokens, a jinx step, players who don't count, a Storyteller visit move.
- **Phase 3, the Storyteller judge:** scripted, rules, dry-run and model modes; reads only what a Storyteller would;
  code picks from its ranking; rulings logged; a test set with known rulings.
- **Phase 4, the 25 BMR characters:** one entry each, with rules tests from the almanac's examples and default
  Storyteller weights for review; the Gossip last.
- **Phase 5, checking:** thousands of free random-bot BMR games, fingerprints, the Goon's conversion rate, a
  readiness note for Sects & Violets and custom scripts.

Not without a separate yes: games with paid models; changes to TB play; the social changes (live voting and the
like); Sects & Violets, custom scripts, Travellers and Fabled; anything on the original repository.
