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
BMR += ['Sailor', 'Innkeeper', 'Courtier', 'Minstrel', 'Exorcist', 'Tea Lady', 'Pacifist', 'Fool', 'Gambler',
        'Professor']
BMR += ['Grandmother', 'Chambermaid', 'Gossip', 'Goon', 'Lunatic', 'Tinker', 'Moonchild']


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


class StartKnowing(ch.Townsfolk):
    """A "you start knowing" Townsfolk (the Grandmother): told something again when the Professor revives them."""
    name = 'Test Grandmother'

    async def resurrected(self, game, me, night):
        game.inform(me, 'You learn your Grandchild again.')


FILLERS = [Town, Town2, Town3, Town4, Town5, Town6, Town7, Out, Out2, Fool, Neighbourly, StartKnowing]
TOWN = 'Test Town'


class Seat:
    """Answers night requests from {night: answer}, and records every request."""

    def __init__(self):
        self.answers, self.log = {}, []

    async def act(self, text, request):
        self.log.append(request)
        if request.kind in ('night', 'death_choice'):  # a death_choice by day (the Moonchild's) answers from day n
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

    def dealt(self, chars, forced=None):
        """A game set up as a real one is (the characters' setup steps, everyone's introduction), seat order kept."""
        names = NAMES[:len(chars)]
        self.seats = {n: Seat() for n in names}
        g = Game(self.seats, Forced(forced), names=names, seed=3, characters=chars, script=self.script, probes=False)
        run(g.setup())
        return g

    def answer(self, night, **answers):
        for name, targets in answers.items():
            self.seats[name].answers[night] = {'targets': targets}

    def choose(self, night, name, targets=(), character=None):
        """`name`'s answer on `night`: players and a character (the Gambler, the Courtier)."""
        self.seats[name].answers[night] = {'targets': list(targets), 'character': character}

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
        self.assertEqual(info[-1]['data']['text'],
                         'Night 1 — Godfather: the Outsiders in play are: Test Out, Test Out 2.')
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
        false = [x for x in shown if not choice.truth({'characters': list(x)})]
        self.assertGreater(len(false), 100)  # usually false (POLICY poisoned_false)
        self.assertEqual({len(x) for x in false}, {2})  # of the true count, so nothing gives it away
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


# ---- Batch 2: the Townsfolk that protect, make players drunk, or bring players back ----------------------------

def drunk(g, name):
    return g.g.is_drunk(g.g[name])


def choices(g, prefix):
    return [e['data'] for e in g.events if e['kind'] == 'st_choice' and e['data']['id'].startswith(prefix)]


class SailorTests(BMRTest):
    # Alex Sailor, Blair Exorcist, Casey Town, Drew Out, Ellis Town 2, Frankie Mastermind, Gray Shabaloth
    CHARS = ['Sailor', 'Exorcist', TOWN, 'Test Out', 'Test Town 2', 'Mastermind', 'Shabaloth']

    def test_a_target_made_drunk_and_a_sober_sailor_survives_the_demon_and_execution(self):
        """Example: the Sailor chooses the Exorcist, who is drunk; the Shabaloth attacks the Sailor, who remains
        alive; the next day the Sailor is executed but remains alive. (The drunk Exorcist's choice of the Demon
        does nothing.)"""
        g = self.game(self.CHARS, forced={'Sailor': {'players': [B]}, 'Shabaloth': {'players': []}})
        self.answer(2, **{A: [B], B: [G], G: [A, C]})
        run(g.night(2))
        self.assertEqual(len(self.asked(G, 2)), 1)  # the drunk Exorcist did not stop the Demon
        self.assertEqual(self.deaths(g, 2), [C])
        self.assertTrue(drunk(g, B) and not drunk(g, A))
        self.assertIn('DRUNK', g.g.grimoire_text().splitlines()[1])
        self.assertEqual(choices(g, 'Sailor:')[0]['value'], {'players': [B]})
        self.day(g, 2)
        g.execute(A)
        self.assertTrue(g.g[A].alive)
        self.assertEqual(g.g.executions[-1], {'player': A, 'day': 2, 'died': False})
        g.g.expire('night', 3)
        self.assertFalse(drunk(g, B))  # until dusk

    def test_a_sailor_who_chose_themself_is_drunk_and_can_die(self):
        """Example: the Sailor has made themself drunk, and the Gossip's ability kills them."""
        g = self.game(self.CHARS)
        self.answer(2, **{A: [A], G: [C, E]})
        run(g.night(2))
        self.assertTrue(drunk(g, A))
        self.assertEqual(choices(g, 'Sailor:'), [])  # nothing to decide
        g.phase = 'night'
        self.assertEqual(g.attempt_kill(g.g[A], 'gossip'), g.g[A])

    def test_a_sailor_made_drunk_after_choosing_an_evil_player_dies_when_executed(self):
        """Example: the Sailor chooses the Mastermind, the Storyteller makes the Sailor drunk; the next day, executed
        to prove they are the Sailor, they die."""
        g = self.game(self.CHARS, forced={'Sailor': {'players': [A]}})
        self.answer(1, **{A: [F]})
        run(g.night(1))
        self.assertTrue(drunk(g, A))
        g.execute(A)
        self.assertFalse(g.g[A].alive)

    def test_the_scripted_storyteller_usually_drinks_a_townsfolk_and_otherwise_the_sailor(self):
        from clocktower.bmr import sailor_choice
        g = self.game(self.CHARS)
        r = random.Random(4)
        for target, usual in ((C, C), (D, A), (F, A), (G, A)):
            picks = [sailor_choice(g.g, g.g[A], target).options(r)['players'][0] for _ in range(1000)]
            self.assertAlmostEqual(picks.count(usual) / 1000, 0.8, delta=0.05)
            self.assertEqual(set(picks), {A, target})  # either can happen

    def test_it_chooses_a_living_player_and_cannot_die_before_choosing_but_the_assassin_kills_it(self):
        """A dead player is not an option; a sober Sailor can't die, even before waking; the Assassin kills anyone."""
        g = self.game(self.CHARS)
        g.g[C].alive = False
        self.answer(1, **{A: [B]})
        run(g.night(1))
        self.assertNotIn(C, self.asked(A, 1)[0].options)
        self.assertIn(A, self.asked(A, 1)[0].options)
        g = self.game(self.CHARS)
        self.assertTrue(g.g.safe(g.g[A], 'demon') and g.g.safe(g.g[A], 'execution'))
        g.g.add(State('poisoned', A))
        self.assertFalse(g.g.safe(g.g[A], 'demon'))
        g = self.game(['Sailor', TOWN, 'Test Out', 'Test Town 2', 'Test Town 3', 'Assassin', 'Po'])
        self.answer(2, **{A: [B], F: [A], G: [C]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A, C])

    def test_a_drunk_or_poisoned_sailor_makes_nobody_drunk(self):
        g = self.game(self.CHARS)
        g.g.add(State('poisoned', A, until=None))
        self.answer(1, **{A: [C]})
        run(g.night(1))
        self.assertFalse(any(s.kind == 'drunk' for s in g.g.states))


class InnkeeperTests(BMRTest):
    # Alex Innkeeper, Blair Fool, Casey Pacifist, Drew Town, Ellis Town 2, Frankie Assassin, Gray Po
    CHARS = ['Innkeeper', 'Fool', 'Pacifist', TOWN, 'Test Town 2', 'Assassin', 'Po']

    def test_a_drunk_fool_is_protected_tonight_but_dies_when_executed(self):
        """Example: the Innkeeper protects the Fool and the Chambermaid; the Fool is drunk; executed tomorrow, they
        die, though they hadn't used their ability."""
        g = self.game(self.CHARS, forced={'Innkeeper': {'players': [B]}, 'Pacifist': {'yes': False}})
        self.answer(2, **{A: [B, D], F: [], G: [B]})
        run(g.night(2))
        req = self.asked(A, 2)[0]
        self.assertEqual((req.n_targets, req.min_targets), (2, 2))
        self.assertEqual(self.deaths(g, 2), [])  # the Po's attack on the protected Fool fails
        self.assertFalse(g.g.spent_ability('Fool'))  # the protection, not the Fool's ability, saved them
        self.assertTrue(drunk(g, B) and not drunk(g, D))
        self.assertFalse(any(s.kind == 'safe' for s in g.g.states))  # SAFE goes at dawn
        run(g.execution(B))
        self.assertFalse(g.g[B].alive)

    def test_a_drunk_assassins_kill_does_nothing(self):
        """Example: the Innkeeper protects the Assassin and the Po; the Assassin is drunk and its kill fails."""
        g = self.game(self.CHARS, forced={'Innkeeper': {'players': [F]}})
        self.answer(2, **{A: [F, G], F: [D], G: [E]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [E])
        self.assertTrue(g.g.spent_ability('Assassin'))

    def test_an_innkeeper_made_drunk_by_choosing_themself_protects_nobody(self):
        """Example: the Innkeeper protects themself and the Pacifist, is drunk, and the Demon kills the Pacifist."""
        g = self.game(self.CHARS, forced={'Innkeeper': {'players': [A]}})
        self.answer(2, **{A: [A, C], F: [], G: [C]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [C])

    def test_it_stops_every_death_tonight_but_the_assassins_and_not_by_day(self):
        g = self.game(self.CHARS, forced={'Innkeeper': {'players': [E]}})
        self.answer(2, **{A: [D, E], F: [D], G: [E]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [D])  # the Assassin kills through; the Po's attack fails
        g = self.game(self.CHARS, forced={'Innkeeper': {'players': [E]}})
        night = Night(2)
        g.day, g.g.day, g.phase = 2, 2, 'night'
        night.chosen[A] = [D, E]
        run(ch.rules('Innkeeper').resolve_night(g, night))
        self.assertIsNone(g.attempt_kill(g.g[D], 'godfather', g.g[F], night))  # a Minion's kill
        self.assertIsNone(g.attempt_kill(g.g[D], 'gambler', g.g[D], night))  # a Townsfolk's own ability
        self.assertIn('cannot die', g.g.grimoire_text())
        g.g.expire('dawn')
        self.day(g, 2)
        g.execute(D)
        self.assertFalse(g.g[D].alive)

    def test_protection_ends_if_the_innkeeper_dies_tonight(self):
        """Example: the Tinker, protected by the Innkeeper, survives the Demon; later that night the Innkeeper dies,
        so the Storyteller kills the Tinker too."""
        g = self.game(self.CHARS, forced={'Innkeeper': {'players': [E]}})
        night = Night(2)
        g.day, g.g.day, g.phase = 2, 2, 'night'
        night.chosen[A] = [D, E]
        run(ch.rules('Innkeeper').resolve_night(g, night))
        self.assertIsNone(g.demon_attack(g.g[D], g.g[G], night))
        g.kill(g.g[A], 'demon')
        self.assertFalse(drunk(g, E))
        self.assertEqual(g.attempt_kill(g.g[D], 'tinker', None, night), g.g[D])

    def test_the_scripted_storyteller_drinks_a_self_choosing_innkeeper_and_usually_a_good_player(self):
        from clocktower.bmr import innkeeper_choice
        g = self.game(self.CHARS)
        r = random.Random(6)
        picks = [innkeeper_choice(g.g, g.g[A], [A, F]).options(r)['players'][0] for _ in range(1000)]
        self.assertAlmostEqual(picks.count(A) / 1000, 0.8, delta=0.05)
        picks = [innkeeper_choice(g.g, g.g[A], [D, F]).options(r)['players'][0] for _ in range(1000)]
        self.assertAlmostEqual(picks.count(D) / 1000, 0.9, delta=0.04)
        self.assertIn(F, picks)  # an evil player, sometimes
        picks = [innkeeper_choice(g.g, g.g[A], [D, E]).options(r)['players'][0] for _ in range(1000)]
        self.assertAlmostEqual(picks.count(D) / 1000, 0.5, delta=0.06)

    def test_not_on_the_first_night_and_a_drunk_innkeeper_does_nothing(self):
        g = self.game(self.CHARS)
        run(g.night(1))
        self.assertEqual(self.asked(A, 1), [])
        g.g.add(State('poisoned', A, until=None))
        self.answer(2, **{A: [D, E], F: [], G: [D]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [D])
        self.assertFalse(any(s.kind == 'drunk' for s in g.g.states))


class CourtierTests(BMRTest):
    # Alex Courtier, Blair Town, Casey Town 2, Drew Out, Ellis Town 3, Frankie Mastermind, Gray Shabaloth
    CHARS = ['Courtier', TOWN, 'Test Town 2', 'Test Out', 'Test Town 3', 'Mastermind', 'Shabaloth']

    def test_it_waits_then_makes_the_demon_drunk_for_three_nights_and_three_days(self):
        """Example: for four nights the Courtier wakes but does not use their ability; on the fifth they make the
        Shabaloth drunk, which for the next three nights acts but cannot kill anybody."""
        g = self.game(self.CHARS, forced={'Shabaloth': {'players': []}})
        g.g[B].alive = g.g[C].alive = False
        for n in range(1, 5):
            self.choose(n, A)  # no character: declined
            self.answer(n, **{G: [B, C]})
            run(g.night(n))
            req = self.asked(A, n)[0]
            self.assertEqual((req.n_targets, req.min_targets), (0, 0))
            self.assertIn('Shabaloth', req.characters)
            self.assertIn('(null for none)', req.prompt)
        self.assertFalse(g.g.spent_ability('Courtier'))
        self.choose(5, A, character='Shabaloth')
        for n in (5, 6, 7, 8):
            self.answer(n, **{G: [D, E]})
            run(g.night(n))
            self.day(g, n)
            self.assertEqual(drunk(g, G), n < 8)
            if n > 5:
                self.assertEqual(self.asked(A, n), [])  # never woken again
        self.assertEqual([self.deaths(g, n) for n in (5, 6, 7, 8)], [[], [], [], [D, E]])

    def test_a_drunk_courtier_wastes_the_ability(self):
        """Example: the Courtier uses their ability while drunk: nothing happens, and they are not woken again."""
        g = self.game(self.CHARS)
        g.g.add(State('poisoned', A, until=None))
        self.choose(1, A, character='Shabaloth')
        run(g.night(1))
        self.assertFalse(drunk(g, G))
        self.assertTrue(g.g.spent_ability('Courtier'))
        g.g.states = []
        run(g.night(2))
        self.assertEqual(self.asked(A, 2), [])
        self.assertFalse(drunk(g, G))  # nor later, now the Courtier is sober

    def test_a_drunk_mastermind_lets_the_executed_demon_end_the_game(self):
        """Example: the Courtier makes the Mastermind drunk; the Po is executed while the Mastermind lives: good
        wins."""
        g = self.game(self.CHARS)
        self.choose(1, A, character='Mastermind')
        run(g.night(1))
        self.day(g, 1)
        g.execute(G)
        self.assertEqual(g.g.winner, 'good')

    def test_the_drunkenness_pauses_while_the_courtier_is_impaired_and_resumes(self):
        g = self.game(self.CHARS, forced={'Shabaloth': {'players': []}})
        self.choose(2, A, character='Shabaloth')
        self.answer(2, **{G: [B, C]})
        run(g.night(2))
        self.assertTrue(drunk(g, G))
        poison = State('poisoned', A, until=None)
        g.g.add(poison)
        self.assertFalse(drunk(g, G))  # the Courtier is poisoned: the Shabaloth sobers
        g.g.states.remove(poison)
        self.assertTrue(drunk(g, G))  # and is drunk again
        self.answer(4, **{G: [D, E]})
        run(g.night(4))
        self.day(g, 4)
        self.assertTrue(drunk(g, G))  # nights 2, 3 and 4 and their days
        run(g.night(5))
        self.assertFalse(drunk(g, G))
        g = self.game(self.CHARS)
        self.choose(1, A, character='Shabaloth')
        run(g.night(1))
        g.kill(g.g[A], 'demon')
        self.assertFalse(drunk(g, G))  # a dead Courtier's drunkenness ends

    def test_a_character_not_in_play_spends_it_and_a_dead_player_can_be_made_drunk(self):
        g = self.game(self.CHARS)
        self.choose(1, A, character='Po')
        run(g.night(1))
        self.assertTrue(g.g.spent_ability('Courtier'))
        self.assertFalse(any(s.kind == 'drunk' for s in g.g.states))
        g = self.game(self.CHARS)
        g.g[D].alive = False
        self.choose(1, A, character='Test Out')
        run(g.night(1))
        self.assertTrue(drunk(g, D))

    def test_a_courtier_who_chooses_themself_is_drunk(self):
        """A reading: the plain text (they are drunk), not a paradox that cancels itself."""
        g = self.game(self.CHARS)
        self.choose(1, A, character='Courtier')
        run(g.night(1))
        self.assertTrue(drunk(g, A))


class MinstrelTests(BMRTest):
    # Alex Minstrel, Blair Pacifist, Casey Town, Drew Town 2, Ellis Out, Frankie Godfather, Gray Devil's Advocate,
    # Harper Assassin, Indigo Po
    CHARS = ['Minstrel', 'Pacifist', TOWN, 'Test Town 2', 'Test Out', 'Godfather', "Devil's Advocate", 'Assassin',
             'Po']

    def test_a_minion_executed_makes_everyone_else_drunk_until_dusk_tomorrow(self):
        """Example: day 1 the Pacifist dies: that night players act as normal. Day 2 the Godfather is executed: that
        night everyone, the Demon too, is drunk, so nobody dies. Day 3 a Minion the drunk Devil's Advocate
        protected is executed and dies, and everyone is drunk again."""
        g = self.game(self.CHARS)
        g.execute(B)
        self.assertFalse(any(s.kind == 'drunk' for s in g.g.states))
        self.answer(2, **{G: [H], H: [], I: [C]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [C])
        self.day(g, 2)
        g.execute(F)
        self.assertEqual([p.name for p in g.g.players if g.g.is_drunk(p)], [B, C, D, E, F, G, H, I])  # the dead too
        self.answer(3, **{G: [H], H: [D], I: [D]})
        run(g.night(3))
        self.assertEqual(self.deaths(g, 3), [])  # the Demon and the Assassin are drunk
        self.day(g, 3)
        self.assertTrue(drunk(g, G))
        g.execute(H)  # the drunk Devil's Advocate's protection fails
        self.assertFalse(g.g[H].alive)
        run(g.night(4))
        self.day(g, 4)
        self.assertTrue(drunk(g, I))  # the second execution's drunkenness: through day 4
        run(g.night(5))
        self.assertFalse(drunk(g, I))
        self.assertFalse(drunk(g, A))

    def test_no_trigger_without_a_minion_dying_by_execution_by_a_working_minstrel(self):
        """Not on a night death, a Minion executed who survives, a dead Minion executed, or a drunk Minstrel."""
        g = self.game(self.CHARS)
        g.phase = 'night'
        g.kill(g.g[F], 'demon')
        g.phase = 'day'
        self.assertFalse(drunk(g, I))
        g.execute(F)  # already dead
        self.assertFalse(drunk(g, I))
        g.g.add(State('safe', G, against='execution'))
        g.execute(G)
        self.assertTrue(g.g[G].alive)
        self.assertFalse(drunk(g, I))
        g.g.add(State('poisoned', A))
        g.execute(H)
        self.assertFalse(drunk(g, I))

    def test_travellers_are_not_made_drunk_and_the_drunkenness_ends_with_the_minstrel(self):
        g = self.game(self.CHARS)
        g.g[E].traveller = True
        g.execute(F)
        self.assertFalse(drunk(g, E))
        self.assertTrue(drunk(g, I))
        g.kill(g.g[A], 'assassin')
        self.assertFalse(drunk(g, I))

    def test_a_drunk_zombuul_executed_dies_for_real(self):
        """Example: the Assassin dies by execution; the next day the Zombuul is executed and dies for the first time:
        good wins, because the Zombuul is drunk."""
        g = self.game(['Minstrel', TOWN, 'Test Town 2', 'Test Out', 'Test Town 3', 'Assassin', 'Zombuul'])
        g.execute(F)
        run(g.night(2))
        self.day(g, 2)
        g.execute(G)
        self.assertEqual(g.g.winner, 'good')

    def test_the_mastermind_executed_makes_the_assassin_drunk(self):
        """Example: the Mastermind dies by execution; that night the Assassin's kill fails."""
        g = self.game(['Minstrel', TOWN, 'Test Town 2', 'Test Out', 'Test Town 3', 'Test Town 4', 'Mastermind',
                       'Assassin', 'Po'])
        g.execute(G)
        self.answer(2, **{H: [B], I: [C]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])


class ExorcistTests(BMRTest):
    # Alex Exorcist, Blair Town, Casey Town 2, Drew Out, Ellis Town 3, Frankie Assassin, Gray the Demon
    def chars(self, demon):
        return ['Exorcist', TOWN, 'Test Town 2', 'Test Out', 'Test Town 3', 'Assassin', demon]

    def test_a_chosen_shabaloth_learns_who_the_exorcist_is_and_does_not_wake(self):
        """Example: the Exorcist chooses the Shabaloth, which does not kill tonight: nobody died."""
        g = self.game(self.chars('Shabaloth'))
        run(g.night(1))
        self.assertEqual(self.asked(A, 1), [])  # not on the first night
        self.answer(2, **{A: [G], F: [], G: [B, C]})
        run(g.night(2))
        self.assertEqual(self.asked(G, 2), [])
        self.assertNotIn(G, g.g.woke[2])  # being told is not waking for an ability (the Chambermaid)
        self.assertEqual(self.deaths(g, 2), [])
        told = [e['data']['text'] for e in g.events if e['kind'] == 'info' and e['to'] == [G]]
        self.assertEqual(told, [f'Night 2: the Exorcist chose you. {A} is the Exorcist, and you do not wake tonight.'])
        self.answer(3, **{A: [B], F: [], G: [B, C]})
        run(g.night(3))
        self.assertNotIn(G, self.asked(A, 3)[0].options)  # not the same player two nights running
        self.assertEqual(self.deaths(g, 3), [B, C])

    def test_a_chosen_pukkas_earlier_victim_still_dies(self):
        """Example: the Exorcist chooses the Pukka, which does not wake, but its previous victim dies."""
        g = self.game(self.chars('Pukka'))
        self.answer(1, **{G: [B]})
        run(g.night(1))
        self.answer(2, **{A: [G], F: [], G: [C]})
        run(g.night(2))
        self.assertEqual(self.asked(G, 2), [])
        self.assertEqual(self.deaths(g, 2), [B])
        self.assertFalse(g.g.is_poisoned(g.g[C]))

    def test_a_po_that_chose_no_one_keeps_its_charge_through_the_night_it_is_exorcised(self):
        """Example: the Po chooses no one; the next night the Exorcist chooses it; the next, the Exorcist chooses
        the Assassin, who can still attack, and the Po chooses three."""
        g = self.game(self.chars('Po'))
        self.answer(2, **{A: [B], F: [], G: []})
        run(g.night(2))
        self.answer(3, **{A: [G], F: []})
        run(g.night(3))
        self.assertEqual(self.asked(G, 3), [])
        self.answer(4, **{A: [F], F: [B], G: [C, D, E]})
        run(g.night(4))
        self.assertEqual(self.asked(G, 4)[0].n_targets, 3)
        self.assertEqual(self.deaths(g, 4), [B, C, D, E])

    def test_a_zombuul_that_seems_dead_can_be_exorcised(self):
        """Tip: against a Zombuul, choose dead players: no death after a day without one means a Zombuul."""
        g = self.game(self.chars('Zombuul'))
        g.g[G].seems_dead = True
        g.g.spend('Zombuul')
        self.answer(2, **{A: [G], F: [], G: [B]})
        run(g.night(2))
        self.assertIn(G, self.asked(A, 2)[0].options)
        self.assertEqual(self.asked(G, 2), [])
        self.assertEqual(self.deaths(g, 2), [])

    def test_choosing_another_player_or_a_drunk_exorcist_lets_the_demon_attack(self):
        g = self.game(self.chars('Po'))
        self.answer(2, **{A: [F], F: [], G: [B]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [B])
        g = self.game(self.chars('Po'))
        g.g.add(State('drunk', A, until=None))
        self.answer(2, **{A: [G], F: [], G: [B]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [B])
        self.assertFalse([e for e in g.events if e['kind'] == 'info' and e['to'] == [G]])


class TeaLadyTests(BMRTest):
    # Alex Out (the Goon), Blair Tea Lady, Casey Mastermind, Drew Town (the Courtier), Ellis Town 2, Frankie Town 3,
    # Gray Po
    CHARS = ['Test Out', 'Tea Lady', 'Mastermind', TOWN, 'Test Town 2', 'Test Town 3', 'Po']

    def test_the_protection_follows_her_alive_neighbours_and_their_alignment(self):
        """Example: the Tea Lady neighbours the Mastermind and the good Goon. The Mastermind is executed; now her
        neighbours are the Goon and the Courtier, and the Courtier survives the Demon. The Goon turns evil, and the
        Demon kills the Courtier."""
        g = self.game(self.CHARS)
        self.assertFalse(g.g.safe(g.g[A], 'demon'))  # an evil neighbour: no protection
        g.execute(C)
        self.assertEqual([q.name for q in g.g.neighbours(g.g[B])], [A, D])
        self.answer(2, **{G: [D]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])
        g.g[A].alignment = 'evil'
        self.answer(3, **{G: [D]})
        run(g.night(3))
        self.assertEqual(self.deaths(g, 3), [D])

    def test_protected_neighbours_survive_execution_and_any_kill_but_the_assassins(self):
        g = self.game([TOWN, 'Tea Lady', 'Test Town 2', 'Test Out', 'Test Town 3', 'Assassin', 'Po'])
        g.execute(A)
        self.assertTrue(g.g[A].alive)
        g.phase = 'night'
        self.assertIsNone(g.attempt_kill(g.g[C], 'godfather'))
        self.assertIsNone(g.attempt_kill(g.g[C], 'gossip'))
        self.assertEqual(g.attempt_kill(g.g[B], 'demon', g.g[G]), g.g[B])  # the Tea Lady herself is not protected
        g = self.game([TOWN, 'Tea Lady', 'Test Town 2', 'Test Out', 'Test Town 3', 'Assassin', 'Po'])
        self.answer(2, **{F: [C], G: [A]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [C])  # the Assassin kills through; the Po does not

    def test_dead_neighbours_are_skipped_and_a_drunk_tea_lady_protects_nobody(self):
        g = self.game([TOWN, 'Tea Lady', 'Test Out', 'Test Town 2', 'Test Town 3', 'Assassin', 'Po'])
        g.g[C].alive = False
        self.assertTrue(g.g.safe(g.g[D], 'execution'))
        g.g.add(State('drunk', B))
        self.assertFalse(g.g.safe(g.g[D], 'execution'))


class PacifistTests(BMRTest):
    # Alex Pacifist, Blair Innkeeper, Casey Professor, Drew Town, Ellis Out (the Lunatic), Frankie Devil's Advocate,
    # Gray Po
    CHARS = ['Pacifist', 'Innkeeper', 'Professor', TOWN, 'Test Out', "Devil's Advocate", 'Po']

    def test_an_executed_good_player_may_survive_and_the_execution_still_counts(self):
        """Example: the Innkeeper is executed but remains alive because of the Pacifist."""
        g = self.game(self.CHARS, forced={'Pacifist': {'yes': True}})
        run(g.execution(B))
        self.assertTrue(g.g[B].alive)
        self.assertEqual(g.g.executions, [{'player': B, 'day': 1, 'died': False}])
        ev = [e for e in g.events if e['kind'] == 'execution'][-1]
        self.assertEqual(render(ev, D), f'{B} is executed, but does not die.')
        self.assertEqual(g.g.notes['Pacifist saves'], 1)
        self.assertEqual(choices(g, 'Pacifist:')[0]['id'], 'Pacifist:' + B)

    def test_it_saves_a_good_outsider_and_itself_but_not_while_drunk_or_an_evil_player(self):
        """Example: evil is winning; the Lunatic is executed but remains alive. The next day the Professor is
        executed and dies, because the Pacifist is drunk. Later the Pacifist is executed but remains alive."""
        g = self.game(self.CHARS, forced={'Pacifist': {'yes': True}})
        run(g.execution(E))
        self.assertTrue(g.g[E].alive)
        self.day(g, 2)
        g.g.add(State('drunk', A))
        run(g.execution(C))
        self.assertFalse(g.g[C].alive)
        self.assertEqual(len(choices(g, 'Pacifist:')), 1)  # nothing to decide while drunk
        g.g.states = []
        self.day(g, 3)
        run(g.execution(A))
        self.assertTrue(g.g[A].alive)
        self.day(g, 4)
        run(g.execution(F))
        self.assertFalse(g.g[F].alive)
        self.assertEqual(len(choices(g, 'Pacifist:')), 2)

    def test_the_save_needs_the_storytellers_yes_and_is_not_asked_when_another_ability_saves(self):
        g = self.game(self.CHARS, forced={'Pacifist': {'yes': False}})
        run(g.execution(D))
        self.assertFalse(g.g[D].alive)
        g = self.game(['Pacifist', 'Fool', 'Tea Lady', TOWN, 'Test Out', "Devil's Advocate", 'Po'],
                      forced={'Pacifist': {'yes': True}})
        run(g.execution(B))
        self.assertTrue(g.g[B].alive)
        self.assertEqual(choices(g, 'Pacifist:'), [])  # the Tea Lady saved them: nothing to decide
        g.g[C].alive = False
        run(g.execution(B))
        self.assertTrue(g.g[B].alive)
        self.assertFalse(g.g.spent_ability('Fool'))  # the Pacifist saved the Fool, who keeps their ability

    def test_the_scripted_storyteller_saves_about_once_a_game_more_at_the_climax_and_sometimes_never(self):
        """How to Run: once per game is usually about right; on rare occasions never (the example: good is winning,
        and after seven days and five good executions the Pacifist has saved nobody)."""
        from clocktower.bmr import pacifist_choice
        g = self.game(self.CHARS)
        r = random.Random(8)

        def rate():
            return sum(pacifist_choice(g.g, g.g[A], g.g[D]).options(r)['yes'] for _ in range(2000)) / 2000
        self.assertAlmostEqual(rate(), POLICY['pacifist_save'], delta=0.03)
        g.g[E].alive = g.g[F].alive = False
        self.assertAlmostEqual(rate(), POLICY['pacifist_late'], delta=0.04)
        g.g.notes['Pacifist saves'] = 1
        self.assertAlmostEqual(rate(), POLICY['pacifist_again'], delta=0.02)
        g.g.notes['Pacifist never'] = True
        self.assertEqual(rate(), 0)
        never = []
        for seed in range(60):
            names = NAMES[:7]
            game = Game({n: Seat() for n in names}, ScriptedStoryteller(random.Random(seed)), names=names, seed=seed,
                        characters=['Pacifist', TOWN, 'Test Town 2', 'Test Town 3', 'Test Town 4', 'Assassin', 'Po'],
                        script=self.script, probes=False)
            run(game.setup())
            never.append(game.g.notes['Pacifist never'])
        self.assertTrue(0 < sum(never) < 20)  # decided once per game, rarely


class FoolTests(BMRTest):
    CHARS = ['Fool', TOWN, 'Test Town 2', 'Test Out', 'Test Town 3', 'Assassin', 'Po']

    def test_the_first_death_by_execution_is_survived_and_the_second_is_not(self):
        """Example: on the first day the Fool is executed but remains alive; on the fourth day, again: they die."""
        g = self.game(self.CHARS)
        g.execute(A)
        self.assertTrue(g.g[A].alive)
        self.assertTrue(g.g.spent_ability('Fool'))
        ev = [e for e in g.events if e['kind'] == 'execution'][-1]
        self.assertEqual(render(ev, B), f'{A} is executed, but does not die.')
        self.day(g, 4)
        g.execute(A)
        self.assertFalse(g.g[A].alive)

    def test_a_demon_attack_is_survived_then_an_execution_kills(self):
        """Example: the Demon attacks the Fool, who remains alive; nobody dies; the next day they are executed and
        die."""
        g = self.game(self.CHARS)
        self.answer(2, **{F: [], G: [A]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])
        g.execute(A)
        self.assertFalse(g.g[A].alive)

    def test_other_protection_comes_first_so_the_fool_keeps_the_ability(self):
        """Example: the Demon attacks the Fool, protected by the Tea Lady: alive, ability kept. After she dies, the
        Innkeeper protects them: the same. After the Innkeeper dies, the Fool survives by their own ability; next
        time they die."""
        g = self.game(['Fool', 'Tea Lady', TOWN, 'Innkeeper', 'Test Town 2', 'Test Town 3', 'Assassin', 'Po'],
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

    def test_the_assassin_kills_the_fool_and_the_zombuul_does_not(self):
        """Example: the Assassin kills the Fool, who dies and stays dead though they still have their ability. A
        Zombuul's attack is survived."""
        g = self.game(self.CHARS)
        self.answer(2, **{F: [A], G: [B]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A, B])
        self.assertFalse(g.g.spent_ability('Fool'))
        g = self.game(['Fool', TOWN, 'Test Town 2', 'Test Out', 'Test Town 3', 'Assassin', 'Zombuul'])
        self.answer(2, **{F: [], G: [A]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])
        self.assertTrue(g.g[A].alive and g.g.spent_ability('Fool'))

    def test_a_drunk_or_poisoned_fool_dies(self):
        g = self.game(self.CHARS)
        g.g.add(State('poisoned', A))
        g.execute(A)
        self.assertFalse(g.g[A].alive)


class GamblerTests(BMRTest):
    # Alex Gambler, Blair Minstrel, Casey Pacifist, Drew Town, Ellis Out, Frankie Devil's Advocate, Gray Po
    CHARS = ['Gambler', 'Minstrel', 'Pacifist', TOWN, 'Test Out', "Devil's Advocate", 'Po']

    def test_a_right_guess_keeps_the_gambler_alive_but_the_demon_may_still_kill_them(self):
        """Example: the Gambler guesses the Minstrel correctly and lives, but the Demon kills them anyway."""
        g = self.game(self.CHARS)
        run(g.night(1))
        self.assertEqual(self.asked(A, 1), [])  # not on the first night
        self.choose(2, A, [B], 'Minstrel')
        self.answer(2, **{F: [D], G: [A]})
        run(g.night(2))
        req = self.asked(A, 2)[0]
        self.assertIn('Minstrel', req.characters)
        self.assertEqual(self.deaths(g, 2), [A])
        self.assertEqual([d['cause'] for d in g.g.death_log], ['demon'])
        self.assertFalse([e for e in g.events if e['kind'] == 'info' and e['to'] == [A]])  # no feedback

    def test_a_wrong_guess_kills_the_gambler(self):
        """Example: the Devil's Advocate bluffs as the Pacifist; the Gambler guesses them as the Pacifist and dies."""
        g = self.game(self.CHARS)
        self.choose(2, A, [F], 'Pacifist')
        self.answer(2, **{F: [D], G: [C]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A, C])
        self.assertEqual(g.g.death_log[0]['cause'], 'gambler')

    def test_any_player_even_dead_or_themself_and_a_drunk_or_protected_gambler_lives(self):
        g = self.game(self.CHARS)
        g.g[D].alive = False
        self.choose(2, A, [A], 'Gambler')
        self.answer(2, **{F: [B], G: [B]})
        run(g.night(2))
        self.assertEqual(set(self.asked(A, 2)[0].options), set(NAMES[:7]))
        self.assertTrue(g.g[A].alive)
        g = self.game(self.CHARS)
        g.g.add(State('drunk', A, until=None))
        self.choose(2, A, [B], 'Po')
        run(g.night(2))
        self.assertTrue(g.g[A].alive)
        g = self.game(self.CHARS)
        g.g.add(State('safe', A, against='any', until=None))  # the Innkeeper's: a Townsfolk's ability can't kill
        self.choose(2, A, [B], 'Po')
        run(g.night(2))
        self.assertTrue(g.g[A].alive)


class ProfessorTests(BMRTest):
    # Alex Professor, Blair Courtier, Casey Minstrel, Drew Fool, Ellis Out, Frankie Grandmother, Gray Town,
    # Harper Shabaloth
    CHARS = ['Professor', 'Courtier', 'Minstrel', 'Fool', 'Test Out', 'Test Grandmother', TOWN, 'Shabaloth']

    def test_choosing_a_dead_player_who_is_not_a_townsfolk_does_nothing_and_spends_it(self):
        """Example: the Professor chooses a dead player claiming to be the Tea Lady, actually the Lunatic: nobody is
        resurrected."""
        g = self.game(self.CHARS, forced={'Shabaloth': {'players': []}})
        g.g[E].alive = False
        self.answer(2, **{A: [E], H: [G, C]})
        run(g.night(2))
        req = self.asked(A, 2)[0]
        self.assertEqual((req.options, req.min_targets), ([C, E, G], 0))  # the dead only, tonight's too
        self.assertFalse(g.g[E].alive)
        self.assertTrue(g.g.spent_ability('Professor'))
        run(g.night(3))
        self.assertEqual(self.asked(A, 3), [])

    def test_a_dead_townsfolk_comes_back_with_their_ability_and_a_start_knowing_one_wakes_now(self):
        """Example: the Professor resurrects the Grandmother, who learns a good player's character again; at dawn all
        learn she is alive, not why. A revived player regains a spent once-per-game ability."""
        g = self.game(self.CHARS, forced={'Shabaloth': {'players': []}})
        g.g[F].alive = g.g[B].alive = False
        g.g.spend('Courtier')
        self.answer(2, **{A: [F], H: [D, E]})
        run(g.night(2))
        self.assertTrue(g.g[F].alive)
        dawn = [e for e in g.events if e['kind'] == 'dawn'][-1]
        self.assertEqual(dawn['data']['revived'], [F])
        self.assertEqual(render(dawn, G).count('Alive again: Frankie.'), 1)
        told = [e['data']['text'] for e in g.events if e['kind'] == 'info' and e['to'] == [F]]
        self.assertEqual(told, ['You learn your Grandchild again.'])
        g = self.game(self.CHARS, forced={'Shabaloth': {'players': []}})
        g.g[B].alive = False
        g.g.spend('Courtier')
        self.answer(2, **{A: [B], H: [D, E]})
        run(g.night(2))
        self.assertEqual(self.asked(B, 2), [])  # the Courtier's step came before the Professor's
        self.assertFalse(g.g.spent_ability('Courtier'))
        self.choose(3, B)
        run(g.night(3))
        self.assertEqual(len(self.asked(B, 3)), 1)

    def test_a_drunk_professor_wastes_it_and_a_regurgitated_player_is_not_an_option(self):
        """Example: the drunk Professor tries the Minstrel, regurgitated by the Shabaloth and alive: the Storyteller
        shakes their head; the Professor chooses the dead Fool, and nothing happens."""
        g = self.game(self.CHARS, forced={'Shabaloth': {'players': [C]}})
        self.answer(2, **{A: [], H: [C, D]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [C])  # the Fool survives the attack: their ability
        g.kill(g.g[D], 'execution')  # and dies for real at execution
        g.g.add(State('drunk', A, until=None))
        self.answer(3, **{A: [D], H: [E, G]})
        run(g.night(3))
        self.assertTrue(g.g[C].alive)
        self.assertNotIn(C, self.asked(A, 3)[0].options)
        self.assertFalse(g.g[D].alive)
        self.assertTrue(g.g.spent_ability('Professor'))

    def test_choosing_no_one_keeps_the_ability(self):
        g = self.game(self.CHARS)
        g.g[G].alive = False
        self.answer(2, **{A: [], H: [D, E]})
        run(g.night(2))
        self.assertFalse(g.g.spent_ability('Professor'))
        self.assertFalse(g.g[G].alive)


class Batch2SmokeTests(BMRTest):
    def test_whole_games_with_these_townsfolk_run_to_the_end(self):
        from clocktower.agents import RandomSeat
        towns = ['Sailor', 'Innkeeper', 'Courtier', 'Minstrel', 'Exorcist', 'Tea Lady', 'Pacifist', 'Fool', 'Gambler',
                 'Professor']
        ended = []
        for seed in range(16):
            r = random.Random(100 + seed)
            chars = r.sample(towns, 7) + r.sample(["Devil's Advocate", 'Assassin', 'Mastermind'], 2)
            chars.append(['Zombuul', 'Pukka', 'Shabaloth', 'Po'][seed % 4])
            r.shuffle(chars)
            names = ALL_NAMES[:len(chars)]
            seats = {n: RandomSeat(n, random.Random(seed * 17 + i), names) for i, n in enumerate(names)}
            g = Game(seats, Forced(), names=names, seed=seed, characters=chars, script=self.script, probes=False,
                     private_beats=1, public_beats=1, max_days=12)
            result = run(g.run())
            ended.append(result['winner'])
            self.assertTrue(result['winner'] or result['stopped'].startswith('stopped after'), result['reason'])
        self.assertGreater(sum(w is not None for w in ended), 10, ended)


# ---- Batch 3: the information Townsfolk, the Gossip, and the Outsiders -----------------------------------------

def told(g, name):
    return [e['data']['text'] for e in g.events if e['kind'] == 'info' and e['to'] == [name]]


class GrandmotherTests(BMRTest):
    # Alex Grandmother, Blair Professor, Casey Gambler, Drew Town, Ellis Town 2, Frankie Assassin, Gray Zombuul
    CHARS = ['Grandmother', 'Professor', 'Gambler', TOWN, 'Test Town 2', 'Assassin', 'Zombuul']

    def test_she_starts_knowing_a_good_player_and_their_character(self):
        """Example: during the first night the Grandmother learns that Julian, their Grandchild, is the Professor."""
        g = self.dealt(self.CHARS, forced={'Grandchild': {'players': [B]}})
        run(g.night(1))
        self.assertEqual(told(g, A), [f'Night 1 — Grandmother: your Grandchild is {B}, the Professor.'])
        self.assertIn(A, g.g.woke[1])
        self.assertIn(f'{A} (Grandmother) was shown: your Grandchild is {B}, the Professor.', g.g.grimoire_text())
        from clocktower.bmr import grandchild_choice
        options = {v['players'][0] for v in grandchild_choice(g.g, g.g[A]).values}
        self.assertEqual(options, {B, C, D, E})  # any good player but herself

    def test_the_scripted_grandchild_is_usually_a_townsfolk_and_may_be_an_outsider(self):
        from clocktower.bmr import grandchild_choice
        g = self.game(['Grandmother', 'Goon', 'Lunatic', TOWN, 'Test Town 2', 'Assassin', 'Zombuul'])
        r = random.Random(5)
        picks = [grandchild_choice(g.g, g.g[A]).options(r)['players'][0] for _ in range(2000)]
        self.assertAlmostEqual((picks.count(D) + picks.count(E)) / 2000, POLICY['grandchild_townsfolk'], delta=0.04)
        self.assertEqual(set(picks), {B, C, D, E})  # the Lunatic and the Goon are good players too

    def test_if_the_demon_kills_the_grandchild_she_dies_too(self):
        """Example: three nights later, Julian is killed by the Demon, so the Grandmother dies too."""
        g = self.game(self.CHARS)
        g.g.notes['Grandchild'] = B
        self.day(g, 3)
        self.answer(4, **{B: [], C: [D], F: [], G: [B]})
        self.choose(4, C, [D], TOWN)
        run(g.night(4))
        self.assertEqual(self.deaths(g, 4), [A, B])  # in seat order, never why
        self.assertEqual([(d['player'], d['cause']) for d in g.g.death_log], [(B, 'demon'), (A, 'grandmother')])

    def test_the_grandchild_dying_any_other_way_does_not_kill_her(self):
        """Example: Lewis, the Grandchild, is the Gambler; he gambles and dies: the Grandmother remains alive. Nor
        by execution, or the Assassin's kill."""
        g = self.game(self.CHARS)
        g.g.notes['Grandchild'] = C
        self.choose(2, C, [D], 'Po')
        self.answer(2, **{B: [], F: [], G: [E]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [C, E])
        self.assertTrue(g.g[A].alive)
        for cause in ('execution', 'assassin', 'godfather', 'gossip', 'moonchild', 'tinker'):
            g = self.game(self.CHARS)
            g.g.notes['Grandchild'] = D
            g.kill(g.g[D], cause)
            self.assertTrue(g.g[A].alive, cause)

    def test_a_drunk_grandmother_survives_her_grandchilds_death(self):
        """Example: Sarah, the Grandchild, is the Tinker; she is killed by the Demon, but the Grandmother is drunk
        because of the Sailor, so the Grandmother remains alive."""
        g = self.game(['Grandmother', 'Sailor', 'Tinker', TOWN, 'Test Town 2', 'Assassin', 'Zombuul'],
                      forced={'Sailor': {'players': [A]}, 'Tinker': {'yes': False}})
        g.g.notes['Grandchild'] = C
        self.answer(2, **{B: [A], F: [], G: [C]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [C])
        self.assertTrue(g.g[A].alive)

    def test_she_dies_with_a_grandchild_the_pukka_poisoned_or_the_shabaloth_ate(self):
        g = self.game(['Grandmother', TOWN, 'Test Town 2', 'Test Town 3', 'Test Town 4', 'Assassin', 'Pukka'])
        g.g.notes['Grandchild'] = B
        self.answer(1, **{G: [B]})
        run(g.night(1))
        self.answer(2, **{F: [], G: [C]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A, B])  # the poison's death is the Demon's kill
        g = self.game(['Grandmother', TOWN, 'Test Town 2', 'Test Town 3', 'Test Town 4', 'Assassin', 'Shabaloth'])
        g.g.notes['Grandchild'] = D
        self.answer(2, **{F: [], G: [C, D]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A, C, D])

    def test_a_po_that_attacks_the_goon_kills_neither_her_nor_later_picks(self):
        """Example: the Po attacks the Moonchild, then the Goon, then the Grandmother. Only the Moonchild dies,
        because the Po became drunk when they attacked the Goon."""
        g = self.game(['Grandmother', 'Moonchild', 'Goon', TOWN, 'Test Town 2', 'Assassin', 'Po'])
        g.g.notes['Grandchild'] = E
        g.g.last_choices[G] = []  # last time the Po chose no one
        self.answer(2, **{F: [], G: [B, C, A]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [B])
        self.assertTrue(g.g[C].evil and drunk(g, G))

    def test_an_impaired_grandmother_may_be_shown_a_false_pair(self):
        from clocktower.bmr import grandmother_choice
        g = self.game(self.CHARS)
        g.g.add(State('poisoned', A, until=None))
        choice = grandmother_choice(g.g, g.g[A], B)
        self.assertEqual(len(choice.values), 6 * len(self.script.good))  # anyone, as any good character
        r = random.Random(2)
        false = 0
        for _ in range(500):
            v = choice.options(r)
            self.assertTrue(choice.legal(v))
            if not choice.truth(v):
                false += 1
                x, c = v['players'][0], v['character']
                self.assertNotEqual(c, 'Grandmother')  # never her own character
                self.assertNotEqual(c, g.g[x].character)  # false: an evil player, or a good one as someone else
        self.assertAlmostEqual(false / 500, POLICY['poisoned_false'], delta=0.06)
        g = self.game(self.CHARS)
        g.g.add(State('drunk', A, until=None))  # drunk (the Sailor's, the Courtier's) as much as poisoned
        self.assertTrue(any(not choice.truth(grandmother_choice(g.g, g.g[A], B).options(r)) for _ in range(20)))

    def test_resurrected_by_the_professor_she_learns_her_grandchild_again(self):
        """Example: the Professor resurrects the Grandmother, who learns a good player's character."""
        g = self.game(['Professor', 'Grandmother', TOWN, 'Test Town 2', 'Test Town 3', 'Assassin', 'Shabaloth'],
                      forced={'Shabaloth': {'players': []}})
        g.g.notes['Grandchild'] = C
        g.g[B].alive = False
        self.answer(2, **{A: [B], F: [], G: [D, E]})
        run(g.night(2))
        self.assertTrue(g.g[B].alive)
        self.assertEqual(told(g, B), [f'Night 2 — Grandmother: your Grandchild is {C}, the {TOWN}.'])


class ChambermaidTests(BMRTest):
    def test_it_counts_players_who_woke_for_their_ability_and_not_a_demon_the_exorcist_chose(self):
        """Example: the Chambermaid chooses the Exorcist and the Innkeeper and learns a 2. The next night the
        Exorcist chooses the Shabaloth; the Chambermaid chooses the Shabaloth and the Fool: a 0."""
        # Alex Chambermaid, Blair Exorcist, Casey Innkeeper, Drew Fool, Ellis Town, Frankie Assassin, Gray Shabaloth
        g = self.game(['Chambermaid', 'Exorcist', 'Innkeeper', 'Fool', TOWN, 'Assassin', 'Shabaloth'],
                      forced={'Shabaloth': {'players': []}})
        self.answer(2, **{A: [B, C], B: [D], C: [D, E], F: [], G: [D, E]})
        run(g.night(2))
        self.assertEqual(told(g, A), [f'Night 2 — Chambermaid: you chose {B} and {C}: 2 of them woke tonight to '
                                      'use their ability.'])
        self.answer(3, **{A: [G, D], B: [G], C: [D, E], F: []})
        run(g.night(3))
        self.assertEqual(told(g, A)[-1], f'Night 3 — Chambermaid: you chose {G} and {D}: 0 of them woke tonight to '
                                         'use their ability.')

    def test_the_assassin_counts_when_woken_even_declining_and_the_gossip_never_wakes(self):
        """Example: the first night, the Assassin and the Moonchild: a 0. The next night the Assassin wakes but does
        not use their ability; the Gossip's ability was used, but the Gossip does not wake: a 1."""
        g = self.game(['Chambermaid', 'Gossip', TOWN, 'Moonchild', 'Test Town 2', 'Assassin', 'Zombuul'],
                      forced={'Gossip kill': {'players': [E]}})
        self.answer(1, **{A: [F, D]})
        run(g.night(1))
        self.assertIn('0 of them', told(g, A)[-1])
        g.public_abilities([B], {B: {'ability': {'character': 'Gossip', 'text': 'Frankie is evil.'}}})
        run(g.run_pending())
        self.answer(2, **{A: [F, B], F: [], G: [C]})
        run(g.night(2))
        self.assertIn('1 of them', told(g, A)[-1])
        self.assertEqual(self.deaths(g, 2), [C, E])

    def test_a_drunk_player_who_woke_counts(self):
        """Players that woke tonight due to their ability but are drunk or poisoned still count."""
        g = self.game(['Chambermaid', 'Exorcist', 'Sailor', TOWN, 'Test Town 2', 'Assassin', 'Zombuul'],
                      forced={'Sailor': {'players': [B]}})
        self.answer(2, **{A: [B, D], B: [G], C: [B], F: [], G: [E]})
        run(g.night(2))
        self.assertTrue(drunk(g, B))
        self.assertIn('1 of them', told(g, A)[-1])

    def test_a_chambermaid_who_chooses_the_goon_is_drunk_and_may_learn_a_false_count(self):
        """Example: the Chambermaid chooses the Goon and the Minstrel, and learns a 1 because the Chambermaid is
        drunk."""
        g = self.game(['Chambermaid', 'Grandmother', 'Minstrel', 'Goon', TOWN, 'Godfather', 'Pukka'],
                      forced={'Chambermaid': {'number': 1}})
        self.answer(2, **{A: [D, C], G: [E]})
        run(g.night(2))
        self.assertTrue(drunk(g, A))
        self.assertIn('1 of them', told(g, A)[-1])  # a legal value only for an impaired Chambermaid
        from clocktower.bmr import chambermaid_choice
        self.assertEqual(chambermaid_choice(g.g, g.g[A], [D, C], 2).truth({'number': 0}), True)
        g = self.game(['Chambermaid', 'Grandmother', 'Minstrel', 'Goon', TOWN, 'Godfather', 'Pukka'])
        g.g.add(State('poisoned', A, until=None))
        choice = chambermaid_choice(g.g, g.g[A], [D, C], 2)
        r = random.Random(3)
        false = sum(choice.options(r)['number'] != 0 for _ in range(500))
        self.assertAlmostEqual(false / 500, POLICY['poisoned_false'], delta=0.06)

    def test_it_chooses_two_alive_players_not_itself_and_sleeps_without_two(self):
        g = self.game(['Chambermaid', TOWN, 'Test Town 2', 'Test Town 3', 'Test Town 4', 'Assassin', 'Zombuul'])
        g.g[C].alive = False
        self.answer(1, **{A: [B, D]})
        run(g.night(1))
        req = self.asked(A, 1)[0]
        self.assertEqual((req.options, req.n_targets, req.min_targets), ([B, D, E, F, G], 2, 2))
        for name in (B, D, E, F):
            g.g[name].alive = False
        run(g.night(2))
        self.assertEqual(self.asked(A, 2), [])  # only one other player alive: not woken


class GossipTests(BMRTest):
    # Alex Gossip, Blair Town, Casey Lunatic, Drew Goon, Ellis Tea Lady (an evil neighbour), Frankie Godfather, Gray Po
    CHARS = ['Gossip', TOWN, 'Lunatic', 'Goon', 'Tea Lady', 'Godfather', 'Po']

    def say(self, g, name, text, character='Gossip'):
        g.public_abilities([name], {name: {'ability': {'character': character, 'text': text}}})
        run(g.run_pending())

    def test_statements_of_simple_forms_are_checked_against_the_grimoire(self):
        from clocktower.bmr import gossip_truth
        g = self.game(self.CHARS)
        g.g[C].shown = 'Po'
        cases = {'Gray is the Demon.': True, 'Gray is the Po': True, 'Casey is the Po.': False,
                 'Casey is the Lunatic': True, 'casey is an Outsider': True, 'Frankie is evil': True,
                 'Frankie is not evil.': False, "Frankie isn't a Minion": False, 'The Demon is Gray': True,
                 'The Demon is not Casey': True, "I'm good": True, 'I am the Gossip': None,
                 'I am the Gossip. My public statement is: the Godfather is in play.': True,
                 'the Assassin is in play': False, 'There is no Assassin in play.': True,
                 'The Demon is wearing a hat.': None, 'Blair and Casey are good.': None, 'Drew is evil': False,
                 'Mastermind is not in play': True, '': None}
        for text, truth in cases.items():
            self.assertEqual(gossip_truth(g.g, g.g[A], text), truth, text)
        g.g[D].alignment = 'evil'  # a Goon that turned
        self.assertTrue(gossip_truth(g.g, g.g[A], 'Drew is evil'))

    def test_a_statement_the_storyteller_cannot_judge_does_not_kill(self):
        """Example: "I am the Gossip. My public statement is: The Demon is wearing a hat." The Demon is not wearing a
        hat: that night nobody dies due to the Gossip's ability."""
        g = self.game(self.CHARS)
        self.say(g, A, 'I am the Gossip. My public statement is: The Demon is wearing a hat.')
        ev = [e for e in g.events if e['kind'] == 'ability'][-1]
        self.assertEqual(render(ev, B), f'{A} claims the Gossip\'s ability: "I am the Gossip. My public statement '
                                        'is: The Demon is wearing a hat."')
        self.assertEqual(choices(g, 'Gossip:')[0]['value'], {'yes': False})  # the scripted Storyteller can't read it
        self.answer(2, **{G: []})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])
        from clocktower.bmr import statement_choice
        self.assertEqual([v['yes'] for v in statement_choice(g.g, g.g[A], 'x').values], [True, False, None])

    def test_a_judge_may_rule_a_statement_true(self):
        g = self.game(self.CHARS, forced={'Gossip:': {'yes': True}, 'Gossip kill': {'players': [E]}})
        self.say(g, A, 'Both my neighbours are good.')
        self.answer(2, **{G: []})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [E])

    def test_a_true_statement_made_drunk_kills_if_the_gossip_is_sober_tonight(self):
        """Example: the drunk Gossip makes a true statement; at dusk the Gossip becomes sober; that night the
        Chambermaid dies (the Storyteller's choice)."""
        g = self.game(self.CHARS, forced={'Gossip kill': {'players': [E]}})
        g.g.add(State('drunk', A, until='night'))
        self.say(g, A, 'Frankie is evil.')
        self.answer(2, **{G: []})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [E])
        self.assertEqual(g.g.death_log[0]['cause'], 'gossip')
        g = self.game(self.CHARS, forced={'Gossip kill': {'players': [E]}})
        self.say(g, A, 'Frankie is evil.')
        g.g.add(State('drunk', A, until=None))  # drunk tonight: no death
        self.answer(2, **{G: []})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])

    def test_a_gossip_the_demon_kills_tonight_kills_no_one(self):
        """Example: the Gossip makes a true statement; that night the Gossip is killed by the Demon; they lose their
        ability, so their statement does not kill anyone tonight."""
        g = self.game(self.CHARS, forced={'Gossip kill': {'players': [E]}})
        self.say(g, A, 'Gray is the Demon.')
        self.answer(2, **{G: [A]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A])

    def test_only_the_living_gossips_first_statement_each_day_counts(self):
        g = self.game(self.CHARS, forced={'Gossip kill': {'players': [E]}})
        self.say(g, B, 'Frankie is evil.')  # a bluff: announced, does nothing
        self.say(g, A, 'Frankie is good.')
        self.say(g, A, 'Frankie is evil.')  # a second statement today doesn't count
        self.assertEqual(len([e for e in g.events if e['kind'] == 'ability']), 3)
        self.answer(2, **{G: []})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])
        self.day(g, 2)
        self.say(g, A, 'Frankie is evil.')
        self.answer(3, **{G: [B, C, D]})
        run(g.night(3))
        self.assertIn(E, self.deaths(g, 3))
        g = self.game(self.CHARS, forced={'Gossip kill': {'players': [E]}})
        g.g[A].alive = False
        self.say(g, A, 'Frankie is evil.')  # the dead have no ability
        self.answer(2, **{G: []})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])

    def test_the_scripted_victim_is_one_who_will_die_never_the_demon_and_none_that_ends_the_game(self):
        """How to Run: choose a character that will actually die, not one protected (the Fool, the Tea Lady's)."""
        from clocktower.bmr import gossip_victim_choice
        g = self.game(['Gossip', 'Tea Lady', TOWN, 'Fool', 'Test Town 2', 'Godfather', 'Po'])
        r = random.Random(6)
        picks = [gossip_victim_choice(g.g, g.g[A]).options(r)['players'][0] for _ in range(1000)]
        self.assertEqual(set(picks), {B, E, F})  # not the Tea Lady's good neighbours, nor the Fool, nor the Po
        self.assertAlmostEqual(picks.count(F) / 1000, POLICY['gossip_victim_evil'], delta=0.04)
        self.assertEqual(len(gossip_victim_choice(g.g, g.g[A]).values), 7)  # any living player is legal
        for name in (A, C, E, F):
            g.g[name].alive = False
        picks = {gossip_victim_choice(g.g, g.g[A]).options(r)['players'][0] for _ in range(100)}
        self.assertEqual(picks, {D})  # three alive: a death would end the game, so one who won't die (the Fool)

    def test_a_self_drunk_sailor_dies_to_the_gossip(self):
        """Sailor example: the Gossip's statement was true; the Sailor made themself drunk; the Sailor dies."""
        g = self.game(['Gossip', 'Sailor', TOWN, 'Test Town 2', 'Test Town 3', 'Godfather', 'Po'],
                      forced={'Gossip kill': {'players': [B]}})
        self.say(g, A, 'Gray is the Po.')
        self.answer(2, **{B: [B], G: [C]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [B, C])


class GoonTests(BMRTest):
    def test_the_courtier_choosing_the_goon_is_drunk_and_the_goon_turns_good(self):
        """Example: the Courtier chooses the Goon. The Goon turns good, and the Courtier becomes drunk."""
        g = self.game(['Courtier', 'Goon', TOWN, 'Test Town 2', 'Test Town 3', 'Assassin', 'Shabaloth'])
        g.g[B].alignment = 'evil'
        self.choose(1, A, character='Goon')
        run(g.night(1))
        self.assertTrue(drunk(g, A) and not drunk(g, B))
        self.assertFalse(g.g[B].evil)
        self.assertEqual(told(g, B), ['Night 1 — Goon: you are now good.'])
        self.assertTrue(g.g.spent_ability('Courtier'))

    def test_a_shabaloth_choosing_the_goon_first_kills_no_one_and_second_kills_the_first(self):
        """Example: the Shabaloth attacks the Goon, then the Gossip: neither dies, and the Goon turns evil. The next
        night it attacks the Gambler, then the Goon: the Gambler dies, then the Shabaloth becomes drunk again; the
        Goon is still alive and still evil."""
        g = self.game(['Goon', 'Gossip', 'Gambler', TOWN, 'Test Town 2', 'Assassin', 'Shabaloth'],
                      forced={'Shabaloth': {'players': []}})
        self.choose(2, C, [D], TOWN)
        self.answer(2, **{F: [], G: [A, B]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])
        self.assertTrue(g.g[A].evil and drunk(g, G))
        self.assertEqual(told(g, A), ['Night 2 — Goon: you are now evil.'])
        self.choose(3, C, [D], TOWN)
        self.answer(3, **{F: [], G: [C, A]})
        run(g.night(3))
        self.assertEqual(self.deaths(g, 3), [C])
        self.assertTrue(g.g[A].alive and g.g[A].evil and drunk(g, G))
        self.assertEqual(len(told(g, A)), 1)  # told only when the alignment changes

    def test_only_the_first_chooser_each_night_is_drunk(self):
        """Later on the same night, another player who chooses the Goon uses their ability as normal."""
        g = self.game(['Goon', 'Sailor', TOWN, 'Test Town 2', 'Test Town 3', 'Assassin', 'Zombuul'])
        self.answer(2, **{B: [A], F: [], G: [C]})
        run(g.night(2))
        self.assertTrue(drunk(g, B))
        g = self.game(['Goon', 'Sailor', TOWN, 'Test Town 2', 'Test Town 3', 'Assassin', 'Zombuul'])
        self.answer(2, **{B: [A], F: [], G: [A]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A])  # the Zombuul's attack works
        self.assertFalse(g.g[A].evil)  # the Sailor (good) was the first
        self.assertFalse(drunk(g, B) or drunk(g, G))  # and the Sailor's drunkenness ended with the Goon (a reading)

    def test_the_assassin_kills_the_goon_who_turns_evil_and_a_drunk_assassin_only_turns_it(self):
        """If chosen by the Assassin, the Goon dies but still turns evil. Example (Courtier): the drunk Assassin
        attacks the Goon, who does not die but turns evil."""
        g = self.game(['Goon', 'Courtier', TOWN, 'Test Town 2', 'Test Town 3', 'Assassin', 'Zombuul'])
        self.answer(2, **{F: [A], G: [C]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A, C])
        self.assertTrue(g.g[A].evil)
        g = self.game(['Goon', 'Courtier', TOWN, 'Test Town 2', 'Test Town 3', 'Assassin', 'Zombuul'])
        self.choose(2, B, character='Assassin')
        self.answer(2, **{F: [A], G: [C]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [C])
        self.assertTrue(g.g[A].alive and g.g[A].evil and g.g.spent_ability('Assassin'))

    def test_the_tea_ladys_protection_switches_off_when_the_goon_turns_evil(self):
        """Example: the Tea Lady neighbours the good Goon and the Tinker. The Tinker is executed but does not die.
        The next day the Goon is evil; the Tinker is executed again and dies."""
        g = self.game(['Goon', 'Tea Lady', 'Tinker', TOWN, 'Test Town 2', "Devil's Advocate", 'Zombuul'],
                      forced={'Tinker': {'yes': False}})
        g.execute(C)
        self.assertTrue(g.g[C].alive)
        self.answer(2, **{F: [A], G: [D]})
        run(g.night(2))
        self.assertTrue(g.g[A].evil and drunk(g, F))
        self.day(g, 2)
        g.execute(C)
        self.assertFalse(g.g[C].alive)

    def test_a_pukka_or_godfather_choosing_the_goon_does_nothing_and_a_drunk_chooser_still_turns_it(self):
        """The Pukka malfunctions before it can poison the Goon (wiki); the Goon still changes alignment, and makes
        the player drunk, if the chooser was already drunk or poisoned."""
        g = self.game(['Goon', TOWN, 'Test Town 2', 'Test Town 3', 'Test Out', 'Godfather', 'Pukka'])
        self.answer(1, **{G: [A]})
        run(g.night(1))
        self.assertFalse(g.g.is_poisoned(g.g[A]))
        self.assertTrue(g.g[A].evil and drunk(g, G))
        g = self.game(['Goon', TOWN, 'Test Town 2', 'Test Town 3', 'Test Out', 'Godfather', 'Pukka'])
        g.g.add(State('poisoned', F, until=None))
        g.kill(g.g[E], 'execution')  # an Outsider died today: the Godfather wakes
        self.answer(2, **{F: [A], G: [B]})
        run(g.night(2))
        self.assertTrue(g.g[A].alive and g.g[A].evil)
        self.assertNotIn(A, self.deaths(g, 2))

    def test_a_zombuul_choosing_the_goon_kills_no_one_and_the_goon_turns_evil(self):
        g = self.game(['Goon', TOWN, 'Test Town 2', 'Test Town 3', 'Test Town 4', 'Mastermind', 'Zombuul'])
        self.answer(2, **{G: [A]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])
        self.assertTrue(g.g[A].evil and drunk(g, G))
        g.g.expire('night', 3)
        self.assertFalse(drunk(g, G))  # until dusk

    def test_the_goon_chosen_by_the_devils_advocate_makes_its_protection_fail(self):
        g = self.game(['Goon', TOWN, 'Test Town 2', 'Test Town 3', 'Test Town 4', "Devil's Advocate", 'Zombuul'])
        self.answer(2, **{F: [A], G: [B]})
        run(g.night(2))
        self.day(g, 2)
        g.execute(A)
        self.assertFalse(g.g[A].alive)

    def test_a_drunk_goon_has_no_ability(self):
        g = self.game(['Goon', TOWN, 'Test Town 2', 'Test Town 3', 'Test Town 4', "Devil's Advocate", 'Zombuul'])
        g.g.add(State('drunk', A, until=None))
        self.answer(2, **{F: [A], G: [C]})
        run(g.night(2))
        self.assertFalse(drunk(g, F) or g.g[A].evil)
        self.day(g, 2)
        g.execute(A)
        self.assertTrue(g.g[A].alive)  # the Devil's Advocate's protection works


class LunaticTests(BMRTest):
    # Alex Lunatic, Blair Exorcist, Casey..Frankie Towns, Gray Assassin, Harper the Demon
    def chars(self, demon='Shabaloth'):
        return ['Lunatic', 'Exorcist', TOWN, 'Test Town 2', 'Test Town 3', 'Test Town 4', 'Assassin', demon]

    def lunatic(self, demon='Shabaloth', shown=None, **forced):
        return self.dealt(self.chars(demon), forced={'Lunatic:demon': {'character': shown or demon},
                                                     'Lunatic:minions': {'players': [C]},
                                                     'Lunatic:bluffs': {'characters': ['Exorcist', 'Sailor', 'Fool']},
                                                     'Shabaloth': {'players': []}, **forced})

    def test_the_lunatic_believes_they_are_the_demon_and_gets_demon_information(self):
        """How to Run: wake the Lunatic and act as if they are the Demon: Minions (any players) and three good
        characters (even in play). Wake the Demon and show them the Lunatic."""
        g = self.lunatic()
        intro = {e['to'][0]: e['data']['text'] for e in g.events if e['kind'] == 'intro'}
        self.assertEqual(g.g[A].shown, 'Shabaloth')
        self.assertIn(f'Your character: {ch.card("Shabaloth")}', intro[A])
        self.assertIn(f'Your Minion: {C} (you do not know which Minion characters). Three good characters not in '
                      'play, for evil to bluff: Exorcist, Sailor, Fool.', intro[A])
        self.assertIn(f'Your Minion: {G} (you do not know which Minion characters).', intro[H])
        self.assertIn(f'The Demon is {H}.', intro[G])
        self.assertNotIn('Lunatic', intro[H])
        run(g.night(1))
        self.assertEqual(told(g, H), [f'Night 1: {A} is the Lunatic (they believe they are the Shabaloth).'])
        self.assertEqual(self.asked(A, 1), [])  # the Shabaloth has no first-night step
        self.assertIn(f'{A}: Lunatic (good) [thinks they are the Shabaloth]', g.g.grimoire_text())

    def test_the_lunatics_picks_kill_no_one_and_the_demon_learns_them_before_choosing(self):
        """Example: the Lunatic, thinking they are the Shabaloth, wakes each night to choose two players. The
        chosen players do not die."""
        g = self.lunatic()
        run(g.night(1))
        self.answer(2, **{A: [C, D], B: [F], G: [], H: [E, F]})
        run(g.night(2))
        self.assertEqual(len(self.asked(A, 2)), 1)  # once, at the Lunatic's step, not again at the Shabaloth's
        self.assertEqual(self.asked(A, 2)[0].n_targets, 2)
        self.assertEqual(self.deaths(g, 2), [E, F])
        seq = {(e['kind'], tuple(e['to']) if isinstance(e['to'], list) else e['to'], e['data'].get('player')): e['seq']
               for e in g.events if e['day'] == 2}
        self.assertLess(seq[('info', (H,), None)], seq[('night_choice', 'audit', H)])
        self.assertEqual(told(g, H)[-1], f'Night 2: the Lunatic ({A}) chose {C}, {D}.')
        self.assertIn(A, g.g.woke[2])  # they woke to use their ability, as they believe it

    def test_a_lunatic_zombuul_wakes_only_when_a_zombuul_would(self):
        """Example: the Lunatic, thinking they are the Zombuul, does not wake often at night; the real Zombuul
        often attacks the same players."""
        g = self.lunatic('Zombuul')
        run(g.night(1))
        self.answer(2, **{A: [C], B: [E], G: [], H: [C]})
        run(g.night(2))
        self.assertEqual((len(self.asked(A, 2)), len(self.asked(H, 2))), (1, 1))
        self.assertEqual(self.deaths(g, 2), [C])
        self.day(g, 2)
        g.execute(D)
        run(g.night(3))
        self.assertEqual((self.asked(A, 3), self.asked(H, 3)), ([], []))
        self.assertEqual(len(told(g, H)), 2)  # not told anything on a night the Lunatic did not wake

    def test_a_lunatic_pukka_wakes_the_first_night_and_one_may_believe_another_demon(self):
        g = self.lunatic('Pukka')
        self.answer(1, **{A: [D], H: [E]})
        run(g.night(1))
        self.assertEqual(len(self.asked(A, 1)), 1)
        self.assertFalse(g.g.is_poisoned(g.g[D]))
        self.assertEqual(told(g, H)[-1], f'Night 1: the Lunatic ({A}) chose {D}.')
        g = self.lunatic('Shabaloth', shown='Po')
        run(g.night(1))
        self.answer(2, **{A: [], B: [F], G: [], H: [E, F]})
        run(g.night(2))
        self.assertEqual([r.n_targets for r in self.asked(A, 2)], [1])
        self.assertEqual(told(g, H)[-1], f'Night 2: the Lunatic ({A}) chose no one.')
        self.answer(3, **{A: [C, D, F], B: [C], G: [], H: [E, D]})
        run(g.night(3))
        self.assertEqual(self.asked(A, 3)[0].n_targets, 3)  # a Lunatic-Po charges as the Po would

    def test_the_exorcist_choosing_the_lunatic_does_nothing_and_choosing_the_demon_leaves_the_lunatic_awake(self):
        g = self.lunatic()
        run(g.night(1))
        self.answer(2, **{A: [C, D], B: [A], G: [], H: [E, F]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [E, F])
        self.assertFalse(any('Exorcist' in t for t in told(g, A)))
        self.answer(3, **{A: [C, D], B: [H], G: []})
        run(g.night(3))
        self.assertEqual((len(self.asked(A, 3)), self.asked(H, 3)), (1, []))
        self.assertEqual(told(g, H)[-2:], [f'Night 3: the Lunatic ({A}) chose {C}, {D}.',
                                           f'Night 3: the Exorcist chose you. {B} is the Exorcist, and you do not wake '
                                           'tonight.'])
        self.assertEqual(self.deaths(g, 3), [])

    def test_the_lunatic_is_a_good_outsider(self):
        """Examples: the Pacifist saves the executed Lunatic (a good player); the Godfather learns the Lunatic is in
        play and, after the Lunatic dies by execution, kills; the Professor's chosen Lunatic is not resurrected."""
        g = self.game(['Lunatic', 'Pacifist', 'Professor', TOWN, 'Test Town 2', 'Godfather', 'Zombuul'],
                      forced={'Pacifist:': {'yes': True}})
        g.g[A].shown = 'Zombuul'
        run(g.execution(A))
        self.assertTrue(g.g[A].alive)
        g = self.game(['Lunatic', 'Pacifist', 'Professor', TOWN, 'Test Town 2', 'Godfather', 'Zombuul'],
                      forced={'Pacifist:': {'yes': False}})
        g.g[A].shown = 'Zombuul'
        run(g.night(1))
        self.assertIn('Lunatic', told(g, F)[0])
        run(g.execution(A))
        self.answer(2, **{C: [A], F: [D], G: [E]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [D])  # the Godfather's kill; the Zombuul does not wake (a death today)
        self.assertFalse(g.g[A].alive)
        self.assertTrue(g.g.spent_ability('Professor'))

    def test_the_lunatic_choosing_the_goon_is_drunk_and_the_goon_stays_good(self):
        g = self.game(['Lunatic', 'Goon', TOWN, 'Test Town 2', 'Test Town 3', 'Assassin', 'Shabaloth'],
                      forced={'Shabaloth': {'players': []}})
        g.g[A].shown = 'Shabaloth'
        g.g[B].alignment = 'evil'
        self.answer(2, **{A: [B, C], F: [], G: [C, D]})
        run(g.night(2))
        self.assertTrue(drunk(g, A) and not g.g[B].evil)  # the Lunatic is good
        self.assertFalse(drunk(g, G))
        self.assertEqual(self.deaths(g, 2), [C, D])

    def test_the_belief_probe_asks_the_lunatic_what_a_demon_is_asked(self):
        from clocktower import probe

        class Probed(Seat):
            async def probe(self, text, meta):
                self.probed = text
                return Reply({**BLANK})
        names = NAMES[:8]
        self.seats = {n: Probed() for n in names}
        g = Game(self.seats, Forced(), names=names, seed=3, characters=self.chars(), script=self.script, probes=True)
        run(g.setup())

        async def go():
            g.probe('dawn')
            await asyncio.gather(*g.probe_tasks)
        run(go())
        self.assertTrue(self.seats[A].probed.endswith(probe.prompt(True)))
        self.assertTrue(self.seats[B].probed.endswith(probe.prompt(False)))

    def test_the_scripted_illusion_usually_shows_the_demon_in_play_and_never_the_lunatic_as_a_bluff(self):
        from clocktower.bmr import lunatic_bluffs_choice, lunatic_demon_choice, lunatic_minions_choice
        g = self.game(self.chars())
        r = random.Random(8)
        demons = [lunatic_demon_choice(g.g, g.g[H]).options(r)['character'] for _ in range(1000)]
        self.assertAlmostEqual(demons.count('Shabaloth') / 1000, POLICY['lunatic_same_demon'], delta=0.04)
        self.assertEqual(set(demons), set(self.script.demons))
        minions = [lunatic_minions_choice(g.g, g.g[A], g.g[H], 1).options(r)['players'] for _ in range(1000)]
        self.assertAlmostEqual(minions.count([H]) / 1000, POLICY['lunatic_shows_demon'], delta=0.05)
        self.assertNotIn([A], minions)
        bluffs = [lunatic_bluffs_choice(g.g).options(r)['characters'] for _ in range(300)]
        self.assertTrue(all(len(set(b)) == 3 and 'Lunatic' not in b for b in bluffs))
        self.assertTrue(any('Exorcist' in b for b in bluffs))  # sometimes a character in play


class TinkerTests(BMRTest):
    # Alex Tinker, Blair..Ellis Towns, Frankie Godfather, Gray Zombuul
    CHARS = ['Tinker', TOWN, 'Test Town 2', 'Test Town 3', 'Test Town 4', 'Godfather', 'Zombuul']

    def test_the_tinker_may_suddenly_die_by_day_and_the_town_sees_it(self):
        """Example: it is the third day. Suddenly, the Tinker dies. (The Godfather wakes; the Zombuul does not.)"""
        g = self.game(self.CHARS, forced={'Tinker': {'yes': True}})
        self.day(g, 3)
        g.moment('beat')
        self.assertFalse(g.g[A].alive)
        ev = [e for e in g.events if e['kind'] == 'died'][-1]
        self.assertEqual(render(ev, B), f'{A} dies.')
        self.assertEqual(g.g.died_today(), [A])
        self.answer(4, **{F: [B], G: [C]})
        run(g.night(4))
        self.assertEqual((len(self.asked(F, 4)), self.asked(G, 4)), (1, []))
        self.assertEqual(self.deaths(g, 4), [B])

    def test_the_tinker_may_die_at_night_whoever_the_demon_attacked(self):
        """Example: during the night, the Tinker dies, even though the Demon attacked a different player."""
        g = self.game(self.CHARS, forced={'Tinker': {'yes': True}})
        self.answer(2, **{G: [B]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A, B])
        self.assertFalse([e for e in g.events if e['kind'] == 'died'])  # announced at dawn, with the others

    def test_a_protected_drunk_or_game_ending_tinker_is_never_asked_about(self):
        """Example: the Tea Lady sits next to the Tinker and another good player, protecting the Tinker from death.
        "We recommend that you never kill the Tinker when it would end the game.\""""
        g = self.game(['Tinker', 'Tea Lady', TOWN, 'Test Town 2', 'Test Town 3', 'Godfather', 'Zombuul'],
                      forced={'Tinker': {'yes': True}})
        g.moment('beat')
        self.assertTrue(g.g[A].alive)  # the Tea Lady's good neighbours can't die
        self.assertEqual(choices(g, 'Tinker'), [])
        g = self.game(self.CHARS, forced={'Tinker': {'yes': True}})
        g.g.add(State('drunk', A, until=None))
        g.moment('beat')
        self.assertTrue(g.g[A].alive)
        g = self.game(self.CHARS, forced={'Tinker': {'yes': True}})
        for name in (B, C, D, E):
            g.g[name].alive = False
        g.moment('dusk')
        self.assertTrue(g.g[A].alive)  # three alive: it would end the game

    def test_after_the_innkeeper_dies_tonight_the_tinker_may_die(self):
        """Example: the Tinker is attacked by the Demon and protected by the Innkeeper. Later that night the
        Innkeeper dies, so the Storyteller chooses to kill the Tinker too."""
        g = self.game(['Tinker', TOWN, 'Test Town 2', 'Innkeeper', 'Test Town 3', 'Assassin', 'Zombuul'],
                      forced={'Tinker': {'yes': True}, 'Innkeeper': {'players': [E]}})
        self.answer(2, **{D: [A, E], F: [D], G: [A]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A, D])
        self.assertEqual([d['cause'] for d in g.g.death_log], ['assassin', 'tinker'])

    def test_a_tinker_the_devils_advocate_saved_may_still_die(self):
        """Example: the Tinker is executed, but the Storyteller kills the Tinker anyway, due to the Tinker
        ability."""
        g = self.game(['Tinker', TOWN, 'Test Town 2', 'Test Town 3', 'Test Town 4', "Devil's Advocate", 'Zombuul'],
                      forced={'Tinker': {'yes': True}})
        g.g.add(State('safe', A, source=F, against='execution'))
        g.execute(A)
        self.assertTrue(g.g[A].alive)
        g.moment('dusk')
        self.assertFalse(g.g[A].alive)

    def test_the_scripted_storyteller_kills_it_mostly_at_night_and_sometimes_never(self):
        from clocktower.bmr import tinker_choice
        g = self.game(self.CHARS)
        r = random.Random(9)
        rate = lambda when: sum(tinker_choice(g.g, g.g[A], when).options(r)['yes'] for _ in range(4000)) / 4000
        self.assertAlmostEqual(rate('night'), POLICY['tinker_night'], delta=0.02)
        self.assertAlmostEqual(rate('beat'), POLICY['tinker_day'], delta=0.004)
        g.g.notes['Tinker never'] = True
        self.assertEqual(rate('night'), 0)


class MoonchildTests(BMRTest):
    def test_killed_at_night_they_choose_at_dawn_and_a_good_player_dies_that_night(self):
        """Example: the Pukka kills the Moonchild. The next morning, the Moonchild chooses a player, who is the
        Exorcist. That night, the Exorcist dies."""
        g = self.game(['Moonchild', 'Exorcist', TOWN, 'Test Town 2', 'Test Town 3', 'Assassin', 'Pukka'])
        self.answer(1, **{G: [A]})
        run(g.night(1))
        self.answer(2, **{A: [B], B: [D], F: [], G: [C]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [A])
        req = [r for r in self.seats[A].log if r.kind == 'death_choice']
        self.assertEqual((len(req), req[0].options), (1, [B, C, D, E, F, G]))
        ev = [e for e in g.events if e['kind'] == 'ability'][-1]
        self.assertEqual(render(ev, C), f"{A} claims the Moonchild's ability on {B}.")
        self.day(g, 2)
        self.answer(3, **{B: [E], F: [], G: [E]})
        run(g.night(3))
        self.assertEqual(self.deaths(g, 3), [B, C])  # the Exorcist (the curse) and the Pukka's earlier victim

    def test_an_executed_moonchild_chooses_at_once_and_an_evil_choice_kills_no_one(self):
        g = self.game(['Moonchild', TOWN, 'Test Town 2', 'Test Town 3', 'Test Town 4', 'Assassin', 'Zombuul'])
        self.answer(1, **{A: [F]})
        run(g.execution(A))
        run(g.run_pending())
        self.assertEqual([e['data']['target'] for e in g.events if e['kind'] == 'ability'], [F])
        self.answer(2, **{F: [], G: [B]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])  # someone died today, so no Zombuul; the Assassin is evil

    def test_a_moonchild_saved_from_execution_does_not_choose(self):
        """Example: the Moonchild is executed but remains alive (the Pacifist): they do not choose a player."""
        g = self.game(['Moonchild', 'Pacifist', TOWN, 'Test Town 2', 'Test Town 3', 'Assassin', 'Zombuul'],
                      forced={'Pacifist:': {'yes': True}})
        run(g.execution(A))
        run(g.run_pending())
        self.assertTrue(g.g[A].alive)
        self.assertFalse([r for r in self.seats[A].log if r.kind == 'death_choice'])

    def test_eaten_twice_by_the_shabaloth_they_choose_twice(self):
        """Example: the Shabaloth eats the Moonchild, who chooses the Assassin, who remains alive. The Shabaloth
        regurgitates the Moonchild. A few nights later it eats the Moonchild again, who chooses the Gossip: the
        Gossip dies."""
        g = self.game(['Moonchild', 'Gossip', TOWN, 'Test Town 2', 'Test Town 3', 'Assassin', 'Shabaloth'],
                      forced={'Shabaloth': {'players': []}})
        self.answer(2, **{A: [F], F: [], G: [A, C]})
        run(g.night(2))
        self.day(g, 2)
        g.st.forced['Shabaloth'] = {'players': [A]}
        self.answer(3, **{F: [], G: [D, E]})
        run(g.night(3))
        self.assertTrue(g.g[A].alive and g.g[F].alive)
        self.day(g, 3)
        g.st.forced['Shabaloth'] = {'players': []}
        self.answer(4, **{A: [B], F: [], G: [A, D]})
        g.g[D].alive = True
        run(g.night(4))
        self.assertFalse(g.g[A].alive)
        self.day(g, 4)
        self.answer(5, **{F: [], G: [D, E]})
        g.g[E].alive = True
        run(g.night(5))
        self.assertIn(B, self.deaths(g, 5))

    def test_sobriety_tonight_decides_not_at_the_choice(self):
        """If the Moonchild is sober at night but was drunk when they chose today, that player dies; drunk or
        poisoned at night (the Pukka can poison the dead Moonchild), the player doesn't."""
        g = self.game(['Moonchild', TOWN, 'Test Town 2', 'Test Town 3', 'Test Town 4', 'Assassin', 'Zombuul'])
        g.g.add(State('drunk', A, until='night'))
        self.answer(1, **{A: [B]})
        run(g.execution(A))
        run(g.run_pending())
        self.answer(2, **{F: []})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [B])
        g = self.game(['Moonchild', TOWN, 'Test Town 2', 'Test Town 3', 'Test Town 4', 'Assassin', 'Pukka'])
        self.answer(1, **{A: [B]})
        run(g.execution(A))
        run(g.run_pending())
        self.answer(2, **{F: [], G: [A]})  # the Pukka poisons the dead Moonchild before the Moonchild's step
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])

    def test_a_goon_good_when_chosen_dies_though_evil_by_night(self):
        g = self.game(['Moonchild', 'Goon', TOWN, 'Test Town 2', 'Test Town 3', "Devil's Advocate", 'Zombuul'])
        self.answer(1, **{A: [B]})
        run(g.execution(A))
        run(g.run_pending())
        self.answer(2, **{F: [B]})
        run(g.night(2))
        self.assertTrue(g.g[B].evil)
        self.assertEqual(self.deaths(g, 2), [B])

    def test_a_bluffed_moonchild_claim_is_announced_and_does_nothing(self):
        g = self.game(['Moonchild', TOWN, 'Test Town 2', 'Test Town 3', 'Test Town 4', 'Assassin', 'Zombuul'])
        g.g[F].alive = False
        g.public_abilities([F], {F: {'ability': {'character': 'Moonchild', 'target': B}}})
        run(g.run_pending())
        ev = [e for e in g.events if e['kind'] == 'ability'][-1]
        self.assertEqual(render(ev, C), f"{F} claims the Moonchild's ability on {B}.")
        self.answer(2, **{F: [], G: [C]})
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [C])


class Batch3CoreTests(BMRTest):
    def test_public_turns_offer_the_claimable_characters_and_private_ones_do_not(self):
        g = self.game(['Gossip', 'Moonchild', TOWN, 'Test Town 2', 'Test Town 3', 'Assassin', 'Zombuul'])
        g.private_beats = g.public_beats = 1
        run(g.beat(1, 1, True))
        run(g.beat(1, 1, False))
        beats = [r for r in self.seats[A].log if r.kind == 'beat']
        self.assertEqual([r.claimable for r in beats], [[], ['Gossip', 'Moonchild']])
        from clocktower.agents import Request
        self.assertEqual(Request('beat', 'x', 1).claimable, [])  # Trouble Brewing's requests are unchanged

    def test_random_seats_claim_abilities_only_when_offered(self):
        from clocktower.agents import RandomSeat, Request
        a, b = RandomSeat(A, random.Random(1), NAMES), RandomSeat(A, random.Random(1), NAMES)
        plain = [run(a.act('', Request('beat', 'x', 1, mode='public'))).action for _ in range(200)]
        offered = [run(b.act('', Request('beat', 'x', 1, mode='public', claimable=['Gossip']))).action
                   for _ in range(200)]
        self.assertFalse(any('ability' in x for x in plain))
        self.assertTrue(any(x.get('ability', {}).get('character') == 'Gossip' for x in offered))

    def test_a_drunk_players_information_may_be_false_as_a_poisoned_ones(self):
        g = self.game([TOWN, 'Test Town 2', 'Test Town 3', 'Test Town 4', 'Test Town 5', 'Assassin', 'Zombuul'])
        g.g.add(State('drunk', A, until=None))
        r = random.Random(1)
        self.assertAlmostEqual(sum(g.g.misinformed(g.g[A], r) for _ in range(2000)) / 2000, POLICY['poisoned_false'],
                               delta=0.03)
        self.assertFalse(g.g.misinformed(g.g[B], r))


class BadMoonRisingTests(unittest.TestCase):
    def test_the_script_loads_with_every_character_and_its_official_text(self):
        bmr = ch.Script('bmr')
        self.assertEqual(len(bmr.all), 25)
        self.assertEqual(bmr.claimable, ['Gossip', 'Moonchild'])
        for c in bmr.all:
            self.assertEqual(ch.rules(c).ability, official.role(c)['ability'], c)

    def test_the_player_prompt_and_schema_build_at_every_size(self):
        from clocktower.prompts import player_system
        from clocktower.schema import player_schema
        bmr = ch.Script('bmr')
        for n in range(5, 16):
            text = player_system(n, script=bmr)
            self.assertIn('Bad Moon Rising', text)
            self.assertNotIn('slayer_shot', text)
            self.assertNotIn('Imp', text.replace('Impact', ''))
        self.assertIn('- ability:', text)
        self.assertIn('- character:', text)
        props = player_schema(ALL_NAMES[:9], bmr)['properties']
        self.assertNotIn('slayer_shot', props)
        self.assertEqual(props['ability']['anyOf'][0]['properties']['character']['enum'], ['Gossip', 'Moonchild'])

    def test_whole_games_of_the_script_run_to_the_end_at_every_size(self):
        from clocktower.agents import RandomSeat
        bmr = ch.Script('bmr')
        claims = 0
        for n in range(5, 16):
            for k in range(2):
                seed = n * 10 + k
                names = ALL_NAMES[:n]
                seats = {x: RandomSeat(x, random.Random(seed * 13 + i), names) for i, x in enumerate(names)}
                g = Game(seats, ScriptedStoryteller(random.Random(seed)), names=names, seed=seed, script=bmr,
                         probes=False, private_beats=1, public_beats=2, max_days=12)
                result = run(g.run())
                self.assertTrue(result['winner'] or result['stopped'].startswith('stopped after'), result['reason'])
                claims += sum(e['kind'] == 'ability' for e in g.events)
        self.assertGreater(claims, 10)
