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
