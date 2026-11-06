# Voice review: Bad Moon Rising rulings

(For the owner: start a new chat on claude.ai, attach or paste this whole file, switch to voice mode and say "let's
start". Say "export" at any time to get the results block; paste that block back into Claude Code.)

---

## Instructions for Claude (read these first; don't read them aloud)

You are helping the owner of a Blood on the Clocktower AI benchmark review rulings, in voice mode. The owner is an
experienced Clocktower player and Storyteller. A game engine that plays the Bad Moon Rising script has been built, and
where the almanac and wiki left an interaction unclear, the engine had to pick a reading. Each ruling below says the
situation, the question, the options, and what the engine does now. The owner decides each one.

How to run the session:
- Speak naturally and briefly: this is a conversation, not a document. Never read IDs, headings, asterisks or
  formatting aloud, except to say "ruling 7 of 32" so the owner knows where they are.
- At the start, say in two sentences what this is and that there are 32 rulings in three groups, then optional extras
  (Storyteller weights and five judge questions). Tell them they can say "keep", "change", "skip", "go back",
  "explain", "pause", or "export" at any time.
- For each ruling: give the situation in one sentence, then the question, then the options, then what the engine does
  now and why. Then ask: keep it, change it, or come back to it later?
- If they want a change, let them explain, ask a short follow-up if the new ruling is ambiguous, then restate the
  ruling you will record in one or two plain sentences and get a yes before moving on.
- Record their reasoning too, in their words, briefly.
- Don't invent rules or claim certainty about official rulings; you may share what you know of Clocktower rules, but
  say when you are unsure. The owner's call is final.
- If they raise something new (a problem or idea not in the list), record it under "other".
- Keep a running tally in your head. When they say "export" (or when everything is done), output the block in the
  exact format at the end of this file, as text, including every ruling discussed so far. Rulings not yet discussed
  are left out. Then say it's ready to copy into Claude Code.

---

## Group 1: Demons and Minions (rulings 1 to 9)

**B1.1. The Assassin and the Zombuul.** The Assassin kills "even if for some reason they could not". The Zombuul
survives its first death and just seems dead. Question: when the Assassin attacks the Zombuul, is that a real death,
or only the Zombuul's seeming first death? And can the Assassin kill a Zombuul that already seems dead? Engine now: a
real death, and yes, it can. Reason: the almanac says a Fool killed by the Assassin dies and stays dead, so by
analogy the Assassin overrides survival abilities.

**B1.2. What triggers the Godfather.** The Godfather kills a player at night "if an Outsider died today". The almanac's
summary talks about an Outsider executed, but the ability text says died. Question: does any Outsider death during the
day count, or only an execution? Engine now: any death during the day, which the almanac's Tinker example supports.

**B1.3. The Pukka's victim while the Pukka is drunk.** The Pukka poisons a player each night, and the previously
poisoned player dies. Question: if the Pukka becomes drunk, is its victim still poisoned? Engine now: the poison
pauses while the Pukka is drunk and resumes when it sobers up, and the victim's death waits until then.

**B1.4. A Pukka that chooses itself.** Question: is the Pukka then stuck poisoned forever, or is it not poisoned by
its own poison, so that it dies the next night as "the previously poisoned player"? Engine now: the second.

**B1.5. The Shabaloth's regurgitation.** The Shabaloth may bring back one of the players it killed the night before.
Questions: may it regurgitate on a night it isn't woken (because the Exorcist chose it)? Engine now: yes, if it is
sober. Only a player it chose on the night before counts, and only if it was woken that night. A regurgitated player
with a first-night-only ability, like the Grandmother, is not woken again to use it.

**B1.6. The Devil's Advocate's protection.** The Devil's Advocate picks a player who won't die if executed tomorrow.
Question: does that protection fail if the Devil's Advocate is drunk or dead by the time of the execution, or does it
hold once made? Engine now: it fails, following the almanac's Minstrel example.

**B1.7. The Mastermind's extra day.** If the Demon dies by execution, the Mastermind gives evil one more day, and
whoever is executed that day loses for their team. Question: does executing an already-dead player that day count?
Engine now: yes, their team loses, and a dead player's team is their alignment at that moment.

**B1.8. The Godfather's plus or minus one Outsider.** The Storyteller chooses one more or one fewer Outsider. Engine
now: a coin flip between the options the setup can deal, with no preference. Question: should the Storyteller lean one
way, and if so how much?

**B1.9. A drunk or poisoned Godfather's false information.** The Godfather starts knowing which Outsiders are in play.
Question: what should an impaired Godfather see? Engine now: a list with the same number of Outsiders as the truth if
possible, otherwise another number the setup allows, and false on the usual share of nights, about 80%.

---

## Group 2: Townsfolk that protect, make players drunk, or bring players back (rulings 10 to 21)

**B2.1. When an ability's drunkenness ends early.** The Sailor, the Innkeeper and the Minstrel make players drunk until
a stated dusk. Question: if the one who caused it dies, does the drunkenness last to its stated dusk anyway, or end?
Engine now: it ends with its source, the general rule for ongoing effects, as with the Poisoner.

**B2.2. A drunk or poisoned Sailor or Innkeeper.** Question: does their ability do nothing, or does the Storyteller
still make someone drunk? Engine now: it does nothing, and an impaired Innkeeper protects nobody.

**B2.3. What the Innkeeper's protection covers.** Engine now: it stops every death that night except the Assassin's,
including one caused by a Townsfolk's own ability, like the Gambler's wrong guess. It ends at dawn, so a Tinker dying
at dawn isn't stopped. It only holds while the Innkeeper is sober and alive, so an Innkeeper who made themselves the
drunk one protects nobody. Question: is that right?

**B2.4. What the Sailor can't die from.** Engine now: while sober and healthy, the Sailor can't die from anything,
execution included, even before they've woken that night. Only the Assassin gets through. Question: is that right?

**B2.5. A Courtier who chooses their own character.** Question: is the Courtier then drunk for three nights and three
days, or is it a paradox that cancels itself? Engine now: the Courtier is drunk, following the plain text. Also, a dead
player of the chosen character is made drunk too.

**B2.6. Declining a character choice.** Engine now: a Courtier who names no character keeps their ability for later.
A Gambler who names no character gets one at random, with a notice. Question: should the Gambler be asked again
instead?

**B2.7. Who the Minstrel affects.** Engine now: when a Minion really dies by execution and the Minstrel is sober and
alive at that moment, every other player is drunk until dusk the next day, dead players included. Question: is that
right?

**B2.8. The Exorcist details.** Engine now: the Demon the Exorcist chose learns who the Exorcist is, but being told
that isn't "waking" for the Chambermaid's count. A Zombuul that seems dead can be exorcised. "Different from last
night" means the last night the Exorcist actually chose, even after a night they were dead. Question: any of these
wrong?

**B2.9. The Tea Lady.** Engine now: her protection goes by her neighbours' true alignment, recomputed every time a
death would happen. It skips dead neighbours and a Zombuul that seems dead. With only one other player alive, who is
her neighbour on both sides, she protects them if they're good. Question: is that right?

**B2.10. When the Pacifist decides.** Engine now: the Storyteller decides just before a good player's execution, and
only if nothing else would already save them, like the Sailor or the Tea Lady. The Pacifist's save comes before the
Fool's own ability, so a Fool the Pacifist saves keeps their ability. The Pacifist can save themselves. Question: is
that right?

**B2.11. The Gambler's guess.** Engine now: a guess is wrong if it isn't the player's character. The Gambler's death
is from their own ability, so the Innkeeper, the Tea Lady and the Fool can stop it, and it doesn't count as a Demon
kill for the Grandmother. Question: is that right?

**B2.12. The Professor.** Engine now: the Professor may choose any player who appears dead, including a Zombuul that
seems dead, or no one. The ability is used up whatever happens. A revived Townsfolk with a "you start knowing" ability
wakes at once to learn it again, but a player the Shabaloth regurgitates does not. Question: is that right?

---

## Group 3: Information roles, the Gossip, and the Outsiders (rulings 22 to 32)

**B3.1. The Grandmother's own death.** The Grandmother dies if the Demon kills her Grandchild. Question: can a
protection on her, like the Innkeeper's or the Tea Lady's, stop that death, or is it unstoppable? Engine now: a
protection stops it. Also, only the Demon's kill counts (its attack, or the Pukka's poison death), with the
Grandmother sober and alive at that moment. The Grandchild is chosen at setup, any good player but her, usually a
Townsfolk.

**B3.2. A resurrected Grandmother.** If the Professor brings the Grandmother back, question: is she shown the same
Grandchild, or does the Storyteller pick a new one? Engine now: the same one.

**B3.3. Misinformation for drunk players.** Engine now: any drunk or poisoned player can be given false information,
at the same rate, about 80% of nights. (Before, only poisoned players could.) Question: should drunk players be
treated the same as poisoned ones?

**B3.4. What the Chambermaid counts.** Engine now: every player woken to make a night choice counts, including a drunk
one, an Assassin who declines, and the Lunatic woken as their Demon, plus every information role shown something,
like the Grandmother and the Godfather on the first night. Being told something isn't waking: a Demon the Exorcist
chose, the Goon learning their new alignment, the Demon learning the Lunatic's choices. Question: is that right,
especially counting the Lunatic?

**B3.5. The Gossip's statement.** Engine now: only the living Gossip's first statement each day counts; later ones are
just heard. It's judged true or false when made, and kills that night only if the Gossip is alive and sober then.
Simple statements are checked by code, like "Alex is the Imp" or "the Tinker is in play"; anything else goes to the
Storyteller judge, and without a judge it's treated as not true. Question: should the first statement count, or the
last? And is the rest right?

**B3.6. Whom the Gossip kills.** When the Gossip's statement is true, the Storyteller chooses who dies. Engine now:
never the Demon, since that would end the game by the Storyteller's choice; preferably a player who will actually die,
not a protected one or the Fool; usually a good player; and with three players left, one who won't die if there is
one. Question: is that the right approach?

**B3.7. The Goon.** The first player to choose the Goon each night is drunk, and the Goon takes their alignment.
Engine now: that player is drunk before their ability acts on anyone. A Courtier naming the Goon counts; the
Storyteller's choices and the Moonchild's day choice don't. The biggest question: when the Lunatic chooses the Goon,
does it count? Engine now: yes, the Lunatic becomes drunk, which changes nothing, and the Goon turns good. The option:
it doesn't count, since the Lunatic has no real Demon ability. Also: the chooser's drunkenness ends if the Goon dies,
or it could last until dusk. And the Goon is told only when their alignment changes.

**B3.8. The Lunatic.** Engine now: the Lunatic usually believes they are the Demon actually in play; their fake Minions
are any players, half the time including the real Demon; their bluffs may include characters in play. They're woken
only when their Demon would be. The real Demon learns on the first night who the Lunatic is and which Demon they think
they are, and each night whom they chose, even on a night the Exorcist stops the real Demon. The question: when the
Exorcist chooses the Lunatic, does nothing happen, or should the Lunatic be treated as exorcised to keep the illusion
going, meaning they'd learn who the Exorcist is? Engine now: nothing happens, and the Lunatic is told nothing.

**B3.9. The Tinker.** Engine now: the Tinker may die at its night step and at each point of the day: dawn, after each
discussion round, before nominations, and at dusk. Never while protected, drunk or poisoned, and never with three or
fewer players alive, since that would end the game. A daytime death is announced at once, never why. Question: is
that right?

**B3.10. The Moonchild.** When the Moonchild learns they died, they publicly choose an alive player, who dies tonight
if good. Engine now: they're asked straight away, at dawn after a night death or at once after a day death. The
question: should the town get one round of discussion first? The almanac says they can take their time and get
advice. Also: a Moonchild who names no alive player gets one at random, with a notice, rather than being asked again.

**B3.11. Random practice bots.** In the free test games, random bots claim a public ability, like the Gossip's, on
about 8% of discussion turns and 4% of comment turns. This only affects free testing, not real games. Question: is
that fine, or should they claim more or less often?

---

## Optional extras (ask whether they want to continue)

### The Storyteller's weights

How often the scripted Storyteller does something, when no judge is used. For each, say the number in plain words, for
example "a quarter of the time", and ask whether it feels right.

**W.1. shabaloth_regurgitate**: the Shabaloth regurgitates on a quarter of nights when it can.
**W.2. regurgitations**: at most about two regurgitations a game; after that it's a tenth as likely.
**W.3. regurgitate_evil**: one time in ten, the regurgitated player may be evil.
**W.4. sailor_townsfolk_drunk**: when the Sailor chooses a Townsfolk, that Townsfolk is the drunk one 80% of the time.
**W.5. sailor_self_drunk**: when the Sailor chooses an Outsider, Minion or Demon, the Sailor is drunk 80% of the time.
**W.6. innkeeper_self_drunk**: an Innkeeper who chose themselves is the drunk one 80% of the time.
**W.7. innkeeper_good_drunk**: of a good and an evil player, the good one is drunk 90% of the time.
**W.8. pacifist_save**: the Pacifist saves an executed good player one time in five.
**W.9. pacifist_late**: two times in five when five or fewer players are alive.
**W.10. pacifist_again**: one time in twenty after it has already saved someone.
**W.11. pacifist_never**: in one game in ten, the Pacifist never saves anyone.
**W.12. grandchild_townsfolk**: the Grandchild is a Townsfolk three times in four, when there's a choice.
**W.13. gossip_victim_evil**: the Gossip's victim is an evil player one time in five, when one would die.
**W.14. tinker_never**: in one game in ten, the Tinker never dies by its ability.
**W.15. tinker_night**: the Tinker dies at its night step about one night in seven.
**W.16. tinker_day**: at each point of the day, a half-percent chance, about twelve chances a day.
**W.17. lunatic_same_demon**: the Lunatic believes they're the Demon actually in play four times in five.
**W.18. lunatic_shows_demon**: half the time, the real Demon is among the Lunatic's fake Minions.
**W.19. lunatic_bluff_in_play**: each of the Lunatic's fake bluffs is a character actually in play one time in four.

### Five questions about the Storyteller judge

**J.1. Who is ahead.** The judge's balance calls depend on who it thinks is winning. Now: evil is ahead with three or
fewer alive and the Demon among them, or with no evil player dead and either four or fewer alive or at least half the
good team dead; good is ahead with an evil player dead and five or more alive, or when the Demon is on the block;
otherwise it's close. Are those the right thresholds?
**J.2. The Slayer and the Recluse in a close game.** With no balance reason either way, the Recluse dies to the
Slayer one time in five. The wiki's player tips say the Slayer will usually kill a Recluse. Should that lean higher?
**J.3. The Tinker's day checks.** These are most of the judge's decisions. With a paid model judge, should only the
Tinker's night step go to the model, and the day checks stay simple?
**J.4. The Demon's bluffs.** A model judge sees a shortlist of 40 of the possible sets of bluffs. Enough, or should
bluffs stay with the simple scripted Storyteller?
**J.5. Night choices when the judge hears only public speech.** It sees only the latest night's choices. Should it see
every night's, as a human Storyteller would?

---

## Export format (output exactly this, as plain text in one block, when asked to export)

```
CLOCKTOWER-REVIEW v1
date: <today>
rulings:
- id: B1.1
  decision: keep
  why: <the owner's reasoning, briefly, in their words; may be empty>
- id: B1.2
  decision: change
  ruling: <the new ruling, in one or two plain sentences, as confirmed with the owner>
  why: <the owner's reasoning>
- id: B2.6
  decision: later
  why: <what they want to think about>
weights:
- id: W.8
  decision: change
  value: <the new number, as a fraction, e.g. 0.3>
  why: <reasoning>
judge:
- id: J.1
  decision: change
  answer: <their answer>
  why: <reasoning>
other:
- <anything new the owner raised, one item per line>
end
```

Rules for the block: one entry for every ruling, weight or question discussed, in the order discussed; `decision` is
exactly keep, change or later; include `ruling` (or `value`, or `answer`) only for a change; leave out anything not
discussed; omit a section that is empty; never paraphrase a confirmed ruling differently from what the owner agreed.
