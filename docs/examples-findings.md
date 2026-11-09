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

## Experimental characters
