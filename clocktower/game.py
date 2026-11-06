"""The table: setup, nights, beats, nominations and votes.

A day has two parts, each a series of beats: private time (whispers only; nobody
else sees them, or that they happened) and then the town square (public talk only).
In a beat every seat gets one turn, in a random order, a wave of a few seats at a
time: a wave acts in parallel and later waves see what earlier ones said. Then
nominations: each round, living players who have not nominated may nominate (or
just speak); one nomination is taken, the nominee defends, and votes go clockwise
one at a time with a running tally.
"""
from __future__ import annotations
import asyncio
import json
import pickle
import math
import random
import re
import time
from pathlib import Path

from .agents import Request, ScriptedStoryteller
from .characters import ALL, TB, card, is_evil_character, kind, rules
from .llm import BudgetExceeded, SeatFailed


class Halted(RuntimeError):
    """An operator asked this one game to stop (a STOP file in its folder); it resumes from its checkpoint."""
from . import probe
from .prompts import dawn_narration
from .render import render
from .state import Grimoire, bluffs_choice, info_text, norm, random_setup, setup_error
ALL_NAMES = ['Alex', 'Blair', 'Casey', 'Drew', 'Ellis', 'Frankie', 'Gray', 'Harper', 'Indigo', 'Jules', 'Kit',
             'Logan', 'Morgan', 'Noel', 'Oakley']
NAMES = ALL_NAMES[:9]  # the default nine-player table
WHISPERS = 1  # per private-time turn (v14; v7-v13 had 2): one conversation at a time
WORDS = {'beat': 150, 'whisper': 150, 'nominate': 150, 'defense': 200, 'comment': 150, 'vote': 60}
# role: (number of targets, prompt, may choose self), for the characters that choose at night
NIGHT_ACTIONS = {c: rules(c).night_choice for c in ALL if rules(c).night_choice}


class Night:
    """One night: who chose what, and who died. Each character's step reads and adds to it."""

    def __init__(self, n):
        self.n, self.first = n, n == 1
        self.chosen = {}  # player name -> the players they chose tonight
        self.deaths = []

    def choice_of(self, g, character):
        """(The living player who really is `character`, their first choice tonight or None)."""
        p = g.with_character(character)
        return (p, self.chosen[p.name][0]) if p and p.name in self.chosen else (p, None)

    @staticmethod
    def steps(first, script=TB):
        """Tonight's night order in batches. Choices are asked a batch at a time, and a batch ends after each
        step that can kill, so a player killed tonight is never woken to choose (the Fortune Teller and Butler
        choose after the Demon's kill). Night 1 has no kill: one batch."""
        batches, batch = [], []
        for c in (script.first_night if first else script.other_nights):
            batch.append(c)
            if rules(c).kills_at_night:
                batches.append(batch)
                batch = []
        return batches + [batch] if batch else batches


# Every seat's text reaches the others in one typography, so a model's style (curly quotes, dash and
# hyphen variants, bullets, arrows, emoji, markdown) can't mark which team a seat is on when the two
# teams are different models.
TYPOGRAPHY = str.maketrans({'\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"', '\u2014': ' - ',
                            '\u2013': ' - ', '\u2026': '...', '\u2010': '-', '\u2011': '-', '\u2012': '-',
                            '\u2212': '-', '\u00a0': ' ', '\u202f': ' ', '\u2022': '-', '\u00b7': '-', '\u25e6': '-',
                            '\u2023': '-', '\u2192': '->', '\u2190': '<-', '\u21d2': '=>', '\u2194': '<->',
                            '*': None, '`': None, '#': None})
EMOJI = re.compile('[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]')


def plain(text):
    return ' '.join(EMOJI.sub('', (text or '').translate(TYPOGRAPHY)).split())


def clip(text, words):
    text = plain(text)
    w = text.split(' ')
    return text if len(w) <= words else ' '.join(w[:words]) + '...'  # the same for every model


def fmt(value):
    return {k: v for k, v in norm(value).items() if v not in (None, [])}


class Game:
    def __init__(self, seats, storyteller=None, *, names=NAMES, seed=None, private_beats=6, public_beats=3, max_days=10,
                 waves=3, characters=None, minion=None, out=None, seat_factory=None, probes=True, script=TB):
        """`seats` maps names to seats; alternatively `seat_factory(name, team)` creates them once the
        characters are dealt (so, for example, the evil team can use a different model). `probes` asks
        seats that support it for their beliefs at dawn of day 1 and before each day's nominations,
        outside the game (probe.py). Every day has
        `private_beats` of private time and `public_beats` of town square. `minion` forces the Minion
        character of a random setup (batches rotate it so every Minion is covered). The Storyteller
        defaults to the scripted one (state.POLICY). `script` is the characters.Script played (Trouble Brewing by
        default)."""
        self.seats, self.names, self.seat_factory, self.script = seats, list(names), seat_factory, script
        self.meta = {}
        self.seed = seed if seed is not None else random.randrange(2 ** 32)
        self.rng = random.Random(self.seed)
        self.st = storyteller or ScriptedStoryteller(random.Random(self.seed ^ 0x5eed))
        self.private_beats, self.public_beats, self.minion = private_beats, public_beats, minion
        self.max_days, self.waves, self.forced = max_days, waves, characters
        self.out = Path(out) if out else None
        if self.out:
            self.out.mkdir(parents=True, exist_ok=True)
        self.g: Grimoire | None = None
        self.day, self.phase = 0, 'setup'
        self.events, self.calls, self.errors = [], [], []
        self.buf = {n: [] for n in self.names}
        self.executed_today = False
        self.starting = None        # {seat: dealt character}
        self.start_teams = None     # {seat: 'good' or 'evil'} as dealt: which team's model plays the seat, all game
        self.probes, self.probe_tasks, self.probe_log = probes, [], []

    # ---- logging -----------------------------------------------------------------------
    def _write(self, filename, line):
        if self.out:
            with (self.out / filename).open('a') as f:
                f.write(line + '\n')

    def emit(self, kind, data, to='public'):
        dead = {p.name for p in self.g.players if not p.alive} if self.g else set()
        ev = {'seq': len(self.events), 'time': round(time.time(), 2), 'day': self.day, 'phase': self.phase,
              'kind': kind, 'data': data, 'to': to, 'dead': sorted(dead)}
        self.events.append(ev)
        for n in self.names:
            text = render(ev, n, dead)
            if text is not None:
                self.buf[n].append(text)
        self._write('events.jsonl', json.dumps(ev))
        self._write('transcript.md', render(ev, 'omniscient', dead))

    def record_call(self, record):
        self.calls.append(record)
        self._write('calls.jsonl', json.dumps(record))

    # ---- belief probes (outside the game) ---------------------------------------------------------
    def probe(self, point):
        """Fork a belief question to every seat that supports it. Runs in the background on a snapshot
        (the seat's conversation and its pending events, which stay pending), so play never waits."""
        if not self.probes:
            return
        for p in self.g.players:
            seat = self.seats.get(p.name)
            if not hasattr(seat, 'probe'):
                continue
            pending = '\n'.join(self.buf[p.name]).strip()
            text = (pending + '\n\n' if pending else '') + '>>> ' + probe.prompt(p.evil)
            meta = {'day': self.day, 'point': point}
            record = {**meta, 'player': p.name, 'character': p.character, 'shown': p.shown,
                      'team': 'evil' if p.evil else 'good', 'alive': p.alive,
                      'truth': {q.name: {'character': q.character, 'evil': q.evil} for q in self.g.players}}
            self.probe_tasks.append(asyncio.create_task(self._probe(seat, text, meta, record)))

    async def _probe(self, seat, text, meta, record):
        try:
            reply = await seat.probe(text, meta)
        except Exception as e:  # a failed probe never touches the game
            record.update(error=repr(e))
        else:
            say = (reply.action or {}).get('say') or ''
            record.update(raw=say, thinking=reply.thinking, **probe.parse(say, self.names))
        self.probe_log.append(record)
        self._write('probes.jsonl', json.dumps(record))

    # ---- asking seats and the Storyteller ------------------------------------------------------
    async def ask(self, name, request: Request) -> dict:
        if self.out and (self.out / self.STOP).exists():  # an operator halts this one game; it resumes later
            raise Halted(f'{self.STOP} file in {self.out}')
        text = '\n'.join(self.buf[name]).strip()
        self.buf[name] = []
        text = (text + '\n\n' if text else '') + '>>> ' + request.prompt
        try:
            reply = await self.seats[name].act(text, request)
        except BudgetExceeded:
            raise
        except Exception as e:  # after the client's own retries: stop the game, never play on without a seat
            self.errors.append(f'{name}: {e!r}')
            self.emit('text', {'text': f'[error] {name}: {e!r}'}, 'audit')
            raise SeatFailed(f'{name}: {e!r}') from e
        if reply.thinking:
            self.emit('thinking', {'player': name, 'kind': request.kind, 'text': reply.thinking}, 'audit')
        return reply.action or {}

    async def ask_many(self, requests: dict) -> dict:
        names = list(requests)
        results = await asyncio.gather(*(self.ask(n, requests[n]) for n in names))
        return dict(zip(names, results))

    def decide(self, choice):
        """The Storyteller's value for a Choice. Choices with one legal value need no decision."""
        if choice.auto:
            return choice.values[0]
        value = norm(self.st.choose(choice))
        if not choice.legal(value):
            raise ValueError(f'illegal Storyteller value for {choice.id}: {value}')
        self.emit('st_choice', {'id': choice.id, 'value': fmt(value), 'valid': True}, 'audit')
        return value

    # ---- setup -------------------------------------------------------------------------------
    async def setup(self):
        names, seating = self.names, ', '.join(self.names)
        if self.forced:
            chars = list(self.forced)  # a forced setup (tests, --characters) keeps its seating order
        else:
            chars = random_setup(self.rng, self.minion, len(names), self.script)
            self.rng.shuffle(chars)
        err = setup_error(chars, self.script)
        if err:
            raise ValueError(err)
        self.g = g = Grimoire(names, chars, script=self.script)

        in_play = set(chars)
        # the characters' own setup (the Drunk's apparent character, then the red herring), for a character someone
        # has or believes they have (a Drunk-as-Fortune-Teller needs a red herring too)
        for c in self.script.setup_steps:
            if c.name in {p.character for p in g.players} | {p.shown for p in g.players}:
                c.setup(self)
        drunk = next((p for p in g.players if rules(p.character).always_drunk), None)
        g.bluffs = self.decide(bluffs_choice([c for c in self.script.good if c not in in_play], drunk is not None,
                                             drunk.shown if drunk else None))['characters']
        self.starting = {p.name: p.character for p in g.players}
        self.start_teams = {p.name: p.alignment for p in g.players}
        if self.seat_factory:
            self.seats = {p.name: self.seat_factory(p.name, 'evil' if p.evil else 'good') for p in g.players}
        self.emit('setup', {'seats': [{'name': p.name, 'character': p.character, 'shown': p.shown} for p in g.players],
                            'red_herring': g.red_herring, 'bluffs': g.bluffs}, 'audit')

        for p in g.players:
            left, right = names[(p.seat - 1) % len(names)], names[(p.seat + 1) % len(names)]
            lines = [f'You are {p.name}. The players, clockwise: {seating} (and back to {names[0]}). '
                     f'You sit between {left} and {right}.',
                     f'Your character: {card(p.shown)}']
            minions = [q.name for q in g.players if kind(q.character) == 'Minion']
            if p.is_demon:  # Demon info and Minion info
                lines.append(f'Your Minion{"" if len(minions) == 1 else "s"}: {", ".join(minions)} (you do not know '
                             f'which Minion characters). Three good characters not in play, for evil to bluff: '
                             f'{", ".join(g.bluffs)}.')
            elif kind(p.character) == 'Minion':
                others = [m for m in minions if m != p.name]
                lines.append(f'The Demon is {g.demon().name}.'
                             + (f' Your fellow Minion{"" if len(others) == 1 else "s"}: {", ".join(others)} (you do not '
                                'know which Minion characters).' if others else ''))
            self.emit('intro', {'text': '\n'.join(lines)}, [p.name])

    # ---- night -------------------------------------------------------------------------------
    def targets(self, name, action, request):
        chosen = [x for x in dict.fromkeys(action.get('targets') or []) if x in request.options][:request.n_targets]
        if len(chosen) < request.n_targets:
            chosen += self.rng.sample([x for x in request.options if x not in chosen], request.n_targets - len(chosen))
            self.emit('notice', {'text': f'(Your choice was incomplete, so the Storyteller chose for you: '
                                         f'{", ".join(chosen)}.)'}, [name])
        return chosen

    def kill(self, p, cause):
        """The one way anyone dies (Demon, execution, Slayer, starpass). Characters react through on_death (the
        Scarlet Woman takes over a dead Demon); abilities that last only while their source lives end."""
        g = self.g
        before = g.alive_count()
        g.die(p)
        self.emit('death', {'player': p.name, 'cause': cause}, 'audit')
        for q in g.players:
            rules(q.character).on_death(self, q, p, cause, before)

    def demon_attack(self, target, demon, night):
        """The Demon attacks `target`: nothing happens if they are dead or safe (the Soldier, the Monk's
        protection); their ability may send the death elsewhere (the Mayor); otherwise they die."""
        if not target.alive or self.g.safe_from_demon(target):
            return
        victim = rules(target.character).redirect_attack(self, target, demon) or target
        self.kill(victim, 'demon')
        night.deaths.append(victim)

    def request(self, *args, **kw):
        return Request(*args, **kw)

    def tell(self, p, role, choice, target=None):
        """The Storyteller decides an information role's result and tells the player."""
        text = info_text(role, self.decide(choice), target)
        self.emit('info', {'text': f'Night {self.day} — {role}: {text}'}, [p.name])
        if rules(role).remembered:
            self.g.reminders.append(f'{p.name} ({role}) was shown: {text}')

    async def wake(self, night, characters):
        """Ask the living players whose (apparent) character chooses at night, among `characters`, for their
        choices, all at once. A Drunk who thinks they are the Monk is woken as the Monk; their choice does
        nothing (each character's step acts only for the player who really is that character)."""
        g, names = self.g, self.names
        roles = {c for c in characters if rules(c).night_choice}
        requests = {}
        for p in g.living():
            if p.shown not in roles:
                continue
            k, text, may_self = rules(p.shown).night_choice
            options = [x for x in names if may_self or x != p.name]
            requests[p.name] = Request('night', f'Night {night.n} — {p.shown}: {text} Put your choice in `targets`.',
                                       night.n, n_targets=k, options=options)
        acts = await self.ask_many(requests)
        for name, req in requests.items():
            night.chosen[name] = self.targets(name, acts[name], req)
            self.emit('night_choice', {'player': name, 'role': g[name].shown, 'targets': night.chosen[name]}, 'audit')

    async def night(self, n):
        """Tonight's steps in the official night order, one character at a time. Choices are asked a batch at
        a time (Night.steps), so they can be asked at once while the dead are never woken."""
        g = self.g
        self.day, self.phase = n, 'night'
        g.expire('night')  # last night's poison, protection and master end at dusk
        self.emit('header', {'text': f'Night {n}'})
        night = Night(n)
        for batch in Night.steps(night.first, g.script):
            await self.wake(night, batch)
            for c in batch:
                await rules(c).resolve_night(self, night)

        self.phase = 'day'
        self.emit('header', {'text': f'Day {n}'})
        self.emit('dawn', {'day': n, 'deaths': [d.name for d in night.deaths],
                           'narration': dawn_narration(self.rng, [d.name for d in night.deaths])})
        if night.first:
            self.probe('dawn')

    # ---- day ---------------------------------------------------------------------------------
    def whispers(self, name, action):
        """Up to WHISPERS whispers, each to one or two players. Anything beyond that is dropped, and the
        sender is told (so they don't believe a player heard what they never received)."""
        out, dropped = [], []
        sent = [w for w in (action.get('whispers') or []) if isinstance(w, dict)]
        for i, w in enumerate(sent):
            to = [t for t in dict.fromkeys(w.get('to') or []) if t in self.names and t != name]
            text = clip(w.get('text'), WORDS['whisper'])
            if not (to and text):
                continue
            if i >= WHISPERS:
                limit = 'one whisper a turn' if WHISPERS == 1 else f'at most {WHISPERS} whispers a turn'
                dropped.append(f'your whisper to {", ".join(to)} was not sent ({limit})')
                continue
            if len(to) > 2:
                dropped.append(f'your whisper to {", ".join(to)} went only to {to[0]} and {to[1]} '
                               '(a whisper goes to one or two players)')
            out.append({'to': to[:2], 'text': text})
        if dropped:
            text = '; '.join(dropped)
            self.emit('notice', {'text': f'({text[:1].upper()}{text[1:]}.)'}, [name])
        return out

    async def turns(self, n, order, kind, head, tail, words, beat=None, private=False, note=''):
        """One turn each for `order`, a wave of a few players at a time: a wave acts simultaneously
        and later waves see what earlier ones said. A private turn is whispers; a public turn is
        speech plus, for anyone claiming to be the Slayer, a shot."""
        g = self.g
        size = math.ceil(len(order) / self.waves)
        waves = [order[i:i + size] for i in range(0, len(order), size)]
        for w, wave in enumerate(waves, start=1):
            requests = {}
            for name in wave:
                prompt = f'{head} — your turn{note}. {tail}'
                if not g[name].alive:
                    prompt += ' (You are dead, but you can still ' + ('whisper.)' if private else 'talk.)')
                requests[name] = Request(kind, prompt, n, beat=beat, alive=g[name].alive,
                                         mode='private' if private else 'public')
            acts = await self.ask_many(requests)
            if private:
                for name in wave:
                    if (acts[name].get('say') or '').strip() and not acts[name].get('whispers'):
                        self.emit('notice', {'text': '(Nothing is said aloud in private time: to talk to someone, '
                                                     'whisper to them.)'}, [name])
                    for msg in self.whispers(name, acts[name]):
                        self.emit('whisper', {'from': name, **msg}, [name, *msg['to']])
                continue
            for name in wave:
                say = clip(acts[name].get('say'), words)
                if say:
                    self.emit('say', {'speaker': name, 'text': say})
            self.shots(wave, acts)
            if g.winner:
                return

    async def beat(self, n, k, private):
        """Everyone gets one turn, in a random order. In private time players can only whisper;
        in the town square they can only speak."""
        total = self.private_beats if private else self.public_beats
        order = list(self.names)
        self.rng.shuffle(order)
        self.emit('header', {'text': f'Day {n} · {"private time" if private else "town square"} {k}'})
        if private:
            left = total - k
            note = f' ({left} whisper{"" if left == 1 else "s"} left today after this one)'
            tail = ('You may send one whisper, to one or two players, or none. Nobody can address the town until the '
                    'town square.')
        else:
            note, tail = '', 'Say something to the town, or nothing. No whispering now.'
            if k == total:
                tail += ' This is the last beat before nominations.'
        await self.turns(n, order, 'beat', f'Day {n}, {"private time" if private else "town square"} {k} of {total}',
                         tail, WORDS['beat'], beat=k, private=private, note=note)

    def shots(self, names, acts):
        """Public day actions taken on these public turns, in order (the Slayer's shot, which anyone can claim)."""
        for name in names:
            t = acts[name].get('slayer_shot')
            if t in self.names and t != name and not self.g.winner:
                self.slayer(name, t)

    def slayer(self, shooter, target):
        g = self.g
        action = g.script.public_actions.get('slayer_shot')  # a script without a Slayer: nobody's shot does anything
        died = action.act_publicly(self, shooter, target) if action else False
        self.emit('slayer', {'shooter': shooter, 'target': target, 'died': died})
        if died:
            self.kill(g[target], 'slayer')
            g.check_victory()

    def execute(self, name):
        g, p = self.g, self.g[name]
        died = p.alive
        self.executed_today = True
        self.emit('execution', {'player': name, 'died': died})
        if died:
            g.alive_at_execution = g.alive_count()
            ends = rules(p.character).executed(self, p)  # the Saint's team loses
            self.kill(p, 'execution')
            g.executed_death = name
            if ends:
                g.winner, g.reason = ends
        g.check_victory()

    def virgin(self, nominator, nominee):
        """The nominee's character reacts to the nomination: True if that ended the day (the Virgin's ability
        executed the nominator)."""
        return rules(self.g[nominee].character).nominated(self, self.g[nominee], nominator)

    def vote_order(self, nominee):
        i = self.names.index(nominee)
        return [self.names[(i + k) % len(self.names)] for k in range(1, len(self.names) + 1)]

    async def vote(self, nominee, block, top):
        g, n = self.g, self.day
        needed = math.ceil(g.alive_count() / 2)
        required = max(needed, top + 1)
        yes, voted, early = [], set(), {}

        async def ask_vote(voter):
            p = g[voter]
            lines = [f'Vote: should {nominee} be executed? It takes {required} yes votes to put them on the block']
            if block:
                lines[0] += f' (replacing {block}, who has {top})'
            elif top:
                lines[0] += f' (more than the {top} of an earlier tied vote)'
            lines[0] += '.'
            lines.append(f'Yes so far: {", ".join(yes) if yes else "none"} ({len(yes)}).')
            if not p.alive:
                lines.append('You are dead: voting yes uses your one ghost vote.')
            if rules(p.character).follows_master and p.alive and g.master:  # poisoned or not: they can't tell
                up = g.master in yes or early.get(g.master, (False,))[0]
                lines.append(f'Your master is {g.master}: their hand is {"up, so you may vote" if up else "down, so you may not vote yes"}.')
            lines.append('Set `vote` to true or false; `say` may hold a very short remark (optional; don\'t just restate your vote).')
            a = await self.ask(voter, Request('vote', ' '.join(lines), n, options=[nominee]))
            if not isinstance(a.get('vote'), bool):  # no vote given: ask once more rather than assume no
                a = await self.ask(voter, Request('vote', 'Your vote was missing. Set `vote` to true (yes) or '
                                                          f'false (no): should {nominee} be executed?', n,
                                                  options=[nominee]))
            return a.get('vote') is True, clip(a.get('say'), WORDS['vote'])

        def can_vote(q):
            return q.alive or q.ghost_vote

        for voter in self.vote_order(nominee):
            p = g[voter]
            if not can_vote(p):
                continue
            master = g[g.master] if rules(p.character).follows_master and p.alive and g.master else None
            if master and master.name not in voted and master.name not in early and can_vote(master):
                # hands go up together: a master who votes later is asked now, so the Butler can see whether
                # their hand is up (the master's vote is still shown at their own seat)
                early[master.name] = await ask_vote(master.name)
            v, remark = early.pop(voter) if voter in early else await ask_vote(voter)
            if (v and rules(p.character).follows_master and g.works(p, p.character) and g.master
                    and not (g.master in yes or early.get(g.master, (False,))[0])):
                v, remark = False, ''  # a Butler may only raise their hand while their master's is up
                self.emit('notice', {'text': f'(Your master {g.master} is not voting yes, so you cannot vote.)'}, [voter])
            ghost = v and not p.alive
            if ghost:
                p.ghost_vote = False
            self.emit('vote', {'voter': voter, 'nominee': nominee, 'yes': v, 'ghost': ghost, 'text': remark})
            voted.add(voter)
            if v:
                yes.append(voter)
        count = len(yes)
        if count >= needed and count > top:
            block, top, outcome = nominee, count, 'block'
        elif count >= needed and count == top:
            block, outcome = None, 'tie'
        else:
            outcome = 'short'
        self.emit('vote_result', {'nominee': nominee, 'votes': count, 'needed': required, 'outcome': outcome,
                                  'voters': yes})
        return block, top

    async def nominations(self):
        """Rounds until a call gets no nomination. Each round: every living player who hasn't
        nominated today is asked at once whether to nominate (if several do, one is taken at random,
        as when hands go up together); then the accusation, the defense, one round of comments from
        everyone, and the clockwise vote."""
        g, n = self.g, self.day
        self.phase = 'nominations'
        self.emit('nominations_open', {})
        nominators, nominees = set(), set()
        block, top = None, 0
        while not g.winner:
            eligible = [p.name for p in g.living() if p.name not in nominators]
            options = [x for x in self.names if x not in nominees]
            if not eligible or not options:
                break
            status = (f'{block} is on the block with {top} votes.' if block else
                      f'Nobody is on the block (an earlier vote tied at {top}).' if top else 'Nobody is on the block yet.')
            prompt = (f'Day {n}, nominations. {status} Already nominated today: {", ".join(sorted(nominees)) or "nobody"}. '
                      'You may nominate someone (set `nominate`; your `say` is the accusation), or pass. Only '
                      'nominations are heard now: everyone can comment after the defense. No whispering now.')
            acts = await self.ask_many({name: Request('nominate', prompt, n, options=options) for name in eligible})
            self.shots(eligible, acts)
            if g.winner:
                return
            noms = [(name, acts[name]['nominate'], clip(acts[name].get('say'), WORDS['nominate']))
                    for name in eligible if acts[name].get('nominate') in options]
            if not noms:
                break
            nominator, nominee, accusation = self.rng.choice(noms)
            for other, t, _ in noms:
                if other != nominator:
                    self.emit('notice', {'text': f'(Your nomination of {t} was not taken: several players nominated at '
                                                 f'once, and {nominator}\'s nomination of {nominee} was picked at '
                                                 'random. You can nominate again later.)'}, [other])
            nominators.add(nominator)
            nominees.add(nominee)
            self.emit('nomination', {'nominator': nominator, 'nominee': nominee, 'text': accusation})
            if self.virgin(nominator, nominee):
                return
            d = await self.ask(nominee, Request('defense', f'Day {n}: {"you have nominated yourself" if nominator == nominee else nominator + " has nominated you"}. '
                                                           'Give your defense in `say`.', n))
            self.emit('defense', {'nominee': nominee, 'text': clip(d.get('say'), WORDS['defense'])})
            order = list(self.names)
            self.rng.shuffle(order)
            await self.turns(n, order, 'comment', f'Day {n}, comments on the nomination of {nominee}',
                             'Say something to the town before the vote, or nothing (don\'t just announce your vote). No whispering now.', WORDS['comment'])
            if g.winner:
                return
            block, top = await self.vote(nominee, block, top)
        if g.winner:
            return
        if block:
            self.execute(block)
        else:
            self.emit('no_execution', {})

    async def daytime(self, n):
        g = self.g
        g.executed_death, self.executed_today = None, False
        for private, total in ((True, self.private_beats), (False, self.public_beats)):
            for k in range(1, total + 1):
                await self.beat(n, k, private)
                if g.winner:
                    return
        self.probe('nominations')
        await self.nominations()
        if g.winner:
            return
        for p in g.players:  # end-of-day abilities (the Mayor's win)
            rules(p.character).end_of_day(self, p)
            if g.winner:
                return

    # ---- the whole game ------------------------------------------------------------------------
    # ---- checkpoints -----------------------------------------------------------------------
    CHECKPOINT = 'checkpoint.pkl'
    STOP = 'STOP'  # touch <game>/STOP to halt that game at its next turn (it keeps its checkpoint)

    async def checkpoint(self, n, elapsed):
        """Save everything needed to continue the game at night n: the Grimoire, the random states,
        every event and call so far, each seat's pending text and conversation. Written at each dusk,
        so a game killed by a machine restart or a failed seat resumes from its last dusk."""
        if not self.out:
            return
        if self.probe_tasks:  # finish the day's belief probes so none is lost with the process
            await asyncio.gather(*self.probe_tasks)
            self.probe_tasks = []
        convs = {name: {k: getattr(seat.conversation, k) for k in ('messages', 'trimmed', 'last_input')}
                 for name, seat in self.seats.items() if hasattr(seat, 'conversation')}
        probes = self.out / 'probes.jsonl'
        state = {'night': n, 'elapsed': elapsed, 'day': self.day, 'phase': self.phase, 'g': self.g,
                 'rng': self.rng.getstate(), 'st_rng': getattr(getattr(self.st, 'rng', None), 'getstate', lambda: None)(),
                 'events': self.events, 'calls': self.calls, 'errors': self.errors, 'buf': self.buf,
                 'executed_today': self.executed_today, 'starting': self.starting, 'start_teams': self.start_teams,
                 'meta': self.meta,
                 'probe_lines': len(probes.read_text().splitlines()) if probes.exists() else 0, 'convs': convs}
        tmp = self.out / (self.CHECKPOINT + '.tmp')
        tmp.write_bytes(pickle.dumps(state))
        tmp.replace(self.out / self.CHECKPOINT)

    def restore(self):
        """Continue from this game's checkpoint, if it has one: returns (night, elapsed seconds) or None.
        The log files are cut back to the checkpoint, so they read as if play never stopped."""
        path = self.out / self.CHECKPOINT if self.out else None
        if not path or not path.exists():
            return None
        s = pickle.loads(path.read_bytes())
        for k in ('day', 'phase', 'g', 'events', 'calls', 'errors', 'buf', 'executed_today', 'starting', 'meta'):
            setattr(self, k, s[k])
        self.start_teams = s.get('start_teams') or {  # checkpoints from before teams were recorded
            n: 'evil' if is_evil_character(c) else 'good' for n, c in self.starting.items()}
        self.rng.setstate(s['rng'])
        if s['st_rng'] is not None:
            self.st.rng.setstate(s['st_rng'])
        if self.seat_factory:
            # by the team each seat was dealt, not its current one: a seat that changed team (a Goon, a Snake
            # Charmer's swap) keeps its model (docs/open-decisions.md, section 1)
            self.seats = {p.name: self.seat_factory(p.name, self.start_teams[p.name]) for p in self.g.players}
        for name, conv in s['convs'].items():
            for k, v in conv.items():
                setattr(self.seats[name].conversation, k, v)
        (self.out / 'events.jsonl').write_text(''.join(json.dumps(ev) + '\n' for ev in self.events))
        (self.out / 'transcript.md').write_text(''.join(
            (render(ev, 'omniscient', set(ev['dead'])) or '') + '\n' for ev in self.events))
        (self.out / 'calls.jsonl').write_text(''.join(json.dumps(c) + '\n' for c in self.calls))
        probes = self.out / 'probes.jsonl'
        if probes.exists():
            probes.write_text(''.join(line + '\n' for line in probes.read_text().splitlines()[:s['probe_lines']]))
        (self.out / 'result.json').unlink(missing_ok=True)  # a stopped game resumes too
        return s['night'], s['elapsed']

    async def run(self):
        start = time.time()
        stopped = None
        try:
            resumed = self.restore()
            if resumed:
                n, earlier = resumed
                start -= earlier
            else:
                await self.setup()
                n = 1
            while True:
                await self.checkpoint(n, time.time() - start)
                await self.night(n)
                if self.g.check_victory():
                    break
                await self.daytime(n)
                if self.g.check_victory():
                    break
                if n >= self.max_days:
                    stopped = f'stopped after day {n}'
                    break
                n += 1
        except BudgetExceeded as e:
            stopped = f'budget: {e}'
        except SeatFailed as e:
            stopped = f'seat failed: {str(e)[:300]}'
        except Halted as e:
            stopped = f'halted: {e}'
        if self.probe_tasks:
            await asyncio.gather(*self.probe_tasks)
        g = self.g
        if g and g.winner:
            self.emit('game_over', {'winner': g.winner, 'reason': g.reason})
        result = self.result(time.time() - start, stopped)
        if self.out:
            (self.out / 'result.json').write_text(json.dumps(result, indent=2))
            if not (stopped or '').startswith(('seat failed', 'budget', 'halted')):  # only a stopped game resumes
                (self.out / self.CHECKPOINT).unlink(missing_ok=True)
        return result

    def result(self, seconds, stopped):
        g = self.g
        usage = {'input': 0, 'cache_read': 0, 'cache_write': 0, 'output': 0}
        for c in self.calls:
            u = c.get('usage', {})
            usage['input'] += u.get('input_tokens', 0)
            usage['cache_read'] += u.get('cache_read_input_tokens', 0)
            usage['cache_write'] += u.get('cache_creation_input_tokens', 0)
            usage['output'] += u.get('output_tokens', 0)
        return {'winner': g.winner if g else None, 'reason': (g.reason if g else None) or stopped,
                'stopped': stopped, 'days': self.day, 'seed': self.seed, 'starting': self.starting,
                'final': {p.name: p.character for p in g.players} if g else None,
                'bluffs': g.bluffs if g else None, 'red_herring': g.red_herring if g else None,
                'drunk_as': next((p.shown for p in g.players if rules(p.character).always_drunk), None) if g else None,
                'cost': round(sum(c.get('cost', 0) for c in self.calls), 4), 'calls': len(self.calls),
                'tokens': usage, 'seconds': round(seconds, 1), 'errors': self.errors, **self.meta}
