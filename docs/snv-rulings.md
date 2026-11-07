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
   players you trust") is always fatal, and the S&V player prompt (not written yet) must say what the Storyteller
   hears. Reports to the Storyteller ("snitching") need a player-to-Storyteller channel, which does not exist yet.
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
