"""The script-independent core: deaths from any source, protection, survival, apparent death, executions that
don't kill, resurrection and states with durations. These mechanics exist for Bad Moon Rising and later scripts;
the tests use small test-only characters (registered for the test and removed after), so they don't depend on
any script's characters being built."""
import asyncio
import random
import unittest

from clocktower import characters as ch
from clocktower.agents import ScriptedStoryteller
from clocktower.game import NAMES, Game, Night
from clocktower.llm import Reply
from clocktower.render import render
from clocktower.state import State

A, B, C, D, E, F, G, H, I = NAMES
BLANK = {'say': '', 'whispers': [], 'nominate': None, 'vote': None, 'targets': [], 'slayer_shot': None}


class Guard(ch.Townsfolk):
    """Protects both neighbours from every death."""
    name = 'Test Guard'

    def protects(self, g, me, other, cause):
        return g.works(me, self.name) and other in g.neighbours(me)


class Jester(ch.Outsider):
    """The first time they would die, they don't."""
    name = 'Test Jester'

    def survives(self, game, me, cause):
        if game.g.works(me, self.name) and not game.g.spent_ability(self.name):
            game.g.spend(self.name)
            return True
        return False


class Ghoul(ch.Demon):
    """The first time they die, they live on but register as dead."""
    name = 'Test Ghoul'

    def dies(self, game, me, cause):
        if not game.g.spent_ability(self.name):
            game.g.spend(self.name)
            return 'seems'
        return None


class Plain(ch.Townsfolk):
    name = 'Test Plain'


class Henchman(ch.Minion):
    name = 'Test Henchman'


TEST = [Guard, Jester, Ghoul, Plain, Henchman]


class Silent:
    async def act(self, text, request):
        return Reply(dict(BLANK))


def run(coro):
    return asyncio.run(coro)


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for c in TEST:
            ch.CHARACTERS[c.name] = c()
        cls.script = ch.Script.of('test', [c.name for c in TEST])

    @classmethod
    def tearDownClass(cls):
        for c in TEST:
            del ch.CHARACTERS[c.name]

    def game(self, chars):
        names = NAMES[:len(chars)]
        g = Game({n: Silent() for n in names}, ScriptedStoryteller(random.Random(1)), names=names, seed=3,
                 characters=chars, script=self.script, probes=False)
        g.setup_error_ok = True
        return g

    def setup(self, chars):
        from clocktower.state import Grimoire
        g = self.game(chars)
        g.g = Grimoire(g.names, chars, script=self.script)
        g.day, g.phase = 1, 'day'
        return g

    def test_a_protector_stops_any_death_and_an_unstoppable_kill_goes_through(self):
        g = self.setup(['Test Plain', 'Test Guard', 'Test Plain', 'Test Henchman', 'Test Ghoul'])
        night = Night(2)
        self.assertIsNone(g.attempt_kill(g.g[A], 'assassin', g.g[D], night))  # Alex sits next to the Guard
        self.assertTrue(g.g[A].alive)
        self.assertIs(g.attempt_kill(g.g[A], 'assassin', g.g[D], night, unstoppable=True), g.g[A])
        self.assertFalse(g.g[A].alive)
        self.assertEqual([p.name for p in night.deaths], [A])

    def test_a_safe_state_stops_only_the_deaths_it_is_against(self):
        g = self.setup(['Test Plain', 'Test Plain', 'Test Plain', 'Test Henchman', 'Test Ghoul'])
        g.g.add(State('safe', A, against='demon'))
        g.g.add(State('safe', B, against='any'))
        self.assertIsNone(g.attempt_kill(g.g[A], 'demon', g.g[E]))
        self.assertIsNotNone(g.attempt_kill(g.g[A], 'assassin', g.g[D]))
        self.assertIsNone(g.attempt_kill(g.g[B], 'assassin', g.g[D]))

    def test_a_survivor_lives_through_one_death_then_dies(self):
        g = self.setup(['Test Jester', 'Test Plain', 'Test Plain', 'Test Henchman', 'Test Ghoul'])
        self.assertIsNone(g.attempt_kill(g.g[A], 'demon', g.g[E]))
        self.assertTrue(g.g[A].alive)
        self.assertIsNotNone(g.attempt_kill(g.g[A], 'demon', g.g[E]))

    def test_an_execution_can_fail_to_kill_and_still_counts_as_the_execution(self):
        g = self.setup(['Test Jester', 'Test Plain', 'Test Plain', 'Test Henchman', 'Test Ghoul'])
        g.execute(A)
        self.assertTrue(g.g[A].alive)
        self.assertTrue(g.executed_today)
        ev = [e for e in g.events if e['kind'] == 'execution'][-1]
        self.assertEqual(ev['data'], {'player': A, 'died': False, 'survived': True})
        self.assertEqual(render(ev, B), f'{A} is executed, but does not die.')
        self.assertIsNone(g.g.executed_death)

    def test_a_player_who_seems_dead_is_dead_to_the_town_but_still_plays(self):
        g = self.setup(['Test Plain', 'Test Plain', 'Test Plain', 'Test Henchman', 'Test Ghoul'])
        g.execute(E)
        ghoul = g.g[E]
        self.assertTrue(ghoul.alive and ghoul.seems_dead and not ghoul.appears_alive)
        self.assertIsNone(g.g.check_victory())  # the Demon lives on: the game goes on
        g.emit('text', {'text': 'x'})
        self.assertIn(E, g.events[-1]['dead'])  # every seat sees them as dead
        self.assertIsNone(g.attempt_kill(ghoul, 'demon', ghoul))  # "dead" players can't be killed at night
        g.execute(E)  # a second execution kills them for real
        self.assertFalse(ghoul.alive)
        self.assertEqual(g.g.check_victory(), 'good')
        self.assertEqual([d['player'] for d in g.g.death_log], [E, E])
        self.assertEqual(g.g.died_today(1), [E, E])

    def test_dawn_names_the_dead_in_seat_order_and_the_revived(self):
        g = self.setup(['Test Plain', 'Test Plain', 'Test Plain', 'Test Henchman', 'Test Ghoul'])
        night = Night(2)
        for name in (C, A):  # killed in this order
            g.attempt_kill(g.g[name], 'demon', g.g[E], night)
        g.g.revive(g.g[A])
        night.revived.append(g.g[A])

        async def steps():
            return None
        g.script.other_nights = []
        orig = Night.__init__

        def fixed(self_, n):
            orig(self_, n)
            self_.deaths, self_.revived = night.deaths, night.revived
        Night.__init__ = fixed
        try:
            run(g.night(2))
        finally:
            Night.__init__ = orig
        dawn = [e for e in g.events if e['kind'] == 'dawn'][-1]
        self.assertEqual(dawn['data']['deaths'], [A, C])
        self.assertEqual(dawn['data']['revived'], [A])
        self.assertIn(f'Alive again: {A}.', render(dawn, B))
        self.assertTrue(g.g[A].alive and g.g[A].ghost_vote)

    def test_a_state_can_last_several_nights_and_pause_while_its_source_is_impaired(self):
        g = self.setup(['Test Plain', 'Test Plain', 'Test Plain', 'Test Henchman', 'Test Ghoul'])
        g.g.add(State('drunk', B, source=A, until=4, while_source_works=True))  # drunk for nights 1-3
        self.assertTrue(g.g.is_drunk(g.g[B]))
        g.g.poisoned = A  # the source is impaired: the drunkenness pauses
        self.assertFalse(g.g.is_drunk(g.g[B]))
        g.g.poisoned = None
        g.g.expire('night', 3)
        self.assertTrue(g.g.is_drunk(g.g[B]))
        g.g.expire('night', 4)  # it ends at the dusk before night 4
        self.assertFalse(g.g.is_drunk(g.g[B]))


if __name__ == '__main__':
    unittest.main()
