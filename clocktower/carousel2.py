"""Batch 2 of the experimental characters (the official data's "carousel" edition): the Pixie, High Priestess, Poppy
Grower, Shugenja, Balloonist, General, Preacher, Cannibal, Puzzlemaster, Heretic, Marionette, Widow, Goblin, Kazali
and Leviathan, and every official jinx between them and a built character.

As in carousel.py (batch 0 and 1, whose helpers and conventions this module shares): each entry follows the wiki's How
to Run, and where the rules leave a question open, a comment says which reading the entry takes, and why
(docs/carousel-rulings.md, batch 2, lists them for review). Each implemented jinx is declared at the end with `jinx`;
a jinx that changes another module's character is guarded there by `Script.jinxed`, so scripts without both
characters play as before.
"""
from __future__ import annotations
import re

from . import carousel, snv
from .characters import CHARACTERS, SETUPS, Choose, Demon, Minion, Outsider, Townsfolk, jinx, kind, rules, settle
from .state import POLICY, Choice, State, judged, madness_choice, yes_choice


# carousel.py and snv.py may still be loading when this module is (whichever of the engine's modules is imported
# first): their names are used through the modules, at call time.

def ability(name):
    """The official ability text."""
    from . import official
    return official.role(name)['ability']


def adjacent(g, a, b):
    """Whether players a and b sit next to each other (dead players count: seats, not living neighbours)."""
    n = len(g.players)
    return (a.seat - b.seat) % n in (1, n - 1)


def seat_neighbours(g, p):
    n = len(g.players)
    return [g.players[(p.seat - 1) % n], g.players[(p.seat + 1) % n]]


def evil_apart(g):
    """Whether the Minions and Demon still don't know each other (a Poppy Grower kept them apart at the start, and
    has not yet died or lost their ability: PoppyGrower.resolve_night)."""
    return bool(g.notes.get('Evil apart')) and not g.notes.get('Evil together')


def named_players(g, text):
    """The players named in `text` (whole words, any case), in seat order."""
    return [p.name for p in g.players if re.search(rf'\b{re.escape(p.name)}\b', text or '', re.I)]


def add_outsider(game, by):
    """A setup step's extra Outsider (the Balloonist's "+0 or +1"): a Townsfolk (not `by`) becomes an Outsider not in
    play, before anyone is told their character. Not the Drunk or the Lunatic, whose illusions are dealt with their
    setup, nor an Outsider only one of whose jinxed pair can be in play."""
    g = game.g
    in_play = {q.character for q in g.players}
    towns = [q.name for q in g.players if kind(q.character) == 'Townsfolk' and q is not by]
    pool = [c for c in g.script.outsiders if c not in in_play and not rules(c).always_drunk
            and not rules(c).wakes_at_own_step and not g.script.clash(in_play | {c})]
    if not (towns and pool):
        return False
    choice = judged(Choice('Extra Outsider', [{'players': [x], 'character': c} for x in towns for c in pool],
                           lambda r: {'players': [r.choice(towns)], 'character': r.choice(pool)}), 'extra_outsider',
                    f'An Outsider is added at setup ({by.shown}): which Townsfolk becomes which Outsider?')
    v = game.decide(choice)
    g.change_character(g[v['players'][0]], v['character'])
    return True


# ---- Townsfolk ---------------------------------------------------------------------------------------------------

def pixie_choice(g, p):
    """The in-play Townsfolk the Pixie learns: a Townsfolk character another player has now. Misinformed (drunk,
    poisoned, or under the Vortox): a Townsfolk on the script that nobody has."""
    in_play = [c for c in dict.fromkeys(q.character for q in g.players if q is not p)
               if kind(c) == 'Townsfolk' and c != 'Pixie']
    impaired = g.unreliable(p, 'Pixie')
    values = [c for c in g.script.townsfolk if c != 'Pixie'] if impaired else in_play
    if not values:
        return None

    def style(r):
        false = [c for c in values if c not in in_play]
        if impaired and g.misinformed(p, r) and false:
            return {'character': r.choice(false)}
        return {'character': r.choice(in_play or values)}
    return snv.info(Choice(f'Pixie:{p.name}', [{'character': c} for c in values], style), g, p, 'Pixie',
                    f'Which in-play Townsfolk does {p.name} (Pixie) learn (they must be mad that they are it)?',
                    lambda v: v['character'] in in_play, impaired)


class Pixie(Townsfolk):
    name = 'Pixie'
    ability = ability(name)
    info = True

    async def show(self, game, p):
        g = game.g
        choice = pixie_choice(g, p)
        if not choice:
            return
        v = await snv.learn(game, p, self.name, choice, lambda v: (
            f'the {v["character"]} is in play. If you are mad that you are the {v["character"]} (convincing the '
            'group of it), you gain their ability when they die.'))
        c = v['character']
        g.notes.setdefault('Pixie', {})[p.name] = c
        g.add(State('mad', p.name, source=p.name, until=None, about=c))  # (the reminder: no execution for breaking it)

    async def resolve_night(self, game, night):
        if night.first:
            for p in snv.believers(game.g, self.name):
                await self.show(game, p)

    async def becomes(self, game, me):
        if me.alive and not (game.tonight is not None and game.tonight.first):
            await self.show(game, me)

    def on_death(self, game, me, dead, cause, alive_before):
        # the player whose (true) character the Pixie was shown dies: if the Pixie has their ability now (alive,
        # sober, still the Pixie) and was mad about it, all game, they gain it (judged after the death)
        g = game.g
        c = g.notes.get('Pixie', {}).get(me.name)
        if c and dead is not me and dead.character == c and not dead.alive and self.name in g.abilities(me) \
                and c not in g.abilities(me):
            game.later(lambda game: self.gain(game, me, c))

    async def gain(self, game, me, c):
        g = game.g
        if not g.works(me, self.name):
            snv.failed(game, me, self.name, 'gained no ability')
            return
        from .judge import madness_evidence
        evidence = madness_evidence(game, me.name, c, 1)
        if (await game.decide_judged(madness_choice(g, me, c, True, evidence)))['yes']:
            return  # they broke their madness: no ability
        me.extra.append(c)
        game.emit('gains', {'player': me.name, 'character': c}, 'audit')
        game.inform(me, f'{snv.when(game)} — Pixie: the {c} has died, and you were mad that you were the {c}: you '
                        f'now have the {c}\'s ability: {rules(c).ability} (You are still the Pixie.)')
        await settle(rules(c).becomes(game, me))


def whispers_between(game, a, b):
    return sum(1 for ev in game.events if ev['kind'] == 'whisper' and {a, b} <= {ev['data']['from'],
                                                                              *ev['data'].get('to', ())})


def high_priestess_choice(game, p):
    """Whom the Storyteller believes the High Priestess should talk to most: the scripted heuristic is a living player
    of their own team (for a good one, a good player), most likely one with information (3x, POLICY
    'priestess_info_weight') and one they have whispered with least. A drunk or poisoned High Priestess may be
    pointed at anyone; misinformed (and under the Vortox, always), at a player of the other team."""
    g = game.g
    others = [q.name for q in g.players if q is not p]
    helpful = [x for x in others if g[x].evil == p.evil and g[x].alive]
    impaired = g.unreliable(p, 'High Priestess')
    values = others if impaired or not helpful else helpful

    def weight(x):
        w = POLICY['priestess_info_weight'] if rules(g[x].character).info or rules(g[x].shown).info else 1
        return w / (1 + whispers_between(game, p.name, x))

    def style(r):
        pool = values
        if impaired and g.misinformed(p, r):
            pool = [x for x in others if x not in helpful] or others
        else:
            pool = [x for x in values if x in helpful] or values
        return {'players': [r.choices(pool, [weight(x) for x in pool])[0]]}
    return snv.info(Choice(f'High Priestess:{p.name}', [{'players': [x]} for x in values], style), g, p,
                    'High Priestess', f'Which player do you believe {p.name} (High Priestess, {p.alignment}) should '
                    'talk to most? Someone whose talk would help them, ideally one they have not spoken with.',
                    lambda v: not helpful or v['players'][0] in helpful, impaired)


class HighPriestess(Townsfolk):
    name = 'High Priestess'
    ability = ability(name)
    info = True

    async def resolve_night(self, game, night):
        for p in snv.believers(game.g, self.name):
            await snv.learn(game, p, self.name, high_priestess_choice(game, p),
                            lambda v: f'the Storyteller believes you should talk to {v["players"][0]} most.')


class PoppyGrower(Townsfolk):
    name = 'Poppy Grower'
    ability = ability(name)
    setup_order = 8  # once every setup change is made

    @staticmethod
    def holds(g, me):
        """`me` has the Poppy Grower's ability now: alive, the Poppy Grower, sober and healthy."""
        return me.character == 'Poppy Grower' and me.alive and not g.impaired(me)

    def keeps_evil_apart(self, g, me):
        return self.holds(g, me)

    def setup(self, game):
        g = game.g
        if any(self.holds(g, q) for q in g.players):
            g.notes['Evil apart'] = True

    async def resolve_night(self, game, night):
        # "If you die, they learn who each other are that night": read as losing the ability (dying, or being drunk
        # or poisoned, or changed, at this step), checked at the Poppy Grower's step each night; a death by day is
        # learnt that night, one tonight after the step the next night. Once learnt, for good
        g = game.g
        if night.first or not evil_apart(g) or any(self.holds(g, q) for q in g.players):
            return
        g.notes['Evil together'] = night.n
        await evil_learns(game, night.n)


async def evil_learns(game, n):
    """The Minions learn the Demon, and the Demon its Minions (the Marionette named): the living ones, now."""
    g = game.g
    demons = [q for q in g.living() if q.is_demon]
    minions = [q for q in g.living() if kind(q.character) == 'Minion']
    for m in minions:
        if not rules(m.shown).evil:
            continue  # (the Marionette learns nothing)
        others = [q.name for q in minions if q is not m and rules(q.shown).evil]
        game.woken(m)
        game.inform(m, f'Night {n}: you learn who the other evil players are. The Demon is '
                       f'{" and ".join(d.name for d in demons) or "nobody"}.'
                       + (f' Your fellow Minions: {", ".join(others)}.' if others else ''))
    for d in demons:
        game.woken(d)
        lines = [f'Night {n}: you learn who your Minions are: {", ".join(q.name for q in minions) or "none"}.']
        lines += [f'{q.name} is the Marionette (they believe they are a good character).' for q in minions
                  if q.character == 'Marionette']
        game.inform(d, ' '.join(lines))


def closest_evil(g, p, evil):
    """The direction to the closest player in `evil` (True: clockwise), or None if equidistant (the dead count)."""
    n = len(g.players)

    def steps(step):
        return next((k for k in range(1, n) if g.players[(p.seat + step * k) % n].name in evil), n)
    cw, ac = steps(1), steps(-1)
    return None if cw == ac else cw < ac


def shugenja_choice(g, p):
    """Whether the Shugenja's closest evil player is clockwise (yes) or anticlockwise, counting seats (the dead
    included). An answer is true if some registration makes it so (a Spy may register good, a Recluse evil), and both
    are when the nearest evil players can be equidistant ("arbitrary"). Misinformed: the other way."""
    others = [q for q in g.players if q is not p]
    may = {q.name for q in others if True in g.registers_evil(q, p)}
    must = {q.name for q in others if g.registers_evil(q, p) == {True}}
    n = len(g.players)

    def steps(step, pool):
        return next((k for k in range(1, n) if g.players[(p.seat + step * k) % n].name in pool), n)
    cw_min, cw_max, ac_min, ac_max = steps(1, may), steps(1, must), steps(-1, may), steps(-1, must)
    true = {d for d, ok in ((True, cw_min <= ac_max), (False, ac_min <= cw_max)) if ok} or {True, False}
    impaired = g.unreliable(p, 'Shugenja')
    values = [True, False] if impaired else sorted(true, reverse=True)

    def style(r):
        world = g.sample_evil(r) - {p.name}
        way = closest_evil(g, p, world or may)
        way = r.random() < 0.5 if way is None else way
        if way not in true:
            way = next(iter(true))
        if impaired and g.misinformed(p, r):
            return {'yes': not way}
        return {'yes': way}
    return snv.info(Choice(f'Shugenja:{p.name}', [{'yes': x} for x in values], style), g, p, 'Shugenja',
                    f'Is the closest evil player to {p.name} (Shugenja) clockwise (yes) or anticlockwise (no)? If '
                    'equidistant, either.', lambda v: v['yes'] in true, impaired)


class Shugenja(Townsfolk):
    name = 'Shugenja'
    ability = ability(name)
    info = True

    async def show(self, game, p):
        await snv.learn(game, p, self.name, shugenja_choice(game.g, p),
                        lambda v: f'your closest evil player is {"clockwise" if v["yes"] else "anticlockwise"}.')

    async def resolve_night(self, game, night):
        if night.first:
            for p in snv.believers(game.g, self.name):
                await self.show(game, p)

    async def becomes(self, game, me):
        if me.alive and not (game.tonight is not None and game.tonight.first):
            await self.show(game, me)


TYPES = ('Townsfolk', 'Outsider', 'Minion', 'Demon')


def types_of(g, q, observer):
    return {kind(c) for c in g.registers_as(q, observer)}


def balloonist_choice(g, p, last):
    """The Balloonist's player: any other player (alive or dead) who can register as a character type other than
    `last`, the type shown last night (none on their first night). Misinformed: a player of the same type."""
    others = [q.name for q in g.players if q is not p]
    true = [x for x in others if types_of(g, g[x], p) - {last}]
    impaired = g.unreliable(p, 'Balloonist')
    values = others if impaired or not true else true

    def style(r):
        same = [x for x in others if last in types_of(g, g[x], p)] if last else []
        if impaired and g.misinformed(p, r) and same:
            return {'players': [r.choice(same)]}
        return {'players': [r.choice([x for x in values if x in true] or values)]}
    return snv.info(Choice(f'Balloonist:{p.name}', [{'players': [x]} for x in values], style), g, p, 'Balloonist',
                    f'Which player does {p.name} (Balloonist) learn: one of a different character type than last '
                    f'night\'s ({last or "none yet"})?', lambda v: v['players'][0] in true, impaired)


class Balloonist(Townsfolk):
    name = 'Balloonist'
    ability = ability(name)
    info = True
    outsider_choices = (0, 1)  # (for the setup checks; dealt by its setup step, not by state.random_setup)
    setup_order = -1  # the extra Outsider, before any other setup step

    async def setup(self, game):
        # "[+0 or +1 Outsider]": in a dealt game, the Storyteller adds one, half the time (POLICY
        # 'balloonist_outsider'), turning a Townsfolk into an Outsider not in play; a forced setup is kept as given
        g = game.g
        b = g.with_character(self.name)
        if b and not game.forced and game.decide(yes_choice('Balloonist outsider', POLICY['balloonist_outsider']))[
                'yes']:
            add_outsider(game, b)

    async def resolve_night(self, game, night):
        g = game.g
        for p in snv.believers(g, self.name):
            last = g.notes.setdefault('Balloonist', {}).get(p.name)
            v = await snv.learn(game, p, self.name, balloonist_choice(g, p, last),
                                lambda v: f'{v["players"][0]} is of a different character type than last night\'s.'
                                if last else f'you learn {v["players"][0]}.')
            q = g[v['players'][0]]
            shown = types_of(g, q, p) - {last} or {kind(q.character)}  # the type they were shown as
            g.notes['Balloonist'][p.name] = kind(q.character) if kind(q.character) in shown else \
                next(t for t in TYPES if t in shown)


def general_choice(game, p):
    """Which alignment the Storyteller believes is winning: the scripted heuristic is judge.standing (good or evil
    "well ahead", else neither). The belief is the Storyteller's, so a judge may answer otherwise for a sober General;
    a drunk or poisoned one is usually told another answer, and under the Vortox only another."""
    from .judge import standing
    g = game.g
    lead, why = standing(game)
    true = {'good': 'good', 'evil': 'evil'}.get(lead, 'neither')
    impaired = g.unreliable(p, 'General')
    values = ['good', 'evil', 'neither']

    def style(r):
        if impaired and g.misinformed(p, r):
            return {'statements': [r.choice([x for x in values if x != true])]}
        return {'statements': [true]}
    return judged(Choice(f'General:{p.name}', [{'statements': [x]} for x in values], style), 'information',
                  f'Which alignment do you believe is winning, as {p.name} (General) learns: good, evil or neither? '
                  f'The heuristic says {true} ({why}).', recipient=p.name, impaired=impaired, ability='General',
                  truth=(lambda v: v['statements'][0] == true) if impaired else None)


class General(Townsfolk):
    name = 'General'
    ability = ability(name)
    info = True

    async def resolve_night(self, game, night):
        for p in snv.believers(game.g, self.name):
            await snv.learn(game, p, self.name, general_choice(game, p),
                            lambda v: {'good': 'the Storyteller believes good is winning.',
                                       'evil': 'the Storyteller believes evil is winning.',
                                       'neither': 'the Storyteller believes neither team is winning.'}[
                                v['statements'][0]])


def preached(g, p):
    """Whether a working Preacher has chosen `p` (a Minion: they have no ability)."""
    return any(p.name in chosen and g.works(g[pr], 'Preacher') for pr, chosen in g.notes.get('Preached', {}).items())


class Preacher(Townsfolk):
    name = 'Preacher'
    ability = ability(name)
    derives = True
    night_choice = Choose(players=1, prompt='Choose a player: a Minion, if chosen, learns this, and has no ability.')

    async def resolve_night(self, game, night):
        g = game.g
        for p, t in snv.holders(g, night, self.name):
            if not t or kind(g[t].character) != 'Minion':
                continue  # (its true type: a Spy is a Minion, a Recluse is not)
            if not g.works(p, self.name):
                snv.failed(game, p, self.name, 'a Minion kept their ability')
                continue
            chosen = g.notes.setdefault('Preached', {}).setdefault(p.name, [])
            if t not in chosen:
                chosen.append(t)
            if rules(g[t].shown).evil:  # (a Marionette, who believes they are good, is not told: a reading)
                game.inform(g[t], f'Night {night.n}: the Preacher selected you. You have no ability.')

    def ongoing(self, g, me):
        # "All chosen Minions have no ability": while the Preacher has theirs (alive, sober and healthy), the players
        # they chose who are still Minions are treated as drunk, the engine's "no ability"
        if not g.works(me, self.name):
            return []
        return [State(k, x, source=me.name, until=None) for x in g.notes.get('Preached', {}).get(me.name, ())
                if kind(g[x].character) == 'Minion' for k in ('drunk', 'no ability')]


def cannibal_lie_choice(game, c, executed):
    """The Cannibal ate an evil player: the ability the Storyteller pretends they have (they are poisoned). Usually
    the good character the executee claimed aloud, else any good character on the script."""
    from .judge import claims
    g = game.g
    pool = [x for x in g.script.good if x != 'Cannibal']
    claim = claims(game, 'public').get(executed.name)

    def style(r):
        if claim in pool and r.random() < POLICY['cannibal_lie_claim']:
            return {'character': claim}
        towns = [x for x in pool if kind(x) == 'Townsfolk'] or pool
        return {'character': r.choice(towns)}
    return judged(Choice(f'Cannibal:{c.name}', [{'character': x} for x in pool], style), 'cannibal_lie',
                  f'The Cannibal ({c.name}) ate {executed.name}, who was evil ({executed.character}): the Cannibal is '
                  'poisoned. Which good ability do you pretend they have? Usually the one the executee claimed.',
                  about=executed.name, recipient=c.name)


class Cannibal(Townsfolk):
    name = 'Cannibal'
    ability = ability(name)

    def on_death(self, game, me, dead, cause, alive_before):
        # "the recently killed executee": the latest player killed by execution (not one who survived it); they are
        # what they were as they died. A good one: the Cannibal has their ability (and any Cannibal poison ends). An
        # evil one: the Cannibal is poisoned until a good player dies by execution, and the Storyteller pretends they
        # have a good ability (cannibal_lie_choice), which therefore never works
        g = game.g
        if cause != 'execution' or dead is me or not me.alive or me.character != self.name:
            return
        if dead.evil:
            g.add(State('poisoned', me.name, source=None, until=None, about='Cannibal'))
            me.extra = []
            game.later(lambda game: self.lie(game, me, dead))
            return
        g.states = [s for s in g.states if not (s.kind == 'poisoned' and s.about == 'Cannibal' and s.target == me.name)]
        me.extra = [dead.character]
        game.emit('gains', {'player': me.name, 'character': dead.character}, 'audit')
        game.later(lambda game: self.lunch(game, me, dead))

    async def lie(self, game, me, dead):
        if me.alive and me.character == self.name and not me.extra:
            me.extra = [(await game.decide_judged(cannibal_lie_choice(game, me, dead)))['character']]
            game.emit('gains', {'player': me.name, 'character': me.extra[0], 'lie': True}, 'audit')

    async def lunch(self, game, me, dead):
        g, c = game.g, dead.character
        if not (me.alive and c in me.extra):
            return
        if c == 'Butler' and g.script.jinxed(self.name, 'Butler'):  # the jinx: they learn it
            game.inform(me, f'{snv.when(game)}: you have gained the Butler\'s ability: {rules(c).ability}')
        record = g.notes.get('Juggler', {}).get(dead.name)
        if c == 'Juggler' and g.script.jinxed(self.name, 'Juggler') and record and record['day'] == game.day:
            # the jinx: the Juggler guessed on their first day and was executed: the Cannibal learns tonight
            g.notes.setdefault('Cannibal Juggler', {})[me.name] = record
        await settle(rules(c).becomes(game, me))  # a "you start knowing" ability acts now (as the Philosopher's)


# ---- Outsiders ---------------------------------------------------------------------------------------------------

def puzzle_drunk_choice(g, pm):
    """The Puzzlemaster's drunk: any other player, usually a good Townsfolk (POLICY 'puzzle_townsfolk')."""
    others = [q.name for q in g.players if q is not pm]
    towns = [x for x in others if kind(g[x].character) == 'Townsfolk' and not g[x].evil]

    def style(r):
        return {'players': [r.choice(towns if towns and r.random() < POLICY['puzzle_townsfolk'] else others)]}
    return judged(Choice(f'Puzzlemaster:{pm.name}', [{'players': [x]} for x in others], style), 'puzzle_drunk',
                  f'Which player is the Puzzlemaster\'s ({pm.name}) drunk, all game?', recipient=pm.name)


def puzzle_demon_choice(g, pm, right):
    """Whom the Puzzlemaster learns is the Demon. A right guess: a player who registers as the Demon; a wrong one:
    false information, a player who does not (surely) register as it. A drunk or poisoned Puzzlemaster may learn
    anyone."""
    others = [q.name for q in g.players if q is not pm]
    demons = [x for x in others if any(kind(c) == 'Demon' for c in g.registers_as(g[x], pm))]
    sure = [x for x in demons if all(kind(c) == 'Demon' for c in g.registers_as(g[x], pm))]
    impaired = g.impaired(pm)
    true = demons if right else [x for x in others if x not in sure]
    values = others if impaired or not true else true

    def style(r):
        if impaired and g.misinformed(pm, r):
            return {'players': [r.choice([x for x in others if x not in true] or others)]}
        real = [x for x in true if g[x].is_demon]
        return {'players': [r.choice(real if right and real else true or others)]}
    return snv.info(Choice(f'Puzzlemaster guess:{pm.name}', [{'players': [x]} for x in values], style), g, pm,
                    'Puzzlemaster', f'{pm.name} (Puzzlemaster) guessed {"right" if right else "wrong"}: which player '
                    'do they learn is the Demon (a wrong guess gets false information)?',
                    lambda v: v['players'][0] in true, impaired)


class Puzzlemaster(Outsider):
    name = 'Puzzlemaster'
    ability = ability(name)
    derives = True
    visit = True  # the guess, made in private by visiting the Storyteller (a reading)
    setup_order = 1.5

    @staticmethod
    def puzzle(g, me):
        return g.notes.get('Puzzle', {}).get(me.name)

    async def pick(self, game, me):
        g = game.g
        g.notes.setdefault('Puzzle', {})[me.name] = (await game.decide_judged(puzzle_drunk_choice(g, me)))[
            'players'][0]

    async def setup(self, game):
        pm = game.g.with_character(self.name)
        if pm:
            await self.pick(game, pm)

    async def becomes(self, game, me):
        await self.pick(game, me)  # a new Puzzlemaster (the Pit-Hag's, a Philosopher's) has a drunk of their own
        snv.fresh(game.g, me, self.name)

    def ongoing(self, g, me):
        # "1 player is drunk, even if you die": while they have the ability (dead too), sober and healthy; a drunk or
        # poisoned Puzzlemaster's player is sober meanwhile (a reading)
        x = self.puzzle(g, me)
        if not x or self.name not in g.abilities(me) or g.impaired(me):
            return []
        return [State('drunk', x, source=me.name, until=None)]

    async def visited(self, game, me, text):
        g = game.g
        if not (me.alive and snv.has(g, me, self.name)):
            return False
        if snv.used(g, me, self.name):
            game.inform(me, f'Day {game.day} — Puzzlemaster: you have already made your guess.')
            return True
        named = [x for x in named_players(g, text) if x != me.name]
        if len(named) != 1:
            game.inform(me, f'Day {game.day} — Puzzlemaster: to guess, name exactly one other player in your visit. '
                            '(Your guess is not spent.)')
            return True
        snv.use(g, me, self.name)  # once per game, drunk or not
        right = named[0] == self.puzzle(g, me)
        v = await game.decide_judged(puzzle_demon_choice(g, me, right))
        game.inform(me, f'Day {game.day} — Puzzlemaster: you guessed {named[0]}. The Storyteller shows you the '
                        f'Demon: {v["players"][0]}.')
        return True


class Heretic(Outsider):
    name = 'Heretic'
    ability = ability(name)
    flips_result = True

    def ended(self, g, me, winner, reason):
        # dead or alive, while they are the Heretic and sober; after every other end hook (the Politician's). Every
        # ending, the Saint's, the Damsel's and the Goblin's included
        if me.character != self.name or g.impaired(me):
            return None
        g.winner = 'evil' if winner == 'good' else 'good'
        return f'{reason} But {me.name} is the Heretic: whoever wins, loses, so {g.winner} wins.'


# ---- Minions -----------------------------------------------------------------------------------------------------

def marionette_as_choice(g, m):
    """The good character the Marionette believes they are: one nobody has or believes they have, usually a Townsfolk
    (POLICY 'marionette_townsfolk'), not one whose illusion needs its own setup (the Drunk, the Lunatic)."""
    taken = {q.character for q in g.players} | {q.shown for q in g.players}
    pool = [c for c in g.script.good if c not in taken and not rules(c).always_drunk and not rules(c).wakes_at_own_step]
    towns = [c for c in pool if kind(c) == 'Townsfolk']

    def style(r):
        group = towns if towns and r.random() < POLICY['marionette_townsfolk'] else pool
        return {'character': r.choices(group, [POLICY['drunk_info_weight'] if rules(c).info else 1 for c in group])[0]}
    return judged(Choice(f'Marionette:{m.name}', [{'character': c} for c in pool], style), 'marionette_as',
                  f'Which good character does the Marionette ({m.name}) believe they are?', recipient=m.name)


async def make_marionette(game, p, demon=None):
    """`p`, a good player, becomes the Marionette without knowing it (they keep believing their character, and turn
    evil); the Demon learns it (the Kazali's and Summoner's jinxes, the Plague Doctor's)."""
    g = game.g
    shown = p.shown
    g.change_character(p, 'Marionette')
    p.shown, p.alignment = shown, 'evil'
    game.emit('becomes', {'player': p.name, 'character': 'Marionette'}, 'audit')
    game.emit('alignment', {'player': p.name, 'alignment': 'evil'}, 'audit')
    demon = demon or g.demon()
    if demon and not evil_apart(g):
        game.inform(demon, f'{snv.when(game)}: {p.name} is now the Marionette (they believe they are still a good '
                           'character).')
    for q in g.players:
        for c in g.abilities(q):
            await settle(rules(c).changed(game, q, p))


async def marionette_enters(game, demon):
    """A Marionette waiting for a Demon (dealt with the Summoner) enters play beside it: one of the new Demon's good
    neighbours becomes the Marionette (the Storyteller's choice)."""
    g = game.g
    if not g.notes.pop('Marionette waiting', None):
        return
    pool = [q.name for q in seat_neighbours(g, demon) if not q.evil]
    if pool:
        x = (await game.decide_judged(carousel.player_choice(
            'Marionette enters', 'marionette_player', 'Which of the Demon\'s good neighbours becomes the Marionette?',
            pool, lambda r: {'players': [r.choice(pool)]})))['players'][0]
        await make_marionette(game, g[x], demon)


class Marionette(Minion):
    name = 'Marionette'
    ability = ability(name)
    always_drunk = True  # their apparent character's ability is the Storyteller's misinformation, as the Drunk's
    setup_order = 0.5  # after the Drunk's (so their apparent characters differ), before the red herring

    async def setup(self, game):
        g = game.g
        m = g.with_character(self.name)
        if not m:
            return
        demon = g.demon()
        if demon and not adjacent(g, m, demon):
            # [You neighbour the Demon]: the Marionette takes a seat beside the Demon (a swap of the dealt tokens)
            pool = [q.name for q in seat_neighbours(g, demon)]
            q = g[game.decide(Choice('Marionette seat', [{'players': [x]} for x in pool],
                                     lambda r: {'players': [r.choice(pool)]}))['players'][0]]
            for k in ('character', 'shown', 'alignment'):
                a, b = getattr(m, k), getattr(q, k)
                setattr(m, k, b)
                setattr(q, k, a)
            m = q
        m.shown = (await game.decide_judged(marionette_as_choice(g, m)))['character']
        if m.shown == 'Balloonist' and g.script.jinxed(self.name, 'Balloonist') and game.decide(yes_choice(
                'Balloonist outsider', POLICY['balloonist_outsider']))['yes']:
            add_outsider(game, m)  # the jinx: an Outsider might have been added for the Balloonist they believe in
        if not demon and g.script.jinxed(self.name, 'Summoner'):
            # the jinx: no Demon yet, so the Marionette enters play after it, beside it (marionette_enters): for now
            # this player is the good character they believe they are
            g.change_character(m, m.shown)
            m.alignment = 'good'
            g.notes['Marionette waiting'] = True

    def told_evil(self, game, me, viewer):
        g = game.g
        if not viewer.is_demon or me.character != self.name or evil_apart(g):
            return []
        magician = any(q.character == 'Magician' and q.alive for q in g.players)
        if magician and g.script.jinxed('Magician', self.name):  # the jinx: which neighbour, the Demon doesn't know
            a, b = seat_neighbours(g, viewer)
            return [f'One of your neighbours, {a.name} or {b.name}, is the Marionette (who believes they are a good '
                    'character).']
        return [f'{me.name} is the Marionette (they believe they are a good character).']


def widow_knower_choice(g, w):
    """The good player who learns a Widow is in play: any living good player, usually a Townsfolk."""
    good = [q.name for q in g.living() if not q.evil and q is not w]
    towns = [x for x in good if kind(g[x].character) == 'Townsfolk']

    def style(r):
        return {'players': [r.choice(towns if towns and r.random() < POLICY['grandchild_townsfolk'] else good)]}
    return judged(Choice(f'Widow knows:{w.name}', [{'players': [x]} for x in good], style), 'widow_knower',
                  'Which good player learns that a Widow is in play?', recipient=w.name)


class Widow(Minion):
    name = 'Widow'
    ability = ability(name)
    night_choice = Choose(players=1, prompt='You have seen the Grimoire. Choose a player: they are poisoned (for the '
                                            'rest of the game, while you have your ability).')

    @staticmethod
    def hidden(g):
        """The players whose tokens the Widow does not see (the Magician jinx: the Demon's and the Magician's)."""
        return ([p.name for p in g.players if p.is_demon or p.character == 'Magician']
                if g.script.jinxed('Magician', 'Widow') else ())

    def night_spec(self, game, me, night):
        # their 1st night only (the night order has no other step for the Widow: one made later does nothing). They
        # look at the Grimoire as they wake, before choosing; not while a Poppy Grower has their ability (the jinx)
        g = game.g
        if not night.first:
            return None
        blind = g.script.jinxed(self.name, 'Poppy Grower') and any(PoppyGrower.holds(g, q) for q in g.players)
        if not blind:
            game.inform(me, f'Night {night.n} — Widow: you look at the Grimoire.\n' + g.grimoire_text(
                hidden=self.hidden(g)))
        return self.night_choice

    async def resolve_night(self, game, night):
        g = game.g
        if not night.first:
            return
        for w in [q for q in g.players if q.alive and q.character == self.name and q.name in night.chosen]:
            t = (night.chosen[w.name] or [None])[0]
            if t and g.works(w, self.name):
                g.add(State('poisoned', t, source=w.name, until=None, ends_with_source=True))
            elif t:
                snv.failed(game, w, self.name, 'nobody poisoned')
            # the good player learns it, whatever the Widow's sobriety (a reading: it is true that a Widow is in play)
            choice = widow_knower_choice(g, w)
            if choice.values:
                x = (await game.decide_judged(choice))['players'][0]
                game.woken(g[x])
                game.inform(g[x], f'Night {night.n}: a Widow is in play.')
                g.reminders.append(f'{x} knows that a Widow is in play.')


class Goblin(Minion):
    name = 'Goblin'
    ability = ability(name)
    public_action = 'ability'  # the claim, aloud (or "I am the Goblin" in their words) while nominated

    def act_publicly(self, game, actor, target, text=None):
        return False  # (the claim is heard: Goblin.claimed reads it at the execution)

    @staticmethod
    def claimed(game, me):
        """Whether `me` publicly claimed to be the Goblin while nominated today: aloud (their defense, speech, or a
        claimed Goblin ability) from their first nomination today on."""
        from .judge import madness_evidence
        start = next((ev['seq'] for ev in game.events if ev['kind'] == 'nomination' and ev['day'] == game.day
                      and ev['data']['nominee'] == me.name), None)
        if start is None:
            return False
        return madness_evidence(game, me.name, 'Goblin', game.day, 'public', after=start)['aloud']

    def execution(self, game, me, executed):
        # executed (dying or not) the day they claimed; with the Goblin's ability then (a Minion who gained it, the
        # Plague Doctor jinx, too). Their team: their alignment
        g = game.g
        if executed is not me or not me.alive or not self.claimed(game, me):
            return None
        if not g.works(me, self.name):
            snv.failed(game, me, self.name, 'the claimed Goblin was executed')
            return None
        return me.alignment, f'{me.name} claimed to be the Goblin when nominated, and was executed: their team wins.'


# ---- Demons ------------------------------------------------------------------------------------------------------

def kazali_outsiders_choice(g, k):
    """The Kazali's "-? to +? Outsiders": how many Townsfolk become Outsiders (or Outsiders Townsfolk) at setup,
    before the Kazali chooses Minions; usually none (POLICY 'kazali_outsiders_same'), else one more or one fewer."""
    towns = [q for q in g.players if kind(q.character) == 'Townsfolk']
    outs = [q for q in g.players if kind(q.character) == 'Outsider']
    in_play = {q.character for q in g.players}
    free_out = [c for c in g.script.outsiders if c not in in_play and not rules(c).always_drunk
                and not rules(c).wakes_at_own_step]
    free_town = [c for c in g.script.townsfolk if c not in in_play]
    values = [0] + ([1] if towns[1:] and free_out else []) + ([-1] if outs and free_town else [])

    def style(r):
        return {'number': 0 if len(values) == 1 or r.random() < POLICY['kazali_outsiders_same'] else
                r.choice(values[1:])}
    return judged(Choice(f'Kazali outsiders:{k.name}', [{'number': x} for x in values], style), 'kazali_outsiders',
                  'The Kazali is in play: one Outsider more (1), one fewer (-1), or as dealt (0)?', recipient=k.name)


class Kazali(Demon):
    name = 'Kazali'
    ability = ability(name)
    night_choice = Choose(players=1, prompt='Choose a player: they die.')
    kills_at_night = True
    no_minions = True  # [You choose which players are which Minions]: none are dealt, Townsfolk in their seats
    setup_order = -2

    def intro(self, game, me):
        return ['Tonight you choose which players become which Minions.']

    async def setup(self, game):
        g = game.g
        k = g.with_character(self.name)
        if not k or game.forced:
            return
        d = (await game.decide_judged(kazali_outsiders_choice(g, k)))['number']
        if d > 0:
            add_outsider(game, k)
        elif d < 0:
            in_play = {q.character for q in g.players}
            outs = [q.name for q in g.players if kind(q.character) == 'Outsider']
            towns = [c for c in g.script.townsfolk if c not in in_play]
            v = game.decide(Choice('Kazali fewer outsiders', [{'players': [x], 'character': c} for x in outs
                                                               for c in towns],
                                   lambda r: {'players': [r.choice(outs)], 'character': r.choice(towns)}))
            g.change_character(g[v['players'][0]], v['character'])

    def night_spec(self, game, me, night):
        return None if night.first else self.night_choice

    async def resolve_night(self, game, night):
        if night.first:
            k = game.g.with_character(self.name)
            if k and not game.g.notes.get('Kazali chose'):
                await self.choose_minions(game, k, night)
            return
        g = game.g
        d, t = night.choice_of(g, self.name)
        if t and g.works(d, self.name):
            await game.demon_attack_judged(g[t], d, night)
        elif t and d:
            snv.failed(game, d, self.name, 'no attack')

    async def choose_minions(self, game, k, night):
        """The first night: the Kazali chooses, one at a time, as many players as the table has Minions, and which
        Minion (on the script, not in play) each becomes; they turn evil and are told. Whatever the Kazali's sobriety
        (it is setup). Not a Marionette unless the player neighbours the Kazali (the jinx), who then keeps believing
        their character; not a Minion whose jinx with a character in play lets only one be in play (the Heretic)."""
        g = game.g
        g.notes['Kazali chose'] = True
        made = []
        for i in range(SETUPS[len(g.players)][2]):
            options = [q.name for q in g.players if q is not k and not q.evil]
            in_play = {q.character for q in g.players}
            minions = [m for m in g.script.minions if m not in in_play and not g.script.clash(in_play | {m})]
            if not (options and minions):
                break
            note = ''
            for attempt in range(game.REASKS + 1):
                pool = minions if attempt < game.REASKS else [m for m in minions if m != 'Marionette'] or minions
                req = game.request('night', f'{note}Night {night.n} — Kazali: choose a player (`targets`) and a '
                                            f'Minion (`character`): they become that Minion, and evil ({i + 1} of '
                                            f'{SETUPS[len(g.players)][2]}).', night.n, n_targets=1, options=options,
                                   min_targets=1, characters=pool)
                a = await game.insist(k.name, req, await game.ask(k.name, req))
                t, m = game.targets(k.name, a, req)[0], a.get('character')
                if m in pool and (m != 'Marionette' or adjacent(g, g[t], k)):
                    break
                note = '(That is not a legal choice: the Marionette must neighbour you. This choice is required.) '
                m = None
            if m is None:
                break
            game.emit('night_choice', {'player': k.name, 'role': self.name, 'targets': [t], 'character': m}, 'audit')
            if m == 'Marionette':
                await make_marionette(game, g[t], k)
            else:
                await game.change(g[t], character=m, alignment='evil')
            made.append(t)
        game.woken(k)
        if not made or evil_apart(g):
            return
        knowing = [x for x in made if rules(g[x].shown).evil]
        for x in knowing:
            demon = game.evil_shown(g[x], [k.name], 'Demon')
            others = [y for y in knowing if y != x]
            game.inform(g[x], f'Night {night.n}: the Demon is {" or ".join(demon)}.'
                              + (f' Your fellow Minions: {", ".join(others)}.' if others else ''))


def leviathan_choice_jinxes(g):
    return [c for c in ('Banshee', 'Sage', 'Ravenkeeper') if g.script.jinxed('Leviathan', c)]


class Leviathan(Demon):
    name = 'Leviathan'
    ability = ability(name)

    def announce(self, game):
        game.emit('text', {'text': 'The Storyteller announces: the Leviathan is in play.'})

    def becomes(self, game, me):
        self.announce(game)  # "All players know you are in play": one made later too

    async def resolve_night(self, game, night):
        g = game.g
        lev = g.holder(self.name)
        if not lev:
            return
        if night.first:
            self.announce(game)
            return
        jinxes = leviathan_choice_jinxes(g)
        if not jinxes:
            return
        # the Banshee, Sage and Ravenkeeper jinxes: each night*, a living player not chosen before (the Leviathan
        # doesn't know who is good: choosing an evil player, or one with none of those characters, does nothing)
        before = g.notes.setdefault('Leviathan chose', [])
        options = [q.name for q in g.living() if q is not lev and q.name not in before]
        if not options:
            return
        req = game.request('night', f'Night {night.n} — Leviathan: choose a living good player you have not chosen '
                                    'before (`targets`).', night.n, n_targets=1, options=options, min_targets=1)
        t = g[game.targets(lev.name, await game.insist(lev.name, req, await game.ask(lev.name, req)), req)[0]]
        before.append(t.name)
        game.woken(lev)
        game.emit('night_choice', {'player': lev.name, 'role': self.name, 'targets': [t.name]}, 'audit')
        if not g.works(lev, self.name):
            snv.failed(game, lev, self.name, 'its choice did nothing')
            return
        c = t.character
        if c == 'Banshee' and 'Banshee' in jinxes and not t.evil:
            await game.attempt_kill_judged(t, 'demon', lev, night)  # "dies & gains their ability" (Banshee.on_death)
        elif c == 'Sage' and 'Sage' in jinxes and not t.evil:
            choice = snv.sage_choice(g, t, lev.name)
            if choice:
                await snv.learn(game, t, 'Sage', choice, lambda v: 'the Demon is {} or {}.'.format(
                    *sorted(v['players'], key=lambda x: g[x].seat)))
        elif c == 'Ravenkeeper' and 'Ravenkeeper' in jinxes:
            req = game.request('ravenkeeper', f'Night {night.n}: Ravenkeeper: the Leviathan chose you. Choose a '
                                              'player to learn their character (`targets`).', night.n, n_targets=1,
                               options=game.names)
            x = game.targets(t.name, await game.ask(t.name, req), req)[0]
            from .state import character_choice
            await game.tell(t, 'Ravenkeeper', character_choice(g, t, 'Ravenkeeper', x), x)

    @staticmethod
    def protected_last_night(game, executed):
        """Which jinx's protection the executed player had last night (the Exorcist's, Innkeeper's or Monk's choice,
        by a player with that ability now working), or None."""
        g = game.g
        last = g.night_choices.get(game.day, {})
        for c in ('Exorcist', 'Innkeeper', 'Monk'):
            if not g.script.jinxed('Leviathan', c):
                continue
            for p in g.players:
                if c in g.abilities(p) and executed.name in last.get(p.name, ()) and g.works(p, c):
                    return c
        return None

    def execution(self, game, me, executed):
        g = game.g
        if me.character != self.name or not me.alive:
            return None
        noms = [x for x in g.nominations if x['day'] == game.day and x['nominee'] == executed.name]
        if noms and noms[-1]['nominator'] == me.name and g.works(me, self.name):
            # the Exorcist, Innkeeper, Monk and Soldier jinxes: the Leviathan nominated and executes that player
            protector = self.protected_last_night(game, executed)
            if protector:
                return 'good', f'The Leviathan nominated and executed the {protector}-chosen player: good wins.'
            if executed.character == 'Soldier' and g.script.jinxed(self.name, 'Soldier'):
                return 'good', 'The Leviathan nominated and executed the Soldier: good wins.'
        if executed.evil:
            return None
        # "If more than 1 good player is executed": counted while a Leviathan is in play (executed, dying or not)
        count = g.notes.get('Good executed', 0) + 1
        g.notes['Good executed'] = count
        if count > 1 and g.works(me, self.name):
            return 'evil', 'A second good player was executed while the Leviathan is in play: evil wins.'
        return None

    def on_death(self, game, me, dead, cause, alive_before):
        # the Grandmother jinx: the Grandchild dies by execution while the Leviathan is in play
        g = game.g
        if cause == 'execution' and g.script.jinxed(self.name, 'Grandmother') and me.character == self.name \
                and dead.name == g.notes.get('Grandchild') and not g.winner:
            g.winner, g.reason = 'evil', 'The Grandchild died by execution while the Leviathan is in play: evil wins.'

    def end_of_day(self, game, me):
        # "After day 5, evil wins": at the end of day 5 (or of a later one, if the Leviathan was drunk or poisoned
        # then). The Mayor jinx: on day 5, with the Mayor and the Leviathan alive and no execution, good wins
        g = game.g
        if game.day < 5 or g.winner or me.character != self.name or not me.alive:
            return
        mayor = any(q.character == 'Mayor' and q.alive for q in g.players)
        if game.day == 5 and mayor and not game.executed_today and g.script.jinxed(self.name, 'Mayor'):
            g.winner, g.reason = 'good', ('Day 5 ended with the Mayor and the Leviathan alive and no execution: good '
                                          'wins.')
        elif g.works(me, self.name):
            g.winner, g.reason = 'evil', f'Day {game.day} has ended with the Leviathan alive: evil wins.'


def summoned_player_choice(g, s, demon):
    """The Summoner/Poppy Grower jinx: the Storyteller chooses whom the Summoner's Demon is: usually a living good
    player."""
    names = [q.name for q in g.players]
    return judged(Choice(f'Summoned player:{s.name}', [{'players': [x]} for x in names],
                         lambda r: {'players': [r.choice(carousel.living_good(g) or names)]}), 'summon_player',
                  f'The Poppy Grower is alive on the 3rd night: the Summoner ({s.name}) chose the {demon}, and you '
                  'choose which player becomes it.', recipient=s.name)


def leviathan_late(g):
    """The Hatter and Pit-Hag jinxes: "The Leviathan cannot enter play after day 5"."""
    return g.day > 5


CHARACTERS.update({c.name: c() for c in [Pixie, HighPriestess, PoppyGrower, Shugenja, Balloonist, General, Preacher,
                                         Cannibal, Puzzlemaster, Heretic, Marionette, Widow, Goblin, Kazali,
                                         Leviathan]})


# ---- Batch 2's jinxes (docs/carousel-rulings.md, batch 2) --------------------------------------------------------

jinx('Cannibal', 'Butler', 'carousel2.Cannibal.lunch')
jinx('Cannibal', 'Juggler', 'carousel2.Cannibal.lunch; snv.Juggler.resolve_night')
jinx('Cerenovus', 'Goblin', 'snv.Cerenovus.night_spec (Choose.also)')
for _x in ('Baron', 'Godfather', 'Pit-Hag', 'Spy', 'Widow'):
    jinx('Heretic', _x, 'characters.Script.clash: state.random_setup, setup_error; snv.PitHag; carousel tea party; '
                        'carousel2.Kazali')
for _x in ('Banshee', 'Sage', 'Ravenkeeper'):
    jinx('Leviathan', _x, 'carousel2.Leviathan.resolve_night')
for _x in ('Exorcist', 'Innkeeper', 'Monk', 'Soldier'):
    jinx('Leviathan', _x, 'carousel2.Leviathan.execution')
jinx('Leviathan', 'Grandmother', 'carousel2.Leviathan.on_death')
jinx('Leviathan', 'Mayor', 'carousel2.Leviathan.end_of_day')
jinx('Leviathan', 'Hatter', 'carousel.tea_party_options (carousel2.leviathan_late)')
jinx('Leviathan', 'Pit-Hag', 'snv.PitHag.resolve_night (carousel2.leviathan_late)')
jinx('Magician', 'Marionette', 'carousel2.Marionette.told_evil')
jinx('Magician', 'Widow', 'carousel2.Widow.hidden')
jinx('Marionette', 'Balloonist', 'carousel2.Marionette.setup, add_outsider')
jinx('Marionette', 'Kazali', 'carousel2.Kazali.choose_minions')
jinx('Marionette', 'Summoner', 'carousel2.Marionette.setup, marionette_enters; carousel.Summoner.summon')
jinx('Mathematician', 'Marionette', 'game.Game.note_information (always_drunk); characters.Slayer.act_publicly')
jinx('Plague Doctor', 'Goblin', 'carousel.PlagueDoctor.gain, minion_gains')
jinx('Plague Doctor', 'Marionette', 'carousel.PlagueDoctor.gain (carousel2.make_marionette)')
jinx('Spy', 'Poppy Grower', 'characters.Spy.resolve_night')
jinx('Summoner', 'Kazali', 'carousel.Summoner.summon')
jinx('Summoner', 'Poppy Grower', 'carousel.Summoner.resolve_night')
jinx('Summoner', 'Preacher', 'carousel.Summoner.resolve_night (carousel2.preached)')
jinx('Widow', 'Damsel', 'carousel.Damsel.ongoing')
jinx('Widow', 'Poppy Grower', 'carousel2.Widow.night_spec')
