"""Trouble Brewing: every worked example on the wiki's character pages, one test each, against the engine.

Each test builds the example's setup with the real Trouble Brewing characters, plays the stated actions, and checks
the stated outcome. Where the example turns on a Storyteller's choice, that choice is forced. Examples that need a
character the engine does not build (Travellers) are left out; docs/examples-findings.md counts them. A test the
engine disagrees with is kept, skipped, and written up there (ETB-n). Trouble Brewing play is frozen (protocol v17):
these findings are recorded, never fixed."""
import asyncio
import random
import unittest

from clocktower.agents import ScriptedStoryteller
from clocktower.game import ALL_NAMES, NAMES, Game
from clocktower.llm import Reply
from clocktower.state import Grimoire, chef_choice, empath_choice, pair_choice, setup_error

A, B, C, D, E, F, G, H, I = NAMES
BLANK = {'say': '', 'whispers': [], 'nominate': None, 'vote': None, 'targets': [], 'slayer_shot': None}


class Seat:
    """Night answers from {night: answer}, votes from {nominee: yes}, other requests from {kind: [answers]} (each used
    once); records every request."""

    def __init__(self):
        self.answers, self.queue, self.votes, self.log = {}, {}, {}, []

    async def act(self, text, request):
        self.log.append(request)
        if request.kind == 'night':  # every night choice is given: Trouble Brewing fills a missing one at random
            if request.day not in self.answers:
                raise AssertionError(f'no answer for {request.prompt}')
            return Reply({**BLANK, **self.answers[request.day]})
        if request.kind == 'vote':
            return Reply({**BLANK, 'vote': self.votes.get(request.options[0], False)})
        queue = self.queue.get(request.kind)
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
    def game(self, chars, forced=None, drunk_as=None, red_herring=None):
        """A game with the Grimoire dealt as given (seat order), at day 1."""
        names = NAMES[:len(chars)]
        self.seats = {n: Seat() for n in names}
        g = Game(self.seats, Forced(forced), names=names, seed=3, characters=chars, probes=False)
        g.g = Grimoire(names, chars, drunk_as=drunk_as)
        g.g.red_herring = red_herring
        g.day, g.phase, g.g.day = 1, 'day', 1
        return g

    def answer(self, night, **answers):
        for name, targets in answers.items():
            self.seats[name].answers[night] = {'targets': targets}

    def day(self, g, n):
        g.day, g.phase, g.g.day = n, 'day', n

    def told(self, g, name):
        return [e['data']['text'] for e in g.events if e['kind'] == 'info' and e['to'] == [name]]

    def deaths(self, g, n):
        return [e['data']['deaths'] for e in g.events if e['kind'] == 'dawn' and e['data']['day'] == n][0]

    def asked(self, name, kind, day=None):
        return [r for r in self.seats[name].log if r.kind == kind and (day is None or r.day == day)]

    def st_choices(self, g, prefix):
        return [e['data'] for e in g.events if e['kind'] == 'st_choice' and e['data']['id'].startswith(prefix)]


# ---- Townsfolk --------------------------------------------------------------------------------------------------

class WasherwomanExamples(Example):
    def test_washerwoman_example_1(self):
        """The Chef and the Ravenkeeper are in play; the Washerwoman learns that one of the two is the Chef.
        (wiki: Washerwoman, example 1)"""
        chars = ['Washerwoman', 'Chef', 'Ravenkeeper', 'Monk', 'Empath', 'Poisoner', 'Imp']
        g = self.game(chars, forced={'Washerwoman': {'players': [B, C], 'character': 'Chef'}})
        self.answer(1, **{F: [D]})
        run(g.night(1))
        self.assertIn(f'either {B} or {C} is the Chef', self.told(g, A)[-1])
        choice = pair_choice(g.g, g.g[A], 'Washerwoman')
        self.assertFalse(choice.legal({'players': [D, F], 'character': 'Chef'}))  # neither is the Chef

    def test_washerwoman_example_2(self):
        """The Imp and the Virgin: the Washerwoman learns that one of them is the Virgin (an evil player may be the
        other of the two). (wiki: Washerwoman, example 2)"""
        chars = ['Washerwoman', 'Virgin', 'Chef', 'Monk', 'Empath', 'Poisoner', 'Imp']
        g = self.game(chars, forced={'Washerwoman': {'players': [G, B], 'character': 'Virgin'}})
        self.answer(1, **{F: [D]})
        run(g.night(1))
        self.assertIn(f'either {G} or {B} is the Virgin', self.told(g, A)[-1])

    def test_washerwoman_example_3(self):
        """With the Spy and the Scarlet Woman as the pair, the Washerwoman is shown the Ravenkeeper: the Spy may
        register as a Townsfolk, even one not in play. (wiki: Washerwoman, example 3)"""
        chars = ['Washerwoman', 'Chef', 'Monk', 'Empath', 'Soldier', 'Spy', 'Scarlet Woman', 'Imp']
        g = self.game(chars, forced={'Washerwoman': {'players': [F, G], 'character': 'Ravenkeeper'}})
        run(g.night(1))
        self.assertIn(f'either {F} or {G} is the Ravenkeeper', self.told(g, A)[-1])


class LibrarianExamples(Example):
    def test_librarian_example_1(self):
        """The Saint and the Baron: the Librarian learns that one of them is the Saint. (wiki: Librarian, example 1)"""
        chars = ['Librarian', 'Saint', 'Butler', 'Chef', 'Monk', 'Baron', 'Imp']
        g = self.game(chars, forced={'Librarian': {'players': [B, F], 'character': 'Saint'}})
        self.answer(1, **{C: [D]})
        run(g.night(1))
        self.assertIn(f'either {B} or {F} is the Saint', self.told(g, A)[-1])

    def test_librarian_example_2(self):
        """No Outsiders in play: the Librarian learns a zero, the only thing a sober Librarian can learn. (wiki:
        Librarian, example 2)"""
        chars = ['Librarian', 'Chef', 'Monk', 'Empath', 'Soldier', 'Poisoner', 'Imp']
        g = self.game(chars)
        self.assertTrue(pair_choice(g.g, g.g[A], 'Librarian').auto)
        self.answer(1, **{F: [D]})
        run(g.night(1))
        self.assertIn('zero Outsiders', self.told(g, A)[-1])

    def test_librarian_example_3(self):
        """The Drunk, who believes they are the Monk, and the Undertaker: the Librarian learns that one of them is
        the Drunk (their true character). (wiki: Librarian, example 3)"""
        chars = ['Librarian', 'Drunk', 'Undertaker', 'Chef', 'Empath', 'Poisoner', 'Imp']
        g = self.game(chars, forced={'Librarian': {'players': [B, C], 'character': 'Drunk'}}, drunk_as='Monk')
        self.answer(1, **{F: [D]})
        run(g.night(1))
        self.assertIn(f'either {B} or {C} is the Drunk', self.told(g, A)[-1])


class InvestigatorExamples(Example):
    def test_investigator_example_1(self):
        """The Baron and the Mayor: the Investigator learns that one of them is the Baron. (wiki: Investigator,
        example 1)"""
        chars = ['Investigator', 'Mayor', 'Saint', 'Butler', 'Chef', 'Baron', 'Imp']
        g = self.game(chars, forced={'Investigator': {'players': [F, B], 'character': 'Baron'}})
        self.answer(1, **{D: [E]})
        run(g.night(1))
        self.assertIn(f'either {F} or {B} is the Baron', self.told(g, A)[-1])

    def test_investigator_example_2(self):
        """The Spy and the Poisoner: the Investigator learns that one of them is the Spy. (wiki: Investigator,
        example 2)"""
        chars = ['Investigator', 'Mayor', 'Chef', 'Monk', 'Empath', 'Spy', 'Poisoner', 'Imp']
        g = self.game(chars, forced={'Investigator': {'players': [F, G], 'character': 'Spy'}})
        self.answer(1, **{G: [D]})
        run(g.night(1))
        self.assertIn(f'either {F} or {G} is the Spy', self.told(g, A)[-1])

    def test_investigator_example_3(self):
        """The Recluse and the Imp: the Investigator learns that one of them is the Poisoner, the Recluse registering
        as a Minion. (wiki: Investigator, example 3)"""
        chars = ['Investigator', 'Recluse', 'Chef', 'Monk', 'Empath', 'Spy', 'Imp']
        g = self.game(chars, forced={'Investigator': {'players': [B, G], 'character': 'Poisoner'}})
        run(g.night(1))
        self.assertIn(f'either {B} or {G} is the Poisoner', self.told(g, A)[-1])


class ChefExamples(Example):
    def test_chef_example_1(self):
        """No two evil players sit next to each other: the Chef learns a zero. (wiki: Chef, example 1)"""
        chars = ['Chef', 'Poisoner', 'Monk', 'Empath', 'Imp', 'Soldier', 'Mayor']
        g = self.game(chars)
        self.answer(1, **{B: [F]})
        run(g.night(1))
        self.assertIn('there are 0 pairs', self.told(g, A)[-1])

    def test_chef_example_2(self):
        """The Imp sits next to the Baron, and elsewhere the Poisoner next to the Scarlet Woman: the Chef learns a two.
        (wiki: Chef, example 2)"""
        chars = ['Chef', 'Imp', 'Baron', 'Saint', 'Butler', 'Poisoner', 'Scarlet Woman', 'Monk', 'Empath']
        g = self.game(chars)
        self.answer(1, **{E: [H], F: [H]})
        run(g.night(1))
        self.assertIn('there are 2 pairs', self.told(g, A)[-1])

    @unittest.skip('disagrees with the example: finding ETB-1')
    def test_chef_example_4(self):
        """The Recluse sits between the Imp and the Poisoner: the Chef may learn a one, the Recluse registering as
        evil for one pair and as good for the other. (wiki: Chef, example 4)"""
        chars = ['Chef', 'Imp', 'Recluse', 'Poisoner', 'Monk', 'Empath', 'Soldier']
        g = self.game(chars, forced={'Chef': {'number': 1}})
        self.answer(1, **{D: [E]})
        self.assertTrue(chef_choice(g.g, g.g[A]).legal({'number': 1}))
        run(g.night(1))
        self.assertIn('there is 1 pair', self.told(g, A)[-1])


class EmpathExamples(Example):
    def test_empath_example_1(self):
        """The Empath sits between two good players, the Soldier and the Monk: a zero. (wiki: Empath, example 1)"""
        chars = ['Soldier', 'Empath', 'Monk', 'Chef', 'Poisoner', 'Imp', 'Mayor']
        g = self.game(chars)
        self.answer(1, **{E: [D]})
        run(g.night(1))
        self.assertIn('0 of your living neighbours are evil', self.told(g, B)[-1])

    def test_empath_example_3(self):
        """Three players are alive, the Empath, the Imp and the Baron: wherever they sit, the Empath learns a two.
        (wiki: Empath, example 3)"""
        chars = ['Empath', 'Chef', 'Imp', 'Monk', 'Baron', 'Saint', 'Butler']
        g = self.game(chars)
        for name in (B, D, F, G):
            g.g[name].alive = False
        self.assertTrue(empath_choice(g.g, g.g[A]).auto)
        self.day(g, 3)
        self.answer(4, **{C: [B]})
        run(g.night(4))
        self.assertIn('2 of your living neighbours are evil', self.told(g, A)[-1])


class FortuneTellerExamples(Example):
    CHARS = ['Fortune Teller', 'Monk', 'Undertaker', 'Empath', 'Butler', 'Saint', 'Poisoner', 'Imp']

    def test_fortune_teller_example_1(self):
        """The Fortune Teller chooses the Monk and the Undertaker: a no. (wiki: Fortune Teller, example 1)"""
        g = self.game(self.CHARS, red_herring=E)
        self.answer(1, **{A: [B, C], E: [B], G: [B]})
        run(g.night(1))
        self.assertIn('NO, neither is the Demon', self.told(g, A)[-1])

    def test_fortune_teller_example_2(self):
        """The Fortune Teller chooses the Imp and the Empath: a yes. (wiki: Fortune Teller, example 2)"""
        g = self.game(self.CHARS, red_herring=E)
        self.answer(1, **{A: [H, D], E: [B], G: [B]})
        run(g.night(1))
        self.assertIn('YES, one of them is the Demon', self.told(g, A)[-1])

    def test_fortune_teller_example_3(self):
        """The Fortune Teller chooses a living Butler and a dead Imp (the Poisoner is now the Imp): a yes. (wiki:
        Fortune Teller, example 3)"""
        g = self.game(self.CHARS, red_herring=B)
        self.answer(2, **{B: [C], G: [C], H: [H], A: [E, H], E: [B]})
        run(g.night(2))
        self.assertFalse(g.g[H].alive)
        self.assertEqual(g.g[G].character, 'Imp')
        self.assertIn('YES, one of them is the Demon', self.told(g, A)[-1])

    def test_fortune_teller_example_4(self):
        """The Fortune Teller chooses themselves and the Saint, who is the red herring: a yes. (wiki: Fortune Teller,
        example 4)"""
        g = self.game(self.CHARS, red_herring=F)
        self.answer(1, **{A: [A, F], E: [B], G: [B]})
        run(g.night(1))
        self.assertIn('YES, one of them is the Demon', self.told(g, A)[-1])


class UndertakerExamples(Example):
    def test_undertaker_example_1(self):
        """After the Mayor's execution, the Undertaker sees the Mayor token that night. (wiki: Undertaker, example
        1)"""
        g = self.game(['Undertaker', 'Mayor', 'Chef', 'Monk', 'Empath', 'Poisoner', 'Imp'])
        g.execute(B)
        self.answer(2, **{D: [C], F: [C], G: [C]})
        run(g.night(2))
        self.assertIn(f'executed today ({B}) was the Mayor', self.told(g, A)[-1])

    def test_undertaker_example_2(self):
        """The Drunk, who believes they are the Virgin, is executed: the Undertaker is shown the Drunk, the true
        character. (wiki: Undertaker, example 2)"""
        g = self.game(['Undertaker', 'Drunk', 'Chef', 'Monk', 'Empath', 'Poisoner', 'Imp'], drunk_as='Virgin')
        g.execute(B)
        self.answer(2, **{D: [C], F: [C], G: [C]})
        run(g.night(2))
        self.assertIn(f'executed today ({B}) was the Drunk', self.told(g, A)[-1])

    def test_undertaker_example_4(self):
        """Nobody was executed today: the Undertaker does not wake that night. (wiki: Undertaker, example 4)"""
        g = self.game(['Undertaker', 'Mayor', 'Chef', 'Monk', 'Empath', 'Poisoner', 'Imp'])
        self.answer(2, **{D: [C], F: [C], G: [C]})
        run(g.night(2))
        self.assertEqual(self.told(g, A), [])
        self.assertNotIn(A, g.g.woke.get(2, []))


class MonkExamples(Example):
    CHARS = ['Monk', 'Fortune Teller', 'Mayor', 'Chef', 'Empath', 'Poisoner', 'Imp']

    def test_monk_example_1(self):
        """The Monk protects the Fortune Teller, whom the Imp attacks: nobody dies tonight. (wiki: Monk, example 1)"""
        g = self.game(self.CHARS, red_herring=D)
        self.answer(2, **{A: [B], B: [C, D], F: [E], G: [B]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])

    def test_monk_example_2(self):
        """The Monk protects the Mayor, whom the Imp attacks: the Mayor is safe, so their ability to send the death
        elsewhere does not trigger. Nobody dies. (wiki: Monk, example 2)"""
        g = self.game(self.CHARS, red_herring=D, forced={'Mayor': {'players': [D]}})
        self.answer(2, **{A: [C], B: [D, E], F: [E], G: [C]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])
        self.assertEqual(self.st_choices(g, 'Mayor'), [])

    def test_monk_example_3(self):
        """The Monk protects the Imp, who chooses to kill themselves: nothing happens. The Imp lives and no new Imp is
        made. (wiki: Monk, example 3)"""
        g = self.game(self.CHARS, red_herring=D)
        self.answer(2, **{A: [G], B: [D, E], F: [E], G: [G]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])
        self.assertTrue(g.g[G].alive)
        self.assertEqual((g.g[G].character, g.g[F].character), ('Imp', 'Poisoner'))


class RavenkeeperExamples(Example):
    def test_ravenkeeper_example_1(self):
        """The Imp kills the Ravenkeeper, who wakes and chooses a player, the Empath, and learns that. (wiki:
        Ravenkeeper, example 1)"""
        g = self.game(['Ravenkeeper', 'Empath', 'Chef', 'Monk', 'Soldier', 'Poisoner', 'Imp'])
        self.seats[A].queue['ravenkeeper'] = [{'targets': [B]}]
        self.answer(2, **{F: [C], G: [A], D: [C]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A])
        self.assertIn(f'{B} is the Empath', self.told(g, A)[-1])

    def test_ravenkeeper_example_2(self):
        """The Imp attacks the Mayor, and the Ravenkeeper dies instead. They choose the dead Recluse and learn the
        Scarlet Woman, the Recluse registering as a Minion. (wiki: Ravenkeeper, example 2)"""
        chars = ['Ravenkeeper', 'Mayor', 'Recluse', 'Chef', 'Monk', 'Scarlet Woman', 'Imp']
        g = self.game(chars, forced={'Mayor': {'players': [A]}, 'Ravenkeeper': {'character': 'Scarlet Woman'}})
        g.g[C].alive = False
        self.seats[A].queue['ravenkeeper'] = [{'targets': [C]}]
        self.answer(2, **{G: [B], E: [D]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A])
        self.assertTrue(g.g[B].alive)
        self.assertIn(f'{C} is the Scarlet Woman', self.told(g, A)[-1])


class VirginExamples(Example):
    CHARS = ['Virgin', 'Washerwoman', 'Drunk', 'Chef', 'Monk', 'Poisoner', 'Imp']

    def nominate(self, g, nominator, nominee):
        self.seats[nominator].queue['nominate'] = [{'nominate': nominee}]
        run(g.nominations())

    def test_virgin_example_1(self):
        """The Washerwoman nominates the Virgin: the Washerwoman is executed at once, and the day ends. (wiki: Virgin,
        example 1)"""
        g = self.game(self.CHARS, drunk_as='Chef')
        self.nominate(g, B, A)
        self.assertFalse(g.g[B].alive)
        self.assertEqual(g.g.executions, [{'player': B, 'day': 1, 'died': True}])
        self.assertEqual([len(self.asked(n, 'vote')) for n in g.names], [0] * 7)  # no vote: the day is over
        self.assertEqual([len(self.asked(n, 'nominate')) for n in g.names], [1] * 7)  # no more nominations

    def test_virgin_example_2(self):
        """The Drunk, who believes they are the Chef, nominates the Virgin: the Drunk lives (not a Townsfolk), the
        Virgin loses their ability, and the town votes on the Virgin. (wiki: Virgin, example 2)"""
        g = self.game(self.CHARS, drunk_as='Chef')
        self.nominate(g, C, A)
        self.assertTrue(g.g[C].alive)
        self.assertTrue(g.g.spent_ability('Virgin'))
        self.assertEqual(len(self.asked(D, 'vote')), 1)
        self.assertFalse(g.virgin(B, A))  # a Townsfolk nominating later is not executed

    def test_virgin_example_3(self):
        """A dead player cannot nominate, so a dead player's nomination of the Virgin does not count, and the Virgin
        keeps the ability. (wiki: Virgin, example 3)"""
        g = self.game(self.CHARS, drunk_as='Chef')
        g.g[B].alive = False
        self.nominate(g, B, A)
        self.assertEqual(self.asked(B, 'nominate'), [])
        self.assertFalse(g.g.spent_ability('Virgin'))
        self.assertTrue(g.g[B].ghost_vote)


class SlayerExamples(Example):
    CHARS = ['Slayer', 'Recluse', 'Chef', 'Monk', 'Empath', 'Scarlet Woman', 'Imp']

    def test_slayer_example_1(self):
        """A shot at the Imp kills it, and the good team wins. (wiki: Slayer, example 1)"""
        g = self.game(self.CHARS)
        g.g[F].character = 'Poisoner'  # no Scarlet Woman to take over
        g.slayer(A, G)
        self.assertFalse(g.g[G].alive)
        self.assertEqual(g.g.winner, 'good')

    def test_slayer_example_2(self):
        """The Slayer chooses the Recluse, and the Storyteller has them register as the Imp: the Recluse dies, and
        the game goes on. (wiki: Slayer, example 2)"""
        g = self.game(self.CHARS, forced={'Slayer:': {'yes': True}})
        g.slayer(A, B)
        self.assertFalse(g.g[B].alive)
        self.assertIsNone(g.g.winner)
        self.assertTrue(g.g.spent_ability('Slayer'))

    def test_slayer_example_3(self):
        """The Imp, bluffing as the Slayer, announces a shot at the Scarlet Woman: nothing happens. (wiki: Slayer,
        example 3)"""
        g = self.game(self.CHARS)
        g.slayer(G, F)
        self.assertTrue(g.g[F].alive)
        self.assertFalse(g.g.spent_ability('Slayer'))


class SoldierExamples(Example):
    def test_soldier_example_1(self):
        """The Imp attacks the Soldier, who does not die: nobody dies that night. (wiki: Soldier, example 1)"""
        g = self.game(['Soldier', 'Chef', 'Monk', 'Empath', 'Mayor', 'Poisoner', 'Imp'])
        self.answer(2, **{F: [B], G: [A], C: [B]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])

    def test_soldier_example_2(self):
        """The Poisoner poisons the Soldier and the Imp attacks them: the Soldier dies, having no ability. (wiki:
        Soldier, example 2)"""
        g = self.game(['Soldier', 'Chef', 'Monk', 'Empath', 'Mayor', 'Poisoner', 'Imp'])
        self.answer(2, **{F: [A], G: [A], C: [B]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A])

    def test_soldier_example_3(self):
        """The Imp attacks a "Soldier" who is really the Drunk: they die. (wiki: Soldier, example 3)"""
        g = self.game(['Drunk', 'Chef', 'Monk', 'Empath', 'Mayor', 'Poisoner', 'Imp'], drunk_as='Soldier')
        self.answer(2, **{F: [B], G: [A], C: [B]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A])

    @unittest.skip('disagrees with the example: finding ETB-2')
    def test_soldier_almanac_example(self):
        """The Imp attacks the Mayor and the Storyteller chooses the Soldier to die instead; the Soldier is safe from
        the Demon, so nobody dies. (almanac TB: Soldier, the example the wiki lacks)"""
        g = self.game(['Mayor', 'Soldier', 'Chef', 'Monk', 'Empath', 'Poisoner', 'Imp'],
                      forced={'Mayor': {'players': [B]}})
        self.answer(2, **{F: [C], G: [A], D: [C]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])


class MayorExamples(Example):
    def test_mayor_example_1(self):
        """The Imp attacks the Mayor, and the Storyteller has the Ravenkeeper die instead. (wiki: Mayor, example 1)"""
        g = self.game(['Mayor', 'Ravenkeeper', 'Chef', 'Monk', 'Empath', 'Poisoner', 'Imp'],
                      forced={'Mayor': {'players': [B]}})
        self.seats[B].queue['ravenkeeper'] = [{'targets': [G]}]
        self.answer(2, **{F: [C], G: [A], D: [C]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [B])
        self.assertTrue(g.g[A].alive)
        self.assertEqual(len(self.asked(B, 'ravenkeeper')), 1)  # the Ravenkeeper died at night: they wake

    def test_mayor_example_2(self):
        """Three players are alive and nobody is nominated today: good wins. (wiki: Mayor, example 2)"""
        g = self.game(['Mayor', 'Chef', 'Monk', 'Empath', 'Soldier', 'Poisoner', 'Imp'])
        for name in (B, C, D, E):
            g.g[name].alive = False
        g.private_beats = g.public_beats = 0
        run(g.daytime(1))
        self.assertEqual(g.g.winner, 'good')
        self.assertIn('Mayor', g.g.reason)


# ---- Outsiders --------------------------------------------------------------------------------------------------

class ButlerExamples(Example):
    CHARS = ['Butler', 'Chef', 'Monk', 'Empath', 'Soldier', 'Poisoner', 'Imp']

    def master_game(self, master):
        g = self.game(self.CHARS)
        self.answer(1, **{A: [master], F: [C]})
        run(g.night(1))
        self.day(g, 1)
        return g

    def votes(self, g, nominee):
        run(g.vote(nominee, None, 0))
        return [e['data'] for e in g.events if e['kind'] == 'vote_result'][-1]['voters']

    def test_butler_example_1(self):
        """The Butler chooses a master; tomorrow the Butler may vote only if the master votes too. (wiki: Butler,
        example 1)"""
        g = self.master_game(F)
        self.assertEqual(g.g.master, F)
        self.seats[A].votes = {D: True}
        self.assertEqual(self.votes(g, D), [])  # the master did not vote: the Butler's hand stays down
        self.seats[F].votes = {E: True}
        self.seats[A].votes = {E: True}
        self.assertEqual(self.votes(g, E), [F, A])

    def test_butler_example_2(self):
        """The Butler and their master both have their hands up, and the master lowers theirs before the count ends:
        the Butler must lower theirs too. (wiki: Butler, example 2) The engine asks each vote once, so this is
        checked as: the Butler's vote counts only if the master's final vote is yes, wherever the master sits."""
        g = self.master_game(B)  # the master votes after the Butler, clockwise from the nominee
        self.seats[A].votes = {G: True}
        self.seats[B].votes = {G: False}
        self.assertEqual(self.votes(g, G), [])
        self.seats[B].votes = {E: True}
        self.seats[A].votes = {E: True}
        self.assertEqual(self.votes(g, E), [A, B])

    def test_butler_example_3(self):
        """A dead Butler has no ability, so they may spend their vote token whenever they like. (wiki: Butler,
        example 3)"""
        g = self.master_game(F)
        g.g[A].alive = False
        self.seats[A].votes = {D: True}
        self.assertEqual(self.votes(g, D), [A])
        self.assertFalse(g.g[A].ghost_vote)


class DrunkExamples(Example):
    def test_drunk_example_1(self):
        """The Drunk, who believes they are the Soldier, is attacked by the Imp and dies. (wiki: Drunk, example 1)"""
        g = self.game(['Drunk', 'Chef', 'Monk', 'Empath', 'Mayor', 'Poisoner', 'Imp'], drunk_as='Soldier')
        self.answer(2, **{F: [B], G: [A], C: [B]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A])

    def test_drunk_example_2(self):
        """The Drunk, who believes they are the Empath, sits next to one evil player and learns a zero; the next night
        a one. (wiki: Drunk, example 2)"""
        g = self.game(['Poisoner', 'Drunk', 'Chef', 'Monk', 'Mayor', 'Soldier', 'Imp'], drunk_as='Empath',
                      forced={'Empath': {'number': 0}})
        self.answer(1, **{A: [E]})
        run(g.night(1))
        self.assertIn('0 of your living neighbours are evil', self.told(g, B)[-1])
        g.st.forced['Empath'] = {'number': 1}
        self.answer(2, **{A: [E], G: [E], D: [C]})
        run(g.night(2))
        self.assertIn('1 of your living neighbours is evil', self.told(g, B)[-1])

    def test_drunk_example_3(self):
        """The Drunk, who believes they are the Ravenkeeper, is killed at night, chooses the Saint, and learns the
        Poisoner. (wiki: Drunk, example 3)"""
        g = self.game(['Drunk', 'Saint', 'Chef', 'Monk', 'Empath', 'Poisoner', 'Imp'], drunk_as='Ravenkeeper',
                      forced={'Ravenkeeper': {'character': 'Poisoner'}})
        self.seats[A].queue['ravenkeeper'] = [{'targets': [B]}]
        self.answer(2, **{F: [C], G: [A], D: [C]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A])
        self.assertIn(f'{B} is the Poisoner', self.told(g, A)[-1])

    def test_drunk_example_4(self):
        """After the Fortune Teller's execution, a Drunk who thinks they are the Undertaker is shown the Drunk token
        that night. (wiki: Drunk, example 4)"""
        g = self.game(['Drunk', 'Fortune Teller', 'Chef', 'Monk', 'Empath', 'Poisoner', 'Imp'], drunk_as='Undertaker',
                      red_herring=C, forced={'Undertaker': {'character': 'Drunk'}})
        g.execute(B)
        self.answer(2, **{F: [C], G: [C], D: [E]})
        run(g.night(2))
        self.assertIn(f'executed today ({B}) was the Drunk', self.told(g, A)[-1])


class RecluseExamples(Example):
    def test_recluse_example_1(self):
        """The Slayer shoots the Recluse, whom the Storyteller has register as the Imp: the Recluse dies (and the
        Slayer believes they killed the Imp; the game goes on). (wiki: Recluse, example 1)"""
        g = self.game(['Slayer', 'Recluse', 'Chef', 'Monk', 'Empath', 'Poisoner', 'Imp'],
                      forced={'Slayer:': {'yes': True}})
        g.slayer(A, B)
        self.assertFalse(g.g[B].alive)
        self.assertEqual([e['data']['died'] for e in g.events if e['kind'] == 'slayer'], [True])
        self.assertIsNone(g.g.winner)

    def test_recluse_example_2(self):
        """The Empath neighbours the Recluse and the Monk: one night a one, the next night a zero. (wiki: Recluse,
        example 2)"""
        g = self.game(['Recluse', 'Empath', 'Monk', 'Chef', 'Soldier', 'Poisoner', 'Imp'],
                      forced={'Empath': {'number': 1}})
        self.answer(1, **{F: [E]})
        run(g.night(1))
        self.assertIn('1 of your living neighbours is evil', self.told(g, B)[-1])
        g.st.forced['Empath'] = {'number': 0}
        self.answer(2, **{F: [E], G: [E], C: [D]})
        run(g.night(2))
        self.assertIn('0 of your living neighbours are evil', self.told(g, B)[-1])

    def test_recluse_example_3(self):
        """The Investigator learns that the Recluse or the Saint is the Scarlet Woman. (wiki: Recluse, example 3)"""
        g = self.game(['Investigator', 'Recluse', 'Saint', 'Chef', 'Monk', 'Poisoner', 'Imp'],
                      forced={'Investigator': {'players': [B, C], 'character': 'Scarlet Woman'}})
        self.answer(1, **{F: [D]})
        run(g.night(1))
        self.assertIn(f'either {B} or {C} is the Scarlet Woman', self.told(g, A)[-1])

    def test_recluse_example_4(self):
        """After the Recluse's execution, the Undertaker may be shown the Imp. (wiki: Recluse, example 4)"""
        g = self.game(['Undertaker', 'Recluse', 'Chef', 'Monk', 'Empath', 'Poisoner', 'Imp'],
                      forced={'Undertaker': {'character': 'Imp'}})
        g.execute(B)
        self.answer(2, **{F: [C], G: [C], D: [E]})
        run(g.night(2))
        self.assertIn(f'executed today ({B}) was the Imp', self.told(g, A)[-1])


class SaintExamples(Example):
    def test_saint_example_1(self):
        """Seven alive: the Saint gets four votes; the Baron, nominated next, gets only three; nothing else: the Saint
        is executed, and evil wins. (wiki: Saint, example 1)"""
        g = self.game(['Saint', 'Chef', 'Monk', 'Empath', 'Soldier', 'Baron', 'Imp'])
        for name in (B, C, D, E):
            self.seats[name].votes = {A: True}
        for name in (B, C, D):
            self.seats[name].votes[F] = True
        block, top = run(g.vote(A, None, 0))
        self.assertEqual((block, top), (A, 4))
        block, top = run(g.vote(F, block, top))
        self.assertEqual((block, top), (A, 4))
        run(g.execution(block))
        self.assertEqual(g.g.winner, 'evil')


# ---- Minions ----------------------------------------------------------------------------------------------------

class PoisonerExamples(Example):
    def test_poisoner_example_1(self):
        """A poisoned Slayer shoots the Imp the following day: no death, and the once-per-game shot is spent.
        (wiki: Poisoner, example 1)"""
        g = self.game(['Slayer', 'Chef', 'Monk', 'Empath', 'Soldier', 'Poisoner', 'Imp'])
        self.answer(1, **{F: [A]})
        run(g.night(1))
        self.day(g, 1)
        g.slayer(A, G)
        self.assertTrue(g.g[G].alive)
        self.assertTrue(g.g.spent_ability('Slayer'))

    def test_poisoner_example_2(self):
        """The poisoned Empath, between two evil players, learns a zero; the next night, no longer poisoned, the truth:
        a two. (wiki: Poisoner, example 2)"""
        g = self.game(['Poisoner', 'Empath', 'Imp', 'Chef', 'Monk', 'Soldier', 'Mayor'],
                      forced={'Empath': {'number': 0}})
        self.answer(1, **{A: [B]})
        run(g.night(1))
        self.assertIn('0 of your living neighbours are evil', self.told(g, B)[-1])
        self.answer(2, **{A: [D], C: [F], E: [F]})
        run(g.night(2))
        self.assertIn('2 of your living neighbours are evil', self.told(g, B)[-1])

    def test_poisoner_example_3(self):
        """The poisoned Investigator learns that one of two players is the Baron, though neither is a Minion. (wiki:
        Poisoner, example 3)"""
        g = self.game(['Investigator', 'Chef', 'Monk', 'Empath', 'Soldier', 'Poisoner', 'Imp'],
                      forced={'Investigator': {'players': [B, C], 'character': 'Baron'}})
        self.answer(1, **{F: [A]})
        run(g.night(1))
        self.assertIn(f'either {B} or {C} is the Baron', self.told(g, A)[-1])

    def test_poisoner_example_4(self):
        """The poisoned Undertaker learns that the Virgin died, though it was the Imp (the Scarlet Woman took over).
        Days later a poisoned Saint is executed and the game goes on. (wiki: Poisoner, example 4)"""
        chars = ['Undertaker', 'Virgin', 'Saint', 'Chef', 'Monk', 'Empath', 'Poisoner', 'Scarlet Woman', 'Imp']
        g = self.game(chars, forced={'Undertaker': {'character': 'Virgin'}})
        g.execute(I)
        self.assertEqual(g.g[H].character, 'Imp')
        self.answer(2, **{G: [A], H: [D], E: [F]})
        run(g.night(2))
        self.assertIn(f'executed today ({I}) was the Virgin', self.told(g, A)[-1])
        self.day(g, 2)
        self.answer(3, **{G: [C], H: [D], E: [F]})
        run(g.night(3))
        self.day(g, 3)
        g.execute(C)
        self.assertFalse(g.g[C].alive)
        self.assertIsNone(g.g.winner)

    def test_poisoner_example_5(self):
        """Once the Poisoner who poisoned the Mayor has become the Imp, the poison ends: nobody is the Poisoner any
        more. (wiki: Poisoner, example 5)"""
        g = self.game(['Mayor', 'Chef', 'Monk', 'Empath', 'Soldier', 'Poisoner', 'Imp'])
        self.answer(2, **{F: [A], G: [G], C: [B]})
        run(g.night(2))
        self.assertEqual(g.g[F].character, 'Imp')
        self.assertFalse(g.g.is_poisoned(g.g[A]))


class SpyExamples(Example):
    def test_spy_example_1(self):
        """The Washerwoman learns that the Monk or the Spy is the Ravenkeeper, the Spy registering as the Ravenkeeper.
        (wiki: Spy, example 1)"""
        g = self.game(['Washerwoman', 'Monk', 'Chef', 'Spy', 'Empath', 'Soldier', 'Imp'],
                      forced={'Washerwoman': {'players': [B, D], 'character': 'Ravenkeeper'}})
        run(g.night(1))
        self.assertIn(f'either {B} or {D} is the Ravenkeeper', self.told(g, A)[-1])

    def test_spy_example_2(self):
        """The Spy sits between the Imp and the Empath: the Chef learns a one (the Spy registering as evil) and later
        that night the Empath a zero (the Spy registering as good). (wiki: Spy, example 2)"""
        g = self.game(['Chef', 'Imp', 'Spy', 'Empath', 'Monk', 'Soldier', 'Mayor'],
                      forced={'Chef': {'number': 1}, 'Empath': {'number': 0}})
        run(g.night(1))
        self.assertIn('there is 1 pair', self.told(g, A)[-1])
        self.assertIn('0 of your living neighbours are evil', self.told(g, D)[-1])

    def test_spy_example_3(self):
        """The Spy, registering as a Townsfolk, dies by the Virgin's ability after nominating her; at night the
        Undertaker sees the Drunk token, the Spy now registering as the Drunk. (wiki: Spy, example 3)"""
        g = self.game(['Virgin', 'Undertaker', 'Chef', 'Monk', 'Empath', 'Spy', 'Imp'],
                      forced={'Virgin:': {'yes': True}, 'Undertaker': {'character': 'Drunk'}})
        self.assertTrue(g.virgin(F, A))
        self.assertFalse(g.g[F].alive)
        self.assertIsNone(g.g.winner)
        self.answer(2, **{G: [C], D: [C]})
        run(g.night(2))
        self.assertIn(f'executed today ({F}) was the Drunk', self.told(g, B)[-1])


class ScarletWomanExamples(Example):
    def test_scarlet_woman_example_2(self):
        """With five alive (the Imp, the Scarlet Woman, the Baron, two Townsfolk), executing the Imp makes her the
        Imp, and play continues. (wiki: Scarlet Woman, example 2)"""
        g = self.game(['Chef', 'Monk', 'Saint', 'Butler', 'Baron', 'Scarlet Woman', 'Imp'])
        g.g[C].alive = g.g[D].alive = False
        g.execute(G)
        self.assertEqual(g.g[F].character, 'Imp')
        self.assertIsNone(g.g.winner)

    def test_scarlet_woman_example_3(self):
        """The Fortune Teller chooses the Scarlet Woman and another player: a no. The Imp dies and she becomes the
        Imp; the same two now give a yes. (wiki: Scarlet Woman, example 3)"""
        g = self.game(['Fortune Teller', 'Scarlet Woman', 'Chef', 'Monk', 'Empath', 'Soldier', 'Imp'], red_herring=C)
        self.answer(1, **{A: [B, D]})
        run(g.night(1))
        self.assertIn('NO, neither is the Demon', self.told(g, A)[-1])
        g.execute(G)
        self.assertEqual(g.g[B].character, 'Imp')
        self.answer(2, **{A: [B, D], B: [E], D: [E]})
        run(g.night(2))
        self.assertIn('YES, one of them is the Demon', self.told(g, A)[-1])


class BaronExamples(Example):
    def test_baron_example_1(self):
        """Seven players would be five Townsfolk, a Minion and the Demon; with the Baron, two Townsfolk give way to
        two Outsiders (the Saint and the Butler): three, two, one and one. (wiki: Baron, example 1)"""
        self.assertIsNone(setup_error(['Chef', 'Monk', 'Empath', 'Saint', 'Butler', 'Baron', 'Imp']))
        self.assertIsNotNone(setup_error(['Chef', 'Monk', 'Empath', 'Mayor', 'Soldier', 'Baron', 'Imp']))
        self.assertIsNone(setup_error(['Chef', 'Monk', 'Empath', 'Mayor', 'Soldier', 'Poisoner', 'Imp']))

    def test_baron_example_2(self):
        """Fifteen players would be nine Townsfolk, two Outsiders, three Minions and the Demon; with the Baron, two
        more Outsiders, the Recluse and the Drunk (who believes they are a Townsfolk): seven Townsfolk tokens and the
        Drunk among the players. (wiki: Baron, example 2)"""
        towns = ['Washerwoman', 'Librarian', 'Investigator', 'Chef', 'Empath', 'Fortune Teller', 'Undertaker',
                 'Monk', 'Ravenkeeper']
        evil = ['Baron', 'Poisoner', 'Spy', 'Imp']
        self.assertIsNone(setup_error(towns[:7] + ['Butler', 'Saint', 'Recluse', 'Drunk'] + evil))
        self.assertIsNotNone(setup_error(towns + ['Butler', 'Saint'] + evil))


# ---- Demon ------------------------------------------------------------------------------------------------------

class ImpExamples(Example):
    def test_imp_example_1(self):
        """On the first night the Imp learns its two Minions and three good characters not in play (the rest is the
        Imp's bluffing, not rules). Later the Imp is executed, and good wins. (wiki: Imp, example 1)"""
        chars = ['Chef', 'Poisoner', 'Monk', 'Empath', 'Spy', 'Soldier', 'Mayor', 'Undertaker', 'Ravenkeeper', 'Imp']
        names = ALL_NAMES[:10]  # ten players: two Minions
        self.seats = {n: Seat() for n in names}
        g = Game(self.seats, Forced({'bluffs': {'characters': ['Librarian', 'Virgin', 'Slayer']}}), names=names,
                 seed=3, characters=chars, probes=False)
        run(g.setup())
        intro = {e['to'][0]: e['data']['text'] for e in g.events if e['kind'] == 'intro'}
        self.assertIn(f'Your Minions: {B}, {E}', intro[names[9]])
        self.assertIn('not in play, for evil to bluff: Librarian, Virgin, Slayer.', intro[names[9]])
        self.assertFalse(set(g.g.bluffs) & set(chars))
        g.day, g.phase, g.g.day = 4, 'day', 4
        g.execute(names[9])
        self.assertEqual(g.g.winner, 'good')

    def test_imp_example_2(self):
        """The Imp kills a player one night; the next night it chooses itself and dies, and the Poisoner becomes the
        Imp. (wiki: Imp, example 2)"""
        g = self.game(['Chef', 'Monk', 'Empath', 'Soldier', 'Mayor', 'Poisoner', 'Imp'])
        self.answer(2, **{F: [A], G: [A], B: [C]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A])
        self.day(g, 2)
        self.answer(3, **{F: [B], G: [G], B: [C]})
        run(g.night(3))
        self.assertEqual(self.deaths(g, 3), [G])
        self.assertEqual(g.g[F].character, 'Imp')
        self.assertIsNone(g.g.check_victory())


if __name__ == '__main__':
    unittest.main()
