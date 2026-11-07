"""The experimental characters (the official data's "carousel" edition) and the jinxes between built characters, on
the script-independent core (characters.py, state.py, game.py), for custom scripts.

Each entry follows the almanac's How to Run (the wiki's, for characters the printed almanac predates). Where the rules
leave a question open, a comment says which reading the entry takes, and why (docs/carousel-rulings.md lists them for
review, numbered across batches).

Jinxes. An official jinx is in effect when both its characters are on the script (`Script.jinxed`), in play or not;
the code a jinx changes asks that and then checks the situation the jinx describes. A jinx between two characters of
the base scripts changes their own entries (in characters.py, bmr.py or snv.py), guarded so that Trouble Brewing, Bad
Moon Rising and Sects & Violets, which hold no jinx, play as before. Every implemented jinx is declared below with
`jinx(a, b, where)`; tests/test_carousel.py checks that each official jinx between two built characters is.
"""
from __future__ import annotations
from itertools import combinations

from . import bmr, snv
from .characters import CHARACTERS, Choose, Demon, Minion, Outsider, Townsfolk, holds, jinx, kind, rules
from .state import POLICY, Choice, State, judged, yes_choice


def ability(name):
    """The official ability text."""
    from . import official
    return official.role(name)['ability']


def townsfolk(q):
    return kind(q.character) == 'Townsfolk'


# Later entries share Sects & Violets' helpers, through the module (snv may be the module being imported first, so
# its names are not bound yet when this one loads): who has or believes they have an ability (snv.believers,
# snv.holders), information through the judge (snv.info, snv.learn, snv.when), once-per-game abilities per player
# (snv.used, snv.use, snv.fresh), the abnormal record for the Mathematician (snv.failed), the final night
# (snv.final_night).
BASE = snv


# ---- Batch 0: the jinxes between characters of the base scripts (docs/carousel-rulings.md, 5-11) ---------------

jinx('Mastermind', 'Vigormortis', 'snv.Vigormortis.dies')
jinx('Mathematician', 'Chambermaid', 'bmr.chambermaid_choice')
jinx('Mathematician', 'Drunk', 'game.Game.note_information; characters.Drunk; characters.Slayer.act_publicly')
jinx('Mathematician', 'Lunatic', 'snv.lunatic_attacked_elsewhere')
jinx('Pit-Hag', 'Goon', 'snv.PitHag.resolve_night; bmr.Goon.chosen')
jinx('Recluse', 'Sage', 'snv.sage_choice')
jinx('Scarlet Woman', 'Fang Gu', 'characters.ScarletWoman.on_death')


# ---- Batch 1: thirteen experimental characters (docs/carousel-rulings.md, 14 on), and their jinxes ---------------
# They complete four corpus scripts: deadpeople (Banshee, Damsel), wonders (Steward, Nightwatchman, Al-Hadikhia),
# binarysupernovae (Magician, Golem, Summoner, Ojo) and djinnsbargain (Fisherman, Plague Doctor, Hatter, Politician).

def living_good(g, p=None):
    return [q.name for q in g.players if q.alive and not q.evil and q is not p]


# ---- Townsfolk ---------------------------------------------------------------------------------------------------

class Banshee(Townsfolk):
    name = 'Banshee'
    ability = ability(name)

    def on_death(self, game, me, dead, cause, alive_before):
        # killed by the Demon's attack (any Demon's: the Vortox's, the Ojo's, the Al-Hadikhia's), sober and healthy
        # as they die; a Philosopher with the Banshee's ability too. Not the Pit-Hag's arbitrary deaths, nor a
        # Demon's other kills (a reading: "the Demon kills you" is its attack)
        g = game.g
        if dead is not me or me.alive or cause != 'demon' or self.name not in g.abilities(me) or g.impaired(me):
            return
        powers = g.notes.setdefault('Banshee', [])
        if me.name in powers:
            return
        powers.append(me.name)
        if not self.announced(g):
            return
        if game.tonight is not None:
            g.notes.setdefault('Banshee at dawn', []).append(me.name)
        else:
            self.announce(game, me)

    @staticmethod
    def announced(g):
        """The announcement tells every player something about a Townsfolk's ability, so a working Vortox would
        make it false: the Storyteller stays silent (the powers still come). The Vortox jinx: it is announced."""
        if g.script.jinxed('Banshee', 'Vortox'):
            return True
        return not any(q.character == 'Vortox' and g.works(q, 'Vortox') for q in g.players)

    def announce(self, game, me):
        game.emit('text', {'text': f'The Storyteller announces: {me.name} has died, killed by the Demon, and is the '
                                   'Banshee. From now on they may nominate twice a day and vote twice on each '
                                   'nomination, even though dead.'})

    def moment(self, game, me, when):
        due = game.g.notes.get('Banshee at dawn', [])
        if when == 'dawn' and me.name in due:
            due.remove(me.name)
            self.announce(game, me)

    @staticmethod
    def screams(g, me):
        """The powers: since the Demon killed them, while they have the Banshee's ability (a drunk or poisoned dead
        Banshee has none for now). Brought back to life, they keep them (a reading)."""
        return me.name in g.notes.get('Banshee', ()) and 'Banshee' in g.abilities(me) and not g.impaired(me)

    def nomination_limit(self, g, me):
        return 2 if self.screams(g, me) else None

    def vote_weight(self, g, me):
        return 2 if self.screams(g, me) else 1

    def free_vote(self, g, me):
        return self.screams(g, me)  # every nomination, without spending a ghost vote


def steward_choice(g, p):
    """The Steward's good player (never themself). Misinformed: a good player of their false world (Grimoire.decoy),
    redrawn until it is one who can't register as good."""
    others = [q.name for q in g.players if q is not p]
    good = [x for x in others if False in g.registers_evil(g[x], p)]
    impaired = g.unreliable(p, 'Steward')
    values = others if impaired else good

    def style(r):
        if impaired and g.misinformed(p, r):  # a good player of their false world, redrawn until it is false
            def world(r):
                evil = g.false_evil(p, r)
                return r.choice([x for x in others if x not in evil] or others)
            return {'players': [g.false_result(p, r, world, set(good))]}
        shown = g.sample_evil(r)  # a misregistering Spy may be shown as good, a Recluse not
        return {'players': [r.choice([x for x in good if x not in shown] or good)]}
    return snv.info(Choice(f'Steward:{p.name}', [{'players': [x]} for x in values], style), g, p, 'Steward',
                    f'Which good player does {p.name} (Steward) learn?', lambda v: v['players'][0] in good, impaired)


class Steward(Townsfolk):
    name = 'Steward'
    ability = ability(name)
    info = True

    async def show(self, game, p):
        choice = steward_choice(game.g, p)
        if choice.values:
            await snv.learn(game, p, self.name, choice, lambda v: f'{v["players"][0]} is good.')

    async def resolve_night(self, game, night):
        if night.first:
            for p in snv.believers(game.g, self.name):
                await self.show(game, p)

    async def becomes(self, game, me):
        if me.alive and not (game.tonight is not None and game.tonight.first):
            await self.show(game, me)  # a new Steward learns at once (as the Clockmaker)


def nightwatchman_choice(g, nw, t):
    """Whom the Nightwatchman's chosen player learns is the Nightwatchman. A drunk or poisoned Nightwatchman (or one
    the Vortox falsifies: it is a Townsfolk's information) shows them another player, or nothing."""
    others = [q.name for q in g.players if q.name != t and q is not nw]
    impaired = g.unreliable(nw, 'Nightwatchman')
    values = [[nw.name]] + ([[]] + [[x] for x in others] if impaired else [])

    def style(r):
        if impaired and g.misinformed(nw, r):
            return {'players': [r.choice(others)] if others and r.random() < POLICY['nightwatchman_shown_other']
                    else []}
        return {'players': [nw.name]}
    return snv.info(Choice(f'Nightwatchman:{nw.name}', [{'players': v} for v in values], style), g, nw,
                    'Nightwatchman', f'{nw.name} (Nightwatchman) chose {t}: whom does {t} learn is the Nightwatchman '
                    '(no one: they are not woken)?', lambda v: v['players'] == [nw.name], impaired, about=t)


class Nightwatchman(Townsfolk):
    name = 'Nightwatchman'
    ability = ability(name)
    night_choice = Choose(players=1, may_self=False, optional=True,
                          prompt='Once per game, you may choose a player: they learn that you are the Nightwatchman. '
                                 'Or choose no one, and keep your ability for a later night.')

    def night_spec(self, game, me, night):
        return None if snv.used(game.g, me, self.name) else self.night_choice

    async def resolve_night(self, game, night):
        g = game.g
        for nw in [q for q in snv.believers(g, self.name) if q.name in night.chosen]:  # a Drunk one too
            t = (night.chosen[nw.name] or [None])[0]
            if not t or snv.used(g, nw, self.name):
                continue
            snv.use(g, nw, self.name)  # spent, drunk or not
            shown = (await game.decide_judged(nightwatchman_choice(g, nw, t)))['players']
            if shown:
                game.inform(g[t], f'Night {night.n}: you are woken: {shown[0]} is the Nightwatchman.')

    def becomes(self, game, me):
        snv.fresh(game.g, me, self.name)


class Magician(Townsfolk):
    name = 'Magician'
    ability = ability(name)

    @staticmethod
    def vizier_nulled(g):
        """The Vizier jinx (batch 4): with the Vizier in play, the Magician has no ability."""
        return g.script.jinxed('Magician', 'Vizier') and any(q.character == 'Vizier' for q in g.players)

    def execution(self, game, me, executed):
        # the Wraith jinx (batch 4): after each execution (dying or not), the living Magician may publicly guess a
        # living player as the Wraith; right, the Demon must choose them tonight
        g = game.g
        if g.script.jinxed(self.name, 'Wraith') and me.alive and me.character == self.name \
                and not self.vizier_nulled(g):
            from .carousel5 import wraith_guess
            game.later(lambda game: wraith_guess(game, me, self.name))
        return None

    def shown_to_evil(self, g, me, viewer):
        # the first night's evil information only (Game.setup): the Demon sees the Magician among its Minions, the
        # Minions see the Magician and the Demon as "the Demon" (with no Demon in play, the Magician alone). A
        # Magician poisoned from the start (the No Dashii's neighbour) does nothing. How they register to abilities
        # is untouched (a reading: the ability names what evil "thinks", not registration)
        if g.impaired(me) or self.vizier_nulled(g):
            return None
        return 'Minion' if viewer.is_demon else 'Demon' if kind(viewer.character) == 'Minion' else None


def fisherman_statements(g, p):
    """The advice the Storyteller may give: the Savant's statements (snv.savant_statements, true and false, checked
    against the Grimoire), and "X is the Y" for each living player who registers as one character. Each says
    whether it helps the Fisherman's team: for good, statements that point at evil players (alignment, the Demon's
    seat, evil characters, poison, choices, votes); for evil, ones about good characters and the setup."""
    out = [dict(s) for s in snv.savant_statements(g, p)]
    for q in g.players:
        reg = g.registers_as(q, p)
        if q.alive and q is not p and len(reg) == 1:
            c = next(iter(reg))
            out.append({'form': 'character', 'text': f'{q.name} is the {c}.', 'true': True, 'about': (q.name,),
                        'character': c})
    evil = p.evil
    for s in out:
        if s['form'] == 'character':
            s['helps'] = rules(s['character']).evil != evil
        elif s['form'] == 'in_play':
            c = s['text'][len('There is a '):-len(' in play.')]
            s['helps'] = c in CHARACTERS and rules(c).evil != evil
        else:
            s['helps'] = (s['form'] in ('outsiders', 'impaired', 'alignment') if evil else
                          s['form'] in ('evil', 'demon_near', 'minion_near', 'alignment', 'impaired', 'chosen',
                                        'dead', 'voted', 'nominated', 'neighbours', 'true_info'))
    return out


def fisherman_choice(g, p):
    """The Fisherman's advice: one true statement that helps their team (by weight, POLICY 'fisherman_helpful_weight';
    never naming the Demon). A drunk or poisoned Fisherman may get bad advice (a false statement); under the Vortox,
    only false advice. A judge ranks the same statements, so the advice is always one the code checked."""
    stmts = fisherman_statements(g, p)
    true = {s['text']: s['true'] for s in stmts}
    impaired = g.unreliable(p, 'Fisherman')
    pool = stmts if impaired else [s for s in stmts if s['true']]
    if not pool:
        return None

    def reveals(s):
        return s['form'] in ('evil', 'character') and g[s['about'][0]].is_demon

    def pick(r, within):
        within = [s for s in within if not reveals(s)] or within
        return r.choices(within, [POLICY['fisherman_helpful_weight'] if s['helps'] else 1 for s in within])[0]

    def style(r):
        if impaired and g.misinformed(p, r):
            false = [s for s in stmts if not s['true']]
            if false:
                return {'statements': [pick(r, false)['text']]}
        return {'statements': [pick(r, [s for s in stmts if s['true']] or stmts)['text']]}
    values = list(dict.fromkeys(s['text'] for s in pool))
    return snv.info(Choice(f'Fisherman:{p.name}', [{'statements': [x]} for x in values], style), g, p, 'Fisherman',
                    f'{p.name} (Fisherman) visits you for advice to help their team ({p.alignment}) win: which true '
                    'statement do you give? Make it useful to their team, without naming the Demon outright.',
                    lambda v: true[v['statements'][0]], impaired)


class Fisherman(Townsfolk):
    name = 'Fisherman'
    ability = ability(name)
    info = True
    visit = True

    async def visited(self, game, me, text):
        g = game.g
        if not (me.alive and snv.has(g, me, self.name)):
            return False
        if snv.used(g, me, self.name):
            game.inform(me, f'Day {game.day} — Fisherman: you have already had your advice.')
            return True
        snv.use(g, me, self.name)  # once per game, drunk or not
        choice = fisherman_choice(g, me)
        if choice is None:
            game.inform(me, f'Day {game.day} — Fisherman: the Storyteller has no advice for you.')
            return True
        advice = (await game.decide_judged(choice))['statements'][0]
        game.inform(me, f'Day {game.day} — Fisherman: the Storyteller\'s advice to help your team win: "{advice}"')
        return True

    def becomes(self, game, me):
        snv.fresh(game.g, me, self.name)


# ---- Outsiders ---------------------------------------------------------------------------------------------------

def damsel_choice(g, ph, target):
    """The Pit-Hag/Damsel jinx: which player becomes the Damsel the Pit-Hag made. Any player not of an evil type,
    usually not the one the Pit-Hag chose (POLICY 'damsel_pithag_target'), so the Pit-Hag doesn't know her."""
    pool = [q.name for q in g.players if kind(q.character) in ('Townsfolk', 'Outsider')] or [target.name]
    if target.name not in pool:
        pool.append(target.name)

    def style(r):
        others = [x for x in pool if x != target.name and g[x].alive]
        return {'players': [target.name if not others or r.random() < POLICY['damsel_pithag_target']
                            else r.choice(others)]}
    return judged(Choice(f'Damsel:{ph.name}', [{'players': [x]} for x in pool], style), 'damsel_player',
                  f'The Pit-Hag ({ph.name}) made {target.name} the Damsel, but you choose which player becomes the '
                  'Damsel (the jinx), so the Pit-Hag does not know: usually another good player.', about=target.name,
                  recipient=ph.name)


class Damsel(Outsider):
    name = 'Damsel'
    ability = ability(name)
    public_action = 'ability'  # a Minion's public guess, through the shared `ability` field (`target`)
    derives = True  # the Spy jinx: poisoned while a Spy is or has been in play
    setup_order = 7

    def setup(self, game):
        self.spy_seen(game.g)
        self.spy_seen(game.g, 'Widow')

    @staticmethod
    def spy_seen(g, c='Spy'):
        """Whether a player is or has been the Spy (or, the Widow jinx, the Widow)."""
        if any(q.character == c for q in g.players):
            g.notes[f'{c} in play'] = True
        return g.notes.get(f'{c} in play', False)

    def told_evil(self, game, me, viewer):
        return ['A Damsel is in play (you do not know who).'] if kind(viewer.character) == 'Minion' else []

    def becomes(self, game, me):
        # a new Damsel (the Pit-Hag's, the Plague Doctor's Baron): the Minions learn it at once
        for q in game.g.players:
            if q.alive and kind(q.character) == 'Minion' and rules(q.shown).evil:  # (not a Marionette)
                game.inform(q, f'{snv.when(game)}: a Damsel is now in play (you do not know who).')

    def changed(self, game, me, other):
        if other.character in ('Spy', 'Widow'):
            game.g.notes[f'{other.character} in play'] = True

    def ongoing(self, g, me):
        # the Spy and Widow jinxes: "If the Spy (the Widow) is (or has been) in play, the Damsel is poisoned", for the
        # rest of the game
        if holds(me, self.name) and any(g.script.jinxed(self.name, c) and self.spy_seen(g, c)
                                             for c in ('Spy', 'Widow')):
            return [State('poisoned', me.name, until=None)]
        return []

    def act_publicly(self, game, actor, target, text=None):
        # each Minion guesses once (a living one, or one keeping their ability), drunk or not; a guess with no player
        # named is not a guess. Right, while both work and the Damsel lives: the Damsel's team loses (an evil
        # Damsel's too)
        g = game.g
        m = g[actor]
        if not target or kind(m.character) != 'Minion' or not (m.alive or g.keeps_ability(m)):
            return False
        guessed = g.notes.setdefault('Damsel guesses', [])
        if m.name in guessed:
            return False
        guessed.append(m.name)
        t = g[target]
        if self.name not in g.abilities(t) or not (t.alive or g.keeps_ability(t)):
            return False  # (a dead Damsel has no ability: guessing her does nothing)
        if g.impaired(m) or g.impaired(t):
            snv.failed(game, m if g.impaired(m) else t, self.name, 'a Minion guessed the Damsel')
            return False
        loser = 'evil' if t.evil else 'good'
        g.winner = 'good' if t.evil else 'evil'
        g.reason = f'{m.name}, a Minion, publicly guessed that {t.name} is the Damsel: the {loser} team loses.'
        return False


def golem_choice(g, golem, t):
    """Whether a nominee who may or may not register as the Demon (the Recluse) does so to the Golem (and lives)."""
    return judged(yes_choice(f'Golem:{t.name}', POLICY['golem_recluse_demon']), 'golem_demon',
                  f'{golem.name}, the Golem, nominated {t.name} (the {t.character}). Does {t.name} register as the '
                  'Demon (yes: true), and so live?', about=t.name, recipient=golem.name, helps='evil')


class Golem(Outsider):
    name = 'Golem'
    ability = ability(name)

    def nomination_limit(self, g, me):
        # one nomination per game, drunk or not (the MAY NOT NOMINATE reminder goes on as they nominate)
        return 0 if me.name in g.notes.get('Golem nominated', ()) else None

    async def nomination(self, game, me, nominator, nominee):
        g = game.g
        if nominator != me.name or me.name in g.notes.get('Golem nominated', ()):
            return
        g.notes.setdefault('Golem nominated', []).append(me.name)
        if not g.works(me, self.name):
            snv.failed(game, me, self.name, 'the nominee lived')
            return
        t = g[nominee]
        demon = {kind(c) == 'Demon' for c in g.registers_as(t, me)}
        if len(demon) > 1:
            demon = {(await game.decide_judged(golem_choice(g, me, t)))['yes']}
        if True not in demon:  # at once, and the nomination still stands (as the Witch's)
            game.ability_kill(t, 'golem', me)


class Politician(Outsider):
    name = 'Politician'
    ability = ability(name)

    @staticmethod
    def most_responsible(g, me):
        """The scripted floor for "the player most responsible for your team losing": the game ended on today's
        execution, and the Politician was the player executed or the one who nominated them. Anything subtler (a
        vote, a claim, a bad shot) is not counted (a reading: the plainest case)."""
        ex = g.executions[-1] if g.executions else None
        if not ex or ex['day'] != g.day:
            return False
        if ex['player'] == me.name:
            return True
        noms = [x for x in g.nominations if x['day'] == g.day and x['nominee'] == ex['player']]
        return bool(noms) and noms[-1]['nominator'] == me.name

    def ended(self, g, me, winner, reason):
        # even if dead; while they have their ability (not drunk or poisoned); an evil player the Pit-Hag made the
        # Politician can't turn good this way (the jinx)
        if not holds(me, self.name) or me.alignment == winner or g.impaired(me):  # (the Hermit's too: batch 4)
            return None
        if winner == 'good' and me.name in g.notes.get('Evil Politicians', ()):
            return None
        if not self.most_responsible(g, me):
            return None
        me.alignment = winner
        return (f'{reason} {me.name}, the Politician, was the player most responsible for their team losing: they '
                f'change alignment ({winner}) and win.')


def tea_party_options(g, p):
    """The characters `p` may become at the Hatter's tea party: another character of their type on the script that
    no other player has now (alive or dead; one another player left earlier tonight is free)."""
    taken = {q.character for q in g.players if q is not p}
    # not the Marionette (it starts beside the Demon, believing it is good: batch 2), nor a character only one of whose
    # jinxed pair can be in play (the Heretic's), nor the Leviathan after day 5 (its jinx)
    late = g.script.jinxed('Leviathan', 'Hatter') and g.day > 5
    return [c for c in g.script.all if kind(c) == kind(p.character) and c not in taken and c != p.character
            and c != 'Marionette' and not g.script.clash(taken | {c}) and not (late and c == 'Leviathan')]


class Hatter(Outsider):
    name = 'Hatter'
    ability = ability(name)

    def on_death(self, game, me, dead, cause, alive_before):
        # the tea party is tonight, at the Hatter's step: the night of a death by day is the coming one. A drunk or
        # poisoned Hatter's death is wasted (their sobriety as they die decides); one who dies tonight after the
        # step gives none (a reading: "today or tonight" is checked at the step)
        g = game.g
        if dead is me and not me.alive and self.name in g.abilities(me) and not g.impaired(me):
            g.notes['Tea party'] = game.day if game.tonight is not None else game.day + 1

    async def resolve_night(self, game, night):
        g = game.g
        if g.notes.get('Tea party') != night.n:
            return
        g.notes['Tea party'] = None
        # each living Minion and Demon, in seat order, may choose (a reading: the dead don't wake), and is told; a
        # choice is made knowing the earlier ones' (a character just left is free)
        for p in [q for q in g.players if q.alive and kind(q.character) in ('Minion', 'Demon')
                  and rules(q.shown).evil]:  # (a Marionette believes they are good: not woken)
            options = tea_party_options(g, p)
            if not options or kind(p.character) not in ('Minion', 'Demon'):
                continue
            k = kind(p.character)
            req = game.request('night', f'Night {night.n} — the Hatter has died: a tea party. You may become another '
                                        f'{k} character on the script (`character`: one of {", ".join(options)}), '
                                        f'or null to stay the {p.character}.', night.n, n_targets=0, options=[],
                               min_targets=0, characters=options)
            c = (await game.ask(p.name, req)).get('character')
            game.woken(p)
            game.emit('night_choice', {'player': p.name, 'role': self.name, 'targets': [],
                                       'character': c if c in options else None}, 'audit')
            if c in options:
                await game.change(p, character=c)


# The Storyteller's use of a Minion ability gained through the Plague Doctor. Abilities the Storyteller can use
# sensibly, by how: at that Minion's own step each night (STEPS, through Game.night and Character.storyteller_step);
# at once, as their jinxes with the Plague Doctor say (a Minion gains the Spy's or Scarlet Woman's, players become
# Outsiders or the Evil Twin); or passively (the Mastermind's extra day). Not the Pit-Hag's (a nightly change of any
# character, with nothing for a scripted style to aim at) nor the Summoner's (a second Demon summoned on the third
# night, which has passed or would end the Demon's game): the Storyteller picks among the others.
PLAGUE_STEPS = ('Poisoner', 'Godfather', "Devil's Advocate", 'Assassin', 'Witch', 'Cerenovus')
PLAGUE_JINXED = ('Spy', 'Scarlet Woman', 'Baron', 'Evil Twin', 'Goblin', 'Marionette',  # (the last two: batch 2)
                 'Boomdandy', 'Fearmonger', 'Wraith')  # (batch 3; the Wraith: batch 4)
PLAGUE_USABLE = PLAGUE_STEPS + PLAGUE_JINXED + ('Mastermind',)


def player_choice(cid, call, question, names, style, **ctx):
    return judged(Choice(cid, [{'players': [x]} for x in names], style), call, question, **ctx)


def good_target(g, r, pool, prefer=None):
    """A player from `pool` for the Storyteller's Minion ability: one passing `prefer` (by default a good player)."""
    prefer = prefer or (lambda x: not g[x].evil)
    best = [x for x in pool if prefer(x)]
    return r.choice(best or pool)


class PlagueDoctor(Outsider):
    name = 'Plague Doctor'
    ability = ability(name)

    @staticmethod
    def gained(g):
        return g.notes.get('Storyteller ability')

    def on_death(self, game, me, dead, cause, alive_before):
        # once a game, on any death of a sober and healthy Plague Doctor (a Philosopher with the ability too)
        g = game.g
        if dead is me and not me.alive and self.name in g.abilities(me) and not g.impaired(me) \
                and 'Storyteller ability' not in g.notes:
            g.notes['Storyteller ability'] = None
            game.later(lambda game: self.gain(game, me))

    async def gain(self, game, me):
        g = game.g
        in_play = {q.character for q in g.players}
        options = [m for m in g.script.minions if m in PLAGUE_USABLE and m not in in_play
                   and (m not in PLAGUE_JINXED or g.script.jinxed(self.name, m))]
        if not options:
            return  # (no Minion ability the Storyteller can use, off the script's characters not in play)
        choice = judged(Choice('Plague Doctor', [{'character': m} for m in options],
                               lambda r: {'character': r.choice(options)}), 'plague_doctor',
                        f'The Plague Doctor ({me.name}) has died: which Minion ability (not in play) do you gain?',
                        about=me.name)
        m = (await game.decide_judged(choice))['character']
        g.notes['Storyteller ability'] = m
        game.emit('text', {'text': f'[the Storyteller gains the {m} ability]'}, 'audit')
        if m in PLAGUE_STEPS:
            g.notes.setdefault('Storyteller abilities', {})[m] = self.name
        elif m in ('Spy', 'Scarlet Woman', 'Goblin', 'Fearmonger', 'Wraith'):
            await self.minion_gains(game, m)
        elif m == 'Boomdandy':
            from .carousel3 import boomdandy_made
            await boomdandy_made(game)
        elif m == 'Marionette':
            await self.marionette(game)
        elif m == 'Baron':
            await self.baron(game)
        elif m == 'Evil Twin':
            await self.evil_twin(game)

    async def minion_gains(self, game, m):
        """The Spy and Scarlet Woman jinxes: a living Minion gains the ability, and learns this."""
        g = game.g
        minions = [q.name for q in g.players if q.alive and kind(q.character) == 'Minion']
        if not minions:
            return
        p = g[(await game.decide_judged(player_choice(
            f'Plague Doctor:{m}', 'plague_minion', f'Which living Minion gains the {m} ability (and learns it)?',
            minions, lambda r: {'players': [r.choice(minions)]})))['players'][0]]
        p.extra.append(m)
        game.emit('gains', {'player': p.name, 'character': m}, 'audit')
        game.inform(p, f'{snv.when(game)}: the Plague Doctor has died, and you gain the {m}\'s ability: '
                       f'{rules(m).ability} (You are still the {p.character}.)')

    async def marionette(self, game):
        """The Marionette jinx: one of the Demon's good neighbours becomes the Marionette (not knowing it)."""
        from . import carousel2
        g = game.g
        demon = g.demon()
        pool = [q.name for q in carousel2.seat_neighbours(g, demon) if not q.evil] if demon else []
        if pool:
            x = (await game.decide_judged(player_choice('Plague Doctor:Marionette', 'plague_marionette',
                                                        'Which of the Demon\'s good neighbours becomes the Marionette?',
                                                        pool, lambda r: {'players': [r.choice(pool)]})))['players'][0]
            await carousel2.make_marionette(game, g[x], demon)

    async def baron(self, game):
        """The Baron jinx: up to two players become Outsiders: living good Townsfolk (the Storyteller's choice, two
        usually), each a different Outsider not in play (not the Drunk or the Lunatic, whose illusions can't start
        mid-game), keeping their alignment."""
        g = game.g
        towns = [q.name for q in g.players if q.alive and not q.evil and kind(q.character) == 'Townsfolk']
        in_play = {q.character for q in g.players}
        pool = [c for c in g.script.outsiders if c not in in_play and not rules(c).always_drunk
                and not rules(c).wakes_at_own_step]
        k = min(2, len(towns), len(pool))
        if not k:
            return
        values = [{'players': list(c)} for n in range(k + 1) for c in combinations(towns, n)]

        def style(r):
            n = k if k < 2 or r.random() < POLICY['plague_baron_two'] else 1
            return {'players': r.sample(towns, n)}
        picks = (await game.decide_judged(judged(Choice('Plague Doctor:Baron', values, style), 'plague_baron',
                                                 'Which Townsfolk (up to two) become Outsiders?')))['players']
        for x in picks:
            pool = [c for c in pool if c not in {q.character for q in g.players}]
            c = (await game.decide_judged(judged(
                Choice(f'Plague Doctor:Baron:{x}', [{'character': c} for c in pool],
                       lambda r, pool=pool: {'character': r.choice(pool)}), 'plague_outsider',
                f'Which Outsider does {x} become?', about=x)))['character']
            await game.change(g[x], character=c)

    async def evil_twin(self, game):
        """The Evil Twin jinx: a player becomes the Evil Twin (a living good player, usually a Townsfolk, keeping
        their alignment: a good Evil Twin, twinned with an evil player)."""
        g = game.g
        good = living_good(g)
        if not good:
            return
        p = g[(await game.decide_judged(player_choice(
            'Plague Doctor:Evil Twin', 'plague_evil_twin', 'Which player becomes the Evil Twin?', good,
            lambda r: {'players': [good_target(g, r, good, lambda x: kind(g[x].character) == 'Townsfolk')]})))[
            'players'][0]]
        await game.change(p, character='Evil Twin')

    async def storyteller_step(self, game, night, m):
        g = game.g
        alive = [q.name for q in g.living()]
        if not alive:
            return
        if m == 'Poisoner':
            t = (await game.decide_judged(player_choice(
                'Storyteller:Poisoner', 'plague_poison', 'You have the Poisoner\'s ability: whom do you poison tonight '
                'and tomorrow?', alive, lambda r: {'players': [good_target(
                    g, r, alive, lambda x: not g[x].evil and rules(g[x].shown).info
                    and r.random() < POLICY['plague_poison_info'])]})))['players'][0]
            g.add(State('poisoned', t, until='night'))
        elif m == 'Godfather':
            if night.first or not bmr.Godfather.outsider_died(g, night.n - 1):
                return
            t = (await game.decide_judged(player_choice(
                'Storyteller:Godfather', 'plague_kill', 'You have the Godfather\'s ability, and an Outsider died '
                'today: whom do you kill tonight?', alive, lambda r: {'players': [good_target(g, r, alive)]})))[
                'players'][0]
            game.attempt_kill(g[t], 'godfather', None, night)
        elif m == "Devil's Advocate":
            last = g.notes.get('Storyteller protected')
            pool = [x for x in alive if x != last] or alive
            t = (await game.decide_judged(player_choice(
                "Storyteller:Devil's Advocate", 'plague_protect', 'You have the Devil\'s Advocate\'s ability: who '
                'does not die if executed tomorrow?', pool, lambda r: {'players': [good_target(
                    g, r, pool, lambda x: g[x].evil == (r.random() < POLICY['plague_protect_evil']))]})))[
                'players'][0]
            g.notes['Storyteller protected'] = t
            g.add(State('safe', t, until='night', against='execution'))
        elif m == 'Assassin':
            if night.first or g.notes.get('Storyteller assassinated'):
                return
            go = (await game.decide_judged(judged(yes_choice('Storyteller:Assassin', POLICY['plague_assassin_night']),
                                                  'plague_assassin', 'You have the Assassin\'s ability: do you use it '
                                                  'tonight?', helps='evil')))['yes']
            if not go:
                return
            g.notes['Storyteller assassinated'] = night.n
            t = (await game.decide_judged(player_choice(
                'Storyteller:Assassin target', 'plague_kill', 'Whom does your Assassin\'s ability kill?', alive,
                lambda r: {'players': [good_target(g, r, alive)]})))['players'][0]
            game.attempt_kill(g[t], 'assassin', None, night, unstoppable=True)
        elif m == 'Witch':
            if snv.Witch.lost(g):
                return
            t = (await game.decide_judged(player_choice(
                'Storyteller:Witch', 'plague_curse', 'You have the Witch\'s ability: whom do you curse (if they '
                'nominate tomorrow, they die)?', alive, lambda r: {'players': [good_target(g, r, alive)]})))[
                'players'][0]
            g.add(State('cursed', t, until='night', about='Storyteller'))
        elif m == 'Cerenovus':
            goods = g.script.good
            values = [{'players': [x], 'character': c} for x in alive for c in goods]

            def style(r):
                x = good_target(g, r, alive)
                return {'players': [x], 'character': r.choice([c for c in goods if c != g[x].shown] or goods)}
            v = await game.decide_judged(judged(Choice('Storyteller:Cerenovus', values, style), 'plague_madness',
                                                'You have the Cerenovus\'s ability: whom do you make mad, and about '
                                                'which good character?'))
            t, c = v['players'][0], v['character']
            g.add(State('mad', t, until='night', about=c))
            game.inform(g[t], f'Night {night.n}: the Cerenovus selected you. Tomorrow you must be "mad" that you are '
                              f'the {c}: do your best to convince the group that you are the {c}, or the Storyteller '
                              'might execute you. (Hinting, or saying you are mad, is not enough.)')

    async def nomination(self, game, me, nominator, nominee):
        g = game.g
        if self.gained(g) == 'Witch' and not snv.Witch.lost(g) and any(
                s.kind == 'cursed' and s.about == 'Storyteller' and s.target == nominator for s in g.states):
            game.ability_kill(g[nominator], 'witch')

    async def moment(self, game, me, when):
        g = game.g
        if self.gained(g) == 'Mastermind':
            rules('Mastermind').moment(game, me, when)
        if self.gained(g) == 'Cerenovus' and when == 'nominations':
            for s in [s for s in g.states if s.kind == 'mad' and s.source is None]:
                if await game.judge_madness(g[s.target], s.about, since=game.day):
                    return

    def overrides_end(self, g, me, winner, reason):
        if self.gained(g) == 'Mastermind':
            return rules('Mastermind').overrides_end(g, me, winner, reason, works=True)
        return None


# ---- Minions -----------------------------------------------------------------------------------------------------

def summon_choice(g, s, target, character, demons):
    """The Courtier/Summoner jinx: the Storyteller has the Summoner's ability (the living Summoner has none): whom it
    makes which evil Demon. Usually what the Summoner chose (POLICY 'summoner_st_honours'), else a living good player
    and any Demon."""
    names = [q.name for q in g.players]
    values = [{'players': [x], 'character': c} for x in names for c in demons]

    def style(r):
        if target and character in demons and r.random() < POLICY['summoner_st_honours']:
            return {'players': [target], 'character': character}
        return {'players': [r.choice(living_good(g) or names)], 'character': r.choice(demons)}
    return judged(Choice(f'Summoner:{s.name}', values, style), 'summon',
                  f'The Summoner ({s.name}) has no ability tonight, so you have it: which player becomes which evil '
                  f'Demon? They chose {target or "no one"} and {character or "no Demon"}.', about=s.name,
                  recipient=s.name)


class Summoner(Minion):
    name = 'Summoner'
    ability = ability(name)
    no_demon = True  # [No Demon]: a Townsfolk is dealt in its place (state.random_setup, setup_error)
    night_choice = Choose(players=1, character=True, kinds=('Demon',),
                          prompt='The 3rd night: choose a player (alive or dead, even yourself) and a Demon '
                                 '(`character`): they become an evil Demon of that kind.')
    pukka_choice = Choose(players=1, character=True, kinds=('Demon',), optional=True,
                          prompt='The 2nd night: you may summon a Pukka now instead of on the 3rd night: choose a '
                                 'player and the Pukka (`character`). Or choose no one, and summon on the 3rd night.')

    def intro(self, game, me):
        return [f'There is no Demon in play. On the 3rd night you choose a player to become an evil Demon of your '
                f'choice. Three good characters not in play, for evil to bluff: {", ".join(game.g.bluffs)}.']

    @staticmethod
    def pending(g, me):
        """Whether `me` may yet summon: they have the Summoner's ability, alive, and the 3rd night has not passed."""
        return (me.alive and 'Summoner' in g.abilities(me) and not g.notes.get('Summoned') and g.day <= 3
                and 'Summoner' in g.script.minions)

    def night_spec(self, game, me, night):
        g = game.g
        if g.notes.get('Summoned'):
            return None
        if night.n == 3 and me.character == 'Alchemist' and g.script.jinxed('Alchemist', self.name):
            # the jinx (batch 3): the Alchemist-Summoner chooses which Demon, not which player
            return Choose(players=0, character=True, kinds=('Demon',),
                          prompt='The 3rd night: choose a Demon (`character`): a player of the Storyteller\'s choice '
                                 'becomes an evil Demon of that kind.')
        if night.n == 3:
            return self.night_choice
        if night.n == 2 and g.script.jinxed(self.name, 'Pukka') and 'Pukka' in g.script.demons:
            return self.pukka_choice  # the jinx: a Pukka may be summoned on the 2nd night instead
        return None

    def overrides_end(self, g, me, winner, reason):
        # no Demon is no win for good while a Summoner may yet summon one
        if winner == 'good' and not g.demon() and self.pending(g, me):
            return False
        return None

    async def resolve_night(self, game, night):
        g = game.g
        if night.first:
            for s in [q for q in g.players if q.alive and q.character == self.name]:
                game.woken(s)  # (woken for their bluffs, already in their introduction)
            return
        if g.notes.get('Summoned') or night.n not in (2, 3):
            return
        for s in [q for q in g.players if q.alive and self.name in g.abilities(q) and q.name in night.chosen]:
            target = (night.chosen[s.name] or [None])[0]
            c = night.characters.get(s.name)
            if night.n == 2 and not (target and c == 'Pukka'):
                continue  # waiting for the 3rd night
            demons = ['Pukka'] if night.n == 2 else list(g.script.demons)
            if s.character == 'Alchemist' and g.script.jinxed('Alchemist', self.name):
                if night.n != 3 or c not in demons:
                    continue
                from .carousel3 import summoned_by_alchemist_choice  # the jinx (batch 3): the Storyteller's player
                target = (await game.decide_judged(summoned_by_alchemist_choice(g, s, c)))['players'][0]
            if g.script.jinxed(self.name, 'Poppy Grower') and any(q.alive and q.character == 'Poppy Grower'
                                                                   for q in g.players) and c in demons:
                # the jinx (batch 2): with the Poppy Grower alive, the Summoner chooses the Demon, not the player
                from .carousel2 import summoned_player_choice
                target = (await game.decide_judged(summoned_player_choice(g, s, c)))['players'][0]
            if not g.works(s, self.name):
                from .carousel2 import preached
                if not (g.script.jinxed(self.name, 'Courtier')
                        or (g.script.jinxed(self.name, 'Preacher') and preached(g, s))):
                    snv.failed(game, s, self.name, 'no Demon summoned')
                    g.notes['Summoned'] = 'failed'  # (no Demon will come: good wins, unless one is in play)
                    return
                v = await game.decide_judged(summon_choice(g, s, target, c, demons))
                target, c = v['players'][0], v['character']
            if c and g.script.clash({q.character for q in g.players if q.name != target} | {c}):
                # (batch 3b) a Demon whose jinx with a character in play lets only one be in play (the Heretic's with
                # the Lleech): the Storyteller summons another Demon on the script instead (a reading)
                others = [d for d in demons if not g.script.clash({q.character for q in g.players
                                                                    if q.name != target} | {d})]
                if not others:
                    g.notes['Summoned'] = 'failed'
                    return
                c = (await game.decide_judged(judged(Choice(f'Summoner clash:{s.name}',
                                                            [{'character': d} for d in others],
                                                            lambda r: {'character': r.choice(others)}),
                                                     'summon_demon', f'The Summoner ({s.name}) chose the {c}, which '
                                                     'cannot be in play with a character in play: which Demon comes '
                                                     'instead?', recipient=s.name)))['character']
            typhon = c == 'Lord of Typhon' and g.script.jinxed(self.name, c)
            if typhon:  # the jinx (batch 3b): the Lord of Typhon must neighbour a Minion
                from .carousel4 import typhon_summoned
                target = await typhon_summoned(game, s, target)
            await self.summon(game, s, g[target], c, night)
            if typhon:  # and its other neighbour becomes an evil Minion
                from .carousel4 import typhon_neighbour
                await typhon_neighbour(game, g[target])
            return
        if night.n == 3 and not g.notes.get('Summoned'):
            g.notes['Summoned'] = 'failed'

    async def summon(self, game, s, t, c, night):
        g = game.g
        g.notes['Summoned'] = night.n
        others = [q for q in g.living() if q.is_demon and q is not t]
        await game.change(t, character=c, alignment='evil')
        if not t.alive and c == 'Zombuul' and g.script.jinxed(self.name, 'Zombuul'):
            # the jinx: a dead player summoned into the Zombuul has already "died once": alive, registering as dead
            t.alive, t.seems_dead = True, True
            g.spend('Zombuul')
        if g.notes.get('Marionette waiting'):  # the Marionette jinx (batch 2): it enters play beside the new Demon
            from .carousel2 import marionette_enters
            await marionette_enters(game, t)
        if others and t.alive and any(g.script.jinxed(self.name, x) for x in ('Pit-Hag', 'Hatter', 'Kazali')):
            # the Pit-Hag and Hatter jinxes: a second living Demon: deaths tonight are arbitrary (as the Pit-Hag's)
            plan = await game.decide_judged(snv.arbitrary_deaths_choice(g, s, t, False, by='Summoner'))
            if not plan['yes']:
                g.notes['Demon kills stopped'] = night.n
            for x in plan['players']:
                game.attempt_kill(g[x], 'summoner', s, night)


# ---- Demons ------------------------------------------------------------------------------------------------------

def ojo_choice(g, ojo, c):
    """The Ojo named a character not in play: the Storyteller chooses who dies, usually a good player who will die
    (POLICY 'ojo_good_victim'), rarely nobody ('ojo_nobody')."""
    alive = [q.name for q in g.living() if q is not ojo]
    values = [{'players': []}] + [{'players': [x]} for x in alive]

    def style(r):
        if not alive or r.random() < POLICY['ojo_nobody']:
            return {'players': []}
        dying = [x for x in alive if bmr.will_die(g, g[x], 'demon')] or alive
        good = [x for x in dying if not g[x].evil]
        return {'players': [r.choice(good if good and r.random() < POLICY['ojo_good_victim'] else dying)]}
    return judged(Choice(f'Ojo:{ojo.name}', values, style), 'ojo_victim',
                  f'The Ojo ({ojo.name}) chose the {c}, who is not in play: who dies (or nobody)?', about=ojo.name,
                  recipient=ojo.name)


class Ojo(Demon):
    name = 'Ojo'
    ability = ability(name)
    night_choice = Choose(players=0, character=True,
                          prompt='Choose a character (`character`): its player dies. If it is not in play, the '
                                 'Storyteller chooses who dies.')
    kills_at_night = True

    async def resolve_night(self, game, night):
        g = game.g
        for o in [q for q in g.players if q.alive and self.name in g.abilities(q) and q.name in night.chosen]:
            c = night.characters.get(o.name)
            if not c:
                continue
            if not g.works(o, self.name):
                snv.failed(game, o, self.name, 'no attack')
                continue
            # in play: the player who is that character now (a reading: their true character, not how they might
            # register); a dead one can't die again. Not in play (the Drunk's apparent character too): the
            # Storyteller's choice
            holders = [q for q in g.players if q.character == c]
            victims = holders if holders else [g[x] for x in (await game.decide_judged(ojo_choice(g, o, c)))['players']]
            for v in victims:
                await game.demon_attack_judged(v, o, night)


def ask_live(game, p, night, text):
    """`p`'s silent choice to live (True) or die, asked as a yes/no in `vote` (required: asked again, never made for
    them; a seat that never answers stops the game, as a failed seat does)."""
    async def go():
        from .llm import SeatFailed
        req = game.request('decide', text, night.n)
        for _ in range(game.REASKS + 1):
            a = await game.ask(p.name, req)
            if isinstance(a.get('vote'), bool):
                game.emit('text', {'text': f'[{p.name} chooses to {"live" if a["vote"] else "die"}]'}, 'audit')
                return a['vote']
            req = game.request('decide', '(Your choice was missing: set `vote` to true to live or false to die.) '
                                         + text, night.n)
        raise SeatFailed(f'{p.name}: no answer to a required choice after {game.REASKS} reminders')
    return go()


def ordinal(i):
    return ('first', 'second', 'third')[i] if i < 3 else f'{i + 1}th'


def al_hadikhia_last_stand(g, winner, works):
    """The Mastermind/Al-Hadikhia jinx, from Mastermind.overrides_end: the Al-Hadikhia was executed today with the
    Mastermind alive (and working): instead of the Mastermind's extra day, the game goes on to tonight, when the dead
    Al-Hadikhia chooses 3 good players (AlHadikhia.last_stand). None when the jinx has nothing to do."""
    stand = g.notes.get('Al-Hadikhia last stand')
    if stand:
        if g.day <= stand['night']:
            return False
        return 'good', 'The Al-Hadikhia was executed, and its last choice never came.'
    if winner != 'good' or not works or not bmr.Mastermind.demon_executed_today(g):
        return None
    last = next(d for d in reversed(g.death_log) if g[d['player']].is_demon and not d.get('seems'))
    if g[last['player']].character != 'Al-Hadikhia':
        return None
    g.notes['Al-Hadikhia last stand'] = {'night': g.day + 1, 'player': last['player']}
    return False


class AlHadikhia(Demon):
    name = 'Al-Hadikhia'
    ability = ability(name)
    night_choice = Choose(players=3, optional=True,
                          prompt='You may choose 3 players (all players learn who, at dawn): each silently chooses to '
                                 'live or die, but if all 3 choose to live, all 3 die. Choosing fewer than 3 is '
                                 'choosing no one.')
    kills_at_night = True
    moment_unheld = True  # "all players learn who": at dawn, even if the Al-Hadikhia has since become another character

    def night_spec(self, game, me, night):
        return None if night.first else self.night_choice

    async def resolve_night(self, game, night):
        g = game.g
        stand = g.notes.get('Al-Hadikhia last stand')
        if stand and stand['night'] == night.n and not g.winner:
            await self.last_stand(game, night, g[stand['player']])
            return
        for ah in [q for q in g.players if q.alive and self.name in g.abilities(q) and q.name in night.chosen]:
            picks = night.chosen[ah.name]
            if len(picks) < 3:
                continue  # (fewer than three is choosing no one: a reading)
            g.notes.setdefault('Al-Hadikhia chose', []).append(list(picks))
            # each is woken in order and chooses, not knowing the others' choices (told only their place); a drunk
            # or poisoned Al-Hadikhia's targets still choose, to no effect
            answers = []
            for i, x in enumerate(picks):
                answers.append(await ask_live(game, g[x], night, (
                    f'Night {night.n}: the Al-Hadikhia chose you, the {ordinal(i)} of three players. Silently choose '
                    'to live (`vote`: true) or to die (false). But if all three choose to live, all three die.'
                    + ('' if g[x].alive else ' You are dead: choosing to live brings you back to life.'))))
            if not g.works(ah, self.name):
                snv.failed(game, ah, self.name, 'no deaths')
                continue
            await self.resolve(game, ah, [g[x] for x in picks], answers, night)

    async def resolve(self, game, ah, targets, answers, night):
        # the deaths are the Demon's (protections stop them, the Mayor may bounce one); a dead player who chooses to
        # live comes back to life (a reading of "chooses to live", for review), and one who chooses to die stays dead
        g = game.g
        if all(answers):
            for t in targets:
                await game.attempt_kill_judged(t, 'demon', ah, night)
            return
        for t, live in zip(targets, answers):
            if live and not t.alive:
                g.revive(t, self.name)
                night.revived.append(t)
                await rules(t.character).resurrected(game, t, night)
            elif not live:
                await game.attempt_kill_judged(t, 'demon', ah, night)
        await self.two_demons(game)

    @staticmethod
    async def two_demons(game):
        """The Scarlet Woman jinx: a dead Demon came back while a Scarlet Woman had become the Demon: there would be
        two Demons, so she becomes the Scarlet Woman again."""
        g = game.g
        if not g.script.jinxed('Scarlet Woman', 'Al-Hadikhia'):
            return
        demons = [q for q in g.living() if q.is_demon]
        was = [q for q in demons if q.name in g.notes.get('Was Scarlet Woman', ())]
        if len(demons) > 1 and was:
            g.notes['Was Scarlet Woman'].remove(was[0].name)
            await game.change(was[0], character='Scarlet Woman')

    def moment(self, game, me, when):
        g = game.g
        if when == 'dawn' and g.notes.get('Al-Hadikhia chose'):
            for picks in g.notes.pop('Al-Hadikhia chose'):
                game.emit('text', {'text': f'The Storyteller announces: last night the Al-Hadikhia chose '
                                           f'{", ".join(picks[:-1])} and {picks[-1]}.'})

    async def last_stand(self, game, night, ah):
        """The Mastermind jinx: the executed Al-Hadikhia (dead) chooses 3 good players tonight: if all 3 choose to
        live, evil wins; otherwise, good wins. Only living good players can be chosen (a reading)."""
        g = game.g
        good = [q.name for q in g.living() if not q.evil]
        k = min(3, len(good))
        if not k:
            g.winner, g.reason = 'good', 'The Al-Hadikhia was executed, and no good player was left to choose.'
            return
        req = game.request('night', f'Night {night.n} — Al-Hadikhia: you were executed, but the Mastermind lives: '
                                    f'choose {k} good players (`targets`). If all of them choose to live, evil wins; '
                                    'otherwise good wins.', night.n, n_targets=k, options=good, min_targets=k)
        picks = game.targets(ah.name, await game.insist(ah.name, req, await game.ask(ah.name, req)), req)
        game.emit('night_choice', {'player': ah.name, 'role': self.name, 'targets': picks}, 'audit')
        answers = []
        for i, x in enumerate(picks):
            answers.append(await ask_live(game, g[x], night, (
                f'Night {night.n}: the executed Al-Hadikhia chose you, the {ordinal(i)} of {k} good players. Silently '
                'choose to live (`vote`: true) or to die (false). If all of them choose to live, evil wins; otherwise '
                'good wins.')))
        if all(answers):
            g.winner, g.reason = 'evil', (f'The Al-Hadikhia was executed while the Mastermind lived, and all of '
                                          f'{", ".join(picks)} chose to live: evil wins.')
        else:
            g.winner, g.reason = 'good', (f'The Al-Hadikhia was executed while the Mastermind lived, and not all of '
                                          f'{", ".join(picks)} chose to live: good wins.')


CHARACTERS.update({c.name: c() for c in [Banshee, Steward, Nightwatchman, Magician, Fisherman, Damsel, Golem,
                                         Politician, Hatter, PlagueDoctor, Summoner, Ojo, AlHadikhia]})


# ---- Batch 1's jinxes (docs/carousel-rulings.md) -----------------------------------------------------------------

jinx('Al-Hadikhia', 'Mastermind', 'bmr.Mastermind.overrides_end; carousel.al_hadikhia_last_stand, AlHadikhia')
jinx('Magician', 'Spy', 'characters.Spy.resolve_night (Grimoire.grimoire_text hidden)')
jinx('Pit-Hag', 'Damsel', 'snv.PitHag.resolve_night; carousel.damsel_choice')
jinx('Pit-Hag', 'Politician', 'snv.PitHag.resolve_night; carousel.Politician.ended')
jinx('Plague Doctor', 'Baron', 'carousel.PlagueDoctor.baron')
jinx('Plague Doctor', 'Evil Twin', 'carousel.PlagueDoctor.evil_twin')
jinx('Plague Doctor', 'Scarlet Woman', 'carousel.PlagueDoctor.minion_gains')
jinx('Plague Doctor', 'Spy', 'carousel.PlagueDoctor.minion_gains; characters.Spy.resolve_night')
jinx('Scarlet Woman', 'Al-Hadikhia', 'characters.ScarletWoman.on_death; carousel.AlHadikhia.two_demons')
jinx('Spy', 'Damsel', 'carousel.Damsel.ongoing')
jinx('Summoner', 'Clockmaker', 'snv.clockmaker_choice')
jinx('Summoner', 'Courtier', 'carousel.Summoner.resolve_night, summon_choice')
jinx('Summoner', 'Hatter', 'carousel.Summoner.summon')
jinx('Summoner', 'Pit-Hag', 'carousel.Summoner.summon')
jinx('Summoner', 'Pukka', 'carousel.Summoner.night_spec')
jinx('Summoner', 'Zombuul', 'carousel.Summoner.summon')
jinx('Vortox', 'Banshee', 'carousel.Banshee.announced')
