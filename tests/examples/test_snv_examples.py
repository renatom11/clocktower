"""Sects & Violets: every worked example of the wiki's "Examples" sections (and the almanac's, where the wiki lacks
one) as a scenario test, played on the real script. Each test is named after the character and the example's number
on the wiki page; an almanac-only example is named `..._almanac_n`. Where an example depends on a Storyteller choice,
the choice is forced (Forced, below), so the test checks the rule, not chance. An example the engine disagrees with is
kept and skipped, with its finding in docs/examples-findings.md (ESNV-n); one the engine cannot build (Travellers, or
facts about the real room) is skipped as not buildable."""
import asyncio
import random
import unittest

from clocktower import characters as ch
from clocktower import judge, snv
from clocktower.agents import ScriptedStoryteller
from clocktower.game import ALL_NAMES, Game
from clocktower.llm import Reply
from clocktower.state import Grimoire, State

A, B, C, D, E, F, G, H, I, J = ALL_NAMES[:10]
BLANK = {'say': '', 'whispers': [], 'nominate': None, 'vote': None, 'targets': []}
TRAVELLERS = 'not buildable: the example needs Travellers (exile), which are not built'


class Seat:
    """Answers night requests from {night: answer} and day requests from {kind: [answers]} (each used once).
    (Copied from tests/test_snv.py.)"""

    def __init__(self):
        self.answers, self.day, self.log = {}, {}, []

    async def act(self, text, request):
        self.log.append(request)
        if request.prompt.startswith('(That is not a legal choice'):
            need = request.n_targets if request.min_targets is None else request.min_targets
            return Reply({**BLANK, 'targets': request.options[:need],
                          'character': request.characters[0] if request.characters else None})
        if request.kind == 'night':
            answer = self.answers.get(request.day, {})
            if isinstance(answer, list):  # one answer per step woken tonight, in order
                answer = answer.pop(0) if answer else {}
            return Reply({**BLANK, **answer})
        queue = self.day.get(request.kind)
        if queue:
            return Reply({**BLANK, **queue.pop(0)})
        return Reply({**BLANK, 'vote': False})


class Forced(ScriptedStoryteller):
    """The scripted Storyteller, except for the choices given: {choice id prefix: value}."""

    def __init__(self, forced=None):
        super().__init__(random.Random(1))
        self.forced = forced or {}

    def choose(self, choice):
        for prefix, value in self.forced.items():
            if choice.id.startswith(prefix):
                return value
        return super().choose(choice)


def run(coro):
    return asyncio.run(coro)


class Example(unittest.TestCase):
    script = ch.Script('snv')

    def game(self, chars, forced=None, judge_=None):
        """A game on the S&V script with the Grimoire dealt as given (seat order, clockwise), at day 1."""
        names = ALL_NAMES[:len(chars)]
        self.seats = {n: Seat() for n in names}
        g = Game(self.seats, Forced(forced), names=names, seed=3, characters=chars, script=self.script, probes=False,
                 judge=judge_, private_beats=1, public_beats=1)
        g.g = Grimoire(names, chars, script=self.script)
        g.day, g.phase, g.g.day = 1, 'day', 1
        self.g = g
        return g

    def choose(self, night, name, targets=(), character=None):
        self.seats[name].answers[night] = {'targets': list(targets), 'character': character}

    def steps(self, night, name, *answers):
        """`name`'s answers on `night`, one per step they are woken at, in order."""
        self.seats[name].answers[night] = [{'targets': list(t), 'character': c} for t, c in answers]

    def day(self, g, n):
        g.day, g.phase, g.g.day = n, 'day', n

    def told(self, name, text):
        return [e['data']['text'] for e in self.g.events
                if e['to'] == [name] and e['kind'] in ('info', 'notice') and text in e['data'].get('text', '')]

    def say(self, g, who, text, to=None):
        if to:
            g.emit('whisper', {'from': who, 'to': list(to), 'text': text}, [who, *to])
        else:
            g.emit('say', {'speaker': who, 'text': text})

    def nominate(self, g, nominator, nominee, voters=()):
        self.seats[nominator].day['nominate'] = [{'nominate': nominee}]
        for v in voters:
            self.seats[v].day['vote'] = [{'vote': True}]
        g.phase = 'nominations'
        run(g.nominations())

    def visit(self, g, who, character, text=''):
        return run(g.visit_judged(who, {'character': character, 'text': text}))

    def deaths(self, g, n):
        return [e['data']['deaths'] for e in g.events if e['kind'] == 'dawn' and e['data']['day'] == n][0]

    def poison(self, g, name, kind_='poisoned'):
        g.g.add(State(kind_, name, source='test', until=None))

    def poisoned(self, g):
        return [p.name for p in g.g.players if g.g.is_poisoned(p)]

    def abnormal(self, g):
        return sorted({a['player'] for a in g.g.abnormal})


# ---- Townsfolk --------------------------------------------------------------------------------------------------

class ClockmakerExamples(Example):
    def test_clockmaker_example_1(self):
        """The Fang Gu sits beside the Pit-Hag: on the first night the Clockmaker learns 1. (wiki: Clockmaker,
        example 1)"""
        g = self.game(['Clockmaker', 'Dreamer', 'Mutant', 'Pit-Hag', 'Fang Gu', 'Oracle', 'Sage'])
        self.choose(1, B, [C])
        run(g.night(1))
        self.assertTrue(self.told(A, 'Clockmaker: the Demon is 1 step from its nearest Minion'))

    def test_clockmaker_example_2(self):
        """Clockwise from the No Dashii the Evil Twin is three seats away, anticlockwise the Witch five: the
        Clockmaker learns 3. (wiki: Clockmaker, example 2)"""
        g = self.game(['No Dashii', 'Dreamer', 'Snake Charmer', 'Evil Twin', 'Clockmaker', 'Witch', 'Sage',
                       'Philosopher', 'Sweetheart', 'Mutant'])
        self.choose(1, B, [D])
        self.choose(1, C, [C])
        self.choose(1, F, [G])
        run(g.night(1))
        self.assertTrue(self.told(E, 'Clockmaker: the Demon is 3 steps from its nearest Minion'))

    @unittest.skip(TRAVELLERS)
    def test_clockmaker_example_3(self):
        """Evil Travellers beside the Fang Gu are not Minions. (wiki: Clockmaker, example 3)"""


class DreamerExamples(Example):
    def test_dreamer_example_1(self):
        """The Dreamer picks the Mutant and is shown the Mutant or the Cerenovus. (wiki: Dreamer, example 1)"""
        g = self.game(['Dreamer', 'Clockmaker', 'Mutant', 'Oracle', 'Cerenovus', 'Fang Gu', 'Sage'],
                      forced={'Dreamer:': {'characters': ['Mutant', 'Cerenovus']}})
        shown = [v['characters'] for v in snv.dreamer_choice(g.g, g.g[A], C).values]
        self.assertTrue(all('Mutant' in v for v in shown))
        self.assertIn(['Mutant', 'Cerenovus'], shown)
        self.choose(1, A, [C])
        self.choose(1, E, [D], 'Oracle')
        run(g.night(1))
        self.assertTrue(self.told(A, f'{C} is either the Mutant or the Cerenovus'))

    def test_dreamer_example_2(self):
        """The Philosopher who gained the Flowergirl's ability earlier tonight is still the Philosopher to the
        Dreamer: shown the Philosopher or the Vigormortis. (wiki: Dreamer, example 2)"""
        g = self.game(['Dreamer', 'Philosopher', 'Clockmaker', 'Oracle', 'Witch', 'Vigormortis', 'Sage'],
                      forced={'Dreamer:': {'characters': ['Philosopher', 'Vigormortis']}})
        self.steps(2, B, ([], 'Flowergirl'), ([], None))
        self.choose(2, A, [B])
        self.choose(2, E, [C])
        self.choose(2, F, [G])
        run(g.night(2))
        self.assertEqual(g.g[B].extra, ['Flowergirl'])
        self.assertTrue(all('Philosopher' in v['characters'] for v in snv.dreamer_choice(g.g, g.g[A], B).values))
        self.assertTrue(self.told(A, f'{B} is either the Philosopher or the Vigormortis'))

    def test_dreamer_example_3(self):
        """The Evil Twin and the Artist both claimed the Artist; the Dreamer picks the Evil Twin. The Storyteller may
        help good (the Evil Twin and the Sweetheart) or, as here, evil (the Evil Twin and the Artist). (wiki:
        Dreamer, example 3)"""
        g = self.game(['Dreamer', 'Artist', 'Sweetheart', 'Oracle', 'Evil Twin', 'Fang Gu', 'Sage'],
                      forced={'Dreamer:': {'characters': ['Artist', 'Evil Twin']}})
        g.g.notes['Twins'] = {E: B}
        self.say(g, E, 'I am the Artist.')
        self.say(g, B, 'I am the Artist.')
        shown = [v['characters'] for v in snv.dreamer_choice(g.g, g.g[A], E, 'Artist').values]
        self.assertIn(['Sweetheart', 'Evil Twin'], shown)
        self.assertIn(['Artist', 'Evil Twin'], shown)
        self.choose(2, A, [E])
        self.choose(2, F, [D])
        run(g.night(2))
        self.assertTrue(self.told(A, f'{E} is either the Artist or the Evil Twin'))

    def test_dreamer_example_4(self):
        """Under the Vortox the Dreamer who picks the Vortox must be wrong: shown the Oracle or the No Dashii. (wiki:
        Dreamer, example 4)"""
        g = self.game(['Dreamer', 'Clockmaker', 'Mutant', 'Oracle', 'Witch', 'Vortox', 'Sage'],
                      forced={'Dreamer:': {'characters': ['Oracle', 'No Dashii']}})
        self.choose(1, A, [F])
        self.choose(1, E, [C])
        run(g.night(1))
        self.assertTrue(self.told(A, f'{F} is either the Oracle or the No Dashii'))
        choice = g.false_only(snv.dreamer_choice(g.g, g.g[A], F))
        self.assertTrue(choice.values)
        self.assertFalse([v for v in choice.values if 'Vortox' in v['characters']])


class SnakeCharmerExamples(Example):
    CHARS = ['Snake Charmer', 'Clockmaker', 'Mutant', 'Oracle', 'Pit-Hag', 'Vigormortis', 'Sage']

    def test_snake_charmer_example_1(self):
        """The Snake Charmer picks the Pit-Hag, then themself the next night: nothing happens. (wiki: Snake Charmer,
        example 1)"""
        g = self.game(self.CHARS)
        self.choose(1, A, [E])
        run(g.night(1))
        self.choose(2, A, [A])
        self.choose(2, E, [B], 'Clockmaker')  # in play: nothing
        self.choose(2, F, [G])
        run(g.night(2))
        self.assertEqual([g.g[x].character for x in (A, E, F)], ['Snake Charmer', 'Pit-Hag', 'Vigormortis'])
        self.assertEqual([g.g[x].alignment for x in (A, E, F)], ['good', 'evil', 'evil'])

    def test_snake_charmer_example_2(self):
        """The Snake Charmer picks the Vigormortis: they become the evil Vigormortis, and the Vigormortis the good,
        poisoned Snake Charmer. (wiki: Snake Charmer, example 2)"""
        g = self.game(self.CHARS)
        self.steps(2, A, ([F], None), ([C], None))
        self.choose(2, E, [B], 'Clockmaker')
        run(g.night(2))
        self.assertEqual((g.g[A].character, g.g[A].alignment), ('Vigormortis', 'evil'))
        self.assertEqual((g.g[F].character, g.g[F].alignment), ('Snake Charmer', 'good'))
        self.assertTrue(g.g.is_poisoned(g.g[F]))

    def test_snake_charmer_example_3(self):
        """A Pit-Hag who made themself the Snake Charmer later charms the Fang Gu: the two swap characters, the old
        Fang Gu is poisoned, and both stay evil. (wiki: Snake Charmer, example 3)"""
        g = self.game(['Clockmaker', 'Oracle', 'Mutant', 'Sage', 'Pit-Hag', 'Fang Gu', 'Dreamer'])
        self.choose(2, E, [E], 'Snake Charmer')
        self.choose(2, F, [A])
        self.choose(2, G, [B])
        run(g.night(2))
        self.assertEqual((g.g[E].character, g.g[E].alignment), ('Snake Charmer', 'evil'))
        self.steps(3, E, ([F], None), ([B], None))
        self.choose(3, G, [B])
        run(g.night(3))
        self.assertEqual((g.g[E].character, g.g[E].alignment), ('Fang Gu', 'evil'))
        self.assertEqual((g.g[F].character, g.g[F].alignment), ('Snake Charmer', 'evil'))
        self.assertTrue(g.g.is_poisoned(g.g[F]))


class MathematicianExamples(Example):
    def test_mathematician_example_1(self):
        """The poisoned Oracle learns 2 when 3 dead players are evil, all else works: the Mathematician learns 1.
        (wiki: Mathematician, example 1)"""
        g = self.game(['Oracle', 'Clockmaker', 'Witch', 'Cerenovus', 'Pit-Hag', 'Vigormortis', 'Mathematician',
                       'Sage', 'Mutant'], forced={'Oracle:': {'number': 2}})
        for x in (C, D, E):
            g.g[x].alive = False
        self.poison(g, A)
        self.choose(2, F, [B])
        run(g.night(2))
        self.assertTrue(self.told(A, 'Oracle: 2 of the dead'))
        self.assertTrue(self.told(G, "Mathematician: 1 player's ability worked abnormally"))

    def test_mathematician_example_2(self):
        """A poisoned Snake Charmer who picks a Townsfolk, a drunk Juggler told the truth, and a Savant told two true
        things: only the Savant's counts, so the Mathematician learns 1. (wiki: Mathematician, example 2; the
        almanac says the Savant is poisoned, as a sober one could not be told two true things)"""
        g = self.game(['Snake Charmer', 'Juggler', 'Savant', 'Mathematician', 'Witch', 'Fang Gu', 'Clockmaker'],
                      forced={'Juggler:': {'number': 1}})
        g.public_abilities([B], {B: {'ability': {'character': 'Juggler', 'target': None, 'text': '',
                                                 'guesses': [{'player': G, 'character': 'Clockmaker'}]}}})
        self.poison(g, C)
        stmts = snv.savant_statements(g.g, g.g[C])
        two_true = [s['text'] for s in stmts if s['true']][:2]
        value = next(v for v in snv.savant_choice(g.g, g.g[C]).values if sorted(v['statements']) == sorted(two_true))
        g.st.forced['Savant:'] = value
        self.visit(g, C, 'Savant')
        self.assertEqual(self.abnormal(g), [C])
        g.g.states = [s for s in g.g.states if s.source != 'test']
        self.poison(g, A)
        self.poison(g, B, 'drunk')
        self.choose(2, A, [G])
        self.choose(2, E, [G])
        self.choose(2, F, [G])
        run(g.night(2))
        self.assertEqual(g.g[A].character, 'Snake Charmer')
        self.assertTrue(self.told(B, 'Juggler: 1 of your guesses was correct'))
        self.assertTrue(self.told(D, "Mathematician: 1 player's ability worked abnormally"))

    def test_mathematician_example_3(self):
        """Under the Vortox five good players got false information and the drunk Witch's cursed nominator lived: six
        abnormal, but the Mathematician is told a false number (the wiki says 4, the almanac 3). (wiki:
        Mathematician, example 3)"""
        g = self.game(['Flowergirl', 'Town Crier', 'Oracle', 'Dreamer', 'Witch', 'Vortox', 'Mathematician',
                       'Seamstress', 'Sage', 'Mutant'], forced={'Mathematician:': {'number': 4}})
        self.choose(1, E, [A])
        self.choose(1, D, [B])
        run(g.night(1))
        self.poison(g, E, 'drunk')
        self.day(g, 1)
        self.nominate(g, A, B)
        self.assertTrue(g.g[A].alive)
        self.choose(2, D, [B])
        self.choose(2, H, [A, B])
        self.choose(2, F, [J])
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertEqual(snv.abnormal_since_dawn(g.g, g.g[G], 2), [A, B, C, D, E, H])
        self.assertNotIn({'number': 6}, g.false_only(snv.mathematician_choice(g.g, g.g[G], 2)).values)
        self.assertTrue(self.told(G, "Mathematician: 4 players' abilities worked abnormally"))


class FlowergirlExamples(Example):
    CHARS = ['Flowergirl', 'Clockmaker', 'Mutant', 'Oracle', 'Witch', 'Fang Gu', 'Sage']

    def test_flowergirl_example_1(self):
        """One nomination, many votes, an execution, but the Demon did not vote: the Flowergirl learns no. (wiki:
        Flowergirl, example 1)"""
        g = self.game(self.CHARS)
        self.nominate(g, B, C, voters=[A, B, D, E, G])
        self.assertFalse(g.g[C].alive)
        self.choose(2, E, [D])
        self.choose(2, F, [D])
        run(g.night(2))
        self.assertTrue(self.told(A, 'Flowergirl: NO'))

    def test_flowergirl_example_2(self):
        """Three nominations, the Demon voted in the second, nobody executed: yes. (wiki: Flowergirl, example 2)"""
        g = self.game(self.CHARS)
        self.nominate(g, B, C)
        self.nominate(g, C, D, voters=[F])
        self.nominate(g, D, G)
        self.assertEqual(g.g.executions, [])
        self.choose(2, E, [D])
        self.choose(2, F, [D])
        run(g.night(2))
        self.assertTrue(self.told(A, 'Flowergirl: YES'))

    @unittest.skip(TRAVELLERS)
    def test_flowergirl_example_3(self):
        """Raising a hand for an exile is not a vote. (wiki: Flowergirl, example 3)"""


class TownCrierExamples(Example):
    CHARS = ['Town Crier', 'Clockmaker', 'Mutant', 'Oracle', 'Witch', 'Fang Gu', 'Cerenovus', 'Sage']

    def test_town_crier_example_1(self):
        """Four players nominated, two of them Minions; many voted, nobody executed: the Town Crier learns yes. (wiki:
        Town Crier, example 1)"""
        g = self.game(self.CHARS)
        for nominator, nominee in ((B, C), (E, D), (G, H), (D, B)):
            self.nominate(g, nominator, nominee, voters=[A, B, C])
        self.assertEqual(g.g.executions, [])
        self.choose(2, E, [D])
        self.choose(2, G, [D], 'Oracle')
        self.choose(2, F, [D])
        run(g.night(2))
        self.assertTrue(self.told(A, 'Town Crier: YES'))

    @unittest.skip(TRAVELLERS)
    def test_town_crier_example_2(self):
        """Calling for an exile is not a nomination. (wiki: Town Crier, example 2)"""

    def test_town_crier_almanac_1(self):
        """Only one Townsfolk nominated today: no. (almanac S&V: Town Crier, first example; not on the wiki)"""
        g = self.game(self.CHARS)
        self.nominate(g, B, C)
        self.choose(2, E, [D])
        self.choose(2, G, [D], 'Oracle')
        self.choose(2, F, [D])
        run(g.night(2))
        self.assertTrue(self.told(A, 'Town Crier: NO'))


class OracleExamples(Example):
    def test_oracle_example_1(self):
        """The Flowergirl is executed on day 1 and the Demon kills the Juggler that night: the Oracle learns 0. (wiki:
        Oracle, example 1)"""
        g = self.game(['Oracle', 'Flowergirl', 'Juggler', 'Clockmaker', 'Witch', 'Fang Gu', 'Mutant'])
        g.execute(B)
        self.choose(2, E, [D])
        self.choose(2, F, [C])
        run(g.night(2))
        self.assertFalse(g.g[C].alive)
        self.assertTrue(self.told(A, 'Oracle: 0 of the dead players are evil'))

    def test_oracle_example_2(self):
        """Seven dead, two evil; the Demon kills one of its Minions, and the Oracle, waking after the Demon, counts it.
        Tested without the evil Traveller exiled today (who would make the wiki's 4): 3. (wiki: Oracle, example 2)"""
        g = self.game(['Oracle', 'Clockmaker', 'Dreamer', 'Sage', 'Seamstress', 'Artist', 'Mutant', 'Klutz', 'Witch',
                       'Cerenovus', 'Pit-Hag', 'Fang Gu', 'Juggler'])
        for x in ALL_NAMES[1:6] + [ALL_NAMES[8], ALL_NAMES[9]]:
            g.g[x].alive = False
        self.choose(2, ALL_NAMES[10], [B], 'Clockmaker')  # the Pit-Hag: in play, nothing
        self.choose(2, ALL_NAMES[11], [ALL_NAMES[10]])
        run(g.night(2))
        self.assertTrue(self.told(A, 'Oracle: 3 of the dead players are evil'))


class SeamstressExamples(Example):
    def test_seamstress_example_1(self):
        """On the first night the Seamstress picks the Barber and the Clockmaker, both good: yes. (wiki: Seamstress,
        example 1)"""
        g = self.game(['Seamstress', 'Barber', 'Clockmaker', 'Oracle', 'Witch', 'Fang Gu', 'Sage'])
        self.choose(1, A, [B, C])
        self.choose(1, E, [D])
        run(g.night(1))
        self.assertTrue(self.told(A, f'Seamstress: {B} and {C} are the same alignment'))

    def test_seamstress_example_2(self):
        """Three nights declined, then the Fang Gu and the Sweetheart on the fourth: no. (wiki: Seamstress, example
        2)"""
        g = self.game(['Seamstress', 'Clockmaker', 'Sweetheart', 'Oracle', 'Witch', 'Fang Gu', 'Sage'])
        for n, victim in ((1, None), (2, D), (3, G)):
            self.choose(n, E, [B])
            if victim:
                self.choose(n, F, [victim])
            run(g.night(n))
            self.day(g, n)
        self.assertFalse(snv.used(g.g, g.g[A], 'Seamstress'))
        self.choose(4, A, [F, C])
        self.choose(4, E, [B])
        self.choose(4, F, [B])
        run(g.night(4))
        self.assertTrue(self.told(A, f'{F} and {C} are NOT the same alignment'))

    def test_seamstress_example_3(self):
        """The Pit-Hag turns the Mathematician into a good Witch; later that night the Seamstress picks the Witch and
        the Town Crier: yes. (wiki: Seamstress, example 3)"""
        g = self.game(['Seamstress', 'Mathematician', 'Mutant', 'Town Crier', 'Pit-Hag', 'Fang Gu', 'Sage'])
        self.choose(2, E, [B], 'Witch')
        self.choose(2, F, [G])
        self.choose(2, A, [B, D])
        run(g.night(2))
        self.assertEqual((g.g[B].character, g.g[B].alignment), ('Witch', 'good'))
        self.assertTrue(self.told(A, f'{B} and {D} are the same alignment'))


class SageExamples(Example):
    CHARS = ['Sage', 'Clockmaker', 'Mutant', 'Oracle', 'Witch', 'Fang Gu', 'Dreamer']

    def test_sage_example_1(self):
        """The Demon kills the Sage on the second night: two players, one of them the Demon. (wiki: Sage, example
        1)"""
        g = self.game(self.CHARS)
        self.choose(2, E, [B])
        self.choose(2, F, [A])
        self.choose(2, G, [B])
        run(g.night(2))
        text = self.told(A, 'Sage: the Demon who killed you is')[0]
        self.assertIn(F, text)

    def test_sage_example_2(self):
        """On the final night the Demon kills the Sage, drunk from the Sweetheart: shown a dead and a living player,
        neither the Demon. (wiki: Sage, example 2)"""
        g = self.game(['Sage', 'Clockmaker', 'Sweetheart', 'Oracle', 'Witch', 'Fang Gu', 'Dreamer', 'Seamstress'],
                      forced={'Sweetheart:': {'players': [A]}, 'Sage:': {'players': [B, H]}})
        for x in (B, D, G):
            g.g[x].alive = False
        self.day(g, 3)
        run(g.execution(C))
        run(g.run_pending())
        self.assertTrue(g.g.is_drunk(g.g[A]))
        self.choose(4, E, [H])
        self.choose(4, F, [A])
        run(g.night(4))
        self.assertEqual(g.g.alive_count(), 3)
        text = self.told(A, 'Sage:')[0]
        self.assertIn(B, text)
        self.assertIn(H, text)
        self.assertNotIn(F, text)

    def test_sage_example_3(self):
        """The Pit-Hag makes a Demon, and the Storyteller's arbitrary deaths kill the old Demon and the Sage: killed by
        the Pit-Hag, not the Demon, the Sage learns nothing. (wiki: Sage, example 3)"""
        g = self.game(['Sage', 'Clockmaker', 'Mutant', 'Oracle', 'Pit-Hag', 'Fang Gu', 'Dreamer'],
                      forced={'Pit-Hag deaths': {'players': [A, F], 'yes': False}})
        self.steps(2, E, ([E], 'Vigormortis'), ([B], None))
        self.choose(2, F, [D])
        self.choose(2, G, [B])
        run(g.night(2))
        self.assertFalse(g.g[A].alive)
        self.assertFalse(g.g[F].alive)
        self.assertEqual(g.g[E].character, 'Vigormortis')
        self.assertFalse(self.told(A, 'Sage'))


class SavantExamples(Example):
    def statements(self, g, p=A):
        return {s['text']: s['true'] for s in snv.savant_statements(g.g, g.g[p])}

    def value(self, g, texts, p=A):
        return next((v for v in snv.savant_choice(g.g, g.g[p]).values if sorted(v['statements']) == sorted(texts)),
                    None)

    @unittest.skip('not buildable: statements about the real room (glasses, a black couch), which no engine '
                   'template states')
    def test_savant_example_1(self):
        """Statements about who wears glasses and who sits on a couch. (wiki: Savant, example 1)"""

    def test_savant_example_2(self):
        """The Savant is told that a Snake Charmer is in play, and that all information given last night was true:
        one true and one false. Here a poisoned Dreamer was misinformed last night, so the second is the false one.
        (wiki: Savant, example 2)"""
        g = self.game(['Savant', 'Snake Charmer', 'Dreamer', 'No Dashii', 'Clockmaker', 'Witch', 'Mutant'],
                      forced={'Dreamer:': {'characters': ['Oracle', 'Witch']}})
        self.assertTrue(g.g.is_poisoned(g.g[C]))
        self.choose(2, B, [B])
        self.choose(2, C, [B])
        self.choose(2, F, [G])
        self.choose(2, D, [G])
        run(g.night(2))
        self.day(g, 2)
        snake, true_info = 'There is a Snake Charmer in play.', ('Everyone who got information from their ability '
                                                                 'last night got true information.')
        s = self.statements(g)
        self.assertIs(s[snake], True)
        self.assertIs(s[true_info], False)
        g.st.forced['Savant:'] = self.value(g, [snake, true_info])
        self.visit(g, A, 'Savant')
        told = self.told(A, 'Savant: the Storyteller tells you two things')[0]
        self.assertIn(snake, told)
        self.assertIn(true_info, told)

    def test_savant_example_3(self):
        """The Savant hears "the Demon is a woman" and "Benjamin is evil". Only the second is a statement the engine
        can make (the first is about the real room): the rules part tested is that "X is evil" is a statement the
        Savant may hear, paired with its opposite truth. (wiki: Savant, example 3)"""
        g = self.game(['Savant', 'Clockmaker', 'Witch', 'Oracle', 'Mutant', 'Fang Gu', 'Sage'])
        s = self.statements(g)
        self.assertIs(s[f'{C} is evil.'], True)
        self.assertIs(s[f'{B} is evil.'], False)
        self.assertIsNotNone(self.value(g, [f'{B} is evil.', 'There is a Witch in play.']))

    def test_savant_example_4(self):
        """The Savant hears that two players are the same alignment and that there is one Outsider in play. (The
        engine's alignment statements pair neighbours, or the Savant with anyone: neighbours here.) (wiki: Savant,
        example 4)"""
        g = self.game(['Savant', 'Clockmaker', 'Witch', 'Oracle', 'Mutant', 'Fang Gu', 'Sage', 'Dreamer'])
        same, one = f'{B} and {C} are the same alignment.', 'There is exactly 1 Outsider in play.'
        s = self.statements(g)
        self.assertIs(s[same], False)
        self.assertIs(s[one], True)
        g.st.forced['Savant:'] = self.value(g, [same, one])
        self.visit(g, A, 'Savant')
        told = self.told(A, 'Savant: the Storyteller tells you two things')[0]
        self.assertIn(same, told)
        self.assertIn(one, told)


class PhilosopherExamples(Example):
    CHARS = ['Philosopher', 'Clockmaker', 'Witch', 'Oracle', 'Mutant', 'Fang Gu', 'Sage']

    def test_philosopher_example_1(self):
        """On the first night the Philosopher gains the Dreamer's ability and acts when the Dreamer acts. (wiki:
        Philosopher, example 1)"""
        g = self.game(self.CHARS)
        self.steps(1, A, ([], 'Dreamer'), ([C], None))
        self.choose(1, C, [B])
        run(g.night(1))
        self.assertEqual((g.g[A].character, g.g[A].extra), ('Philosopher', ['Dreamer']))
        self.assertTrue(self.told(A, f'Dreamer: {C} is either the'))
        self.choose(2, C, [B])
        self.choose(2, F, [G])
        self.choose(2, A, [D])
        run(g.night(2))
        self.assertTrue(self.told(A, f'Dreamer: {D} is either the'))

    def test_philosopher_example_2(self):
        """On the third night the Philosopher gains the Clockmaker's ability and learns the distance that night.
        (wiki: Philosopher, example 2)"""
        g = self.game(['Philosopher', 'Sage', 'Witch', 'Oracle', 'Mutant', 'Fang Gu', 'Dreamer'])
        self.choose(3, A, [], 'Clockmaker')
        self.choose(3, C, [B])
        self.choose(3, F, [B])
        self.choose(3, G, [B])
        run(g.night(3))
        self.assertTrue(self.told(A, 'Clockmaker: the Demon is 3 steps from its nearest Minion'))

    def test_philosopher_example_3(self):
        """The Philosopher gains the in-play Artist's ability: the Artist is drunk; when the Philosopher dies, the
        Artist is sober again (also if the Philosopher is drunk). (wiki: Philosopher, example 3)"""
        g = self.game(['Philosopher', 'Artist', 'Witch', 'Oracle', 'Mutant', 'Fang Gu', 'Sage'])
        self.choose(1, A, [], 'Artist')
        self.choose(1, C, [D])
        run(g.night(1))
        self.assertTrue(g.g.is_drunk(g.g[B]))
        drunk = State('drunk', A, source='test', until=None)
        g.g.add(drunk)
        self.assertFalse(g.g.is_drunk(g.g[B]))
        g.g.states.remove(drunk)
        self.assertTrue(g.g.is_drunk(g.g[B]))
        g.kill(g.g[A], 'demon')
        self.assertFalse(g.g.is_drunk(g.g[B]))


class ArtistExamples(Example):
    CHARS = ['Artist', 'Clockmaker', 'Evil Twin', 'Oracle', 'Mutant', 'Fang Gu', 'Sage']

    def ask(self, g, text):
        self.visit(g, A, 'Artist', text)
        return self.told(A, 'The Storyteller answers')

    @unittest.skip('not buildable: a question about the real room (chair colours), which only a model judge could '
                   'answer')
    def test_artist_example_1(self):
        """Is the Demon in a brown chair? (wiki: Artist, example 1)"""

    def test_artist_example_2(self):
        """"Is David the Evil Twin?": yes, because he is. (wiki: Artist, example 2)"""
        g = self.game(self.CHARS)
        self.assertTrue(self.ask(g, f'Is {C} the Evil Twin?')[0].endswith('Yes.'))

    @unittest.skip('disagrees with the example: finding ESNV-1')
    def test_artist_example_3(self):
        """"How many Minions are alive?" is not a yes/no question: the Storyteller asks for another question, and the
        ability is not spent. (wiki: Artist, example 3)"""
        g = self.game(self.CHARS)
        self.ask(g, 'How many Minions are alive?')
        self.assertFalse(snv.used(g.g, g.g[A], 'Artist'))
        self.assertTrue(self.ask(g, f'Is {C} the Evil Twin?')[-1].endswith('Yes.'))

    def test_artist_example_4(self):
        """"Are we winning?" gets "I don't know" (all the Minions are dead, but the town trusts the Demon). (wiki:
        Artist, example 4)"""
        g = self.game(self.CHARS)
        g.g[C].alive = False
        self.assertTrue(self.ask(g, 'Are we winning?')[0].endswith("I don't know."))


class JugglerExamples(Example):
    def juggle(self, g, who, guesses):
        g.public_abilities([who], {who: {'ability': {'character': 'Juggler', 'target': None, 'text': '',
                                                     'guesses': [{'player': p, 'character': c} for p, c in guesses]}}})

    def test_juggler_example_1(self):
        """On day 1 the Juggler guesses a Town Crier, a No Dashii and a Sage, two of them right: a 2 that night.
        (wiki: Juggler, example 1)"""
        g = self.game(['Juggler', 'Town Crier', 'No Dashii', 'Oracle', 'Witch', 'Sage', 'Mutant'])
        self.assertFalse(g.g.is_poisoned(g.g[A]))
        self.juggle(g, A, [(B, 'Town Crier'), (C, 'No Dashii'), (D, 'Sage')])
        self.choose(2, E, [G])
        self.choose(2, C, [G])
        run(g.night(2))
        self.assertTrue(self.told(A, 'Juggler: 2 of your guesses were correct'))

    def test_juggler_example_2(self):
        """The Savant becomes the Juggler on night 4; the next day they guess one player as the Pit-Hag and the Witch,
        and another as the Pit-Hag: a 1. (wiki: Juggler, example 2)"""
        g = self.game(['Savant', 'Clockmaker', 'Witch', 'Oracle', 'Mutant', 'Fang Gu', 'Pit-Hag', 'Sage'])
        self.day(g, 3)
        self.choose(4, G, [A], 'Juggler')
        self.choose(4, C, [B])
        self.choose(4, F, [B])
        run(g.night(4))
        self.assertEqual(g.g[A].character, 'Juggler')
        self.day(g, 4)
        self.juggle(g, A, [(G, 'Pit-Hag'), (G, 'Witch'), (B, 'Pit-Hag')])
        self.choose(5, C, [D])
        self.choose(5, F, [H])
        self.choose(5, G, [D], 'Clockmaker')
        run(g.night(5))
        self.assertTrue(self.told(A, 'Juggler: 1 of your guesses was correct'))


# ---- Outsiders --------------------------------------------------------------------------------------------------

class MutantExamples(Example):
    CHARS = ['Clockmaker', 'Mutant', 'Oracle', 'Sage', 'Witch', 'Fang Gu', 'Dreamer']

    def test_mutant_example_1(self):
        """Early on day 1 the Mutant says aloud they are the Mutant: executed at once, and no nomination today (one
        execution a day). (wiki: Mutant, example 1)"""
        g = self.game(self.CHARS, forced={'Madness execution': {'yes': True}})
        self.say(g, B, 'I am the Mutant.')
        run(g.daytime(1))
        self.assertEqual(g.g.executions[0]['player'], B)
        self.assertFalse([e for e in g.events if e['kind'] == 'nominations_open'])

    def test_mutant_example_2(self):
        """The Witch reports to the Storyteller, privately, that the Mutant confided a Klutz claim to them: the
        Storyteller executes the Mutant. Here the judge hears every whisper (the default hearing), so the Mutant's
        own whisper is heard. (wiki: Mutant, example 2)"""
        g = self.game(self.CHARS, forced={'Madness execution': {'yes': True}}, judge_=judge.RulesJudge('all'))
        self.say(g, B, "I'm the Klutz, keep it quiet.", to=[E])
        self.visit(g, E, 'Artist', f'{B} told me he is the Klutz.')
        g.st.rng = random.Random(0)  # the judge's first choice
        run(g.daytime(1))
        self.assertEqual([x['player'] for x in g.g.executions], [B])

    @unittest.skip('disagrees with the example: finding ESNV-2')
    def test_mutant_example_2_report_only(self):
        """The same example where the Storyteller did not overhear the Mutant: the Witch's private report alone is
        what the Storyteller acts on. (wiki: Mutant, example 2)"""
        g = self.game(self.CHARS, forced={'Madness execution': {'yes': True}}, judge_=judge.RulesJudge('public'))
        self.say(g, B, "I'm the Klutz, keep it quiet.", to=[E])
        self.visit(g, E, 'Artist', f'{B} told me he is the Klutz.')
        g.st.rng = random.Random(0)
        run(g.daytime(1))
        self.assertEqual([x['player'] for x in g.g.executions], [B])

    @unittest.skip('disagrees with the example: finding ESNV-3')
    def test_mutant_example_3(self):
        """The Mutant says they are a Townsfolk without saying which, and stays silent when asked whether they are
        the Mutant: the Storyteller executes them. (wiki: Mutant, example 3)"""
        g = self.game(self.CHARS, forced={'Madness execution': {'yes': True}}, judge_=judge.RulesJudge())
        self.say(g, B, "I'm a Townsfolk. I won't say which.")
        self.say(g, A, f'{B}, are you the Mutant?')
        self.say(g, B, '...')
        g.st.rng = random.Random(0)
        run(g.daytime(1))
        self.assertEqual([x['player'] for x in g.g.executions], [B])

    @unittest.skip('disagrees with the example: finding ESNV-4')
    def test_mutant_example_4(self):
        """The Mutant claims the Oracle with made-up information, then says they are "definitely not the Mutant"
        with a wink: the Storyteller executes them. (wiki: Mutant, example 4)"""
        g = self.game(self.CHARS, forced={'Madness execution': {'yes': True}}, judge_=judge.RulesJudge())
        self.say(g, B, 'I am the Oracle: 1 dead player is evil. By the way, I am definitely not the Mutant. *winks*')
        g.st.rng = random.Random(0)
        run(g.daytime(1))
        self.assertEqual([x['player'] for x in g.g.executions], [B])


class SweetheartExamples(Example):
    CHARS = ['Mathematician', 'Sweetheart', 'Mutant', 'Oracle', 'Witch', 'Fang Gu', 'Sage']

    def test_sweetheart_example_1(self):
        """The Sweetheart dies and the Mathematician is drunk from now on: they may be misinformed. (wiki:
        Sweetheart, example 1)"""
        g = self.game(self.CHARS, forced={'Sweetheart:': {'players': [A]}})
        run(g.execution(B))
        run(g.run_pending())
        self.assertTrue(g.g.is_drunk(g.g[A]))
        self.assertGreater(len(snv.mathematician_choice(g.g, g.g[A], 2).values), 1)  # any number may be given

    def test_sweetheart_example_2(self):
        """The Sweetheart dies and the Mutant is drunk: the Mutant may say they are the Mutant safely. (wiki:
        Sweetheart, example 2)"""
        g = self.game(self.CHARS, forced={'Sweetheart:': {'players': [C]}, 'Madness execution': {'yes': True}})
        run(g.execution(B))
        run(g.run_pending())
        self.assertTrue(g.g.is_drunk(g.g[C]))
        self.day(g, 2)
        g.executed_today = False
        self.say(g, C, 'I am the Mutant.')
        run(g.daytime(2))
        self.assertTrue(g.g[C].alive)
        self.assertNotIn(C, [x['player'] for x in g.g.executions])

    def test_sweetheart_example_3(self):
        """The Sweetheart dies and the Demon is drunk: their attack kills nobody. (wiki: Sweetheart, example 3)"""
        g = self.game(self.CHARS, forced={'Sweetheart:': {'players': [F]}})
        run(g.execution(B))
        run(g.run_pending())
        self.choose(2, E, [C])
        self.choose(2, F, [A])
        run(g.night(2))
        self.assertTrue(g.g[A].alive)
        self.assertEqual(self.deaths(g, 2), [])


class BarberExamples(Example):
    def test_barber_example_1(self):
        """The Barber dies; the Demon thinks about swapping two players, then swaps nobody. (wiki: Barber, example
        1)"""
        g = self.game(['Clockmaker', 'Barber', 'Juggler', 'Oracle', 'Witch', 'Fang Gu', 'Sage'])
        run(g.execution(B))
        self.steps(2, F, ([D], None), ([], None))
        self.choose(2, E, [D])
        run(g.night(2))
        self.assertTrue([r for r in self.seats[F].log if r.kind == 'night' and 'Barber' in r.prompt])
        self.assertEqual([g.g[x].character for x in (A, B, C)], ['Clockmaker', 'Barber', 'Juggler'])

    def test_barber_example_2(self):
        """The Barber dies; the Demon swaps the living Snake Charmer with the dead Barber: a living Barber and a dead
        Snake Charmer. (wiki: Barber, example 2; the almanac has an Oracle)"""
        g = self.game(['Snake Charmer', 'Barber', 'Clockmaker', 'Oracle', 'Witch', 'Fang Gu', 'Sage'])
        run(g.execution(B))
        self.choose(2, A, [D])
        self.steps(2, F, ([C], None), ([A, B], None))
        self.choose(2, E, [D])
        run(g.night(2))
        self.assertEqual((g.g[A].character, g.g[A].alive), ('Barber', True))
        self.assertEqual((g.g[B].character, g.g[B].alive), ('Snake Charmer', False))

    def test_barber_example_3(self):
        """The Barber dies; the Vortox swaps themself with a living Witch. (wiki: Barber, example 3)"""
        g = self.game(['Oracle', 'Barber', 'Clockmaker', 'Sage', 'Witch', 'Vortox', 'Dreamer'])
        g.kill(g.g[B], 'demon')
        self.steps(2, F, ([C], None), ([F, E], None))
        self.choose(2, E, [D])
        self.choose(2, G, [A])
        run(g.night(2))
        self.assertEqual((g.g[E].character, g.g[E].alignment), ('Vortox', 'evil'))
        self.assertEqual((g.g[F].character, g.g[F].alignment), ('Witch', 'evil'))

    def test_barber_example_4(self):
        """The Pit-Hag made a good Demon last night; the Barber dies and the Vigormortis swaps themself with a dead
        Sweetheart, becoming the evil Sweetheart: a Demon still lives, so the game goes on. (wiki: Barber, example
        4)"""
        g = self.game(['Barber', 'Sweetheart', 'Oracle', 'Pit-Hag', 'Vigormortis', 'Clockmaker', 'Sage'],
                      forced={'Pit-Hag deaths': {'players': [], 'yes': True}, 'Barber Demon': {'players': [E]}})
        g.g[B].alive = False
        self.choose(2, D, [G], 'No Dashii')
        self.choose(2, G, [B])
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertEqual((g.g[G].character, g.g[G].alignment), ('No Dashii', 'good'))
        self.day(g, 2)
        run(g.execution(A))
        run(g.run_pending())
        self.choose(3, D, [F], 'Clockmaker')
        self.choose(3, G, [B])
        self.steps(3, E, ([C], None), ([E, B], None))
        run(g.night(3))
        self.assertEqual((g.g[E].character, g.g[E].alignment, g.g[E].alive), ('Sweetheart', 'evil', True))
        self.assertEqual((g.g[B].character, g.g[B].alive), ('Vigormortis', False))
        self.assertIsNone(g.g.check_victory())
        self.assertIsNone(g.g.winner)

    def test_barber_example_4_without_the_good_demon(self):
        """The same swap with no other Demon: the example's "because" implies the Vigormortis moved onto a dead player
        is a dead Demon, and good wins. (wiki: Barber, example 4, read the other way round)"""
        g = self.game(['Barber', 'Sweetheart', 'Oracle', 'Pit-Hag', 'Vigormortis', 'Clockmaker', 'Sage'])
        g.g[B].alive = False
        self.day(g, 2)
        run(g.execution(A))
        run(g.run_pending())
        self.choose(3, D, [F], 'Clockmaker')
        self.steps(3, E, ([C], None), ([E, B], None))
        run(g.night(3))
        self.assertEqual((g.g[B].character, g.g[B].alive), ('Vigormortis', False))
        self.assertEqual(g.g.check_victory(), 'good')


class KlutzExamples(Example):
    def test_klutz_example_1(self):
        """The executed Klutz chooses a player who is the Seamstress: the game goes on. (wiki: Klutz, example 1)"""
        g = self.game(['Klutz', 'Seamstress', 'Mutant', 'Oracle', 'Witch', 'Fang Gu', 'Sage'])
        self.seats[A].day['death_choice'] = [{'targets': [B]}]
        run(g.execution(A))
        run(g.run_pending())
        self.assertIsNone(g.g.winner)

    def test_klutz_example_2(self):
        """The Demon kills the Klutz; in the morning they choose the Demon: evil wins at once. (wiki: Klutz, example
        2)"""
        g = self.game(['Klutz', 'Clockmaker', 'Mutant', 'Oracle', 'Witch', 'Vigormortis', 'Sage'])
        self.seats[A].day['death_choice'] = [{'targets': [F]}]
        self.choose(2, E, [B])
        self.choose(2, F, [A])
        run(g.night(2))
        self.assertEqual(g.g.winner, 'evil')


# ---- Minions ----------------------------------------------------------------------------------------------------

class WitchExamples(Example):
    CHARS = ['Sage', 'Dreamer', 'Mutant', 'Oracle', 'Witch', 'Fang Gu', 'Clockmaker']

    def test_witch_example_1(self):
        """The cursed Sage nominates the Dreamer and dies at once; the vote still goes ahead and the Dreamer is
        executed. (wiki: Witch, example 1)"""
        g = self.game(self.CHARS)
        self.choose(1, E, [A])
        self.choose(1, B, [C])
        run(g.night(1))
        self.nominate(g, A, B, voters=[C, D, E, F, G])
        self.assertFalse(g.g[A].alive)
        self.assertEqual(g.g.death_log[0]['cause'], 'witch')
        self.assertEqual(g.g.executions[0]['player'], B)
        self.assertFalse(g.g[B].alive)

    def test_witch_example_2(self):
        """The Witch curses themself, nominates the Demon and dies; nobody votes, and nominations go on. (wiki: Witch,
        example 2)"""
        g = self.game(self.CHARS)
        self.choose(1, E, [E])
        self.choose(1, B, [C])
        run(g.night(1))
        self.nominate(g, E, F)
        self.assertFalse(g.g[E].alive)
        self.assertTrue(g.g[F].alive)
        self.nominate(g, A, C)
        self.assertEqual([x['nominator'] for x in g.g.nominations], [E, A])

    def test_witch_example_3(self):
        """The Witch curses the Klutz, whom the Fang Gu attacks: the Klutz becomes the Fang Gu, still cursed,
        nominates and dies: good wins. (wiki: Witch, example 3)"""
        g = self.game(['Sage', 'Dreamer', 'Klutz', 'Oracle', 'Witch', 'Fang Gu', 'Clockmaker'])
        self.choose(2, E, [C])
        self.choose(2, F, [C])
        self.choose(2, B, [D])
        run(g.night(2))
        self.assertEqual((g.g[C].character, g.g[C].alignment), ('Fang Gu', 'evil'))
        self.assertFalse(g.g[F].alive)
        self.day(g, 2)
        self.nominate(g, C, A)
        self.assertEqual(g.g.winner, 'good')

    def test_witch_example_4(self):
        """The Witch curses the Savant; the Demon's kill that night leaves three alive, so the curse is removed and
        the Savant nominates safely. (wiki: Witch, example 4)"""
        g = self.game(['Savant', 'Clockmaker', 'Witch', 'Oracle', 'Fang Gu'])
        g.g[D].alive = False
        self.choose(2, C, [A])
        self.choose(2, E, [B])
        run(g.night(2))
        self.assertEqual(g.g.alive_count(), 3)
        self.day(g, 2)
        self.nominate(g, A, C)
        self.assertTrue(g.g[A].alive)

    @unittest.skip(TRAVELLERS)
    def test_witch_example_5(self):
        """A cursed player who calls for an exile does not die. (wiki: Witch, example 5)"""


class CerenovusExamples(Example):
    CHARS = ['Clockmaker', 'Barber', 'Mutant', 'Oracle', 'Cerenovus', 'Fang Gu', 'Sage']

    def test_cerenovus_example_1(self):
        """The Barber, mad about being the Savant, claims it, visits the Storyteller, shares two made-up facts and
        firmly denies being mad: not executed. (wiki: Cerenovus, example 1)"""
        g = self.game(self.CHARS, forced={'Madness execution': {'yes': True}})
        self.choose(1, E, [B], 'Savant')
        run(g.night(1))
        self.assertTrue(self.told(B, 'you must be "mad" that you are the Savant'))
        self.say(g, B, 'I am the Savant.')
        self.visit(g, B, 'Savant')
        self.say(g, B, 'The Storyteller told me Alex is good and that there is a Witch in play.')
        self.say(g, A, f'{B}, are you mad?')
        self.say(g, B, 'No! I am not mad.')
        run(g.daytime(1))
        self.assertTrue(g.g[B].alive)
        self.assertNotIn(B, [x['player'] for x in g.g.executions])

    def test_cerenovus_example_2(self):
        """The dead Artist, mad about being the Sage, says nothing of it the next day: executed. (wiki: Cerenovus,
        example 2)"""
        g = self.game(['Artist', 'Barber', 'Mutant', 'Oracle', 'Cerenovus', 'Fang Gu', 'Sage'],
                      forced={'Madness execution': {'yes': True}})
        g.g[A].alive = False
        self.choose(1, E, [A], 'Sage')
        run(g.night(1))
        run(g.daytime(1))
        self.assertEqual(g.g.executions, [{'player': A, 'day': 1, 'died': False}])

    def test_cerenovus_example_3(self):
        """The Flowergirl, mad about being the Clockmaker, claims it aloud with a 2 but privately hints that they are
        mad; the Storyteller overhears and executes them (a judge hearing whispers). (wiki: Cerenovus, example 3)"""
        g = self.game(['Flowergirl', 'Barber', 'Mutant', 'Oracle', 'Cerenovus', 'Fang Gu', 'Sage'],
                      forced={'Madness execution': {'yes': True}}, judge_=judge.RulesJudge('all'))
        self.choose(1, E, [A], 'Clockmaker')
        run(g.night(1))
        self.say(g, A, 'I am the Clockmaker, and I learned a 2.')
        self.say(g, A, "Don't trust my 2: I'm actually mad.", to=[B])
        g.st.rng = random.Random(0)  # the judge's first choice
        run(g.daytime(1))
        self.assertEqual([x['player'] for x in g.g.executions], [A])


class PitHagExamples(Example):
    CHARS = ['Clockmaker', 'Savant', 'Sage', 'Flowergirl', 'Pit-Hag', 'Fang Gu', 'Oracle']

    def test_pit_hag_example_1(self):
        """The Pit-Hag turns the Clockmaker into the Mutant. (wiki: Pit-Hag, example 1)"""
        g = self.game(self.CHARS)
        self.choose(2, E, [A], 'Mutant')
        self.choose(2, F, [B])
        run(g.night(2))
        self.assertEqual((g.g[A].character, g.g[A].alignment), ('Mutant', 'good'))
        self.assertTrue(self.told(A, 'you are now the Mutant'))

    def test_pit_hag_example_2(self):
        """Turning the Savant into the Sage does nothing: a Sage is in play. (wiki: Pit-Hag, example 2)"""
        g = self.game(self.CHARS)
        self.choose(2, E, [B], 'Sage')
        self.choose(2, F, [A])
        run(g.night(2))
        self.assertEqual(g.g[B].character, 'Savant')
        self.assertEqual(g.g[C].character, 'Sage')

    def test_pit_hag_example_3(self):
        """The Flowergirl is made the Evil Twin by the Pit-Hag: a good Evil Twin, paired with an evil player, and
        the two learn each other. (wiki: Pit-Hag, example 3)"""
        g = self.game(self.CHARS)
        self.choose(2, E, [D], 'Evil Twin')
        self.choose(2, F, [A])
        run(g.night(2))
        self.assertEqual((g.g[D].character, g.g[D].alignment), ('Evil Twin', 'good'))
        twin = g.g.notes['Twins'][D]
        self.assertTrue(g.g[twin].evil)
        self.assertTrue(self.told(D, f'your twin is {twin}, the {g.g[twin].character}'))
        self.assertTrue(self.told(twin, f'{D} is the Evil Twin'))

    def test_pit_hag_example_4(self):
        """On the final night the Oracle is made a good No Dashii by the Pit-Hag, and the Storyteller kills only the
        evil Demon: one Demon is alive on the final day. (wiki: Pit-Hag, example 4)"""
        g = self.game(['Oracle', 'Clockmaker', 'Mutant', 'Sage', 'Pit-Hag', 'Fang Gu', 'Dreamer'],
                      forced={'Pit-Hag deaths': {'players': [F], 'yes': False}})
        for x in (C, D, G):
            g.g[x].alive = False
        self.day(g, 4)
        self.choose(5, E, [A], 'No Dashii')
        self.choose(5, F, [B])
        self.choose(5, A, [B])
        run(g.night(5))
        self.assertEqual((g.g[A].character, g.g[A].alignment, g.g[A].alive), ('No Dashii', 'good', True))
        self.assertFalse(g.g[F].alive)
        self.assertTrue(g.g[B].alive)
        self.assertEqual([p.name for p in g.g.players if p.alive and p.is_demon], [A])
        self.assertIsNone(g.g.winner)


class EvilTwinExamples(Example):
    CHARS = ['Clockmaker', 'Oracle', 'Mutant', 'Sage', 'Evil Twin', 'Fang Gu', 'Dreamer']

    def test_evil_twin_example_1(self):
        """Both twins claim the Oracle; the Evil Twin is executed and the game goes on. (wiki: Evil Twin, example
        1)"""
        g = self.game(self.CHARS)
        g.g.notes['Twins'] = {E: B}
        self.say(g, B, 'I am the Oracle.')
        self.say(g, E, 'I am the Oracle.')
        g.execute(E)
        self.assertIsNone(g.g.winner)

    def test_evil_twin_example_2(self):
        """The Pit-Hag turns the good Sage, the good twin, into the Mutant; both twins claim the Mutant, and the
        Storyteller executes the real Mutant, the good twin: evil wins. (wiki: Evil Twin, example 2)"""
        g = self.game(['Sage', 'Clockmaker', 'Oracle', 'Evil Twin', 'Pit-Hag', 'Fang Gu', 'Dreamer'],
                      forced={'Madness execution': {'yes': True}})
        g.g.notes['Twins'] = {D: A}
        self.choose(2, E, [A], 'Mutant')
        self.choose(2, F, [B])
        self.choose(2, G, [C])
        run(g.night(2))
        self.assertEqual(g.g.notes['Twins'], {D: A})
        self.day(g, 2)
        self.say(g, A, 'I am the Mutant.')
        self.say(g, D, 'I am the Mutant.')
        run(g.daytime(2))
        self.assertEqual(g.g.executions[0]['player'], A)
        self.assertEqual(g.g.winner, 'evil')

    def test_evil_twin_example_3(self):
        """Both twins claim the Artist and both visit the Storyteller; the town executes the Demon instead: the game
        goes on (both twins live), with no more deaths at night. (wiki: Evil Twin, example 3)"""
        g = self.game(['Clockmaker', 'Artist', 'Mutant', 'Oracle', 'Evil Twin', 'Fang Gu', 'Sage'])
        g.g.notes['Twins'] = {E: B}
        self.visit(g, B, 'Artist', f'Is {E} evil?')
        self.visit(g, E, 'Artist', f'Is {B} evil?')
        self.assertTrue(self.told(E, 'listened and nodded'))
        g.execute(F)
        self.assertIsNone(g.g.winner)
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])
        self.assertIsNone(g.g.winner)

    def test_evil_twin_example_4(self):
        """A good player made the Evil Twin by the Pit-Hag stays good; the town executes the good Evil Twin:
        evil wins. (wiki: Evil Twin, example 4)"""
        g = self.game(['Sage', 'Clockmaker', 'Oracle', 'Mutant', 'Pit-Hag', 'Fang Gu', 'Dreamer'],
                      forced={'Twin': {'players': [E]}})
        self.choose(2, E, [A], 'Evil Twin')
        self.choose(2, F, [B])
        self.choose(2, G, [C])
        run(g.night(2))
        self.assertEqual((g.g[A].character, g.g[A].alignment), ('Evil Twin', 'good'))
        self.day(g, 2)
        g.execute(A)
        self.assertEqual(g.g.winner, 'evil')

    def test_evil_twin_almanac_2(self):
        """The Demon dies but the game goes on, with no deaths at night; two days later the Evil Twin dies: good
        wins. (almanac S&V: Evil Twin, second example; not on the wiki)"""
        g = self.game(self.CHARS)
        g.g.notes['Twins'] = {E: B}
        g.execute(F)
        self.assertIsNone(g.g.winner)
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])
        self.day(g, 2)
        run(g.night(3))
        self.day(g, 3)
        g.execute(E)
        self.assertEqual(g.g.winner, 'good')


# ---- Demons -----------------------------------------------------------------------------------------------------

class FangGuExamples(Example):
    def test_fang_gu_example_1(self):
        """The Fang Gu kills the Artist; next night attacks the Sweetheart, who becomes the Fang Gu as the old one
        dies (the Sweetheart did not die, so nobody is made drunk); next night the new Fang Gu kills the Klutz.
        (wiki: Fang Gu, example 1)"""
        g = self.game(['Artist', 'Clockmaker', 'Sweetheart', 'Oracle', 'Witch', 'Fang Gu', 'Klutz'])
        self.seats[G].day['death_choice'] = [{'targets': [B]}]
        self.choose(2, E, [B])
        self.choose(2, F, [A])
        run(g.night(2))
        self.assertFalse(g.g[A].alive)
        self.choose(3, E, [B])
        self.choose(3, F, [C])
        run(g.night(3))
        self.assertEqual((g.g[C].character, g.g[C].alignment, g.g[C].alive), ('Fang Gu', 'evil', True))
        self.assertFalse(g.g[F].alive)
        self.assertFalse(any(g.g.is_drunk(q) for q in g.g.players))
        self.choose(4, E, [B])
        self.choose(4, C, [G])
        run(g.night(4))
        self.assertFalse(g.g[G].alive)
        self.assertEqual(g.g[G].character, 'Klutz')
        self.assertIsNone(g.g.winner)

    def test_fang_gu_almanac_2(self):
        """The Fang Gu attacks the dead Klutz, who cannot die again: the Fang Gu lives, the Klutz stays good, nobody
        dies tonight. (almanac S&V: Fang Gu, second example; not on the wiki)"""
        g = self.game(['Artist', 'Clockmaker', 'Sweetheart', 'Oracle', 'Witch', 'Fang Gu', 'Klutz'])
        g.g[G].alive = False
        self.choose(2, E, [B])
        self.choose(2, F, [G])
        run(g.night(2))
        self.assertTrue(g.g[F].alive)
        self.assertEqual((g.g[G].character, g.g[G].alignment), ('Klutz', 'good'))
        self.assertEqual(self.deaths(g, 2), [])


class VigormortisExamples(Example):
    def test_vigormortis_example_1(self):
        """The Vigormortis kills the Witch: the player the Witch cursed tonight stays cursed, and dies nominating the
        next day. (wiki: Vigormortis, example 1)"""
        g = self.game(['Clockmaker', 'Oracle', 'Witch', 'Sage', 'Vigormortis', 'Dreamer', 'Seamstress'],
                      forced={'Vigormortis': {'players': [D]}})
        self.choose(2, C, [A])
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertFalse(g.g[C].alive)
        self.assertTrue(g.g.has(g.g[A], 'cursed'))
        self.day(g, 2)
        self.nominate(g, A, B)
        self.assertFalse(g.g[A].alive)

    def test_vigormortis_example_2(self):
        """The Vigormortis kills the Evil Twin, between a Klutz and a Flowergirl, with the Sage beyond the Klutz: the
        Storyteller poisons the Sage. The almanac adds: the good twin is executed next day, and evil wins. (wiki:
        Vigormortis, example 2; almanac S&V: Vigormortis)"""
        g = self.game(['Sage', 'Klutz', 'Evil Twin', 'Flowergirl', 'Vigormortis', 'Oracle', 'Clockmaker'],
                      forced={'Vigormortis': {'players': [A]}})
        g.g.notes['Twins'] = {C: G}
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertFalse(g.g[C].alive)
        self.assertTrue(g.g.is_poisoned(g.g[A]))
        self.assertFalse(g.g.is_poisoned(g.g[D]))
        self.day(g, 2)
        g.execute(G)
        self.assertEqual(g.g.winner, 'evil')

    def test_vigormortis_example_3(self):
        """The Pit-Hag, killed by the Vigormortis, makes a Savant the Witch; that Witch, also killed, curses a player
        to death; the Pit-Hag then makes the dead Witch an Oracle (with no ability), then the Vigormortis a Vortox,
        and has no ability left. (wiki: Vigormortis, example 3)"""
        g = self.game(['Savant', 'Clockmaker', 'Mutant', 'Sage', 'Pit-Hag', 'Vigormortis', 'Dreamer'],
                      forced={'Pit-Hag deaths': {'players': [], 'yes': True}})
        self.choose(2, E, [A], 'Clockmaker')  # in play: nothing
        self.choose(2, F, [E])
        self.choose(2, G, [B])
        run(g.night(2))
        self.assertFalse(g.g[E].alive)
        self.assertTrue(g.g.works(g.g[E], 'Pit-Hag'))
        self.choose(3, E, [A], 'Witch')
        self.choose(3, F, [A])
        self.choose(3, G, [B])
        run(g.night(3))
        self.assertEqual(g.g[A].character, 'Witch')
        self.assertFalse(g.g[A].alive)
        self.choose(4, A, [D])
        self.choose(4, E, [B], 'Clockmaker')
        self.choose(4, F, [A])
        self.choose(4, G, [B])
        run(g.night(4))
        self.day(g, 4)
        self.nominate(g, D, B)
        self.assertFalse(g.g[D].alive)
        self.choose(5, E, [A], 'Oracle')
        self.choose(5, F, [A])
        self.choose(5, G, [B])
        run(g.night(5))
        self.assertEqual(g.g[A].character, 'Oracle')
        self.assertFalse(g.g.keeps_ability(g.g[A]))
        self.choose(6, E, [F], 'Vortox')
        self.choose(6, F, [A])
        self.choose(6, G, [B])
        run(g.night(6))
        self.assertEqual(g.g[F].character, 'Vortox')
        self.assertFalse(g.g.works(g.g[E], 'Pit-Hag'))


class NoDashiiExamples(Example):
    def test_no_dashii_example_1(self):
        """The No Dashii's Town Crier and Snake Charmer neighbours are poisoned; days later both are dead, and the
        nearest living neighbours (a Clockmaker, a Barber) are not poisoned. (wiki: No Dashii, example 1)"""
        g = self.game(['Clockmaker', 'Town Crier', 'No Dashii', 'Snake Charmer', 'Barber', 'Witch', 'Sage'])
        self.assertEqual(self.poisoned(g), [B, D])
        g.kill(g.g[B], 'demon')
        g.kill(g.g[D], 'demon')
        self.assertEqual(self.poisoned(g), [B, D])

    def test_no_dashii_example_2(self):
        """Clockwise a Philosopher, Mathematician, Sage; anticlockwise a Witch, Mutant, Seamstress: the Philosopher and
        the Seamstress are poisoned. (wiki: No Dashii, example 2)"""
        g = self.game(['No Dashii', 'Philosopher', 'Mathematician', 'Sage', 'Seamstress', 'Mutant', 'Witch'])
        self.assertEqual(self.poisoned(g), [B, E])

    def test_no_dashii_almanac_3(self):
        """The Pit-Hag turns the dead No Dashii into the Flowergirl, then the next night the living Fang Gu into the
        No Dashii, who now poisons its two Townsfolk neighbours. (almanac S&V: No Dashii, third example; not on the
        wiki)"""
        g = self.game(['Clockmaker', 'No Dashii', 'Oracle', 'Pit-Hag', 'Sage', 'Fang Gu', 'Dreamer'],
                      forced={'Pit-Hag deaths': {'players': [], 'yes': True}})
        g.g[B].alive = False
        self.choose(2, D, [B], 'Flowergirl')
        self.choose(2, F, [C])
        self.choose(2, G, [A])
        run(g.night(2))
        self.assertEqual(g.g[B].character, 'Flowergirl')
        self.choose(3, D, [F], 'No Dashii')
        self.choose(3, F, [A])
        self.choose(3, G, [A])
        run(g.night(3))
        self.assertEqual(g.g[F].character, 'No Dashii')
        self.assertEqual(self.poisoned(g), [E, G])


class VortoxExamples(Example):
    def test_vortox_example_1(self):
        """The Vortox kills the Sage, who is shown two players, neither of them the Demon. (wiki: Vortox, example
        1)"""
        g = self.game(['Sage', 'Clockmaker', 'Mutant', 'Oracle', 'Witch', 'Vortox', 'Dreamer'])
        self.choose(2, E, [B])
        self.choose(2, F, [A])
        self.choose(2, G, [B])
        run(g.night(2))
        self.assertNotIn(F, self.told(A, 'Sage:')[0])

    def test_vortox_example_2(self):
        """Nobody nominated or voted, but the Mutant was executed (madness): that night the Flowergirl and the Town
        Crier both learn yes. (wiki: Vortox, example 2)"""
        g = self.game(['Flowergirl', 'Town Crier', 'Mutant', 'Oracle', 'Witch', 'Vortox', 'Sage'],
                      forced={'Madness execution': {'yes': True}})
        self.say(g, C, 'I am the Mutant.')
        run(g.daytime(1))
        self.assertEqual(g.g.executions[0]['player'], C)
        self.assertEqual(g.g.nominations, [])
        self.assertIsNone(g.g.winner)
        self.choose(2, E, [D])
        self.choose(2, F, [D])
        run(g.night(2))
        self.assertTrue(self.told(A, 'Flowergirl: YES'))
        self.assertTrue(self.told(B, 'Town Crier: YES'))

    def test_vortox_example_3(self):
        """The Savant's two statements are both false; the Dreamer picks the Savant and is shown the Philosopher or
        the No Dashii. (wiki: Vortox, example 3)"""
        g = self.game(['Savant', 'Dreamer', 'Mutant', 'Oracle', 'Witch', 'Vortox', 'Sage'],
                      forced={'Dreamer:': {'characters': ['Philosopher', 'No Dashii']}})
        self.visit(g, A, 'Savant')
        said = g.g.notes['Savant told'][A]
        truth = {s['text']: s['true'] for s in snv.savant_statements(g.g, g.g[A])}
        self.assertEqual([truth[x] for x in said], [False, False])
        self.choose(2, B, [A])
        self.choose(2, E, [C])
        self.choose(2, F, [C])
        run(g.night(2))
        self.assertTrue(self.told(B, f'{A} is either the Philosopher or the No Dashii'))

    def test_vortox_example_4(self):
        """The Pit-Hag turns the Juggler into the Witch: they learn truly that they are the good Witch, since that
        comes from the Pit-Hag's ability, not a Townsfolk's. (wiki: Vortox, example 4)"""
        g = self.game(['Juggler', 'Clockmaker', 'Mutant', 'Oracle', 'Pit-Hag', 'Vortox', 'Sage'])
        self.choose(2, E, [A], 'Witch')
        self.choose(2, F, [B])
        run(g.night(2))
        self.assertEqual((g.g[A].character, g.g[A].alignment), ('Witch', 'good'))
        self.assertTrue(self.told(A, 'you are now the Witch'))
        self.assertTrue(self.told(A, 'you are still good'))

    def test_vortox_example_5(self):
        """A player died from the Witch and five nominations happened, but nobody was executed: evil wins. Tested
        without the two Travellers exiled (an exile is not an execution). (wiki: Vortox, example 5)"""
        g = self.game(['Clockmaker', 'Oracle', 'Mutant', 'Sage', 'Witch', 'Vortox', 'Dreamer', 'Seamstress'])
        self.choose(1, E, [B])
        self.choose(1, G, [A])
        run(g.night(1))
        self.day(g, 1)
        for nominator, nominee in ((B, C), (A, D), (C, E), (D, F), (G, H)):
            self.nominate(g, nominator, nominee)
        self.assertFalse(g.g[B].alive)
        self.assertEqual(g.g.death_log[0]['cause'], 'witch')
        self.assertEqual(len(g.g.nominations), 5)
        self.assertEqual(g.g.executions, [])
        self.assertIsNone(g.g.winner)
        for p in g.g.players:  # dusk: the end-of-day abilities (Game.daytime)
            for c in g.g.abilities(p):
                ch.rules(c).end_of_day(g, p)
        self.assertEqual(g.g.winner, 'evil')


if __name__ == '__main__':
    unittest.main()
