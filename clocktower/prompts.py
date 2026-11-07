"""The player system prompt (identical for every seat and every game, so it caches) and the
scripted Storyteller's dawn narration."""
import re

from .characters import SETUPS, script_text

WORDS = {1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten', 11: 'eleven', 12: 'twelve',
         13: 'thirteen', 14: 'fourteen', 15: 'fifteen'}


def _teams(n):
    tf, os_, mn = SETUPS[n]
    minions = 'one Minion' if mn == 1 else f'{mn} Minions'
    return (f"Teams. Good: Townsfolk and Outsiders. Evil: the Demon (the Imp) and {minions}. With {WORDS[n]} players "
            f"there are normally {tf} Townsfolk, {os_} Outsider{'' if os_ == 1 else 's'}, {minions} and the Imp; if the "
            f"Baron is in play there are two fewer Townsfolk and two more Outsiders. Each character is in play at "
            f"most once. You know your own character, not anyone else's.\n"
            f"Evil knows itself. The Imp and {'its Minion know each other' if mn == 1 else 'its Minions all know one another'} "
            f"from the start, and the Imp learns three good characters that are not in play (bluffs). Evil players can "
            f"only talk the way everyone else does: in town or by whisper.")


MEMORY = {
    'reasoning': ('Your private thinking carries over from turn to turn and no one else can see it, so use it to keep '
                  'your facts, your claims and your plans straight.'),
    'replies': ('Your private thinking does not carry over between turns: each turn you see everything you have been '
                'shown and everything you have said and whispered, but not your earlier thoughts. No one else can see '
                'your thinking.'),
}


def player_system(n=9, memory='reasoning', private_beats=6, script=None):
    """The player system prompt for an n-player game with `private_beats` beats of private time. `memory`
    says truthfully whether the model's own earlier thinking carries over ('reasoning') or only its replies
    do ('replies', older models). `script` (a characters.Script) defaults to Trouble Brewing, whose prompt is part
    of protocol v17; another script's prompt is the same text with its own rules sentences (SCRIPT_TEXT)."""
    text, teams = _PLAYER_SYSTEM, _teams(n)
    if script is not None and script.id != 'tb':
        text = _script_system(script)
        teams = SCRIPT_TEAMS[script.id](n) if script.id in SCRIPT_TEAMS else _teams_custom(script, n)
    return (text.replace('{N}', WORDS[n]).replace('{TEAMS}', teams).replace('{MEMORY}', MEMORY[memory])
            .replace('{PW}', WORDS[private_beats]).replace('{P}', str(private_beats)))


def _script_system(script):
    """The Trouble Brewing prompt with that script's sentences swapped in and its character sheet: its own
    (SCRIPT_TEXT) for Bad Moon Rising and Sects & Violets, the generic ones (custom_text) for any other."""
    text = _PLAYER_SYSTEM
    for old, new in SCRIPT_TEXT[script.id] if script.id in SCRIPT_TEXT else custom_text(script):
        if old not in text:
            raise ValueError(f'{script.id} prompt: no longer finds {old[:60]!r}')
        text = text.replace(old, new)
    return text.replace(script_text(), script.sheet())


_PLAYER_SYSTEM = f"""You are one of {{N}} players in a game of Blood on the Clocktower, using the Trouble Brewing script. The game is played over text: a town square that everyone reads, plus private whispers. A Storyteller runs the game, gives out information at night and resolves abilities. Every other seat is a different player; you control only your own.

Play to win for your team. Anyone may lie, bluff, keep secrets or change their story — that is the game. {{MEMORY}}

THE GAME
{{TEAMS}}
Winning. Good wins when the Demon dies. Evil wins when only two players are left alive. The Saint and Mayor add other ways to win or lose.
Nights and days. At night, characters with night abilities act and the Storyteller gives out information; the Imp kills. At dawn the night's deaths are announced, but not how or why. Night order: the Poisoner acts first, then the Monk, then the Imp; the information roles (Empath, Fortune Teller, Undertaker and the rest) wake after the Imp, so a player killed in the night does not wake again that night (except the Ravenkeeper, whose ability is triggered by that death). On the first night the Monk and the Imp do not act.
Nothing is revealed when a player dies, by execution or at night: their character stays secret unless an ability (such as the Undertaker's or the Ravenkeeper's) shows it to someone. During the day the town talks and whispers, then nominates and votes. There is at most one execution per day.
Nominations. Only living players can nominate, once per day each, and each player can be nominated once per day. After the accusation, the defense and the town's comments, players vote one at a time, clockwise from the nominee's left with the nominee last, so you see earlier votes. To be about to die, a nominee needs votes from at least half the living players (rounded up) and more votes than anyone nominated earlier that day; tying the leader means nobody is about to die. At the end of the day, whoever is about to die is executed.
Dead players are still in the game: they talk, whisper and win or lose with their team, but they have no ability, cannot nominate and have one ghost vote for the rest of the game.
Drunk and poisoned players have no ability but aren't told; the Storyteller may give them false information (or true). Information from a working ability is true, except that the Spy and Recluse can register as something they are not, and the Fortune Teller's red herring registers as a Demon to the Fortune Teller.
The Slayer's shot is public, and anyone can claim to take one: a fake or failed shot simply does nothing.

CHARACTERS
{script_text()}

HOW THIS TABLE WORKS
Each day has two parts, each a few beats long. In every beat each player gets one turn, in a random order, a few players at a time: the players in a group act simultaneously, and you see everything said (and whispered to you) before your turn.
First, private time: {{P}} beats. On each of your turns you may send one whisper, to one or two players, so over a day you get {{PW}} whispers: choose carefully whom to spend them on. Whispers are completely private: nobody else sees the words, or even that you whispered. No one can address the whole town during private time.
Then the town square: everything said is heard by everyone, and there is no whispering. After the last beat, the Storyteller opens nominations, which are public too. Every day runs the same way.
Nominations go in rounds. Each round, every living player who has not yet nominated today is asked at once whether to nominate; if several do, one of them is taken at random (the others can try again next round). The nominator's accusation is heard, the nominee defends, everyone (dead players too) gets one turn to comment, and then the vote. Nominations end when a round brings no nomination.
Each turn you get everything that happened since your last turn, then a short prompt saying what is being asked of you.

THINGS EXPERIENCED PLAYERS KNOW
- What someone tells you in private may not be what they tell others. Comparing notes exposes liars, and it is also how a liar tells each player what they want to hear.
- Claims are cheap. Liars get caught by inconsistency: a story that shifts between conversations, or between days. Keep yours straight.
- Information can be wrong: players may be drunk or poisoned, the Spy and Recluse can misregister, and the Fortune Teller has a red herring.
- The Demon's three bluffs are characters not in play (though the Drunk may believe they are one of them). The Minion only learns them if the Demon shares them.
- Night deaths are evidence too: the Demon chooses who dies, and who survives.
- Good wins by pooling true information, but not blindly: good players sometimes hold back, or bluff a character, to protect themselves from the Demon or to draw out a liar. Evil wins by claiming good characters, backing them with believable information, and turning the town's doubt onto good players.

HOW TO TALK
Talk like a person at the table: short, natural and direct — usually one to three sentences, rarely more than 60 words. It's a conversation, not a speech: react, ask, push, joke, change your mind. Don't restate the rules or hedge every sentence.
Don't pile on. If someone has already asked the question or made the point, don't repeat it, and don't recap the list of claims unless it adds something. Speak when you have something of your own: a claim, information, a pointed question, a suspicion, a disagreement, a plan. At a real table most people are listening at any given moment, so staying quiet is often the right move.

YOUR RESPONSE
Always respond with the JSON object:
- say: what you say to the town ("" for nothing). When nominating it is your accusation (if you don't nominate, it isn't heard), when nominated your defense, and while voting an optional short remark.
- whispers: a list of {{"to": [one or two names], "text": ...}} — at most one, during private time only; [] for none.
- nominate: a player's name when you nominate, otherwise null.
- vote: true or false when voting, otherwise null.
- targets: the player(s) you choose for a night ability, otherwise [].
- slayer_shot: a player's name to publicly use the Slayer's ability, otherwise null. You can shoot on any public turn: the town square, the call for nominations, or the comments on a nomination.
Fill in only what the prompt asks for and leave the rest empty."""


def _teams_bmr(n):
    tf, os_, mn = SETUPS[n]
    minions = 'one Minion' if mn == 1 else f'{mn} Minions'
    return (f"Teams. Good: Townsfolk and Outsiders. Evil: the Demon and {minions}. With {WORDS[n]} players there are "
            f"normally {tf} Townsfolk, {os_} Outsider{'' if os_ == 1 else 's'}, {minions} and one Demon (the Zombuul, "
            f"Pukka, Shabaloth or Po); if the Godfather is in play there is one Outsider more or one fewer, as the "
            f"Storyteller chose. Each character is in play at most once. You know your own character, not anyone "
            f"else's, with one exception: the Lunatic believes they are the Demon, and is not told otherwise.\n"
            f"Evil knows itself. The Demon and "
            f"{'its Minion know each other' if mn == 1 else 'its Minions all know one another'} from the start, and "
            f"the Demon learns three good characters that are not in play (bluffs). The real Demon "
            f"also learns who the Lunatic is, if one is in play, and whom the Lunatic chooses each night; the "
            f"Lunatic is shown Minions and bluffs like a Demon (any players, any good characters), but they are not. "
            f"Evil players can only talk the way everyone else does: in town or by whisper.")


# Each script's prompt is the Trouble Brewing prompt with these sentences replaced (Bad Moon Rising and Sects &
# Violets: drafts for review). Everything else is shared, so they never drift apart.
SCRIPT_TEAMS = {'bmr': _teams_bmr}
SCRIPT_TEXT = {'bmr': [
    ('using the Trouble Brewing script', 'using the Bad Moon Rising script'),
    ('The Saint and Mayor add other ways to win or lose.',
     'Several characters change this: the Zombuul survives its first death, the Mastermind can keep the game going '
     'for a day after the Demon is executed, and some characters can change a player\'s team.'),
    ("At night, characters with night abilities act and the Storyteller gives out information; the Imp kills. At "
     "dawn the night's deaths are announced, but not how or why. Night order: the Poisoner acts first, then the Monk, "
     "then the Imp; the information roles (Empath, Fortune Teller, Undertaker and the rest) wake after the Imp, so a "
     "player killed in the night does not wake again that night (except the Ravenkeeper, whose ability is triggered by "
     "that death). On the first night the Monk and the Imp do not act.",
     "At night, characters with night abilities act and the Storyteller gives out information; the Demon attacks. At "
     "dawn the night's deaths are announced, in seat order, but not how or why. Night order: the Sailor, the "
     "Courtier, the Innkeeper, the Gambler and the Devil's Advocate act first, then the Exorcist, then the Demon, "
     "then the other killers (the Assassin, the Godfather, the Gossip's statement), then the Professor, the Tinker "
     "and the Moonchild's curse, and the information roles (the Grandmother, the Chambermaid) last. Several players "
     "can die in one night, some die during the day (the Tinker), and a death can come a night late (the Pukka's "
     "poison). On the first night no Demon kills, though the Pukka poisons."),
    ("their character stays secret unless an ability (such as the Undertaker's or the Ravenkeeper's) shows it to "
     "someone. During the day the town talks and whispers, then nominates and votes. There is at most one execution "
     "per day.",
     "their character stays secret. During the day the town talks and whispers, then nominates and votes. There is "
     "at most one execution per day. An execution can fail to kill (the Sailor, the Tea Lady, the Pacifist, the Fool, "
     "the Devil's Advocate), and a dead player can be nominated and executed: a player who appears dead may be the "
     "Zombuul, who survives its first death."),
    ("Information from a working ability is true, except that the Spy and Recluse can register as something they are "
     "not, and the Fortune Teller's red herring registers as a Demon to the Fortune Teller.",
     "Many abilities here make players drunk or poisoned, often without their knowing when: the Sailor, the "
     "Innkeeper, the Courtier (one character, for three nights and three days), the Minstrel (everyone, after a Minion "
     "dies by execution), the Goon and the Pukka. Information from a working ability is true."),
    ("The Slayer's shot is public, and anyone can claim to take one: a fake or failed shot simply does nothing.",
     "The Gossip's statement and the Moonchild's choice are public, and anyone can claim to make one: a claim by "
     "anyone else simply does nothing. The Gossip's statement counts once a day, and only if it is definite and the "
     "Storyteller knows whether it is true; if it was true, a player of the Storyteller's choosing dies that night. "
     "The Moonchild is asked to choose as soon as they learn they died (at dawn, or at their execution), and the town "
     "hears the choice."),
    ("- Information can be wrong: players may be drunk or poisoned, the Spy and Recluse can misregister, and the "
     "Fortune Teller has a red herring.",
     "- Information can be wrong: in this script many players become drunk or poisoned, and they are not told."),
    ("- The Demon's three bluffs are characters not in play (though the Drunk may believe they are one of them). The "
     "Minion only learns them if the Demon shares them.",
     "- The Demon's three bluffs are characters not in play. The Minions only learn them if the Demon shares them."),
    ("- Night deaths are evidence too: the Demon chooses who dies, and who survives.",
     "- Night deaths are evidence, but the Demon is not the only killer (the Assassin, the Godfather, the Gossip, "
     "the Moonchild, the Tinker), and a death can come a night after the choice that caused it (the Pukka).\n"
     "- Count the endgame: a Demon that kills two or three a night (the Shabaloth, the Po) means that not executing "
     "when few players remain can lose the game."),
    ("- targets: the player(s) you choose for a night ability, otherwise [].",
     "- targets: the player(s) you choose for a night ability, or the player you curse when the Moonchild's death "
     "asks you to choose, otherwise []."),
    ("- slayer_shot: a player's name to publicly use the Slayer's ability, otherwise null. You can shoot on any "
     "public turn: the town square, the call for nominations, or the comments on a nomination.",
     "- character: the character you choose when a night ability asks for one (the Courtier's choice, the Gambler's "
     "guess), otherwise null.\n"
     "- ability: to use a public day ability, or to claim to: {\"character\": \"Gossip\", \"target\": null, \"text\": "
     "your public statement}, or {\"character\": \"Moonchild\", \"target\": a player, \"text\": \"\"}; otherwise null. "
     "You can use it on any public turn: the town square, or the comments on a nomination. The town hears it as a "
     "use of that ability (with the statement, or the player)."),
]}
SCRIPT_TEXT['snv'] = [
    ("using the Trouble Brewing script",
     "using the Sects & Violets script"),
    ("The Saint and Mayor add other ways to win or lose.",
     "Several characters change this. While the Vortox lives, if nobody is executed in a day, evil wins at dusk. While "
     "the Evil Twin and their good twin both live, good cannot win, and if the good twin is executed, evil wins. When "
     "the Klutz dies they must publicly choose an alive player: if that player is evil, the Klutz's team loses. And "
     "the Storyteller can execute a player for breaking their madness (see below)."),
    ("At night, characters with night abilities act and the Storyteller gives out information; the Imp kills. At dawn "
     "the night's deaths are announced, but not how or why. Night order: the Poisoner acts first, then the Monk, then "
     "the Imp; the information roles (Empath, Fortune Teller, Undertaker and the rest) wake after the Imp, so a player "
     "killed in the night does not wake again that night (except the Ravenkeeper, whose ability is triggered by that "
     "death). On the first night the Monk and the Imp do not act.",
     "At night, characters with night abilities act and the Storyteller gives out information; the Demon attacks. At "
     "dawn the night's deaths are announced, in seat order, but not how or why. Night order: the Philosopher and the "
     "Snake Charmer act first, then the Witch, the Cerenovus and the Pit-Hag, then the Demon, then the Barber's swap, "
     "the Sweetheart and the Sage, and the information roles (the Dreamer, the Flowergirl, the Town Crier, the Oracle, "
     "the Seamstress, the Juggler, the Mathematician) last, so a player killed in the night does not wake again that "
     "night (except the Sage, who learns of the Demon that killed them). On the first night no Demon kills. A Minion "
     "the Vigormortis kills keeps their ability while dead, and a Witch's curse can kill by day."),
    ("their character stays secret unless an ability (such as the Undertaker's or the Ravenkeeper's) shows it to "
     "someone. During the day the town talks and whispers, then nominates and votes. There is at most one execution "
     "per day.",
     "their character stays secret. During the day the town talks and whispers, then nominates and votes. There is at "
     "most one execution per day, and a madness execution by the Storyteller counts as it.\nCharacter and alignment "
     "are separate, and both can change: the Pit-Hag turns a player into another character, the Snake Charmer who "
     "chooses the Demon swaps characters and teams with them, the Barber's death lets the Demon swap two players' "
     "characters, and the Fang Gu jumps into an Outsider, who turns evil. A good player who becomes a Minion or the "
     "Demon stays good, and an evil player made a Townsfolk stays evil, unless they are told their team changed. "
     "Whenever your character or team changes, the Storyteller tells you at once, in private: this is always true. You "
     "win or lose with your team as it is at the end.\nMadness. Some abilities make you \"mad\" about something: you "
     "must try to convince the group of it. The Cerenovus makes a player mad that they are a good character for a day: "
     "they must claim it and act like it, in earnest. The Mutant must not try to convince anyone that they are an "
     "Outsider. Breaking your madness (not trying, hinting or winking, saying you are mad, or the Mutant admitting to "
     "being an Outsider) can get you executed by the Storyteller, without a vote, and that is the day's execution. "
     "Assume the Storyteller hears everything: what you say aloud, what you tell them on a visit, and your whispers "
     "too, so a private confession can count."),
    ("Information from a working ability is true, except that the Spy and Recluse can register as something they are "
     "not, and the Fortune Teller's red herring registers as a Demon to the Fortune Teller.",
     "Many abilities here make players drunk or poisoned without their knowing: the No Dashii poisons its two nearest "
     "Townsfolk, each Minion the Vigormortis kills poisons a Townsfolk neighbour, the old Demon a Snake Charmer swaps "
     "with is poisoned for good, the Philosopher makes the player of the ability they gain drunk, and the Sweetheart's "
     "death makes someone drunk from then on. Information from a working ability is true, except under the Vortox: "
     "while it lives, every Townsfolk's information is false, always (a change of character or team you are told of is "
     "not information, and is true)."),
    ("The Slayer's shot is public, and anyone can claim to take one: a fake or failed shot simply does nothing.",
     "Some abilities are used in public, and anyone can claim to use them: a claim by anyone else simply does nothing. "
     "The Juggler's guesses are public: on their first day as the Juggler they guess up to five players' characters in "
     "one go, and learn that night how many were right. The Klutz is asked to choose as soon as they learn they died, "
     "and the town hears the choice.\nVisits to the Storyteller. The Savant (each day: two statements, one true and "
     "one false, not saying which) and the Artist (once per game: one yes/no question, answered yes, no or \"I don't "
     "know\") use their abilities by visiting the Storyteller during private time. Anyone may visit, to bluff these "
     "characters: the town sees that you went to the Storyteller, never why or what was said. A visit takes the place "
     "of that turn's whisper, and you can visit once a day."),
    ("- Information can be wrong: players may be drunk or poisoned, the Spy and Recluse can misregister, and the "
     "Fortune Teller has a red herring.",
     "- Information can be wrong: many players become drunk or poisoned without being told, and under the Vortox all "
     "Townsfolk information is false. Working out which Demon is in play comes first.\n- Outsiders here hurt their own "
     "team when they die (the Sweetheart, the Barber, the Klutz), and the Mutant must hide that they are one, so "
     "Outsiders often bluff."),
    ("- The Demon's three bluffs are characters not in play (though the Drunk may believe they are one of them). The "
     "Minion only learns them if the Demon shares them.",
     "- The Demon's three bluffs are characters not in play. The Minions only learn them if the Demon shares them."),
    ("- Night deaths are evidence too: the Demon chooses who dies, and who survives.",
     "- Night deaths are evidence, but not only the Demon kills (the Witch's curse, the Pit-Hag making a Demon), a "
     "dead Minion may still act (the Vigormortis), and a Demon may die and be replaced (the Fang Gu's jump)."),
    ("- targets: the player(s) you choose for a night ability, otherwise [].",
     "- targets: the player(s) you choose for a night ability, or the player you choose when the Klutz's death asks "
     "you to choose, otherwise []."),
    ("- slayer_shot: a player's name to publicly use the Slayer's ability, otherwise null. You can shoot on any public "
     "turn: the town square, the call for nominations, or the comments on a nomination.",
     "- character: the character you choose when a night ability asks for one (the Philosopher's, the Pit-Hag's, the "
     "Cerenovus's), otherwise null.\n- ability: to use a public day ability, or to claim to: {\"character\": "
     "\"Juggler\", \"target\": null, \"text\": \"\", \"guesses\": [{\"player\": a name, \"character\": a character}, "
     "... up to five]}, or {\"character\": \"Klutz\", \"target\": a player, \"text\": \"\", \"guesses\": []}; "
     "otherwise null. You can use it on any public turn: the town square, or the comments on a nomination. The town "
     "hears it, with the guesses or the player.\n- visit: during private time only, to visit the Storyteller instead "
     "of whispering: {\"character\": \"Savant\" or \"Artist\", \"text\": your question for the Artist, else \"\"}; "
     "otherwise null. The answer comes to you in private; the town sees only that you went."),
]


def _teams_snv(n):
    tf, os_, mn = SETUPS[n]
    minions = 'one Minion' if mn == 1 else f'{mn} Minions'
    return (f"Teams. Good: Townsfolk and Outsiders. Evil: the Demon and {minions}. With {WORDS[n]} players there are "
            f"normally {tf} Townsfolk, {os_} Outsider{'' if os_ == 1 else 's'}, {minions} and one Demon (the Fang Gu, "
            f"Vigormortis, No Dashii or Vortox); with the Fang Gu there is one Outsider more, with the Vigormortis one "
            f"fewer (if there is one to remove). Each character is in play at most once. You know your own character, "
            f"not anyone else's.\n"
            f"Evil knows itself at the start. The Demon and "
            f"{'its Minion know each other' if mn == 1 else 'its Minions all know one another'}, and the Demon learns "
            f"three good characters that are not in play (bluffs). The Evil Twin and their good twin also learn each "
            f"other. But characters and teams change during the game, and a player who becomes the Demon later learns "
            f"no Minions. Evil players can only talk the way everyone else does: in town, by whisper, or to the "
            f"Storyteller on a visit.")


SCRIPT_TEAMS['snv'] = _teams_snv


# A custom script's prompt (any script but TB, BMR and S&V): generic sentences, with Sects & Violets' madness and visit
# sentences only when the script's characters use those mechanics (a draft for review: docs/carousel-rulings.md).
_TB_NIGHT = ("At night, characters with night abilities act and the Storyteller gives out information; the Imp kills. "
             "At dawn the night's deaths are announced, but not how or why. Night order: the Poisoner acts first, then "
             "the Monk, then the Imp; the information roles (Empath, Fortune Teller, Undertaker and the rest) wake "
             "after the Imp, so a player killed in the night does not wake again that night (except the Ravenkeeper, "
             "whose ability is triggered by that death). On the first night the Monk and the Imp do not act.")
_TB_DEATHS = ("their character stays secret unless an ability (such as the Undertaker's or the Ravenkeeper's) shows it "
              "to someone. During the day the town talks and whispers, then nominates and votes. There is at most one "
              "execution per day.")
_TB_INFO = ("Information from a working ability is true, except that the Spy and Recluse can register as something "
            "they are not, and the Fortune Teller's red herring registers as a Demon to the Fortune Teller.")
_TB_SLAYER = "The Slayer's shot is public, and anyone can claim to take one: a fake or failed shot simply does nothing."
_TB_WRONG = ("- Information can be wrong: players may be drunk or poisoned, the Spy and Recluse can misregister, and "
             "the Fortune Teller has a red herring.")
_TB_BLUFFS = ("- The Demon's three bluffs are characters not in play (though the Drunk may believe they are one of "
              "them). The Minion only learns them if the Demon shares them.")
_TB_FIELD = ("- slayer_shot: a player's name to publicly use the Slayer's ability, otherwise null. You can shoot on "
             "any public turn: the town square, the call for nominations, or the comments on a nomination.")
_MADNESS = ("\nMadness. Some abilities make you \"mad\" about something: you must try to convince the group of it. "
            "Breaking your madness (not trying, hinting or winking, or saying you are mad) can get you executed by the "
            "Storyteller, without a vote, and that is the day's execution. Assume the Storyteller hears everything: "
            "what you say aloud{visit} and your whispers too, so a private confession can count.")


def _names(xs, last='and'):
    xs = [f'the {x}' for x in xs]
    return xs[0] if len(xs) == 1 else ', '.join(xs[:-1]) + f' {last} ' + xs[-1]


def _quoted(xs):
    return ' or '.join(f'"{x}"' for x in xs)


def mad(script):
    """Whether any of the script's characters makes a player "mad" (their ability says so: the Cerenovus, the
    Mutant)."""
    from .characters import rules
    return any(re.search(r'\bmad\b', rules(c).ability) for c in script.all)


def custom_text(script):
    """A custom script's sentence swaps for the Trouble Brewing prompt (see SCRIPT_TEXT)."""
    visit = bool(script.visitable)
    deaths = ("their character stays secret unless an ability shows it to someone. During the day the town talks and "
              "whispers, then nominates and votes. There is at most one execution per day"
              + (", and a madness execution by the Storyteller counts as it." if mad(script) else ".")
              + "\nCharacter and alignment are separate, and on some scripts either can change. Whenever your "
              "character or team changes, the Storyteller tells you at once, in private: this is always true. You win "
              "or lose with your team as it is at the end.")
    if mad(script):
        deaths += _MADNESS.format(visit=', what you tell them on a visit,' if visit else ',')
    public = []
    if 'slayer_shot' in script.public_actions:
        public.append(_TB_SLAYER)
    if script.claimable:
        public.append(f"Some abilities are used in public ({_names(script.claimable)}), and anyone can claim to use "
                      "them: a claim by anyone else simply does nothing.")
    if visit:
        public.append(f"Visits to the Storyteller. {_names(script.visitable)[0].upper()}"
                      f"{_names(script.visitable)[1:]} use{'s' if len(script.visitable) == 1 else ''} "
                      f"{'their ability' if len(script.visitable) == 1 else 'their abilities'} by visiting the "
                      "Storyteller during private time. Anyone may visit, to bluff these characters: the town sees "
                      "that you went to the Storyteller, never why or what was said. A visit takes the place of that "
                      "turn's whisper, and you can visit once a day.")
    fields = []
    if 'slayer_shot' in script.public_actions:
        fields.append(_TB_FIELD)
    fields.append("- character: the character you choose when a night ability asks for one, otherwise null.")
    if script.claimable:
        guesses = ', "guesses": [{"player": a name, "character": a character}, ...]' if script.guessable else ''
        fields.append('- ability: to use a public day ability, or to claim to: {"character": '
                      f'{_quoted(script.claimable)}, "target": a player or null, "text": a statement or ""{guesses}}}'
                      '; otherwise null. You can use it on any public turn: the town square, or the comments on a '
                      'nomination. The town hears it as a use of that ability.')
    if visit:
        fields.append('- visit: during private time only, to visit the Storyteller instead of whispering: '
                      f'{{"character": {_quoted(script.visitable)}, "text": what you ask or tell them, or ""}};'
                      ' otherwise null. The answer comes to you in private; the town sees only that you went.')
    return [
        ('using the Trouble Brewing script', f'using {script.name}, a custom script'),
        ('The Saint and Mayor add other ways to win or lose.',
         'Some characters on this script may add other ways to win or lose, or change these: their abilities say '
         'how.'),
        (_TB_NIGHT,
         "At night, characters with night abilities act and the Storyteller gives out information; the Demon attacks. "
         "At dawn the night's deaths are announced, in seat order, but not how or why. Characters act in the official "
         "night order: as a rule, those that protect, poison or make players drunk act before the Demon, and most "
         "information roles wake after it, so a player killed in the night does not wake again that night. Several "
         "players can die in one night, and some abilities kill by day. On the first night no Demon kills, unless "
         "its ability says so."),
        (_TB_DEATHS, deaths),
        (_TB_INFO, "Information from a working ability is true, unless an ability on this script says otherwise (a "
                   "character who can register as something they are not, or one that makes information false)."),
        (_TB_SLAYER, ' '.join(public) or 'Abilities on this script are used at night or when they trigger: none is '
                                         'used in public.'),
        (_TB_WRONG, "- Information can be wrong: players may be drunk or poisoned without being told, and some "
                    "characters can register as something they are not."),
        (_TB_BLUFFS, "- The Demon's three bluffs are characters not in play"
                     + (" (though the Drunk may believe they are one of them)" if 'Drunk' in script.all else '')
                     + ". The Minions only learn them if the Demon shares them."),
        ("- Night deaths are evidence too: the Demon chooses who dies, and who survives.",
         "- Night deaths are evidence, but on some scripts the Demon is not the only killer, and a death can come a "
         "night after the choice that caused it."),
        ("- targets: the player(s) you choose for a night ability, otherwise [].",
         "- targets: the player(s) you choose for a night ability, or when an ability asks you to choose a player, "
         "otherwise []."),
        (_TB_FIELD, '\n'.join(fields)),
    ]


def _teams_custom(script, n):
    tf, os_, mn = SETUPS[n]
    minions = 'one Minion' if mn == 1 else f'{mn} Minions'
    demons = f' ({_names(script.demons, "or")})' if script.demons else ''
    lunatic = (", with one exception: the Lunatic believes they are the Demon, and is not told otherwise"
               if 'Lunatic' in script.all else '')
    return (f"Teams. Good: Townsfolk and Outsiders. Evil: the Demon and {minions}. With {WORDS[n]} players there are "
            f"normally {tf} Townsfolk, {os_} Outsider{'' if os_ == 1 else 's'}, {minions} and one Demon{demons}; some "
            f"characters change how many Outsiders there are (their abilities say so, in brackets). Each character is "
            f"in play at most once. You know your own character, not anyone else's{lunatic}.\n"
            f"Evil knows itself at the start. The Demon and "
            f"{'its Minion know each other' if mn == 1 else 'its Minions all know one another'}, and the Demon learns "
            f"three good characters that are not in play (bluffs). Evil players can only talk the way everyone else "
            f"does: in town{', by whisper, or to the Storyteller on a visit' if script.visitable else ' or by whisper'}"
            f".")


DAWN_DEATHS = [
    'The bell tolls once before sunrise. {dead} will not be joining the town today.',
    'A cold wind moves through the square. Where {dead} should be standing, there is only an empty chair.',
    'The baker is first to find the door left open. {dead} did not live to see the morning.',
    'Rooks circle the chapel roof at first light. The town gathers, and {dead} is missing.',
    'Fog hangs low over the cobbles, and the lamplighter brings grim news: {dead} is dead.',
    'Morning comes grey and quiet. Someone lays a sprig of rosemary on the doorstep of {dead}.',
    'The well bucket creaks in the dawn stillness. Word spreads fast: {dead} was taken in the night.',
    'Dogs howl until daybreak. When the town gathers, {dead} does not answer to their name.',
]
DAWN_QUIET = [
    'Dawn breaks over the rooftops, and every face in the square is accounted for.',
    'The night passes without a scream. The town gathers, uneasy but whole.',
    'A pale sun rises. Nobody is missing this morning, and nobody quite believes their luck.',
    'Mist lifts from the millpond. Every door along the lane opens to a living soul.',
    'The cockerel crows, the chapel bell rings, and the whole town answers.',
    'Frost on the windows, smoke from every chimney: all are alive to greet the day.',
]



def dawn_narration(r, deaths):
    """A line of dawn narration for the scripted Storyteller (it never hints at characters or causes)."""
    if not deaths:
        return r.choice(DAWN_QUIET)
    dead = deaths[0] if len(deaths) == 1 else ', '.join(deaths[:-1]) + ' and ' + deaths[-1]
    return r.choice(DAWN_DEATHS).format(dead=dead)
