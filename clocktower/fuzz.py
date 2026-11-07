"""Fuzzing: random scripts drawn from every built character, random-bot games on them, invariants checked as they play.

Smoke runs (smoke.py) play the real scripts; this plays scripts nobody wrote, so characters meet that no script puts
together. Each game is a random legal script (by default 13 Townsfolk, 4 Outsiders, 4 Minions and 4 Demons, drawn
from characters.CHARACTERS), written as a script JSON and loaded like any custom script, so its night order and jinxes
are the official ones; random bots play it under the scripted Storyteller or the rules judge, seeded, so every game
replays from its one-line repro command.

The game is a Game subclass (FuzzGame) whose overrides only watch: they call the engine's own method and then check
the Grimoire, drawing no random number and changing nothing, so play is exactly the engine's (tests/test_fuzz.py
replays recorded fingerprints through it). What is checked, after every night step, every turn of the day and at
each dawn and dusk (Monitor):

- information ('oracle', 'engine-truth', 'falsified-true'): what a sober, healthy player with the ability is told
  must be true, judged by the engine's own truth test and, for the information roles in ORACLES, by an independent
  one computed here from the Grimoire (only the characters whose text says they "might register" may register
  otherwise); information the Vortox falsifies must be false;
- dead players' abilities ('dead-acts'): the dead don't wake, learn, kill or place states unless they keep their
  ability (the Vigormortis's Minions) or their ability says it works on or after death (DEAD_OK);
- once-per-game abilities ('once-twice'): a player-character instance (a new character or a return to life starts a
  new one) uses it at most once; a player who only believes they have it is not woken to use it again
  ('once-rewoken');
- the Grimoire's coherence ('coherence'): known characters on the script, one alignment, no two living players with
  the same character, states naming real players, no state outliving the source it ends with;
- the end ('missed-win', 'false-win', 'continued-past-win'): no play once there is a winner, no standard win
  declared without its condition, no dawn or dusk with a standard win condition met and nothing to delay it;
- crashes and loops ('crash', 'loop', 'timeout'): every exception, more than STEP_CAP seat requests, or a game over
  TIME_CAP seconds.

Advisories (not violations, reported for review): states that outlive a dead source, and an unclear error for a
setup that cannot be dealt.

Pair coverage counts, for every pair of characters, the games in which both were in play (at any point) and the games
in which both also acted (woke, learned, killed, placed a state or used a public ability; a character with no
choice and no information of its own counts as acting when in play). `--target-uncovered` puts the pairs least often
seen both acting onto the script and into play. `matrix` plays each character against each shared mechanism in short
forced scenarios.

    python -m clocktower fuzz run --games 2000 --workers 4 --out /tmp/fuzz        # random scripts, both modes
    python -m clocktower fuzz run --games 500 --target-uncovered --coverage /tmp/fuzz/coverage.json --out /tmp/f2
    python -m clocktower fuzz repro --seed 123 --players 9 --judge rules --chars chef,empath,...   # one game again
    python -m clocktower fuzz matrix --out /tmp/matrix
"""
from __future__ import annotations
import argparse
import asyncio
import copy
import json
import multiprocessing
import os
import random
import re
import signal
import sys
import tempfile
import time
import traceback
from collections import Counter
from itertools import combinations, product
from pathlib import Path

from . import judge as judges, official
from .agents import RandomSeat
from .characters import CHARACTERS, SETUPS, Character, Script, kind, rules
from .game import ALL_NAMES, Game
from .state import norm, setup_error

TYPES = ('Townsfolk', 'Outsider', 'Minion', 'Demon')
SCRIPT_COUNTS = (13, 4, 4, 4)
EXCLUDED = set()  # built characters a random script should not draw (none yet)
STEP_CAP = 30000  # seat requests per game before it counts as a loop
TIME_CAP = 120    # seconds per game
SEED_BASE = 9_000_000


def text(c):
    return official.role(c)['ability']


def _matching(pattern):
    return {c for c in CHARACTERS if re.search(pattern, text(c).lower())}


# characters that may register as something they are not ("might register": the Spy, the Recluse)
MISREG = _matching(r'might register')
# abilities that act on or after their owner's death
DEAD_OK = _matching(r'you die|you died|kills you|even if dead|dead, you')
ONCE = _matching(r'once per game')


def misreg(p):
    return p.character in MISREG


def pool():
    """{type: [names]}: every built character a script can deal."""
    return {k: sorted(n for n, c in CHARACTERS.items() if c.kind == k and n not in EXCLUDED) for k in TYPES}


def ids(names):
    return ','.join(official.ids()[n] for n in names)


def names_of(spec):
    by_id = {i: r['name'] for i, r in official.roles().items()}
    return [by_id[official.official_id(x)] for x in spec.split(',') if x.strip()]


# ---- scripts ------------------------------------------------------------------------------------------------------

def random_script(rng, counts=SCRIPT_COUNTS, weights=None, force=()):
    """A random script: `counts` characters of each type (fewer if fewer are built), `force` among them, the rest
    drawn without replacement, weighted by `weights` ({name: weight}, default uniform)."""
    out = []
    for k, n in zip(TYPES, counts):
        names = pool()[k]
        chosen = [c for c in force if c in names]
        rest = [c for c in names if c not in chosen]
        while len(chosen) < n and rest:
            w = [weights.get(c, 1.0) if weights else 1.0 for c in rest]
            c = rng.choices(rest, w)[0]
            chosen.append(c)
            rest.remove(c)
        out += chosen
    return out


SCRIPT_DIR = None


def make_script(chars):
    """The characters as a script JSON in the official format, loaded as any custom script (official night order and
    jinxes)."""
    global SCRIPT_DIR
    if SCRIPT_DIR is None:
        SCRIPT_DIR = Path(tempfile.mkdtemp(prefix='clocktower-fuzz-'))
    path = SCRIPT_DIR / f'fuzz-{os.getpid()}.json'
    path.write_text(json.dumps([{'id': '_meta', 'name': 'Fuzz', 'author': 'clocktower fuzz'},
                                *(official.ids()[c] for c in chars)]))
    return Script(path)


def setup_with(script, required, rng, players=None, tries=60):
    """A legal setup of `script` (a list in seat order) with every character in `required` in play (only the first
    Demon, if several), for `players` or any table size; None if there is none."""
    req = [c for c in required if c in script.all]
    demons = [c for c in req if kind(c) == 'Demon'][:1]
    req = [c for c in req if kind(c) != 'Demon'] + demons
    sizes = [players] if players else rng.sample(sorted(SETUPS), len(SETUPS))
    for n in sizes:
        for _ in range(tries):
            tf, os_, mn = SETUPS[n]
            minions = [c for c in req if kind(c) == 'Minion']
            if len(minions) > mn:
                break
            minions += rng.sample([m for m in script.minions if m not in minions], mn - len(minions))
            demon = demons or [rng.choice(script.demons)]
            shift = rng.choice(range(-2, 4))  # setup modifiers move Outsiders: try several counts
            o = max(0, os_ + shift)
            t = tf + os_ - o
            goods = [c for c in req if kind(c) in ('Townsfolk', 'Outsider')]
            towns = [c for c in goods if kind(c) == 'Townsfolk']
            outs = [c for c in goods if kind(c) == 'Outsider']
            if len(towns) > t or len(outs) > o or t < 0:
                continue
            spare_t = [c for c in script.townsfolk if c not in towns]
            spare_o = [c for c in script.outsiders if c not in outs]
            if len(spare_t) < t - len(towns) or len(spare_o) < o - len(outs):
                continue
            chars = (towns + rng.sample(spare_t, t - len(towns)) + outs + rng.sample(spare_o, o - len(outs))
                     + minions + demon)
            if setup_error(chars, script) is None:
                rng.shuffle(chars)
                return chars
    return None


# ---- the watched game -----------------------------------------------------------------------------------------------

class StepCap(RuntimeError):
    """A game made more than STEP_CAP seat requests: a loop."""


class FuzzGame(Game):
    """A Game whose overrides call the engine's own method and then let the Monitor look: no random draw, no
    change to play."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fz = Monitor(self)

    def emit(self, kind_, data, to='public'):
        super().emit(kind_, data, to)
        if self.g is not None:
            self.fz.event(kind_, data)

    async def ask(self, name, request):
        self.fz.asked(name, request)
        return await super().ask(name, request)

    async def decide_judged(self, choice):
        value = await super().decide_judged(choice)
        self.fz.decided(choice, value)
        return value

    async def wake(self, night, characters):
        woken = await super().wake(night, characters)
        self.fz.woke(night, characters, woken)
        return woken

    def kill(self, p, cause, source=None, final=False):
        self.fz.killing(p, cause, source)
        return super().kill(p, cause, source, final)

    async def run_pending(self):
        await super().run_pending()
        self.fz.step('step')

    async def night(self, n):
        self.fz.boundary('dusk', n)  # (the run loop has checked for a winner: Game.run)
        await super().night(n)

    async def daytime(self, n):
        self.fz.boundary('dawn', n)
        await super().daytime(n)


def overrides_end(c):
    return type(rules(c)).overrides_end is not Character.overrides_end


class Monitor:
    """The invariants, checked as the game plays (see the module docstring). Reads the Grimoire, never changes it."""

    def __init__(self, game):
        self.game = game
        self.violations, self.advisories = [], []
        self.asks = 0
        self.in_play, self.acted = set(), set()
        self.epoch = Counter()       # player -> instance number (a new character, a return to life)
        self.once = Counter()        # (player, role, epoch) -> uses
        self.states_seen = {}        # id(state) -> (source character, source alive) when first seen
        self.death_chars = {}        # player -> character when they (last) died
        self.votes, self.noms = [], []  # (day, voter, character) with a yes vote; (day, nominator, character)
        self.revived = 0
        self.won_checked = False
        self.past_win = False
        self.step_name = 'setup'
        self.flagged = set()
        self.checked = Counter()  # information checked, by 'engine:' or 'oracle:' and role
        self.touched = {p: set() for p in game.names}  # player -> {(state kind, source character)} seen

    # ---- recording ----------------------------------------------------------------------------------------------
    def flag(self, type_, detail, chars=(), advisory=False):
        game = self.game
        if (type_, detail) in self.flagged or len(self.violations) > 100:
            return  # each once a game (a check repeats at every step); a runaway check stops recording
        self.flagged.add((type_, detail))
        entry = {'type': type_, 'detail': detail, 'characters': sorted(set(chars)), 'day': game.day,
                 'phase': game.phase, 'step': self.step_name}
        (self.advisories if advisory else self.violations).append(entry)

    @property
    def g(self):
        return self.game.g

    def asked(self, name, request):
        self.asks += 1
        if self.asks > STEP_CAP:
            raise StepCap(f'more than {STEP_CAP} seat requests')
        g = self.g
        if g is not None and g.winner and not self.past_win:
            self.past_win = True
            self.flag('continued-past-win', f'{name} asked ({request.kind}) after {g.winner} won: {g.reason}')

    def event(self, kind_, data):
        g = self.g
        if kind_ in ('becomes', 'gains'):
            self.epoch[data['player']] += 1
            self.in_play.add(data['character'])
        elif kind_ == 'night_choice':
            self.night_choice(data)
        elif kind_ == 'vote' and data.get('yes'):
            self.votes.append((self.game.day, data['voter'], g[data['voter']].character))
        elif kind_ == 'nomination':
            self.noms.append((self.game.day, data['nominator'], g[data['nominator']].character))
        elif kind_ == 'slayer':
            s = g[data['shooter']]
            if data.get('died'):
                if 'Slayer' not in g.abilities(s):
                    self.flag('ability-without-character', f'{s.name} ({s.character}) shot {data["target"]} dead '
                                                            'without the Slayer\'s ability', [s.character])
                else:
                    self.use(s, 'Slayer')
                self.acted.add('Slayer')
        elif kind_ in ('ability', 'visit_text'):
            p = g[data['player']]
            if data.get('character') in g.abilities(p):
                self.acted.add(data['character'])

    def use(self, p, role):
        key = (p.name, role, self.epoch[p.name])
        self.once[key] += 1
        if self.once[key] == 2:
            really = role in self.g.abilities(p)
            self.flag('once-twice' if really else 'once-rewoken',
                      f'{p.name} ({p.character}{"" if really else ", believing they are the " + role}) used the '
                      f'once-per-game {role} ability a second time', [p.character, role])

    def night_choice(self, data):
        g = self.g
        p, role = g[data['player']], data.get('role')
        if role in g.abilities(p):
            self.acted.add(role)
        if role not in ONCE:
            return
        targets, character = data.get('targets') or [], data.get('character')
        used = {'Seamstress': len(targets) == 2, 'Courtier': character is not None,
                'Philosopher': character is not None}.get(role, bool(targets))
        if used:
            self.use(p, role)

    # ---- information ----------------------------------------------------------------------------------------------
    def decided(self, choice, value):
        g = self.g
        if g is None:
            return
        ctx = choice.context or {}
        role = ctx.get('ability') or choice.id.split(':')[0]
        if role in CHARACTERS:
            self.acted.add(role)
        if ctx.get('call') != 'information' or role not in CHARACTERS:
            return
        p = g.by_name.get(ctx.get('recipient'))
        if p is None:
            return
        value = norm(value)
        has = role in g.abilities(p)
        if not (p.alive or g.keeps_ability(p)) and role not in DEAD_OK:
            self.flag('dead-acts', f'dead {p.name} ({p.character}) was given {role} information', [p.character, role])
        healthy = has and not g.impaired(p)
        falsified = g.falsified(p, role)
        truth = choice.truth(value) if choice.truth else None
        shown = json.dumps({k: v for k, v in value.items() if v not in (None, [])})
        if healthy and not falsified and truth is False:
            self.flag('engine-truth', f'healthy {p.name} ({role}) was given {shown}, false by the engine\'s own test',
                      [role, *self.context_chars()])
        if falsified and has and truth is True and not ctx.get('impaired'):  # built as reliable information
            self.flag('falsified-true', f'{p.name} ({role}) was given true information {shown} although it must be '
                                        'false (the Vortox)', [role, *self.falsifiers()])
        oracle = ORACLES.get(role)
        if healthy and not falsified:
            self.checked['engine:' + role] += 1
        if healthy and not falsified and oracle:
            self.checked['oracle:' + role] += 1
            problem = oracle(self, p, ctx, value)
            if problem:
                self.flag('oracle', f'healthy {p.name} ({role}) was given {shown}: {problem}',
                          [role, *self.context_chars()])

    def falsifiers(self):
        return [q.character for q in self.g.players if rules(q.character).falsifies_info]

    def context_chars(self):
        return sorted({q.character for q in self.g.players})

    # ---- dead players ---------------------------------------------------------------------------------------------
    def woke(self, night, characters, woken):
        g = self.g
        for name in woken:
            p = g[name]
            if not (p.alive or g.keeps_ability(p)):
                self.flag('dead-acts', f'dead {p.name} ({p.character}) was woken at the {"/".join(characters)} step',
                          [p.character, *characters])
        self.step_name = f'night {night.n}: {"/".join(characters)}'

    def killing(self, p, cause, source):
        g = self.g
        if not p.alive:
            self.flag('coherence', f'{p.name} ({p.character}), already dead, killed again ({cause})', [p.character])
        if cause == 'execution':
            self.death_chars[p.name] = p.character
        c = source.character if source is not None and cause == 'demon' else CAUSES.get(cause)
        if c:
            self.acted.add(c)
        if source is not None and source is not p and not (source.alive or g.keeps_ability(source)):
            if c not in DEAD_OK and cause not in STORYTELLER_DEATHS and not DEAD_OK & set(g.abilities(source)):
                self.flag('dead-acts', f'{p.name} killed ({cause}) by dead {source.name} ({source.character})',
                          [source.character, p.character])

    # ---- every step -------------------------------------------------------------------------------------------------
    def step(self, where):
        g = self.g
        if g is None:
            return
        script = g.script
        living = Counter()
        for p in g.players:
            self.in_play.add(p.character)
            self.in_play.update(g.abilities(p))
            if p.character not in CHARACTERS or p.character not in script.all:
                self.flag('coherence', f'{p.name} has character {p.character!r}, not on the script', [p.character])
            if p.shown not in CHARACTERS:
                self.flag('coherence', f'{p.name} believes they are {p.shown!r}', [p.character])
            elif p.shown != p.character and not (rules(p.character).always_drunk
                                                 or rules(p.character).wakes_at_own_step):
                self.flag('coherence', f'{p.name} is the {p.character} but believes they are the {p.shown}',
                          [p.character, p.shown])
            if p.alignment not in ('good', 'evil'):
                self.flag('coherence', f'{p.name} has alignment {p.alignment!r}', [p.character])
            if getattr(p, 'extra', None) and 'gain' not in text(p.character).lower():
                self.flag('coherence', f'{p.name} ({p.character}) holds extra abilities {p.extra}', [p.character])
            if p.alive:
                living[p.character] += 1
        for c, n in living.items():
            if n > 1:
                self.flag('coherence', f'{n} living players are the {c}', [c])
        self.check_states()
        for st in [*g.states, *g.derived()]:  # what touched whom (the mechanism matrix reads it)
            if g.active(st):
                self.touched[st.target].add((st.kind, g[st.source].character if st.source in g.by_name else None))
        for name, used in g.notes.get('Used', {}).items():
            for role, n in Counter(used).items():
                if n > 1 and (name, role, n) not in self.flagged:
                    self.flagged.add((name, role, n))
                    self.flag('once-twice', f'{name} ({g[name].character}) used the {role} ability {n} times',
                              [g[name].character, role])
        if len(g.revivals) > self.revived:
            for r in g.revivals[self.revived:]:
                self.epoch[r['player']] += 1
                self.acted.add(r.get('source'))
            self.revived = len(g.revivals)
        if g.winner and not self.won_checked:
            self.won_checked = True
            self.check_win()

    def check_states(self):
        g = self.g
        for s in g.states:
            if s.target not in g.by_name or (s.source is not None and s.source not in g.by_name):
                self.flag('coherence', f'a {s.kind} state names a player not in the game: {s.target}/{s.source}', [])
                continue
            src = g[s.source] if s.source else None
            first = self.states_seen.get(id(s))
            if first is None:
                self.states_seen[id(s)] = (src.character if src else None, src.alive if src else None, s)
                if src is not None and self.paradox(s, src):
                    key = ('paradox', f'a dead {src.character} kept its ability through a {s.kind} state it put on '
                                      f'the {g[s.target].character} that keeps it', src.character)
                    if key not in self.flagged:
                        self.flagged.add(key)
                        self.flag(key[0], key[1], [src.character, g[s.target].character], advisory=True)
                    self.states_seen[id(s)] = (src.character, True, s)
                    continue
                if src is not None and not (src.alive or g.keeps_ability(src)) and not DEAD_OK & set(g.abilities(src)):
                    self.flag('dead-acts', f'dead {src.name} ({src.character}) put a {s.kind} state on {s.target}',
                              [src.character, g[s.target].character])
                if src is not None:
                    self.acted.add(src.character)
                continue
            if src is None:
                continue
            made_by, alive = first[0], src.alive or g.keeps_ability(src) or self.paradox(s, src)
            if s.ends_with_source and (not alive or made_by not in g.abilities(src)) and (id(s), 1) not in self.flagged:
                self.flagged.add((id(s), 1))
                kept = [f'{k.source} ({g[k.source].character}, {"paused" if not g.active(k) else "active"})'
                        for k in g.states if k.kind == 'has ability' and k.target == src.name and k.source]
                self.flag('coherence', f'a {s.kind} state on {s.target} outlived its source {src.name} ({made_by}, '
                                       f'now {src.character}, {"alive" if src.alive else "dead"}'
                                       + (f'; ability kept by {", ".join(kept)}' if kept else '') + ')',
                          [made_by, g[s.target].character] + [g[k.source].character for k in g.states
                                                               if k.kind == 'has ability' and k.target == src.name])
            elif not s.ends_with_source and s.until is not None and not alive and first[1] and made_by not in DEAD_OK:
                key = ('state', f'a {s.kind} state outlives its dead source ({s.until})', made_by)
                if key not in self.flagged:
                    self.flagged.add(key)
                    self.flag(key[0], key[1], [made_by], advisory=True)

    def paradox(self, s, src):
        """Whether state `s` (poison, drunkenness) is on the player whose ability lets its dead source keep theirs:
        the dead Poisoner, kept by the Vigormortis, poisoning the Vigormortis."""
        g = self.g
        return (s.kind in ('poisoned', 'drunk') and not src.alive
                and any(k.kind == 'has ability' and k.target == src.name and k.source == s.target for k in g.states))

    def boundary(self, when, n):
        """Dusk before night n, or dawn of day n: a standard win condition met must have ended the game, unless a
        character can delay the end (then for at most a day and a night)."""
        g = self.g
        self.step(when)
        self.step_name = f'{when} {n}'
        if g is None or g.winner:
            return
        demon = any(p.alive and p.is_demon for p in g.players)
        alive = sum(1 for p in g.players if p.alive and not p.traveller)
        if demon and alive > 2:
            return
        delay = [p.character for p in g.players if overrides_end(p.character)]
        # a character that can delay the end (the Mastermind, the Evil Twin) is asked on a copy, since asking may
        # change its bookkeeping (the Mastermind's extra day)
        if delay and copy.deepcopy(g).check_victory() is None:
            return
        what = 'no living Demon' if not demon else f'only {alive} players alive'
        self.flag('missed-win', f'{what} at {when} {n}, and no winner', delay or self.context_chars())

    def check_win(self):
        g = self.g
        demon = any(p.alive and p.is_demon for p in g.players)
        alive = sum(1 for p in g.players if p.alive and not p.traveller)
        if g.reason == 'The Demon is dead.' and demon:
            self.flag('false-win', 'good won "The Demon is dead." with a Demon alive', self.context_chars())
        if g.reason == 'Only two players remain alive.' and alive > 2:
            self.flag('false-win', f'evil won "Only two players remain" with {alive} alive', self.context_chars())

    def passive_in_play(self):
        """Characters in play with no night choice, no information of their own, no public action and no visit (the
        Soldier, the Baron, the Spy, the Scarlet Woman, the Barber, the Evil Twin): in play counts as acting."""
        return {c for c in self.in_play if rules(c).night_choice is None and not rules(c).info
                and rules(c).public_action is None and not rules(c).visit}


CAUSES = {c.lower(): c for c in CHARACTERS}
STORYTELLER_DEATHS = {'pit-hag'}  # the Storyteller's arbitrary deaths when a Demon is made, whoever the source


# ---- the independent information oracles ----------------------------------------------------------------------------
# Each returns None if the value is one a working ability could give in this Grimoire, else why not. Registration: only
# a character whose text says it "might register" (MISREG) may register otherwise, and then as anything.

def reg_evil(p):
    return {True, False} if misreg(p) else {p.evil}


def could_be(p, character):
    return misreg(p) or p.character == character


def _pair(group):
    def check(m, p, ctx, v):
        g = m.g
        if not v['players']:
            if group != 'Outsider':
                return 'no players shown'
            real = [q.name for q in g.players if kind(q.character) == 'Outsider' and not misreg(q)]
            return f'"zero Outsiders" with {", ".join(real)} in play' if real else None
        c = v['character']
        if c is None or kind(c) != group:
            return f'{c} is not a {group}'
        if not any(could_be(g[x], c) for x in v['players']):
            return f'neither is the {c} (' + ', '.join(f'{x}: {g[x].character}' for x in v['players']) + ')'
        return None
    return check


def _counts(players, f):
    """Every value of f(evil set) over the registrations the players could have."""
    flex = [q for q in players if misreg(q)]
    fixed = {q.name for q in players if q.evil and not misreg(q)}
    out = set()
    for combo in product((False, True), repeat=len(flex)):
        out.add(f(fixed | {q.name for q, e in zip(flex, combo) if e}))
    return out


def chef(m, p, ctx, v):
    ring = m.g.players
    n = len(ring)
    ok = _counts(ring, lambda evil: sum(1 for i in range(n) if ring[i].name in evil and ring[(i + 1) % n].name in evil))
    return None if v['number'] in ok else f'{v["number"]} pairs, but the Grimoire gives {sorted(ok)}'


def neighbours(g, p):
    out = []
    n = len(g.players)
    for step in (-1, 1):
        for k in range(1, n):
            q = g.players[(p.seat + step * k) % n]
            if q is not p and q.appears_alive:
                out.append(q)
                break
    return out[:1] if len(out) == 2 and out[0] is out[1] else out


def empath(m, p, ctx, v):
    nb = neighbours(m.g, p)
    ok = _counts(nb, lambda evil: sum(1 for q in nb if q.name in evil))
    return None if v['number'] in ok else (f'{v["number"]} evil, but its neighbours ' + ', '.join(
        f'{q.name} ({q.character}, {q.alignment})' for q in nb) + f' give {sorted(ok)}')


def fortune_teller(m, p, ctx, v):
    g = m.g
    ts = [g[x] for x in ctx.get('players') or []]
    must = any(kind(q.character) == 'Demon' or q.name == g.red_herring for q in ts)
    can = must or any(misreg(q) for q in ts)
    who = ', '.join(f'{q.name}: {q.character}' for q in ts)
    if v['yes'] and not can:
        return f'YES, but neither is a Demon or the red herring ({who})'
    if not v['yes'] and must:
        return f'NO, but one is a Demon or the red herring ({who})'
    return None


def undertaker(m, p, ctx, v):
    g = m.g
    t = ctx.get('about') or g.executed_death
    was = m.death_chars.get(t, g[t].character)
    if v['character'] == was or was in MISREG:
        return None
    return f'{t} died by execution as the {was}' + (f' (now the {g[t].character})' if g[t].character != was else '')


def ravenkeeper(m, p, ctx, v):
    t = m.g[ctx['about']]
    if t is p and v['character'] == p.shown:
        return None
    return None if could_be(t, v['character']) else f'{t.name} is the {t.character}'


def clockmaker(m, p, ctx, v):
    g = m.g
    options = []
    for q in g.players:
        k = kind(q.character)
        options.append({k, 'Minion', 'Demon', 'other'} if misreg(q) else {k})
    ok = set()
    from .snv import steps_between
    for combo in product(*[sorted(o) for o in options]):
        ds = [q for q, k in zip(g.players, combo) if k == 'Demon']
        ms = [q for q, k in zip(g.players, combo) if k == 'Minion']
        if ds and ms:
            ok.add(min(steps_between(g, d, x) for d in ds for x in ms if d is not x) if any(
                d is not x for d in ds for x in ms) else None)
        if len(ok) > 8:
            break
    return None if v['number'] in ok else f'{v["number"]} steps, but the Grimoire gives {sorted(x for x in ok if x)}'


def dreamer(m, p, ctx, v):
    t = m.g[ctx['about']]
    a, b = v['characters']
    if kind(a) not in ('Townsfolk', 'Outsider') or kind(b) not in ('Minion', 'Demon'):
        return f'not one good and one evil character: {a}, {b}'
    return None if could_be(t, a) or could_be(t, b) else f'{t.name} is the {t.character}'


def seamstress(m, p, ctx, v):
    a, b = (m.g[x] for x in ctx['players'])
    ok = {x == y for x in reg_evil(a) for y in reg_evil(b)}
    return None if v['yes'] in ok else f'{a.name} is {a.alignment}, {b.name} is {b.alignment}'


def oracle(m, p, ctx, v):
    dead = [q for q in m.g.players if not q.appears_alive]
    ok = _counts(dead, lambda evil: sum(1 for q in dead if q.name in evil))
    return None if v['number'] in ok else f'{v["number"]} evil dead, but the Grimoire gives {sorted(ok)}'


def _today(records, day, k):
    must = any(d == day and kind(c) == k for d, _, c in records)
    can = must or any(d == day and c in MISREG for d, _, c in records)
    return must, can


def flowergirl(m, p, ctx, v):
    must, can = _today(m.votes, m.game.day - 1, 'Demon')
    return 'YES, but no Demon voted' if v['yes'] and not can else 'NO, but a Demon voted' if not v['yes'] and must \
        else None


def town_crier(m, p, ctx, v):
    must, can = _today(m.noms, m.game.day - 1, 'Minion')
    return 'YES, but no Minion nominated' if v['yes'] and not can else 'NO, but a Minion nominated' \
        if not v['yes'] and must else None


def sage(m, p, ctx, v):
    g = m.g
    death = next((d for d in reversed(g.death_log) if d['player'] == p.name and d['cause'] == 'demon'), None)
    killer = death and death['source']
    if killer in v['players']:
        return None
    if g.script.jinxed('Recluse', 'Sage') and any(g[x].character == 'Recluse' for x in v['players']):
        return None
    return f'the Demon who killed them was {killer}'


def grandmother(m, p, ctx, v):
    g = m.g
    child = g.notes.get('Grandchild')
    x = v['players'][0] if v['players'] else None
    if x != child:
        return f'{x} is not the Grandchild ({child})'
    if g[x].evil and m.game.start_teams.get(x) != 'good':  # (a Goon who turned evil since setup is still shown)
        return f'the Grandchild {x} is evil'
    return None if could_be(g[x], v['character']) else f'{x} is the {g[x].character}'


def godfather(m, p, ctx, v):
    g = m.g
    real = {q.character for q in g.players if kind(q.character) == 'Outsider'}
    flex = {q.character for q in g.players if misreg(q)}
    shown = set(v['characters'])
    if real - flex <= shown and all(c in real or flex for c in shown):
        return None
    return f'shown {sorted(shown)}, in play {sorted(real)}'


ORACLES = {'Washerwoman': _pair('Townsfolk'), 'Librarian': _pair('Outsider'), 'Investigator': _pair('Minion'),
           'Chef': chef, 'Empath': empath, 'Fortune Teller': fortune_teller, 'Undertaker': undertaker,
           'Ravenkeeper': ravenkeeper, 'Clockmaker': clockmaker, 'Dreamer': dreamer, 'Seamstress': seamstress,
           'Oracle': oracle, 'Flowergirl': flowergirl, 'Town Crier': town_crier, 'Sage': sage,
           'Grandmother': grandmother, 'Godfather': godfather}


# ---- one game -------------------------------------------------------------------------------------------------

def spec_repro(spec):
    line = (f"python -m clocktower fuzz repro --seed {spec['seed']} --players {spec['players']} "
            f"--judge {spec['mode']} --chars {ids(spec['chars'])}")
    if spec.get('setup'):
        line += f" --setup {ids(spec['setup'])}"
    return line


def _alarm(signum, frame):
    raise TimeoutError(f'game over {TIME_CAP}s')


TRACE = ('setup', 'death', 'becomes', 'alignment', 'gains', 'execution', 'night_choice', 'st_choice', 'info', 'slayer',
         'virgin', 'ability', 'game_over')


def play(spec, directives=None, decide=None, trace=None):
    """Play one game of `spec` ({seed, players, mode, chars, setup?}): its summary, violations and coverage. A crash,
    a loop or a timeout is a violation too."""
    script = make_script(spec['chars'])
    players, seed = spec['players'], spec['seed']
    names = ALL_NAMES[:players]
    rng = random.Random(seed + 1)
    seats = {n: RandomSeat(n, random.Random(rng.random()), names) for n in names}
    if directives:
        seats = {n: DirectedSeat(s, directives) for n, s in seats.items()}
    cls = FuzzGame if decide is None else type('ScenarioGame', (FuzzGame,), {'decide_judged': decide})
    game = cls(seats, None, names=names, seed=seed, minion=script.minions[seed % len(script.minions)],
               probes=False, script=script, judge=judges.make(spec['mode']), characters=spec.get('setup'))
    if directives is not None:
        directives.game = game
    out = {'spec': spec, 'winner': None, 'reason': None, 'days': 0}
    use_alarm = hasattr(signal, 'SIGALRM') and multiprocessing.current_process().name != 'MainProcess' or \
        os.environ.get('CLOCKTOWER_FUZZ_ALARM')
    if use_alarm:
        signal.signal(signal.SIGALRM, _alarm)
        signal.alarm(TIME_CAP)
    try:
        result = asyncio.run(game.run())
        out.update(winner=result['winner'], reason=result['reason'], days=result['days'])
        game.fz.step('end')
    except StepCap as e:
        game.fz.flag('loop', str(e), game.fz.context_chars() if game.g else spec['chars'])
    except TimeoutError as e:
        game.fz.flag('timeout', str(e), game.fz.context_chars() if game.g else spec['chars'])
    except Exception as e:
        tb = traceback.format_exc()
        if game.g is None and isinstance(e, ValueError) and 'sample' in str(e).lower():
            game.fz.flag('setup', f'{type(e).__name__}: {e}', spec['chars'], advisory=True)
        else:
            game.fz.flag('crash', f'{type(e).__name__}: {e}\n{tb[-1500:]}',
                         game.fz.context_chars() if game.g else spec['chars'])
    finally:
        if use_alarm:
            signal.alarm(0)
    m = game.fz
    acted = set(m.acted) & m.in_play
    if game.g is not None:
        acted |= m.passive_in_play()
    out.update(violations=m.violations, advisories=m.advisories, checked=dict(m.checked),
               in_play=sorted(m.in_play & set(CHARACTERS)),
               acted=sorted(acted & set(CHARACTERS)), repro=spec_repro(spec))
    if directives is not None:
        out['notes'] = directives.summary(game)
    if trace is not None:  # the game's audit trail, for a repro
        for ev in game.events:
            if ev['kind'] in TRACE:
                who = ev['to'] if isinstance(ev['to'], str) else ev['to'][0]
                to = '' if ev['to'] == 'public' else f' ({who})'
                trace.append(f"day {ev['day']} {ev['phase']}: {ev['kind']}{to} {json.dumps(ev['data'])[:400]}")
    return out


# ---- many games ---------------------------------------------------------------------------------------------------

def pair_key(a, b):
    return '|'.join(sorted((a, b)))


def all_pairs():
    names = sorted(c for k in TYPES for c in pool()[k])
    return [pair_key(a, b) for a, b in combinations(names, 2)]


def make_specs(start, count, rng_seed, modes, sizes, bias=None, force=(), coverage=None, target=False):
    """`count` game specs from seed `start`. bias 'rare': characters weighted by how rarely they have been in play
    (coverage); `target`: each game puts the pair least often seen both acting onto the script and into play."""
    specs = []
    weights = None
    pair_counts = Counter((coverage or {}).get('acted', {}))
    char_counts = Counter((coverage or {}).get('characters', {}))
    if bias == 'rare':
        weights = {c: 1.0 / (1 + char_counts.get(c, 0)) ** 0.5 for k in TYPES for c in pool()[k]}
    ranked = None
    if target:
        ranked = sorted(all_pairs(), key=lambda k: (pair_counts.get(k, 0), k))
    for i in range(count):
        seed = start + i
        r = random.Random(seed * 7919 + rng_seed)
        forced = list(force)
        if ranked:
            low = pair_counts.get(ranked[0], 0)
            lowest = [k for k in ranked[:400] if pair_counts.get(k, 0) <= low + 1]
            pick = r.choice(lowest)
            forced += [c for c in pick.split('|') if c not in forced]
            pair_counts[pick] += 1  # spread the next games over other pairs
        chars = random_script(r, weights=weights, force=forced)
        players = r.choice(list(sizes))
        spec = {'seed': seed, 'players': players, 'mode': modes[i % len(modes)], 'chars': chars}
        if forced:
            script = make_script(chars)
            setup = setup_with(script, forced, r, None)
            if setup:
                spec['players'], spec['setup'] = len(setup), setup
        specs.append(spec)
    return specs


def _work(spec):
    return play(spec)


class Tally:
    """What a run found: violations by type, coverage, and games."""

    def __init__(self, coverage=None):
        coverage = coverage or {}
        self.games = coverage.get('games', 0)
        self.chars = Counter(coverage.get('characters', {}))
        self.chars_acted = Counter(coverage.get('characters_acted', {}))
        self.in_play = Counter(coverage.get('in_play', {}))
        self.both_acted = Counter(coverage.get('acted', {}))
        self.violations = Counter()
        self.advisories = Counter()
        self.advisory_chars = {}
        self.winners = Counter()
        self.reasons = Counter()
        self.checked = Counter(coverage.get('checked', {}))
        self.first = {}  # (type, signature) -> an example
        self.examples = Counter()

    def add(self, out, log=None):
        self.games += 1
        self.winners[out['winner']] += 1
        self.checked.update(out.get('checked', {}))
        self.reasons[re.sub(r'\b[A-Z][a-z]+\b(?=,| was| the| chose)', 'X', str(out['reason']))[:80]] += 1
        for c in out['in_play']:
            self.chars[c] += 1
        for c in out['acted']:
            self.chars_acted[c] += 1
        for a, b in combinations(out['in_play'], 2):
            self.in_play[pair_key(a, b)] += 1
        for a, b in combinations(out['acted'], 2):
            self.both_acted[pair_key(a, b)] += 1
        for v in out['violations']:
            self.violations[v['type']] += 1
            sig = (v['type'], signature(v))
            self.examples[sig] += 1
            if sig not in self.first:
                self.first[sig] = {**v, 'repro': out['repro'], 'seed': out['spec']['seed'],
                                   'script': ids(out['spec']['chars'])}
            if log:
                log.write(json.dumps({**v, 'repro': out['repro']}) + '\n')
        for a in out['advisories']:
            key = (a['type'], a['detail'])
            self.advisories[key] += 1  # with the characters every such game had
            self.advisory_chars[key] = self.advisory_chars.get(key, set(a['characters'])) & set(a['characters'])

    def coverage(self):
        return {'games': self.games, 'characters': dict(self.chars), 'characters_acted': dict(self.chars_acted),
                'in_play': dict(self.in_play), 'acted': dict(self.both_acted), 'checked': dict(self.checked)}


def signature(v):
    """A violation's kind, without player names and numbers, for grouping."""
    d = v['detail'].split('\n')[0]
    d = re.sub(r'\b(' + '|'.join(ALL_NAMES) + r')\b', 'P', d)
    d = re.sub(r'\d+', 'N', d)
    d = re.sub(r'\{.*?\}', '{...}', d)
    if v['type'] == 'oracle':  # what was shown, and who was who, vary: the role and the reason's shape group them
        names = sorted(CHARACTERS, key=len, reverse=True)
        head, _, rest = d.partition(')')
        d = head + ')' + re.sub(r'\b(' + '|'.join(re.escape(c) for c in names) + r')\b', 'C', rest)
    return d[:160]


def run(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    coverage = json.loads(Path(args.coverage).read_text()) if args.coverage and Path(args.coverage).exists() else None
    tally = Tally(coverage if args.coverage else None)
    modes = args.judge.split(',')
    sizes = sizes_of(args.sizes)
    force = names_of(args.force) if args.force else ()
    start = time.time()
    seed, left = args.seed, args.games
    log = (out / 'violations.jsonl').open('w')
    chunk = 400 if args.target_uncovered or args.bias == 'rare' else args.games
    with multiprocessing.Pool(args.workers) as pool_:
        while left > 0:
            n = min(chunk, left)
            specs = make_specs(seed, n, args.seed, modes, sizes, args.bias, force, tally.coverage(),
                               args.target_uncovered)
            for i, res in enumerate(pool_.imap_unordered(_work, specs, chunksize=4), 1):
                tally.add(res, log)
                if tally.games % 1000 == 0:
                    print(f'{tally.games} games, {sum(tally.violations.values())} violations, '
                          f'{time.time() - start:.0f}s', file=sys.stderr)
            seed += n
            left -= n
    log.close()
    (out / 'coverage.json').write_text(json.dumps(tally.coverage()))
    (out / 'summary.md').write_text(summary(tally, time.time() - start, args))
    print(summary(tally, time.time() - start, args, short=True))
    return 0


def summary(t, seconds, args=None, short=False):
    pairs = all_pairs()
    covered = [k for k in pairs if t.in_play.get(k)]
    acted = [k for k in pairs if t.both_acted.get(k)]
    lines = [f'# Fuzz run: {t.games} games in {seconds:.0f}s', '']
    if args is not None:
        lines += [f'Arguments: {" ".join(sys.argv[1:])}', '']
    lines += ['## Violations by type', ''] + [f'- {k}: {n}' for k, n in t.violations.most_common()] or ['- none']
    lines += ['', f'Winners: {dict(t.winners)}', '',
              f'## Pair coverage ({len(pairs)} pairs of {len(t.chars)} characters seen)', '',
              f'- both in play in some game: {len(covered)} ({100 * len(covered) / len(pairs):.1f}%)',
              f'- both in play and both acted: {len(acted)} ({100 * len(acted) / len(pairs):.1f}%)', '']
    if short:
        return '\n'.join(lines)
    lines += ['## Distinct violations (first example of each)', '']
    for (type_, sig), n in sorted(t.examples.items(), key=lambda kv: (kv[0][0], -kv[1])):
        ex = t.first[(type_, sig)]
        lines += [f'### {type_} x{n}: {sig}', '', f'- characters: {", ".join(ex["characters"])}',
                  f'- where: day {ex["day"]}, {ex["phase"]}, {ex["step"]}', f'- detail: {ex["detail"][:600]}',
                  f'- repro: `{ex["repro"]}`', '']
    lines += ['## Advisories', ''] + [f'- {a[0]}: {a[1]} (always with: {", ".join(sorted(t.advisory_chars[a]))}) x{n}'
                                      for a, n in t.advisories.most_common(60)]
    ranked = sorted(pairs, key=lambda k: t.in_play.get(k, 0))
    lines += ['', '## Least-covered pairs (in play together)', '']
    lines += [f'- {k}: {t.in_play.get(k, 0)} (both acted {t.both_acted.get(k, 0)})' for k in ranked[:60]]
    lines += ['', '## Most-covered pairs', ''] + [f'- {k}: {t.in_play.get(k, 0)}' for k in ranked[::-1][:20]]
    never = [k for k in pairs if not t.in_play.get(k)]
    lines += ['', f'## Never in play together ({len(never)})', '', ', '.join(never) or 'none']
    never_acted = [k for k in pairs if t.in_play.get(k) and not t.both_acted.get(k)]
    lines += ['', f'## In play together but never both acted ({len(never_acted)})', '',
              ', '.join(never_acted) or 'none']
    lines += ['', '## Characters (games in play, games acted)', '']
    lines += [f'- {c}: {t.chars[c]}, {t.chars_acted.get(c, 0)}' for c in sorted(t.chars, key=lambda c: t.chars[c])]
    lines += ['', '## Information checked for healthy players (engine: its own truth test; oracle: the independent '
              'one)', '']
    lines += [f'- {k}: {n}' for k, n in sorted(t.checked.items())]
    lines += ['', '## End reasons', ''] + [f'- {r}: {n}' for r, n in t.reasons.most_common(40)]
    return '\n'.join(lines) + '\n'


# ---- the mechanism matrix -----------------------------------------------------------------------------------------

class DirectedSeat:
    """A random bot whose night choices follow `directives` ({role: callable(game, request) -> action or None}), so
    a scenario's mechanism is aimed at the character under test."""

    def __init__(self, seat, directives):
        self.seat, self.directives, self.name = seat, directives, seat.name

    async def act(self, text_, request):
        reply = await self.seat.act(text_, request)
        m = re.match(r'Night \d+ — (?:the )?([A-Z][\w\' -]+?)(?: has died)?[:.]', request.prompt)
        if request.kind == 'night' and m:
            action = self.directives.night(m.group(1), self.name, request)
            if action is not None:
                reply.action = {**(reply.action or {}), **action}
        return reply


class Directives:
    """A scenario's aim: who the mechanism's characters choose, and what the matrix records."""

    def __init__(self, subject, mechanism, rng):
        self.subject, self.mechanism, self.rng, self.game = subject, mechanism, rng, None

    def holder(self):
        g = self.game.g
        return next((p for p in g.players if p.character == self.subject or self.subject in g.abilities(p)), None) \
            or next((p for p in g.players if p.shown == self.subject), None)

    def night(self, role, me, request):
        g = self.game.g
        x = self.holder()
        if g is None or x is None:
            return None
        aim = x.name if x.name in request.options else None
        others = [o for o in request.options if o != x.name]
        if role in ('Poisoner', 'Monk', 'Innkeeper', 'Cerenovus', 'Pit-Hag', 'Professor', 'Snake Charmer', 'Sailor',
                    'Witch', 'Devil\'s Advocate', 'Exorcist', 'Butler', 'Dreamer', 'Fortune Teller', 'Courtier'):
            if role == 'Courtier':
                return {'character': self.subject} if self.subject in request.characters else None
            if role == 'Snake Charmer':
                d = next((p.name for p in g.players if p.is_demon and p.name in request.options), None)
                return {'targets': [d]} if d else None
            if role == 'Pit-Hag':
                out = [c for c in request.characters if c not in {p.character for p in g.players}
                       and kind(c) == kind(self.subject)]
                return {'targets': [aim], 'character': self.rng.choice(out)} if aim and out else None
            if role == 'Cerenovus':
                good = [c for c in request.characters if c != self.subject]
                return {'targets': [aim], 'character': self.rng.choice(good)} if aim and good else None
            if aim is None:
                return None
            k = request.n_targets
            return {'targets': [aim] + self.rng.sample(others, min(k - 1, len(others)))}
        if role == 'Barber':
            return {'targets': [x.name, self.rng.choice(others)]} if x.name in request.options and others else None
        if self.mechanism in ('revival', 'monk', 'soldier', 'tea lady', 'innkeeper') and role in CHARACTERS \
                and kind(role) == 'Demon' and aim and x is not g[me]:
            return {'targets': [aim] + self.rng.sample(others, min(request.n_targets - 1, len(others)))}
        return None

    def summary(self, game):
        g = game.g
        if g is None:
            return {}
        x = next((p for p in g.players if game.starting and game.starting.get(p.name) == self.subject), None)
        x = x or self.holder()
        if x is None:
            return {'absent': True}
        ab = [a for a in g.abnormal if a['player'] == x.name]
        deaths = [d['cause'] for d in g.death_log if d['player'] == x.name]
        revived = any(r['player'] == x.name for r in g.revivals)
        became = x.character if x.character not in (self.subject, 'Drunk') else None
        tea = any(q.character == 'Tea Lady' and x in g.neighbours(q) for q in g.players)
        touched = game.fz.touched.get(x.name, set())
        kinds = {k for k, _ in touched}
        sources = {c for _, c in touched}
        start_team = (game.start_teams or {}).get(x.name)
        hit = {'drunk': 'drunk' in kinds or (x.character == 'Drunk' and x.shown == self.subject),
               'poisoned': 'poisoned' in kinds, 'misregistration': True,
               'monk': ('safe', 'Monk') in touched, 'soldier': True, 'tea lady': tea,
               'innkeeper': 'Innkeeper' in sources, 'pit-hag': bool(became), 'barber': bool(became),
               'snake charmer': bool(became) or 'Snake Charmer' in sources,
               'alignment': start_team is not None and x.alignment != start_team,
               'madness': 'mad' in kinds, 'revival': revived}[self.mechanism]
        return {'died': deaths, 'became': became, 'alignment': x.alignment, 'revived': revived,
                'abnormal': len(ab), 'alive': x.alive, 'hit': hit}


# mechanism -> (characters put into play beside the subject, how)
MECHANISMS = {
    'drunk': ['Drunk'],            # the Drunk believing the subject (a Townsfolk); else the Courtier choosing it
    'poisoned': ['Poisoner'],
    'misregistration': ['Spy', 'Recluse'],
    'monk': ['Monk'], 'soldier': ['Soldier'], 'tea lady': ['Tea Lady'], 'innkeeper': ['Innkeeper'],
    'pit-hag': ['Pit-Hag'], 'barber': ['Barber'], 'snake charmer': ['Snake Charmer'],
    'alignment': ['Snake Charmer', 'Goon'],
    'madness': ['Cerenovus'],
    'revival': ['Professor', 'Shabaloth'],
}


def scenario(subject, mechanism, seed, mode):
    """A spec for one game: the subject and the mechanism's characters in play, on a random script holding them."""
    r = random.Random(seed)
    extra = list(MECHANISMS[mechanism])
    if mechanism == 'drunk' and kind(subject) != 'Townsfolk':
        extra = ['Courtier']
    if subject in extra:
        extra.remove(subject)
    on_script = [subject, *extra]
    chars = random_script(r, force=on_script)
    script = make_script(chars)
    in_play = [c for c in extra if not (mechanism == 'drunk' and c == 'Drunk')]
    if mechanism == 'drunk' and kind(subject) == 'Townsfolk':
        in_play.append('Drunk')
    else:
        in_play.insert(0, subject)
    if kind(subject) == 'Demon':  # the subject is the Demon: a Demon-based mechanism gives way
        in_play = [c for c in in_play if kind(c) != 'Demon' or c == subject]
        in_play.remove(subject)
        in_play.insert(0, subject)
    setup = setup_with(script, in_play, r, None)
    if setup is None:
        return None
    if mechanism == 'tea lady' and subject != 'Tea Lady' and subject in setup and 'Tea Lady' in setup:
        setup.remove('Tea Lady')  # seated beside the subject
        setup.insert((setup.index(subject) + 1) % (len(setup) + 1), 'Tea Lady')
    return {'seed': seed, 'players': len(setup), 'mode': mode, 'chars': chars, 'setup': setup}


def _drunk_as(subject):
    async def decide(self, choice):
        if choice.id == 'drunk_as':
            for v in choice.values:
                if v['character'] == subject:
                    self.fz.decided(choice, v)
                    return v
        return await FuzzGame.decide_judged(self, choice)
    return decide


def _matrix_cell(job, trace=None):
    subject, mechanism, seed, mode = job
    try:
        spec = scenario(subject, mechanism, seed, mode)
    except Exception:  # a scenario that can't be built is the matrix's own bug: show it in the cell, don't stop
        return job, {'violations': [{'type': 'scenario', 'detail': traceback.format_exc()[-300:]}], 'notes': {},
                     'repro': f'fuzz.scenario({subject!r}, {mechanism!r}, {seed}, {mode!r})'}
    if spec is None:
        return job, None
    d = Directives(subject, mechanism, random.Random(seed))
    decide = _drunk_as(subject) if mechanism == 'drunk' and kind(subject) == 'Townsfolk' else None
    out = play(spec, d, decide, trace)
    out['repro'] = (f'python -m clocktower fuzz cell --subject {official.ids()[subject]} --mechanism "{mechanism}" '
                    f'--seed {seed} --judge {mode}')
    return job, out


def cell(args):
    """One game of the mechanism matrix again (its repro line)."""
    trace = [] if args.events else None
    _, res = _matrix_cell((names_of(args.subject)[0], args.mechanism, args.seed, args.judge), trace)
    if res is None:
        print('no legal setup holds the character and the mechanism')
        return 0
    for line in trace or ():
        print(line)
    print(f"notes: {res.get('notes')}")
    for v in res['violations']:
        print(f"{v['type']}: day {v.get('day')} {v.get('phase')} ({v.get('step')}): {v['detail']}")
    return 1 if res['violations'] else 0


def matrix(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    subjects = sorted(c for k in TYPES for c in pool()[k])
    if args.only:
        subjects = names_of(args.only)
    jobs = [(s, m, args.seed + 1000 * i + j, 'rules' if j % 2 else 'scripted')
            for i, (s, m) in enumerate((s, m) for s in subjects for m in MECHANISMS) for j in range(args.seeds)]
    cells = {}
    with multiprocessing.Pool(args.workers) as pool_:
        for (s, m, seed, mode), res in pool_.imap_unordered(_matrix_cell, jobs, chunksize=2):
            cells.setdefault((s, m), []).append((seed, res))
    rows, bad = [], []
    for s in subjects:
        cols = []
        for m in MECHANISMS:
            runs = cells.get((s, m), [])
            played = [r for _, r in runs if r is not None]
            if not played:
                cols.append('n/a')
                continue
            viol = Counter(v['type'] for r in played for v in r['violations'])
            notes = Counter()
            for r in played:
                n = r.get('notes') or {}
                if n.get('absent'):
                    notes['gone'] += 1
                if n.get('died'):
                    notes['died:' + n['died'][0]] += 1
                if n.get('became'):
                    notes['became ' + n['became']] += 1
                if n.get('revived'):
                    notes['revived'] += 1
                if n.get('abnormal'):
                    notes['abnormal'] += 1
            hits = sum(1 for r in played if (r.get('notes') or {}).get('hit'))
            cell = (f'{len(played)} ok' if not viol else ', '.join(f'{k} {n}' for k, n in viol.items()))
            cell += f' (hit {hits}/{len(played)})'
            if notes:
                cell += '; ' + ', '.join(f'{k}{"" if n == 1 else " x" + str(n)}' for k, n in notes.most_common(3))
            cols.append(cell)
            for r in played:
                for v in r['violations']:
                    bad.append(f'- {s} x {m}: {v["type"]}: {v["detail"].splitlines()[0][:300]} '
                               f'(`{r["repro"]}`)')
        rows.append(f'| {s} | ' + ' | '.join(cols) + ' |')
    head = ['# Mechanism matrix', '',
            f'Each cell: {args.seeds} short forced games (scripted and rules judge alternating) with the character and '
            'the mechanism in play, the mechanism aimed at the character (clocktower/fuzz.py, Directives). "N ok": no '
            'crash and no violation; then what happened to the character most often (died by cause, became another '
            'character, revived, an abnormal result recorded). n/a: no legal setup holds both.', '',
            '"hit k/N": in k of the N games the mechanism reached the character (it was drunk, poisoned, protected, '
            'changed, turned, mad or revived; for misregistration and the Soldier, both were in play).', '',
            '| character | ' + ' | '.join(MECHANISMS) + ' |', '|' + '---|' * (len(MECHANISMS) + 1)]
    (out / 'matrix.md').write_text('\n'.join(head + rows + ['', '## Violations', ''] + (bad or ['none'])) + '\n')
    print(f'{len(jobs)} games; {len(bad)} violations; matrix in {out / "matrix.md"}')
    return 0


# ---- the command line -----------------------------------------------------------------------------------------------

def sizes_of(spec):
    a, _, b = spec.partition('-')
    return range(int(a), int(b or a) + 1)


def repro(args):
    spec = {'seed': args.seed, 'players': args.players, 'mode': args.judge, 'chars': names_of(args.chars)}
    if args.setup:
        spec['setup'] = names_of(args.setup)
        spec['players'] = len(spec['setup'])
    os.environ.setdefault('CLOCKTOWER_FUZZ_ALARM', '1')
    trace = [] if args.events else None
    res = play(spec, trace=trace)
    for line in trace or ():
        print(line)
    print(f"winner {res['winner']} ({res['reason']}), day {res['days']}")
    for v in res['violations']:
        print(f"{v['type']}: day {v['day']} {v['phase']} ({v['step']}): {v['detail']}")
    print(f"{len(res['violations'])} violations")
    return 1 if res['violations'] else 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog='clocktower fuzz', description=__doc__.split('\n\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run', help='random scripts, random-bot games, invariants')
    r.add_argument('--games', type=int, default=1000)
    r.add_argument('--workers', type=int, default=os.cpu_count() or 2)
    r.add_argument('--seed', type=int, default=SEED_BASE)
    r.add_argument('--sizes', default='5-15')
    r.add_argument('--judge', default='scripted,rules', help='Storyteller modes, alternating')
    r.add_argument('--bias', choices=['rare'], help='favour characters rarely in play so far (with --coverage)')
    r.add_argument('--force', help='official ids always on the script and in play, comma-separated')
    r.add_argument('--target-uncovered', action='store_true', help='each game holds a least-covered pair')
    r.add_argument('--coverage', help='a coverage.json to start from (and bias by)')
    r.add_argument('--out', required=True)
    p = sub.add_parser('repro', help='replay one game and print its violations')
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--players', type=int, required=True)
    p.add_argument('--judge', default='scripted')
    p.add_argument('--chars', required=True, help='the script: official ids, comma-separated')
    p.add_argument('--setup', help='a forced setup in seat order: official ids')
    p.add_argument('--events', action='store_true', help='print the audit trail (setup, choices, deaths, changes)')
    m = sub.add_parser('matrix', help='each character against each shared mechanism')
    m.add_argument('--seeds', type=int, default=4, help='games per cell')
    m.add_argument('--seed', type=int, default=SEED_BASE + 500_000)
    m.add_argument('--workers', type=int, default=os.cpu_count() or 2)
    m.add_argument('--only', help='only these characters (official ids)')
    m.add_argument('--out', required=True)
    c = sub.add_parser('cell', help='replay one game of the mechanism matrix (its repro line)')
    c.add_argument('--subject', required=True, help='the character (official id)')
    c.add_argument('--mechanism', required=True, choices=list(MECHANISMS))
    c.add_argument('--seed', type=int, required=True)
    c.add_argument('--judge', default='scripted')
    c.add_argument('--events', action='store_true', help='print the audit trail')
    args = ap.parse_args(argv)
    return {'run': run, 'repro': repro, 'matrix': matrix, 'cell': cell}[args.cmd](args)


if __name__ == '__main__':
    sys.exit(main())
