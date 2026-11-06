"""Characters: one entry per character, holding everything the engine knows about it.

Each character is a class: its type, the ability text players are shown, and the hooks through which it acts
(its night step, how it registers, what happens when it dies, is nominated or executed, and so on). The game
loop and the Grimoire don't test character names: they ask the characters in play. A character that needs
nothing from a hook doesn't define it.

The official data (clocktower/data/official, via official.py) supplies each character's id, type, edition and
place in the universal night order; a script's night order is that order filtered to its characters. The
ability text is the protocol's own wording (the player prompt is part of the frozen protocol), which differs
from the official text in a few small ways (tests/test_characters.py lists them).

The Storyteller's choices (what an information role is shown, how a misregistering character registers) are
in state.py, as `Choice`s with the scripted style in `state.POLICY`; the hooks here build those choices and
apply the results.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from . import official

# Official setup by player count: (Townsfolk, Outsiders, Minions), plus one Demon. Setup modifiers (the Baron's
# "+2 Outsiders") turn Townsfolk into Outsiders.
SETUPS = {5: (3, 0, 1), 6: (3, 1, 1), 7: (5, 0, 1), 8: (5, 1, 1), 9: (5, 2, 1), 10: (7, 0, 2), 11: (7, 1, 2),
          12: (7, 2, 2), 13: (9, 0, 3), 14: (9, 1, 3), 15: (9, 2, 3)}


@dataclass(frozen=True)
class Choose:
    """What a character chooses at night, beyond Trouble Brewing's (count, prompt, may choose themselves) tuples."""
    players: int = 1          # how many players, at most (0 with character=True: only a character, the Courtier)
    prompt: str = ''
    may_self: bool = True
    optional: bool = False    # may choose no one (the Po, the Assassin)
    alive_only: bool = False  # only players who are alive (as the town sees it)
    not_last: bool = False    # not the player chosen last night (the Exorcist)
    character: bool = False   # a character too (the Gambler) or instead (the Courtier)


def choice_spec(c):
    """A character's night choice as a Choose, or None. Trouble Brewing's tuples keep their v17 meaning."""
    nc = c.night_choice
    if nc is None or isinstance(nc, Choose):
        return nc
    k, text, may_self = nc
    return Choose(players=k, prompt=text, may_self=may_self)


class Character:
    """A character with no ability the engine has to act on. Subclasses set what they need."""
    name = ''
    kind = ''                # 'Townsfolk', 'Outsider', 'Minion' or 'Demon'
    ability = ''             # the text players are shown
    info = False             # an information role (the Drunk believes they are one more often)
    remembered = False       # the Grimoire keeps what they were shown (pair abilities; the Spy sees it)
    night_choice = None      # a Choose (or TB's (count, prompt, may choose themselves)) if they choose at night
    kills_at_night = False   # night choices after this step are asked only once it has resolved
    public_action = None     # the move (schema field) through which anyone can claim this character's day action
    outsiders = 0            # setup modifier: Townsfolk turned into Outsiders (the Baron's +2)
    setup_order = None       # characters with a setup step run in this order
    misregisters = None      # the POLICY key for how often a working one registers as evil
    follows_master = False   # may vote only while their master votes (the Butler)
    always_drunk = False     # has no ability and doesn't know it (the Drunk)

    @property
    def evil(self):
        return self.kind in ('Minion', 'Demon')

    @property
    def id(self):
        return official.ids()[self.name]

    # ---- registration: the set of answers an ability could get about player `me` --------------------
    def registers_evil(self, g, me):
        return {me.evil}

    def registers_as(self, g, me):
        return {me.character}

    def registers_demon_to_ft(self, g, me):
        return {self.kind == 'Demon' or me.name == g.red_herring}

    def safe_from_demon(self, g, me):
        """Whether the Demon's attack cannot kill `me` because of their own ability."""
        return False

    def safe_from(self, g, me, cause):
        """Whether `me` can't die from `cause` ('demon', 'execution', ...) because of their own ability."""
        return cause == 'demon' and self.safe_from_demon(g, me)

    def protects(self, g, me, other, cause):
        """Whether `me`'s ability stops `other` dying from `cause` (a Tea Lady's good neighbours)."""
        return False

    def survives(self, game, me, cause):
        """`me` would die from `cause`: True if their ability saves them (the Fool, once). May spend it."""
        return False

    def dies(self, game, me, cause):
        """`me` dies: 'seems' if they live on but register as dead (the Zombuul, the first time), else None."""
        return None

    # ---- hooks --------------------------------------------------------------------------------
    def setup(self, game):
        """A setup step, run once the characters are dealt (in `setup_order`)."""

    async def resolve_night(self, game, night):
        """This character's step in tonight's night order (the night's choices were asked already)."""

    def information(self, game, me, night):
        """For an information role: (the Storyteller's Choice, the target named in the message), or None."""
        return None

    def redirect_attack(self, game, me, demon):
        """The player who dies when the Demon attacks `me` (the Mayor may bounce it), or None for `me`."""
        return None

    def on_death(self, game, me, dead, cause, alive_before):
        """Any player, `dead`, has just died; `me` is a player with this character."""

    def executed(self, game, me):
        """`me` is about to die by execution: (winner, reason) if that ends the game."""
        return None

    def nominated(self, game, me, nominator):
        """`me` was nominated: True if that ends the day (the Virgin)."""
        return False

    def end_of_day(self, game, me):
        """The day's nominations are over."""

    def act_publicly(self, game, actor, target):
        """`actor` publicly claims this character's day action on `target`: whether the target dies."""
        return False

    def card(self):
        return f'{self.name} ({self.kind}, {"evil" if self.evil else "good"} team): {self.ability}'


class Townsfolk(Character):
    kind = 'Townsfolk'


class Outsider(Character):
    kind = 'Outsider'


class Minion(Character):
    kind = 'Minion'


class Demon(Character):
    kind = 'Demon'


class InfoRole(Townsfolk):
    """A Townsfolk woken to learn something. Every living player who believes they are this character is told
    (the Drunk too: their information is the Storyteller's misinformation)."""
    info = True

    async def resolve_night(self, game, night):
        for p in game.g.players:
            if p.alive and p.shown == self.name:
                told = self.information(game, p, night)
                if told:
                    game.tell(p, self.name, *told)


# ---- Trouble Brewing ------------------------------------------------------------------------------------------

class Washerwoman(InfoRole):
    name = 'Washerwoman'
    ability = 'You start knowing that 1 of 2 players is a particular Townsfolk.'
    remembered = True

    def information(self, game, me, night):
        return state.pair_choice(game.g, me, self.name), None


class Librarian(InfoRole):
    name = 'Librarian'
    ability = 'You start knowing that 1 of 2 players is a particular Outsider. (Or that zero are in play.)'
    remembered = True

    def information(self, game, me, night):
        return state.pair_choice(game.g, me, self.name), None


class Investigator(InfoRole):
    name = 'Investigator'
    ability = 'You start knowing that 1 of 2 players is a particular Minion.'
    remembered = True

    def information(self, game, me, night):
        return state.pair_choice(game.g, me, self.name), None


class Chef(InfoRole):
    name = 'Chef'
    ability = 'You start knowing how many pairs of evil players there are (evil players sitting next to each other).'

    def information(self, game, me, night):
        return state.chef_choice(game.g, me), None


class Empath(InfoRole):
    name = 'Empath'
    ability = 'Each night, you learn how many of your 2 alive neighbours are evil.'

    def information(self, game, me, night):
        return state.empath_choice(game.g, me), None


class FortuneTeller(InfoRole):
    name = 'Fortune Teller'
    ability = ('Each night, choose 2 players: you learn if either is a Demon. '
               'There is a good player that registers as a Demon to you.')
    night_choice = (2, 'Choose two players: you learn whether either of them is the Demon.', True)
    setup_order = 1

    def setup(self, game):
        g = game.g
        if any(p.shown == self.name for p in g.players):  # the Drunk-as-Fortune-Teller too
            g.red_herring = game.decide(state.red_herring_choice(g))['players'][0]

    def information(self, game, me, night):
        chosen = night.chosen.get(me.name)
        return (state.fortune_teller_choice(game.g, me, chosen), chosen) if chosen else None


class Undertaker(InfoRole):
    name = 'Undertaker'
    ability = 'Each night*, you learn which character died by execution today.'

    def information(self, game, me, night):
        t = game.g.executed_death
        return (state.character_choice(game.g, me, self.name, t), t) if t else None


class Monk(Townsfolk):
    name = 'Monk'
    ability = 'Each night*, choose a player (not yourself): they are safe from the Demon tonight.'
    night_choice = (1, 'Choose a player (not yourself) to protect from the Demon tonight.', False)

    async def resolve_night(self, game, night):
        monk, t = night.choice_of(game.g, self.name)
        if t and game.g.works(monk, self.name):
            game.g.add(state.State('safe', t, source=monk.name, until='night'))


class Ravenkeeper(InfoRole):
    name = 'Ravenkeeper'
    ability = 'If you die at night, you are woken to choose a player: you learn their character.'

    async def resolve_night(self, game, night):
        for d in night.deaths:
            if d.shown == self.name:
                text = (f'Night {night.n}: you were killed in the night. Ravenkeeper: choose a player to learn their '
                        'character (`targets`).')
                req = game.request('ravenkeeper', text, night.n, n_targets=1, options=game.names)
                t = game.targets(d.name, await game.ask(d.name, req), req)[0]
                game.tell(d, self.name, state.character_choice(game.g, d, self.name, t), t)


class Virgin(Townsfolk):
    name = 'Virgin'
    ability = 'The 1st time you are nominated, if the nominator is a Townsfolk, they are executed immediately.'

    def nominated(self, game, me, nominator):
        g = game.g
        if g.spent_ability(self.name):
            return False
        g.spend(self.name)
        if not g.works(me, self.name):
            return False
        registers = {kind(c) == 'Townsfolk' for c in g.registers_as(g[nominator])}
        townsfolk = next(iter(registers))
        if len(registers) > 1:  # a misregistering nominator (the Spy) may or may not count as a Townsfolk
            townsfolk = game.decide(state.yes_choice(f'Virgin:{nominator}', state.POLICY['spy_virgin']))['yes']
        if not townsfolk:
            return False
        game.emit('virgin', {'nominator': nominator, 'nominee': me.name})
        game.execute(nominator)
        return True


class Slayer(Townsfolk):
    name = 'Slayer'
    ability = 'Once per game, during the day, publicly choose a player: if they are the Demon, they die.'
    public_action = 'slayer_shot'

    def act_publicly(self, game, actor, target):
        g = game.g
        s, t = g[actor], g[target]
        if not (s.alive and s.character == self.name and not g.spent_ability(self.name)):
            return False  # anyone can claim a shot; only a real, unused Slayer's does anything
        g.spend(self.name)
        if g.is_poisoned(s) or not t.alive:
            return False
        registers = {kind(c) == 'Demon' for c in g.registers_as(t)}
        if len(registers) > 1:  # a misregistering target (the Recluse) may or may not die
            return game.decide(state.yes_choice(f'Slayer:{t.name}', state.POLICY['recluse_slain']))['yes']
        return next(iter(registers))


class Soldier(Townsfolk):
    name = 'Soldier'
    ability = 'You are safe from the Demon.'

    def safe_from_demon(self, g, me):
        return g.works(me, self.name)


class Mayor(Townsfolk):
    name = 'Mayor'
    ability = ('If only 3 players live & no execution occurs, your team wins. '
               'If you die at night, another player might die instead.')

    def redirect_attack(self, game, me, demon):
        if game.g.works(me, self.name):
            return game.g[game.decide(state.mayor_choice(game.g, me, demon))['players'][0]]
        return None

    def end_of_day(self, game, me):
        g = game.g
        if not game.executed_today and g.alive_count() == 3 and g.works(me, self.name):
            g.winner, g.reason = 'good', 'Three players remain, there was no execution, and the Mayor lives.'


class Butler(Outsider):
    name = 'Butler'
    ability = 'Each night, choose a player (not yourself): tomorrow, you may only vote if they are voting too.'
    night_choice = (1, 'Choose your master (not yourself): tomorrow you may only vote if they vote too.', False)
    follows_master = True

    async def resolve_night(self, game, night):
        butler, t = night.choice_of(game.g, self.name)
        if butler and butler.alive and t:
            game.g.add(state.State('master', t, source=butler.name, until='night'))


class Drunk(Outsider):
    name = 'Drunk'
    ability = 'You do not know you are the Drunk. You think you are a Townsfolk character, but you are not.'
    always_drunk = True
    setup_order = 0  # before the red herring, which a Drunk-as-Fortune-Teller needs

    def setup(self, game):
        g = game.g
        drunk = g.with_character(self.name)
        if drunk:
            in_play = {p.character for p in g.players}
            options = [c for c in g.script.townsfolk if c not in in_play]
            drunk.shown = game.decide(state.drunk_as_choice(options))['character']


class Recluse(Outsider):
    name = 'Recluse'
    ability = 'You might register as evil & as a Minion or Demon, even if dead.'
    misregisters = 'recluse_evil'

    def registers_evil(self, g, me):
        return {me.evil} if g.is_poisoned(me) else {True, False}

    def registers_as(self, g, me):
        return {me.character} if g.is_poisoned(me) else {self.name, *g.script.minions, *g.script.demons}

    def registers_demon_to_ft(self, g, me):
        if me.name == g.red_herring:
            return {True}
        return {False} if g.is_poisoned(me) else {True, False}


class Saint(Outsider):
    name = 'Saint'
    ability = 'If you die by execution, your team loses.'

    def executed(self, game, me):
        if game.g.works(me, self.name):
            return 'evil', f'{me.name} was the Saint, and the Saint was executed.'
        return None


class Poisoner(Minion):
    name = 'Poisoner'
    ability = 'Each night, choose a player: they are poisoned tonight and tomorrow day.'
    night_choice = (1, 'Choose a player to poison tonight and tomorrow.', True)

    async def resolve_night(self, game, night):
        poisoner, t = night.choice_of(game.g, self.name)
        if t:  # the poison lasts while the Poisoner has their ability: it ends if they die or change character
            game.g.add(state.State('poisoned', t, source=poisoner.name, until='night', ends_with_source=True))


class Spy(Minion):
    name = 'Spy'
    ability = 'Each night, you see the Grimoire. You might register as good & as a Townsfolk or Outsider, even if dead.'
    misregisters = 'spy_evil'

    def registers_evil(self, g, me):
        return {me.evil} if g.is_poisoned(me) else {True, False}

    def registers_as(self, g, me):
        return {me.character} if g.is_poisoned(me) else {self.name, *g.script.townsfolk, *g.script.outsiders}

    async def resolve_night(self, game, night):
        spy = game.g.with_character(self.name)
        if spy and spy.alive:
            game.emit('info', {'text': f'Night {night.n} — Spy: you look at the Grimoire.\n'
                                       + game.g.grimoire_text()}, [spy.name])


class ScarletWoman(Minion):
    name = 'Scarlet Woman'
    ability = 'If there are 5 or more players alive & the Demon dies, you become the Demon.'

    def takes_over(self, g, me, alive_before):
        """Whether `me` becomes the Demon when it dies with `alive_before` players alive."""
        return g.works(me, self.name) and alive_before >= 5

    def on_death(self, game, me, dead, cause, alive_before):
        if dead.is_demon and cause != 'starpass' and self.takes_over(game.g, me, alive_before):
            game.g.change_character(me, dead.character)
            game.emit('becomes', {'player': me.name, 'character': dead.character}, 'audit')
            game.emit('notice', {'text': f'The Demon has died — and because you are the Scarlet Woman, you are '
                                         f'now the {dead.character}! From the next night you choose who dies.'},
                      [me.name])


class Baron(Minion):
    name = 'Baron'
    ability = 'There are extra Outsiders in play. [+2 Outsiders]'
    outsiders = 2


class Imp(Demon):
    name = 'Imp'
    ability = 'Each night*, choose a player: they die. If you kill yourself this way, a Minion becomes the Imp.'
    night_choice = (1, 'Choose a player to kill. (Choosing yourself kills you and makes one of your Minions the new '
                       'Imp.)', True)
    kills_at_night = True

    async def resolve_night(self, game, night):
        g = game.g
        imp, t = night.choice_of(g, self.name)
        if not (imp and t) or g.is_poisoned(imp):
            return
        target = g[t]
        if target is not imp:
            game.demon_attack(target, imp, night)
            return
        if imp.name == g.protected:  # a Monk-protected Imp cannot die, so no starpass
            return
        before = g.alive_count()
        game.kill(imp, 'starpass')
        night.deaths.append(imp)
        # a Minion who takes over the Demon (the Scarlet Woman) does; otherwise the Storyteller picks a living Minion
        living = [q for q in g.living() if kind(q.character) == 'Minion']
        heir = next((q for q in living if getattr(rules(q.character), 'takes_over', None)
                     and rules(q.character).takes_over(g, q, before)), None)
        if heir is None and living:
            heir = g[game.decide(state.heir_choice([q.name for q in living]))['players'][0]]
        if heir:
            g.change_character(heir, self.name)  # a Poisoner's poison ends when they stop being the Poisoner
            game.emit('becomes', {'player': heir.name, 'character': self.name}, 'audit')
            game.emit('notice', {'text': f'Night {night.n}: the Imp killed themselves, and you are now the Imp! '
                                         'From tomorrow night you choose who dies.'}, [heir.name])


# Every character the engine implements, by name (any script draws from these).
CHARACTERS = {c.name: c() for c in [Washerwoman, Librarian, Investigator, Chef, Empath, FortuneTeller, Undertaker, Monk,
                                     Ravenkeeper, Virgin, Slayer, Soldier, Mayor, Butler, Drunk, Recluse, Saint,
                                     Poisoner, Spy, ScarletWoman, Baron, Imp]}


def rules(character):
    """The entry for a character name."""
    return CHARACTERS[character]


def kind(character):
    return CHARACTERS[character].kind


def is_evil_character(character):
    return CHARACTERS[character].evil


def card(character):
    return CHARACTERS[character].card()


class Script:
    """A script: its characters by type (in the script's order, which random setups draw from), its night order
    (the official universal order filtered to its characters) and its characters' setup steps and public actions.
    `source` is a built-in script id ('tb', 'bmr') or a path to a script JSON in the official format."""

    def __init__(self, source='tb'):
        self.id = Path(str(source)).stem
        self.name, names = official.script(source)
        missing = [n for n in names if n not in CHARACTERS]
        if missing:
            raise ValueError(f'{self.name}: characters not implemented yet: {", ".join(missing)}')
        by = {k: [n for n in names if kind(n) == k] for k in ('Townsfolk', 'Outsider', 'Minion', 'Demon')}
        self.townsfolk, self.outsiders, self.minions, self.demons = (by[k] for k in by)
        self.all = self.townsfolk + self.outsiders + self.minions + self.demons
        self.good = self.townsfolk + self.outsiders
        self.first_night = official.night_order(self.all, True)
        self.other_nights = official.night_order(self.all, False)
        steps = [rules(n) for n in self.all if rules(n).setup_order is not None]
        self.setup_steps = sorted(steps, key=lambda c: c.setup_order)
        self.public_actions = {rules(n).public_action: rules(n) for n in self.all if rules(n).public_action}
        # Trouble Brewing asks night choices in batches (protocol v17); other scripts wake one character at a time,
        # since their steps depend on earlier ones (the Lunatic before the Demon, the Exorcist's target, the Goon)
        self.batched_night = self.id == 'tb'

    @classmethod
    def of(cls, name, characters, first_night=(), other_nights=()):
        """A script built in code from implemented characters, with its night order given (tests; characters
        not in the official data)."""
        s = cls.__new__(cls)
        s.id, s.name = name, name
        by = {k: [n for n in characters if kind(n) == k] for k in ('Townsfolk', 'Outsider', 'Minion', 'Demon')}
        s.townsfolk, s.outsiders, s.minions, s.demons = (by[k] for k in by)
        s.all = s.townsfolk + s.outsiders + s.minions + s.demons
        s.good = s.townsfolk + s.outsiders
        s.first_night, s.other_nights = list(first_night), list(other_nights)
        s.setup_steps = sorted((rules(n) for n in s.all if rules(n).setup_order is not None),
                               key=lambda c: c.setup_order)
        s.public_actions = {rules(n).public_action: rules(n) for n in s.all if rules(n).public_action}
        s.batched_night = False
        return s

    def __repr__(self):
        return f'Script({self.id!r})'

    def __eq__(self, other):
        return isinstance(other, Script) and other.all == self.all

    def __hash__(self):
        return hash(tuple(self.all))

    def sheet(self):
        """The character sheet every player and the Storyteller sees."""
        lines = []
        for title, group in [('Townsfolk (good)', self.townsfolk), ('Outsiders (good)', self.outsiders),
                             ('Minions (evil)', self.minions), ('Demon (evil)', self.demons)]:
            lines.append(f'{title}:')
            lines += [f'- {c}: {rules(c).ability}' for c in group]
        lines.append('(* = not on the first night)')
        return '\n'.join(lines)


# Trouble Brewing, the default script (protocol v17). The lists below are its; code written for TB uses them.
TB = Script('tb')
TOWNSFOLK, OUTSIDERS, MINIONS, DEMONS = TB.townsfolk, TB.outsiders, TB.minions, TB.demons
ALL, GOOD = TB.all, TB.good
INFO_ROLES = {n for n in TB.all if rules(n).info}
ABILITY = {n: c.ability for n, c in CHARACTERS.items()}
# Night order (official): "*" abilities (Monk, Imp, Undertaker) have no first-night step.
FIRST_NIGHT, OTHER_NIGHTS = TB.first_night, TB.other_nights
SETUP_STEPS, PUBLIC_ACTIONS = TB.setup_steps, TB.public_actions


def script_text():
    """Trouble Brewing's character sheet."""
    return TB.sheet()


# The hooks build the Storyteller's choices in state.py, which itself imports the lists above: import it last.
from . import state  # noqa: E402
