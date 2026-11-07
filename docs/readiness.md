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
  Every World Championship 2025 corpus script loads up to its unbuilt characters.
- **Jinxes**: `Script.jinxed(a, b)` (in effect when both are on the script; `Script.of(..., jinxes=...)` for tests),
  with every implemented jinx declared in `clocktower/carousel.py`. The seven official jinxes between characters
  already built are implemented (Mastermind/Vigormortis, Mathematician with the Chambermaid, the Drunk and the
  Lunatic, Pit-Hag/Goon, Recluse/Sage, Scarlet Woman/Fang Gu); none is in effect on TB, BMR or S&V.
- **The custom-script player prompt**: TB's with generic sentences, S&V's madness and visit sentences only when the
  script's characters use them (a draft for review).
- **Smoke runs**: `python -m clocktower smoke --script ID` and `--corpus` (random bots, both Storyteller modes, every
  size). The synthetic `carousel-1` (all seven jinxes) plays 2,200 games with no crash and has replay fingerprints.

**Built in batch 1** (docs/carousel-rulings.md, 14-39):
- **Thirteen experimental characters** in `clocktower/carousel.py`: the Banshee, Damsel, Steward, Nightwatchman,
  Al-Hadikhia, Magician, Golem, Summoner, Ojo, Fisherman, Plague Doctor, Hatter and Politician, with Storyteller's
  notes (`clocktower/data/storyteller/carousel.md`) and the seventeen official jinxes between them and built
  characters. Core hooks they needed, all no-ops elsewhere: nomination limits and weighted or free votes (the
  Banshee, the Golem), evil's first-night information (the Magician, the Damsel), no Demon at setup (the Summoner),
  the Storyteller holding a Minion's ability (the Plague Doctor), an end-of-game hook (the Politician), a yes/no
  request kind (`decide`: the Al-Hadikhia's live or die), the Spy's Grimoire with tokens removed.
- **Four corpus scripts play end to end**: deadpeople, wonders, binarysupernovae and djinnsbargain (`python -m
  clocktower smoke --corpus`: 2,200 random-bot games each under the scripted Storyteller and under the rules judge,
  sizes 5-15, no crash). Two fixes found that way: a Demon whose setup modifier can't be dealt is not drawn, and a
  false result names the script's Demon rather than the Imp.
- **The synthetic `carousel-2`** (the thirteen, and all seventeen jinxes) plays 2,200 games with no crash and has
  replay fingerprints.

**Built in batch 2** (docs/carousel-rulings.md, 40-64):
- **Fifteen experimental characters** in `clocktower/carousel2.py`: the Pixie, High Priestess, Poppy Grower,
  Shugenja, Balloonist, General, Preacher, Cannibal, Puzzlemaster, Heretic, Marionette, Widow, Goblin, Kazali and
  Leviathan, with Storyteller's notes and the thirty-three official jinxes between them and built characters. Core
  changes, all no-ops on the base scripts: a jinx text that allows only one of a pair in play (`Script.clash`: the
  Heretic's), no Minions dealt (the Kazali), the evil team kept apart at the start (the Poppy Grower), evil
  information skipping a Minion who believes they are good (the Marionette, played as the Drunk), result-flipping end
  hooks last (the Heretic), information roles answering players who gained them (the Pixie, the Cannibal).
- **The Carousel Script Collection's martianvampires** (Revenge of the Martian Vampires) plays end to end: 2,200
  random-bot games under each Storyteller mode, no crash. Of the collection's thirteen, it is the only one so far;
  haroldholt and the World Championship's warrens now need only the Amnesiac (batch 5). The four World Championship
  scripts of batch 1 still play.
- **The synthetic `carousel-3`** (the fifteen and all thirty-three jinxes) plays 2,200 games with no crash and has
  replay fingerprints.

**Built in batch 3** (docs/carousel-rulings.md, 65-81):
- **Thirteen experimental characters** in `clocktower/carousel3.py`: the Village Idiot, Acrobat, Lycanthrope,
  Alchemist, Zealot, Organ Grinder, Noble, Farmer, Harpy, Boffin, Boomdandy, Fearmonger and Xaan, with Storyteller's
  notes and the eighteen official jinxes between them and built characters. Lil' Monsta is not built: its Demon is a
  token, not a character (ruling 65, for the owner). Core changes, all no-ops elsewhere: several players with one
  character (the Village Idiot), an end-of-night hook (the Acrobat), a good player registering as evil (the
  Lycanthrope), a good ability a Demon has through the Boffin (whose sobriety counts), eyes-closed votes and a
  compelled hand (the Organ Grinder, the Zealot), a Demon's choice limited to one player (the Alchemist-Spy's guess),
  the Godfather and Assassin for a player who has the ability without the character (the Alchemist), the Assassin
  spent per player.
- **Two more corpus scripts play end to end**: the Carousel Script Collection's monkeydomath (Monkey Do Math) and the
  World Championship's seat7 (The Ballad of Seat 7), 2,200 random-bot games each under each Storyteller mode with no
  crash; the earlier ones still play. buyersremorse now needs only the Lleech, and 1daymore only Lil' Monsta.
- **The synthetic `carousel-4`** (the thirteen and all eighteen jinxes) plays 2,200 games with no crash and has
  replay fingerprints. The fuzzer draws the new characters, with oracles for the Noble and the Village Idiot and
  checks on the Faux Paw, the Farmer's heir, the Boffin's and Alchemist's picks and the Zealot's vote
  (docs/interaction-findings.md, the third runs).

**Built in batch 3b** (docs/carousel-rulings.md, 82-99):
- **Nine experimental characters** in `clocktower/carousel4.py`: the Alsaahir, Huntsman, Snitch, Knight, Choirboy,
  King, Cult Leader, Lord of Typhon and Lleech, with Storyteller's notes and the eight official jinxes between them and
  built characters (the Boffin's with the Cult Leader, pending since batch 3, among them). Core changes, all no-ops
  elsewhere: a Demon's extra Minions at setup (`Character.extra_minions`: the Lord of Typhon's +1, its line of evil
  seats made by moving the dealt tokens), the Slayer's shot at the Lleech's host, the Pit-Hag's lock on an evil Cult
  Leader, the Summoner's Lord of Typhon jinx and its substitute Demon when the one named cannot be in play. The Cult
  Leader's cult vote is a secret yes/no asked of every player (`decide`), not a change to the execution vote; the
  Alsaahir's guess uses the public `ability` move's `guesses`.
- **One more corpus script plays end to end**: the World Championship's buyersremorse (Buyer's Remorse), 2,200
  random-bot games under each Storyteller mode with no crash; the earlier ones still play. No Carousel Script
  Collection script is completed by this batch: whosecult (Who's Cult Is It Anyway) now needs only Lil' Monsta, and
  irrationalbehaviour, phantomdetectives, quickmaths, witchhunt and trainedkiller still need others.
- **The synthetic `carousel-5`** (the nine and all eight jinxes) plays 2,200 games with no crash and has replay
  fingerprints. The fuzzer draws the new characters, with oracles for the Knight, the King and the Choirboy and checks
  on the Alsaahir's and the cult's wins, the Lleech's life link and the Lord of Typhon's line
  (docs/interaction-findings.md, the fourth runs).

**Still open:**
- **The experimental characters** (16 more Townsfolk, Outsiders, Minions and Demons in the official data's carousel
  edition): later batches. Across both corpora the scripts need the Amnesiac (10) most; Lil' Monsta waits for the
  owner's design (ruling 65).
- **Jinxes** with experimental characters: each with its character. They take about eight forms (bans, setup
  changes, registration and visibility overrides, replacement abilities, alignment locks, kill rulings).
- **No Demon or several** (the Legion, the Riot, the Atheist): victory checks and evil's first-night information.
- **Speech-triggered abilities** (the Yaggababble's phrase, the Mezepheles' word): the judge reads speech.
- **Storyteller-invented content** (the Wizard's wish, the Amnesiac's ability): a model judge that generates, with
  code limiting it to effects the engine can carry out.
- **Vote mechanics** (negative, set by a Traveller: the Thief, the Bureaucrat, the Voudon; secret votes are built, the
  Organ Grinder's): the vote is a
  count of raised hands, each one vote unless an ability says more (the Banshee's two).
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
