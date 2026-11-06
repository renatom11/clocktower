# Bad Moon Rising: rulings to review

Where the almanac and wiki leave an interaction unclear, the engine had to pick a reading. Each entry says the
question, the options, what the engine does now, and why. These are for the owner to confirm or change; each change
is a small edit in `clocktower/bmr.py` plus its test in `tests/test_bmr.py`. The Storyteller's new weights are in
`state.POLICY`, marked "default, for review".

## Batch 1: Demons and Minions

1. **The Assassin and the Zombuul.** Is the Assassin's kill (a) real or (b) only the Zombuul's apparent first
   death? Can the Assassin kill a Zombuul that already seems dead? **Engine: (a) real, and yes**, by analogy with
   the Fool, who "dies and stays dead" when the Assassin kills them ("even if for some reason they could not").
2. **What triggers the Godfather.** The almanac's summary says an Outsider "executed and dies"; the ability text
   says an Outsider died today. **Engine: any death by day**, which the almanac's Tinker example supports.
3. **The Pukka's victim while the Pukka is drunk.** Still poisoned, or not until the Pukka sobers? **Engine: the
   poison pauses** ("the poison resumes" when the Pukka sobers up).
4. **A Pukka that chooses itself.** Stuck poisoned forever, or not poisoned by its own poison (and dying the next
   night as "the previously poisoned player")? **Engine: the second.**
5. **The Shabaloth's regurgitation.** It may regurgitate even on a night it isn't woken (the Exorcist), if sober;
   only a player it chose on the night before, and only if it was woken that night; a regurgitated player with a
   first-night-only ability is not woken again for it.
6. **The Devil's Advocate's protection.** Does it fail if the Devil's Advocate is drunk or dead at the time of the
   execution, or hold once made? **Engine: it fails** (the almanac's Minstrel example).
7. **The Mastermind's extra day.** Executing an already-dead player that day counts as "a player executed": their
   team loses. A dead player's team is their alignment at that moment.
8. **The Godfather's -1 or +1 Outsider.** Uniform between the options the setup can deal; no weight yet.
9. **An impaired Godfather's false Outsider list.** The same number of Outsiders as the truth where possible,
   otherwise another number the setup allows; false on the usual share of nights (`poisoned_false`).

New weights: `shabaloth_regurgitate` 0.25 (per night with a candidate), `regurgitations` 2 (per game; beyond it the
chance is a tenth), `regurgitate_evil` 0.1 (the regurgitated player may be evil).

## Batch 2: Townsfolk that protect, make players drunk, or bring players back

1. **When an ability's drunkenness ends early.** Does the drunkenness the Sailor, the Innkeeper or the Minstrel
   causes last to its stated dusk whatever happens, or end if its source dies? **Engine: it ends with its source**
   (the general rule for ongoing effects, as with the Poisoner), like the Innkeeper's protection, which the almanac's
   Tinker example ends when the Innkeeper dies that night.
2. **A drunk or poisoned Sailor or Innkeeper** makes nobody drunk (and the Innkeeper protects nobody): the ability
   does nothing. The Storyteller could instead still pick a drunk player; the engine does not.
3. **The Innkeeper's protection** stops every death tonight but the Assassin's, including a Townsfolk's own ability
   (the Gambler's: "safe from death caused by ... Townsfolk"), and ends at dawn (a Tinker death at dawn is not
   stopped). It holds only while the Innkeeper is sober and alive, so an Innkeeper made drunk by their own choice
   protects nobody (the almanac's example).
4. **The Sailor can't die** from any cause, execution included, while sober and healthy, even before waking; only the
   Assassin's kill gets through.
5. **A Courtier who chooses themself.** (a) Drunk for three nights and days, or (b) a paradox that cancels itself
   (as batch 1 read the Pukka poisoning itself)? **Engine: (a)**, the plain text. A dead player of the chosen
   character is made drunk too ("in play").
6. **Declining a character choice.** A Courtier who names no character, or one not on the script, declines (keeps
   the ability). A Gambler who names none gets one at random, with a notice (the core's rule for a choice that
   must be made). Option: re-ask the Gambler instead.
7. **The Minstrel** drinks every other player, dead ones too, but not Travellers, until the dusk after the next day.
   It triggers only for a Minion who really dies by execution, with the Minstrel sober and alive at that moment.
8. **The Exorcist.** The Demon is told who the Exorcist is; that telling is not waking for an ability (the
   Chambermaid does not count it). A Zombuul that seems dead can be exorcised. "Different to last night" means the
   last night the Exorcist chose (after a night they were dead, still that one). How the Exorcist treats the
   Lunatic is left to batch 3: today the Lunatic still wakes.
9. **The Tea Lady** goes by alignment, recomputed at each death, and skips dead neighbours and a Zombuul that seems
   dead. With one other player alive (her neighbour on both sides), she protects them if they are good.
10. **When the Pacifist decides.** Just before a good, living player's execution, and only if nothing else would save
    them (the Sailor, the Tea Lady, the Devil's Advocate): then there is nothing to decide. The Pacifist decides
    before the Fool's own ability, so a Fool the Pacifist saves keeps their ability ("If another character's ability
    protects the Fool"). The Pacifist can save themself.
11. **The Gambler's guess** is wrong when it is not a character the player could register as (in Bad Moon Rising,
    their character). The death is the Gambler's own ability's, so the Innkeeper, the Tea Lady and the Fool can stop
    it, and it does not count as a Demon kill (the Grandmother).
12. **The Professor's options** are the players who appear dead (a seeming-dead Zombuul is one; a player the Shabaloth
    regurgitated is not), or no one. The ability is spent whatever the choice does. A revived "you start knowing"
    Townsfolk wakes at once through the new `resurrected` hook; a player the Shabaloth regurgitates does not (batch 1,
    ruling 5).

New weights: `sailor_townsfolk_drunk` 0.8 (a chosen Townsfolk is the drunk one), `sailor_self_drunk` 0.8 (with an
Outsider, Minion or Demon chosen, the Sailor is), `innkeeper_self_drunk` 0.8 (an Innkeeper who chose themself is the
drunk one), `innkeeper_good_drunk` 0.9 (of a good and an evil player, the good one; two alike, either),
`pacifist_save` 0.2 (per good execution before the first save), `pacifist_late` 0.4 (the same, with five or fewer
alive), `pacifist_again` 0.05 (after a save), `pacifist_never` 0.1 (per game, never saves). The Sailor's, the
Innkeeper's and the Pacifist's decisions go through the Storyteller judge.

## Batch 3: the information Townsfolk, the Gossip, and the Outsiders

1. **The Grandchild** is chosen when the game is set up: any good player but the Grandmother (the Lunatic and the Goon
   count), usually a Townsfolk. Her death is her own ability's kill, so a protection on her (the Innkeeper's, the Tea
   Lady's) stops it; option: make it unstoppable. Only the Demon's kill counts (its attack, and the Pukka's poison
   death), with the Grandmother sober and alive at that moment.
2. **A resurrected Grandmother** (the Professor) is shown the same Grandchild again: the reminder stays where it was.
   Option: the Storyteller picks a new one.
3. **Misinformation for drunk players.** Before, only a poisoned player (or the Drunk) could be given false
   information; now any drunk or poisoned player can, at the same rate (`poisoned_false`). Trouble Brewing is
   unchanged (nothing there makes a player drunk); this also affects the Godfather's Outsider list.
4. **What the Chambermaid counts:** every player woken to make a night choice (a drunk one, an Assassin who declines,
   the Lunatic woken as their Demon) and every information role shown something (the Grandmother and the Godfather on
   the first night). Being told something is not waking for an ability: a Demon the Exorcist chose, the Goon learning
   its alignment, the Demon learning the Lunatic's choices. An impaired Chambermaid is shown a false count when
   misinformed, any of the other two.
5. **The Gossip's statement** goes through the shared `ability` move. Only the living Gossip's first statement each
   day counts (later ones that day are just heard); option: the last. It is judged as it is made, whatever the
   Gossip's sobriety then, and kills that night only if the Gossip is alive and sober at their step. The engine checks
   simple forms ("X is (not) the Y", "X is evil/good", "X is a Townsfolk/Outsider/Minion/Demon", "the Demon is X", "the
   Y is (not) in play", "there is no Y in play", with "I am the Gossip." and "My statement is:" ignored in front);
   anything else goes to the judge (true, false, or doesn't count), and without a judge is not true.
6. **Whom the Gossip kills.** The scripted Storyteller never picks the Demon (the game would end by its choice),
   prefers a player who will actually die (not protected, not the Fool), usually a good one, and with three players
   alive picks one who won't die if there is one.
7. **The Goon.** The first player to choose the Goon each night is drunk before their ability acts on anyone (the
   Shabaloth's, the Po's and the Assassin's picks land one at a time). A Courtier naming the Goon counts; the
   Storyteller's choices (the Grandchild, the Gossip's victim) and the Moonchild's day choice don't. **The Lunatic
   choosing the Goon counts** (the Lunatic is drunk, which changes nothing, and the Goon turns good); option: it
   doesn't, since the Lunatic has no Demon ability. The Assassin's sobriety is settled as it chooses, so a sober
   Assassin kills the Goon, who turns evil. The chooser's drunkenness ends if the Goon dies (batch 2, ruling 1); option:
   it lasts until dusk. A drunk or poisoned Goon has no ability. The Goon is told only when its alignment changes;
   its seat keeps the model of the team it was dealt.
8. **The Lunatic's illusion.** They usually believe they are the Demon in play; their "Minions" are any players, as
   many as there are Minions, half the time including the real Demon; their bluffs may include characters in play,
   never the Lunatic. They are woken at the Lunatic's step as their Demon, and only when that Demon would wake (a
   Lunatic-Zombuul after a day with no death, a Lunatic-Pukka on the first night, a Lunatic-Po charging after choosing
   no one). The real Demon is told on the first night who the Lunatic is and which Demon they believe they are, and
   each night whom they chose, before it acts (even on a night the Exorcist stops it). **An Exorcist who chooses the
   Lunatic does nothing**: the Lunatic is not the Demon and is told nothing; option: treat them as exorcised to keep
   the illusion (they would learn who the Exorcist is). The belief probe asks the Lunatic what it asks evil players.
9. **The Tinker** may die at its night step (a judged decision) and at each point of the day (dawn, each beat,
   nominations, dusk; the scripted style, since those hooks don't wait), never while protected, drunk or poisoned, or
   with three or fewer players alive (it would end the game). A day death is announced at once ("X dies."), never why.
10. **The Moonchild** chooses at dawn after dying at night, and at once after dying by day. They are asked directly;
    option: give the town one round of comments first (the almanac: they "can take their time and get advice"). A
    choice naming no alive player is completed at random with a notice. Whether it kills depends on the target's
    alignment at the choice and the Moonchild's sobriety that night (a dead Moonchild can be drunk or poisoned). Anyone
    can claim the Moonchild's ability through the `ability` move as a bluff; the real Moonchild's choice is announced
    the same way.
11. **Random seats** claim a public ability on about 8% of town-square turns and 4% of comment turns, with a
    statement of a checkable form or one only a judge can rule on, only when the request offers claimable characters
    (never in Trouble Brewing, whose random seats are unchanged).

New weights: `grandchild_townsfolk` 0.75 (the Grandchild is a Townsfolk, when there are both), `gossip_victim_evil`
0.2 (the Gossip's victim is an evil player, when one would die), `tinker_never` 0.1 (per game), `tinker_night` 0.15
(per night), `tinker_day` 0.005 (per point of the day, about 12 a day), `lunatic_same_demon` 0.8, `lunatic_shows_demon`
0.5 (the real Demon among the Lunatic's Minions), `lunatic_bluff_in_play` 0.25 (per bluff). The Grandmother's,
the Chambermaid's, the Gossip's (statement and victim) and the Tinker's night decisions go through the Storyteller
judge.
