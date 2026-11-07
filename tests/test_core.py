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


ORDER = []  # the order steps resolve in tonight


class Picker(ch.Townsfolk):
    """Chooses a character, and may choose no one (like a Courtier)."""
    name = 'Test Picker'
    night_choice = ch.Choose(players=0, prompt='Choose a character.', character=True)

    async def resolve_night(self, game, night):
        ORDER.append(self.name)


class Hunter(ch.Minion):
    """May choose one alive player who wasn't last night's choice, or no one."""
    name = 'Test Hunter'
    night_choice = ch.Choose(players=1, prompt='Choose a player, or no one.', optional=True, alive_only=True,
                             not_last=True)

    async def resolve_night(self, game, night):
        ORDER.append(self.name)


class Henchman(ch.Minion):
    name = 'Test Henchman'


class Crier(ch.Townsfolk):
    """A public day ability anyone can claim: a real one kills the named player."""
    name = 'Test Crier'
    public_action = 'ability'

    def act_publicly(self, game, actor, target, text=None):
        return game.g.works(game.g[actor], self.name)


class Avenger(ch.Outsider):
    """When they die, they choose a player (asked after the death resolves): that player dies too."""
    name = 'Test Avenger'

    def on_death(self, game, me, dead, cause, alive_before):
        if dead is me:
            async def choose(game):
                req = game.request('avenger', 'Choose a player.', game.day, n_targets=1, options=game.names)
                t = game.targets(me.name, await game.ask(me.name, req), req)[0]
                game.attempt_kill(game.g[t], 'avenger', me)
            game.later(choose)


class Fixer(ch.Minion):
    """The Storyteller deals one Outsider more or one fewer."""
    name = 'Test Fixer'
    outsider_choices = (-1, 1)


class Keeper(ch.Minion):
    """While alive, the Demon's death doesn't end the game."""
    name = 'Test Keeper'

    def overrides_end(self, g, me, winner, reason):
        return False if me.alive and winner == 'good' else None


TEST = [Guard, Jester, Ghoul, Plain, Henchman, Picker, Hunter, Crier, Avenger, Fixer, Keeper]


class Silent:
    async def act(self, text, request):
        return Reply(dict(BLANK))


class Answers:
    """Answers night requests from a dict, and records them."""

    def __init__(self, answer, log):
        self.answer, self.log = answer, log

    async def act(self, text, request):
        self.log.append(request)
        return Reply({**BLANK, **(self.answer if request.kind in ('night', 'avenger') else {})})


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


    def test_new_choice_shapes_no_one_a_character_alive_only_not_last_and_one_step_at_a_time(self):
        from clocktower.state import Grimoire
        chars = ['Test Picker', 'Test Plain', 'Test Plain', 'Test Hunter', 'Test Ghoul']
        logs = {n: [] for n in NAMES[:5]}
        answers = {A: {'character': 'Test Plain'}, D: {'targets': []}}
        seats = {n: Answers(answers.get(n, {}), logs[n]) for n in NAMES[:5]}
        script = ch.Script.of('test', chars, other_nights=['Test Hunter', 'Test Picker'])
        g = Game(seats, ScriptedStoryteller(random.Random(1)), names=NAMES[:5], seed=3, characters=chars,
                 script=script, probes=False)
        g.g = Grimoire(g.names, chars, script=script)
        g.g[C].alive = False
        g.g.night_choices[1] = {D: [B]}  # last night's choice
        ORDER.clear()
        run(g.night(2))
        self.assertEqual(ORDER, ['Test Hunter', 'Test Picker'])  # one step at a time, in night order
        hunter, picker = logs[D][0], logs[A][0]
        self.assertEqual((hunter.min_targets, hunter.n_targets), (0, 1))
        self.assertNotIn(C, hunter.options)  # dead
        self.assertNotIn(B, hunter.options)  # last night's choice
        self.assertIn('[] for no one', hunter.prompt)
        self.assertEqual(picker.characters, script.all)
        choices = {e['data']['player']: e['data'] for e in g.events if e['kind'] == 'night_choice'}
        self.assertEqual(choices[D]['targets'], [])  # choosing no one is taken as given, with no notice
        self.assertEqual(choices[A]['character'], 'Test Plain')
        self.assertFalse(any(e['kind'] == 'notice' for e in g.events))
        self.assertEqual(g.g.woke[2], [D, A])

    def test_trouble_brewing_keeps_its_v17_schema(self):
        from clocktower.schema import player_schema
        self.assertEqual(player_schema(NAMES), player_schema(NAMES, ch.TB))
        other = player_schema(NAMES, self.script)
        self.assertIn('character', other['properties'])
        self.assertNotIn('slayer_shot', other['properties'])


    def test_anyone_can_claim_a_public_ability_and_only_a_real_one_works(self):
        script = ch.Script.of('test', ['Test Crier', 'Test Plain', 'Test Plain', 'Test Henchman', 'Test Ghoul'])
        self.assertEqual(script.claimable, ['Test Crier'])
        g = self.setup(['Test Crier', 'Test Plain', 'Test Plain', 'Test Henchman', 'Test Ghoul'])
        g.g.script = g.script = script
        g.public_abilities([B], {B: {'ability': {'character': 'Test Crier', 'target': C, 'text': 'hear me'}}})
        self.assertTrue(g.g[C].alive)  # Blair isn't the Crier: the claim does nothing
        ev = [e for e in g.events if e['kind'] == 'ability'][-1]
        self.assertEqual(render(ev, D), f'{B} claims the Test Crier\'s ability on {C}: "hear me"')
        g.public_abilities([A], {A: {'ability': {'character': 'Test Crier', 'target': C}}})
        self.assertFalse(g.g[C].alive)
        self.assertEqual(g.g.death_log[-1]['cause'], 'test crier')

    def test_an_ability_that_triggers_on_death_asks_its_player_afterwards(self):
        chars = ['Test Avenger', 'Test Plain', 'Test Plain', 'Test Henchman', 'Test Ghoul']
        g = self.setup(chars)
        log = []
        g.seats[A] = Answers({'targets': [C]}, log)

        async def go():
            g.kill(g.g[A], 'demon')
            self.assertEqual(len(g.pending), 1)  # asked only once the death has resolved
            await g.run_pending()
        run(go())
        self.assertEqual(log[0].kind, 'avenger')
        self.assertFalse(g.g[C].alive)

    def test_a_setup_modifier_can_be_the_storytellers_choice(self):
        from clocktower.state import random_setup, setup_error
        script = ch.Script.of('test', ['Test Plain', 'Test Guard', 'Test Picker', 'Test Crier', 'Test Jester',
                                       'Test Avenger', 'Test Fixer', 'Test Henchman', 'Test Ghoul'])
        outsiders = set()
        for seed in range(40):
            chars = random_setup(random.Random(seed), 'Test Fixer', 7, script)  # 7 players: 5, 0, 1 normally
            self.assertIsNone(setup_error(chars, script))
            outsiders.add(sum(ch.kind(c) == 'Outsider' for c in chars))
        self.assertEqual(outsiders, {1})  # -1 is impossible with no Outsiders, so only +1 deals
        outsiders = set()
        for seed in range(40):
            chars = random_setup(random.Random(seed), 'Test Fixer', 6, script)  # 6 players: 3, 1, 1 normally
            self.assertIsNone(setup_error(chars, script))
            outsiders.add(sum(ch.kind(c) == 'Outsider' for c in chars))
        self.assertEqual(outsiders, {0, 2})  # the Storyteller's -1 or +1

    def test_a_character_can_keep_the_game_going(self):
        g = self.setup(['Test Plain', 'Test Plain', 'Test Plain', 'Test Keeper', 'Test Ghoul'])
        g.g.spend('Test Ghoul')  # no apparent death: the Ghoul dies for real
        g.kill(g.g[E], 'execution')
        self.assertIsNone(g.g.check_victory())
        g.kill(g.g[D], 'demon')
        self.assertEqual(g.g.check_victory(), 'good')

    def test_an_ability_can_be_held_by_another_character_and_jinxes_come_from_the_official_data(self):
        g = self.setup(['Test Plain', 'Test Plain', 'Test Plain', 'Test Henchman', 'Test Ghoul'])
        g.g[B].extra.append('Test Crier')
        self.assertTrue(g.g.works(g.g[B], 'Test Crier'))
        self.assertFalse(g.g.works(g.g[C], 'Test Crier'))
        self.assertEqual(ch.TB.jinxes, {})
        import json
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'j.json'
            path.write_text(json.dumps(['washerwoman', 'spy', 'poisoner', 'imp', 'scarletwoman', 'recluse']))
            self.assertEqual(ch.Script(path).jinxes, {})


if __name__ == '__main__':
    unittest.main()
