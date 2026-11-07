# Interaction findings: what the fuzzer found

`clocktower/fuzz.py` plays random-bot games on random scripts drawn from every built character (13 Townsfolk,
4 Outsiders, 4 Minions, 4 Demons, loaded as custom script JSON, so the night order and jinxes are the official ones),
under the scripted Storyteller and the rules judge alternately, and checks invariants after every night step, every
turn of the day, and at each dawn and dusk. Its module docstring lists the checks; this file is what they turned up,
triaged, for review. Each entry: the characters, a repro (a one-line command that replays the game and prints the
violation; add `--events` for the audit trail), what happened, what the rules say, and a suggested ruling or fix.

How to rerun (about 60 games a second on four cores):

    python -m clocktower fuzz run --games 40000 --out /tmp/fuzz                     # uniform random scripts
    python -m clocktower fuzz run --games 10000 --target-uncovered --coverage /tmp/fuzz/coverage.json --out /tmp/f2
    python -m clocktower fuzz run --games 10000 --bias rare --coverage /tmp/f2/coverage.json --out /tmp/f3
    python -m clocktower fuzz matrix --out /tmp/matrix                              # character x mechanism
    python -m clocktower fuzz repro --seed ... --events                             # one game, from its repro line
    python -m clocktower fuzz cell --subject ... --mechanism ... --seed ...         # one matrix game

Each run writes `summary.md` (violations grouped, with a first example and its repro; advisories; pair coverage; the
information checked), `violations.jsonl` (every violation with its repro) and `coverage.json`.

## The runs behind this file (2026-11-07, the 72 characters built then: TB, BMR, S&V)

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

## Engine bugs, written up (in character entries this branch must not touch: suggested fixes)

B1. **The Scarlet Woman becomes the Demon when a Zombuul only seems to die.** Zombuul + Scarlet Woman. The Zombuul is
executed (or killed) for the first time; it lives on, registering as dead, but `ScarletWoman.on_death` sees "the
Demon died" and makes the Scarlet Woman a second, living Zombuul. Repro:
`python -m clocktower fuzz repro --seed 9000047 --players 15 --judge rules --chars mathematician,juggler,clockmaker,undertaker,sailor,philosopher,virgin,gossip,ravenkeeper,slayer,mayor,courtier,chef,lunatic,barber,klutz,tinker,scarletwoman,assassin,baron,cerenovus,fanggu,imp,zombuul,nodashii`
(day 2: Drew, the Zombuul, executed and "seems" dead; Indigo, the Scarlet Woman, becomes the Zombuul). Rules: the
Zombuul's first death does not kill it ("you live but register as dead"), and the Scarlet Woman acts when the Demon
dies; the almanac's Zombuul notes say the Storyteller treats the Zombuul as alive. Fix: in `ScarletWoman.on_death`,
also require `not dead.alive` (Game.kill calls the hooks for an apparent death too). Fingerprint-safe: no base script
has both. The most frequent violation (about 0.6% of games).

B2. **The Vortox does not falsify the Chambermaid's or the Grandmother's information.** Vortox + Chambermaid or
Grandmother. `bmr.chambermaid_choice` and `bmr.grandmother_choice` decide impairment with `g.impaired` (drunk or
poisoned) rather than `g.unreliable` (which adds the Vortox), so their only legal value is the true one and
`Game.false_only` has nothing false to keep: a sober Chambermaid or Grandmother gets true information under the
Vortox. Repros: Chambermaid `python -m clocktower fuzz repro --seed 9000001 --players 13 --judge rules --chars empath,sailor,gambler,savant,chambermaid,ravenkeeper,clockmaker,philosopher,virgin,librarian,slayer,exorcist,mayor,saint,sweetheart,recluse,barber,scarletwoman,mastermind,baron,cerenovus,vortox,pukka,shabaloth,fanggu`;
Grandmother `python -m clocktower fuzz repro --seed 9000043 --players 8 --judge rules --chars seamstress,chambermaid,slayer,soldier,tealady,sailor,fortuneteller,dreamer,fool,artist,grandmother,virgin,innkeeper,saint,tinker,moonchild,recluse,assassin,spy,cerenovus,devilsadvocate,zombuul,vortox,vigormortis,imp`.
Rules: "Townsfolk abilities yield false info" covers every Townsfolk's information. Fix: `g.unreliable(cm,
'Chambermaid')` / `g.unreliable(gm, 'Grandmother')` in those two choices, and their misinformed styles keyed on it as
the S&V ones are. Fingerprint-safe (identical to `impaired` with no Vortox on the script). The Godfather's
information is a Minion's, so it stays as is.

B3. **A Drunk who believes they have a once-per-game night ability is woken to use it again and again.** Drunk + one
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

B4. **A Philosopher who gains the Courtier or the Professor: the choice does nothing, or blocks the real one.**
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
evil (no Philosopher can gain it), so it is unaffected today.

## Unruled interactions (the engine does something defensible; a ruling would settle it)

U1. **The Undertaker learns the executed player's character after it changed.** Undertaker + Pit-Hag or Barber (also
the Scarlet Woman/Pit-Hag making the dead player a Demon). The executed player dies as, say, the Washerwoman; that
night, before the Undertaker's step, the Pit-Hag makes the dead player the Goon (or the Barber's Demon swaps them);
the Undertaker is told "Goon". Repro: `python -m clocktower fuzz repro --seed 9000547 --players 8 --judge rules --chars chef,savant,slayer,fortuneteller,seamstress,empath,virgin,chambermaid,artist,soldier,clockmaker,undertaker,mathematician,barber,mutant,recluse,goon,poisoner,devilsadvocate,eviltwin,assassin,fanggu,imp,shabaloth,nodashii`.
About 1 game in 1,000 with both. Rules: the ability is "which character died by execution today", and the almanac's
Undertaker example (an executed Imp, the Scarlet Woman now the Imp: the Undertaker learns the Imp) reads it as the
character at death. Suggested ruling: the character they died as (`state.character_choice` would read a "died as"
record, which `Game.kill` could keep in the death log; Trouble Brewing has no character change of a dead player, so
TB play would not change). Option: the current character (what the engine does; some Storytellers rule this way for
the Pit-Hag).

U2. **A drunk or poisoned Vigormortis: its dead Minions' effects stay in force.** Vigormortis + Poisoner, Witch,
Cerenovus or Devil's Advocate (killed by the Vigormortis, so keeping their ability). While the Vigormortis is drunk or
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
Woman. The Shabaloth kills itself; the Scarlet Woman becomes the Shabaloth; the next night the new Shabaloth chooses
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
(six players with the Baron; or every other Townsfolk position held by misregistering or changed characters). The
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
dead holder.** Barber + Vigormortis (matrix cell). The Barber dies; the Vigormortis swaps itself with a dead Juggler, so
the living player is now a Juggler and the dead one the Vigormortis. `Vigormortis.hand_over` moves the "keeps their
ability" states to the new Vigormortis, who is dead, so the Spy it killed keeps their ability through a dead Demon.
Repro: `python -m clocktower fuzz cell --subject vigormortis --mechanism barber --seed 10366000 --judge scripted`.
Rules: the Barber's Demon may choose themself and any other non-Demon player; a Demon moved onto a dead player is a
dead Demon (good wins at once unless another Demon lives). Suggested ruling: kept abilities end when the Vigormortis
character ends up dead (as when it dies), and the Storyteller should not choose such a swap (the almanac's "the Demon
may not choose another Demon" is the only stated limit).

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

A3. **The Pit-Hag's arbitrary deaths are credited to the Pit-Hag even when it has just made itself a Demon and died.**
Cosmetic (the death log's source); the fuzzer does not count it.

## What is checked, and where it is weak

**The mechanism matrix** (`docs/fuzz-matrix.md`, `python -m clocktower fuzz matrix`): each of the 72 characters
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
anything, so it cannot catch a wrong misregistration; it does not judge Storyteller discretion (whether a value is a
good choice), only whether it is a possible one; "acted" is a coarse record (a choice made, information received, a
kill, a state placed); the once-per-game check sees uses through night choices, Slayer kills and the per-player use
record, not the Artist's or the Virgin's by effect; and random bots never make the deliberate plays (a Slayer shooting
the Demon, a Gossip telling the truth) that some interactions need, so those pairs are thin.
