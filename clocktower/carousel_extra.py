"""Batch 6 of the experimental characters, removable by design: Lil' Monsta, the Atheist, the Wizard, Legion and Riot,
the five the brief kept for a design with the owner (its batch 6 update brings them in on one condition: each can
always be taken out again).

So each is a section of its own below, between its markers, holding everything about it: its imports, its class, its
Storyteller's weights (added to state.POLICY here, under the Carousel heading's batch 6 entries, rather than written
into state.py), the jinxes it implements (declared here, and listed in JINXES for tests/test_carousel.py), its
registration in characters.CHARACTERS. Nothing outside this module names them. The core hooks a section uses do
nothing on a script without its character (most are generic: an attribute or a list on the Script that only these
characters set), and the generic ones several of them need were added before any of them (the deal hooks in state.py,
the rule sentences in prompts.py), so each character is one commit, and `git revert` of that commit removes it (its
section, its core hooks, its tests in tests/test_carousel_<id>.py, its rulings, its synthetic script and fingerprints)
without touching the others. Where a section reads another batch 6 character (a jinx between two of them), it asks
whether that character is built, so either can go.

As in carousel.py to carousel6.py (whose helpers and conventions this module shares): each entry follows the wiki's How
to Run, and where the rules leave a question open, a comment says which reading the entry takes, and why
(docs/carousel-rulings.md, batch 6, lists them for review, one subsection per character).
"""
from __future__ import annotations

from .characters import CHARACTERS

JINXES = []  # the official jinxes implemented here, as (a, b) pairs (tests/test_carousel.py checks them all)


def built(name):
    """Whether batch 6's character `name` is built (its section is here): a section that reads another asks this."""
    return name in CHARACTERS


def ability(name):
    """The official ability text."""
    from . import official
    return official.role(name)['ability']


async def ask_yes(game, p, n, text):
    """`p`'s yes or no, asked in `vote` (required: asked again, never made for them; a seat that never answers stops
    the game, as a failed seat does)."""
    from .llm import SeatFailed
    req = game.request('decide', text, n)
    for _ in range(game.REASKS + 1):
        a = await game.ask(p.name, req)
        if isinstance(a.get('vote'), bool):
            return a['vote']
        req = game.request('decide', '(Your answer was missing: set `vote` to true or false.) ' + text, n)
    raise SeatFailed(f'{p.name}: no answer to a required choice after {game.REASKS} reminders')


# ---- Lil' Monsta -------------------------------------------------------------------------------------------------
# "Each night, Minions choose who babysits Lil' Monsta & "is the Demon". Each night*, a player might die. [+1 Minion]"
# Lil' Monsta is never dealt: with it as the Demon in play, a Minion sits in the Demon's seat (Character.deals). Its
# Demon is a token, not a character: the babysitter keeps their own Minion character and ability and carries the token
# beside it (Player.carries, a core field nothing else sets), which makes them the Demon (Player.is_demon), gives them
# its hooks (Grimoire.abilities) and its registration (Grimoire.registers_as: as Lil' Monsta and as themself).
# docs/carousel-rulings.md, batch 6, Lil' Monsta.
from . import carousel as _c1, carousel2 as _c2, snv as _snv  # noqa: E402
from .characters import Demon as _Demon, jinx as _jinx, kind as _kind, rules as _rules  # noqa: E402
from .state import POLICY as _POLICY, SETUPS as _SETUPS, Choice as _Choice, judged as _judged  # noqa: E402
from .state import setup_changes as _setup_changes, team_sizes as _team_sizes  # noqa: E402

LIL_MONSTA = "Lil' Monsta"
_POLICY.update({  # (Carousel, batch 6: Lil' Monsta. Default, for review.)
    'lilmonsta_kill': 0.9,         # each night*, a player dies (else nobody), a living good player
    'lilmonsta_keep_sitter': 0.6,  # the Minions disagree: the Storyteller keeps the babysitter they had, when one of
    #                                them chose them (else one of the chosen at random)
})


def lilmonsta_rec(g):
    """Lil' Monsta's bookkeeping, when it is in play: {'babysitter', 'as' (their character when chosen), 'dead',
    'fixed' (the Scarlet Woman jinx's babysitter for good)}; None when it is not."""
    return g.notes.get(LIL_MONSTA)


def babysitter_choice(g, cid, call, question, pool, prefer=None):
    """Which of `pool` babysits Lil' Monsta tonight, the Storyteller's judged call: the Minions disagreed (the scripted
    style keeps the babysitter they had, when one of them chose them: POLICY 'lilmonsta_keep_sitter'), the Magician
    jinx, or nobody took the token under the Poppy Grower jinx."""
    def style(r):
        if prefer in pool and r.random() < _POLICY['lilmonsta_keep_sitter']:
            return {'players': [prefer]}
        return {'players': [r.choice(pool)]}
    return _c1.player_choice(cid, call, question, pool, style)


def lilmonsta_victim_choice(g, sitter, n):
    """Who dies tonight by Lil' Monsta ("a player might die"), the Storyteller's judged call: any living player but
    the babysitter (no starpass: a reading), or nobody. The scripted style kills on POLICY 'lilmonsta_kill', a living
    good player."""
    alive = [q.name for q in g.players if q.alive and q is not sitter]
    good = [x for x in alive if not g[x].evil]

    def style(r):
        if alive and r.random() < _POLICY['lilmonsta_kill']:
            return {'players': [r.choice(good or alive)]}
        return {'players': []}
    return _judged(_Choice(f'{LIL_MONSTA}:{n}', [{'players': [x]} for x in alive] + [{'players': []}], style),
                   'lilmonsta_victim', f'Night {n}: Lil\' Monsta (babysat by {sitter.name}) might kill a player: who '
                   'dies (none for nobody)?', about=sitter.name)


def lilmonsta_minion_choice(g, p, options):
    """The Minion character a player who became Lil' Monsta becomes too (the Storyteller's, when they give none)."""
    return _judged(_Choice(f'{LIL_MONSTA} Minion:{p.name}', [{'character': c} for c in options],
                           lambda r: {'character': r.choice(options)}), 'lilmonsta_minion',
                   f'{p.name} became Lil\' Monsta: which Minion character do they become, babysitting it?',
                   recipient=p.name)


def carry(g, p):
    """`p` babysits Lil' Monsta now (and nobody else does)."""
    for q in g.players:
        if q.carries == LIL_MONSTA and q is not p:
            q.carries = ''
    p.carries = LIL_MONSTA
    rec = g.notes.setdefault(LIL_MONSTA, {'babysitter': None, 'as': None, 'dead': False, 'fixed': None})
    rec.update(babysitter=p.name, align=p.alignment, **{'as': p.character})


class LilMonsta(_Demon):
    name = LIL_MONSTA
    ability = ability(name)
    kills_at_night = True
    deals = True
    setup_order = 0.6  # after the Marionette's (0.5), before the red herring: whoever is the Demon is settled first
    setup_unheld = True  # its setup step runs with nobody holding it (it is never dealt)

    # ---- the deal: a Minion in the Demon's seat --------------------------------------------------------------------
    def deal_error(self, characters, script):
        if self.name in characters:
            return 'Lil\' Monsta is never dealt: a Minion sits in the Demon\'s seat [+1 Minion]'
        if any(_kind(c) == 'Demon' for c in characters) or any(_rules(c).no_demon for c in characters):
            return None  # another Demon's deal, or the Summoner's [No Demon]
        n = len(characters)
        counts = {k: sum(1 for c in characters if _kind(c) == k) for k in ('Townsfolk', 'Outsider', 'Minion')}
        mn = _SETUPS[n][2] + 1
        if counts['Minion'] != mn:
            return f'need exactly {mn} Minions and no Demon (Lil\' Monsta\'s +1 Minion), or a Demon'
        sizes = {_team_sizes(n, d, floor=True)[:2] for d in _setup_changes(characters)}
        if (counts['Townsfolk'], counts['Outsider']) not in sizes:
            t, o = sorted(sizes)[0]
            return f'need {t} Townsfolk and {o} Outsiders with Lil\' Monsta in play'
        return ''

    def redeal(self, rng, characters, players, script):
        # the extra Minion: one not dealt, with no setup modifier of its own (the Baron's Outsiders were not drawn for
        # it), never the Summoner (no Demon of its own) nor the Kazali's kind; a reading of "[+1 Minion]"
        if self.name not in characters:
            return characters
        spare = [m for m in script.minions if m not in characters and not _rules(m).outsiders
                 and not _rules(m).outsider_choices and not _rules(m).no_demon]
        if not spare:
            return None  # (draw again)
        return [rng.choice(spare) if c == self.name else c for c in characters]

    def rule_text(self, script):
        return ['Lil\' Monsta is never dealt. When it is the Demon in play, a Minion sits in the Demon\'s seat (one '
                'Minion more than usual), the Minions learn the Demon\'s three bluffs on the first night, and each '
                'night they choose one of themselves to babysit it: that player is the Demon (registering as Lil\' '
                'Monsta) and keeps their Minion ability. If the babysitter dies, Lil\' Monsta dies.']

    # ---- setup and the night -----------------------------------------------------------------------------------
    async def setup(self, game):
        g = game.g
        if any(p.is_demon or _rules(p.character).no_demon for p in g.players):
            return  # (another Demon is in play, or the Summoner's game; the deal itself was checked by setup_error)
        g.notes[self.name] = {'babysitter': None, 'as': None, 'dead': False, 'fixed': None}
        m = g.with_character('Marionette')
        if m and g.script.jinxed('Marionette', self.name) and not g.notes.get('Marionette waiting'):
            # the jinx: "they enter play after the Demon & must start as their neighbor": for now the good character
            # they believe they are, made the Marionette beside the first babysitter (carousel2.marionette_enters)
            g.change_character(m, m.shown)
            m.alignment = 'good'
            g.notes['Marionette waiting'] = True

    @staticmethod
    def minions(g):
        """The Minions who choose and may babysit: living players whose character is a Minion and who know it (a
        Marionette believes they are good)."""
        return [q for q in g.players if q.alive and _kind(q.character) == 'Minion' and _rules(q.shown).evil]

    async def choose_sitter(self, game, night, minions, rec):
        """The Minions' choice tonight: each living Minion names one of them; agreed, that one; else the Storyteller
        picks among those named. The Magician and Poppy Grower jinxes change who chooses."""
        g, names = game.g, [q.name for q in minions]
        old = rec['babysitter'] if rec['babysitter'] in names else None
        if g.script.jinxed('Magician', self.name) and any(q.alive and q.character == 'Magician' for q in g.players):
            return (await game.decide_judged(babysitter_choice(  # the jinx: the Storyteller chooses which Minion
                g, f'{self.name} sitter:{night.n}', 'lilmonsta_babysitter', f'Night {night.n}: the Magician is alive, '
                'so the Storyteller chooses which Minion babysits Lil\' Monsta.', names, old)))['players'][0]
        if g.script.jinxed('Poppy Grower', self.name) and any(q.alive and q.character == 'Poppy Grower'
                                                              for q in g.players):
            # the jinx: "Minions wake one by one, until one of them chooses to take the Lil' Monsta token" (in seat
            # order, from the babysitter they had: a reading); nobody takes it, the Storyteller gives it
            for q in sorted(minions, key=lambda q: (q.name != old, q.seat)):
                game.woken(q)
                if await ask_yes(game, q, night.n, f'Night {night.n} — Lil\' Monsta: the Minions wake one by one '
                                      '(the Poppy Grower is alive). Do you take the Lil\' Monsta token, and babysit it '
                                      '(you are the Demon)? Set `vote` to true to take it, false to pass.'):
                    return q.name
            return (await game.decide_judged(babysitter_choice(
                g, f'{self.name} sitter:{night.n}', 'lilmonsta_babysitter', f'Night {night.n}: no Minion took the '
                'Lil\' Monsta token: which of them babysits it?', names, old)))['players'][0]
        prompt = (f'Night {night.n} — Lil\' Monsta: you and the other Minions choose which of you babysits Lil\' '
                  f'Monsta tonight ({", ".join(names)}): that player is the Demon until the next choice. If you '
                  'disagree, the Storyteller chooses among the players you named. Put your choice in `targets`.')
        reqs = {x: game.request('night', prompt, night.n, n_targets=1, options=names, min_targets=1) for x in names}
        acts = await game.ask_many(reqs)
        named = []
        for x in names:
            acts[x] = await game.insist(x, reqs[x], acts[x])
            t = game.targets(x, acts[x], reqs[x])[0]
            named.append(t)
            game.woken(g[x])
            game.emit('night_choice', {'player': x, 'role': self.name, 'targets': [t]}, 'audit')
        named = sorted(set(named), key=names.index)
        if len(named) == 1:
            return named[0]
        return (await game.decide_judged(babysitter_choice(
            g, f'{self.name} sitter:{night.n}', 'lilmonsta_babysitter', f'Night {night.n}: the Minions named '
            f'{", ".join(named)} to babysit Lil\' Monsta: which babysits it?', named, old)))['players'][0]

    async def resolve_night(self, game, night):
        g = game.g
        rec = lilmonsta_rec(g)
        if not rec or rec['dead']:
            return
        minions = self.minions(g)
        sitter = g[rec['babysitter']] if rec['babysitter'] else None
        if rec['fixed'] and sitter and sitter.alive:
            pass  # the Scarlet Woman jinx: she babysits it for the rest of the game
        elif minions:
            chosen = g[await self.choose_sitter(game, night, minions, rec)]
            carry(g, chosen)
            game.emit('text', {'text': f'[{chosen.name} babysits Lil\' Monsta]'}, 'audit')
            sitter = chosen
            for q in minions:  # (the Minions know whom they chose; the babysitter is shown YOU ARE Lil' Monsta)
                game.inform(q, f'Night {night.n} — Lil\' Monsta: ' + (
                    'you babysit Lil\' Monsta: you are the Demon (and still your own character).' if q is chosen else
                    f'{chosen.name} babysits Lil\' Monsta: they are the Demon.'))
            if night.first:
                for q in minions:
                    game.inform(q, f'Night 1 — Lil\' Monsta: three good characters not in play, for evil to bluff: '
                                   f'{", ".join(g.bluffs)}.')
                await _c2.marionette_enters(game, chosen)
        if night.first or not sitter or not sitter.alive:
            return
        if sitter.name in night.asleep:  # (the Exorcist chose the Demon: Lil' Monsta does not act tonight)
            return
        if not g.works(sitter, self.name):
            _snv.failed(game, sitter, self.name, 'nobody died')
            return
        v = await game.decide_judged(lilmonsta_victim_choice(g, sitter, night.n))
        if v['players']:
            await game.attempt_kill_judged(g[v['players'][0]], 'demon', sitter, night)

    def overrides_end(self, g, me, winner, reason):
        # no Demon before the Minions first choose a babysitter is no win for good (asked with `me` None: nobody
        # holds it, Grimoire.check_victory)
        rec = lilmonsta_rec(g)
        if me is None and winner == 'good' and rec and not rec['babysitter'] and not rec['dead']:
            return False
        return None

    # ---- the babysitter's hooks (Grimoire.abilities gives them the token's) ----------------------------------------
    def carried_registers_as(self, g, me, observer=None):
        # "is the Demon": as Lil' Monsta, and as their own character (as they register on their own: a Spy might
        # register as good characters too)
        return {self.name} | _rules(me.character).registers_as(g, me, observer)

    def carried_registers_demon_to_ft(self, g, me, observer=None):
        return {True}

    def dooms(self, game, me, cause):
        # the Psychopath and Vizier jinxes: "If the Psychopath [the Vizier] is babysitting Lil' Monsta, they die when
        # executed" (no roshambo; no surviving the day)
        return cause == 'execution' and me.character in ('Psychopath', 'Vizier') and game.g.script.jinxed(
            me.character, self.name)

    def on_death(self, game, me, dead, cause, alive_before):
        # the babysitter died: Lil' Monsta dies with them, unless the Scarlet Woman jinx: "If Lil' Monsta dies with 5
        # or more players alive, the Scarlet Woman babysits Lil' Monsta for the rest of the game"
        g = game.g
        rec = lilmonsta_rec(g)
        if dead is not me or me.alive or me.carries != self.name or not rec or rec['dead']:
            return
        sw = next((q for q in g.players if q.alive and q.character == 'Scarlet Woman' and q is not me), None)
        if sw and alive_before >= 5 and g.works(sw, 'Scarlet Woman') and g.script.jinxed('Scarlet Woman', self.name):
            carry(g, sw)
            rec['fixed'] = sw.name
            game.emit('text', {'text': f'[{sw.name}, the Scarlet Woman, babysits Lil\' Monsta for good]'}, 'audit')
            game.inform(sw, f'{_snv.when(game)}: Lil\' Monsta\'s babysitter has died, and because you are the Scarlet '
                            'Woman, you babysit Lil\' Monsta for the rest of the game: you are the Demon.')
            return
        rec['dead'] = True

    async def becomes(self, game, me):
        # a player made Lil' Monsta (the Pit-Hag's, the Summoner's, a tea party's choice: the Hatter jinx, "they also
        # choose a Minion to become") becomes a Minion character as well, of their choice, and babysits it (a
        # reading for every way: the token needs a Minion to carry it); from the next night the Minions choose
        g = game.g
        taken = {q.character for q in g.players if q is not me and q.alive}  # (a dead player's Minion is free)
        options = [c for c in g.script.minions if c not in taken and c != 'Marionette'] or list(g.script.minions)
        req = game.request('night', f'{_snv.when(game)} — you became Lil\' Monsta, whose Demon is a token a Minion '
                                    f'babysits: choose the Minion character you become (`character`: one of '
                                    f'{", ".join(options)}). You babysit Lil\' Monsta, and are the Demon.',
                           game.day, n_targets=0, options=[], min_targets=0, characters=options)
        c = (await game.ask(me.name, req)).get('character')
        if c not in options:
            c = (await game.decide_judged(lilmonsta_minion_choice(g, me, options)))['character']
        await game.change(me, character=c)
        carry(g, me)
        lilmonsta_rec(g)['dead'] = False
        game.emit('text', {'text': f'[{me.name} babysits Lil\' Monsta]'}, 'audit')

    def changed(self, game, me, other):
        # the babysitter swapped characters and alignments (the Snake Charmer's choice of the Demon): the token goes
        # with their Minion character to the player who took it (a reading); any other change leaves it with them
        # until the Minions next choose
        g = game.g
        rec = lilmonsta_rec(g)
        if other is not me or me.carries != self.name or not rec or me.character == rec['as']:
            return
        taker = next((q for q in g.players if q is not me and q.alive and q.character == rec['as']
                      and q.alignment == rec.get('align') and me.alignment != rec.get('align')), None)
        if taker:
            carry(g, taker)
            game.emit('text', {'text': f'[{taker.name} babysits Lil\' Monsta]'}, 'audit')
            game.inform(taker, f'{_snv.when(game)}: you babysit Lil\' Monsta: you are the Demon.')


CHARACTERS[LIL_MONSTA] = LilMonsta()
for _other, _where in (('Hatter', 'carousel_extra.LilMonsta.becomes'),
                       ('Magician', 'carousel_extra.LilMonsta.choose_sitter'),
                       ('Poppy Grower', 'carousel_extra.LilMonsta.choose_sitter'),
                       ('Psychopath', 'carousel_extra.LilMonsta.dooms; carousel5.Psychopath.before_execution'),
                       ('Scarlet Woman', 'carousel_extra.LilMonsta.on_death; characters.ScarletWoman.on_death'),
                       ('Vizier', 'carousel_extra.LilMonsta.dooms (game.Game.prevent_death)'),
                       ('Marionette', 'carousel_extra.LilMonsta.setup, resolve_night (carousel2.marionette_enters)')):
    _jinx(LIL_MONSTA, _other, _where)
    JINXES.append((LIL_MONSTA, _other))
# ---- end of Lil' Monsta ------------------------------------------------------------------------------------------


# ---- Atheist -----------------------------------------------------------------------------------------------------
# "The Storyteller can break the game rules, and if executed, good wins, even if you are dead. [No evil characters]"
# The honest version (a Storyteller free to break any rule) cannot be run by an engine, so the Storyteller breaks
# them in a bounded set of ways the engine can execute: a fake evil team it keeps to itself, information that follows
# that fake Grimoire (Grimoire.unreliable and misinformed, while g.notes['Storyteller lies'] is set), and night deaths
# as if a Demon killed. Anyone may nominate the Storyteller on its scripts (Character.extra_nominees, Game.nominations).
# docs/carousel-rulings.md, batch 6, Atheist.
from .characters import Townsfolk as _Townsfolk, kind as _kind_at  # noqa: E402
from .state import POLICY as _POLICY_at, SETUPS as _SETUPS_at, Choice as _Choice_at, judged as _judged_at  # noqa: E402

ATHEIST = 'Atheist'
STORYTELLER = 'Storyteller'
_POLICY_at.update({  # (Carousel, batch 6: the Atheist. Default, for review.)
    'atheist_lie': 0.9,   # with the Atheist in play, a piece of information follows the fake Grimoire (else the truth)
    'atheist_kill': 0.85,  # each night*, the Storyteller kills a player as a Demon would (else nobody)
})


def fake_team_choice(g, n):
    """The fake evil team the Atheist's Storyteller plays to: a Demon of the script and as many Minions as the table
    has, among the players but the Atheist (the Storyteller's call; the scripted style draws them at random)."""
    pool = [q.name for q in g.players if q.character != ATHEIST]
    mn = _SETUPS_at[len(g.players)][2]

    def style(r):
        team = r.sample(pool, min(len(pool), mn + 1))
        return {'players': team, 'character': r.choice(g.script.demons)}
    values = [{'players': team, 'character': d} for team in _combos(pool, min(len(pool), mn + 1)) for d in
              g.script.demons]
    return _judged_at(_Choice_at(f'{ATHEIST} fake team', values, style), 'atheist_fake_team',
                      'The Atheist is in play and there is no evil team: which players does the Storyteller treat as '
                      'the evil team (the first, the Demon of the character named), for the information it gives?')


def _combos(pool, k):
    # ordered pairs would explode; the first player is the fake Demon, the rest in any order: the first of each
    # combination may be any of it (k <= 4 players from at most 15: at most 15 * C(14, 3) = 5,460 values)
    from itertools import combinations
    out = []
    for first in pool:
        for rest in combinations([x for x in pool if x != first], k - 1):
            out.append([first, *rest])
    return out


def atheist_victim_choice(g, n):
    """Who the Atheist's Storyteller kills tonight, as a Demon would: a living player not safe from the Demon, or
    nobody (the scripted style kills on POLICY 'atheist_kill', a player outside the fake evil team)."""
    rec = g.notes.get(ATHEIST) or {}
    fake = set(rec.get('team') or ())
    alive = [q.name for q in g.players if q.alive and not g.safe(q, 'demon')]

    def style(r):
        pool = [x for x in alive if x not in fake] or alive
        if pool and r.random() < _POLICY_at['atheist_kill']:
            return {'players': [r.choice(pool)]}
        return {'players': []}
    return _judged_at(_Choice_at(f'{ATHEIST}:{n}', [{'players': [x]} for x in alive] + [{'players': []}], style),
                      'atheist_victim', f'Night {n}: the Atheist is in play: does the Storyteller kill a player, as a '
                      'Demon would (none for nobody)?')


class Atheist(_Townsfolk):
    name = ATHEIST
    ability = ability(name)
    deals = True
    setup_order = -5  # first of all: before any setup change can turn the Atheist into another character (an
    #                   Alchemist-Baron's extra Outsiders), the game is the Atheist's
    extra_nominees = (STORYTELLER,)

    # ---- the deal: no evil characters ------------------------------------------------------------------------------
    def deal_error(self, characters, script):
        if self.name not in characters:
            return None
        evil = [c for c in characters if _kind_at(c) in ('Minion', 'Demon')]
        return f'no evil characters with the Atheist in play: {", ".join(evil)}' if evil else ''

    def redeal(self, rng, characters, players, script):
        # every Minion's and the Demon's seat goes to a Townsfolk not in play (an Outsider if none is left); the
        # Outsiders are the table's, as without setup modifiers (no Minion is in play to change them): a reading
        if self.name not in characters:
            return characters
        tf, os_, mn = _SETUPS_at[players]
        towns = [c for c in characters if _kind_at(c) == 'Townsfolk']
        outs = [c for c in characters if _kind_at(c) == 'Outsider'][:os_]
        spare_o = [c for c in script.outsiders if c not in outs]
        while len(outs) < os_ and spare_o:
            outs.append(spare_o.pop(rng.randrange(len(spare_o))))
        spare_t = [c for c in script.townsfolk if c not in towns]
        while len(towns) + len(outs) < players and spare_t:
            towns.append(spare_t.pop(rng.randrange(len(spare_t))))
        while len(towns) + len(outs) < players and spare_o:
            outs.append(spare_o.pop(rng.randrange(len(spare_o))))
        if len(towns) + len(outs) < players or ('Drunk' in outs and set(script.townsfolk) <= set(towns)) or len(
                script.good) - players < 3:
            return None  # (draw again: no Drunk without a Townsfolk to believe in, no deal without three bluffs)
        return towns + outs

    def rule_text(self, script):
        return [f'The Atheist is on this script: anyone may nominate the Storyteller (nominate "{STORYTELLER}"), and '
                'everyone votes as on a player. If the Storyteller is executed, good wins if the Atheist is in play '
                '(alive or dead), and evil wins if not. With the Atheist in play there are no evil characters, and '
                'the Storyteller may break the rules: give information as if there were an evil team, and kill '
                'players at night; if nobody executes the Storyteller, evil wins when two players remain.']

    # ---- the game ---------------------------------------------------------------------------------------------
    async def setup(self, game):
        g = game.g
        if not any(q.character == self.name for q in g.players):
            return  # (a Drunk who believes it: the evil team is real)
        v = await game.decide_judged(fake_team_choice(g, 0))
        team = list(v['players'])
        g.notes[self.name] = {'team': team, 'demon': team[0] if team else None, 'as': v['character']}
        g.notes['Storyteller lies'] = True
        g.reminders.append(f'The Atheist is in play: the Storyteller\'s fake evil team is {", ".join(team)} '
                           f'({team[0]} as the {v["character"]}).' if team else 'The Atheist is in play.')
        for q in g.players:  # every player's information comes from the one fake Grimoire (Grimoire.decoy)
            others = [x for x in team if x != q.name]
            if others:
                g.decoys[q.name] = (others[0], set(others))

    @staticmethod
    def game_on(g):
        return bool(g.notes.get(ATHEIST))

    def overrides_end(self, g, me, winner, reason):
        # no Demon is no win: the game goes on until the Storyteller is executed or two players remain (evil's win,
        # though there is no evil team: good never found the Storyteller out). Asked with `me` None (as the deal's
        # character, Grimoire.check_victory), so it holds even if the Atheist's player became another character
        if me is not None or not self.game_on(g):
            return None
        if reason == 'The Demon is dead.' and g.alive_count() > 2:
            return False
        if reason in ('The Demon is dead.', 'Only two players remain alive.'):
            return 'evil', ('Only two players remain alive, and good never executed the Storyteller (the Atheist was '
                            'in play: there was no evil team).')
        return None

    async def end_of_night(self, game, me, night):
        # the night's deaths, as a Demon's would be: once a night (for the first Atheist), not the first night
        g = game.g
        if night.first or not self.game_on(g) or me is not next(q for q in g.players if q.character == self.name):
            return
        v = await game.decide_judged(atheist_victim_choice(g, night.n))
        if v['players']:
            game.attempt_kill(g[v['players'][0]], 'storyteller', None, night)

    async def nominee_executed(self, game, nominee):
        g = game.g
        game.emit('execution', {'player': nominee, 'died': True})
        if any(q.character == self.name for q in g.players):
            g.winner, g.reason = 'good', 'The Storyteller was executed, and the Atheist is in play.'
        else:
            g.winner, g.reason = 'evil', 'The Storyteller was executed, and the Atheist is not in play.'


CHARACTERS[ATHEIST] = Atheist()
# ---- end of Atheist ----------------------------------------------------------------------------------------------


# ---- Wizard ------------------------------------------------------------------------------------------------------
# "Once per game, choose to make a wish. If granted, it might have a price & leave a clue as to its nature."
# The wish is one of a curated list (WISHES) of effects the engine runs, each with the prices it may have; the Wizard
# picks one (by its number, or in words the Storyteller matches to the list), and the Storyteller's judged calls grant
# it or not, choose its price among that wish's and its clue among the list's (CLUES): a judge chooses, never invents.
# The wishing is asked at the Wizard's night step through Request.menu (random bots pick from it). docs/
# carousel-rulings.md, batch 6, Wizard.
import re as _re_wz  # noqa: E402
from dataclasses import dataclass as _dataclass_wz  # noqa: E402

from . import snv as _snv_wz  # noqa: E402
from .characters import Minion as _Minion_wz  # noqa: E402
from .state import POLICY as _POLICY_wz, Choice as _Choice_wz, State as _State_wz, judged as _judged_wz  # noqa: E402

WIZARD = 'Wizard'
_POLICY_wz.update({  # (Carousel, batch 6: the Wizard. Default, for review.)
    'wizard_grant': 0.85,       # a sober, living Wizard's wish is granted
    'wizard_price': 0.8,        # a granted wish has a price (else none)
    'wizard_clue': 0.7,         # it leaves a clue (else none)
})


@_dataclass_wz(frozen=True)
class Wish:
    id: str
    text: str            # what the Wizard is shown, and what a clue says
    target: str          # '' (no player), 'any', 'alive', 'dead'
    prices: tuple        # ids of PRICES this wish may have
    keywords: tuple      # words that match it, for a wish made in words (wish_match_choice)


WISHES = (
    Wish('kill', 'A player of your choice dies tonight.', 'alive', ('poisoned', 'exposed', 'dies'),
         ('die', 'dies', 'kill', 'death', 'dead')),
    Wish('protect', 'The Demon cannot die until your next night.', '', ('poisoned', 'exposed', 'demon pair'),
         ('protect', 'safe', 'demon', 'survive')),
    Wish('corrupt', 'A player of your choice turns evil (and is told).', 'alive', ('dies', 'demon poisoned', 'exposed'),
         ('evil', 'turn', 'convert', 'corrupt', 'side')),
    Wish('learn', 'You learn the character of a player of your choice.', 'any', ('told', 'exposed'),
         ('learn', 'know', 'character', 'role', 'who')),
    Wish('grimoire', 'You see the Grimoire tonight.', '', ('exposed', 'poisoned'),
         ('grimoire', 'see', 'everything', 'all')),
    Wish('drunk', 'A player of your choice is drunk for the next three days and nights.', 'alive',
         ('poisoned', 'exposed'), ('drunk', 'poison', 'silence', 'ability')),
    Wish('revive', 'A dead evil player of your choice comes back to life.', 'dead', ('dies', 'demon pair'),
         ('alive', 'revive', 'resurrect', 'back', 'life')),
    Wish('bluffs', 'You learn the three good characters the Demon was shown as not in play.', '', ('exposed', 'told'),
         ('bluff', 'bluffs', 'not in play')),
)
WISH = {w.id: w for w in WISHES}
PRICES = {
    'poisoned': 'you are poisoned for the next two days and nights',
    'exposed': 'a good player learns that you are a Minion',
    'dies': 'you die tonight',
    'demon pair': 'a good player learns that the Demon is one of two players',
    'demon poisoned': 'the Demon is poisoned tonight and tomorrow',
    'told': 'the player your wish named (or a good player) learns that you are the Wizard',
}
CLUES = ('announced', 'whispered')  # the town is told a wish was granted; a good player learns what was wished


def wish_menu():
    return [f'{i}. {w.text}' for i, w in enumerate(WISHES, start=1)]


def wish_match_choice(g, p, text):
    """The wish a Wizard made in words (no number): the Storyteller matches it to one of the list, or to none (no wish
    made tonight). The scripted style: the wish whose keywords the words hold most, else none."""
    words = set(_re_wz.findall(r"[a-z']+", (text or '').lower()))
    scores = [(sum(1 for k in w.keywords if k in words or k in (text or '').lower()), w.id) for w in WISHES]
    best = max(scores)

    def style(r):
        return {'statements': [best[1]]} if best[0] else {'statements': ['none']}
    return _judged_wz(_Choice_wz(f'{WIZARD} wish:{p.name}', [{'statements': [w.id]} for w in WISHES]
                                 + [{'statements': ['none']}], style), 'wizard_wish',
                      f'{p.name} (Wizard) wished, in words: "{text}". Which wish of the list is it (none: not a wish '
                      f'the list holds)? The list: ' + ' '.join(wish_menu()), recipient=p.name)


def grant_choice(g, p, wish):
    from .state import yes_choice
    return _judged_wz(yes_choice(f'{WIZARD} grant:{p.name}', _POLICY_wz['wizard_grant']), 'wizard_grant',
                      f'{p.name} (Wizard) wishes: "{wish.text}". Is it granted (yes)?', recipient=p.name)


def price_choice(g, p, wish):
    def style(r):
        if r.random() < _POLICY_wz['wizard_price']:
            return {'statements': [r.choice(wish.prices)]}
        return {'statements': ['none']}
    return _judged_wz(_Choice_wz(f'{WIZARD} price:{p.name}', [{'statements': [x]} for x in (*wish.prices, 'none')],
                                 style), 'wizard_price',
                      f'{p.name} (Wizard) is granted "{wish.text}". Its price, of these (none for no price): '
                      + '; '.join(f'{x}: {PRICES[x]}' for x in wish.prices), recipient=p.name)


def clue_choice(g, p, wish):
    def style(r):
        return {'statements': [r.choice(CLUES)]} if r.random() < _POLICY_wz['wizard_clue'] else {'statements': ['none']}
    return _judged_wz(_Choice_wz(f'{WIZARD} clue:{p.name}', [{'statements': [x]} for x in (*CLUES, 'none')], style),
                      'wizard_clue', f'{p.name} (Wizard) is granted "{wish.text}". Its clue: announced (the town is '
                      'told at dawn that a wish was granted), whispered (a good player learns what was wished), or '
                      'none?',
                      recipient=p.name)


def good_player_choice(g, cid, question, avoid=()):
    pool = [q.name for q in g.players if q.alive and not q.evil and q.name not in avoid]
    return _judged_wz(_Choice_wz(cid, [{'players': [x]} for x in pool], lambda r: {'players': [r.choice(pool)]}),
                      'wizard_witness', question) if pool else None


class Wizard(_Minion_wz):
    name = WIZARD
    ability = ability(name)

    def rule_text(self, script):
        return ['The Wizard\'s wish is one of a fixed list of wishes the Storyteller can grant, each with the prices '
                'it may have; the Wizard is shown the list when woken.']

    moment_unheld = True  # (the dawn's clue is announced even if the Wizard died paying for the wish)

    def moment(self, game, me, when):
        g = game.g
        if when == 'dawn' and game.day in g.notes.get('Wizard clues', ()):  # (once: the first call takes it)
            g.notes['Wizard clues'] = [x for x in g.notes['Wizard clues'] if x != game.day]
            game.emit('text', {'text': 'The Storyteller announces: a wish was granted in the night.'})

    async def resolve_night(self, game, night):
        g = game.g
        for p in [q for q in g.players if q.alive and _snv_wz.has(g, q, self.name) and not _snv_wz.used(g, q,
                                                                                                         self.name)]:
            await self.offer(game, night, p)

    async def offer(self, game, night, p):
        g = game.g
        menu = wish_menu()
        req = game.request('night', f'Night {night.n} — Wizard: once per game you may make a wish. The wishes the '
                                    'Storyteller can grant: ' + ' '.join(menu) + ' To wish, put its number in `say` '
                                    '(and the player it names in `targets`); to wait, leave `say` empty. A granted '
                                    'wish might have a price and leave a clue.', night.n, n_targets=1,
                           options=game.names,
                           min_targets=0, menu=menu)
        a = await game.ask(p.name, req)
        game.woken(p)
        say = (a.get('say') or '').strip()
        if not say:
            return
        m = _re_wz.search(r'\d+', say)
        wid = WISHES[int(m.group()) - 1].id if m and 1 <= int(m.group()) <= len(WISHES) else None
        if wid is None:
            wid = (await game.decide_judged(wish_match_choice(g, p, say)))['statements'][0]
            if wid == 'none':
                game.inform(p, f'Night {night.n} — Wizard: that is not a wish the Storyteller can grant; you '
                               'may wish another night.')
                return
        wish = WISH[wid]
        t = next(iter(game.targets(p.name, a, req)), None)
        ok = {'': True, 'any': t is not None, 'alive': t is not None and g[t].alive,
              'dead': t is not None and not g[t].alive and g[t].evil}[wish.target]
        if not ok:
            game.inform(p, f'Night {night.n} — Wizard: that wish needs a player ({wish.target or "none"}); none '
                           'fit, so no wish was made. You may wish another night.')
            return
        _snv_wz.use(g, p, self.name)  # (spent per player, drunk or not, as every once-per-game ability)
        game.emit('night_choice', {'player': p.name, 'role': self.name, 'targets': [t] if t else [],
                                   'wish': wish.id}, 'audit')
        if not g.works(p, self.name):
            _snv_wz.failed(game, p, self.name, 'the wish was not granted')
            game.inform(p, f'Night {night.n} — Wizard: you wished "{wish.text}". The Storyteller does not grant it.')
            return
        if not (await game.decide_judged(grant_choice(g, p, wish)))['yes']:
            game.inform(p, f'Night {night.n} — Wizard: you wished "{wish.text}". The Storyteller does not grant it.')
            return
        price = (await game.decide_judged(price_choice(g, p, wish)))['statements'][0]
        clue = (await game.decide_judged(clue_choice(g, p, wish)))['statements'][0]
        g.reminders.append(f'{p.name} (Wizard) wished: {wish.text}' + (f' ({t})' if t else '')
                           + f' Price: {PRICES.get(price, "none")}. Clue: {clue}.')
        game.inform(p, f'Night {night.n} — Wizard: your wish is granted: {wish.text}'
                       + (f' ({t})' if t else '') + (f' Its price: {PRICES[price]}.' if price != 'none' else ''))
        await self.grant(game, night, p, wish, t)
        await self.pay(game, night, p, price, t)
        await self.leave_clue(game, night, p, wish, clue)

    async def grant(self, game, night, p, wish, t):
        g, n = game.g, night.n
        if wish.id == 'kill':
            game.attempt_kill(g[t], 'wizard', p, night)
        elif wish.id == 'protect':
            for d in [q for q in g.players if q.alive and q.is_demon]:
                g.add(_State_wz('safe', d.name, source=p.name, until=n + 1, against='any'))
        elif wish.id == 'corrupt':
            if not g[t].evil:
                await game.change(g[t], alignment='evil')
        elif wish.id == 'learn':
            game.inform(p, f'Night {n} — Wizard: {t} is the {g[t].character}.')
        elif wish.id == 'grimoire':
            game.inform(p, f'Night {n} — Wizard: you see the Grimoire.\n' + g.grimoire_text())
        elif wish.id == 'drunk':
            g.add(_State_wz('drunk', t, source=p.name, until=n + 3))
        elif wish.id == 'revive':
            g.revive(g[t], source=self.name)
            night.revived.append(g[t])
        elif wish.id == 'bluffs':
            game.inform(p, f'Night {n} — Wizard: the Demon\'s bluffs are {", ".join(g.bluffs) or "none"}.')

    async def pay(self, game, night, p, price, t):
        g, n = game.g, night.n
        if price == 'poisoned':
            g.add(_State_wz('poisoned', p.name, source=None, until=n + 2))
        elif price == 'dies':
            game.attempt_kill(p, 'wizard', p, night, unstoppable=True)
        elif price == 'demon poisoned':
            for d in [q for q in g.players if q.alive and q.is_demon]:
                g.add(_State_wz('poisoned', d.name, source=None, until=n + 1))
        elif price in ('exposed', 'demon pair', 'told'):
            to = g[t] if price == 'told' and t and g[t].alive and g[t] is not p else None
            if to is None:
                c = good_player_choice(g, f'{WIZARD} witness:{p.name}', f'Who learns the price of {p.name}\'s wish?',
                                       avoid=(p.name,))
                if c is None:
                    return
                to = g[(await game.decide_judged(c))['players'][0]]
            if price == 'exposed':
                text = f'{p.name} is a Minion.'
            elif price == 'told':
                text = f'{p.name} is the Wizard.'
            else:
                demon = next((q for q in g.players if q.alive and q.is_demon), None)
                if demon is None:
                    return
                other = next((q for q in g.players if q is not demon and q is not to and q.alive), None)
                pair = sorted([demon.name] + ([other.name] if other else []), key=lambda x: g[x].seat)
                text = f'the Demon is {" or ".join(pair)}.'
            game.woken(to)
            game.inform(to, f'Night {n}: the Storyteller tells you that {text}')

    async def leave_clue(self, game, night, p, wish, clue):
        g = game.g
        if clue == 'announced':  # (at dawn: Wizard.moment)
            g.notes.setdefault('Wizard clues', []).append(night.n)
        elif clue == 'whispered':
            c = good_player_choice(g, f'{WIZARD} hears:{p.name}', 'Who learns what the Wizard wished?',
                                   avoid=(p.name,))
            if c is not None:
                to = g[(await game.decide_judged(c))['players'][0]]
                game.woken(to)
                game.inform(to, f'Night {night.n}: the Storyteller tells you that a wish was granted tonight: '
                                f'"{wish.text}"')


CHARACTERS[WIZARD] = Wizard()
# ---- end of Wizard -----------------------------------------------------------------------------------------------


# ---- Legion ------------------------------------------------------------------------------------------------------
# "Each night*, a player might die. Executions fail if only evil voted. You register as a Minion too. [Most players are
# Legion]" Several players have the one Demon character (Character.duplicates), dealt in place of the Minions and some
# good players (Character.deals); the game is good's when every Legion is dead. docs/carousel-rulings.md, batch 6,
# Legion.
from .characters import Demon as _Demon_lg, kind as _kind_lg  # noqa: E402
from .characters import jinx as _jinx_lg  # noqa: E402
from . import snv as _snv_lg  # noqa: E402
from .state import POLICY as _POLICY_lg, SETUPS as _SETUPS_lg, Choice as _Choice_lg, State as _State_lg  # noqa: E402
from .state import judged as _judged_lg, yes_choice as _yes_lg  # noqa: E402

LEGION = 'Legion'
_POLICY_lg.update({  # (Carousel, batch 6: Legion. Default, for review.)
    'legion_kill': 0.85,          # each night*, a player dies (else nobody), a living good player
    'legion_registers_evil': 0.5,  # a voter who may register either way (a Spy, a Recluse; the jinxes' Politician and
    #                                Zealot) registers as evil to Legion
    'legion_revealed': 0.5,       # the Minstrel and Preacher jinxes: the Minstrel (Preacher) learns they are Legion
})


def legion_count(n):
    """"Most players are Legion": a bare majority (a reading)."""
    return n // 2 + 1


def legions(g, alive=True):
    return [q for q in g.players if q.character == LEGION and (q.alive or not alive)]


def legion_victim_choice(g, n):
    alive = [q.name for q in g.players if q.alive and q.character != LEGION]
    if not alive:  # (only Legion left: one of them, so the game comes down to two players)
        alive = [q.name for q in g.players if q.alive]
    good = [x for x in alive if not g[x].evil]

    def style(r):
        if alive and r.random() < _POLICY_lg['legion_kill']:
            return {'players': [r.choice(good or alive)]}
        return {'players': []}
    return _judged_lg(_Choice_lg(f'{LEGION}:{n}', [{'players': [x]} for x in alive] + [{'players': []}], style),
                      'legion_victim', f'Night {n}: Legion might kill a player: who dies (none for nobody)?')


class Legion(_Demon_lg):
    name = LEGION
    ability = ability(name)
    kills_at_night = True
    deals = True
    duplicates = 15  # (every player but the good ones)
    own_evil_info = True  # its intro is the evil information (no Minions to show: Game.setup)
    also_minion = True  # "You register as a Minion too": to the Investigator (state.pair_choice), a reading
    setup_order = 9.8

    # ---- the deal ----------------------------------------------------------------------------------------------
    def deal_error(self, characters, script):
        if self.name not in characters:
            return None
        n, k = len(characters), characters.count(self.name)
        others = [c for c in characters if _kind_lg(c) in ('Minion', 'Demon') and c != self.name]
        if others:
            return f'only Legion is evil with Legion in play: {", ".join(others)}'
        if k * 2 <= n or k >= n:
            return f'most players are Legion, and not every one ({k} of {n})'
        return ''

    def redeal(self, rng, characters, players, script):
        # the Minions' seats and as many good seats as it takes go to Legion: a bare majority, the good players kept
        # being Townsfolk and the table's Outsiders first (a reading)
        if self.name not in characters:
            return characters
        good = [c for c in characters if _kind_lg(c) in ('Townsfolk', 'Outsider')]
        keep = players - legion_count(players)
        os_ = _SETUPS_lg[players][1]
        outs = [c for c in good if _kind_lg(c) == 'Outsider'][:min(os_, keep)]
        towns = [c for c in good if _kind_lg(c) == 'Townsfolk'][:keep - len(outs)]
        kept = towns + outs
        spare = [c for c in script.townsfolk if c not in kept]
        while len(kept) < keep and spare:
            kept.append(spare.pop(rng.randrange(len(spare))))
        if len(kept) < keep or ('Drunk' in kept and set(script.townsfolk) <= set(kept)):
            return None
        return kept + [self.name] * (players - keep)

    def rule_text(self, script):
        return ['Legion: when it is the Demon in play, most players are Legion (one Demon character shared by every '
                'evil player, and no Minions); the Legion learn each other. Each night except the first one player '
                'might die. An execution fails (the player does not die) if every player who voted for it is evil.']

    # ---- what the Legion learn ---------------------------------------------------------------------------------
    def intro(self, game, me):
        g = game.g
        bluffs = f'Three good characters not in play, for evil to bluff: {", ".join(g.bluffs)}.'
        if g.script.jinxed('Magician', self.name) and any(q.character == 'Magician' for q in g.players):
            # the jinx: "Legion wake in separate groups. Each group learns which players are good, but does not
            # learn the Magician" (the groups: each Legion alone, a reading); the good players named are all but
            # the Magician
            good = [q.name for q in g.players if not q.evil and q.character != 'Magician']
            return [f'You are one of the Legion. With the Magician in play you learn only which players are good: '
                    f'{", ".join(good)}. {bluffs}']
        others = [q.name for q in legions(g) if q is not me]
        return [f'You are one of the Legion: there are no Minions, and the other Legion are '
                f'{", ".join(others) or "none"}. {bluffs}']

    async def setup(self, game):
        # the Engineer jinx: "If Legion is in play, the Engineer starts knowing this but has no ability": no ability
        # is the engine's drunkenness, for good (as the Preacher's). (The Hatter's: Legion.resolve_night)
        g = game.g
        if not legions(g):
            return
        for q in [q for q in g.players if q.character == 'Engineer' and g.script.jinxed(self.name, 'Engineer')]:
            g.add(_State_lg('drunk', q.name, source=None, until=None))
            g.notes.setdefault('Intro', {}).setdefault(q.name, []).append('Legion is in play, so you have no ability.')

    # ---- the night ---------------------------------------------------------------------------------------------
    async def resolve_night(self, game, night):
        g = game.g
        alive = legions(g)
        self.no_tea_party(g, alive)
        if night.first or not alive:
            return
        working = [q for q in alive if g.works(q, self.name) and q.name not in night.asleep]
        if not working:
            for q in alive:
                _snv_lg.failed(game, q, self.name, 'nobody died')
            return
        v = await game.decide_judged(legion_victim_choice(g, night.n))
        if v['players']:
            await game.attempt_kill_judged(g[v['players'][0]], 'demon', working[0], night)
        self.no_tea_party(g, legions(g))

    def no_tea_party(self, g, alive):
        # the Hatter jinx: "If Legion is in play, the Hatter has no ability": no tea party tonight (whoever has the
        # Hatter's ability: the Hermit's too), Legion's step coming before the Hatter's
        if alive and g.notes.get('Tea party') and g.script.jinxed(self.name, 'Hatter'):
            g.notes['Tea party'] = None

    # ---- executions --------------------------------------------------------------------------------------------
    async def before_execution(self, game, me, executed):
        # "Executions fail if only evil voted": the vote that put them on the block (today's last nomination of
        # them), with at least one vote, every voter registering as evil to Legion, while a living Legion is sober:
        # they survive the execution (asked once, for the first Legion in seat order)
        g = game.g
        alive = legions(g)
        if not alive or me is not alive[0] or not executed.alive:
            return
        noms = [x for x in g.nominations if x['day'] == game.day and x['nominee'] == executed.name]
        voters = noms[-1].get('voters') if noms else None
        if not voters or not any(g.works(q, self.name) for q in alive):
            return
        for x in voters:
            q = g[x]
            regs = set(g.registers_evil(q, me))
            if any(g.script.jinxed(self.name, c) and q.character == c for c in ('Politician', 'Zealot')):
                regs.add(True)  # the jinxes: they might register as evil to Legion
            if regs == {False}:
                return
            if regs != {True} and not (await game.decide_judged(_judged_lg(
                    _yes_lg(f'Legion sees:{x}', _POLICY_lg['legion_registers_evil']), 'legion_registers_evil',
                    f'{x} ({q.character}) voted: do they register as evil to Legion (yes)?', about=x)))['yes']:
                return
        g.add(_State_lg('safe', executed.name, source=me.name, until='night', against='execution'))
        g.reminders.append(f'Day {game.day}: only evil voted to execute {executed.name}: the execution fails.')

    def on_death(self, game, me, dead, cause, alive_before):
        # the Minstrel jinx: Legion registers as a Minion, so a Legion executed sets off the Minstrel ("all other
        # players are drunk until dusk tomorrow"), but "Legion keeps their ability" (the Legion are not made drunk)
        # and the Minstrel might learn they are Legion. Once per death, for the first Legion holding the hook
        g = game.g
        if cause != 'execution' or dead.character != self.name or me is not next(
                (q for q in g.players if q.character == self.name), None):
            return
        for m in [q for q in g.players if q.character == 'Minstrel' and g.works(q, 'Minstrel')
                  and g.script.jinxed(self.name, 'Minstrel')]:
            for p in g.players:
                if p is not m and not p.traveller and p.character != self.name:
                    g.add(_State_lg('drunk', p.name, source=m.name, until=game.day + 2, ends_with_source=True))
            game.later(lambda game, m=m: self.reveal(game, m, dead, 'Minstrel'))

    async def reveal(self, game, to, who, by):
        if (await game.decide_judged(_judged_lg(_yes_lg(f'Legion revealed:{to.name}', _POLICY_lg['legion_revealed']),
                                                'legion_revealed', f'Does the {by} ({to.name}) learn that {who.name} '
                                                'is Legion (yes)?', recipient=to.name)))['yes']:
            game.woken(to)
            game.inform(to, f'{_snv_lg.when(game)} — {by}: {who.name} is Legion.')

    def chosen(self, game, me, chooser, night):
        # the Preacher jinx: "If the Preacher chooses Legion, Legion keeps their ability (the Preacher acts only on a
        # Minion character), but the Preacher might learn they are Legion"
        g = game.g
        if chooser.character == 'Preacher' and g.works(chooser, 'Preacher') and g.script.jinxed(self.name, 'Preacher'):
            game.later(lambda game: self.reveal(game, chooser, me, 'Preacher'))

    async def becomes(self, game, me):
        # "If Legion is created, all evil players become Legion" (the Engineer, Hatter and Summoner jinxes; the
        # Pit-Hag's too, as the rule they share: a reading)
        g = game.g
        others = [q for q in g.players if q.evil and q.character != self.name and q is not me]
        if others:
            await game.changes([(q, self.name, None) for q in others])


CHARACTERS[LEGION] = Legion()
for _other in ('Engineer', 'Hatter', 'Minstrel', 'Politician', 'Preacher', 'Summoner', 'Zealot', 'Magician'):
    _jinx_lg(LEGION, _other, 'carousel_extra.Legion')
    JINXES.append((LEGION, _other))
# ---- end of Legion -----------------------------------------------------------------------------------------------


# ---- Riot --------------------------------------------------------------------------------------------------------

# ---- end of Riot -------------------------------------------------------------------------------------------------
