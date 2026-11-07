"""Sects & Violets' characters: the almanac's examples and How to Run, one test class per character.

Until every S&V character is built, the games here use a test script: the S&V characters under test, two Trouble
Brewing information Townsfolk (the Empath and the Chef, for the Vortox), and plain test-only fillers (registered for
these tests and removed after), with the official night order."""
import asyncio
import random
import unittest

from clocktower import characters as ch
from clocktower import judge, official
from clocktower.agents import ScriptedStoryteller
from clocktower.game import ALL_NAMES, NAMES, Game
from clocktower.llm import Reply
from clocktower.snv import arbitrary_deaths_choice, twin_choice
from clocktower.state import (POLICY, Grimoire, State, empath_choice, madness_choice, madness_penalty_choice,
                              random_setup, setup_error, team_sizes)

A, B, C, D, E, F, G, H, I = NAMES
BLANK = {'say': '', 'whispers': [], 'nominate': None, 'vote': None, 'targets': []}
SNV = ['Witch', 'Cerenovus', 'Pit-Hag', 'Evil Twin', 'Fang Gu', 'Vigormortis', 'No Dashii', 'Vortox']
INFO = ['Empath', 'Chef']


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


class Out(ch.Outsider):
    name = 'Test Out'


class Out2(Out):
    name = 'Test Out 2'


class Out3(Out):
    name = 'Test Out 3'


FILLERS = [Town, Town2, Town3, Town4, Town5, Out, Out2, Out3]
T1, T2, T3, T4, T5 = (c.name for c in FILLERS[:5])
O1, O2, O3 = (c.name for c in FILLERS[5:])


class Seat:
    """Answers night requests from {night: answer} and day requests from {kind: [answers]} (each used once), and
    records every request."""

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


class SNVTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for c in FILLERS:
            ch.CHARACTERS[c.name] = c()
        cls.script = ch.Script.of('snv-test', [c.name for c in FILLERS] + SNV + INFO,
                                  official.night_order(SNV + INFO, True), official.night_order(SNV + INFO, False))

    @classmethod
    def tearDownClass(cls):
        for c in FILLERS:
            del ch.CHARACTERS[c.name]

    def game(self, chars, forced=None, judge_=None, **kw):
        """A game with the Grimoire dealt as given (seat order), at day 1."""
        names = ALL_NAMES[:len(chars)]
        self.seats = {n: Seat() for n in names}
        g = Game(self.seats, Forced(forced), names=names, seed=3, characters=chars, script=self.script, probes=False,
                 judge=judge_, private_beats=1, public_beats=1, **kw)
        g.g = Grimoire(names, chars, script=self.script)
        g.day, g.phase, g.g.day = 1, 'day', 1
        return g

    def dealt(self, chars, forced=None):
        """A game set up as a real one is (the characters' setup steps), seat order kept."""
        names = NAMES[:len(chars)]
        self.seats = {n: Seat() for n in names}
        g = Game(self.seats, Forced(forced), names=names, seed=3, characters=chars, script=self.script, probes=False,
                 private_beats=1, public_beats=1)
        run(g.setup())
        return g

    def choose(self, night, name, targets=(), character=None):
        self.seats[name].answers[night] = {'targets': list(targets), 'character': character}

    def steps(self, night, name, *answers):
        """`name`'s answers on `night`, one per step they are woken at, in order (a Pit-Hag who becomes a Demon)."""
        self.seats[name].answers[night] = [{'targets': list(t), 'character': c} for t, c in answers]

    def day(self, g, n):
        g.day, g.phase, g.g.day = n, 'day', n

    def told(self, name, text):
        return [e['data']['text'] for e in self.events_for(name) if text in e['data'].get('text', '')]

    def events_for(self, name):
        return [e for e in self.g.events if e['to'] == [name] and e['kind'] in ('info', 'notice')]

    def say(self, g, who, text, to=None):
        if to:
            g.emit('whisper', {'from': who, 'to': list(to), 'text': text}, [who, *to])
        else:
            g.emit('say', {'speaker': who, 'text': text})

    def nominate(self, g, nominator, nominee, voters=()):
        """Today's nominations: `nominator` nominates `nominee`, and `voters` vote yes."""
        self.seats[nominator].day['nominate'] = [{'nominate': nominee}]
        for v in voters:
            self.seats[v].day['vote'] = [{'vote': True}]
        g.phase = 'nominations'
        run(g.nominations())

    def deaths(self, g, n):
        return [e['data']['deaths'] for e in g.events if e['kind'] == 'dawn' and e['data']['day'] == n][0]


# ---- Minions ---------------------------------------------------------------------------------------------------

class WitchTests(SNVTest):
    CHARS = [T1, T2, O1, T3, 'Witch', 'Fang Gu', T4]

    def test_a_cursed_player_who_nominates_dies_and_the_vote_still_happens(self):
        """Example: the Witch curses the Sage; the Sage nominates the Dreamer and dies at once; the players still vote
        to execute the Dreamer, who dies too."""
        self.g = g = self.game(self.CHARS)
        self.choose(1, E, [A])
        run(g.night(1))
        self.assertTrue(g.g.has(g.g[A], 'cursed'))
        self.nominate(g, A, B, voters=[A, C, D, E, F, G])
        self.assertFalse(g.g[A].alive)
        self.assertEqual([e['data']['player'] for e in g.events if e['kind'] == 'died'], [A])  # declared at once
        self.assertEqual(g.g.death_log[0]['cause'], 'witch')
        self.assertEqual(g.g.executions[0]['player'], B)
        self.assertFalse(g.g[B].alive)

    def test_a_witch_who_curses_themself_dies_nominating_and_nominations_go_on(self):
        self.g = g = self.game(self.CHARS)
        self.choose(1, E, [E])
        run(g.night(1))
        self.nominate(g, E, F)  # nobody votes
        self.assertFalse(g.g[E].alive)
        self.assertTrue(g.g[F].alive)
        self.assertEqual(g.g.executions, [])

    def test_an_uncursed_player_nominates_safely_and_the_curse_lasts_one_day(self):
        self.g = g = self.game(self.CHARS)
        self.choose(1, E, [A])
        run(g.night(1))
        self.nominate(g, B, C)
        self.assertTrue(g.g[B].alive)
        self.choose(2, E, [D])
        self.choose(2, F, [G])
        run(g.night(2))
        self.assertFalse(g.g.has(g.g[A], 'cursed'))
        self.nominate(g, A, C)
        self.assertTrue(g.g[A].alive)

    def test_the_fang_gu_jumps_into_the_cursed_klutz_who_nominates_and_good_wins(self):
        """Example: the Witch curses the Klutz; the Fang Gu attacks the Klutz, who becomes the Fang Gu; the new Fang
        Gu, cursed, nominates and dies: good wins."""
        self.g = g = self.game(self.CHARS)
        self.choose(2, E, [C])
        self.choose(2, F, [C])
        run(g.night(2))
        self.assertEqual((g.g[C].character, g.g[C].alignment), ('Fang Gu', 'evil'))
        self.assertFalse(g.g[F].alive)
        self.assertIsNone(g.g.check_victory())
        self.nominate(g, C, A)
        self.assertEqual(g.g.winner, 'good')

    def test_at_three_alive_the_curse_is_removed_and_the_witch_acts_no_more(self):
        """Example: the Witch curses the Savant; that night the Demon's kill leaves three alive, so the curse is
        removed and the Savant nominates safely."""
        self.g = g = self.game([T1, T2, 'Witch', T3, 'Fang Gu'])
        g.g[D].alive = False
        self.choose(2, C, [A])
        self.choose(2, E, [B])
        run(g.night(2))
        self.assertEqual(g.g.alive_count(), 3)
        self.nominate(g, A, C)
        self.assertTrue(g.g[A].alive)
        run(g.night(3))
        self.assertFalse([r for r in self.seats[C].log if r.kind == 'night' and r.day == 3])  # not woken

    def test_a_drunk_witchs_curse_is_suspended_and_resumes_and_a_drunk_choice_is_wasted(self):
        """The rulebook: the sober Witch has cursed a player; drunk, that player is not cursed; sober, cursed again.
        A Witch drunk as they choose curses nobody."""
        self.g = g = self.game(self.CHARS)
        self.choose(1, E, [A])
        run(g.night(1))
        drunk = State('drunk', E, source=G)
        g.g.add(drunk)
        self.assertFalse(g.g.has(g.g[A], 'cursed'))
        g.g.states.remove(drunk)
        self.assertTrue(g.g.has(g.g[A], 'cursed'))
        g.g.add(State('drunk', E, source=G, until=None))
        self.choose(2, E, [B])
        run(g.night(2))
        self.assertFalse([s for s in g.g.states if s.kind == 'cursed'])


class CerenovusTests(SNVTest):
    CHARS = [T1, T2, O1, T3, 'Cerenovus', 'Fang Gu', T4]

    def mad(self, g, who, about, n=1):
        self.choose(n, E, [who], about)
        run(g.night(n))

    def test_the_target_is_told_and_is_mad_tomorrow_only(self):
        self.g = g = self.game(self.CHARS)
        self.mad(g, B, 'Chef')
        self.assertTrue(self.told(B, 'you must be "mad" that you are the Chef'))
        self.assertEqual([s.about for s in g.g.states if s.kind == 'mad' and s.target == B], ['Chef'])
        self.assertIn('MAD about being the Chef', g.g.grimoire_text())
        self.choose(2, E, [C], 'Empath')
        self.choose(2, F, [G])
        run(g.night(2))
        self.assertFalse([s for s in g.g.states if s.kind == 'mad' and s.target == B])  # a previously mad player

    def test_only_a_good_character_on_the_script_may_be_named(self):
        self.g = g = self.game(self.CHARS)
        self.mad(g, B, 'Chef')
        req = [r for r in self.seats[E].log if r.kind == 'night'][0]
        self.assertIn('Chef', req.characters)
        self.assertIn(O1, req.characters)
        self.assertNotIn('Witch', req.characters)
        self.assertNotIn('Vortox', req.characters)

    def test_a_player_who_claims_the_character_aloud_and_denies_being_mad_is_safe(self):
        """Example: the Barber made mad as the Savant claims the Savant, gives made-up facts, and when asked whether
        they are mad says "no" emphatically: not executed."""
        self.g = g = self.game(self.CHARS)
        self.mad(g, B, 'Chef')
        self.say(g, B, "I'm the Chef, and I learned there is 1 pair of evil players.")
        self.say(g, B, 'No! I am not mad, I promise.')
        run(g.moment_judged('nominations'))
        self.assertTrue(g.g[B].alive)
        self.assertFalse(g.executed_today)

    def test_a_dead_player_who_says_nothing_is_executed_and_the_day_goes_to_night(self):
        """Example: the dead Artist is made mad about being the Sage, says nothing, and is executed. A madness
        execution before nominations is the day's execution: no nominations today."""
        self.g = g = self.game(self.CHARS, forced={'Madness execution': {'yes': True}})
        g.g[B].alive = False
        self.mad(g, B, 'Chef')
        run(g.daytime(1))
        self.assertEqual(g.g.executions, [{'player': B, 'day': 1, 'died': False}])
        kinds = [e['kind'] for e in g.events]
        self.assertNotIn('nominations_open', kinds)
        self.assertIn('The Storyteller declares that Blair is executed.', [e['data'].get('text') for e in g.events])

    def test_claiming_another_character_or_denying_it_breaks_madness(self):
        for said in ["I'm the Empath.", "I am the Chef. Actually no, I'm not the Chef.", 'I am mad.']:
            self.g = g = self.game(self.CHARS, forced={'Madness execution': {'yes': True}})
            self.mad(g, B, 'Chef')
            self.say(g, B, said)
            run(g.moment_judged('nominations'))
            self.assertTrue(g.executed_today, said)

    def test_a_private_confession_counts_only_for_a_storyteller_who_hears_whispers(self):
        """Example: the Flowergirl made mad as the Clockmaker claims it aloud but hints privately that they are mad;
        the Storyteller overhears and executes them. The scripted Storyteller and a judge hearing only what is said
        aloud never hear the hint; a judge hearing all does."""
        self.g = g = self.game(self.CHARS)
        self.mad(g, B, 'Chef')
        self.say(g, B, 'I am the Chef: I learned a 1.')
        self.say(g, B, "Between us, I'm actually mad: the Cerenovus got me.", to=[C])
        evidence = judge.madness_evidence(g, B, 'Chef', 1, 'public')
        choice = madness_choice(g.g, g.g[B], 'Chef', True, evidence)
        self.assertIs(choice.options(random.Random(1))['yes'], False)  # the scripted Storyteller: kept
        self.assertIs(judge.RulesJudge('public').ranking(g, choice)[0][0]['yes'], False)
        ranked, reason = judge.RulesJudge('all').ranking(g, choice)
        self.assertIs(ranked[0]['yes'], True)
        self.assertIn('whispered', reason)

    def test_mad_evil_players_are_executed_less_often_than_good_ones(self):
        self.g = g = self.game(self.CHARS)
        rate = lambda p: sum(madness_penalty_choice(g.g, g.g[p], 'Chef').options(random.Random(i))['yes']
                             for i in range(2000)) / 2000
        self.assertAlmostEqual(rate(B), POLICY['mad_execute_good'], delta=0.03)
        self.assertAlmostEqual(rate(F), POLICY['mad_execute_evil'], delta=0.04)
        self.assertIs(judge.RulesJudge().ranking(g, madness_penalty_choice(g.g, g.g[B], 'Chef'))[0][0]['yes'], True)

    def test_a_drunk_cerenovus_makes_nobody_mad_but_the_target_is_still_told(self):
        self.g = g = self.game(self.CHARS)
        g.g.add(State('drunk', E, source=G, until=None))
        self.mad(g, B, 'Chef')
        self.assertTrue(self.told(B, 'mad'))
        self.assertFalse([s for s in g.g.states if s.kind == 'mad'])
        run(g.moment_judged('nominations'))
        self.assertFalse(g.executed_today)

    def test_there_is_one_execution_a_day(self):
        self.g = g = self.game(self.CHARS)
        self.mad(g, B, 'Chef')
        g.execute(A)
        self.assertFalse(run(g.judge_madness(g.g[B], 'Chef')))
        self.assertTrue(g.g[B].alive)

    def test_the_good_twin_executed_for_madness_loses_the_game(self):
        """Example (Evil Twin): the good twin, made mad, is executed by the Storyteller: evil wins (the rulebook: the
        player's choice, not the Storyteller's)."""
        self.g = g = self.game([T1, T2, O1, 'Evil Twin', 'Cerenovus', 'Fang Gu', T4],
                               forced={'Madness execution': {'yes': True}})
        g.g.notes['Twins'] = {D: B}
        self.mad(g, B, 'Chef')
        run(g.moment_judged('nominations'))
        self.assertEqual(g.g.winner, 'evil')


class PitHagTests(SNVTest):
    CHARS = [T1, 'Empath', O1, T3, 'Pit-Hag', 'Fang Gu', T4]

    def test_nothing_happens_if_the_character_is_in_play_and_not_on_the_first_night(self):
        """Example: the Pit-Hag tries to turn the Savant into the Sage, but a Sage is in play."""
        self.g = g = self.game(self.CHARS)
        run(g.night(1))
        self.assertFalse([r for r in self.seats[E].log if r.kind == 'night'])
        self.choose(2, E, [A], 'Empath')
        run(g.night(2))
        self.assertEqual(g.g[A].character, T1)

    def test_the_player_becomes_the_character_keeps_their_alignment_and_is_told(self):
        """How to Run: show them YOU ARE and their new character; remind them their alignment is unchanged. Under a
        Vortox the notice is still true: it is not a Townsfolk's information (the Juggler made the good Witch)."""
        self.g = g = self.game([T1, 'Empath', O1, T3, 'Pit-Hag', 'Vortox', T4])
        self.choose(2, E, [A], 'Cerenovus')
        self.choose(2, F, [G])
        run(g.night(2))
        self.assertEqual((g.g[A].character, g.g[A].alignment), ('Cerenovus', 'good'))
        self.assertTrue(self.told(A, 'you are now the Cerenovus'))
        self.assertTrue(self.told(A, 'you are still good'))
        self.assertFalse(g.g[A].evil)

    def test_a_dead_player_can_be_changed_and_a_drunk_pit_hag_changes_nobody(self):
        self.g = g = self.game(self.CHARS)
        g.g[A].alive = False
        self.choose(2, E, [A], O2)
        run(g.night(2))
        self.assertEqual(g.g[A].character, O2)
        g.g.add(State('drunk', E, source=G, until=None))
        self.choose(3, E, [D], O3)
        run(g.night(3))
        self.assertEqual(g.g[D].character, T3)

    def test_a_new_evil_twin_is_paired_with_an_evil_player_and_they_learn_each_other(self):
        """Example: the Pit-Hag turns the Flowergirl into the Evil Twin: there is a good Evil Twin, and the Evil Twin
        and an evil player learn each other's character."""
        self.g = g = self.game(self.CHARS)
        self.choose(2, E, [A], 'Evil Twin')
        run(g.night(2))
        twin = g.g.notes['Twins'][A]
        self.assertTrue(g.g[twin].evil)
        self.assertTrue(self.told(A, f'your twin is {twin}, the {g.g[twin].character}'))
        self.assertTrue(self.told(twin, f'{A} is the Evil Twin'))

    def test_a_demon_made_into_another_demon_usually_kills_nobody_tonight(self):
        """How to Run: best to make no death occur tonight; the Storyteller can see whom the Demon attacks and
        decide that no one dies."""
        self.g = g = self.game(self.CHARS, forced={'Pit-Hag deaths': {'players': [], 'yes': False}})
        self.choose(2, E, [F], 'No Dashii')
        self.choose(2, F, [A])
        run(g.night(2))
        self.assertEqual(g.g[F].character, 'No Dashii')
        self.assertTrue(g.g[A].alive)
        self.assertEqual(self.deaths(g, 2), [])
        quiet = 0
        for i in range(1000):
            v = arbitrary_deaths_choice(g.g, g.g[E], g.g[F], True).options(random.Random(i))
            quiet += v['yes'] is False and not v['players']
        self.assertAlmostEqual(quiet / 1000, POLICY['pithag_quiet'], delta=0.04)

    def test_a_new_evil_demon_and_the_old_one_dies(self):
        """How to Run: if the Pit-Hag creates a new evil Demon, best to kill the old Demon and some other player."""
        self.g = g = self.game(self.CHARS, forced={'Pit-Hag deaths': {'players': [F], 'yes': True}})
        self.steps(2, E, ([E], 'Vortox'), ([A], None))  # the Pit-Hag, now the Vortox, wakes at its step too
        run(g.night(2))
        self.assertEqual(g.g[E].character, 'Vortox')
        self.assertFalse(g.g[F].alive)
        self.assertEqual(g.g.death_log[0]['cause'], 'pit-hag')
        self.assertIsNone(g.g.check_victory())

    def test_a_good_demon_on_the_final_night_and_the_evil_demon_dies(self):
        """Example: during the final night, the Pit-Hag turns the Oracle into a good No Dashii; the Storyteller kills
        the evil Demon only."""
        self.g = g = self.game(self.CHARS)
        for x in (C, D, G):
            g.g[x].alive = False
        run(g.change(g.g[A], character='No Dashii'))
        picks = [arbitrary_deaths_choice(g.g, g.g[E], g.g[A], False).options(random.Random(i))['players']
                 for i in range(1000)]
        self.assertAlmostEqual(picks.count([F]) / 1000, POLICY['pithag_final_kill'], delta=0.04)
        self.assertEqual(picks.count([]), 1000 - picks.count([F]))

    def test_the_vigormortis_and_pit_hag_example(self):
        """Example: the Vigormortis kills the Pit-Hag, who changes a Savant into a Witch; the Vigormortis kills the
        Witch, who curses and kills a player; the Pit-Hag turns the dead Witch into the Oracle, who has no ability;
        the Pit-Hag turns the Vigormortis into a Vortox, and now has no ability."""
        self.g = g = self.game([T1, 'Empath', O1, T3, 'Pit-Hag', 'Vigormortis', T4])
        self.choose(2, E, [A], 'Empath')  # in play: nothing
        self.choose(2, F, [E])
        run(g.night(2))
        self.assertFalse(g.g[E].alive)
        self.assertTrue(g.g.works(g.g[E], 'Pit-Hag'))  # the dead Pit-Hag wakes and acts
        self.choose(3, E, [A], 'Witch')
        self.choose(3, F, [A])
        run(g.night(3))
        self.assertEqual(g.g[A].character, 'Witch')
        self.assertFalse(g.g[A].alive)
        self.choose(4, A, [D])  # the dead Witch curses
        self.choose(4, E, [B], 'Empath')
        self.choose(4, F, [A])
        run(g.night(4))
        self.day(g, 4)
        self.nominate(g, D, B)
        self.assertFalse(g.g[D].alive)
        self.choose(5, E, [A], T5)
        self.choose(5, F, [A])
        run(g.night(5))
        self.assertEqual(g.g[A].character, T5)
        self.assertFalse(g.g.keeps_ability(g.g[A]))  # a Townsfolk now: no ability
        self.assertFalse(g.g.works(g.g[A], T5))
        self.choose(6, E, [F], 'Vortox')
        self.choose(6, F, [A])
        run(g.night(6))
        self.assertEqual(g.g[F].character, 'Vortox')
        self.assertFalse(g.g.works(g.g[E], 'Pit-Hag'))  # the Pit-Hag now has no ability


# ---- Evil Twin -------------------------------------------------------------------------------------------------

class EvilTwinTests(SNVTest):
    CHARS = [T1, T2, O1, T3, 'Evil Twin', 'Fang Gu', T4]

    def twins(self, forced_twin=B):
        self.g = g = self.dealt(self.CHARS, forced={'Twin': {'players': [forced_twin]}})
        return g

    def test_at_setup_a_good_player_is_the_twin_and_on_the_first_night_they_learn_each_other(self):
        g = self.twins()
        self.assertEqual(g.g.notes['Twins'], {E: B})
        run(g.night(1))
        self.assertTrue(self.told(E, f'your twin is {B}, the {T2}'))
        self.assertTrue(self.told(B, f'{E} is the Evil Twin'))
        picks = {twin_choice(g.g, g.g[E]).options(random.Random(i))['players'][0] for i in range(200)}
        self.assertEqual(picks, {A, B, C, D, G})  # any good player

    def test_a_new_evil_twin_on_the_final_night_is_paired_with_the_demon_or_a_dead_player(self):
        """How to Run: if a Pit-Hag creates an Evil Twin during the final night, make the other twin the Demon or a
        dead player, so that the good team can still win."""
        self.g = g = self.game([T1, T2, O1, T3, 'Evil Twin', 'Fang Gu', T4])
        self.day(g, 4)
        for x in (C, D, G):
            g.g[x].alive = False
        run(g.change(g.g[A], alignment='evil'))  # an evil Evil Twin would need a good twin: B, C, D or G
        picks = {twin_choice(g.g, g.g[E]).options(random.Random(i))['players'][0] for i in range(200)}
        self.assertEqual(picks, {C, D, G})

    def test_executing_the_evil_twin_and_the_game_goes_on(self):
        """Example: both twins claim the Oracle; the Evil Twin is executed; the game continues."""
        g = self.twins()
        g.execute(E)
        self.assertIsNone(g.g.winner)

    def test_executing_the_good_twin_and_evil_wins(self):
        g = self.twins()
        g.execute(B)
        self.assertEqual(g.g.winner, 'evil')

    def test_good_cant_win_while_both_twins_live(self):
        """Example: the Demon dies; the game continues, with no death at night from now on; two days later the Evil
        Twin dies: good wins."""
        g = self.twins()
        g.execute(F)
        self.assertIsNone(g.g.winner)
        self.choose(2, F, [A])
        run(g.night(2))
        self.assertEqual(self.deaths(g, 2), [])
        self.day(g, 3)
        g.execute(E)
        self.assertEqual(g.g.winner, 'good')

    def test_a_dead_evil_twin_has_no_ability(self):
        g = self.twins()
        g.kill(g.g[E], 'demon')
        g.execute(B)
        self.assertIsNone(g.g.winner)

    def test_a_good_evil_twin_executed_and_evil_wins(self):
        """Example: the Pit-Hag turns the good Sage into the Evil Twin; their twin is an evil Witch; the good Evil Twin
        is executed: evil wins."""
        self.g = g = self.game([T1, T2, O1, T3, 'Pit-Hag', 'Fang Gu', T4], forced={'Twin': {'players': [E]}})
        self.choose(2, E, [B], 'Evil Twin')
        run(g.night(2))
        self.assertEqual(g.g.notes['Twins'], {B: E})
        self.day(g, 2)
        g.execute(E)  # the evil twin: the game goes on
        self.assertIsNone(g.g.winner)
        g.execute(B)
        self.assertEqual(g.g.winner, 'evil')

    def test_a_twin_who_turns_to_the_evil_twins_side_is_replaced(self):
        """If both twins are the same alignment, the Storyteller chooses a new twin (the Fang Gu jumps into the good
        twin, an Outsider)."""
        g = self.twins(forced_twin=C)
        g.st.forced['Twin'] = {'players': [A]}
        self.choose(2, F, [C])
        run(g.night(2))
        self.assertTrue(g.g[C].evil)
        self.assertEqual(g.g.notes['Twins'], {E: A})
        self.assertTrue(self.told(A, f'{E} is the Evil Twin'))

    def test_the_vigormortis_kills_the_evil_twin_who_keeps_their_ability(self):
        """Example: the Vigormortis kills the Evil Twin, who neighbours a Klutz and a Flowergirl; the Sage is next to
        the Klutz; the Storyteller poisons the Sage. The good twin is executed: evil wins."""
        self.g = g = self.game([T1, O1, 'Evil Twin', T2, 'Vigormortis', T3, T4],
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


# ---- Demons ----------------------------------------------------------------------------------------------------

class FangGuTests(SNVTest):
    CHARS = [T1, T2, O1, T3, 'Witch', 'Fang Gu', O2]

    def test_one_extra_outsider(self):
        self.assertEqual(team_sizes(7, 1), (4, 1, 1))
        self.assertIsNone(setup_error([T1, T2, O1, T3, 'Witch', 'Fang Gu', T4], self.script))
        self.assertIsNotNone(setup_error([T1, T2, T5, T3, 'Witch', 'Fang Gu', T4], self.script))
        rng = random.Random(5)
        for _ in range(50):
            chars = random_setup(rng, players=7, script=self.script)
            self.assertIsNone(setup_error(chars, self.script), chars)

    def test_the_first_outsider_it_kills_becomes_an_evil_fang_gu_and_the_old_one_dies(self):
        """Example: the Fang Gu attacks the Artist, who dies; next night the Sweetheart, who becomes the Fang Gu while
        the old Fang Gu dies (the Sweetheart did not die); next night the new Fang Gu attacks the Klutz, who dies."""
        self.g = g = self.game(self.CHARS)
        self.choose(2, F, [A])
        run(g.night(2))
        self.assertFalse(g.g[A].alive)
        self.choose(3, F, [C])
        run(g.night(3))
        self.assertEqual((g.g[C].character, g.g[C].alignment, g.g[C].alive), ('Fang Gu', 'evil', True))
        self.assertFalse(g.g[F].alive)
        self.assertEqual(self.deaths(g, 3), [F])
        self.assertTrue(self.told(C, 'you are now the Fang Gu'))
        self.assertTrue(self.told(C, 'you are now evil'))
        self.assertFalse(self.told(C, 'Minion'))  # they learn no Minions
        self.assertIsNone(g.g.check_victory())
        self.choose(4, C, [G])
        run(g.night(4))
        self.assertFalse(g.g[G].alive)
        self.assertEqual(g.g[G].character, O2)

    def test_attacking_a_dead_outsider_does_nothing(self):
        """Example: the Fang Gu attacks the dead Klutz; the Fang Gu does not die, the Klutz stays good, and no deaths
        occur tonight."""
        self.g = g = self.game(self.CHARS)
        g.g[C].alive = False
        self.choose(2, F, [C])
        run(g.night(2))
        self.assertTrue(g.g[F].alive)
        self.assertEqual((g.g[C].character, g.g[C].alignment), (O1, 'good'))
        self.assertEqual(self.deaths(g, 2), [])
        self.assertFalse(g.g.notes.get('Fang Gu once'))

    def test_an_outsider_who_does_not_die_does_not_become_the_fang_gu(self):
        self.g = g = self.game(self.CHARS)
        g.g.add(State('safe', C, source=A, against='any', until=None))
        self.choose(2, F, [C])
        run(g.night(2))
        self.assertEqual(g.g[C].character, O1)
        self.assertTrue(g.g[F].alive)


class VigormortisTests(SNVTest):
    CHARS = [T1, T2, 'Witch', T3, 'Vigormortis', 'Cerenovus', T4, T5, O1]

    def test_one_fewer_outsider_and_none_removed_where_there_are_none(self):
        self.assertEqual(team_sizes(7, -1, floor=True), (5, 0, 1))
        self.assertIsNone(setup_error([T1, T2, T3, T4, T5, 'Witch', 'Vigormortis'], self.script))
        self.assertIsNone(setup_error([T1, T2, T3, T4, 'Witch', 'Vigormortis'], self.script))  # 6: 4 and 0
        self.assertIsNotNone(setup_error([T1, T2, T3, O1, 'Witch', 'Vigormortis'], self.script))

    def test_a_minion_it_kills_keeps_their_ability_and_a_townsfolk_neighbour_is_poisoned(self):
        """Example: the Vigormortis kills the Witch; the player the Witch cursed tonight remains cursed, and dies
        nominating the next day. The dead Witch wakes and curses again."""
        self.g = g = self.game(self.CHARS, forced={'Vigormortis': {'players': [D]}})
        self.choose(2, C, [A])
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertFalse(g.g[C].alive)
        self.assertTrue(g.g.keeps_ability(g.g[C]))
        self.assertTrue(g.g.is_poisoned(g.g[D]))
        self.assertFalse(g.g.is_poisoned(g.g[B]))
        self.assertIn('keeps their ability while dead', g.g.grimoire_text())
        self.day(g, 2)
        self.nominate(g, A, B)
        self.assertFalse(g.g[A].alive)
        self.choose(3, C, [B])
        run(g.night(3))
        self.assertTrue(g.g.has(g.g[B], 'cursed'))

    def test_the_neighbour_poisoned_is_the_nearest_townsfolk_either_way_and_follows_changes(self):
        self.g = g = self.game([T1, O1, 'Witch', O2, T2, T3, 'Vigormortis'], forced={'Vigormortis': {'players': [E]}})
        self.choose(2, G, [C])
        run(g.night(2))
        self.assertTrue(g.g.is_poisoned(g.g[E]))  # Outsiders skipped
        run(g.change(g.g[E], character=O3))
        self.assertTrue(g.g.is_poisoned(g.g[F]))  # the next Townsfolk that way
        self.assertFalse(g.g.is_poisoned(g.g[E]))

    def test_all_of_it_ends_when_the_vigormortis_dies_and_a_drunk_dead_minion_has_no_ability(self):
        self.g = g = self.game(self.CHARS, forced={'Vigormortis': {'players': [D]}})
        self.choose(2, C, [A])
        self.choose(2, E, [C])
        run(g.night(2))
        drunk = State('drunk', C, source=G, until=None)
        g.g.add(drunk)
        self.assertFalse(g.g.works(g.g[C], 'Witch'))
        self.assertFalse(g.g.has(g.g[A], 'cursed'))  # paused
        g.g.states.remove(drunk)
        self.assertTrue(g.g.works(g.g[C], 'Witch'))
        g.kill(g.g[E], 'execution')
        self.assertFalse(g.g.keeps_ability(g.g[C]))
        self.assertFalse(g.g.is_poisoned(g.g[D]))
        self.assertFalse([s for s in g.g.states if s.kind == 'cursed'])  # the Witch's curse ends with their ability

    def test_a_non_minion_it_kills_just_dies(self):
        self.g = g = self.game(self.CHARS)
        self.choose(2, E, [A])
        run(g.night(2))
        self.assertFalse(g.g[A].alive)
        self.assertFalse(g.g.keeps_ability(g.g[A]))


class NoDashiiTests(SNVTest):
    def test_the_nearest_townsfolk_each_way_are_poisoned_skipping_others(self):
        """Example: clockwise from the No Dashii sit a Philosopher, a Mathematician and a Sage; anticlockwise a Witch,
        a Mutant and a Seamstress: the Philosopher and the Seamstress are poisoned."""
        self.g = g = self.game(['No Dashii', T1, T2, T3, T4, O1, 'Witch'])
        poisoned = [p.name for p in g.g.players if g.g.is_poisoned(p)]
        self.assertEqual(poisoned, [B, E])
        self.assertIn('POISONED', g.g.grimoire_text())

    def test_dead_neighbours_stay_poisoned_and_living_ones_beyond_do_not_become_poisoned(self):
        """Example: the Town Crier and the Snake Charmer are poisoned; days later both are dead, and the nearest alive
        neighbours (a Clockmaker and a Barber) are not poisoned."""
        self.g = g = self.game([T1, 'No Dashii', T2, T3, 'Witch', O1, T4])
        g.kill(g.g[A], 'demon')
        g.kill(g.g[C], 'demon')
        self.assertEqual([p.name for p in g.g.players if g.g.is_poisoned(p)], [A, C])
        self.assertFalse(g.g.is_poisoned(g.g[D]))

    def test_the_poison_moves_at_once_and_ends_with_the_no_dashii(self):
        self.g = g = self.game(['No Dashii', T1, T2, T3, T4, 'Witch', T5])
        self.assertTrue(g.g.is_poisoned(g.g[B]))
        run(g.change(g.g[B], character=O1))  # a poisoned Townsfolk becomes an Outsider
        self.assertEqual([p.name for p in g.g.players if g.g.is_poisoned(p)], [C, G])
        self.assertTrue(g.g.impaired(g.g[C]))
        g.kill(g.g[A], 'execution')
        self.assertEqual([p.name for p in g.g.players if g.g.is_poisoned(p)], [])

    def test_the_pit_hag_example(self):
        """Example: the Pit-Hag changes the dead No Dashii into the Flowergirl; next night the alive Fang Gu into the
        No Dashii, who now poisons their two Townsfolk neighbours."""
        self.g = g = self.game([T1, 'No Dashii', T2, 'Pit-Hag', T3, 'Fang Gu', T4],
                               forced={'Pit-Hag deaths': {'players': [], 'yes': True}})
        g.g[B].alive = False
        self.assertEqual([p.name for p in g.g.players if g.g.is_poisoned(p)], [])  # a dead No Dashii poisons nobody
        self.choose(2, D, [B], T5)
        run(g.night(2))
        self.choose(3, D, [F], 'No Dashii')
        run(g.night(3))
        self.assertEqual([p.name for p in g.g.players if g.g.is_poisoned(p)], [E, G])


class VortoxTests(SNVTest):
    CHARS = ['Empath', T1, 'Chef', 'Witch', T2, 'Vortox', T3]

    def test_townsfolk_information_is_always_false_even_drunk_or_with_a_judge(self):
        self.g = g = self.game(self.CHARS)
        for j in (None, judge.RulesJudge()):
            g.judge = j
            for i in range(150):
                g.st.rng = random.Random(i)
                choice = empath_choice(g.g, g.g[A])
                value = run(g.decide_judged(choice))
                self.assertFalse(choice.truth(value), value)
        g.g.add(State('drunk', A, source=G, until=None))
        for i in range(100):
            g.st.rng = random.Random(i)
            choice = empath_choice(g.g, g.g[A])
            self.assertFalse(choice.truth(run(g.decide_judged(choice))))

    def test_the_whole_night_gives_false_information(self):
        self.g = g = self.game(self.CHARS)
        run(g.night(1))
        chef = self.told(C, 'pair')[0]
        self.assertNotIn(' 0 pairs', chef)  # the truth: no evil players sit together
        empath = self.told(A, 'neighbours')[0]
        self.assertNotIn('0 of your', empath)

    def test_a_dead_vortox_falsifies_nothing_and_others_information_is_untouched(self):
        self.g = g = self.game(self.CHARS)
        self.assertTrue(g.g.falsified(g.g[A]))
        self.assertFalse(g.g.falsified(g.g[D]))  # a Minion's
        g.kill(g.g[F], 'execution')
        self.assertFalse(g.g.falsified(g.g[A]))
        choice = empath_choice(g.g, g.g[A])
        self.assertEqual(choice.values, [{**choice.values[0], 'number': 0}])

    def test_if_no_one_is_executed_today_evil_wins(self):
        """Example: a player died from the Witch, five nominations happened, but nobody was executed: evil wins."""
        self.g = g = self.game(self.CHARS)
        self.choose(1, D, [B])
        run(g.night(1))
        self.seats[B].day['nominate'] = [{'nominate': C}]
        run(g.daytime(1))
        self.assertFalse(g.g[B].alive)
        self.assertEqual(g.g.winner, 'evil')

    def test_an_execution_even_of_a_dead_player_or_for_madness_keeps_the_game_going(self):
        """Example: nobody voted or nominated, but the Mutant was executed: the game goes on."""
        self.g = g = self.game(self.CHARS)
        g.g[B].alive = False
        self.seats[A].day['nominate'] = [{'nominate': B}]
        for x in (A, C, D, E, F, G):
            self.seats[x].day['vote'] = [{'vote': True}]
        run(g.daytime(1))
        self.assertIsNone(g.g.winner)
        self.g = g = self.game([T1, T2, O1, T3, 'Cerenovus', 'Vortox', T4], forced={'Madness execution': {'yes': True}})
        self.choose(1, E, [B], 'Chef')
        run(g.night(1))
        run(g.daytime(1))
        self.assertEqual(g.g.executions[0]['player'], B)
        self.assertIsNone(g.g.winner)


class SmokeTests(SNVTest):
    def test_whole_games_with_these_demons_and_minions_run_to_the_end(self):
        """Random seats and random legal setups of the test script (every Demon and Minion here, the Empath and the
        Chef), scripted or with the rules judge hearing all: no crash, and nearly every game ends."""
        from clocktower.agents import RandomSeat
        ended = []
        for seed in range(24):
            r = random.Random(seed)
            n = r.choice([7, 8, 9, 10])  # the test script has ten good characters: three are left for bluffs
            chars = random_setup(r, players=n, script=self.script)
            r.shuffle(chars)
            names = ALL_NAMES[:n]
            seats = {x: RandomSeat(x, random.Random(seed * 13 + i), names) for i, x in enumerate(names)}
            g = Game(seats, Forced(), names=names, seed=seed, characters=chars, script=self.script, probes=False,
                     private_beats=1, public_beats=1, max_days=12, judge=judge.RulesJudge('all') if seed % 2 else None)
            result = run(g.run())
            ended.append(result['winner'])
            self.assertTrue(result['winner'] or result['stopped'].startswith('stopped after'), result['reason'])
        self.assertGreater(sum(w is not None for w in ended), 18, ended)


class NotesTests(SNVTest):
    def test_every_built_character_has_storyteller_notes_and_the_judge_reads_them(self):
        sections = judge._sections(judge.NOTES / 'snv.md')
        built = [n for n in official.script('snv')[1] if n in ch.CHARACTERS]
        self.assertEqual(set(sections), set(built))
        self.assertTrue(all(len(v.split()) >= 30 for v in sections.values()))
        self.g = g = self.game(CerenovusTests.CHARS)
        self.say(g, B, 'I am the Chef.')
        text = judge.prompt(g, madness_choice(g.g, g.g[B], 'Chef', True, judge.madness_evidence(g, B, 'Chef', 1)))
        self.assertRegex(text, r'(?m)^Cerenovus: ')
        self.assertIn('did they break their madness', text)


if __name__ == '__main__':
    unittest.main()
