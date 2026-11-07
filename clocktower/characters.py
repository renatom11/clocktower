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
import inspect
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
    dead_only: bool = False   # only players who are dead (as the town sees it: the Professor)
    not_last: bool = False    # not the player chosen last night (the Exorcist)
    character: bool = False   # a character too (the Gambler) or instead (the Courtier)
    kinds: tuple = ()         # the character types that may be named (the Cerenovus's good characters); () any
    also: tuple = ()          # characters that may be named beyond those types (the Cerenovus/Goblin jinx's Goblin)


async def settle(result):
    """A hook's result: hooks that consult the Storyteller judge are coroutines (they await Game.decide_judged), the
    others return at once."""
    return (await result) if inspect.isawaitable(result) else result


def now(coro):
    """Run a coroutine that never waits to its end, synchronously: a judged hook with no judge (or the rules judge),
    for the synchronous entry points kept for tests and callers outside the game loop. A judge that must wait (a
    model's) needs the async path, which the game loop always takes."""
    try:
        coro.send(None)
    except StopIteration as done:
        return done.value
    coro.close()
    raise RuntimeError('a judged decision had to wait: use the async variant (the game loop does)')


def choice_spec(c, nc=None):
    """A character's night choice (or `nc`, one its night_spec gave) as a Choose, or None. Trouble Brewing's tuples
    keep their v17 meaning."""
    nc = c.night_choice if nc is None else nc
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
    public_action = None     # the move through which anyone can claim this character's day action: its own
    #                          schema field ('slayer_shot', protocol v17) or the shared 'ability' field
    outsiders = 0            # setup modifier: Townsfolk turned into Outsiders (the Baron's +2)
    outsider_choices = ()    # or the Storyteller picks one of these when dealing (the Godfather: -1 or +1)
    outsider_policy = None   # the POLICY key for how often the largest choice is dealt (else uniform)
    wakes_after = ()         # characters whose night step must come before this one's (moves this one after them)
    setup_order = None       # characters with a setup step run in this order
    misregisters = None      # the POLICY key for how often a working one registers as evil
    follows_master = False   # may vote only while their master votes (the Butler)
    always_drunk = False     # has no ability and doesn't know it (the Drunk)
    wakes_at_own_step = False  # woken at this character's own step, as the character they believe they are, and
    #                            not at that character's (the Lunatic, as their Demon, before the real one wakes)
    picks_in_turn = False    # its night step reports each player it chose (Game.pick) as it acts on them, since a
    #                          pick can stop the later ones (the Shabaloth choosing the Goon first)
    derives = False          # its ability puts states in force that are worked out from the Grimoire whenever they
    #                          are asked about (`ongoing`: the No Dashii's poisoned neighbours, recomputed)
    falsifies_info = False   # its ability can make other players' information false (`falsifies`: the Vortox)
    visit = False            # its ability is used by visiting the Storyteller in private by day (the Savant, the
    #                          Artist): anyone may claim a visit on a private-time turn (`visited` answers it)
    public_guesses = 0       # its public day ability takes up to this many (player, character) guesses (the
    #                          Juggler's 5), passed to `act_publicly` as `guesses`
    no_demon = False         # setup modifier: no Demon is dealt, a Townsfolk in its place (the Summoner's [No Demon])
    no_minions = False       # setup modifier (a Demon's): no Minions are dealt, Townsfolk in their place (the Kazali)
    flips_result = False     # its end hook turns the result around, so it runs after every other one (the Heretic)

    @property
    def evil(self):
        return self.kind in ('Minion', 'Demon')

    @property
    def id(self):
        return official.ids()[self.name]

    # ---- registration: the set of answers an ability could get about player `me` --------------------
    # (each takes the observer too: registration may differ by who is looking, and by check)
    def registers_evil(self, g, me, observer=None):
        return {me.evil}

    def registers_as(self, g, me, observer=None):
        return {me.character}

    def registers_demon_to_ft(self, g, me, observer=None):
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
    # setup, redirect_attack, nominated, nomination, act_publicly, moment, becomes and changed may be coroutines
    # (async def) when they make a Storyteller's call through Game.decide_judged; the game loop awaits them
    # (characters.settle).
    def night_spec(self, game, me, night):
        """What `me`, who believes they are this character, is woken to choose tonight: `night_choice`, a choice of
        another shape (the Po's three after choosing no one) or None not to wake them (the Zombuul when someone died
        today, a spent Assassin). Asked before tonight's choice is recorded, so `g.last_choices` is last night's."""
        return self.night_choice

    def setup(self, game):
        """A setup step, run once the characters are dealt (in `setup_order`)."""

    def intro(self, game, me):
        """Lines added to `me`'s introduction before the first night (the Lunatic's Demon information)."""
        return []

    def chosen(self, game, me, chooser, night):
        """`me` was just chosen by `chooser`, woken tonight to use their ability (the Goon makes the first one
        drunk). Called for each player chosen, in order, before the chooser's ability acts on them."""

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

    async def before_execution(self, game, me, executed):
        """Player `executed` is about to be executed: a decision the execution needs, made now (the Pacifist's)."""

    async def resurrected(self, game, me, night):
        """`me` came back to life tonight through an ability that wakes a "you start knowing" ability again (the
        Professor's): use it now."""

    def executed(self, game, me):
        """`me` is about to die by execution: (winner, reason) if that ends the game."""
        return None

    def nominated(self, game, me, nominator):
        """`me` was nominated: True if that ends the day (the Virgin)."""
        return False

    def end_of_day(self, game, me):
        """The day's nominations are over."""

    def act_publicly(self, game, actor, target, text=None):
        """`actor` publicly claims this character's day action (on `target`, with `text`, such as the Gossip's
        statement; with `public_guesses`, also `guesses`, a list of {player, character}: the Juggler's). Anyone may
        claim it; it does something only for a real, working one. Returns whether the target dies at once (the
        Slayer's shot)."""
        return False

    def visited(self, game, me, text):
        """With `visit`: `me` visited the Storyteller in private claiming this character's ability, saying `text`
        (the Artist's question). If they have it, or believe they do, the Storyteller answers them privately and this
        returns True; otherwise False (a pretend visit: the town saw a visit, nothing happens)."""
        return False

    def hand_over(self, g, old, new):
        """This character passes from player `old` to player `new` in one change (a swap: the Snake Charmer's, the
        Barber's). Returns the States that belong to the character rather than its player, taken out of the Grimoire
        (and moves its own bookkeeping); Game.changes puts them back with `new` as their source once the change is
        made, so they are not lost with the old player (the Vigormortis's dead Minions keep their abilities)."""
        return []

    def moment(self, game, me, when):
        """A point of the day when the Storyteller may act for this character: 'dawn', 'beat' (after each beat),
        'nominations' (before they open) or 'dusk' (after them). The Tinker may die at any of them."""

    def ongoing(self, g, me):
        """With `derives`: the States `me`'s ability puts in force now, worked out from the Grimoire each time they
        are asked about, so they follow every change at once (the No Dashii's two nearest Townsfolk are poisoned;
        when one becomes an Outsider, the next Townsfolk is). Placed states are in `g.states`; these are not."""
        return []

    def falsifies(self, g, me, recipient, ability):
        """With `falsifies_info`: whether `me`'s ability makes the information `recipient` gets from `ability` false
        (the Vortox: every Townsfolk's), so the Storyteller may give only false values (Game.decide_judged)."""
        return False

    def nomination(self, game, me, nominator, nominee):
        """Any player just nominated (after the nominee's own reaction, the Virgin's); `me` has this ability (the
        Witch's curse kills a cursed nominator; the nomination still stands)."""

    def execution(self, game, me, executed):
        """Player `executed` is being executed (dying or not), just before they die: (winner, reason) if that ends
        the game for `me`'s ability (the Evil Twin's good twin), else None. The executed player's own character
        answers through `executed`."""
        return None

    def becomes(self, game, me):
        """`me` has just become this character mid-game (Game.change: the Pit-Hag's, a Demon's jump), and been told:
        what the new character needs now (a new Evil Twin is paired with a twin)."""

    def changed(self, game, me, other):
        """Player `other`'s character or alignment has just changed (Game.change); `me` has this ability (an Evil
        Twin whose twin turned to their side gets a new twin)."""

    def overrides_end(self, g, me, winner, reason):
        """The game would end with `winner` for `reason`: None to let it, False to keep it going (the Mastermind's
        extra day), or a different (winner, reason)."""
        return None

    def ended(self, g, me, winner, reason):
        """The game has ended with `winner` for `reason` (no override kept it going): a new reason if `me`'s ability
        acts now (the Politician changes alignment), else None."""
        return None

    # ---- hooks of the experimental characters (all no-ops by default, so other scripts play as before) ----------
    def nomination_limit(self, g, me):
        """How many nominations `me` may make today, or None for the usual rule (one, while alive): the Banshee's
        two, even dead; a Golem who has nominated, none."""
        return None

    def vote_weight(self, g, me):
        """How many votes `me`'s raised hand counts as (the Banshee's two)."""
        return 1

    def free_vote(self, g, me):
        """Whether `me` may vote while dead without spending their ghost vote (the Banshee)."""
        return False

    def shown_to_evil(self, g, me, viewer):
        """How `me` appears in `viewer`'s first-night evil information: 'Minion' (in the Demon's list of Minions),
        'Demon' (pointed out to the Minions as the Demon), or None (as their character: the Magician's illusion)."""
        return None

    def told_evil(self, game, me, viewer):
        """Lines added to the first-night information of `viewer`, an evil player, because `me` is in play (the
        Minions learn a Damsel is in play)."""
        return []

    def keeps_evil_apart(self, g, me):
        """Whether `me`'s ability stops the Minions and Demon learning each other at the start (the Poppy Grower)."""
        return False

    async def storyteller_step(self, game, night, character):
        """At `character`'s step tonight, the Storyteller uses `character`'s ability, gained through `me`'s (the
        Plague Doctor's): Game.night calls this for each ability in g.notes['Storyteller abilities']."""

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
        for p in game.g.players:  # (and a player who gained the ability: the Pixie's, the Cannibal's)
            if p.alive and (p.shown == self.name or self.name in getattr(p, 'extra', ())):
                told = self.information(game, p, night)
                if told:
                    await game.tell(p, self.name, *told)


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

    async def setup(self, game):
        g = game.g
        if any(p.shown == self.name for p in g.players):  # the Drunk-as-Fortune-Teller too
            g.red_herring = (await game.decide_judged(state.red_herring_choice(g)))['players'][0]

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
                await game.tell(d, self.name, state.character_choice(game.g, d, self.name, t), t)


class Virgin(Townsfolk):
    name = 'Virgin'
    ability = 'The 1st time you are nominated, if the nominator is a Townsfolk, they are executed immediately.'

    async def nominated(self, game, me, nominator):
        g = game.g
        if g.spent_ability(self.name):
            return False
        g.spend(self.name)
        if not g.works(me, self.name):
            return False
        registers = {kind(c) == 'Townsfolk' for c in g.registers_as(g[nominator])}
        townsfolk = next(iter(registers))
        if len(registers) > 1:  # a misregistering nominator (the Spy) may or may not count as a Townsfolk
            townsfolk = (await game.decide_judged(state.virgin_choice(g, me, g[nominator])))['yes']
        if not townsfolk:
            return False
        game.emit('virgin', {'nominator': nominator, 'nominee': me.name})
        game.execute(nominator)
        return True


class Slayer(Townsfolk):
    name = 'Slayer'
    ability = 'Once per game, during the day, publicly choose a player: if they are the Demon, they die.'
    public_action = 'slayer_shot'

    async def act_publicly(self, game, actor, target, text=None):
        g = game.g
        s, t = g[actor], g[target]
        if not (s.alive and s.character == self.name and not g.spent_ability(self.name)):
            if (s.alive and s.shown == self.name and rules(s.character).always_drunk and t.alive and t.is_demon
                    and g.script.jinxed('Mathematician', s.character) and not g.notes.get(f'Drunk shot:{s.name}')):
                g.notes[f'Drunk shot:{s.name}'] = True  # the Mathematician jinx: a Drunk's shot at the Demon
                game.abnormal(s, self.name, 'shot the Demon, who did not die')
            return False  # anyone can claim a shot; only a real, unused Slayer's does anything
        g.spend(self.name)
        if g.is_poisoned(s) or not t.alive:
            return False
        registers = {kind(c) == 'Demon' for c in g.registers_as(t)}
        if len(registers) > 1:  # a misregistering target (the Recluse) may or may not die
            return (await game.decide_judged(state.slayer_choice(g, s, t)))['yes']
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

    async def redirect_attack(self, game, me, demon):
        if game.g.works(me, self.name):
            return game.g[(await game.decide_judged(state.mayor_choice(game.g, me, demon)))['players'][0]]
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

    async def setup(self, game):
        g = game.g
        drunk = g.with_character(self.name)
        if drunk:
            in_play = {p.character for p in g.players}
            options = [c for c in g.script.townsfolk if c not in in_play]
            drunk.shown = (await game.decide_judged(state.drunk_as_choice(options, drunk)))['character']

    # The Mathematician jinx (custom scripts): the Drunk's ability "failed to work properly" when the Townsfolk they
    # believe they are would have done something. Their false information counts through Game.note_information; these
    # are the other cases the engine can see (docs/carousel-rulings.md, 7). Without the jinx none is recorded.
    @staticmethod
    def jinxed(g):
        return g.script.jinxed('Mathematician', 'Drunk')

    def on_death(self, game, me, dead, cause, alive_before):
        night = game.tonight
        if cause != 'demon' or not self.jinxed(game.g):
            return
        if (dead is me and me.shown == 'Soldier') or (me.shown == 'Monk' and night is not None and me.alive
                                                     and dead.name in (night.chosen.get(me.name) or ())):
            game.abnormal(me, me.shown, 'the Demon killed a player this ability would have kept safe')

    def nominated(self, game, me, nominator):
        g = game.g
        if me.shown == 'Virgin' and self.jinxed(g) and not g.notes.get(f'Drunk Virgin:{me.name}'):
            g.notes[f'Drunk Virgin:{me.name}'] = True  # the first nomination only, as the Virgin's
            if kind(g[nominator].character) == 'Townsfolk':
                game.abnormal(me, 'Virgin', 'a Townsfolk nominated them and was not executed')
        return False


class Recluse(Outsider):
    name = 'Recluse'
    ability = 'You might register as evil & as a Minion or Demon, even if dead.'
    misregisters = 'recluse_evil'

    def registers_evil(self, g, me, observer=None):
        return {me.evil} if g.is_poisoned(me) else {True, False}

    def registers_as(self, g, me, observer=None):
        return {me.character} if g.is_poisoned(me) else {self.name, *g.script.minions, *g.script.demons}

    def registers_demon_to_ft(self, g, me, observer=None):
        if me.name == g.red_herring:
            return {True}
        return {False} if g.is_poisoned(me) else {True, False}


class Saint(Outsider):
    name = 'Saint'
    ability = 'If you die by execution, your team loses.'

    async def before_execution(self, game, me, executed):
        """Player `executed` is about to be executed: a decision the execution needs, made now (the Pacifist's)."""

    async def resurrected(self, game, me, night):
        """`me` came back to life tonight through an ability that wakes a "you start knowing" ability again (the
        Professor's): use it now."""

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
        # the poison lasts while the Poisoner has their ability: it ends if they die or change character; none from
        # a Poisoner with no ability (custom scripts: one the Preacher chose)
        if t and not game.g.has(poisoner, 'no ability'):
            game.g.add(state.State('poisoned', t, source=poisoner.name, until='night', ends_with_source=True))


class Spy(Minion):
    name = 'Spy'
    ability = 'Each night, you see the Grimoire. You might register as good & as a Townsfolk or Outsider, even if dead.'
    misregisters = 'spy_evil'

    def registers_evil(self, g, me, observer=None):
        return {me.evil} if g.is_poisoned(me) else {True, False}

    def registers_as(self, g, me, observer=None):
        return {me.character} if g.is_poisoned(me) else {self.name, *g.script.townsfolk, *g.script.outsiders}

    async def resolve_night(self, game, night):
        g = game.g
        # the Magician jinx (custom scripts): the Demon's and the Magician's tokens are removed from what the Spy sees
        hidden = ([p.name for p in g.players if p.is_demon or p.character == 'Magician']
                  if g.script.jinxed(self.name, 'Magician') else ())
        spy = g.with_character(self.name)
        if g.script.jinxed(self.name, 'Poppy Grower') and any(  # the jinx (custom scripts): no Grimoire while a
                rules('Poppy Grower').holds(g, q) for q in g.players):  # Poppy Grower has their ability
            return
        if spy and spy.alive:
            game.emit('info', {'text': f'Night {night.n} — Spy: you look at the Grimoire.\n'
                                       + g.grimoire_text(hidden=hidden)}, [spy.name])
        for p in g.players:  # a Minion who gained the Spy's ability (the Plague Doctor jinx: carousel.PlagueDoctor)
            if p.alive and p.character != self.name and self.name in getattr(p, 'extra', ()):
                game.emit('info', {'text': f'Night {night.n} — Spy: you look at the Grimoire.\n'
                                           + g.grimoire_text(hidden=hidden)}, [p.name])


class ScarletWoman(Minion):
    name = 'Scarlet Woman'
    ability = 'If there are 5 or more players alive & the Demon dies, you become the Demon.'

    def takes_over(self, g, me, alive_before):
        """Whether `me` becomes the Demon when it dies with `alive_before` players alive."""
        return g.works(me, self.name) and alive_before >= 5

    def on_death(self, game, me, dead, cause, alive_before):
        # a Demon that only seems to die (the Zombuul's first death: it lives on, registering as dead) has not died
        if dead.is_demon and not dead.alive and cause != 'starpass' and self.takes_over(game.g, me, alive_before):
            two = game.g.script.jinxed(self.name, 'Fang Gu') or game.g.script.jinxed(self.name, 'Al-Hadikhia')
            if two and any(q.is_demon and q.alive and q is not dead and q is not me for q in game.g.players):
                return  # the Fang Gu and Al-Hadikhia jinxes: there would be two Demons, so she stays the Scarlet Woman
            if game.g.script.jinxed(self.name, 'Al-Hadikhia'):  # (so a second Demon later turns her back: carousel)
                game.g.notes.setdefault('Was Scarlet Woman', []).append(me.name)
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
            await game.demon_attack_judged(target, imp, night)
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
            heir = g[(await game.decide_judged(state.heir_choice([q.name for q in living], imp)))['players'][0]]
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


def after(order):
    """The night order with each character that must wake after another (Character.wakes_after) moved to just after
    it, when both are on the script (the Lunatic after the Exorcist, so an exorcised Lunatic doesn't wake)."""
    order = list(order)
    for c in list(order):
        for other in rules(c).wakes_after:
            if other in order and order.index(other) > order.index(c):
                order.remove(c)
                order.insert(order.index(other) + 1, c)
    return order


class Script:
    """A script: its characters by type (in the script's order, which random setups draw from), its night order
    (the official universal order filtered to its characters) and its characters' setup steps and public actions.
    `source` is a built-in script id ('tb', 'bmr') or a path to a script JSON in the official format.

    A custom script may also list Travellers, Fabled and Loric (`travellers`, `fabled`, `loric`, by name, homebrew
    ones included): they are kept, noted on the character sheet as not in play, and never dealt or woken, since this
    engine runs none of them. Every Townsfolk, Outsider, Minion and Demon must be built (an official one in
    `CHARACTERS`; a homebrew one never is), or loading says which are not."""

    def __init__(self, source='tb'):
        self.id = Path(str(source)).stem
        loaded = official.script_entries(source)
        self.name = loaded['name']
        entries = loaded['entries']
        missing = [e['name'] if e['official'] else f"{e['name']} (homebrew: {e['id']})" for e in entries
                   if e['type'] in official.PLAYER_TYPES and not (e['official'] and e['name'] in CHARACTERS)]
        if missing:
            raise ValueError(f'{self.name}: characters not implemented yet: {", ".join(missing)}')
        names = [e['name'] for e in entries if e['type'] in official.PLAYER_TYPES]
        self.travellers, self.fabled, self.loric = ([e['name'] for e in entries if e['type'] == k]
                                                    for k in ('Traveller', 'Fabled', 'Loric'))
        self._build(names, after(official.night_order(names, True)), after(official.night_order(names, False)))
        # Trouble Brewing asks night choices in batches (protocol v17); other scripts wake one character at a time,
        # since their steps depend on earlier ones (the Lunatic before the Demon, the Exorcist's target, the Goon)
        self.batched_night = self.id == 'tb'
        # official jinxes between this script's characters (none within Trouble Brewing)
        self.jinxes = {pair: text for pair, text in official.jinxes().items() if set(pair) <= set(self.all)}

    def _build(self, characters, first_night, other_nights):
        by = {k: [n for n in characters if kind(n) == k] for k in ('Townsfolk', 'Outsider', 'Minion', 'Demon')}
        self.townsfolk, self.outsiders, self.minions, self.demons = (by[k] for k in by)
        self.all = self.townsfolk + self.outsiders + self.minions + self.demons
        self.good = self.townsfolk + self.outsiders
        self.first_night, self.other_nights = first_night, other_nights
        steps = [rules(n) for n in self.all if rules(n).setup_order is not None]
        self.setup_steps = sorted(steps, key=lambda c: c.setup_order)
        self.public_actions = {rules(n).public_action: rules(n) for n in self.all
                               if rules(n).public_action not in (None, 'ability')}
        self.claimable = [n for n in self.all if rules(n).public_action == 'ability']  # via the 'ability' field
        self.derivers = [n for n in self.all if rules(n).derives]  # characters with states worked out on demand
        self.falsifiers = [n for n in self.all if rules(n).falsifies_info]  # characters that can falsify information
        self.visitable = [n for n in self.all if rules(n).visit]  # abilities used by visiting the Storyteller
        self.guessable = [n for n in self.all if rules(n).public_guesses]  # public abilities that take guesses

    @classmethod
    def of(cls, name, characters, first_night=(), other_nights=(), jinxes=()):
        """A script built in code from implemented characters, with its night order given (tests; characters
        not in the official data). `jinxes`: pairs of its characters whose official jinx is in effect, or a
        {pair: text} for jinxes of its own."""
        s = cls.__new__(cls)
        s.id, s.name = name, name
        s.travellers, s.fabled, s.loric = [], [], []
        s._build(list(characters), after(list(first_night)), after(list(other_nights)))
        s.batched_night = False
        texts = jinxes if isinstance(jinxes, dict) else {tuple(p): official.jinxes()[tuple(p)] for p in jinxes}
        s.jinxes = {}
        for (a, b), text in texts.items():
            s.jinxes[(a, b)] = s.jinxes[(b, a)] = text
        return s

    def exclusive(self, a, b):
        """Whether the jinx between `a` and `b` says only one of them can be in play (the Heretic's with the Spy)."""
        return self.jinxes.get((a, b), '').startswith('Only 1 jinxed character')

    def clash(self, characters):
        """A pair of `characters` that the script's jinxes say cannot both be in play, or None."""
        return next(((a, b) for a, b in self.jinxes if a in characters and b in characters and self.exclusive(a, b)),
                    None)

    def jinxed(self, a, b):
        """Whether the jinx between characters `a` and `b` is in effect: both are on this script and a jinx between
        them is (an official one, or one given to Script.of). A jinx applies whenever both are on the script, in play
        or not; the code a jinx changes asks this and then checks the situation the jinx describes."""
        return (a, b) in self.jinxes

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
        for title, group in [('Travellers', self.travellers), ('Fabled', self.fabled), ('Loric', self.loric)]:
            if group:  # listed by the script, but this engine runs none of them
                lines.append(f'{title} (not in play in this engine): {", ".join(group)}')
        seen = set()
        for (a, b), text in self.jinxes.items():  # each pair once
            if (b, a) not in seen:
                seen.add((a, b))
                lines.append(f'Jinx, {a} and {b}: {text}')
        return '\n'.join(lines)


# The jinxes the engine implements, {frozenset((a, b)): where}: each is declared with `jinx` (in carousel.py, which
# lists them all), and its code asks Script.jinxed. tests/test_carousel.py checks every official jinx between two built
# characters is here.
IMPLEMENTED_JINXES = {}


def jinx(a, b, where):
    """Declare that the official jinx between characters `a` and `b` is implemented, by the code at `where`."""
    if (a, b) not in official.jinxes():
        raise ValueError(f'no official jinx between {a} and {b}')
    IMPLEMENTED_JINXES[frozenset((a, b))] = where


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
from . import state  # noqa: E402  (state.py, once loaded, loads the Bad Moon Rising characters: see its end)
