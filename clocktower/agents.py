"""Seats and the Storyteller.

A seat receives the text of everything it saw since its last turn plus a prompt,
and returns an action dict (the JSON schema in schema.py). Model seats, random
seats (for tests) and human seats all implement the same `act`.
"""
from __future__ import annotations
import asyncio
import random
import time
from dataclasses import dataclass, field

from .llm import Reply


@dataclass
class Request:
    kind: str  # night | ravenkeeper | death_choice | decide (a yes or no) | beat | nominate | defense | comment | vote
    prompt: str
    day: int
    beat: int | None = None
    n_targets: int = 0          # night choices
    options: list = field(default_factory=list)   # legal targets / nominees
    alive: bool = True
    min_targets: int | None = None  # night choices beyond Trouble Brewing's: the fewest players (0: may choose no one)
    characters: list = field(default_factory=list)  # a character to choose too (the Gambler) or instead (the Courtier)
    mode: str = ''              # 'private' (whispers only) or 'public' (speech only)
    claimable: list = field(default_factory=list)  # public turns beyond Trouble Brewing: the characters whose day
    #                                                ability anyone may claim through the `ability` field (the Gossip)
    visitable: list = field(default_factory=list)  # private turns: the characters whose ability is used by visiting
    #                                                the Storyteller (the Savant, the Artist), through the `visit` field
    guesses: list = field(default_factory=list)  # public turns: the characters a claimed ability's guesses may name,
    #                                              when one takes guesses (the Juggler's), else []
    menu: list = field(default_factory=list)  # a night choice of an item from a list, by its number in `say` (batch
    #                                          6: the Wizard's wishes); random bots pick one now and then
    chatter: list = field(default_factory=list)  # turns on scripts with an ability that listens to what is said (the
    #                                              Mezepheles's word): lines a random bot may say (Character.chatter);
    #                                              only random bots read it


class ModelSeat:
    def __init__(self, conversation):
        self.conversation = conversation

    async def act(self, text, request: Request) -> Reply:
        return await self.conversation.send(text, {'kind': request.kind, 'day': request.day, 'beat': request.beat})

    async def probe(self, text, meta) -> Reply:
        """An out-of-game question on a fork of the conversation (see probe.py)."""
        return await self.conversation.send(text, {'kind': 'probe', **meta}, commit=False)


LINES = ['I have info, will share soon.', 'Who wants to claim first?', 'I trust Alex for now.',
         'That claim sounds off to me.', 'Let us not rush an execution.', 'I think we should nominate today.']


class RandomSeat:
    """Plays legal random moves. For tests only."""

    def __init__(self, name, rng: random.Random, names):
        self.name, self.rng, self.names = name, rng, names

    async def act(self, text, request: Request) -> Reply:
        r, others = self.rng, [n for n in self.names if n != self.name]
        a = {'say': '', 'whispers': [], 'nominate': None, 'vote': None, 'targets': [],
             'slayer_shot': None}
        if request.kind in ('night', 'ravenkeeper', 'death_choice') and request.min_targets is None:
            a['targets'] = r.sample(request.options, min(request.n_targets, len(request.options)))
        elif request.kind in ('night', 'ravenkeeper'):
            k = r.randint(request.min_targets, min(request.n_targets, len(request.options)))
            a['targets'] = r.sample(request.options, k)
            if request.characters:
                a['character'] = r.choice(request.characters)
            if request.menu and r.random() < 0.35:  # (batch 6: the Wizard's wishes; nothing drawn without a menu)
                a['say'] = str(r.randint(1, len(request.menu)))
        elif request.kind == 'beat':
            if r.random() < 0.5: a['say'] = r.choice(LINES)
            if r.random() < 0.3: a['whispers'] = [{'to': [r.choice(others)], 'text': 'psst, what are you?'}]
            if r.random() < 0.03: a['slayer_shot'] = r.choice(others)
            if request.claimable and r.random() < 0.08: a['ability'] = self.claim(request.claimable, request.guesses)
            if request.visitable and r.random() < 0.15: a['visit'] = self.visit(request.visitable)
            if request.chatter: self.chat(a, request)
        elif request.kind == 'nominate':
            if request.options and r.random() < 0.4:
                a['nominate'] = r.choice(request.options)
                a['say'] = 'You seem suspicious.'
        elif request.kind == 'comment':
            if r.random() < 0.3: a['say'] = r.choice(LINES)
            if request.claimable and r.random() < 0.04: a['ability'] = self.claim(request.claimable, request.guesses)
            if request.chatter: self.chat(a, request)
        elif request.kind == 'defense':
            a['say'] = 'I am good, I promise.'
        elif request.kind == 'vote':
            a['vote'] = r.random() < 0.5
        elif request.kind == 'decide':  # a yes/no choice an ability asks for (the Al-Hadikhia's live or die)
            a['vote'] = r.random() < 0.5
        return Reply(a)

    def chat(self, a, request):
        """(Scripts with an ability that listens to what is said: Request.chatter.) Now and then say one of its lines
        instead, aloud, or in the whisper of a private turn, so random play can trigger it. Scripts without one draw
        nothing more, so their random play is unchanged."""
        r = self.rng
        if r.random() < 0.3:
            line = r.choice(request.chatter)
            if request.mode == 'private' and a['whispers']:
                a['whispers'][0]['text'] = line
            elif request.mode != 'private':
                a['say'] = line

    def claim(self, claimable, guesses=()):
        """A claimed public ability (scripts beyond Trouble Brewing): a character, a player and a statement of one
        of the forms the Gossip's are checked in, or one only a judge can rule on; and, where an ability takes guesses
        (the Juggler's), up to five (player, character) guesses."""
        r = self.rng
        x = r.choice(self.names)
        statement = r.choice([f'{x} is evil.', f'{x} is good.', f'{x} is a Minion.', f'{x} is not the Demon.',
                              f'{x} is an Outsider.', f'The {r.choice(claimable)} is in play.',
                              f'I am the Gossip. My statement is: {x} is the {r.choice(claimable)}.',
                              'The Demon is wearing a hat.', f'{x} will be executed today.'])
        out = {'character': r.choice(claimable), 'target': x, 'text': statement}
        if guesses:  # (scripts without a guessing ability draw nothing more, so their random play is unchanged)
            out['guesses'] = [{'player': r.choice(self.names), 'character': r.choice(guesses)}
                              for _ in range(r.randint(0, 5))]
        return out

    def visit(self, visitable):
        """A visit to the Storyteller (scripts with the Savant or the Artist): a character's ability, and a question
        of a form the code answers or one only a judge can."""
        r = self.rng
        x, y = r.sample(self.names, 2)
        question = r.choice([f'Is {x} evil?', f'Is {x} the Demon?', f'Are {x} and {y} the same alignment?',
                             f'Is there a {r.choice(visitable)} in play?', f'Is the Demon {x} or {y}?',
                             'Are we winning?', ''])
        return {'character': r.choice(visitable), 'text': question}


class ScriptedStoryteller:
    """Makes every Storyteller choice by the policy in state.py (what an experienced human
    Storyteller would usually do, with some randomness). No API calls."""

    def __init__(self, rng: random.Random):
        self.rng = rng

    def choose(self, choice):
        return choice.options(self.rng)


class HumanSeat:
    """Waits for a move submitted through the web UI (see web.py). `timeout` (seconds, optional) passes
    the turn when nobody answers in time, the way a seat that says nothing passes; so does `away()`
    turning true (the player's page has stopped checking in), so a closed tab never stalls the table."""

    def __init__(self, name, timeout=None, away=None):
        self.name, self.timeout, self.away = name, timeout, away
        self.pending: Request | None = None
        self.future: asyncio.Future | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.turn = 0               # increments per request, so a late submit can't answer the next one
        self.deadline = None        # epoch seconds, when there is a timeout

    async def act(self, text, request: Request) -> Reply:
        self.loop = asyncio.get_running_loop()
        self.future = self.loop.create_future()
        self.turn += 1
        self.deadline = time.time() + self.timeout if self.timeout else None
        self.pending = request
        try:
            while not (self.away and self.away()):  # someone already gone passes at once
                wait = 2 if self.deadline is None else max(0, min(2, self.deadline - time.time()))
                try:
                    return Reply(await asyncio.wait_for(asyncio.shield(self.future), wait))
                except asyncio.TimeoutError:
                    if self.deadline and time.time() >= self.deadline:
                        return Reply({})
            return Reply({})
        finally:
            self.pending, self.future, self.deadline = None, None, None

    def submit(self, action: dict, turn=None):
        """Called from the web server thread. Returns False if nothing (or another turn) is pending."""
        future, loop = self.future, self.loop
        if not (future and loop) or (turn is not None and turn != self.turn):
            return False
        loop.call_soon_threadsafe(lambda: future.done() or future.set_result(action))
        return True
