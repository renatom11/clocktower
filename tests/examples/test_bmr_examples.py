"""Bad Moon Rising: every worked example on the wiki's character pages (and the almanac's where the wiki lacks one),
one test each, against the engine.

Each test builds the example's setup with the real Bad Moon Rising characters on the real script, plays the stated
actions, and checks the stated outcome. Where the example turns on a Storyteller's choice, that choice is forced.
Examples that need a character the engine does not build (Travellers) are left out, or tested without that part when
the rest stands on its own (said in the docstring); docs/examples-findings.md counts them. A test the engine disagrees
with is kept, skipped, and written up there (EBMR-n)."""
import asyncio
import random
import unittest

from clocktower import characters as ch
from clocktower.agents import ScriptedStoryteller
from clocktower.game import ALL_NAMES, Game
from clocktower.llm import Reply
from clocktower.render import render
from clocktower.state import Grimoire, State

A, B, C, D, E, F, G, H, I, J = ALL_NAMES[:10]
BLANK = {'say': '', 'whispers': [], 'nominate': None, 'vote': None, 'targets': []}
BMR = ch.Script('bmr')


class Seat:
    """Night answers from {night: answer} (a list: one per step woken that night, in order), every other request
    from {kind: [answers]} (each used once; 'retry' answers a required choice asked again); records every request.
    A night request with no answer given fails the test, so no choice is left to chance."""

    def __init__(self):
        self.answers, self.queue, self.log = {}, {}, []

    async def act(self, text, request):
        self.log.append(request)
        kind = 'retry' if request.prompt.startswith('(That is not a legal choice') else request.kind
        if kind == 'night':
            if request.day not in self.answers:
                raise AssertionError(f'no answer for {request.prompt}')
            answer = self.answers[request.day]
            if isinstance(answer, list):
                answer = answer.pop(0)
            return Reply({**BLANK, **answer})
        queue = self.queue.get(kind)
        if queue:
            return Reply({**BLANK, **queue.pop(0)})
        if kind in ('retry', 'death_choice'):
            raise AssertionError(f'no answer for {request.prompt}')
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
    def game(self, chars, forced=None):
        """A game on the Bad Moon Rising script with the Grimoire dealt as given (seat order), at day 1."""
        names = ALL_NAMES[:len(chars)]
        self.seats = {n: Seat() for n in names}
        g = Game(self.seats, Forced(forced), names=names, seed=3, characters=chars, script=BMR, probes=False)
        g.g = Grimoire(names, chars, script=BMR)
        g.day, g.phase, g.g.day = 1, 'day', 1
        return g

    def answer(self, night, **answers):
        """Each player's targets on `night` (a list of lists: one per step they wake for)."""
        for name, targets in answers.items():
            if targets and isinstance(targets[0], list):
                self.seats[name].answers[night] = [{'targets': t} for t in targets]
            else:
                self.seats[name].answers[night] = {'targets': targets}

    def choose(self, night, name, targets=(), character=None):
        """`name`'s answer on `night`: players and a character (the Gambler, the Courtier)."""
        self.seats[name].answers[night] = {'targets': list(targets), 'character': character}

    def curse(self, name, target):
        """The Moonchild's answer when they learn they died."""
        self.seats[name].queue.setdefault('death_choice', []).append({'targets': [target]})

    def day(self, g, n):
        g.day, g.phase, g.g.day = n, 'day', n

    def deaths(self, g, n):
        return [e['data']['deaths'] for e in g.events if e['kind'] == 'dawn' and e['data']['day'] == n][0]

    def asked(self, name, night):
        return [r for r in self.seats[name].log if r.kind == 'night' and r.day == night]

    def told(self, g, name):
        return [e['data']['text'] for e in g.events if e['kind'] == 'info' and e['to'] == [name]]

    def drunk(self, g, name):
        return g.g.is_drunk(g.g[name])

    def say(self, g, name, text, character='Gossip'):
        g.public_abilities([name], {name: {'ability': {'character': character, 'text': text}}})
        run(g.run_pending())


# ---- Minions ----------------------------------------------------------------------------------------------------

class GodfatherExamples(Example):
    def test_godfather_example_1(self):
        """Night 1: the Godfather is shown that the Outsiders in play are the Lunatic and the Moonchild (its Tinker
        bluff is the player's choice). An Outsider, the Lunatic, is executed on day 3, so that night two die: the
        Minstrel to the Po, the Pacifist to the Godfather. (wiki: Godfather, example 1)"""
        g = self.game(['Lunatic', 'Moonchild', 'Minstrel', 'Pacifist', 'Gossip', 'Fool', 'Godfather', 'Po'])
        g.g[A].shown = 'Po'
        run(g.night(1))
        self.assertIn('the Outsiders in play are: Lunatic, Moonchild', self.told(g, G)[-1])
        self.day(g, 3)
        g.execute(A)
        self.answer(4, **{G: [D], H: [C]})
        run(g.night(4))
        self.assertEqual(self.deaths(g, 4), [C, D])
        self.assertEqual({d['player']: d['cause'] for d in g.g.death_log if d['phase'] == 'night'},
                         {C: 'demon', D: 'godfather'})

    def test_godfather_example_2(self):
        """A Tinker saved from execution by the Devil's Advocate has not died, so the Godfather sleeps that
        night. When the Tinker's own ability kills them the following day, the Godfather may kill that night, and
        picks itself (to look good), beside the Demon's kill. (wiki: Godfather, example 2)"""
        g = self.game(['Tinker', 'Minstrel', 'Pacifist', 'Gossip', 'Fool', 'Tea Lady', 'Godfather',
                       "Devil's Advocate", 'Po'], forced={f'Tinker:{A}': {'yes': False}})
        self.answer(1, **{H: [A]})
        run(g.night(1))
        self.day(g, 1)
        g.execute(A)
        self.assertTrue(g.g[A].alive)
        self.answer(2, **{H: [B], I: [C]})
        run(g.night(2))
        self.assertEqual(self.asked(G, 2), [])
        self.day(g, 2)
        g.st.forced[f'Tinker:{A}'] = {'yes': True}
        g.moment('beat')
        self.assertFalse(g.g[A].alive)
        self.answer(3, **{G: [G], H: [E], I: [D]})
        run(g.night(3))
        self.assertEqual(self.deaths(g, 3), [D, G])


class DevilsAdvocateExamples(Example):
    CHARS = ['Grandmother', 'Tinker', 'Minstrel', 'Pacifist', 'Gossip', 'Fool', "Devil's Advocate", 'Zombuul']

    def test_devils_advocate_example_1(self):
        """The Devil's Advocate protects themself; executed the next day, they live. (wiki: Devil's Advocate,
        example 1)"""
        g = self.game(self.CHARS, forced={'Grandchild': {'players': [C]}, 'Tinker': {'yes': False}})
        self.answer(1, **{G: [G]})
        run(g.night(1))
        self.day(g, 1)
        g.execute(G)
        self.assertTrue(g.g[G].alive)
        self.assertEqual(g.g.executions, [{'player': G, 'day': 1, 'died': False}])

    def test_devils_advocate_example_2(self):
        """The Devil's Advocate protects the Zombuul, executed but not even seeming dead; executed again the next day,
        it registers as dead. (wiki: Devil's Advocate, example 2)"""
        g = self.game(self.CHARS, forced={'Grandchild': {'players': [C]}, 'Tinker': {'yes': False}})
        self.answer(1, **{G: [H]})
        run(g.night(1))
        self.day(g, 1)
        g.execute(H)
        self.assertTrue(g.g[H].appears_alive)
        self.answer(2, **{G: [A], H: [E]})  # nobody died today: the Zombuul attacks
        run(g.night(2))
        self.day(g, 2)
        g.execute(H)
        self.assertTrue(g.g[H].alive and g.g[H].seems_dead)
        self.assertIsNone(g.g.check_victory())

    def test_devils_advocate_example_3(self):
        """The Devil's Advocate protects the Grandmother, who is executed and lives. Later it protects the Tinker, who
        is executed and lives, but the Storyteller kills the Tinker by the Tinker's ability. (wiki: Devil's Advocate,
        example 3; its last part, the Judge forcing an execution, needs a Traveller and is left out)"""
        g = self.game(self.CHARS, forced={'Grandchild': {'players': [C]}, 'Tinker': {'yes': False}})
        self.answer(1, **{G: [A]})
        run(g.night(1))
        self.day(g, 1)
        g.execute(A)
        self.assertTrue(g.g[A].alive)
        self.answer(2, **{G: [B], H: [C]})
        run(g.night(2))
        self.day(g, 2)
        g.execute(B)
        self.assertTrue(g.g[B].alive)
        g.st.forced['Tinker'] = {'yes': True}
        g.moment('dusk')
        self.assertFalse(g.g[B].alive)
        self.assertEqual(g.g.death_log[-1]['cause'], 'tinker')


class AssassinExamples(Example):
    def test_assassin_example_1(self):
        """For three nights the Assassin wakes but does nothing; on the fourth it kills the Fool, who dies and stays
        dead though their ability is unused. (wiki: Assassin, example 1)"""
        g = self.game(['Fool', 'Minstrel', 'Pacifist', 'Gossip', 'Tea Lady', 'Assassin', 'Po'])
        run(g.night(1))
        for n, victim in ((2, B), (3, C), (4, D)):
            self.answer(n, **{F: [], G: [victim]})
            run(g.night(n))
            self.day(g, n)
        self.assertEqual([len(self.asked(F, n)) for n in (1, 2, 3, 4)], [0, 1, 1, 1])
        self.answer(5, **{F: [A], G: [E]})
        run(g.night(5))
        self.assertFalse(g.g[A].alive)
        self.assertFalse(g.g.spent_ability('Fool'))
        self.assertIn(A, self.deaths(g, 5))

    def test_assassin_example_2(self):
        """The Tea Lady's neighbours are both good; the Assassin kills one of them, who dies though she protects them.
        (wiki: Assassin, example 2)"""
        g = self.game(['Gossip', 'Tea Lady', 'Minstrel', 'Pacifist', 'Fool', 'Assassin', 'Po'])
        self.assertTrue(g.g.safe(g.g[A], 'demon'))
        self.answer(2, **{F: [A], G: []})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A])

    def test_assassin_example_3(self):
        """An executed Mastermind sets off the Minstrel, so on that night the Assassin is drunk: its pick, the
        Moonchild, lives. (wiki: Assassin, example 3)"""
        g = self.game(['Minstrel', 'Moonchild', 'Pacifist', 'Gossip', 'Fool', 'Tea Lady', 'Mastermind', 'Assassin',
                       'Po'])
        g.execute(G)
        self.answer(2, **{H: [B], I: [C]})
        run(g.night(2))
        self.assertTrue(g.g[B].alive)
        self.assertTrue(g.g.spent_ability('Assassin'))
        self.assertEqual(self.deaths(g, 2), [])

    def test_assassin_example_4(self):
        """The Assassin, drunk because of the Courtier, chooses the Goon: no kill, but the Goon turns evil. (wiki:
        Assassin, example 4)"""
        g = self.game(['Courtier', 'Goon', 'Minstrel', 'Pacifist', 'Gossip', 'Assassin', 'Po'])
        self.choose(1, A, character='Assassin')
        run(g.night(1))
        self.assertTrue(self.drunk(g, F))
        self.answer(2, **{F: [B], G: []})
        run(g.night(2))
        self.assertTrue(g.g[B].alive and g.g[B].evil)


class MastermindExamples(Example):
    def test_mastermind_example_1(self):
        """After the executed Shabaloth, the Mastermind's extra day: a good player (the Professor) executed and
        dying then means evil wins. (wiki: Mastermind, example 1)"""
        g = self.game(['Professor', 'Minstrel', 'Pacifist', 'Gossip', 'Fool', 'Mastermind', 'Shabaloth'])
        g.execute(G)
        self.assertIsNone(g.g.winner)
        self.answer(2, **{A: []})
        run(g.night(2))
        self.assertIsNone(g.g.check_victory())
        self.day(g, 2)
        g.execute(A)
        self.assertEqual(g.g.winner, 'evil')

    def test_mastermind_example_2(self):
        """After the executed Po, the Mastermind's extra day: the Godfather, protected by the Devil's
        Advocate, survives the execution, but executing an evil player is enough for good to win. (wiki: Mastermind,
        example 2)"""
        g = self.game(['Minstrel', 'Pacifist', 'Gossip', 'Fool', 'Tea Lady', 'Moonchild', 'Mastermind', 'Godfather',
                       "Devil's Advocate", 'Po'])
        g.execute(J)
        self.assertIsNone(g.g.winner)
        self.answer(2, **{I: [H]})
        run(g.night(2))
        self.day(g, 2)
        g.execute(H)
        self.assertTrue(g.g[H].alive)
        self.assertEqual(g.g.winner, 'good')

    def test_mastermind_example_3(self):
        """The Zombuul is executed and seems to die: the game would not have ended, so the Mastermind's ability waits.
        Executed again, it dies for real; now the Mastermind's ability gives one more day. (wiki: Mastermind,
        example 3)"""
        g = self.game(['Minstrel', 'Pacifist', 'Gossip', 'Fool', 'Tea Lady', 'Mastermind', 'Zombuul'])
        g.execute(G)
        self.assertNotIn('Mastermind', g.g.notes)
        self.answer(2, **{G: [A]})
        run(g.night(2))
        self.day(g, 2)
        g.execute(G)
        self.assertFalse(g.g[G].alive)
        self.assertIsNone(g.g.winner)
        self.assertEqual(g.g.notes['Mastermind'], 2)

    def test_mastermind_example_4(self):
        """Three alive; the Demon dies. The next day, two alive, good does not execute; at nightfall, the Demon being
        dead, good wins. (wiki: Mastermind, example 4)"""
        g = self.game(['Minstrel', 'Pacifist', 'Gossip', 'Fool', 'Tea Lady', 'Mastermind', 'Po'])
        for name in (A, B, C, D):
            g.g[name].alive = False
        g.execute(G)
        self.assertEqual(g.g.alive_count(), 2)
        self.assertIsNone(g.g.check_victory())
        run(g.night(2))
        self.day(g, 2)
        g.moment('dusk')
        self.assertEqual(g.g.check_victory(), 'good')


# ---- Demons -----------------------------------------------------------------------------------------------------

class ZombuulExamples(Example):
    CHARS = ['Minstrel', 'Pacifist', 'Gossip', 'Fool', 'Tea Lady', 'Godfather', 'Zombuul']

    def test_zombuul_example_1(self):
        """The Zombuul is executed and seems to die; it cannot attack tonight. Days later only two players appear
        alive, and the game goes on until one more dies. (wiki: Zombuul, example 1)"""
        g = self.game(self.CHARS)
        g.execute(G)
        self.assertTrue(g.g[G].alive and g.g[G].seems_dead)
        self.answer(2, **{G: [A]})
        run(g.night(2))
        self.assertEqual(self.asked(G, 2), [])
        for name in (A, B, C, D):
            g.g[name].alive = False
        self.assertEqual(sum(p.appears_alive for p in g.g.players), 2)
        self.assertIsNone(g.g.check_victory())
        g.kill(g.g[E], 'demon')
        self.assertEqual(g.g.check_victory(), 'evil')

    def test_zombuul_example_2(self):
        """A day with no death lets the Zombuul attack that night; after a day on which the Tinker died, it
        sleeps. (wiki: Zombuul, example 2)"""
        g = self.game(['Tinker', 'Pacifist', 'Gossip', 'Fool', 'Tea Lady', 'Minstrel', 'Assassin', 'Zombuul'],
                      forced={'Tinker': {'yes': False}})
        self.answer(2, **{G: [], H: [B]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [B])
        self.day(g, 2)
        g.st.forced['Tinker'] = {'yes': True}
        g.moment('beat')
        self.assertFalse(g.g[A].alive)
        self.answer(3, **{G: [], H: [C]})
        run(g.night(3))
        self.assertEqual(self.asked(H, 3), [])
        self.assertEqual(self.deaths(g, 3), [])


class PukkaExamples(Example):
    def test_pukka_example_1(self):
        """The Pukka poisons the Chambermaid, who gets false information; the next night the Chambermaid dies.
        (wiki: Pukka, example 1)"""
        g = self.game(['Chambermaid', 'Pacifist', 'Gossip', 'Fool', 'Tea Lady', 'Godfather', 'Pukka'],
                      forced={'Chambermaid': {'number': 2}})
        self.answer(1, **{A: [B, C], G: [A]})
        run(g.night(1))
        self.assertIn('2 of them woke', self.told(g, A)[-1])  # neither woke: false, so only for an impaired one
        self.answer(2, **{A: [B, C], G: [D]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A])

    def test_pukka_example_2(self):
        """Poisoned by the Pukka, the Fool has no ability and dies when executed, so nobody dies of the poison
        that night, when the Gossip is poisoned. Drunk the night after, the Pukka poisons nobody (its pick, the
        Tinker, is fine) and the Gossip lives on; once it is sober again, the Gossip dies. (wiki: Pukka, example 2)"""
        g = self.game(['Fool', 'Gossip', 'Tinker', 'Pacifist', 'Tea Lady', 'Godfather', 'Pukka'],
                      forced={'Tinker': {'yes': False}})
        self.answer(1, **{G: [A]})
        run(g.night(1))
        self.day(g, 1)
        g.execute(A)
        self.assertFalse(g.g[A].alive)
        self.answer(2, **{G: [B]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])
        self.day(g, 2)
        g.g.add(State('drunk', G, until=4))  # drunk for night 3
        self.answer(3, **{G: [C]})
        run(g.night(3))
        self.assertEqual(self.deaths(g, 3), [])
        self.assertFalse(g.g.is_poisoned(g.g[C]))
        self.day(g, 3)
        self.answer(4, **{G: [D]})
        run(g.night(4))
        self.assertEqual(self.deaths(g, 4), [B])

    def test_pukka_example_3(self):
        """Exorcised the night after it poisoned the Pacifist, the Pukka sleeps, yet the Pacifist still dies.
        (wiki: Pukka, example 3)"""
        g = self.game(['Exorcist', 'Pacifist', 'Gossip', 'Fool', 'Tea Lady', 'Godfather', 'Pukka'])
        self.answer(1, **{G: [B]})
        run(g.night(1))
        self.answer(2, **{A: [G], G: [C]})
        run(g.night(2))
        self.assertEqual(self.asked(G, 2), [])
        self.assertEqual(self.deaths(g, 2), [B])

    def test_pukka_example_4(self):
        """The Moonchild is executed and curses the Courtier; that night the Pukka poisons the dead Moonchild, so the
        Courtier lives. (wiki: Pukka, example 4)"""
        g = self.game(['Moonchild', 'Courtier', 'Gossip', 'Fool', 'Tea Lady', 'Mastermind', 'Pukka'])
        self.choose(1, B)
        self.answer(1, **{G: [C]})
        run(g.night(1))
        self.curse(A, B)
        run(g.execution(A))
        run(g.run_pending())
        self.choose(2, B)
        self.answer(2, **{G: [A]})
        run(g.night(2))
        self.assertTrue(g.g[B].alive)
        self.assertEqual(self.deaths(g, 2), [C])


class ShabalothExamples(Example):
    def test_shabaloth_example_1(self):
        """Of the Shabaloth's two victims, the Gossip dies and the Gambler, under the Innkeeper's protection,
        does not. (wiki: Shabaloth, example 1)"""
        g = self.game(['Gossip', 'Gambler', 'Innkeeper', 'Fool', 'Tea Lady', 'Godfather', 'Shabaloth'],
                      forced={'Innkeeper': {'players': [D]}, 'Shabaloth': {'players': []}})
        self.answer(2, **{C: [B, D], G: [A, B]})
        self.choose(2, B, [B], 'Gambler')
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A])

    def test_shabaloth_example_2(self):
        """Of a living Courtier and a dead Exorcist chosen by the Shabaloth, the Courtier dies. The following
        night the Storyteller has the Exorcist regurgitated; their step was earlier in the night, so they do not act.
        (wiki: Shabaloth, example 2)"""
        g = self.game(['Courtier', 'Exorcist', 'Gossip', 'Fool', 'Tea Lady', 'Godfather', 'Shabaloth'],
                      forced={'Shabaloth': {'players': []}})
        g.g[B].alive = False
        self.choose(2, A)
        self.answer(2, **{G: [A, B]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A])
        self.day(g, 2)
        g.st.forced['Shabaloth'] = {'players': [B]}
        self.answer(3, **{G: [C, E]})
        run(g.night(3))
        self.assertTrue(g.g[B].alive)
        self.assertEqual(self.asked(B, 3), [])
        dawn = [e for e in g.events if e['kind'] == 'dawn'][-1]
        self.assertEqual(dawn['data']['revived'], [B])

    def test_shabaloth_example_3(self):
        """Choosing the Tea Lady's protected neighbour first and then her, the Shabaloth kills only her.
        (wiki: Shabaloth, example 3)"""
        g = self.game(['Gossip', 'Tea Lady', 'Pacifist', 'Fool', 'Minstrel', 'Godfather', 'Shabaloth'],
                      forced={'Shabaloth': {'players': []}})
        self.answer(2, **{G: [A, B]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [B])
        self.assertTrue(g.g[A].alive)


class PoExamples(Example):
    CHARS = ['Gossip', 'Pacifist', 'Minstrel', 'Fool', 'Tinker', 'Mastermind', 'Po']

    def test_po_example_1(self):
        """The Po kills one on night 2, chooses nobody on night 3, and so kills three on night 4. (wiki: Po,
        example 1)"""
        g = self.game(self.CHARS, forced={'Tinker': {'yes': False}})
        for n, picks in ((2, [A]), (3, []), (4, [B, C, E])):
            self.answer(n, **{G: picks})
            run(g.night(n))
            self.assertEqual(self.asked(G, n)[0].n_targets, 3 if n == 4 else 1)
            self.day(g, n)
        self.assertEqual([self.deaths(g, n) for n in (2, 3, 4)], [[A], [], [B, C, E]])

    def test_po_example_2(self):
        """The Po chooses nobody, while drunk; the next night, poisoned, it chooses three, and none die; the night
        after, sober and healthy, it attacks one player, who dies. (wiki: Po, example 2)"""
        g = self.game(self.CHARS, forced={'Tinker': {'yes': False}})
        g.g.add(State('drunk', G, until=3))
        self.answer(2, **{G: []})
        run(g.night(2))
        g.g.add(State('poisoned', G, until=4))
        self.answer(3, **{G: [A, B, C]})
        run(g.night(3))
        self.assertEqual(self.asked(G, 3)[0].n_targets, 3)
        self.assertEqual(self.deaths(g, 3), [])
        self.answer(4, **{G: [C]})
        run(g.night(4))
        self.assertEqual(self.asked(G, 4)[0].n_targets, 1)
        self.assertEqual(self.deaths(g, 4), [C])

    def test_po_example_3(self):
        """A charged Po picks the Moonchild, the Goon and the Grandmother in that order; choosing the Goon makes
        it drunk, so the Moonchild is its only kill. (wiki: Po, example 3)"""
        g = self.game(['Moonchild', 'Goon', 'Grandmother', 'Gossip', 'Fool', 'Minstrel', 'Godfather', 'Po'])
        g.g.notes['Grandchild'] = D
        self.answer(2, **{H: []})
        run(g.night(2))
        self.day(g, 2)
        self.curse(A, D)
        self.answer(3, **{H: [A, B, C]})
        run(g.night(3))
        self.assertEqual(self.deaths(g, 3), [A])
        self.assertTrue(self.drunk(g, H) and g.g[B].evil)


# ---- Townsfolk --------------------------------------------------------------------------------------------------

class SailorExamples(Example):
    def test_sailor_example_1(self):
        """The Sailor chooses the Exorcist, whom the Storyteller makes drunk; the Shabaloth attacks the Sailor, who
        lives; the next day the Sailor is executed and lives. (wiki: Sailor, example 1)"""
        g = self.game(['Sailor', 'Exorcist', 'Gossip', 'Fool', 'Tea Lady', 'Godfather', 'Shabaloth'],
                      forced={'Sailor': {'players': [B]}, 'Shabaloth': {'players': []}})
        self.answer(2, **{A: [B], B: [G], G: [A, C]})
        run(g.night(2))
        self.assertTrue(self.drunk(g, B))
        self.assertTrue(g.g[A].alive)
        self.assertEqual(self.deaths(g, 2), [C])
        self.day(g, 2)
        g.execute(A)
        self.assertTrue(g.g[A].alive)

    def test_sailor_example_2(self):
        """The Gossip's statement, which they thought false, was true; that night the Gossip's ability kills, and the
        Storyteller picks the Sailor, drunk by their own choice, who dies. (wiki: Sailor, example 2)"""
        g = self.game(['Gossip', 'Sailor', 'Pacifist', 'Fool', 'Tea Lady', 'Godfather', 'Po'],
                      forced={'Gossip kill': {'players': [B]}})
        self.say(g, A, 'Gray is the Po.')
        self.answer(2, **{B: [B], G: []})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [B])
        self.assertEqual(g.g.death_log[0]['cause'], 'gossip')

    def test_sailor_example_3(self):
        """The Sailor chooses the Mastermind and the Storyteller makes the Sailor drunk; executed the next day to
        prove a claim, the Sailor dies. (wiki: Sailor, example 3)"""
        g = self.game(['Sailor', 'Gossip', 'Pacifist', 'Fool', 'Tea Lady', 'Mastermind', 'Po'],
                      forced={'Sailor': {'players': [A]}})
        self.answer(1, **{A: [F]})
        run(g.night(1))
        self.day(g, 1)
        g.execute(A)
        self.assertFalse(g.g[A].alive)


class InnkeeperExamples(Example):
    def test_innkeeper_example_1(self):
        """The Innkeeper protects the Fool and the Chambermaid, and the Fool is made drunk; executed tomorrow, the Fool
        dies, their ability unused. (wiki: Innkeeper, example 1)"""
        g = self.game(['Innkeeper', 'Fool', 'Chambermaid', 'Gossip', 'Tea Lady', 'Godfather', 'Po'],
                      forced={'Innkeeper': {'players': [B]}})
        self.answer(2, **{A: [B, C], C: [D, E], G: []})
        run(g.night(2))
        self.assertTrue(self.drunk(g, B))
        self.day(g, 2)
        g.execute(B)
        self.assertFalse(g.g[B].alive)
        self.assertFalse(g.g.spent_ability('Fool'))

    def test_innkeeper_example_2(self):
        """The Innkeeper protects the Assassin and the Po, and the Assassin is made drunk: its kill later that night
        does nothing. (wiki: Innkeeper, example 2)"""
        g = self.game(['Innkeeper', 'Fool', 'Pacifist', 'Gossip', 'Tea Lady', 'Assassin', 'Po'],
                      forced={'Innkeeper': {'players': [F]}})
        self.answer(2, **{A: [F, G], F: [D], G: []})
        run(g.night(2))
        self.assertTrue(g.g[D].alive)
        self.assertTrue(g.g.spent_ability('Assassin'))

    def test_innkeeper_example_3(self):
        """The Innkeeper protects themself and the Pacifist and is the one made drunk: the Demon attacks the Pacifist,
        who dies. (wiki: Innkeeper, example 3)"""
        g = self.game(['Innkeeper', 'Pacifist', 'Fool', 'Gossip', 'Tea Lady', 'Godfather', 'Po'],
                      forced={'Innkeeper': {'players': [A]}})
        self.answer(2, **{A: [A, B], G: [B]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [B])


class CourtierExamples(Example):
    CHARS = ['Courtier', 'Pacifist', 'Fool', 'Gossip', 'Minstrel', 'Mastermind', 'Shabaloth']

    def test_courtier_example_1(self):
        """For four nights the Courtier wakes and declines; on the fifth it makes the Shabaloth drunk, which for three
        nights acts but kills nobody. (wiki: Courtier, example 1)"""
        g = self.game(self.CHARS, forced={'Shabaloth': {'players': []}})
        g.g[B].alive = g.g[C].alive = False
        for n in range(1, 9):
            if n < 6:
                self.choose(n, A, character='Shabaloth' if n == 5 else None)
            self.answer(n, **{G: [B, C] if n < 5 else [D, E]})
            run(g.night(n))
            self.day(g, n)
        self.assertEqual([len(self.asked(A, n)) for n in range(1, 9)], [1, 1, 1, 1, 1, 0, 0, 0])
        self.assertEqual([self.deaths(g, n) for n in range(5, 9)], [[], [], [], [D, E]])

    def test_courtier_example_2(self):
        """The drunk Courtier uses their ability: nothing happens, and they are not woken again. (wiki: Courtier,
        example 2)"""
        g = self.game(self.CHARS, forced={'Shabaloth': {'players': []}})
        g.g.add(State('drunk', A, until=2))
        self.choose(1, A, character='Shabaloth')
        run(g.night(1))
        self.assertFalse(self.drunk(g, G))
        self.answer(2, **{G: [D, E]})
        run(g.night(2))
        self.assertEqual(self.asked(A, 2), [])
        self.assertEqual(self.deaths(g, 2), [D, E])

    def test_courtier_example_3(self):
        """A drunk Mastermind (the Courtier's doing) cannot keep the game going: executing the Po ends it, and
        good wins. (wiki: Courtier, example 3)"""
        g = self.game(['Courtier', 'Pacifist', 'Fool', 'Gossip', 'Minstrel', 'Mastermind', 'Po'])
        self.choose(1, A, character='Mastermind')
        run(g.night(1))
        self.day(g, 1)
        g.execute(G)
        self.assertTrue(g.g[F].alive)
        self.assertEqual(g.g.winner, 'good')


class MinstrelExamples(Example):
    # Alex Minstrel, Blair Pacifist, Casey Gossip, Drew Fool, Ellis Tea Lady, Frankie Godfather, Gray Devil's
    # Advocate, Harper Assassin, Indigo Po
    CHARS = ['Minstrel', 'Pacifist', 'Gossip', 'Fool', 'Moonchild', 'Godfather', "Devil's Advocate", 'Assassin', 'Po']

    def test_minstrel_example_1(self):
        """Day 1 the Pacifist dies: that night all act as normal. Day 2 the Godfather is executed: that night everyone,
        the Demon too, is drunk, and nobody dies. Day 3 a Minion the drunk Devil's Advocate protected is executed and
        dies, and everyone is drunk again. (wiki: Minstrel, example 1; the Judge's execution on day 2 is an ordinary
        one here, the Judge being a Traveller)"""
        g = self.game(self.CHARS)
        self.answer(1, **{G: [A]})
        run(g.night(1))
        self.day(g, 1)
        g.execute(B)
        self.answer(2, **{G: [D], H: [], I: [C]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [C])
        self.day(g, 2)
        g.execute(F)
        self.assertTrue(all(self.drunk(g, x) for x in (B, C, D, E, F, G, H, I)))
        self.assertFalse(self.drunk(g, A))
        self.answer(3, **{G: [H], H: [D], I: [E]})
        run(g.night(3))
        self.assertEqual(self.deaths(g, 3), [])
        self.day(g, 3)
        g.execute(H)  # the Assassin, whom the drunk Devil's Advocate chose
        self.assertFalse(g.g[H].alive)
        self.answer(4, **{G: [A], I: [D]})
        run(g.night(4))
        self.assertEqual(self.deaths(g, 4), [])
        self.assertTrue(self.drunk(g, I))

    def test_minstrel_example_2(self):
        """The Assassin is executed: everyone is drunk. The next day the Godfather is executed: everyone is drunk
        again. The Demon kills nobody on either night. (wiki: Minstrel, example 2; its last part, a Traveller exiled,
        is left out)"""
        g = self.game(self.CHARS)
        g.execute(H)
        self.answer(2, **{G: [A], I: [C]})
        run(g.night(2))
        self.day(g, 2)
        g.execute(F)
        self.answer(3, **{G: [B], I: [D]})
        run(g.night(3))
        self.assertEqual((self.deaths(g, 2), self.deaths(g, 3)), ([], []))

    def test_minstrel_example_3(self):
        """The Assassin's execution makes everyone drunk; next day the drunk Zombuul, executed, dies outright
        at its first death, and good wins. (wiki: Minstrel, example 3)"""
        g = self.game(['Minstrel', 'Pacifist', 'Gossip', 'Fool', 'Tea Lady', 'Assassin', 'Zombuul'])
        g.execute(F)
        self.answer(2, **{G: [B]})
        run(g.night(2))
        self.day(g, 2)
        g.execute(G)
        self.assertFalse(g.g[G].alive)
        self.assertEqual(g.g.winner, 'good')


class ExorcistExamples(Example):
    def chars(self, demon):
        return ['Exorcist', 'Pacifist', 'Gossip', 'Fool', 'Tea Lady', 'Assassin', demon]

    def test_exorcist_example_1(self):
        """The Exorcist chooses the Shabaloth, which kills nobody tonight: at dawn, nobody died. (wiki: Exorcist,
        example 1)"""
        g = self.game(self.chars('Shabaloth'), forced={'Shabaloth': {'players': []}})
        self.answer(2, **{A: [G], F: [], G: [B, C]})
        run(g.night(2))
        self.assertEqual(self.asked(G, 2), [])
        self.assertEqual(self.deaths(g, 2), [])

    def test_exorcist_example_2(self):
        """The Exorcist chooses the Pukka, which does not wake, but its victim from last night still dies. (wiki:
        Exorcist, example 2)"""
        g = self.game(self.chars('Pukka'))
        self.answer(1, **{G: [B]})
        run(g.night(1))
        self.answer(2, **{A: [G], F: [], G: [C]})
        run(g.night(2))
        self.assertEqual(self.asked(G, 2), [])
        self.assertEqual(self.deaths(g, 2), [B])

    def test_exorcist_example_3(self):
        """A Po that chose nobody, then was exorcised (and slept), then wakes when the Exorcist picks the
        Assassin instead: the Assassin's kill still happens, and the Po, whose last choice was nobody, takes three.
        (wiki: Exorcist, example 3)"""
        g = self.game(['Exorcist', 'Pacifist', 'Gossip', 'Tinker', 'Minstrel', 'Moonchild', 'Assassin', 'Po'],
                      forced={'Tinker': {'yes': False}})
        self.answer(2, **{A: [B], G: [], H: []})
        run(g.night(2))
        self.answer(3, **{A: [H], G: []})
        run(g.night(3))
        self.assertEqual(self.asked(H, 3), [])
        self.answer(4, **{A: [G], G: [B], H: [C, D, E]})
        run(g.night(4))
        self.assertEqual(self.asked(H, 4)[0].n_targets, 3)
        self.assertEqual(self.deaths(g, 4), [B, C, D, E])


class TeaLadyExamples(Example):
    def test_tea_lady_example_1(self):
        """Seated between the Mastermind and a good Goon, the Tea Lady, once the Mastermind is executed, has the
        Goon and the Courtier as living neighbours, so a Demon's attack on the Courtier fails. When the Goon later
        turns evil her protection lapses, and the Courtier dies to the next attack. (wiki: Tea Lady, example 1)"""
        g = self.game(['Goon', 'Tea Lady', 'Mastermind', 'Courtier', 'Pacifist', 'Fool', "Devil's Advocate", 'Po'])
        self.choose(1, D)
        self.answer(1, **{G: [E]})
        run(g.night(1))
        self.day(g, 1)
        g.execute(C)
        self.assertEqual([q.name for q in g.g.neighbours(g.g[B])], [A, D])
        self.choose(2, D)
        self.answer(2, **{G: [F], H: [D]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])
        self.day(g, 2)
        self.choose(3, D)
        self.answer(3, **{G: [A], H: [D]})  # the Devil's Advocate chooses the Goon, who turns evil
        run(g.night(3))
        self.assertTrue(g.g[A].evil)
        self.assertEqual(self.deaths(g, 3), [D])


class PacifistExamples(Example):
    CHARS = ['Pacifist', 'Innkeeper', 'Professor', 'Lunatic', 'Gossip', 'Fool', 'Godfather', 'Po']

    def test_pacifist_example_1(self):
        """The Innkeeper is executed and lives, because of the Pacifist. (wiki: Pacifist, example 1)"""
        g = self.game(self.CHARS, forced={'Pacifist': {'yes': True}})
        run(g.execution(B))
        self.assertTrue(g.g[B].alive)
        self.assertEqual(g.g.executions[-1]['died'], False)

    def test_pacifist_example_2(self):
        """With the Pacifist in play and good winning, five good players are executed over seven days and the
        Pacifist saves none of them: saving is the Storyteller's choice. (wiki: Pacifist, example 2)"""
        g = self.game(['Pacifist', 'Innkeeper', 'Professor', 'Gossip', 'Fool', 'Minstrel', 'Goon', 'Moonchild',
                       'Godfather', 'Po'], forced={'Pacifist': {'yes': False}})
        for n, name in enumerate((B, C, D, F, H), start=1):
            self.day(g, n)
            if name == H:
                self.curse(H, I)
            run(g.execution(name))
            run(g.run_pending())
            self.assertFalse(g.g[name].alive, name)
        self.assertTrue(g.g[A].alive)

    def test_pacifist_example_3(self):
        """Evil winning: the Lunatic is executed and lives. The next day the Professor is executed and dies, the
        Pacifist being drunk. Later the Pacifist is executed and lives, because of the Pacifist. (wiki: Pacifist,
        example 3; the good Bishop's exile, a Traveller's, is left out)"""
        g = self.game(self.CHARS, forced={'Pacifist': {'yes': True}})
        run(g.execution(D))
        self.assertTrue(g.g[D].alive)
        self.day(g, 2)
        drunk = State('drunk', A)
        g.g.add(drunk)
        run(g.execution(C))
        self.assertFalse(g.g[C].alive)
        g.g.states.remove(drunk)
        self.day(g, 4)
        run(g.execution(A))
        self.assertTrue(g.g[A].alive)


class FoolExamples(Example):
    CHARS = ['Fool', 'Pacifist', 'Gossip', 'Minstrel', 'Moonchild', 'Assassin', 'Po']

    def test_fool_example_1(self):
        """On day 1 the Fool is executed and lives; on day 4, executed again, they die. (wiki: Fool, example 1)"""
        g = self.game(self.CHARS)
        g.execute(A)
        self.assertTrue(g.g[A].alive)
        self.day(g, 4)
        g.execute(A)
        self.assertFalse(g.g[A].alive)

    def test_fool_example_2(self):
        """The Demon attacks the Fool, who lives: nobody dies. The next day the Fool is executed and dies. (wiki:
        Fool, example 2; the Judge's execution is an ordinary one here, the Judge being a Traveller)"""
        g = self.game(self.CHARS)
        self.answer(2, **{F: [], G: [A]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])
        self.day(g, 2)
        g.execute(A)
        self.assertFalse(g.g[A].alive)

    def test_fool_example_3(self):
        """The Tea Lady protects the Fool from the Demon: they live and keep their ability. After she dies, the
        Innkeeper protects them: the same. After the Innkeeper dies, the Fool lives by their own ability, so next
        time they die. (wiki: Fool, example 3)"""
        g = self.game(['Fool', 'Tea Lady', 'Gossip', 'Innkeeper', 'Minstrel', 'Pacifist', 'Assassin', 'Po'],
                      forced={'Innkeeper': {'players': [E]}})
        self.answer(2, **{D: [C, E], G: [], H: [A]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])
        self.assertFalse(g.g.spent_ability('Fool'))
        g.kill(g.g[B], 'demon')
        self.answer(3, **{D: [A, E], G: [], H: [A]})
        run(g.night(3))
        self.assertEqual(self.deaths(g, 3), [])
        self.assertFalse(g.g.spent_ability('Fool'))
        g.kill(g.g[D], 'demon')
        self.answer(4, **{G: [], H: [A]})
        run(g.night(4))
        self.assertEqual(self.deaths(g, 4), [])
        self.assertTrue(g.g.spent_ability('Fool'))
        self.answer(5, **{G: [], H: [A]})
        run(g.night(5))
        self.assertEqual(self.deaths(g, 5), [A])


class GamblerExamples(Example):
    CHARS = ['Gambler', 'Minstrel', 'Pacifist', 'Gossip', 'Fool', "Devil's Advocate", 'Po']

    def test_gambler_example_1(self):
        """The Gambler guesses the Minstrel's player as the Minstrel: right, so the Gambler lives, but the Demon kills
        them that night anyway. (wiki: Gambler, example 1)"""
        g = self.game(self.CHARS)
        self.choose(2, A, [B], 'Minstrel')
        self.answer(2, **{F: [D], G: [A]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A])
        self.assertEqual([d['cause'] for d in g.g.death_log], ['demon'])

    def test_gambler_example_2(self):
        """The Devil's Advocate bluffs as the Pacifist; the Gambler guesses them as the Pacifist: wrong, and the
        Gambler dies. (wiki: Gambler, example 2)"""
        g = self.game(self.CHARS)
        self.choose(2, A, [F], 'Pacifist')
        self.answer(2, **{F: [D], G: []})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A])
        self.assertEqual(g.g.death_log[0]['cause'], 'gambler')


class ProfessorExamples(Example):
    def test_professor_example_1(self):
        """The Professor chooses a dead player who claims the Tea Lady but is the Lunatic: nobody comes back. (wiki:
        Professor, example 1)"""
        g = self.game(['Professor', 'Lunatic', 'Gossip', 'Fool', 'Minstrel', 'Godfather', 'Po'])
        g.g[B].alive = False
        self.answer(2, **{A: [B], G: []})
        run(g.night(2))
        self.assertFalse(g.g[B].alive)
        self.assertTrue(g.g.spent_ability('Professor'))

    def test_professor_example_2(self):
        """Brought back by the Professor, the Grandmother is shown a good player's character again; dawn
        announces her player alive, without her character. (wiki: Professor, example 2)"""
        g = self.game(['Professor', 'Grandmother', 'Gossip', 'Fool', 'Minstrel', 'Godfather', 'Po'],
                      forced={'Grandchild': {'players': [C]}})
        run(ch.rules('Grandmother').setup(g))  # the Grandchild is marked as the game is set up
        run(g.night(1))
        self.assertIn(f'your Grandchild is {C}, the Gossip', self.told(g, B)[-1])
        g.g[B].alive = False
        self.answer(2, **{A: [B], G: []})
        run(g.night(2))
        self.assertTrue(g.g[B].alive)
        self.assertEqual(len(self.told(g, B)), 2)
        self.assertIn(f'{C}, the Gossip', self.told(g, B)[-1])
        dawn = [e for e in g.events if e['kind'] == 'dawn'][-1]
        self.assertEqual(dawn['data']['revived'], [B])
        self.assertNotIn('Grandmother', render(dawn, D))

    @unittest.skip('disagrees with the example: finding EBMR-1')
    def test_professor_example_3(self):
        """The drunk Professor chooses the Minstrel, whom the Shabaloth brought back and who is alive: the
        Storyteller shakes their head, a dead player being needed. The Professor chooses the dead Fool instead:
        nothing happens (drunk), and the ability is gone. (wiki: Professor, example 3)"""
        g = self.game(['Professor', 'Minstrel', 'Fool', 'Gossip', 'Pacifist', 'Tinker', 'Moonchild', 'Tea Lady',
                       'Mastermind', 'Shabaloth'], forced={'Shabaloth': {'players': []}, 'Tinker': {'yes': False}})
        g.g[C].alive = False  # the Fool, dead (their ability used before)
        self.answer(2, **{A: [], J: [B, D]})
        run(g.night(2))
        self.day(g, 2)
        g.st.forced['Shabaloth'] = {'players': [B]}
        self.answer(3, **{A: [], J: [E, F]})
        run(g.night(3))
        self.assertTrue(g.g[B].alive)
        self.day(g, 3)
        g.st.forced['Shabaloth'] = {'players': []}
        g.g.add(State('drunk', A, until=None))
        self.answer(4, **{A: [B], J: [H, I]})
        self.seats[A].queue['retry'] = [{'targets': [C]}]
        run(g.night(4))
        self.assertNotIn(B, self.asked(A, 4)[0].options)
        self.assertFalse(g.g[C].alive)
        self.assertTrue(g.g.spent_ability('Professor'))


class GrandmotherExamples(Example):
    def test_grandmother_example_1(self):
        """On the first night the Grandmother learns that her Grandchild is the Professor. Three nights later the
        Demon kills the Grandchild, and the Grandmother dies too. (wiki: Grandmother, example 1)"""
        g = self.game(['Grandmother', 'Professor', 'Gossip', 'Fool', 'Minstrel', 'Godfather', 'Po'],
                      forced={'Grandchild': {'players': [B]}})
        run(ch.rules('Grandmother').setup(g))  # the Grandchild is marked as the game is set up
        run(g.night(1))
        self.assertIn(f'your Grandchild is {B}, the Professor', self.told(g, A)[-1])
        for n in (2, 3):
            self.answer(n, **{B: [], G: [E if n == 2 else D]})
            run(g.night(n))
            self.day(g, n)
        self.answer(4, **{B: [], G: [B]})
        run(g.night(4))
        self.assertEqual(self.deaths(g, 4), [A, B])

    def test_grandmother_example_2(self):
        """The Grandchild is the Gambler, who gambles and dies of it: the Grandmother lives. (wiki: Grandmother,
        example 2)"""
        g = self.game(['Grandmother', 'Gambler', 'Gossip', 'Fool', 'Minstrel', 'Godfather', 'Po'],
                      forced={'Grandchild': {'players': [B]}})
        run(ch.rules('Grandmother').setup(g))
        run(g.night(1))
        self.choose(2, B, [C], 'Po')
        self.answer(2, **{G: []})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [B])
        self.assertTrue(g.g[A].alive)

    def test_grandmother_example_3(self):
        """The Grandchild is the Tinker; the Demon kills the Tinker, but the Sailor made the Grandmother drunk, so she
        lives. (wiki: Grandmother, example 3)"""
        g = self.game(['Grandmother', 'Tinker', 'Sailor', 'Fool', 'Minstrel', 'Godfather', 'Po'],
                      forced={'Grandchild': {'players': [B]}, 'Sailor': {'players': [A]}, 'Tinker': {'yes': False}})
        run(ch.rules('Grandmother').setup(g))
        self.answer(1, **{C: [A]})
        run(g.night(1))
        self.answer(2, **{C: [A], G: [B]})
        run(g.night(2))
        self.assertTrue(self.drunk(g, A))
        self.assertEqual(self.deaths(g, 2), [B])
        self.assertTrue(g.g[A].alive)


class ChambermaidExamples(Example):
    def test_chambermaid_example_1(self):
        """Night 2: the Exorcist and the Innkeeper both woke for their abilities, so the Chambermaid learns 2.
        Night 3: the Shabaloth was woken only to be told the Exorcist chose it, and the Fool never wakes, so a 0. (wiki:
        Chambermaid, example 1)"""
        g = self.game(['Chambermaid', 'Exorcist', 'Innkeeper', 'Fool', 'Gossip', 'Godfather', 'Shabaloth'],
                      forced={'Shabaloth': {'players': []}, 'Innkeeper': {'players': [D]}})
        self.answer(2, **{A: [B, C], B: [D], C: [D, E], G: [D, E]})
        run(g.night(2))
        self.assertIn(f'you chose {B} and {C}: 2 of them woke', self.told(g, A)[-1])
        self.day(g, 2)
        self.answer(3, **{A: [G, D], B: [G], C: [D, E]})
        run(g.night(3))
        self.assertIn(f'you chose {G} and {D}: 0 of them woke', self.told(g, A)[-1])

    @unittest.skip('disagrees with the example: finding EBMR-2')
    def test_chambermaid_example_2(self):
        """Night 2: choosing the Grandmother and an evil Goon makes the Chambermaid (first to pick the Goon)
        drunk, and she is shown 2. The true count is 1, because the Goon wakes to learn it is good again. (wiki:
        Chambermaid, example 2)"""
        g = self.game(['Chambermaid', 'Grandmother', 'Goon', 'Gossip', 'Fool', 'Godfather', 'Po'],
                      forced={'Grandchild': {'players': [D]}, 'Chambermaid': {'number': 2}})
        g.g[C].alignment = 'evil'
        self.answer(1, **{A: [D, E]})
        run(g.night(1))
        self.answer(2, **{A: [B, C], G: []})
        run(g.night(2))
        self.assertTrue(self.drunk(g, A))
        self.assertIn('2 of them woke', self.told(g, A)[-1])
        self.assertFalse(g.g[C].evil)
        from clocktower.bmr import chambermaid_choice
        self.assertTrue(chambermaid_choice(g.g, g.g[A], [B, C], 2).truth({'number': 1}))

    def test_chambermaid_example_3(self):
        """Night 1: the Assassin has no first-night step and the Moonchild never wakes: 0. Night 2: the
        Assassin woke and declined, which counts; the Gossip's kill happened but the Gossip did not wake: 1. (wiki:
        Chambermaid, example 3)"""
        g = self.game(['Chambermaid', 'Gossip', 'Moonchild', 'Fool', 'Minstrel', 'Assassin', 'Zombuul'],
                      forced={'Gossip kill': {'players': [E]}})
        self.answer(1, **{A: [F, C]})
        run(g.night(1))
        self.assertIn('0 of them woke', self.told(g, A)[-1])
        self.say(g, B, 'Frankie is evil.')
        self.answer(2, **{A: [F, B], F: [], G: [D]})
        run(g.night(2))
        self.assertIn('1 of them woke', self.told(g, A)[-1])
        self.assertIn(E, self.deaths(g, 2))


class GossipExamples(Example):
    CHARS = ['Gossip', 'Chambermaid', 'Pacifist', 'Fool', 'Minstrel', 'Godfather', 'Po']

    def test_gossip_example_1(self):
        """The Gossip says the Demon is wearing a hat; it is not, and nobody dies of the Gossip's ability that night.
        (wiki: Gossip, example 1)"""
        g = self.game(self.CHARS, forced={'Gossip kill': {'players': [B]}})
        self.say(g, A, 'I am the Gossip, and here is my statement: the Demon has a hat on.')
        self.answer(2, **{B: [C, D], G: []})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])

    def test_gossip_example_2(self):
        """The drunk Gossip, between two good players, says both neighbours are good; at dusk the Gossip sobers, and
        that night the Chambermaid dies. (wiki: Gossip, example 2; a good Townsfolk sits in the good Traveller's seat,
        and the statement, beyond the engine's simple forms, is ruled true by a forced Storyteller decision)"""
        g = self.game(['Gossip', 'Pacifist', 'Chambermaid', 'Fool', 'Minstrel', 'Godfather', 'Po'],
                      forced={'Gossip:': {'yes': True}, 'Gossip kill': {'players': [C]}})
        g.g.add(State('drunk', A, until='night'))
        self.say(g, A, 'Both my neighbours are good.')
        self.answer(2, **{C: [D, E], G: []})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [C])

    def test_gossip_example_3(self):
        """The Gossip's statement is true, but that night the Demon kills the Gossip, whose ability is lost: nobody
        dies of the statement. (wiki: Gossip, example 3)"""
        g = self.game(self.CHARS, forced={'Gossip kill': {'players': [B]}})
        self.say(g, A, 'Gray is the Demon.')
        self.answer(2, **{B: [C, D], G: [A]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A])


# ---- Outsiders --------------------------------------------------------------------------------------------------

class GoonExamples(Example):
    def test_goon_example_1(self):
        """A Courtier naming the Goon is the drunk one, and the (evil) Goon becomes good. (wiki: Goon, example 1)"""
        g = self.game(['Courtier', 'Goon', 'Gossip', 'Fool', 'Minstrel', 'Assassin', 'Shabaloth'])
        g.g[B].alignment = 'evil'
        self.choose(1, A, character='Goon')
        run(g.night(1))
        self.assertTrue(self.drunk(g, A))
        self.assertFalse(g.g[B].evil)

    def test_goon_example_2(self):
        """Night 2: the Shabaloth picks the Goon first, is drunk at once, kills neither, and the Goon goes evil.
        Night 3: it picks the Gambler first (who dies) and the Goon second, drunk again; the Goon lives, evil still.
        (wiki: Goon, example 2)"""
        g = self.game(['Goon', 'Gossip', 'Gambler', 'Fool', 'Minstrel', 'Assassin', 'Shabaloth'],
                      forced={'Shabaloth': {'players': []}})
        self.choose(2, C, [C], 'Gambler')
        self.answer(2, **{F: [], G: [A, B]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])
        self.assertTrue(g.g[A].evil and self.drunk(g, G))
        self.day(g, 2)
        self.choose(3, C, [C], 'Gambler')
        self.answer(3, **{F: [], G: [C, A]})
        run(g.night(3))
        self.assertEqual(self.deaths(g, 3), [C])
        self.assertTrue(g.g[A].alive and g.g[A].evil and self.drunk(g, G))

    def test_goon_example_3(self):
        """A Chambermaid who picks the Goon and the Minstrel is drunk, and may be shown a 1. (wiki: Goon, example
        3)"""
        g = self.game(['Chambermaid', 'Goon', 'Minstrel', 'Gossip', 'Fool', 'Godfather', 'Po'],
                      forced={'Chambermaid': {'number': 1}})
        self.answer(1, **{A: [B, C]})
        run(g.night(1))
        self.assertTrue(self.drunk(g, A))
        self.assertIn('1 of them woke', self.told(g, A)[-1])

    def test_goon_example_4(self):
        """The Tea Lady's neighbours are a good Goon and the Tinker, so the Tinker survives an execution; once
        the Goon has turned evil, a second execution kills the Tinker. (wiki: Goon, example 4)"""
        g = self.game(['Goon', 'Tea Lady', 'Tinker', 'Gossip', 'Fool', "Devil's Advocate", 'Zombuul'],
                      forced={'Tinker': {'yes': False}})
        self.answer(1, **{F: [D]})
        run(g.night(1))
        self.day(g, 1)
        g.execute(C)
        self.assertTrue(g.g[C].alive)
        self.answer(2, **{F: [A], G: [D]})
        run(g.night(2))
        self.assertTrue(g.g[A].evil)
        self.day(g, 2)
        g.execute(C)
        self.assertFalse(g.g[C].alive)


class LunaticExamples(Example):
    def lunatic(self, demon):
        chars = ['Lunatic', 'Gossip', 'Fool', 'Minstrel', 'Pacifist', 'Tea Lady', 'Assassin', demon]
        names = ALL_NAMES[:8]
        self.seats = {n: Seat() for n in names}
        forced = {'Lunatic:demon': {'character': demon}, 'Lunatic:minions': {'players': [C]},
                  'Lunatic:bluffs': {'characters': ['Exorcist', 'Sailor', 'Courtier']}, 'Shabaloth': {'players': []}}
        g = Game(self.seats, Forced(forced), names=names, seed=3, characters=chars, script=BMR, probes=False)
        run(g.setup())
        return g

    def test_lunatic_example_1(self):
        """A Lunatic who believes they are the Shabaloth picks two players every night; those picks never die.
        (wiki: Lunatic, example 1)"""
        g = self.lunatic('Shabaloth')
        run(g.night(1))
        for n, eaten in ((2, [B, E]), (3, [F, G])):
            self.answer(n, **{A: [C, D], G: [], H: eaten})
            run(g.night(n))
            self.assertEqual(self.asked(A, n)[0].n_targets, 2)
            self.assertEqual(self.deaths(g, n), eaten)
            self.day(g, n)
        self.assertTrue(g.g[C].alive and g.g[D].alive)

    def test_lunatic_example_2(self):
        """The Lunatic, believing they are the Zombuul, seldom wakes; the real Zombuul knows whom the Lunatic chose,
        so it can attack the same players (keeping up the illusion is the Demon's choice, not a rule). (wiki:
        Lunatic, example 2)"""
        g = self.lunatic('Zombuul')
        run(g.night(1))
        self.day(g, 1)
        g.execute(B)  # a death today: neither the Zombuul nor the Lunatic believing it is one wakes
        self.answer(2, **{G: []})
        run(g.night(2))
        self.assertEqual(self.asked(A, 2), [])
        self.day(g, 2)
        self.answer(3, **{A: [D], G: [], H: [D]})
        run(g.night(3))
        self.assertEqual(len(self.asked(A, 3)), 1)
        self.assertIn(f'the Lunatic ({A}) chose {D}', self.told(g, H)[-1])
        self.assertEqual(self.deaths(g, 3), [D])


class TinkerExamples(Example):
    CHARS = ['Tinker', 'Gossip', 'Fool', 'Minstrel', 'Pacifist', 'Godfather', 'Zombuul']

    def test_tinker_almanac_example(self):
        """On the third day the Tinker suddenly dies. (almanac BMR: Tinker, the example the wiki lacks)"""
        g = self.game(self.CHARS, forced={'Tinker': {'yes': True}})
        self.day(g, 3)
        g.moment('beat')
        self.assertFalse(g.g[A].alive)
        ev = [e for e in g.events if e['kind'] == 'died'][-1]
        self.assertEqual(render(ev, B), f'{A} dies.')

    def test_tinker_example_1(self):
        """In the night the Tinker dies, though the Demon attacked someone else. (wiki: Tinker, example 1)"""
        g = self.game(self.CHARS, forced={'Tinker': {'yes': True}})
        self.answer(2, **{G: [B]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A, B])

    def test_tinker_example_2(self):
        """The Tea Lady sits between the Tinker and another good player, protecting the Tinker: the Tinker cannot die
        of their own ability. (wiki: Tinker, example 2)"""
        g = self.game(['Tinker', 'Tea Lady', 'Fool', 'Minstrel', 'Pacifist', 'Godfather', 'Zombuul'],
                      forced={'Tinker': {'yes': True}})
        for when in ('dawn', 'beat', 'nominations', 'dusk'):
            g.moment(when)
        self.answer(2, **{G: [D]})
        run(g.night(2))
        self.assertTrue(g.g[A].alive)

    def test_tinker_example_3(self):
        """The Demon attacks the Tinker, protected by the Innkeeper, who lives; later that night the Innkeeper dies,
        so the Storyteller kills the Tinker too. (wiki: Tinker, example 3)"""
        g = self.game(['Tinker', 'Innkeeper', 'Fool', 'Minstrel', 'Pacifist', 'Assassin', 'Po'],
                      forced={'Tinker': {'yes': True}, 'Innkeeper': {'players': [C]}})
        self.answer(2, **{B: [A, C], F: [B], G: [A]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A, B])
        self.assertEqual([d['cause'] for d in g.g.death_log], ['assassin', 'tinker'])


class MoonchildExamples(Example):
    def test_moonchild_example_1(self):
        """Killed by the Pukka in the night, the Moonchild names the Exorcist at dawn, and the Exorcist dies
        the next night. (wiki: Moonchild, example 1)"""
        g = self.game(['Moonchild', 'Exorcist', 'Gossip', 'Fool', 'Minstrel', 'Godfather', 'Pukka'])
        self.answer(1, **{G: [A]})
        run(g.night(1))
        self.curse(A, B)
        self.answer(2, **{B: [D], G: [C]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A])
        self.day(g, 2)
        self.answer(3, **{B: [E], G: [E]})
        run(g.night(3))
        self.assertIn(B, self.deaths(g, 3))
        self.assertEqual([d['cause'] for d in g.g.death_log if d['player'] == B], ['moonchild'])

    def test_moonchild_example_2(self):
        """With the Pacifist in play the Moonchild is executed and lives: not having died, they choose nobody. (wiki:
        Moonchild, example 2)"""
        g = self.game(['Moonchild', 'Pacifist', 'Gossip', 'Fool', 'Minstrel', 'Godfather', 'Po'],
                      forced={'Pacifist': {'yes': True}})
        run(g.execution(A))
        run(g.run_pending())
        self.assertTrue(g.g[A].alive)
        self.assertFalse([r for r in self.seats[A].log if r.kind == 'death_choice'])

    def test_moonchild_example_3(self):
        """The Shabaloth eats the Moonchild, who chooses the Assassin: the Assassin lives. The Shabaloth brings the
        Moonchild back; nights later it eats them again, and now they choose the Gossip, who dies. (wiki: Moonchild,
        example 3)"""
        g = self.game(['Moonchild', 'Gossip', 'Fool', 'Minstrel', 'Pacifist', 'Tea Lady', 'Assassin', 'Shabaloth'],
                      forced={'Shabaloth': {'players': []}})
        self.curse(A, G)
        self.answer(2, **{G: [], H: [A, C]})
        run(g.night(2))
        self.assertFalse(g.g[A].alive)
        self.day(g, 2)
        g.st.forced['Shabaloth'] = {'players': [A]}
        self.answer(3, **{G: [], H: [D, E]})
        run(g.night(3))
        self.assertTrue(g.g[A].alive and g.g[G].alive)
        self.day(g, 3)
        g.st.forced['Shabaloth'] = {'players': []}
        self.curse(A, B)
        self.answer(4, **{G: [], H: [A, F]})
        run(g.night(4))
        self.assertFalse(g.g[A].alive)
        self.day(g, 4)
        self.answer(5, **{G: [], H: [C, G]})
        run(g.night(5))
        self.assertIn(B, self.deaths(g, 5))


if __name__ == '__main__':
    unittest.main()
