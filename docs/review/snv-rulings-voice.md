# Voice review: Sects & Violets rulings

(For the owner: start a new chat on claude.ai, attach or paste this whole file, switch to voice mode and say "let's
start". Say "export" at any time to get the results block; paste that block back into Claude Code.)

---

## Instructions for Claude (read these first; don't read them aloud)

You are helping the owner of a Blood on the Clocktower AI benchmark review rulings, in voice mode. The owner is an
experienced Clocktower player and Storyteller. A game engine that plays the Sects & Violets script has been built, and
where the almanac and wiki left an interaction unclear, the engine had to pick a reading. Each ruling below says the
situation, the question, the options, and what the engine does now. The owner decides each one.

How to run the session:
- Speak naturally and briefly: this is a conversation, not a document. Never read IDs, headings, asterisks or
  formatting aloud, except to say "ruling 7 of 48" so the owner knows where they are (count rulings in the order they
  appear in this file).
- At the start, say in two sentences what this is and that there are 48 rulings in three groups, with the madness
  rulings first in each group that has them because they matter most, then optional extras (Storyteller weights and
  three judge questions). Tell them they can say "keep", "change", "skip", "go back", "explain", "pause", or "export"
  at any time.
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
- IDs: S1.n is ruling n of batch 1 in the rulings document, S2.n ruling n of batch 2, S3.n ruling n of batch 3, in
  that document's order. In group 3 the madness rulings are asked first, so its IDs are not in sequence; always use
  the ID written on the ruling.

---

## Group 1: the core, the Minions, the Evil Twin and the Demons (rulings 1 to 21)

**S1.1. Madness: what the Storyteller hears. This is the most important ruling; take it slowly.** When the
Storyteller decides whether a mad player broke their madness today, it looks at what that player said aloud, their
nominations and defences, and the character abilities they publicly claimed, from the moment they were made mad,
never anyone's private thoughts. The scripted Storyteller hears only what was said aloud, as a human Storyteller
would. But a Storyteller judge, by default, also hears every whisper. So under the default, a mad player who whispers
"I'm actually mad" to one friend is overheard, and that confession is fatal: they can be executed for it, as in the
almanac's Flowergirl example. The judge can be set to hear only public speech, but that is not the default. Question:
when judging madness, should the Storyteller hear whispers? Options: one, as now, the judge hears whispers by default;
two, never whispers, for any judge; three, a random share of whispers is overheard, so a private confession is a risk
rather than certain death. Engine now: option one. What follows: the wiki's advice to the Mutant, to come out secretly
to one or two trusted players, is always fatal, and the players are told to assume the Storyteller hears everything,
whispers included. Reporting a mad player to the Storyteller in private is possible only by visiting the Storyteller,
which comes up in group 3.

**S1.2. Madness: the minimum test.** The Cerenovus makes a player mad about being a good character. Engine now: the
scripted Storyteller and the simple rules-based judge say the player broke madness unless they claimed that character
aloud, it is still the latest character they claimed, and they never said they aren't it or that they're mad, like "I
am mad" or "the Cerenovus picked me". Saying "I'm not mad" is fine, as in the almanac's Barber example. For the
Mutant, who must not be mad about being an Outsider, claiming an Outsider or saying they're mad breaks it. This is
only a floor: a model judge also weighs effort, hints and how the story builds. Question: should the scripted
Storyteller sometimes be lenient, at a set chance, since it can't judge effort?

**S1.3. Madness: when it is judged, and the day of a madness execution.** Engine now: the Cerenovus's target is judged
once a day, after private conversations and the town square, before nominations open. An execution for madness is the
day's one execution, and the day goes straight to night with no nominations, as the almanac says. What they say
during nominations doesn't count. Question: is once, before nominations, right? Options: also judge at dusk, seeing
nominations and defences, though someone may already have been executed, and the almanac also allows executing them
the next day; or judge after every part of the day, closer to "at any time" but many more judge calls.

**S1.4. Madness: "might be executed".** Engine now: a good player who broke madness is executed nine times in ten,
because the rulebook says it's the player's choice even when it ends the game; an evil one half the time, because the
almanac says "might" lets the Storyteller stop evil using madness as a strategy. The rules-based judge always executes
a good one and decides an evil one by how the game stands. A drunk or poisoned Cerenovus makes nobody mad, and neither
does one who loses their ability before the judgment, for example by dying, unless the Vigormortis killed them.
Question: is that right?

**S1.5. Character changes.** When a player's character changes, engine now: they're told at once, in private, their
new character and ability, and whether they're now evil or still good. This is never false, even under the Vortox or
when drunk or poisoned. The new ability starts fresh, even a once-per-game one an earlier holder used, following the
Barber's almanac entry. The old character's ongoing effects end, so a poisoner who changes stops poisoning. A player
who becomes a Demon isn't told the Minions, and the Minions aren't told. A new Evil Twin is paired, and an Evil Twin
whose twin changed side is dealt with. If the new character's night step is still to come tonight, they act tonight.
Question: is that right?

**S1.6. Dead players keeping their ability.** The Vigormortis's dead Minions keep their ability. Engine now: it's kept
as a Minion ability, so a dead Minion who becomes another Minion keeps it, and one who becomes a Townsfolk doesn't.
While it's kept they wake at their step, the ability works and its effects carry on; once lost, the effects end. If
the Vigormortis is drunk or poisoned, its Minions have no ability. Question: is that right?

**S1.7. Poison worked out fresh.** The No Dashii's and the Vigormortis's poison isn't placed once; it's worked out
again whenever someone's sobriety matters, so it follows every change at once. A poison never touches its own source:
the No Dashii isn't poisoned by its own poison. Question: is that right?

**S1.8. Information that must be false.** Under the Vortox, Townsfolk information must be false. Engine now: no
scripted choice or judge can give a true answer. Whether it counts as Townsfolk information goes by the character the
player believes they are. If no false answer exists, the true one is given, since there is nothing false to give. It
also works for Trouble Brewing information roles, so a custom script mixing them works. Question: is that right,
especially giving the true answer when nothing false exists?

**S1.9. Abilities set off by someone else's nomination or execution.** For example, the Evil Twin's when the good twin
is executed. Engine now: the nominee's own reaction, like the Virgin's, comes first, then everyone else's. An
execution counts whether or not the player dies, so executing a dead player counts too. Question: is that right?

**S1.10. Setup changes from the Demon.** The Fang Gu adds an Outsider and the Vigormortis removes one. Engine now:
these count. Removing an Outsider when there are none removes nothing and adds no extra Townsfolk. Bad Moon Rising's
Godfather keeps its old dealing, so those games are unchanged, though its setup check now also accepts that lower
count, which the official rule allows. Question: is that right?

**S1.11. The Witch.** Engine now: only a sober, healthy Witch makes a curse. The curse pauses while the Witch is drunk
or poisoned and comes back when she sobers, as in the rulebook's example; it follows the player through a character
change, and ends when the Witch loses her ability, unless the Vigormortis killed her. With three players alive, the
Witch loses her ability at once, a curse already made included, and isn't woken. A cursed player's death is announced
at once, never why. Question: is that right?

**S1.12. The Cerenovus.** It may choose any player, alive or dead, itself too, and any good character on the script.
Question: when the Cerenovus is drunk or poisoned, is the target still told they're mad? Engine now: yes, so nothing
gives the wasted ability away, but nobody is executed for it. Option: tell them nothing.

**S1.13. The Pit-Hag: what "in play" means.** Engine now: a character is in play if any player has it, alive or dead;
the Drunk's apparent Townsfolk doesn't count. A dead player can be changed, and the Pit-Hag may change themself.
Question: is that right?

**S1.14. The Pit-Hag: deaths when a Demon is made.** The almanac lets deaths that night be arbitrary. Engine now: at
the Pit-Hag's step, the Storyteller decides up to two extra deaths and whether the Demons' attacks still kill. The
scripted Storyteller follows the almanac: a Demon made into another Demon, nobody dies four times in five; a new evil
Demon, the old Demon dies four times in five and the new one attacks as usual; a good Demon made on the final night,
four or fewer players alive, the evil Demon dies four times in five; otherwise, as usual. The rules-based judge has no
preference. Question: is that right? Options: let the Storyteller protect only chosen players, or allow more than two
deaths.

**S1.15. The Evil Twin's twin.** Engine now: any good player at setup, picked at random. Both always learn each other
truly, even if the Evil Twin is drunk on the first night, because it's knowledge of each other, like a character
change. Option: a drunk Evil Twin is shown a false pair.

**S1.16. The Evil Twin's win conditions.** "If the good player is executed, evil wins": engine now, whichever of the
two is good, even a good Evil Twin, executed alive or dead, while the Evil Twin has their ability, meaning alive and
sober, or dead with the ability kept by the Vigormortis. "Good can't win while you both live": both alive and the Evil
Twin sober. Question: is that right?

**S1.17. Re-pairing the twins.** Engine now: if the twins end up on the same side, for example the Fang Gu jumps into
the twin, the Storyteller picks a new twin of the other alignment, and both are told. A new Evil Twin made by the
Pit-Hag is paired at once; on the final night the twin may be the Demon or a dead player, if they're of the other
alignment. Question: is that right?

**S1.18. The Fang Gu's jump.** Engine now: the first Outsider it would kill becomes an evil Fang Gu and is told, then
the old Fang Gu dies. An Outsider who wouldn't die, already dead or protected, doesn't jump. It happens once a game,
remembered whatever happens to the Fang Gu. The new Fang Gu isn't told the Minions. Not handled: the Scarlet Woman
jinx, a custom-script case, where the Scarlet Woman would take over instead. Question: is that right?

**S1.19. The Vigormortis's poison.** It poisons a Townsfolk neighbour of each Minion it kills. Engine now: at the
kill, the Storyteller picks a side at random, and the nearest Townsfolk that way, alive or dead, is poisoned, worked
out again as things change, so one Townsfolk per Minion is always poisoned. Option: fix the player at the kill. Second
question: a dead Minion who is drunk or poisoned loses their own ability, but their poison goes on, because the
poison is the Vigormortis's ability. Option: it stops too. A kill that fails, on a protected Minion, keeps nothing.

**S1.20. The No Dashii.** Engine now: it poisons its nearest Townsfolk by character type, so an evil Townsfolk
counts, from the start of the game, whether the No Dashii is alive or dead. With only one Townsfolk in play, only that
one. Question: is that right?

**S1.21. The Vortox.** Engine now: every Townsfolk's information is false while it has its ability, so not while dead,
drunk or poisoned. At dusk, if nobody was executed today, evil wins. Executing a dead player counts, and so does a
madness execution; a Witch death doesn't. Question: is that right?

---

## Group 2: the information Townsfolk, and the Snake Charmer (rulings 22 to 33)

(Say once at the start of this group: every information result can be false for a drunk or poisoned player, is
always false under the Vortox, and a false result always fits some possible setup.)

**S2.1. What the Mathematician counts.** The Mathematician learns how many players' abilities worked abnormally
because of another character. Engine now counts: any information a working ability couldn't have given, so a drunk or
poisoned player's false result, and every false result under the Vortox, as the almanac does; a poisoned player who
happens to get true information doesn't count, as in the almanac's Empath example. It also counts abilities that
would have acted but whose holder was drunk or poisoned: the Demon's attack, the Witch's curse, including a cursed
nominator who lives, the Cerenovus's madness, the Pit-Hag's change when it would have worked, the Snake Charmer
choosing the Demon, and the Evil Twin when the good twin is executed. Not counted now: a kill stopped by protection,
which can't happen on this script; the Demon kills the Pit-Hag stops; a drunk or poisoned No Dashii or Vortox, whose
effects are continuous; the Recluse registering as evil; and the Drunk's own false results, which the official jinx
counts on scripts with both. Question: should any of those be counted?

**S2.2. The Mathematician's "since dawn".** Engine now: each night it counts players with an abnormal result from the
previous day or that night, and on the first night since the game began, each player once. Its own failures aren't
counted, since it doesn't detect its own ability failing, but another Mathematician's would be. Question: is that
right?

**S2.3. Votes and nominations as they happened.** Engine now: the Flowergirl and Town Crier go by each player's
character at the moment they voted or nominated, so a Demon who voted and was then swapped by the Snake Charmer that
night still counts as a Demon voting. A dead Demon's ghost vote counts. Question: is that right?

**S2.4. The judge and the Dreamer's bluff.** Engine now: when the Dreamer is shown a pair of characters, the
rules-based judge prefers a pair including the character the evil player claimed, as it already did for single
characters. Question: is that right?

**S2.5. The Clockmaker.** Engine now: it counts steps the short way round the circle, dead players included, from any
Demon to the nearest Minion by character type, so a good Minion made by the Pit-Hag counts. A false number is
anything from one to half the table. Question: a player who becomes the Clockmaker after the first night learns the
number at once, following the Barber's almanac entry. Options: at the next night, or never.

**S2.6. The Dreamer.** Engine now: it goes by character type, not alignment, so a good Witch is shown as the Witch
plus a good character. The scripted false character: for a good player, a Minion in play half the time, since the wiki
says almost always, otherwise any Minion or Demon. For an evil player, half the time the good character they last
claimed aloud, as the almanac suggests to help evil; otherwise a secretive good character three times in ten, like
the Snake Charmer, Sage, Mutant or Klutz; otherwise another, never the Dreamer itself. Misinformed or under the
Vortox, neither shown character is right. The scripted Storyteller only counts claims made aloud. Question: is that
right?

**S2.7. The Snake Charmer.** Engine now: it chooses living players only; choosing themself or a non-Demon does
nothing. Choosing the Demon, by character, a good Demon too, swaps characters and alignments, and both are told at
once. The old Demon is then poisoned for the rest of the game, even through later character changes, reading
"permanently" literally. Option: the poison ends once they stop being the Snake Charmer. The new Demon isn't told the
Minions and acts tonight. Question: is that right? (A charmed Vigormortis is a later ruling.)

**S2.8. The Mathematician's false number.** Engine now: misinformed, one or two off the truth; under the Vortox, any
number but the truth. Question: is that right?

**S2.9. The Flowergirl and the Town Crier.** Engine now: a yes or no about the day just past, not on the first night;
misinformed, the opposite. A day ended by a madness execution, with no nominations, gives no, or yes under the Vortox,
as in its almanac example. Question: is that right?

**S2.10. The Oracle.** Engine now: it counts dead players who are evil, at its step after the Demon's kill, so a
dead good Evil Twin isn't evil, and a Townsfolk turned evil is. Question: is that right?

**S2.11. The Seamstress.** Engine now: she may decline any night, and naming only one player counts as declining.
The ability is spent once two players are chosen, even if she's drunk or poisoned. Dead players may be chosen.
Question: is naming one player the same as declining?

**S2.12. The Sage.** Engine now: the Sage learns only if the Demon's own attack killed them tonight; the Vigormortis's
and Fang Gu's attacks count, but not the Witch, the Pit-Hag's extra deaths or an execution. They're shown that Demon
and another player; before the final night the other is alive nine times in ten, on the final night anyone.
Misinformed, two players who aren't that Demon, one dead and one alive on the final night, as in the almanac's drunk
Sage. Their sobriety at their step decides. Question: is that right?

---

## Group 3: visits to the Storyteller, the last Townsfolk, and the Outsiders (rulings 34 to 48; madness first)

**S3.3. Madness: what's said on a visit counts.** Players can now visit the Storyteller in private. Engine now: what a
player says there is madness evidence, heard by the Storyteller whatever the hearing setting, but it isn't "aloud",
so it doesn't count as claiming a character for the Cerenovus. This is the first way to report someone to the
Storyteller: a model judge reads everything said on every visit. The scripted Storyteller only checks the visitor's
own words about themself. Question: is that right?

**S3.6. Madness: when the Mutant is judged.** Engine now: twice a day. Once before nominations, on the day's talk, as
for the Cerenovus, and again at dusk, on what was said since, nominations and defences, if nobody was executed today.
Nothing is judged twice, and the "might be executed" chance is rolled each time. Never at night, since nobody talks.
Option: after every part of the day, closer to "at any time"; a madness execution would then end the day earlier.

**S3.11. Madness: the Mutant.** Engine now: the Mutant must not claim any Outsider, or just "an Outsider", aloud, in
a whisper the Storyteller hears, or on a visit, and must not say they're mad. They're judged at those two points and
executed by the usual chances, nine in ten if good, half if evil. Question: is that right?

**S3.1. The charmed Vigormortis.** This changes the earlier Snake Charmer ruling. Engine now: the dead Minions'
abilities and their poison belong to the Vigormortis character, not its player. When the Snake Charmer charms it, or
the Barber swaps it, they move to the new Vigormortis, whose sobriety then decides them; the old one, now the poisoned
Snake Charmer, keeps nothing. Option: they end, as before. Question: is that right?

**S3.2. Visiting the Storyteller.** On a private-time turn, any player may visit the Storyteller claiming a visiting
ability, the Savant's or the Artist's, with the Artist's question. The town sees who went, never why. A player with
the ability, or who believes they have it, is answered in private; anyone else is told the Storyteller listened and
nodded, which helps evil bluff, as the almanac suggests. Engine now: one visit a day per player, and a visit is that
turn's only conversation, so a whisper sent with it isn't sent. Options: allow a whisper alongside it, or more than
one visit a day. Dead players may visit, but are answered only if their ability works while dead, which none of
these do. Trouble Brewing and Bad Moon Rising are unchanged. Question: is that right?

**S3.4. Abilities gained from another character, the Philosopher.** Engine now: the player is woken at that
character's step as that character, and both the Philosopher and the drunk original act. A player whose character
changes loses the abilities gained through the old one; the almanac says the duplicate sobers up if the Philosopher
becomes a different character. Once-per-game abilities are spent per player, so the Philosopher and the original
each have theirs, and a player who becomes that character later starts fresh. Question: is that right?

**S3.5. How the Juggler guesses.** Engine now: the Juggler's guesses are a list version of the shared public-ability
move, up to five guesses of a player and a character, heard by the town, and offered only on scripts with such a
character. Question: is that right?

**S3.7. The Savant's statements.** Engine now: twelve kinds of statement, checked by code. For example, two players
are the same alignment; the Demon sits within one or two seats of a living player; exactly so many living players are
drunk or poisoned; a living player was chosen at night by someone's ability; a given character is in play; exactly so
many Outsiders; so many of the Savant's living neighbours are evil; a living player is evil; a Minion sits next to
the Demon; and from day two, everyone got true information last night, a Demon voted yesterday, a Minion nominated
yesterday, so many dead players are evil. The scripted Storyteller picks the true statement's kind at random,
favouring ones about living players, never a true "this player is evil" about the Demon, and nothing already said;
the false one is the same kind half the time. Drunk or poisoned, both false seven times in ten, otherwise both true;
under the Vortox, both false. The rules-based judge has no preference, and a model judge ranks a shortlist. Question:
is that right? Options: more kinds, like seat ranges or claims; a chance to favour statements about today's claims.

**S3.8. The Philosopher.** Engine now: they choose any Townsfolk or Outsider, or none, keeping the ability. It's spent
even if they're drunk or poisoned, which the Mathematician counts. The player who has the chosen character is drunk
while the Philosopher has their ability, including a player made that character later. A "you start knowing" ability
gained after the first night acts at once; on the first night, at its step. Choosing the Philosopher does nothing.
Question: is that right?

**S3.9. The Artist.** Engine now: simple questions are answered by code, like "is this player that character, evil,
or an Outsider", "is the Demon one of these three", "are these two the same alignment", or "is this character in
play"; misinformed or under the Vortox, the opposite. Anything else goes to the judge, who says yes, no, or "I don't
know"; the scripted Storyteller says "I don't know". The main question: a question that isn't yes or no gets "I don't
know" and spends the ability. The almanac says to ask them to rephrase. Option: the judge can say "ask again" without
spending it. An empty question isn't a use.

**S3.10. The Juggler's count.** Engine now: only a living Juggler's first claim with at least one guess, on their
first day as the Juggler, counts, drunk or not. Correct guesses are counted at once against true characters; that
night's sobriety decides what they learn, one off if misinformed, any other number under the Vortox. Question: a
claim with no guesses isn't a use. Option: it is, and they learn zero.

**S3.12. The Sweetheart.** Engine now: any death counts, and their sobriety as they die decides, so a drunk or
poisoned Sweetheart's death is wasted. The Storyteller makes another player drunk for the rest of the game, through
later changes. The scripted Storyteller picks a living good Townsfolk nine times in ten, otherwise any other living
player; the rules-based judge picks an evil player when evil is well ahead, otherwise a good Townsfolk. It's decided at
once. Question: is that right?

**S3.13. The Barber.** Engine now: a death by day gives haircuts the coming night, a death at night that night, and
the Barber's sobriety as they die decides. The Demon, picked at random if there are several, may choose two players,
alive or dead, themself included, never another Demon, or nobody; naming one counts as nobody. The swap keeps
alignments, and each is told. Question: is that right?

**S3.14. The Klutz.** Engine now: the Klutz chooses as soon as they learn they died, at dawn or at once by day,
publicly, and must choose, asked again until the choice is legal. If they choose an evil player, their team loses at
once, so an evil Klutz choosing evil makes good win. Their sobriety at the choice decides, and the Vortox doesn't
affect it. Anyone can fake a Klutz choice as a public claim; it does nothing. Question: is that right?

**S3.15. The script plays end to end.** Sects & Violets now loads and plays at every size, with and without the
rules-based judge. The players' instructions cover madness and what the Storyteller hears, character and alignment
changes, the Vortox, visits and the Juggler's guesses. They tell players to assume the Storyteller hears everything,
whispers included, which is true by default and safe otherwise. Question: is that the right advice to give players?

---

## Optional extras (ask whether they want to continue)

### The Storyteller's weights

How often the scripted Storyteller does something, when no judge is used. For each, say the number in plain words, for
example "a quarter of the time", and ask whether it feels right.

**SW.1. mad_execute_good**: a good player who broke madness is executed nine times in ten.
**SW.2. mad_execute_evil**: an evil player who broke madness is executed half the time.
**SW.3. pithag_quiet**: when the Pit-Hag turns a Demon into another Demon, nobody dies that night four times in five.
**SW.4. pithag_kill_old_demon**: when the Pit-Hag makes a new evil Demon, the old Demon dies four times in five.
**SW.5. pithag_final_kill**: when the Pit-Hag makes a good Demon on the final night, the evil Demon dies four times in
five.
**SW.6. final_night_alive**: a night counts as the final night when four or fewer players are alive at dusk (a count,
not a chance).
**SW.7. dreamer_minion_in_play**: a good player is shown to the Dreamer with a Minion in play half the time.
**SW.8. dreamer_bluff**: an evil player is shown as the good character they claimed aloud half the time.
**SW.9. dreamer_secretive**: otherwise, as a secretive good character three times in ten.
**SW.10. sage_alive**: before the final night, the Sage's second player is alive nine times in ten.
**SW.11. savant_same_kind**: the Savant's false statement is the same kind as the true one half the time.
**SW.12. savant_both_false**: a drunk or poisoned Savant gets two false statements seven times in ten.
**SW.13. sweetheart_townsfolk**: the Sweetheart's death makes a living good Townsfolk drunk nine times in ten.

### Three questions about the Storyteller judge

**J.1. The Pit-Hag's deaths.** The rules-based judge has no preference about deaths when the Pit-Hag makes a Demon, so
the scripted style decides. Should it lean by the balance of the game, for example killing the old Demon less often
when evil is behind?
**J.2. The Savant.** The rules-based judge has no preference among the thousands of possible statement pairs, and a
model judge sees only a shortlist. Enough, or should the shortlist favour statements about what was claimed today?
**J.3. The Sweetheart.** The rules-based judge makes an evil player drunk only when evil is well ahead. Is that the
right threshold, or should it sometimes pick an Outsider, as the almanac also allows?

---

## Export format (output exactly this, as plain text in one block, when asked to export)

```
CLOCKTOWER-REVIEW v1
date: <today>
rulings:
- id: S1.1
  decision: keep
  why: <the owner's reasoning, briefly, in their words; may be empty>
- id: S1.2
  decision: change
  ruling: <the new ruling, in one or two plain sentences, as confirmed with the owner>
  why: <the owner's reasoning>
- id: S2.6
  decision: later
  why: <what they want to think about>
weights:
- id: SW.1
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
