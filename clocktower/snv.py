"""Sects & Violets' characters, on the script-independent core (characters.py, state.py, game.py).

Each entry follows the almanac's How to Run. Where the rules leave a question open, a comment says which reading
the entry takes, and why (docs/snv-rulings.md lists them for review).
"""
from __future__ import annotations
from itertools import combinations

from .characters import CHARACTERS, Choose, Demon, Minion, kind
from .state import POLICY, Choice, State, judged


def ability(name):
    """The official ability text."""
    from . import official
    return official.role(name)['ability']


def townsfolk(q):
    return kind(q.character) == 'Townsfolk'


def final_night(g):
    """Whether tonight is (likely) the final night: few enough players alive (POLICY 'final_night_alive')."""
    return g.alive_count() <= POLICY['final_night_alive']


# ---- Minions ---------------------------------------------------------------------------------------------------

class Witch(Minion):
    name = 'Witch'
    ability = ability(name)
    night_choice = Choose(players=1, prompt='Choose a player: if they nominate tomorrow, they die.')

    @staticmethod
    def lost(g):
        """"If just 3 players live, you lose this ability": at once, a curse already made included."""
        return g.alive_count() <= 3

    def night_spec(self, game, me, night):
        return None if self.lost(game.g) else self.night_choice

    async def resolve_night(self, game, night):
        g = game.g
        w, t = night.choice_of(g, self.name)
        if t and g.works(w, self.name) and not self.lost(g):
            # for tomorrow only; a drunk Witch's choice is wasted; a curse is paused while the Witch is drunk or
            # poisoned and resumes when they sober up (the rulebook's example), and ends if they die (unless the
            # Vigormortis killed them: they keep their ability)
            g.add(State('cursed', t, source=w.name, until='night', ends_with_source=True, while_source_works=True))

    def nomination(self, game, me, nominator, nominee):
        g = game.g
        if self.lost(g) or not g.works(me, self.name):
            return
        if any(s.kind == 'cursed' and s.source == me.name and s.target == nominator and g.active(s)
               for s in g.states):
            game.ability_kill(g[nominator], 'witch', me)  # declared at once; the nomination still stands


class Cerenovus(Minion):
    name = 'Cerenovus'
    ability = ability(name)
    night_choice = Choose(players=1, character=True, kinds=('Townsfolk', 'Outsider'),
                          prompt='Choose a player and a good character (`character`): tomorrow they must be "mad" '
                                 'that they are this character, trying to convince the group, or they might be '
                                 'executed.')

    async def resolve_night(self, game, night):
        g = game.g
        c, t = night.choice_of(g, self.name)
        about = night.characters.get(c.name) if c else None
        if not (t and about):
            return
        if g.works(c, self.name):
            # for tomorrow; it ends if the Cerenovus loses their ability (dies, unless kept, or is drunk or poisoned)
            g.add(State('mad', t, source=c.name, until='night', ends_with_source=True, while_source_works=True,
                        about=about))
        # the target is told even when the Cerenovus is drunk or poisoned (a reading: the wasted ability gives
        # nothing away; nobody is executed for it)
        game.inform(g[t], f'Night {night.n}: the Cerenovus selected you. Tomorrow you must be "mad" that you are '
                          f'the {about}: do your best to convince the group that you are the {about}, or the '
                          'Storyteller might execute you. (Hinting, or saying you are mad, is not enough.)')

    async def moment(self, game, me, when):
        # judged once, when the day's talk is done and before nominations open (a reading): a madness execution then
        # is the day's execution, and the day goes to night without nominations
        if when != 'nominations':
            return
        g = game.g
        for s in [s for s in g.states if s.kind == 'mad' and s.source == me.name and g.active(s)]:
            if await game.judge_madness(g[s.target], s.about, since=game.day):
                return


def arbitrary_deaths_choice(g, ph, new, was_demon):
    """The Pit-Hag made a Demon: "deaths tonight are arbitrary". Who else dies tonight (at most two players, as
    attacks of the Pit-Hag), and whether the Demons' attacks still kill (yes). The scripted style follows the almanac:
    a Demon made into another Demon, usually nobody dies (the town sees the change); a new evil Demon, usually the
    old Demon dies too; a good Demon on the final night, usually the evil Demon dies; otherwise as usual."""
    alive = [q.name for q in g.living()]
    others = [q.name for q in g.living() if q.is_demon and q is not new]
    values = [{'players': list(c), 'yes': y} for k in range(3) for c in combinations(alive, k) for y in (True, False)]

    def style(r):
        if was_demon:
            return {'players': [], 'yes': r.random() >= POLICY['pithag_quiet']}
        if new.evil:
            return {'players': others[:2] if others and r.random() < POLICY['pithag_kill_old_demon'] else [],
                    'yes': True}
        if final_night(g) and others and r.random() < POLICY['pithag_final_kill']:
            evil = [x for x in others if g[x].evil] or others
            return {'players': [r.choice(evil)], 'yes': True}
        return {'players': [], 'yes': True}
    return judged(Choice(f'Pit-Hag deaths:{new.name}', values, style), 'arbitrary_deaths',
                  f'The Pit-Hag ({ph.name}) made {new.name} ({new.alignment}) the {new.character}'
                  f'{" (they were a Demon)" if was_demon else ""}. Deaths tonight are arbitrary: who else dies '
                  '(players), and do the Demons\' attacks still kill (yes)? The almanac: a Demon into another Demon, '
                  'best that nobody dies; a new evil Demon, kill the old one; a good Demon, kill either Demon on the '
                  'final night, else let both run.', about=new.name, recipient=ph.name)


class PitHag(Minion):
    name = 'Pit-Hag'
    ability = ability(name)
    night_choice = Choose(players=1, character=True,
                          prompt='Choose a player and a character (`character`) they become, if that character is not '
                                 'in play. If you make a Demon, deaths tonight are arbitrary.')

    async def resolve_night(self, game, night):
        g = game.g
        ph, t = night.choice_of(g, self.name)
        c = night.characters.get(ph.name) if ph else None
        if not (t and c) or not g.works(ph, self.name):
            return
        if any(q.character == c for q in g.players):
            return  # in play (a dead player's character too; a Drunk's apparent one is not): nothing happens
        target = g[t]
        was_demon = target.is_demon
        await game.change(target, character=c)  # a dead player too; their alignment stays
        if kind(c) == 'Demon':
            plan = await game.decide_judged(arbitrary_deaths_choice(g, ph, target, was_demon))
            if not plan['yes']:
                g.notes['Demon kills stopped'] = night.n
            for x in plan['players']:
                game.attempt_kill(g[x], 'pit-hag', ph, night)


def twin_choice(g, et):
    """The Evil Twin's twin: a player of the other alignment (at setup, any good player). On the final night (a
    Pit-Hag's new Evil Twin), the Demon or a dead player, so the good team can still win."""
    opposing = [q.name for q in g.players if q is not et and q.alignment != et.alignment]
    late = [x for x in opposing if g[x].is_demon or not g[x].alive] if final_night(g) and g.day > 1 else []

    def style(r):
        return {'players': [r.choice(late or opposing)]}
    return judged(Choice(f'Twin:{et.name}', [{'players': [x]} for x in opposing], style), 'twin',
                  f'Who is the Evil Twin\'s ({et.name}, {et.alignment}) twin: a player of the other alignment? Any; '
                  'rarely a Traveller; if a new Evil Twin appears on the final night, the Demon or a dead player.',
                  about=et.name, recipient=et.name)


class EvilTwin(Minion):
    name = 'Evil Twin'
    ability = ability(name)
    setup_order = 6

    @staticmethod
    def twin(g, me):
        name = g.notes.get('Twins', {}).get(me.name)
        return g[name] if name else None

    async def pair(self, game, me):
        """A new twin for `me` (setup; a new Evil Twin; a twin now on the same side): the Storyteller's choice."""
        g = game.g
        choice = twin_choice(g, me)
        if choice.values:
            g.notes.setdefault('Twins', {})[me.name] = (await game.decide_judged(choice))['players'][0]
        else:
            g.notes.setdefault('Twins', {}).pop(me.name, None)

    def introduce(self, game, me, when):
        """Both twins learn each other: the twin learns the Evil Twin, the Evil Twin the twin's character."""
        g, twin = game.g, self.twin(game.g, me)
        if not twin:
            return
        game.woken(me)
        game.inform(me, f'{when} — Evil Twin: your twin is {twin.name}, the {twin.character}. They know that you '
                        'are the Evil Twin.')
        game.inform(twin, f'{when}: {me.name} is the Evil Twin, and your twin. You know each other: they know your '
                          'character.')
        g.reminders.append(f'{me.name} (Evil Twin, {me.alignment}) and {twin.name} ({twin.character}, '
                           f'{twin.alignment}) are twins.')

    async def setup(self, game):
        et = game.g.with_character(self.name)
        if et:
            await self.pair(game, et)

    async def resolve_night(self, game, night):
        et = game.g.with_character(self.name)
        if et and night.first:
            self.introduce(game, et, f'Night {night.n}')

    async def becomes(self, game, me):
        # a new Evil Twin (the Pit-Hag's) is paired at once with a player of the other alignment, and both learn it
        await self.pair(game, me)
        self.introduce(game, me, f'Night {game.day}' if game.tonight is not None else f'Day {game.day}')

    async def changed(self, game, me, other):
        twin = self.twin(game.g, me)
        if (other is me or other is twin) and (twin is None or twin.alignment == me.alignment):
            # "If both Twins are the same alignment, the Storyteller chooses a new Twin"
            await self.pair(game, me)
            self.introduce(game, me, f'Night {game.day}' if game.tonight is not None else f'Day {game.day}')

    def execution(self, game, me, executed):
        g, twin = game.g, self.twin(game.g, me)
        if not twin or not g.works(me, self.name) or twin.alignment == me.alignment:
            return None
        good = me if not me.evil else twin
        if executed is good:  # whichever twin is good (a good Evil Twin too), executed alive or dead (a reading)
            return 'evil', f'{good.name}, the good twin, was executed while the Evil Twin ({me.name}) lives.'
        return None

    def overrides_end(self, g, me, winner, reason):
        twin = self.twin(g, me)
        if (winner == 'good' and twin and me.alive and twin.alive and twin.alignment != me.alignment
                and g.works(me, self.name)):
            return False  # "Good can't win if you both live": the game goes on
        return None


# ---- Demons ----------------------------------------------------------------------------------------------------

class Killer(Demon):
    """A Demon that chooses a player each night but the first: they die."""
    night_choice = Choose(players=1, prompt='Choose a player: they die.')
    kills_at_night = True

    async def resolve_night(self, game, night):
        g = game.g
        d, t = night.choice_of(g, self.name)
        if t and g.works(d, self.name):
            await self.attack(game, d, g[t], night)

    async def attack(self, game, me, target, night):
        await game.demon_attack_judged(target, me, night)


class FangGu(Killer):
    name = 'Fang Gu'
    ability = ability(name)
    outsiders = 1

    async def attack(self, game, me, target, night):
        g = game.g
        jumps = (kind(target.character) == 'Outsider' and not g.notes.get('Fang Gu once') and target.alive
                 and not target.seems_dead and not game.demon_kills_stopped(night))
        if not jumps:
            await game.demon_attack_judged(target, me, night)  # a dead Outsider can't die again: nothing happens
            return
        if game.prevent_death(target, 'demon'):
            return  # the Outsider doesn't die: no jump, and the Fang Gu lives
        g.notes['Fang Gu once'] = True  # once per game, whatever happens to this Fang Gu later
        # the Outsider becomes an evil Fang Gu (told so; they learn no Minions), then the old one dies
        await game.change(target, character=self.name, alignment='evil')
        game.kill(me, 'fang gu', me)
        night.deaths.append(me)


def vigormortis_choice(g, vig, minion):
    """Which of the dead Minion's nearest Townsfolk (one each way round the circle, alive or dead) is poisoned."""
    near = {}
    for step in (1, -1):
        q = g.nearest(minion, step, townsfolk)
        if q and q.name not in near:
            near[q.name] = step
    choice = Choice(f'Vigormortis:{minion.name}', [{'players': [x]} for x in near] or [{'players': []}],
                    lambda r: {'players': [r.choice(list(near))] if near else []})
    choice.sides = near
    return judged(choice, 'vigormortis_poison',
                  f'The Vigormortis ({vig.name}) killed {minion.name}, a Minion, who keeps their ability: which of '
                  f'their Townsfolk neighbours ({", ".join(near) or "none"}) is poisoned?', about=minion.name,
                  recipient=vig.name)


class Vigormortis(Killer):
    name = 'Vigormortis'
    ability = ability(name)
    outsiders = -1  # with no Outsider to remove, no Townsfolk is added (state.team_sizes' floor)
    derives = True

    async def attack(self, game, me, target, night):
        g = game.g
        if kind(target.character) != 'Minion' or not target.alive:
            await game.demon_attack_judged(target, me, night)
            return
        # a Minion it kills keeps their ability while dead, as long as the Vigormortis has its own (alive, sober and
        # healthy) and they are still a Minion; kept from the moment they die, so their effects carry on (the
        # almanac's Witch, whose curse made tonight still kills)
        keep = State('has ability', target.name, source=me.name, until=None, ends_with_source=True,
                     while_source_works=True, about='Minion')
        g.add(keep)
        if await game.attempt_kill_judged(target, 'demon', me, night) is not target:
            g.states = [s for s in g.states if s is not keep]
            return
        choice = vigormortis_choice(g, me, target)
        value = await game.decide_judged(choice)
        side = choice.sides.get((value['players'] or [None])[0], 1)
        g.notes.setdefault('Vigormortis', {}).setdefault(me.name, {})[target.name] = side

    def ongoing(self, g, me):
        # each kept Minion poisons the nearest Townsfolk on the side the Storyteller chose, recomputed (so one
        # Townsfolk per Minion is always poisoned); all of it ends when the Vigormortis loses its ability. A dead
        # Minion who is drunk or poisoned loses their own ability, but the poison is the Vigormortis's (a reading)
        if not g.works(me, self.name):
            return []
        out = []
        for m, step in g.notes.get('Vigormortis', {}).get(me.name, {}).items():
            minion = g[m]
            kept = any(s.kind == 'has ability' and s.target == m and s.source == me.name for s in g.states)
            if kept and kind(minion.character) == 'Minion':
                t = g.nearest(minion, step, townsfolk)
                if t:
                    out.append(State('poisoned', t.name, source=me.name, until=None))
        return out


class NoDashii(Killer):
    name = 'No Dashii'
    ability = ability(name)
    derives = True

    def ongoing(self, g, me):
        # the nearest Townsfolk each way round the circle, alive or dead (Outsiders and Minions are skipped), from
        # the start of the game, recomputed whenever asked; healthy again once the No Dashii loses its ability
        if not g.works(me, self.name):
            return []
        near = {q.name for q in (g.nearest(me, 1, townsfolk), g.nearest(me, -1, townsfolk)) if q}
        return [State('poisoned', n, source=me.name, until=None) for n in sorted(near, key=lambda n: g[n].seat)]


class Vortox(Killer):
    name = 'Vortox'
    ability = ability(name)
    falsifies_info = True

    def falsifies(self, g, me, recipient, ability):
        # every Townsfolk ability's information, drunk, poisoned or not, while the Vortox has its ability; not a
        # character or alignment change, nor Outsider or Minion information
        return kind(ability) == 'Townsfolk' and g.works(me, self.name)

    def end_of_day(self, game, me):
        g = game.g
        if not game.executed_today and g.works(me, self.name) and not g.winner:
            g.winner, g.reason = 'evil', 'Nobody was executed today, and the Vortox lives.'


CHARACTERS.update({c.name: c() for c in [Witch, Cerenovus, PitHag, EvilTwin, FangGu, Vigormortis, NoDashii, Vortox]})
