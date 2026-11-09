# The official examples as tests: where the engine disagrees

Every worked example in the wiki's "Examples" sections (and the almanacs', where the wiki has none) for a built
character is a scenario test in `tests/examples/`. A test the engine disagrees with is kept, skipped with its finding's
number, so the suite stays green and the disagreement is on record. Each finding gives the example (paraphrased) and
its source, what the engine does instead (verified by running the test unskipped), and which kind it is: an engine
bug, a deliberate ruling the example contradicts, an open question the example answers, or an ambiguous reading. The
engine is not changed by this work.

## Trouble Brewing

## Bad Moon Rising

## Sects & Violets

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

### Examples that answer open questions

- Damsel, example 2: ruling 16's option, one guess for the Minion team (EC-1).
- High Priestess, examples 1 and 2: ruling 41's option, a good High Priestess may be shown an evil player (EC-6).
- Nightwatchman, examples 2 and 3: ruling 20. A drunk Nightwatchman's chosen player learns nothing (not another
  player), and under the Vortox the chosen player is shown another player; the engine allows both (its 50% weight
  `nightwatchman_shown_other`), and the examples reject the option "the target always learns the truth".
- Widow, example 3: the Widow's poison pauses while she is drunk and resumes when she is sober (ruling 54, finding B5
  in `docs/interaction-findings.md`); the engine agrees.
- Cannibal, example 2: a poisoned Cannibal who ate an evil player is woken as the character the executee claimed
  (ruling 47's `cannibal_lie_claim`); the engine agrees.
