# Open decisions

Questions the extension beyond Trouble Brewing raises that are not settled yet. Each says what the problem is, what
is already handled, the options, and when it has to be decided. When one is settled, record the decision here (and
in `docs/protocol-history.md` if it changes play).

## 1. Seats that change team: how do we rate good against evil?

**The problem.** The eval puts one model on every good seat and another on every evil seat, and credits each game
to "good model vs evil model" (detection against deception). That assumes every seat stays on its starting team.
Several characters break it:

- **Goon** (Bad Moon Rising): "the 1st player to choose you with their ability is drunk until dusk. You become
  their alignment." A Goon chosen by an evil player turns evil, while the good team's model still plays the seat.
- **Snake Charmer** (Sects & Violets): choosing the Demon swaps the two players' characters and teams. The Demon
  is then played by the good team's model, and the old Demon is a good, poisoned Snake Charmer played by the evil
  team's model.
- **Fang Gu** (Sects & Violets): when it attacks an Outsider, that Outsider becomes the Fang Gu, so a good
  model's seat becomes the evil Demon.
- Custom scripts add more (Cult Leader, Bounty Hunter, Summoner, Kazali, Mezepheles, Politician, Ogre, ...), and
  some make the evil team's size or membership unknown until mid-game.

The Lunatic is not one of these: a Lunatic stays good and only believes they are the Demon.

**Already settled.** A seat keeps its model for the whole game. Its memory of the game is that model's
conversation, so handing it to another model would make no sense; at a real table it is the same person. The engine
stores alignment on each player separately from their character (`state.Player.alignment`), so team changes are
representable.

**To fix in code before any script with team changes is played.** On resume from a checkpoint, seats are rebuilt
from each player's *current* alignment (`Game.restore` calls the seat factory with `p.evil`, and `cli.seat_models`
assigns models by `p.evil`), so a converted seat would silently get the other team's model after a restart. Seats
must be rebuilt from their starting assignment. This cannot happen in Trouble Brewing, where nobody changes team.

**The decision: how to score a game in which a seat changed team.**

1. Score by starting teams and flag the game (record which seats changed, when and how). Simplest; fits the
   existing Bradley-Terry fit; a converted seat adds noise, and the flag lets us measure how much. *(Recommended.)*
2. Rate games with team changes separately, or leave them out. Cleaner, but loses games if changes are common.
3. Credit each seat to the team it ended on (or by time on each team). Most precise, but the rating model is not
   built for per-seat credit and would need redesigning.

Also worth deciding: whether a converted seat is told anything beyond what the rules give it (the rules give a
Goon nothing but their new alignment), and whether the result file and the replay viewer show team changes.

**Measure first.** Once Bad Moon Rising runs, random-bot games (free) show how often a Goon converts and how often
the converted seat decides the result. That number should guide the choice.

**When.** Before the first rated Bad Moon Rising batch. It does not block building the rules.

## 2. Other open decisions from the engine audit

From the November 2026 audit of the engine against the rulebook, almanacs, wiki and TPI's design essays. Each
changes play, so each is a protocol change when adopted.

- **Fixed or balancing Storyteller.** TPI's advice is to help the weaker team and aim for a close finish; the
  scripted Storyteller deliberately ignores the state of the game, to keep ratings comparable. Option: a fixed
  "eval mode" for ratings and a balancing "realism mode" for play and study.
- **How visible private talk is.** At a table everyone sees who talks to whom; here whispers are invisible. A public
  who-whispered-to-whom log was tried in v15 and dropped because it cost evil heavily. Untried options: exclusive
  conversations, a visible channel plus a slower hidden one, seat proximity.
- **What a judging Storyteller may see.** A model that judges madness or the Gossip would see every whisper, which a
  real Storyteller does not; that would make secret confessions always fatal.
- **Model Storyteller scope.** v1-v2 used a model Storyteller and dropped it (it chose the same setup every game,
  undid evil's misinformation, and repeated itself). A model should judge only what a weighted table can't: madness,
  the Gossip, the Artist, and Storyteller-invented content such as the Wizard's wish.
- **Fixed or dynamic day length.** Madness executions end the day early, which conflicts with the fixed day (v5).
- **Live voting.** Hands visible during the sweep, raised early and dropped late (including the Butler and their
  master), instead of each voter locked in turn.
