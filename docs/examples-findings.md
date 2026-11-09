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
  two alive).
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
  and the Wizard may wish again on a later night, not at once.)
- **EC-23. The Storyteller's execution is not on the record of executions.** Example: with no Atheist in play, the
  Politician claims the Atheist and the town executes the Storyteller: evil wins, and the Politician with them (wiki:
  Politician, example 3; tested with the Politician as the nominator). Engine: evil wins, but the execution of the
  Storyteller is not written to `Grimoire.executions`, so the Politician's floor (ruling 25: the nominator of the
  executed player) does not see it, and the Politician stays good. An engine bug in the Atheist's core change
  (`carousel_extra.Atheist.nominee_executed`).

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
  (the engine means the same, but is a day late: EC-13).
- Politician, example 3: ruling 154's reading that executing the Storyteller with no Atheist in play is evil's win (its
  option "no effect" is rejected); the engine agrees on the winner (the Politician's part is EC-23).
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
page in scope has examples, so the Kickstarter almanac was not needed. 164 tests: 133 pass, 30 are skipped as
disagreements (EC-1 to EC-23), and 1 is skipped as not buildable (Widow, example 2: the Scapegoat is a Traveller).
Tests that check only the rules part of an example about the players' reasoning say so in their docstring (the
General's three, Fisherman 2, Harpy 3, Marionette 1 and 2, Mezepheles 2, Wraith 1).
