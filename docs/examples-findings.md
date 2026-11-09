# The official examples as tests: findings

Every worked example in the wiki's character pages (their "Examples" sections), and in the almanacs where the wiki
has none, is a scenario test in `tests/examples/`: the example's setup, its actions, and its stated outcome. Where
the engine disagrees, the test is kept but skipped (`@unittest.skip("disagrees with the example: finding ...")`),
and the disagreement is written up here: what the example says (paraphrased), what the engine does instead (checked
by running it), and which kind of disagreement it is. Examples that need a character the engine does not build
(Travellers, Fabled, homebrew) are counted and left out. Examples that settle a question still open for the owner
are listed under each section's "Examples that answer open questions", whether or not the engine agrees. The tests
run with the suite or on their own: `python -m unittest discover -s tests/examples`. The open questions they answer
are put to the owner in docs/review/everything-open-voice.md (each part's instructions list them; EC-20, EBMR-1 and
EBMR-2 are items there of their own).

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
empty answer as declining (the Po, the Assassin, the Professor and the Courtier alike). Put to the owner:
docs/review/everything-open-voice.md, item B.6.

**EBMR-2. Does the Goon's waking to learn its new alignment count for the Chambermaid?** Example (wiki:
Chambermaid, example 2): on night 2 the Chambermaid picks the Grandmother and an evil Goon and is shown 2, a false
count, since picking the Goon first made her drunk; the example adds that of those two only the Goon wakes that
night, so the true count is 1. Engine: the Goon turns good and is told so, but `bmr.chambermaid_choice` counts only the
players in `Grimoire.woke`, and being told an alignment is not waking for an ability, so the true count is 0 (the
false 2 is still shown, as the example has it). Kind: a deliberate ruling the example contradicts: docs/bmr-rulings.md
B3.4 (kept in the owner's review) lists "the Goon learning its alignment" as not waking. The example reads the
Goon's wake as its own ability's, as against the Shabaloth woken by the Exorcist (Chambermaid example 1, which the
engine agrees with). A fix would record the Goon in `Grimoire.woke` when its alignment changes at night (the
Chambermaid's step is last, so every such change has happened by then). Put to the owner:
docs/review/everything-open-voice.md, item B.7.

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

Tests: `tests/examples/test_carousel_examples.py`, and `tests/examples/test_carousel_extra_examples.py` for the five
removable characters of batch 6 (one class each, so reverting a character deletes only its class). Rulings are
numbered as in `docs/carousel-rulings.md`.

- **EC-1. The Damsel: one guess for the whole Minion team.** Example: the Boomdandy guesses the wrong player, then
  the Goblin guesses the Damsel correctly, and nothing happens (wiki: Damsel, example 2; the page's summary says the
  Minions share one guess). Engine: each Minion has a guess of their own, so the Goblin's right guess ends the game for
  evil. A deliberate ruling the example contradicts: ruling 16, whose listed option ("one guess for the whole Minion
  team") the example settles.
- **EC-2. The Politician most responsible without an execution.** Example: with three alive the Politician talks the
  town out of executing; evil wins that night, and the Storyteller judges the Politician most responsible, so they
  win with evil (wiki: Politician, example 1). Engine: the Politician turns evil only when the game ends on the
  execution of the Politician or of their nominee; here they stay good and lose. A deliberate ruling: ruling 25 (its
  options "count a claim" or "let a judge rule" would cover it).
- **EC-3. The Fisherman's advice is free advice.** Example: the advice "don't trust Ben", Ben being a poisoned Empath
  (wiki: Fisherman, example 1); example 2's "keep the claimed Outsiders alive" is of the same kind. Engine: the advice
  is one of the checked statements (the Savant's, and "X is the Y"), which can say how many players are impaired but
  not that a named player is, nor give a course of action. A deliberate ruling: ruling 23 (option: a judge writes free
  advice). Example 2's test checks the rules part only and passes.
- **EC-4. The Hatter's tea party: taking a character a later player holds.** Example: after the Hatter's death the
  Assassin becomes the Mastermind; the Mastermind, wishing to stay, must choose again (the character is taken) and
  becomes the Assassin, who then kills again (wiki: Hatter, example 3). Engine: a player may only take a character no
  other player has at that moment, so the Assassin cannot take the Mastermind's (with only those two Minions on the
  script, neither is even asked). A deliberate ruling the example contradicts: ruling 27.
- **EC-5. The Plague Doctor: the Storyteller with the Organ Grinder's ability.** Example: the Storyteller has had the
  Organ Grinder's ability for two days; the Plague Doctor made drunk later changes nothing (wiki: Plague Doctor,
  example 3). Engine: the Organ Grinder is not among the abilities the Storyteller can gain (`PLAGUE_USABLE`), so the
  choice is illegal. A deliberate ruling: ruling 28 (its list of usable abilities); the example's own point (later
  drunkenness changes nothing) is untested for want of the ability.
- **EC-6. The High Priestess pointed at an evil player.** Examples: a sober High Priestess is shown the Goblin, whom
  the Storyteller thinks she should find out early (wiki: High Priestess, example 1), and on the last night the Imp,
  whose story clashes with others' (example 2). Engine: a sober High Priestess is only pointed at a living player of
  her own team; the evil player is illegal. A deliberate ruling: ruling 41, whose option ("point a good High Priestess
  at the Demon sometimes") both examples settle.
- **EC-7. A preached Minion is not woken.** Example: the Cerenovus chosen by the Preacher learns it and is not woken
  to use their ability (wiki: Preacher, example 2). Engine: the Minion is woken as usual and their choice does
  nothing ("no ability" is played as drunk). A deliberate ruling: ruling 46. (Example 3, the Pit-Hag woken again once
  the Preacher is poisoned, agrees.)
- **EC-8. A Pixie who gains the Washerwoman's ability learns nothing.** Example: the Pixie, mad about being the
  Washerwoman, gains her ability when she is executed, and that night learns that one of two players is the Monk
  (wiki: Pixie, example 1). Engine: the Pixie gains the ability and is told so, but is never given the Washerwoman's
  information, neither at once nor on a later night. An engine bug: ruling 40 says a "you start knowing" ability
  gained this way acts at once, and for the Washerwoman it does not (her ability acts only at her first-night step).
  **Fixed** in 2280a5f: `InfoRole.becomes` gives a Washerwoman, Librarian, Investigator or Chef ability that begins after
  the first night its information at once (by day, "Day n"), whether gained (the Pixie's, the Cannibal's, the
  Philosopher's) or become (the Pit-Hag's). The Pixie learns it the day the Washerwoman is executed, not that night;
  the test passes.
- **EC-9. The Boffin's abilities: the Virgin, the Chambermaid, the Banshee.** Examples: the Imp with the Virgin's
  ability executes the Alsaahir who nominates it (wiki: Boffin, example 1); the Lord of Typhon with the Chambermaid's
  wakes each night, and not while the Boffin is drunk (example 2); the Kazali with the Banshee's nominates and votes
  twice once dead (example 3). Engine: none of these three is offered (`carousel3.boffin_options`: the Washerwoman,
  Librarian, Investigator, Chef, Empath, Undertaker, Monk, Noble, Village Idiot and Goon only), so the Boffin gives no
  ability. A deliberate ruling: ruling 76 (its list).
- **EC-10. The Xaan with no Outsiders.** Example: with no Outsiders in play the Xaan never poisons anyone (wiki: Xaan,
  example 3). Engine: X = 0 does mean no poison, but a dealt game never has the Xaan and no Outsiders: its setup step
  adds one. A deliberate ruling the example contradicts: ruling 79 ("a dealt game with none gets one", a reading).
- **EC-11. A Snitch created later gives the Minions bluffs.** Example: the Pit-Hag creates a Snitch on the fourth
  night, and every Minion learns three characters not in play (wiki: Snitch, example 3). Engine: the Snitch acts on the
  first night only; a Snitch made later gives nothing. A deliberate ruling the example contradicts: ruling 91 ("on the
  first night only").
- **EC-12. The Hermit's Butler's and Drunk's abilities.** Examples: a Hermit with the Klutz's, Butler's and Recluse's
  abilities chooses a master each night (wiki: Hermit, example 1); a Hermit with the Drunk's, Mutant's and
  Sweetheart's believes he is the Exorcist and acts as one (example 2). Engine: the Hermit never holds the Butler's
  ability (one master a game) nor the Drunk's (an illusion dealt at setup), so neither is held. A deliberate ruling:
  ruling 107 (option: a Hermit with the Drunk on the script is drunk all game). The other abilities of both examples
  are held.
- **EC-13. A Princess made later: her first day is one day late.** Example: the Pit-Hag makes the Dreamer the Princess
  on night 4; that day she nominates the Zealot, who is executed, and that night the Kazali's choice, the Princess,
  lives (wiki: Princess, example 2). Engine: a Princess made on night n has her first day set to day n + 1, but the day
  after night n is day n in the engine, so day 4's execution does not count and the Kazali kills her. An engine bug
  (`carousel5.Princess.becomes` adds one for a change made at night): ruling 105 says "the next day she is one".
  **Fixed** in 07c9b12: made at night n, her first day is day n; the test passes.
- **EC-14. The Yaggababble's deaths come by day.** Example: having said the phrase twice today, the Yaggababble kills
  the Heretic and the Golem as each nominates, with a Witch in play to hide it (wiki: Yaggababble, example 2). Engine:
  the deaths come at the Yaggababble's step the next night, so nobody dies by day. A deliberate ruling: ruling 130.
  (Example 1, deaths at night, agrees.)
- **EC-15. The Amnesiac's abilities outside the list.** Examples: an Amnesiac whose ability detects whether either of
  two chosen players is a Minion (wiki: Amnesiac, example 1), and one who learns how many living neighbours are
  Townsfolk (example 2). Engine: the ability is drawn from a curated list of 31 (`carousel6.AMNESIAC`), and neither is
  on it (its nearest are the Fortune Teller's Demon check and the Empath's evil count), so neither can be drawn. A
  deliberate ruling: ruling 132.
- **EC-16. The Atheist's Storyteller breaks rules by day.** Example: with the Atheist in play, the Investigator learns
  a false Minion pair (the engine allows this), the Sweetheart dies nominating with no Witch, and the Slayer's shot
  kills the Gossip (wiki: Atheist, example 1). Engine: the Storyteller's rule breaks are a bounded set (a fake evil
  team, false information, a night death); nobody dies by day, so the Slayer's shot kills nobody. A deliberate ruling:
  ruling 153 (its option "more breaks"). Example 2 (an extra Outsider, then the Storyteller executed: good wins)
  agrees: the deal is accepted and good wins.
- **EC-17. The Wizard's wishes outside the list.** Examples: every good player drunk (wiki: Wizard, example 2), the
  Wizard becoming a Demon (example 3), and winning the game (example 4), each granted. Engine: the wish is one of a
  list of eight (`carousel_extra.WISHES`); none of these is on it, and wishes that end the game are left out by design.
  The scripted matching of words to the list also misreads example 2: "all good players are drunk" becomes the wish
  to see the Grimoire (its keyword "all" scores as high as "drunk"). A deliberate ruling: ruling 157.
- **EC-18. The Alchemist is never asked to choose differently.** Example: the Alchemist with the Poisoner's ability
  tries to poison the Lord of Typhon; the Storyteller asks for another choice, and they poison the King (wiki:
  Alchemist, example 2). Engine: the choice stands and the Demon is poisoned. A deliberate ruling: ruling 71, whose
  option ("let a judge refuse a choice") the example settles.
- **EC-19. Legion: a vote of only evil players counts zero.** Example: with four alive, three Legion vote for Julian,
  who is not executed; Alex, with two votes, one of them good, is executed instead (wiki: Legion, example 2; the page
  says the tally of an only-evil vote is zero). Engine: Julian's three votes put him on the block, and his execution
  then fails, so nobody dies; Alex's two votes never beat three. A deliberate ruling the example contradicts: ruling
  165 ("the execution fails").
- **EC-20. Legion: one good player left is evil's win.** Example: with a Fortune Teller and a Slayer the last good
  players, the Slayer and six Legion vote the Fortune Teller out, and evil wins (wiki: Legion, example 1; the page says
  the Storyteller may declare evil's win when one good player is left). Engine: the execution succeeds (a good player
  voted), but the game goes on. An open question the example answers: no ruling covers it (ruling 164 plays on to
  two alive). Put to the owner: docs/review/everything-open-voice.md, item C7.7.
- **EC-21. A jinxed creation is refused and the Pit-Hag chooses again.** Example: with the Pit-Hag and the Heretic
  jinxed, a Pit-Hag's attempt to make a Heretic is refused by the Storyteller, and she picks some other
  character (wiki: Djinn, example 1, the jinx example). Engine: the creation does nothing and the Pit-Hag is not asked
  again. A deliberate ruling: ruling 51 ("nothing happens"). (The Djinn's example 2, a jinx in effect with neither
  character in play, agrees: ruling 4.)
- **EC-22. A number in a wish in words is read as the list's number.** Example: a Wizard's wish of five lives for
  everyone and every reminder token in play is declined as too awkward, and the Storyteller asks for another wish
  (wiki: Wizard, example 5). Engine: the first number in the words is taken as the wish's number on the list, so this
  is wish 5 (see the Grimoire), granted. An engine bug (`carousel_extra.Wizard.offer`): ruling 158 matches a wish in
  words to the list, and only a bare number should be read as one. (Without the number, the engine declines the wish
  and the Wizard may wish again on a later night, not at once.) **Fixed** in 904fec7 (inside the Wizard's section of
  carousel_extra.py): only a bare number ("5", "wish 5") is the list's number; words with a number in them go to the
  Storyteller's match. The test forces the Storyteller's match to "none", as the example has it (the scripted match
  reads "all" as the Grimoire's keyword, EC-17), and passes.
- **EC-23. The Storyteller's execution is not on the record of executions.** Example: with no Atheist in play, the
  Politician claims the Atheist and the town executes the Storyteller: evil wins, and the Politician with them (wiki:
  Politician, example 3; tested with the Politician as the nominator). Engine: evil wins, but the execution of the
  Storyteller is not written to `Grimoire.executions`, so the Politician's floor (ruling 25: the nominator of the
  executed player) does not see it, and the Politician stays good. An engine bug in the Atheist's core change
  (`carousel_extra.Atheist.nominee_executed`). **Fixed** in 35e270a (inside the Atheist's section of carousel_extra.py): the
  Storyteller's execution is on the record; the Politician who nominated wins with evil, and the test passes.

### Examples that answer open questions

- Damsel, example 2: ruling 16's option, one guess for the Minion team (EC-1).
- High Priestess, examples 1 and 2: ruling 41's option, a good High Priestess may be shown an evil player (EC-6).
- Alchemist, example 2: ruling 71's option, the Storyteller may refuse a choice and ask again (EC-18).
- Legion, example 2: ruling 165, an only-evil vote counts zero rather than failing the execution (EC-19); example 1:
  with one good player left the Storyteller may end the game for evil, which no ruling covers (EC-20).
- Nightwatchman, examples 2 and 3: ruling 20. A drunk Nightwatchman's chosen player learns nothing (not another
  player), and under the Vortox the chosen player is shown another player; the engine allows both (its 50% weight
  `nightwatchman_shown_other`), and the examples reject the option "the target always learns the truth".
- Mezepheles, example 3: ruling 120's option "count visits too". The Noble says the word to the Storyteller in private,
  and only the Courtier's drunkenness keeps him good, so a word said on a visit counts. The engine does not count it;
  the outcome (he stays good) is the same, so the test passes.
- Princess, example 2: ruling 105's reading of "your 1st day" for a Princess made later, the day after she is made
  (the engine means the same; it was a day late, EC-13, now fixed).
- Politician, example 3: ruling 154's reading that executing the Storyteller with no Atheist in play is evil's win (its
  option "no effect" is rejected); the engine agrees on the winner, and since EC-23's fix on the Politician too.
- Vizier, example 2: ruling 116, "if good voted" means any good voter (two evil and one good voted, and the Vizier
  executed); its option "most voters were good" is rejected. The engine agrees.
- Preacher, example 3: ruling 46's present-tense reading (a Minion gets their ability back once the Preacher is
  poisoned; its option "the Minions stay silenced" is rejected). The engine agrees.
- Engineer, example 2: ruling 103, a new character's setup part does not happen and a changed one is not undone (the
  Baron made the Boomdandy leaves the two extra Outsiders). The engine agrees.
- Lycanthrope, example 2: ruling 68, "the Demon doesn't kill tonight" covers the Pukka's delayed kill of last night's
  poisoned player. The engine agrees.
- Widow, example 3: the Widow's poison pauses while she is drunk and resumes when she is sober (ruling 54, finding B5
  in `docs/interaction-findings.md`). The engine agrees.
- Cannibal, example 2: a poisoned Cannibal who ate an evil player is woken as the character the executee claimed
  (ruling 47's `cannibal_lie_claim`). The engine agrees.

### Counts

164 examples read: the 162 in the "Examples" sections of the 66 built experimental characters' wiki pages, and the
Djinn's two jinx examples (the only wiki page whose examples are about jinxes between built characters). Every wiki
page in scope has examples, so the Kickstarter almanac was not needed. 164 tests: 137 pass, 26 are skipped as
disagreements (EC-1 to EC-23 but the four engine bugs EC-8, EC-13, EC-22 and EC-23, fixed since), and 1 is skipped as
not buildable (Widow, example 2: the Scapegoat is a Traveller).
Tests that check only the rules part of an example about the players' reasoning say so in their docstring (the
General's three, Fisherman 2, Harpy 3, Marionette 1 and 2, Mezepheles 2, Wraith 1).
