"""Bad Moon Rising's characters, on the script-independent core (characters.py, state.py, game.py).

Each entry follows the almanac's How to Run. Where the rules leave a question open, a comment says which reading
the entry takes, and why.
"""
from __future__ import annotations
from itertools import combinations

from .characters import CHARACTERS, Choose, Demon, Minion, Townsfolk, kind, rules
from .state import POLICY, Choice, State, setup_changes, team_sizes, yes_choice


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
    choice.context = {'about': None, 'recipient': p.name, 'impaired': impaired,
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

    def night_spec(self, game, me, night):
        return None if night.first or game.g.spent_ability(self.name) else self.night_choice

    async def resolve_night(self, game, night):
        g = game.g
        a, t = night.choice_of(g, self.name)
        if not t:
            return
        works = g.works(a, self.name)
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
            game.demon_attack(g[t], z, night)


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
            game.demon_attack(g[s.target], pukka, night)
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
    choice.context = {'about': None, 'recipient': shab.name, 'impaired': False,
                      'question': f'Does the Shabaloth regurgitate one of the dead players it chose last night (alive '
                                  f'again at dawn), and whom? Rarely: once a game, maybe twice ({done} so far).'}
    return choice


class Shabaloth(Demon):
    name = 'Shabaloth'
    ability = ability(name)
    night_choice = Choose(players=2, prompt='Choose two players: they die.')
    kills_at_night = True

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
            if not g.works(shab, self.name):
                break  # the first pick made the Shabaloth drunk (the Goon)
            game.demon_attack(g[t], shab, night)


class Po(Demon):
    name = 'Po'
    ability = ability(name)
    night_choice = Choose(players=1, prompt='You may choose a player: they die. If you choose no one, next time you '
                                            'choose three.', optional=True)
    charged = Choose(players=3, prompt='Last time you chose no one, so choose three players tonight: they die.')
    kills_at_night = True

    def night_spec(self, game, me, night):
        # "last choice": the first night and a night the Po was not woken (the Exorcist) are not choices, so a
        # charge survives them; a drunk Po's "no one" still charges
        return self.charged if game.g.last_choices.get(me.name) == [] else self.night_choice

    async def resolve_night(self, game, night):
        g = game.g
        po = g.with_character(self.name)
        for t in night.chosen.get(po.name, []) if po else []:
            if not g.works(po, self.name):
                break  # a pick made the Po drunk (the Goon): the later ones fail
            game.demon_attack(g[t], po, night)


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
    choice.context = {'about': target, 'recipient': sailor.name, 'impaired': False,
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
    choice.context = {'about': None, 'recipient': inn.name, 'impaired': False,
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
    choice.context = {'about': p.name, 'recipient': pac.name, 'impaired': False,
                      'question': f'{p.name} (good) is being executed. Does the Pacifist ({pac.name}) save them, so '
                                  f'they are executed but do not die? About once a game is usual, more likely at the '
                                  f'climax, and less if good is winning ({saves} saved so far).'}
    return choice


class Pacifist(Townsfolk):
    name = 'Pacifist'
    ability = ability(name)
    setup_order = 2

    def setup(self, game):
        # rarely, the Storyteller never saves anyone, to make the Pacifist look suspicious: decided once per game
        game.g.notes['Pacifist never'] = game.decide(yes_choice('Pacifist:never', POLICY['pacifist_never']))['yes']

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


CHARACTERS.update({c.name: c() for c in [Godfather, DevilsAdvocate, Assassin, Mastermind, Zombuul, Pukka,
                                          Shabaloth, Po, Sailor, Innkeeper, Courtier, Minstrel, Exorcist, TeaLady,
                                          Pacifist, Fool, Gambler, Professor]})
