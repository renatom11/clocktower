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
