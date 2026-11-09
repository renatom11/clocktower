# Custom scripts and the experimental characters: rulings to review

Where the almanac, the wiki and the official jinx texts leave a question open, the engine had to pick a reading.
Each entry says the question, the options, what the engine does now, and why. These are for the owner to confirm or
change; each change is a small edit in `clocktower/carousel.py` (or the entry or core code it names) plus its test in
`tests/test_carousel.py`. The Storyteller's new weights are in `state.POLICY` under "Carousel", marked "default, for
review". Entries are numbered continuously across batches.

## Batch 0: custom scripts and jinxes

### Loading custom scripts

1. **Which entry is which character.** A script entry's id is matched to an official id ignoring case and anything
   that is not a letter or digit (`Fortune_Teller`, `fortune-teller` and `fortuneteller` are the same), and an
   object entry that names an official id is that character, whatever else it holds (a custom image, a changed
   night position or reminder text are ignored). **The engine plays the official character.** Option: refuse an
   official id whose object changes its ability text, as a homebrew variant (ruling 2). Why: the script tool writes
   official characters as objects too, and the World Championship scripts do.
2. **Homebrew characters.** An object entry with an id the official data lacks, a `name` and a `team` is a homebrew
   character: a Townsfolk, Outsider, Minion or Demon one is never built, even with an official character's name and
   text (the corpus's Witch Hunt Witch is the Witch with "several in the bag"), so loading says "not implemented yet:
   Witch (homebrew: witchhunt-witch)". An id with no definition is still "not in the official data". Options: play a
   homebrew entry whose name and ability text match an official character's as that character (the Witch Hunt Witch
   would then load, without its bag rule); build homebrew characters case by case. Why: a homebrew entry may change
   rules the text doesn't show (`special` fields, bootlegger rules), so playing it as the official one would be a
   silent ruling.
3. **Travellers, Fabled and Loric.** Kept on the script by name (`Script.travellers`, `.fabled`, `.loric`, homebrew
   ones included), listed on the character sheet as "not in play in this engine", never dealt, never on the night
   order, and their rules not applied (a Djinn's or Bootlegger's house rules included: the corpus's "bootlegger"
   rules in the `_meta` entry are ignored too). The setup counts are the normal ones. Options: refuse such scripts;
   build Travellers and Fabled (they need a design agreed first: exile, the Storyteller's helpers). Why: most corpus
   scripts list a few, and the four player types alone play a legal game; the players are told plainly they are
   absent.

### The jinx framework

4. **When a jinx is in effect.** An official jinx applies when both its characters are on the script, in play or not
   (the official rule: jinxes are a property of the script). `Script.jinxed(a, b)` answers it; the code a jinx
   changes asks that, then checks the situation the jinx describes (both in play, who chose whom). `Script.of(...,
   jinxes=[pairs])` takes official jinxes for tests, or `{pair: text}` for a jinx of the test's own. Every
   implemented jinx is declared in `carousel.py` (`jinx(a, b, where)`), and a test checks that each official jinx
   between two built characters is. Trouble Brewing, Bad Moon Rising and Sects & Violets hold no official jinx, so
   no jinx is in effect on them (tested), and their play is unchanged (their fingerprints are identical). The
   character sheet lists the jinxes on the script, as before. Option: apply a jinx only when both characters are in
   play; it makes no difference for the seven below except the Chambermaid's (ruling 6), whose Mathematician must be
   in play to wake anyway.

### The seven jinxes between characters of the base scripts

5. **Mastermind and Vigormortis** ("A Mastermind that has their ability keeps it if the Vigormortis dies"). The
   Vigormortis kills the Mastermind, who keeps their ability while dead as any Minion it kills does; when the
   Vigormortis dies (by any cause: `Vigormortis.dies`, just before its death), a dead Mastermind who has their
   ability through it at that moment keeps it for the rest of the game, no longer depending on the Vigormortis. So
   executing the Vigormortis starts the Mastermind's extra day. A Mastermind who has no ability as the Vigormortis
   dies (it was drunk or poisoned) keeps nothing; the Vigormortis's poison on the Mastermind's neighbour ends as
   usual. Options: also keep it when the Vigormortis stops being the Vigormortis (a Snake Charmer or Pit-Hag change:
   now the ability passes with the character, per S&V's ruling, or ends); keep it whatever the Vigormortis's
   sobriety. Why: "has their ability" reads as at that moment; a character change is not "dies".
6. **Mathematician and Chambermaid** ("The Chambermaid can detect if the Mathematician will wake tonight"). The
   Chambermaid wakes just before the Mathematician (the official order), so normally a Mathematician has not woken
   yet when she learns her number. With the jinx, every living player who has the Mathematician's ability or
   believes they do (a Drunk Mathematician wakes too) counts as waking tonight. Options: count only a sober
   Mathematician; count a Mathematician only once they have woken (a Storyteller who wakes them before her). Why:
   "will wake" is about waking, and a drunk player who wakes already counts for the Chambermaid (BMR's reading).
7. **Mathematician and Drunk** ("The Mathematician learns if the Drunk's ability yielded false info or failed to work
   properly"). Normally the Drunk's own false results are not abnormal (their drunkenness is not another character's
   ability: S&V ruling 22). With the jinx, recorded as abnormal: (a) every false result of the Drunk's information
   (any information decision a working ability could not give, as for a poisoned player; true information for the
   Drunk is not abnormal, as for a poisoned player); (b) the failures of the Townsfolk they believe they are that the
   engine can see: a Drunk Soldier killed by the Demon, a Drunk Monk whose chosen player the Demon killed that night,
   a Drunk Slayer's first shot at the Demon, and a Drunk Virgin's first nomination by a Townsfolk. **Not recorded**
   (options for review): other believed abilities that would have changed something (an Innkeeper's or Sailor's
   protection, a Snake Charmer choosing the Demon, the Philosopher's choice...), which need each character's own
   check; registration (a misregistering nominator for the Virgin) is read from the true character. Why: these are
   the cases where a Storyteller would put the ABNORMAL reminder without judgment.
8. **Mathematician and Lunatic** ("The Mathematician learns if the Lunatic attacks a different player than the real
   Demon attacked"). At the Mathematician's step, if both the Lunatic and the real Demon chose tonight and their
   choices differ as sets of players (the Po choosing nobody, or three, differs from a single choice), the Lunatic's
   ability worked abnormally tonight (once a night). Not recorded when either did not choose (the first night, an
   exorcised Lunatic or Demon). Options: compare only who died (a protected target is still "attacked"); count a
   Lunatic attack that overlaps the Demon's in part as the same. Why: "attacks a different player" is about the
   choice, not its result.
9. **Pit-Hag and Goon** ("If the Pit-Hag turns an evil player into the Goon, they can't turn good due to their own
   ability"). When a sober Pit-Hag makes an evil player the Goon, that player is marked; a marked Goon chosen first by
   a good player still makes the chooser drunk, but stays evil. A marked Goon chosen by an evil player stays evil
   too. The mark is cleared if the Pit-Hag later makes the same player the Goon while they are good. Other ways a
   player turns good (a Snake Charmer's swap) are untouched. Option: lock the Goon's alignment against every change
   (not only its own ability). Why: the jinx names "their own ability" only.
10. **Recluse and Sage** ("The Recluse might register as the Demon to the Sage"). When the Demon kills a sober Sage,
    the Storyteller may show the Recluse (one not poisoned, alive or dead) in the Demon's place: a pair of the
    Recluse and any player but the Demon (and never the Sage). Such a pair is true information (not abnormal for the
    Mathematician). The scripted Storyteller shows the Recluse 30% of the time (`sage_shows_recluse`, default, for
    review), else as before; the other player is alive early, anyone on the final night, as for the Demon's pair. A
    drunk or poisoned Sage gets the misinformation as before. Options: a lower weight (a Recluse shown in the
    Demon's place makes the Sage's death much less useful); also let the Spy register as the Demon to the Sage (no
    jinx says so: the engine never reads registration for the Sage). Why: a Storyteller uses a Recluse's
    misregistration sparingly, as in Trouble Brewing's weights (the Recluse registers as the Imp 30% of the time it
    registers as evil).
11. **Scarlet Woman and Fang Gu** ("If there would be two Demons, one of which was the Scarlet Woman, the Scarlet
    Woman remains the Scarlet Woman"). When the Fang Gu jumps (the Outsider becomes the Fang Gu, then the old one
    dies) with five or more alive, the Scarlet Woman would become the Demon while the new Fang Gu lives: she stays
    the Scarlet Woman. Applied generally: on this script, whenever a Demon dies while another living Demon is in
    play, she stays herself. A Fang Gu dying any other way (executed, with no other Demon) is taken over as usual.
    Options: apply it only to the Fang Gu's jump. Why: the jinx's text is about two Demons, not the jump; on these
    scripts the jump is the only way to get two (a Pit-Hag's new Demon excepted, where the same answer seems right).

### The player prompt

12. **The custom-script prompt** (`prompts.custom_text`, `_teams_custom`). Any script but Trouble Brewing, Bad Moon
    Rising and Sects & Violets gets Trouble Brewing's prompt with generic sentences: "using <name>, a custom
    script", its character sheet (with its jinxes and the characters not in play), its Demons named in the team
    sizes, the Lunatic's exception only if it is on the script, a generic night order ("protect, poison or make
    drunk before the Demon, most information after"), character and alignment changes told at once, information true
    unless an ability says otherwise, and the response fields the schema has (the Slayer's shot only with a Slayer;
    `ability` and `visit` only when a character uses them). Sects & Violets' madness sentences appear only when a
    character's ability says "mad" (the Cerenovus, the Mutant, and experimental ones such as the Pixie and the
    Harpy), and its visit sentences only when a character visits the Storyteller (the Savant, the Artist). The
    Trouble Brewing prompt is byte-identical. Options: generate the night-order sentence from the script's own
    order; describe each script's setup modifiers. A draft for review, like the BMR and S&V prompts.

### Playability

13. **The first synthetic script** (`clocktower/data/scripts/carousel-1.json`, "Carousel test 1"): 13 Townsfolk
    (Washerwoman, Empath, Fortune Teller, Undertaker, Monk, Slayer, Soldier, Chambermaid, Innkeeper, Mathematician,
    Sage, Dreamer, Seamstress), 4 Outsiders (Drunk, Recluse, Goon, Lunatic), 4 Minions (Poisoner, Scarlet Woman,
    Pit-Hag, Mastermind) and 3 Demons (Imp, Fang Gu, Vigormortis): all seven jinxes are on it, and every size from 5
    to 15 can be dealt (the Fang Gu's extra Outsider included). 1,100 random-bot games under the scripted Storyteller
    and 1,100 under the rules judge finish with no crash (`python -m clocktower smoke --script carousel-1`); its
    replay fingerprints are `tests/data/fingerprints-carousel-1.json`. Every jinx fires in them (in 1,100 scripted
    games: the Drunk's abnormal results about 270 times, the Lunatic attacking elsewhere about 680, the Scarlet Woman
    staying herself 34, the Sage shown with a Recluse in play 34, a Mastermind kept past the Vigormortis 30, an evil
    Goon locked 12). About a quarter of the random-bot games reach the engine's day limit unfinished, more than on
    the base scripts: worth a look once real players play it.

New weight: `sage_shows_recluse` 0.3.

## Batch 1: thirteen experimental characters

The Banshee, Damsel, Steward, Nightwatchman, Al-Hadikhia, Magician, Golem, Summoner, Ojo, Fisherman, Plague Doctor,
Hatter and Politician (`clocktower/carousel.py`, tests in `tests/test_carousel1.py`, Storyteller's notes in
`clocktower/data/storyteller/carousel.md`). With them four corpus scripts play end to end: deadpeople, wonders,
binarysupernovae and djinnsbargain. The seventeen official jinxes between them and built characters are all
implemented.

### Townsfolk

14. **The Banshee.** What counts as "the Demon kills you": the Demon's attack (any Demon's: the Vortox's, the Ojo's,
    the Al-Hadikhia's), with the Banshee sober and healthy as she dies, a Philosopher who has her ability included.
    Not an execution, the Pit-Hag's arbitrary deaths or a Fang Gu's jump. The town is told at dawn (the night
    reminder). From then on she may nominate twice a day and her raised hand counts as two votes on every
    nomination, though dead, without spending her ghost vote (a new core hook: `nomination_limit`, `vote_weight`,
    `free_vote`). While dead she is drunk or poisoned, she has neither. Brought back to life, she keeps the powers.
    Options: one extra vote token rather than a double vote; nothing while dead and impaired is already the case.
    Why: the ability says "vote twice per nomination", which a dead player could not do with one token.
15. **The Banshee and the Vortox** ("If the Vortox kills the Banshee, all players learn that the Banshee has
    died"). Without the jinx, the engine treats the announcement as the town's information from a Townsfolk's
    ability, which the Vortox would make false: the Storyteller makes none (the powers still come). With it, the
    announcement is made. The jinx is on every script with both, so the first case is only tested. Option: never
    let the Vortox touch the announcement (then the jinx changes nothing). Why: the jinx exists because the
    announcement is otherwise affected.
16. **The Damsel.** Every Minion learns at the start that a Damsel is in play (not who); a Damsel made later (a
    Pit-Hag's, the Plague Doctor's Baron) is announced to the living Minions then. A guess is a public use of the
    Damsel's ability through the shared `ability` field, naming the player (anyone can claim one, as for the Gossip).
    Each Minion guesses once, alive (or keeping their ability); a drunk or poisoned Minion's guess, or a guess at a
    drunk or poisoned Damsel, is spent and does nothing (an abnormal result for the Mathematician). A right guess
    ends the game at once: the Damsel's team loses (an evil Damsel's team too). Options: one guess for the whole
    Minion team; let dead Minions guess. Why: "(once)" reads per Minion in the wiki, and a dead player has no ability.
17. **The Damsel and the Spy** ("If the Spy is (or has been) in play, the Damsel is poisoned"). Poisoned for the rest
    of the game from the moment any player is the Spy (at the start, or made later by the Pit-Hag or the Hatter's tea
    party), worked out from the Grimoire whenever asked. Not a player who only gained the Spy's ability (the Plague
    Doctor jinx). Option: count a gained Spy ability too.
18. **The Damsel and the Pit-Hag** ("If a Pit-Hag creates a Damsel, the Storyteller chooses which player it is").
    The Storyteller picks any player of a good type (Townsfolk or Outsider; the named player is always allowed), who
    becomes the Damsel keeping their alignment. The scripted Storyteller keeps the named player 30% of the time
    (`damsel_pithag_target`), else a living other. Why: the point of the jinx is that the Pit-Hag does not know her.
19. **The Steward.** A good player by registration: any player who can register as good is legal (a Spy, a
    Recluse); the scripted style draws who registers as evil this time (the usual weights: a Spy usually registers
    good, a Recluse half the time evil) and shows one of the others. A misinformed Steward is shown a "good" player
    of their false world, redrawn until it is false; under the Vortox an evil one. A new Steward (Pit-Hag, Philosopher) learns at once, as the
    Clockmaker does.
20. **The Nightwatchman.** Once per game (spent drunk or not), on any night, optionally. The chosen player is told
    who the Nightwatchman is. Their being told is treated as the Nightwatchman's information (a Townsfolk's), so a
    drunk or poisoned Nightwatchman, or the Vortox, may show them another player (50%,
    `nightwatchman_shown_other`) or nothing (they are not woken); the abnormal result is the Nightwatchman's. Option:
    the target always learns the truth (being shown a token is not information). Why: the almanac's drunk
    Nightwatchman shows a wrong player.
21. **The Magician.** Only the first night's evil information changes (a core hook, `shown_to_evil`): the Demon's
    list of Minions includes the Magician, in seat order; each Minion is told "The Demon is X or Y (you were shown
    both)". How the Magician registers is untouched: every ability that detects the Demon finds the real one. A
    Magician poisoned from the start (a No Dashii's neighbour) does nothing; a Drunk who believes they are the
    Magician does nothing; a player who becomes the Magician later, or a Philosopher who gains it, changes nothing.
    With no Demon in play (the Summoner), the Minions are shown the Magician alone as "the Demon" (a reading: the
    ability applied literally; the Summoner can see through it). Options: show the Minions nothing with no Demon.
22. **The Magician and the Spy** ("When the Spy sees the Grimoire, the Demon and Magician's character tokens are
    removed"). The Spy's Grimoire shows every Demon's and the Magician's line as "(token removed)", with nothing
    else on it (their alignment, states and reminders hidden too), for a Spy or a Minion who gained the Spy's ability.
23. **The Fisherman.** Visited once per game (`Game.visit_judged`), spent drunk or not. The advice is one statement
    chosen by the Storyteller from those the code can check: the Savant's statements (S&V ruling 25) and "X is the
    Y" for each living player who registers as one character. A true statement is chosen, three times as likely
    when it helps the Fisherman's team (`fisherman_helpful_weight`: for good, statements about evil players,
    poison, choices, votes and the Demon's seat; for evil, about good characters and the setup), never one naming
    the Demon outright. A drunk or poisoned Fisherman may get a false one (bad advice); under the Vortox only false
    ones are legal. A model judge ranks these statements; it does not write its own. Options: let a judge write
    free advice (its truth could not be checked by code, so a false "advice" could slip through); allow the Demon to
    be named. Why: the advice must be true, and only checked statements are guaranteed to be.

### Outsiders

24. **The Golem.** "You may only nominate once per game" holds while they are the Golem, drunk or poisoned or not
    (the reminder goes on as they nominate). The nominee dies at once if they are not the Demon (the Golem's own
    kill: protections stop it) and the nomination still goes to a vote, as with the Witch. A Recluse may register as
    the Demon and live (20%, `golem_recluse_demon`, a judged call that helps evil). A drunk or poisoned Golem kills
    nobody (abnormal for the Mathematician). Option: end the nomination when the nominee dies.
25. **The Politician.** "The player most responsible for your team losing" is a judgment; the scripted floor is
    deterministic: the game ended on today's execution and the Politician was the player executed, or the one who
    nominated them. Then they change alignment and win, even if dead, unless drunk or poisoned. It runs once the
    game has ended however the winner was set (a new end hook, `Character.ended`, from `Grimoire.finish` in
    `Game.run`), not in `overrides_end`: an override is asked before another override (the Mastermind's) may keep
    the game going, and the Saint, the Damsel or the Vortox set the winner without it. A judge cannot weigh in (the
    end check is synchronous). Options: count a decisive vote, a claim or a bad shot; let a judge rule.
26. **The Pit-Hag and the Politician** ("If the Pit-Hag turns an evil player into the Politician, they can't turn
    good due to their own ability"). Marked as the Pit-Hag/Goon jinx is (ruling 9); a good player made the
    Politician later is free again.
27. **The Hatter.** A sober Hatter's death (by day or night) holds a tea party at the Hatter's step on the night of
    the death (the coming night for a day death); one who dies tonight after the step gives none. Each living Minion
    and Demon, in seat order, may name another character of their type on the script that no other player has
    (alive or dead; one just left by an earlier player is free), or keep theirs; they are told. The dead do not
    choose. A character's setup does not happen mid-game (a Baron made now adds no Outsiders). Options: let the dead
    choose; ask everyone at once.
28. **The Plague Doctor.** On a sober Plague Doctor's death (once a game), the Storyteller gains the ability of a
    Minion on the script and not in play, chosen uniformly among those it can use; none if there is none. How each
    is used: at that Minion's own night step (a core call, `Character.storyteller_step`, for the abilities in
    `g.notes['Storyteller abilities']`): the Poisoner's poison (usually a good information role:
    `plague_poison_info` 0.8), the Godfather's kill after an Outsider died today, the Devil's Advocate's protection
    (usually an evil player: `plague_protect_evil` 0.8), the Assassin's one kill (25% a night,
    `plague_assassin_night`), the Witch's curse and the Cerenovus's madness (usually on good players); the
    Mastermind's extra day passively; the Spy, Scarlet Woman, Baron and Evil Twin by their jinxes (ruling 29). **Not
    used**: the Pit-Hag's (a nightly change of any character, with no aim a scripted style could follow) and the
    Summoner's (its third night has passed or a Demon is in play). Options: let the Storyteller gain an off-script
    Minion when the script's are all in play; include the Pit-Hag with a conservative style.
29. **The Plague Doctor's jinxes.** The Spy's and the Scarlet Woman's ability go to a living Minion (the
    Storyteller's choice), who is told and has it as an extra ability (the Spy's Grimoire each night; the Scarlet
    Woman's takeover); the Baron's turns up to two living good Townsfolk (two 70% of the time, `plague_baron_two`)
    into different Outsiders not in play (not the Drunk or the Lunatic, whose illusions can't begin mid-game),
    keeping their alignment; the Evil Twin's makes a living good player (usually a Townsfolk) the Evil Twin,
    keeping their alignment (a good Evil Twin, paired with an evil player). Options: a good player made the Evil
    Twin turns evil; a gained Spy also misregisters.

### Minions

30. **The Summoner's setup.** "[No Demon]": a Townsfolk is dealt in the Demon's place (`no_demon`; the setup checks
    allow no Demon then, and one more Townsfolk). The Summoner learns three bluffs in their introduction; the other
    Minions are told "No player is the Demon yet." The game does not end for want of a Demon while a living Summoner
    with the ability may still summon (to the end of the third night); a Summoner who dies first summons nobody, so
    good wins at once.
31. **The summon.** On the third night the Summoner names any player, alive or dead, themself included, and a Demon on
    the script: that player becomes that Demon and evil, and is told (they learn no Minions). The Summoner wakes
    before the Demons, so the new Demon acts that night. A drunk or poisoned Summoner (with no Courtier jinx)
    summons nobody, and good wins at dawn unless a Demon is in play. A dead player made any Demon but the Zombuul
    stays dead (and good wins). Options: let a drunk Summoner's choice stand; refuse dead players.
32. **The Summoner's jinxes.** Courtier ("If the living Summoner has no ability, the Storyteller has the Summoner
    ability"): the Storyteller summons in their place, usually the player and Demon the Summoner chose (80%,
    `summoner_st_honours`), else a good player and any Demon on the script, even one already in play (open, like
    the Summoner's own summon: finding U7). Pukka: on the second night the Summoner may summon a Pukka (only
    a Pukka; naming no one, or another Demon, waits for the third night). Zombuul: a dead player summoned into the
    Zombuul is alive, registering as dead, with its first death spent. Pit-Hag and Hatter: a summon that
    makes a second living Demon makes tonight's deaths the Storyteller's, as the Pit-Hag's (`arbitrary_deaths_choice`,
    "Summoner deaths"). Clockmaker: the Summoner counts as the Demon (the distance to the nearest other Minion; none
    if there is no other).

### Demons

33. **The Ojo.** The character named is matched to players' true characters (not how a Spy or Recluse might
    register); a dead player's character is in play, and nobody dies. A character nobody has (the Drunk's apparent
    one included) lets the Storyteller choose any living player but the Ojo, usually a good one who will die
    (`ojo_good_victim` 0.9), rarely nobody (`ojo_nobody` 0.05). The deaths are the Demon's attack. Options: let
    registration decide; never allow "nobody".
34. **The Al-Hadikhia.** Fewer than three players named is no choice. Each target is woken in turn and asked to live
    or die (a new request kind, `decide`, answered in `vote`; required, asked again, never made for them), told only
    their place in the order. The three are announced to everyone at dawn. Those who choose to die die, unless
    protected (the deaths are the Demon's attack; the Mayor may bounce one); if all three choose to live, all three
    die. A dead player who chooses to live comes back to life (a reading, for review); one who chooses to die stays
    dead. A drunk or poisoned Al-Hadikhia's targets still choose, to no effect. Options: a dead target can only stay
    dead; tell the targets the other two names.
35. **The Al-Hadikhia and the Mastermind** ("If the Al-Hadikhia dies by execution, and the Mastermind is alive, the
    Al-Hadikhia chooses 3 good players tonight..."). In place of the Mastermind's extra day: when the executed Demon
    is the Al-Hadikhia and a working Mastermind lives, the game goes on; that night the dead Al-Hadikhia chooses three
    living good players (all of them, if fewer), each chooses to live or die, and the game ends: evil if all chose to
    live, good otherwise. Option: let the Mastermind be drunk (the jinx says only "alive").
36. **The Al-Hadikhia and the Scarlet Woman** ("If there would be two Demons, one of which was the Scarlet Woman, the
    Scarlet Woman becomes the Scarlet Woman again"). She does not take over a Demon who dies while another living
    Demon is in play (as ruling 11); and when a dead Demon comes back (an Al-Hadikhia target who chose to live) while
    she holds the Demon, she becomes the Scarlet Woman again, and is told.

### Core changes and playability

37. **Dealing.** A Demon whose setup modifier the script can't deal with the Minions chosen is not drawn (the corpus's
    deadpeople has four Outsiders: the Fang Gu's extra one with the Baron's two can't be dealt at 15 players, so the
    Imp is); a setup that still can't be dealt is a clear error ("cannot be dealt for 15 players with ..."). On the
    base scripts and carousel-1 every Demon always fits, so their draws are unchanged.
38. **False results name the script's Demon.** A misinformed or misregistered result that showed "the Imp" now shows
    the Imp only where the script has it, else the Demon in play (the Undertaker on wonders could name an Imp not on
    the script).
39. **The second synthetic script** (`clocktower/data/scripts/carousel-2.json`, "Carousel test 2"): the thirteen,
    with the Clockmaker, Courtier, Empath, Fortune Teller, Undertaker, Monk, Chef and Investigator; Spy, Scarlet
    Woman, Baron, Pit-Hag, Evil Twin and Mastermind; Pukka, Vortox and Zombuul. All seventeen batch 1 jinxes are on
    it, and every size from 5 to 15 deals (the Summoner's Townsfolk and the Baron's Outsiders included). Its replay
    fingerprints are `tests/data/fingerprints-carousel-2.json`.

New weights: `golem_recluse_demon` 0.2, `nightwatchman_shown_other` 0.5, `ojo_nobody` 0.05, `ojo_good_victim` 0.9,
`fisherman_helpful_weight` 3, `summoner_st_honours` 0.8, `damsel_pithag_target` 0.3, `plague_poison_info` 0.8,
`plague_assassin_night` 0.25, `plague_protect_evil` 0.8, `plague_baron_two` 0.7. The rules judge has no heuristic of
its own for the new calls (the scripted style decides, or its balance for the yes/no ones that help a team).

## Batch 2: fifteen experimental characters

The Pixie, High Priestess, Poppy Grower, Shugenja, Balloonist, General, Preacher, Cannibal, Puzzlemaster, Heretic,
Marionette, Widow, Goblin, Kazali and Leviathan (`clocktower/carousel2.py`, tests in `tests/test_carousel2.py`,
Storyteller's notes in `clocktower/data/storyteller/carousel.md`). With them the Carousel Script Collection's Revenge
of the Martian Vampires plays end to end. The thirty-three official jinxes between them and built characters are all
implemented.

### Townsfolk

40. **The Pixie.** On the first night the Pixie learns a Townsfolk character another player truly has (never the
    Pixie's own); drunk, poisoned or under the Vortox, one nobody has. They are marked mad about it for the game
    (shown on the Grimoire), but breaking it is never punished by execution. When the player who has that character
    dies, and the Pixie then has their own ability (alive, sober, still the Pixie), the Storyteller judges whether
    they were mad, over everything said aloud since day 1 (the Cerenovus's floor: they claimed it aloud, their latest
    claim was it, and they never denied it or confessed); if so they gain the ability on top of their own (as the
    Philosopher's, without making anyone drunk), and a "you start knowing" ability acts at once (by day, told at once,
    "Day n"; for the Washerwoman, Librarian, Investigator and Chef too, through `InfoRole.becomes`, which also tells a
    player the Pit-Hag or another change makes one of them later, as the S&V characters already were: finding EC-8).
    Options: judge only the days before the death; let a dead Pixie gain. Why: "if you were mad" reads as the whole game.
41. **The High Priestess.** Each night (the first too) the Storyteller points at one player. The scripted heuristic,
    and the truth for the Vortox and the Mathematician: a living player of the High Priestess's team, weighted three
    to one towards players with information (`priestess_info_weight`) and against players they have whispered with
    often. A drunk or poisoned one may be pointed at anyone (usually the other team); under the Vortox, only the other
    team. A judge ranks the same players. Options: count dead players; point a good High Priestess at the Demon
    sometimes (the wiki allows it). Why: "should talk to most" is about who helps them.
42. **The Poppy Grower.** While a Poppy Grower has the ability at the start (alive, sober: a Drunk who thinks they
    are one does nothing), the Demon learns only its bluffs, and the Minions nothing about the evil team ("You do not
    learn who the other evil players are"). At the Poppy Grower's step each later night, if no Poppy Grower has the
    ability any more (dead, drunk or poisoned at that moment, or changed), every living Minion learns the Demon and
    each other, and the Demon its Minions (the Marionette named, who learns nothing); this happens once. A death by
    day is learnt that night; a death later in the night, the next night. Options: only a death triggers it (a
    poisoned Poppy Grower keeps evil apart). Why: "Minions & Demons do not know each other" is the ability working.
43. **The Shugenja.** Seats are counted round the circle, the dead included. Registration counts: an answer is true
    if a way the Spy and Recluse can register makes it the closer side (or equidistant), so a sober Shugenja may have
    two legal answers; the scripted style draws who registers as evil this time, and picks at random when
    equidistant. Misinformed: the other side; under the Vortox, the false side when one is. A new Shugenja (Pit-Hag)
    learns at once.
44. **The Balloonist.** Each night (the first too) another player, alive or dead, never themself; after the first
    night, one who can register as a type other than the one shown the night before (the type they were shown as is
    recorded: the true type where it qualifies, else one they can register as). Misinformed (and under the Vortox,
    always): a player of last night's type. The "[+0 or +1 Outsider]" is a setup step, not part of the draw: in a dealt
    game, half the time (`balloonist_outsider` 0.5), a Townsfolk becomes an Outsider not in play (not the Drunk or
    the Lunatic) before anyone learns their character; a forced setup is kept as given. The setup checks accept both
    counts. Options: draw the extra Outsider in `random_setup`; allow the Balloonist to be shown themself.
45. **The General.** Each night: good, evil or neither. The scripted heuristic is the rules judge's `standing` (good
    or evil "well ahead", else neither). The answer is the Storyteller's belief, so for a sober General every value
    is legal and a model judge may answer otherwise (no abnormal result either way); drunk or poisoned, usually
    another answer, under the Vortox never the heuristic's. Option: hold a sober General to the heuristic.
46. **The Preacher.** A Minion is the true type (a Spy is one, a Recluse is not). A chosen Minion is told at once and
    has no ability while the Preacher has theirs: dead, drunk or poisoned, the Minions get theirs back (a reading of
    the present tense). "No ability" is played as drunk, plus a `no ability` state the Poisoner checks (ruling 63). A
    Marionette chosen loses nothing they have and is not told (being told would reveal them: a reading, for review).
    A drunk Preacher's choice does nothing (abnormal for the Mathematician). Option: the Minions stay silenced after
    the Preacher dies.
47. **The Cannibal.** "The recently killed executee" is the latest player killed by execution (one who survived it
    does not count), as the character they were. Good: the Cannibal has that ability as an extra one (woken at its
    step, a "you start knowing" one acting at once); any Cannibal poison ends. Evil: the Cannibal is poisoned until a
    good player dies by execution, and the Storyteller's lie is the ability they have meanwhile: a good character,
    usually the one the executee claimed aloud (`cannibal_lie_claim` 0.8), else a random Townsfolk, whose ability then
    misfires (they are poisoned). The Cannibal is not told the character, but being woken as it shows it (an engine
    limit: night prompts name the role). A dead Cannibal gains nothing. An ability that only acts through its own
    character's hooks (the Saint's loss, the Soldier's safety) does not act for the Cannibal or any player who gained
    it (an existing engine limit, shared with the Philosopher).
48. **The Cannibal's jinxes.** Butler: the Cannibal is told they have the Butler's ability (the vote rule still binds
    only a true Butler: the engine limit above). Juggler: a Juggler who guessed on their first day and is executed
    that same day lets the living Cannibal learn, that night at the Juggler's step, how many guesses were right.

### Outsiders

49. **The Puzzlemaster.** At setup the Storyteller marks another player as drunk (usually a good Townsfolk:
    `puzzle_townsfolk` 0.8), for the whole game, the Puzzlemaster's death included; while the Puzzlemaster is drunk or
    poisoned that player is sober (a reading). The guess is made privately, by visiting the Storyteller and naming one
    other player (a visit naming none or several is no guess and is not spent); once per game, spent drunk or not. A
    right guess shows a player who registers as the Demon; a wrong one shows a player who does not (false
    information); a drunk or poisoned Puzzlemaster may be shown anyone. They are never told whether they were right.
    A new Puzzlemaster (Pit-Hag, Philosopher) has a drunk of their own. Options: a public guess; tell them right or
    wrong.
50. **The Heretic.** At the very end (`Character.ended`, now run with the result-flippers last: a core change, so
    the Politician's change comes first), a Heretic who is the Heretic and sober, dead or alive, reverses the winner,
    whatever ended the game. Option: let the Politician act on the reversed result.
51. **The Heretic's jinxes** ("Only 1 jinxed character can be in play": the Baron, Godfather, Pit-Hag, Spy, Widow).
    A core rule from the jinx text (`Script.exclusive`, `Script.clash`): `random_setup` draws again when both are
    dealt, `setup_error` refuses them, the Pit-Hag cannot make one while the other is in play (nothing happens), a
    tea party cannot choose one, and the Kazali cannot make one. A gained ability (the Plague Doctor's Spy) is not
    "in play".

### Minions

52. **The Marionette's setup.** The Marionette is dealt like any Minion, then (a setup step) swaps seats with one of
    the Demon's neighbours if not already beside it, and believes they are a good character nobody has or believes
    they have (a Townsfolk 80%, `marionette_townsfolk`, information roles three times as likely; never the Drunk or
    the Lunatic). They are played as the Drunk is (`always_drunk`: their apparent ability is the Storyteller's
    misinformation, one false story all game). They get no evil information and are told nothing as a Minion; the
    Demon learns "X is the Marionette" in its first-night information (and X among its Minions); the other Minions
    are not told about them. They cannot be created by the Pit-Hag or chosen at a tea party (the Marionette starts
    beside the Demon, believing it is good, or not at all). Options: let the other Minions see them; let the Pit-Hag
    create one (told, so useless).
53. **The Marionette's jinxes.** Magician: while a Magician is alive, the Demon learns only "one of your neighbours,
    X or Y, is the Marionette". Mathematician: the Marionette's false information counts as abnormal (the Drunk's
    jinx code, made generic). Balloonist: a Marionette who believes they are the Balloonist may bring the extra
    Outsider (the Balloonist's setup step). Summoner: with no Demon at setup, the dealt Marionette's player is, for
    now, the good character they believe they are; when the Summoner makes a Demon, one of its good neighbours (the
    Storyteller's choice) becomes the Marionette without being told, keeping their character in mind, and the Demon
    learns it. Kazali: the Kazali may make only a neighbour the Marionette (asked again otherwise); that player keeps
    believing their character. Plague Doctor: the Storyteller "gaining" the Marionette makes one of the Demon's good
    neighbours the Marionette the same way.
54. **The Widow.** The first night only (the night order has no later step: a Widow made later does nothing). They
    see the whole Grimoire as they wake, then choose a player: poisoned for the rest of the game, while the Widow has
    the ability (dead, the poison ends; drunk, it is not made; made drunk or poisoned later, it pauses, as the
    Poisoner's: B5 in docs/interaction-findings.md). Then a living good player (by alignment; usually a
    Townsfolk) learns "a Widow is in play", whatever the Widow's sobriety (a reading: it is true). Options: no
    knower when the Widow is drunk; the knower may be a Spy registering as good.
55. **The Widow's jinxes.** Poppy Grower: no Grimoire while a Poppy Grower has the ability (she still chooses). Magician:
    the Demon's and the Magician's tokens are removed, as for the Spy (ruling 22). Damsel: the Damsel is poisoned once
    a Widow is or has been in play, as with the Spy (ruling 17). Heretic: ruling 51.
56. **The Goblin.** The claim is public and made once nominated: from the Goblin's first nomination of the day on,
    anything they say aloud claiming to be the Goblin ("I am the Goblin", in their defence or a comment) or a public
    use of the Goblin's ability through the shared `ability` field. A claim before the nomination does not count. If
    they are executed that day (dying or not), alive and with the ability then, their team (their alignment) wins at
    once. Options: only the defence counts; a later nomination's claim must be the one executed.
57. **The Goblin's jinxes.** Cerenovus: the Goblin may be named as the madness (a new `Choose.also`). Plague Doctor:
    a living Minion gains the Goblin's ability and is told, as for the Spy.

### Demons

58. **The Kazali's setup.** No Minions are dealt: their seats are Townsfolk (`no_minions`, in the dealing and the setup
    checks). "-? to +? Outsiders": as a setup step, the Storyteller keeps the dealt Outsiders (60%,
    `kazali_outsiders_same`) or adds or removes one. Its introduction says no player is a Minion yet.
59. **The Kazali's first night.** At its step (the first of the night), the Kazali chooses, one at a time, as many
    players as the table has Minions, each with a Minion character on the script not in play; each turns evil and is
    told their character; then each learns the Demon (the Magician may be shown too) and the others (not while a
    Poppy Grower keeps evil apart). It happens whatever the Kazali's sobriety (it is setup). Required: asked again
    until legal. Later nights it kills like any Demon. A Baron chosen adds no Outsiders (they were settled at setup).
    Setup choices made before (the red herring, the Grandchild) stay with players who became Minions (the
    Grandmother is then shown her Grandchild's Minion character: a core fix).
60. **The Kazali's jinxes.** Summoner: a summon that makes a second living Demon makes tonight's deaths arbitrary
    (as the Pit-Hag's and Hatter's jinxes). Marionette: ruling 53. Heretic: ruling 51.
61. **The Leviathan.** All players learn it is in play when the first night is played (or whenever it enters play).
    It never kills. Every execution of a good player (by alignment, dying or not) while it is in play counts; at the
    second, with the Leviathan alive and working, evil wins. At the end of day 5 (or a later day, if it was drunk or
    poisoned then), with the Leviathan alive and working, evil wins. Options: count only executions that kill; count
    executions from before a Pit-Hag made it.
62. **The Leviathan's jinxes.** Banshee, Sage, Ravenkeeper: each night but the first the Leviathan must choose a
    living player it has not chosen before (it does not know who is good: choosing an evil player does nothing); a
    chosen good Banshee dies (as killed by the Demon: the town is told, and she gains her powers); a chosen good Sage
    learns that the Leviathan is one of two players; a chosen Ravenkeeper chooses a player and learns their character;
    neither dies. Exorcist, Innkeeper, Monk, Soldier: the Leviathan nominated, and that day's execution is, the player
    the Exorcist, Innkeeper or Monk chose last night (that ability working now), or the Soldier: good wins. Grandmother:
    the Grandchild dies by execution with the Leviathan in play: evil wins. Mayor: day 5 ends with the Mayor and the
    Leviathan alive and no execution: good wins. Hatter, Pit-Hag: neither can make a Leviathan after day 5.

### Core changes and playability

63. **Core changes**, each a no-op on the base scripts (their fingerprints are identical): a Townsfolk information
    role also informs a player who gained its ability (the Pixie's, the Cannibal's: Trouble Brewing's roles answered
    only their own players before); the Drunk's per-game truthfulness and single false world apply to any
    `always_drunk` character (the Marionette); the first-night evil information skips players who believe they are
    good and stops when a Poppy Grower keeps evil apart (`Character.keeps_evil_apart`); a Demon with no Minions yet is
    told so; the Poisoner does nothing while it has a `no ability` state (the Preacher's); the Grandmother's choice
    always includes the truth. A Poisoner made drunk by another ability (the Courtier, the Innkeeper, the
    Puzzlemaster) used to poison all the same; since the fuzzer batch (docs/interaction-findings.md, B5) a drunk or
    poisoned Poisoner poisons no one (abnormal for the Mathematician), and the poison pauses while the Poisoner is
    made drunk or poisoned later (the Courtier and the Innkeeper act after it), except a Poisoner's poison on
    themself (Trouble Brewing's case, which stands as before). carousel-1's fingerprints were re-recorded for it.
64. **The third synthetic script** (`clocktower/data/scripts/carousel-3.json`, "Carousel test 3"): the fifteen, with
    the Magician, Monk, Soldier, Mayor, Sage, Ravenkeeper, Exorcist, Innkeeper, Juggler, Mathematician, Banshee and
    Grandmother; the Butler, Damsel, Hatter and Plague Doctor; the Spy, Summoner, Cerenovus, Pit-Hag, Baron and
    Godfather; the Kazali, the Leviathan and the Imp. All thirty-three batch 2 jinxes are on it (forty jinxes in
    all), and every size from 5 to 15 deals. Its replay fingerprints are
    `tests/data/fingerprints-carousel-3.json`.

New weights: `priestess_info_weight` 3, `balloonist_outsider` 0.5, `cannibal_lie_claim` 0.8, `puzzle_townsfolk`
0.8, `marionette_townsfolk` 0.8, `kazali_outsiders_same` 0.6. The rules judge has no heuristic of its own for the new
calls (the scripted style decides).

## Batch 3: thirteen experimental characters

The Village Idiot, Acrobat, Lycanthrope, Alchemist, Zealot, Organ Grinder, Noble, Farmer, Harpy, Boffin, Boomdandy,
Fearmonger and Xaan (`clocktower/carousel3.py`, tests in `tests/test_carousel3.py`, Storyteller's notes in
`clocktower/data/storyteller/carousel.md`). The first six, with built characters, make the Carousel Script
Collection's Monkey Do Math, which now plays end to end; their interactions with each other are tested there. The
eighteen official jinxes between them and built characters are all implemented. Lil' Monsta is not built (65).

65. **Lil' Monsta is left out.** Its Demon is not a character but a token the Minions pass each night ("is the
    Demon"): no player's character is a Demon, the babysitter keeps their Minion ability, and the token decides who
    dies to execution as the Demon, who registers as it, and the victory check. That is the "no Demon character"
    design the brief keeps for the owner with the Legion, Riot and Atheist; its five jinxes (Hatter, Magician, Poppy
    Grower, Scarlet Woman, Marionette) wait with it. Options: a Demon token held as a state (`Player.is_demon` and
    every registration hook reading it), or a Lil' Monsta character moved between Minions each night (simple, but the
    babysitter would lose their own ability, which the text keeps).

### Townsfolk

66. **The Village Idiot.** In a dealt game the Storyteller adds no extra (0.4), one (0.35) or two (0.25) Village
    Idiots at setup, Townsfolk becoming them before anyone is told (never a Townsfolk whose own setup step has run:
    the Alchemist); a forced setup keeps the ones given. With two or more, the Storyteller marks one, any of them, as
    drunk all game. Each night every Village Idiot chooses a player and learns the alignment they register as (a Spy
    may show good, a Recluse evil, the Lycanthrope's player evil). The drunk one's results are drawn as a poisoned
    player's are, night by night (not one false world for the game, as the Drunk's: a reading). Up to three players
    may have the character at once (`Character.duplicates`; `setup_error` allows it).
67. **The Acrobat.** "Are or become drunk or poisoned tonight": checked at the Acrobat's step and again when
    tonight's last step is done (`Character.end_of_night`, a new hook), so a player the Organ Grinder or the Sailor
    makes drunk later in the night counts; the Drunk always counts. The Acrobat must have a working ability at the
    check: a poisoned Acrobat never dies this way, even choosing themself. A death, announced at dawn.
68. **The Lycanthrope.** "If good": as the player registers (a Spy may register either way: the Storyteller's call,
    POLICY `lycanthrope_misregister_good` 0.5; the Faux Paw registers evil, so survives). A good choice dies (not a
    Demon's kill: the Monk and the Soldier don't stop it) and the Demons' attacks kill nobody tonight, even if the
    chosen player is protected and lives (a reading). "One good player registers as evil": chosen at setup (or when
    a living player becomes the Lycanthrope), usually a Townsfolk, and never one that would leave a Noble with no
    true three (see U9); while the Lycanthrope is alive, sober and healthy, they register as evil to every alignment
    check (`Grimoire.registers_evil`, a 'registers evil' state), not as an evil character.
69. **The Noble.** On their first night (or when they become one), three other players of whom exactly one can
    register as evil. Drunk, poisoned or under the Vortox: any three, misinformed with none or two or more evil.
70. **The Farmer.** Any death at night while sober and healthy (a Philosopher's too); none by day. The Storyteller
    picks a living good player (usually a Townsfolk, not already a Farmer), who becomes a Farmer and is told; several
    Farmers can be in play. With the Leviathan (its jinx), a good Farmer it chooses makes a new Farmer and lives.
71. **The Alchemist.** The Storyteller picks, at setup, a Minion on the script that is not in play, among those the
    engine runs for a good player (Poisoner, Devil's Advocate, Assassin, Godfather, Baron, Witch, Cerenovus,
    Fearmonger, Boomdandy, Harpy). The Scarlet Woman (a good Demon), Pit-Hag, Evil Twin, Goblin and Xaan are never
    offered (options: build each for a good holder). The Alchemist holds it on top of their own, is shown it on the
    first night, and in a dealt game its setup change comes with it (the Baron's two Outsiders; the Godfather's one
    more, 0.75, or one fewer). "May prompt you to choose differently": the engine never does (option: let a judge
    refuse a choice that would end the game for evil). A Drunk who believes they are the Alchemist is shown a Minion
    not in play, without a setup change, woken for its step, with no effect.
72. **The Alchemist's jinxes.** Spy, Widow: only while that Minion is in play; no ability; after each execution
    (dying or not) a living Alchemist may publicly name a living player as it, optionally; a right guess makes every
    Demon's night choice tonight that player. Marionette: only while one is in play; nothing. Mastermind: only while
    not in play; nothing. Organ Grinder: only while one is in play; both have the ability, and while both are sober
    (by anything placed, not by this jinx's own drunkenness, so it does not loop) both are drunk. Boffin: the
    Alchemist is not told the Demon's ability. Summoner: only in a dealt game, at setup, with an evil player other than
    the Demon and a Marionette (else no evil player would be in play until the third night: a smoke crash): the Demon
    dealt becomes a good Townsfolk not in play; on the third night the Alchemist names a Demon and the Storyteller
    the player (usually a living good one), who becomes it, evil; until then good does not win for want of a Demon,
    and the Alchemist dying first wins for evil.

### Outsiders

73. **The Zealot.** "5 or more players alive": as the town sees it. A working Zealot is asked to vote as usual, told
    they must vote yes, and their hand is raised whatever they answer (with a private notice); a drunk or poisoned one
    is told the same and their answer stands. A dead Zealot has no ability. With the Cannibal (its jinx), a Cannibal
    who gains the Zealot's ability is told.

### Minions

74. **The Organ Grinder.** Each night a yes/no (`decide`): drunk until dusk, or not. While a holder is alive, sober
    and healthy, every vote is eyes closed (`Character.secret_votes`): each voter sees only their own hand, the
    prompt gives no tally and no block, the count goes to the Storyteller's record only, and nominations do not say
    who is about to die; the execution, or no execution, is announced at the end as usual. With the Butler (its
    jinx), the Butler is not shown the master's hand and may raise theirs; it counts only if the master's is up.
75. **The Harpy.** Two players each night; the first is told, by name, whom they must be mad about (even when the
    Harpy is drunk or poisoned: no penalty then). Judged once, as the day's talk ends and before nominations (as the
    Cerenovus's). The scripted floor: they broke it unless, aloud that day, they said the second player is evil (a
    sentence naming them with "evil", "Demon", "Minion" or "Imp") or nominated them, and never called them good or
    said they were mad (a judge weighs effort). Broken: the Storyteller kills nobody 20% of the time, the first player
    48%, the second 16% and both 16% (`harpy_kill` 0.8; then `harpy_both` 0.2 and `harpy_first` 0.6 of that, the
    rest the second; with one of the two dead, the living one). Option: judge at dusk, over the whole day.
76. **The Boffin.** At the Boffin's step on the first night the Storyteller picks a good character not in play from
    those the engine runs for a Demon who has them (the Washerwoman, Librarian, Investigator, Chef, Empath,
    Undertaker, Monk, Noble, Village Idiot and Goon); the Demon and the Boffin are told. The Demon has it while the
    Boffin is alive and still has their ability, whichever player is the Demon (a starpass passes it on), and it works
    while the Boffin is sober and healthy, whatever the Demon's own sobriety (`Grimoire.gift`, `gift_impaired`). Its
    jinxes: never the Drunk's, Heretic's or Politician's ability; a Demon with the Goon's doesn't turn good by it; the
    Village Idiot's even in play while a token is spare (another Village Idiot: the drunk one is chosen again).
77. **The Boomdandy.** Executed and dying while sober and healthy (an Alchemist's too), once a game: the town is told,
    and all but three living players die, the Storyteller choosing the three (usually the Demon and two others,
    0.9, so the pointing decides). With three or fewer alive, nobody dies first. Then every player, dead ones too,
    points at a living player at once; the one most pointed at dies, and a tie kills nobody (a reading). With the
    Plague Doctor (its jinx), a player becomes the Boomdandy: usually a living Minion (0.8), keeping their alignment.
78. **The Fearmonger.** A new choice is announced to all only when it takes effect (a drunk or poisoned Fearmonger's
    choice changes nothing and is not announced: a reading); the chosen player is not told. If the Fearmonger
    nominated today's executee and that is their chosen player, the executee's team loses at the execution, dying or
    not. With the Plague Doctor (its jinx), a living Minion gains the ability and is told.
79. **The Xaan.** "[X Outsiders]": dealt with one more, as many or one fewer Outsider than the table's base (the
    Storyteller's, uniformly, among those the script can deal: `outsider_choices`); X is then the number of Outsiders
    in play after every setup change, and a dealt game with none gets one (else X is 0 and the Xaan never poisons). A
    Xaan made later has X equal to the Outsiders in play then. On night X, from the Xaan's step until dusk, every
    Townsfolk (as they are now) is poisoned while the Xaan is alive, sober and healthy (as the Poisoner's poison:
    finding B5); a drunk or poisoned Xaan at that step poisons nobody, and night X never comes again.

### Core changes and playability

80. **Core changes**, each a no-op on the base scripts (their fingerprints are identical, and so are carousel-1 to
    carousel-3's): a character may be held by several players (`Character.duplicates`, the Village Idiot's three);
    an end-of-night hook (the Acrobat); a 'registers evil' state (the Lycanthrope's); a good ability a Demon has
    through another's whose sobriety counts (`Grimoire.gift`: the Boffin); secret votes and a compelled hand
    (`Character.secret_votes`, `must_vote`, `followers_blind`: the Organ Grinder, the Zealot, the Butler jinx); a
    Demon's night choice limited to one player (the Alchemist-Spy's right guess); abilities gained beyond a
    character wake a player for that character's step and inform them as before, now also when a Demon has them
    through the Boffin. The Godfather and the Assassin act for a living player who has the ability without being the
    character (the Alchemist); the Assassin is spent per player (snv.use), so two players with it each have one use
    (finding B12: identical with one Assassin, so BMR replays). Setup steps that turn Townsfolk into other characters
    (the Balloonist's and Xaan's Outsider, the Village Idiot's extras) never take a Townsfolk whose own setup has run
    (the Alchemist: finding B11).
81. **The fourth synthetic script** (`clocktower/data/scripts/carousel-4.json`, "Carousel test 4"): the thirteen,
    with the Cannibal, Empath, Monk, Chef, Washerwoman, Investigator and Undertaker; the Butler, Drunk, Goon,
    Heretic, Politician, Plague Doctor and Recluse; the Spy, Widow, Marionette, Mastermind, Summoner and Pit-Hag; the
    Imp and the Leviathan. All eighteen batch 3 jinxes are on it, and every size from 5 to 15
    deals. Its replay fingerprints are
    `tests/data/fingerprints-carousel-4.json`.

New weights: `idiot_extra_one` 0.35, `idiot_extra_two` 0.25, `lycanthrope_misregister_good` 0.5, `harpy_kill` 0.8,
`harpy_first` 0.6, `harpy_both` 0.2, `boomdandy_keep_demon` 0.9, `plague_boomdandy_minion` 0.8. The rules judge has
no heuristic of its own for the new calls (the scripted style decides, or its balance for the yes/no ones that help
a team).

## Batch 3b: nine experimental characters

The Alsaahir, Huntsman, Snitch, Knight, Choirboy, King, Cult Leader, Lord of Typhon and Lleech
(`clocktower/carousel4.py`, loaded after carousel3; tests in `tests/test_carousel3b.py`, Storyteller's notes in
`clocktower/data/storyteller/carousel.md`). With the Lleech, the World Championship's Buyer's Remorse plays end to end.
The eight official jinxes between them and built characters are all implemented, the Boffin's with the Cult Leader
(left pending by batch 3) among them. None of the nine needed a design the brief keeps for the owner: the Cult
Leader's cult vote is a separate yes/no, not a change to the execution vote.

### Townsfolk

82. **The Alsaahir.** The guess is a public use of the `ability` field whose `guesses` name players, each with a
    Minion or a Demon character on the script: only the type counts ("X is the Poisoner" guesses X a Minion), and a
    guess naming a good character is ignored. It is right when the players named as Minions are exactly the players
    whose character is a Minion, and likewise for the Demons, the dead included, by the Grimoire's truth (no
    misregistration: a Spy is a Minion, a Recluse is not; option: let a misregistering player count either way, a
    judged call). One guess a day per Alsaahir, alive (a dead one has no ability); a right guess with a working
    ability wins for good at once, a drunk or poisoned one's is an abnormal result. Anyone may claim one, as with any
    public ability; a player who claims it with no guesses is told how to name them.
83. **The Huntsman.** "[+the Damsel]": in a dealt game, if the Damsel is on the script and not in play, she takes the
    seat of a dealt Outsider (so the counts hold), or, with none, of a Townsfolk (one more Outsider), never a Drunk,
    a Lunatic or a character whose own setup step has run; only for a real Huntsman (a Drunk who believes they are one
    adds none: a setup modifier belongs to the character in play), and a forced setup keeps its characters. Option:
    always in a Townsfolk's seat. "Once per game, at night": any night, the first included; choosing no one keeps it;
    choosing any living player spends it (a drunk Huntsman's too, and a Drunk's who believes they are one, so they
    are not woken again). A working Huntsman's chosen Damsel becomes a Townsfolk on the script that nobody has or
    believes they have and that has no setup step (the Storyteller's choice), keeping her alignment, and is told; the
    Huntsman is not told.
84. **The Marionette/Huntsman jinx.** A Marionette who believes they are the Huntsman brings the Damsel at setup, as a
    real Huntsman does (the Huntsman's setup step runs after the Marionette's).
85. **The Knight.** On their first night (or when they become one), two other players neither of whom registers only
    as the Demon (a Recluse may be shown). Drunk, poisoned or under the Vortox: any two, misinformed with the Demon
    among them.
86. **The King.** "The Demon knows you are the King": on the first night, every Demon in play learns which player is a
    real King (a Drunk's King has no ability: no Demon is told); a player who becomes a Demon later through a reported
    change (the Pit-Hag's, the Summoner's, a Fang Gu's jump) or a new King learns it then. The Imp's starpass does not
    pass it on (the engine reports no change there: an option). "If the dead equal or outnumber the living": by the
    town's view, counted at the King's step each night (the first night too, harmlessly). "1 alive character": the
    character a living player other than the King can register as (the King's own when nobody else lives: finding
    B15). With the Leviathan in play (its jinx), from the first death on. Drunk, poisoned or under the Vortox: any
    character on the script, misinformed with one nobody alive has.
87. **The Choirboy.** "[+the King]": in a dealt game, if the King is on the script and not in play, a Townsfolk (not
    one whose setup step has run, and after the Village Idiot's extras) becomes the King; only for a real Choirboy.
    "If the Demon kills the King": a Demon's attack (cause `demon`, a Mayor's bounce onto the King too) kills the
    player who is the King; that night the Choirboy, alive, learns the Demon who attacked (or the Demon now, if the
    attacker is no longer one). The King's execution or any other death tells nothing. Drunk, poisoned or under the
    Vortox: any player, misinformed with another.
88. **The Cult Leader's alignment.** Each night, the first included, a Cult Leader with a working ability takes the
    alignment of one of their alive neighbours (the town's view): the Storyteller's choice when the two differ (POLICY
    `cult_leader_evil` 0.5, default, for review), and they are woken and told only when it changes. A drunk or
    poisoned one changes nothing.
89. **The cult vote.** "If all good players choose to join your cult": by day, on a public turn, any player may call a
    cult vote through the `ability` field (a bluff's vote is held the same way, so it looks the same); one a day, the
    first call. Every player, alive or dead, is asked in private (`decide`, eyes closed) whether to join. If every good
    player (by alignment at the vote, the dead included) joined and the caller is alive with a working Cult Leader's
    ability, the caller's team wins at once; otherwise the Storyteller announces only that the vote is over (no count,
    no names). Options: only the living count; the vote is open (hands raised); several calls a day.
90. **The Cult Leader's jinxes.** Boffin: the Boffin may give the Demon the Cult Leader's ability; it never turns that
    Demon good (its cult vote can win for evil). Pit-Hag: an evil player the Pit-Hag makes the Cult Leader never turns
    good by it; a good player made it later is free (as the Goon's and Politician's jinxes).

### Outsiders

91. **The Snitch.** On the first night only, at the Snitch's step, while a player with the ability (a Philosopher's,
    a Demon's through the Boffin) is sober and healthy: each Minion who knows they are one (not a Marionette) is shown
    three good characters nobody has or believes they have, chosen for each Minion as the Demon's bluffs are (they may
    differ from the Demon's and from each other). A drunk or poisoned Snitch gives nothing. A Minion made later gets
    none.

### Demons

92. **The Lord of Typhon's setup.** "+1 Minion": one Minion more than the table's, in a Townsfolk's seat
    (`Character.extra_minions`; `state.random_setup` draws it after the Demon, so scripts without the Lord of Typhon
    draw exactly as before). The extra is never the Summoner or the Kazali's kind (no Demon, no Minions), nor a Minion
    whose modifier is the Storyteller's choice (the Godfather), and leaves at least two Townsfolk; a script with too
    few Minions or Townsfolk is not dealt the Lord of Typhon. "Evil characters are in a line. You are in the middle":
    the dealt tokens are moved before anyone is told their character (as the Marionette's seat is), in a forced setup
    too: the Minions take the seats beside the Lord of Typhon, a side each, the sides differing by at most one (the
    Storyteller picks the longer side), and the players there take the Minions' seats. The first night's "show the
    neighbours they are Minions" is then the ordinary evil information. "-? to +? Outsiders": in a dealt game, as dealt
    (POLICY `typhon_outsiders_same` 0.6), else one fewer (`typhon_outsiders_fewer` 0.75, to offset the extra Minion),
    else one more, keeping two Townsfolk (finding B17); `setup_error` accepts any number of Outsiders with it, as with
    the Kazali. Options: more than one Outsider either way.
93. **The Summoner/Lord of Typhon jinx.** A Lord of Typhon summoned onto a player who neighbours no Minion goes instead
    to a player the Storyteller picks (usually a good one) who does; then its other neighbour, if not a Minion, becomes
    an evil Minion on the script not in play (the Storyteller's, never the Marionette), and is told.
94. **The Lleech's host.** "You start by choosing a player": on the first night, another player (not themself),
    whatever the Lleech's sobriety; the host is poisoned for the rest of the game while the Lleech has its ability,
    paused while the Lleech is drunk or poisoned (as the Poisoner's poison). A Lleech made later (the Pit-Hag's, a
    Scarlet Woman's takeover) has no host: on its next night it chooses one instead of killing (a reading). A swap
    (the Snake Charmer's, the Barber's) moves the host with the character. Each other night it kills.
95. **"You die if & only if they are dead."** While the host lives and the Lleech's ability works, nothing kills the
    Lleech (an execution fails, the Slayer's shot, its own choice, the Pit-Hag's arbitrary deaths), except the
    Assassin, whose kill goes through everything. When the host dies, by any cause, a Lleech with a working ability
    dies at once (announced at dawn, or at once by day). A drunk or poisoned Lleech can die normally and does not die
    with its host; once its host is dead it is an ordinary Demon.
96. **The Lleech's jinxes.** Slayer: a Slayer's shot at the host kills the host (and so the Lleech). Mastermind: a host
    executed while a Mastermind lives leaves the Lleech alive with no ability (no kill, no poison, and no protection:
    it can then be executed). Heretic: only one of the two in play (Script.clash), and a Summoner who names the Lleech
    with the Heretic in play summons another Demon on the script, the Storyteller's choice (finding B16).
97. **The Boffin's new abilities.** The Boffin may now give the Demon the Knight's, the Snitch's or the Cult Leader's
    ability (each runs for a Demon who has it). Not the Alsaahir's (a Demon's right guess would win for good), the
    Huntsman's (it hunts a Damsel the Demon's team would rather keep), the King's or the Choirboy's (about the Demon
    itself).

### Core changes and playability

98. **Core changes**, each a no-op on the base scripts (their fingerprints are identical, and so are carousel-1 to
    carousel-4's): a Demon's setup modifier for extra Minions (`Character.extra_minions`, in `state.random_setup` and
    `setup_error`); the Slayer's shot at a Lleech's host (the jinx, in `characters.Slayer`); the Pit-Hag's lock for an
    evil Cult Leader (in `snv.PitHag`); the Summoner's Lord of Typhon jinx and its substitute for a Demon that cannot be
    in play (in `carousel.Summoner`).
99. **The fifth synthetic script** (`clocktower/data/scripts/carousel-5.json`, "Carousel test 5"): the nine, with the
    Slayer, Empath, Chef, Washerwoman, Monk, Undertaker and Fortune Teller; the Damsel, Heretic, Drunk and Recluse; the
    Boffin, Pit-Hag, Mastermind, Marionette, Summoner, Poisoner and Spy; the Leviathan and the Imp. All eight batch 3b
    jinxes are on it, and every size from 5 to 15 deals. Its replay fingerprints are
    `tests/data/fingerprints-carousel-5.json`.

New weights: `cult_leader_evil` 0.5, `typhon_outsiders_same` 0.6, `typhon_outsiders_fewer` 0.75. The rules judge has
no heuristic of its own for the new calls (the scripted style decides).

## Batch 4: eight experimental characters

The Bounty Hunter, Engineer, Princess, Hermit, Ogre, Psychopath, Wraith and Vizier (`clocktower/carousel5.py`,
loaded after carousel4; tests in `tests/test_carousel4.py`, Storyteller's notes in
`clocktower/data/storyteller/carousel.md`). With them the Carousel Script Collection's Contempt plays end to end. The
twenty official jinxes between them and built characters are all implemented, among them the Alchemist's, the Plague
Doctor's and the Magician's with the Wraith, the Boffin's with the Ogre and the Vizier's seven (the Legion's with the
Engineer and Lil' Monsta's with the Psychopath and the Vizier wait for those characters). None of the eight needed a
design the brief keeps for the owner. The Vizier decides executions, it does not change votes: once a vote is over it
may execute the nominee at once, through a core hook that does nothing on any script without it (ruling 116). The
Amnesiac, Mezepheles and Yaggababble are batch 5; the Wizard, Legion, Riot, Atheist and Lil' Monsta batch 6.

### Townsfolk

100. **The Bounty Hunter's evil players.** "You start knowing 1 evil player": on the first night (or, for a player
     who gets the ability later, the Pit-Hag's or a Philosopher's, at once), another living player who can register
     as evil (a Recluse may be shown, by its usual chance; a Spy may not be passed over as good). "If the player you
     know dies, you learn another evil player tonight": at the Bounty Hunter's step on any night once the player they
     know is dead (as the town sees it: died today or tonight), a living player who can register as evil and has not
     been shown to them before; with none, nothing, and nothing more later. Drunk, poisoned or under the Vortox: any
     other living player, misinformed with a good one. Option: allow a dead player, or one shown before.
101. **"[1 Townsfolk is evil]".** Once per game, for a Bounty Hunter in play (a Drunk who believes they are one makes
     none, as every setup modifier: ruling 83), in a forced setup too (it changes an alignment, not a character): a
     good Townsfolk, not a Bounty Hunter, the Storyteller's choice, turns evil before anyone is told their character.
     The setup step runs once the characters are final (after the Huntsman's Damsel) and before any step that picks a
     good player (the red herring, the Grandchild, the Faux Paw, the Evil Twin's twin: finding B18). The evil Townsfolk
     is told in their introduction that they are evil and nothing more; the evil team is not told about them (a
     reading of "they know they are evil"). They win with evil and register as evil. The scripted Storyteller avoids
     a choice that leaves a Noble no three players exactly one of whom is evil (a five-player table: finding U11).
     Options: the evil Townsfolk learns the Demon, or the Demon learns them.
102. **The Bounty Hunter's jinxes.** Kazali: with the Kazali in play the evil Townsfolk waits for the Kazali's
     first-night choice; at the Bounty Hunter's step that night (after the Kazali's), if a Bounty Hunter is still in
     play a Townsfolk turns evil and is told at once ("you are now evil"); if the Kazali made the Bounty Hunter a
     Minion, none does. Philosopher: when a Philosopher gains the ability, a good Townsfolk (not the Philosopher) turns
     evil half the time (POLICY `bounty_philosopher_evil` 0.5, default, for review) and is told at once, unless an
     evil Townsfolk was already made.
103. **The Engineer.** "Once per game, at night": the Engineer names a character (`character`, null keeps it). A
     Demon: the living Demon becomes it (with several, the Storyteller picks which, so two players never share it; a
     Demon already in play, or one jinxed out of play, changes nothing). A Minion: the Engineer then names the rest one
     request at a time, as many as there are living Minions (not a Marionette), each different; a Minion already
     holding a named character keeps it and the others take the rest, the Storyteller's assignment, all at once, each
     woken and told. The dead keep their characters (option: change them too). Never the Marionette (it believes it
     is good and sits by the Demon from the start), the Summoner (no Demon) or the Kazali (no Minions): naming one
     keeps the ability, with a notice. The new characters' setup parts do not happen (no Lord of Typhon line, no
     Fang Gu Outsider); a new Lleech chooses a host on its next night (ruling 94). Spent even if drunk or poisoned,
     then nothing changes. A Drunk who believes they are the Engineer spends it for nothing.
104. **The Summoner/Engineer jinx.** "If the living Summoner is removed from play, the Storyteller has the Summoner
     ability": a living Summoner the Engineer turns into another Minion before it summons leaves the ability with the
     Storyteller (`g.notes['Storyteller abilities']`, as the Plague Doctor's): until the third night no Demon is no
     win for good, and at the Summoner's step on the third night the Storyteller makes a player (usually a living good
     one, POLICY `summoner_st_honours`'s choice) an evil Demon on the script not in play (finding B22: never one
     already in play).
105. **The Princess.** "Your 1st day": day 1, or for a Princess made later the next day she is one (a reading): made
     at night, the day that follows that night; made by day, that day (finding EC-13 fixed a day's delay).
     "Nominated & executed": she made the last nomination of the player executed that day (died or not, the Vizier's
     immediate execution included). That night, at her step (before the Demons'), with her ability working (alive,
     sober, healthy then), the Demon wakes as normal but its attacks kill nobody tonight (Game.demon_kills_stopped,
     as the Pit-Hag's "no one dies"); its other effects (a Pukka's poison) stand. Option: judge her sobriety at the
     execution.
106. **The Princess's jinxes.** Al-Hadikhia: its kills are the Demon's, so its three survive (the stop covers it as
     written). Cannibal: a Cannibal who nominated, executed and killed the Princess today holds her ability, and that
     night the Demon kills nobody; without the jinx a Cannibal's Princess ability never has a first day (it was not
     theirs when they nominated).

### Outsiders

107. **The Hermit's abilities.** "You have all Outsider abilities": every Outsider on the script, in play or not, but
     the Drunk's and the Lunatic's (illusions dealt at setup about who a player believes they are: the Hermit knows),
     the Butler's (the engine keeps one master a game, `Grimoire.master`) and the Puzzlemaster's (one puzzle and one
     drunk player a game). They are held as gained abilities (`extra`, a `gains` event each, at setup or when a player
     becomes the Hermit), so each acts as for a Philosopher who gained it: the Hermit wakes at its step (the Ogre's
     choice), its hooks run (the Tinker's death, the Klutz's, Moonchild's, Sweetheart's and Barber's deaths, the
     Golem's nomination, the Zealot's vote, the Mutant's madness, the Snitch's bluffs, the Damsel's hunt); the hooks
     the engine asks of a player's own character are passed on (the Recluse's registration, the Saint's execution,
     the Damsel's news for the Minions, the Plague Doctor's end, the Politician's and the Heretic's). Code that asks
     whether a player is the Outsider itself now accepts the Hermit too (`characters.holds`: the Politician, Heretic,
     Damsel's Spy jinx, Tinker), and nothing else changes for anyone else. The result turns around once, whoever has
     the Heretic's ability: a sober Heretic in play turns it already, so two do not cancel out. Drunk or poisoned,
     every ability stops. A Philosopher who gains the Hermit's ability gains no more (a reading: it names abilities,
     not a character). Options: a Hermit with the Drunk on the script is drunk all game (the Drunk's ability); a
     second master for a Hermit-Butler.
108. **The Hermit's "[-0 or -1 Outsider]".** In a dealt game, one fewer half the time (POLICY
     `hermit_fewer_outsider` 0.5, default, for review): another Outsider becomes a Townsfolk not in play (keeping one
     for a Drunk to believe), after the other Outsider changes (the Balloonist's, the Kazali's) and before the Xaan
     counts them; `setup_error` accepts both counts. A forced setup keeps its characters.
109. **The Ogre.** "On your 1st night, choose a player (not yourself)": a required choice on the first night, whatever
     the Ogre's sobriety ("even if drunk or poisoned"). The Ogre takes the alignment the chosen player registers as to
     it (a Recluse might register evil, by its usual chance; a Spy might register good, but for its jinx), silently:
     no "you are now", and the Storyteller's other reactions to a change of alignment run (the Cult Leader's, the Evil
     Twin's). A Drunk who believes they are the Ogre changes nothing. The official night order wakes the Ogre on the
     first night only, so a player who gets the ability later (the Pit-Hag's Ogre, a Philosopher's, a Hermit made
     later) chooses at once, as the change is made (a reading: that night is their first). Option: their first
     whole night.
110. **The Ogre's jinxes.** Spy: the Spy always registers as evil to it. Recluse: a Recluse who registers as evil to
     it makes it evil, and it is told so. Pit-Hag: an evil player the Pit-Hag makes the Ogre stays evil whoever it
     chooses (as the Goon's, Politician's and Cult Leader's locks). Boffin: the Demon is never given the Ogre's
     ability (it is not among the Boffin's abilities).

### Minions

111. **The Psychopath's kill.** "Each day, before nominations, you may publicly choose a player": through the public
     `ability` move with a `target`, on a public turn of the day, never during the nominations' comments; once a day,
     alive. Anyone may claim it (a bluff looks the same, and nothing happens). A working Psychopath's target dies at
     once, announced (not why), through the usual protections (a Tea Lady's neighbour lives); the game may end on it.
     Drunk or poisoned, the day's choice is spent and nobody dies.
112. **The roshambo.** "If executed, you only die if you lose roshambo": a living Psychopath with a working ability
     who is executed (by vote, by the Vizier, by a madness ruling) plays the player who nominated them (the
     Storyteller, with no nominator). The result is the Storyteller's judged call, a fair draw for the scripted
     Storyteller (POLICY `psychopath_roshambo_win` 0.5, default, for review: rock-paper-scissors with ties replayed is
     even); a judge may rule otherwise. It is announced; won, the Psychopath survives the execution (as the town sees:
     "survived"). Drunk or poisoned: no roshambo, they die. Option: ask the two players to throw (rock, paper or
     scissors), ties again, so the players themselves pick.
113. **The Wraith.** "You may choose to open your eyes at night": asked each night at its step, the night's first
     (`decide`). "You wake when other evil players do": either way, just before dawn it is told who woke tonight to use
     an ability and whom (or which character) they chose: every player with its eyes open, only the evil players with
     them shut. Never what anyone was shown (the Storyteller's tokens and fingers are hidden). Drunk or poisoned, it is
     told nothing (no false wakes are staged). Options: tell it at each step as it happens; let opening its eyes risk
     being seen.
114. **The Wraith's jinxes.** Alchemist: an Alchemist-Wraith has no ability, a Wraith is in play, and after each
     execution the living Alchemist may publicly guess a living player as the Wraith; right, the Demon must choose
     them that night (as its Spy and Widow jinxes: ruling 72). Magician: after each execution the living Magician may
     guess the same way (not while the Vizier takes the Magician's ability). Plague Doctor: if the Storyteller would
     gain the Wraith's ability, a living Minion gains it and learns this.
115. **The Vizier's announcement and protection.** "All players know you are the Vizier": every player's introduction
     says who it is (a Vizier made later, the Engineer's or the Pit-Hag's, is announced at once), unless the Alsaahir
     or the Investigator is on the script (their jinxes: not declared). "You cannot die during the day": every death by
     day fails while its ability works (an execution "survived", the Psychopath's kill, the Slayer's shot, the
     Tinker's); at night it dies as anyone does.
116. **"If good voted, you may choose to execute immediately".** After each vote in which a player who registers as
     good to the Vizier raised a hand (a Spy might register good, a Recluse evil: the Storyteller's judged call for
     each, POLICY `vizier_registers_evil` 0.5, default, for review), the living Vizier with a working ability is asked
     (`decide`) whether to execute the nominee now, whatever the tally. Yes: it is announced, the nominee is executed
     at once, today's execution, and the day's nominations end. With secret votes (the Organ Grinder) it is still
     asked: the Storyteller knows who voted (a reading). This is a core hook (`Character.vote_over`, asked by
     `Game.vote_over_judged` after each vote) that does nothing on any script without the Vizier: the vote itself
     never changes, so it is not one of the vote-changing characters the brief keeps for the owner. Options: "good
     voted" as "most voters were good"; never asked under secret votes.
117. **The Vizier's jinxes.** Alsaahir, Investigator: not declared. Courtier, Preacher: a Vizier made drunk by the
     Courtier, or chosen by the Preacher, is told so (just before dawn) and still cannot die by day, though it cannot
     execute anyone. Fearmonger: the Vizier learns whom the Fearmonger chose whenever the choice is new (just before
     dawn) and cannot execute that player by its ability. Magician: with the Vizier in play the Magician has no ability
     (no first-night illusion, no Wraith guess), and the Vizier cannot execute the Magician by its ability. Politician,
     Zealot: a Politician or Zealot who voted might register as evil to the Vizier (the same judged call).

### Core changes and playability

118. **Core changes**, each a no-op on the base scripts and on carousel-1 to carousel-5 (their fingerprints are
     identical): `Character.vote_over` and `Game.vote_over_judged` (the Vizier); introduction lines a setup step leaves
     in `g.notes['Intro']` (the Bounty Hunter's evil Townsfolk, the Vizier's name); `characters.holds` (an Outsider's
     code accepts the Hermit, and the Tinker's night death acts for one); the Alchemist's, Plague Doctor's and
     Magician's Wraith jinxes and the Pit-Hag's Ogre lock (guarded by `Script.jinxed`). Fixes the fuzzer found
     (docs/interaction-findings.md): the red herring is never an evil Townsfolk (B20); a spent Assassin no longer acts
     on a choice its player made with another ability the same night (B21); a Lleech swapped onto a dead player
     poisons nobody (B19).
119. **The sixth synthetic script** (`clocktower/data/scripts/carousel-6.json`, "Carousel test 6"): the eight, with the
     Alchemist, Philosopher, Cannibal, Magician, Alsaahir, Courtier, Investigator, Preacher, Empath, Chef and
     Washerwoman; the Recluse, Politician, Zealot, Plague Doctor and Saint; the Boffin, Pit-Hag, Spy, Summoner,
     Fearmonger and Poisoner; the Al-Hadikhia, Kazali and Imp. All twenty batch 4 jinxes are on it, and every size from
     5 to 15 deals. Its replay fingerprints are `tests/data/fingerprints-carousel-6.json`.

New weights: `bounty_philosopher_evil` 0.5, `hermit_fewer_outsider` 0.5, `psychopath_roshambo_win` 0.5,
`vizier_registers_evil` 0.5. The rules judge has no heuristic of its own for the new calls (the scripted style
decides).

## Batch 5: the Mezepheles, the Yaggababble and the Amnesiac

The three characters the brief kept for a design agreed with the owner, brought in by its batch 5 update
(`clocktower/carousel6.py`, loaded after carousel5; tests in `tests/test_carousel5.py`, Storyteller's notes in
`clocktower/data/storyteller/carousel.md`). Two are triggered by speech, through a core hook that does nothing on any
script without them; the Amnesiac's ability is drawn from a curated list the engine can run. With them the Carousel
Script Collection's Harold Holt, Insanity Intuition, Ones You Least Expect and Punchy play end to end, and the World
Championship corpus's Dead Council, Phantom Detectives, River Styx and Warrens. The one official jinx between them
and a built character (the Yaggababble's with the Exorcist) is implemented. The Wizard, Legion, Riot, Atheist and Lil'
Monsta are batch 6.

### Hearing what is said

120. **What counts as saying.** Every word a player says to other players reaches the listening abilities on the
     script (`Character.listens`, `heard`, called from `Game.emit` for the speech events, `game.SPEECH`): the town
     square, nomination accusations, defenses, comments, the remark with a vote and the text of a public ability
     claim, aloud; whispers, in private (and a remark with a secret vote under the Organ Grinder, which only the
     Storyteller hears, counts as private). What a player tells the Storyteller on a visit (the Savant's, the Artist's,
     the Amnesiac's guess) and night choices are not said to anyone, so they never count. Option: count visits too.
121. **The match.** A word or phrase is said when its words appear next to each other, in order, as whole words of
     what was said: lowercased, an apostrophe joining its word ("let's" is "lets"), every other run of punctuation or
     spacing one break (`game.words`, `game.said`). "Trusted" is not "trust", "distrust" is not "trust". Each
     non-overlapping occurrence counts (twice in one sentence is twice: the Yaggababble's count).
122. **Near misses.** A near miss (`game.nearly_said`: the word with up to four more letters, a shorter form of four
     letters or more, one letter added, missing or changed in a word of five or more; for a phrase, each word so, or one
     extra word inside it) is never counted by the scripted Storyteller, which is not even asked. With a judge, each is
     a judged call (`speech_near_miss`) at the next safe point; the rules judge counts another form of the same word (an
     ending: s, es, 's, d, ed, ing, ly, er), not a misspelling, a different word or an inserted one; a model judge
     decides as it sees fit. A near miss ruled in counts from when it was said, so "the first" stays the first.
123. **Whispers.** They count for the Mezepheles ("the 1st good player to say this word": saying is saying, in public
     or private; the Storyteller here hears every whisper), not for the Yaggababble ("each time you said it
     publicly"). Option: public speech only for both (a human Storyteller does not hear whispers).
124. **Choosing the word and the phrase.** From a curated list of ordinary table talk, twenty words for the Mezepheles
     and twenty phrases for the Yaggababble (`clocktower/data/storyteller/speech.json`, default, for review): each one
     common enough to be said by accident now and then (honestly, obviously, evidence; to be fair, the thing is, mark my
     words), none so common that saying it is certain (no player or character names, no game words like vote, Demon or
     evil). The draw is a judged call among them (a judge chooses, never inventing one); the scripted Storyteller draws
     at random; never one another player already has. Options: a longer list; one picked per table size.
125. **Who learns it.** The player with the ability (or who believes they have it: a Lunatic who believes they are the
     Yaggababble learns a phrase too, and nothing comes of it) is told at their first-night step (that is the step's
     reminder) and privately reminded at each later dawn, so it stays in view however long the conversation gets.
     Nobody else learns it: it is not written on the Grimoire the Spy and the Widow see (a reading: the token is a
     reminder, the word is the Storyteller's). A player who becomes one later (the Pit-Hag's, a Demon's jump, a Snake
     Charmer's swap) gets a new word or phrase at once; the old player's is theirs. The player prompt says that such
     abilities exist on the script, how a word counts, and that only the holder learns it.
126. **Random bots say the words.** The bots' fixed lines never contain them, so on a script with a listening ability
     (only there) each turn carries the lists' lines (`Request.chatter`, read only by random bots), and a bot says one
     on about 30% of its turns (in a whisper on a private turn), a few near-miss forms among them, and the Yaggababble's
     bot its own phrase often. On any other script the bots draw nothing more, so their play and every recorded
     fingerprint are unchanged.

### Minions

127. **The Mezepheles's first good player.** "The 1st good player to say this word": good as they are when they say
     it (dead players too: they still talk; the Bounty Hunter's evil Townsfolk not), aloud or in a whisper, while a
     living player has the ability (drunk or not: that is tested at night). Said after the Mezepheles died, it is
     nothing. Each Mezepheles has its own word and first player.
128. **"Becomes evil that night".** At the Mezepheles's step the night after the word was said: the player turns evil
     and is told ("you are now evil"), and learns nothing else; the Mezepheles is not told. The ability is then spent
     ("No Ability"), whether or not anyone turned: drunk or poisoned at its step, nobody turns (abnormal, for the
     Mathematician), and a player already evil stays as they are. Option: the Mezepheles's sobriety as the word is said.

### Demons

129. **The Yaggababble's count.** "For each time you said it publicly today": only what the player with the ability
     says aloud, alive, each occurrence (another player saying the phrase, or the Yaggababble whispering it, counts for
     nothing), drunk or not (tested at night). A Lunatic who believes they are it counts nothing.
130. **"A player might die".** At its step the next night, for each time, a judged call: which player dies, any living
     player but the Yaggababble (a reading: it is no starpass), not one chosen already tonight, or nobody. The scripted
     Storyteller kills on 75% of them (POLICY `yaggababble_kill`, default, for review), a random living good player.
     Each is the Demon's kill (`attempt_kill`, cause 'demon'): the Monk, the Soldier, the Princess and the Pit-Hag's
     "no one dies" stop it, the Mayor may bounce it, the Sage learns of it. Drunk or poisoned at its step it kills
     nobody (abnormal); on the first night nothing (no day before). Option: cap the deaths per night.
131. **The Exorcist jinx.** If the Exorcist chose the Yaggababble tonight, its phrase kills nobody tonight. Without the
     jinx (a script that leaves it out) an exorcised Yaggababble still kills: it does not wake to kill, the Storyteller
     does it.

### Townsfolk: the Amnesiac

132. **The list.** The Amnesiac's ability is one of 31 (`carousel6.AMNESIAC`, default, for review), each run by the
     engine's code: 24 built characters' abilities reworded (the Washerwoman's, Librarian's, Investigator's, Chef's,
     Clockmaker's, Steward's, Noble's and Shugenja's starting information; the Empath's, Undertaker's, Oracle's,
     Flowergirl's and Town Crier's nightly; the Fortune Teller's, Dreamer's, Seamstress's and Monk's choices; the
     Soldier, Fool, Tea Lady, Virgin, the Mayor's three-alive win, the Ravenkeeper and the Sage) and 7 small ones of the
     Amnesiac's own (how many Outsiders are in play; which Demon is in play; whether a neighbour is the Demon; the
     executed player's alignment; each night whether a chosen player is a Townsfolk; once, a chosen player's
     alignment; once, a chosen player cannot die tonight). Left out: public abilities (the Slayer's shot, the Gossip's:
     the Amnesiac cannot claim what it does not know), madness, setup modifiers, and abilities that change characters.
     The draw at setup is a judged call among them (a judge chooses, never inventing one); the scripted Storyteller
     draws at random. The Fortune-Teller-like ability has no red herring of its own (the Fortune Teller's, if one is in
     play, registers to it as to anyone).
133. **Not knowing it.** The Amnesiac is never told the text. When its ability needs a choice it is woken with "Your
     ability asks you to choose a player (not yourself). You are not told why." (the number of players and "not
     yourself" do show; a reading: a Storyteller's fingers would too); what it learns comes as "your ability tells
     you: ..." in the model ability's own words, which are no more telling than a Storyteller's info tokens.
     Introduction: it is told it does not know its ability, and how to guess.
134. **When it acts.** Its step moves to just before the first Demon's on the night order (`Character.wakes_before`, a
     core order rule nothing else uses), so a protection works; its information comes at the night's end, after every
     step (as the Empath's would). "You start knowing": the first night it has the ability (one made later learns at
     the next night's end); "each night*": not the first. A death trigger (the Ravenkeeper's, the Sage's) acts at the
     night's end, when it has died tonight.
135. **The guess.** "Each day, privately guess what it is": a visit to the Storyteller (`visit`, as the Amnesiac, the
     guess in `text`; once a day, alive; the Savant's and the Artist's channel), answered hot (right, or very nearly),
     warm (partly) or cold. The scripted Storyteller's closeness (`carousel6.amnesiac_closeness`): hot if the guess
     names the model character or two of the ability's key words, warm if one key word or the right kind of ability
     (information, protection, a death, nominations), cold otherwise. Sober, any of the three is legal (it is a
     judgement; a judge may rule otherwise); drunk or poisoned, the scripted answer is usually wrong (POLICY
     `poisoned_false`); under the Vortox (a Townsfolk's information) never the code's closeness. An empty guess is
     not one. Options: a numeric closeness; a guess also changes how the Storyteller runs it (the almanac's "if they
     guess right, their ability may change"; not done).
136. **Edges.** A Drunk who believes they are the Amnesiac has a pretend ability drawn the same way: woken and told
     things at its step (true or false by the Drunk's chance), protecting nobody, its guesses answered as
     misinformation. A Philosopher or Cannibal who gains the Amnesiac's ability, or a player the Pit-Hag makes one, has
     a new ability drawn at once. The standing abilities (the Soldier's, Fool's, Tea Lady's, Virgin's) work only for a
     player who is the Amnesiac (the engine asks those of a player's own character); the rest work for any holder.
     Once-per-game abilities are spent per player, even drunk or poisoned.

### Core changes and playability

137. **Core changes**, each a no-op on the base scripts and on carousel-1 to carousel-6 (their fingerprints are
     identical): `Character.listens`, `heard` and `chatter`, `Game.heard` (from `Game.emit`) and `Game.chatter`, the
     matching in `game.words`, `said` and `nearly_said`, `Script.listeners`, `Request.chatter` and the random bots'
     lines; `Character.wakes_before` in the night order (`characters.after`); a custom-script prompt sentence on
     listening abilities; the rules judge's `speech_near_miss` heuristic. The fix the fuzzer found
     (docs/interaction-findings.md): the Amnesiac's step acts only on a choice asked at its own step tonight (B23). Two
     interactions of earlier batches it turned up are recorded for the owner, not changed (U12, the Noble and the Lord
     of Typhon at 5 players; U13, the Plague Doctor's Marionette jinx choosing a dead neighbour, whose fix would change
     a carousel-3 and a carousel-4 replay).
138. **The seventh synthetic script** (`clocktower/data/scripts/carousel-7.json`, "Carousel test 7"): the three, with the
     Exorcist, Philosopher, Monk, Soldier, Empath, Fortune Teller, Virgin, Sage, Mathematician, Chambermaid, Princess and
     Undertaker; the Drunk, Recluse, Lunatic and Saint; the Pit-Hag, Spy and Poisoner; the Imp, Vortox and Fang Gu. Its
     one jinx is on it, and every size from 5 to 15 deals. Its replay fingerprints are
     `tests/data/fingerprints-carousel-7.json`.

New weights: `yaggababble_kill` 0.75. The rules judge's new heuristic: `speech_near_miss` (ruling 122); it has none
for the word, phrase or ability draws, nor the Amnesiac's closeness (the scripted style decides).

## Batch 6 (removable): Lil' Monsta, the Atheist, the Wizard, Legion and Riot

The five characters the brief kept for a design with the owner, brought in by its batch 6 update on one condition:
each can always be taken out again. Each is a section of its own in `clocktower/carousel_extra.py` (loaded last),
with its tests in `tests/test_carousel_<id>.py`, its Storyteller's notes in `clocktower/data/storyteller/extra-<id>.md`,
its synthetic script (one character each: never two of them on one script, so each replays on its own) and its rulings
in its subsection below. Each can be switched off (`CLOCKTOWER_WITHOUT=<id>`, or `python -m clocktower --without <id>`:
its section registers nothing, a script naming it says it is not built, and its tests skip) or deleted for good (its
section, its test file, its examples class, its notes file, its synthetic script and fingerprints:
`carousel_extra.py`'s docstring lists them); `tests/test_extra_removable.py` checks the switch for each of the five and
for all five at once. (Each was first built in one commit so that `git revert` would remove it; later fixes inside the
sections make those reverts conflict, so the switch and the deletion replace them.) Nothing outside its section names
it; each core hook it needs does nothing on a script without it, and every recorded fingerprint (TB, BMR, S&V,
carousel-1 to carousel-7) replays identically with it in or out. The generic hooks two or more of them use were added
first, in a commit of their own that names none of them: `Character.deals`
(`deal_error`, `redeal`: a character whose presence changes the whole deal, asked by `state.setup_error`,
`state.random_setup` and the fuzzer's forced setups; a redeal may return None to draw again, and a deal's character may
hold or change the end, `Grimoire.check_victory` asking its `overrides_end` with nobody holding it) and
`Character.rule_text` (sentences the custom-script prompt adds for a rule a character brings). A character that could
not be kept isolated would be removed and left here as a design note instead.

### Lil' Monsta

Built (section "Lil' Monsta" of `carousel_extra.py`; tests `tests/test_carousel_lilmonsta.py`; notes
`data/storyteller/extra-lilmonsta.md`; script `carousel-8`). Its seven official jinxes (Hatter, Magician, Poppy Grower,
Psychopath, Scarlet Woman, Vizier, Marionette) are implemented. With it the Carousel Script Collection's Whose Cult Is
It Anyway? and the World Championship's One Day More and Trained Killer have every character built (Witch Hunt still
needs a homebrew Witch).

139. **Never dealt.** With Lil' Monsta as the Demon in play no Demon is dealt: a Minion sits in the Demon's seat, so
     there is one Minion more than the table's ("[+1 Minion]"), and the Townsfolk and Outsiders are as the other Minions'
     setup modifiers make them (the Baron's +2 counts). The Demon is drawn as on any script; when the draw is Lil'
     Monsta, it is replaced by a Minion not dealt that has no setup modifier of its own and is not the Summoner (a
     reading: the Outsiders were drawn for the others); a draw that leaves none is drawn again. A deal naming Lil'
     Monsta is refused. With the Summoner dealt, its [No Demon] deal is the one in play, and Lil' Monsta is not.
140. **A token, not a character.** The babysitter keeps their Minion character, its ability and their alignment, and
     carries the token beside it (`Player.carries`): they are the Demon for every rule that asks (dying as it, the
     game's end, "the Demon" in other abilities), have its hooks (`Grimoire.abilities`), and the Spy's Grimoire shows
     it. Option: the babysitter's character becomes Lil' Monsta (simpler, but their own ability would be lost, which
     the text keeps).
141. **The Minions' choice.** Every night, the first included, each living Minion who knows they are one (not a
     Marionette, who believes they are good) names one of them, at Lil' Monsta's step in the night order; if they agree,
     that one babysits; if not, the Storyteller picks among those named (a judged call; the scripted style keeps the
     babysitter they had, when named, 60% of the time: POLICY `lilmonsta_keep_sitter`, default, for review). The dead
     don't wake. All of them learn who babysits; the babysitter is told they are the Demon.
142. **What evil learns.** At setup the Minions learn each other as usual, and that no player is the Demon yet; at the
     first-night step they learn the three bluffs (nobody else does). The rule sentence on the custom prompt says how
     Lil' Monsta works, since the team sizes it gives differ from the table's.
143. **Registration.** The babysitter registers as Lil' Monsta and as their own character (a Spy babysitter also as the
     Spy's good characters): information may show either. The Fortune Teller always sees a Demon there, and the Slayer's
     shot always kills them ("is the Demon"). Other abilities that ask whether a player registers as the Demon treat
     them as able to register either way, the Storyteller's call (option: always as the Demon, which the engine's
     registration sets cannot say together with "and as their Minion").
144. **"A player might die".** Each night but the first, at Lil' Monsta's step, the Storyteller's judged call: any
     living player but the babysitter (no starpass), or nobody; the scripted style kills 90% of nights (POLICY
     `lilmonsta_kill`, default, for review), a living good player. It is the Demon's kill (cause 'demon'): the Monk,
     Soldier and the other protections stop it, the Mayor may bounce it. A drunk or poisoned babysitter kills nobody
     (abnormal); one the Exorcist chose tonight does not act.
145. **Lil' Monsta dies with its babysitter.** However the babysitter dies (executed, shot, killed at night), Lil' Monsta
     is dead and good wins at the next check (unless the Scarlet Woman jinx, or another Demon is in play); the Minions
     do not choose again, through a Mastermind's extra day too. Another Minion's death changes nothing. Before the first
     choice no Demon is no win for good (`Grimoire.check_victory` asks the deal's character: nobody holds it).
146. **Becoming Lil' Monsta.** A player made Lil' Monsta (the Pit-Hag's choice, the Summoner's, the Engineer's, a tea
     party's: the Hatter jinx says "they also choose a Minion to become") becomes a Minion character of their choice too
     (one no living player has; the Storyteller's, if they give none) and babysits it; from the next night the Minions
     choose as usual. A good player made it stays good (as any Demon the Pit-Hag makes). If every Minion character is
     held by a living player they take one anyway, a second of it (U14 in docs/interaction-findings.md, for the owner).
147. **The token stays with its player** through any change until the Minions next choose, except a swap of
     characters and alignments (the Snake Charmer choosing the Demon): it goes with their Minion character to the player
     who took it with their alignment (a reading: the Snake Charmer takes the Demon).
148. **The jinxes.** Hatter: as 146. Magician: while a Magician is alive, the Storyteller chooses which Minion babysits
     (no Minion wakes to choose). Poppy Grower: while one is alive, the Minions wake one by one (from the babysitter
     they had, then in seat order), each asked whether to take the token, until one does; if none does, the
     Storyteller gives it. Psychopath: babysitting, they die when executed, with no roshambo. Vizier: babysitting, they
     die when executed (`Game.dooms`, the token's hook, before every protection). Scarlet Woman: if the babysitter dies
     with five or more players alive and a working Scarlet Woman lives, she babysits it for the rest of the game (the
     Minions no longer choose) and is told; she stays the Scarlet Woman. Marionette: a dealt Marionette waits as the
     good character they believe they are, and enters play beside the first babysitter on the first night (one of their
     good neighbours becomes it, as with the Summoner's jinx).
149. **Core changes**, each a no-op on every script without Lil' Monsta (the earlier fingerprints replay identically):
     `Player.carries` and `Player.is_demon` reading it; `Grimoire.abilities`, `registers_as`, `registers_demon_to_ft`,
     `demon_shown` and the Grimoire text for a carrier; `Character.setup_unheld` (its setup step runs with nobody holding
     it), `carried_registers_as`, `carried_registers_demon_to_ft` and `dooms` (`Game.dooms`, asked by
     `Game.prevent_death` and the Psychopath's roshambo); the Scarlet Woman leaves a carrier's death to the token; the
     Slayer's shot kills a carrier; the Clockmaker counts from the Demon to another player's Minion. The fuzzer reads
     the token too (its Clockmaker, Fortune Teller, Balloonist and Ravenkeeper oracles, the Vizier check).
150. **The synthetic script** (`clocktower/data/scripts/carousel-8.json`, "Carousel test 8"): Lil' Monsta and the Imp;
     the Poppy Grower, Magician, Fortune Teller, Slayer, Monk, Empath, Undertaker, Ravenkeeper, Investigator, Exorcist,
     Soldier, Snake Charmer and Chef; the Hatter, Drunk, Recluse and Saint; the Psychopath, Scarlet Woman, Vizier,
     Marionette, Poisoner and Spy. Every jinx of Lil' Monsta's is on it, and every size from 5 to 15 deals. Fingerprints:
     `tests/data/fingerprints-carousel-8.json`.

New weights: `lilmonsta_kill` 0.9, `lilmonsta_keep_sitter` 0.6 (added to POLICY by the section). The rules judge has
no heuristic for its calls (the scripted style decides).

### Atheist

Built (section "Atheist" of `carousel_extra.py`; tests `tests/test_carousel_atheist.py`; notes
`data/storyteller/extra-atheist.md`; script `carousel-9`). Its one official jinx is with Riot (Riot's subsection). With
it the Carousel Script Collection's Anonymous Dishonesty and The Midnight Oasis play end to end. The honest version of
its ability, a Storyteller free to break any rule, cannot be run by an engine; this is the closest reading it can run,
a bounded set of rule breaks (ruling 153), for the owner to widen or narrow.

151. **The deal.** The Atheist is a Townsfolk drawn as any other. When it is drawn, every Minion's and the Demon's seat
     goes to a Townsfolk not in play (an Outsider when none is left), and the Outsiders are the table's, as if no setup
     modifier were in play (none of the evil characters that would bring one is). A draw that leaves fewer than three
     good characters out of play for the bluffs, or a Drunk with no Townsfolk to believe in, is drawn again. A deal with
     the Atheist and an evil character is refused. A Drunk who believes they are the Atheist changes nothing: the evil
     team is real. An evil Townsfolk (the Bounty Hunter's) is a good character with an evil player: allowed.
152. **No Demon is no win.** With the Atheist in play the game goes on with no Demon, until the Storyteller is executed
     or two players remain; two remaining is evil's win ("good never executed the Storyteller"), though nobody is
     evil. This holds as the deal's rule (asked with nobody holding it), so an Atheist turned into another character at
     setup (an Alchemist-Baron's extra Outsiders) still has no Demon; the Atheist's setup step runs first of all.
153. **The rules the Storyteller breaks** (the bounded set): (a) before the first night it picks a fake evil team, a
     Demon of the script and the table's number of Minions among the players but the Atheist (a judged call; the
     scripted style draws them), written on the Grimoire for the Storyteller alone; (b) every piece of information may
     be anything (`Grimoire.unreliable` while `g.notes['Storyteller lies']`), and the scripted style gives what the
     fake Grimoire would show 90% of the time (POLICY `atheist_lie`, default, for review), else the truth; every
     player's false world is that one fake team (`Grimoire.decoy`), so the lies agree with each other; (c) each night
     but the first, a player may die as if a Demon killed: a judged call among the living players not safe from the
     Demon (the Monk's, the Soldier's), or nobody; the scripted style kills 85% of nights (POLICY `atheist_kill`,
     default, for review), outside the fake team. Nothing else is broken: abilities work, the fake team's members are
     good, and executing the fake Demon does nothing special. Options: more breaks (telling a player they are evil,
     faking a Demon's death and a win, nominations that fail), or fewer (truth only, so the Atheist shows at once).
154. **Nominating the Storyteller.** On any script with the Atheist (in play or not) anyone may nominate the
     Storyteller (`nominate: "Storyteller"`, in the schema and the nomination prompt's options; `Script.nominees`), once
     a day as any nominee. The nominator's abilities react as to any nomination (a cursed nominator dies; it is the
     Golem's one nomination, and nobody dies of it); no nominee's ability does, nobody defends, the comments and the vote
     run as for a player (clockwise from the nominator), and the Storyteller can be put on the block, tie or be
     replaced. Executed at the end of the day, the Storyteller ends the game: good wins if the Atheist is in play,
     alive or dead ("even if you are dead"), and evil wins if not (a reading of the How to Run; option: no effect when
     the Atheist is not in play). The custom prompt says so (`Character.rule_text`).
155. **Core changes**, each a no-op on every script without the Atheist: the Storyteller's lies in
     `Grimoire.unreliable` and `misinformed`; `Character.extra_nominees` and `nominee_executed`, `Script.nominees`, the
     schema's nominee list, and `Game.nominations` and `vote_order` for a nominee who is not a player; the Golem's
     nomination of a nominee who is not a player. The fuzzer does not check information given under the lies as a
     working ability's.
156. **The synthetic script** (`clocktower/data/scripts/carousel-9.json`, "Carousel test 9"): the Atheist with the
     Washerwoman, Investigator, Empath, Fortune Teller, Undertaker, Chef, Monk, Soldier, Slayer, Virgin, Mathematician
     and Ravenkeeper; the Drunk, Recluse, Saint and Butler; the Poisoner, Spy, Baron and Scarlet Woman; the Imp and Fang
     Gu. Every size from 5 to 15 deals (with and without the Atheist). Fingerprints:
     `tests/data/fingerprints-carousel-9.json`.

New weights: `atheist_lie` 0.9, `atheist_kill` 0.85 (added to POLICY by the section). The rules judge has no heuristic
for its calls.

### Wizard

Built (section "Wizard" of `carousel_extra.py`; tests `tests/test_carousel_wizard.py`; notes
`data/storyteller/extra-wizard.md`; script `carousel-10`). It has no official jinx. With it the Carousel Script
Collection's Irrational Behaviour and the World Championship's Off to see the Wizard play end to end.

157. **The wish list** (`carousel_extra.WISHES`, default, for review): eight wishes the engine can grant, each with the
     prices it may have (`PRICES`): a chosen living player dies tonight (price: the Wizard poisoned two days and nights,
     a good player learns the Wizard is a Minion, or the Wizard dies tonight); the Demon cannot die until the Wizard's
     next night (poisoned, exposed, or a good player learns the Demon is one of two players); a chosen living player
     turns evil and is told (the Wizard dies, the Demon poisoned tonight and tomorrow, or exposed); the Wizard learns a
     chosen player's character (the chosen player, or a good player, learns the Wizard is the Wizard; or exposed); the
     Wizard sees the Grimoire tonight (exposed, poisoned); a chosen living player is drunk for three days and nights
     (poisoned, exposed); a chosen dead evil player comes back to life (the Wizard dies, or the Demon pair); the Wizard
     learns the Demon's three bluffs (exposed, told). Left out: wishes the engine could not run (a new character, a
     changed rule, more votes), or that end the game at once. Options: a longer list; prices of the owner's choosing.
158. **Making the wish.** At the Wizard's step each night, the first included, a living Wizard who has not wished is
     shown the numbered list (`Request.menu`; random bots pick one now and then) and may wish (its number in `say`, and
     the player it names in `targets`) or wait. A wish in words is matched to the list by the Storyteller, a judged call
     whose only values are the list's wishes and "none" (the scripted style: the wish whose keywords the words hold
     most): a judge chooses, never invents. "None", or a wish without a fitting player, is no wish: the Wizard may wish
     another night. Once made, the wish is spent (per player), granted or not.
159. **Granted, its price and its clue.** Three judged calls, each among listed values only: whether it is granted (the
     scripted style 85%: POLICY `wizard_grant`), its price among that wish's or none ("might have a price": 80% a
     price, `wizard_price`), and its clue: announced (the town is told at dawn that a wish was granted), whispered (a
     good player of the Storyteller's choice learns the wish's words) or none ("might leave a clue": 70% one,
     `wizard_clue`). The Wizard is told whether it was granted and its price. A drunk or poisoned Wizard's wish is not
     granted (abnormal) and is spent. Everything is written on the Grimoire (the Spy sees it).
160. **Core changes**, each a no-op on every script without the Wizard: `Request.menu` and the random bots' pick from
     it (no draw without a menu, so other scripts' bots play as before).
161. **The synthetic script** (`clocktower/data/scripts/carousel-10.json`, "Carousel test 10"): the Washerwoman,
     Librarian, Investigator, Chef, Empath, Fortune Teller, Undertaker, Monk, Ravenkeeper, Virgin, Slayer, Soldier and
     Mayor; the Butler, Drunk, Recluse and Saint; the Wizard, Poisoner, Spy and Scarlet Woman; the Imp and No Dashii.
     Every size from 5 to 15 deals. Fingerprints: `tests/data/fingerprints-carousel-10.json`.

New weights: `wizard_grant` 0.85, `wizard_price` 0.8, `wizard_clue` 0.7 (added to POLICY by the section). The rules
judge has no heuristic for its calls.

### Legion

Built (section "Legion" of `carousel_extra.py`; tests `tests/test_carousel_legion.py`; notes
`data/storyteller/extra-legion.md`; script `carousel-11`). Its eight official jinxes (Engineer, Hatter, Minstrel,
Politician, Preacher, Summoner, Zealot, Magician) are implemented, among them the Engineer's that batch 4 left waiting.
With it the Carousel Script Collection's Devout Theists plays end to end.

162. **The deal.** When the Demon drawn is Legion, a bare majority of the players are Legion ("most players": n // 2 + 1,
     a reading; options: the almanac's table, or the Storyteller's choice), no Minion is dealt, and the rest are good,
     the table's Outsiders first (the Drunk only with a Townsfolk left to believe in). A deal with Legion and another evil
     character, or Legion short of a majority, is refused. Legion is one character several players have
     (`Character.duplicates`); good wins when every Legion is dead.
163. **What the Legion learn.** Each Legion learns the others and the bluffs (its own evil information:
     `Character.own_evil_info`, so the empty Minion list is not shown). The Legion do not wake to choose.
164. **"A player might die".** Each night but the first, at Legion's step, one judged call for all of them: any living
     player who is not Legion, or nobody; with only Legion left, one of them, so the game comes down to two. The scripted
     style kills 85% of nights (POLICY `legion_kill`, default, for review), a good player. It is the Demon's kill. With
     every living Legion drunk, poisoned or exorcised tonight, nobody dies.
165. **"Executions fail if only evil voted".** When a player is executed, the vote that put them there (today's last
     nomination of them) is read: at least one vote, every voter registering as evil to Legion (a Spy or Recluse is a
     judged call, POLICY `legion_registers_evil` 0.5), while a living Legion is sober: the execution fails, the player
     does not die (it is still the day's execution). An execution without a vote (madness, the Vizier's) is not "only
     evil voted".
166. **"You register as a Minion too".** To the Investigator (shown a Legion as a Minion of the script, true information;
     a reading): everywhere else Legion registers as Legion only, the Demon, so the Slayer, the Knight and the Fortune
     Teller see the Demon and nothing else. The engine's registration sets would make "a Demon and a Minion at once" read
     as "either", the Storyteller's call, which the text does not allow. Option: register as a Minion to every ability
     that asks about Minions.
167. **The jinxes.** Engineer: with Legion in play, the Engineer learns it at the start and has no ability (drunk for good,
     the engine's "no ability", as the Preacher's). Hatter: with Legion in play, no tea party (whoever has the Hatter's
     ability: the Hermit's too). Engineer, Hatter, Summoner, and any other way (the Pit-Hag's, a reading): when Legion is
     created, every evil player becomes Legion. Minstrel: a Legion executed sets off a working Minstrel (Legion registers
     as a Minion), but the Legion are not made drunk, and the Minstrel might learn they were Legion (judged, POLICY
     `legion_revealed` 0.5). Preacher: a Legion chosen keeps their ability (the Preacher acts only on Minion
     characters), and the Preacher might learn they are Legion (judged). Politician and Zealot: they might register as
     evil to Legion's vote check (judged). Magician: with a Magician in play, each Legion learns only which players are
     good, the Magician left out of that list (each Legion its own group, a reading), not the other Legion.
168. **Core changes**, each a no-op on every script without Legion: `Character.own_evil_info` (Game.setup) and
     `also_minion` (the Investigator's pair, `state.pair_choice`, and the fuzzer's Investigator oracle).
169. **The synthetic script** (`clocktower/data/scripts/carousel-11.json`, "Carousel test 11"): Legion and the Imp; the
     Engineer, Minstrel, Preacher, Magician, Fortune Teller, Empath, Investigator, Slayer, Monk, Chef, Undertaker,
     Soldier and Virgin; the Hatter, Politician, Zealot and Drunk; the Summoner, Poisoner, Spy and Scarlet Woman. Every
     jinx of Legion's is on it, and every size from 5 to 15 deals. Fingerprints: `tests/data/fingerprints-carousel-11.json`.
     About a quarter of its random-bot games reach the tenth day unfinished (random good votes rarely carry an
     execution past Legion's rule).

New weights: `legion_kill` 0.85, `legion_registers_evil` 0.5, `legion_revealed` 0.5 (added to POLICY by the section).
The rules judge has no heuristic for its calls.

### Riot

Built (section "Riot" of `carousel_extra.py`; tests `tests/test_carousel_riot.py`; notes `data/storyteller/extra-riot.md`;
script `carousel-12`). Its twelve official jinxes are implemented: eleven with built characters, and the Atheist's,
declared only while the Atheist is built (so either can be switched off or deleted). With it the Carousel Script Collection's Quick
Maths plays end to end. The text built is the official data's ("On day 3, Minions become Riot & nominees die but
nominate an alive player immediately. This must happen."); its jinxes speak of a nightly choice it does not have, read
below.

170. **Before day 3.** Riot is dealt as any Demon, with its Minions, and kills nobody at night. Days 1 and 2 play as
     usual; executing Riot then is good's win.
171. **"Minions become Riot".** At Riot's step on the third night (its reminder: "If it is night 3, you may wake the
     Minions"), every living Minion becomes Riot and is told; the dead stay as they are. Several players are then Riot
     (`Character.duplicates`), all Demons: good wins when every Riot is dead.
172. **The riot.** Day 3's nominations are Riot's (`Character.runs_nominations`, a core hook nothing else sets): announced
     when they open; anyone who may nominate may start it; if nobody does, "this must happen": the first living Riot
     must. Each nominee is executed at once, without a vote (an execution in every way: the Saint, the Tea Lady, the
     Fool, the Pacifist, the Mastermind apply), then must nominate an alive player not nominated today; a nominee who
     names nobody legal has it named by the Storyteller (a judged call; "must"). The nominator's abilities react to
     each nomination as usual (the Witch's curse). It ends when the game does, or when the nominee has nobody to name
     (or may not nominate again: a Golem who has), and then the day goes on. Later days are as usual. Option: the newer
     text's "After day 3, evil wins".
173. **The jinxes.** Exorcist, Innkeeper, Monk, Soldier: if a Riot nominates, and so executes, the player a working one
     chose last night (the Soldier: a working Soldier), good wins at once. Grandmother: with a living Riot, the
     Grandchild dying by execution is evil's win. King: with Riot in play and a player dead, a King whose own rule did
     not tell them tonight learns an alive character at Riot's step (after the King's). Mayor: before each riot
     nomination a living, working Mayor is asked whether to stop the riot: yes ends the game, good's win with one Riot
     alive, else evil's. Atheist (while built): the Storyteller may be nominated in the riot; players vote as usual,
     and the Storyteller on the block is executed (the Atheist's rule, ruling 154); if not, the nominator nominates
     again. Banshee, Farmer, Ravenkeeper, Sage: with any of them on the script, each night but the first the first
     living Riot chooses an alive player it has not chosen before; a good, working one of these characters uses their
     ability without dying (the Farmer makes a good player a Farmer; the Ravenkeeper chooses a player and learns their
     character; the Sage learns Riot is one of two players), and a chosen Banshee dies as the Demon's kill (and so
     gains its ability). Others chosen: nothing.
174. **Core changes**, each a no-op on every script without Riot: `Character.runs_nominations` and `run_nominations`
     (`Game.nominations` asks the script's characters first); the fuzzer's Sage oracle reads a Sage told by a choice
     rather than a death.
175. **The synthetic script** (`clocktower/data/scripts/carousel-12.json`, "Carousel test 12"): Riot, the only Demon;
     the Banshee, Exorcist, Farmer, Grandmother, Innkeeper, King, Mayor, Monk, Ravenkeeper, Sage, Soldier, Fortune
     Teller and Empath; the Drunk, Recluse, Saint and Butler; the Poisoner, Spy, Scarlet Woman and Baron. Every jinx of
     Riot's with a character built before batch 6 is on it (not the Atheist's: never two batch 6 characters on one
     script), and every size from 5 to 15 deals. Fingerprints: `tests/data/fingerprints-carousel-12.json`. Every game
     ends by day 3.

No new weights. The rules judge has no heuristic for its calls.

## The refactor: ability instances and one change path

Readings the refactor of docs/state-machines.md ("Refactor results") had to take where the audit's fix needed one. Each
plays only on custom scripts (Trouble Brewing, BMR and S&V replay identically). Questions the audit left open (U1, U13,
G2, and whether a swap carries a Demon's own bookkeeping) are not decided here: the engine keeps what it did.

176. **A seeming death is the Zombuul's** (the audit's G11, fuzz finding S3). **Pending owner confirmation**: a new
     choice the refactor made, which flips outcomes (a seeming-dead Zombuul changed is dead, where before it lived on);
     the engine keeps it, since it is what fixes S3, until the owner rules (docs/review/everything-open-voice.md, Part
     B, group 7). A player who registers as dead through the
     Zombuul's first death and then stops being the Zombuul (the Pit-Hag's change, the Barber's swap, a tea party) is
     dead, as the town already believes: the ability that kept them alive is gone. Their last death in the Grimoire is
     no longer a seeming one; nothing is announced (the death was). Made a Demon this way, they are a dead Demon (good
     wins unless another Demon lives). A Zombuul swapped by the Barber gives the new Zombuul a first death of its own
     (the Barber's fresh ability, as before). Option: they live, and the town is told they are alive.
177. **A gained ability is an instance of its own.** An ability gained again later (the Cannibal's next meal of the same
     character, the Hermit's Outsiders anew) starts fresh, as a character taken anew does (the Barber's almanac); one
     still held carries on. A revived player's own ability is the same instance, fresh again; what they gained is kept
     as it was (the engine's reading before, unchanged: G2 stays the owner's).
178. **The Marionette's belief.** A player made the Marionette believes they are still what they were, so what they had
     used as it stays used for that belief (they are not woken to use a spent once-per-game ability again, which would
     tell them they changed), and what it recorded for its holder stays theirs (ruling 179's records: a Balloonist made
     the Marionette is still told "a different type than last night's").
179. **Records of one holder end with their instance.** The Golem's nomination, the Banshee's powers, the Fearmonger's
     chosen player, the Lleech's host and lost ability, the Alchemist's Minion, the Balloonist's type shown last night,
     the Acrobat's choice tonight, the Xaan's night X and the Wraith's open eyes belong to the holder's instance
     (`Character.instance_notes`), and the Mathematician/Drunk jinx's marks (a Drunk Slayer's first shot, a Drunk
     Virgin's first nomination) to the believed instance's own record: a player who becomes the character again starts
     fresh, and nobody reads a former holder's (the Vizier/Fearmonger jinx read the old Fearmonger's choice). The Evil
     Twin's twin and the Xaan's X are set again by `becomes`, so need no such end. The Damsel's guesses stay by player
     ("each Minion gets 1 guess": the player, not their character; a reading kept as it was).
