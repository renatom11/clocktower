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
