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
- **Visiting the Storyteller** (the Savant, the Artist): a private move, seen by the town as a visit, fakeable by
  anyone. Not built: no Bad Moon Rising character needed it.
- **Built in batch 1** (docs/snv-rulings.md): madness (a 'mad' state, `Game.judge_madness`: a judged "did they
  break it?" with a scripted floor and an evidence policy, then a judged "might be executed"; a madness execution
  before nominations is the day's), character changes in bulk with their notices (`Game.change`, `Game.swap`),
  information that must be false (`Character.falsifies`: the Vortox), states worked out on demand (the No Dashii's
  seat-based poison), dead players keeping their ability (the Vigormortis), and abilities triggered by any
  nomination or execution (the Witch, the Evil Twin). The Demons and Minions use them.
- **Madness still needs:** the S&V player prompt (what madness is, what the Storyteller hears), reports to the
  Storyteller ("snitching"), and the Mutant's checkpoints.
- **New win conditions** still to build: the Klutz and the Mutant (`overrides_end` and a public choice on death
  exist).
- **Day guesses** (the Juggler: up to five player-and-character guesses): the shared `ability` move needs a list form.
- **Storyteller content:** Savant statements (templates checked by code against the Grimoire; the TheGrim Discord's
  Savant Generator is one reference) and the Artist's answers (a model turns the question into a checkable statement,
  code answers it).
- **Records** the Flowergirl, Town Crier and Oracle read (who voted, who nominated, dead evil players) exist; the
  Mathematician needs a record of every ability that misfired (a counterfactual "would a sober ability have given
  this?").

**Storyteller policy:** Storyteller's notes for the 25 characters, POLICY weights, and the judge's rules heuristics.

## Custom scripts

- **Loading works** for any script whose characters are built; one with others says which aren't.
- **Jinxes:** the official ones are loaded and shown on the character sheet (`Script.jinxes`), but none is applied:
  each needs implementing (they take about eight forms: bans, setup changes, registration and visibility overrides,
  replacement abilities, alignment locks, kill rulings) or a judge ruling.
- **No Demon or several** (the Legion, the Riot, the Atheist): victory checks and evil's first-night information.
- **Speech-triggered abilities** (the Yaggababble's phrase, the Mezepheles' word): the judge reads speech.
- **Storyteller-invented content** (the Wizard's wish, the Amnesiac's ability): a model judge that generates, with
  code limiting it to effects the engine can carry out.
- **Vote mechanics** (weighted, negative, secret: the Thief, the Bureaucrat, the Voudon): the vote is a plain count.
- **Travellers and exile, Fabled and Loric:** a Traveller flag on players exists; nothing else.

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
