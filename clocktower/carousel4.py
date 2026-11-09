"""Batch 3b of the experimental characters (the official data's "carousel" edition): the Alsaahir, Huntsman, Snitch,
Knight, Choirboy, King, Cult Leader, Lord of Typhon and Lleech, and every official jinx between them and a built
character (the Boffin's with the Cult Leader among them). With them the World Championship's Buyer's Remorse plays end
to end.

As in carousel.py to carousel3.py (whose helpers and conventions this module shares): each entry follows the wiki's How
to Run, and where the rules leave a question open, a comment says which reading the entry takes, and why
(docs/carousel-rulings.md, batch 3b, lists them for review). Each implemented jinx is declared at the end with `jinx`;
a jinx that changes another module's character is guarded there by `Script.jinxed`, so scripts without both
characters play as before.
"""
from __future__ import annotations

from . import carousel2, snv
from .characters import CHARACTERS, Choose, Demon, Outsider, Townsfolk, jinx, kind, rules
from .state import POLICY, Choice, State, bluffs_choice, judged


# carousel.py to carousel3.py and snv.py may still be loading when this module is (whichever of the engine's modules is
# imported first): their names are used through the modules, at call time.

def ability(name):
    """The official ability text."""
    from . import official
    return official.role(name)['ability']


def convertible(g, by, types=('Townsfolk',), order=0.0):
    """Players a setup step may give another character: of `types`, not `by`, not one whose own setup step has run
    (setup_order below `order`: the Alchemist, the Village Idiots) nor one whose illusion is dealt with its setup (the
    Drunk, the Lunatic)."""
    return [q.name for q in g.players if kind(q.character) in types and q is not by
            and not (rules(q.character).setup_order is not None and rules(q.character).setup_order < order)
            and not rules(q.character).always_drunk and not rules(q.character).wakes_at_own_step]


def add_character(game, by, character, order):
    """A setup modifier that names a character ([+the King], [+the Damsel]): if it is on the script and not in play, it
    takes the seat of a dealt character of its own type (so the counts hold), or, with none, of a Townsfolk. Returns
    whether it was added (docs/carousel-rulings.md, batch 3b)."""
    g = game.g
    if character not in g.script.all or any(q.character == character for q in g.players):
        return False
    pool = convertible(g, by, (kind(character),), order) or convertible(g, by, ('Townsfolk',), order)
    if not pool:
        return False
    x = game.decide(judged(Choice(f'Add {character}', [{'players': [x]} for x in pool],
                                  lambda r: {'players': [r.choice(pool)]}), 'add_character',
                           f'The {by.shown} adds the {character}: whose token does it take?'))['players'][0]
    game.transition(g[x], character, how='dealt', quiet=True)
    return True


# ---- Townsfolk ---------------------------------------------------------------------------------------------------

def alsaahir_right(g, guesses):
    """Whether `guesses` ([{player, character}]) name exactly the players who are Minions, as Minions, and those who are
    Demons, as Demons: a guess counts by the type of the character named (the Grimoire's truth, alive or dead)."""
    named = {}
    for x in guesses:
        if kind(x['character']) in ('Minion', 'Demon'):
            named[x['player']] = kind(x['character'])
    truth = {q.name: kind(q.character) for q in g.players if kind(q.character) in ('Minion', 'Demon')}
    return bool(truth) and named == truth


class Alsaahir(Townsfolk):
    name = 'Alsaahir'
    ability = ability(name)
    public_action = 'ability'  # a public guess, through the shared `ability` field's `guesses`
    public_guesses = 15  # every player, each named with a Minion or a Demon character

    def act_publicly(self, game, actor, target, text=None, guesses=()):
        # once a day, alive (a dead Alsaahir has no ability); the guess names every Minion and every Demon, by type,
        # alive or dead, as the Grimoire has them (no misregistration: a reading); right, with a working ability:
        # good wins at once
        g = game.g
        p = g[actor]
        if not (p.alive and self.name in g.abilities(p)) or not guesses:
            if p.alive and p.shown == self.name and not guesses:
                game.inform(p, f'Day {game.day} — Alsaahir: no guess heard (name each player you guess in `guesses`, '
                               'with a Minion character for a Minion and a Demon character for a Demon).')
            return False
        seen = g.notes.setdefault('Alsaahir guessed', {})
        if seen.get(p.name) == game.day:
            return False  # one guess a day
        seen[p.name] = game.day
        right = alsaahir_right(g, guesses)
        if right and not g.works(p, self.name):
            snv.failed(game, p, self.name, 'a right guess did not win')
        elif right:
            g.winner, g.reason = 'good', (f'{p.name}, the Alsaahir, publicly guessed which players are the Minions and '
                                          'which the Demons: good wins.')
        return False


class Huntsman(Townsfolk):
    name = 'Huntsman'
    ability = ability(name)
    setup_order = 0.6  # after the Marionette's (the jinx: a Marionette who believes they are the Huntsman)
    night_choice = Choose(players=1, optional=True, alive_only=True,
                          prompt='Once per game: choose a living player: the Damsel, if chosen, becomes a Townsfolk '
                                 'not in play (or choose no one, to wait).')

    async def setup(self, game):
        # [+the Damsel]: for a real Huntsman, and for a Marionette who believes they are one (the jinx); not for a
        # Drunk who believes it (a reading: a setup modifier belongs to the character in play). A forced setup keeps its
        # characters
        g = game.g
        if game.forced:
            return
        for q in g.players:
            if q.character == self.name or (q.shown == self.name and q.character == 'Marionette'
                                            and g.script.jinxed('Marionette', self.name)):
                add_character(game, q, 'Damsel', self.setup_order)
                return

    def night_spec(self, game, me, night):
        return None if snv.used(game.g, me, self.name) else self.night_choice

    async def resolve_night(self, game, night):
        g = game.g
        # a Philosopher's too, each once; and a player who only believes they are the Huntsman (the Drunk), who spends
        # it as one. Any player chosen spends it
        for p in [q for q in snv.believers(g, self.name) if q.name in night.chosen]:
            t = (night.chosen[p.name] or [None])[0]
            if not t or snv.used(g, p, self.name):
                continue
            snv.use(g, p, self.name)
            target = g[t]
            if self.name not in g.abilities(p) or target.character != 'Damsel':
                continue
            if not g.works(p, self.name):
                snv.failed(game, p, self.name, 'the Damsel was not changed')
                continue
            in_play = {q.character for q in g.players} | {q.shown for q in g.players}
            towns = [c for c in g.script.townsfolk if c not in in_play and rules(c).setup_order is None]
            if not towns:
                continue
            c = (await game.decide_judged(judged(Choice(f'Huntsman:{p.name}', [{'character': c} for c in towns],
                                                        lambda r: {'character': r.choice(towns)}),
                                                 'huntsman_townsfolk', f'The Huntsman ({p.name}) chose the Damsel '
                                                 f'({t}): which Townsfolk not in play does she become?',
                                                 recipient=t)))['character']
            game.woken(target)
            await game.change(target, character=c)


def knight_choice(g, p):
    """The Knight's two players: neither can register as the Demon. Drunk, poisoned or under the Vortox: any two,
    misinformed with the Demon among them."""
    from itertools import combinations
    others = [q.name for q in g.players if q is not p]

    def demon(x):
        return any(kind(c) == 'Demon' for c in g.registers_as(g[x], p))

    def never(x):
        return not all(kind(c) == 'Demon' for c in g.registers_as(g[x], p))
    pairs = [sorted(t, key=lambda x: g[x].seat) for t in combinations(others, 2)]
    true = [t for t in pairs if never(t[0]) and never(t[1])]
    impaired = g.unreliable(p, 'Knight')
    values = pairs if impaired or not true else true

    def style(r):
        if impaired and g.misinformed(p, r):
            false = [t for t in pairs if any(g[x].is_demon for x in t)] or pairs
            return {'players': r.choice(false)}
        safe = [x for x in others if not demon(x)] or [x for x in others if never(x)]
        if len(safe) >= 2:
            return {'players': sorted(r.sample(safe, 2), key=lambda x: g[x].seat)}
        return {'players': r.choice(true or pairs)}
    return snv.info(Choice(f'Knight:{p.name}', [{'players': t} for t in values], style), g, p, 'Knight',
                    f'Which two players, neither of them the Demon, does {p.name} (Knight) learn?',
                    lambda v: all(never(x) for x in v['players']), impaired)


class Knight(Townsfolk):
    name = 'Knight'
    ability = ability(name)
    info = True

    async def show(self, game, p):
        g = game.g
        if len(g.players) < 3:
            return
        await snv.learn(game, p, self.name, knight_choice(g, p),
                        lambda v: '{} and {} are not the Demon.'.format(*v['players']))

    async def resolve_night(self, game, night):
        if night.first:
            for p in snv.believers(game.g, self.name):
                await self.show(game, p)

    async def becomes(self, game, me):
        if me.alive and not (game.tonight is not None and game.tonight.first):
            await self.show(game, me)


def king_choice(g, p):
    """The King's alive character: one a living player (not the King, unless nobody else lives) can register as.
    Drunk, poisoned or under the Vortox: any character on the script, misinformed with one no living player has."""
    alive = [q for q in g.players if q.appears_alive and q is not p] or [p]
    true = sorted({c for q in alive for c in g.registers_as(q, p)})
    impaired = g.unreliable(p, 'King')
    values = list(g.script.all) if impaired or not true else true

    def style(r):
        if impaired and g.misinformed(p, r):
            false = [c for c in g.script.all if c not in true] or list(g.script.all)
            return {'character': r.choice(false)}
        if not alive:
            return {'character': r.choice(values)}
        q = r.choice(alive)
        regs = sorted(g.registers_as(q, p))
        return {'character': q.character if q.character in regs else r.choice(regs)}
    return snv.info(Choice(f'King:{p.name}', [{'character': c} for c in values], style), g, p, 'King',
                    f'Which character of a living player does {p.name} (King) learn?',
                    lambda v: v['character'] in true, impaired)


class King(Townsfolk):
    name = 'King'
    ability = ability(name)
    info = True

    @staticmethod
    def due(g):
        """Whether the King learns tonight: the dead (as the town sees them) equal or outnumber the living; with the
        Leviathan in play (its jinx), once any player is dead."""
        dead = sum(1 for q in g.players if not q.appears_alive)
        if dead and g.script.jinxed('Leviathan', 'King') and any(q.character == 'Leviathan' for q in g.players):
            return True
        return dead >= len(g.players) - dead

    def tell_demon(self, game, me, demon):
        g = game.g
        told = g.notes.setdefault('King told', [])
        if (me.name, demon.name) in told or not demon.alive:
            return
        told.append((me.name, demon.name))
        game.woken(demon)
        game.inform(demon, f'{snv.when(game)} — King: {me.name} is the King.')

    async def resolve_night(self, game, night):
        g = game.g
        if night.first:
            # "The Demon knows you are the King": every Demon in play, of a real King (a Drunk's King has no ability)
            for k in [q for q in g.players if q.character == self.name]:
                for d in [q for q in g.players if q.is_demon]:
                    self.tell_demon(game, k, d)
        if not self.due(g):
            return
        for p in snv.believers(g, self.name):
            await snv.learn(game, p, self.name, king_choice(g, p), lambda v: f'the {v["character"]} is alive.')

    def becomes(self, game, me):
        for d in [q for q in game.g.players if q.is_demon]:
            self.tell_demon(game, me, d)

    def changed(self, game, me, other):
        # a player who becomes a Demon later (a starpass, the Summoner's, the Pit-Hag's) learns it too
        if me.character == self.name and other.is_demon:
            self.tell_demon(game, me, other)


def choirboy_choice(g, p, demon):
    """The player the Choirboy learns is the Demon; drunk, poisoned or under the Vortox, any player."""
    others = [q.name for q in g.players if q is not p]
    impaired = g.unreliable(p, 'Choirboy')
    values = others if impaired else [demon]

    def style(r):
        if impaired and g.misinformed(p, r):
            return {'players': [r.choice([x for x in others if x != demon] or others)]}
        return {'players': [demon]}
    return snv.info(Choice(f'Choirboy:{p.name}', [{'players': [x]} for x in values], style), g, p, 'Choirboy',
                    f'The Demon killed the King: which player does {p.name} (Choirboy) learn is the Demon?',
                    lambda v: v['players'] == [demon], impaired)


class Choirboy(Townsfolk):
    name = 'Choirboy'
    ability = ability(name)
    info = True
    setup_order = -0.45  # [+the King]: after the Village Idiot's extras (which would take the King's token)

    async def setup(self, game):
        g = game.g
        if game.forced:
            return
        for q in g.players:
            if q.character == self.name:  # (a real one: a Drunk's Choirboy adds no King, a reading)
                add_character(game, q, 'King', self.setup_order)
                return

    async def resolve_night(self, game, night):
        g = game.g
        if night.first:
            return
        # a King killed tonight by a Demon's attack (a Mayor's bounce onto the King too): the Demon who attacked, or
        # the Demon now if they are no longer one
        for d in [d for d in g.death_log if d['day'] == night.n and d['phase'] == 'night' and d['cause'] == 'demon'
                  and d['source'] and g[d['player']].character == 'King']:
            src = g[d['source']]
            demon = src if src.is_demon else g.demon()
            if demon is None:
                continue
            for p in snv.believers(g, self.name):
                await snv.learn(game, p, self.name, choirboy_choice(g, p, demon.name),
                                lambda v: f'the Demon killed the King: {v["players"][0]} is the Demon.')


def cult_alignment_choice(g, p, sides):
    """Which alive neighbour's alignment the Cult Leader becomes, when they differ (POLICY 'cult_leader_evil')."""
    return judged(Choice(f'Cult Leader:{p.name}', [{'yes': x == 'evil'} for x in sides],
                         lambda r: {'yes': r.random() < POLICY['cult_leader_evil']}), 'cult_leader_alignment',
                  f'The Cult Leader ({p.name}) has a good and an evil alive neighbour: do they become evil (yes) or '
                  'good (no)?', recipient=p.name)


async def cult_vote(game, leader):
    """A cult vote, called aloud by `leader`: every player, alive or dead, says in secret (eyes closed) whether they
    join. If every good player joined and `leader` has a working Cult Leader's ability, their team wins; otherwise the
    Storyteller says only that the vote is over."""
    g = game.g
    if g.winner:
        return
    game.emit('text', {'text': f'{leader.name} calls a cult vote: with eyes closed, each player chooses whether to '
                               'join the cult.'})
    text = (f'Day {game.day} — cult vote ({leader.name}\'s): do you join the cult? (`vote` true: join, false: do '
            'not. Your choice is secret.)')
    reqs = {q.name: game.request('decide', text, game.day) for q in g.players}
    acts = await game.ask_many(reqs)
    joined = {}
    for name, a in acts.items():
        if not isinstance(a.get('vote'), bool):  # missing: asked once more, as a vote is
            a = await game.ask(name, game.request('decide', '(Your choice was missing: set `vote`.) ' + text, game.day))
        joined[name] = a.get('vote') is True
    game.emit('cult_vote', {'leader': leader.name, 'joined': sorted(x for x, y in joined.items() if y)}, 'audit')
    good = [q for q in g.players if not q.evil]
    if all(joined[q.name] for q in good) and 'Cult Leader' in g.abilities(leader) and leader.alive:
        if not g.works(leader, 'Cult Leader'):
            snv.failed(game, leader, 'Cult Leader', 'the cult did not win')
        else:
            team = leader.alignment
            g.winner, g.reason = team, (f'Every good player joined the cult of {leader.name}, the Cult Leader '
                                        f'({team}): {team} wins.')
            return
    game.emit('text', {'text': 'The cult vote is over.'})


class CultLeader(Townsfolk):
    name = 'Cult Leader'
    ability = ability(name)
    public_action = 'ability'  # the call for a cult vote, through the shared `ability` field

    @staticmethod
    def locked(g, me):
        """Whether `me` can't turn good by this ability: a Demon who has it through the Boffin, an evil player the
        Pit-Hag made the Cult Leader (their jinxes)."""
        if me.is_demon and g.script.jinxed('Boffin', 'Cult Leader') and (g.gift(me) or {}).get('ability') == \
                'Cult Leader':
            return True
        return me.name in g.notes.get('Evil Cult Leaders', ())

    async def resolve_night(self, game, night):
        # each night, the first too: the Storyteller's choice of alive neighbour when their alignments differ; told
        # (woken) only if the alignment changes
        g = game.g
        for p in [q for q in g.players if q.alive and self.name in g.abilities(q)]:
            sides = sorted({q.alignment for q in g.neighbours(p)})
            if not sides:
                continue
            side = sides[0]
            if len(sides) > 1:
                side = 'evil' if (await game.decide_judged(cult_alignment_choice(g, p, sides)))['yes'] else 'good'
            if side == p.alignment or (side == 'good' and self.locked(g, p)):
                continue
            if not g.works(p, self.name):
                snv.failed(game, p, self.name, 'the alignment did not change')
                continue
            game.woken(p)
            await game.change(p, alignment=side)

    def act_publicly(self, game, actor, target, text=None):
        # anyone may call one (a bluff's vote is held the same way, so it looks the same); one cult vote a day
        g = game.g
        if g.notes.get('Cult vote') == game.day or g.winner:
            return False
        g.notes['Cult vote'] = game.day
        p = g[actor]
        game.later(lambda game: cult_vote(game, p))
        return False


# ---- Outsiders ---------------------------------------------------------------------------------------------------

class Snitch(Outsider):
    name = 'Snitch'
    ability = ability(name)

    async def resolve_night(self, game, night):
        # the first night: each Minion who knows they are one (not a Marionette) is shown three good characters not in
        # play, chosen for each Minion (they may differ from the Demon's), while a player with the ability is sober
        # and healthy at this step (a Demon's, through the Boffin, too)
        g = game.g
        if not night.first or g.notes.get('Snitch'):
            return
        holders = [q for q in g.players if q.alive and self.name in g.abilities(q)]
        if not holders:
            return
        if not any(g.works(q, self.name) for q in holders):
            for q in holders:
                snv.failed(game, q, self.name, 'the Minions got no bluffs')
            return
        g.notes['Snitch'] = True
        in_play = {q.character for q in g.players} | {q.shown for q in g.players}
        options = [c for c in g.script.good if c not in in_play]
        drunk = next((q for q in g.players if rules(q.character).always_drunk and kind(q.character) == 'Outsider'),
                     None)
        if len(options) < 3:
            return
        for m in [q for q in g.players if kind(q.character) == 'Minion' and rules(q.shown).evil]:
            choice = bluffs_choice(options, drunk is not None, drunk.shown if drunk else None)
            choice.id = f'Snitch:{m.name}'
            choice.context = {**choice.context, 'recipient': m.name}
            bluffs = (await game.decide_judged(choice))['characters']
            game.woken(m)
            game.inform(m, f'Night {night.n} — Snitch: three characters not in play, for you to bluff: '
                           f'{", ".join(bluffs)}.')


# ---- Demons ------------------------------------------------------------------------------------------------------

def typhon_line(g, lot):
    """Whether the evil characters (the Minions and Demons) sit in a line with the Lord of Typhon in its middle: both
    its neighbours are Minions, and the two sides of the line differ by at most one."""
    n = len(g.players)
    evil = {q.name for q in g.players if kind(q.character) in ('Minion', 'Demon')}

    def run(step):
        k = 0
        while k < n - 1 and g.players[(lot.seat + step * (k + 1)) % n].name in evil:
            k += 1
        return k
    a, b = run(-1), run(1)
    return a >= 1 and b >= 1 and abs(a - b) <= 1 and a + b + 1 == len(evil)


def typhon_outsiders_choice(g, lot):
    """The Lord of Typhon's "-? to +? Outsiders": one fewer (usually, to offset the extra Minion), one more, or as dealt
    (POLICY 'typhon_outsiders_same', then 'typhon_outsiders_fewer')."""
    towns = [q for q in g.players if kind(q.character) == 'Townsfolk']
    outs = [q for q in g.players if kind(q.character) == 'Outsider' and not rules(q.character).always_drunk]
    in_play = {q.character for q in g.players}
    free_out = [c for c in g.script.outsiders if c not in in_play and not rules(c).always_drunk
                and not rules(c).wakes_at_own_step and not g.script.clash(in_play | {c})]
    free_town = [c for c in g.script.townsfolk if c not in in_play]
    drunk = any(rules(q.character).always_drunk and kind(q.character) == 'Outsider' for q in g.players)
    # (two Townsfolk stay, so a Washerwoman has another to be shown: docs/interaction-findings.md, U4)
    values = [0] + ([1] if towns[2:] and free_out else []) + ([-1] if outs and free_town[drunk:] else [])

    def style(r):
        if len(values) == 1 or r.random() < POLICY['typhon_outsiders_same']:
            return {'number': 0}
        if -1 in values and (1 not in values or r.random() < POLICY['typhon_outsiders_fewer']):
            return {'number': -1}
        return {'number': 1}
    return judged(Choice(f'Typhon outsiders:{lot.name}', [{'number': x} for x in values], style), 'typhon_outsiders',
                  'The Lord of Typhon is in play: one Outsider more (1), one fewer (-1), or as dealt (0)?',
                  recipient=lot.name)


def line_up(game, lot):
    """Seat the evil characters in a line with the Lord of Typhon in the middle, by moving the dealt tokens before
    anyone is told their character (as the Marionette's seat is): the Minions take the seats beside it, the players
    there take the Minions' seats. With an odd number of Minions, the Storyteller picks the longer side."""
    g = game.g
    n = len(g.players)
    minions = [q for q in g.players if kind(q.character) == 'Minion']
    k = len(minions)
    if k < 2 or k + 1 > n or typhon_line(g, lot):
        return
    left = k // 2
    if k % 2:
        left = k // 2 + game.decide(Choice('Typhon line', [{'yes': True}, {'yes': False}],
                                           lambda r: {'yes': r.random() < 0.5}))['yes']
    seats = [(lot.seat - i) % n for i in range(1, left + 1)] + [(lot.seat + i) % n for i in range(1, k - left + 1)]
    movers = [q for q in minions if q.seat not in seats]
    for s in [s for s in seats if kind(g.players[s].character) != 'Minion']:
        m, q = movers.pop(0), g.players[s]
        for attr in ('character', 'shown', 'alignment'):
            a, b = getattr(m, attr), getattr(q, attr)
            setattr(m, attr, b)
            setattr(q, attr, a)


class LordOfTyphon(Demon):
    name = 'Lord of Typhon'
    ability = ability(name)
    extra_minions = 1  # [+1 Minion]: dealt in a Townsfolk's seat (state.random_setup, setup_error)
    setup_order = -3  # the tokens are moved first, before any other setup step reads a seat

    night_choice = Choose(players=1, prompt='Choose a player: they die.')
    kills_at_night = True

    def night_spec(self, game, me, night):
        return None if night.first else self.night_choice

    async def resolve_night(self, game, night):
        g = game.g
        d, t = night.choice_of(g, self.name)
        if t and g.works(d, self.name):
            await game.demon_attack_judged(g[t], d, night)
        elif t and d:
            snv.failed(game, d, self.name, 'no attack')

    async def setup(self, game):
        # [Evil characters are in a line. You are in the middle]: the tokens are arranged so (in a forced setup too);
        # the neighbours learn they are Minions with the usual evil information (a reading of the first night's
        # thumbs-down). [-? to +? Outsiders]: in a dealt game, usually as dealt, else one fewer or one more
        g = game.g
        lot = g.with_character(self.name)
        if not lot:
            return
        line_up(game, lot)
        if game.forced:
            return
        d = (await game.decide_judged(typhon_outsiders_choice(g, lot)))['number']
        if d > 0:
            carousel2.add_outsider(game, lot)
        elif d < 0:
            in_play = {q.character for q in g.players}
            outs = [q.name for q in g.players if kind(q.character) == 'Outsider'
                    and not rules(q.character).always_drunk]
            towns = [c for c in g.script.townsfolk if c not in in_play]
            if outs and towns:
                v = game.decide(Choice('Typhon fewer outsiders', [{'players': [x], 'character': c} for x in outs
                                                                  for c in towns],
                                       lambda r: {'players': [r.choice(outs)], 'character': r.choice(towns)}))
                game.transition(g[v['players'][0]], v['character'], how='dealt', quiet=True)


async def typhon_summoned(game, s, target):
    """The Summoner/Lord of Typhon jinx, before the summoning: "they must neighbour a Minion": a player who does not is
    replaced by the Storyteller's choice of one who does (usually a good one), or kept when none does."""
    g = game.g
    near = [q.name for q in g.players if any(kind(x.character) == 'Minion' for x in carousel2.seat_neighbours(g, q))
            and kind(q.character) != 'Minion']
    if target in near or not near:
        return target
    good = [x for x in near if not g[x].evil]
    return (await game.decide_judged(judged(Choice(f'Typhon summoned:{s.name}', [{'players': [x]} for x in near],
                                                   lambda r: {'players': [r.choice(good or near)]}), 'summon_player',
                                            f'The Summoner ({s.name}) summons the Lord of Typhon, who must neighbour '
                                            'a Minion: which player becomes it?', recipient=s.name)))['players'][0]


async def typhon_neighbour(game, lot):
    """The Summoner/Lord of Typhon jinx, after: the summoned Lord of Typhon's other neighbour (not a Minion) becomes an
    evil Minion not in play, the Storyteller's choice, and is told."""
    g = game.g
    a, b = carousel2.seat_neighbours(g, lot)
    other = b if kind(a.character) == 'Minion' else a if kind(b.character) == 'Minion' else None
    if other is None or kind(other.character) == 'Minion' or other is lot:
        return
    in_play = {q.character for q in g.players}
    pool = [m for m in g.script.minions if m not in in_play and m != 'Marionette' and not rules(m).no_demon
            and not g.script.clash((in_play - {other.character}) | {m})]
    if not pool:
        return
    m = (await game.decide_judged(judged(Choice(f'Typhon minion:{other.name}', [{'character': m} for m in pool],
                                                lambda r: {'character': r.choice(pool)}), 'typhon_minion',
                                         f'{other.name} neighbours the summoned Lord of Typhon: which Minion do they '
                                         'become?', recipient=other.name)))['character']
    await game.change(other, character=m, alignment='evil')


def host(g, lleech):
    return g.notes.get('Lleech host', {}).get(lleech.name)


class Lleech(Demon):
    name = 'Lleech'
    ability = ability(name)
    instance_notes = ('Lleech host', 'Lleech lost')  # (a swap hands the host over first: hand_over)
    night_choice = Choose(players=1, prompt='Choose a player: they die.')
    kills_at_night = True
    host_choice = Choose(players=1, may_self=False, prompt='Choose a player (not yourself): they are poisoned, and you '
                                                           'die if and only if they are dead.')

    @staticmethod
    def lost(g, me):
        """The Mastermind jinx: the Lleech lost their ability (its host was executed while a Mastermind lived)."""
        return me.name in g.notes.get('Lleech lost', ())

    def night_spec(self, game, me, night):
        # "You start by choosing a player": the first night; a Lleech made later, which has none, chooses its host on
        # its next night instead of killing (a reading). A Lunatic who believes they are the Lleech, likewise
        g = game.g
        if me.character != self.name:
            return self.host_choice if night.first else self.night_choice
        if host(g, me) is None:
            return self.host_choice
        return None if night.first else self.night_choice

    async def resolve_night(self, game, night):
        g = game.g
        d, t = night.choice_of(g, self.name)
        if not (d and t) or self.lost(g, d):
            return
        if host(g, d) is None:
            # whatever the Lleech's sobriety: it is how it starts. The host is poisoned while the Lleech has its ability
            # (paused while it is drunk or poisoned, as the Poisoner's poison), for the rest of the game
            g.notes.setdefault('Lleech host', {})[d.name] = t
            g.add(State('poisoned', t, source=d.name, until=None, ends_with_source=True, while_source_sober=True))
            g.reminders.append(f'{t} is the Lleech\'s host (poisoned).')
            return
        if g.works(d, self.name):
            await game.demon_attack_judged(g[t], d, night)
        else:
            snv.failed(game, d, self.name, 'no attack')

    def safe_from(self, g, me, cause):
        # "You die ... only if they are dead": nothing else kills a working Lleech while its host lives (but the
        # Assassin's kill, which goes through everything: Game.prevent_death)
        h = host(g, me)
        return bool(h) and g[h].alive and g.works(me, self.name) and not self.lost(g, me)

    def on_death(self, game, me, dead, cause, alive_before):
        # "You die if ... they are dead": the host's death (any cause) kills a Lleech with a working ability at once;
        # the Mastermind jinx: a host executed while a Mastermind lives leaves the Lleech alive, with no ability
        g = game.g
        if me.character != self.name or not me.alive or self.lost(g, me) or dead.name != host(g, me):
            return
        if cause == 'execution' and g.script.jinxed(self.name, 'Mastermind') and any(
                q.alive and q.character == 'Mastermind' for q in g.players):
            g.notes.setdefault('Lleech lost', []).append(me.name)
            g.states = [s for s in g.states if not (s.source == me.name and s.kind == 'poisoned')]
            game.emit('text', {'text': f'[{me.name}, the Lleech, loses their ability (the Mastermind jinx)]'}, 'audit')
            return
        if not g.works(me, self.name):
            snv.failed(game, me, self.name, 'did not die with its host')
            return
        game.kill(me, 'lleech', me)
        if game.tonight is not None:
            game.tonight.deaths.append(me)
        else:
            game.emit('died', {'player': me.name})

    def hand_over(self, g, old, new):
        # the host belongs to the Lleech, not its player: a new Lleech by a swap (the Snake Charmer's, the Barber's)
        # keeps it, and its poison
        hosts = g.notes.get('Lleech host', {})
        if old.name in hosts:
            hosts[new.name] = hosts.pop(old.name)
        keep = [s for s in g.states if s.source == old.name and s.kind == 'poisoned'
                and s.target == hosts.get(new.name)]
        g.states = [s for s in g.states if not any(s is k for k in keep)]
        return keep if new.alive else []  # (a swap onto a dead player: a dead Lleech poisons nobody, finding B19)


CHARACTERS.update({c.name: c() for c in [Alsaahir, Huntsman, Knight, King, Choirboy, CultLeader, Snitch, LordOfTyphon,
                                         Lleech]})


# ---- Batch 3b's jinxes (docs/carousel-rulings.md, batch 3b) ------------------------------------------------------

jinx('Boffin', 'Cult Leader', 'carousel4.CultLeader.locked; carousel3.BOFFIN_USABLE')
jinx('Pit-Hag', 'Cult Leader', 'snv.PitHag.resolve_night; carousel4.CultLeader.locked')
jinx('Heretic', 'Lleech', 'characters.Script.clash: state.random_setup, setup_error; snv.PitHag; carousel2.Kazali')
jinx('Leviathan', 'King', 'carousel4.King.due')
jinx('Lleech', 'Mastermind', 'carousel4.Lleech.on_death')
jinx('Lleech', 'Slayer', 'characters.Slayer.act_publicly')
jinx('Marionette', 'Huntsman', 'carousel4.Huntsman.setup')
jinx('Summoner', 'Lord of Typhon', 'carousel.Summoner.resolve_night (carousel4.typhon_summoned, typhon_neighbour)')
