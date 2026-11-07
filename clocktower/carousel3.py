"""Batch 3a of the experimental characters (the official data's "carousel" edition): the Village Idiot, Acrobat,
Lycanthrope, Alchemist, Zealot, Organ Grinder (together with built characters, the Carousel Script Collection's Monkey
Do Math), Noble, Farmer, Harpy, Boffin, Boomdandy, Fearmonger and Xaan, and every official jinx between them and a
built character. Lil' Monsta is left out: its Demon is a token passed between Minions, not a character (the design the
brief keeps for the owner with the Legion, Riot and Atheist; docs/carousel-rulings.md, batch 3).

As in carousel.py and carousel2.py (whose helpers and conventions this module shares): each entry follows the wiki's
How to Run, and where the rules leave a question open, a comment says which reading the entry takes, and why
(docs/carousel-rulings.md, batch 3, lists them for review). Each implemented jinx is declared at the end with `jinx`;
a jinx that changes another module's character is guarded there by `Script.jinxed`, so scripts without both
characters play as before.
"""
from __future__ import annotations
from itertools import combinations
import re

from . import carousel, carousel2, snv
from .characters import CHARACTERS, Choose, Minion, Outsider, Townsfolk, jinx, kind, rules
from .state import POLICY, Choice, State, judged, yes_choice


# carousel.py, carousel2.py and snv.py may still be loading when this module is (whichever of the engine's modules is
# imported first): their names are used through the modules, at call time.

def ability(name):
    """The official ability text."""
    from . import official
    return official.role(name)['ability']


def ask_yes(game, p, n, text):
    """`p`'s yes/no choice (in `vote`), asked again while missing; a seat that never answers stops the game."""
    async def go():
        from .llm import SeatFailed
        req = game.request('decide', text, n)
        for _ in range(game.REASKS + 1):
            a = await game.ask(p.name, req)
            if isinstance(a.get('vote'), bool):
                return a['vote']
            req = game.request('decide', '(Your choice was missing: set `vote` to true or false.) ' + text, n)
        raise SeatFailed(f'{p.name}: no answer to a required choice after {game.REASKS} reminders')
    return go()


def remove_outsider(game, by):
    """A setup step's Outsider fewer (the Alchemist-Godfather's -1): an Outsider (not `by`) becomes a Townsfolk not in
    play, keeping a Townsfolk not in play for a Drunk to believe. Returns whether one was removed."""
    g = game.g
    in_play = {q.character for q in g.players}
    outs = [q.name for q in g.players if kind(q.character) == 'Outsider' and q is not by]
    drunk = any(rules(q.character).always_drunk and kind(q.character) == 'Outsider' for q in g.players)
    towns = [c for c in g.script.townsfolk if c not in in_play]
    if not outs or not towns[drunk:]:
        return False
    towns = towns[:len(towns) - drunk] if drunk else towns
    v = game.decide(Choice('Fewer outsiders', [{'players': [x], 'character': c} for x in outs for c in towns],
                           lambda r: {'players': [r.choice(outs)], 'character': r.choice(towns)}))
    g.change_character(g[v['players'][0]], v['character'])
    return True


def outsiders(g):
    return sum(1 for q in g.players if kind(q.character) == 'Outsider')


# ---- Townsfolk ---------------------------------------------------------------------------------------------------

def village_idiot_choice(g, p, t):
    """The alignment the Village Idiot learns of `t`: what they can register as (a Spy may register good, a Recluse
    evil). Drunk (the extra one), poisoned or under the Vortox: either; misinformed, the other."""
    true = g.registers_evil(g[t], p)
    impaired = g.unreliable(p, 'Village Idiot')
    values = [True, False] if impaired else sorted(true)

    def style(r):
        evil = t in g.sample_evil(r) if len(true) > 1 else next(iter(true))
        if impaired and g.misinformed(p, r):
            return {'yes': not evil}
        return {'yes': evil if evil in true or impaired else next(iter(true))}
    return snv.info(Choice(f'Village Idiot:{p.name}', [{'yes': x} for x in values], style), g, p, 'Village Idiot',
                    f'{p.name} (Village Idiot) chose {t}: do they learn {t} is evil (yes) or good (no)?',
                    lambda v: v['yes'] in true, impaired, about=t)


def extra_idiots_choice(g, towns):
    """[+0 to +2 Village Idiots]: which Townsfolk become extra Village Idiots (POLICY 'idiot_extra_one', '_two')."""
    values = [list(c) for k in range(min(2, len(towns)) + 1) for c in combinations(towns, k)]

    def style(r):
        x = r.random()
        k = 2 if x < POLICY['idiot_extra_two'] else 1 if x < POLICY['idiot_extra_two'] + POLICY['idiot_extra_one'] \
            else 0
        return {'players': r.sample(towns, min(k, len(towns)))}
    return judged(Choice('Village Idiot extras', [{'players': v} for v in values], style), 'idiot_extras',
                  'The Village Idiot is in play: which Townsfolk (none, one or two) become extra Village Idiots?')


def drunk_idiot_choice(g, idiots):
    return judged(Choice('Village Idiot drunk', [{'players': [x]} for x in idiots],
                         lambda r: {'players': [r.choice(idiots)]}), 'idiot_drunk',
                  f'Several Village Idiots ({", ".join(idiots)}): which one is drunk all game?')


class VillageIdiot(Townsfolk):
    name = 'Village Idiot'
    ability = ability(name)
    info = True
    derives = True
    duplicates = 3  # the one dealt and up to two extras
    setup_order = -0.5  # after the Outsider changes (Kazali, Alchemist, Balloonist, Xaan), before the Drunk's
    night_choice = Choose(players=1, prompt='Choose a player: you learn their alignment.')

    async def setup(self, game):
        # in a dealt game the Storyteller adds 0-2 extras, Townsfolk who become Village Idiots before anyone is told
        # their character; a forced setup keeps the ones given. With two or more, one (the Storyteller's choice, the
        # dealt one included: they are alike) is drunk all game, as the Drunk is
        g = game.g
        if not any(q.character == self.name for q in g.players):
            return
        if not game.forced:
            towns = [q.name for q in g.players if kind(q.character) == 'Townsfolk' and q.character != self.name
                     and not (rules(q.character).setup_order or 0) < -1]  # (not the Alchemist: its step has run)
            for x in (await game.decide_judged(extra_idiots_choice(g, towns)))['players']:
                g.change_character(g[x], self.name)
        await self.mark_drunk(game)

    async def mark_drunk(self, game, again=False):
        g = game.g
        idiots = [q.name for q in g.players if q.character == self.name]
        if len(idiots) >= 2 and (again or not g.notes.get('Village Idiot drunk')):
            g.notes['Village Idiot drunk'] = (await game.decide_judged(drunk_idiot_choice(g, idiots)))['players'][0]

    def ongoing(self, g, me):
        if g.notes.get('Village Idiot drunk') == me.name and me.character == self.name:
            return [State('drunk', me.name, source=None, until=None)]
        return []

    async def resolve_night(self, game, night):
        g = game.g
        for p in snv.believers(g, self.name):
            t = (night.chosen.get(p.name) or [None])[0]
            if t:
                await snv.learn(game, p, self.name, village_idiot_choice(g, p, t),
                                lambda v: f'you chose {t}: they are {"evil" if v["yes"] else "good"}.')


class Acrobat(Townsfolk):
    name = 'Acrobat'
    ability = ability(name)
    night_choice = Choose(players=1, prompt='Choose a player: if they are or become drunk or poisoned tonight, you '
                                            'die.')

    def night_spec(self, game, me, night):
        return None if night.first else self.night_choice

    async def resolve_night(self, game, night):
        g = game.g
        for p, t in snv.holders(g, night, self.name):
            if t:
                g.notes.setdefault('Acrobat', {})[p.name] = (night.n, t)
                self.check(game, p, night)

    def check(self, game, me, night):
        # "are or become ... tonight": checked at the Acrobat's step and again once tonight's steps are done, while
        # the Acrobat has a working ability then (a poisoned Acrobat's ability does nothing, even on themself)
        g = game.g
        n, t = g.notes.get('Acrobat', {}).get(me.name, (None, None))
        if n != night.n or not me.alive or not g.impaired(g[t]):
            return
        if not g.works(me, self.name):
            snv.failed(game, me, self.name, 'did not die')
            return
        g.notes['Acrobat'][me.name] = (None, t)  # (once)
        game.attempt_kill(me, 'acrobat', me, night)

    def end_of_night(self, game, me, night):
        self.check(game, me, night)


def faux_paw_choice(g, lyc):
    """The good player who registers as evil (the Faux Paw): any other good player, usually a Townsfolk."""
    good = [q.name for q in g.players if not q.evil and q is not lyc]

    def spoils(x):  # (a Noble with no three players left, exactly one evil: a 5-player table, docs U9)
        nobles = [q for q in g.players if 'Noble' in (q.shown, *g.abilities(q))]
        return any(not any(sum(1 for y in t if g[y].evil or y == x) == 1
                           for t in combinations([q.name for q in g.players if q is not p], 3)) for p in nobles)
    safe = [x for x in good if not spoils(x)] or good
    towns = [x for x in safe if kind(g[x].character) == 'Townsfolk']

    def style(r):
        return {'players': [r.choice(towns if towns and r.random() < POLICY['grandchild_townsfolk'] else safe)]}
    return judged(Choice(f'Faux Paw:{lyc.name}', [{'players': [x]} for x in good], style), 'faux_paw',
                  'The Lycanthrope is in play: which good player registers as evil?', recipient=lyc.name)


class Lycanthrope(Townsfolk):
    name = 'Lycanthrope'
    ability = ability(name)
    kills_at_night = True
    setup_order = 7.5
    night_choice = Choose(players=1, alive_only=True, prompt='Choose a living player: if they are good, they die, '
                                                             'and the Demon does not kill tonight.')

    def night_spec(self, game, me, night):
        return None if night.first else self.night_choice

    async def paw(self, game, me):
        # "One good player registers as evil": chosen at setup (or when one becomes the Lycanthrope), to every ability
        # and the Lycanthrope's own, while the Lycanthrope has their ability (alive, sober and healthy: a reading)
        g = game.g
        if not me.alive:
            return  # (a dead player made the Lycanthrope: the Barber's swap) has no ability to give it
        choice = faux_paw_choice(g, me)
        if choice.values:
            x = (await game.decide_judged(choice))['players'][0]
            g.add(State('registers evil', x, source=me.name, until=None, ends_with_source=True,
                        while_source_works=True))
            g.reminders.append(f'{x} registers as evil (the Lycanthrope\'s Faux Paw).')

    async def setup(self, game):
        lyc = game.g.with_character(self.name)
        if lyc:
            await self.paw(game, lyc)

    async def becomes(self, game, me):
        await self.paw(game, me)

    async def resolve_night(self, game, night):
        g = game.g
        for p, t in snv.holders(g, night, self.name):
            if not t:
                continue
            if not g.works(p, self.name):
                snv.failed(game, p, self.name, 'nobody died')
                continue
            seen = g.registers_evil(g[t], p)
            good = seen == {False}
            if len(seen) > 1:
                good = (await game.decide_judged(judged(
                    yes_choice(f'Lycanthrope:{t}', POLICY['lycanthrope_misregister_good']), 'lycanthrope_good',
                    f'The Lycanthrope ({p.name}) chose {t} ({g[t].character}), who may register as good or evil: do '
                    'they register as good (yes), and so die?', about=t, recipient=p.name, helps='evil')))['yes']
            if good:
                # the Demon's attacks kill nobody tonight, whether or not the chosen player dies (protected: a reading)
                g.notes['Demon kills stopped'] = night.n
                await game.attempt_kill_judged(g[t], 'lycanthrope', p, night)


def noble_choice(g, p):
    """The Noble's three players: exactly one registers as evil (some registration makes it so). Misinformed: three
    of whom none, or two or more, are evil."""
    others = [q.name for q in g.players if q is not p]
    regs = {x: g.registers_evil(g[x], p) for x in others}

    def one(trio):
        sure = sum(1 for x in trio if regs[x] == {True})
        may = sum(1 for x in trio if True in regs[x])
        return sure <= 1 <= may
    trios = [list(t) for t in combinations(others, 3)]
    true = [t for t in trios if one(t)]
    impaired = g.unreliable(p, 'Noble')
    values = trios if impaired or not true else true

    def style(r):
        evil = g.sample_evil(r) - {p.name}
        if impaired and g.misinformed(p, r):
            false = [t for t in trios if sum(1 for x in t if x in evil) != 1] or trios
            return {'players': r.choice(false)}
        bad = [x for x in others if x in evil] or [x for x in others if True in regs[x]]
        good = [x for x in others if x not in evil and False in regs[x]]
        if bad and len(good) >= 2:
            pick = [r.choice(bad)] + r.sample(good, 2)
            if pick in true or sorted(pick) in [sorted(t) for t in true]:
                return {'players': pick}
        return {'players': r.choice(true or trios)}
    return snv.info(Choice(f'Noble:{p.name}', [{'players': t} for t in values], style), g, p, 'Noble',
                    f'Which three players does {p.name} (Noble) learn, exactly one of them evil?',
                    lambda v: one(v['players']), impaired)


class Noble(Townsfolk):
    name = 'Noble'
    ability = ability(name)
    info = True

    async def show(self, game, p):
        g = game.g
        if len(g.players) < 4:
            return
        await snv.learn(game, p, self.name, noble_choice(g, p), lambda v: '{}, {} and {}: one and only one of them '
                        'is evil.'.format(*sorted(v['players'], key=lambda x: g[x].seat)))

    async def resolve_night(self, game, night):
        if night.first:
            for p in snv.believers(game.g, self.name):
                await self.show(game, p)

    async def becomes(self, game, me):
        if me.alive and not (game.tonight is not None and game.tonight.first):
            await self.show(game, me)


def farmer_choice(g, me):
    """The living good player who becomes a Farmer: usually a Townsfolk (POLICY 'grandchild_townsfolk')."""
    good = [q.name for q in g.living() if not q.evil and q is not me]
    towns = [x for x in good if kind(g[x].character) == 'Townsfolk' and g[x].character != 'Farmer']

    def style(r):
        return {'players': [r.choice(towns if towns and r.random() < POLICY['grandchild_townsfolk'] else good)]}
    return judged(Choice(f'Farmer:{me.name}', [{'players': [x]} for x in good], style), 'farmer_heir',
                  f'The Farmer ({me.name}) died at night: which living good player becomes a Farmer?', about=me.name)


async def farm(game, me):
    """A living good player becomes a Farmer (and is told, woken)."""
    g = game.g
    choice = farmer_choice(g, me)
    if not choice.values:
        return
    x = g[(await game.decide_judged(choice))['players'][0]]
    game.woken(x)
    if x.character == 'Farmer':
        return  # (already one: nothing changes)
    await game.change(x, character='Farmer')


class Farmer(Townsfolk):
    name = 'Farmer'
    ability = ability(name)

    def on_death(self, game, me, dead, cause, alive_before):
        # any death at night, with the ability then (sober and healthy as they die; a Philosopher's too)
        g = game.g
        if dead is me and not me.alive and game.tonight is not None and self.name in g.abilities(me) \
                and not g.impaired(me):
            game.later(lambda game: farm(game, me))


# ---- Outsiders ---------------------------------------------------------------------------------------------------

class Zealot(Outsider):
    name = 'Zealot'
    ability = ability(name)

    def must_vote(self, g, me):
        # five or more players alive as the town sees it; alive themself (a dead Zealot has no ability)
        return me.alive and sum(1 for q in g.players if q.appears_alive) >= 5


# ---- Minions -----------------------------------------------------------------------------------------------------

def plain_sober(g, q):
    """Neither drunk nor poisoned by anything placed (the Drunk, a poison, a choice), leaving out what abilities work
    out from the Grimoire: the Alchemist/Organ Grinder jinx's "if both are sober" (a reading, so it does not loop)."""
    return not rules(q.character).always_drunk and not any(
        s.kind in ('drunk', 'poisoned') and s.target == q.name and g.active(s) for s in g.states)


class OrganGrinder(Minion):
    name = 'Organ Grinder'
    ability = ability(name)
    derives = True

    async def resolve_night(self, game, night):
        g = game.g
        for p in [q for q in g.players if q.alive and self.name in g.abilities(q)]:
            game.woken(p)
            drunk = await ask_yes(game, p, night.n, f'Night {night.n} — Organ Grinder: are you drunk until dusk '
                                                    '(`vote` true: drunk, and tomorrow\'s votes are open; false: '
                                                    'sober, and they are secret)?')
            game.emit('text', {'text': f'[{p.name} chooses to be {"drunk" if drunk else "sober"}]'}, 'audit')
            if drunk:
                g.add(State('drunk', p.name, source=p.name, until='night'))

    def secret_votes(self, g, me):
        return g.works(me, self.name)

    def followers_blind(self, g, me):
        return g.script.jinxed('Butler', self.name)

    def ongoing(self, g, me):
        # the Alchemist jinx: an Alchemist with the ability and the Organ Grinder, both sober: both are drunk
        if not g.script.jinxed('Alchemist', self.name) or not me.alive:
            return []
        holders = [q for q in g.players if q.alive and self.name in g.abilities(q)]
        if len(holders) < 2 or not all(plain_sober(g, q) for q in holders):
            return []
        return [State('drunk', me.name, source=me.name, until=None)]


HARPY_EVIL = re.compile(r'\b(evil|demon|minion|imp)\b', re.I)
HARPY_GOOD = re.compile(r'\b(not|isn\'t|never) (?:\w+ )?(evil|the demon|a minion)\b|\b(is|are) good\b', re.I)


def harpy_evidence(game, player, second, day):
    """What `player` said aloud on `day` about `second` being evil: claimed (a sentence naming them as evil, a Demon or
    a Minion, or a nomination of them), denied (called them good, or not evil), confessed (said they are mad)."""
    out = {'claimed': False, 'denied': False, 'confessed': False}
    mad = re.compile(r"\bI(?:'m| am| was)(?: actually| really| secretly| made)? mad\b(?! at)|\bHarpy (?:chose|picked|"
                     r"made|selected|targeted|got) me\b", re.I)
    for ev in game.events:
        d = ev['data']
        if ev['day'] != day or ev['to'] != 'public':
            continue
        who = d.get('nominee') if ev['kind'] == 'defense' else d.get('speaker') or d.get('nominator') or d.get('player')
        if who != player:
            continue
        if ev['kind'] == 'nomination' and d.get('nominee') == second:
            out['claimed'] = True
        text = d.get('text') or ''
        if mad.search(text):
            out['confessed'] = True
        for sentence in re.split(r'(?<=[.!?])\s+', text):
            if not re.search(rf'\b{re.escape(second)}\b', sentence, re.I):
                continue
            if HARPY_GOOD.search(sentence):
                out['denied'] = True
            elif HARPY_EVIL.search(sentence):
                out['claimed'] = True
    return out


def harpy_madness_choice(g, first, second, evidence):
    broke = evidence['confessed'] or evidence['denied'] or not evidence['claimed']
    return judged(Choice(f'Harpy madness:{first}', [{'yes': True}, {'yes': False}], lambda r: {'yes': broke}),
                  'harpy_madness', f'{first} must be mad that {second} is evil today: trying, sincerely, to convince '
                                   f'the group that {second} is evil. Did they break their madness (yes: they did, and '
                                   'one or both of them might die)?', about=first, recipient=first,
                  claimed=evidence['claimed'], denied=evidence['denied'], confessed=evidence['confessed'])


def harpy_penalty_choice(g, first, second):
    """Who dies for the Harpy's broken madness: nobody, the 1st, the 2nd or both (POLICY 'harpy_kill', then
    'harpy_first' and 'harpy_both')."""
    alive = [x for x in (first, second) if g[x].alive]
    values = [[]] + [[x] for x in alive] + ([alive] if len(alive) == 2 else [])

    def style(r):
        if not alive or r.random() >= POLICY['harpy_kill']:
            return {'players': []}
        x = r.random()
        if len(alive) == 2 and x < POLICY['harpy_both']:
            return {'players': alive}
        if first in alive and (x < POLICY['harpy_both'] + POLICY['harpy_first'] or second not in alive):
            return {'players': [first]}
        return {'players': [second if second in alive else first]}
    return judged(Choice(f'Harpy deaths:{first}', [{'players': v} for v in values], style), 'harpy_penalty',
                  f'{first} broke their madness that {second} is evil: who dies (nobody, either or both)?',
                  about=first, recipient=first)


class Harpy(Minion):
    name = 'Harpy'
    ability = ability(name)
    night_choice = Choose(players=2, prompt='Choose 2 players: tomorrow, the 1st must be mad that the 2nd is evil, or '
                                            'one or both might die.')

    async def resolve_night(self, game, night):
        g = game.g
        for p in [q for q in g.players if q.alive and self.name in g.abilities(q) and q.name in night.chosen]:
            pair = night.chosen[p.name]
            if len(pair) < 2:
                continue
            first, second = pair[0], pair[1]
            if g.works(p, self.name):  # for tomorrow; it ends if the Harpy loses their ability (as the Cerenovus's)
                g.add(State('harpy', first, source=p.name, until='night', ends_with_source=True,
                            while_source_works=True, about=second))
            else:
                snv.failed(game, p, self.name, 'nobody made mad')
            # the 1st is told even when the Harpy is drunk or poisoned (as the Cerenovus's target)
            game.inform(g[first], f'Night {night.n}: the Harpy selected you, and points to {second}. Tomorrow you must '
                                  f'be "mad" that {second} is evil: do your best to convince the group that {second} '
                                  'is evil, or one or both of you might die.')

    async def moment(self, game, me, when):
        # judged once, when the day's talk is done and before nominations open (as the Cerenovus's)
        if when != 'nominations':
            return
        g = game.g
        for s in [s for s in g.states if s.kind == 'harpy' and s.source == me.name and g.active(s)]:
            if g.winner:
                return
            evidence = harpy_evidence(game, s.target, s.about, game.day)
            if not (await game.decide_judged(harpy_madness_choice(g, s.target, s.about, evidence)))['yes']:
                continue
            for x in (await game.decide_judged(harpy_penalty_choice(g, s.target, s.about)))['players']:
                game.ability_kill(g[x], 'harpy', me)
            g.check_victory()


BOFFIN_USABLE = ('Washerwoman', 'Librarian', 'Investigator', 'Chef', 'Empath', 'Undertaker', 'Monk', 'Noble',
                 'Village Idiot', 'Goon', 'Knight', 'Snitch', 'Cult Leader')  # (the last three: batch 3b)


def boffin_options(g):
    """The good abilities the Boffin can give the Demon: built ones the engine runs for a Demon who has them (the
    Drunk, Heretic and Politician never: their jinxes), not in play; the Village Idiot even in play, while there is
    a spare token (its jinx)."""
    in_play = {q.character for q in g.players} | {q.shown for q in g.players}
    idiots = sum(1 for q in g.players if q.character == 'Village Idiot')
    return [c for c in g.script.good if c in BOFFIN_USABLE and (
        c not in in_play or (c == 'Village Idiot' and g.script.jinxed('Boffin', c) and idiots < 3))]


class Boffin(Minion):
    name = 'Boffin'
    ability = ability(name)

    async def resolve_night(self, game, night):
        # the first night, as the Storyteller shows it (the Boffin's step is the first): the Demon has the ability
        # while the Boffin is alive and still has theirs, and it works while the Boffin is sober and healthy, whatever
        # the Demon's sobriety (Grimoire.gift). An Alchemist with the ability is not told which (the jinx)
        g = game.g
        if not night.first or g.notes.get('Boffin gift'):
            return
        b = next((q for q in g.players if q.alive and self.name in g.abilities(q)), None)
        demon = g.demon()
        options = boffin_options(g)
        if not (b and demon and options):
            return
        c = (await game.decide_judged(judged(Choice(f'Boffin:{b.name}', [{'character': x} for x in options],
                                                    lambda r: {'character': r.choice(options)}), 'boffin_ability',
                                             f'The Boffin ({b.name}): which good ability (not in play) does the Demon '
                                             f'({demon.name}) have?', recipient=demon.name)))['character']
        g.notes['Boffin gift'] = {'ability': c, 'giver': b.name}
        game.emit('gains', {'player': demon.name, 'character': c}, 'audit')
        game.woken(demon)
        game.inform(demon, f'Night {night.n} — Boffin: the Boffin is {b.name}, and you have the {c}\'s ability (as '
                           f'well as your own, even if you are drunk or poisoned): {rules(c).ability}')
        if b.character == self.name or not g.script.jinxed('Alchemist', self.name):
            game.woken(b)
            game.inform(b, f'Night {night.n} — Boffin: the Demon ({demon.name}) has the {c}\'s ability.')
        if c == 'Village Idiot' and g.script.jinxed(self.name, c):
            await rules(c).mark_drunk(game, again=True)  # (another Village Idiot: one of them is drunk)


def boom_survivors_choice(g, me):
    """The three players left alive when the Boomdandy explodes: usually the Demon and two others (POLICY
    'boomdandy_keep_demon'), so the countdown decides the game."""
    alive = [q.name for q in g.living()]
    demons = [x for x in alive if g[x].is_demon]

    def style(r):
        if demons and r.random() < POLICY['boomdandy_keep_demon']:
            return {'players': [demons[0]] + r.sample([x for x in alive if x != demons[0]], 2)}
        return {'players': r.sample(alive, 3)}
    return judged(Choice(f'Boomdandy:{me.name}', [{'players': list(t)} for t in combinations(alive, 3)], style),
                  'boomdandy_survivors', f'The Boomdandy ({me.name}) was executed: which three players stay alive?',
                  about=me.name)


async def boom(game, me):
    """All but three players die; then everyone points, and the player most pointed at dies (a tie: nobody)."""
    g = game.g
    game.emit('text', {'text': f'{me.name} was the Boomdandy: all but 3 players die. Then, after a countdown from 10, '
                               'the player with the most players pointing at them dies.'})
    if len(g.living()) > 3:
        keep = (await game.decide_judged(boom_survivors_choice(g, me)))['players']
        for q in [q for q in g.living() if q.name not in keep]:
            game.ability_kill(q, 'boomdandy', me)
        if g.check_victory():
            return
    alive = [q.name for q in g.living()]
    if not alive:
        return
    reqs = {q.name: game.request('night', f'Day {game.day} — Boomdandy: 10, 9, 8 ... 1: point at a living player '
                                          '(`targets`): the one most pointed at dies.', game.day, n_targets=1,
                                 options=alive, min_targets=1) for q in g.players}
    acts = await game.ask_many(reqs)
    points = {name: game.targets(name, acts[name], reqs[name])[0] for name in reqs}
    tally = {x: sum(1 for t in points.values() if t == x) for x in alive}
    game.emit('text', {'text': 'Pointing: ' + '; '.join(f'{a} at {b}' for a, b in points.items()) + '.'})
    top = max(tally.values())
    most = [x for x in alive if tally[x] == top]
    if len(most) == 1:
        game.ability_kill(g[most[0]], 'boomdandy', me)
    else:
        game.emit('text', {'text': f'A tie ({", ".join(most)}): nobody dies.'})
    g.check_victory()


class Boomdandy(Minion):
    name = 'Boomdandy'
    ability = ability(name)

    def on_death(self, game, me, dead, cause, alive_before):
        # executed and dying, with the ability then (sober and healthy as they die; an Alchemist's too); once a game
        g = game.g
        if dead is me and cause == 'execution' and self.name in g.abilities(me) and not g.impaired(me) \
                and not g.notes.get('Boomdandy'):
            g.notes['Boomdandy'] = game.day
            game.later(lambda game: boom(game, me))
        elif dead is me and cause == 'execution' and self.name in g.abilities(me):
            snv.failed(game, me, self.name, 'nobody died')


async def boomdandy_made(game):
    """The Plague Doctor jinx: the Storyteller would gain the Boomdandy's ability, so a player becomes the Boomdandy
    (usually a living Minion, keeping their alignment; else a living good player, who stays good: a reading)."""
    g = game.g
    alive = [q.name for q in g.living()]
    minions = [x for x in alive if kind(g[x].character) == 'Minion']
    if not alive:
        return
    x = (await game.decide_judged(carousel.player_choice(
        'Plague Doctor:Boomdandy', 'plague_boomdandy', 'Which player becomes the Boomdandy?', alive,
        lambda r: {'players': [r.choice(minions if minions and r.random() < POLICY['plague_boomdandy_minion']
                                        else alive)]})))['players'][0]
    await game.change(g[x], character='Boomdandy')


class Fearmonger(Minion):
    name = 'Fearmonger'
    ability = ability(name)
    night_choice = Choose(players=1, prompt='Choose a player: if you nominate and execute them, their team loses. '
                                            'Everyone learns if you choose a new player.')

    async def resolve_night(self, game, night):
        g = game.g
        for p, t in snv.holders(g, night, self.name):
            if not t:
                continue
            if not g.works(p, self.name):
                snv.failed(game, p, self.name, 'nobody chosen')
                continue
            fear = g.notes.setdefault('Fear', {})
            if fear.get(p.name) != t:  # announced only when the choice takes effect (a reading)
                fear[p.name] = t
                game.emit('text', {'text': 'The Storyteller announces: the Fearmonger has chosen a player.'})

    def execution(self, game, me, executed):
        g = game.g
        noms = [x for x in g.nominations if x['day'] == game.day and x['nominee'] == executed.name]
        if not (noms and noms[-1]['nominator'] == me.name and g.notes.get('Fear', {}).get(me.name) == executed.name
                and g.works(me, self.name)):
            return None
        team = 'evil' if executed.evil else 'good'
        return ('good' if executed.evil else 'evil',
                f'The Fearmonger nominated and executed their chosen player, {executed.name} ({team}): the {team} '
                'team loses.')


class Xaan(Minion):
    name = 'Xaan'
    ability = ability(name)
    derives = True
    outsider_choices = (-1, 0, 1)  # [X Outsiders]: any number the setup can deal; X is how many there are
    setup_order = -0.8  # once the other Outsider changes are made (the Balloonist's), before the Village Idiot's

    @staticmethod
    def count(g):
        return outsiders(g)

    async def setup(self, game):
        # X is the number of Outsiders in play; with none, a dealt game adds one (so night 1 can come), else X is 0
        # and the Xaan never poisons (a reading)
        g = game.g
        x = g.with_character(self.name)
        if not x:
            return
        if not outsiders(g) and not game.forced:
            carousel2.add_outsider(game, x)
        g.notes.setdefault('Xaan', {})[x.name] = outsiders(g)

    def becomes(self, game, me):
        game.g.notes.setdefault('Xaan', {})[me.name] = outsiders(game.g)  # (a night already passed never comes)

    def intro(self, game, me):
        return [f'X is {game.g.notes.get("Xaan", {}).get(me.name, 0)}: on night X all Townsfolk are poisoned until '
                'dusk.']

    async def resolve_night(self, game, night):
        g = game.g
        for p in [q for q in g.players if q.alive and self.name in g.abilities(q)]:
            if g.notes.get('Xaan', {}).get(p.name) != night.n:
                continue
            if g.works(p, self.name):
                g.notes.setdefault('Xaan night', {})[p.name] = night.n
            else:
                snv.failed(game, p, self.name, 'no Townsfolk poisoned')

    def ongoing(self, g, me):
        # every Townsfolk (as they are now), from the Xaan's step on night X until dusk, while the Xaan is alive,
        # sober and healthy (as the Poisoner's poison: docs/interaction-findings.md, B5)
        if g.notes.get('Xaan night', {}).get(me.name) != g.day or not me.alive or g.impaired(me):
            return []
        return [State('poisoned', q.name, source=me.name, until=None) for q in g.players
                if kind(q.character) == 'Townsfolk']


# ---- The Alchemist (a Townsfolk with a Minion's ability) -------------------------------------------------------

# Minion abilities the engine runs for a good player who has them (each through `extra`, tested); the others are not
# offered (docs/carousel-rulings.md, batch 3: the Scarlet Woman, Pit-Hag, Evil Twin, Goblin and Xaan)
ALCHEMIST_USABLE = ('Poisoner', "Devil's Advocate", 'Assassin', 'Godfather', 'Baron', 'Witch', 'Cerenovus',
                    'Fearmonger', 'Boomdandy', 'Harpy')
# their jinxes: in play alongside (no ability: Spy, Widow, Marionette; both have it: Organ Grinder), or not
ALCHEMIST_IN_PLAY = ('Spy', 'Widow', 'Marionette', 'Organ Grinder', 'Wraith')  # (the last: batch 4)
ALCHEMIST_NOT_IN_PLAY = ('Mastermind', 'Boffin', 'Summoner')
ALCHEMIST_NONE = ('Spy', 'Widow', 'Marionette', 'Mastermind', 'Wraith')  # the jinxes: no ability
ALCHEMIST_SETUP = ('Baron', 'Godfather', 'Summoner')  # setup changes: only in a dealt game, at setup


def alchemist_options(game, setup=True):
    g = game.g
    in_play = {q.character for q in g.players}
    out = [m for m in g.script.minions if m in ALCHEMIST_USABLE and m not in in_play]
    for m in g.script.minions:
        if g.script.jinxed('Alchemist', m) and ((m in ALCHEMIST_IN_PLAY and m in in_play)
                                                or (m in ALCHEMIST_NOT_IN_PLAY and m not in in_play)):
            out.append(m)
    evil = [q for q in g.players if q.evil and q.character != 'Marionette']
    if not setup or game.forced or not any(not q.is_demon for q in evil):
        # (the Summoner jinx's [No Demon] needs a dealt game, at setup, and another evil player than the Demon: a
        # Marionette alone would wait for the summoned Demon, leaving no evil player until the 3rd night)
        out = [m for m in out if m != 'Summoner']
    return out


def alchemist_text(g, m):
    if m in ALCHEMIST_NONE:
        return (f'you have the {m}\'s ability, but (their jinx) you have no {m} ability, and the {m} is '
                + ('not in play.' if m == 'Mastermind' else 'in play: after each execution, while alive, you may '
                   f'publicly guess a living player as the {m}; if you are right, the Demon must choose them tonight.'))
    if m == 'Summoner':
        return ('you have the Summoner\'s ability (their jinx): there is no Demon yet; on the 3rd night you choose '
                'which Demon, and the Storyteller which player. If you die before then, evil wins.')
    if m == 'Boffin':
        return 'you have the Boffin\'s ability: the Demon has a good character\'s ability (you do not learn which).'
    return (f'you have the {m}\'s ability: {rules(m).ability} (When you use it, the Storyteller may prompt you to '
            'choose differently.)')


class Alchemist(Townsfolk):
    name = 'Alchemist'
    ability = ability(name)
    setup_order = -1.5  # its Minion's setup changes (the Baron's Outsiders) come first

    @staticmethod
    def minion(g, me):
        return g.notes.get('Alchemist', {}).get(me.name)

    async def pick(self, game, me, setup=False):
        g = game.g
        options = alchemist_options(game, setup) if me.character == self.name or self.name in me.extra else \
            [m for m in g.script.minions if m in ALCHEMIST_USABLE and m not in ALCHEMIST_SETUP
             and m not in {q.character for q in g.players}]  # (a Drunk's: never a working ability)
        if not options:
            return None
        m = (await game.decide_judged(judged(Choice(f'Alchemist:{me.name}', [{'character': x} for x in options],
                                                    lambda r: {'character': r.choice(options)}), 'alchemist_minion',
                                             f'The Alchemist ({me.name}): which Minion\'s ability (not in play) do '
                                             'they have?', recipient=me.name)))['character']
        g.notes.setdefault('Alchemist', {})[me.name] = m
        if m not in ALCHEMIST_NONE:
            me.extra.append(m)
            game.emit('gains', {'player': me.name, 'character': m}, 'audit')
        if setup and not game.forced:
            await self.setup_change(game, me, m)
        return m

    async def setup_change(self, game, me, m):
        # a dealt game: the Minion's setup modifier, as if it were in play (the Baron's +2 Outsiders, the Godfather's
        # -1 or +1, the Summoner's [No Demon]: the Demon dealt becomes a Townsfolk not in play, good)
        g = game.g
        if m == 'Baron':
            for _ in range(2):
                carousel2.add_outsider(game, me)
        elif m == 'Godfather':
            if game.decide(yes_choice('Alchemist Godfather more', POLICY['godfather_more_outsiders']))['yes']:
                carousel2.add_outsider(game, me)
            else:
                remove_outsider(game, me)
        elif m == 'Summoner':
            demon = g.demon()
            in_play = {q.character for q in g.players}
            towns = [c for c in g.script.townsfolk if c not in in_play and rules(c).setup_order is None]
            if demon and towns:
                c = game.decide(Choice('Alchemist Summoner townsfolk', [{'character': c} for c in towns],
                                       lambda r: {'character': r.choice(towns)}))['character']
                g.change_character(demon, c)
                demon.alignment = 'good'

    async def setup(self, game):
        for a in [q for q in game.g.players if q.character == self.name]:
            await self.pick(game, a, setup=True)

    async def becomes(self, game, me):
        if self.minion(game.g, me) is None or me.character == self.name:
            m = await self.pick(game, me)
            if m:
                game.inform(me, f'{snv.when(game)} — Alchemist: {alchemist_text(game.g, m)}')

    async def resolve_night(self, game, night):
        # the first night: the Alchemist is shown their Minion (a Drunk who believes they are the Alchemist is
        # given one too, whose ability never works: they are drunk)
        g = game.g
        if not night.first:
            return
        for p in snv.believers(g, self.name):
            m = self.minion(g, p)
            if m is None and p.character != self.name and p.name not in g.notes.get('Alchemist', {}):
                m = await self.pick(game, p)
            if m:
                game.woken(p)
                game.inform(p, f'Night {night.n} — Alchemist: {alchemist_text(g, m)}')

    def execution(self, game, me, executed):
        # the Spy and Widow jinxes (and the Wraith's, batch 4): after each execution (dying or not), a living Alchemist
        # with that "ability" may guess publicly
        g = game.g
        m = self.minion(g, me)
        if m in ('Spy', 'Widow', 'Wraith') and me.alive and me.character == self.name and g.script.jinxed(self.name, m):
            game.later(lambda game: self.guess(game, me, m))
        return None

    async def guess(self, game, me, m):
        g = game.g
        alive = [q.name for q in g.living() if q is not me]
        if not (me.alive and alive):
            return
        req = game.request('night', f'Day {game.day} — Alchemist: you may publicly guess a living player as the {m} '
                                    '(`targets`; [] for no guess). If you are right, the Demon must choose them '
                                    'tonight.', game.day, n_targets=1, options=alive, min_targets=0)
        t = game.targets(me.name, await game.ask(me.name, req), req)
        if not t:
            return
        game.emit('text', {'text': f'{me.name} publicly guesses that {t[0]} is the {m}.'})
        if g[t[0]].character == m:
            g.notes.setdefault('Demon must choose', {})[game.day + 1] = t[0]

    def overrides_end(self, g, me, winner, reason):
        # an Alchemist-Summoner who may yet summon: no win for good with no Demon (as the Summoner's)
        if self.minion(g, me) == 'Summoner' and 'Summoner' in g.abilities(me):
            return rules('Summoner').overrides_end(g, me, winner, reason)
        return None

    def on_death(self, game, me, dead, cause, alive_before):
        # the Summoner jinx: they die before they summon: evil wins
        g = game.g
        if dead is me and self.minion(g, me) == 'Summoner' and g.script.jinxed(self.name, 'Summoner') \
                and not g.notes.get('Summoned') and not g.winner and 'Summoner' in g.abilities(me):
            g.winner, g.reason = 'evil', f'The Alchemist-Summoner ({me.name}) died before summoning: evil wins.'


def summoned_by_alchemist_choice(g, s, demon):
    """The Alchemist/Summoner jinx: the Storyteller chooses which player becomes the Demon the Alchemist chose:
    usually a living good player (as the Summoner's)."""
    names = [q.name for q in g.players]
    return judged(Choice(f'Alchemist summons:{s.name}', [{'players': [x]} for x in names],
                         lambda r: {'players': [r.choice(carousel.living_good(g, s) or names)]}), 'summon_player',
                  f'The Alchemist-Summoner ({s.name}) chose the {demon}: which player becomes it (an evil Demon)?',
                  recipient=s.name)


CHARACTERS.update({c.name: c() for c in [VillageIdiot, Acrobat, Lycanthrope, Alchemist, Zealot, OrganGrinder, Noble,
                                         Farmer, Harpy, Boffin, Boomdandy, Fearmonger, Xaan]})


# ---- Batch 3's jinxes (docs/carousel-rulings.md, batch 3) --------------------------------------------------------

jinx('Alchemist', 'Boffin', 'carousel3.Boffin.resolve_night')
for _x in ('Spy', 'Widow'):
    jinx('Alchemist', _x, 'carousel3.Alchemist.execution, guess; game.Game.wake (Demon must choose)')
jinx('Alchemist', 'Marionette', 'carousel3.alchemist_options, ALCHEMIST_NONE')
jinx('Alchemist', 'Mastermind', 'carousel3.alchemist_options, ALCHEMIST_NONE')
jinx('Alchemist', 'Organ Grinder', 'carousel3.alchemist_options; carousel3.OrganGrinder.ongoing')
jinx('Alchemist', 'Summoner', 'carousel3.Alchemist.setup_change, overrides_end, on_death; carousel.Summoner')
jinx('Boffin', 'Drunk', 'carousel3.BOFFIN_USABLE (never offered)')
jinx('Boffin', 'Heretic', 'carousel3.BOFFIN_USABLE (never offered)')
jinx('Boffin', 'Politician', 'carousel3.BOFFIN_USABLE (never offered)')
jinx('Boffin', 'Goon', 'bmr.Goon.chosen')
jinx('Boffin', 'Village Idiot', 'carousel3.boffin_options, Boffin.resolve_night')
jinx('Butler', 'Organ Grinder', 'game.Game.vote')
jinx('Cannibal', 'Zealot', 'carousel2.Cannibal.lunch')
jinx('Leviathan', 'Farmer', 'carousel2.Leviathan.resolve_night')
jinx('Pit-Hag', 'Village Idiot', 'snv.PitHag.resolve_night')
jinx('Plague Doctor', 'Boomdandy', 'carousel.PlagueDoctor.gain (carousel3.boomdandy_made)')
jinx('Plague Doctor', 'Fearmonger', 'carousel.PlagueDoctor.gain, minion_gains')
