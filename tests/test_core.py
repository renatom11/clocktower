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


class Miasma(ch.Townsfolk):
    """Poisons the nearest Test Plain clockwise (alive or dead), worked out whenever asked."""
    name = 'Test Miasma'
    derives = True

    def ongoing(self, g, me):
        if not g.works(me, self.name):
            return []
        q = g.nearest(me, 1, lambda q: q.character == 'Test Plain')
        return [State('poisoned', q.name, source=me.name, until=None)] if q else []


class Liar(ch.Minion):
    """Every Townsfolk's information is false while they live."""
    name = 'Test Liar'
    falsifies_info = True

    def falsifies(self, g, me, recipient, ability):
        return ch.kind(ability) == 'Townsfolk' and g.works(me, self.name)


class Hexer(ch.Minion):
    """Whoever nominates the Hexer dies; executing the Test Guard wins for evil."""
    name = 'Test Hexer'

    def nomination(self, game, me, nominator, nominee):
        if nominee == me.name and game.g.works(me, self.name):
            game.ability_kill(game.g[nominator], 'hexer', me)

    def execution(self, game, me, executed):
        return ('evil', 'the Guard was executed') if executed.character == 'Test Guard' else None


BECAME = []


class Changeling(ch.Outsider):
    """Records when a player becomes it, and every change it sees."""
    name = 'Test Changeling'

    def becomes(self, game, me):
        BECAME.append(('becomes', me.name))

    async def changed(self, game, me, other):
        BECAME.append(('changed', me.name, other.name))


TEST = [Guard, Jester, Ghoul, Plain, Henchman, Picker, Hunter, Crier, Avenger, Fixer, Keeper, Miasma, Liar, Hexer,
        Changeling]


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



class SectsAndVioletsCoreTests(unittest.TestCase):
    """The core Sects & Violets needs: character changes in bulk, dead players keeping their ability, states worked
    out on demand, falsified information, abilities triggered by any nomination or execution, and madness."""
    game, setup = CoreTests.game, CoreTests.setup

    @classmethod
    def setUpClass(cls):
        CoreTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        CoreTests.tearDownClass.__func__(cls)

    def told(self, g, name):
        return [e['data']['text'] for e in g.events if e['to'] == [name] and e['kind'] == 'info']

    def test_a_change_is_told_at_once_gives_a_fresh_ability_and_runs_the_hooks(self):
        g = self.setup(['Test Plain', 'Test Plain', 'Test Changeling', 'Test Henchman', 'Test Ghoul'])
        BECAME.clear()
        g.g.spend('Test Crier')  # an earlier holder used it
        g.g.add(State('poisoned', A, source=B, ends_with_source=True))
        run(g.change(g.g[B], character='Test Crier'))
        self.assertEqual(g.g[B].shown, 'Test Crier')
        self.assertFalse(g.g.spent_ability('Test Crier'))
        self.assertFalse(g.g.is_poisoned(g.g[A]))  # B's old ability's effects end
        self.assertEqual(self.told(g, B), ['Day 1: you are now the Test Crier () and you are still good.'])
        self.assertEqual(BECAME, [('changed', C, B)])
        run(g.change(g.g[A], character='Test Changeling', alignment='evil'))
        self.assertEqual(self.told(g, A), ['Day 1: you are now the Test Changeling () and you are now evil.'])
        self.assertEqual(BECAME[1:], [('becomes', A), ('changed', A, A), ('changed', C, A)])
        self.assertTrue(g.g[A].evil)
        run(g.change(g.g[A], character='Test Changeling'))  # no change: nobody is told
        self.assertEqual(len(self.told(g, A)), 1)

    def test_a_swap_exchanges_characters_and_if_asked_alignments(self):
        g = self.setup(['Test Plain', 'Test Crier', 'Test Plain', 'Test Henchman', 'Test Ghoul'])
        run(g.swap(g.g[B], g.g[E], alignments=True))
        self.assertEqual((g.g[B].character, g.g[B].alignment, g.g[E].character, g.g[E].alignment),
                         ('Test Ghoul', 'evil', 'Test Crier', 'good'))
        self.assertEqual(self.told(g, B), ['Day 1: you are now the Test Ghoul () and you are now evil.'])
        run(g.swap(g.g[A], g.g[D]))
        self.assertEqual((g.g[A].character, g.g[A].alignment), ('Test Henchman', 'good'))

    def test_a_dead_player_can_keep_their_ability_wake_and_lose_it(self):
        g = self.setup(['Test Plain', 'Test Plain', 'Test Plain', 'Test Hunter', 'Test Ghoul'])
        hunter = g.g[D]
        g.g.add(State('has ability', D, source=E, until=None, ends_with_source=True, while_source_works=True,
                      about='Minion'))
        g.kill(hunter, 'demon')
        self.assertTrue(g.g.keeps_ability(hunter) and g.g.works(hunter, 'Test Hunter'))
        self.assertIs(g.g.holder('Test Hunter'), hunter)
        self.assertIsNone(g.g.with_character('Test Hunter'))
        g.g.add(State('safe', A, source=D, until=None, ends_with_source=True))  # an effect of the kept ability
        log = []
        g.seats = {n: Answers({'targets': []}, log if n == D else []) for n in g.names}
        g.script = g.g.script = ch.Script.of('test', [c.name for c in TEST], [], ['Test Hunter'])
        run(g.night(2))
        self.assertEqual([r.kind for r in log], ['night'])  # the dead Hunter wakes
        g.g.poisoned = E  # the source loses its ability for now: so does the Hunter
        self.assertFalse(g.g.works(hunter, 'Test Hunter'))
        g.g.poisoned = None
        g.g.spend('Test Ghoul')  # no apparent death: it really dies
        g.kill(g.g[E], 'execution')  # gone for good, and its effects with it
        self.assertFalse(g.g.keeps_ability(hunter))
        self.assertFalse(g.g.safe(g.g[A], 'any'))

    def test_a_kept_ability_ends_when_the_player_is_no_longer_what_it_was_kept_for(self):
        g = self.setup(['Test Plain', 'Test Plain', 'Test Plain', 'Test Hunter', 'Test Ghoul'])
        g.g.add(State('has ability', D, source=E, until=None, ends_with_source=True, about='Minion'))
        g.kill(g.g[D], 'demon')
        run(g.change(g.g[D], character='Test Henchman'))  # another Minion: kept
        self.assertTrue(g.g.keeps_ability(g.g[D]))
        run(g.change(g.g[D], character='Test Plain'))
        self.assertFalse(g.g.keeps_ability(g.g[D]))

    def test_a_derived_state_follows_the_grimoire_and_cannot_feed_itself(self):
        g = self.setup(['Test Miasma', 'Test Guard', 'Test Plain', 'Test Plain', 'Test Ghoul'])
        self.assertEqual([p.name for p in g.g.players if g.g.is_poisoned(p)], [C])
        self.assertIn('POISONED', g.g.grimoire_text())
        run(g.change(g.g[C], character='Test Jester'))
        self.assertEqual(g.g.holders('poisoned'), [D])
        g.g.add(State('drunk', A, source=E, until=None))
        self.assertEqual(g.g.holders('poisoned'), [])
        g.g.states.clear()
        g.kill(g.g[A], 'demon')
        self.assertEqual(g.g.holders('poisoned'), [])
        self.assertEqual(ch.TB.derivers, [])

    def test_falsified_information_offers_only_false_values(self):
        from clocktower.state import Choice, judged, only_false
        g = self.setup(['Test Plain', 'Test Plain', 'Test Plain', 'Test Liar', 'Test Ghoul'])

        def info():
            c = Choice('info', [{'number': n} for n in range(4)], lambda r: {'number': 1})
            return judged(c, 'information', '?', recipient=A, truth=lambda v: v['number'] == 1)
        self.assertTrue(g.g.falsified(g.g[A]))
        self.assertFalse(g.g.falsified(g.g[D]))
        for i in range(50):
            g.st.rng = random.Random(i)
            self.assertNotEqual(run(g.decide_judged(info()))['number'], 1)
        self.assertEqual(only_false(info()).context['false_only'], True)
        c = Choice('x', [{'number': 1}], lambda r: {'number': 1})
        c.truth = lambda v: True
        self.assertIs(only_false(c), c)  # nothing false to give: unchanged
        g.kill(g.g[D], 'execution')
        self.assertFalse(g.g.falsified(g.g[A]))
        self.assertEqual(ch.TB.falsifiers, [])

    def test_a_nomination_or_an_execution_can_trigger_another_players_ability(self):
        g = self.setup(['Test Plain', 'Test Plain', 'Test Plain', 'Test Hexer', 'Test Ghoul', 'Test Guard'])
        run(g.nomination_judged(B, D))
        self.assertFalse(g.g[B].alive)
        self.assertEqual([e['data']['player'] for e in g.events if e['kind'] == 'died'], [B])
        run(g.nomination_judged(C, A))
        self.assertTrue(g.g[C].alive)
        g.execute(F)
        self.assertEqual(g.g.winner, 'evil')

    def test_madness_is_broken_by_claiming_what_a_player_must_not_be_mad_about(self):
        from clocktower import judge
        from clocktower.state import madness_broken
        g = self.setup(['Test Plain', 'Test Jester', 'Test Plain', 'Test Henchman', 'Test Ghoul'])
        g.emit('say', {'speaker': B, 'text': 'I am a Townsfolk, trust me.'})
        ev = judge.madness_evidence(g, B, 'Outsider', 1)
        self.assertFalse(madness_broken(ev, must=False))
        g.emit('say', {'speaker': B, 'text': "Fine: I'm the Test Jester."})
        ev = judge.madness_evidence(g, B, 'Outsider', 1)
        self.assertTrue(madness_broken(ev, must=False))
        self.assertFalse(judge.madness_evidence(g, B, 'Outsider', 2)['claimed'])  # only from day 2 on

    def test_team_sizes_can_floor_a_removal_of_outsiders(self):
        from clocktower.state import team_sizes
        self.assertEqual(team_sizes(7, -1), (6, -1, 1))  # the old arithmetic, as Bad Moon Rising's dealing uses it
        self.assertEqual(team_sizes(7, -1, floor=True), (5, 0, 1))
        self.assertEqual(team_sizes(8, -1, floor=True), (6, 0, 1))


if __name__ == '__main__':
    unittest.main()
