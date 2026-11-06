"""Bad Moon Rising's characters: the almanac's examples and How to Run, one test class per character.

Until every BMR character is built, the games here use a test script: the BMR characters under test plus plain
test-only fillers (registered for these tests and removed after), with the official night order."""
import asyncio
import random
import unittest

from clocktower import characters as ch
from clocktower import official
from clocktower.agents import ScriptedStoryteller
from clocktower.game import ALL_NAMES, NAMES, Game, Night
from clocktower.llm import Reply
from clocktower.render import render
from clocktower.state import POLICY, Grimoire, State

A, B, C, D, E, F, G, H, I = NAMES
BLANK = {'say': '', 'whispers': [], 'nominate': None, 'vote': None, 'targets': []}
BMR = ['Godfather', "Devil's Advocate", 'Assassin', 'Mastermind', 'Zombuul', 'Pukka', 'Shabaloth', 'Po']


class Town(ch.Townsfolk):
    name = 'Test Town'


class Town2(Town):
    name = 'Test Town 2'


class Town3(Town):
    name = 'Test Town 3'


class Town4(Town):
    name = 'Test Town 4'


class Town5(Town):
    name = 'Test Town 5'


class Town6(Town):
    name = 'Test Town 6'


class Town7(Town):
    name = 'Test Town 7'


class Out(ch.Outsider):
    name = 'Test Out'


class Out2(Out):
    name = 'Test Out 2'


class Fool(ch.Townsfolk):
    """The first time they die, they don't (the Fool)."""
    name = 'Test Fool'

    def survives(self, game, me, cause):
        if game.g.works(me, self.name) and not game.g.spent_ability(self.name):
            game.g.spend(self.name)
            return True
        return False


class Neighbourly(ch.Townsfolk):
    """Their living neighbours can't die (a Tea Lady with two good neighbours)."""
    name = 'Test Tea Lady'

    def protects(self, g, me, other, cause):
        return g.works(me, self.name) and other in g.neighbours(me)


FILLERS = [Town, Town2, Town3, Town4, Town5, Town6, Town7, Out, Out2, Fool, Neighbourly]
TOWN = 'Test Town'


class Seat:
    """Answers night requests from {night: answer}, and records every request."""

    def __init__(self):
        self.answers, self.log = {}, []

    async def act(self, text, request):
        self.log.append(request)
        if request.kind == 'night':
            return Reply({**BLANK, **self.answers.get(request.day, {})})
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


class BMRTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for c in FILLERS:
            ch.CHARACTERS[c.name] = c()
        cls.script = ch.Script.of('bmr-test', [c.name for c in FILLERS] + BMR, official.night_order(BMR, True),
                                  official.night_order(BMR, False))

    @classmethod
    def tearDownClass(cls):
        for c in FILLERS:
            del ch.CHARACTERS[c.name]

    def game(self, chars, forced=None):
        """A game with the Grimoire dealt as given (seat order), at day 1."""
        names = NAMES[:len(chars)]
        self.seats = {n: Seat() for n in names}
        g = Game(self.seats, Forced(forced), names=names, seed=3, characters=chars, script=self.script, probes=False)
        g.g = Grimoire(names, chars, script=self.script)
        g.day, g.phase, g.g.day = 1, 'day', 1
        return g

    def answer(self, night, **answers):
        for name, targets in answers.items():
            self.seats[name].answers[night] = {'targets': targets}

    def asked(self, name, night):
        return [r for r in self.seats[name].log if r.kind == 'night' and r.day == night]

    def day(self, g, n):
        g.day, g.phase, g.g.day = n, 'day', n

    def deaths(self, g, n):
        return [e['data']['deaths'] for e in g.events if e['kind'] == 'dawn' and e['data']['day'] == n][0]


class ZombuulTests(BMRTest):
    CHARS = [TOWN, 'Test Town 2', 'Test Out', 'Test Town 3', 'Test Town 4', 'Godfather', 'Zombuul']

    def test_the_first_death_lives_on_registering_dead_and_the_second_is_real(self):
        """How to Run: declare that they died, do not add a shroud; the second time, they die for real."""
        g = self.game(self.CHARS)
        z = g.g[G]
        g.execute(G)
        self.assertTrue(z.alive and z.seems_dead)
        self.assertIsNone(g.g.check_victory())
        self.assertEqual(g.g.died_today(), [G])  # marked DIED TODAY
        ev = [e for e in g.events if e['kind'] == 'execution'][-1]
        self.assertEqual(render(ev, A), f'{G} is executed.')  # as any death: the town sees them die
        self.day(g, 2)
        g.execute(G)
        self.assertFalse(z.alive)
        self.assertEqual(g.g.check_victory(), 'good')

    def test_executed_it_cannot_attack_tonight_and_later_two_other_players_alive_is_not_the_end(self):
        """Example: the Zombuul is executed and appears to die; they cannot attack tonight. Later only two players
        appear alive, and the game continues until one more player dies."""
        g = self.game(self.CHARS)
        g.execute(G)
        self.answer(2, **{G: [A]})
        run(g.night(2))
        self.assertEqual(self.asked(G, 2), [])  # somebody (the Zombuul) died today: not woken
        self.assertTrue(g.g[A].alive)
        for name in (B, C, D, E):
            g.g[name].alive = False
        self.assertEqual(sum(p.appears_alive for p in g.g.players), 2)
        self.assertIsNone(g.g.check_victory())  # three are really alive
        g.kill(g.g[A], 'demon')
        self.assertEqual(g.g.check_victory(), 'evil')

    def test_it_attacks_only_after_a_day_with_no_death_even_while_seeming_dead(self):
        """Example: nobody died today, the Zombuul attacks; the next day the Tinker dies; that night it does not
        wake."""
        g = self.game(self.CHARS)
        g.g[G].seems_dead = True
        g.g.spend('Zombuul')
        self.answer(2, **{G: [A]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A])
        g.kill(g.g[C], 'tinker')  # an Outsider dies by day, by their own ability
        self.answer(3, **{G: [B]})
        run(g.night(3))
        self.assertEqual(self.asked(G, 3), [])
        self.assertTrue(g.g[B].alive)

    def test_executing_a_dead_player_is_no_death_so_the_zombuul_wakes(self):
        g = self.game(self.CHARS)
        g.g[A].alive = False
        g.execute(A)
        self.assertEqual(g.g.died_today(), [])
        self.answer(2, **{G: [B]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [B])

    def test_a_drunk_or_poisoned_zombuul_dies_for_real(self):
        g = self.game(self.CHARS)
        g.g.add(State('poisoned', G))
        g.execute(G)
        self.assertFalse(g.g[G].alive)
        self.assertEqual(g.g.check_victory(), 'good')

    def test_a_poisoned_zombuul_attacks_nobody(self):
        g = self.game(self.CHARS)
        g.g.add(State('poisoned', G, until=None))
        self.answer(2, **{G: [A]})
        run(g.night(2))
        self.assertEqual(len(self.asked(G, 2)), 1)  # woken, but the attack fails
        self.assertEqual(self.deaths(g, 2), [])

    def test_seeming_dead_they_cannot_nominate_lose_their_vote_token_and_are_no_alive_neighbour(self):
        """Summary: they cannot nominate, lose their vote token when they vote, are not an alive neighbour."""
        g = self.game(self.CHARS)
        z = g.g[G]
        z.seems_dead = True
        self.assertEqual([q.name for q in g.g.neighbours(g.g[A])], [F, B])  # Gray sits between Frankie and Alex
        self.seats[G].log.clear()
        run(g.nominations())
        self.assertFalse([r for r in self.seats[G].log if r.kind == 'nominate'])
        self.assertTrue([r for r in self.seats[A].log if r.kind == 'nominate'])

        class Yes(Seat):
            async def act(self, text, request):
                self.log.append(request)
                return Reply({**BLANK, 'vote': True})
        g.seats[G] = Yes()
        run(g.vote(A, None, 0))
        prompt = g.seats[G].log[0].prompt
        self.assertIn('It takes 3 yes votes', prompt)  # six players appear alive
        self.assertIn('ghost vote', prompt)
        self.assertFalse(z.ghost_vote)


class PukkaTests(BMRTest):
    CHARS = ['Test Fool', 'Test Town 2', 'Test Out', 'Test Town 3', 'Test Town 4', 'Godfather', 'Pukka']

    def test_it_poisons_on_the_first_night_and_the_victim_dies_the_next_night_then_is_healthy(self):
        """Example: the Pukka poisons the Chambermaid, who gets false information; the next night they die."""
        g = self.game(self.CHARS)
        self.answer(1, **{G: [B]})
        run(g.night(1))
        self.assertEqual(len(self.asked(G, 1)), 1)  # unlike other Demons, it acts on the first night
        self.assertTrue(g.g.is_poisoned(g.g[B]))
        self.assertEqual(self.deaths(g, 1), [])
        self.day(g, 1)
        self.assertTrue(g.g.is_poisoned(g.g[B]))  # all day too
        self.answer(2, **{G: [C]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [B])
        self.assertFalse(g.g.is_poisoned(g.g[B]))
        self.assertTrue(g.g.is_poisoned(g.g[C]))

    def test_an_executed_victim_means_no_death_and_a_drunk_pukka_poisons_nobody_and_delays_the_death(self):
        """Example: the Pukka poisons the Fool, who is executed and dies (no ability); that night nobody dies and
        the Pukka poisons the Gossip; the next night the drunk Pukka tries to poison the Tinker but does not; the
        next night, the Gossip dies because the Pukka is sober."""
        g = self.game(self.CHARS)
        self.answer(1, **{G: [A]})
        run(g.night(1))
        self.day(g, 1)
        g.execute(A)
        self.assertFalse(g.g[A].alive)  # the poisoned Fool has no ability
        self.answer(2, **{G: [B]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])
        g.g.add(State('drunk', G, until=4))  # drunk for night 3
        self.answer(3, **{G: [C]})
        run(g.night(3))
        self.assertEqual(self.deaths(g, 3), [])
        self.assertFalse(g.g.is_poisoned(g.g[C]))
        self.assertFalse(g.g.is_poisoned(g.g[B]))  # paused while the Pukka is drunk
        self.answer(4, **{G: [D]})
        run(g.night(4))
        self.assertEqual(self.deaths(g, 4), [B])
        self.assertTrue(g.g.is_poisoned(g.g[D]))

    def test_a_pukka_not_woken_still_kills_its_earlier_victim(self):
        """Example: the Exorcist chooses the Pukka; the Pacifist dies, but the Pukka does not wake."""
        g = self.game(self.CHARS)
        g.g.add(State('poisoned', B, source=G, until=None, ends_with_source=True, while_source_works=True))
        night = Night(3)
        g.day, g.g.day = 3, 3
        run(ch.rules('Pukka').resolve_night(g, night))
        self.assertEqual([p.name for p in night.deaths], [B])
        self.assertFalse(any(s.kind == 'poisoned' for s in g.g.states))

    def test_a_victim_saved_from_the_demon_is_cured(self):
        """The Innkeeper prevents the Pukka from killing a poisoned player, then that player is no longer poisoned."""
        g = self.game(self.CHARS)
        g.g.add(State('poisoned', B, source=G, until=None, ends_with_source=True, while_source_works=True))
        g.g.add(State('safe', B, against='any', until=None))
        self.answer(2, **{G: [C]})
        run(g.night(2))
        self.assertTrue(g.g[B].alive)
        self.assertFalse(g.g.is_poisoned(g.g[B]))

    def test_the_poison_ends_with_the_pukka(self):
        g = self.game(self.CHARS)
        self.answer(1, **{G: [B]})
        run(g.night(1))
        self.day(g, 1)
        g.execute(G)
        self.assertFalse(g.g.is_poisoned(g.g[B]))

    def test_a_dead_player_can_be_poisoned(self):
        """Example: the Pukka chooses the dead Moonchild, whose ability then fails because they are poisoned."""
        g = self.game(self.CHARS)
        g.g[C].alive = False
        self.answer(1, **{G: [C]})
        run(g.night(1))
        self.assertTrue(g.g.is_poisoned(g.g[C]))

    def test_a_pukka_who_poisons_themself_is_not_poisoned_by_it_and_dies_the_next_night(self):
        g = self.game(self.CHARS)
        self.answer(1, **{G: [G]})
        run(g.night(1))
        self.assertFalse(g.g.is_poisoned(g.g[G]))
        self.answer(2, **{G: [B]})
        run(g.night(2))
        self.assertFalse(g.g[G].alive)
        self.assertEqual(g.g.check_victory(), 'good')


class ShabalothTests(BMRTest):
    CHARS = [TOWN, 'Test Tea Lady', 'Test Town 2', 'Test Out', 'Test Town 3', 'Test Town 4', 'Godfather',
             'Shabaloth']

    def test_it_kills_two_and_a_protected_one_survives(self):
        """Example: the Shabaloth attacks the Gossip, then the Gambler; the Gambler, protected, remains alive."""
        g = self.game(self.CHARS)
        g.g.add(State('safe', E, until=None))
        self.answer(2, **{H: [D, E]})
        run(g.night(2))
        req = self.asked(H, 2)[0]
        self.assertEqual((req.n_targets, req.min_targets), (2, 2))
        self.assertEqual(self.deaths(g, 2), [D])

    def test_a_protected_neighbour_survives_then_the_protector_dies(self):
        """Example: the Shabaloth attacks the Tea Lady's neighbour, then the Tea Lady: the neighbour, protected, does
        not die, but then the Tea Lady dies."""
        g = self.game(self.CHARS)
        self.answer(2, **{H: [C, B]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [B])
        self.assertTrue(g.g[C].alive)

    def test_a_dead_player_it_chose_last_night_may_be_regurgitated(self):
        """Example: the Shabaloth attacks the alive Courtier and the dead Exorcist; the Courtier dies. The next
        night the Storyteller decides that the Exorcist is alive again; they don't act tonight (their step is
        earlier). At dawn: alive again (not why)."""
        g = self.game(self.CHARS, forced={'Shabaloth': {'players': [E]}})
        g.g[E].alive = False
        g.g.spend('Test Town 3')  # a spent once-per-game ability comes back
        self.answer(2, **{H: [D, E]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [D])
        self.answer(3, **{H: [F, G]})
        run(g.night(3))
        dawn = [e for e in g.events if e['kind'] == 'dawn'][-1]
        self.assertEqual(dawn['data']['revived'], [E])
        self.assertTrue(g.g[E].alive and g.g[E].ghost_vote)
        self.assertFalse(g.g.spent_ability('Test Town 3'))
        self.assertEqual(g.g.revivals, [{'player': E, 'day': 3, 'source': 'Shabaloth'}])
        ids = [e['data']['id'] for e in g.events if e['kind'] == 'st_choice']
        self.assertIn('Shabaloth:' + H, ids)

    def test_only_last_nights_dead_choices_can_come_back_and_only_from_a_working_shabaloth(self):
        g = self.game(self.CHARS, forced={'Shabaloth': {'players': [D]}})
        self.answer(2, **{H: [D, E]})
        run(g.night(2))
        g.g.add(State('poisoned', H, until=None))
        self.answer(3, **{H: [F, G]})
        run(g.night(3))
        self.assertFalse(g.g[D].alive)  # a poisoned Shabaloth regurgitates no one (and kills no one)
        self.assertEqual(self.deaths(g, 3), [])
        g.g.states = []
        self.answer(4, **{H: [F, G]})
        run(g.night(4))
        self.assertFalse(g.g[D].alive)  # chosen two nights ago: too late
        ids = [e['data']['id'] for e in g.events if e['kind'] == 'st_choice']
        self.assertNotIn('Shabaloth:' + H, ids)

    def test_the_scripted_storyteller_regurgitates_rarely_and_usually_a_good_player(self):
        from clocktower.bmr import regurgitation_choice
        g = self.game(self.CHARS)
        g.g[A].alive = g.g[G].alive = False
        choice = regurgitation_choice(g.g, g.g[H], [A, G])
        self.assertEqual(len(choice.values), 3)
        r = random.Random(5)
        picks = [tuple(choice.options(r)['players']) for _ in range(2000)]
        self.assertAlmostEqual(picks.count(()) / 2000, 1 - POLICY['shabaloth_regurgitate'], delta=0.04)
        self.assertGreater(picks.count((A,)), 5 * picks.count((G,)))
        self.assertGreater(picks.count((G,)), 0)  # a Minion, rarely
        g.g.revivals = [{'player': B, 'day': 2, 'source': 'Shabaloth'}] * POLICY['regurgitations']
        choice = regurgitation_choice(g.g, g.g[H], [A, G])
        self.assertLess(sum(bool(choice.options(r)['players']) for _ in range(2000)), 150)  # beyond the budget


class PoTests(BMRTest):
    CHARS = [TOWN, 'Test Town 2', 'Test Out', 'Test Town 3', 'Test Town 4', 'Test Town 5', 'Godfather', 'Po']

    def test_choosing_no_one_charges_three_kills_the_next_night(self):
        """Example: on the second night the Po attacks one player; on the third, nobody; on the fourth, three."""
        g = self.game(self.CHARS)
        self.answer(2, **{H: [A]})
        run(g.night(2))
        req = self.asked(H, 2)[0]
        self.assertEqual((req.n_targets, req.min_targets), (1, 0))  # the first night does not count as no one
        self.assertEqual(self.deaths(g, 2), [A])
        self.answer(3, **{H: []})
        run(g.night(3))
        self.assertEqual(self.deaths(g, 3), [])
        self.assertFalse([e for e in g.events if e['kind'] == 'notice'])  # no one is taken as given
        self.answer(4, **{H: [B, C, D]})
        run(g.night(4))
        req = self.asked(H, 4)[0]
        self.assertEqual((req.n_targets, req.min_targets), (3, 3))  # must choose three
        self.assertEqual(self.deaths(g, 4), [B, C, D])
        self.answer(5, **{H: []})
        run(g.night(5))
        self.assertEqual(self.asked(H, 5)[0].n_targets, 1)

    def test_a_drunk_no_one_still_charges_and_a_poisoned_triple_kills_no_one(self):
        """Example: the Po chooses nobody, but is drunk; the next night, poisoned, it chooses three: none die; the
        following night, sober and healthy, it attacks a player, who dies."""
        g = self.game(self.CHARS)
        g.g.add(State('drunk', H, until=3))  # drunk on night 2
        self.answer(2, **{H: []})
        run(g.night(2))
        g.g.add(State('poisoned', H, until=4))  # poisoned on night 3
        self.answer(3, **{H: [A, B, C]})
        run(g.night(3))
        self.assertEqual(self.asked(H, 3)[0].n_targets, 3)
        self.assertEqual(self.deaths(g, 3), [])
        self.answer(4, **{H: [D]})
        run(g.night(4))
        self.assertEqual(self.asked(H, 4)[0].n_targets, 1)
        self.assertEqual(self.deaths(g, 4), [D])

    def test_a_night_it_is_not_woken_keeps_the_charge(self):
        """If the Po chose no one the night before the Exorcist chose it, it chooses three the night after."""
        g = self.game(self.CHARS)
        po = ch.rules('Po')
        g.g.last_choices[H] = []
        self.assertEqual(po.night_spec(g, g.g[H], Night(3)).players, 3)  # still three after a night not woken
        g.g.last_choices[H] = [A]
        self.assertEqual(po.night_spec(g, g.g[H], Night(3)).players, 1)  # a choice that killed no one: one


class GodfatherTests(BMRTest):
    CHARS = [TOWN, 'Test Town 2', 'Test Out', 'Test Town 3', 'Test Out 2', 'Test Town 4', 'Godfather', 'Po']

    def test_it_starts_knowing_which_outsiders_are_in_play(self):
        """Example: the Godfather learns that the Lunatic and the Moonchild are in play."""
        g = self.game(self.CHARS)
        run(g.night(1))
        info = [e for e in g.events if e['kind'] == 'info' and e['to'] == [G]]
        self.assertEqual(info[-1]['data']['text'], 'Night 1 — Godfather: the Outsiders in play are: Test Out, Test Out 2.')
        self.assertEqual(self.asked(G, 1), [])  # nothing to choose
        self.assertIn(G, g.g.woke[1])

    def test_an_impaired_godfather_may_be_shown_a_false_set_of_a_count_the_setup_allows(self):
        from clocktower.bmr import outsiders_choice
        g = self.game(self.CHARS)
        g.g.add(State('poisoned', G))
        choice = outsiders_choice(g.g, g.g[G])
        # 8 players: one Outsider, plus or minus one; never a count the setup rules out
        self.assertEqual({len(v['characters']) for v in choice.values}, {0, 2})
        r = random.Random(2)
        shown = [tuple(choice.options(r)['characters']) for _ in range(200)]
        self.assertIn((), shown)  # the only false answer here: no Outsiders
        self.assertGreater(shown.count(()), 100)  # usually false (POLICY poisoned_false)
        self.assertFalse(choice.truth({'characters': []}))
        g.g.states = []
        self.assertTrue(outsiders_choice(g.g, g.g[G]).auto)  # a working Godfather: the truth only

    def test_after_an_outsider_dies_by_day_it_chooses_a_player_who_dies(self):
        """Example: the Lunatic dies by execution; that night the Demon kills the Minstrel, and the Godfather kills
        the Pacifist."""
        g = self.game(self.CHARS)
        g.execute(C)
        self.answer(2, **{G: [A], H: [B]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A, B])
        self.assertEqual({d['player']: d['cause'] for d in g.g.death_log if d['phase'] == 'night'},
                         {A: 'godfather', B: 'demon'})

    def test_no_kill_after_a_day_without_an_outsider_death_or_after_an_outsider_died_at_night(self):
        """Outsiders that die at night don't count."""
        g = self.game(self.CHARS)
        g.execute(A)  # a Townsfolk
        run(g.night(2))
        self.assertEqual(self.asked(G, 2), [])
        self.day(g, 2)
        g.phase = 'night'
        g.kill(g.g[C], 'demon')
        g.phase = 'day'
        run(g.night(3))
        self.assertEqual(self.asked(G, 3), [])

    def test_an_outsider_saved_from_execution_does_not_count_but_one_dying_by_their_own_ability_does(self):
        """Example: the Tinker is executed but remains alive (the Devil's Advocate): the Godfather does not act.
        The next day the Tinker dies by their own ability; that night the Godfather kills themself."""
        g = self.game(self.CHARS)
        g.g.add(State('safe', C, against='execution'))
        g.execute(C)
        self.assertTrue(g.g[C].alive)
        run(g.night(2))
        self.assertEqual(self.asked(G, 2), [])
        g.kill(g.g[C], 'tinker')
        g.kill(g.g[E], 'tinker')  # two Outsiders died: still one kill
        self.answer(3, **{G: [G]})
        run(g.night(3))
        req = self.asked(G, 3)[0]
        self.assertEqual(req.n_targets, 1)
        self.assertFalse(g.g[G].alive)

    def test_its_kill_is_stopped_by_protection(self):
        g = self.game(self.CHARS)
        g.g.add(State('safe', A, against='any', until=None))
        g.execute(C)
        self.answer(2, **{G: [A]})
        run(g.night(2))
        self.assertTrue(g.g[A].alive)

    def test_setup_has_one_outsider_more_or_fewer(self):
        from clocktower.state import setup_error
        towns = ['Test Town', 'Test Town 2', 'Test Town 3', 'Test Town 4', 'Test Town 5', 'Test Town 6']
        # 8 players: 5 Townsfolk and 1 Outsider normally; with the Godfather 4 and 2, or 6 and 0
        self.assertIsNone(setup_error(towns[:4] + ['Test Out', 'Test Out 2', 'Godfather', 'Po'], self.script))
        self.assertIsNone(setup_error(towns + ['Godfather', 'Po'], self.script))
        self.assertIsNotNone(setup_error(towns[:5] + ['Test Out', 'Godfather', 'Po'], self.script))
        self.assertIsNone(setup_error(towns[:5] + ['Test Out', 'Assassin', 'Po'], self.script))


class DevilsAdvocateTests(BMRTest):
    CHARS = [TOWN, 'Test Town 2', 'Test Out', 'Test Town 3', 'Test Town 4', "Devil's Advocate", 'Zombuul']

    def test_a_chosen_player_who_is_executed_tomorrow_does_not_die(self):
        """Example: at night, the Devil's Advocate protects themself; the next day, they are executed but remain
        alive (the town is not told why)."""
        g = self.game(self.CHARS)
        self.answer(1, **{F: [F]})
        run(g.night(1))
        self.day(g, 1)
        g.execute(F)
        self.assertTrue(g.g[F].alive)
        ev = [e for e in g.events if e['kind'] == 'execution'][-1]
        self.assertEqual(render(ev, A), f'{F} is executed, but does not die.')
        self.assertEqual(g.g.executions, [{'player': F, 'day': 1, 'died': False}])

    def test_a_saved_zombuul_stays_alive_and_the_next_execution_makes_it_seem_dead(self):
        """Example: the Devil's Advocate protects the Zombuul, executed but remaining alive (life token not
        flipped); the next day the Zombuul is executed again and registers as dead."""
        g = self.game(self.CHARS)
        self.answer(1, **{F: [G]})
        run(g.night(1))
        self.day(g, 1)
        g.execute(G)
        self.assertTrue(g.g[G].appears_alive)
        self.answer(2, **{F: [A]})
        run(g.night(2))
        self.day(g, 2)
        g.execute(G)
        self.assertTrue(g.g[G].alive and g.g[G].seems_dead)

    def test_it_chooses_a_living_player_other_than_last_nights_and_never_a_zombuul_that_seems_dead(self):
        g = self.game(self.CHARS)
        g.g[A].alive = False
        g.g[G].seems_dead = True
        g.g.last_choices[F] = [B]
        self.answer(2, **{F: [C]})
        run(g.night(2))
        options = self.asked(F, 2)[0].options
        self.assertEqual(options, [C, D, E, F])

    def test_the_save_lasts_one_day_and_needs_a_working_devils_advocate(self):
        g = self.game(self.CHARS)
        self.answer(1, **{F: [A]})
        run(g.night(1))
        g.g.add(State('drunk', F))  # drunk by the time of the execution
        self.day(g, 1)
        g.execute(A)
        self.assertFalse(g.g[A].alive)
        self.answer(2, **{F: [B]})
        run(g.night(2))
        self.day(g, 2)
        run(g.night(3))  # tomorrow has passed
        self.day(g, 3)
        g.execute(B)
        self.assertFalse(g.g[B].alive)


class AssassinTests(BMRTest):
    CHARS = ['Test Fool', 'Test Tea Lady', 'Test Town 2', 'Test Out', 'Test Town 3', 'Test Town 4', 'Assassin', 'Po']

    def test_it_may_wait_and_once_it_kills_it_never_wakes_again(self):
        """Example: for the first three nights the Assassin wakes but chooses not to act; on the fourth it kills
        the Fool, who dies and stays dead even though they still have their ability."""
        g = self.game(self.CHARS)
        run(g.night(1))
        self.assertEqual(self.asked(G, 1), [])  # not on the first night
        for n in (2, 3):
            self.answer(n, **{G: []})
            run(g.night(n))
            self.assertEqual((self.asked(G, n)[0].min_targets, self.asked(G, n)[0].n_targets), (0, 1))
            self.assertIn(G, g.g.woke[n])  # waking counts, even to decline
        self.assertFalse(g.g.spent_ability('Assassin'))
        self.answer(4, **{G: [A]})
        run(g.night(4))
        self.assertEqual(self.deaths(g, 4), [A])
        self.assertFalse(g.g.spent_ability('Test Fool'))  # the Fool's ability did not save them
        run(g.night(5))
        self.assertEqual(self.asked(G, 5), [])

    def test_it_kills_through_protection(self):
        """Example: the Assassin kills one of the Tea Lady's neighbours, who dies though protected."""
        g = self.game(self.CHARS)
        g.g.add(State('safe', C, against='any', until=None))
        self.answer(2, **{G: [C]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [C])

    def test_a_drunk_assassin_kills_no_one_and_loses_the_ability(self):
        """Example: the Assassin, drunk due to the Courtier, chooses the Goon; the Assassin has no ability."""
        g = self.game(self.CHARS)
        g.g.add(State('drunk', G, until=None))
        self.answer(2, **{G: [D]})
        run(g.night(2))
        self.assertTrue(g.g[D].alive)
        self.assertTrue(g.g.spent_ability('Assassin'))

    def test_it_kills_a_zombuul_for_real(self):
        """A reading: like the Fool, the Zombuul's first death does not save it, and one that seems dead can die."""
        g = self.game([TOWN, 'Test Town 2', 'Test Out', 'Test Town 3', 'Test Town 4', 'Assassin', 'Zombuul'])
        self.answer(2, **{F: [G]})
        run(g.night(2))
        self.assertFalse(g.g[G].alive)
        g = self.game([TOWN, 'Test Town 2', 'Test Out', 'Test Town 3', 'Test Town 4', 'Assassin', 'Zombuul'])
        g.g[G].seems_dead = True
        g.g.spend('Zombuul')
        g.execute(A)  # someone died today: the Zombuul sleeps, the Assassin doesn't
        self.answer(2, **{F: [G]})
        run(g.night(2))
        self.assertFalse(g.g[G].alive)

    def test_a_regurgitated_assassin_gets_the_ability_back(self):
        g = self.game(self.CHARS)
        g.g.spend('Assassin')
        g.g[G].alive = False
        g.g.revive(g.g[G], 'Shabaloth')
        self.assertIsNotNone(ch.rules('Assassin').night_spec(g, g.g[G], Night(3)))


class MastermindTests(BMRTest):
    CHARS = [TOWN, 'Test Town 2', 'Test Out', 'Test Town 3', 'Test Town 4', 'Mastermind', 'Shabaloth']

    def extra_day(self, chars=None):
        """The Demon is executed on day 1; the game goes on."""
        g = self.game(chars or self.CHARS)
        g.execute(G)
        self.assertFalse(g.g[G].alive)
        self.assertIsNone(g.g.winner)
        self.answer(2, **{G: [A, B]})
        run(g.night(2))
        self.assertIsNone(g.g.check_victory())
        self.day(g, 2)
        return g

    def test_a_good_player_executed_on_the_extra_day_loses_the_game_for_good(self):
        """Example: the Shabaloth dies; the next day the Professor is executed and dies; evil wins. The dead Demon
        does not attack on the extra night."""
        g = self.extra_day()
        self.assertEqual(self.deaths(g, 2), [])
        self.assertEqual(self.asked(G, 2), [])
        g.execute(C)
        self.assertEqual(g.g.winner, 'evil')
        self.assertIn('Mastermind', g.g.reason)

    def test_an_evil_player_executed_on_it_loses_even_if_they_survive(self):
        """Example: the Po dies; the next day the Godfather is executed but remains alive (the Devil's Advocate);
        an evil player was executed, so good wins."""
        g = self.extra_day()
        g.g.add(State('safe', F, against='execution'))
        g.execute(F)
        self.assertTrue(g.g[F].alive)
        self.assertEqual(g.g.winner, 'good')

    def test_no_execution_on_the_extra_day_means_good_wins_and_two_alive_does_not_end_it(self):
        """Example: three players alive, the Demon dies; the next day, two alive, good doesn't execute; at night
        good wins."""
        g = self.game(self.CHARS)
        for name in (A, B, C, D):
            g.g[name].alive = False
        g.execute(G)
        self.assertEqual(g.g.alive_count(), 2)
        self.assertIsNone(g.g.check_victory())
        run(g.night(2))
        self.assertIsNone(g.g.check_victory())
        self.day(g, 2)
        g.moment('dusk')
        self.assertEqual(g.g.check_victory(), 'good')
        self.assertIn('nobody was executed', g.g.reason)

    def test_a_drunk_or_dead_mastermind_lets_the_game_end(self):
        """Example (Courtier): a drunk Mastermind, and the executed Po ends the game."""
        g = self.game(self.CHARS)
        g.g.add(State('drunk', F))
        g.execute(G)
        self.assertEqual(g.g.winner, 'good')
        g = self.game(self.CHARS)
        g.g[F].alive = False
        g.execute(G)
        self.assertEqual(g.g.winner, 'good')

    def test_a_demon_dying_at_night_ends_the_game(self):
        g = self.game(self.CHARS)
        g.phase = 'night'
        g.kill(g.g[G], 'assassin')
        self.assertEqual(g.g.check_victory(), 'good')

    def test_the_zombuuls_seeming_death_does_not_trigger_it_but_its_real_one_does(self):
        """Example: the Zombuul is executed and appears to die: no trigger, the game did not end. Executed a second
        time it dies for real, and the game continues for one more day."""
        g = self.game([TOWN, 'Test Town 2', 'Test Out', 'Test Town 3', 'Test Town 4', 'Mastermind', 'Zombuul'])
        g.execute(G)
        self.assertNotIn('Mastermind', g.g.notes)
        self.day(g, 2)
        g.execute(G)
        self.assertFalse(g.g[G].alive)
        self.assertIsNone(g.g.winner)
        self.assertEqual(g.g.notes['Mastermind'], 2)

    def test_the_whole_game_plays_the_extra_day(self):
        """Through Game.run's loop: the Demon executed on day 1, nobody executed on day 2: good wins after day 2."""
        g = self.extra_day()

        async def go():
            await g.daytime(2)  # silent seats: nobody nominates
            return g.g.check_victory()
        g.private_beats = g.public_beats = 0
        self.assertEqual(run(go()), 'good')


class DemonInfoTests(BMRTest):
    def test_each_demon_learns_its_minions_and_bluffs_and_the_minions_learn_the_demon(self):
        for demon in ('Zombuul', 'Pukka', 'Shabaloth', 'Po'):
            chars = ['Test Town', 'Test Town 2', 'Test Town 3', 'Test Town 4', 'Test Town 5', 'Test Town 6',
                     'Test Out', 'Godfather', 'Assassin', demon]
            names = ALL_NAMES[:10]
            seats = {n: Seat() for n in names}
            g = Game(seats, Forced(), names=names, seed=3, characters=chars, script=self.script, probes=False)
            run(g.setup())
            intro = {e['to'][0]: e['data']['text'] for e in g.events if e['kind'] == 'intro'}
            demon_seat = names[9]
            self.assertIn(f'Your Minions: {H}, {I}', intro[demon_seat])
            self.assertEqual(len(g.g.bluffs), 3)
            self.assertIn(f'The Demon is {demon_seat}.', intro[H])
            run(g.night(1))
            self.assertTrue(any(e['kind'] == 'info' and e['to'] == [H] and 'Test Out' in e['data']['text']
                                for e in g.events))


if __name__ == '__main__':
    unittest.main()


class SmokeTests(BMRTest):
    def test_whole_games_with_these_demons_and_minions_run_to_the_end(self):
        """Random seats, every Demon with two of these Minions: no crash, and nearly every game ends (random seats
        rarely execute, so a Zombuul can outlast twelve days)."""
        from clocktower.agents import RandomSeat
        from clocktower.game import ALL_NAMES
        towns = ['Test Town', 'Test Town 2', 'Test Town 3', 'Test Town 4', 'Test Town 5', 'Test Fool', 'Test Tea Lady']
        minions = ['Godfather', "Devil's Advocate", 'Assassin', 'Mastermind']
        ended = []
        for seed in range(16):  # ten players: 7 Townsfolk and 2 Minions (6 and an Outsider with the Godfather)
            r = random.Random(seed)
            pair = r.sample(minions, 2)
            outsiders = ['Test Out'] if 'Godfather' in pair else []
            chars = towns[:7 - len(outsiders)] + outsiders + pair + [['Zombuul', 'Pukka', 'Shabaloth', 'Po'][seed % 4]]
            r.shuffle(chars)
            names = ALL_NAMES[:len(chars)]
            seats = {n: RandomSeat(n, random.Random(seed * 31 + i), names) for i, n in enumerate(names)}
            g = Game(seats, Forced(), names=names, seed=seed, characters=chars, script=self.script, probes=False,
                     private_beats=1, public_beats=1, max_days=12)
            result = run(g.run())
            ended.append(result['winner'])
            self.assertTrue(result['winner'] or result['stopped'].startswith('stopped after'), result['reason'])
        self.assertGreater(sum(w is not None for w in ended), 12, ended)
