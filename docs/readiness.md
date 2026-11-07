# Readiness: what Sects & Violets and custom scripts still need

Written after Bad Moon Rising was built (November 2026). It lists what the next scripts need beyond the core as it
stands, so the next stage starts from a known list rather than a fresh audit. The detailed findings behind each line
are in the engine audit (kept with the fork owner, not in this repository: `snv.md` and `experimental.md`).

## Already in the core

Scripts in the official JSON format; characters as data with hooks; alignment separate from character, kept when the
character changes (`Grimoire.change_character`); states with sources, durations and pauses; deaths from any source,
layered protection, unstoppable kills, survival, apparent death and revival; executions that don't kill; night
choices of any shape (players, none, a character, alive or dead only, not last night's); a stepwise night in the
official order; abilities held beyond one's own character (`Grimoire.abilities`, for the Philosopher); registration
queries that take the observer; public abilities anyone can claim; triggers that ask a player afterwards; points in
the day where the Storyteller acts; setup modifiers, fixed or the Storyteller's choice; victory overrides; records of
deaths, executions, revivals, who woke, nominations and votes; the Storyteller judge (it hears everything but minds,
ranks every discretionary call, reads per-script Storyteller's notes); per-script fingerprints; seats keep their
dealt team's model after a team change.

## Sects & Violets

**New moves and mechanics**
- **Built in batch 3** (docs/snv-rulings.md): visiting the Storyteller (`visit`, `Game.visit_judged`: a private move
  seen by the town as a visit, fakeable by anyone), guesses in the public `ability` move (the Juggler), abilities
  gained beyond one's character woken at their step (the Philosopher), and every remaining character. Sects &
  Violets plays end to end, with its player prompt and replay fingerprints.
- **Built in batch 1** (docs/snv-rulings.md): madness (a 'mad' state, `Game.judge_madness`: a judged "did they
  break it?" with a scripted floor and an evidence policy, then a judged "might be executed"; a madness execution
  before nominations is the day's), character changes in bulk with their notices (`Game.change`, `Game.swap`),
  information that must be false (`Character.falsifies`: the Vortox), states worked out on demand (the No Dashii's
  seat-based poison), dead players keeping their ability (the Vigormortis), and abilities triggered by any
  nomination or execution (the Witch, the Evil Twin). The Demons and Minions use them.
- **Still open:** reports to the Storyteller about other players ("snitching") are only what a visit's text says
  (the model judge reads it; the scripted floor reads only the visitor's own words); the Savant's templates could
  grow (seat ranges, claims); the Artist's non-yes/no questions get "I don't know" rather than "ask again".

**Storyteller policy:** notes for the 25 characters, POLICY weights and the rules judge's heuristics exist, all
marked for the owner's review (docs/snv-rulings.md).

## Custom scripts

**Built in batch 0** (docs/carousel-rulings.md, 1-13):
- **Loading real custom scripts**: ids in any spelling, official characters written as objects, homebrew entries
  (a homebrew Townsfolk, Outsider, Minion or Demon is reported as not built), and Travellers, Fabled and Loric kept
  on the script (`Script.travellers`, `.fabled`, `.loric`), noted on the sheet as not in play, never dealt or woken.
  Every World Championship 2025 corpus script loads up to its unbuilt characters; none yet has all of them built.
- **Jinxes**: `Script.jinxed(a, b)` (in effect when both are on the script; `Script.of(..., jinxes=...)` for tests),
  with every implemented jinx declared in `clocktower/carousel.py`. The seven official jinxes between characters
  already built are implemented (Mastermind/Vigormortis, Mathematician with the Chambermaid, the Drunk and the
  Lunatic, Pit-Hag/Goon, Recluse/Sage, Scarlet Woman/Fang Gu); none is in effect on TB, BMR or S&V.
- **The custom-script player prompt**: TB's with generic sentences, S&V's madness and visit sentences only when the
  script's characters use them (a draft for review).
- **Smoke runs**: `python -m clocktower smoke --script ID` and `--corpus` (random bots, both Storyteller modes, every
  size). The synthetic `carousel-1` (all seven jinxes) plays 2,200 games with no crash and has replay fingerprints.

**Still open:**
- **The experimental characters** (71 in the official data's carousel edition): later batches, in
  `clocktower/carousel.py`. The corpus needs Balloonist (7 scripts), Fisherman and Shugenja (6), Amnesiac, Damsel,
  High Priestess, Noble and Pixie (5) most.
- **Jinxes** with experimental characters: each with its character. They take about eight forms (bans, setup
  changes, registration and visibility overrides, replacement abilities, alignment locks, kill rulings).
- **No Demon or several** (the Legion, the Riot, the Atheist): victory checks and evil's first-night information.
- **Speech-triggered abilities** (the Yaggababble's phrase, the Mezepheles' word): the judge reads speech.
- **Storyteller-invented content** (the Wizard's wish, the Amnesiac's ability): a model judge that generates, with
  code limiting it to effects the engine can carry out.
- **Vote mechanics** (weighted, negative, secret: the Thief, the Bureaucrat, the Voudon): the vote is a plain count.
- **Travellers and exile, Fabled and Loric:** listed, not played; a Traveller flag on players exists; nothing else.
- **Homebrew characters** and scripts' house rules (the corpus's "bootlegger" rules): not played.

## Around the engine

- **The browser table** (`web.py`, `table/`) plays Trouble Brewing only: its character sheet, roles and the Slayer
  button are TB's.
- **Ratings and analysis** (`ratings.py`, `analyze.py`, `export.py`) have setup terms for TB's Minions; another
  script needs its own (its Minions and Demons).
- **Rating seats that change team:** a Goon is in play in about 29% of random 10-12 player BMR games and ends on the
  other team in about 28% of those (about 8% of all games, from 3,000 random-bot games; random bots choose at random,
  so this is how often the mechanic can fire, not how often players would make it). See `docs/open-decisions.md`,
  section 1.
- **The judge's model** defaults to claude-haiku-4-5, the cheapest model the engine prices; a newer one needs adding to
  `llm.py` by CONTRIBUTING's process.
