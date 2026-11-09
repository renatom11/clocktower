# Implicit state machines: an audit

State in the engine that moves through phases or lifetimes without being modelled as such: where it is stored, what
moves it, the invariants it should keep, and the gaps (transitions missing or inconsistent). An audit of the code as of
branch `claude/great-thompson-4ej047` (after batch 6); no engine code, test or data was changed for it. The one code
change is a set of opt-in fuzzer checks (`python -m clocktower fuzz run --lifecycle`, clocktower/fuzz.py), whose
findings are S1 to S4 below.

Every gap has a scenario, its B or U item in docs/interaction-findings.md if there is one, whether it is reachable now
(and how that was checked: a scratch script against the engine, a fuzz repro, or reading only), a suggested fix, and
whether the fix would change the Trouble Brewing (TB), Bad Moon Rising (BMR) or Sects & Violets (S&V) fingerprints.
"Custom only" means the characters involved never meet on a base script, so the base fingerprints cannot change (the
carousel-N fingerprints may, and would be re-checked).

## Summary

| # | machine | where its state is stored | states | gaps | risk |
|---|---|---|---|---|---|
| M1 | once-per-game use | `Grimoire.spent` (by character), `notes['Used']` (by player), ad hoc marks (`notes['Golem nominated']`, `'Damsel guesses'`, `'Fang Gu once'`, `'Amnesiac fool'`...) | 2 per instance (fresh, spent), instances by player and character | G1, G2, G3, G4 | high |
| M2 | gained abilities | `Player.extra`, `notes['Boffin gift']`, `Player.carries`, the Amnesiac's `notes['Amnesiac']` | 3 (not held, held, held but dispatched only by own character) | G5, G6 | medium |
| M3 | effect lifetimes | `Grimoire.states` (`State.until`, `ends_with_source`, `while_source_works`, `while_source_sober`), `Grimoire.derived()` | 4 (in force, paused, expired, ended with source) | G7, G8, G9, G10 | high |
| M4 | life, death and the seeming dead | `Player.alive`, `seems_dead`, `ghost_vote`, `Grimoire.death_log`, `revivals` | 4 (alive, seems dead, dead, revived) | G11, G12 | high |
| M5 | registration | `Character.registers_*`, `'registers evil'` states, `Grimoire.decoys`, `truthful` | 3 per query (true, may misregister, forced) | G13, G14 | medium |
| M6 | character and alignment changes | `Game.changes`, `Grimoire.change_character` called directly, `Character.hand_over`, `becomes`, `changed` | 2 paths that should be 1 | G1, G8, G12 (and U1, U16) | high |
| M7 | the night | `Game.tonight` (`Night`), `Night.steps`, `g.last_choices`, `g.night_choices`, `g.woke` | per step: wake, pick, resolve, pending, win check; then end of night, dawn | none new | low |
| M8 | the day, nominations and votes | `Game.phase`, `executed_today`, `g.nominations`, `g.executions`, `block`/`top` (locals), `secret_votes()` | private, public, nominations (per round: nominate, defend, comment, vote), execution, dusk | G15 | medium |
| M9 | Demons with phases | Zombuul `spent` + `seems_dead`; Pukka states; Po `last_choices`; Shabaloth `night.before`; Lleech `notes['Lleech host']`; Lil' Monsta `notes[...]` + `carries`; Yaggababble counts; Summoner `notes['Summoned']`; Kazali, Legion, Riot | 2 to 4 each | G7, G8, G11, G1 | high |
| M10 | Minions and others with phases | Mezepheles, Atheist, Vizier, Fearmonger, Harpy, Cerenovus, Evil Twin, Vigormortis, Bounty Hunter, Farmer, Huntsman/Damsel, Engineer, Banshee, Golem | 2 to 3 each | G4, G16 | medium |
| M11 | seat and game lifecycle | `Table.status`, `Table.run`, `seat_map`, `Game.phase`, `checkpoint.pkl`, `STOP`, `result.json` | table: lobby, playing, paused, shutdown, over; game: setup, night, day, nominations, over/stopped | G17, G18, G19 | medium |
| M12 | requests and decisions | `Game.insist`/`REASKS`, `targets` (TB fill), the vote re-ask, `decide`/`decide_judged`, `SeatFailed` | asked, re-asked (up to 4), filled or failed; decided (auto, scripted, judged) | G20 | low |

Fuzzer findings with the new checks (10,000 games, `--lifecycle`): S1 the Pukka kills a player it never chose (12), S2
the Organ Grinder's secret tally shown (8), S3 a non-Zombuul who "seems dead" (7), S4 a stale once-per-game record (1).

## M1. Once-per-game use

**Stored:** three records that overlap.

- `Grimoire.spent`, a set of character names (`Grimoire.spend`, `spent_ability`): the Virgin, Slayer, Zombuul, Fool,
  Assassin, Courtier, Professor. The Spy sees it ("Spent once-per-game abilities").
- `notes['Used']`, player name -> list of abilities (`snv.use`/`used`/`fresh`): the S&V and experimental ones, and
  (since B3, B4, B12) the Assassin, Courtier and Professor too, beside `spent`.
- Ad hoc marks: `notes['Golem nominated']`, `'Damsel guesses'` (by Minion), `'Fang Gu once'` (global), `'Mastermind'`,
  `'Pacifist saves'`, `'Sweetheart'`, `'Banshee'`, `'Drunk shot:<name>'`, `'Drunk Virgin:<name>'`, `'Amnesiac fool'` and
  `'Amnesiac virgin'` (in `Used`), and the Fang Gu/Summoner/Riot flags of M9.

**States and transitions** (one machine per player-character instance, which is what the fuzzer's `epoch` counts):

```
fresh --use (even drunk or poisoned)--> spent
spent --revive (Grimoire.revive)------> fresh   (only p.character's entry, in both records)
any   --Game.changes to character c---> fresh   (spent.discard(c); Used only through c's own `becomes` -> fresh)
any   --Grimoire.change_character-----> unchanged (Scarlet Woman, Imp heir, make_marionette, setup steps)
```

**Invariants.** A new instance (a new character, a return to life) starts fresh, however it came about. One player's use
never spends another's. A use is recorded for whoever was woken and chose, drunk or not (B3). Both records agree.

**Gaps.**

- **G1. The direct `change_character` path skips the fresh start and the change hooks.** Scenario: Zombuul + Scarlet
  Woman. The Zombuul's first death only seems; its second is real and the Scarlet Woman becomes the Zombuul with
  `spent == {'Zombuul'}`: executed once, she dies for good. A Pit-Hag-made Zombuul starts fresh. Likewise the Scarlet
  Woman who becomes the Yaggababble gets no secret phrase (its `becomes` never runs), so she can never kill; and no
  `changed` hook runs (an Evil Twin, the Damsel's Spy record). Not a B/U item (B1 is the neighbouring Scarlet Woman/
  Zombuul fault, fixed). **Reachable**, custom scripts: verified by scratch script (Zombuul and Yaggababble). Fix: one
  change path. Minimal: `Grimoire.change_character` discards the new character from `spent` and clears it from
  `Used[p]`, and the two in-play callers (ScarletWoman.on_death, Imp.resolve_night's heir) run `becomes` and `changed`
  as Game.changes does, without its "you are now" message. TB: the Imp has no once-per-game record and neither hook, so
  unchanged; BMR and S&V have no Scarlet Woman. No base fingerprint changes.
- **G2. A revival restores only half the instance.** Scenario: a Philosopher gains the Courtier, uses it, dies, and the
  Professor revives them. `revive` clears `Used[p]` of 'Philosopher' only: they are woken to choose again (a second
  gained ability) while keeping the first, whose use stays spent. Not a B/U item (B4's note says revival clears the
  per-player use, for the character itself). **Reachable** (Philosopher + Professor or Shabaloth, custom scripts):
  verified by scratch script. Fix: a ruling on what a revived player holds (suggested: their character fresh, gained
  abilities kept as they are, and the Philosopher's own choice not offered again while `extra` is non-empty), done in
  `revive`. BMR revives only players whose records name their own character; S&V and TB revive nobody: unchanged.
- **G3. A record by character is shared by two holders.** Scenario: the Summoner summons a second Zombuul (U7): the
  first Zombuul's seeming death spends 'Zombuul' for both, so the second dies outright. The Fool (`spent_ability('Fool')`
  in the Pacifist's code too), the Virgin and the Slayer have the same shape. Part of U7; otherwise unreachable, since
  no other way puts two of these in play. Fix: per player for all of them (keep `spent` beside it for the Spy's view, as
  the Courtier does). TB/BMR unchanged while `spent` is kept as it is.
- **G4. Per-player records survive a change of character and back.** Scenario (fuzz, S4): the Hatter's tea party makes
  the Wizard the Baron, and a later one the Wizard again: still spent. The Huntsman, Engineer, Ogre, Puzzlemaster and
  Wizard have no `becomes` -> `fresh`; the Golem's, Banshee's, Damsel guesses', Lleech's 'lost' and the Fearmonger's
  marks are keyed by player and never cleared. Not a B/U item. **Reachable** (1 in 10,000 games). Fix: Game.changes
  clears `Used[p]` of the new character (as it discards `spent`), and the character-specific `becomes` -> `fresh` go;
  the ad hoc marks move into `Used`. S&V's once-per-game characters all have `becomes` -> `fresh` already: unchanged.

## M2. Gained abilities

**Stored:** `Player.extra` (Philosopher, Cannibal, Pixie, Alchemist's Minion, Hermit's Outsiders, Plague Doctor's Spy,
batch 6's babysitter), `notes['Boffin gift']` (the Demon's, through `Grimoire.gift`), `Player.carries` (Lil' Monsta),
the Amnesiac's gift in `notes['Amnesiac'][p]` (its own character's hooks).

**States:** not held; held (woken at that step: Game.wake's `abilities(p)[1:]`; informed: InfoRole; acting through
hooks dispatched over `g.abilities(p)`: `on_death`, `moment`, `nomination`, `execution`, `end_of_day`, `changed`,
`end_of_night`, `vote_over`, `secret_votes`); held but inert: hooks asked only of `rules(p.character)`.

**Transitions:** gained (a 'gains' event); lost on a change of character (`change_character` empties `extra`; ruling
S&V 37); kept on death; kept on revival (G2); not moved by a seat swap (U16).

**Invariants.** An ability gained acts as its character's would (the almanac: the Philosopher "gains that ability"), and
its in-play original is drunk while the gainer has their own ability. It goes when its source character goes.

**Gaps.**

- **G5. Hooks asked only of the player's own character.** `Game.prevent_death` (`survives`), `Grimoire.safe` (`safe_from`,
  `protects` of `q.character`), `Game.attempt_kill_judged` (`redirect_attack`), `Game.kill` (`dies`), `Game.execute`
  (`executed`), `Game.virgin_judged` (`nominated`), the registration questions and `check_victory` (`overrides_end`), plus
  explicit `character ==` tests in the Slayer's shot and `shown ==` in the Ravenkeeper's step. Scenario: a Philosopher
  gains the Soldier and the Demon kills them; a Cannibal gains the Virgin and nobody is executed. Known engine limit,
  carousel ruling 47 (not a B/U item). **Reachable**; the new advisory counts the gains in 10,000 games: Virgin 29,
  Sailor 28, Tea Lady 26, Mayor 26, Soldier 24, Recluse 18, Fool 15, Spy 12, Saint 7 (the Summoner, Engineer, Atheist,
  Alchemist, Plague Doctor, Amnesiac, Hermit and Drunk entries are mostly hooks of no use to a gainer). Fix: dispatch
  these hooks over `g.abilities(p)` with each entry's own `works` test (the Hermit's `held` already does it by hand).
  TB and BMR gain nothing; S&V's Philosopher can gain none of these on S&V: unchanged.
- **G6. A seat swap at setup keeps gained abilities on the seat** (the Marionette's swap beside the Demon, after the
  Alchemist's step). U16. Reachable (1 in 1,500 there). Fix as U16: move `extra` with the character. Custom only.

## M3. Effect lifetimes

**Stored:** `Grimoire.states` (`State(kind, target, source, until, ends_with_source, while_source_works,
while_source_sober, against, about)`), plus states worked out on demand (`Character.ongoing`: the No Dashii's, the
Vigormortis's, the Philosopher's drunk original, the Damsel's Spy jinx) and notes some abilities keep beside them
(`'Lleech host'`, `'Vigormortis'`).

**States and transitions:**

```
placed --dusk (expire 'night' / a night number) / dawn ('dawn')--> expired
placed --source dies (unless kept) or changes character, if ends_with_source (_source_lost)--> ended
placed --source drunk or poisoned (while_source_sober / while_source_works), or dead (works)--> paused <--> in force
placed --swap, if the character's hand_over takes it (Vigormortis, Lleech only)--> moved to the new source
```

**Invariants.** A state names the ability that made it, and only that ability reads or ends it; a state that lasts
while its source has its ability ends or pauses whenever that ability stops, whatever stops it (death, change, drunk,
poisoned, a kept ability lost); a swap moves what belongs to the character, not the player.

**Gaps.**

- **G7. States carry their source player, not their ability** (S1). The Pukka finds its pending victim as "a poisoned
  state from the Pukka's player lasting until None". Scenario: the Snake Charmer charms the Pukka: the old Pukka (now
  the Snake Charmer) gets the charm's permanent poison, with the new Pukka as its source. At its step the new Pukka takes
  that poison for its own: it kills the old Pukka at once and the charm's poison is gone; the old Pukka's real victim
  is healthy (its poison ended with its source). Not a B/U item. **Reachable**: scratch script, and the new
  `lifecycle-pukka` check, 12 in 10,000 games (repro: `python -m clocktower fuzz repro --seed 9000177 --players 13
  --judge rules --chars ravenkeeper,chef,artist,snakecharmer,pacifist,choirboy,washerwoman,huntsman,empath,mathematician,philosopher,amnesiac,juggler,drunk,golem,heretic,sweetheart,mezepheles,witch,mastermind,spy,fanggu,pukka,shabaloth,vortox
  --lifecycle`). Fix: a `State.ability` field (default None) set where states are made, and the Pukka (and any reader)
  selects by it. BMR's Pukka is the only until-None poisoner there: unchanged.
- **G8. A swap does not move what a Demon keeps by player** (part of S1). Only the Vigormortis and the Lleech have
  `hand_over`. Scenarios: the Snake Charmer charms a charged Po (it chose no one last night): the new Po is woken for one
  kill, not three (`g.last_choices` is the player's); the Pukka's victim of G7; the Shabaloth's regurgitation reads
  `night.before[player]`; the Yaggababble's count for today is the old player's (and `becomes` draws a new phrase).
  Not a B/U item. **Reachable** (Po and Pukka verified by scratch script; Snake Charmer or Barber with these Demons,
  custom scripts). Fix: `hand_over` for the Po, Pukka, Shabaloth and Yaggababble, or (better) key their bookkeeping by
  the character instance. Custom only.
- **G9. Protections and a master outlive their dead source until dusk.** A1 (an advisory: 1,564 and 602 in 40,000).
  Reachable. Fix as A1 (`ends_with_source` for the Innkeeper and Devil's Advocate first; the Monk last, since the Spy's
  Grimoire text would change in TB).
- **G10. A kept ability's effects are not paused with it.** U2 (a drunk Vigormortis), U6 (kept abilities through a dead
  Vigormortis), U10 (the Harpy's second death). The ends of `ends_with_source` states are evaluated only when the source
  dies or changes, never when `keeps_ability` turns false. Reachable (16 in 60,000). Fix as U2: `Grimoire.active` treats a
  dead source without a kept ability as not in force. Custom only.

## M4. Life, death and the seeming dead

**Stored:** `Player.alive`, `seems_dead`, `ghost_vote`; `Grimoire.death_log` (with `seems`), `revivals`,
`executed_death`, `executions`.

**States:** alive; alive but seems dead (the Zombuul's first death; the Summoner/Zombuul jinx); dead; alive again.

```
alive --kill, dies() == 'seems'--> seems dead --execution or unstoppable kill--> dead
alive --kill--> dead --revive--> alive (seems_dead cleared, ghost vote back)
seems dead --change of character / swap--> (unchanged: the flag stays on the player)
```

**Invariants.** Only a character that can seem dead (its `dies` can say 'seems') leaves a living player registering as
dead; the town's view (`appears_alive`) and the night's targets agree with it; what the dead learn is about the
character they died as.

**Gaps.**

- **G11. `seems_dead` belongs to the player, not the Zombuul** (S3). Scenario: the Barber dies and the Zombuul, seeming
  dead, swaps itself with a Townsfolk: the old player, now a Townsfolk, stays alive but "dead" for good, cannot
  nominate and cannot be killed at night (`attempt_kill_judged` skips the seeming dead), only executed; the new Zombuul
  starts with a fresh first death. The Pit-Hag, the Hatter and the Engineer do the same by changing the seeming-dead
  Zombuul into another Demon (Ojo, Po, Pukka, No Dashii, Fang Gu seen) or a Village Idiot. Not a B/U item.
  **Reachable**: scratch script, and `lifecycle-seems-dead`, 7 in 10,000 games (repro: `python -m clocktower fuzz repro
  --seed 9002171 --players 9 --judge rules --chars shugenja,soldier,monk,dreamer,librarian,fool,king,professor,noble,exorcist,fortuneteller,bountyhunter,ravenkeeper,hatter,plaguedoctor,butler,mutant,xaan,baron,mezepheles,scarletwoman,fanggu,zombuul,pukka,ojo
  --lifecycle`). Fix: a ruling (suggested: the seeming death is the Zombuul's; a player who stops being the Zombuul while
  seeming dead is dead, as the town believes, and a swap hands the "died once" mark to the new Zombuul through
  `hand_over`), in `change_character`. BMR's Zombuul never changes character: unchanged.
- **G12. The dead's character is read now, not as they died.** U1 (the Undertaker after a change; the most frequent
  violation, 10 in these 10,000 games too). Reachable. Fix as U1: a "died as" record in the death log. TB unchanged.

## M5. Registration

**Stored:** computed per query (`registers_evil`, `registers_as`, `registers_demon_to_ft`), a `'registers evil'` state
(the Faux Paw), the Hermit's held Outsiders, `Grimoire.decoys` (an impaired player's false world, fixed when first drawn)
and `truthful` (the Drunk's, once a game).

**Invariants.** A misregistering ability works only while it works: dead (where the text says so) yes, drunk or
poisoned no; a false world stays consistent but follows what is true of the world it frames.

**Gaps.**

- **G13. A drunk Spy or Recluse still misregisters.** The Spy's and Recluse's `registers_*`, `false_evil` and
  `sample_evil` test `is_poisoned`, not `impaired`. Scenario: the Sailor (or Innkeeper, Philosopher, Sweetheart, Minstrel)
  makes the Recluse drunk; the Empath beside them may still be shown them as evil. Not a B/U item (the same pattern as
  B2: the wrong sobriety predicate). **Reachable** on custom scripts: verified by scratch script. Fix: `impaired`. TB has
  no drunkenness from an ability (the Drunk is its own character), and BMR and S&V have no Spy or Recluse: unchanged.
- **G14. A false world is fixed for the game while alignments change.** `Grimoire.decoy` frames a good player once; after
  a Goon, Snake Charmer, Mezepheles or Cult Leader turns them evil, the "false" world can be the true one. Not a B/U
  item. Reachable by reading only (not verified). Fix: redraw the decoy when its framed player turns evil. TB has no
  alignment changes but the Goon's (not on TB): unchanged.

## M6. Character and alignment changes

**Stored:** nothing of its own: the change paths.

| path | callers | discards `spent` | `becomes` / `changed` | `hand_over` | told |
|---|---|---|---|---|---|
| `Game.changes` | Pit-Hag, Barber, Snake Charmer, Fang Gu, Huntsman, Engineer, Summoner, Hatter, Farmer... | yes | yes | yes (swaps) | yes |
| `Grimoire.change_character` alone | Scarlet Woman, Imp heir, make_marionette, setup steps | no | no (make_marionette: `changed` only) | no | own notice |
| `setattr` swap | the Marionette's seat at setup | no | no | no (`extra` stays: U16) | no |

**Invariants.** Every change ends the old character's ongoing effects, starts the new one fresh, runs its `becomes` and
everyone's `changed`, moves what belongs to a character in a swap, and leaves the per-player flags of the old character
(`seems_dead`, `Used`, ad hoc marks) consistent with the new one.

**Gaps:** G1 (the second path), G8 (hand_over for two characters only), G11 (`seems_dead`), and U1, U16. The setup-time
uses are before anyone acts, so harmless.

## M7. The night

**Stored:** `Game.tonight` (a `Night`: `chosen`, `characters`, `deaths`, `revived`, `before`, `asleep`), `Game.phase`
('night'), the night order (`Night.steps`: batches for TB, one character a step elsewhere), `g.last_choices`,
`g.night_choices`, `g.woke`, `notes['Demon kills stopped']`.

**States:** dusk (expire 'night' states) -> for each step: wake, picks (`chosen` hooks), resolve, pending abilities,
Storyteller-held abilities, win check -> end of night (`end_of_night`) -> dawn (expire 'dawn', deaths announced in seat
order, `moment('dawn')`).

**Invariants.** Nobody wakes after a win (B6); nobody killed earlier tonight is woken (TB batches end at each killing
step); a choice made at one step is read only by its own step (B21, B23); deaths are announced at dawn, never in kill
order.

**Gaps:** none new. The opt-in `lifecycle-checkpoint` check (nothing pending and no night in progress at a dusk, which
is when the game checkpoints) held in all 10,000 games.

## M8. The day, nominations and votes

**Stored:** `Game.phase` ('day', 'nominations'; batch 6's Riot sets it itself), `executed_today`, `g.nominations`,
`g.executions`, the locals `block`/`top` of `Game.nominations`, `secret_votes()` (asked anew each round),
`notes['Mastermind']` (the extra day), `notes['Riot done']`, the Vizier's `vote_over`, madness executions
(`Game.judge_madness`, which end the day before nominations), the Psychopath's, Cult Leader's and Alsaahir's day wins.

**States:** private beats -> public beats -> `moment('nominations')` (madness, the Psychopath) -> nominations (rounds:
nominate, the nominee's reaction, everyone's `nomination`, defence, comments, vote, `vote_over`) -> execution or none
-> `end_of_day` -> `moment('dusk')`.

**Invariants.** One execution a day; a regime that covers the day (secret votes, the Banshee's double vote, the
Zealot's) covers every vote of it consistently; what a regime hides stays hidden.

**Gaps.**

- **G15. The Organ Grinder's secret votes are decided anew each round** (S2). Scenario: the Witch curses the Organ
  Grinder, who nominates after a secret vote has put someone on the block; the curse kills them, votes turn public, and
  the next prompts say "Casey is on the block with 7 votes" and "(replacing Casey, who has 7)": the secret tally is
  out. Not a B/U item. **Reachable**: scratch script, and `lifecycle-secret-vote`, 8 in 10,000 games (repro: `python -m
  clocktower fuzz repro --seed 9004448 --players 10 --judge scripted --chars shugenja,alchemist,investigator,artist,empath,courtier,king,preacher,oracle,soldier,fisherman,chef,nightwatchman,klutz,lunatic,moonchild,heretic,organgrinder,witch,boffin,harpy,pukka,vigormortis,fanggu,lordoftyphon
  --lifecycle`). Fix: once a vote today was secret, prompts never show the block or a tally (a ruling whether later votes
  stay secret). Custom only.

## M9. Demons with phases

| Demon | stored | states and moves | gaps |
|---|---|---|---|
| Zombuul | `spent` 'Zombuul' (by character), `seems_dead` (by player) | fresh -> seems dead (first death, working) -> dead; woken only after a day with no death | G1, G3, G11 |
| Pukka | poisoned States (source = player, until None, paused while drunk) | choose -> victim poisoned -> next choice: victim dies, healthy; an Exorcist's night keeps it waiting | G7, G8 |
| Shabaloth | `night.before` (player's last picks), `g.woke`, `revivals` (budget) | chose -> dead -> maybe regurgitated next night | G8, U3 |
| Po | `g.last_choices[player] == []` | normal -> charged (chose no one) -> three kills | G8 |
| Lleech | `notes['Lleech host'][player]`, host poison, `notes['Lleech lost']` | no host -> host (night 1, or its first night as a made Lleech) -> dies with the host; lost (the Mastermind jinx) | `hand_over` exists (B19); 'Lleech lost' not cleared (G4 shape) |
| Lil' Monsta | `notes["Lil' Monsta"]` (babysitter, as, dead, fixed), `Player.carries` | unheld -> babysat each night by a Minion -> dead with its babysitter | U14 (a made Lil' Monsta needing a free Minion: also 2 in these 10,000 games) |
| Yaggababble | `notes['Yaggababble'][player]` (`secret`, `count` by day) | phrase drawn at setup or `becomes` -> said publicly (count) -> kills that night | G1 (none for a Scarlet Woman's), G8 (a swap's count) |
| Summoner | `notes['Summoned']` (absent, a night number, 'failed'), `notes['Storyteller abilities']` | waiting -> summoned (night 2 Pukka jinx, night 3) or failed; holds good's win while waiting | U7, B22 |
| Kazali | Minions chosen on night 1 (`change` of good players) | none dealt -> chosen by dawn 1 | the fuzzer's count check, 4 in 10,000, not triaged here (the Riot runs saw one from an Engineer-made Legion) |
| Legion, Riot | batch 6 notes (`'Riot chose'`, `'Riot done'`, `RIOT_DAY`) | Riot: Minions become Riot on night 3, day 3's riot once | none new |

## M10. Minions and other characters with phases

| character | stored | states and moves | gaps |
|---|---|---|---|
| Mezepheles | `notes['Mezepheles'][player]` (`secret`, `first`, `done`) | word drawn -> first good speaker recorded -> turned that night, ability gone | none new (a swap draws a new word: a reading) |
| Atheist | `notes['Storyteller lies']`, the deal's `overrides_end` | for the game, whoever holds it (ruling 152) | none |
| Vizier | `notes['Vizier told']`, `vote_over`, `survives` by day | public at setup; executes at once when good voted | none new |
| Fearmonger | `notes['Fear'][player]` | chosen player kept until a new one (announced) | G4 shape (kept across a change and back) |
| Harpy, Cerenovus | 'mad' States (until dusk, `while_source_works`), judged at `moment('nominations')` | mad tomorrow -> judged -> maybe executed | U10 |
| Evil Twin | `notes['Twins'][player]` | paired at setup or `becomes` -> re-paired when both share an alignment (`changed`) | G1 (no `changed` from the Scarlet Woman's path) |
| Vigormortis | 'has ability' States, `notes['Vigormortis']`, derived poison | kept while the Vigormortis works -> paused -> lost | U2, U6, U10 (G10) |
| Bounty Hunter | `notes['Evil Townsfolk']`, `'Bounty Hunter'` | evil Townsfolk made at setup (B18) -> shown players | none new |
| Farmer | `change` at night death | a living good player becomes a Farmer | none |
| Huntsman / Damsel | `Used` (Huntsman), `notes['Damsel guesses']`, `'Spy in play'` | one choice; Damsel -> a Townsfolk not in play | G4 shape |
| Engineer | `Used` | one choice -> the Demon or the Minions become the chosen | G4 (no `fresh`); U14 through Lil' Monsta |
| Banshee, Golem | `notes['Banshee']`, `'Golem nominated'` (by player) | killed by the Demon -> two votes and nominations; one nomination | G4 shape |

**Gaps.** G16: per-player marks of a character not tied to holding it (the G4 family; low risk, since only a player
who becomes the same character twice meets it).

## M11. Seat and game lifecycle

**Stored:** `Table.status` (lobby, playing, paused, shutdown, over), `Table.run`, `seat_map`, `dealt`, `ended`,
`final`; the game's folder (`checkpoint.pkl`, `STOP`, `result.json`, logs); `Game.phase` (setup, night, day,
nominations), `starting`, `start_teams`.

```
lobby --start--> playing --STOP / end--> halted (checkpoint kept) --> over (shown as ended)
playing --Hub.shutdown--> shutdown (saved as playing) --Hub.restore--> playing (run + 1; own key: paused)
playing --winner or day cap--> over (checkpoint deleted)
playing --SeatFailed / budget--> over (checkpoint kept; the CLI resumes it, the web does not)
game: setup --> checkpoint at each dusk (night n) --> night n --> day n --> ...
```

**Invariants.** Everything play depends on is in the checkpoint, or is rebuilt from it the same way; a resumed game is
the game it was; a reader never sees a half-restored game; the team's model follows the seat as dealt
(`start_teams`).

**Gaps.**

- **G17. Seat state lives outside the checkpoint.** The random bots' generators (`RandomSeat.rng`, seeded when the game
  is built, so a resume restarts them), and the web's seat assignment (`Table.humans`: `assign(..., random.Random())`,
  unseeded) are not checkpointed or seeded. A resumed game is not the game an uninterrupted run would play, and two runs
  of one web game differ. Model seats are restored (their conversations). Not a B/U item. Reachable on every resume.
  Fix: save the seats' generator states in the checkpoint; seed the assignment from the game's seed. No fingerprint
  changes (fingerprints are uninterrupted games).
- **G18. `Game.restore` publishes a half-restored game.** It sets `g` before `events`, `starting` and the seats, while
  the web thread reads `table.game` (PersistenceTest waits for `game.g is not None`). Not a B/U item. A race, not
  observed. Fix: build everything, then set `g` last.
- **G19. The PersistenceTest flake.** Its two failures in 24 runs here (none in 52 more of an instrumented copy) were both `self.assertIn(t2.state(b,
  0)['reveal']['winner'], ('good', 'evil'))`: `None`. The resumed game sometimes reaches the 15-day cap of the test's
  `args` (`days=15`) with no winner and stops ("stopped after day 15"), which is a legal ending with no winner. With the
  test's seed 7 and random seats, 14 of 300 simulated TB games (about 5%) end that way; whether this run does depends on
  G17 (unseeded seat assignment, bots restarted on resume) and on the order the test's polling thread answers the two
  human seats. Not fixed here; fixes: the test accepts a stopped ending (or raises `days`), or G17 makes the game
  deterministic.

## M12. Requests and decisions

**Stored:** nothing persistent: `Game.insist` (REASKS = 4), `Game.targets` (TB v17 fills an incomplete choice at
random from the game's generator), the vote's one re-ask (then no), `chosen_character` (random), `decide`/`decide_judged`
(the judge's ranking drawn with `st.rng` only when a judge is set), `SeatFailed`.

**States:** asked -> legal (taken) | illegal (re-asked, up to 4) -> failed (the game stops; it resumes from the last
dusk). Decisions: auto (one legal value) | scripted | judged (top, second, or the scripted style).

**Invariants.** A required choice is never made for the player outside TB (B2.6, B3.10); a decision draws the same
random numbers with or without a model (the judge's draw comes only with a judge); a stopped game replays to the same
point.

**Gaps.**

- **G20. A seat failure mid-day replays the whole night on resume.** The checkpoint is at dusk only, so the night's
  results players already saw are decided again (the Storyteller's generator is restored, but the seats' answers may
  differ: G17 for bots, a model's sampling for model seats). Design, not a fault; noted because every resume is a small
  rewrite of history. No fix suggested beyond G17.

## Families

Groups of B, U and new items that share one root cause.

1. **Identity by player name, not by ability instance.** Records are keyed by the player (`Used`, `last_choices`,
   `notes[...][player]`, `State.source`) or by the character (`spent`), never by "this player's instance of this
   ability". B3, B4, B12, B21, B19, U6, U16, G2, G3, G4, G7, G8, G16, S1, S4.
2. **Two ways to change a character.** `Game.changes` does the full transition; `Grimoire.change_character` alone, and
   the Marionette's `setattr`, do part of it. B11, B13, B18, U1, U13, U16, G1, G11, S3.
3. **Lifetimes evaluated at events, not on demand.** `ends_with_source` is checked when the source dies or changes, not
   when its ability stops otherwise; the `while_source_*` pauses are on demand. A1, B5, B19, U2, U6, U10, G9, G10.
4. **Hooks asked only of the player's own character.** Ruling 47, B4 (fixed for the Courtier and Professor), G5.
5. **The wrong sobriety predicate.** `impaired` vs `is_poisoned` vs `unreliable` vs `works`, chosen per call site. B2
   (`impaired` for `unreliable`), B5 (none at all), G13 (`is_poisoned` for `impaired`).
6. **Regimes recomputed mid-phase.** A rule that should hold for a day or a vote is asked anew at each use: the Organ
   Grinder's secret votes (G15, S2); the Witch's "if just 3 live" and the Banshee's powers do it deliberately.
7. **Information with nothing true to show** (a deal or a change leaves no legal truth). U4, U8, U9, U11, U12, U15, B8,
   B15, B17. Not a lifetime problem, but the same shape: a state the setup or a change moved into, with no transition
   out (a ruling picks the Storyteller's fallback).
8. **Duplicates of a single character.** One player per character is assumed by `with_character`, `spent` and the
   Demons' steps. U3, U7, U14, B22, G3.
9. **Lifecycle outside the checkpoint.** G17, G18, G19, G20.

## Proposed changes, in priority order

1. **One change path** (family 2: G1, G11, U16): `Grimoire.change_character` discards `spent`/`Used` for the new
   character and settles `seems_dead`; the Scarlet Woman and Imp heir run `becomes`/`changed`; the Marionette's seat swap
   moves `extra`. TB/BMR/S&V unchanged (argued in G1 and G11).
2. **Ability-tagged states and instance keys** (family 1: G7, G8): `State.ability`, and `hand_over` (or instance keys)
   for the Po, Pukka, Shabaloth and Yaggababble. Fixes S1. BMR unchanged.
3. **The Organ Grinder's secret** (G15): never show the block or a tally after a secret vote today. Custom only.
4. **The sobriety predicate for misregistration** (G13): `impaired`. TB/BMR/S&V unchanged.
5. **Own-character hooks over `g.abilities(p)`** (G5, ruling 47). TB/BMR/S&V unchanged.
6. **Per-player once-per-game records everywhere, cleared by Game.changes** (G3, G4; then G2's revival ruling). Keep
   `spent` for the Spy's view. TB/BMR unchanged while `spent` is kept.
7. **Pause effects with a kept ability** (G10, U2) and **end protections with their source** (G9, A1), as already
   suggested there.
8. **Checkpoint the seats' generators and seed the web's seat assignment; restore atomically** (G17, G18); then the
   PersistenceTest either accepts a stopped ending or is deterministic (G19).
9. **A "died as" record** (G12, U1), and **decoys that follow alignment changes** (G14).

## Proposed fuzzer invariants

Implemented behind `--lifecycle` (clocktower/fuzz.py; default runs and their output are unchanged):

| check | catches (family) | what it tests |
|---|---|---|
| `lifecycle-seems-dead` | 2 (G11) | a living player registering as dead holds a character whose `dies` can say so |
| `lifecycle-stale-spent` | 1, 2 (G1, G4) | a player who becomes a once-per-game character does not find it already spent, by character or for them |
| `lifecycle-pukka` | 1 (G7, G8) | a Pukka kills only a player some Pukka chose on an earlier night (or an attack the Mayor sends on) |
| `lifecycle-secret-vote` | 6 (G15) | after a secret vote today, no nomination or vote prompt shows the block or a tally |
| `lifecycle-checkpoint` | 9 | at each dusk (the checkpoint) nothing is pending and no night is in progress |
| `lifecycle-inert-gain` (advisory) | 4 (G5) | counts gained abilities that act only through their own character's hooks |

Proposed, not implemented:

- **instance epochs for every per-player record** (family 1): at each `becomes`/revival, every record keyed by the player
  for the new character is empty (generalises `lifecycle-stale-spent` to the ad hoc marks);
- **a swap moves the character's bookkeeping** (family 1): after a swap, the new holder's character-owned records
  (charge, pending victim, count, host) equal the old holder's before it;
- **sobriety by predicate** (family 5): for a drunk or poisoned Spy or Recluse, every registration query returns only
  the truth;
- **checkpoint round trip** (family 9): at each dusk, a game restored from the checkpoint into a fresh `Game` (bots
  included) plays the next night identically to the original;
- **paused effects** (family 3): no `ends_with_source` state is in force while its source neither lives nor keeps its
  ability (the existing coherence check reports it as outliving; this would test the pause itself).

## Fuzzer findings with the new checks

10,000 games (`python -m clocktower fuzz run --games 10000 --lifecycle`, seeds from 9,000,000, table sizes 5-15,
scripted Storyteller and rules judge alternating; 138 seconds on four cores). The default checks found what they
find without the flag (Undertaker U1 x10; the Noble, Knight and Puzzlemaster with nothing true to show, U9/U11/U12/U15/U8;
the Kazali's count; U7's two Kazalis; U14's two Boomdandys and two Marionettes; U4's lone Washerwoman with Legion). New:

- **S1. The Pukka kills a player it never chose** (`lifecycle-pukka` x12; Snake Charmer + Pukka): G7 and G8. The new
  Pukka kills the charmed old Pukka through the charm's poison; the old Pukka's victim lives.
- **S2. The Organ Grinder's secret tally is shown** (`lifecycle-secret-vote` x8, 4 games; the Witch's curse or another
  death by day ends the Organ Grinder's ability during nominations): G15.
- **S3. A player seems dead without being the Zombuul** (`lifecycle-seems-dead` x7; the Hatter's tea party, the Pit-Hag
  or the Barber on a seeming-dead Zombuul: it became an Ojo, Po, Pukka, No Dashii, Fang Gu or Village Idiot): G11.
- **S4. A once-per-game ability stale after a change and back** (`lifecycle-stale-spent` x1; the Hatter made a Wizard the
  Baron, and later the Wizard again, still spent): G4. Repro: `python -m clocktower fuzz repro --seed 9006975 --players 11
  --judge rules --chars tealady,atheist,pixie,choirboy,villageidiot,engineer,towncrier,noble,undertaker,chef,cultleader,cannibal,investigator,zealot,hatter,hermit,plaguedoctor,wizard,boffin,baron,wraith,lleech,zombuul,vigormortis,shabaloth
  --lifecycle`.

`lifecycle-checkpoint` found nothing. The `lifecycle-inert-gain` advisory counts are in G5.


## Refactor results

The two root causes of families 1 and 2 are now modelled (commits "Ability instances and one path for every character
change" and "A drunk Spy or Recluse registers truly; a secret tally stays secret"; the carousel-N fingerprints are
re-recorded in a commit of their own). Trouble Brewing, BMR and S&V replay 1100/1100 identically after each commit.
Every item of both families, and G13 and S2, has a regression test in tests/test_lifecycle.py named after it, playing
the scenario above. Readings the fixes needed are docs/carousel-rulings.md 176 to 179.

**The model.** `state.Ability` is one player's instance of one character's ability: `character`, `holder`, `how`
(dealt, changed, gained through the Philosopher, Cannibal, Pixie, Alchemist, Hermit or Plague Doctor, `token`, `gift`,
`believed`), `used` and `spent` (its once-per-game record), `data` (its own bookkeeping: its last night choice) and
`ended`. `Grimoire.instances` holds them; `Grimoire.ability(p, c)` finds p's instance of c; `gain`, `set_gained` and
`believe` begin them. `snv.use/used/fresh` and `Grimoire.spend/spent_ability(c, p)` record on the instance
(`notes['Used']` and `spent` remain as views, for the Spy's Grimoire and the fuzzer). `State.ability` names the instance
that made a state (set where it matters, else guessed by `Grimoire.add` from the step acting). A character's per-holder
notes (`Character.instance_notes`) end with the instance. **One change path:** `Grimoire.change_character` (state:
the old instances end, the new one begins fresh, a seeming death settles, states that lasted while the old character
had its ability end) and `Game.transition` (its audit event) are taken by every change: `Game.changes` (Pit-Hag,
Barber, Snake Charmer, Fang Gu, Farmer, Hatter, Engineer, Summoner...), `Game.become`/`become_now` (the Imp's
starpass, the Scarlet Woman), `make_marionette`, and the setup steps (`how='dealt'`, no event: the Balloonist's,
Kazali's, Lord of Typhon's, Village Idiot's, Alchemist's, Huntsman's and King's added characters, the Marionette's and
Lil' Monsta's waits); the Marionette's seat swap is `Grimoire.swap_seats`. After it, `Game.after_change` runs the new
character's `becomes` and everyone's `changed`, for every path but the setup's (nothing has happened yet).

**Closed.**

| item | what changed | test |
|---|---|---|
| S1, G7 | the Pukka's victims are its instance's states; the charm's poison is the Snake Charmer's | `test_S1_pukka_snake_charmer`, `test_G7_states_name_their_ability` |
| G8 | the Po's charge and the Shabaloth's meal are its instance's last choice (`Night.before_of`), not its player's as another character; a checkpoint from before instances carries `last_choices` and `woke` into each player's own instance (follow-up, bc37b28) | `test_G8_po_charge_and_shabaloth_meal_are_the_instances`, `test_G8_checkpoint_before_instances_keeps_the_charge_and_the_meal` |
| G3 | the Zombuul's, Fool's, Virgin's and Slayer's spent record is per instance (`spent` kept for the Spy) | `test_G3_two_zombuuls_each_have_a_first_death` |
| G4, S4 | a change ends the instance and its uses: a change and back is fresh; a new gained instance (a later meal) too; a Marionette's belief keeps its uses (ruling 178), and its per-holder notes (follow-up, 3ddf35a) | `test_G4_once_per_game_fresh_after_a_change_and_back`, `test_S4_stale_spent_wizard_baron_wizard`, `test_G4_a_marionette_still_believes_its_spent_ability`, `test_G4_a_marionette_still_believes_its_records`, `test_G4_a_cannibals_new_meal_is_a_fresh_instance` |
| G16 | the Golem's, Banshee's, Fearmonger's, Lleech's and Alchemist's per-holder notes end with the instance (ruling 179); follow-up (3ddf35a): the Balloonist's, Acrobat's, Xaan's night X and Wraith's eyes too, and the Mathematician/Drunk jinx's marks (`'Drunk shot:<name>'`, `'Drunk Virgin:<name>'`) are now the believed instance's own record (`data`; old checkpoints migrated) | `test_G16_per_holder_marks_end_with_the_instance`, `test_G16_balloonist_acrobat_xaan_wraith_marks_end_with_the_instance`, `test_G16_a_new_drunk_belief_has_its_own_first_shot_and_nomination` |
| G1 | the Scarlet Woman, the Imp's heir and the Marionette take the one path: a fresh instance, `becomes`, `changed` | `test_G1_scarlet_woman_takes_over_a_fresh_zombuul`, `test_G1_scarlet_woman_yaggababble_learns_a_phrase`, `test_G1_imp_starpass_runs_the_change_hooks` |
| G11, S3 | a seeming death is the Zombuul's: stopping being it, the player is dead (ruling 176, pending owner confirmation: a new choice that flips outcomes) | `test_G11_a_seeming_zombuul_changed_is_dead`, `test_S3_barber_swaps_a_seeming_zombuul` |
| U16 (G6) | the seat swap moves gained abilities, instances and notes with the token; follow-up (2c51a67): the Lord of Typhon's line takes the same swap (it moved tokens with raw `setattr`, leaving the dealt instances behind). Settled by the refactor, pending owner confirmation | `test_U16_marionette_seat_swap_moves_the_gained_ability`, `test_U16_marionette_setup_uses_the_seat_swap`, `test_the_line_moves_the_instances_with_the_tokens` (tests/test_carousel3b.py) |
| U6 | a Vigormortis swapped onto a dead player loses its kept Minions, as when it dies. Settled by the refactor, pending owner confirmation | `test_U6_vigormortis_swapped_onto_a_dead_player` |
| G13 | the Spy's and Recluse's registration test `impaired`; follow-up (8961567): the Slayer's shot and the Imp's kill too (a Slayer or an Imp made drunk by an ability, or by the Goon, no longer acts) | `test_G13_a_drunk_spy_or_recluse_registers_truly`, `test_G13_a_drunk_slayer_or_imp_does_not_act` |
| S2 (G15) | after a secret vote today no prompt shows the block, a tally or the votes needed beyond the majority; follow-up (e66f6f1): nor does a later public vote's result (it goes to the audit; the town is told the count and the majority only), and the fuzzer's `lifecycle-secret-vote` reads public events too | `test_S2_organ_grinder_secret_tally_stays_secret` (now plays a secret vote, impairs the Organ Grinder and holds two public votes; it fails on the code before the fix) |
| B3, B4, B12, B19, B21 | already fixed; now on instances (B19 also through `instance_notes`) | `test_B3_...`, `test_B4_...`, `test_B12_...`, `test_B19_...`, `test_B21_...` |
| B11, B13, B18 | already fixed; the setup steps now take the one path (`how='dealt'`) | `test_B11_...`, `test_B13_...`, `test_B18_...` |

**Not closed, and why.**

- **U1** (the Undertaker after a change) and **U13** (a dead neighbour made the Marionette): owner questions. The
  engine does what it did; the death log now records `as`, the character each player died as, so U1's ruling is one
  line either way. Tests `test_U1_undertaker_after_a_change` and `test_U13_make_marionette_takes_the_one_path` pin the
  current behaviour.
- **G2** (what a revived player holds): an owner question. The revived player's own instance is the same one, fresh
  again, and gained instances are kept as they were (the engine's reading before). `test_G2_revival_restores_the_instance`.
- **G8, the swap half**: whether a swap carries a Demon's own bookkeeping to its new holder (the Po's charge, the
  Pukka's waiting victim, the Yaggababble's count for today). The engine's swap gives a fresh instance (the Barber's
  almanac), so none of it moves, as before; only the Vigormortis and the Lleech hand theirs over (their rulings).
- **U6, the second half** (whether the Storyteller should choose a swap onto a dead player): the owner's; unchanged.
- **The Damsel's guesses** stay by player ("each Minion": ruling 179): an owner question (item C3.4 of the voice
  review; the official Damsel example 2 has one guess for the team). The Evil Twin's twin (`notes['Twins']`) and the
  Xaan's X are set again by `becomes` when a player becomes the character again, so they need no end; nothing else
  reads a former holder's.
- **Rulings for the owner**: 176 (a seeming-dead Zombuul that changes character is dead) is a new choice the refactor
  made that flips outcomes, and U6's first half and U16 were settled as consequences of it: all three are pending the
  owner's confirmation (docs/review/everything-open-voice.md, Part B, group 7, with 177 to 179). The engine keeps them.
- Outside the two families and not touched: G5 (hooks asked only of the own character, ruling 47), G9, G10, U2, U10
  (lifetimes evaluated at events), G12 beyond the `as` record, G14, G17 to G20.

No item needed TB, BMR or S&V play to change.

**Fuzz, before and after.** The audit's runs: `python -m clocktower fuzz run --games 10000 --lifecycle` and the
default `python -m clocktower fuzz run --games 10000` (seeds from 9,000,000, sizes 5-15, scripted Storyteller and rules
judge alternating), on the commit before the refactor and after it.

| violations | lifecycle run, before | after | default run, before | after |
|---|---|---|---|---|
| lifecycle-pukka (S1) | 12 | 0 | - | - |
| lifecycle-secret-vote (S2) | 8 | 0 | - | - |
| lifecycle-seems-dead (S3) | 7 | 0 | - | - |
| lifecycle-stale-spent (S4) | 1 | 0 | - | - |
| oracle | 18 | 18 | 18 | 18 |
| engine-truth | 10 | 10 | 10 | 10 |
| coherence | 4 | 4 | 4 | 4 |
| setup | 4 | 4 | 4 | 4 |
| crash | 1 | 1 | 1 | 1 |
| total | 65 | 37 | 37 | 37 |

Every violation left is the one it was, detail for detail (the known ones the audit lists for these seeds); none is
new. A first pass after the refactor showed one new kind of `coherence` (3 games: "holds
extra abilities no ability gave"): the seat swap now moves an Alchemist's or a Hermit's abilities, and the fuzzer had
seen them given to the other seat; the swap now tells the audit (a `gains` event for the new seat), and they are gone.
These seeds show none of U6 or U16 in the default run, so they were measured where they occur:

| run | before | after |
|---|---|---|
| U16's repro (`fuzz repro --seed 9000806 ...`, interaction-findings U16) | 1 (`once-rewoken`) | 0 |
| `fuzz run --games 1500 --force vigormortis,barber`: states outliving a Vigormortis swapped onto a dead player (U6: six kept abilities, one kept Cerenovus's madness) | 7 | 0 |
| the same run: other violations | 1 (U2: a curse through a drunk Vigormortis) | 1 (the same) |
| `fuzz run --games 1500 --force alchemist,marionette` | 0 | 0 |

**Re-recorded carousel games.** 198 of the 13,200 carousel-N fingerprints changed (carousel-8 and carousel-9 none);
each game's cause was found by taking each fix out in turn (an ablation copy of the engine, not committed): the game
replays as recorded with that fix out, and with no other. By script, cause and seed (the table size is the seed's
thousands):

- **G13** (78 games): a drunk Spy or Recluse (the Courtier's, the Sailor's, the Innkeeper's drunkenness) registers
  truly to the information roles and the Storyteller's samples.
- **G1** (99): a Demon made by the Imp's starpass (carousel-5, 62) or by the Scarlet Woman (carousel-12, 34; Riot) now
  learns the King ("The Demon knows you are the King": the King's `changed`, which the direct path skipped); the
  Scarlet Woman's Zombuul has its own first death (carousel-2, 3).
- **G11** (7, carousel-2): a seeming-dead Zombuul changed by the Pit-Hag is dead (ruling 176).
- **G16** (7, carousel-6): the Vizier/Fearmonger jinx read a former Fearmonger's choice.
- **U16** (6, carousel-4): the Marionette's seat swap moves the Alchemist's Minion with the Alchemist's token.
- **G4** (1, carousel-6, 14099): a Cannibal's later meal of the Philosopher is a fresh instance (ruling 177).

- **carousel-1** (2): G13 (2): 11029, 12049.
- **carousel-2** (15): G13 (5): 6063, 10004, 11096, 13003, 15058; G11 (7): 6074, 9020, 9088, 10085, 12031, 13045, 15050; G1 (3): 7051, 11013, 14056.
- **carousel-3** (6): G13 (6): 6091, 9089, 10038, 11016, 11036, 14088.
- **carousel-4** (6): U16 (6): 8048, 12075, 12092, 13028, 13049, 15007.
- **carousel-5** (62): G1 (62): 6023, 6028, 6050, 7005, 7028, 7048, 8011, 8027, 8088, 9004, 9016, 9045, 9064, 9081, 10005, 10029, 10065, 10075, 10093, 10095, 11002, 11023, 11030, 11039, 11077, 11096, 12029, 12032, 12035, 12065, 12070, 12073, 12075, 12078, 12079, 12095, 13007, 13038, 13044, 13045, 13055, 13056, 13060, 13071, 13095, 13096, 14007, 14029, 14063, 14064, 14094, 15003, 15011, 15025, 15028, 15038, 15045, 15053, 15067, 15080, 15091, 15094.
- **carousel-6** (42): G16 (7): 7094, 9034, 11082, 12014, 12075, 14012, 14094; G13 (34): 8020, 8073, 9015, 9085, 9097, 10005, 10010, 10028, 10030, 12009, 12022, 12024, 12033, 12041, 12061, 13006, 13036, 13058, 13062, 13080, 13094, 13095, 13097, 14015, 14037, 15007, 15011, 15020, 15042, 15060, 15066, 15078, 15079, 15080; G4 (1): 14099.
- **carousel-7** (4): G13 (4): 11085, 14062, 14080, 15078.
- **carousel-10** (1): G13 (1): 13048.
- **carousel-11** (15): G13 (15): 10050, 11031, 11050, 13006, 13034, 13042, 14026, 14028, 14034, 14068, 14079, 14099, 15004, 15013, 15018.
- **carousel-12** (45): G1 (34): 5022, 5086, 5090, 6078, 6098, 7026, 7038, 7094, 9042, 10009, 10022, 10025, 10026, 11003, 11021, 11074, 12037, 12058, 13004, 13024, 13036, 13059, 13062, 14010, 14016, 14026, 14032, 14034, 14057, 14062, 14088, 14091, 15051, 15077; G13 (11): 9037, 9043, 9091, 10007, 11046, 11053, 11081, 14051, 15044, 15055, 15091.

**Risks.** The instance model is in the core, and every script's play depends on it; the base scripts' fingerprints
show it changes nothing there, but custom scripts may meet paths the fingerprints and the fuzzer do not (a character
whose ability records by player in a way not listed here, read through the `notes['Used']` view, which is rebuilt only
for the player whose instance changed). `Grimoire.add` guesses a state's instance from the step acting; a state made
outside a night step by a gained ability is tagged with the holder's own character's instance (only the Pukka reads
the tag today). The Scarlet Woman's `becomes` hooks that consult the judge run at the next safe point (Game.later),
not at once. Checkpoints made before the refactor are restored with instances rebuilt from `notes['Used']` and `spent`,
and each player's last night choice (`last_choices`, its night from `woke`) on their own character's instance (a choice
made with a gained ability was then by player too, so it lands on the own character's: the old reading).

**Follow-up: the independent review.** A review of the refactor confirmed most of it and found the gaps above marked
"follow-up", fixed in bc37b28 to 8961567; the official examples' engine bugs EC-8, EC-13, EC-22 and EC-23
(docs/examples-findings.md) are fixed in 2280a5f to 35e270a, and the example tests run on their own (91bed69:
`python -m unittest discover -s tests/examples`). Trouble Brewing, BMR and S&V replay 1100/1100 identically after
each. The carousel-N fingerprints changed in 432 games, re-recorded in b0f2b3e; each game's cause is the first of these
commits after which it replays differently (each was replayed after every commit), and one game's first differing
events were read for each cause:

- **G13, the Slayer and the Imp** (8961567, 118 games): a drunk Imp no longer kills or starpasses, and a drunk Slayer's
  shot no longer kills (in the games read: the Imp that picked the Goon, who makes their first chooser drunk, and an
  Imp made drunk by another ability).
- **EC-8** (2280a5f, 307 games, 5 of them also changed by 8961567): a Washerwoman, Librarian, Investigator or Chef
  ability that begins later learns at once (`InfoRole.becomes`), as rulings 40 and 47 say and the S&V characters already did:
  the Pit-Hag's new Washerwoman or Chef at night, the Cannibal's meal of one by day ("Day n — Chef: ...").
- **EC-13** (07c9b12, 7 games): a Princess made at night has her first day the day that follows, not the one after.
- None from bc37b28 to 3ddf35a (the S2 fix changes no recorded game: none has a public vote after a secret one with
  the Organ Grinder impaired; the Lord of Typhon's swap and the notes' ends change none), nor from 904fec7 to 91bed69.

By script, cause and seed (a starred seed changed with 8961567 and again with 2280a5f):

- **carousel-1** (48): G13 (32): 5032, 5046, 6057, 6070*, 6091, 7030, 7037, 8023, 8039, 9010, 9057, 9069, 9071, 9077, 11045, 11066, 11084, 12000, 12019, 12039, 12055, 12057, 12080, 14002, 14069, 14070, 14097, 15017, 15039, 15045, 15068, 15085; EC-8 (16): 6058, 6078, 10014, 10053, 11018, 12009, 13001, 13022, 14028, 14042, 14062, 14087, 15023, 15024, 15047, 15057.
- **carousel-2** (23): EC-8 (23): 6094, 7074, 8005, 8075, 9048, 11021, 11043, 11048, 12019, 12040, 12044, 13024, 13076, 13087, 14003, 14013, 14048, 14072, 14076, 15027, 15050, 15055, 15065.
- **carousel-3** (9): G13 (9): 6031, 8083, 9070, 9094, 10093, 13027, 15006, 15080, 15087.
- **carousel-4** (98): G13 (16): 6012, 8039, 8066, 8087, 8096, 9003, 10070, 11026, 12018, 13018, 14059, 15026*, 15038, 15047, 15074*, 15077; EC-8 (82): 5003, 5015, 5080, 6068, 6071, 7007, 7051, 7066, 7067, 7070, 7091, 8014, 8019, 8037, 8075, 8081, 8091, 9030, 9050, 9070, 9075, 10004, 10020, 10025, 10034, 10043, 10049, 10071, 10083, 10090, 11011, 11017, 11042, 11047, 11057, 11068, 12009, 12016, 12023, 12028, 12059, 12061, 12094, 12098, 13006, 13029, 13034, 13048, 13078, 13080, 13084, 13085, 13086, 13097, 14002, 14005, 14015, 14018, 14027, 14045, 14050, 14053, 14062, 14069, 14071, 14087, 15002, 15004, 15005, 15013, 15014, 15032, 15033, 15035, 15039, 15046, 15050, 15063, 15065, 15081, 15092, 15095.
- **carousel-5** (27): EC-8 (27): 6006, 6035, 9017, 10053, 10063, 11001, 11033, 11034, 12006, 13010, 13013, 13036, 13045, 13052, 13070, 13088, 13089, 13098, 14001, 14007, 14052, 14078, 14084, 14090, 15047, 15059, 15065.
- **carousel-6** (171): G13 (9): 6052, 7052, 8063, 10031, 11002*, 14047, 14052, 15009, 15064*; EC-8 (159): 5007, 6019, 6046, 6058, 6097, 7010, 7015, 7026, 7070, 7071, 8000, 8005, 8024, 8029, 8031, 8049, 8079, 8084, 8085, 8086, 9000, 9002, 9011, 9013, 9016, 9029, 9031, 9035, 9042, 9059, 9071, 9079, 10008, 10010, 10018, 10024, 10030, 10066, 10068, 10071, 10079, 10089, 10099, 11009, 11027, 11028, 11034, 11038, 11044, 11045, 11047, 11050, 11055, 11056, 11075, 11077, 11085, 11086, 11093, 11096, 12000, 12002, 12003, 12010, 12013, 12014, 12015, 12019, 12020, 12021, 12027, 12030, 12032, 12037, 12038, 12039, 12041, 12044, 12047, 12049, 12066, 12086, 12097, 13003, 13005, 13010, 13012, 13015, 13016, 13020, 13023, 13025, 13026, 13028, 13034, 13037, 13042, 13045, 13046, 13047, 13050, 13052, 13053, 13054, 13058, 13065, 13069, 13071, 13081, 13083, 13092, 13095, 14003, 14005, 14008, 14012, 14018, 14019, 14024, 14029, 14032, 14033, 14040, 14042, 14043, 14048, 14050, 14055, 14063, 14070, 14071, 14076, 14085, 14089, 14091, 15001, 15004, 15005, 15008, 15014, 15015, 15019, 15028, 15033, 15034, 15037, 15039, 15052, 15055, 15061, 15066, 15067, 15068, 15070, 15073, 15078, 15086, 15091, 15097; EC-13 (3): 7088, 14087, 15074.
- **carousel-7** (4): EC-13 (4): 11061, 14059, 14065, 14087.
- **carousel-10** (1): G13 (1): 15024.
- **carousel-11** (51): G13 (51): 5055, 5074, 6046, 7031, 7035, 7054, 8041, 9054, 9081, 9083, 9096, 10005, 10049, 10061, 11054, 11073, 11089, 12091, 13004, 13006, 13011, 13055, 13068, 13076, 13087, 13088, 13091, 13096, 13097, 14007, 14025, 14028, 14038, 14042, 14045, 14052, 14065, 14068, 14083, 14085, 14087, 14099, 15000, 15013, 15018, 15027, 15037, 15038, 15053, 15089, 15095.

Fuzz: `fuzz run --games 400 --force organgrinder --lifecycle` (seeds from 9,000,000) shows 5 `lifecycle-secret-vote`
violations with the extended check on the code before e66f6f1 (a later public vote's result) and none after.
