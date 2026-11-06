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

**Fixed.** On resume from a checkpoint, seats used to be rebuilt from each player's *current* alignment, so a
converted seat would have got the other team's model after a restart. Games now record each seat's dealt team
(`Game.start_teams`) and rebuild seats from it (test: `test_a_seat_that_changed_team_keeps_its_dealt_teams_model_on_resume`).

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

## 2. The Storyteller judge: following evil's bluffs

**The problem.** The rulebook: "To run drunkenness and poisoning well, listen to the bluffs of the evil players, and
support those bluffs wherever possible... Normally, you should make drunkenness and poisoning as harmful as possible
to the drunk or poisoned player." The scripted Storyteller listens to nobody. Example: the Imp, claiming Washerwoman,
is executed; the Scarlet Woman takes over; the Poisoner poisons the Undertaker that night to support the claim. Over
20,000 draws of the v17 Storyteller, the Undertaker learns "Imp" 20% of the time (poisoned information is true on 20%
of nights), "Washerwoman" 20% (2% when Washerwoman is not among the Demon's three bluffs), and another Demon bluff,
which contradicts the Imp's own claim, about 40%.

**Built** (`clocktower/judge.py`, `--judge`; tests in `tests/test_judge.py`). **The design:** The model listens, the code decides:
1. Code lists every legal answer (the Choice), as now.
2. A judge reads what a real Storyteller knows (the Grimoire, tonight's choices, everything said aloud; never
   private whispers) and ranks the legal answers against a rubric written from the rulebook, almanacs and wiki
   advice, with a short reason and quotes.
3. Code picks from the ranking with fixed, tunable weights, so only legal answers appear and no single habit
   takes over (the v1-v2 model Storyteller undid misinformation and repeated itself).
4. Every ruling is logged with its reason and reused on replay or resume.

Modes: `scripted` (today's weighted table: the default; random bots, tests and fingerprints use it), `rules` (a free
deterministic judge that reads simple public claims), `dry-run` (writes the prompt the model would get, calls nothing)
and `model` (a cheap model, opt-in with an API key, within the budget ledger). Tests use recorded answers and never
call a paid API. A test set of situations with known rulings (starting with the Undertaker case above and the
rulebook's "Doug the Baron bluffing Mayor") measures how often the judge agrees with an expert.

**Still to decide.** Which model; whether the rubric includes TPI's "help the weaker team" advice (balancing) or
only the rules-of-thumb for misinformation; the weights.

**Trouble Brewing (a future v18 proposal).** The same judge would be the most valuable protocol change the audit
found for TB. It changes play, so it needs a proposal to the original author and a calibration batch on matched seeds
(paid), per CONTRIBUTING.md.

## 2b. An omniscient Storyteller judge (the owner's direction, 2026-11-06)

**The direction.** A good Storyteller knows everything that is going on at every moment and how it relates, and
makes each discretionary call in context: "the Spy nominated the Virgin: is it more balanced, and does it honour
both abilities better, to let the Spy die to the Virgin or not?"; "the Slayer shot the Recluse: should they die?".
The engine's Storyteller should do the same. Today those two calls are fixed coin flips that ignore the game
(`POLICY['spy_virgin']` and `POLICY['recluse_slain']`, 20% each), like most of the scripted Storyteller.

**What changes from section 2's design.**
1. **The judge knows everything except players' minds:** the Grimoire, every night choice, everything said aloud,
   *and every whisper*, every nomination and vote, the death log. (Section 2 had it hear only public speech, like a
   human Storyteller; the owner prefers an omniscient one.) It never sees players' thinking or belief probes:
   "maybe not inside the head of all the players, but using the Storyteller's interpretation of how the game is
   going". Keep this a setting (`--judge-hears all|public`), because one place it changes the rules is madness
   (Sects & Violets): a judge that reads whispers makes a private confession to one player fatal.
2. **Every discretionary call can go to the judge,** not only misinformation: the Spy and the Virgin, the Slayer
   and the Recluse, how the Spy and Recluse register to each ability, the Mayor's bounce, the starpass heir, the red
   herring, the Drunk's character, the Demon's bluffs, and every Bad Moon Rising choice (the Sailor's and
   Innkeeper's drunk player, the Pacifist, the Tinker, the Shabaloth, the Gossip's victim). With no judge each stays
   the scripted weight, so Trouble Brewing v17 is unchanged.
3. **The judge weighs balance as well as the rules of thumb:** honour both abilities where it can, support evil's
   bluffs, make impairment harmful, and keep the game close (TPI's advice to help the weaker team). Its prompt gets a
   short summary of the state of the game (alive counts, claims, executions so far, where the votes went) besides
   the record.
4. **The judge studies the script first:** each script gets Storyteller's notes (`clocktower/data/storyteller/<script>.md`),
   compiled from the almanac's How to Run sections and the wiki's rulings and tips, listing the interactions to
   watch and how a good Storyteller handles each (the Spy and the Virgin, the Recluse and the Slayer, the Pukka and
   the Exorcist, ...). The judge reads the notes for the characters in play with every decision.

**Built** (2026-11-06; `clocktower/judge.py`, tests in `tests/test_judge.py`).
1. **Hearing:** `--judge-hears all` (the default for any judge: the Grimoire, every night's choices, everything said
   aloud, every whisper, every nomination and vote, the death log; never thinking or belief probes) or `public` (no
   whispers, and only the latest night's choices). On `run`, `play` and `sim`, next to `--judge`; recorded in the
   game's config as `judge:<mode>:hears-<setting>`. Hearing all, the rules judge reads whispered claims too (the
   most recent claim to anyone counts) and the prompt shows every whisper and the claims made in them.
2. **Every discretionary call is routed** through `Game.decide_judged`, each Choice carrying a context (`call`,
   `about`, `recipient`, `impaired`, a plain `question`, and `helps` for yes/no calls that help one team) and `truth`
   where an ability's result is checked: every information result in Trouble Brewing (the Washerwoman, Librarian,
   Investigator, Chef, Empath, Fortune Teller, Undertaker and Ravenkeeper, so the Spy's and Recluse's registration
   to each), the Spy and the Virgin, the Slayer and the Recluse, the Mayor's bounce, the starpass heir, the red
   herring, the Drunk's character, the Demon's bluffs, and in Bad Moon Rising the Lunatic's Demon, Minions and
   bluffs, the Grandchild, the Pacifist's and Tinker's "never" draws, and the Tinker's day deaths (the rest were
   judged already). Hooks that make a judged call are coroutines (`setup`, `redirect_attack`, `nominated`,
   `act_publicly`, `moment`), awaited by the game loop through async variants (`attempt_kill_judged`,
   `demon_attack_judged`, `virgin_judged`, `slayer_judged`, `shots_judged`, `public_abilities_judged`,
   `moment_judged`, an async `tell`); the old synchronous entry points remain for tests and run the same code
   (`characters.now`). With no judge every decision, and every random draw, is exactly as before: the 1,100 TB
   fingerprints replay, and 300 random BMR games hash identically before and after. Left as dice: completing a
   player's incomplete choice, which of several simultaneous nominations is taken, and the Godfather's +1 or -1
   Outsider (drawn while dealing, before there is anything to judge).
3. **Balance:** the rubric adds honouring both abilities, keeping the game close, and deciding "as a skilled
   Storyteller who has followed everything". Every prompt has a state-of-the-game summary (`judge.summary`: alive
   and dead, ghost votes left, claims aloud and in whispers, executions, deaths, recent votes, and `judge.standing`:
   which team is well ahead, by a documented heuristic). The rules judge's heuristics, each with a short reason,
   are listed on `RulesJudge`: a Spy claiming a Townsfolk dies to the Virgin (one claiming an Outsider doesn't; with
   no claim, by balance); yes/no calls that help one team (the Recluse slain, the Tinker's death, the Pacifist's
   save, the Spy and the Virgin) help the team that is well behind, and have no opinion when it is close; the Mayor
   dies when good is well ahead and bounces to a good player when evil is; the heir is the Minion with a good claim,
   then the least suspected; the Gossip's victim and the Shabaloth's regurgitation follow the balance; setup calls
   have no opinion.
4. **Storyteller's notes:** `clocktower/data/storyteller/tb.md` and `bmr.md`, a section per character (what the
   Storyteller decides, the interactions to watch, how a good Storyteller handles them), paraphrased from the
   almanacs' How to Run sections and the wiki. The model and dry-run prompts include the sections for the
   characters in play (and those players believe they are). A long list of legal answers (the Demon's bluffs, a
   poisoned Washerwoman's pairs) is shortened to 40 for a model: the rules judge's top answers, then the scripted
   style's draws.

**Questions on the built judge, for the owner.**
1. *Who is ahead* (`judge.standing`, which drives every balance call): evil is ahead with three or fewer alive and
   the Demon among them, or with no evil player dead and either four or fewer alive or at least half the good team
   (two or more) dead; good is ahead with an evil player dead and five or more alive, or when the Demon's latest
   nomination put them on the block; otherwise close. Are those the right thresholds?
2. *The Slayer and the Recluse in a close game:* the rules judge has no opinion, so the scripted 20% decides; the
   wiki's player tips say the Slayer "will usually kill" a Recluse. Should the close-game default lean that way?
3. *The Tinker's day checks* (about twelve a day) are most of the judged calls: with a model judge, should only the
   Tinker's night step go to the model?
4. *The Demon's bluffs:* a model judge sees a shortlist of 40 of the possible sets. Enough, or keep bluffs scripted?
5. *Night choices when hearing only public speech:* only the latest night's are shown; should it be every night's,
   as a human Storyteller sees them?

**Still to decide.** Balancing and validity: a Storyteller that helps the weaker team compresses the difference
between strong and weak models. Options for rated games: (a) the same balancing judge in every game of a protocol
(comparable within it, with smaller gaps), or (b) a judge that honours abilities and bluffs but doesn't balance by
state. Also cost: hearing whispers makes each judge prompt much longer (a summary instead of the full text, and a
cheap model, keep it to cents a game). Measured with random bots: about 15 judged calls a BMR game
(most of them the Tinker's day checks, the Sailor's and Innkeeper's drunk, and the Pacifist), prompts of about
10,000 characters; a model judge's cost is that many calls a game. Also: the standing heuristic's thresholds, and
whether the Tinker's day checks (about 12 a day) should go to a model at all.

**When.** After Bad Moon Rising's characters (Phase 4), before its random-bot checks (Phase 5), so the checks run
with every call judgeable. For Trouble Brewing it is part of the v18 proposal in section 2.

## 3. Other open decisions from the engine audit

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
