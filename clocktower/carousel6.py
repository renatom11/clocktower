"""Batch 5 of the experimental characters (the official data's "carousel" edition): the Mezepheles, the Yaggababble and
the Amnesiac, the three the brief first kept for a design agreed with the owner (its batch 5 update brings them in), and
the one official jinx between them and a built character (the Yaggababble's with the Exorcist).

As in carousel.py to carousel5.py (whose helpers and conventions this module shares): each entry follows the wiki's How
to Run, and where the rules leave a question open, a comment says which reading the entry takes, and why
(docs/carousel-rulings.md, batch 5, lists them for review).

Two of them listen to what is said. Every word a player says, aloud or in a whisper, reaches the listening abilities
on the script (Character.listens and `heard`, a core hook that does nothing on any script without one), and a secret
word or phrase is said when its words are said together, as whole words, whatever the case or punctuation
(game.said). A near miss (game.nearly_said: "trusted" for "trust") is never counted by the scripted Storyteller; with a
judge it is the judge's call. The words and phrases are drawn from a short list of ordinary table talk
(data/storyteller/speech.json), a judge choosing among them, never inventing one.

The Amnesiac's ability is one of a curated list (AMNESIAC, below), drawn at setup the same way: most are a built
character's ability reworded, a few are small ones of the Amnesiac's own, and each is run by code here. The Amnesiac
guesses it by visiting the Storyteller (the Savant's and the Artist's channel) and is told how close the guess is:
hot, warm or cold (amnesiac_closeness).
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product
import json
from pathlib import Path

from . import carousel, carousel2, carousel3, snv
from .characters import CHARACTERS, Choose, Demon, Minion, Townsfolk, jinx, kind
from .state import POLICY, Choice, State, judged


# carousel.py to carousel5.py and snv.py may still be loading when this module is (whichever of the engine's modules is
# imported first): their names are used through the modules, at call time.

def ability(name):
    """The official ability text."""
    from . import official
    return official.role(name)['ability']


SPEECH = json.loads((Path(__file__).resolve().parent / 'data' / 'storyteller' / 'speech.json').read_text())


def secret_choice(g, p, character, pool, taken):
    """Which secret word (the Mezepheles's) or phrase (the Yaggababble's) `p` starts knowing: one of the curated list,
    not one another player already has (the Storyteller's judged call; the scripted style draws one at random)."""
    pool = [x for x in pool if x not in taken] or list(pool)
    what = 'word' if character == 'Mezepheles' else 'phrase'
    return judged(Choice(f'{character} {what}:{p.name}', [{'statements': [x]} for x in pool],
                         lambda r: {'statements': [r.choice(pool)]}), 'secret_' + what,
                  f'{p.name} ({character}) starts knowing a secret {what}: which, of this list? A fair one: ordinary '
                  'table talk a player might say by accident, not one they are sure to say.', recipient=p.name)


def near_miss_choice(game, speaker, text, phrase, form, holder, character):
    """Whether `form`, which `speaker` said (in `text`), counts as saying the secret word or phrase: a judge's call
    (the scripted Storyteller never counts a near miss, and is never asked). The rules judge's heuristic:
    judge.RulesJudge._speech_near_miss."""
    return judged(Choice(f'{character} near miss:{speaker}', [{'yes': True}, {'yes': False}], lambda r: {'yes': False}),
                  'speech_near_miss', f'{speaker} said "{text}". The {character} ({holder})\'s secret '
                  f'{"word" if character == "Mezepheles" else "phrase"} is "{phrase}", and they said "{form}": does '
                  'that count as saying it (yes)? Only a clear form of the same word or phrase should.', about=speaker,
                  recipient=holder, phrase=phrase, form=form, utterance=text)


def secret_of(g, character, name):
    return g.notes.get(character, {}).get(name)


async def give_secret(game, p, character, pool):
    """`p` starts knowing a secret word or phrase (kept in g.notes[character][p.name]), told at their first-night step
    or at once (Secret.tell)."""
    g = game.g
    recs = g.notes.setdefault(character, {})
    v = await game.decide_judged(secret_choice(g, p, character, pool, {r['secret'] for r in recs.values()}))
    recs[p.name] = {'secret': v['statements'][0], 'told': False, 'first': None, 'done': False, 'count': {}}
    return recs[p.name]


class Secret:
    """What the Mezepheles and the Yaggababble share: a secret drawn at setup (or when a player becomes them) for
    everyone who has the ability or believes they do (a Lunatic who believes they are the Yaggababble learns a phrase:
    nothing comes of it), told at their first-night step and again at each dawn, so it stays in view; and the bots'
    chatter, so random play can say it."""
    pool_key = ''
    what = ''
    listens = True
    setup_order = 9.6  # once the characters are final

    def pool(self):
        return SPEECH[self.pool_key]

    async def setup(self, game):
        for p in [q for q in game.g.players if q.shown == self.name or self.name in game.g.abilities(q)]:
            if not secret_of(game.g, self.name, p.name):
                await give_secret(game, p, self.name, self.pool())

    def told_text(self, rec):
        raise NotImplementedError

    def tell(self, game, p, rec):
        rec['told'] = True
        game.woken(p)
        game.inform(p, f'{snv.when(game)} — {self.name}: your secret {self.what} is "{rec["secret"]}". '
                    + self.told_text(rec))

    async def becomes(self, game, me):
        # a player who becomes it later (the Pit-Hag's, a Demon's jump, a swap) learns a new secret at once (a reading:
        # the old holder's was theirs)
        rec = await give_secret(game, me, self.name, self.pool())
        self.tell(game, me, rec)

    def remind(self, game, me):
        rec = secret_of(game.g, self.name, me.name)
        if rec and rec['told'] and me.alive and game.day > 1:
            game.inform(me, f'Day {game.day} — {self.name}: (a reminder) your secret {self.what} is '
                            f'"{rec["secret"]}".')

    def chatter(self, game, name):
        # every player's random bot may say any line of the list (most of them miss), a near miss now and then; the
        # player with the ability, theirs often (the Yaggababble must say it itself)
        lines = [f'{x[:1].upper()}{x[1:]}, I am not sure yet.' for x in self.pool()]
        lines += [f'I keep {x}ing about it.' for x in self.pool()[:3]]
        rec = secret_of(game.g, self.name, name)
        if rec and self.name in game.g.abilities(game.g[name]):
            lines += [f'{rec["secret"][:1].upper()}{rec["secret"][1:]}, that is all I will say.'] * len(lines)
        return lines

    def near_miss(self, game, speaker, text, phrase, holder):
        """The near misses in `text` to put to the judge (each at the next safe point: Game.later). The scripted
        Storyteller counts none, and is never asked."""
        from .game import nearly_said
        if game.judge is None:
            return []
        return nearly_said(text, phrase)


# ---- Minions -----------------------------------------------------------------------------------------------------

class Mezepheles(Secret, Minion):
    name = 'Mezepheles'
    ability = ability(name)
    pool_key = 'mezepheles_words'
    what = 'word'

    def told_text(self, rec):
        return ('The first good player to say it (aloud or in a whisper) turns evil that night. Players are not told '
                'the word; whether to steer someone into saying it is up to you.')

    async def resolve_night(self, game, night):
        g = game.g
        for p in [q for q in g.players if q.alive and (q.shown == self.name or self.name in g.abilities(q))]:
            rec = secret_of(g, self.name, p.name)
            if rec and not rec['told']:
                self.tell(game, p, rec)
        if night.first:
            return
        # "The 1st good player to say this word becomes evil that night": at its step, the night after the word was
        # said. Once a good player has said it, the ability is spent ("No Ability"), whether or not anyone turned:
        # drunk or poisoned now, nobody turns (a reading: its sobriety at night counts, as for every night effect)
        for holder, rec in list(g.notes.get(self.name, {}).items()):
            if not rec['first'] or rec['done']:
                continue
            h, t = g[holder], g[rec['first']['player']]
            rec['done'] = True
            g.reminders.append(f'{holder} (Mezepheles): {t.name} said the word (TURNS EVIL; NO ABILITY).')
            if not (h.alive and self.name in g.abilities(h)):
                continue
            if not g.works(h, self.name):
                snv.failed(game, h, self.name, 'nobody turned evil')
                continue
            if not t.evil:  # (told at once, in private: "you are now evil")
                await game.change(t, alignment='evil')

    def heard(self, game, speaker, text, public, seq):
        # the first good player (as they are when they say it; dead players too: they still talk) to say it, aloud or
        # in a whisper ("say", not "publicly": a reading), while a living player has the ability (drunk or not: what
        # counts is tested at night)
        from .game import said
        g = game.g
        p = g[speaker]
        for holder, rec in g.notes.get(self.name, {}).items():
            h = g[holder]
            if rec['done'] or p.evil or not (h.alive and self.name in g.abilities(h)):
                continue
            if rec['first'] and rec['first']['seq'] < seq:
                continue
            if said(text, rec['secret']):
                rec['first'] = {'player': speaker, 'seq': seq, 'day': game.day, 'public': public}
                continue
            for form in self.near_miss(game, speaker, text, rec['secret'], holder):
                game.later(lambda game, holder=holder, rec=rec, form=form: self.judge_near_miss(
                    game, speaker, text, form, holder, rec, seq, public))

    async def judge_near_miss(self, game, speaker, text, form, holder, rec, seq, public):
        if rec['done'] or (rec['first'] and rec['first']['seq'] < seq) or game.g[speaker].evil:
            return
        if (await game.decide_judged(near_miss_choice(game, speaker, text, rec['secret'], form, holder,
                                                      self.name)))['yes']:
            rec['first'] = {'player': speaker, 'seq': seq, 'day': game.day, 'public': public, 'near': form}

    def moment(self, game, me, when):
        if when == 'dawn' and me.character == self.name:
            self.remind(game, me)


# ---- Demons ------------------------------------------------------------------------------------------------------

def yaggababble_victim_choice(g, y, k, of, dead):
    """For the k-th of `of` times the Yaggababble said its phrase today, the player who dies tonight, or nobody ("a
    player might die"). Any living player but the Yaggababble (a reading) and those already chosen tonight. The
    scripted style: usually someone (POLICY 'yaggababble_kill'), a living good player."""
    alive = [q.name for q in g.players if q.appears_alive and q is not y and q.name not in dead]
    good = [x for x in alive if not g[x].evil]

    def style(r):
        if alive and r.random() < POLICY['yaggababble_kill']:
            return {'players': [r.choice(good or alive)]}
        return {'players': []}
    return judged(Choice(f'Yaggababble:{y.name}:{k}', [{'players': [x]} for x in alive] + [{'players': []}], style),
                  'yaggababble_kill', f'The Yaggababble ({y.name}) said its phrase {of} time{"" if of == 1 else "s"} '
                  f'publicly today: for time {k}, who dies tonight (or nobody: "a player might die")?', about=y.name)


class Yaggababble(Secret, Demon):
    name = 'Yaggababble'
    ability = ability(name)
    pool_key = 'yaggababble_phrases'
    what = 'phrase'
    kills_at_night = True

    def told_text(self, rec):
        return ('For each time you say it publicly (aloud, in the town square, an accusation, a defense or a comment) '
                'today, a player might die tonight. Whispers do not count, and nobody else learns the phrase.')

    def heard(self, game, speaker, text, public, seq):
        # "each time you said it publicly today": what the player with the ability says aloud (not in a whisper), each
        # time the phrase is said (twice in one sentence is twice), alive; drunk or not (it is tested at night)
        from .game import said
        g = game.g
        rec = secret_of(g, self.name, speaker)
        p = g[speaker]
        if not (public and rec and p.alive and self.name in g.abilities(p)):
            return
        n = said(text, rec['secret'])
        if n:
            rec['count'][game.day] = rec['count'].get(game.day, 0) + n
            return
        for form in self.near_miss(game, speaker, text, rec['secret'], speaker):
            game.later(lambda game, form=form: self.judge_near_miss(game, speaker, text, form, rec))

    async def judge_near_miss(self, game, speaker, text, form, rec):
        day = game.day
        if (await game.decide_judged(near_miss_choice(game, speaker, text, rec['secret'], form, speaker,
                                                      self.name)))['yes']:
            rec['count'][day] = rec['count'].get(day, 0) + 1

    async def resolve_night(self, game, night):
        g = game.g
        for p in [q for q in g.players if q.alive and (q.shown == self.name or self.name in g.abilities(q))]:
            rec = secret_of(g, self.name, p.name)
            if rec and not rec['told']:
                self.tell(game, p, rec)
        if night.first:
            return
        for y in [q for q in g.players if self.name in g.abilities(q)]:
            rec = secret_of(g, self.name, y.name)
            times = rec['count'].get(night.n - 1, 0) if rec else 0
            if not (times and y.alive):
                continue
            # the Exorcist jinx: if the Exorcist chose it tonight, it does not kill (without the jinx an exorcised
            # Yaggababble still kills: it does not wake to do so)
            if y.name in night.asleep and g.script.jinxed(self.name, 'Exorcist'):
                game.emit('text', {'text': f'[{y.name} (Yaggababble) was exorcised: no deaths from its phrase]'},
                          'audit')
                continue
            if not g.works(y, self.name):
                snv.failed(game, y, self.name, 'nobody died')
                continue
            dead = []
            for k in range(1, times + 1):  # each a Demon's kill: the Monk, the Soldier and the Princess stop it
                v = await game.decide_judged(yaggababble_victim_choice(g, y, k, times, dead))
                if v['players']:
                    dead.append(v['players'][0])
                    await game.attempt_kill_judged(g[v['players'][0]], 'demon', y, night)

    def moment(self, game, me, when):
        if when == 'dawn' and me.character == self.name:
            self.remind(game, me)


# ---- Townsfolk: the Amnesiac -------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Gift:
    """One ability the Amnesiac may have (AMNESIAC). `text` is what it does (for the Storyteller and the judge; never
    shown to the Amnesiac); `model` the built character whose ability it rewords ('' for one of the Amnesiac's own);
    `when`: 'first' (you start knowing), 'each' (each night), 'other' (each night but the first), 'once' (once per game,
    at night), 'other once' (once per game, not the first night), or 'passive' (a standing ability or one a death or a
    nomination triggers); `choose`, the players chosen at night (0: none; may_self: may choose themself); `keys`, the
    words a guess is judged against (amnesiac_closeness: stems, a guess word that starts with one matches); `family`,
    what kind of ability it is."""
    id: str
    text: str
    model: str
    when: str
    family: str
    keys: tuple
    choose: int = 0
    may_self: bool = True


INFO, PROTECT, DEATH, VOTE = 'information', 'protection', 'death', 'nominations and execution'
AMNESIAC = [
    # you start knowing (the first night, or the night they first have it)
    Gift('washerwoman', 'You start knowing that 1 of 2 players is a particular Townsfolk.', 'Washerwoman', 'first',
         INFO, ('townsfolk', 'two', 'pair', 'start')),
    Gift('librarian', 'You start knowing that 1 of 2 players is a particular Outsider (or that none are in play).',
         'Librarian', 'first', INFO, ('outsider', 'two', 'pair', 'start')),
    Gift('investigator', 'You start knowing that 1 of 2 players is a particular Minion.', 'Investigator', 'first',
         INFO, ('minion', 'two', 'pair', 'start')),
    Gift('chef', 'You start knowing how many pairs of evil players sit next to each other.', 'Chef', 'first', INFO,
         ('pair', 'evil', 'next', 'sit', 'number')),
    Gift('clockmaker', 'You start knowing how many steps from the Demon to its nearest Minion.', 'Clockmaker',
         'first', INFO, ('step', 'demon', 'minion', 'distance', 'number')),
    Gift('steward', 'You start knowing 1 good player.', 'Steward', 'first', INFO, ('good', 'player', 'start', 'one')),
    Gift('noble', 'You start knowing 3 players, 1 and only 1 of which is evil.', 'Noble', 'first', INFO,
         ('three', 'evil', 'player', 'start')),
    Gift('shugenja', 'You start knowing if your closest evil player is clockwise or anti-clockwise.', 'Shugenja',
         'first', INFO, ('clockwise', 'direction', 'closest', 'evil')),
    Gift('outsiders', 'You start knowing how many Outsiders are in play.', '', 'first', INFO,
         ('outsider', 'number', 'how many', 'start')),
    Gift('demon character', 'You start knowing which Demon is in play.', '', 'first', INFO,
         ('demon', 'which', 'character', 'start')),
    # each night (or each night*)
    Gift('empath', 'Each night, you learn how many of your 2 alive neighbours are evil.', 'Empath', 'each', INFO,
         ('neighbo', 'evil', 'number', 'each night')),
    Gift('undertaker', 'Each night*, you learn which character died by execution today.', 'Undertaker', 'other', INFO,
         ('execut', 'character', 'died', 'dead')),
    Gift('oracle', 'Each night*, you learn how many dead players are evil.', 'Oracle', 'other', INFO,
         ('dead', 'evil', 'number', 'how many')),
    Gift('flowergirl', 'Each night*, you learn if a Demon voted today.', 'Flowergirl', 'other', INFO,
         ('vote', 'demon', 'today')),
    Gift('town crier', 'Each night*, you learn if a Minion nominated today.', 'Town Crier', 'other', INFO,
         ('nominat', 'minion', 'today')),
    Gift('demon neighbour', 'Each night, you learn whether one of your 2 alive neighbours is the Demon.', '', 'each',
         INFO, ('neighbo', 'demon', 'each night')),
    Gift('executed alignment', 'Each night*, you learn the alignment of the player executed today.', '', 'other', INFO,
         ('execut', 'alignment', 'good', 'evil')),
    # choosing at night
    Gift('fortune teller', 'Each night, choose 2 players: you learn if either is a Demon.', 'Fortune Teller', 'each',
         INFO, ('demon', 'two', 'choose', 'either'), choose=2),
    Gift('dreamer', 'Each night, choose a player (not yourself): you learn 1 good and 1 evil character, 1 of which is '
         'correct.', 'Dreamer', 'each', INFO, ('character', 'good', 'evil', 'choose', 'correct'), choose=1,
         may_self=False),
    Gift('seamstress', 'Once per game, at night, choose 2 players (not yourself): you learn if they are the same '
         'alignment.', 'Seamstress', 'once', INFO, ('alignment', 'same', 'two', 'once'), choose=2, may_self=False),
    Gift('townsfolk check', 'Each night, choose a player: you learn if they are a Townsfolk.', '', 'each', INFO,
         ('townsfolk', 'choose', 'learn'), choose=1),
    Gift('alignment check', 'Once per game, at night, choose a player: you learn their alignment.', '', 'once', INFO,
         ('alignment', 'good', 'evil', 'once'), choose=1),
    Gift('monk', 'Each night*, choose a player (not yourself): they are safe from the Demon tonight.', 'Monk', 'other',
         PROTECT, ('safe', 'protect', 'demon', 'choose'), choose=1, may_self=False),
    Gift('shelter', 'Once per game, at night*, choose a player: they cannot die tonight.', '', 'other once', PROTECT,
         ('die', 'protect', 'safe', 'once'), choose=1),
    # standing abilities, and those a death or a nomination triggers
    Gift('soldier', 'You are safe from the Demon.', 'Soldier', 'passive', PROTECT, ('safe', 'demon', 'protect',
                                                                                     'immune')),
    Gift('fool', 'The 1st time you die, you don\'t.', 'Fool', 'passive', PROTECT, ('die', 'first', 'survive',
                                                                                   'once')),
    Gift('tea lady', 'If both your alive neighbours are good, they cannot die.', 'Tea Lady', 'passive', PROTECT,
         ('neighbo', 'good', 'die', 'protect')),
    Gift('virgin', 'The 1st time you are nominated, if the nominator is a Townsfolk, they are executed immediately.',
         'Virgin', 'passive', VOTE, ('nominat', 'townsfolk', 'execut', 'first')),
    Gift('mayor', 'If only 3 players live & no execution occurs, your team wins.', 'Mayor', 'passive', VOTE,
         ('three', 'win', 'execut', 'final')),
    Gift('ravenkeeper', 'If you die at night, you are woken to choose a player: you learn their character.',
         'Ravenkeeper', 'passive', DEATH, ('die', 'night', 'character', 'choose')),
    Gift('sage', 'If the Demon kills you, you learn that it is 1 of 2 players.', 'Sage', 'passive', DEATH,
         ('demon', 'kill', 'die', 'two')),
]
GIFTS = {x.text: x for x in AMNESIAC}
FAMILY_WORDS = {INFO: ('learn', 'know', 'info', 'told', 'tell', 'show'), PROTECT: ('safe', 'protect', 'save', 'surviv',
                                                                                    'cannot die', 'immune'),
                DEATH: ('die', 'death', 'dead', 'kill'), VOTE: ('nominat', 'vote', 'execut', 'win')}


def gift_choice(g, p):
    """The Amnesiac's ability, one of AMNESIAC (the Storyteller's judged call: a judge chooses among them, never
    inventing one; the scripted style draws one at random)."""
    texts = [x.text for x in AMNESIAC]
    return judged(Choice(f'Amnesiac ability:{p.name}', [{'statements': [t]} for t in texts],
                         lambda r: {'statements': [r.choice(texts)]}), 'amnesiac_ability',
                  f'{p.name} is the Amnesiac: which of these abilities do they have (they will not know it)?',
                  recipient=p.name)


def amnesiac_closeness(gift, guess):
    """How close a guess is to the ability (the scripted Storyteller's judgement; a judge may rule otherwise): 'hot'
    when it names the character whose ability it is, or two of its key words; 'warm' for one key word, or the right
    kind of ability (information, protection, a death or nominations); 'cold' otherwise."""
    from .game import words
    ws = words(guess)
    text = ' ' + ' '.join(ws) + ' '

    def has(key):
        k = ' '.join(words(key))
        return (f' {k}' in text) if ' ' in k else any(w.startswith(k) for w in ws)
    if gift.model and f' {" ".join(words(gift.model))} ' in text:
        return 'hot'
    hits = sum(1 for k in gift.keys if has(k))
    if hits >= 2:
        return 'hot'
    if hits == 1 or any(has(k) for k in FAMILY_WORDS[gift.family]):
        return 'warm'
    return 'cold'


def guess_choice(g, p, gift, guess):
    """What the Amnesiac learns of their guess: hot, warm or cold. Sober, any of the three is legal (it is a judgement,
    not a fact a test could check: amnesiac_closeness is the scripted Storyteller's); drunk, poisoned or under the
    Vortox, the code's closeness is what a working ability gives, and a misinformed answer another."""
    true = amnesiac_closeness(gift, guess)
    impaired = g.unreliable(p, 'Amnesiac')
    values = ['hot', 'warm', 'cold']

    def style(r):
        if impaired and g.misinformed(p, r):
            return {'statements': [r.choice([x for x in values if x != true])]}
        return {'statements': [true]}
    choice = Choice(f'Amnesiac guess:{p.name}', [{'statements': [x]} for x in values], style)
    return snv.info(choice, g, p, 'Amnesiac', f'{p.name} (Amnesiac) guesses their ability: "{guess}". It is: '
                    f'"{gift.text}". How close is the guess: hot (right, or nearly), warm (partly) or cold? The '
                    f'scripted Storyteller would say {true}.', (lambda v: v['statements'] == [true]) if impaired
                    else None, impaired, guess=guess, gift=gift.text)


def kind_choice(g, p, cid, question, sets, impaired):
    """A yes/no a working ability gives as some registration makes it: `sets`, one set of possible answers per player
    it is about (any of them true: yes). Misinformed: the other answer."""
    possible = {any(c) for c in product(*[sorted(s) for s in sets])} if sets else {False}

    def style(r):
        true = next(iter(possible)) if len(possible) == 1 else r.random() < POLICY['recluse_evil']
        return {'yes': not true if impaired and g.misinformed(p, r) else true}
    values = [True, False] if impaired else sorted(possible)
    return snv.info(Choice(cid, [{'yes': x} for x in values], style), g, p, 'Amnesiac', question,
                    lambda v: v['yes'] in possible, impaired)


def count_choice(g, p, cid, question, sets, most):
    """A number a working ability gives as some registration makes it (each player in `sets` counting if their set
    holds True). Misinformed: another number."""
    possible = {sum(c) for c in product(*[sorted(s) for s in sets])}
    impaired = g.unreliable(p, 'Amnesiac')

    def style(r):
        true = min(possible)
        if impaired and g.misinformed(p, r):
            return {'number': r.choice([x for x in range(0, most + 1) if x not in possible] or [true])}
        return {'number': true}
    values = list(range(0, most + 1)) if impaired else sorted(possible)
    return snv.info(Choice(cid, [{'number': x} for x in values], style), g, p, 'Amnesiac', question,
                    lambda v: v['number'] in possible, impaired)


def as_amnesiac(choice, gift):
    """A built character's information Choice given to the Amnesiac: the ability is the Amnesiac's (the Vortox and
    the Mathematician count it as a Townsfolk's), the model character named for the judge."""
    if choice is None or not choice.values:
        return None
    choice.context.update(ability='Amnesiac', model=gift.model, gift=gift.text)
    choice.context['question'] = f'[The Amnesiac, whose ability is: {gift.text}] {choice.context["question"]}'
    return choice


def info_for(game, p, gift, night):
    """(The information Choice, the text of what they learn) for an information gift tonight, or None."""
    from . import state
    g, i = game.g, gift.id
    chosen = (g.notes.get('Amnesiac', {}).get(p.name) or {}).get('chosen')
    picked = chosen[1] if chosen and chosen[0] == night.n else []
    imp = g.unreliable(p, 'Amnesiac')
    if i in ('washerwoman', 'librarian', 'investigator'):
        return as_amnesiac(state.pair_choice(g, p, gift.model), gift), lambda v: state.info_text(gift.model, v)
    if i == 'chef':
        return as_amnesiac(state.chef_choice(g, p), gift), lambda v: state.info_text('Chef', v)
    if i == 'clockmaker':
        return as_amnesiac(snv.clockmaker_choice(g, p), gift), lambda v: (
            f'the Demon is {v["number"]} step{"" if v["number"] == 1 else "s"} from its nearest Minion.')
    if i == 'steward':
        return as_amnesiac(carousel.steward_choice(g, p), gift), lambda v: f'{v["players"][0]} is good.'
    if i == 'noble':
        return as_amnesiac(carousel3.noble_choice(g, p), gift), lambda v: '{}, {} and {}: exactly one is evil.'.format(
            *sorted(v['players'], key=lambda x: g[x].seat))
    if i == 'shugenja':
        return as_amnesiac(carousel2.shugenja_choice(g, p), gift), lambda v: (
            f'your closest evil player is {"clockwise" if v["yes"] else "anticlockwise"}.')
    if i == 'outsiders':
        sets = [{kind(c) == 'Outsider' for c in g.registers_as(q, p)} for q in g.players]
        return (count_choice(g, p, f'Amnesiac outsiders:{p.name}', f'How many Outsiders does {p.name} (Amnesiac) '
                             'learn are in play?', sets, len(g.players)),
                lambda v: f'there {"is" if v["number"] == 1 else "are"} {v["number"]} Outsider'
                          f'{"" if v["number"] == 1 else "s"} in play.')
    if i == 'demon character':
        true = sorted({q.character for q in g.players if q.is_demon})
        if not true:
            return None
        values = g.script.demons if imp else true

        def style(r):
            if imp and g.misinformed(p, r):
                return {'character': r.choice([c for c in g.script.demons if c not in true] or true)}
            return {'character': r.choice(true)}
        return (snv.info(Choice(f'Amnesiac demon:{p.name}', [{'character': c} for c in values], style), g, p,
                         'Amnesiac', f'Which Demon does {p.name} (Amnesiac) learn is in play?',
                         lambda v: v['character'] in true, imp), lambda v: f'the {v["character"]} is in play.')
    if i == 'empath':
        return as_amnesiac(state.empath_choice(g, p), gift), lambda v: state.info_text('Empath', v)
    if i == 'undertaker':
        t = g.executed_death
        return (as_amnesiac(state.character_choice(g, p, 'Undertaker', t), gift),
                lambda v: state.info_text('Undertaker', v, t)) if t else None
    if i == 'oracle':
        return as_amnesiac(snv.oracle_choice(g, p), gift), lambda v: (
            f'{v["number"]} of the dead players {"is" if v["number"] == 1 else "are"} evil.')
    if i == 'flowergirl':
        return as_amnesiac(snv.yes_no(g, p, 'Flowergirl', snv.demon_voted(g, night.n - 1), 'Did a Demon vote today '
                                      f'(yes: true)? What does {p.name} learn?'), gift), lambda v: (
            'YES, a Demon voted today.' if v['yes'] else 'NO, no Demon voted today.')
    if i == 'town crier':
        return as_amnesiac(snv.yes_no(g, p, 'Town Crier', snv.minion_nominated(g, night.n - 1), 'Did a Minion '
                                      f'nominate today (yes: true)? What does {p.name} learn?'), gift), lambda v: (
            'YES, a Minion nominated today.' if v['yes'] else 'NO, no Minion nominated today.')
    if i == 'demon neighbour':
        nb = g.neighbours(p)
        sets = [{kind(c) == 'Demon' for c in g.registers_as(q, p)} for q in nb]
        return (kind_choice(g, p, f'Amnesiac neighbour:{p.name}', f'Is one of {p.name}\'s alive neighbours '
                            f'({" and ".join(q.name for q in nb)}) the Demon (yes)?', sets, imp),
                lambda v: 'YES, one of your alive neighbours is the Demon.' if v['yes'] else
                'NO, neither of your alive neighbours is the Demon.')
    if i == 'executed alignment':
        t = g.executed_death
        if not t:
            return None
        return (kind_choice(g, p, f'Amnesiac executed:{p.name}', f'Is {t}, executed today, evil (yes) to {p.name}?',
                            [g.registers_evil(g[t], p)], imp),
                lambda v: f'{t}, executed today, is {"evil" if v["yes"] else "good"}.')
    if i == 'fortune teller' and len(picked) == 2:
        return as_amnesiac(state.fortune_teller_choice(g, p, picked), gift), lambda v: state.info_text(
            'Fortune Teller', v, picked)
    if i == 'dreamer' and picked:
        t = picked[0]
        return as_amnesiac(snv.dreamer_choice(g, p, t), gift), lambda v: (
            f'{t} is either the {v["characters"][0]} or the {v["characters"][1]}.')
    if i == 'seamstress' and len(picked) == 2:
        return as_amnesiac(snv.seamstress_choice(g, p, picked), gift), lambda v: (
            f'{picked[0]} and {picked[1]} are {"" if v["yes"] else "NOT "}the same alignment.')
    if i == 'townsfolk check' and picked:
        t = picked[0]
        return (kind_choice(g, p, f'Amnesiac townsfolk:{p.name}', f'Is {t} a Townsfolk (yes) to {p.name}?',
                            [{kind(c) == 'Townsfolk' for c in g.registers_as(g[t], p)}], imp),
                lambda v: f'{t} is {"" if v["yes"] else "NOT "}a Townsfolk.')
    if i == 'alignment check' and picked:
        t = picked[0]
        return (kind_choice(g, p, f'Amnesiac alignment:{p.name}', f'Is {t} evil (yes) to {p.name}?',
                            [g.registers_evil(g[t], p)], imp), lambda v: f'{t} is {"evil" if v["yes"] else "good"}.')
    return None


class Amnesiac(Townsfolk):
    name = 'Amnesiac'
    ability = ability(name)
    info = True
    visit = True  # the guess: a private visit to the Storyteller by day (the Savant's and the Artist's channel)
    setup_order = 9.6
    wakes_before = 'Demon'  # its step, before the Demons' (its ability may protect), its information at the night's end
    night_choice = Choose(players=1, prompt='Your ability asks you to choose a player.')  # (the shape: night_spec)

    @staticmethod
    def rec(g, p):
        return g.notes.get('Amnesiac', {}).get(p.name)

    @classmethod
    def gift(cls, g, p):
        r = cls.rec(g, p)
        return GIFTS[r['gift']] if r else None

    @staticmethod
    def working(g, p):
        return g.works(p, 'Amnesiac')

    async def draw(self, game, p):
        g = game.g
        v = await game.decide_judged(gift_choice(g, p))
        g.notes.setdefault('Amnesiac', {})[p.name] = {'gift': v['statements'][0], 'started': False, 'chosen': None,
                                                      'guesses': []}
        snv.fresh(g, p, self.name)
        g.reminders.append(f'{p.name} (Amnesiac): {v["statements"][0]}')

    async def setup(self, game):
        # drawn for everyone who has the ability or believes they do (a Drunk who believes they are the Amnesiac:
        # nothing comes of theirs), who is told how to guess
        g = game.g
        for p in [q for q in g.players if snv.has(g, q, self.name)]:
            if not self.rec(g, p):
                await self.draw(game, p)
                carousel5_intro(g, p.name, 'You do not know your ability (the Storyteller does). You may be woken at '
                                'night to choose players, or told things, without being told why. Each day you may '
                                'guess it: visit the Storyteller in private (`visit`, as the Amnesiac) and describe it '
                                'in `text`; you learn how close you are: hot, warm or cold.')

    async def becomes(self, game, me):
        # a player who becomes the Amnesiac later (the Pit-Hag's), or gains its ability (the Philosopher's, the
        # Cannibal's): a new ability is drawn, and they are told they have one they do not know
        await self.draw(game, me)
        game.inform(me, f'{snv.when(game)} — Amnesiac: you do not know your ability. Each day you may visit the '
                        'Storyteller to guess it (`visit`, as the Amnesiac, the guess in `text`): hot, warm or cold.')

    def night_spec(self, game, me, night):
        g = game.g
        gift = self.gift(g, me)
        if gift is None or not gift.choose:
            return None
        if gift.when in ('other', 'other once') and night.first:
            return None
        once = gift.when in ('once', 'other once')
        if once and snv.used(g, me, self.name):
            return None
        k = gift.choose
        if night is not None:  # (asked at its step tonight: what it chose there is its own, not another ability's)
            self.rec(g, me)['asked'] = night.n
        return Choose(players=k, may_self=gift.may_self, optional=once,
                      prompt=f'Your ability asks you to choose {"a player" if k == 1 else f"{k} players"}'
                             f'{"" if gift.may_self else " (not yourself)"}. You are not told why.'
                             + (' It works once per game: or choose no one, to keep it for a later night.' if once
                                else ''))

    async def resolve_night(self, game, night):
        # its step (before the Demons'): what was chosen is acted on (a protection) or kept for the night's end (the
        # information). A Drunk who believes they are the Amnesiac is woken as one and told things here (all false
        # or true by the Drunk's chance: their own ability does nothing)
        g = game.g
        for p in [q for q in snv.believers(g, self.name) if self.rec(g, q)]:
            gift, rec = self.gift(g, p), self.rec(g, p)
            asked = rec.get('asked') == night.n and p.name in night.chosen
            picked = night.chosen[p.name] if asked else None
            if picked is not None and gift.choose:
                if len(picked) < gift.choose:
                    continue  # (none chosen: a once-per-game one is kept for a later night)
                if gift.when in ('once', 'other once'):
                    snv.use(g, p, self.name)  # spent even if drunk or poisoned
                rec['chosen'] = (night.n, list(picked))
                if gift.family == PROTECT and self.name in g.abilities(p):
                    if not self.working(g, p):
                        snv.failed(game, p, self.name, 'protected no one')
                    elif gift.id == 'monk':
                        g.add(State('safe', picked[0], source=p.name, until='night'))
                    elif gift.id == 'shelter':
                        g.add(State('safe', picked[0], source=p.name, until='dawn', against='any'))
            if self.name not in g.abilities(p):  # (the Drunk's: at once)
                await self.learn(game, p, gift, night)

    def end_of_night(self, game, me, night):
        return self.learn(game, me, self.gift(game.g, me), night) if self.rec(game.g, me) else None

    async def learn(self, game, p, gift, night):
        """What an information gift tells `p` tonight (or a death triggered: the Ravenkeeper's, the Sage's)."""
        g = game.g
        rec = self.rec(g, p)
        if gift.id == 'ravenkeeper':
            return await self.ravenkeeper(game, p, night)
        if gift.id == 'sage':
            return await self.sage(game, p, night)
        if gift.family != INFO or not p.alive:
            return
        if gift.when == 'first':
            if rec['started']:
                return
            rec['started'] = True
        elif gift.when == 'other' and night.first:
            return
        told = info_for(game, p, gift, night)
        if told and told[0] is not None:
            await snv.learn(game, p, self.name, told[0], lambda v: f'your ability tells you: {told[1](v)}')

    async def ravenkeeper(self, game, p, night):
        from . import state
        g = game.g
        if p.alive or p not in night.deaths or self.rec(g, p).get('raven') == night.n:
            return
        self.rec(g, p)['raven'] = night.n
        req = game.request('ravenkeeper', f'Night {night.n}: you were killed in the night. Your ability (Amnesiac) '
                                          'wakes you to choose a player (`targets`).', night.n, n_targets=1,
                           options=game.names)
        t = game.targets(p.name, await game.ask(p.name, req), req)[0]
        choice = as_amnesiac(state.character_choice(g, p, 'Ravenkeeper', t), GIFTS[self.rec(g, p)['gift']])
        await snv.learn(game, p, self.name, choice, lambda v: f'your ability tells you: {t} is the {v["character"]}.')

    async def sage(self, game, p, night):
        g = game.g
        death = next((d for d in g.death_log if d['player'] == p.name and d['day'] == night.n
                      and d['phase'] == 'night' and d['cause'] == 'demon' and d['source']), None)
        if p.alive or not death or self.rec(g, p).get('sage') == night.n:
            return
        self.rec(g, p)['sage'] = night.n
        choice = as_amnesiac(snv.sage_choice(g, p, death['source']), GIFTS[self.rec(g, p)['gift']])
        if choice:
            await snv.learn(game, p, self.name, choice, lambda v: 'your ability tells you: the Demon who killed you is '
                            '{} or {}.'.format(*sorted(v['players'], key=lambda x: g[x].seat)))

    # ---- the standing abilities (for the Amnesiac's own character: the engine asks these of a player's character)
    def holds(self, g, me, gift_id):
        gift = self.gift(g, me)
        return gift is not None and gift.id == gift_id and me.character == self.name and self.working(g, me)

    def safe_from_demon(self, g, me):
        return self.holds(g, me, 'soldier')

    def protects(self, g, me, other, cause):
        if not self.holds(g, me, 'tea lady'):
            return False
        nb = g.neighbours(me)
        return other in nb and not any(q.evil for q in nb)

    def survives(self, game, me, cause):
        g = game.g
        gift = self.gift(g, me)
        if gift is None or gift.id != 'fool' or me.character != self.name or snv.used(g, me, 'Amnesiac fool'):
            return False
        if not self.working(g, me):
            return False
        snv.use(g, me, 'Amnesiac fool')
        return True

    async def nominated(self, game, me, nominator):
        from . import state
        g = game.g
        gift = self.gift(g, me)
        if gift is None or gift.id != 'virgin' or snv.used(g, me, 'Amnesiac virgin'):
            return False
        snv.use(g, me, 'Amnesiac virgin')  # the first nomination, working or not
        if not self.working(g, me):
            snv.failed(game, me, self.name, 'the nominator was not executed')
            return False
        registers = {kind(c) == 'Townsfolk' for c in g.registers_as(g[nominator])}
        townsfolk = next(iter(registers))
        if len(registers) > 1:
            townsfolk = (await game.decide_judged(state.virgin_choice(g, me, g[nominator])))['yes']
        if not townsfolk:
            return False
        game.emit('virgin', {'nominator': nominator, 'nominee': me.name})
        game.execute(nominator)
        return True

    def end_of_day(self, game, me):
        g = game.g
        if self.gift(g, me) and self.gift(g, me).id == 'mayor' and not game.executed_today and g.alive_count() == 3 \
                and self.working(g, me) and not g.winner:
            g.winner, g.reason = me.alignment, f'Three players remain, there was no execution, and {me.name} lives.'

    async def visited(self, game, me, text):
        # "Each day, privately guess what it is": one visit a day (the engine's), alive, with the ability or believing
        # it (the Drunk's guess is answered as misinformation); an empty guess is not one (they are asked for it)
        g = game.g
        if not (me.alive and snv.has(g, me, self.name) and self.rec(g, me)):
            return False
        if not (text or '').strip():
            game.inform(me, f'Day {game.day} — Amnesiac: describe your guess in `text` when you visit.')
            return True
        gift = self.gift(g, me)
        v = (await game.decide_judged(guess_choice(g, me, gift, text)))['statements'][0]
        self.rec(g, me)['guesses'].append({'day': game.day, 'guess': text, 'answer': v})
        game.woken(me)
        game.inform(me, f'Day {game.day} — Amnesiac: you guessed "{text}". The Storyteller says: {v.upper()} ('
                        + {'hot': 'right, or very nearly', 'warm': 'partly right', 'cold': 'not close'}[v] + ').')
        return True


def carousel5_intro(g, name, text):
    from .carousel5 import intro_line
    intro_line(g, name, text)


CHARACTERS.update({c.name: c() for c in [Mezepheles, Yaggababble, Amnesiac]})


# ---- Batch 5's jinxes (docs/carousel-rulings.md, batch 5) --------------------------------------------------------

jinx('Yaggababble', 'Exorcist', 'carousel6.Yaggababble.resolve_night')
