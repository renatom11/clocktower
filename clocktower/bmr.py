"""Bad Moon Rising's characters, on the script-independent core (characters.py, state.py, game.py).

Each entry follows the almanac's How to Run. Where the rules leave a question open, a comment says which reading
the entry takes, and why.
"""
from __future__ import annotations
from itertools import combinations
import re

from .characters import CHARACTERS, Choose, Demon, Minion, Outsider, Townsfolk, kind, rules
from .state import POLICY, Choice, State, judged, setup_changes, team_sizes, yes_choice


def ability(name):
    """The official ability text."""
    from . import official
    return official.role(name)['ability']


# ---- Minions ---------------------------------------------------------------------------------------------------

def outsiders_choice(g, p):
    """What the Godfather is shown on the first night: the Outsider characters in play. An impaired Godfather may be
    shown another set, of a size the setup allows (base Outsiders, one more or one fewer)."""
    true = [c for c in g.script.outsiders if any(q.character == c for q in g.players)]
    impaired = g.impaired(p)
    sizes = {team_sizes(len(g.players), d)[1] for d in setup_changes([q.character for q in g.players])}
    values = [list(c) for k in sorted(sizes) if 0 <= k <= len(g.script.outsiders)
              for c in combinations(g.script.outsiders, k)] if impaired else [true]

    def style(r):
        if impaired and g.misinformed(p, r):
            false = [v for v in values if v != true]
            same = [v for v in false if len(v) == len(true)]  # the same count: false, and nothing gives it away
            if same or false:
                return {'characters': r.choice(same or false)}
        return {'characters': true}
    choice = Choice(f'Godfather:{p.name}', [{'characters': v} for v in values], style)
    choice.truth = lambda v: sorted(v['characters']) == sorted(true)
    choice.context = {'call': 'information', 'about': None, 'recipient': p.name, 'impaired': impaired,
                      'question': f'Which Outsider characters is {p.name} (Godfather) shown as in play?'}
    return choice


class Godfather(Minion):
    name = 'Godfather'
    ability = ability(name)
    outsider_choices = (-1, 1)  # the Storyteller's choice when dealing (state.random_setup)
    night_choice = Choose(players=1, prompt='An Outsider died today: choose a player: they die.')
    kills_at_night = True

    @staticmethod
    def outsider_died(g, day):
        """Whether an Outsider died during day `day` (any day death counts, not only an execution: the ability text
        and the almanac's Tinker example, over its summary's "executed and dies")."""
        return any(kind(g[n].character) == 'Outsider' for n in g.died_today(day))

    def night_spec(self, game, me, night):
        # the first night is the Outsider information, with nothing to choose; later, only after an Outsider's
        # day death (one kill however many died)
        if night.first or not self.outsider_died(game.g, night.n - 1):
            return None
        return self.night_choice

    async def resolve_night(self, game, night):
        g = game.g
        gf = g.with_character(self.name)
        if not gf:
            return
        if night.first:
            value = await game.decide_judged(outsiders_choice(g, gf))
            shown = value['characters']
            game.woken(gf)
            text = (f'the Outsiders in play are: {", ".join(shown)}.' if shown else 'there are no Outsiders in play.')
            game.inform(gf, f'Night {night.n} — Godfather: {text}')
            return
        _, t = night.choice_of(g, self.name)
        if t and g.works(gf, self.name):
            game.attempt_kill(g[t], 'godfather', gf, night)


class DevilsAdvocate(Minion):
    name = "Devil's Advocate"
    ability = ability(name)
    night_choice = Choose(players=1, prompt='Choose a living player (not the one you chose last night): if they are '
                                            'executed tomorrow, they do not die.', alive_only=True, not_last=True)

    async def resolve_night(self, game, night):
        g = game.g
        da, t = night.choice_of(g, self.name)
        if t and g.works(da, self.name):
            # until tomorrow's dusk, and only while the Devil's Advocate keeps a working ability (a drunk one's
            # saved Minion dies: the Minstrel example)
            g.add(State('safe', t, source=da.name, until='night', against='execution', ends_with_source=True,
                        while_source_works=True))


class Assassin(Minion):
    name = 'Assassin'
    ability = ability(name)
    night_choice = Choose(players=1, prompt='Once per game, you may choose a player: they die, even if for some '
                                            'reason they could not. Or choose no one, and keep your ability.',
                          optional=True)
    kills_at_night = True
    picks_in_turn = True  # the Goon it chooses makes it drunk, but the kill goes through ("even if ...")

    def night_spec(self, game, me, night):
        return None if night.first or game.g.spent_ability(self.name) else self.night_choice

    async def resolve_night(self, game, night):
        g = game.g
        a, t = night.choice_of(g, self.name)
        if not t:
            return
        works = g.works(a, self.name)  # as it chooses: a Goon chosen by a sober Assassin dies, and turns evil
        game.pick(night, a, t)
        g.spend(self.name)  # spent even when drunk or poisoned: the Assassin won't wake again
        if works:
            # nothing stops it: protections, the Fool's survival, and (a reading: like the Fool's) the Zombuul's
            # first death, or a Zombuul who only seems dead
            game.attempt_kill(g[t], 'assassin', a, night, unstoppable=True)


class Mastermind(Minion):
    name = 'Mastermind'
    ability = ability(name)

    @staticmethod
    def demon_executed_today(g):
        """Whether the Demon's (real) death was by execution, today."""
        last = next((d for d in reversed(g.death_log) if g[d['player']].is_demon and not d.get('seems')), None)
        return bool(last and last['cause'] == 'execution' and last['day'] == g.day and not g.demon())

    def overrides_end(self, g, me, winner, reason):
        day = g.notes.get(self.name)
        if day is None:
            if winner == 'good' and g.works(me, self.name) and self.demon_executed_today(g):
                g.notes[self.name] = g.day  # play one more day; the town is not told the Demon died
                return False
            return None
        # the extra day is day + 1: its execution decides, killing or not (the Devil's Advocate example)
        executed = [e for e in g.executions if e['day'] == day + 1]
        if executed:
            p = g[executed[0]['player']]
            team = 'evil' if p.evil else 'good'
            return ('good' if p.evil else 'evil',
                    f'The Demon was executed, but the Mastermind played one more day, and {p.name} ({team}) was '
                    f'executed on it: the {team} team loses.')
        if g.day > day + 1:  # the extra day ended with no execution (see moment)
            return 'good', self.no_execution
        return False  # the extra night and day go on, even with two players alive

    no_execution = 'The Demon was executed; the Mastermind played one more day, and nobody was executed on it.'

    def moment(self, game, me, when):
        day = game.g.notes.get(self.name)
        if when == 'dusk' and day is not None and game.day == day + 1 and not game.g.winner:
            game.g.winner, game.g.reason = 'good', self.no_execution


# ---- Demons ----------------------------------------------------------------------------------------------------

class Zombuul(Demon):
    name = 'Zombuul'
    ability = ability(name)
    night_choice = Choose(players=1, prompt='Nobody died today: choose a player: they die.')
    kills_at_night = True

    def night_spec(self, game, me, night):
        # woken only if nobody died today (a seeming death counts; executing a dead player kills nobody)
        return None if night.first or game.g.died_today(night.n - 1) else self.night_choice

    def dies(self, game, me, cause):
        g = game.g
        if g.works(me, self.name) and not g.spent_ability(self.name):  # a drunk or poisoned Zombuul dies for real
            g.spend(self.name)
            return 'seems'
        return None

    async def resolve_night(self, game, night):
        g = game.g
        z, t = night.choice_of(g, self.name)
        if t and g.works(z, self.name):
            await game.demon_attack_judged(g[t], z, night)


class Pukka(Demon):
    name = 'Pukka'
    ability = ability(name)
    night_choice = Choose(players=1, prompt='Choose a player to poison: tomorrow night, when you choose again, they '
                                            'die.')
    kills_at_night = True

    @staticmethod
    def poisons(g, pukka):
        return [s for s in g.states if s.kind == 'poisoned' and s.source == pukka.name and s.until is None]

    async def resolve_night(self, game, night):
        g = game.g
        pukka = g.with_character(self.name)
        if not pukka:
            return
        _, t = night.choice_of(g, self.name)  # none if the Pukka was not woken (the Exorcist): the old victim dies
        earlier = self.poisons(g, pukka)
        if not g.works(pukka, self.name):
            return  # a drunk Pukka poisons nobody, and the earlier victim waits for it to sober up
        if t:
            # lasts until the victim dies; paused while the Pukka is drunk or poisoned ("the poison resumes")
            g.add(State('poisoned', t, source=pukka.name, until=None, ends_with_source=True, while_source_works=True))
        for s in earlier:  # the previously poisoned player dies (still poisoned), then is healthy
            await game.demon_attack_judged(g[s.target], pukka, night)
            g.states = [x for x in g.states if x is not s]


def regurgitation_choice(g, shab, dead):
    """Whether the Shabaloth regurgitates one of the dead players it chose last night, and whom."""
    done = sum(1 for r in g.revivals if r['source'] == 'Shabaloth')

    def style(r):
        chance = POLICY['shabaloth_regurgitate'] * (1 if done < POLICY['regurgitations'] else 0.1)
        if r.random() >= chance:
            return {'players': []}
        good = [x for x in dead if not g[x].evil]
        return {'players': [r.choice(good if good and r.random() >= POLICY['regurgitate_evil'] else dead)]}
    choice = Choice(f'Shabaloth:{shab.name}', [{'players': []}] + [{'players': [x]} for x in dead], style)
    choice.context = {'call': 'regurgitation', 'about': None, 'recipient': shab.name, 'impaired': False,
                      'question': f'Does the Shabaloth regurgitate one of the dead players it chose last night (alive '
                                  f'again at dawn), and whom? Rarely: once a game, maybe twice ({done} so far).'}
    return choice


class Shabaloth(Demon):
    name = 'Shabaloth'
    ability = ability(name)
    night_choice = Choose(players=2, prompt='Choose two players: they die.')
    kills_at_night = True
    picks_in_turn = True

    async def resolve_night(self, game, night):
        g = game.g
        shab = g.with_character(self.name)
        if not shab:
            return
        # just before the Shabaloth acts: a dead player it chose last night may come back (the Storyteller's call)
        last = night.before.get(shab.name, []) if shab.name in g.woke.get(night.n - 1, []) else []
        dead = [x for x in last if not g[x].alive]
        if dead and g.works(shab, self.name):
            value = await game.decide_judged(regurgitation_choice(g, shab, dead))
            if value['players']:
                p = g[value['players'][0]]
                g.revive(p, self.name)  # they wake later tonight if their step comes later
                night.revived.append(p)
        for t in night.chosen.get(shab.name, []):  # in the order chosen
            game.pick(night, shab, t)
            if not g.works(shab, self.name):
                break  # the first pick made the Shabaloth drunk (the Goon)
            await game.demon_attack_judged(g[t], shab, night)


class Po(Demon):
    name = 'Po'
    ability = ability(name)
    night_choice = Choose(players=1, prompt='You may choose a player: they die. If you choose no one, next time you '
                                            'choose three.', optional=True)
    charged = Choose(players=3, prompt='Last time you chose no one, so choose three players tonight: they die.')
    kills_at_night = True
    picks_in_turn = True

    def night_spec(self, game, me, night):
        # "last choice": the first night and a night the Po was not woken (the Exorcist) are not choices, so a
        # charge survives them; a drunk Po's "no one" still charges
        return self.charged if game.g.last_choices.get(me.name) == [] else self.night_choice

    async def resolve_night(self, game, night):
        g = game.g
        po = g.with_character(self.name)
        for t in night.chosen.get(po.name, []) if po else []:
            game.pick(night, po, t)
            if not g.works(po, self.name):
                break  # a pick made the Po drunk (the Goon): the later ones fail
            await game.demon_attack_judged(g[t], po, night)


# ---- Townsfolk that protect, make players drunk, or bring players back ------------------------------------------

def sailor_choice(g, sailor, target):
    """Who is drunk until dusk when the Sailor chooses another player: the Sailor or them."""
    t = g[target]
    townsfolk = kind(t.character) == 'Townsfolk'

    def style(r):
        if townsfolk:
            return {'players': [target if r.random() < POLICY['sailor_townsfolk_drunk'] else sailor.name]}
        return {'players': [sailor.name if r.random() < POLICY['sailor_self_drunk'] else target]}
    choice = Choice(f'Sailor:{sailor.name}', [{'players': [sailor.name]}, {'players': [target]}], style)
    choice.context = {'call': 'sailor', 'about': target, 'recipient': sailor.name, 'impaired': False,
                      'question': f'{sailor.name} (Sailor) chose {target} (the {t.character}). Who is drunk until '
                                  f'dusk: the Sailor or {target}? Usually the Townsfolk if a Townsfolk was chosen, '
                                  f'otherwise the Sailor.'}
    return choice


class Sailor(Townsfolk):
    name = 'Sailor'
    ability = ability(name)
    night_choice = Choose(players=1, prompt='Choose a living player: either you or they are drunk until dusk.',
                          alive_only=True)

    def safe_from(self, g, me, cause):
        # while sober and healthy, from every death (only the Assassin's gets through), even before they choose
        return g.works(me, self.name)

    async def resolve_night(self, game, night):
        g = game.g
        sailor, t = night.choice_of(g, self.name)
        if not t or not g.works(sailor, self.name):
            return  # a drunk or poisoned Sailor makes nobody drunk
        drunk = t if t == sailor.name else (await game.decide_judged(sailor_choice(g, sailor, t)))['players'][0]
        # like any ongoing effect, it ends if the Sailor dies (a reading: the general rule)
        g.add(State('drunk', drunk, source=sailor.name, until='night', ends_with_source=True))


def innkeeper_choice(g, inn, pair):
    """Which of the Innkeeper's two players is drunk until dusk."""
    def style(r):
        if inn.name in pair:
            other = next((x for x in pair if x != inn.name), inn.name)
            return {'players': [inn.name if r.random() < POLICY['innkeeper_self_drunk'] else other]}
        good = [x for x in pair if not g[x].evil]
        if len(good) == 1:
            evil = next(x for x in pair if x not in good)
            return {'players': [good[0] if r.random() < POLICY['innkeeper_good_drunk'] else evil]}
        return {'players': [r.choice(pair)]}
    choice = Choice(f'Innkeeper:{inn.name}', [{'players': [x]} for x in pair], style)
    choice.context = {'call': 'innkeeper', 'about': None, 'recipient': inn.name, 'impaired': False,
                      'question': f'{inn.name} (Innkeeper) protected {" and ".join(pair)}. Which of them is drunk '
                                  'until dusk? Almost always a good player, depending on how the game is going; an '
                                  'Innkeeper who chose themself is usually the drunk one.'}
    return choice


class Innkeeper(Townsfolk):
    name = 'Innkeeper'
    ability = ability(name)
    night_choice = Choose(players=2, prompt='Choose two players: they cannot die tonight, but one of them is drunk '
                                            'until dusk.')

    async def resolve_night(self, game, night):
        g = game.g
        inn = g.with_character(self.name)
        pair = night.chosen.get(inn.name, []) if inn else []
        if not pair or not g.works(inn, self.name):
            return
        drunk = (await game.decide_judged(innkeeper_choice(g, inn, pair)))['players'][0]
        g.add(State('drunk', drunk, source=inn.name, until='night', ends_with_source=True))
        for t in pair:  # until dawn, against every death but the Assassin's, and only while the Innkeeper works: an
            # Innkeeper made drunk by their own choice protects nobody; one who dies tonight stops protecting (Tinker)
            g.add(State('safe', t, source=inn.name, until='dawn', against='any', ends_with_source=True,
                        while_source_works=True))


class Courtier(Townsfolk):
    name = 'Courtier'
    ability = ability(name)
    night_choice = Choose(players=0, character=True, optional=True,
                          prompt='Once per game, you may choose a character: they are drunk for 3 nights & 3 days. Or '
                                 'choose none, and keep your ability.')

    def night_spec(self, game, me, night):
        return None if game.g.spent_ability(self.name) else self.night_choice

    async def resolve_night(self, game, night):
        g = game.g
        c = g.with_character(self.name)
        chosen = night.characters.get(c.name) if c else None
        if not chosen:
            return
        works = g.works(c, self.name)
        g.spend(self.name)  # used even while drunk: not woken again
        target = next((p for p in g.players if p.character == chosen), None)  # in play, alive or dead
        if target and works:
            # tonight and the next two nights and days: until the dusk before night n + 3. Paused while the Courtier is
            # drunk, poisoned or dead; a Courtier who chooses themself is simply drunk (a reading)
            g.add(State('drunk', target.name, source=c.name, until=night.n + 3, ends_with_source=True,
                        while_source_works=target is not c))


class Minstrel(Townsfolk):
    name = 'Minstrel'
    ability = ability(name)

    def on_death(self, game, me, dead, cause, alive_before):
        g = game.g
        if cause != 'execution' or kind(dead.character) != 'Minion' or not g.works(me, self.name):
            return  # not a night death, an execution that did not kill, a dead Minion executed, or a drunk Minstrel
        for p in g.players:  # the dead too; until dusk tomorrow (the dusk before night day + 2); it ends if the
            if p is not me and not p.traveller:  # Minstrel dies (a reading: the general rule)
                g.add(State('drunk', p.name, source=me.name, until=game.day + 2, ends_with_source=True))


class Exorcist(Townsfolk):
    name = 'Exorcist'
    ability = ability(name)
    night_choice = Choose(players=1, prompt='Choose a player (not the one you chose last night): if they are the '
                                            'Demon, they learn who you are and do not wake tonight.', not_last=True)

    async def resolve_night(self, game, night):
        g = game.g
        ex, t = night.choice_of(g, self.name)
        if not t or not g.works(ex, self.name) or not (g[t].alive and g[t].is_demon):
            return
        # the Demon doesn't wake for its own ability tonight; its other abilities still work (the Pukka's poison,
        # the Zombuul's first death, the Shabaloth's regurgitation). Being told is not waking for an ability.
        night.asleep.add(t)
        game.inform(g[t], f'Night {night.n}: the Exorcist chose you. {ex.name} is the Exorcist, and you do not wake '
                          'tonight.')


class TeaLady(Townsfolk):
    name = 'Tea Lady'
    ability = ability(name)

    def protects(self, g, me, other, cause):
        # recomputed at each death: her alive neighbours now (a Zombuul that seems dead is skipped), by alignment
        if not g.works(me, self.name):
            return False
        nb = g.neighbours(me)
        return other in nb and not any(q.evil for q in nb)


def pacifist_choice(g, pac, p):
    """Whether the Pacifist saves `p`, a good player being executed."""
    saves = g.notes.get('Pacifist saves', 0)

    def style(r):
        if g.notes.get('Pacifist never'):
            return {'yes': False}
        chance = POLICY['pacifist_again'] if saves else POLICY['pacifist_late' if g.alive_count() <= 5 else
                                                               'pacifist_save']
        return {'yes': r.random() < chance}
    choice = Choice(f'Pacifist:{p.name}', [{'yes': True}, {'yes': False}], style)
    choice.context = {'call': 'pacifist', 'about': p.name, 'recipient': pac.name, 'impaired': False, 'helps': 'good',
                      'question': f'{p.name} (good) is being executed. Does the Pacifist ({pac.name}) save them, so '
                                  f'they are executed but do not die? About once a game is usual, more likely at the '
                                  f'climax, and less if good is winning ({saves} saved so far).'}
    return choice


class Pacifist(Townsfolk):
    name = 'Pacifist'
    ability = ability(name)
    setup_order = 2

    async def setup(self, game):
        # rarely, the Storyteller never saves anyone, to make the Pacifist look suspicious: decided once per game
        pac = game.g.with_character(self.name, alive=False)
        choice = judged(yes_choice('Pacifist:never', POLICY['pacifist_never']), 'pacifist_never',
                        'Before the game: will the Pacifist never save anyone this game (yes: true)? Rarely, to make '
                        'the Pacifist look suspicious.', about=pac and pac.name, recipient=pac and pac.name)
        game.g.notes['Pacifist never'] = (await game.decide_judged(choice))['yes']

    async def before_execution(self, game, me, p):
        g = game.g
        if not (g.works(me, self.name) and p.alive and not p.evil) or g.safe(p, 'execution'):
            return  # nothing to decide: a drunk Pacifist, an evil or dead player, or one saved anyway
        if (await game.decide_judged(pacifist_choice(g, me, p)))['yes']:
            g.notes['Pacifist saves'] = g.notes.get('Pacifist saves', 0) + 1
            g.add(State('safe', p.name, source=me.name, against='execution', ends_with_source=True,
                        while_source_works=True))


class Fool(Townsfolk):
    name = 'Fool'
    ability = ability(name)

    def survives(self, game, me, cause):
        # asked only once no protection saved them (the Tea Lady's, the Innkeeper's keep the Fool's ability); a drunk
        # or poisoned Fool dies
        g = game.g
        if g.works(me, self.name) and not g.spent_ability(self.name):
            g.spend(self.name)
            return True
        return False


class Gambler(Townsfolk):
    name = 'Gambler'
    ability = ability(name)
    night_choice = Choose(players=1, character=True, prompt='Choose a player (alive or dead, even yourself) and guess '
                                                            'their character: if you guess wrong, you die.')

    async def resolve_night(self, game, night):
        g = game.g
        gam, t = night.choice_of(g, self.name)
        guess = night.characters.get(gam.name) if gam else None
        # wrong: not a character they could register as (in Bad Moon Rising, their character). No feedback; the death
        # is the Gambler's own ability's, so protections stop it
        if t and guess and g.works(gam, self.name) and guess not in g.registers_as(g[t], gam):
            game.attempt_kill(gam, 'gambler', gam, night)


class Professor(Townsfolk):
    name = 'Professor'
    ability = ability(name)
    night_choice = Choose(players=1, optional=True, dead_only=True,
                          prompt='Once per game, you may choose a dead player: if they are a Townsfolk, they are '
                                 'resurrected. Or choose no one, and keep your ability.')

    def night_spec(self, game, me, night):
        return None if game.g.spent_ability(self.name) else self.night_choice

    async def resolve_night(self, game, night):
        g = game.g
        prof, t = night.choice_of(g, self.name)
        if not t:
            return
        works = g.works(prof, self.name)
        g.spend(self.name)  # gone even if nothing happens (an Outsider, a Minion, a Demon, or a drunk Professor)
        p = g[t]
        if works and not p.alive and kind(p.character) == 'Townsfolk':
            g.revive(p, self.name)  # alive at dawn (not why); they wake later tonight if their step comes later
            night.revived.append(p)
            await rules(p.character).resurrected(game, p, night)


# ---- The information Townsfolk, the Gossip, and the Outsiders ---------------------------------------------------

def grandchild_choice(g, gm):
    """The Grandchild, marked before the first night: any good player (the Lunatic, a Goon), usually a Townsfolk."""
    good = [q.name for q in g.players if not q.evil and q is not gm]
    towns = [x for x in good if kind(g[x].character) == 'Townsfolk']
    others = [x for x in good if x not in towns]

    def style(r):
        pool = towns if towns and (not others or r.random() < POLICY['grandchild_townsfolk']) else others
        return {'players': [r.choice(pool)]}
    return judged(Choice(f'Grandchild:{gm.name}', [{'players': [x]} for x in good], style), 'grandchild',
                  f'Which good player is the Grandmother\'s ({gm.name}) Grandchild? Any good player, usually a '
                  'Townsfolk.', recipient=gm.name)


def grandmother_choice(g, gm, child):
    """What the Grandmother is shown: the Grandchild and their character. An impaired one may be shown any player
    with any good character; when misinformed, a false pair (an evil player, usually, as a good character, or a good
    player as a character they are not), never the Grandmother's own character."""
    true = {'players': [child], 'character': g[child].character}
    impaired = g.impaired(gm)
    others = [q.name for q in g.players if q is not gm]
    values = [{'players': [x], 'character': c} for x in others for c in g.script.good] if impaired else [true]

    def style(r):
        if impaired and g.misinformed(gm, r):
            evil = [q.name for q in g.players if q.evil and q is not gm]
            for _ in range(30):
                x = r.choice(evil) if evil and r.random() < POLICY['false_vouch_evil'] else r.choice(others)
                c = g.fake_good(r, (g.script.townsfolk, g.script.outsiders), bluffs=g[x].evil,
                                avoid=(gm.shown, g[x].character, g[x].shown))
                if c in g.script.good:
                    return {'players': [x], 'character': c}
        return true
    choice = Choice(f'Grandmother:{gm.name}', values, style)
    choice.truth = lambda v: v['players'] == [child] and v['character'] == true['character']
    choice.context = {'call': 'information', 'about': child, 'recipient': gm.name, 'impaired': impaired,
                      'question': f'Which player and character is {gm.name} (Grandmother) shown as their Grandchild?'}
    return choice


class Grandmother(Townsfolk):
    name = 'Grandmother'
    ability = ability(name)
    info = True
    setup_order = 4  # after the Lunatic's (a good player who may be the Grandchild)

    async def setup(self, game):
        g = game.g
        gm = g.with_character(self.name)
        if gm:
            g.notes['Grandchild'] = (await game.decide_judged(grandchild_choice(g, gm)))['players'][0]

    async def show(self, game, gm, n):
        g = game.g
        child = g.notes.get('Grandchild')
        if not child:
            return
        v = await game.decide_judged(grandmother_choice(g, gm, child))
        game.woken(gm)
        text = f'your Grandchild is {v["players"][0]}, the {v["character"]}.'
        game.inform(gm, f'Night {n} — Grandmother: {text}')
        g.reminders.append(f'{gm.name} (Grandmother) was shown: {text}')

    async def resolve_night(self, game, night):
        gm = game.g.with_character(self.name)
        if gm and night.first:
            await self.show(game, gm, night.n)

    async def resurrected(self, game, me, night):
        # the Professor's example: a resurrected Grandmother learns their Grandchild again (the same one, a reading:
        # the GRANDCHILD reminder stays where it was put)
        await self.show(game, me, night.n)

    def on_death(self, game, me, dead, cause, alive_before):
        g = game.g
        # only the Demon's kill (its attack, the Pukka's poison too); her sobriety and life at that moment decide.
        # Her death is her own ability's, so a protection on her stops it (a reading: as for the Tinker)
        if dead.name == g.notes.get('Grandchild') and cause == 'demon' and g.works(me, self.name):
            game.ability_kill(me, 'grandmother', me)


def chambermaid_choice(g, cm, pair, n):
    """How many of the Chambermaid's two woke tonight to use their ability (Grimoire.woke). An impaired one may be
    shown any count; when misinformed, a false one."""
    woke = set(g.woke.get(n, []))
    true = sum(1 for x in pair if x in woke)
    impaired = g.impaired(cm)
    values = [0, 1, 2] if impaired else [true]

    def style(r):
        if impaired and g.misinformed(cm, r):
            return {'number': r.choice([v for v in values if v != true])}
        return {'number': true}
    choice = Choice(f'Chambermaid:{cm.name}', [{'number': v} for v in values], style)
    choice.truth = lambda v: v['number'] == true
    choice.context = {'call': 'information', 'about': None, 'recipient': cm.name, 'impaired': impaired,
                      'question': f'{cm.name} (Chambermaid) chose {" and ".join(pair)}: how many of them woke tonight '
                                  'to use their own ability?'}
    return choice


class Chambermaid(Townsfolk):
    name = 'Chambermaid'
    ability = ability(name)
    info = True
    night_choice = Choose(players=2, alive_only=True, may_self=False,
                          prompt='Choose two alive players (not yourself): you learn how many of them woke tonight to '
                                 'use their ability.')

    def night_spec(self, game, me, night):
        alive = [p for p in game.g.players if p.appears_alive and p is not me]
        return self.night_choice if len(alive) >= 2 else None  # not woken without two players to choose

    async def resolve_night(self, game, night):
        # last in the night order: everyone who wakes tonight has woken. Being told something (the Demon learning
        # the Exorcist, the Goon its alignment) is not waking to use an ability; a drunk player who woke counts
        g = game.g
        cm = g.with_character(self.name)
        pair = night.chosen.get(cm.name, []) if cm else []
        if len(pair) == 2:
            v = await game.decide_judged(chambermaid_choice(g, cm, pair, night.n))
            game.inform(cm, f'Night {night.n} — Chambermaid: you chose {pair[0]} and {pair[1]}: {v["number"]} of '
                            'them woke tonight to use their ability.')


def gossip_truth(g, speaker, text):
    """Whether a statement of one of the simple forms the code can check is true, against the Grimoire now: "X is
    (not) the Y", "X is evil/good", "X is a Townsfolk/Outsider/Minion/Demon", "the Demon is X", "the Y is (not) in
    play", "there is no Y in play" (X a player or "I", Y a character on the script; "I am the Gossip." and "My
    statement is:" in front are ignored). None for anything else: a judge rules on it."""
    s = ' '.join((text or '').lower().replace('’', "'").split())
    s = re.sub(r"\bi'm\b", 'i am', s).replace("isn't", 'is not').replace("aren't", 'are not')
    s = re.sub(r'^i am the gossip\s*[.!,;:-]*\s*', '', s)
    s = re.sub(r'^(?:and\s+)?(?:my\s+)?(?:public\s+)?statement(?:\s+is)?\s*[:,-]?\s*', '', s)
    s = s.strip(' "\'.!')
    if not s:
        return None
    names = {n.lower(): n for n in g.by_name}
    chars = {c.lower(): c for c in g.script.all}
    alt = lambda xs: '|'.join(re.escape(x) for x in sorted(xs, key=len, reverse=True))
    player, char = rf"(?P<p>{alt(names)}|i)", rf"(?P<c>{alt(chars)})"
    art = r'(?:the |a |an )?'

    def who(m):
        return speaker if m.group('p') == 'i' else g[names[m.group('p')]]

    def answer(possible, neg):
        if len(possible) > 1:
            return None  # registers either way (none can in Bad Moon Rising): a judge rules
        return next(iter(possible)) != bool(neg)

    m = re.fullmatch(rf'{player} (?:is|am) (?P<neg>not )?(?P<a>evil|good)', s)
    if m:
        return answer({e == (m.group('a') == 'evil') for e in g.registers_evil(who(m))}, m.group('neg'))
    m = re.fullmatch(rf'{player} (?:is|am) (?P<neg>not )?{art}(?P<k>townsfolk|outsider|minion|demon)', s)
    if m:
        return answer({kind(c).lower() == m.group('k') for c in g.registers_as(who(m))}, m.group('neg'))
    m = re.fullmatch(rf'the demon is (?P<neg>not )?{player}', s)
    if m:
        return answer({kind(c) == 'Demon' for c in g.registers_as(who(m))}, m.group('neg'))
    m = re.fullmatch(rf'{player} (?:is|am) (?P<neg>not )?{art}{char}', s)
    if m:
        return answer({c == chars[m.group('c')] for c in g.registers_as(who(m))}, m.group('neg'))
    in_play = lambda c: any(q.character == chars[c] for q in g.players)  # dead players' characters too
    m = re.fullmatch(rf'{art}{char} is (?P<neg>not )?in play', s)
    if m:
        return in_play(m.group('c')) != bool(m.group('neg'))
    m = re.fullmatch(rf'there is (?P<q>no|not an?|not the|an?|the) {char} in play', s)
    if m:
        return in_play(m.group('c')) != m.group('q').startswith('no')
    return None


def statement_choice(g, gossip, text):
    """Whether a statement the code can't check is true, false, or doesn't count. The scripted Storyteller can't
    read it: for it, the statement is not true."""
    choice = Choice(f'Gossip:{gossip.name}', [{'yes': True}, {'yes': False}, {'yes': None}], lambda r: {'yes': False})
    choice.context = {'call': 'statement', 'about': None, 'recipient': gossip.name, 'impaired': False,
                      'question': f'{gossip.name} (the Gossip) made this public statement: "{text}". Is it definitely '
                                  'true (yes: True), definitely false (yes: False), or does it not count (nothing): '
                                  'not definite, about the future or intentions, or not something you know?'}
    return choice


def will_die(g, p, cause):
    """Whether `p` would really die from `cause` now: alive, unprotected, and not the Fool with their ability."""
    if not p.appears_alive or g.safe(p, cause):
        return False
    return not (p.character == 'Fool' and g.works(p, 'Fool') and not g.spent_ability('Fool'))


def gossip_victim_choice(g, gossip):
    """Whom the Gossip's true statement kills: any player. The almanac recommends one who will actually die; the
    scripted Storyteller never picks the Demon (the game would end by its choice), usually a good player, and with
    three alive one who won't die if there is one (a death would end the game)."""
    alive = [p.name for p in g.players if p.appears_alive]

    def style(r):
        dying = [x for x in alive if will_die(g, g[x], 'gossip') and not g[x].is_demon]
        if g.alive_count() <= 3:
            safe = [x for x in alive if x not in dying and not g[x].is_demon]
            if safe:
                return {'players': [r.choice(safe)]}
        evil = [x for x in dying if g[x].evil]
        good = [x for x in dying if not g[x].evil]
        pool = evil if evil and (not good or r.random() < POLICY['gossip_victim_evil']) else (good or dying or alive)
        return {'players': [r.choice(pool)]}
    choice = Choice(f'Gossip kill:{gossip.name}', [{'players': [x]} for x in alive], style)
    choice.context = {'call': 'gossip_victim', 'about': None, 'recipient': gossip.name, 'impaired': False,
                      'question': "The Gossip's statement yesterday was true: which player dies tonight? Usually one "
                                  'who will actually die (not one protected, nor the Fool), so the Gossip learns from '
                                  'it; never to end the game by your own choice.'}
    return choice


class Gossip(Townsfolk):
    name = 'Gossip'
    ability = ability(name)
    public_action = 'ability'  # the statement, through the shared `ability` field

    def act_publicly(self, game, actor, target, text=None):
        g = game.g
        p = g[actor]
        if p.character != self.name or not p.alive or g.notes.get('Gossip statement') == game.day:
            return False  # anyone may claim it; only the living Gossip's first statement of the day counts
        g.notes['Gossip statement'] = day = game.day

        async def rule(game):
            # judged as made (true or not, whatever the Gossip's sobriety): a drunk Gossip's true statement kills if
            # the Gossip is sober tonight (the almanac's example)
            true = gossip_truth(g, p, text)
            if true is None:
                true = (await game.decide_judged(statement_choice(g, p, text)))['yes']
            else:
                game.emit('st_choice', {'id': f'Gossip:{p.name}', 'value': {'yes': true}, 'valid': True,
                                        'checked': 'by the engine'}, 'audit')
            if true:
                g.notes['Gossip true'] = day
        game.later(rule)
        return False

    async def resolve_night(self, game, night):
        g = game.g
        gossip = g.with_character(self.name)
        if gossip and g.notes.get('Gossip true') == night.n - 1 and g.works(gossip, self.name):
            victim = (await game.decide_judged(gossip_victim_choice(g, gossip)))['players'][0]
            game.attempt_kill(g[victim], 'gossip', gossip, night)


class Goon(Outsider):
    name = 'Goon'
    ability = ability(name)

    def chosen(self, game, me, chooser, night):
        g = game.g
        key = f'Goon:{me.name}'
        if chooser is me or g.notes.get(key) == night.n or not g.works(me, self.name):
            return  # only the first chooser each night, and only while the Goon has a working ability
        g.notes[key] = night.n
        # drunk at once (even if already drunk or poisoned), until dusk; it ends if the Goon dies (a reading, as in
        # batch 2: the Assassin's kill still lands, since its sobriety was settled as it chose)
        g.add(State('drunk', chooser.name, source=me.name, until='night', ends_with_source=True))
        if me.alignment != chooser.alignment:
            me.alignment = chooser.alignment
            game.emit('alignment', {'player': me.name, 'alignment': me.alignment}, 'audit')
            game.inform(me, f'Night {night.n} — Goon: you are now {me.alignment}.')


def lunatic_demon_choice(g, demon):
    """The Demon the Lunatic believes they are: usually the one in play, sometimes another on the script."""
    real = demon.character if demon else g.script.demons[0]
    others = [d for d in g.script.demons if d != real]

    def style(r):
        return {'character': real if not others or r.random() < POLICY['lunatic_same_demon'] else r.choice(others)}
    lun = next((q.name for q in g.players if q.character == 'Lunatic'), None)
    return judged(Choice('Lunatic:demon', [{'character': d} for d in g.script.demons], style), 'lunatic_demon',
                  f'Which Demon does the Lunatic believe they are? Usually the one in play ({real}).', about=lun,
                  recipient=lun)


def lunatic_minions_choice(g, lun, demon, k):
    """The Lunatic's "Minions": any players, as many as there are Minions. Sometimes the real Demon is among them
    (the almanac's Zombuul "pretending to be the Lunatic's Minion"), else any others."""
    others = [q.name for q in g.players if q is not lun]

    def style(r):
        if demon and r.random() < POLICY['lunatic_shows_demon']:
            rest = [x for x in others if x != demon.name]
            return {'players': [demon.name] + r.sample(rest, k - 1)}
        return {'players': r.sample([x for x in others if not demon or x != demon.name] or others, k)}
    return judged(Choice('Lunatic:minions', [{'players': list(c)} for c in combinations(others, k)], style),
                  'lunatic_minions', f'Which {k} player{"s" if k > 1 else ""} does the Lunatic ({lun.name}) see as '
                  'their Minions? Any players; sometimes the real Demon among them.', about=lun.name,
                  recipient=lun.name)


def lunatic_bluffs_choice(g):
    """The Lunatic's three bluffs: any good characters, even ones in play (never the Lunatic itself, which would
    tell them everything)."""
    pool = [c for c in g.script.good if c != 'Lunatic']
    in_play = {q.character for q in g.players}

    def style(r):
        picks = []
        for _ in range(3):
            want_in = r.random() < POLICY['lunatic_bluff_in_play']
            options = [c for c in pool if c not in picks and (c in in_play) == want_in]
            picks.append(r.choice(options or [c for c in pool if c not in picks]))
        return {'characters': picks}
    lun = next((q.name for q in g.players if q.character == 'Lunatic'), None)
    return judged(Choice('Lunatic:bluffs', [{'characters': list(c)} for c in combinations(pool, 3)], style),
                  'lunatic_bluffs', 'Which three good characters does the Lunatic learn as their Demon bluffs? Any, '
                  'even characters in play.', about=lun, recipient=lun)


class Lunatic(Outsider):
    name = 'Lunatic'
    ability = ability(name)
    wakes_at_own_step = True  # as their Demon, before the real one, and only when that Demon would wake
    setup_order = 3

    async def setup(self, game):
        g = game.g
        lun = g.with_character(self.name)
        if not lun:
            return
        demon = g.demon()
        lun.shown = (await game.decide_judged(lunatic_demon_choice(g, demon)))['character']
        k = sum(1 for q in g.players if kind(q.character) == 'Minion')
        minions = (await game.decide_judged(lunatic_minions_choice(g, lun, demon, k)))['players']
        minions = sorted(minions, key=lambda x: g[x].seat)
        bluffs = (await game.decide_judged(lunatic_bluffs_choice(g)))['characters']
        g.notes['Lunatic'] = {'minions': minions, 'bluffs': bluffs}
        g.reminders.append(f'{lun.name} (Lunatic) believes they are the {lun.shown}, and was shown Minions '
                           f'{", ".join(minions)} and bluffs {", ".join(bluffs)}.')

    def intro(self, game, me):
        from .game import demon_info  # (game.py imports this module's registry)
        shown = game.g.notes.get('Lunatic')
        return [demon_info(shown['minions'], shown['bluffs'])] if shown else []

    async def resolve_night(self, game, night):
        # the real Demon learns the Lunatic on the first night, and each night whom they chose, before it acts.
        # Being told is not waking for an ability; an Exorcist who chooses the Lunatic does nothing (not the Demon)
        g = game.g
        lun, demon = g.with_character(self.name), g.demon()
        if not (lun and demon):
            return
        if night.first:
            game.inform(demon, f'Night {night.n}: {lun.name} is the Lunatic (they believe they are the {lun.shown}).')
        if lun.name in night.chosen:
            picks = night.chosen[lun.name]
            game.inform(demon, f'Night {night.n}: the Lunatic ({lun.name}) chose {", ".join(picks) or "no one"}.')


def tinker_choice(g, tinker, when):
    """Whether the Tinker dies now (asked only when the death would land and not end the game)."""
    def style(r):
        if g.notes.get('Tinker never'):
            return {'yes': False}
        return {'yes': r.random() < POLICY['tinker_night' if when == 'night' else 'tinker_day']}
    choice = Choice(f'Tinker:{tinker.name}', [{'yes': True}, {'yes': False}], style)
    return judged(choice, 'tinker', f'Does the Tinker ({tinker.name}) die now ({when})? Most interesting at night; '
                                    'never to end the game.', about=tinker.name, recipient=tinker.name, helps='evil')


class Tinker(Outsider):
    name = 'Tinker'
    ability = ability(name)
    setup_order = 5

    async def setup(self, game):
        # sometimes, the Storyteller never kills the Tinker (it makes them look suspicious): decided once per game
        t = game.g.with_character(self.name, alive=False)
        choice = judged(yes_choice('Tinker:never', POLICY['tinker_never']), 'tinker_never',
                        'Before the game: will the Tinker never die by their own ability this game (yes: true)? '
                        'Sometimes, to make the Tinker look suspicious.', about=t and t.name, recipient=t and t.name)
        game.g.notes['Tinker never'] = (await game.decide_judged(choice))['yes']

    def can_die(self, g, me):
        # sober and healthy, not protected (the Tea Lady's, the Innkeeper's), and never when it would end the game
        return g.works(me, self.name) and will_die(g, me, 'tinker') and g.alive_count() > 3 and not g.winner

    async def resolve_night(self, game, night):
        g = game.g
        t = g.with_character(self.name)
        if t and self.can_die(g, t) and (await game.decide_judged(tinker_choice(g, t, 'night')))['yes']:
            game.ability_kill(t, 'tinker', t)

    async def moment(self, game, me, when):
        g = game.g
        if self.can_die(g, me) and (await game.decide_judged(tinker_choice(g, me, when)))['yes']:
            game.ability_kill(me, 'tinker', me)  # by day announced at once, not why


class Moonchild(Outsider):
    name = 'Moonchild'
    ability = ability(name)
    public_action = 'ability'  # anyone may claim to curse (a bluff); the real Moonchild is asked when they die

    def act_publicly(self, game, actor, target, text=None):
        return False

    def on_death(self, game, me, dead, cause, alive_before):
        if dead is not me or me.alive:
            return
        if game.tonight is not None:  # they learn it at dawn
            game.g.notes.setdefault('Moonchild at dawn', []).append(me.name)
        else:  # executed or killed by day: at once (a Moonchild who survives an execution never chooses)
            game.later(lambda game: self.curse(game, me))

    def moment(self, game, me, when):
        due = game.g.notes.get('Moonchild at dawn', [])
        if when == 'dawn' and me.name in due:
            due.remove(me.name)
            game.later(lambda game: self.curse(game, me))

    async def curse(self, game, me):
        """The public choice: asked of the player, completed at random if they name no alive player (the almanac:
        not choosing is cheating). Whether it kills is decided by the target's alignment now."""
        g = game.g
        options = [p.name for p in g.players if p.appears_alive]
        if not options:
            return
        req = game.request('death_choice', f'Day {game.day}: you have died. Moonchild: publicly choose an alive player '
                                           '(`targets`): if they are good, they die tonight.', game.day, n_targets=1,
                           options=options)
        t = game.targets(me.name, await game.ask(me.name, req), req)[0]
        game.emit('ability', {'player': me.name, 'character': self.name, 'target': t})
        g.notes.setdefault('Moonchild curses', []).append({'moonchild': me.name, 'target': t, 'good': not g[t].evil,
                                                           'day': game.day})

    async def resolve_night(self, game, night):
        g = game.g
        curses = g.notes.get('Moonchild curses', [])
        g.notes['Moonchild curses'] = [c for c in curses if c['day'] >= night.n]
        for c in curses:
            mc = g[c['moonchild']]
            # tonight's sobriety decides (a dead Moonchild can be drunk or poisoned), not the day's
            if c['day'] < night.n and c['good'] and self.name in g.abilities(mc) and not g.impaired(mc):
                game.attempt_kill(g[c['target']], 'moonchild', mc, night)


CHARACTERS.update({c.name: c() for c in [Godfather, DevilsAdvocate, Assassin, Mastermind, Zombuul, Pukka,
                                          Shabaloth, Po, Sailor, Innkeeper, Courtier, Minstrel, Exorcist, TeaLady,
                                          Pacifist, Fool, Gambler, Professor, Grandmother, Chambermaid, Gossip, Goon,
                                          Lunatic, Tinker, Moonchild]})
