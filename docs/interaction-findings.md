# Interaction findings: what the fuzzer found

`clocktower/fuzz.py` plays random-bot games on random scripts drawn from every built character (today 122: the
Trouble Brewing, BMR and S&V characters and the experimental ones of carousel.py to carousel4.py; each script has
13 Townsfolk, 4 Outsiders, 4 Minions, 4 Demons, loaded as custom script JSON, so the night order and jinxes are the
official ones),
under the scripted Storyteller and the rules judge alternately, and checks invariants after every night step, every
turn of the day, and at each dawn and dusk. Its module docstring lists the checks; this file is what they turned up,
triaged, for review. Each entry: the characters, a repro (a one-line command that replays the game and prints the
violation; add `--events` for the audit trail), what happened, what the rules say, and a suggested ruling or fix.

How to rerun (about 80 games a second on four cores):

    python -m clocktower fuzz run --games 40000 --out /tmp/fuzz                     # uniform random scripts
    python -m clocktower fuzz run --games 10000 --target-uncovered --coverage /tmp/fuzz/coverage.json --out /tmp/f2
    python -m clocktower fuzz run --games 10000 --bias rare --coverage /tmp/f2/coverage.json --out /tmp/f3
    python -m clocktower fuzz matrix --out /tmp/matrix                              # character x mechanism
    python -m clocktower fuzz repro --seed ... --events                             # one game, from its repro line
    python -m clocktower fuzz cell --subject ... --mechanism ... --seed ...         # one matrix game

Each run writes `summary.md` (violations grouped, with a first example and its repro; advisories; pair coverage; the
information checked), `violations.jsonl` (every violation with its repro) and `coverage.json`.

## The fourth runs (2026-11-07, all 122 built characters: batch 3b added)

The pool now holds batch 3b's nine (carousel4.py). New checks: independent oracles for the Knight (two other
players, neither a Demon), the King (a character some living player can be, the King's own when nobody else lives)
and the Choirboy (the player shown is a Demon); a right guess by a working Alsaahir (every Minion and Demon, by type,
as the Grimoire has them) and a cult vote every good player joined with a working Cult Leader must win at once, and
neither win may be declared otherwise; a working Lleech never dies while its host lives (but to the Assassin) and
dies with it ('lleech'); the evil characters sit in a line with the Lord of Typhon in the middle ('setup'); the
Huntsman's Damsel becomes a Townsfolk not in play, the Cult Leader takes an alive neighbour's alignment, and the
summoned Lord of Typhon's neighbour a Minion not in play ('choice'). A death decided with others whose first one ends
the source's kept ability is not a dead player acting (U10).

10,000 games: 7,000 uniform (same seeds as before) and 3,000 `--target-uncovered`, plus 3,600 games with one of the
nine forced into play (`--force`, 400 each). A first pass found three engine faults in the new code, B15 to B17
below, all fixed, and one unruled interaction, U10. After the fixes: 6 violations in the uniform run (U8 x3, U1 x2,
U7) and 4 in the targeted one (U2 x2, U8, U1), all known; one in the forced runs (U1). All 7,381 pairs of the 122
characters were in play together but 4, and 7,342 with both acting, after the targeted run. Decisions checked in the
uniform run include the Knight's 591, the King's 307 and the Choirboy's 10 (each by its oracle too) and 1,155 Cult
Leader alignments.

## The third runs (2026-11-07, all 113 built characters: batch 3 added)

The pool now holds batch 3's thirteen (carousel3.py). New checks: independent oracles for the Noble (three other
players, exactly one able to register as evil) and the Village Idiot (the chosen player's alignment as it can
register); the Lycanthrope's Faux Paw registers as evil in every alignment oracle (a 'registers evil' state, only while
the Lycanthrope has their ability); Storyteller choices the texts fix: the Faux Paw is good, the Farmer's heir alive
and good, the Boffin's gift a good character not in play and never the Drunk, Heretic or Politician (the Village Idiot
in play only by its jinx), the Alchemist's Minion not in play (unless its jinx says so); a working Zealot votes for
every nomination with five or more alive; up to three living Village Idiots and any number of Farmers are coherent.
A Demon's ability through the Boffin is judged by the Boffin's sobriety.

10,000 games: 7,000 uniform (same seeds as before) and 3,000 `--target-uncovered`. A first pass (two 7,000-game runs)
found four engine faults, B11 to B14 below, and an oracle bug (the Faux Paw check shadowed a name, 610 crashes in
the fuzzer itself), all fixed. After the fixes: 7 violations in the uniform run (U1 x3, U2, U4, U7, U8) and 3 in the
targeted one (U7 x2, U1): nothing new but U9, which the scripted Storyteller now avoids. All 6,328 pairs of the 113
characters were in play together, and 6,325 with both acting, after the targeted run. Decisions checked in the
uniform run include the Noble's 800 and the Village Idiot's 807 (oracle 790 and 800), 622 Alchemist picks, 408
Boffin gifts and 216 Farmer heirs.

## The second runs (2026-11-07, all 100 built characters: TB, BMR, S&V and experimental batches 0-2)

The fuzzer now draws the experimental characters too (they register into `characters.CHARACTERS`), and checks more
of what they make structural (the module docstring): independent oracles for the Steward, Shugenja, Balloonist,
Nightwatchman, Pixie, Fisherman ("X is the Y" advice), High Priestess and General (only what the rules fix: their
answers are the Storyteller's belief), the Widow's knower and the Grandchild (good players), the once-per-game Golem
nomination and Damsel guesses, extra abilities only through an ability that gives them, the Marionette's seat, the
Kazali's Minions by the first dawn, and the Leviathan's and the Al-Hadikhia's public announcements. Forced setups
deal the Kazali (no Minions) and the Summoner (no Demon); a pair no setup can deal (the Kazali and a Minion, the
Summoner and a Demon) puts one in play and the other on the script. The oracles' misregistration is now what the
texts allow (the Spy as a Townsfolk or Outsider, the Recluse as a Minion or Demon), not anything.

Same seeds and sizes as the first runs: 40,000 uniform games, 10,000 `--target-uncovered`, 10,000 `--bias rare`,
and the matrix (5,200 games), about 15 minutes on four cores. A first pass found ten more engine faults, B5 to B10
below, all fixed; after the fixes (the counts below), nothing else but the unruled interactions:

| finding | violations in 60,000 games (40k / targeted / rare) | in the matrix |
|---|---|---|
| U1 Undertaker told the character after a change | 67 (52 / 6 / 9) | 16 |
| U2 a paused Vigormortis's Minions' effects stay (poison 8, madness 4, curse 3, protection 1) | 16 | 1 |
| U7 the Summoner summons a Demon already in play | 11 | 1 |
| U8 the Puzzlemaster's right guess with no Demon in play | 11 | 5 |
| U4 lone Washerwoman (crash) | 5 | 1 |
| U3 two living Shabaloths (the Scarlet Woman and the regurgitation) | 4 | 1 |
| U6 kept abilities outlive a dead Vigormortis | 2 | 1 |

That is 116 violations in 60,000 games (and 26 in the matrix), against 128 in the first 40,000-game pass before
B6-B10 (35 missed Al-Hadikhia announcements, 9 crashes). Still no loop or timeout, no false or missed win, no dead
player woken or informed, and no healthy player given information false by the engine's own test except U8. 16
percent of games reach the ten-day cap. Advisories: protection and a master outliving their source (A1, 1,564 and
602 in 40,000), the Vigormortis-Poisoner paradox (U2, 20), and 54 setups that cannot be dealt (A4).

**Information checked** (60,000 games): 331,000 decisions of 31 roles against the engine's own truth test, 271,000
of 25 roles against an independent oracle, and 13,700 Storyteller choices (the Widow's knower, the Grandchild).
Without an oracle of their own: the Chambermaid, Mathematician, Savant, Artist, Juggler and Puzzlemaster (whether the
guess was right is not in the choice).

**Pair coverage.** All 4,950 pairs of the 100 characters were in play together (fewest 15 games, median 597) and in
play with both acting (fewest 4, median 509; 29 pairs under 20, 176 under 50). The thin pairs are the Slayer's again
(Sage, Ravenkeeper, Heretic, Shabaloth, Moonchild, Vortox, Damsel and Klutz with the Slayer: 4 to 13), which acts
only when its shot kills the Demon. The targeted run raised the minimum both-acting count from 1 to 4 and cut the
pairs under 20 from 127 to 38; the rare-biased one, to 29. The rarest character is the Heretic (in 2,503 of the
60,000 games: its jinxes keep it from the Baron, Godfather, Pit-Hag, Spy and Widow).

## The first runs (2026-11-07, the 72 characters built then: TB, BMR, S&V)

60,000 random-script games (40,000 uniform, 10,000 `--target-uncovered`, 10,000 `--bias rare`; table sizes 5-15;
scripted Storyteller and rules judge alternating), about 25 minutes on four cores, plus the mechanism matrix (3,744
forced games, `docs/fuzz-matrix.md`). After the two fixes below (F1, F2), the violations, by finding:

| finding | violations | games affected, roughly |
|---|---|---|
| B2 Vortox: Chambermaid / Grandmother told the truth | 1,261 / 909 | 1 in 35 |
| B1 Scarlet Woman becomes a second Zombuul | 347 | 1 in 170 |
| B3 Drunk re-woken for a once-per-game ability (Philosopher, Courtier, Professor, Seamstress) | 121 / 119 / 43 / 40 | 1 in 190 |
| B4 Philosopher-Courtier / Philosopher-Professor choice ignored (and the real Professor's) | 74 / 12 / 3 | 1 in 670 |
| U1 Undertaker told the character after a change | 56 | 1 in 1,100 |
| U2 a paused Vigormortis's Minions' effects stay (plus 33 paradox advisories in 40,000) | 23 | 1 in 3,000 |
| U4 lone Washerwoman (crash) | 10 | 1 in 6,000 |
| U3 two living players with the same Demon | 4 | 1 in 15,000 |

No other crash, no loop or timeout, no false win, no missed win, no play after a win, no dead player woken or
informed, no healthy player given information false by the engine's own test, and no independent-oracle failure
except U1. Before F1 and F2, 5 games in a 4,000-game run crashed on them. 17 percent of games reach the ten-day cap
without a winner (random bots rarely execute well); that is play, not a fault.

**Information checked.** For a sober, healthy player with the ability and no Vortox falsifying it, every information
decision is checked against the engine's own truth test (the Choice's `truth`: 22 roles, about 240,000 decisions in
the 60,000 games), and the information of 17 roles against an independent oracle computed in fuzz.py from the
Grimoire (Washerwoman, Librarian, Investigator, Chef, Empath, Fortune Teller, Undertaker, Ravenkeeper, Clockmaker,
Dreamer, Seamstress, Oracle, Flowergirl, Town Crier, Sage, Grandmother, Godfather). Not independently checked: the
Chambermaid (who "woke" is the engine's own record), the Mathematician (its abnormal record), the Savant, the Artist,
the Gossip and the Juggler (statements), only by the engine's test where it has one.

**Pair coverage.** All 2,556 pairs of the 72 characters were in play together (fewest: 57 games, median 1,190), and
all were in play together with both acting (fewest: 12, median 990; 3 pairs under 20, 67 under 50). The thin pairs
all involve the Slayer, which counts as acting only when its shot kills the Demon (Ravenkeeper, Sage, Gossip and Klutz
with the Slayer: both need a death first). The targeted run raised the minimum from 1 to 10. Demon pairs are in play
together only through a Pit-Hag, Snake Charmer, Barber or Scarlet Woman change (there is one Demon at setup).

## Fixed in the core (fingerprint-safe: Trouble Brewing, BMR, S&V and carousel-1 replay identically)

F1. **A false or misregistered result names the Imp on scripts without it** (Undertaker, Ravenkeeper; the Recluse
registering as a Demon). `state.character_choice`'s false world showed the framed player as `'Imp'`, and
`Grimoire.evil_character` showed a Recluse as `'Imp'`; on a custom script without the Imp that value is not legal, and
the game stopped with "illegal Storyteller value for Undertaker:...". Seen with: Undertaker or Ravenkeeper, any
impairment, no Imp on the script; Recluse with Undertaker/Ravenkeeper. Repro (before the fix):
`python -m clocktower fuzz repro --seed 9001448 --players 7 --judge scripted --chars librarian,innkeeper,investigator,dreamer,pacifist,professor,towncrier,mathematician,sage,clockmaker,ravenkeeper,flowergirl,undertaker,sweetheart,goon,barber,tinker,assassin,devilsadvocate,godfather,scarletwoman,vigormortis,shabaloth,pukka,nodashii`.
Fix: `Grimoire.demon_shown()`: the Imp where the script has it (so Trouble Brewing draws and shows exactly as before),
else the Demon in play, else the script's first Demon.

F2. **`Grimoire.fake_good` with every character avoided** (an impaired Dreamer choosing the Spy, who may register as
every good character, so every good character is "correct" and avoided): `random.choices` on an empty list,
IndexError. Repro (before): `python -m clocktower fuzz repro --seed 9001475 --players 5 --judge rules --chars chambermaid,empath,dreamer,artist,investigator,fortuneteller,monk,slayer,professor,librarian,exorcist,innkeeper,undertaker,moonchild,barber,klutz,sweetheart,devilsadvocate,scarletwoman,baron,spy,vortox,zombuul,pukka,vigormortis`.
Fix: with nothing left, any character of the kinds asked (only reached where it used to crash). Rules: a drunk
Dreamer's two characters are arbitrary, so any is legal; the Dreamer's own legality check then applies.

## Engine bugs

B1 to B4 were found by the first runs and written up with suggested fixes; they are fixed now, as suggested
(commit 0ebe376; carousel-1 and carousel-2 fingerprints re-recorded). B5 to B10 were found by the second runs and
fixed at once (c6dd8f3, d700831); their tests are in tests/test_interactions.py. Each fix is unreachable on the base
scripts, whose fingerprints replay 1100/1100.

B1. **Fixed (0ebe376).** **The Scarlet Woman becomes the Demon when a Zombuul only seems to die.** Zombuul + Scarlet Woman. The Zombuul is
executed (or killed) for the first time; it lives on, registering as dead, but `ScarletWoman.on_death` sees "the
Demon died" and makes the Scarlet Woman a second, living Zombuul. Repro:
`python -m clocktower fuzz repro --seed 9000047 --players 15 --judge rules --chars mathematician,juggler,clockmaker,undertaker,sailor,philosopher,virgin,gossip,ravenkeeper,slayer,mayor,courtier,chef,lunatic,barber,klutz,tinker,scarletwoman,assassin,baron,cerenovus,fanggu,imp,zombuul,nodashii`
(day 2: Drew, the Zombuul, executed and "seems" dead; Indigo, the Scarlet Woman, becomes the Zombuul). Rules: the
Zombuul's first death does not kill it ("you live but register as dead"), and the Scarlet Woman acts when the Demon
dies; the almanac's Zombuul notes say the Storyteller treats the Zombuul as alive. Fix: in `ScarletWoman.on_death`,
also require `not dead.alive` (Game.kill calls the hooks for an apparent death too). Fingerprint-safe: no base script
has both. The most frequent violation (about 0.6% of games).

B2. **Fixed (0ebe376).** **The Vortox does not falsify the Chambermaid's or the Grandmother's information.** Vortox + Chambermaid or
Grandmother. `bmr.chambermaid_choice` and `bmr.grandmother_choice` decide impairment with `g.impaired` (drunk or
poisoned) rather than `g.unreliable` (which adds the Vortox), so their only legal value is the true one and
`Game.false_only` has nothing false to keep: a sober Chambermaid or Grandmother gets true information under the
Vortox. Repros: Chambermaid `python -m clocktower fuzz repro --seed 9000001 --players 13 --judge rules --chars empath,sailor,gambler,savant,chambermaid,ravenkeeper,clockmaker,philosopher,virgin,librarian,slayer,exorcist,mayor,saint,sweetheart,recluse,barber,scarletwoman,mastermind,baron,cerenovus,vortox,pukka,shabaloth,fanggu`;
Grandmother `python -m clocktower fuzz repro --seed 9000043 --players 8 --judge rules --chars seamstress,chambermaid,slayer,soldier,tealady,sailor,fortuneteller,dreamer,fool,artist,grandmother,virgin,innkeeper,saint,tinker,moonchild,recluse,assassin,spy,cerenovus,devilsadvocate,zombuul,vortox,vigormortis,imp`.
Rules: "Townsfolk abilities yield false info" covers every Townsfolk's information. Fix: `g.unreliable(cm,
'Chambermaid')` / `g.unreliable(gm, 'Grandmother')` in those two choices, and their misinformed styles keyed on it as
the S&V ones are. Fingerprint-safe (identical to `impaired` with no Vortox on the script). The Godfather's
information is a Minion's, so it stays as is.

B3. **Fixed (0ebe376; the Marionette believing one too).** **A Drunk who believes they have a once-per-game night ability is woken to use it again and again.** Drunk + one
of Courtier, Professor, Seamstress, Philosopher (the Drunk believing it). The "spent" marks are made only for the
player who really has the ability (`g.spend` in Courtier/Professor; `snv.use` in Seamstress/Philosopher only for
holders), so `night_spec` keeps waking the Drunk, who can "use" it every night. Repros: Courtier
`python -m clocktower fuzz repro --seed 9000775 --players 14 --judge rules --chars towncrier,courtier,pacifist,empath,fool,tealady,slayer,virgin,soldier,dreamer,innkeeper,sage,chef,drunk,barber,saint,lunatic,witch,spy,mastermind,scarletwoman,imp,zombuul,shabaloth,vigormortis`;
Philosopher `python -m clocktower fuzz repro --seed 9000066 --players 15 --judge scripted --chars snakecharmer,philosopher,mayor,sailor,savant,courtier,monk,empath,juggler,grandmother,slayer,soldier,librarian,sweetheart,drunk,mutant,saint,poisoner,godfather,eviltwin,assassin,vortox,pukka,fanggu,shabaloth`;
Seamstress `python -m clocktower fuzz repro --seed 9000186 --players 11 --judge scripted --chars ravenkeeper,fortuneteller,grandmother,seamstress,juggler,empath,philosopher,chef,librarian,undertaker,minstrel,courtier,mayor,butler,goon,drunk,klutz,scarletwoman,mastermind,pithag,cerenovus,po,pukka,vigormortis,fanggu`.
Rules: the Drunk is woken and treated exactly as the character they think they are, so a once-per-game ability is
spent for them too; being woken a second time also tells them they are not that character. Fix: mark the use per
player (`snv.use`) for every player woken at the step who chose, drunk or not, and have `night_spec` read it
(`snv.used`) for Courtier and Professor as Seamstress and Philosopher already do. Fingerprint-safe: neither BMR nor
S&V has the Drunk, and Trouble Brewing has none of the four.

B4. **Fixed (0ebe376).** **A Philosopher who gains the Courtier or the Professor: the choice does nothing, or blocks the real one.**
Philosopher + Courtier or Professor. `Courtier.resolve_night` reads only `g.with_character('Courtier')`, so a
Philosopher-Courtier's choice is ignored, never spent, and they are woken every night; `Professor.resolve_night` takes
`night.choice_of` (the first holder in seat order), so of a Philosopher-Professor and the real (now drunk) Professor
only the earlier seat's choice counts, and the other is woken again; both spend by character (`g.spend`), so one use
spends the other's. Repros: Courtier `python -m clocktower fuzz repro --seed 9001777 --players 14 --judge rules --chars philosopher,courtier,chambermaid,mathematician,mayor,gambler,dreamer,pacifist,minstrel,virgin,grandmother,monk,professor,barber,lunatic,moonchild,sweetheart,devilsadvocate,cerenovus,witch,eviltwin,vigormortis,pukka,vortox,fanggu`;
Professor `python -m clocktower fuzz repro --seed 9029276 --players 15 --judge scripted --chars flowergirl,juggler,sailor,philosopher,mayor,investigator,librarian,towncrier,courtier,clockmaker,professor,snakecharmer,savant,lunatic,klutz,goon,mutant,devilsadvocate,spy,mastermind,godfather,fanggu,zombuul,shabaloth,vigormortis`
(night 2: Morgan, the real Professor, chooses Kit; Indigo, the Philosopher-Professor in an earlier seat, chose no one,
so nothing happens and Morgan is woken again). Rules: the Philosopher gains the ability itself and uses it as that
character would; the in-play one is drunk (so its use does nothing, but is spent). Fix: iterate `snv.holders(g,
night, name)` as the S&V entries do, spending per player. The Assassin has the same `choice_of`/`spend` shape but is
evil (no Philosopher can gain it), so it is unaffected today. With the fix, a resurrected player's per-player use is
cleared too, as `Grimoire.revive` already cleared the per-character record.

B5. **Fixed (c6dd8f3; carousel-1 re-recorded).** **A drunk or poisoned Poisoner still poisons.** Poisoner + Courtier,
Innkeeper, Puzzlemaster (noticed by batch 2, docs/carousel-rulings.md 63). The Poisoner's step checked only the
Preacher's "no ability". Now an impaired Poisoner poisons no one (abnormal for the Mathematician), and its poison is
in force only while the Poisoner is sober and healthy (a new `State.while_source_sober`), since the Courtier and the
Innkeeper act after it in the night order and their drunkenness must stop tonight's poison. A Poisoner's poison on
themself stays unconditional (Trouble Brewing's case; the state would otherwise pause itself). The Widow's poison
pauses the same way.

B6. **Fixed (d700831; carousel-2 re-recorded).** **A win decided at night does not end the night.** Al-Hadikhia +
Mastermind (the jinx's last stand, at the Al-Hadikhia's step). Later steps went on waking players after the winner
was set (`continued-past-win`). `Game.night` now returns at once after a step that sets a winner. Repro (before):
`python -m clocktower fuzz repro --seed 9000483 --players 14 --judge rules --chars exorcist,banshee,general,minstrel,preacher,philosopher,gossip,investigator,seamstress,steward,tealady,balloonist,mathematician,moonchild,heretic,butler,politician,marionette,mastermind,widow,spy,fanggu,imp,ojo,alhadikhia`.

B7. **Fixed (d700831).** **The Al-Hadikhia's choice is not announced when its player has become another character.**
Al-Hadikhia + Hatter (a tea party after the Al-Hadikhia's step; also the Pit-Hag, the Barber). "All players learn
who" was the Al-Hadikhia's dawn `moment`, which runs only for a player with the ability. A new
`Character.moment_unheld` runs it with no holder. 35 games in 40,000 before. Repro (before):
`python -m clocktower fuzz repro --seed 9001138 --players 14 --judge scripted --chars snakecharmer,chef,monk,poppygrower,courtier,shugenja,innkeeper,mayor,empath,pixie,slayer,investigator,virgin,drunk,tinker,politician,hatter,mastermind,cerenovus,eviltwin,devilsadvocate,vortox,alhadikhia,zombuul,ojo`.

B8. **Fixed (d700831).** **A drunk information role with nothing true to show crashes.** A Marionette who believes
they are the Investigator and is the only Minion (also the Washerwoman's and Librarian's code path): a "truthful"
drunk draw found no true pair and offered "zero", which is not legal for the Investigator. Now such a player gets a
false pair. Repro (before): `python -m clocktower fuzz repro --seed 9027326 --players 5 --judge scripted --chars preacher,ravenkeeper,virgin,chambermaid,clockmaker,balloonist,poppygrower,fortuneteller,nightwatchman,investigator,professor,fool,monk,drunk,butler,golem,goon,eviltwin,assassin,marionette,witch,leviathan,vigormortis,fanggu,pukka`.

B9. **Fixed (d700831; carousel-3's one recorded crash now plays).** **An impaired Godfather with the Kazali's Outsider
count crashes.** The Kazali's "-? to +? Outsiders" can leave a count outside the setup modifiers' sizes, from which
an impaired Godfather's values were drawn; the true set was then not among them. It always is now (as the
Grandmother's, ruling 63). Repro (before): `python -m clocktower fuzz repro --seed 9016940 --players 11 --judge scripted --chars preacher,gambler,magician,virgin,tealady,oracle,sage,exorcist,shugenja,fisherman,slayer,ravenkeeper,poppygrower,heretic,plaguedoctor,butler,goon,devilsadvocate,assassin,godfather,witch,pukka,kazali,imp,ojo`.

B10. **Fixed (d700831).** **A Drunk with no Townsfolk to believe crashes.** Kazali + Drunk at 15 players: the Kazali's
"one fewer Outsider" turned the last free Townsfolk into play, and the Drunk's setup drew from nothing (IndexError).
The Kazali no longer offers one fewer when it would leave a Drunk nothing to believe, and `setup_error` rejects a
setup with the Drunk and every Townsfolk (a forced one: the fuzzer's own Kazali setups hit it). Repro (before):
`python -m clocktower fuzz repro --seed 9008676 --players 15 --judge scripted --chars pixie,seamstress,nightwatchman,investigator,librarian,virgin,exorcist,oracle,slayer,chambermaid,grandmother,ravenkeeper,highpriestess,mutant,damsel,tinker,drunk,poisoner,scarletwoman,goblin,godfather,ojo,alhadikhia,kazali,imp`.

B11. **Fixed (batch 3 commit).** **A setup step turns the Alchemist into another character.** Alchemist + Village Idiot
(or the Balloonist's or the Xaan's added Outsider): the Alchemist's step (setup order -1.5) had already acted, the
Summoner jinx's [No Demon] included, when the Village Idiot's extras took the Alchemist's player; with no Alchemist and
no Demon, nobody could summon and good did not win (`missed-win`). Repro (before): `python -m clocktower fuzz repro --seed 9004385 --players 6 --judge rules --chars snakecharmer,librarian,noble,nightwatchman,chef,sailor,villageidiot,investigator,alchemist,fortuneteller,preacher,shugenja,banshee,lunatic,plaguedoctor,golem,moonchild,devilsadvocate,witch,summoner,scarletwoman,imp,pukka,alhadikhia,vigormortis`.
Fix: those steps never take a Townsfolk whose setup step has run (setup order below -1: only the Alchemist).

B12. **Fixed (batch 3 commit).** **Two players with the Assassin's ability.** Alchemist-Assassin + an Assassin made
later (the Hatter's tea party): the Assassin was spent for the Grimoire as a whole and acted only for the first holder
in seat order, so the made Assassin's choice was ignored and they were woken again (`once-twice`). Repro (before):
`python -m clocktower fuzz repro --seed 9003532 --players 9 --judge scripted --chars innkeeper,alchemist,chef,monk,ravenkeeper,clockmaker,shugenja,exorcist,mayor,villageidiot,sage,philosopher,pacifist,puzzlemaster,hatter,heretic,mutant,cerenovus,scarletwoman,assassin,pithag,vigormortis,kazali,shabaloth,zombuul`.
Fix: each holder acts, and the ability is spent per player (as snv.use); with one Assassin it is the same, and BMR
replays identically.

B13. **Fixed (batch 3 commit).** **A dead player made the Lycanthrope places a Faux Paw.** Lycanthrope + Barber (a
swap onto a dead player): the new Lycanthrope chose a Faux Paw whose source was already dead (`coherence`). Repro
(before): `python -m clocktower fuzz repro --seed 9000584 --players 12 --judge scripted --chars banshee,soldier,professor,investigator,undertaker,grandmother,philosopher,dreamer,tealady,savant,lycanthrope,noble,innkeeper,barber,damsel,butler,lunatic,cerenovus,boffin,summoner,baron,nodashii,vigormortis,pukka,ojo`.
Fix: only a living Lycanthrope chooses one.

B14. **Fixed (batch 3 commit; found by the smoke run of carousel-4).** **An Alchemist-Summoner with only a Marionette.**
At 7 players with the Marionette the only Minion, the Summoner jinx's [No Demon] left no evil player at all (the
Marionette waits for the summoned Demon), and the Investigator had nothing true to show (crash). The Summoner is now
offered to the Alchemist only with an evil player other than the Demon and a Marionette (ruling 72).

B15. **Fixed (batch 3b commit; found by the targeted run).** **The King with nobody else alive.** The Lleech killed its
own host, the Spy, and died with it, leaving the King alone among the living; the King's choice had no true value, so
any character was offered and a healthy King was told "the Mutant is alive" (`engine-truth`, `oracle`). Repro (before):
`python -m clocktower fuzz repro --seed 9002193 --players 10 --judge rules --chars monk,grandmother,king,noble,professor,cultleader,magician,preacher,washerwoman,seamstress,tealady,nightwatchman,knight,saint,damsel,mutant,lunatic,scarletwoman,baron,poisoner,spy,lleech,pukka,nodashii,alhadikhia --setup lleech,monk,king,scarletwoman,nightwatchman,grandmother,washerwoman,magician,spy,tealady`.
Fix: with no other living player, the alive character is the King's own (ruling 86).

B16. **Fixed (batch 3b commit; found by pair coverage).** **The Summoner summons a Lleech with the Heretic in play.**
"Only 1 jinxed character can be in play" was kept at setup, by the Pit-Hag, the tea party and the Kazali, but not by
the Summoner, who could name the Lleech (the Heretic's only jinxed Demon); pair coverage showed the two in play
together once in 7,000 games. Fix: the Storyteller summons another Demon on the script instead (ruling 96; a no-op
on carousel-1 to carousel-4, whose Heretic has no jinxed Demon).

B17. **Fixed (batch 3b commit; found by the uniform run).** **The Lord of Typhon could leave a lone Washerwoman (U4).**
At five players its extra Minion leaves two Townsfolk; adding an Outsider ("-? to +?") left one, and a Washerwoman
alone had nothing true to show (the U4 crash). Repro (before): `python -m clocktower fuzz repro --seed 9000312 --players 5 --judge scripted --chars washerwoman,shugenja,innkeeper,grandmother,exorcist,highpriestess,undertaker,mayor,fortuneteller,soldier,cultleader,fool,poppygrower,barber,sweetheart,puzzlemaster,golem,boffin,godfather,scarletwoman,witch,alhadikhia,ojo,lleech,lordoftyphon`.
Fix: the Lord of Typhon's setup keeps two Townsfolk (ruling 92). U4 itself is unchanged.

## Unruled interactions (the engine does something defensible; a ruling would settle it)

U1. **The Undertaker learns the executed player's character after it changed.** Undertaker + Pit-Hag or Barber (also
the Scarlet Woman/Pit-Hag making the dead player a Demon; in the second runs also the Snake Charmer, the Hatter, the
Cerenovus's madness cell and the Barber's swap onto a dead Marionette or Widow: 67 in 60,000 games, the most frequent
violation now). The executed player dies as, say, the Washerwoman; that
night, before the Undertaker's step, the Pit-Hag makes the dead player the Goon (or the Barber's Demon swaps them);
the Undertaker is told "Goon". Repro: `python -m clocktower fuzz repro --seed 9000547 --players 8 --judge rules --chars chef,savant,slayer,fortuneteller,seamstress,empath,virgin,chambermaid,artist,soldier,clockmaker,undertaker,mathematician,barber,mutant,recluse,goon,poisoner,devilsadvocate,eviltwin,assassin,fanggu,imp,shabaloth,nodashii`.
About 1 game in 1,000 with both. Rules: the ability is "which character died by execution today", and the almanac's
Undertaker example (an executed Imp, the Scarlet Woman now the Imp: the Undertaker learns the Imp) reads it as the
character at death. Suggested ruling: the character they died as (`state.character_choice` would read a "died as"
record, which `Game.kill` could keep in the death log; Trouble Brewing has no character change of a dead player, so
TB play would not change). Option: the current character (what the engine does; some Storytellers rule this way for
the Pit-Hag).

U2. **A drunk or poisoned Vigormortis: its dead Minions' effects stay in force.** Vigormortis + Poisoner, Witch,
Cerenovus, Devil's Advocate or (second runs) Widow (killed by the Vigormortis, so keeping their ability). The second
runs report it as a state outliving its source, with the Vigormortis named as paused: 16 in 60,000 games. B5's
`while_source_sober` deliberately does not cover it (it pauses the Poisoner's poison on the Poisoner's own
drunkenness, not on its kept ability), so this ruling stays open. While the Vigormortis is drunk or
poisoned, its dead Minions have no ability (`Grimoire.keeps_ability` pauses: they are not woken, correctly), but the
poison, curse, madness or protection they placed earlier stays. Repro (Poisoner):
`python -m clocktower fuzz repro --seed 9006780 --players 10 --judge scripted --chars slayer,artist,exorcist,gossip,juggler,librarian,empath,tealady,innkeeper,minstrel,oracle,mathematician,chambermaid,lunatic,goon,barber,drunk,baron,godfather,cerenovus,poisoner,pukka,imp,nodashii,vigormortis`;
Witch: `python -m clocktower fuzz repro --seed 9002012 --players 15 --judge scripted --chars soldier,seamstress,sage,gambler,philosopher,mathematician,washerwoman,chef,slayer,snakecharmer,exorcist,sailor,undertaker,saint,klutz,goon,recluse,scarletwoman,witch,godfather,spy,imp,vigormortis,fanggu,shabaloth`.
Rules: a character whose ability stops working (drunk, poisoned, dead) stops its ongoing effects (a dead Poisoner's
poison ends, as the engine does). Suggested ruling: the effects pause with the ability (make the kept Minion's
`ends_with_source` states also `while_source_works`-style paused, i.e. `Grimoire.active` treats a dead source that
does not keep its ability now as not in force).
The extreme case is a paradox (an advisory, about 1 game in 1,200 with both): the dead Poisoner, kept by the
Vigormortis, poisons the Vigormortis, which takes away the Poisoner's ability, which would end the poison. The engine
keeps the poison (the state is not re-examined). Suggested ruling: as the Pukka's self-poison (S&V ruling), the poison
stands for its night and day, since it was placed while the ability worked.

U3. **Two living players with the same Demon.** Scarlet Woman + a reviving Demon (Shabaloth), or Pit-Hag + Scarlet
Woman (second runs: 4 in 60,000 games, all Shabaloths; the Summoner's duplicates are U7). The Shabaloth kills itself; the Scarlet Woman becomes the Shabaloth; the next night the new Shabaloth chooses
the dead old one, and the night after regurgitates them, still a Shabaloth. Two living Shabaloths. Repro:
`python -m clocktower fuzz repro --seed 9004517 --players 13 --judge rules --chars librarian,virgin,slayer,professor,empath,chambermaid,courtier,chef,oracle,innkeeper,seamstress,ravenkeeper,investigator,moonchild,drunk,recluse,sweetheart,godfather,witch,pithag,scarletwoman,shabaloth,vigormortis,imp,po`.
Similarly the Pit-Hag makes a good player the Vortox, the Storyteller kills the new Demon, the Scarlet Woman becomes
the Vortox, and the Shabaloth regurgitates the first: `python -m clocktower fuzz repro --seed 9002997 --players 15 --judge rules --chars mathematician,gambler,pacifist,clockmaker,flowergirl,artist,fortuneteller,professor,sage,grandmother,virgin,librarian,innkeeper,goon,recluse,lunatic,barber,scarletwoman,baron,devilsadvocate,pithag,imp,nodashii,vortox,shabaloth`.
Rules: the text allows it (the Shabaloth chose them), but no rule addresses a revived Demon whose character another
player now has; the regurgitated player is evil, which `POLICY['regurgitate_evil']` (0.1) already makes rare.
Suggested ruling: never regurgitate a player whose character is a Demon another living player has (or: they come back
as the character they died as, and the duplicate is accepted, as the engine does now); and the Scarlet Woman takes
over only when the last living Demon dies (with a second Demon alive, as in the Pit-Hag case, there is still a Demon:
the Fang Gu jinx's reasoning).

U4. **A lone Washerwoman: no other player registers as a Townsfolk.** Washerwoman + a setup with no other Townsfolk
(second runs: 5 in 60,000 games, at five or six players with the Baron, the Summoner's extra Townsfolk not
helping, and once after the Barber's swap; six players with the Baron; or every other Townsfolk position held by misregistering or changed characters). The
Washerwoman's choice has no legal value and the game stops ("illegal Storyteller value for Washerwoman"). Trouble
Brewing has it too: five of its 1,100 recorded fingerprints are this crash (six players, the Baron), so it is part
of frozen protocol v17. Repro: `python -m clocktower fuzz repro --seed 9002675 --players 6 --judge rules --chars mathematician,librarian,oracle,empath,investigator,savant,tealady,professor,sage,monk,fool,washerwoman,mayor,lunatic,drunk,sweetheart,recluse,witch,scarletwoman,assassin,baron,po,zombuul,imp,vigormortis`.
Rules: the ability always yields information; with no true answer the Storyteller must show something false
(common practice: one of the two is the Washerwoman themself, shown as a Townsfolk not in play, or a Townsfolk that
is not in play). Suggested ruling, for scripts other than Trouble Brewing (guarded by script id, so v17 stays as
recorded): when no pair is true, offer every pair with a Townsfolk not in play, as a misinformed result.

U5. **The Grandmother is shown a Grandchild who has turned evil.** Grandmother + Goon. The Grandchild is marked at
setup (a good player); a Goon chosen by an evil player on the first night turns evil before the Grandmother's step,
and she is shown them, now evil. Rules: "You start knowing a good player": the engine reads "good" as at setup.
Suggested ruling: keep (the Grandchild is chosen before the first night); the oracle accepts it.

U6. **The Barber's Demon swaps itself with a dead player: the Vigormortis's kept abilities follow the character to a
dead holder.** Barber + Vigormortis (matrix cell; second runs: 2 in 60,000 games and the Vigormortis x drunk cell,
`python -m clocktower fuzz cell --subject vigormortis --mechanism drunk --seed 10709002 --judge scripted`). The Barber dies; the Vigormortis swaps itself with a dead Juggler, so
the living player is now a Juggler and the dead one the Vigormortis. `Vigormortis.hand_over` moves the "keeps their
ability" states to the new Vigormortis, who is dead, so the Spy it killed keeps their ability through a dead Demon.
Repro: `python -m clocktower fuzz cell --subject vigormortis --mechanism barber --seed 10366000 --judge scripted`.
Rules: the Barber's Demon may choose themself and any other non-Demon player; a Demon moved onto a dead player is a
dead Demon (good wins at once unless another Demon lives). Suggested ruling: kept abilities end when the Vigormortis
character ends up dead (as when it dies), and the Storyteller should not choose such a swap (the almanac's "the Demon
may not choose another Demon" is the only stated limit).

U7. **The Summoner summons a Demon already in play.** Summoner + any Demon brought into play before the third night
(the Kazali making the Summoner, then the Summoner choosing the Kazali; the Pit-Hag making a Zombuul; the Scarlet
Woman's or a Courtier-jinx Storyteller summon). `Summoner` offers every Demon on the script, so the summoned player
can have the same character as a living Demon: two living Kazalis, Zombuuls, Leviathans, Shabaloths, No Dashiis or
Imps. 11 in 60,000 games. Repro: `python -m clocktower fuzz repro --seed 9202042 --players 12 --judge scripted --chars slayer,chef,courtier,grandmother,gossip,investigator,librarian,steward,nightwatchman,monk,fool,mayor,mathematician,mutant,damsel,plaguedoctor,drunk,cerenovus,devilsadvocate,summoner,spy,shabaloth,ojo,zombuul,kazali --setup courtier,nightwatchman,slayer,kazali,mutant,mathematician,investigator,steward,grandmother,plaguedoctor,damsel,drunk`
(night 1 the Kazali makes Casey the Summoner; night 3 Casey summons Kit into the Kazali). Rules: the text says "an
evil Demon of your choice", and the Kazali, Pit-Hag and Hatter jinxes speak of "a second living Demon" without
saying it must be a different one; the Pit-Hag's own text needs a character "not in play". Suggested ruling: only a
Demon not in play (as the Pit-Hag's), which removes the duplicate and keeps the jinxes' arbitrary deaths for a second,
different Demon. Option: allow it (the engine now), two players with one character.

U8. **The Puzzlemaster guesses right while no Demon is in play.** Puzzlemaster + Summoner (before the third night;
also after the Demon died and before a new one). "Learn who the Demon is": with no player registering as a Demon,
the engine offers every player and its own truth test calls each false (`engine-truth`, 11 in 60,000 games).
Repro: `python -m clocktower fuzz repro --seed 9100313 --players 10 --judge rules --chars poppygrower,snakecharmer,minstrel,sailor,slayer,shugenja,dreamer,flowergirl,seamstress,banshee,chef,grandmother,preacher,puzzlemaster,plaguedoctor,hatter,drunk,godfather,summoner,baron,goblin,leviathan,zombuul,alhadikhia,nodashii`
(day 2, the Summoner's game: Drew guesses his drunk right and is shown Blair, a Townsfolk). Suggested ruling: tell
them no player is the Demon (true, and the guess is spent); option: hold the guess until a Demon is in play.

U9. **The Noble with nothing true to show.** Noble + Lycanthrope at 5 players: two evil players and the Faux Paw leave
one good player among the Noble's four others, so no three hold exactly one evil player; the engine offered any three
and its truth test called them false (`engine-truth`, 2 in 7,000 games before the change). Repro: `python -m clocktower fuzz repro --seed 9006413 --players 5 --judge rules --chars towncrier,shugenja,pixie,nightwatchman,gossip,sailor,highpriestess,lycanthrope,magician,ravenkeeper,artist,noble,philosopher,goon,hatter,tinker,moonchild,harpy,widow,marionette,mastermind,vortox,pukka,shabaloth,leviathan`.
The scripted Storyteller (and the judge's default) now picks a Faux Paw that leaves the Noble a true answer when one
exists, but a judge may still choose otherwise, and a Recluse can do the same. Suggested ruling: the Storyteller must
not make the Noble's information impossible (the Faux Paw is theirs to choose). Option: show any three (the
almanac's habit for information with no true answer).

U10. **A Harpy kept by the Vigormortis kills the second player after the first was the Vigormortis.** Harpy +
Vigormortis (forced runs: 1 in 3,600 games). The Vigormortis killed the Harpy, who keeps her ability; the Harpy's
madness was broken and the Storyteller chose that both players die; the first was the Vigormortis, so the Harpy lost
her ability, and the second died anyway (the fuzzer called it a dead player acting). Repro: `python -m clocktower fuzz repro --seed 9102199 --players 12 --judge rules --chars huntsman,alsaahir,courtier,poppygrower,fortuneteller,savant,cultleader,fool,librarian,ravenkeeper,investigator,gambler,villageidiot,goon,plaguedoctor,golem,zealot,cerenovus,harpy,godfather,witch,zombuul,alhadikhia,lleech,vigormortis --setup harpy,cultleader,librarian,godfather,huntsman,fortuneteller,golem,fool,plaguedoctor,vigormortis,ravenkeeper,poppygrower`.
The engine takes the two deaths as one decision, made while the Harpy had her ability, which is defensible ("one or
both might die" is one penalty); stopping after the first would also change five recorded carousel-4 games, so it
is left as is, and the fuzzer now counts a death decided at the step that ended the source's kept ability as made
with it. Suggested ruling: keep it (both die together). Option: stop at the first death that ends the game or the
ability.

## Advisories (counted, not violations)

A1. **Protection and a Butler's master outlast their dead source until dusk.** Monk, Innkeeper, Devil's Advocate,
Butler, and a Philosopher with one of those abilities. The state lasts "until dusk" and is not ended when its source
dies (only the Poisoner's, the Courtier's and the Minstrel's are `ends_with_source`). It matters only when the source
dies earlier the same night than a later attack (the Monk killed by the Assassin or the Godfather after the Monk's
step, before the Demon's). Rules: a dead player's ability stops working; the almanac does not discuss a Monk who dies
mid-night. Suggested ruling: end them with their source (`ends_with_source=True` in Monk/Innkeeper/Devil's
Advocate). For the Monk in Trouble Brewing nothing would change in play (the Imp is the only night killer, and the
Monk only dies to it, after protecting), but the Grimoire text the Spy sees would ("protected by the Monk tonight"
gone after the Monk's death), so the TB fingerprints must be checked; Innkeeper and Devil's Advocate first.

A2. **A script that cannot be dealt gives a raw error.** Baron + Fang Gu (+2 and +1 Outsiders) on a script with four
Outsiders, at 13 to 15 players (two base Outsiders plus three is five). `state.random_setup` raises "Sample larger than
population or is negative". Rules: such a script is illegal at those sizes (the Storyteller would not put both in).
Suggested fix: check the Outsider count before sampling and raise a clear error naming the modifiers (ruling-style,
as the smoke brief asks for genuine impossibilities). The fuzzer counts these as advisories, not crashes.

A4. **The Heretic's jinxes leave some setups undealable.** Heretic + Baron on a script with four Outsiders, the Baron
forced as the game's Minion (the fuzzer rotates it), at 9, 12 and 15 players: the base two Outsiders plus the Baron's
two are all four, so the Heretic is always dealt with the Baron. `state.random_setup` raises its clear error ("no
setup for N players without two characters only one of which can be in play"), which the fuzzer counts as an
advisory (54 in 40,000 games). A genuine impossibility of that script and size.

A3. **The Pit-Hag's arbitrary deaths are credited to the Pit-Hag even when it has just made itself a Demon and died.**
Cosmetic (the death log's source); the fuzzer does not count it.

## What is checked, and where it is weak

**The mechanism matrix** (`docs/fuzz-matrix.md`, `python -m clocktower fuzz matrix`), second runs: each of the 100
characters against the 13 mechanisms, 1,300 cells, 1,293 with a legal setup (no setup holds the Heretic with the Spy
or the Pit-Hag, the Kazali with the Poisoner, the Spy, the Pit-Hag or the Cerenovus, or the Summoner with the
Professor and the Shabaloth); 1,268 with no violation, the other 25 only U1, U2, U3, U4, U6, U7 and U8. The
mechanism did not reach the character in 184 cells, by construction as before (alignment 74, Snake Charmer 54,
revival 28, Tea Lady 13, Barber 10, Monk 3, drunk 2). First runs: each of the 72 characters
against 13 mechanisms (drunk, poisoned, Spy/Recluse misregistration, Monk, Soldier, Tea Lady, Innkeeper, Pit-Hag,
Barber, Snake Charmer, alignment change, madness, revival), four forced games a cell, the mechanism's characters'
choices aimed at the character (`Directives`). 936 cells, 935 with a legal setup; 828 with no violation; the other
108 show only the findings above (mostly B2, which any cell with the Vortox on its random rest of script can show)
plus U6, found there. A cell also says what happened to the character (died, by what; became; revived; abnormal) and
in how many games the mechanism reached it. It did not reach it in 129 cells, mostly by construction (alignment
changes only reach a Snake Charmer's Demon or a Goon; the Professor revives only Townsfolk, so Minions and Demons are
not revived; the Tea Lady protects only when both neighbours are good), which are holes to fill with targeted
scenarios rather than findings. Each violation line there has its own repro (`fuzz cell ...`).

**Where the checks are weak.** The oracle allows a misregistering character (the Spy, the Recluse) to register as
anything its text allows, so it cannot catch a wrong misregistration within that; it does not judge Storyteller discretion (whether a value is a
good choice), only whether it is a possible one; "acted" is a coarse record (a choice made, information received, a
kill, a state placed); the once-per-game check sees uses through night choices, Slayer kills and the per-player use
record, the Golem's nomination and the Damsel guesses, not the Artist's or the Virgin's by effect; the High Priestess's
and the General's answers are the Storyteller's belief, so only their form is checked; and random bots never make the deliberate plays (a Slayer shooting
the Demon, a Gossip telling the truth) that some interactions need, so those pairs are thin.
