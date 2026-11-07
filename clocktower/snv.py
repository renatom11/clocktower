"""Sects & Violets' characters, on the script-independent core (characters.py, state.py, game.py).

Each entry follows the almanac's How to Run. Where the rules leave a question open, a comment says which reading
the entry takes, and why (docs/snv-rulings.md lists them for review).
"""
from __future__ import annotations
from itertools import combinations, product
import dataclasses
import re

from .characters import CHARACTERS, SETUPS, Choose, Demon, Minion, Outsider, Townsfolk, kind, rules, settle
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


def failed(game, p, ability, why):
    """p's ability would have acted but p is drunk or poisoned: an abnormal result for the Mathematician."""
    if game.g.impaired(p):
        game.abnormal(p, ability, why)


# Once-per-game abilities are spent per player, not per character (Grimoire.spend), since two players can have one: a
# Philosopher who gained it, and the original player, drunk. A player who becomes the character later starts fresh.
def used(g, p, name):
    return name in g.notes.get('Used', {}).get(p.name, ())


def use(g, p, name):
    g.notes.setdefault('Used', {}).setdefault(p.name, []).append(name)


def fresh(g, p, name):
    left = [x for x in g.notes.get('Used', {}).get(p.name, ()) if x != name]
    if p.name in g.notes.get('Used', {}):
        g.notes['Used'][p.name] = left


def holders(g, night, name):
    """The living players with `name`'s ability (their own, or one gained: the Philosopher's) who chose tonight at its
    step, with their first choice: several can have it (the Philosopher, and the original player made drunk)."""
    return [(p, (night.chosen[p.name] or [None])[0]) for p in g.players
            if p.alive and name in g.abilities(p) and p.name in night.chosen]


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
        if t and not self.lost(g) and not g.works(w, self.name):
            failed(game, w, self.name, 'no curse')
        if t and g.works(w, self.name) and not self.lost(g):
            # for tomorrow only; a drunk Witch's choice is wasted; a curse is paused while the Witch is drunk or
            # poisoned and resumes when they sober up (the rulebook's example), and ends if they die (unless the
            # Vigormortis killed them: they keep their ability)
            g.add(State('cursed', t, source=w.name, until='night', ends_with_source=True, while_source_works=True))

    def nomination(self, game, me, nominator, nominee):
        g = game.g
        if self.lost(g):
            return
        if not g.works(me, self.name):
            if any(s.kind == 'cursed' and s.source == me.name and s.target == nominator for s in g.states):
                failed(game, me, self.name, 'a cursed nominator lived')  # the almanac's drunk Witch
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

    def night_spec(self, game, me, night):
        if game.g.script.jinxed(self.name, 'Goblin'):  # the jinx (custom scripts): the Goblin may be named too
            return dataclasses.replace(self.night_choice, also=('Goblin',))
        return self.night_choice

    async def resolve_night(self, game, night):
        g = game.g
        c, t = night.choice_of(g, self.name)
        about = night.characters.get(c.name) if c else None
        if not (t and about):
            return
        if not g.works(c, self.name):
            failed(game, c, self.name, 'nobody made mad')
        else:
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


def arbitrary_deaths_choice(g, ph, new, was_demon, by='Pit-Hag'):
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
    return judged(Choice(f'{by} deaths:{new.name}', values, style), 'arbitrary_deaths',
                  f'The {by} ({ph.name}) made {new.name} ({new.alignment}) the {new.character}'
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
        if not (t and c):
            return
        idiots = sum(1 for q in g.players if q.character == c) if c == 'Village Idiot' else 0
        extra_idiot = idiots and idiots < 3 and g.script.jinxed(self.name, c)  # (custom scripts: a spare token)
        if any(q.character == c for q in g.players) and not extra_idiot:
            return  # in play (a dead player's character too; a Drunk's apparent one is not): nothing happens
        if c == 'Marionette' and 'Marionette' in g.script.all:
            return  # (custom scripts: the Marionette starts beside the Demon or not at all, docs/carousel-rulings.md)
        if g.script.clash({q.character for q in g.players if q.name != t} | {c}):
            return  # the Heretic jinxes (custom scripts): only one of the pair can be in play
        if c == 'Leviathan' and g.script.jinxed(self.name, c) and g.day > 5:
            return  # the jinx (custom scripts): the Leviathan cannot enter play after day 5
        if not g.works(ph, self.name):
            failed(game, ph, self.name, 'no change')
            return
        target = g[t]
        if c == 'Damsel' and g.script.jinxed(self.name, c):
            # the jinx (custom scripts): the Storyteller chooses which player becomes the Damsel (carousel.py)
            from .carousel import damsel_choice
            target = g[(await game.decide_judged(damsel_choice(g, ph, target)))['players'][0]]
        was_demon = target.is_demon
        await game.change(target, character=c)  # a dead player too; their alignment stays
        if extra_idiot:  # the jinx (batch 3): with another Village Idiot, the drunk one might change
            await rules(c).mark_drunk(game, again=True)
        if c in ('Goon', 'Politician', 'Cult Leader', 'Ogre') and g.script.jinxed(self.name, c):
            # the jinxes (custom scripts): an evil player made the Goon (or the Politician, or the Cult Leader) can't
            # turn good by its own ability; a good one made it later is free again (docs/carousel-rulings.md, 9, batch
            # 1 and batch 3b)
            locked = g.notes.setdefault({'Goon': 'Evil Goons', 'Politician': 'Evil Politicians',
                                         'Ogre': 'Evil Ogres'}.get(c, 'Evil Cult Leaders'), [])
            if target.evil and target.name not in locked:
                locked.append(target.name)
            elif not target.evil and target.name in locked:
                locked.remove(target.name)
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
        if not twin or twin.alignment == me.alignment:
            return None
        good = me if not me.evil else twin
        if executed is not good:
            return None
        if not g.works(me, self.name):
            if me.alive or g.keeps_ability(me):
                failed(game, me, self.name, 'the good twin was executed')
            return None
        # whichever twin is good (a good Evil Twin too), executed alive or dead (a reading)
        return 'evil', f'{good.name}, the good twin, was executed while the Evil Twin ({me.name}) lives.'

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
        elif t and d:
            failed(game, d, self.name, 'no attack')  # a drunk or poisoned Demon kills nobody

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

    def dies(self, game, me, cause):
        # the Mastermind jinx (custom scripts): a dead Mastermind who has their ability through this Vigormortis now
        # (it is alive, sober and healthy: "that has their ability") keeps it when the Vigormortis dies, for good: the
        # kept state no longer depends on the Vigormortis (docs/carousel-rulings.md, 5)
        g = game.g
        if g.script.jinxed('Mastermind', self.name):
            keep = [s.kind == 'has ability' and s.source == me.name and g.active(s)
                    and g[s.target].character == 'Mastermind' for s in g.states]
            g.states = [State('has ability', s.target, until=None, about=s.about) if k else s
                        for s, k in zip(g.states, keep)]
        return None

    def hand_over(self, g, old, new):
        # the kept abilities and their poison belong to the Vigormortis character, not its player: charmed by the
        # Snake Charmer (or swapped by the Barber), the new Vigormortis keeps its dead Minions (batch 3's ruling)
        keep = [s for s in g.states if s.kind == 'has ability' and s.source == old.name]
        g.states = [s for s in g.states if not any(s is k for k in keep)]
        sides = g.notes.get('Vigormortis', {}).pop(old.name, None)
        if sides:
            g.notes['Vigormortis'].setdefault(new.name, {}).update(sides)
        return keep

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



# ---- Townsfolk -------------------------------------------------------------------------------------------------
# Each information result is a Choice through Game.decide_judged with the truth (what a working ability could show),
# so a drunk or poisoned player (the No Dashii's neighbours) may be misinformed, falsified information (the Vortox)
# is only false, and a false result is an abnormal one for the Mathematician (Game.note_information).

def believers(g, name, alive=True):
    """The players with `name`'s ability (their own or one gained) or who believe they have it; alive, by default."""
    return [p for p in g.players if (p.alive or not alive) and (p.shown == name or name in g.abilities(p))]


def when(game):
    return f'Night {game.day}' if game.tonight is not None else f'Day {game.day}'


async def learn(game, p, role, choice, text):
    """The Storyteller decides `choice` (judged) and tells p, who woke for it, what `text(value)` says."""
    v = await game.decide_judged(choice)
    game.woken(p)
    game.inform(p, f'{when(game)} — {role}: {text(v)}')
    return v


def info(choice, g, p, role, question, truth, impaired, about=None, **more):
    return judged(choice, 'information', question, about=about, recipient=p.name, impaired=impaired, truth=truth,
                  ability=role, **more)


def steps_between(g, a, b):
    """Seats from a to b the short way round the circle, the dead included (the Clockmaker's count)."""
    d = (b.seat - a.seat) % len(g.players)
    return min(d, len(g.players) - d)


def clockmaker_choice(g, p):
    """The steps from the Demon to its nearest Minion, by character type (a good Minion counts). None if there is
    no Demon or no Minion. A misinformed Clockmaker gets the distance in their false world (Grimoire.decoy)."""
    demons = [q for q in g.players if q.is_demon]
    minions = [q for q in g.players if kind(q.character) == 'Minion']
    if g.script.jinxed('Clockmaker', 'Summoner'):  # the jinx (custom scripts): the Summoner registers as the Demon
        summoners = [q for q in minions if q.character == 'Summoner']
        demons, minions = demons + summoners, [q for q in minions if q not in summoners]
    if not (demons and minions):
        return None
    true = min(steps_between(g, d, m) for d in demons for m in minions)
    impaired = g.unreliable(p, 'Clockmaker')
    values = list(range(1, len(g.players) // 2 + 1)) if impaired else [true]

    def world(r):
        framed, evil = g.decoy(p, r)
        return min([steps_between(g, g[framed], g[m]) for m in evil if m != framed] or [true])

    def style(r):
        if impaired and g.misinformed(p, r):
            return {'number': g.false_result(p, r, world, {true})}
        return {'number': true}
    return info(Choice(f'Clockmaker:{p.name}', [{'number': x} for x in values], style), g, p, 'Clockmaker',
                f'How many steps from the Demon to its nearest Minion does {p.name} (Clockmaker) learn?',
                lambda v: v['number'] == true, impaired)


class Clockmaker(Townsfolk):
    name = 'Clockmaker'
    ability = ability(name)
    info = True

    async def show(self, game, p):
        choice = clockmaker_choice(game.g, p)
        if choice:
            await learn(game, p, self.name, choice,
                        lambda v: f'the Demon is {v["number"]} step{"" if v["number"] == 1 else "s"} from its '
                                  'nearest Minion.')

    async def resolve_night(self, game, night):
        if night.first:
            for p in believers(game.g, self.name):
                await self.show(game, p)

    async def becomes(self, game, me):
        # a player who becomes the Clockmaker later (the Pit-Hag's) learns it at once: a new character's ability is
        # theirs even if it is a "you start knowing" one (the Barber's almanac). On the first night, at the step
        if me.alive and not (game.tonight is not None and game.tonight.first):
            await self.show(game, me)


SECRETIVE = ('Snake Charmer', 'Sage', 'Mutant', 'Klutz')  # the almanac's "more secretive" good characters


def dreamer_choice(g, p, t, claim=None):
    """1 good and 1 evil character (by type: Townsfolk or Outsider, Minion or Demon), one of which `t` is (registers
    as). The scripted style follows the almanac: for a good-type player, a Minion in play (POLICY
    'dreamer_minion_in_play') or any evil character; for an evil-type one, the good character they claimed aloud
    ('dreamer_bluff'), a secretive one ('dreamer_secretive') or another, never the Dreamer's own. Misinformed:
    neither is correct."""
    target = g[t]
    shows = g.registers_as(target)
    good, evil = g.script.good, g.script.minions + g.script.demons
    impaired = g.unreliable(p, 'Dreamer')
    correct = lambda v: any(c in shows for c in v['characters'])
    pairs = [{'characters': [a, b]} for a in good for b in evil]
    values = pairs if impaired else [v for v in pairs if correct(v)]
    if not values:
        return None
    minions_in_play = [q.character for q in g.players if kind(q.character) == 'Minion' and q.character in evil]

    def false_evil(r, avoid):
        pool = [c for c in minions_in_play if c not in avoid]
        if pool and r.random() < POLICY['dreamer_minion_in_play']:
            return r.choice(pool)
        return r.choice([c for c in evil if c not in avoid] or evil)

    def false_good(r, avoid):
        avoid = set(avoid) | {p.shown}
        if claim in good and claim not in avoid and r.random() < POLICY['dreamer_bluff']:
            return claim
        secretive = [c for c in SECRETIVE if c in good and c not in avoid]
        if secretive and r.random() < POLICY['dreamer_secretive']:
            return r.choice(secretive)
        for _ in range(30):
            c = g.fake_good(r, (g.script.townsfolk, g.script.outsiders), avoid=avoid)
            if c in good:
                return c
        return r.choice([c for c in good if c not in avoid] or good)

    def style(r):
        if impaired and g.misinformed(p, r):  # neither: an evil player shown as their claim, if they made one
            return {'characters': [false_good(r, shows), false_evil(r, shows)]}
        c = target.character if target.character in shows else sorted(shows)[0]
        return {'characters': [c, false_evil(r, {c})] if c in good else [false_good(r, {c}), c]}

    choice = Choice(f'Dreamer:{p.name}', values, lambda r: None)
    choice.style = lambda r: (lambda v: v if choice.legal(v) else r.choice(values))(style(r))
    return info(choice, g, p, 'Dreamer', f'{p.name} (Dreamer) chose {t}: which good character and which evil '
                f'character are they shown, one of which {t} is?', correct, impaired, about=t, players=[t])


class Dreamer(Townsfolk):
    name = 'Dreamer'
    ability = ability(name)
    info = True
    night_choice = Choose(players=1, may_self=False, prompt='Choose a player (not yourself): you learn 1 good and 1 '
                                                            'evil character, 1 of which is correct.')

    async def resolve_night(self, game, night):
        from .judge import claims
        g = game.g
        for p in believers(g, self.name):
            t = (night.chosen.get(p.name) or [None])[0]
            choice = dreamer_choice(g, p, t, claims(game, 'public').get(t)) if t else None
            if choice:
                await learn(game, p, self.name, choice,
                            lambda v: f'{t} is either the {v["characters"][0]} or the {v["characters"][1]}.')


class SnakeCharmer(Townsfolk):
    name = 'Snake Charmer'
    ability = ability(name)
    night_choice = Choose(players=1, alive_only=True,
                          prompt='Choose an alive player: if they are the Demon, you swap characters and alignments '
                                 'with them, and they are then poisoned.')

    async def resolve_night(self, game, night):
        for sc, t in holders(game.g, night, self.name):  # a Philosopher-Snake Charmer too
            await self.charm(game, sc, t)

    async def charm(self, game, sc, t):
        g = game.g
        if not t or not g[t].is_demon or g[t] is sc or self.name not in g.abilities(sc):
            return  # not the Demon: nothing happens (themself included); or no longer a Snake Charmer tonight
        d = g[t]
        if not g.works(sc, self.name):
            failed(game, sc, self.name, 'charmed the Demon')  # the wiki's poisoned Snake Charmer
            return
        # not information, so the Vortox doesn't touch it; each is told their new character and alignment (both
        # evil stay evil: the Pit-Hag's Snake Charmer). The old Demon is poisoned for the rest of the game, whatever
        # happens later (a reading of "permanently": a later change keeps it). The new Demon, if its step is still to
        # come tonight, acts tonight; it learns no Minions
        await game.swap(sc, d, alignments=True)
        g.add(State('poisoned', d.name, source=sc.name, until=None))


def abnormal_since_dawn(g, me, n):
    """Players (other than `me`) whose abilities worked abnormally since dawn, as of night n: on day n-1 and tonight
    (on the first night, since the game began)."""
    return sorted({a['player'] for a in g.abnormal if a['player'] != me.name
                   and ((a['phase'] == 'night' and a['day'] == n) or (a['phase'] == 'day' and a['day'] == n - 1))})


def mathematician_choice(g, p, n):
    """How many players' abilities worked abnormally since dawn (Grimoire.abnormal). Misinformed: a number one or two
    off, as small numbers are what Mathematicians usually see."""
    true = len(abnormal_since_dawn(g, p, n))
    impaired = g.unreliable(p, 'Mathematician')
    values = list(range(0, len(g.players))) if impaired else [true]

    def style(r):
        if impaired and g.misinformed(p, r):
            return {'number': r.choice([x for x in (true - 1, true + 1, true + 1, true + 2) if x >= 0])}
        return {'number': true}
    return info(Choice(f'Mathematician:{p.name}', [{'number': x} for x in values], style), g, p, 'Mathematician',
                f'How many players\' abilities worked abnormally since dawn because of another character\'s ability '
                f'does {p.name} (Mathematician) learn?', lambda v: v['number'] == true, impaired)


def lunatic_attacked_elsewhere(game, night):
    """The Mathematician/Lunatic jinx (custom scripts): tonight's Lunatic attacked a different player than the real
    Demon did, an abnormal result (recorded once a night, before the Mathematician counts). Both must have chosen
    tonight; a different set of players (the Po's none, or three) is different (docs/carousel-rulings.md, 8)."""
    g = game.g
    lun, demon = g.with_character('Lunatic'), g.demon()
    if not (lun and demon and lun.name in night.chosen and demon.name in night.chosen):
        return
    if any(a['player'] == lun.name and a['day'] == night.n and a['phase'] == 'night' and a['ability'] == 'Lunatic'
           for a in g.abnormal):
        return
    if set(night.chosen[lun.name] or ()) != set(night.chosen[demon.name] or ()):
        game.abnormal(lun, 'Lunatic', 'attacked a different player than the Demon')


class Mathematician(Townsfolk):
    name = 'Mathematician'
    ability = ability(name)
    info = True

    async def resolve_night(self, game, night):
        if game.g.script.jinxed(self.name, 'Lunatic'):
            lunatic_attacked_elsewhere(game, night)
        for p in believers(game.g, self.name):
            await learn(game, p, self.name, mathematician_choice(game.g, p, night.n),
                        lambda v: ("1 player's ability" if v['number'] == 1 else f"{v['number']} players' "
                                   'abilities') + ' worked abnormally since dawn.')


def yes_no(g, p, role, true, question):
    """A yes or no a working ability gives as `true`; misinformed, the other."""
    impaired = g.unreliable(p, role)

    def style(r):
        return {'yes': not true if impaired and g.misinformed(p, r) else true}
    return info(Choice(f'{role}:{p.name}', [{'yes': x} for x in ([True, False] if impaired else [true])], style),
                g, p, role, question, lambda v: v['yes'] == true, impaired)


def demon_voted(g, day):
    """Whether a Demon (any, dead too, as they were when they voted) voted for an execution on `day`."""
    return any(kind(c) == 'Demon' for x in g.nominations if x['day'] == day for c in x.get('characters', {}).values())


def minion_nominated(g, day):
    """Whether a Minion (as they were when they nominated) made a nomination on `day`."""
    return any(kind(x.get('character') or g[x['nominator']].character) == 'Minion'
               for x in g.nominations if x['day'] == day)


class Flowergirl(Townsfolk):
    name = 'Flowergirl'
    ability = ability(name)
    info = True

    async def resolve_night(self, game, night):
        if night.first:
            return
        for p in believers(game.g, self.name):
            choice = yes_no(game.g, p, self.name, demon_voted(game.g, night.n - 1),
                            f'Did a Demon vote today (yes: true)? What does {p.name} (Flowergirl) learn?')
            await learn(game, p, self.name, choice,
                        lambda v: 'YES, a Demon voted today.' if v['yes'] else 'NO, no Demon voted today.')


class TownCrier(Townsfolk):
    name = 'Town Crier'
    ability = ability(name)
    info = True

    async def resolve_night(self, game, night):
        if night.first:
            return
        for p in believers(game.g, self.name):
            choice = yes_no(game.g, p, self.name, minion_nominated(game.g, night.n - 1),
                            f'Did a Minion nominate today (yes: true)? What does {p.name} (Town Crier) learn?')
            await learn(game, p, self.name, choice,
                        lambda v: 'YES, a Minion nominated today.' if v['yes'] else 'NO, no Minion nominated today.')


def oracle_choice(g, p):
    """How many dead players are evil (alignment: a good Demon doesn't count, an evil Townsfolk does), as they are at
    the Oracle's step, after the Demon's kill. Misinformed: the count in their false world."""
    dead = [q for q in g.players if not q.appears_alive]
    possible = {sum(c) for c in product(*[sorted(g.registers_evil(q, p)) for q in dead])}
    impaired = g.unreliable(p, 'Oracle')
    values = list(range(0, len(dead) + 1)) if impaired else sorted(possible)

    def style(r):
        if impaired and g.misinformed(p, r):
            count = lambda r: sum(1 for q in dead if q.name in g.false_evil(p, r))
            return {'number': g.false_result(p, r, count, possible)}
        evil = g.sample_evil(r)
        return {'number': sum(1 for q in dead if q.name in evil)}
    return info(Choice(f'Oracle:{p.name}', [{'number': x} for x in values], style), g, p, 'Oracle',
                f'How many of the dead players ({", ".join(q.name for q in dead) or "none"}) does {p.name} (Oracle) '
                'learn are evil?', lambda v: v['number'] in possible, impaired)


class Oracle(Townsfolk):
    name = 'Oracle'
    ability = ability(name)
    info = True

    async def resolve_night(self, game, night):
        if night.first:
            return
        for p in believers(game.g, self.name):
            await learn(game, p, self.name, oracle_choice(game.g, p),
                        lambda v: f'{v["number"]} of the dead players {"is" if v["number"] == 1 else "are"} evil.')


def seamstress_choice(g, p, pair):
    """Whether the two are the same alignment (as they register). Misinformed: as in their false world."""
    a, b = (g[x] for x in pair)
    possible = {x == y for x in g.registers_evil(a, p) for y in g.registers_evil(b, p)}
    impaired = g.unreliable(p, 'Seamstress')

    def style(r):
        if impaired and g.misinformed(p, r):
            same = lambda r: (lambda evil: (a.name in evil) == (b.name in evil))(g.false_evil(p, r))
            return {'yes': g.false_result(p, r, same, possible)}
        evil = g.sample_evil(r)
        return {'yes': (a.name in evil) == (b.name in evil)}
    values = [True, False] if impaired else sorted(possible)
    return info(Choice(f'Seamstress:{p.name}', [{'yes': x} for x in values], style), g, p, 'Seamstress',
                f'{p.name} (Seamstress) chose {a.name} and {b.name}: are they the same alignment (yes: true)?',
                lambda v: v['yes'] in possible, impaired, players=list(pair))


class Seamstress(Townsfolk):
    name = 'Seamstress'
    ability = ability(name)
    info = True
    night_choice = Choose(players=2, may_self=False, optional=True,
                          prompt='Once per game: choose 2 players (not yourself) to learn whether they are the same '
                                 'alignment, or choose no one to keep your ability for a later night.')

    def night_spec(self, game, me, night):
        return None if used(game.g, me, self.name) else self.night_choice

    async def resolve_night(self, game, night):
        g = game.g
        # a Philosopher-Seamstress too, each once; and a player who only believes they are the Seamstress (the Drunk,
        # custom scripts), who is woken and answered as one and spends it as one
        for se in [q for q in believers(g, self.name) if q.name in night.chosen]:
            pair = night.chosen.get(se.name, [])
            if len(pair) != 2 or used(g, se, self.name):
                continue  # declined (one player named counts as declining: a reading)
            use(g, se, self.name)  # used up even if drunk or poisoned: not woken again
            await learn(game, se, self.name, seamstress_choice(g, se, pair),
                        lambda v: f'{pair[0]} and {pair[1]} are {"" if v["yes"] else "NOT "}the same alignment.')

    def becomes(self, game, me):
        fresh(game.g, me, self.name)  # a new Seamstress's ability is fresh (the Barber's almanac)


def sage_choice(g, p, demon):
    """Two players (never the Sage), one the Demon that killed them. Before the final night the other is usually
    alive (POLICY 'sage_alive'); on it, anyone. Misinformed: two others, one dead on the final night (the almanac's
    drunk Sage)."""
    others = [q.name for q in g.players if q is not p]
    rest = [x for x in others if x != demon]
    impaired = g.unreliable(p, 'Sage')
    values = ([list(c) for c in combinations(others, 2)] if impaired else [[demon, x] for x in rest])
    if not values:
        return None
    late = final_night(g)
    # the Recluse/Sage jinx (custom scripts): a Recluse who can register as a Demon (not poisoned) may stand in the
    # Demon's place, with any other player but the Demon (docs/carousel-rulings.md, 10)
    recluse = next((q.name for q in g.players if q is not p and q.character == 'Recluse' and g.script.jinxed(
        'Recluse', 'Sage') and any(kind(c) == 'Demon' for c in g.registers_as(q, p))), None)
    if recluse and not impaired:
        values += [[recluse, x] for x in rest if x != recluse]

    def style(r):
        if recluse and not impaired and r.random() < POLICY['sage_shows_recluse']:
            pool = [x for x in rest if x != recluse]
            alive = [x for x in pool if g[x].appears_alive]
            if pool:
                return {'players': [recluse, r.choice(alive if alive and not late else pool)]}
        return plain(r)

    def plain(r):
        alive = [x for x in rest if g[x].appears_alive and not g[x].is_demon]
        dead = [x for x in rest if not g[x].appears_alive]
        if impaired and g.misinformed(p, r):
            if late and dead and alive:
                return {'players': [r.choice(dead), r.choice(alive)]}
            pool = alive if len(alive) >= 2 else [x for x in rest if not g[x].is_demon]
            return {'players': r.sample(pool, 2) if len(pool) >= 2 else [demon, r.choice(rest)]}
        pool = [x for x in rest if g[x].appears_alive]
        if late or not pool or r.random() >= POLICY['sage_alive']:
            pool = rest
        return {'players': [demon, r.choice(pool)]}
    return info(Choice(f'Sage:{p.name}', [{'players': v} for v in values], style if recluse else plain), g, p, 'Sage',
                f'The Demon ({demon}) killed {p.name} (Sage): which two players are they shown, one the Demon that '
                'killed them? Two alive players early; one alive and one dead is fine on the final night.'
                + (f' The Recluse ({recluse}) may register as the Demon to the Sage, in its place.' if recluse else ''),
                lambda v: demon in v['players'] or (recluse is not None and recluse in v['players']), impaired,
                about=demon)


class Sage(Townsfolk):
    name = 'Sage'
    ability = ability(name)
    info = True

    async def resolve_night(self, game, night):
        # only the Demon's attack tonight (not the Witch's, nor the Pit-Hag's arbitrary deaths, nor an execution);
        # the Sage's sobriety now decides whether it is true
        g = game.g
        for p in believers(g, self.name, alive=False):
            death = next((d for d in g.death_log if d['player'] == p.name and d['day'] == night.n
                          and d['phase'] == 'night' and d['cause'] == 'demon' and d['source']), None)
            choice = sage_choice(g, p, death['source']) if death and not p.alive else None
            if choice:
                await learn(game, p, self.name, choice, lambda v: 'the Demon who killed you is {} or {}.'.format(
                    *sorted(v['players'], key=lambda x: g[x].seat)))


# ---- Townsfolk (batch 3: the Savant, the Philosopher, the Artist, the Juggler) ---------------------------------

def has(g, p, name):
    """Whether p has `name`'s ability (their own, or one gained) or believes they are it."""
    return p.shown == name or name in g.abilities(p)


def plural(n, one, many):
    return f'{n} {one if n == 1 else many}'


def register(values):
    """A registration set's one answer, or None if it could go either way (none can on Sects & Violets)."""
    return next(iter(values)) if len(values) == 1 else None


def savant_statements(g, p):
    """The statements the Savant may hear today, each {'form', 'text', 'true', 'about': the players it is about}, built
    from templates and checked by code against the Grimoire and its records (alignment, seats, drunkenness and
    poison, night choices, characters in play, Outsider counts, evil neighbours, abnormal information, votes and
    nominations, the dead). A statement whose truth depends on how someone registers either way is left out. False
    ones never contradict what the setup's public counts allow (the Outsider counts are those some legal setup has);
    statements about the Savant's own character are left out."""
    out, names = [], [q.name for q in g.players]
    n, alive = len(g.players), [q for q in g.players if q.alive]
    evil = {q.name: register(g.registers_evil(q, p)) for q in g.players}

    def add(form, text, true, about=()):
        if true is not None:
            out.append({'form': form, 'text': text, 'true': bool(true), 'about': tuple(about)})
    pairs = {tuple(sorted((names[i], names[(i + 1) % n]))) for i in range(n)}
    pairs |= {tuple(sorted((p.name, x))) for x in names if x != p.name}
    for a, b in sorted(pairs, key=lambda ab: (g[ab[0]].seat, g[ab[1]].seat)):
        same = None if None in (evil[a], evil[b]) else evil[a] == evil[b]
        add('alignment', f'{a} and {b} are the same alignment.', same, (a, b))
    demons = [q for q in g.players if register({kind(c) == 'Demon' for c in g.registers_as(q, p)})]
    for x in alive:
        for k in (1, 2):
            near = any(d is not x and steps_between(g, x, d) <= k for d in demons)
            add('demon_near', f'The Demon sits within {plural(k, "seat", "seats")} of {x.name} (and is not '
                f'{x.name}).', near, (x.name,))
    impaired = sum(1 for q in alive if g.impaired(q))
    for k in range(4):
        add('impaired', f'Exactly {plural(k, "living player is", "living players are")} drunk or poisoned.',
            impaired == k)
    for x in alive:
        chosen = any(x.name in t for night in g.night_choices.values() for who, t in night.items() if who != x.name)
        add('chosen', f"{x.name} has been chosen at night by another player's ability.", chosen, (x.name,))
    own = {p.shown, *g.abilities(p)}
    for c in g.script.all:
        if c not in own:
            add('in_play', f'There is a {c} in play.', any(q.character == c for q in g.players))
    base = SETUPS[n][1]
    shifts = {0} | {rules(c).outsiders for c in g.script.all} | {d for c in g.script.all
                                                                 for d in rules(c).outsider_choices}
    outsiders = sum(1 for q in g.players if kind(q.character) == 'Outsider')
    for k in sorted({base + d for d in shifts if 0 <= base + d <= len(g.script.outsiders)}):
        add('outsiders', f'There {"is" if k == 1 else "are"} exactly {plural(k, "Outsider", "Outsiders")} in play.',
            outsiders == k)
    nb = g.neighbours(p)
    if None not in (evil[q.name] for q in nb):
        count = sum(evil[q.name] for q in nb)
        for k in range(len(nb) + 1):
            add('neighbours', f'Exactly {k} of your living neighbours {"is" if k == 1 else "are"} evil.', count == k,
                tuple(q.name for q in nb))
    for x in alive:
        if x is not p:
            add('evil', f'{x.name} is evil.', evil[x.name], (x.name,))
    adjacent = any(kind(g.players[i].character) == 'Minion' and g.players[(i + 1) % n] in demons
                   or g.players[i] in demons and kind(g.players[(i + 1) % n].character) == 'Minion' for i in range(n))
    add('minion_near', 'A Minion sits next to the Demon (the dead count).', adjacent)
    if g.day >= 2:
        false = any(a['phase'] == 'night' and a['day'] == g.day and a['why'] == 'false information'
                    for a in g.abnormal)
        add('true_info', 'Everyone who got information from their ability last night got true information.',
            not false)
        add('voted', 'A Demon voted yesterday.', demon_voted(g, g.day - 1))
        add('nominated', 'A Minion nominated yesterday.', minion_nominated(g, g.day - 1))
        dead = [q for q in g.players if not q.appears_alive]
        if dead and None not in (evil[q.name] for q in dead):
            count = sum(evil[q.name] for q in dead)
            for k in range(len(dead) + 1):
                add('dead', f'Exactly {plural(k, "dead player is", "dead players are")} evil.', count == k)
    return out


def savant_choice(g, p):
    """The Savant's two statements: one true and one false (Grimoire.unreliable: a drunk or poisoned Savant may hear
    any two; under the Vortox two false). The scripted Storyteller's scoring rule: the true statement's form is chosen
    uniformly among the forms with a true statement (so the many pair statements don't crowd out the rest), then a
    statement of that form by weight: 2 if it is about living players only (or no player), 1 otherwise; a true
    statement that names the Demon ("X is evil" for the Demon) is never picked, nor anything the Savant heard before.
    The false one has the same form when it can (POLICY 'savant_same_kind'), else any form, by the same weights, and
    never contradicts the setup's public counts. A misinformed Savant hears two false statements ('savant_both_false')
    or two true ones. A judge may rank the pairs instead."""
    stmts = savant_statements(g, p)
    told = set(g.notes.get('Savant told', {}).get(p.name, ()))
    true = {s['text']: s['true'] for s in stmts}
    t_all, f_all = [s for s in stmts if s['true']], [s for s in stmts if not s['true']]
    impaired, falsified = g.impaired(p), g.falsified(p, 'Savant')
    if falsified and len(f_all) >= 2:
        values = [[a['text'], b['text']] for a, b in combinations(f_all, 2)]
    elif impaired or falsified:
        values = [[a['text'], b['text']] for a, b in combinations(stmts, 2)]
    else:
        values = [[a['text'], b['text']] for a in t_all for b in f_all]
    if not values:
        return None

    def reveals(s):
        return s['form'] == 'evil' and g[s['about'][0]].is_demon

    def weight(s):
        return 2 if all(g[x].alive for x in s['about']) else 1

    def pick(r, pool, form=None, avoid=()):
        pool = [s for s in pool if s['text'] not in avoid] or pool
        fresh_ = [s for s in pool if s['text'] not in told] or pool
        forms = sorted({s['form'] for s in fresh_})
        form = form if form in forms else r.choice(forms)
        within = [s for s in fresh_ if s['form'] == form]
        return r.choices(within, [weight(s) for s in within])[0]

    def style(r):
        if falsified or (impaired and g.misinformed(p, r)):
            pool = f_all if (falsified or r.random() < POLICY['savant_both_false']) and len(f_all) >= 2 else t_all
            if len(pool) < 2:
                pool = stmts
            a = pick(r, pool)
            return {'statements': [a['text'], pick(r, pool, a['form'], {a['text']})['text']]}
        a = pick(r, [s for s in t_all if not reveals(s)] or t_all)
        same = r.random() < POLICY['savant_same_kind']
        return {'statements': [a['text'], pick(r, f_all, a['form'] if same else None)['text']]}

    choice = Choice(f'Savant:{p.name}', [{'statements': v} for v in values], lambda r: None)
    choice.style = lambda r: (lambda v: v if choice.legal(v) else {'statements': r.choice(values)})(style(r))
    one_true = lambda v: sum(true[x] for x in v['statements']) == 1
    return info(choice, g, p, 'Savant', f'{p.name} (Savant) visits you: which two statements do they hear, one true '
                'and one false? Keep them helpful and related to the game, as a Townsfolk ability would give, and '
                'avoid saying who exactly the Demon is.', one_true, impaired or falsified, rules_opinion=False)


class Savant(Townsfolk):
    name = 'Savant'
    ability = ability(name)
    info = True
    visit = True

    async def visited(self, game, me, text):
        # each day (the engine allows one visit a day), alive; a Philosopher-Savant too
        g = game.g
        if not (me.alive and has(g, me, self.name)):
            return False
        choice = savant_choice(g, me)
        if choice is None:
            game.inform(me, f'Day {game.day} — Savant: the Storyteller has nothing to tell you today.')
            return True
        a, b = sorted((await game.decide_judged(choice))['statements'])
        g.notes.setdefault('Savant told', {}).setdefault(me.name, []).extend([a, b])
        game.inform(me, f'Day {game.day} — Savant: the Storyteller tells you two things, one true and one false '
                        f'(you are not told which): "{a}" and "{b}" (Seats are counted round the circle, the dead '
                        'included.)')
        return True


class Philosopher(Townsfolk):
    name = 'Philosopher'
    ability = ability(name)
    derives = True
    night_choice = Choose(players=0, character=True, optional=True, kinds=('Townsfolk', 'Outsider'),
                          prompt='Once per game: choose a good character (`character`) to gain their ability from now '
                                 'on (you stay the Philosopher; if that character is in play, its player is drunk), or '
                                 'null to keep your ability for a later night.')

    def night_spec(self, game, me, night):
        return None if used(game.g, me, self.name) else self.night_choice

    async def resolve_night(self, game, night):
        g = game.g
        for p in [q for q in believers(g, self.name) if q.name in night.chosen]:
            c = night.characters.get(p.name)
            if not c or used(g, p, self.name):
                continue
            use(g, p, self.name)  # spent even if drunk or poisoned
            if self.name not in g.abilities(p):
                continue  # a player who only believes they are the Philosopher (the Drunk): spent, nothing gained
            if not g.works(p, self.name):
                failed(game, p, self.name, 'gained no ability')
                continue
            if c in g.abilities(p):
                continue  # their own ability (the Philosopher's): nothing more
            # they gain the ability, not the character: they wake at its step from tonight (Game.wake), a "you start
            # knowing" one acts now (its `becomes`), and the in-play player of it is drunk while the Philosopher has
            # their own ability (Philosopher.ongoing)
            p.extra.append(c)
            game.emit('gains', {'player': p.name, 'character': c}, 'audit')
            game.woken(p)
            game.inform(p, f'Night {night.n} — Philosopher: you now have the {c}\'s ability: {rules(c).ability} '
                           '(You are still the Philosopher.)')
            await settle(rules(c).becomes(game, p))

    def becomes(self, game, me):
        fresh(game.g, me, self.name)

    def ongoing(self, g, me):
        # the in-play player of each gained character is drunk, recomputed (one made that character later is drunk
        # too), while the Philosopher has their own ability: sober again if the Philosopher dies, is drunk or poisoned
        if not me.extra or not g.works(me, self.name):
            return []
        return [State('drunk', q.name, source=me.name, until=None) for c in me.extra for q in g.players
                if q is not me and q.character == c]


QUESTION = re.compile(r'^(?:storyteller,?\s*|so,?\s*|ok,?\s*)?(?:is it true that|tell me (?:if|whether)|i ask:?)\s+')


def artist_truth(g, asker, text):
    """The honest answer to a yes/no question of a simple form the code can check against the Grimoire now, or None:
    "Is X the Y / a Townsfolk / evil?", "Am I ...?", "Is the Demon X?", "Is the Demon X, Y or Z?" (also "one of",
    "among", "X or Y the Demon?"), "Are X and Y the same alignment (on the same team)?", "Is there a Y in play?", "Is
    the Y in play?" (X a player or "I"/"me", Y a character on the script). Anything else is the Storyteller's to
    answer (a judge), or "I don't know"."""
    from .bmr import gossip_truth
    s = ' '.join((text or '').lower().replace('’', "'").split()).strip(' ?.!"\'')
    s = QUESTION.sub('', s)
    names = {x.lower(): x for x in g.by_name}
    alt = '|'.join(re.escape(x) for x in sorted(names, key=len, reverse=True))
    player = rf'(?:{alt}|i|me)'

    def who(x):
        return asker if x in ('i', 'me') else g[names[x]]

    def listed(part):
        items = [x.strip() for x in re.split(r',\s*(?:and\s+|or\s+)?|\s+(?:or|and)\s+', part) if x.strip()]
        items = [re.sub(r'^either\s+', '', x) for x in items]
        return [who(x) for x in items] if items and all(x in names or x in ('i', 'me') for x in items) else None

    def any_demon(players):
        sets = [{kind(c) == 'Demon' for c in g.registers_as(q, asker)} for q in players]
        if any(True in x and len(x) == 1 for x in sets):
            return True
        return False if all(x == {False} for x in sets) else None
    m = re.fullmatch(rf'(?:are|is) ({player}) and ({player}) (?:the same alignment|on the same team|of the same '
                     r'alignment|both good or both evil)', s)
    if m:
        a, b = (register(g.registers_evil(who(x), asker)) for x in m.groups())
        return None if None in (a, b) else a == b
    m = re.fullmatch(r'is the demon (?:one of |among |either )?(.+)', s)
    if m and listed(m.group(1)):
        return any_demon(listed(m.group(1)))
    m = re.fullmatch(r'(?:is|are) (?:either )?(.+?) (?:the|a) demon', s)
    if m and listed(m.group(1)) and len(listed(m.group(1))) > 1:
        return any_demon(listed(m.group(1)))
    m = re.fullmatch(r'is there (.+)', s)
    if m:
        s = 'there is ' + m.group(1)
    m = re.fullmatch(rf'(?:is|am) ({player}) (.+)', s)
    if m:
        s = f'{"i" if m.group(1) in ("i", "me") else m.group(1)} is {m.group(2)}'
    m = re.fullmatch(r'is ((?:the |a |an )?.+) in play', s)
    if m:
        s = f'{m.group(1)} is in play'
    return gossip_truth(g, asker, s)


def artist_choice(g, p, text):
    """The Storyteller's answer to the Artist's question: a question the code can check (artist_truth) is answered
    honestly, or misinformed the opposite (drunk or poisoned: usually; the Vortox: always); any other goes to the
    judge (yes, no, or "I don't know": nothing), and the scripted Storyteller, which can't read it, says "I don't
    know"."""
    true = artist_truth(g, p, text)
    if true is not None:
        return yes_no(g, p, 'Artist', true, f'{p.name} (Artist) privately asks you: "{text}". The answer (yes: true)?')
    falsified = g.falsified(p, 'Artist')
    question = (f'{p.name} (Artist) privately asks you: "{text}". Answer honestly: yes (true), no (false), or "I '
                'don\'t know" (nothing) if it is subjective, about the future or intentions, not something you know, '
                'or not a yes/no question (the almanac: "Are we winning?" gets "I don\'t know").'
                + (' They are drunk or poisoned: you may answer falsely.' if g.impaired(p) else '')
                + (' The Vortox is in play: if you can answer, answer falsely.' if falsified else ''))
    return judged(Choice(f'Artist:{p.name}', [{'yes': True}, {'yes': False}, {'yes': None}], lambda r: {'yes': None}),
                  'artist', question, recipient=p.name, impaired=g.impaired(p))


class Artist(Townsfolk):
    name = 'Artist'
    ability = ability(name)
    info = True
    visit = True

    async def visited(self, game, me, text):
        g = game.g
        if not (me.alive and has(g, me, self.name)):
            return False
        if used(g, me, self.name):
            game.inform(me, f'Day {game.day} — Artist: you have already asked your one question.')
            return True
        if not (text or '').strip():  # (the almanac: prompt them to ask; the ability isn't used)
            game.inform(me, f'Day {game.day} — Artist: ask your yes/no question in `text` when you visit. Your '
                            'ability is not used.')
            return True
        use(g, me, self.name)
        v = (await game.decide_judged(artist_choice(g, me, text)))['yes']
        answer = {True: 'Yes.', False: 'No.', None: "I don't know."}[v]
        game.inform(me, f'Day {game.day} — Artist: you asked "{text}" The Storyteller answers: {answer}')
        return True

    def becomes(self, game, me):
        fresh(game.g, me, self.name)


def juggler_choice(g, p, record):
    """How many of the Juggler's guesses were correct when made (CORRECT reminders). Misinformed: one off."""
    true, most = record['correct'], record['guesses']
    impaired = g.unreliable(p, 'Juggler')
    values = list(range(0, most + 1)) if impaired else [true]

    def style(r):
        if impaired and g.misinformed(p, r):
            return {'number': r.choice([x for x in (true - 1, true + 1) if 0 <= x <= most] or values)}
        return {'number': true}
    return info(Choice(f'Juggler:{p.name}', [{'number': x} for x in values], style), g, p, 'Juggler',
                f'{p.name} (Juggler) guessed {record["guesses"]} characters yesterday: how many correct do they learn?',
                lambda v: v['number'] == true, impaired)


class Juggler(Townsfolk):
    name = 'Juggler'
    ability = ability(name)
    info = True
    public_action = 'ability'  # the guesses, through the shared `ability` field (its `guesses`)
    public_guesses = 5

    @staticmethod
    def first_day(g, p):
        return g.notes.get('Juggler day', {}).get(p.name, 1)

    def act_publicly(self, game, actor, target, text=None, guesses=None):
        # anyone may claim it; only a living Juggler's first guesses on their first day as the Juggler count, drunk
        # or not (counted now, against the true characters: the CORRECT reminders); no guesses is not a use
        g, p = game.g, game.g[actor]
        if not (p.alive and has(g, p, self.name) and guesses) or self.first_day(g, p) != game.day:
            return False
        if p.name in g.notes.get('Juggler', {}):
            return False
        correct = sum(1 for x in guesses if g[x['player']].character == x['character'])
        g.notes.setdefault('Juggler', {})[p.name] = {'day': game.day, 'guesses': len(guesses), 'correct': correct}
        return False

    def becomes(self, game, me):
        # "your 1st day" is their first day as the Juggler (the almanac's Savant made the Juggler on night 4)
        g = game.g
        g.notes.setdefault('Juggler day', {})[me.name] = game.day
        g.notes.get('Juggler', {}).pop(me.name, None)

    async def resolve_night(self, game, night):
        g = game.g
        for p in believers(g, self.name):  # alive: if they are killed first, they learn nothing
            record = g.notes.get('Juggler', {}).get(p.name)
            if record and record['day'] == night.n - 1:
                await learn(game, p, self.name, juggler_choice(g, p, record),
                            lambda v: f'{plural(v["number"], "of your guesses was", "of your guesses were")} '
                                      'correct.')
        for name, record in list(g.notes.pop('Cannibal Juggler', {}).items()):
            # the Cannibal jinx (custom scripts): the executed Juggler's guesses, learnt by the living Cannibal
            if g[name].alive and g.script.jinxed('Cannibal', self.name):
                await learn(game, g[name], self.name, juggler_choice(g, g[name], record), lambda v: 'the Juggler '
                            f'you ate made {plural(v["number"], "correct guess", "correct guesses")}.')


# ---- Outsiders -------------------------------------------------------------------------------------------------

class Mutant(Outsider):
    name = 'Mutant'
    ability = ability(name)

    async def moment(self, game, me, when):
        # judged when the day's talk is done (before nominations), and at dusk on what was said since (nominations
        # and defenses), if nobody was executed today; must=False: they must NOT try to convince anyone they are an
        # Outsider (any Outsider). Only while a living, sober and healthy Mutant
        g = game.g
        if when not in ('nominations', 'dusk') or not g.works(me, self.name):
            return
        marks = g.notes.setdefault('Mutant judged', {})
        if when == 'nominations':
            marks[me.name] = (game.day, len(game.events))
            await game.judge_madness(me, 'Outsider', must=False)
        elif marks.get(me.name, (None,))[0] == game.day:
            await game.judge_madness(me, 'Outsider', must=False, after=marks[me.name][1])


def sweetheart_choice(g, sh):
    """Who is drunk from now on: any other player. The scripted style follows the almanac: a living good Townsfolk
    (POLICY 'sweetheart_townsfolk'), else any other living player."""
    others = [q.name for q in g.players if q is not sh]

    def style(r):
        good = [x for x in others if g[x].alive and not g[x].evil and townsfolk(g[x])]
        alive = [x for x in others if g[x].alive] or others
        return {'players': [r.choice(good if good and r.random() < POLICY['sweetheart_townsfolk'] else alive)]}
    return judged(Choice(f'Sweetheart:{sh.name}', [{'players': [x]} for x in others], style), 'sweetheart_drunk',
                  f'{sh.name}, the Sweetheart, has died: which player is drunk from now on? The almanac: almost always '
                  'a Townsfolk, which hurts good; if evil is winning convincingly, an Outsider, a Minion or even the '
                  'Demon.', about=sh.name, recipient=sh.name)


class Sweetheart(Outsider):
    name = 'Sweetheart'
    ability = ability(name)

    def on_death(self, game, me, dead, cause, alive_before):
        # any death; a drunk or poisoned Sweetheart's death is wasted (their sobriety as they die decides)
        g = game.g
        if dead is not me or me.alive or g.impaired(me) or self.name not in g.abilities(me):
            return
        done = g.notes.setdefault('Sweetheart', [])
        if me.name not in done:
            done.append(me.name)
            game.later(lambda game: self.drunk(game, me))

    async def drunk(self, game, me):
        g = game.g
        t = (await game.decide_judged(sweetheart_choice(g, me)))['players'][0]
        g.add(State('drunk', t, source=me.name, until=None))  # for the rest of the game, whatever happens to them


def barber_demon_choice(g, demons):
    """Which living Demon makes the Barber's swap, when there are several: the Storyteller's (uniform)."""
    names = [d.name for d in demons]
    return judged(Choice('Barber Demon', [{'players': [x]} for x in names], lambda r: {'players': [r.choice(names)]}),
                  'barber_demon', f'The Barber died: which living Demon ({", ".join(names)}) may swap two players\' '
                                  'characters tonight?')


class Barber(Outsider):
    name = 'Barber'
    ability = ability(name)

    def on_death(self, game, me, dead, cause, alive_before):
        # haircuts tonight: the night of a death by day is the coming one; a drunk or poisoned Barber's death is
        # wasted; a player who dies and then becomes the Barber gives none (they did not die as the Barber)
        g = game.g
        if dead is me and not me.alive and self.name in g.abilities(me) and not g.impaired(me):
            g.notes['Haircuts'] = game.day if game.tonight is not None else game.day + 1

    async def resolve_night(self, game, night):
        g = game.g
        if g.notes.get('Haircuts') != night.n:
            return
        demons = [q for q in g.players if q.alive and q.is_demon]
        if not demons:
            return
        d = demons[0] if len(demons) == 1 else g[(await game.decide_judged(barber_demon_choice(g, demons)))[
            'players'][0]]
        options = [q.name for q in g.players if not (q.is_demon and q is not d)]
        req = game.request('night', f'Night {night.n} — the Barber has died. As the Demon you may choose 2 players '
                                    '(alive or dead, yourself too, but not another Demon) to swap characters: their '
                                    'alignments stay, and each learns their new character. Put them in `targets`, or '
                                    '[] to swap no one.', night.n, n_targets=2, options=options, min_targets=0)
        chosen = game.targets(d.name, await game.ask(d.name, req), req)
        game.woken(d)
        game.emit('night_choice', {'player': d.name, 'role': self.name, 'targets': chosen}, 'audit')
        if len(chosen) == 2:  # one player named is declining (a reading, as for the Seamstress)
            await game.swap(g[chosen[0]], g[chosen[1]])


class Klutz(Outsider):
    name = 'Klutz'
    ability = ability(name)
    public_action = 'ability'  # anyone may claim to choose (a bluff); the real Klutz is asked when they learn they died

    def act_publicly(self, game, actor, target, text=None):
        return False

    def on_death(self, game, me, dead, cause, alive_before):
        if dead is not me or me.alive or self.name not in game.g.abilities(me):
            return
        if game.tonight is not None:  # they learn it at dawn
            game.g.notes.setdefault('Klutz at dawn', []).append(me.name)
        else:  # executed or killed by day: at once
            game.later(lambda game: self.choose(game, me))

    def moment(self, game, me, when):
        due = game.g.notes.get('Klutz at dawn', [])
        if when == 'dawn' and me.name in due:
            due.remove(me.name)
            game.later(lambda game: self.choose(game, me))

    async def choose(self, game, me):
        """The public choice: required, asked again until they name an alive player (never chosen for them). Their
        sobriety now decides; the Vortox does not touch it (not information). An evil Klutz who chooses an evil player
        makes good win (the almanac)."""
        g = game.g
        options = [p.name for p in g.players if p.appears_alive]
        if not options or g.winner:
            return
        req = game.request('death_choice', f'Day {game.day}: you have died. Klutz: publicly choose an alive player '
                                           '(`targets`): if they are evil, your team loses.', game.day, n_targets=1,
                           options=options)
        t = game.targets(me.name, await game.insist(me.name, req, await game.ask(me.name, req)), req)[0]
        game.emit('ability', {'player': me.name, 'character': self.name, 'target': t})
        if not g[t].evil:
            return
        if g.impaired(me) or self.name not in g.abilities(me):
            failed(game, me, self.name, 'chose an evil player')
            return
        g.winner = 'good' if me.evil else 'evil'
        g.reason = f'{me.name}, the Klutz, chose {t}, who is evil: the {"evil" if me.evil else "good"} team loses.'


CHARACTERS.update({c.name: c() for c in [Witch, Cerenovus, PitHag, EvilTwin, FangGu, Vigormortis, NoDashii, Vortox,
                                         Clockmaker, Dreamer, SnakeCharmer, Mathematician, Flowergirl, TownCrier,
                                         Oracle, Seamstress, Sage, Savant, Philosopher, Artist, Juggler, Mutant,
                                         Sweetheart, Barber, Klutz]})
