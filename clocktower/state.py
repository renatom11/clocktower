"""Grimoire state, and the Storyteller's choices.

The Grimoire holds the truth: who is which character, on which team, alive or dead, and the states the
abilities leave on players (poisoned, safe, a Butler's master), each with its source and when it ends. What a
character does is its entry in characters.py; the Grimoire answers questions about the game for those entries.

Everything the Storyteller decides (setup details, information for impaired players, Spy/Recluse
registration, Mayor bounces) is a Choice: the full list of legal values plus the scripted Storyteller's style
(see POLICY). The style can produce every legal value, so no legal option is ever ruled out; the engine never
applies an illegal value.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from itertools import combinations, product
import random
from typing import Callable
from .characters import INFO_ROLES, SETUPS, TB, is_evil_character, kind, rules


@dataclass
class Player:
    name: str
    seat: int
    character: str          # true character (changes when, say, a Minion becomes the Demon)
    shown: str              # the character this player believes they are (differs for the Drunk)
    alive: bool = True
    ghost_vote: bool = True
    alignment: str = ''     # 'good' or 'evil': dealt with the character, and kept when the character changes
    seems_dead: bool = False  # alive, but registers and is shown as dead (the Zombuul after its first death)
    extra: list = field(default_factory=list)  # abilities held beyond their own character's (the Philosopher's)
    traveller: bool = False  # a Traveller doesn't count towards 'two alive' or the Scarlet Woman's five

    def __post_init__(self):
        self.alignment = self.alignment or ('evil' if is_evil_character(self.character) else 'good')

    @property
    def evil(self):
        # games checkpointed before alignment was stored hold players without it
        return (self.alignment or ('evil' if is_evil_character(self.character) else 'good')) == 'evil'

    @property
    def is_demon(self):
        return kind(self.character) == 'Demon'

    @property
    def appears_alive(self):
        """Alive as the town sees it: what nominations, votes, ghost votes and the 'dead' labels go by."""
        return self.alive and not self.seems_dead


@dataclass
class State:
    """Something an ability put on a player: 'poisoned', 'drunk', 'safe' (from the Demon), 'master' (a Butler's),
    'cursed' (the Witch's), 'mad' (the Cerenovus's: `about` is the character they must be mad about being) or 'has
    ability' (a dead player keeps their ability: the Vigormortis's Minions; `about` is the character or type they
    keep it as). It ends at `until` (a dusk: 'night'), and, if `ends_with_source`, as soon as its source dies or stops
    being the character that made it (a dead Poisoner's poison ends)."""
    kind: str
    target: str
    source: str | None = None
    until: str | int = 'night'  # 'night': the next dusk; 'dawn': the end of tonight; a number n: the dusk before
    #                             night n; None: no end
    ends_with_source: bool = False
    against: str = 'demon'      # for 'safe': the deaths it stops ('demon', 'execution' or 'any')
    while_source_works: bool = False  # in force only while its source is alive, sober and healthy (the Courtier)
    about: str | None = None    # what a 'mad' or 'has ability' state is about (a character, or a character type)


def team_sizes(n, outsiders=0, floor=False):
    """(Townsfolk, Outsiders, Minions) for n players, from the official table, with `outsiders` Townsfolk turned
    into Outsiders by setup modifiers (True means the Baron's 2). With `floor`, removing Outsiders where there are too
    few removes only those there are, and adds no Townsfolk for the rest (the Vigormortis's rule)."""
    tf, os_, mn = SETUPS[n]
    d = 2 if outsiders is True else int(outsiders)
    if floor and os_ + d < 0:
        d = -os_
    return tf - d, os_ + d, mn


def setup_change(characters):
    """Townsfolk the characters' fixed setup modifiers turn into Outsiders (the Baron: 2)."""
    return sum(rules(c).outsiders for c in characters)


def setup_changes(characters):
    """Every total the characters' setup modifiers allow, including the Storyteller's choices (the Godfather's
    -1 or +1)."""
    totals = {setup_change(characters)}
    for c in characters:
        if rules(c).outsider_choices:
            totals = {t + d for t in totals for d in rules(c).outsider_choices}
    return totals


def setup_error(characters, script=TB):
    """Why a list of characters is not a legal setup of `script`, or None."""
    n = len(characters)
    if n not in SETUPS: return f'{script.name} is for {min(SETUPS)}-{max(SETUPS)} players'
    if len(set(characters)) != n: return 'characters must be distinct'
    bad = [c for c in characters if c not in script.all]
    if bad: return f'not on the script: {bad}'
    counts = {k: sum(1 for c in characters if kind(c) == k) for k in ('Townsfolk', 'Outsider', 'Minion', 'Demon')}
    if counts['Demon'] != 1: return 'need exactly one ' + (script.demons[0] if len(script.demons) == 1 else 'Demon')
    sizes = [team_sizes(n, d, floor=True) for d in sorted(setup_changes(characters))]
    tf, os_, mn = sizes[0]
    if counts['Minion'] != mn: return f'need exactly {mn} Minion(s)'
    if (counts['Townsfolk'], counts['Outsider']) not in {(t, o) for t, o, _ in sizes}:
        modifiers = [c for c in characters if rules(c).outsiders]
        return f'need {tf} Townsfolk and {os_} Outsiders' + (f' ({", ".join(modifiers)} in play)' if modifiers else '')
    return None


def random_setup(rng, minion=None, players=9, script=TB):
    """A uniformly random legal setup of `script`; `minion` forces one of the Minions (batches rotate it)."""
    mn = SETUPS[players][2]
    minions = ([minion] if minion else []) + rng.sample([m for m in script.minions if m != minion],
                                                        mn - (1 if minion else 0))
    change = setup_change(minions)
    for m in minions:  # the Storyteller's choice for a modifier that offers one (the Godfather), among those the
        if rules(m).outsider_choices:  # script can deal (no -1 with no Outsiders to remove)
            def dealable(d):
                t, o, _ = team_sizes(players, change + d)
                return 0 <= t <= len(script.townsfolk) and 0 <= o <= len(script.outsiders)
            options = [d for d in rules(m).outsider_choices if dealable(d)]
            key = rules(m).outsider_policy
            if key and len(options) > 1:  # the largest choice by its weight (the Godfather's +1), else the others
                big = max(options)
                change += big if rng.random() < POLICY[key] else rng.choice([d for d in options if d != big])
            else:
                change += rng.choice(options)
    demon = script.demons if len(script.demons) == 1 else [rng.choice(script.demons)]
    change += setup_change(demon)  # a Demon's modifier (the Fang Gu's +1, the Vigormortis's -1)
    tf, os_, _ = team_sizes(players, change, floor=True)
    return rng.sample(script.townsfolk, tf) + rng.sample(script.outsiders, os_) + minions + demon


# How the scripted Storyteller uses its discretion. Every number is a judgment call about what an
# experienced human Storyteller tends to do. There is no separate random floor: the style is itself
# random and can produce any answer a working ability could give in some legal game (tests check
# this), so no plausible option is ever ruled out, and impossible ones never appear.
POLICY = {
    # impaired players
    'drunk_truthful': 0.2,    # per game: the Drunk gets true information (else from their false world)
    'poisoned_false': 0.8,    # per night: a poisoned player's information comes from a false world (else true)
    'false_vouch_evil': 0.7,  # a misinformed Washerwoman's pair includes an evil player (else any player)
    # registration (weighted toward evil, as a Storyteller balancing the game would)
    'spy_evil': 0.1,          # the Spy registers as evil
    'recluse_evil': 0.5,      # the Recluse registers as evil
    'recluse_as_imp': 0.3,    # a Recluse registering as an evil character registers as the Imp (else a Minion)
    'as_bluff': 0.7,          # an evil player shown as a good character is shown as a Demon bluff,
    'as_in_play': 0.1,        # or as a good character in play (else one not in play)
    'misregister_pair': 0.5,  # a Washerwoman/Librarian/Investigator is shown a misregistering Spy/Recluse
    'recluse_slain': 0.2,     # the Slayer's shot kills the Recluse
    'spy_virgin': 0.2,        # the Spy registers as a Townsfolk to the Virgin
    # setup and other
    'drunk_info_weight': 3,   # the Drunk believes they are an information role, 3x as likely as another
    'bluff_drunk_role': 0.05, # the Drunk's apparent character may be among the Demon's bluffs (else kept out)
    'bluff_drunk': 0.05,      # the Drunk may be among the Demon's bluffs (else kept out)
    'herring_townsfolk': 0.85,  # the red herring is a Townsfolk other than the Fortune Teller (else any good player)
    'pair_partner_good': 0.9, # an Investigator's second player is a good player (else anyone)
    'mayor_bounce': 0.5,      # an attack on the Mayor kills someone else
    'bounce_evil': 0.05,      # a Mayor bounce may land on the Minion (else a good player)
    # Bad Moon Rising
    # the Shabaloth regurgitates one of the dead players it chose last night: the almanac says "only rarely ...
    # once per game, maybe twice"; the wiki, usually a good player, a Minion "rarely". Default, for review.
    'shabaloth_regurgitate': 0.25,  # per night with a candidate, while under the budget
    # the owner's review (docs/bmr-rulings.md), 2026-11-06
    'godfather_more_outsiders': 0.75,  # the Godfather's +1 Outsider, when -1 is possible too (B1.8: extra Outsiders
    #                                    feed the Godfather, as the Baron's do)
    'pacifist_over_fool': 0.5,   # an executed Fool is saved by the Pacifist, keeping their ability (else by their own)
    'exorcise_lunatic': 0.75,    # an Exorcist choosing the Lunatic is treated as exorcising them (B3.8)
    'regurgitations': 2,            # the budget per game; beyond it the chance is a tenth
    'regurgitate_evil': 0.1,        # the regurgitated player may be evil (else a good one, when there is one)
    # the Sailor's choice of another player: who is drunk. The almanac: "If they choose a Townsfolk, the Storyteller
    # will usually make the Townsfolk drunk, but if an Outsider, a Minion, or the Demon is chosen ... usually make the
    # Sailor the drunk one". Default, for review.
    'sailor_townsfolk_drunk': 0.8,  # a chosen Townsfolk is the drunk one (else the Sailor)
    'sailor_self_drunk': 0.8,       # with an Outsider, Minion or Demon chosen, the Sailor is the drunk one
    # which of the Innkeeper's two is drunk. The almanac: the drunk "may be good or evil, but will almost always be
    # good"; the wiki: an Innkeeper who picks themself is likely to be made drunk. Default, for review.
    'innkeeper_self_drunk': 0.8,    # an Innkeeper who chose themself is the drunk one
    'innkeeper_good_drunk': 0.9,    # of a good and an evil player, the good one is drunk (two alike: either)
    # whether the Pacifist saves an executed good player. The almanac: "once per game is usually about right ...
    # On rare occasions, to make the Pacifist look suspicious, you can never trigger it"; the wiki: more likely "at a
    # critical juncture as the game comes to a climax". Default, for review.
    'pacifist_save': 0.2,           # per good player's execution, before the first save
    'pacifist_late': 0.4,           # the same, once five or fewer players are alive (the climax)
    'pacifist_again': 0.05,         # per execution after a save
    'pacifist_never': 0.1,          # per game: the Pacifist never saves anyone
    # the Grandchild. The almanac: "choose a Grandchild by marking any good character". Default, for review.
    'grandchild_townsfolk': 0.75,   # the Grandchild is a Townsfolk (else an Outsider), when there are both
    # whom the Gossip's true statement kills. The almanac: "we recommend that you choose a character that will
    # actually die, not one protected from death". Default, for review.
    'gossip_victim_evil': 0.2,      # the victim is an evil player (never the Demon), when one would die
    # when the Tinker dies. The almanac: "most interesting if the Tinker dies at night"; "You can choose to never kill
    # the Tinker"; "never kill the Tinker when it would end the game". Default, for review.
    'tinker_never': 0.1,            # per game: the Tinker never dies by their ability
    'tinker_night': 0.2,            # per night, at the Tinker's step (owner: usually at night, among other deaths)
    'tinker_day': 0.002,            # per point of the day (about 12 a day: about 2% a day, a tenth of a night's)
    # the Lunatic's illusion. The almanac: Minions "can be any players"; bluffs "can even be characters that are in
    # play"; "You can make the Lunatic think they are a different Demon than the in-play Demon". Default, for review.
    'lunatic_same_demon': 0.8,      # the Lunatic believes they are the Demon in play (else another on the script)
    'lunatic_shows_demon': 0.5,     # the real Demon is among the Lunatic's "Minions" (else other players)
    'lunatic_bluff_in_play': 0.25,  # each of the Lunatic's three bluffs is a good character in play (else not)
    # Sects & Violets
    # whether a player who broke madness is executed. The almanac (Cerenovus): mad evil players "might be executed this
    # way, but 'might' means you can choose not to, to prevent evil from winning by this strategy"; the rulebook: a
    # player made mad "can end the game by being executed, because that's a player's choice". Default, for review.
    'mad_execute_good': 0.9,        # a good player who broke madness is executed
    'mad_execute_evil': 0.5,        # an evil one
    # deaths tonight when the Pit-Hag makes a Demon (almanac How to Run). Default, for review.
    'pithag_quiet': 0.8,            # a Demon made into another Demon: nobody dies tonight ("best ... no death")
    'pithag_kill_old_demon': 0.8,   # a new evil Demon: the old Demon dies tonight ("best to kill the old Demon")
    'pithag_final_kill': 0.8,       # a good Demon on the final night: the evil Demon dies ("kill either Demon")
    'final_night_alive': 4,         # a night is the final one when this many players or fewer are alive at dusk
    # the Dreamer's false character. The almanac: for a good player, "any Minion or Demon"; the wiki: "almost always
    # show real Dreamers in-play Minions"; for an evil player, "you can help the evil team if you show ... the good
    # character that this evil player is bluffing as, or ... a more secretive character". Default, for review.
    'dreamer_minion_in_play': 0.5,  # a good player's false character is a Minion in play (else any evil character)
    'dreamer_bluff': 0.5,           # an evil player who claimed a good character aloud is shown as it
    'dreamer_secretive': 0.3,       # otherwise, a secretive good character (Snake Charmer, Sage, Mutant, Klutz)
    # the Sage's second player. The almanac: "If the Sage dies early, you will probably want to show the Sage two
    # alive players ... If the Sage dies on the final night, feel free to show one alive and one dead player".
    # Default, for review.
    'sage_alive': 0.9,              # before the final night, the other player shown is alive (else anyone)
    # the Savant's two statements (snv.savant_choice). The almanac: "Keep the information you give helpful and related
    # to the game. Avoid saying who exactly the Demon is"; a drunk or poisoned Savant "might get two pieces of true
    # information or two pieces of false information". Default, for review.
    'savant_same_kind': 0.5,        # the false statement has the same form as the true one (else any form)
    'savant_both_false': 0.7,       # a misinformed Savant hears two false statements (else two true ones)
    # whom the Sweetheart's death makes drunk. The almanac: "You will almost always want to make a Townsfolk drunk ...
    # but if evil is winning quite convincingly, you can make an Outsider, Minion, or even the Demon drunk." Default,
    # for review.
    'sweetheart_townsfolk': 0.9,    # a living good Townsfolk (else any other living player)
    # Carousel (the experimental characters and custom scripts: docs/carousel-rulings.md)
    # the Recluse/Sage jinx: "The Recluse might register as the Demon to the Sage". Default, for review.
    'sage_shows_recluse': 0.3,      # a working Sage killed by the Demon is shown the Recluse in the Demon's place
    # the Storyteller judge (judge.py, when one is chosen; never in TB's protocol v17): how often the judge's first and
    # second choices are taken; otherwise the scripted style decides, so no habit takes over
    'judge_top': 0.85,
    'judge_second': 0.10,
}


def norm(value):
    """A Storyteller value: any of players, character, number, yes, characters, and statements (the Savant's: only
    when there are some, so values without them read exactly as before)."""
    value = value or {}
    out = {'players': list(value.get('players') or []), 'character': value.get('character'),
           'number': value.get('number'), 'yes': value.get('yes'), 'characters': list(value.get('characters') or [])}
    if value.get('statements'):
        out['statements'] = list(value['statements'])
    return out


def _key(v):
    v = norm(v)
    return (tuple(sorted(v['players'])), v['character'], v['number'], v['yes'], tuple(sorted(v['characters'])),
            tuple(sorted(v.get('statements', []))))


class Choice:
    """A decision the Storyteller makes: every legal value, and the scripted style. `context` and `truth` (what a
    working ability could show) are for the Storyteller judge (judge.py)."""
    context = None
    truth = None

    def __init__(self, id, values, style: Callable[[random.Random], dict]):
        self.id, self.values, self.style = id, [norm(v) for v in values], style
        self.keys = {_key(v) for v in self.values}
        self.auto = len(self.keys) == 1  # only one legal value: nothing to decide

    def legal(self, value):
        return _key(value) in self.keys

    def options(self, r):
        """The scripted Storyteller's pick: the style (random, and always legal)."""
        if self.auto:
            return self.values[0]
        return norm(self.style(r))


def judged(choice, call, question, about=None, recipient=None, impaired=False, truth=None, **more):
    """`choice` with what the Storyteller judge needs (judge.py): `call`, the kind of decision (the rules judge's
    heuristics go by it); `question`, in plain words; `about`, the player the result is about; `recipient`, who
    learns or is affected by it; `impaired`, whether they are drunk or poisoned (so any value is legal); `truth`,
    what a working ability could show. Nothing here touches the scripted style, so with no judge the value is the
    same."""
    choice.context = {'call': call, 'about': about, 'recipient': recipient, 'impaired': impaired,
                      'question': question, **more}
    if truth is not None:
        choice.truth = truth
    return choice


_PAUSING = set()  # states whose pause is being worked out (Grimoire.active), so a state can't loop on itself
_DERIVING = set()  # (player, ability) whose derived states are being worked out (Grimoire.derived), likewise


class Grimoire:
    def __init__(self, names, characters, drunk_as=None, script=TB):
        self.script = script
        self.players = [Player(n, i, c, drunk_as if rules(c).always_drunk else c)
                        for i, (n, c) in enumerate(zip(names, characters))]
        self.by_name = {p.name: p for p in self.players}
        self.red_herring = None
        self.bluffs = []
        self.reminders = []         # what the pair abilities were shown, as on the real Grimoire
        self.states = []            # State: what abilities have put on players (poison, protection, a master)
        self.spent = set()          # once-per-game abilities used (by character)
        self.death_log = []         # every death, real or apparent: {player, cause, source, day, phase}
        self.woke = {}              # night -> players woken to use their own ability (the Chambermaid)
        self.nominations = []       # every nomination: {day, nominator, nominee, votes, voters, outcome, and the
        #                             characters of the nominator (character) and voters (characters) then}
        self.last_choices = {}      # player -> who they chose on their last night choice (the Po)
        self.night_choices = {}     # night -> {player: who they chose that night} ("last night": the Exorcist)
        self.executions = []        # every execution, killing or not: {player, day, died} (the Mastermind's day)
        self.revivals = []          # every return to life: {player, day, source} (the Shabaloth's budget)
        self.notes = {}             # an ability's own bookkeeping across nights (the Mastermind's extra day)
        self.abnormal = []          # abilities that worked abnormally due to another's: {player, ability, why, day,
        #                             phase} (Game.abnormal; the Mathematician counts them since dawn)
        self.day = 0
        self.executed_death = None  # who died by execution today (Undertaker)
        self.alive_at_execution = 0  # players alive just before that execution
        self.decoys = {}            # impaired player -> the false picture their information follows
        self.truthful = {}          # Drunk -> whether their information is true this game
        self.winner = None
        self.reason = None

    def __setstate__(self, d):
        """Games checkpointed before states existed held one field per state: carry them over."""
        old = {k: d.pop(k, None) for k in ('poisoned', 'protected', 'master', 'slayer_used', 'virgin_used')}
        self.__dict__.update(d)
        self.__dict__.setdefault('script', TB)
        self.__dict__.setdefault('death_log', [])
        self.__dict__.setdefault('woke', {})
        self.__dict__.setdefault('nominations', [])
        self.__dict__.setdefault('last_choices', {})
        self.__dict__.setdefault('night_choices', {})
        self.__dict__.setdefault('executions', [])
        self.__dict__.setdefault('revivals', [])
        self.__dict__.setdefault('notes', {})
        self.__dict__.setdefault('abnormal', [])
        if 'states' not in d:
            self.states, self.spent = [], set()
            for kind_, name in (('poisoned', old['poisoned']), ('safe', old['protected']), ('master', old['master'])):
                if name:
                    p = next((q for q in self.players if q.character == {'poisoned': 'Poisoner', 'safe': 'Monk',
                                                                         'master': 'Butler'}[kind_]), None)
                    self.add(State(kind_, name, p.name if p else None, ends_with_source=kind_ == 'poisoned'))
            self.spent = {c for c, used in (('Slayer', old['slayer_used']), ('Virgin', old['virgin_used'])) if used}

    def __getitem__(self, name):
        return self.by_name[name]

    # ---- states ----------------------------------------------------------------------
    def add(self, state):
        self.states.append(state)

    def expire(self, moment, night=None):
        """Remove the states that end at `moment` ('night': each dusk; `night` is the number of the night that
        starts, which ends states lasting until then)."""
        self.states = [s for s in self.states if s.until != moment and not (night and s.until == night)]

    def active(self, s):
        """Whether a state is in force now: one that lasts only while its source works is paused (not removed)
        while the source is dead, drunk or poisoned (the Courtier's drunkenness, when the Courtier is drunk). A state
        that would pause itself is not in force, rather than the question looping: a Pukka who poisons themself is
        not poisoned by it (and dies the next night, as the previously poisoned player)."""
        if not s.while_source_works or not s.source:
            return True
        if id(s) in _PAUSING:
            return True
        _PAUSING.add(id(s))
        try:
            src = self[s.source]
            return (src.alive or self.keeps_ability(src)) and not self.impaired(src)
        finally:
            _PAUSING.discard(id(s))

    def holders(self, kind_):
        """Names of the players with a state of this kind, in the order the states were made (then those an ability
        works out from the Grimoire: Grimoire.derived)."""
        return ([s.target for s in self.states if s.kind == kind_ and self.active(s)]
                + [s.target for s in self.derived() if s.kind == kind_])

    def has(self, p, kind_):
        return (any(s.kind == kind_ and s.target == p.name and self.active(s) for s in self.states)
                or any(s.kind == kind_ and s.target == p.name for s in self.derived()))

    def derived(self):
        """The states abilities put in force now by working them out from the Grimoire (Character.ongoing: the No
        Dashii's poisoned neighbours), so they follow every change of seat, character or sobriety at once. An ability
        asked about while its own states are being worked out adds nothing (a No Dashii is not poisoned by its own
        poison), as Grimoire.active does for a state that would pause itself."""
        names = getattr(self.script, 'derivers', ())
        if not names:
            return []
        out = []
        for q in self.players:
            for c in self.abilities(q):
                if c in names and (q.name, c) not in _DERIVING:
                    _DERIVING.add((q.name, c))
                    try:
                        out += rules(c).ongoing(self, q)
                    finally:
                        _DERIVING.discard((q.name, c))
        return out

    def keeps_ability(self, p):
        """Whether p, dead, still has their ability: an ability keeps it for them (a 'has ability' state: the
        Vigormortis's Minions) while they are still what it was kept for (a Minion: one who becomes a Townsfolk has no
        ability)."""
        return any(s.kind == 'has ability' and s.target == p.name and s.about in (p.character, kind(p.character))
                   and self.active(s) for s in self.states)

    def holder(self, character):
        """The player who has `character`'s ability now (their own, or one gained: the Philosopher's): alive, or dead
        and keeping it (Grimoire.keeps_ability). The first in seat order, if several have it."""
        return next((p for p in self.players if character in self.abilities(p) and (p.alive or self.keeps_ability(p))),
                    None)

    def nearest(self, p, step, test=lambda q: True):
        """The nearest player to p (not p) going one way round the circle (step 1: clockwise, -1: anticlockwise) who
        passes `test`, alive or dead (the No Dashii's Townsfolk neighbours), or None."""
        n = len(self.players)
        for k in range(1, n):
            q = self.players[(p.seat + step * k) % n]
            if test(q):
                return q
        return None

    def _single(self, kind_, value, source=None, ends_with_source=False):
        self.states = [s for s in self.states if s.kind != kind_]
        if value:
            self.add(State(kind_, value, source, ends_with_source=ends_with_source))

    # The three states Trouble Brewing has, as single names (one Poisoner, one Monk, one Butler)
    poisoned = property(lambda self: next(iter(self.holders('poisoned')), None),
                        lambda self, name: self._single('poisoned', name))
    protected = property(lambda self: next(iter(self.holders('safe')), None),
                         lambda self, name: self._single('safe', name))
    master = property(lambda self: next(iter(self.holders('master')), None),
                      lambda self, name: self._single('master', name))

    def spend(self, character):
        self.spent.add(character)

    def spent_ability(self, character):
        return character in self.spent

    slayer_used = property(lambda self: 'Slayer' in self.spent)
    virgin_used = property(lambda self: 'Virgin' in self.spent)

    # ---- basic queries -------------------------------------------------------------
    def living(self):
        return [p for p in self.players if p.alive]

    def alive_count(self):
        return len(self.living())

    def with_character(self, character, alive=True):
        return next((p for p in self.players if p.character == character and (p.alive or not alive)), None)

    def demon(self):
        """The living Demon, if any."""
        return next((p for p in self.players if p.alive and p.is_demon), None)

    def is_poisoned(self, p):
        return self.has(p, 'poisoned')

    def is_drunk(self, p):
        return rules(p.character).always_drunk or self.has(p, 'drunk')

    def impaired(self, p):
        """The player's own ability (as they understand it) is not working."""
        return self.is_drunk(p) or self.is_poisoned(p)

    def abilities(self, p):
        """The characters whose abilities p has: their own, and any gained (the Philosopher's)."""
        return [p.character, *getattr(p, 'extra', [])]

    def works(self, p, character):
        """p is alive (or dead and keeping their ability: the Vigormortis's Minions), has `character`'s ability, and
        is neither drunk nor poisoned."""
        return (p.alive or self.keeps_ability(p)) and character in self.abilities(p) and not self.impaired(p)

    def falsified(self, p, ability=None):
        """Whether the information p gets from `ability` (default: the character they believe they are) must be false,
        whatever their sobriety: another player's ability falsifies it (Character.falsifies: the Vortox's)."""
        names = getattr(self.script, 'falsifiers', ())
        if not names:
            return False
        ability = ability or p.shown
        return any(rules(c).falsifies(self, q, p, ability) for q in self.players for c in self.abilities(q)
                   if c in names)

    def unreliable(self, p, ability=None):
        """Whether p's information may be false: they are drunk or poisoned, or it is falsified (the Vortox). An
        information Choice offers every value then, as for an impaired player."""
        return self.impaired(p) or self.falsified(p, ability)

    def safe_from_demon(self, p):
        """The Demon's attack can't kill p: their own ability (the Soldier) or protection (the Monk's)."""
        return self.safe(p, 'demon')

    def safe(self, p, cause):
        """Whether p can't die from `cause` ('demon', 'execution', or another source such as 'assassin'): their
        own ability (the Soldier, against the Demon), a protection on them (the Monk's against the Demon; others
        against any death), or another player's ability that protects them (a Tea Lady's neighbours)."""
        if rules(p.character).safe_from(self, p, cause):
            return True
        if any(s.kind == 'safe' and s.target == p.name and s.against in (cause, 'any') and self.active(s)
               for s in self.states):
            return True
        return any(q is not p and rules(q.character).protects(self, q, p, cause) for q in self.players)

    def revive(self, p, source=None):
        """p comes back to life (the Professor, the Shabaloth): alive, with their vote token and their ability,
        even a spent once-per-game one. `source` names the ability (for the log)."""
        p.alive, p.seems_dead, p.ghost_vote = True, False, True
        self.spent.discard(p.character)
        self.revivals.append({'player': p.name, 'day': self.day, 'source': source})

    def jinxed(self, a, b):
        """The text of the jinx between two characters in effect on this script (Script.jinxed), or None."""
        return self.script.jinxes.get((a, b))

    def died_today(self, day=None):
        """Players who died (or seemed to) during day `day` (default: the current one), in order."""
        day = self.day if day is None else day
        return [d['player'] for d in self.death_log if d['day'] == day and d['phase'] != 'night']

    def change_character(self, p, character):
        """p becomes `character` (and believes it), keeping their alignment. States that last only while their
        source has its ability end (a Poisoner who becomes the Imp stops poisoning)."""
        p.character = p.shown = character
        if getattr(p, 'extra', None):  # abilities gained through the old character go with it (the Philosopher's)
            p.extra = []
        self._source_lost(p)

    def _source_lost(self, p):
        kept = [s.target for s in self.states if s.kind == 'has ability' and s.source == p.name and s.ends_with_source]
        self.states = [s for s in self.states if not (s.ends_with_source and s.source == p.name)]
        for name in kept:  # dead players who kept their ability through p's lose it, and its effects end
            q = self[name]
            if not q.alive and not self.keeps_ability(q):
                self._source_lost(q)

    def neighbours(self, p):
        """Nearest living players clockwise and anticlockwise (excluding p). A Zombuul who seems dead is not an
        alive neighbour."""
        n = len(self.players)
        out = []
        for step in (-1, 1):
            i = p.seat
            for _ in range(n - 1):
                i = (i + step) % n
                q = self.players[i]
                if q.appears_alive and q is not p:
                    out.append(q)
                    break
        if len(out) == 2 and out[0] is out[1]:
            out = out[:1]
        return out

    # ---- registration --------------------------------------------------------------
    def registers_evil(self, p, observer=None):
        """Set of possible answers to 'is p evil?' (asked by `observer`'s ability, if given)"""
        return rules(p.character).registers_evil(self, p, observer)

    def registers_as(self, p, observer=None):
        """Set of characters p might register as."""
        return rules(p.character).registers_as(self, p, observer)

    def registers_demon_to_ft(self, p, observer=None):
        return rules(p.character).registers_demon_to_ft(self, p, observer)

    def decoy(self, p, r):
        """The false world an impaired player's information comes from, fixed per player so it stays
        consistent from night to night: a framed good player is the Demon, as many other non-Demon
        players as the game has Minions are the Minions, and everyone else (the real Demon included)
        is good. Misinformed results are what
        a working ability would show in that world, so they look like real results: never inverted,
        and sometimes true where the false world agrees with the real one."""
        if p.name not in self.decoys:
            others = [q for q in self.players if q is not p]
            framed = r.choice([q for q in others if not q.evil])
            minions = sum(1 for q in self.players if kind(q.character) == 'Minion') or 1
            partners = r.sample([q for q in others if q is not framed and q.character != 'Imp'], minions)
            self.decoys[p.name] = (framed.name, {framed.name, *(q.name for q in partners)})
        return self.decoys[p.name]

    def false_evil(self, p, r):
        """Who registers as evil in p's false world this time: its two evil players, plus the Recluse
        by the usual registration chance (as it would for a working ability)."""
        evil = set(self.decoy(p, r)[1])
        for q in self.players:
            c = rules(q.character)
            if not c.evil and c.misregisters and not self.is_poisoned(q) and r.random() < POLICY[c.misregisters]:
                evil.add(q.name)
        return evil

    def false_result(self, p, r, result, truths):
        """A misinformed result, `result(r)` drawn from p's false world. A poisoned player's false world is
        redrawn until the result is not one a working ability could give (when some result is not), so
        poison makes information false. The Drunk keeps one false world all game, so their story holds."""
        v = result(r)
        for _ in range(30):
            if p.character == 'Drunk' or v not in truths:
                return v
            self.decoys.pop(p.name, None)
            v = result(r)
        return v

    def minions_shown(self):
        """Minion characters a false or misregistered result may name: a setup modifier (the Baron) only
        when in play (the Outsider count would otherwise rule it out)."""
        return [m for m in self.script.minions if not rules(m).outsiders or m in self.in_play()]

    def misinformed(self, p, r):
        """Whether the scripted Storyteller gives this impaired player false information now. The
        Drunk's is decided once per game, so their story stays consistent either way."""
        if p.character == 'Drunk' and not self.falsified(p):
            if p.name not in self.truthful:
                self.truthful[p.name] = r.random() < POLICY['drunk_truthful']
            return not self.truthful[p.name]
        if self.falsified(p):  # always false, without a draw (the Vortox)
            return True
        # drunk or poisoned (in Trouble Brewing only the Poisoner impairs a player who isn't the Drunk)
        return self.impaired(p) and r.random() < POLICY['poisoned_false']

    def sample_evil(self, r):
        """Who registers as evil this time, under the scripted Storyteller's registration policy."""
        out = set()
        for q in self.players:
            key = rules(q.character).misregisters
            chance = POLICY[key] if key else None
            if chance is not None and not self.is_poisoned(q):
                if r.random() < chance:
                    out.add(q.name)
            elif q.evil:
                out.add(q.name)
        return out

    def fake_good(self, r, kinds=None, avoid=(), bluffs=True):
        """A good character to show for an evil player: a Demon bluff, one in play, or another. With
        bluffs=False (for a good player) never a Demon bluff: no good player can be one in any world."""
        kinds = kinds or (self.script.townsfolk,)
        pool = [c for k in kinds for c in k if c not in avoid and (bluffs or c not in self.bluffs)]
        bluffs = [c for c in pool if c in self.bluffs]
        in_play = [c for c in pool if c in self.in_play() and c not in bluffs]
        other = [c for c in pool if c not in bluffs and c not in in_play]
        groups = [(x, w) for x, w in ((bluffs, POLICY['as_bluff']), (in_play, POLICY['as_in_play']),
                                      (other, 1 - POLICY['as_bluff'] - POLICY['as_in_play'])) if x]
        return r.choice(r.choices([x for x, _ in groups], [w for _, w in groups])[0])

    def evil_character(self, r, imp=True):
        """An evil character to show for a Recluse (the Imp only when `imp` is consistent)."""
        return 'Imp' if imp and r.random() < POLICY['recluse_as_imp'] else r.choice(self.minions_shown())

    def in_play(self):
        return {q.character for q in self.players} | {q.shown for q in self.players}

    # ---- deaths and victory ----------------------------------------------------------
    def die(self, p):
        p.alive = False
        if not self.keeps_ability(p):  # a dead Poisoner's poison ends (not a Minion the Vigormortis killed)
            self._source_lost(p)

    def check_victory(self):
        if self.winner: return self.winner
        end = None
        if not self.demon():
            end = 'good', 'The Demon is dead.'
        elif self.alive_count() <= 2:
            end = 'evil', 'Only two players remain alive.'
        for p in self.players if end else ():  # a character may keep the game going or change who wins
            changed = rules(p.character).overrides_end(self, p, *end)
            if changed is False:
                return None
            if changed:
                end = changed
        if end:
            self.winner, self.reason = end
        return self.winner

    # ---- views ---------------------------------------------------------------------
    def grimoire_text(self, reminders=()):
        lines = []
        for p in self.players:
            tags = []
            if p.shown != p.character: tags.append(f'thinks they are the {p.shown}')
            if not p.alive: tags.append('DEAD' + ('' if p.ghost_vote else ', ghost vote used'))
            if self.is_poisoned(p): tags.append('POISONED')
            if self.has(p, 'drunk'): tags.append('DRUNK')  # from an ability (none in Trouble Brewing)
            if any(s.kind == 'safe' and s.target == p.name and s.against == 'demon' and self.active(s)
                   for s in self.states):
                tags.append('protected by the Monk tonight')
            tags += ['cannot die' + ('' if s.against == 'any' else f' by {s.against}')  # protections beyond TB's
                     for s in self.states
                     if s.kind == 'safe' and s.target == p.name and s.against != 'demon' and self.active(s)]
            if p.seems_dead: tags.append('ALIVE, but registers as dead')
            for s in self.states:  # Sects & Violets' states (none in Trouble Brewing or Bad Moon Rising)
                if s.target == p.name and self.active(s) and s.kind in ('cursed', 'mad', 'has ability'):
                    tags.append({'cursed': 'CURSED (dies if they nominate today)',
                                 'mad': f'MAD about being the {s.about}',
                                 'has ability': 'keeps their ability while dead'}[s.kind])
            if getattr(p, 'extra', None): tags.append(f"also has the ability of the {', '.join(p.extra)}")
            if p.name == self.red_herring: tags.append("Fortune Teller's red herring")
            if self.has(p, 'master'): tags.append("Butler's master")
            team = 'evil' if p.evil else 'good'
            lines.append(f'{p.seat + 1}. {p.name}: {p.character} ({team})' + (f" [{'; '.join(tags)}]" if tags else ''))
        if self.bluffs: lines.append(f"Demon bluffs: {', '.join(self.bluffs)}")
        used = sorted(self.spent)
        if used: lines.append(f"Spent once-per-game abilities: {', '.join(used)}")
        lines += list(self.reminders) + list(reminders)
        return '\n'.join(lines)


# ---- Storyteller choices -----------------------------------------------------------

def drunk_as_choice(options, drunk=None):
    """The Townsfolk the Drunk believes they are (one not in play)."""
    w = [POLICY['drunk_info_weight'] if c in INFO_ROLES else 1 for c in options]
    choice = Choice('drunk_as', [{'character': c} for c in options], lambda r: {'character': r.choices(options, w)[0]})
    return judged(choice, 'drunk_as', 'Which Townsfolk (not in play) does the Drunk believe they are? Usually an '
                                      'information role, whose false results do the most to mislead.',
                  about=drunk and drunk.name, recipient=drunk and drunk.name)


def red_herring_choice(g):
    """A good player who registers as the Demon to the Fortune Teller: usually a Townsfolk other than
    the Fortune Teller (so a good player is framed), else any good player."""
    good = [p.name for p in g.players if not p.evil]
    townsfolk = [p.name for p in g.players if kind(p.character) == 'Townsfolk' and p.character != 'Fortune Teller']

    def style(r):
        pool = townsfolk if townsfolk and r.random() < POLICY['herring_townsfolk'] else good
        return {'players': [r.choice(pool)]}
    ft = next((p.name for p in g.players if p.shown == 'Fortune Teller'), None)
    return judged(Choice('red_herring', [{'players': [x]} for x in good], style), 'red_herring',
                  'Which good player is the red herring (registers as the Demon to the Fortune Teller all game)? '
                  'Usually a Townsfolk other than the Fortune Teller.', recipient=ft)


def pick_bluffs(r, options, drunk, drunk_shown=None):
    """Three Demon bluffs that fit the setup's counts: an information role (so evil can invent checkable
    results), and one Outsider only when the Drunk is in play (the town sees one Outsider fewer than
    the setup has, so one evil Outsider claim fits; otherwise it would break the count). The Drunk's
    apparent character (a sure double claim) and the Drunk (unclaimable) are usually kept out."""
    avoid = {c for c, keep in ((drunk_shown, POLICY['bluff_drunk_role']), ('Drunk', POLICY['bluff_drunk']))
             if c and r.random() >= keep}
    if len([c for c in options if c not in avoid]) >= 3:
        options = [c for c in options if c not in avoid]
    townsfolk = [c for c in options if kind(c) != 'Outsider']
    outsiders = [c for c in options if kind(c) == 'Outsider']
    picks = []
    info = [c for c in townsfolk if c in INFO_ROLES]
    if info:
        picks.append(r.choice(info))
    if drunk and outsiders:
        picks.append(r.choice(outsiders))
    rest = [c for c in townsfolk if c not in picks]
    if len(rest) < 3 - len(picks):  # too few Townsfolk left (never at 10-12 players)
        rest = [c for c in options if c not in picks]
    return picks + r.sample(rest, 3 - len(picks))


def bluffs_choice(options, drunk, drunk_shown=None):
    """Three good characters not in play, shown to the Imp."""
    choice = Choice('bluffs', [{'characters': list(c)} for c in combinations(options, 3)],
                    lambda r: {'characters': pick_bluffs(r, options, drunk, drunk_shown)})
    return judged(choice, 'bluffs', 'Which three good characters, not in play, does the Demon learn as bluffs? Ones '
                                    'evil can claim safely: an information role, an Outsider only when the town sees '
                                    'one Outsider fewer than the setup has (the Drunk), and not the Drunk\'s apparent '
                                    'character.')


def _pair(r, first, others, avoid=()):
    """`first` and a second player from `others` (not in `avoid` if possible), in random order."""
    pool = [x for x in others if x != first and x not in avoid] or [x for x in others if x != first]
    pair = [first, r.choice(pool)]
    r.shuffle(pair)
    return pair


def pair_choice(g, p, ability):
    """Washerwoman / Librarian / Investigator starting information."""
    s = g.script
    group = {'Washerwoman': s.townsfolk, 'Librarian': s.outsiders, 'Investigator': s.minions}[ability]
    others = [q.name for q in g.players if q is not p]
    impaired = g.unreliable(p, ability)
    values = [{'players': [a, b], 'character': c} for a, b in combinations(others, 2) for c in group
              if impaired or any(c in g.registers_as(g[x]) for x in (a, b))]
    if ability == 'Librarian' and (impaired or not any(g.registers_as(q) <= set(s.outsiders) for q in g.players)):
        values.append({'players': [], 'character': None})  # "zero Outsiders in play"

    def false_pair(r, first, pool):
        """A pair with `first` and a character from `pool` that neither player really is (nor believes
        they are), and never the recipient's own apparent character: false, and not self-revealing."""
        for _ in range(50):
            pair = _pair(r, first, others)
            c = r.choice(pool)
            if c != p.shown and all(c not in (g[x].character, g[x].shown) for x in pair):
                return {'players': pair, 'character': c}
        return {'players': pair, 'character': c}

    def style(r):
        if impaired and g.misinformed(p, r):
            framed, _ = g.decoy(p, r)
            evil = [q.name for q in g.players if q.evil and q is not p]
            if ability == 'Washerwoman':  # usually vouch for an evil player
                shown = r.choice(evil) if evil and r.random() < POLICY['false_vouch_evil'] else r.choice(others)
                return false_pair(r, shown, [g.fake_good(r, bluffs=g[shown].evil) for _ in range(6)])
            if ability == 'Librarian':
                if not any(kind(q.character) == 'Outsider' for q in g.players):
                    return {'players': [], 'character': None}  # the false world has no Outsiders either
                shown = r.choice(evil + [framed])
                return false_pair(r, shown, [g.fake_good(r, (s.outsiders,), bluffs=g[shown].evil) for _ in range(6)])
            return false_pair(r, framed, g.minions_shown())  # frame a good player
        real = [(q.name, q.character) for q in g.players if q is not p and q.character in group]
        mis = []  # a misregistering Spy (as a Townsfolk or Outsider) or Recluse (as a Minion)
        for q in g.players:
            if q is p or q.character not in ('Spy', 'Recluse') or q.character in group:
                continue
            options = g.registers_as(q) & set(group)
            if not options:
                continue
            if q.character == 'Spy':  # never the recipient's own character (that would point at the Spy)
                mis.append((q.name, g.fake_good(r, (group,), avoid=(p.shown,))))
            else:
                mis.append((q.name, r.choice(sorted(options & set(g.minions_shown())))))
        pool = mis if mis and r.random() < POLICY['misregister_pair'] else real  # with no real one: 'zero'
        if not pool:
            return {'players': [], 'character': None}
        n, c = r.choice(pool)
        avoid = ()
        if ability == 'Investigator' and r.random() < POLICY['pair_partner_good']:
            avoid = {q.name for q in g.players if q.evil}  # the second player is a good one
        return {'players': _pair(r, n, others, avoid), 'character': c}

    def shows(v):  # what a working ability could show
        if not v['players']:
            return ability == 'Librarian' and not any(g.registers_as(q) <= set(s.outsiders) for q in g.players)
        return any(v['character'] in g.registers_as(g[x]) for x in v['players'])
    what = {'Washerwoman': 'Townsfolk', 'Librarian': 'Outsider', 'Investigator': 'Minion'}[ability]
    return judged(Choice(f'{ability}:{p.name}', values, style), 'information',
                  f'Which two players, and which {what} character, is {p.name} ({ability}) shown?', recipient=p.name,
                  impaired=impaired, truth=shows)


def _pairs(ring, evil):
    return sum(1 for i in range(len(ring)) if ring[i].name in evil and ring[(i + 1) % len(ring)].name in evil)


def chef_choice(g, p):
    ring = g.players
    possible = set()
    for combo in product(*[sorted(g.registers_evil(q)) for q in ring]):
        possible.add(sum(1 for i in range(len(ring)) if combo[i] and combo[(i + 1) % len(ring)]))
    impaired = g.unreliable(p, 'Chef')
    values = range(0, 5) if impaired else sorted(possible)

    def style(r):
        if impaired and g.misinformed(p, r):
            return {'number': g.false_result(p, r, lambda r: _pairs(ring, g.false_evil(p, r)), possible)}
        return {'number': _pairs(ring, g.sample_evil(r))}
    return judged(Choice(f'Chef:{p.name}', [{'number': x} for x in values], style), 'information',
                  f'How many pairs of evil players sitting next to each other does {p.name} (Chef) learn?',
                  recipient=p.name, impaired=impaired, truth=lambda v: v['number'] in possible)


def empath_choice(g, p):
    nb = g.neighbours(p)
    possible = {sum(c) for c in product(*[sorted(g.registers_evil(q)) for q in nb])}
    impaired = g.unreliable(p, 'Empath')
    values = [0, 1, 2] if impaired else sorted(possible)

    def style(r):
        if impaired and g.misinformed(p, r):
            count = lambda r: sum(1 for q in nb if q.name in g.false_evil(p, r))
            return {'number': g.false_result(p, r, count, possible)}
        evil = g.sample_evil(r)
        return {'number': sum(1 for q in nb if q.name in evil)}
    return judged(Choice(f'Empath:{p.name}', [{'number': x} for x in values], style), 'information',
                  f'How many of their alive neighbours ({" and ".join(q.name for q in nb)}) does {p.name} (Empath) '
                  'learn are evil?', recipient=p.name, impaired=impaired,
                  truth=lambda v: v['number'] in possible)


def fortune_teller_choice(g, p, targets):
    ts = [g[t] for t in targets]
    possible = {any(c) for c in product(*[sorted(g.registers_demon_to_ft(q)) for q in ts])}
    impaired = g.unreliable(p, 'Fortune Teller')
    values = [True, False] if impaired else sorted(possible)

    def style(r):
        if impaired and g.misinformed(p, r):  # in the false world the framed player is the Demon
            def yes(r):
                framed, _ = g.decoy(p, r)
                recluse = any(g[t].character == 'Recluse' and r.random() < POLICY['recluse_evil'] for t in targets)
                herring = g.red_herring if p.character == 'Drunk' else None  # a poisoned FT's false world has none
                return recluse or any(t in (framed, herring) for t in targets)
            return {'yes': g.false_result(p, r, yes, possible)}
        if len(possible) == 1:
            return {'yes': next(iter(possible))}
        return {'yes': r.random() < POLICY['recluse_evil']}
    return judged(Choice(f'Fortune Teller:{p.name}', [{'yes': x} for x in values], style), 'information',
                  f'{p.name} (Fortune Teller) chose {" and ".join(targets)}: do they learn that one is the Demon (yes: '
                  'true)?', recipient=p.name, impaired=impaired, truth=lambda v: v['yes'] in possible,
                  players=list(targets))


def character_choice(g, p, ability, target):
    """Undertaker (executed player) and Ravenkeeper (chosen player)."""
    t = g[target]
    impaired = g.unreliable(p, ability)
    values = g.script.all if impaired else sorted(g.registers_as(t))

    def as_good(r):  # an evil player shown as a good character (usually a Demon bluff), never the recipient's
        for _ in range(30):
            c = g.fake_good(r, (g.script.townsfolk, g.script.outsiders))
            if c != p.shown:
                return c
        return c

    def style(r):
        if t is p:  # a Ravenkeeper who picks themselves learns what they think they are (a Drunk too)
            return {'character': p.shown}
        # "Imp" for an executed player is only consistent with the game going on if a Scarlet Woman
        # could have taken over (5+ alive at the execution)
        imp_ok = ability == 'Ravenkeeper' or g.alive_at_execution >= 5

        def false_world(r):  # what a working ability would show in the false world
            framed, evil = g.decoy(p, r)
            if t.name in evil:  # the framed player is the false world's Imp, the others its Minions
                return 'Imp' if t.name == framed and imp_ok else r.choice(g.minions_shown())
            if t.evil:  # the real evil player is good in the false world
                return as_good(r)
            if t.character == 'Recluse' and r.random() < POLICY['recluse_evil']:
                return g.evil_character(r, imp_ok)
            return t.character  # an unframed good player is who they are

        if impaired and g.misinformed(p, r):
            return {'character': g.false_result(p, r, false_world, set(g.registers_as(t)))}
        if t.character == 'Spy' and len(values) > 1 and r.random() > POLICY['spy_evil']:
            return {'character': as_good(r)}
        if t.character == 'Recluse' and len(values) > 1 and r.random() < POLICY['recluse_evil']:
            return {'character': g.evil_character(r, imp_ok)}
        return {'character': t.character}
    choice = Choice(f'{ability}:{p.name}', [{'character': c} for c in values], style)
    shows = set(g.registers_as(t))
    choice.truth = lambda v: v['character'] in shows
    return judged(choice, 'information', f'Which character does {p.name} ({ability}) learn {target} is?', about=target,
                  recipient=p.name, impaired=impaired)


def heir_choice(minions, demon=None):
    """Which living Minion becomes the Imp when the Imp kills themselves (no Scarlet Woman to take over)."""
    choice = Choice('starpass', [{'players': [m]} for m in minions], lambda r: {'players': [r.choice(minions)]})
    return judged(choice, 'starpass', f'The Demon{f" ({demon.name})" if demon else ""} killed themselves: which '
                                      f'living Minion ({", ".join(minions)}) becomes the new Demon?',
                  about=demon and demon.name)


def yes_choice(cid, chance):
    return Choice(cid, [{'yes': True}, {'yes': False}], lambda r: {'yes': r.random() < chance})


def virgin_choice(g, virgin, nominator):
    """Whether a nominator who may or may not register as a Townsfolk (the Spy) does so to the Virgin, and so is
    executed at once (POLICY 'spy_virgin')."""
    return judged(yes_choice(f'Virgin:{nominator.name}', POLICY['spy_virgin']), 'spy_virgin',
                  f'{nominator.name} (the {nominator.character}) nominated {virgin.name}, the Virgin (first '
                  f'nomination). Does {nominator.name} register as a Townsfolk (yes: true), and so is executed at '
                  'once?', about=nominator.name, recipient=virgin.name, helps='good')


def slayer_choice(g, slayer, target):
    """Whether the Slayer's shot kills a target who may or may not register as the Demon (the Recluse; POLICY
    'recluse_slain')."""
    return judged(yes_choice(f'Slayer:{target.name}', POLICY['recluse_slain']), 'recluse_slain',
                  f'{slayer.name}, the Slayer, shot {target.name} (the {target.character}). Does {target.name} '
                  'register as the Demon (yes: true), and so die?', about=target.name, recipient=slayer.name,
                  helps='evil')


def mayor_choice(g, mayor, imp):
    """Who dies when the Imp attacks a healthy Mayor: the Mayor, or someone else instead."""
    victims = [q.name for q in g.living() if q is not imp and not g.safe_from_demon(q)]
    others = [n for n in victims if n != mayor.name]
    good = [n for n in others if not g[n].evil]

    def style(r):
        if not others or r.random() >= POLICY['mayor_bounce']:
            return {'players': [mayor.name]}
        pool = good if good and r.random() >= POLICY['bounce_evil'] else others
        return {'players': [r.choice(pool)]}
    return judged(Choice(f'Mayor:{mayor.name}', [{'players': [x]} for x in victims], style), 'mayor_bounce',
                  f'The Demon ({imp.name}) attacked {mayor.name}, the Mayor, tonight. Who dies: the Mayor, or another '
                  'player instead?', about=mayor.name, recipient=mayor.name)


def only_false(choice):
    """`choice` limited to the values a working ability could not give (`choice.truth`), for information that must be
    false (the Vortox: "even if they are drunk or poisoned, it must be false"); the scripted style keeps its own picks
    when they are false. Unchanged if every value is false already, or none is (a result with no false value: the
    Storyteller has nothing false to give, so a true one stands)."""
    false = [v for v in choice.values if not choice.truth(v)]
    if not false or len(false) == len(choice.values):
        return choice
    keys = {_key(v) for v in false}

    def style(r):
        for _ in range(30):
            v = norm(choice.style(r))
            if _key(v) in keys:
                return v
        return r.choice(false)
    out = Choice(choice.id, false, style)
    out.truth, out.context = choice.truth, {**(choice.context or {}), 'false_only': True}
    return out


def madness_broken(evidence, must=True):
    """Whether the evidence (judge.madness_evidence) shows a player broke their madness: told to be mad about being
    `about` (must=True, the Cerenovus), they did not claim it aloud, or their latest claim heard was another
    character, or they denied it or said they were mad; told not to be (must=False, the Mutant), they claimed it or
    said they were mad. A floor for what no judgment is needed for (the rulebook: "If a player flat out says, 'I am
    mad,' ... that counts"; simply staying quiet is not an effort to convince the group)."""
    if evidence['confessed']:
        return True
    if not must:
        return bool(evidence['claimed'])
    return evidence['denied'] or not evidence['aloud'] or not evidence['latest_matches']


def madness_choice(g, p, about, must, evidence):
    """Whether `p` broke their madness about `about` (yes: they did). The scripted Storyteller goes by what was said
    aloud (madness_broken on `evidence`, the public record); a judge weighs effort, hints and, if it hears them,
    whispers."""
    broke = madness_broken(evidence, must)
    choice = Choice(f'Madness:{p.name}', [{'yes': True}, {'yes': False}], lambda r: {'yes': broke})
    it = being(g, about)
    what = (f'mad about being {it}: trying, sincerely, to convince the group they are {it}' if must
            else f'not mad about being {it}: not trying to convince anyone, aloud, in private or to you, that they '
                 f'are {it}')
    return judged(choice, 'madness', f'{p.name} must be {what}. Today, did they break their madness (yes: they did, '
                                     'and might be executed for it)? Judge their effort and intent, as with humour: a '
                                     'claim with no effort behind it, a hint or wink, a private confession you heard, '
                                     'or silence when asked all count against them.',
                  about=p.name, recipient=p.name, mad_about=about, must=must, since=evidence['since'],
                  after=evidence.get('after'))


def being(g, about):
    """'the Chef' for a character, 'an Outsider' for a character type (the Mutant's madness)."""
    return f'the {about}' if about in g.script.all else f'a{"n" if about[:1] in "AEIOU" else ""} {about}'


def madness_penalty_choice(g, p, about):
    """Whether the Storyteller executes `p`, who broke their madness ("might be executed"): usually for a good player
    (it is their choice), less often for an evil one, so evil can't use it to end the day."""
    chance = POLICY['mad_execute_evil' if p.evil else 'mad_execute_good']
    return judged(yes_choice(f'Madness execution:{p.name}', chance), 'madness_penalty',
                  f'{p.name} broke their madness about being {being(g, about)}. Do you execute them now (yes), which '
                  "is today's execution, or let it pass? Usually yes for a good player (their choice); for an evil "
                  'one, not if it would help evil (ending the day before a dangerous nomination).', about=p.name,
                  recipient=p.name, helps='good' if p.evil else 'evil')


def info_text(ability, value, target=None):
    """What the recipient is told."""
    v = norm(value)
    if ability in ('Washerwoman', 'Librarian', 'Investigator'):
        if not v['players']:
            return 'You learn that there are zero Outsiders in play.'
        a, b = v['players']
        return f'You learn that either {a} or {b} is the {v["character"]}.'
    if ability == 'Chef':
        return f'You learn that there {"is" if v["number"] == 1 else "are"} {v["number"]} pair{"" if v["number"] == 1 else "s"} of evil players sitting next to each other.'
    if ability == 'Empath':
        return f'You learn that {v["number"]} of your living neighbours {"is" if v["number"] == 1 else "are"} evil.'
    if ability == 'Fortune Teller':
        return f'You chose {target[0]} and {target[1]}: {"YES, one of them is the Demon." if v["yes"] else "NO, neither is the Demon."}'
    if ability == 'Undertaker':
        return f'You learn that the player executed today ({target}) was the {v["character"]}.'
    if ability == 'Ravenkeeper':
        return f'You learn that {target} is the {v["character"]}.'
    raise KeyError(ability)


# The Bad Moon Rising characters (bmr.py) register themselves in characters.CHARACTERS. They need this module and
# characters.py complete, so they load last, here: whichever of the two is imported first, both are done by now.
from . import bmr  # noqa: E402
from . import snv  # noqa: E402  (after bmr: Sects & Violets, clocktower/snv.py)
from . import carousel  # noqa: E402  (after snv: the experimental characters and jinxes, clocktower/carousel.py)

BMR, SNV, CAROUSEL = bmr, snv, carousel  # (a use, so pyflakes sees the imports are wanted)
