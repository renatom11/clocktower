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
import dataclasses
import inspect
import json
import pickle
import math
import random
import re
import time
from pathlib import Path

from .agents import Request, ScriptedStoryteller
from .characters import ALL, TB, Choose, card, choice_spec, is_evil_character, kind, now, rules, settle
from .llm import BudgetExceeded, SeatFailed


class Halted(RuntimeError):
    """An operator asked this one game to stop (a STOP file in its folder); it resumes from its checkpoint."""
from . import probe
from .prompts import dawn_narration
from .render import render
from .state import (POLICY, Grimoire, bluffs_choice, info_text, madness_choice, madness_penalty_choice, norm,
                    only_false, random_setup, setup_error)
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
        self.characters = {}  # player name -> the character they chose tonight (the Courtier, the Gambler)
        self.deaths = []
        self.revived = []  # players alive again (the Professor, the Shabaloth), announced at dawn
        self.before = {}  # each player's choice on their previous night, as it stood at dusk (the Shabaloth's meal)
        self.prior = {}  # each ability instance's last night choice at dusk: {Ability.id: (night, players)}
        self.asleep = set()  # players who don't wake tonight to use their own ability (the Exorcist's Demon)

    def choice_of(self, g, character):
        """(The living player who really is `character` (or a dead one keeping their ability: Grimoire.holder), their
        first choice tonight or None: not woken, or they chose no one)."""
        p = g.holder(character)
        return (p, (self.chosen[p.name] or [None])[0]) if p and p.name in self.chosen else (p, None)

    def before_of(self, g, p, character):
        """The players p chose last night with `character`'s ability (their instance of it: state.Ability), as it
        stood at dusk; [] if that instance did not wake and choose last night (one begun since, by a change of
        character, has no last night: the Shabaloth's meal is its own)."""
        n, chosen = self.prior.get(g.ability(p, character).id, (None, []))
        return list(chosen) if n == self.n - 1 else []

    @staticmethod
    def steps(first, script=TB):
        """Tonight's night order in batches. Choices are asked a batch at a time, and a batch ends after each
        step that can kill, so a player killed tonight is never woken to choose (the Fortune Teller and Butler
        choose after the Demon's kill). Night 1 has no kill: one batch."""
        order = script.first_night if first else script.other_nights
        if not script.batched_night:
            return [[c] for c in order]
        batches, batch = [], []
        for c in order:
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


# ---- what is said: matching words and phrases (abilities that listen: Character.listens) ---------------------------
# A word or phrase is said when its words appear, in order and next to each other, as whole words of what a player
# said: case, punctuation and spacing don't matter, and an apostrophe joins its word ("let's" is "lets").
def words(text):
    """The words of `text`, lowercased, with punctuation and spacing collapsed."""
    return re.sub(r"[^0-9a-z]+", ' ', (text or '').lower().replace("'", '').replace('\u2019', '')).split()


def said(text, phrase):
    """How many times `phrase` is said in `text`, as a whole-word sequence (non-overlapping)."""
    target, ws = words(phrase), words(text)
    k, i, n = len(target), 0, 0
    while target and i + k <= len(ws):
        if ws[i:i + k] == target:
            n, i = n + 1, i + k
        else:
            i += 1
    return n


def _close(a, b):
    """Whether word `a` is a near miss for word `b`: another form of it (`b` and up to four more letters, or a shorter
    word it starts with, of four letters or more), or one letter added, missing or changed (words of five or more)."""
    if a == b:
        return False
    if a.startswith(b) and len(a) - len(b) <= 4:
        return True
    if b.startswith(a) and len(a) >= 4 and len(b) - len(a) <= 2:
        return True
    if min(len(a), len(b)) < 5 or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    short, long_ = sorted((a, b), key=len)
    return any(long_[:i] + long_[i + 1:] == short for i in range(len(long_)))


def nearly_said(text, phrase):
    """The near misses for `phrase` in `text` (each as the words said): a run of words each the phrase's word or close
    to it (_close), not all exact; or, for a phrase of several words, the phrase with one word too many inside it.
    Exact sayings are not near misses."""
    target, ws = words(phrase), words(text)
    k, out = len(target), []
    if not target:
        return out
    for i in range(len(ws) - k + 1):
        run = ws[i:i + k]
        if run != target and all(a == b or _close(a, b) for a, b in zip(run, target)):
            out.append(' '.join(run))
    if k > 1:
        for i in range(len(ws) - k):
            run = ws[i:i + k + 1]
            if run[0] == target[0] and run[-1] == target[-1] and run[:k] != target and run[1:] != target and any(
                    run[:j] + run[j + 1:] == target for j in range(1, k)):
                out.append(' '.join(run))
    return list(dict.fromkeys(out))


# The events whose text a player says, and who says it: aloud (to 'public'), or in a whisper
SPEECH = {'say': 'speaker', 'nomination': 'nominator', 'defense': 'nominee', 'vote': 'voter', 'ability': 'player',
          'whisper': 'from'}


def clip(text, words):
    text = plain(text)
    w = text.split(' ')
    return text if len(w) <= words else ' '.join(w[:words]) + '...'  # the same for every model


def fmt(value):
    return {k: v for k, v in norm(value).items() if v not in (None, [])}


def demon_info(minions, bluffs):
    """What the Demon is told before the first night (and the Lunatic, who believes they are one)."""
    if not minions:  # (the Kazali, who chooses its Minions on the first night)
        return f'No player is a Minion yet. Three good characters not in play, for evil to bluff: {", ".join(bluffs)}.'
    return (f'Your Minion{"" if len(minions) == 1 else "s"}: {", ".join(minions)} (you do not know which Minion '
            f'characters). Three good characters not in play, for evil to bluff: {", ".join(bluffs)}.')


class Game:
    def __init__(self, seats, storyteller=None, *, names=NAMES, seed=None, private_beats=6, public_beats=3, max_days=10,
                 waves=3, characters=None, minion=None, out=None, seat_factory=None, probes=True, script=TB,
                 judge=None):
        """`seats` maps names to seats; alternatively `seat_factory(name, team)` creates them once the
        characters are dealt (so, for example, the evil team can use a different model). `probes` asks
        seats that support it for their beliefs at dawn of day 1 and before each day's nominations,
        outside the game (probe.py). Every day has
        `private_beats` of private time and `public_beats` of town square. `minion` forces the Minion
        character of a random setup (batches rotate it so every Minion is covered). The Storyteller
        defaults to the scripted one (state.POLICY). `script` is the characters.Script played (Trouble Brewing by
        default)."""
        self.seats, self.names, self.seat_factory, self.script = seats, list(names), seat_factory, script
        self.judge = judge  # the Storyteller judge for judged decisions (judge.py); None: the scripted style
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
        self.pending = []  # abilities waiting for a player's answer (Game.later)
        self.tonight = None  # the Night being played, or None by day (where an ability's kill is announced at dawn)

    # ---- logging -----------------------------------------------------------------------
    def _write(self, filename, line):
        if self.out:
            with (self.out / filename).open('a') as f:
                f.write(line + '\n')

    def emit(self, kind, data, to='public'):
        dead = {p.name for p in self.g.players if not p.appears_alive} if self.g else set()
        ev = {'seq': len(self.events), 'time': round(time.time(), 2), 'day': self.day, 'phase': self.phase,
              'kind': kind, 'data': data, 'to': to, 'dead': sorted(dead)}
        self.events.append(ev)
        if kind in SPEECH and self.g is not None and getattr(self.g.script, 'listeners', ()):
            self.heard(ev)  # (custom scripts: abilities that listen to what is said)
        for n in self.names:
            text = render(ev, n, dead)
            if text is not None:
                self.buf[n].append(text)
        self._write('events.jsonl', json.dumps(ev))
        self._write('transcript.md', render(ev, 'omniscient', dead))

    def heard(self, ev):
        """A player said something (a SPEECH event): every listening ability on the script hears it (Character.heard),
        aloud or in a whisper, with the event's number, so "the first to say" can be told."""
        d = ev['data']
        speaker, text = d.get(SPEECH[ev['kind']]), d.get('text') or ''
        if speaker in self.g.by_name and text:
            for c in self.g.script.listeners:
                rules(c).heard(self, speaker, text, ev['to'] == 'public', ev['seq'])

    def chatter(self, name):
        """Lines a random bot may say on `name`'s turn, from the listening abilities on the script (Character.chatter);
        [] on any script without one."""
        if self.g is None or not getattr(self.g.script, 'listeners', ()):
            return []
        return [line for c in self.g.script.listeners for line in rules(c).chatter(self, name)]

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
            # the team they believe they are on (the Lunatic believes they are the Demon)
            believes_evil = rules(p.shown).evil if p.shown != p.character else p.evil
            text = (pending + '\n\n' if pending else '') + '>>> ' + probe.prompt(believes_evil)
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

    async def decide_judged(self, choice):
        """A decision that needs judgment (misinformation, misregistration, a statement's truth): the judge ranks
        the legal values and the code picks from the ranking with fixed weights (POLICY 'judge_top' for the first,
        'judge_second' for the second, otherwise the scripted style). With no judge, the same as decide(). False
        information is recorded as an abnormal result (Game.abnormal)."""
        value = await self._decide_judged(choice)
        self.note_information(choice, value)
        return value

    async def _decide_judged(self, choice):
        choice = self.false_only(choice)
        if self.judge is None or choice.auto:  # exactly decide(): the same value and random draws
            return self.decide(choice)
        ranking, reason = await self.judge.rank(self, choice)
        ranking = [norm(v) for v in ranking if choice.legal(v)]
        r = self.st.rng.random() if hasattr(self.st, 'rng') else 1.0
        if ranking and r < POLICY['judge_top']:
            value, took = ranking[0], 1
        elif len(ranking) > 1 and r < POLICY['judge_top'] + POLICY['judge_second']:
            value, took = ranking[1], 2
        else:
            value, took = norm(self.st.choose(choice)), 0
        if not choice.legal(value):
            raise ValueError(f'illegal Storyteller value for {choice.id}: {value}')
        self.emit('st_choice', {'id': choice.id, 'value': fmt(value), 'valid': True,
                                'judge': {'mode': self.judge.mode, 'ranked': [fmt(v) for v in ranking[:3]],
                                          'took': took, 'reason': reason}}, 'audit')
        return value

    def abnormal(self, p, ability, why):
        """Record that p's `ability` worked abnormally because of another character's ability (the Mathematician's
        ABNORMAL reminder): information that should have been true was false, or an ability that should have worked
        didn't (a poisoned Demon's kill, a drunk Witch's curse). Kept in the Grimoire with when it happened (the day
        number and the phase: 'night', or 'day' for any point of the day), so "since dawn" can be counted. Nothing is
        emitted: no one is told."""
        self.g.abnormal.append({'player': p.name, 'ability': ability, 'why': why, 'day': self.day,
                                'phase': 'night' if self.tonight is not None else 'day'})

    def note_information(self, choice, value):
        """An information decision whose value a working ability could not give (`choice.truth`) is abnormal: the
        recipient was drunk or poisoned by an ability, or their information was falsified (the Vortox). True
        information for an impaired player is not (the almanac: the poisoned Empath getting true information). The
        Drunk's own drunkenness is not another character's ability (a reading), except where the Mathematician/Drunk
        jinx is in effect (a custom script with both: docs/carousel-rulings.md, 7)."""
        ctx = choice.context or {}
        if ctx.get('call') != 'information' or choice.truth is None or self.g is None:
            return
        p = self.g.by_name.get(ctx.get('recipient'))
        ability = ctx.get('ability') or (p.shown if p else None)
        if p is None or choice.truth(value):
            return
        if (rules(p.character).always_drunk and not self.g.falsified(p, ability)
                and not self.g.script.jinxed('Mathematician', p.character)):
            return
        self.abnormal(p, ability, 'false information')

    def false_only(self, choice):
        """An information Choice whose recipient's information must be false (Grimoire.falsified: the Vortox) offers
        only its false values (state.only_false), so no scripted draw or judge can give a true one. Any other Choice
        is unchanged."""
        ctx = choice.context or {}
        p = self.g.by_name.get(ctx.get('recipient')) if self.g and ctx.get('call') == 'information' else None
        if p is None or choice.truth is None or not self.g.falsified(p, ctx.get('ability')):
            return choice
        return only_false(choice)

    # ---- character and alignment changes -------------------------------------------------------------
    async def change(self, p, character=None, alignment=None):
        """p becomes `character` and/or turns `alignment` (the Pit-Hag's change, the Fang Gu's jump): see changes()."""
        await self.changes([(p, character, alignment)])

    async def swap(self, a, b, alignments=False):
        """a and b swap characters, and alignments too if `alignments` (the Snake Charmer's swap with the Demon; the
        Barber's swaps keep alignments): see changes()."""
        await self.changes([(a, b.character, b.alignment if alignments else None),
                            (b, a.character, a.alignment if alignments else None)])

    async def changes(self, changes):
        """Each (player, character or None, alignment or None) happens at once; then each player who changed is told
        in private, at once, what they are now ("You are now the X"; their alignment, changed or "still"). Being
        told is not information: drunkenness, poison and the Vortox never touch it. Taking a new character ends the
        old one's ongoing effects (Grimoire.change_character: a Demon that is no longer the Demon stops poisoning)
        and gives its ability fresh, even a once-per-game one used before (the Barber's almanac); a new Demon learns
        no Minions. Then the new character's `becomes` (a new Evil Twin's twin) and everyone's `changed` hooks run.
        A character that passes from one player to another here (a swap) takes what belongs to it, not to its old
        player (Character.hand_over: the Vigormortis's dead Minions keep their abilities)."""
        g, done, moving = self.g, [], []
        before = [(p, p.character) for p, _, _ in changes]
        for p, character, _ in changes:
            giver = next((q for q, c in before if c == character and q is not p), None) if character else None
            if giver and character != p.character:
                moving.append((p, rules(character).hand_over(g, giver, p)))
        for p, character, alignment in changes:
            old = (p.character, p.alignment)
            if character and character != p.character:
                self.transition(p, character)
            if alignment and alignment != p.alignment:
                p.alignment = alignment
                self.emit('alignment', {'player': p.name, 'alignment': alignment}, 'audit')
            if (p.character, p.alignment) != old:
                done.append((p, old))
        for p, states in moving:
            for st in states:  # (now the new holder's instance's)
                st.source, st.ability = p.name, g.ability(p, p.character).id
                g.add(st)
        when = f'Night {self.day}' if self.tonight is not None else f'Day {self.day}'
        for p, (character, alignment) in done:
            told = [f'you are now the {p.character} ({rules(p.character).ability})'] if p.character != character else []
            told.append(f'you are now {p.alignment}' if p.alignment != alignment else f'you are still {p.alignment}')
            self.inform(p, f'{when}: {" and ".join(told)}.')
        for p, (character, _) in done:
            if p.character != character:
                await settle(rules(p.character).becomes(self, p))
        for p, _ in done:
            await self.after_change(p, False)

    def transition(self, p, character, how='changed', quiet=False):
        """The one path every character change takes, whatever makes it (Game.changes: the Pit-Hag, the Barber, the
        Snake Charmer, the Fang Gu, the Farmer...; Game.become: the Scarlet Woman, the Imp's starpass, the
        Marionette; the setup steps, with how='dealt'): Grimoire.change_character (the old ability instances end
        with what they recorded, the new one starts fresh, a seeming death settles, what lasted only while the old
        character had its ability ends) and the audit's 'becomes' event (none for a setup step, `quiet`: the setup
        is announced as a whole). The caller tells the player, in its own words, and runs the hooks (after_change)."""
        self.g.change_character(p, character, how)
        if not quiet:
            self.emit('becomes', {'player': p.name, 'character': character}, 'audit')

    async def after_change(self, p, became=True):
        """The hooks a change runs: the new character's `becomes` (if p took a new character: what it needs now, a
        new Yaggababble's phrase), then everyone's `changed` (an Evil Twin whose twin changed)."""
        if became:
            await settle(rules(p.character).becomes(self, p))
        for q in self.g.players:
            for c in self.g.abilities(q):
                await settle(rules(c).changed(self, q, p))

    async def become(self, p, character, notice=None):
        """p becomes `character` by an ability that tells them in its own words (`notice`): the Imp's starpass, the
        Marionette's. The same transition and hooks as Game.changes."""
        self.transition(p, character)
        if notice:
            self.emit('notice', {'text': notice}, [p.name])
        await self.after_change(p)

    def become_now(self, p, character, notice=None):
        """Game.become from a hook that cannot wait (the Scarlet Woman's, on a death): the hooks run now if none of
        them consults the Storyteller judge, else at the next safe point (Game.later)."""
        self.transition(p, character)
        if notice:
            self.emit('notice', {'text': notice}, [p.name])
        hooks = [rules(p.character).becomes] + [rules(c).changed for q in self.g.players for c in self.g.abilities(q)]
        if any(inspect.iscoroutinefunction(h) for h in hooks):
            self.later(lambda game: game.after_change(p))
        else:
            now(self.after_change(p))

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
            if c.setup_unheld or c.name in {p.character for p in g.players} | {p.shown for p in g.players}:
                await settle(c.setup(self))
        drunk = next((p for p in g.players if rules(p.character).always_drunk), None)
        g.bluffs = (await self.decide_judged(bluffs_choice([c for c in self.script.good if c not in in_play],
                                                           drunk is not None, drunk.shown if drunk else None)))[
            'characters']
        self.starting = {p.name: p.character for p in g.players}
        self.start_teams = {p.name: p.alignment for p in g.players}
        if self.seat_factory:
            self.seats = {p.name: self.seat_factory(p.name, 'evil' if p.evil else 'good') for p in g.players}
        self.emit('setup', {'seats': [{'name': p.name, 'character': p.character, 'shown': p.shown} for p in g.players],
                            'red_herring': g.red_herring, 'bluffs': g.bluffs}, 'audit')

        # a Poppy Grower with their ability keeps the Minions and Demon from learning each other
        apart = any(rules(q.character).keeps_evil_apart(g, q) for q in g.players)
        for p in g.players:
            left, right = names[(p.seat - 1) % len(names)], names[(p.seat + 1) % len(names)]
            lines = [f'You are {p.name}. The players, clockwise: {seating} (and back to {names[0]}). '
                     f'You sit between {left} and {right}.',
                     f'Your character: {card(p.shown)}']
            minions = [q.name for q in g.players if kind(q.character) == 'Minion']
            knows = rules(p.shown).evil  # a Minion who believes they are good (the Marionette) learns nothing evil
            if apart and knows and (p.is_demon or kind(p.character) == 'Minion'):
                lines.append('You do not learn who the other evil players are.' + (
                    f' Three good characters not in play, for evil to bluff: {", ".join(g.bluffs)}.'
                    if p.is_demon else ''))
            elif p.is_demon and not rules(p.character).own_evil_info:  # Demon info and Minion info (batch 6:
                #                                                         Legion's is its own)
                lines.append(demon_info(self.evil_shown(p, minions, 'Minion'), g.bluffs))
            elif kind(p.character) == 'Minion' and knows:
                others = [m for m in minions if m != p.name and rules(g[m].shown).evil]
                demon = g.demon()
                shown = self.evil_shown(p, [demon.name] if demon else [], 'Demon')
                lines.append((f'The Demon is {shown[0]}.' if len(shown) == 1 else
                              f'The Demon is {" or ".join(shown)} (you were shown both).' if shown else
                              'No player is the Demon yet.')
                             + (f' Your fellow Minion{"" if len(others) == 1 else "s"}: {", ".join(others)} (you do not '
                                'know which Minion characters).' if others else ''))
            if p.evil and knows:
                for q in g.players:  # what evil learns because a character is in play (the Damsel)
                    lines += rules(q.character).told_evil(self, q, p)
            lines += rules(p.character).intro(self, p)  # a character's own first information (the Lunatic's)
            lines += g.notes.get('Intro', {}).get(p.name, [])  # (custom scripts: what a setup step tells a player:
            #                                                   the Bounty Hunter's evil Townsfolk, the Vizier's name)
            self.emit('intro', {'text': '\n'.join(lines)}, [p.name])

    def evil_shown(self, viewer, names, as_):
        """`names` (the Minions shown to the Demon, or the Demon shown to the Minions), with the players who appear as
        `as_` to `viewer` (Character.shown_to_evil: the Magician), in seat order."""
        g = self.g
        extra = [q.name for q in g.players if q is not viewer and q.name not in names
                 and rules(q.character).shown_to_evil(g, q, viewer) == as_]
        return sorted(names + extra, key=lambda x: g[x].seat) if extra else names

    # ---- night -------------------------------------------------------------------------------
    def targets(self, name, action, request):
        """The legal players a night choice named, completed at random (with a notice) when too few were named. A
        choice that may name no one (min_targets 0) is taken as given."""
        chosen = [x for x in dict.fromkeys(action.get('targets') or []) if x in request.options][:request.n_targets]
        need = request.n_targets if request.min_targets is None else request.min_targets
        if len(chosen) < need:
            chosen += self.rng.sample([x for x in request.options if x not in chosen], need - len(chosen))
            self.emit('notice', {'text': f'(Your choice was incomplete, so the Storyteller chose for you: '
                                         f'{", ".join(chosen)}.)'}, [name])
        return chosen

    REASKS = 4  # reminders before a seat that keeps giving no legal answer to a required choice stops the game

    def choice_problem(self, action, request, spec=None):
        """Why an answer to a choice isn't legal (too few legal players, or no character on the script when one must
        be named), or None."""
        named = [x for x in dict.fromkeys(action.get('targets') or []) if x in request.options][:request.n_targets]
        need = request.n_targets if request.min_targets is None else request.min_targets
        if len(named) < need:
            return (f'You named {len(named)} of the {need} player(s) this choice needs, from: '
                    f'{", ".join(request.options)}.')
        optional = spec is not None and spec.optional
        if request.characters and not optional and action.get('character') not in request.characters:
            return 'Name a character on the script in `character`.'
        return None

    async def insist(self, name, request, action, spec=None):
        """A required choice (the Gambler's guess, the Moonchild's curse, any choice that isn't optional) is asked
        again until it is legal, never made for the player (owner's rulings B2.6, B3.10). A seat that gives no legal
        answer after REASKS reminders stops the game, as a failed seat does (it resumes from its checkpoint)."""
        for _ in range(self.REASKS):
            problem = self.choice_problem(action, request, spec)
            if not problem:
                return action
            again = dataclasses.replace(request, prompt=f'(That is not a legal choice: {problem} This choice is '
                                                        f'required.) {request.prompt}')
            action = await self.ask(name, again)
        if self.choice_problem(action, request, spec):
            raise SeatFailed(f'{name}: no legal answer to a required choice after {self.REASKS} reminders')
        return action

    def chosen_character(self, name, action, request):
        """The character a night choice named (the Courtier, the Gambler), or one at random, with a notice."""
        c = action.get('character')
        if c in request.characters:
            return c
        c = self.rng.choice(request.characters)
        self.emit('notice', {'text': f'(You named no character on the script, so the Storyteller chose {c}.)'}, [name])
        return c

    def kill(self, p, cause, source=None, final=False):
        """The one way anyone dies (Demon, execution, Slayer, starpass, any other ability). Returns whether the
        player died as the town sees it. A character may live on while registering as dead (the Zombuul), unless the
        death is `final` (the Assassin's: "even if for some reason they could not"); every death goes in the
        Grimoire's death log, and characters react through on_death (the Scarlet Woman takes over a dead Demon).
        Abilities that last only while their source lives end."""
        g = self.g
        before = g.alive_count()
        seems = not final and rules(p.character).dies(self, p, cause) == 'seems'
        if seems:
            p.seems_dead = True
        else:
            g.die(p)
        # `as`: the character they died as (U1, open: the Undertaker is still told the character now, as before)
        g.death_log.append({'player': p.name, 'cause': cause, 'source': source.name if source else None,
                            'day': self.day, 'phase': self.phase, 'as': p.character,
                            **({'seems': True} if seems else {})})
        self.emit('death', {'player': p.name, 'cause': cause, **({'seems': True} if seems else {})}, 'audit')
        for q in g.players:
            for c in g.abilities(q):
                rules(c).on_death(self, q, p, cause, before)
        return True

    def later(self, action):
        """Run `action(game)`, a coroutine, at the next safe point (after the current turn, execution or night
        step): for an ability that needs a player's answer when it triggers (the Moonchild's choice on death)."""
        self.pending.append(action)

    async def run_pending(self):
        while self.pending and not self.g.winner:
            await self.pending.pop(0)(self)

    async def moment_judged(self, when):
        """A point of the day when characters' abilities may act (see Character.moment), a hook that may consult the
        Storyteller judge (the Tinker's death)."""
        for p in self.g.players:
            for c in self.g.abilities(p):
                await settle(rules(c).moment(self, p, when))
        for c in self.g.script.all:  # (custom scripts: the base scripts have none)
            if rules(c).moment_unheld and not any(c in self.g.abilities(p) for p in self.g.players):
                await settle(rules(c).moment(self, None, when))

    def moment(self, when):
        """moment_judged, synchronously (tests; with no judge, or the rules judge)."""
        now(self.moment_judged(when))

    def prevent_death(self, p, cause, unstoppable=False):
        """Whether p, about to die from `cause`, doesn't: a protection or their own ability (the Fool, once), unless
        the kill is `unstoppable` (the Assassin's: the Fool dies and stays dead)."""
        if unstoppable or self.dooms(p, cause):
            return False
        if self.g.safe(p, cause):
            return True
        return rules(p.character).survives(self, p, cause)

    async def attempt_kill_judged(self, target, cause, source=None, night=None, unstoppable=False):
        """An ability tries to kill `target`: nothing if they are dead or saved; the Demon's attack may land on
        someone else (the Mayor, a Storyteller's call the judge may make). A night death is announced at dawn.
        Returns the player who died, or None. An `unstoppable` kill goes through every protection and survival, and
        kills even a player who only seems dead (the Assassin's: "even if for some reason they could not")."""
        if not target.alive or (target.seems_dead and cause != 'execution' and not unstoppable):
            return None
        if cause == 'demon' and night is not None and self.demon_kills_stopped(night):
            return None
        if self.prevent_death(target, cause, unstoppable):
            return None
        victim = target
        if cause == 'demon':
            victim = await settle(rules(target.character).redirect_attack(self, target, source)) or target
        self.kill(victim, cause, source, final=unstoppable)
        if night is not None:
            night.deaths.append(victim)
        return victim

    def dooms(self, p, cause):
        """Whether p dies from `cause` whatever would save them: a Demon token they carry says so (Character.dooms:
        the Lil' Monsta jinxes, batch 6). False on every other script."""
        return bool(p.carries) and rules(p.carries).dooms(self, p, cause)

    def demon_kills_stopped(self, night):
        """Whether the Storyteller has ruled that the Demons' attacks kill nobody tonight (the Pit-Hag's arbitrary
        deaths: "you can even wake the Demon, see who they choose to attack, and decide that no one dies")."""
        return self.g.notes.get('Demon kills stopped') == night.n

    def attempt_kill(self, target, cause, source=None, night=None, unstoppable=False):
        """attempt_kill_judged, synchronously: for every kill but the Demon's (whose redirection the judge may
        decide), and for tests."""
        return now(self.attempt_kill_judged(target, cause, source, night, unstoppable))

    async def demon_attack_judged(self, target, demon, night):
        """The Demon attacks `target`: nothing happens if they are dead or safe (the Soldier, the Monk's
        protection); their ability may send the death elsewhere (the Mayor); otherwise they die."""
        await self.attempt_kill_judged(target, 'demon', demon, night)

    def demon_attack(self, target, demon, night):
        """demon_attack_judged, synchronously (tests)."""
        now(self.demon_attack_judged(target, demon, night))

    def request(self, *args, **kw):
        return Request(*args, **kw)

    def inform(self, p, text):
        """Tell one player something in private (at night: the Demon learning who the Exorcist chose)."""
        self.emit('info', {'text': text}, [p.name])

    def woken(self, p):
        """Record that p woke tonight to use their ability (the Chambermaid counts them)."""
        self.g.woke.setdefault(self.day, [])
        if p.name not in self.g.woke[self.day]:
            self.g.woke[self.day].append(p.name)

    async def tell(self, p, role, choice, target=None):
        """The Storyteller decides an information role's result (a judged call: misinformation, misregistration)
        and tells the player."""
        text = info_text(role, await self.decide_judged(choice), target)
        self.woken(p)
        self.emit('info', {'text': f'Night {self.day} — {role}: {text}'}, [p.name])
        if rules(role).remembered:
            self.g.reminders.append(f'{p.name} ({role}) was shown: {text}')

    async def wake(self, night, characters):
        """Ask the living players whose (apparent) character chooses at night, among `characters`, for their
        choices, all at once. A Drunk who thinks they are the Monk is woken as the Monk; their choice does
        nothing (each character's step acts only for the player who really is that character). Returns the names
        of the players woken."""
        g, names = self.g, self.names
        roles = {c for c in characters if rules(c).night_choice}
        tonight = g.script.first_night if night.first else g.script.other_nights
        requests, specs, woken_as = {}, {}, {}
        for p in g.players:
            if not (p.alive or g.keeps_ability(p)):  # the dead don't wake, unless they keep their ability (Vigormortis)
                continue
            role = p.shown
            if rules(p.character).wakes_at_own_step:  # at their own step, as who they believe they are, if that
                if p.character not in characters or not rules(p.shown).night_choice or p.shown not in tonight:
                    continue  # character has a step tonight (a Lunatic who believes they are the Zombuul)
            elif p.shown not in roles:
                # an ability gained beyond their character (the Philosopher's) wakes them at that character's step
                role = next((c for c in g.abilities(p)[1:] if c in roles), None)
                if role is None:
                    continue
            if p.name in night.asleep:
                continue
            nc = rules(role).night_spec(self, p, night)  # tonight's shape, or None: not woken tonight
            if nc is None:
                continue
            spec, v17 = choice_spec(rules(role), nc), not isinstance(nc, Choose)
            # "different to last night": the night just before; a player who chose no one then may choose anyone
            last = g.night_choices.get(night.n - 1, {}).get(p.name, []) if spec.not_last else []
            options = [x for x in names if (spec.may_self or x != p.name) and x not in last
                       and (not spec.alive_only or g[x].appears_alive)
                       and (not spec.dead_only or not g[x].appears_alive)]
            must = g.notes.get('Demon must choose', {}).get(night.n) if g.notes.get('Demon must choose') else None
            if must in options and kind(role) == 'Demon':  # (custom scripts: the Alchemist-Spy's right guess)
                options = [must]
            if v17:  # Trouble Brewing's wording and choice, as in protocol v17
                requests[p.name] = Request('night', f'Night {night.n} — {p.shown}: {spec.prompt} Put your choice in '
                                                    '`targets`.', night.n, n_targets=spec.players, options=options)
                continue
            how = ('Put your choice in `targets`' + (' ([] for no one)' if spec.optional else '')
                   + (' and the character in `character`' if spec.character else '') + '.')
            if spec.players == 0:
                how = 'Put the character in `character`' + (' (null for none)' if spec.optional else '') + '.'
            specs[p.name], woken_as[p.name] = spec, role
            requests[p.name] = Request('night', f'Night {night.n} — {role}: {spec.prompt} {how}', night.n,
                                       n_targets=spec.players, options=options,
                                       min_targets=0 if spec.optional else spec.players,
                                       characters=[c for c in g.script.all if not spec.kinds or kind(c) in spec.kinds
                                                   or c in spec.also] if spec.character else [])
        acts = await self.ask_many(requests)
        for name, req in requests.items():
            if g.script.id != 'tb':  # a required choice is asked again, never made for the player (TB: v17's fill)
                acts[name] = await self.insist(name, req, acts[name], specs.get(name))
            night.chosen[name] = self.targets(name, acts[name], req)
            g.last_choices[name] = night.chosen[name]
            inst = g.ability(g[name], woken_as.get(name, g[name].shown))  # (and the instance woken: the Po's charge)
            inst.data['last'], inst.data['last_night'] = night.chosen[name], night.n
            g.night_choices.setdefault(night.n, {})[name] = night.chosen[name]
            g.woke.setdefault(night.n, []).append(name)
            data = {'player': name, 'role': woken_as.get(name, g[name].shown), 'targets': night.chosen[name]}
            if req.characters:  # a character only, that may be declined (the Courtier's): None for none, or for a
                # name not on the script (never a random use of a once-per-game ability)
                spec = specs[name]
                declined = spec.optional and not spec.players and acts[name].get('character') not in req.characters
                night.characters[name] = data['character'] = (None if declined else
                                                               self.chosen_character(name, acts[name], req))
            self.emit('night_choice', data, 'audit')
        return list(requests)

    def pick(self, night, chooser, target):
        """`chooser`, woken tonight, chose player `target` with their ability: the target's abilities react before
        the choice acts (the Goon makes the first chooser drunk)."""
        t = self.g[target]
        for c in self.g.abilities(t):
            rules(c).chosen(self, t, chooser, night)

    def picks(self, night, woken):
        """The choices just made by the players in `woken`, in order, each player chosen (or the player of a chosen
        character, for a choice of a character only: the Courtier's). Characters whose step reports each choice as
        it acts on it (picks_in_turn) are left to do so."""
        g = self.g
        for name in woken:
            p = g[name]
            if rules(p.character).picks_in_turn:
                continue
            for t in night.chosen.get(name, []):
                self.pick(night, p, t)
            chosen = night.characters.get(name)
            spec = choice_spec(rules(p.shown), None)
            if chosen and spec is not None and not spec.players:
                holder = next((q for q in g.players if q.character == chosen), None)
                if holder:
                    self.pick(night, p, holder.name)

    def ability_kill(self, target, cause, source=None):
        """An ability's kill at any time (the Tinker's, the Grandmother's): at night announced at dawn, by day at
        once (the town is not told why). Returns the player who died, or None."""
        victim = self.attempt_kill(target, cause, source, self.tonight)
        if victim and self.tonight is None:
            self.emit('died', {'player': victim.name})
        return victim

    async def night(self, n):
        """Tonight's steps in the official night order, one character at a time. Choices are asked a batch at
        a time (Night.steps), so they can be asked at once while the dead are never woken."""
        g = self.g
        self.day, self.phase = n, 'night'
        g.day = n
        g.expire('night', n)  # last night's poison, protection and master end at dusk
        self.emit('header', {'text': f'Night {n}'})
        night = Night(n)
        night.before = dict(g.last_choices)
        night.prior = {a.id: (a.data.get('last_night'), list(a.data['last'])) for a in g.instances if 'last' in a.data}
        self.tonight = night
        for batch in Night.steps(night.first, g.script):
            woken = await self.wake(night, batch)
            if not g.script.batched_night:  # one character at a time: their picks land before their step acts
                self.picks(night, woken)
            for c in batch:
                g.acting = c  # (the states this step makes belong to its ability: Grimoire.add)
                await rules(c).resolve_night(self, night)
                g.acting = None
                await self.run_pending()
                held = g.notes.get('Storyteller abilities')  # abilities the Storyteller uses (the Plague Doctor's)
                if held and c in held:
                    await rules(held[c]).storyteller_step(self, night, c)
                    await self.run_pending()
                if g.winner:  # a win at night (custom scripts: the Al-Hadikhia's last stand): the game ends now, no
                    self.tonight = None  # later step wakes anyone (the base scripts have none: their wins come by
                    return  # day, or at the dawn check)
        for p in g.players:  # (custom scripts: the Acrobat's check; the base scripts' characters do nothing here)
            for c in g.abilities(p):
                await settle(rules(c).end_of_night(self, p, night))
        await self.run_pending()
        if g.winner:
            self.tonight = None
            return
        g.expire('dawn')  # protections that last only tonight end (the Innkeeper's)
        self.tonight = None

        self.phase = 'day'
        self.emit('header', {'text': f'Day {n}'})
        # deaths are announced in seat order, so the order never says which ability killed whom
        deaths = sorted({p.seat: p for p in night.deaths}.values(), key=lambda p: p.seat)
        revived = sorted({p.seat: p for p in night.revived}.values(), key=lambda p: p.seat)
        self.emit('dawn', {'day': n, 'deaths': [d.name for d in deaths],
                           'narration': dawn_narration(self.rng, [d.name for d in deaths]),
                           **({'revived': [p.name for p in revived]} if revived else {})})
        if night.first:
            self.probe('dawn')
        await self.moment_judged('dawn')
        await self.run_pending()

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
        visitable, guessable = getattr(g.script, 'visitable', ()), getattr(g.script, 'guessable', ())
        for w, wave in enumerate(waves, start=1):
            requests = {}
            for name in wave:
                prompt = f'{head} — your turn{note}. {tail}'
                if not g[name].appears_alive:
                    prompt += ' (You are dead, but you can still ' + ('whisper.)' if private else 'talk.)')
                requests[name] = Request(kind, prompt, n, beat=beat, alive=g[name].appears_alive,
                                         mode='private' if private else 'public',
                                         claimable=[] if private else list(g.script.claimable),
                                         visitable=list(visitable) if private else [],
                                         guesses=[] if private or not guessable else list(g.script.all),
                                         chatter=self.chatter(name))
            acts = await self.ask_many(requests)
            if private:
                for name in wave:
                    visit = acts[name].get('visit') if visitable else None
                    if isinstance(visit, dict) and visit.get('character') in visitable:
                        if await self.visit_judged(name, visit, acts[name]):
                            continue  # the turn's one conversation was with the Storyteller
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
            await self.shots_judged(wave, acts)
            await self.public_abilities_judged(wave, acts)
            await self.run_pending()
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
            if getattr(self.g.script, 'visitable', ()):  # (scripts with the Savant or the Artist)
                tail += (' Or, instead of whispering, visit the Storyteller in private (`visit`): the town sees that '
                         'you went, never why. One visit a day.')
        else:
            note, tail = '', 'Say something to the town, or nothing. No whispering now.'
            if k == total:
                tail += ' This is the last beat before nominations.'
        await self.turns(n, order, 'beat', f'Day {n}, {"private time" if private else "town square"} {k} of {total}',
                         tail, WORDS['beat'], beat=k, private=private, note=note)

    async def shots_judged(self, names, acts):
        """Public day actions taken on these public turns, in order (the Slayer's shot, which anyone can claim)."""
        for name in names:
            t = acts[name].get('slayer_shot')
            if t in self.names and t != name and not self.g.winner:
                await self.slayer_judged(name, t)

    def shots(self, names, acts):
        now(self.shots_judged(names, acts))

    async def public_abilities_judged(self, names, acts):
        """Public day abilities claimed on these turns, beyond the Slayer's shot (the Gossip's statement): anyone may
        claim one, the town hears the claim, and it does something only for a real, working one."""
        g = self.g
        for name in names:
            use = acts[name].get('ability')
            if not isinstance(use, dict) or use.get('character') not in g.script.claimable or g.winner:
                continue
            c, target = use['character'], use.get('target') if use.get('target') in self.names else None
            text = clip(use.get('text'), WORDS['beat'])
            more = {}
            if rules(c).public_guesses:  # (player, character) guesses, as many as the ability takes (the Juggler's)
                more['guesses'] = [{'player': x['player'], 'character': x['character']}
                                   for x in use.get('guesses') or [] if isinstance(x, dict)
                                   and x.get('player') in self.names and x.get('character') in g.script.all
                                   ][:rules(c).public_guesses]
            self.emit('ability', {'player': name, 'character': c, **({'target': target} if target else {}),
                                  **({'text': text} if text else {}), **({'guesses': more['guesses']}
                                                                         if more.get('guesses') else {})})
            if await settle(rules(c).act_publicly(self, name, target, text, **more)) and target:
                if not self.prevent_death(g[target], c.lower()):
                    self.kill(g[target], c.lower(), g[name])
                    g.check_victory()

    def public_abilities(self, names, acts):
        """public_abilities_judged, synchronously (tests)."""
        now(self.public_abilities_judged(names, acts))

    async def visit_judged(self, name, visit, action=None):
        """`name` visits the Storyteller on a private-time turn, claiming `visit['character']`'s ability (the Savant,
        the Artist) and saying `visit['text']` (the Artist's question). Anyone may visit, so a bluff looks the same:
        the town sees who went (a public 'visit' event), never why; what was said is the Storyteller's (an audit
        event the judge hears). The character's `visited` answers privately if they have the ability, or believe
        they do; otherwise the Storyteller only nods. One visit a day: a second is refused (and the turn goes on). A
        visit is the turn's one conversation: a whisper sent with it is not sent. Returns whether the visit
        happened."""
        g, c = self.g, visit['character']
        seen = g.notes.setdefault('Visits', {})
        if seen.get(name) == self.day:
            self.emit('notice', {'text': '(You have already visited the Storyteller today: one visit a day.)'}, [name])
            return False
        seen[name] = self.day
        text = clip(visit.get('text'), WORDS['whisper'])
        if (action or {}).get('whispers'):
            self.emit('notice', {'text': '(Your whisper was not sent: you spent this turn with the Storyteller.)'},
                      [name])
        self.emit('visit', {'player': name})
        self.emit('visit_text', {'player': name, 'character': c, 'text': text}, 'audit')
        if not await settle(rules(c).visited(self, g[name], text)):
            self.inform(g[name], f'Day {self.day}: you visited the Storyteller, who listened and nodded. (You do not '
                                 f'have the {c}\'s ability, so nothing happens; the town saw only that you went.)')
        await self.run_pending()
        return True

    async def slayer_judged(self, shooter, target):
        g = self.g
        action = g.script.public_actions.get('slayer_shot')  # a script without a Slayer: nobody's shot does anything
        died = (await settle(action.act_publicly(self, shooter, target))) if action else False
        died = died and not self.prevent_death(g[target], 'slayer')
        self.emit('slayer', {'shooter': shooter, 'target': target, 'died': died})
        if died:
            self.kill(g[target], 'slayer')
            g.check_victory()

    def slayer(self, shooter, target):
        now(self.slayer_judged(shooter, target))

    async def execution(self, name):
        """Today's execution, after any decision it needs (whether the Pacifist saves a good player)."""
        for p in self.g.players:
            for c in self.g.abilities(p):
                await rules(c).before_execution(self, p, self.g[name])
        self.execute(name)

    def execute(self, name):
        """Execution is not death: an executed player may survive (the Tea Lady's neighbour, the Fool, a
        Pacifist's save; the town is not told why), and executing a dead player kills nobody. Either way it is
        today's execution."""
        g, p = self.g, self.g[name]
        won = None  # another player's ability ends the game on this execution (the Evil Twin's good twin)
        for q in g.players:
            for c in g.abilities(q):
                won = won or rules(c).execution(self, q, p)
        died = p.alive  # a player who only seems dead (the Zombuul) dies for real when executed again
        survived = died and self.prevent_death(p, 'execution')
        died = died and not survived
        self.executed_today = True
        g.executions.append({'player': name, 'day': self.day, 'died': died})
        self.emit('execution', {'player': name, 'died': died, **({'survived': True} if survived else {})})
        if died:
            g.alive_at_execution = g.alive_count()
            ends = rules(p.character).executed(self, p)  # the Saint's team loses
            self.kill(p, 'execution')
            g.executed_death = name
            if ends:
                g.winner, g.reason = ends
        if won and not g.winner:
            g.winner, g.reason = won
        g.check_victory()

    async def virgin_judged(self, nominator, nominee):
        """The nominee's character reacts to the nomination: True if that ended the day (the Virgin's ability
        executed the nominator; whether a Spy counts as a Townsfolk is a judged call)."""
        return await settle(rules(self.g[nominee].character).nominated(self, self.g[nominee], nominator))

    def virgin(self, nominator, nominee):
        return now(self.virgin_judged(nominator, nominee))

    async def nomination_judged(self, nominator, nominee):
        """Every ability reacts to the nomination (the Witch's curse kills the nominator; the nomination stands).
        True if that ended the game."""
        g = self.g
        deaths = len(g.death_log)
        for p in g.players:
            for c in g.abilities(p):
                await settle(rules(c).nomination(self, p, nominator, nominee))
        return len(g.death_log) > deaths and bool(g.check_victory())

    def vote_order(self, nominee):
        if nominee not in self.names:  # (batch 6: a nominee who is not a player: clockwise from the nominator)
            nominee = self.g.nominations[-1]['nominator']
        i = self.names.index(nominee)
        return [self.names[(i + k) % len(self.names)] for k in range(1, len(self.names) + 1)]

    async def vote(self, nominee, block, top):
        g, n = self.g, self.day
        needed = math.ceil(sum(p.appears_alive for p in g.players) / 2)  # of the players the town sees alive
        required = max(needed, top + 1)
        yes, voted, early = [], set(), {}
        hands = 0  # the yes votes: one per raised hand, unless an ability counts it as more (the Banshee's two)

        def free(q):  # may vote while dead without spending their ghost vote (the Banshee)
            return any(rules(c).free_vote(g, q) for c in g.abilities(q))

        def weight(q):
            return max(rules(c).vote_weight(g, q) for c in g.abilities(q))

        secret = self.secret_votes()  # (custom scripts: the Organ Grinder's eyes-closed voting)
        jinxed_butler = secret and any(rules(c).followers_blind(g, q) for q in g.players for c in g.abilities(q)
                                       if rules(c).secret_votes(g, q))

        def must(q):  # believes they must vote yes now (the Zealot), and whether their hand is raised regardless
            told = any(rules(c).must_vote(g, q) for c in dict.fromkeys([q.shown, *g.abilities(q)]))
            return told, any(rules(c).must_vote(g, q) and g.works(q, c) for c in g.abilities(q))

        # a secret vote earlier today (custom scripts: the Organ Grinder's, whose ability then ended) keeps its tally
        # secret: no block or tally from it is shown (finding S2; whether later votes stay secret is not ruled: they
        # are public, as before)
        hidden = getattr(self, 'secret_day', None) == n

        async def ask_vote(voter):
            p = g[voter]
            lines = [f'Vote: should {nominee} be executed? It takes {required} yes votes to put them on the block']
            if secret:  # eyes closed: no tally, no block, no hands seen
                lines = [f'Vote, eyes closed: should {nominee} be executed? The votes and the tally are secret (only '
                         'the Storyteller knows who is about to die)']
            elif hidden:
                lines = [f'Vote: should {nominee} be executed? It takes at least {needed} yes votes to put them on the '
                         'block, and more than any earlier vote today (an earlier vote was secret: only the '
                         'Storyteller knows its tally)']
            elif block:
                lines[0] += f' (replacing {block}, who has {top})'
            elif top:
                lines[0] += f' (more than the {top} of an earlier tied vote)'
            lines[0] += '.'
            if not secret:
                lines.append(f'Yes so far: {", ".join(yes) if yes else "none"} ({hands}).')
            if must(p)[0]:
                lines.append('You must vote yes on every nomination (5 or more players are alive).')
            if not p.appears_alive and not free(p):
                lines.append('You are dead: voting yes uses your one ghost vote.')
            if weight(p) > 1:
                lines.append(f'Your raised hand counts as {weight(p)} votes.')
            if jinxed_butler and rules(p.character).follows_master and p.alive and g.master:
                lines.append(f'Your master is {g.master}: you may raise your hand, but your vote counts only if they '
                             'vote yes too.')
            elif rules(p.character).follows_master and p.alive and g.master:  # poisoned or not: they can't tell
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
            return q.appears_alive or q.ghost_vote or free(q)

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
                if not jinxed_butler:  # (the Organ Grinder jinx: their hand is up, but it does not count)
                    self.emit('notice', {'text': f'(Your master {g.master} is not voting yes, so you cannot vote.)'},
                              [voter])
            if not v and must(p)[1]:  # a working Zealot's hand is raised regardless (custom scripts)
                v = True
                self.emit('notice', {'text': '(You are the Zealot: your hand is raised.)'}, [voter])
            ghost = v and not p.appears_alive and not free(p)  # a Zombuul who seems dead spends their token too
            if ghost:
                p.ghost_vote = False
            w = weight(p) if v else 1
            self.emit('vote', {'voter': voter, 'nominee': nominee, 'yes': v, 'ghost': ghost, 'text': remark,
                               **({'votes': w} if w != 1 else {})}, [voter] if secret else 'public')
            voted.add(voter)
            if v:
                yes.append(voter)
                hands += w
        count = hands
        if count >= needed and count > top:
            block, top, outcome = nominee, count, 'block'
        elif count >= needed and count == top:
            block, outcome = None, 'tie'
        else:
            outcome = 'short'
        self.emit('vote_result', {'nominee': nominee, 'votes': count, 'needed': required, 'outcome': outcome,
                                  'voters': yes}, 'audit' if secret else 'public')
        if secret:
            self.secret_day = n
            self.emit('text', {'text': f'The vote on {nominee} is over (eyes closed: the tally is secret).'})
        if g.nominations and g.nominations[-1]['nominee'] == nominee:
            # the voters' characters as they voted (the Flowergirl detects a Demon who voted, even one who changed
            # character later that day or night)
            g.nominations[-1].update(votes=count, voters=list(yes), outcome=outcome,
                                     characters={x: g[x].character for x in yes})
        return block, top

    async def vote_over_judged(self, nominee):
        """Whether an ability executes `nominee` at once now that the vote on them is over (Character.vote_over: the
        Vizier's, "If good voted, you may choose to execute immediately"). The base scripts have none."""
        g = self.g
        for p in g.players:
            for c in g.abilities(p):
                if not g.winner and await settle(rules(c).vote_over(self, p, nominee)):
                    return True
        return False

    def secret_votes(self):
        """Whether votes are secret now: an ability makes them so (Character.secret_votes: the Organ Grinder's)."""
        g = self.g
        return any(rules(c).secret_votes(g, q) for q in g.players for c in g.abilities(q))

    def nomination_limit(self, p):
        """How many nominations p may make today: one while alive (as the town sees it), else none, unless an ability
        says otherwise (Character.nomination_limit: the Banshee's two; a Golem who has nominated, none)."""
        limits = [x for x in (rules(c).nomination_limit(self.g, p) for c in self.g.abilities(p)) if x is not None]
        if not limits:
            return 1 if p.appears_alive else 0
        return 0 if 0 in limits else max(limits)

    async def nominations(self):
        """Rounds until a call gets no nomination. Each round: every living player who hasn't
        nominated today is asked at once whether to nominate (if several do, one is taken at random,
        as when hands go up together); then the accusation, the defense, one round of comments from
        everyone, and the clockwise vote."""
        g, n = self.g, self.day
        for c in g.script.all:  # (batch 6: a character that runs the day's nominations, Riot's riot; none elsewhere)
            if rules(c).runs_nominations and await rules(c).run_nominations(self):
                return
        self.phase = 'nominations'
        self.emit('nominations_open', {})
        nominators, nominees = {}, set()
        block, top = None, 0
        while not g.winner:
            eligible = [p.name for p in g.players if nominators.get(p.name, 0) < self.nomination_limit(p)]
            options = [x for x in self.names if x not in nominees]
            options += [x for x in g.script.nominees if x not in nominees]  # (batch 6: the Atheist's Storyteller)
            if not eligible or not options:
                break
            status = (f'{block} is on the block with {top} votes.' if block else
                      f'Nobody is on the block (an earlier vote tied at {top}).' if top else 'Nobody is on the block yet.')
            if self.secret_votes():  # (custom scripts: the Organ Grinder)
                status = 'Votes are secret today (eyes closed): only the Storyteller knows who is about to die.'
            elif getattr(self, 'secret_day', None) == n:  # (a secret vote earlier today: its tally stays secret)
                status = 'An earlier vote today was secret: only the Storyteller knows who is about to die.'
            prompt = (f'Day {n}, nominations. {status} Already nominated today: {", ".join(sorted(nominees)) or "nobody"}. '
                      'You may nominate someone (set `nominate`; your `say` is the accusation), or pass. Only '
                      'nominations are heard now: everyone can comment after the defense. No whispering now.')
            acts = await self.ask_many({name: Request('nominate', prompt, n, options=options) for name in eligible})
            await self.shots_judged(eligible, acts)
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
            nominators[nominator] = nominators.get(nominator, 0) + 1
            nominees.add(nominee)
            self.emit('nomination', {'nominator': nominator, 'nominee': nominee, 'text': accusation})
            g.nominations.append({'day': n, 'nominator': nominator, 'nominee': nominee,
                                  'character': g[nominator].character})  # the nominator's, as they nominated
            if nominee not in g.by_name:  # (batch 6: not a player, the Atheist's Storyteller: the nominator's
                if await self.nomination_judged(nominator, nominee):  # abilities react, none of a nominee's)
                    return
                self.emit('text', {'text': f'The {nominee} does not defend themself.'})
                order = list(self.names)
                self.rng.shuffle(order)
                await self.turns(n, order, 'comment', f'Day {n}, comments on the nomination of the {nominee}',
                                 'Say something to the town before the vote, or nothing (don\'t just announce your '
                                 'vote). No whispering now.', WORDS['comment'])
                if g.winner:
                    return
                block, top = await self.vote(nominee, block, top)
                continue
            if await self.virgin_judged(nominator, nominee):
                return
            if await self.nomination_judged(nominator, nominee):
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
            if await self.vote_over_judged(nominee):  # (custom scripts: the Vizier executes the nominee at once)
                await self.execution(nominee)
                await self.run_pending()
                return
        if g.winner:
            return
        if block and block not in g.by_name:  # (batch 6: the Atheist's Storyteller)
            self.executed_today = True
            await rules(g.script.nominees[block]).nominee_executed(self, block)
        elif block:
            await self.execution(block)
            await self.run_pending()
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
                await self.moment_judged('beat')
                await self.run_pending()
                if g.winner:
                    return
        self.probe('nominations')
        await self.moment_judged('nominations')
        if g.winner:
            return
        if not self.executed_today:  # a Storyteller's execution before nominations (madness) ends the day's
            await self.nominations()
        if g.winner:
            return
        for p in g.players:  # end-of-day abilities (the Mayor's win)
            for c in g.abilities(p):
                rules(c).end_of_day(self, p)
            if g.winner:
                return
        await self.moment_judged('dusk')
        await self.run_pending()

    async def judge_madness(self, p, about, must=True, since=None, after=None):
        """The Storyteller judges whether `p` broke their madness about `about` (a character, or a type such as
        'Outsider'; must=False: they must NOT be mad about it, as the Mutant) in what was said since day `since`
        (default today), and if so whether to execute them ("might be executed"). Both are judged decisions
        (state.madness_choice, madness_penalty_choice); the scripted Storyteller reads only what was said aloud
        (judge.madness_evidence), a judge hears what its `--judge-hears` allows. Only one execution a day: none if
        there was one today. A madness execution is announced, and is today's execution (before nominations, the
        day's nominations don't open). `after`, an event number: only what was said from then on (a later checkpoint
        the same day, so evidence already judged is not judged again). Returns whether they were executed."""
        from .judge import madness_evidence
        g = self.g
        if self.executed_today or g.winner:
            return False
        evidence = madness_evidence(self, p.name, about, self.day if since is None else since, 'public', after)
        if not (await self.decide_judged(madness_choice(g, p, about, must, evidence)))['yes']:
            return False
        if not (await self.decide_judged(madness_penalty_choice(g, p, about)))['yes']:
            return False
        self.emit('text', {'text': f'The Storyteller declares that {p.name} is executed.'})
        await self.execution(p.name)
        await self.run_pending()
        return True

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
            g.finish()
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
