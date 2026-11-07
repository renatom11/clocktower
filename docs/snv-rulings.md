# Sects & Violets: rulings to review

Where the almanac and wiki leave an interaction unclear, the engine had to pick a reading. Each entry says the
question, the options, what the engine does now, and why. These are for the owner to confirm or change; each change
is a small edit in `clocktower/snv.py` (or the core) plus its test in `tests/test_snv.py`. The Storyteller's new
weights are in `state.POLICY` under "Sects & Violets", marked "default, for review".

## Batch 1: the core, the Demons and the Minions

### The core

1. **Madness: what the Storyteller hears (the evidence policy).** The madness decision ("did this player break
   their madness today?") reads, from the start of the madness window: what the player said aloud (speech,
   nominations, defenses) and the public ability claims they made (claiming a character's ability claims the
   character). Never anyone's thinking or belief probes. **The scripted Storyteller reads only what was said aloud,
   as a human Storyteller hears it. A judge hears what `--judge-hears` allows: with `all` (the default) every
   whisper too, so a whispered confession ("I'm actually mad") is overheard and fatal, as in the almanac's Flowergirl
   example; with `public`, only what was said aloud.** Options: (a) as now; (b) never whispers, for any judge; (c) a
   seeded share of whispers "overheard" (the audit's SNV-17), so a private confession is a risk rather than certain
   death. The consequence to note: under the default, the wiki's Mutant advice ("come out secretly to one or two
   players you trust") is always fatal, and the S&V player prompt must say what the Storyteller hears (*since
   written, in batch 3: ruling 48*). Reports to the Storyteller ("snitching") need a player-to-Storyteller channel
   (*since built: visits, ruling 36*).
2. **Madness: the rule the scripted Storyteller and the rules judge apply** (`state.madness_broken`). Told to be
   mad about being a character (the Cerenovus): they broke it unless they claimed it aloud, the latest claim heard
   from them is it, and they never said they are not it or that they are mad ("I am mad", "the Cerenovus picked
   me"). Saying "I'm not mad" is fine (the almanac's Barber). Told not to be mad about something (the Mutant: being
   an Outsider): they break it by claiming it, or saying they are mad. This is a floor, not the judgment the madness
   guide asks for: a model judge weighs effort, hints and arc (the question it is given says so). Option: let the
   scripted Storyteller be lenient sometimes (a weight), since it cannot judge effort.
3. **Madness: when it is judged, and the day after a madness execution.** The Cerenovus's target is judged once,
   when the day's talk is done (after private time and the town square) and before nominations open. A madness
   execution then is the day's one execution, and the day goes to night without nominations (the almanac: "go to the
   night phase"); the day keeps its fixed beats (protocol v5). What the player says during nominations is not
   evidence. Options: judge at dusk too (seeing nominations and defenses; an execution may already have happened,
   and the almanac also allows "the next ... night"); judge after every beat (closer to "at any time", many more
   judge calls). The core takes a checkpoint per character (`Game.judge_madness`), so the Mutant can use others.
4. **Madness: "might be executed".** A player who broke madness is executed 90% of the time if good (the rulebook:
   it is the player's choice, even when it ends the game), 50% if evil (the almanac: "might" lets the Storyteller
   stop evil using it). The rules judge executes a good player, and decides an evil one by the balance of the game.
   A drunk or poisoned Cerenovus makes nobody mad; so does one who loses their ability before the judgment (dies,
   unless the Vigormortis killed them).
5. **Character changes** (`Game.change`, `Game.swap`, `Game.changes`). The player is told at once and in private:
   "you are now the X (its ability)" and their alignment, "now evil" or "still good". It is never false (the
   Vortox, drunkenness and poison don't touch it). The new character's ability is fresh, even a once-per-game one an
   earlier holder used (the Barber's almanac). The old character's ongoing effects end (a poisoner who changes stops
   poisoning). A player who becomes a Demon learns no Minions, and the Minions are not told. Then the new
   character's `becomes` hook (a new Evil Twin is paired) and everyone's `changed` hooks (an Evil Twin whose twin
   changed side) run. A new character whose night step comes later tonight acts tonight.
6. **Dead players keeping their ability** (a 'has ability' state, `Grimoire.keeps_ability`). It names what it was
   kept as ('Minion'): a dead Minion who becomes another Minion keeps it; one who becomes a Townsfolk does not. While
   kept, the player wakes at their step, their ability works, and their effects carry on; when it is lost, their
   effects end. The source's sobriety matters too (the Vigormortis drunk: its Minions have no ability).
7. **States worked out on demand** (`Character.ongoing`, `Grimoire.derived`): the No Dashii's and the Vigormortis's
   poison are not placed but worked out whenever someone's sobriety is asked about, so they follow every change at
   once. An ability whose own states are being worked out adds nothing (a No Dashii is not poisoned by its poison).
8. **Information that must be false** (`Character.falsifies`, `Grimoire.falsified`, `state.only_false`). An
   information decision whose recipient's information is falsified offers every value (as for an impaired player),
   then only the false ones: no scripted draw or judge can give a true one. "Townsfolk information" goes by the
   ability's type (the character the recipient believes they are, unless the decision names the ability). **A result
   with no false value keeps its true one** (the Storyteller has nothing false to give). The Trouble Brewing
   information Choices (and the Empath and Chef in tests) honour it, so a custom script mixing them works.
9. **A nomination or an execution can trigger another player's ability** (`Character.nomination`, `execution`). The
   nominee's own reaction (the Virgin) comes first, then everyone's. An execution counts for these whether or not the
   player dies (an executed dead player too: "if the good player is executed").
10. **Setup modifiers.** A Demon's modifier counts now (the Fang Gu's +1, the Vigormortis's -1). Removing Outsiders
    where there are none removes none and adds no Townsfolk (`team_sizes(..., floor=True)`), in setup checks and in
    random setups. Bad Moon Rising's Godfather keeps its old dealing (a -1 that would go below zero is not dealt),
    so its games are unchanged; its setup check now also accepts the floored count, which the official rule allows.

### Minions

11. **The Witch.** A curse is made only by a sober, healthy Witch; it pauses while the Witch is drunk or poisoned
    and resumes (the rulebook's example), follows the player through a character change, and ends with the Witch's
    ability (unless the Vigormortis killed them). At three players alive the ability is lost at once, a curse
    already made included, and the Witch is not woken. The death is announced at once ("X dies."), not why.
12. **The Cerenovus.** Any player, dead or alive (themself too), and any good character on the script. **The
    target is told even when the Cerenovus is drunk or poisoned** (nothing gives the wasted ability away; nobody is
    executed for it). Option: tell them nothing.
13. **The Pit-Hag: in play.** A character is in play if any player has it, dead or alive; a Drunk's apparent
    character does not count (the audit's note). A dead player can be changed. The Pit-Hag may change themself.
14. **The Pit-Hag: deaths tonight are arbitrary.** When a Demon is made (from a living or dead player), the
    Storyteller decides, at the Pit-Hag's step, up to two extra deaths tonight (attacks of the Pit-Hag) and whether
    the Demons' attacks still kill. The scripted style follows the almanac: a Demon made into another Demon, nobody
    dies 80% of the time (`pithag_quiet`); a new evil Demon, the old Demon dies 80% (`pithag_kill_old_demon`), and the
    new one attacks as usual; a good Demon on the final night (four or fewer alive, `final_night_alive`), the evil
    Demon dies 80% (`pithag_final_kill`); otherwise as usual. The rules judge has no opinion. Options: allow
    protecting chosen players only, or more than two deaths.

### The Evil Twin

15. **The twin** is any good player at setup (uniform). Both always learn each other truly, even if the Evil Twin
    is drunk on the first night (a reading: it is knowledge of each other, as a character change is). Option: a
    drunk Evil Twin's pair is misinformation.
16. **"If the good player is executed, evil wins"**: whichever of the two is good (a good Evil Twin too), executed
    alive or dead, while the Evil Twin has their ability (alive and sober, or kept by the Vigormortis). "Good can't
    win if you both live": both alive, and the Evil Twin sober.
17. **Re-pairing.** When the twins end up on the same side (a Fang Gu jump into the twin), the Storyteller picks a
    new twin of the other alignment and both are told. A new Evil Twin (the Pit-Hag's) is paired at once; on the
    final night with the Demon or a dead player when one is of the other alignment.

### Demons

18. **The Fang Gu's jump.** The first Outsider it would kill becomes an evil Fang Gu, told so, then the old Fang Gu
    dies (an Outsider who would not die, dead or protected, does not jump). Once a game, kept in the Grimoire's notes
    whatever happens to the Fang Gu. The new Fang Gu learns no Minions. Not handled: the Scarlet Woman jinx
    ("remains the Scarlet Woman", a custom-script case): the Trouble Brewing Scarlet Woman would take over.
19. **The Vigormortis's poison.** The Storyteller picks a side (the nearest Townsfolk clockwise or anticlockwise of
    the dead Minion, alive or dead) at the kill, uniformly; the poisoned player is then recomputed on that side, so
    one Townsfolk per Minion is always poisoned. Option: fix the player chosen. **A dead Minion who is drunk or
    poisoned loses their own ability, but their poison goes on** (a reading: the poison is the Vigormortis's
    ability). Option: it stops too. A kill that fails (protected) keeps nothing.
20. **The No Dashii** poisons by character type (an evil Townsfolk counts), from the start of the game, alive or
    dead; with one Townsfolk in play, only that one.
21. **The Vortox** falsifies every Townsfolk ability's information while it has its ability (dead, drunk or
    poisoned: no). At dusk, if nobody was executed today, evil wins: an execution of a dead player and a madness
    execution count, a Witch death does not.

New weights: `mad_execute_good` 0.9, `mad_execute_evil` 0.5, `pithag_quiet` 0.8, `pithag_kill_old_demon` 0.8,
`pithag_final_kill` 0.8, `final_night_alive` 4 (a count, not a chance). The madness, madness-penalty, twin,
Pit-Hag-deaths and Vigormortis-poison decisions go through the Storyteller judge.

Not yet done, for later batches: the S&V player prompt (madness, what the Storyteller hears, the Vortox's dusk
rule), visits to the Storyteller, and the Townsfolk and Outsiders (the Mutant uses `Game.judge_madness` with
`must=False`; the Snake Charmer and Barber use `Game.swap`).

## Batch 2: the information Townsfolk, and the Snake Charmer

Every result is a Choice with its truth (what a working ability could show) through `Game.decide_judged`, so a
drunk or poisoned player (the No Dashii's neighbours) may be misinformed, falsified information (the Vortox) is only
false, and the judge sees the call as `information`. A misinformed result comes from the recipient's false world
(`Grimoire.decoy`) where the ability has one (the Clockmaker, Oracle, Seamstress), so it never breaks the setup's
counts.

### The core

22. **The abnormal record (the Mathematician).** `Game.abnormal(p, ability, why)` records, in `Grimoire.abnormal`,
    an ability that worked abnormally because of another character's ability, with the day and phase. Two sources:
    (a) every information decision whose value a working ability could not give (`Game.note_information`, run by
    `decide_judged` for any `information` call with a truth): a poisoned or drunk player's false result, and every
    falsified one under the Vortox (the almanac counts the Vortox's victims); a poisoned player's true result is not
    abnormal (the almanac's Empath). (b) S&V abilities that would have acted but their holder is drunk or poisoned:
    the Demon's attack, the Witch's curse (made, or a cursed nominator who lives: the almanac's example), the
    Cerenovus's madness, the Pit-Hag's change (only when the character is not in play: it would have worked), the
    Snake Charmer charming the Demon (not a Townsfolk: the almanac's example), and the Evil Twin when the good twin
    is executed. **Not recorded** (options for review): a kill stopped by a protection (none on S&V); the Pit-Hag's
    "Demon kills stopped"; a drunk or poisoned No Dashii or Vortox (their effects are continuous); the Recluse
    registering as evil, which the almanac says counts (not on S&V: the truth sets include registration); the
    Drunk's own false results (the official Mathematician/Drunk jinx says they count, on scripts with both).
    Nothing is emitted, so Trouble Brewing and Bad Moon Rising play identically.
23. **Since dawn.** On night n the Mathematician counts the players with a record on day n-1 or tonight (on the
    first night, since the game began); distinct players, as the almanac counts reminders. Their own records are
    not counted (they "do not detect their own ability failing"), but another Mathematician would count them.
24. **Votes and nominations as they happened** (`Grimoire.nominations`). Each vote now records the voters'
    characters (`characters`), and each nomination the nominator's (`character`), so the Flowergirl detects the
    Demon who voted even if they changed character later (a Snake Charmer's swap that night), and the Town Crier
    the Minion who nominated. A dead Demon's ghost vote counts. Registration (a Recluse as a Demon) is not
    consulted: none on S&V.
25. **The rules judge supports a bluff in a pair of characters** (the Dreamer): a value whose `characters` hold the
    character the chosen evil player claimed ranks first, as a single `character` already did.

### Townsfolk

26. **The Clockmaker** counts seats the short way, the dead included, from any Demon to any player whose character
    is a Minion (by type: a good Minion counts, as the Pit-Hag can make one). Impaired values are 1 to half the
    table. **A player who becomes the Clockmaker after the first night learns the number at once** (the Barber's
    almanac: a new character's ability is theirs even if it is "you start knowing"). Options: at the next night;
    never.
27. **The Dreamer.** By character type, not alignment (a good Witch is shown as the Witch and a good character).
    The scripted false character: for a good-type player, an in-play Minion 50% (`dreamer_minion_in_play`; the
    wiki: "almost always"), else any Minion or Demon; for an evil-type player, the good character they last claimed
    aloud 50% (`dreamer_bluff`: the almanac's "help evil" example), else a secretive one 30% (`dreamer_secretive`:
    Snake Charmer, Sage, Mutant, Klutz), else another, never the Dreamer's own. Misinformed or under the Vortox,
    neither is correct. The scripted Storyteller reads claims made aloud only, as for madness.
28. **The Snake Charmer.** Alive players only; choosing themself or a non-Demon does nothing. Charming the Demon
    (by character: a good Demon too) swaps characters and alignments (`Game.swap`; two evil stay evil), both told at
    once; the old Demon is then **poisoned for the rest of the game, even through later character changes** (a
    reading of "permanently"). Option: the poison ends if they stop being the Snake Charmer. The new Demon learns
    no Minions and acts tonight (the Demons' steps come later). A Vigormortis charmed: its dead Minions' kept
    abilities and poison follow it to the new player (*fixed in batch 3: ruling 34*). A Philosopher-Snake Charmer
    is handled in batch 3.
29. **The Mathematician** misinformed: a number one or two off the truth (small numbers are usual). Under the
    Vortox any number but the truth.
30. **The Flowergirl and the Town Crier**: yes or no about the day just past, not on the first night; misinformed,
    the opposite. A madness execution with no nominations gives a "no" (a "yes" under the Vortox: its example).
31. **The Oracle** counts dead players (as the town sees them) by alignment, at its step after the Demon's kill: a
    dead good Evil Twin is not evil, a Townsfolk turned evil is.
32. **The Seamstress** may decline any night; naming one player is declining (a reading: the prompt asks for two
    or none). The ability is spent once two are chosen, even drunk or poisoned. Dead players may be chosen.
33. **The Sage** learns only when the Demon's own attack killed them tonight (the death log's cause `demon`: the
    Vigormortis's and Fang Gu's attacks count; the Witch, the Pit-Hag's arbitrary deaths and executions do not). The
    pair is the Demon that killed them and another player (never the Sage); before the final night the other is
    alive 90% of the time (`sage_alive`), on it anyone. Misinformed: two players who are not that Demon, one dead
    and one alive on the final night (the almanac's drunk Sage). Their sobriety at the step decides.

New weights: `dreamer_minion_in_play` 0.5, `dreamer_bluff` 0.5, `dreamer_secretive` 0.3, `sage_alive` 0.9.

## Batch 3: visits to the Storyteller, the last Townsfolk, the Outsiders; the script plays end to end

### The core

34. **The Vigormortis charmed (a fix to batch 2, ruling 28).** The kept abilities of the Minions the Vigormortis
    killed, and their poison, belong to the Vigormortis character, not its player: when the Snake Charmer charms the
    Vigormortis (or the Barber swaps it), they move to the new Vigormortis, whose sobriety then decides them; the old
    Vigormortis, now the poisoned Snake Charmer, keeps nothing. Generic: `Character.hand_over` (a character passing
    from one player to another in one change takes what is its own; Game.changes puts it back with the new source).
    Option: they end, as before.
35. **Visiting the Storyteller** (`visit`, `Game.visit_judged`). On a private-time turn any player may visit the
    Storyteller claiming a visiting ability (the Savant, the Artist), with a text (the Artist's question). The town sees
    a public event naming who went, never why; what was said is the Storyteller's (an audit event the judge hears,
    under either hearing). A player with the ability, or who believes they have it, is answered in private; anyone
    else is told the Storyteller listened and nodded (the almanac: help evil bluff). **One visit a day per player, and
    a visit is the turn's one conversation: a whisper sent with it is not sent** (a reading: one conversation at a time,
    as whispers are). Options: a visit alongside the whisper; more than one visit a day. Dead players may visit (and
    are answered only if their ability works dead: none of these). The field is in the schema, and offered to random
    seats, only for scripts with a visiting ability, so Trouble Brewing and Bad Moon Rising are unchanged.
36. **What is said on a visit is evidence for madness** (said to the Storyteller, so heard under both hearings, but
    not "aloud" for the Cerenovus). This is a first channel for reports to the Storyteller ("snitching"): the model
    judge reads every visit's text in its record. The scripted floor reads only the visitor's own words.
37. **Abilities gained beyond one's character** (the Philosopher's `Player.extra`): the player is woken at that
    character's step (Game.wake) as that character; `Grimoire.holder` and the S&V Townsfolk steps look at abilities,
    not characters, and loop over every holder (the Philosopher and the drunk original). **A player whose character
    changes loses the abilities gained through the old one** (`Grimoire.change_character`; the almanac: the duplicate
    sobers up if the Philosopher "turned into a different character"). Once-per-game S&V abilities are spent per
    player (`snv.used`), so the Philosopher and the original each have theirs; a player who becomes the character
    later starts fresh.
38. **The Juggler's guesses** are a list form of the shared public `ability` move (`Character.public_guesses`): up to
    five {player, character} guesses, heard by the town. In the schema only when a script has such a character.
39. **The Mutant's checkpoints**: judged once before nominations on the day's talk (as the Cerenovus), and again at
    dusk on what was said since (nominations, defenses), if nobody was executed today (`Game.judge_madness(after=)`,
    so evidence is never judged, and the "might" rolled, twice). Not at night (nobody talks then). Option: after every
    beat (closer to "at any time"; a madness execution would then end the day earlier).

### Townsfolk

40. **The Savant's statements** (`snv.savant_statements`): twelve templates checked by code against the Grimoire and
    records: two players are the same alignment (neighbours, and the Savant with anyone); the Demon sits within 1 or 2
    seats of a living player (and is not them); exactly N living players are drunk or poisoned (0-3); a living player
    has been chosen at night by another's ability; there is a Y in play (any character but the Savant's own); exactly
    N Outsiders (only counts some legal setup has); N of the Savant's living neighbours are evil; a living player is
    evil; a Minion sits next to the Demon; and from day 2: everyone got true information last night, a Demon voted
    yesterday, a Minion nominated yesterday, N dead players are evil. **The scoring rule** (the scripted Storyteller):
    the true statement's form uniformly among the forms with one, then by weight (2 if about living players only, 1
    otherwise), never a true "X is evil" for the Demon and nothing heard before; the false one of the same form 50%
    of the time (`savant_same_kind`), else any. Drunk or poisoned: two false 70% (`savant_both_false`), else two true;
    under the Vortox, two false always. The rules judge has no opinion (thousands of pairs); a model judge ranks a
    shortlist. Options: more templates (seat ranges, claims); a weight for "pertinent to today's claims".
41. **The Philosopher** chooses any Townsfolk or Outsider (or none, keeping it). Spent even if drunk or poisoned (a
    wasted choice is abnormal for the Mathematician). The in-play player of the gained character is drunk while the
    Philosopher has their own ability (worked out on demand: a player made that character later is drunk too). A
    "you start knowing" ability gained after the first night acts at once (the Clockmaker example); on the first
    night, at its step. Choosing the Philosopher does nothing.
42. **The Artist.** Code answers questions of the simple forms `snv.artist_truth` reads ("Is X the Y / evil / an
    Outsider?", "Is the Demon X, Y or Z?", "Are X and Y the same alignment?", "Is there a Y in play?"); misinformed or
    under the Vortox the opposite. Anything else goes to the judge (yes, no, "I don't know"); the scripted Storyteller
    says "I don't know". **A question that is not yes/no gets "I don't know" and spends the ability** (a reading; the
    almanac asks them to rephrase: option: let the judge return "ask again" without spending it). An empty question
    is not a use. Under the Vortox a question only the judge can answer is the judge's to answer falsely.
43. **The Juggler**: only a living Juggler's first claim with at least one guess, on their first day as the Juggler
    (day 1, or the day they became it), counts, drunk or not; correct guesses are counted at once against true
    characters; that night's sobriety decides (one off when misinformed, any other number under the Vortox). A claim
    with no guesses is not a use (option: it is, and learns 0).

### Outsiders

44. **The Mutant** must not claim any Outsider (or the type) aloud, in a whisper heard, or on a visit, nor say they
    are mad (the batch 1 floor with `must=False`); judged at the two checkpoints (ruling 39), executed by the usual
    "might" weights.
45. **The Sweetheart**: any death; their sobriety as they die decides (a drunk or poisoned Sweetheart's death is
    wasted). The Storyteller picks any other player, drunk for the rest of the game (through later changes); the
    scripted style: a living good Townsfolk 90% (`sweetheart_townsfolk`), else any other living player; the rules
    judge: an evil player when evil is well ahead, else a good Townsfolk. Decided at once (at the next safe point).
46. **The Barber**: a death by day gives haircuts the coming night, at night that night; the Barber's sobriety as
    they die decides. The Demon (the Storyteller's pick of several, uniformly) may choose two players, alive or dead,
    themself included, never another Demon, or none (one named is none); the swap keeps alignments and each is told.
47. **The Klutz** chooses when they learn they died (at dawn, or at once by day), publicly, required (asked again
    until legal). Evil chosen: the Klutz's team loses at once (an evil Klutz choosing evil: good wins); their sobriety
    at the choice decides; not touched by the Vortox. The Klutz is a claimable public ability, so anyone may fake a
    Klutz choice (it does nothing).

### Playability

48. **Sects & Violets plays end to end**: `Script('snv')` loads, random games run at every size with and without the
    rules judge, the player prompt is written (Trouble Brewing's with sentences swapped: madness and what the
    Storyteller hears, character and alignment changes, the Vortox, visits, the Juggler's guesses, the new response
    fields), and its replay fingerprints are recorded (`tests/data/fingerprints-snv.json`). The prompt tells players
    to assume the Storyteller hears everything, whispers included, which is true under the default hearing and safe
    under the others.

New weights: `savant_same_kind` 0.5, `savant_both_false` 0.7, `sweetheart_townsfolk` 0.9.
