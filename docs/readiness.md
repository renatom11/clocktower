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

**Built in batch 4** (docs/carousel-rulings.md, 100-119):
- **Eight experimental characters** in `clocktower/carousel5.py`: the Bounty Hunter, Engineer, Princess, Hermit, Ogre,
  Psychopath, Wraith and Vizier, with Storyteller's notes and the twenty official jinxes between them and built
  characters (the Alchemist's, Plague Doctor's and Magician's with the Wraith, the Boffin's with the Ogre, the Vizier's
  seven). Core changes, all no-ops elsewhere: an ability may execute the nominee once a vote is over
  (`Character.vote_over`: the Vizier's "execute immediately", which decides an execution and changes no vote), lines a
  setup step adds to a player's introduction (the Bounty Hunter's evil Townsfolk, the Vizier's name), and
  `characters.holds` so an Outsider's own code accepts the Hermit, who holds every Outsider ability on the script but
  the Drunk's, Lunatic's, Butler's and Puzzlemaster's. The Psychopath's kill uses the public `ability` move; its
  roshambo and the Wraith's eyes are a judged call and a `decide`.
- **One more corpus script plays end to end**: the Carousel Script Collection's contempt (Contempt), 2,200 random-bot
  games under each Storyteller mode with no crash; the earlier ones (martianvampires, monkeydomath and the six World
  Championship scripts) still play. No World Championship script is completed by this batch.
- **The synthetic `carousel-6`** (the eight and all twenty jinxes) plays 2,200 games with no crash and has replay
  fingerprints. The fuzzer draws the new characters, with an oracle for the Bounty Hunter and checks on its evil
  Townsfolk, the Vizier's day, the Psychopath's kill and nights whose Demon kills were stopped
  (docs/interaction-findings.md, the fifth runs: five engine faults found and fixed, B18-B22).

**Built in batch 5** (docs/carousel-rulings.md, 120-138):
- **The Mezepheles, Yaggababble and Amnesiac** in `clocktower/carousel6.py`, the three the brief first kept for a
  design with the owner, with Storyteller's notes and the one official jinx between them and a built character (the
  Yaggababble's with the Exorcist). Speech triggers: every word a player says, aloud or in a whisper, reaches the
  listening abilities on the script (`Character.listens`/`heard`, called from `Game.emit`), and a secret word or phrase
  is said when its words are said together as whole words, whatever the case or punctuation (`game.said`); a near miss
  is never counted by the scripted Storyteller and is a judge's call otherwise (the rules judge counts another form of
  the same word). The words and phrases come from a curated list of ordinary table talk
  (`data/storyteller/speech.json`); the Mezepheles hears whispers, the Yaggababble only what it says aloud. The random
  bots say the lists' lines on these scripts only, so the triggers fire in smoke games. The Amnesiac's ability is one
  of 31 the engine runs (`carousel6.AMNESIAC`: 24 built characters' abilities reworded, 7 small ones of its own),
  drawn at setup (a judge chooses among them, never inventing one); it guesses by visiting the Storyteller and is
  told hot, warm or cold. Core changes, all no-ops elsewhere: the speech hook and matching, the bots' chatter
  (`Request.chatter`), a night-order rule moving the Amnesiac's step before the Demons' (`Character.wakes_before`), a
  prompt sentence on listening abilities, the rules judge's near-miss heuristic.
- **Eight more corpus scripts play end to end**: the Carousel Script Collection's haroldholt, insanityintuition,
  onesyouleastexpect and punchy, and the World Championship's deadcouncil, phantomdetectives, riverstyx and warrens,
  2,200 random-bot games each under each Storyteller mode with no crash; the earlier ones still play. Seven of the
  collection's thirteen and ten of the sixteen World Championship scripts now play.
- **The synthetic `carousel-7`** (the three and the jinx) plays 2,200 games with no crash and has replay fingerprints.
  The fuzzer draws the new characters, checks the Mezepheles's first player and the Yaggababble's count against the
  events, and checks the Amnesiac's information by its model character's oracle (docs/interaction-findings.md, the
  sixth runs: one engine fault found and fixed, B23).

**Built in batch 6, removable by design** (docs/carousel-rulings.md, 139-175):
- **Lil' Monsta, the Atheist, the Wizard, Legion and Riot** in `clocktower/carousel_extra.py` (loaded last), each in a
  section of its own, one commit each, with its own tests (`tests/test_carousel_<id>.py`), Storyteller's notes
  (`data/storyteller/extra-<id>.md`), synthetic script (`carousel-8` to `carousel-12`, one character each, with
  replay fingerprints), rulings and fuzz findings, so that `git revert` of a character's commit removes it and leaves
  the others; each was checked that way (the revert of each, at the last commit, passes the full check). A scaffold
  commit before them holds the hooks two or more of them share (`Character.deals`: a character whose presence changes
  the whole deal; `Character.rule_text`: a prompt sentence for a rule it brings) and names none of them. Every core
  hook is a no-op on a script without its character; TB, BMR, S&V and `carousel-1` to `-7` replay identically.
- **Lil' Monsta**: a Demon token (`Player.carries`) the Minions pass between them each night, the babysitter being the
  Demon and keeping their own Minion ability; never dealt (a Minion in the Demon's seat); its seven jinxes.
- **The Atheist**: the closest reading the engine can run of a Storyteller who "can break the game rules": a fake evil
  team its information follows, night deaths as a Demon's, no Demon no win; anyone may nominate the Storyteller, whose
  execution is good's win with the Atheist in play and evil's without.
- **The Wizard**: one wish from a curated list of eight effects the engine runs, each with the prices it may have; the
  grant, price and clue are judged calls among listed values only (a judge chooses, never invents).
- **Legion**: a bare majority of the players share the one Demon character; executions fail when only evil voted;
  it registers as a Minion to the Investigator; its eight jinxes.
- **Riot**: the Minions become Riot on the third night, and day 3's nominations are a riot (each nominee executed at
  once, nominating the next); its twelve jinxes (the Atheist's only while the Atheist is built).
- **Every corpus script whose characters are all official now plays end to end**: all thirteen of the Carousel Script
  Collection, and thirteen of the sixteen World Championship scripts (beautifulhouse, stowedaway and witchhunt hold
  homebrew characters), 2,200 random-bot games each with no crash. The fuzzer: about 3,000 games per character (1,500
  forced into play); fourteen faults found in the new code and fixed (B24-B37), three interactions recorded for the
  owner (U14-U16).

**Still open:**
- **The experimental characters**: none left unbuilt in the official data's carousel edition. Batch 6's readings are
  for the owner to review: the Atheist's bounded rule-breaking (153), the Wizard's wish list (157), Legion's majority
  and registration (162, 166), Riot's text (the official data's, not the newer "after day 3, evil wins": 172), and
  U14-U16.
- **Jinxes** with experimental characters: each with its character. They take about eight forms (bans, setup
  changes, registration and visibility overrides, replacement abilities, alignment locks, kill rulings).
- **No Demon or several** (built in batch 6: Legion, Riot, the Atheist, Lil' Monsta): what remains is the owner's
  review of the readings.
- **Speech-triggered abilities** (built in batch 5): what remains is review of the word and phrase lists and of the
  whisper and near-miss rulings (122-124), and a model judge's near-miss calls in real play.
- **Storyteller-invented content**: the Wizard's wish and the Amnesiac's ability are drawn from curated lists (batches
  5 and 6); a model judge that generates new ones, with code limiting it to effects the engine can carry out, is not
  built.
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
