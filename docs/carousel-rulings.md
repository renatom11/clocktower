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
    `summoner_st_honours`), else a good player and any Demon. Pukka: on the second night the Summoner may summon a
    Pukka (only a Pukka; naming no one, or another Demon, waits for the third night). Zombuul: a dead player summoned
    into the Zombuul is alive, registering as dead, with its first death spent. Pit-Hag and Hatter: a summon that
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
    Philosopher's, without making anyone drunk), and a "you start knowing" ability acts at once. Options: judge only
    the days before the death; let a dead Pixie gain. Why: "if you were mad" reads as the whole game.
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
    the ability (dead, the poison ends; drunk, it is not made). Then a living good player (by alignment; usually a
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
    always includes the truth. Noticed, not changed: a Poisoner made drunk by another ability (the Courtier, the
    Innkeeper, the Puzzlemaster) still poisons; fixing that would change carousel-1's fingerprints, so it is left for
    the owner.
64. **The third synthetic script** (`clocktower/data/scripts/carousel-3.json`, "Carousel test 3"): the fifteen, with
    the Magician, Monk, Soldier, Mayor, Sage, Ravenkeeper, Exorcist, Innkeeper, Juggler, Mathematician, Banshee and
    Grandmother; the Butler, Damsel, Hatter and Plague Doctor; the Spy, Summoner, Cerenovus, Pit-Hag, Baron and
    Godfather; the Kazali, the Leviathan and the Imp. All thirty-three batch 2 jinxes are on it (forty jinxes in
    all), and every size from 5 to 15 deals. Its replay fingerprints are
    `tests/data/fingerprints-carousel-3.json`.

New weights: `priestess_info_weight` 3, `balloonist_outsider` 0.5, `cannibal_lie_claim` 0.8, `puzzle_townsfolk`
0.8, `marionette_townsfolk` 0.8, `kazali_outsiders_same` 0.6. The rules judge has no heuristic of its own for the new
calls (the scripted style decides).
