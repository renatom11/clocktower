"""Batch 4 of the experimental characters (the official data's "carousel" edition): the Bounty Hunter, Engineer,
Princess, Hermit, Ogre, Psychopath, Wraith and Vizier, and every official jinx between them and a built character
(the Alchemist's, Plague Doctor's and Magician's with the Wraith, the Boffin's with the Ogre and the Vizier's seven
among them). The Amnesiac, Mezepheles and Yaggababble are left for batch 5, the Wizard, Legion, Riot, Atheist and Lil'
Monsta for batch 6 (docs/carousel-rulings.md).

As in carousel.py to carousel4.py (whose helpers and conventions this module shares): each entry follows the wiki's How
to Run, and where the rules leave a question open, a comment says which reading the entry takes, and why
(docs/carousel-rulings.md, batch 4, lists them for review). Each implemented jinx is declared at the end with `jinx`;
a jinx that changes another module's character is guarded there by `Script.jinxed`, so scripts without both
characters play as before.

The Vizier decides executions, not votes: once a vote is over, it may execute the nominee at once
(Character.vote_over, a core hook that does nothing on any script without it), so it is not one of the vote-changing
characters the brief keeps for the owner (the Bureaucrat, Thief and Voudon change how many votes a hand counts for).
"""
from __future__ import annotations

from . import carousel, carousel3, snv
from .characters import CHARACTERS, Choose, Minion, Outsider, Townsfolk, holds, jinx, kind, rules, settle
from .state import POLICY, Choice, State, judged, yes_choice


# carousel.py to carousel4.py and snv.py may still be loading when this module is (whichever of the engine's modules is
# imported first): their names are used through the modules, at call time.

def ability(name):
    """The official ability text."""
    from . import official
    return official.role(name)['ability']


def intro_line(g, name, text):
    """A line added to `name`'s introduction before the first night (Game.setup reads g.notes['Intro'])."""
    g.notes.setdefault('Intro', {}).setdefault(name, []).append(text)


# ---- Townsfolk ---------------------------------------------------------------------------------------------------

def bounty_choice(g, p, shown):
    """The evil player the Bounty Hunter learns: another living player who can register as evil, not one shown before
    (the first night: any). Drunk, poisoned or under the Vortox: any other living player, misinformed with a good one.
    None when nobody new can be shown truly to a sober one (nothing is learned)."""
    others = [q.name for q in g.players if q is not p and q.alive]
    fresh = [x for x in others if x not in shown] or others
    true = [x for x in fresh if True in g.registers_evil(g[x], p)]
    impaired = g.unreliable(p, 'Bounty Hunter')
    if not fresh or not (true or impaired):
        return None
    values = fresh if impaired else true

    def style(r):
        if impaired and g.misinformed(p, r):
            good = [x for x in fresh if False in g.registers_evil(g[x], p)]
            return {'players': [r.choice(good or fresh)]}
        evil = [x for x in true if g[x].evil]  # usually a truly evil player (a Recluse only by its chance)
        seen = g.sample_evil(r)
        return {'players': [r.choice([x for x in true if x in seen] or evil or true or values)]}
    return snv.info(Choice(f'Bounty Hunter:{p.name}', [{'players': [x]} for x in values], style), g, p,
                    'Bounty Hunter', f'Which evil player does {p.name} (Bounty Hunter) learn' +
                    (' (another: the one they knew has died)?' if shown else '?'),
                    lambda v: v['players'][0] in true, impaired)


def evil_townsfolk_choice(g, by):
    """[1 Townsfolk is evil]: which good Townsfolk (not a Bounty Hunter) the Storyteller makes evil."""
    towns = [q.name for q in g.players if kind(q.character) == 'Townsfolk' and not q.evil
             and q.character != 'Bounty Hunter' and q is not by]
    if not towns:
        return None
    from itertools import combinations

    def spoils(x):  # (a Noble left with no three players exactly one of them evil: a 5-player table, finding U11)
        return any(not any(sum(1 for y in t if g[y].evil or y == x) == 1
                           for t in combinations([o.name for o in g.players if o is not q], 3))
                   for q in g.players if q.character == 'Noble' and q.name != x)
    safe = [x for x in towns if not spoils(x)] or towns
    return judged(Choice('Bounty Hunter evil townsfolk', [{'players': [x]} for x in towns],
                         lambda r: {'players': [r.choice(safe)]}), 'evil_townsfolk',
                  'The Bounty Hunter is in play: which Townsfolk is evil? (They learn they are evil, and nothing '
                  'more.)')


class BountyHunter(Townsfolk):
    name = 'Bounty Hunter'
    ability = ability(name)
    info = True
    setup_order = 0.7  # once the characters are final (after the Huntsman's Damsel), and before any setup step picks a
    #                    good player (the red herring, the Grandchild, the Faux Paw, the Evil Twin's twin: finding B18)

    @staticmethod
    def kazali_waits(g):
        """The Kazali jinx: with the Kazali in play, the evil Townsfolk waits for the Kazali's first-night choice (a
        Bounty Hunter it makes a Minion makes none)."""
        return g.script.jinxed('Bounty Hunter', 'Kazali') and any(q.character == 'Kazali' for q in g.players)

    async def setup(self, game):
        # "[1 Townsfolk is evil]": once, for a Bounty Hunter in play (a Drunk who believes they are one makes none, as
        # every setup modifier: ruling 83); in a forced setup too (it changes an alignment, not a character). The
        # evil Townsfolk is told in their introduction that they are evil and nothing more: the evil team does not
        # learn them, nor they the evil team (a reading of the almanac's "they know they are evil")
        g = game.g
        bh = g.with_character(self.name)
        if not bh or g.notes.get('Evil Townsfolk'):
            return
        if self.kazali_waits(g):
            g.notes['Evil Townsfolk'] = 'waiting'
            return
        choice = evil_townsfolk_choice(g, bh)
        if choice is None:
            return
        x = (await game.decide_judged(choice))['players'][0]
        g[x].alignment = 'evil'
        g.notes['Evil Townsfolk'] = x
        game.emit('alignment', {'player': x, 'alignment': 'evil'}, 'audit')
        intro_line(g, x, 'You are evil (a Bounty Hunter is in play, and one Townsfolk is evil: you). You win or lose '
                         'with the evil team; you do not know who the other evil players are, and they do not know '
                         'you.')

    async def made_late(self, game):
        """The Kazali jinx, at the Bounty Hunter's first-night step (after the Kazali's): a Bounty Hunter still in play
        makes the evil Townsfolk now, told at once."""
        g = game.g
        g.notes['Evil Townsfolk'] = None
        bh = g.with_character(self.name)
        choice = evil_townsfolk_choice(g, bh) if bh else None
        if choice is None:
            return
        x = (await game.decide_judged(choice))['players'][0]
        g.notes['Evil Townsfolk'] = x
        await game.change(g[x], alignment='evil')

    async def show(self, game, p):
        g = game.g
        rec = g.notes.setdefault('Bounty Hunter', {}).setdefault(p.name, {'know': None, 'shown': []})
        choice = bounty_choice(g, p, rec['shown'])
        if choice is None:
            rec['know'] = None
            return
        v = await snv.learn(game, p, self.name, choice, lambda v: f'{v["players"][0]} is evil.' if not rec['shown']
                            else f'the player you knew has died: {v["players"][0]} is evil.')
        rec['know'] = v['players'][0]
        rec['shown'].append(rec['know'])
        g.reminders.append(f'{p.name} (Bounty Hunter) knows {rec["know"]} (KNOW).')

    async def resolve_night(self, game, night):
        g = game.g
        if night.first and g.notes.get('Evil Townsfolk') == 'waiting':
            await self.made_late(game)
        # "You start knowing": the first night (or the night they first have it); "if the player you know dies, you
        # learn another evil player tonight": at this step, once the one they know is dead (today or tonight)
        for p in snv.believers(g, self.name):
            rec = g.notes.get('Bounty Hunter', {}).get(p.name)
            if rec is None or (rec['know'] and not g[rec['know']].appears_alive):
                await self.show(game, p)

    async def becomes(self, game, me):
        # a Bounty Hunter made later (the Pit-Hag's) or a Philosopher who gains the ability: they learn one now. The
        # Philosopher jinx: "a Townsfolk might turn evil" (POLICY 'bounty_philosopher_evil'), told at once
        g = game.g
        if me.character != self.name and self.name in me.extra and g.script.jinxed(self.name, 'Philosopher') \
                and not g.notes.get('Evil Townsfolk'):
            choice = evil_townsfolk_choice(g, me)
            if choice is not None and (await game.decide_judged(judged(
                    yes_choice('Bounty Hunter philosopher', POLICY['bounty_philosopher_evil']), 'evil_townsfolk_made',
                    f'{me.name} (Philosopher) gained the Bounty Hunter\'s ability: does a Townsfolk turn evil?',
                    recipient=me.name, helps='evil')))['yes']:
                x = (await game.decide_judged(choice))['players'][0]
                g.notes['Evil Townsfolk'] = x
                await game.change(g[x], alignment='evil')
        if me.alive:
            g.notes.setdefault('Bounty Hunter', {}).pop(me.name, None)
            await self.show(game, me)


# The Engineer may not make: the Marionette (it believes it is good and sits by the Demon from the start), a Minion
# with no Demon (the Summoner) or a Demon with no Minions (the Kazali), whose texts describe a setup
def engineer_allowed(g, c):
    return c in g.script.all and kind(c) in ('Minion', 'Demon') and c != 'Marionette' and not rules(c).no_demon \
        and not rules(c).no_minions


def engineer_assign_choice(g, eng, movers, free):
    """Which of the Minions to change becomes which of the chosen characters not yet in play."""
    from itertools import permutations
    values = [{'players': list(order)} for order in permutations(movers)]
    return judged(Choice(f'Engineer assign:{eng.name}', values, lambda r: {'players': r.sample(movers, len(movers))}),
                  'engineer_assign', f'The Engineer ({eng.name}) chose the Minions {", ".join(free)} (not in play): '
                  f'in this order, which of {", ".join(movers)} becomes each?', recipient=eng.name)


class Engineer(Townsfolk):
    name = 'Engineer'
    ability = ability(name)
    night_choice = Choose(players=0, character=True, optional=True, kinds=('Minion', 'Demon'),
                          prompt='Once per game: choose a Demon (`character`): the Demon becomes it; or a Minion: '
                                 'you then choose the rest of the Minions, one at a time, and the Minions become them. '
                                 'Or null, to keep your ability for a later night.')

    def night_spec(self, game, me, night):
        return None if snv.used(game.g, me, self.name) else self.night_choice

    async def resolve_night(self, game, night):
        g = game.g
        for p in [q for q in snv.believers(g, self.name) if q.name in night.chosen]:
            c = night.characters.get(p.name)
            if not c or snv.used(g, p, self.name):
                continue
            if not engineer_allowed(g, c):  # (kept for a later night, with a notice: a reading)
                game.inform(p, f'Night {night.n} — Engineer: the {c} cannot be chosen; your ability is kept.')
                continue
            snv.use(g, p, self.name)  # spent even if drunk or poisoned
            if self.name not in g.abilities(p):
                continue
            minions = [c] if kind(c) == 'Minion' else []
            if minions:  # the rest of the Minions, one request each
                k = sum(1 for q in g.players if q.alive and kind(q.character) == 'Minion'
                        and q.character != 'Marionette')
                for i in range(1, k):
                    pool = [m for m in g.script.minions if engineer_allowed(g, m) and m not in minions]
                    if not pool:
                        break
                    req = game.request('night', f'Night {night.n} — Engineer: choose Minion {i + 1} of {k} '
                                                f'(`character`; chosen so far: {", ".join(minions)}).', night.n,
                                       characters=pool)
                    minions.append(game.chosen_character(p.name, await game.ask(p.name, req), req))
            game.emit('engineer', {'player': p.name, 'characters': minions or [c]}, 'audit')
            if not g.works(p, self.name):
                snv.failed(game, p, self.name, 'nothing changed')
                continue
            if minions:
                await self.make_minions(game, p, minions)
            else:
                await self.make_demon(game, p, c)

    async def make_demon(self, game, eng, c):
        # "which Demon is in play": the living Demon becomes it (the dead keep theirs: a reading); with several, the
        # Storyteller picks which one, so two players never share it
        g = game.g
        demons = [q.name for q in g.players if q.alive and q.is_demon]
        if not demons or any(g[x].character == c for x in demons) or g.script.clash(
                {q.character for q in g.players if q.name not in demons} | {c}):
            return
        x = demons[0]
        if len(demons) > 1:
            x = (await game.decide_judged(carousel.player_choice(
                f'Engineer demon:{eng.name}', 'engineer_demon', f'The Engineer ({eng.name}) chose the {c}: which '
                'Demon becomes it?', demons, lambda r: {'players': [r.choice(demons)]})))['players'][0]
        await game.change(g[x], character=c)

    async def make_minions(self, game, eng, chosen):
        # "which Minions are in play": the living Minions (not a Marionette, who believes they are good) are the
        # chosen characters: one who already has a chosen one keeps it, the others take the rest (the Storyteller's
        # assignment), all at once, each told. The Summoner jinx: a living Summoner removed from play leaves its
        # ability with the Storyteller
        g = game.g
        live = [q for q in g.players if q.alive and kind(q.character) == 'Minion' and q.character != 'Marionette']
        keep = [q for q in live if q.character in chosen]
        free = [c for c in dict.fromkeys(chosen) if c not in {q.character for q in keep}
                and not any(q.character == c for q in g.players)]
        movers = [q.name for q in live if q not in keep][:len(free)]
        free = free[:len(movers)]
        if not movers:
            return
        order = (await game.decide_judged(engineer_assign_choice(g, eng, movers, free)))['players'] \
            if len(movers) > 1 else movers
        changes = list(zip(order, free))
        summoners = [x for x, _ in changes if g[x].character == 'Summoner']
        await game.changes([(g[x], c, None) for x, c in changes])
        if summoners and g.script.jinxed('Summoner', self.name) and not g.notes.get('Summoned'):
            g.notes.setdefault('Storyteller abilities', {})['Summoner'] = self.name
            g.notes['Storyteller summons'] = summoners[0]
            game.emit('text', {'text': '[the Storyteller has the Summoner ability (the Engineer jinx)]'}, 'audit')

    def overrides_end(self, g, me, winner, reason):
        # the Summoner jinx: while the Storyteller may yet summon, no Demon is no win for good (as the Summoner's)
        if winner == 'good' and not g.demon() and g.notes.get('Storyteller summons') and not g.notes.get(
                'Summoned') and g.day <= 3:
            return False
        return None

    async def storyteller_step(self, game, night, character):
        # the Summoner jinx: on the 3rd night, at the Summoner's step, the Storyteller makes a player (usually a
        # living good one) an evil Demon of its choice
        g = game.g
        if character != 'Summoner' or night.n != 3 or g.notes.get('Summoned') not in (None, 'failed'):
            return
        s = g[g.notes['Storyteller summons']]
        in_play = {q.character for q in g.players}  # (never a Demon in play: two players would share it)
        demons = [d for d in g.script.demons if d not in in_play and not g.script.clash(in_play | {d})]
        if not demons:
            g.notes['Summoned'] = 'failed'
            return
        v = await game.decide_judged(carousel.summon_choice(g, s, None, None, demons))
        await rules('Summoner').summon(game, s, g[v['players'][0]], v['character'], night)


class Princess(Townsfolk):
    name = 'Princess'
    ability = ability(name)

    @staticmethod
    def first_day(g, p):
        return g.notes.get('Princess day', {}).get(p.name, 1)

    def becomes(self, game, me):
        # "your 1st day": a Princess made later (the Pit-Hag's) has hers the next day she is the Princess (a reading)
        game.g.notes.setdefault('Princess day', {})[me.name] = game.day + (1 if game.tonight is not None else 0)

    @staticmethod
    def stops(g, p, day):
        """Whether `p` (with the ability) nominated today's executed player on their 1st day; the Cannibal jinx: or
        the Cannibal nominated, executed and killed the Princess today."""
        for ex in [x for x in g.executions if x['day'] == day]:
            noms = [x for x in g.nominations if x['day'] == day and x['nominee'] == ex['player']]
            if not (noms and noms[-1]['nominator'] == p.name):
                continue
            if p.character != 'Cannibal' and day == Princess.first_day(g, p):  # (a Cannibal's: only the jinx's)
                return True
            if p.character == 'Cannibal' and g.script.jinxed('Cannibal', 'Princess') and ex['died'] \
                    and g[ex['player']].character == 'Princess':
                return True
        return False

    async def resolve_night(self, game, night):
        # at her step, before the Demon's: the Demon wakes as normal, but its attacks kill nobody tonight (as the
        # Pit-Hag's arbitrary "no one dies": Game.demon_kills_stopped). The Princess alive, sober and healthy now
        g = game.g
        if night.first:
            return
        for p in [q for q in g.players if self.name in g.abilities(q)]:
            if not self.stops(g, p, night.n - 1):
                continue
            if not g.works(p, self.name):
                snv.failed(game, p, self.name, 'the Demon killed')
                continue
            g.notes['Demon kills stopped'] = night.n
            game.emit('text', {'text': f'[{p.name} (Princess): the Demon does not kill tonight]'}, 'audit')


# ---- Outsiders ---------------------------------------------------------------------------------------------------

# The Outsider abilities the Hermit does not have (docs/carousel-rulings.md, batch 4): the Drunk's and the Lunatic's are
# illusions dealt at setup about who a player believes they are (the Hermit knows); the Butler's master is one per game
# in this engine (Grimoire.master), and the Puzzlemaster's puzzle one per game (its drunk player)
HERMIT_NONE = ('Hermit', 'Drunk', 'Lunatic', 'Butler', 'Puzzlemaster')


def hermit_abilities(g):
    return [c for c in g.script.outsiders if c not in HERMIT_NONE]


class Hermit(Outsider):
    name = 'Hermit'
    ability = ability(name)
    outsider_choices = (-1, 0)  # [-0 or -1 Outsider] (for the setup checks; dealt by its setup step)
    flips_result = True  # its end hook may hold the Heretic's, which turns the result around after every other one
    setup_order = -0.85  # after the other Outsider changes (Balloonist, Kazali), before the Xaan counts them

    @staticmethod
    def held(me):
        return [c for c in getattr(me, 'extra', ()) if c not in HERMIT_NONE] if me.character == 'Hermit' else []

    def gain(self, game, me):
        """The Hermit has every Outsider ability on the script (in play or not) but those in HERMIT_NONE: held in
        `extra`, so each acts as for a player who gained it (they wake at its step, its hooks run); the hooks the
        engine asks of a player's own character are passed on below."""
        me.extra = [c for c in hermit_abilities(game.g) if c not in me.extra]
        for c in me.extra:
            game.emit('gains', {'player': me.name, 'character': c}, 'audit')

    async def setup(self, game):
        # [-0 or -1 Outsider]: in a dealt game, one fewer half the time (POLICY 'hermit_fewer_outsider'), another
        # Outsider becoming a Townsfolk not in play; a forced setup keeps its characters
        g = game.g
        for h in [q for q in g.players if q.character == self.name]:
            self.gain(game, h)
        h = g.with_character(self.name)
        if h and not game.forced and game.decide(yes_choice('Hermit fewer', POLICY['hermit_fewer_outsider']))['yes']:
            carousel3.remove_outsider(game, h)

    async def becomes(self, game, me):
        # a Hermit made later (the Pit-Hag's): every ability now, each as if gained (a "you start knowing" one acts
        # now). A Philosopher who gains the Hermit's ability gains no more (a reading: it names abilities, not a
        # character; option: every Outsider ability)
        if me.character != self.name:
            return
        self.gain(game, me)
        for c in list(me.extra):
            await settle(rules(c).becomes(game, me))

    # the hooks the engine asks of a player's own character (registration, execution, the evil team's information, the
    # end), passed on to each ability held; the others reach the abilities through Grimoire.abilities
    def registers_evil(self, g, me, observer=None):
        out = {me.evil}
        for c in self.held(me):
            out |= rules(c).registers_evil(g, me, observer)
        return out

    def registers_as(self, g, me, observer=None):
        out = {me.character}
        for c in self.held(me):
            out |= rules(c).registers_as(g, me, observer)
        return out

    def registers_demon_to_ft(self, g, me, observer=None):
        out = {me.name == g.red_herring}
        for c in self.held(me):
            out |= rules(c).registers_demon_to_ft(g, me, observer)
        return out

    def executed(self, game, me):
        return next((x for x in (rules(c).executed(game, me) for c in self.held(me)) if x), None)

    def told_evil(self, game, me, viewer):
        return [line for c in self.held(me) for line in rules(c).told_evil(game, me, viewer)]

    def overrides_end(self, g, me, winner, reason):
        for c in self.held(me):
            x = rules(c).overrides_end(g, me, winner, reason)
            if x is not None:
                return x
        return None

    def ended(self, g, me, winner, reason):
        # the Politician's, then the Heretic's: the result turns around once, whoever has the Heretic's ability (a
        # Heretic in play, sober, turns it already: a reading, so two do not cancel out)
        out = None
        for c in sorted(self.held(me), key=lambda c: rules(c).flips_result):
            if c == 'Heretic' and any(q is not me and q.character == 'Heretic' and not g.impaired(q)
                                      for q in g.players):
                continue
            x = rules(c).ended(g, me, g.winner, out or reason)
            out = x or out
        return out


class Ogre(Outsider):
    name = 'Ogre'
    ability = ability(name)
    night_choice = Choose(players=1, may_self=False, prompt='Your 1st night: choose a player (not yourself): you '
                                                            'become their alignment (you are not told which).')

    def night_spec(self, game, me, night):
        return None if snv.used(game.g, me, self.name) else self.night_choice

    def becomes(self, game, me):
        # "On your 1st night": the official night order wakes the Ogre on the first night only, so a player who has the
        # ability later (the Pit-Hag's Ogre, a Philosopher's, a Hermit made later) chooses at once, when they get it
        # (a reading: their first night is the one they became it in)
        snv.fresh(game.g, me, self.name)
        game.later(lambda game: self.choose_now(game, me))  # (once the change that made them is done: the Pit-Hag's
        #                                                     lock on an evil Ogre comes after it)

    async def choose_now(self, game, me):
        g = game.g
        others = [q.name for q in g.players if q is not me]
        if not (me.alive and self.name in g.abilities(me)) or snv.used(g, me, self.name) or not others:
            return
        n = game.day
        req = game.request('night', f'{snv.when(game)} — Ogre: {self.night_choice.prompt} Put your choice in '
                                    '`targets`.', n, n_targets=1, options=others, min_targets=1)
        act = await game.insist(me.name, req, await game.ask(me.name, req), self.night_choice)
        t = (game.targets(me.name, act, req) or [None])[0]
        if t:
            game.woken(me)
            await self.befriend(game, me, t, n)

    async def resolve_night(self, game, night):
        g = game.g
        for p in [q for q in snv.believers(g, self.name) if q.name in night.chosen]:
            t = (night.chosen[p.name] or [None])[0]
            if t and not snv.used(g, p, self.name):
                await self.befriend(game, p, t, night.n)

    async def befriend(self, game, p, t, n):
        g = game.g
        snv.use(g, p, self.name)
        if self.name not in g.abilities(p):
            return  # a player who only believes they are the Ogre (the Drunk): nothing
        # "even if drunk or poisoned"; the alignment as the target registers to the Ogre (the Spy jinx: the Spy
        # registers evil; a Recluse might, by its usual chance)
        target = g[t]
        regs = g.registers_evil(target, p)
        if target.character == 'Spy' and g.script.jinxed('Spy', self.name):
            regs = {True}
        evil = next(iter(regs))
        if len(regs) > 1:
            key = rules(target.character).misregisters or 'recluse_evil'
            evil = (await game.decide_judged(judged(
                yes_choice(f'Ogre:{t}', POLICY[key]), 'ogre_evil',
                f'The Ogre ({p.name}) chose {t} ({target.character}), who may register as good or evil: do they '
                'register as evil (yes)?', about=t, recipient=p.name)))['yes']
        g.notes.setdefault('Ogre', {})[p.name] = t
        g.reminders.append(f'{p.name} (Ogre) chose {t} (FRIEND).')
        side = 'evil' if evil else 'good'
        if side == 'good' and p.name in g.notes.get('Evil Ogres', ()):
            side = p.alignment  # the Pit-Hag jinx: an evil player made the Ogre can't turn good by it
        if side != p.alignment:
            p.alignment = side
            game.emit('alignment', {'player': p.name, 'alignment': side}, 'audit')
            for q in g.players:
                for c in g.abilities(q):
                    await settle(rules(c).changed(game, q, p))
        if evil and not target.evil and holds(target, 'Recluse') and g.script.jinxed('Recluse', self.name):
            game.inform(p, f'{snv.when(game)} — Ogre: {t} registered as evil to you: you are evil.')


# ---- Minions -----------------------------------------------------------------------------------------------------

async def psychopath_roshambo(game, me):
    """The Psychopath is executed: they and their nominator play roshambo, the Storyteller's judged call (a random draw
    for the scripted Storyteller: POLICY 'psychopath_roshambo_win'); won, they survive the execution."""
    g = game.g
    noms = [x for x in g.nominations if x['day'] == game.day and x['nominee'] == me.name]
    rival = noms[-1]['nominator'] if noms and noms[-1]['nominator'] != me.name else None
    won = (await game.decide_judged(judged(
        yes_choice(f'Psychopath roshambo:{me.name}', POLICY['psychopath_roshambo_win']), 'psychopath_roshambo',
        f'{me.name} (Psychopath) is executed and plays roshambo with {rival or "the Storyteller"}: does the Psychopath '
        'win (yes), and so survive?', about=me.name, recipient=me.name)))['yes']
    game.emit('text', {'text': f'{me.name} is executed and plays roshambo with {rival or "the Storyteller"}: '
                               f'{me.name} {"wins" if won else "loses"}.'})
    if won:
        g.add(State('safe', me.name, source=me.name, until='night', against='execution'))


class Psychopath(Minion):
    name = 'Psychopath'
    ability = ability(name)
    public_action = 'ability'  # the public choice, through the shared `ability` field (`target`)

    def act_publicly(self, game, actor, target, text=None):
        # "Each day, before nominations": on a public turn of the day (not during the nominations' comments), once a
        # day, alive; anyone may claim it (a bluff looks the same, and nothing happens). The kill is announced at once
        # (the town is not told why); it goes through the ordinary protections
        g = game.g
        p = g[actor]
        if game.phase != 'day' or not target or not (p.alive and self.name in g.abilities(p)):
            return False
        seen = g.notes.setdefault('Psychopath chose', {})
        if seen.get(p.name) == game.day:
            return False
        seen[p.name] = game.day
        if not g.works(p, self.name):
            snv.failed(game, p, self.name, 'nobody died')
            return False
        t = g[target]
        if t.appears_alive:
            game.ability_kill(t, 'psychopath', p)
            g.check_victory()
        return False

    async def before_execution(self, game, me, executed):
        # "If executed, you only die if you lose roshambo": a living Psychopath with a working ability, against the
        # player who nominated them (the Storyteller, for an execution with no nominator); the roshambo is announced
        g = game.g
        if executed is me and me.alive and me.character == self.name and g.works(me, self.name):
            await psychopath_roshambo(game, me)


async def wraith_guess(game, me, who):
    """The Alchemist/Magician jinxes with the Wraith: after an execution, `me` (living) may publicly guess a living
    player as the Wraith; right, the Demon must choose them tonight (Game.wake: 'Demon must choose')."""
    g = game.g
    alive = [q.name for q in g.living() if q is not me]
    if not (me.alive and alive) or g.winner:
        return
    req = game.request('night', f'Day {game.day} — {who}: you may publicly guess a living player as the Wraith '
                                '(`targets`; [] for no guess). If you are right, the Demon must choose them tonight.',
                       game.day, n_targets=1, options=alive, min_targets=0)
    t = game.targets(me.name, await game.ask(me.name, req), req)
    if not t:
        return
    game.emit('text', {'text': f'{me.name} publicly guesses that {t[0]} is the Wraith.'})
    if g[t[0]].character == 'Wraith':
        g.notes.setdefault('Demon must choose', {})[game.day + 1] = t[0]


class Wraith(Minion):
    name = 'Wraith'
    ability = ability(name)

    async def resolve_night(self, game, night):
        # its step, the night's first: "You may choose to open your eyes" (asked each night, `decide`); either way
        # it wakes with the other evil players
        g = game.g
        for p in [q for q in g.players if q.alive and self.name in g.abilities(q)]:
            opened = await carousel3.ask_yes(game, p, night.n, f'Night {night.n} — Wraith: do you open your eyes '
                                             'tonight? (`vote` true: at dawn you learn every player who woke tonight '
                                             'and whom they chose; false: only the evil players who woke, and whom '
                                             'they chose.)')
            g.notes.setdefault('Wraith eyes', {})[p.name] = (night.n, opened)

    async def end_of_night(self, game, me, night):
        # what it saw: who woke tonight to use an ability, and the players they chose (never what they were shown:
        # the Storyteller's tokens and fingers are hidden, a reading); eyes shut, only the evil players among them.
        # A drunk or poisoned Wraith sees nothing (a reading: no false wakes are staged)
        g = game.g
        if not (me.alive and self.name in g.abilities(me)):
            return
        n, opened = g.notes.get('Wraith eyes', {}).get(me.name, (None, False))
        opened = opened and n == night.n
        if not g.works(me, self.name):
            snv.failed(game, me, self.name, 'saw nothing')
            return
        seen = [x for x in dict.fromkeys(g.woke.get(night.n, [])) if x != me.name and (opened or g[x].evil)]
        parts = []
        for x in seen:
            chose = night.chosen.get(x) or []
            what = night.characters.get(x)
            parts.append(x + (f' (chose {", ".join(chose)}' + (f' and the {what}' if what else '') + ')' if chose
                              else f' (chose the {what})' if what else ''))
        game.inform(me, f'Night {night.n} — Wraith ({"eyes open" if opened else "with the evil players"}): '
                        + (f'awake tonight: {"; ".join(parts)}.' if parts else 'you saw nobody wake.'))


class Vizier(Minion):
    name = 'Vizier'
    ability = ability(name)
    setup_order = 9.5  # once the characters are final

    @staticmethod
    def declared(g):
        """"All players know you are the Vizier", unless the Alsaahir or Investigator jinx: the Storyteller doesn't
        declare it."""
        return not (g.script.jinxed('Vizier', 'Alsaahir') or g.script.jinxed('Vizier', 'Investigator'))

    def setup(self, game):
        # announced before the first night, in every player's introduction (the first night's announcement)
        g = game.g
        if not self.declared(g):
            return
        for v in [q for q in g.players if q.character == self.name]:
            for q in g.players:
                intro_line(g, q.name, f'The Storyteller announces: {v.name} is the Vizier.')

    def becomes(self, game, me):
        if self.declared(game.g):
            game.emit('text', {'text': f'The Storyteller announces: {me.name} is now the Vizier.'})

    @staticmethod
    def lost_by_jinx(g, me):
        """The Courtier and Preacher jinxes: the Vizier lost their ability to a Courtier's drunkenness or a Preacher."""
        from .carousel2 import preached
        if g.script.jinxed('Vizier', 'Preacher') and preached(g, me):
            return 'Preacher'
        if g.script.jinxed('Vizier', 'Courtier') and any(
                s.kind == 'drunk' and s.target == me.name and s.source and s.source in g.by_name and g.active(s)
                and 'Courtier' in g.abilities(g[s.source]) for s in g.states):
            return 'Courtier'
        return None

    def survives(self, game, me, cause):
        # "You cannot die during the day": every death by day (an execution survived, as the town sees it), while
        # their ability works, or (the Courtier and Preacher jinxes) they lost it to one of those
        g = game.g
        return game.tonight is None and me.character == self.name and (
            g.works(me, self.name) or (me.alive and self.lost_by_jinx(g, me) is not None))

    def end_of_night(self, game, me, night):
        g = game.g
        if me.character != self.name or not me.alive:
            return
        why = self.lost_by_jinx(g, me)
        told = g.notes.setdefault('Vizier told', {})
        if why and told.get(me.name) != why:  # "they learn this"
            told[me.name] = why
            game.woken(me)
            game.inform(me, f'Night {night.n} — Vizier: you have lost your ability (the {why}), but you still cannot '
                            'die during the day.')
        elif not why:
            told.pop(me.name, None)
        if g.script.jinxed(self.name, 'Fearmonger'):  # "The Vizier wakes with the Fearmonger, learns who they choose"
            for f, t in g.notes.get('Fear', {}).items():
                key = f'Vizier fear:{me.name}:{f}'
                if g.notes.get(key) != t:
                    g.notes[key] = t
                    game.woken(me)
                    game.inform(me, f'Night {night.n} — Vizier: the Fearmonger ({f}) has chosen {t}: you cannot '
                                    'execute them by your ability.')

    async def good_voted(self, game, me, voters):
        """Whether a good player voted (as they register to the Vizier: a Spy might register good, a Recluse evil; the
        Politician and Zealot jinxes: they might register evil), the Storyteller's judged call for each player who
        could register either way (POLICY 'vizier_registers_evil')."""
        g = game.g
        for x in voters:
            q = g[x]
            regs = set(g.registers_evil(q, me))
            if any(g.script.jinxed(self.name, c) and holds(q, c) for c in ('Politician', 'Zealot')):
                regs.add(True)
            if regs == {True}:
                continue
            if regs == {False}:
                return True
            if not (await game.decide_judged(judged(
                    yes_choice(f'Vizier sees:{x}', POLICY['vizier_registers_evil']), 'vizier_registers_evil',
                    f'{x} ({q.character}) voted: do they register as evil to the Vizier ({me.name}) (yes)?', about=x,
                    recipient=me.name)))['yes']:
                return True
        return False

    async def vote_over(self, game, me, nominee):
        # "If good voted, you may choose to execute immediately": after each vote any good player voted in, the living
        # Vizier with their ability is asked (`decide`); yes, the nominee is executed now, whatever the tally, and the
        # day's nominations end. Not the Magician (its jinx: immune), nor the Fearmonger's chosen player (its jinx)
        g = game.g
        if me.character != self.name or not g.works(me, self.name) or g.winner:
            return False
        if g.script.jinxed('Magician', self.name) and g[nominee].character == 'Magician':
            return False
        if g.script.jinxed(self.name, 'Fearmonger') and nominee in g.notes.get('Fear', {}).values():
            return False
        rec = g.nominations[-1] if g.nominations and g.nominations[-1]['nominee'] == nominee else {}
        if not await self.good_voted(game, me, rec.get('voters') or []):
            return False
        if not await carousel3.ask_yes(game, me, game.day, f'Day {game.day} — Vizier: a good player voted for '
                                       f'{nominee}. Do you execute {nominee} now (`vote` true), whatever the tally? '
                                       'It ends today\'s nominations.'):
            return False
        game.emit('text', {'text': f'{me.name}, the Vizier, chooses to execute {nominee} immediately.'})
        return True


CHARACTERS.update({c.name: c() for c in [BountyHunter, Engineer, Princess, Hermit, Ogre, Psychopath, Wraith,
                                         Vizier]})


# ---- Batch 4's jinxes (docs/carousel-rulings.md, batch 4) --------------------------------------------------------

jinx('Alchemist', 'Wraith', 'carousel3.ALCHEMIST_IN_PLAY, ALCHEMIST_NONE, Alchemist.execution, guess')
jinx('Al-Hadikhia', 'Princess', 'carousel5.Princess.resolve_night (Game.demon_kills_stopped)')
jinx('Boffin', 'Ogre', 'carousel3.BOFFIN_USABLE (never offered)')
jinx('Bounty Hunter', 'Kazali', 'carousel5.BountyHunter.setup, made_late')
jinx('Bounty Hunter', 'Philosopher', 'carousel5.BountyHunter.becomes')
jinx('Cannibal', 'Princess', 'carousel5.Princess.stops')
jinx('Magician', 'Vizier', 'carousel.Magician.vizier_nulled, shown_to_evil; carousel5.Vizier.vote_over')
jinx('Magician', 'Wraith', 'carousel.Magician.execution; carousel5.wraith_guess')
jinx('Pit-Hag', 'Ogre', 'snv.PitHag.resolve_night; carousel5.Ogre.resolve_night')
jinx('Plague Doctor', 'Wraith', 'carousel.PlagueDoctor.gain, minion_gains')
jinx('Recluse', 'Ogre', 'carousel5.Ogre.resolve_night')
jinx('Spy', 'Ogre', 'carousel5.Ogre.resolve_night')
jinx('Summoner', 'Engineer', 'carousel5.Engineer.make_minions, storyteller_step, overrides_end')
jinx('Vizier', 'Alsaahir', 'carousel5.Vizier.declared')
jinx('Vizier', 'Investigator', 'carousel5.Vizier.declared')
jinx('Vizier', 'Courtier', 'carousel5.Vizier.lost_by_jinx, survives, end_of_night')
jinx('Vizier', 'Preacher', 'carousel5.Vizier.lost_by_jinx, survives, end_of_night')
jinx('Vizier', 'Fearmonger', 'carousel5.Vizier.end_of_night, vote_over')
jinx('Vizier', 'Politician', 'carousel5.Vizier.good_voted')
jinx('Vizier', 'Zealot', 'carousel5.Vizier.good_voted')
