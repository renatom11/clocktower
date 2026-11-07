"""Sects & Violets' characters, on the script-independent core (characters.py, state.py, game.py).

Each entry follows the almanac's How to Run. Where the rules leave a question open, a comment says which reading
the entry takes, and why (docs/snv-rulings.md lists them for review).
"""
from __future__ import annotations
from itertools import combinations, product

from .characters import CHARACTERS, Choose, Demon, Minion, Townsfolk, kind
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
        if not (t and c):
            return
        if any(q.character == c for q in g.players):
            return  # in play (a dead player's character too; a Drunk's apparent one is not): nothing happens
        if not g.works(ph, self.name):
            failed(game, ph, self.name, 'no change')
            return
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
        g = game.g
        sc, t = night.choice_of(g, self.name)
        if not t or not g[t].is_demon or g[t] is sc:
            return  # not the Demon: nothing happens (themself included)
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


class Mathematician(Townsfolk):
    name = 'Mathematician'
    ability = ability(name)
    info = True

    async def resolve_night(self, game, night):
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
        return None if game.g.spent_ability(self.name) else self.night_choice

    async def resolve_night(self, game, night):
        g = game.g
        se, _ = night.choice_of(g, self.name)
        pair = night.chosen.get(se.name, []) if se else []
        if len(pair) != 2:
            return  # declined (one player named counts as declining: a reading)
        g.spend(self.name)  # used up even if drunk or poisoned: not woken again
        await learn(game, se, self.name, seamstress_choice(g, se, pair),
                    lambda v: f'{pair[0]} and {pair[1]} are {"" if v["yes"] else "NOT "}the same alignment.')


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

    def style(r):
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
    return info(Choice(f'Sage:{p.name}', [{'players': v} for v in values], style), g, p, 'Sage',
                f'The Demon ({demon}) killed {p.name} (Sage): which two players are they shown, one the Demon that '
                'killed them? Two alive players early; one alive and one dead is fine on the final night.',
                lambda v: demon in v['players'], impaired, about=demon)


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


CHARACTERS.update({c.name: c() for c in [Witch, Cerenovus, PitHag, EvilTwin, FangGu, Vigormortis, NoDashii, Vortox,
                                         Clockmaker, Dreamer, SnakeCharmer, Mathematician, Flowergirl, TownCrier,
                                         Oracle, Seamstress, Sage]})
