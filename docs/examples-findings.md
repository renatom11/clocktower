# The official examples as tests: findings

Every worked example in the wiki's character pages (their "Examples" sections), and in the almanacs where the wiki
has none, is a scenario test in `tests/examples/`: the example's setup, its actions, and its stated outcome. Where
the engine disagrees, the test is kept but skipped (`@unittest.skip("disagrees with the example: finding ...")`),
and the disagreement is written up here: what the example says (paraphrased), what the engine does instead (checked
by running it), and which kind of disagreement it is. Examples that need a character the engine does not build
(Travellers, Fabled, homebrew) are counted and left out. Examples that settle a question still open for the owner
are listed under each section's "Examples that answer open questions", whether or not the engine agrees.

## Trouble Brewing

`tests/examples/test_tb_examples.py`: 71 examples on the 22 characters' wiki pages, plus 1 in the almanac the wiki
lacks (the Soldier's, with the Mayor); 64 tests, 62 passing and 2 skipped as disagreements; 8 examples not
buildable. Trouble Brewing play is frozen (protocol v17), so these findings
are recorded only, never fixed.

Not buildable (each needs a Traveller): Chef 3 (an evil Scapegoat), Empath 2 (an evil Gunslinger), Undertaker 3
(two exiled Travellers), Mayor 3 (two exiled Travellers), Recluse 5 (an evil Traveller), Saint 2 (the Gunslinger),
Saint 3 (the Scapegoat), Scarlet Woman 1 (three Travellers).

**ETB-1. The Chef and a Recluse between two evil players.** Example (wiki: Chef, example 4): the Recluse sits
between the Imp and the Poisoner, and the Chef learns a 1, because the Recluse registers as evil for the pair with
the Imp but as good for the pair with the Poisoner. Engine: `state.chef_choice` lets each player register one way
for the whole count (every combination of each player's possible registrations), so with the Imp, the Recluse and
the Poisoner in a row the only legal answers are 0 (the Recluse good) and 2 (the Recluse evil); forcing a 1 raises
"illegal Storyteller value". Kind: a deliberate reading of the engine's (one registration per player per piece of
information) that the example contradicts; no numbered ruling covers it. Frozen: recorded only. A fix would let a
misregistering player count per pair, so `chef_choice`'s legal set would become every count from the pairs where
both are evil for certain up to the pairs where both might be (here 0, 1 and 2); the scripted style would not need
to change (so the scripted fingerprints could stay as they are), but the legal set and the judge's options would,
whenever a Chef sees a Spy or a Recluse next to another evil player.

**ETB-2. The Mayor's death passed to a player the Demon cannot kill.** Example (almanac TB: Soldier, the third
example, not on the wiki): the Imp attacks the Mayor, the Storyteller chooses the Soldier to die instead, and since
the Soldier is safe from the Demon nobody dies. Engine: `state.mayor_choice` offers only players who are not safe
from the Demon (the Mayor and the unprotected others), so choosing the Soldier raises "illegal Storyteller value",
and an attack on a sober Mayor always kills someone. Kind: a deliberate design of the engine (no numbered ruling)
that the example contradicts. Frozen: recorded only. A fix would add the safe players to the Mayor choice's legal
values and have `Game.attempt_kill_judged` check the redirected victim's protection again (today it kills whoever
the redirect returns); the scripted style could keep its picks, so only judged games would change.

Read narrowly, as the engine allows (no disagreement, but noted): Butler 2 has the master lower their hand at the
last moment. The engine asks each vote once, a master sitting later being asked first, so the test checks the rule
underneath: the Butler's vote counts only if the master's final vote is yes.

### Examples that answer open questions

None of the Trouble Brewing examples settles an item in docs/review/everything-open-voice.md, docs/bmr-rulings.md
"Still open" or the U-items of docs/interaction-findings.md.

## Bad Moon Rising

`tests/examples/test_bmr_examples.py`: 74 examples on the 25 characters' wiki pages, plus 1 in the almanac the wiki
lacks (the Tinker's sudden death on day 3); 74 tests, 72 passing and 2 skipped as disagreements; 1 example not
buildable. The other almanac examples repeat the wiki's.

Not buildable: Tea Lady 2 (a good Matron and a good Judge, both Travellers, and an exile).

Tested in part, the Traveller's share left out (each says so in its docstring): Devil's Advocate 3 (the Judge forcing
an execution), Minstrel 1 and Fool 2 (the Judge's execution is an ordinary one here), Minstrel 2 (an Apprentice
exiled), Pacifist 3 (a Bishop exiled), Gossip 2 (a good Townsfolk sits in the good Traveller's seat).

**EBMR-1. An optional choice of a player who is not an option.** Example (wiki: Professor, example 3): a drunk
Professor picks the Minstrel, unaware the Shabaloth has regurgitated them; the Storyteller refuses (only the dead may
be picked), so the Professor picks the dead Fool; being drunk, nothing comes of it, and the once-per-game ability is
used up. Engine: `Game.wake` reads a night answer through `Game.targets`, which drops names that are
not among the options; the Professor's choice is optional (`min_targets` 0), so `Game.insist` finds nothing to ask
again and the illegal pick counts as choosing no one. The Professor is not asked again, does not choose the Fool,
and keeps the ability. Kind: a gap in the owner's "Required choices, generally" (docs/bmr-rulings.md, the owner's
review): it re-asks required choices only, so an optional choice that names an illegal player is silently taken as
declining. Suggested fix: re-ask an optional choice that named players but none legal, with the reason, and take an
empty answer as declining (the Po, the Assassin, the Professor and the Courtier alike).

**EBMR-2. Does the Goon's waking to learn its new alignment count for the Chambermaid?** Example (wiki:
Chambermaid, example 2): on night 2 the Chambermaid picks the Grandmother and an evil Goon and is shown 2, a false
count, since picking the Goon first made her drunk; the example adds that of those two only the Goon wakes that
night, so the true count is 1. Engine: the Goon turns good and is told so, but `bmr.chambermaid_choice` counts only the
players in `Grimoire.woke`, and being told an alignment is not waking for an ability, so the true count is 0 (the
false 2 is still shown, as the example has it). Kind: a deliberate ruling the example contradicts: docs/bmr-rulings.md
B3.4 (kept in the owner's review) lists "the Goon learning its alignment" as not waking. The example reads the
Goon's wake as its own ability's, as against the Shabaloth woken by the Exorcist (Chambermaid example 1, which the
engine agrees with). A fix would record the Goon in `Grimoire.woke` when its alignment changes at night (the
Chambermaid's step is last, so every such change has happened by then).

### Examples that answer open questions

- **B.1 (old B1.3), the Pukka's victim while the Pukka is drunk** (docs/review/everything-open-voice.md, Part C):
  Pukka example 2 settles it as the engine reads it. The Pukka poisons the Gossip; the next night the drunk Pukka's
  poison on the Tinker does nothing, and the Gossip does not die; the night after, the Pukka sober again, the Gossip
  dies. So the poison pauses and the death waits (`test_pukka_example_2`, passing).
- **B.4, the fresh-instance question**: Professor example 2 has the resurrected Grandmother learn "a good player's
  character" again, so a revived "you start knowing" ability is used again, as the engine does for the Professor
  (`test_professor_example_2`, passing); it does not say whether she is shown the same Grandchild (old B3.2 stays
  open on that). Moonchild example 3 has a regurgitated Moonchild's ability work a second time (passing). No example
  covers a regurgitated first-night ability; the almanac's Shabaloth How to Run (not an example) says such a player
  wakes at once to use it, which supports the suggested change.
- **B.5, the Gossip without a judge**: Gossip example 1 (the Demon "wearing a hat") kills no one, which the scripted
  engine gets right: a statement it cannot check counts as not true. Gossip example 2's statement ("both my
  neighbours are good") is a natural, checkable claim outside the engine's simple forms: without a judge it would
  count as not true and the Chambermaid would live; the test forces the Storyteller's decision to rule it true. A
  form for neighbours' alignment ("my neighbours are good / evil", "one of my neighbours is evil") would let the
  engine check this one.

## Sects & Violets

Tests: `tests/examples/test_snv_examples.py`, on the real S&V script. 79 wiki examples (all 25 characters) and 4
almanac-only ones (Town Crier, Evil Twin, Fang Gu and No Dashii; the almanac's ending to Vigormortis example 2 is
folded into that test): 85 tests (two extra: Mutant example 2 without the overheard whisper, Barber example 4 without
the good Demon). 75 pass, 4 are skipped as disagreements (below), 6 as not buildable: four need Travellers (Clockmaker
3, Flowergirl 3, Town Crier 2, Witch 5) and two are about the real room (Savant 1: glasses and a couch; Artist 1: chair
colours). Oracle 2 and Vortox 5 are tested without their Travellers (Oracle 2 then counts 3, not 4), and Savant 3 only
for its "X is evil" half. Mathematician 3: the wiki has the Mathematician learn 4, the almanac 3; either is a legal
false number under the Vortox (the test forces 4).

**ESNV-1. The Artist's question that is not yes/no.** Example: the Artist asks how many Minions are alive; the
Storyteller asks for another question, since it can't be answered yes, no or "I don't know" (wiki: Artist, example 3;
the almanac's How to Run says the same). Engine: the scripted Storyteller answers "I don't know" and the ability is
spent; a second question gets "you have already asked your one question". Kind: a deliberate ruling,
docs/snv-rulings.md 42 ("a question that is not yes/no gets 'I don't know' and spends the ability"), whose listed
option (the judge may say "ask again" without spending it) is what the example does. It answers open question S3.9.

**ESNV-2. A private report about the Mutant.** Example: the Witch tells the Storyteller in private that the Mutant
told them they are the Klutz, and the Storyteller executes the Mutant (wiki: Mutant, example 2). Engine: under the
default hearing (`--judge-hears all`, a judge) the Mutant's own whisper is overheard and they are executed, so the test
of the example passes. But the report itself counts for nothing: with the scripted Storyteller (no judge) or a judge
hearing only `public`, the Witch's visit text ("Blair told me he is the Klutz") does not make the Mutant break
madness, and nobody is executed (test `test_mutant_example_2_report_only`). Kind: a deliberate ruling, 36 ("the
scripted floor reads only the visitor's own words"; a model judge reads every visit's text); the example says a third
player's report is enough to act on. It answers open question S3.3, and bears on S1.1.

**ESNV-3. The Mutant's silence.** Example: the Mutant claims to be a Townsfolk without saying which and stays silent
when asked whether they are the Mutant; after a while the Storyteller executes them (wiki: Mutant, example 3).
Engine: not executed, with no judge or with the rules judge (hearing all): the floor (`state.madness_broken`,
must=False) breaks the Mutant only on an Outsider claim or a confession, and silence is neither. A model judge is told
that silence counts. Kind: a deliberate ruling, 2 (the floor is "a floor, not the judgment"; option: a lenient or
stricter scripted Storyteller) and 44. It answers open questions S1.2 and S3.11: silence when questioned counts.

**ESNV-4. The Mutant's denial with a wink.** Example: the Mutant claims the Oracle with invented information, then
says they are definitely not the Mutant, winking; the Storyteller executes them (wiki: Mutant, example 4). Engine: not
executed, with no judge or with the rules judge: there is no Outsider claim, and for the Mutant a denial is not
evidence (and "I am definitely not the Mutant" is not even read as a denial: the pattern wants "I am not"). The wink
cannot be represented. Kind: a deliberate ruling, 2 (the floor) and 44. It answers S1.2 and S3.11: a pointed denial
can itself be the hint.

### Examples that answer open questions

Open questions are docs/review/everything-open-voice.md Part A (S1.x, S2.x, S3.x) and docs/interaction-findings.md
(U-n). "Agrees": the engine already does what the example shows.

- S1.1, S3.3 (what the Storyteller hears; visits as reports): Cerenovus 3, a private hint that the player is mad is
  overheard and fatal (agrees under the default hearing). Mutant 2: a third player's private report is enough (ESNV-2).
- S1.2, S3.11 (the madness floor): Cerenovus 1, an emphatic "no" when asked about madness is safe (agrees). Mutant 3
  and 4: silence and a winking denial count against the Mutant (ESNV-3, ESNV-4).
- S1.3, S3.6 (when madness is judged): Mutant 1, executed seconds into day 1 with no nominations that day. The engine
  judges at the pre-nomination checkpoint: the same outcome (agrees), though the example's "immediately" leans to
  "at any time".
- S1.12 (the Cerenovus may pick a dead player): Cerenovus 2 (agrees).
- S1.5 (character changes are told truly): Vortox 4, the Juggler made the Witch learns it truly under the Vortox
  (agrees); Seamstress 3 and Pit-Hag 3, alignment is kept (agrees).
- S1.13 (in play; dead players can be changed): Pit-Hag 2, Vigormortis 3 (agrees).
- S1.14 (the Pit-Hag's arbitrary deaths): Pit-Hag 4 (only the evil Demon dies on the final night) and Sage 3 (the
  Sage killed this way learns nothing) (agrees).
- S1.16 (the Evil Twin's win): Evil Twin 2 and 4 (a good twin executed for madness, a good Evil Twin executed: evil
  wins); Vigormortis 2 with the almanac's ending (a dead Evil Twin kept by the Vigormortis still wins on the good
  twin's execution); Evil Twin almanac 2 (good wins only once both the Demon and the Evil Twin are dead) (agrees).
- S1.17 (pairing a new Evil Twin): Pit-Hag 3 (agrees).
- S1.18 (the Fang Gu's jump): Fang Gu 1 (the jump is not the Sweetheart's death) and almanac 2 (a dead Outsider does
  not jump) (agrees).
- S1.21 (the Vortox at dusk): Vortox 2 (a madness execution counts) and 5 (a Witch death does not) (agrees).
- S2.1 (what the Mathematician counts): Mathematician 1-3 (a poisoned player's true result and a poisoned Snake
  Charmer picking a Townsfolk are not counted; Vortox false results and a drunk Witch's cursed nominator are)
  (agrees).
- S2.6 (the Dreamer): Dreamer 2 (a Philosopher with a gained ability is shown as the Philosopher) and 3 (the bluff may
  be shown) (agrees).
- S2.7 (the Snake Charmer): Snake Charmer 3 (an evil Snake Charmer charming the Demon: both stay evil) (agrees).
- S2.9 (yes/no on a day with no nominations): Vortox 2 (agrees).
- S2.12 (the Sage): Sage 2 (drunk, final night: a dead and a living player) and 3 (agrees).
- S3.4, S3.8 (the Philosopher): Philosopher 2 (a first-night ability gained later acts at once) and 3 (the original
  sobers when the Philosopher dies or is drunk) (agrees).
- S3.9 (the Artist): Artist 3 (ESNV-1); Artist 4 ("I don't know" for an unknowable question) (agrees).
- S3.10 (the Juggler's day): Juggler 2 (the first day as the Juggler, after a change) (agrees).
- S3.12 (the Sweetheart): Sweetheart 1-3 (any player, the Demon included) (agrees).
- S3.13, U6 (the Barber's swap onto a dead player): Barber 2 and 4. A swap with a dead player is allowed, and the
  example's reasoning (the game goes on because a good Demon lives) confirms U6's rule that a Demon moved onto a dead
  player is a dead Demon: without the good Demon the engine has good win
  (`test_barber_example_4_without_the_good_demon`) (agrees). It does not settle U6's question about the
  Vigormortis's kept abilities.

## Experimental characters
