# The official examples as tests: findings

Every worked example in the wiki's "Examples" sections (and the almanacs' examples the wiki lacks) is a scenario test
under `tests/examples/`, one file per scope. A test the engine fails because it disagrees with the example is kept,
skipped with its finding's number, and written up here: what the example says (paraphrased), what the engine does
(verified by running it), and which kind of disagreement it is. Each scope also lists the examples that settle an open
question for the owner, even where the engine already agrees.

## Trouble Brewing

## Bad Moon Rising

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
