"""Batch 2 of the experimental characters (clocktower/carousel2.py): the Pixie, High Priestess, Poppy Grower,
Shugenja, Balloonist, General, Preacher, Cannibal, Puzzlemaster, Heretic, Marionette, Widow, Goblin, Kazali and
Leviathan, each edge their text implies, and every official jinx between them and a built character
(docs/carousel-rulings.md, batch 2)."""
import io
import random
import unittest

from clocktower import carousel, carousel2, smoke
from clocktower import characters as ch
from clocktower.game import ALL_NAMES, NAMES, Game
from clocktower.state import Grimoire, random_setup, setup_error

from test_carousel import JINXES2, O1, T1, T2, T3, T4, run
from test_carousel1 import Batch1Test, Forced, Seat

A, B, C, D, E, F, G, H, I = NAMES


class Batch2Test(Batch1Test):
    def dealt(self, chars, jinxed=True, forced=None, extra=()):
        names = ALL_NAMES[:len(chars)]
        script = self.script(list(chars) + list(extra) + ['Soldier', 'Empath', 'Chef', 'Undertaker'], jinxed)
        self.seats = {n: Seat() for n in names}
        g = Game(self.seats, Forced(forced), names=names, seed=3, characters=chars, script=script, probes=False,
                 private_beats=1, public_beats=1)
        run(g.setup())
        self.g = g
        return g

    def say(self, name, text, kind='say'):
        key = 'nominee' if kind == 'defense' else 'speaker'
        self.g.emit(kind, {key: name, 'text': text})

    def finish(self, winner, reason='test'):
        self.g.g.winner, self.g.g.reason = winner, reason
        self.g.g.finish()
        return self.g.g.winner

    def values(self, cid):
        return self.g.st.seen[cid].values


# ---- Townsfolk ---------------------------------------------------------------------------------------------------

class PixieTests(Batch2Test):
    CHARS = ['Pixie', 'Monk', T2, 'Poisoner', 'Imp', T3]

    def test_learns_an_in_play_townsfolk_and_is_mad_about_it(self):
        for seed in range(5):
            g = self.game(self.CHARS)
            g.st.rng = random.Random(seed)
            self.choose(1, D, [E])
            run(g.night(1))
            told = self.told(A, 'Pixie: the ')
            self.assertEqual(len(told), 1)
            c = g.g.notes['Pixie'][A]
            self.assertIn(c, ('Monk', T2, T3))
            self.assertTrue(any(s.kind == 'mad' and s.target == A and s.about == c for s in g.g.states))

    def test_poisoned_or_under_the_vortox_a_townsfolk_not_in_play(self):
        g = self.game(self.CHARS, forced={'Pixie': {'character': T4}}, extra=[T4])
        self.choose(1, D, [A])
        run(g.night(1))
        self.assertTrue(self.told(A, f'the {T4} is in play'))
        g = self.game(['Pixie', 'Monk', T2, 'Poisoner', 'Vortox', T3], extra=[T4])
        self.choose(1, D, [B])
        run(g.night(1))
        self.assertIn(g.g.notes['Pixie'][A], (T1, T4))

    def test_gains_the_ability_when_they_die_if_mad_and_not_otherwise(self):
        for claimed in (True, False):
            g = self.game(self.CHARS, forced={'Pixie': {'character': 'Monk'}})
            self.choose(1, D, [E])
            run(g.night(1))
            if claimed:
                self.say(A, 'I am the Monk, trust me.')
            self.day(g, 1)
            g.execute(B)
            run(g.run_pending())
            self.assertEqual(g.g[A].extra, ['Monk'] if claimed else [])
            self.assertEqual(bool(self.told(A, "now have the Monk's ability")), claimed)

    def test_a_poisoned_or_dead_pixie_gains_nothing(self):
        g = self.game(self.CHARS, forced={'Pixie': {'character': 'Monk'}})
        self.choose(1, D, [E])
        run(g.night(1))
        self.say(A, 'I am the Monk.')
        self.poison(A)
        g.execute(B)
        run(g.run_pending())
        self.assertEqual(g.g[A].extra, [])
        g = self.game(self.CHARS, forced={'Pixie': {'character': 'Monk'}})
        run(g.night(1))
        self.say(A, 'I am the Monk.')
        g.g[A].alive = False
        g.execute(B)
        run(g.run_pending())
        self.assertEqual(g.g[A].extra, [])


class HighPriestessTests(Batch2Test):
    CHARS = ['High Priestess', T1, T2, 'Poisoner', 'Imp', T3]

    def test_each_night_a_living_player_of_their_team(self):
        for seed in range(5):
            g = self.game(self.CHARS)
            g.st.rng = random.Random(seed)
            self.choose(1, D, [E])
            run(g.night(1))
            told = self.told(A, 'you should talk to')
            self.assertEqual(len(told), 1)
            self.assertTrue(any(f'talk to {x} most' in told[0] for x in (B, C, F)), told)
        self.choose(2, D, [F])
        self.choose(2, E, [B])
        run(g.night(2))
        self.assertEqual(len(self.told(A, 'you should talk to')), 2)
        self.assertFalse(any(f'talk to {B}' in t for t in self.told(A, 'you should talk to')[1:]))

    def test_poisoned_anyone_and_under_the_vortox_the_other_team(self):
        g = self.game(self.CHARS, forced={'High Priestess': {'players': [E]}})
        self.choose(1, D, [A])
        run(g.night(1))
        self.assertTrue(self.told(A, f'talk to {E} most'))
        g = self.game(['High Priestess', T1, T2, 'Poisoner', 'Vortox', T3])
        self.choose(1, D, [B])
        run(g.night(1))
        self.assertTrue(self.told(A, f'talk to {D} most') or self.told(A, f'talk to {E} most'))


class PoppyGrowerTests(Batch2Test):
    CHARS = ['Poppy Grower', T1, T2, T3, T4, 'Poisoner', 'Imp', 'Spy', 'Monk', 'Mayor']

    def test_the_evil_team_does_not_learn_each_other(self):
        self.dealt(self.CHARS)
        for x in (F, G, H):
            self.assertTrue(self.intro(x, 'You do not learn who the other evil players are.'))
        self.assertFalse(self.intro(G, 'Your Minions'))
        self.assertTrue(self.intro(G, 'Three good characters not in play'))

    def test_when_the_poppy_grower_dies_they_learn_each_other_that_night(self):
        g = self.dealt(self.CHARS)
        self.choose(1, F, [B])
        run(g.night(1))
        self.day(g, 1)
        g.execute(A)
        self.choose(2, F, [B])
        self.choose(2, G, [C])
        run(g.night(2))
        self.assertTrue(self.told(F, f'The Demon is {G}. Your fellow Minions: {H}.'))
        self.assertTrue(self.told(G, f'you learn who your Minions are: {F}, {H}'))

    def test_a_drunk_or_poisoned_poppy_grower_keeps_no_one_apart(self):
        self.dealt(['Drunk', T1, T2, T3, T4, 'Poisoner', 'Imp', 'Monk'], extra=['Poppy Grower'],
                   forced={'drunk_as': {'character': 'Poppy Grower'}})
        self.assertTrue(self.intro(F, f'The Demon is {G}.'))
        g = self.dealt(self.CHARS)
        self.choose(1, F, [B])
        run(g.night(1))
        self.poison(A)
        self.choose(2, F, [B])
        self.choose(2, G, [C])
        run(g.night(2))  # poisoned at the Poppy Grower's step: they learn now
        self.assertTrue(self.told(G, 'you learn who your Minions are'))

    def test_the_spy_jinx_no_grimoire_while_the_poppy_grower_has_their_ability(self):
        for jinxed in self.both():
            g = self.dealt(self.CHARS, jinxed)
            self.choose(1, F, [B])
            run(g.night(1))
            self.assertEqual(bool(self.told(H, 'Spy: you look at the Grimoire')), not jinxed)
        g.execute(A)
        self.choose(2, F, [B])
        self.choose(2, G, [C])
        run(g.night(2))
        self.assertTrue(self.told(H, 'Spy: you look at the Grimoire'))

    def test_the_widow_jinx_no_grimoire_while_the_poppy_grower_has_their_ability(self):
        for jinxed in self.both():
            g = self.dealt(['Poppy Grower', T1, T2, T3, T4, 'Widow', 'Imp', O1], jinxed)
            self.choose(1, F, [B])
            run(g.night(1))
            self.assertEqual(bool(self.told(F, 'Widow: you look at the Grimoire')), not jinxed)

    def test_the_summoner_jinx_the_storyteller_chooses_the_player(self):
        g = self.game(['Poppy Grower', T1, T2, T3, 'Summoner', T4, O1], extra=['Imp'],
                      forced={'Summoned player': {'players': [C]}})
        self.choose(3, E, [B], character='Imp')
        run(g.night(3))
        self.assertEqual((g.g[C].character, g.g[B].character), ('Imp', T1))
        g = self.game(['Poppy Grower', T1, T2, T3, 'Summoner', T4, O1], jinxed=False, extra=['Imp'],
                      forced={'Summoned player': {'players': [C]}})
        self.choose(3, E, [B], character='Imp')
        run(g.night(3))
        self.assertEqual(g.g[B].character, 'Imp')


class ShugenjaTests(Batch2Test):
    def test_the_direction_of_the_closest_evil_player(self):
        g = self.game(['Shugenja', T1, 'Poisoner', T2, T3, T4, 'Imp'])  # 2 clockwise, 1 anticlockwise
        self.choose(1, C, [B])
        run(g.night(1))
        self.assertTrue(self.told(A, 'closest evil player is anticlockwise'))
        g = self.game(['Shugenja', 'Poisoner', T1, T2, T3, 'Imp', T4])
        self.choose(1, B, [C])
        run(g.night(1))
        self.assertTrue(self.told(A, 'closest evil player is clockwise'))

    def test_equidistant_either_and_a_spy_or_recluse_registers(self):
        choice = carousel2.shugenja_choice(self.game(['Shugenja', 'Poisoner', T1, T2, T3, T4, 'Imp']).g, self.g.g[A])
        self.assertEqual(len(choice.values), 2)
        g = self.game(['Shugenja', 'Spy', T1, T2, T3, 'Imp', T4])
        self.assertEqual(len(carousel2.shugenja_choice(g.g, g.g[A]).values), 2)  # the Spy may register good
        g = self.game(['Shugenja', 'Recluse', T1, T2, T3, 'Imp', T4])
        self.assertEqual(len(carousel2.shugenja_choice(g.g, g.g[A]).values), 2)  # the Recluse may register evil

    def test_poisoned_the_wrong_way_is_legal(self):
        g = self.game(['Shugenja', 'Poisoner', T1, T2, T3, 'Imp', T4], forced={'Shugenja': {'yes': False}})
        self.choose(1, B, [C])
        run(g.night(1))  # sober: only the truth is legal (one value: no decision)
        self.assertTrue(self.told(A, 'is clockwise'))
        g = self.game(['Shugenja', 'Poisoner', T1, T2, T3, 'Imp', T4], forced={'Shugenja': {'yes': False}})
        self.choose(1, B, [A])
        run(g.night(1))
        self.assertTrue(self.told(A, 'anticlockwise'))


    def test_under_the_vortox_the_wrong_way_and_a_drunk_shugenja_is_woken(self):
        g = self.game(['Shugenja', 'Poisoner', T1, T2, T3, 'Vortox', T4])
        self.choose(1, B, [C])
        run(g.night(1))
        self.assertTrue(self.told(A, 'is anticlockwise'))
        g = self.game(['Drunk', 'Poisoner', T1, T2, T3, 'Imp', T4], extra=['Shugenja'])
        g.g[A].shown = 'Shugenja'
        self.choose(1, B, [C])
        run(g.night(1))
        self.assertTrue(self.told(A, 'Shugenja: your closest evil player is'))


class BalloonistTests(Batch2Test):
    CHARS = ['Balloonist', T1, O1, 'Poisoner', 'Imp', T2]

    def test_each_night_a_player_of_a_different_type_than_last_nights(self):
        g = self.game(self.CHARS, forced={'Balloonist': {'players': [B]}})
        self.choose(1, D, [E])
        run(g.night(1))
        self.assertEqual(g.g.notes['Balloonist'][A], 'Townsfolk')
        g.st.forced = {}
        self.choose(2, D, [E])
        self.choose(2, E, [C])
        run(g.night(2))
        values = [v['players'][0] for v in self.values(f'Balloonist:{A}')]
        self.assertEqual(sorted(values), sorted([C, D, E]))  # not a Townsfolk
        self.assertNotEqual(g.g.notes['Balloonist'][A], 'Townsfolk')

    def test_poisoned_a_player_of_the_same_type_is_legal(self):
        g = self.game(self.CHARS, forced={'Balloonist': {'players': [B]}})
        self.choose(1, D, [E])
        run(g.night(1))
        g.st.forced = {'Balloonist': {'players': [F]}}
        self.choose(2, D, [A])
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertTrue(self.told(A, f'{F} is of a different character type'))

    def test_under_the_vortox_the_same_type_again(self):
        g = self.game(['Balloonist', T1, O1, 'Poisoner', 'Vortox', T2], forced={'Balloonist': {'players': [B]}})
        self.choose(1, D, [C])
        run(g.night(1))
        g.st.forced = {}
        self.choose(2, D, [C])
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertEqual(g.g.notes['Balloonist'][A], 'Townsfolk')

    def test_an_outsider_might_be_added_at_setup(self):
        names = NAMES[:7]
        chars = ['Balloonist', T1, T2, T3, T4, 'Poisoner', 'Imp']
        script = self.script(chars + [O1], True)
        g = Game({n: Seat() for n in names}, Forced({'Balloonist outsider': {'yes': True},
                                                     'Extra Outsider': {'players': [B], 'character': O1}}),
                 names=names, seed=1, script=script, probes=False)
        g.g = Grimoire(names, chars, script=script)
        run(ch.rules('Balloonist').setup(g))
        self.assertEqual(g.g[B].character, O1)
        self.assertIsNone(setup_error([p.character for p in g.g.players], script))

    def test_the_marionette_jinx_an_outsider_for_a_marionette_who_believes_they_are_the_balloonist(self):
        g = self.dealt([T1, T2, T3, 'Marionette', 'Imp', T4, 'Monk'], extra=['Balloonist', O1],
                       forced={'Marionette:': {'character': 'Balloonist'}, 'Balloonist outsider': {'yes': True},
                               'Extra Outsider': {'players': [A], 'character': O1}})
        self.assertEqual(g.g[D].shown, 'Balloonist')
        self.assertEqual(g.g[A].character, O1)


class GeneralTests(Batch2Test):
    CHARS = ['General', T1, T2, 'Poisoner', 'Imp', T3]

    def test_learns_the_heuristics_belief_and_a_judge_may_say_otherwise(self):
        g = self.game(self.CHARS)
        self.choose(1, D, [E])
        run(g.night(1))
        self.assertTrue(self.told(A, 'neither team is winning'))
        choice = self.g.st.seen[f'General:{A}']
        self.assertEqual((len(choice.values), choice.truth), (3, None))
        g = self.game(self.CHARS)
        for x in (B, C):
            g.g[x].alive = False
        self.choose(2, D, [E])
        self.choose(2, E, [F])
        run(g.night(2))
        self.assertTrue(self.told(A, 'evil is winning'))

    def test_poisoned_or_under_the_vortox_another_answer(self):
        g = self.game(self.CHARS, forced={'General': {'statements': ['good']}})
        self.choose(1, D, [A])
        run(g.night(1))
        self.assertTrue(self.told(A, 'good is winning'))
        g = self.game(['General', T1, T2, 'Poisoner', 'Vortox', T3])
        self.choose(1, D, [B])
        run(g.night(1))
        self.assertFalse(self.told(A, 'neither team is winning'))


class PreacherTests(Batch2Test):
    CHARS = ['Preacher', T1, T2, 'Poisoner', 'Imp', T3]

    def test_a_chosen_minion_learns_it_and_has_no_ability_while_the_preacher_has_theirs(self):
        g = self.game(self.CHARS)
        self.choose(1, A, [D])
        self.choose(1, D, [B])
        run(g.night(1))
        self.assertTrue(self.told(D, 'the Preacher selected you'))
        self.assertFalse(g.g.is_poisoned(g.g[B]))  # the Poisoner chose after losing their ability
        self.assertTrue(g.g.impaired(g.g[D]))
        g.g[A].alive = False
        self.assertFalse(g.g.impaired(g.g[D]))  # a dead Preacher: the Minion has their ability again

    def test_a_non_minion_or_a_drunk_preacher_nothing(self):
        g = self.game(self.CHARS)
        self.choose(1, A, [B])
        run(g.night(1))
        self.assertFalse(self.told(B, 'Preacher'))
        g = self.game(self.CHARS)
        self.poison(A)
        self.choose(1, A, [D])
        run(g.night(1))
        self.assertFalse(self.told(D, 'Preacher'))
        self.assertFalse(g.g.impaired(g.g[D]))

    def test_the_summoner_jinx_the_storyteller_summons_for_a_preached_summoner(self):
        for jinxed in self.both():
            g = self.game(['Preacher', T1, T2, T3, 'Summoner', T4, O1], jinxed, extra=['Imp'],
                          forced={'Summoner:': {'players': [C], 'character': 'Imp'}})
            g.g.notes['Preached'] = {A: [E]}
            self.choose(3, E, [B], character='Imp')
            self.choose(3, A, [B])
            run(g.night(3))
            self.assertEqual(g.g[C].character == 'Imp', jinxed)
            self.assertEqual(g.g.notes['Summoned'], 3 if jinxed else 'failed')


class CannibalTests(Batch2Test):
    CHARS = ['Cannibal', 'Empath', T2, 'Poisoner', 'Imp', T3]

    def test_a_good_executee_gives_their_ability(self):
        g = self.game(self.CHARS)
        g.execute(B)
        run(g.run_pending())
        self.assertEqual(g.g[A].extra, ['Empath'])
        self.choose(2, D, [F])
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertTrue(self.told(A, 'Empath:'))

    def test_an_evil_executee_poisons_the_cannibal_until_a_good_player_dies_by_execution(self):
        g = self.game(self.CHARS + ['Butler', T4])
        self.say(D, 'I am the Empath.')
        g.execute(D)
        run(g.run_pending())
        self.assertTrue(g.g.is_poisoned(g.g[A]))
        self.assertEqual(len(g.g[A].extra), 1)
        self.assertNotIn(g.g[A].extra[0], ('Poisoner', 'Cannibal'))
        self.day(g, 2)
        g.execute(C)
        run(g.run_pending())
        self.assertFalse(g.g.is_poisoned(g.g[A]))
        self.assertEqual(g.g[A].extra, [T2])

    def test_a_dead_cannibal_or_a_survived_execution_nothing(self):
        g = self.game(self.CHARS)
        g.g[A].alive = False
        g.execute(B)
        self.assertEqual(g.g[A].extra, [])

    def test_the_butler_jinx_the_cannibal_learns_it(self):
        for jinxed in self.both():
            g = self.game(['Cannibal', 'Butler', T2, 'Poisoner', 'Imp', T3], jinxed)
            g.execute(B)
            run(g.run_pending())
            self.assertEqual(bool(self.told(A, "gained the Butler's ability")), jinxed)

    def test_the_juggler_jinx_the_cannibal_learns_the_executed_jugglers_count(self):
        for jinxed in self.both():
            g = self.game(['Cannibal', 'Juggler', T2, 'Poisoner', 'Imp', T3], jinxed)
            ch.rules('Juggler').act_publicly(g, B, None, guesses=[{'player': D, 'character': 'Poisoner'},
                                                                  {'player': E, 'character': T2}])
            g.execute(B)
            run(g.run_pending())
            self.choose(2, D, [F])
            self.choose(2, E, [C])
            run(g.night(2))
            self.assertEqual(bool(self.told(A, 'the Juggler you ate made 1 correct guess')), jinxed)


# ---- Outsiders ---------------------------------------------------------------------------------------------------

class PuzzlemasterTests(Batch2Test):
    CHARS = ['Puzzlemaster', T1, T2, 'Poisoner', 'Imp', T3]

    def dealt_pm(self, forced=None):
        g = self.dealt(self.CHARS, forced={'Puzzlemaster:': {'players': [B]}, **(forced or {})})
        self.day(g, 1)
        return g

    def guess(self, g, text, who=A):
        return run(g.visit_judged(who, {'character': 'Puzzlemaster', 'text': text}))

    def test_one_player_is_drunk_even_if_the_puzzlemaster_dies_not_while_they_are_poisoned(self):
        g = self.dealt_pm()
        self.assertTrue(g.g.is_drunk(g.g[B]))
        g.g[A].alive = False
        self.assertTrue(g.g.is_drunk(g.g[B]))
        g.g[A].alive = True
        self.poison(A)
        self.assertFalse(g.g.is_drunk(g.g[B]))

    def test_a_right_guess_learns_the_demon_a_wrong_one_false_info_once(self):
        g = self.dealt_pm()
        self.guess(g, f'I think it is {B}.')
        self.assertTrue(self.told(A, f'you guessed {B}. The Storyteller shows you the Demon: {E}.'))
        self.day(g, 2)
        self.guess(g, f'{C}?')
        self.assertTrue(self.told(A, 'already made your guess'))
        g = self.dealt_pm()
        self.guess(g, f'Is it {C}?')
        told = self.told(A, f'you guessed {C}')[0]
        self.assertNotIn(f'the Demon: {E}', told)

    def test_naming_no_one_or_two_players_is_no_guess_and_others_get_a_nod(self):
        g = self.dealt_pm()
        self.guess(g, f'{B} or {C}')
        self.assertTrue(self.told(A, 'name exactly one other player'))
        self.guess(g, f'{B}', who=C)
        self.assertTrue(self.told(C, 'listened and nodded'))
        self.day(g, 2)
        self.guess(g, f'{B}')
        self.assertTrue(self.told(A, 'the Demon: '))


class HereticTests(Batch2Test):
    CHARS = ['Heretic', T1, T2, 'Poisoner', 'Imp', T3]

    def test_whoever_wins_loses_even_dead_not_drunk(self):
        g = self.game(self.CHARS)
        self.assertEqual(self.finish('good'), 'evil')
        g = self.game(self.CHARS)
        g.g[A].alive = False
        self.assertEqual(self.finish('evil'), 'good')
        g = self.game(self.CHARS)
        self.poison(A)
        self.assertEqual(self.finish('good'), 'good')

    def test_every_ending_the_saints_too_and_after_the_politician(self):
        g = self.game(['Heretic', 'Saint', T2, 'Poisoner', 'Imp', T3])
        g.execute(B)
        self.assertEqual(g.g.winner, 'evil')
        g.g.finish()
        self.assertEqual(g.g.winner, 'good')
        g = self.game(['Politician', 'Heretic', T2, 'Poisoner', 'Imp', T3])
        self.day(g, 2)
        g.g.nominations.append({'day': 2, 'nominator': A, 'nominee': E})
        g.execute(E)
        g.g.finish()
        self.assertEqual((g.g[A].alignment, g.g.winner), ('good', 'evil'))

    def test_only_one_of_its_jinxed_pairs_is_ever_in_play(self):
        for m in ('Spy', 'Baron', 'Godfather', 'Pit-Hag', 'Widow'):
            s = self.script(['Heretic', m, 'Imp', 'Poisoner', 'Monk', 'Mayor', 'Sage', 'Saint', 'Butler'], True)
            self.assertIn('only one of', setup_error(['Heretic', m, T1, T2, 'Imp'], s))
            for seed in range(30):
                chars = random_setup(random.Random(seed), m, 8, s)
                self.assertFalse({'Heretic', m} <= set(chars))
        unjinxed = self.script(['Heretic', 'Spy', T1, T2, T3, 'Imp'], False)
        self.assertIsNone(setup_error(['Heretic', 'Spy', T1, T2, T3, 'Imp'], unjinxed))

    def test_the_pit_hag_cannot_make_a_jinxed_pair_nor_the_tea_party(self):
        g = self.game(['Heretic', T1, T2, 'Pit-Hag', 'Imp', T3], extra=['Spy'])
        self.choose(2, D, [B], character='Spy')
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertEqual(g.g[B].character, T1)
        g = self.game(['Hatter', T1, T2, 'Poisoner', 'Imp', 'Heretic'], extra=['Spy', 'Witch'])
        self.assertEqual(carousel.tea_party_options(g.g, g.g[D]), ['Witch'])


# ---- Minions -----------------------------------------------------------------------------------------------------

class MarionetteTests(Batch2Test):
    CHARS = ['Marionette', T1, T2, T3, 'Imp', O1, T4, 'Monk']

    def test_neighbours_the_demon_believes_good_and_the_demon_knows(self):
        for seed in range(4):
            g = self.dealt(self.CHARS, extra=['Empath', 'Washerwoman'])
            g.st.rng = random.Random(seed)
            m = next(p for p in g.g.players if p.character == 'Marionette')
            demon = g.g.demon()
            self.assertTrue(carousel2.adjacent(g.g, m, demon))
            self.assertEqual(ch.kind(m.shown) in ('Townsfolk', 'Outsider'), True)
            self.assertNotIn(m.shown, {p.character for p in g.g.players})
            self.assertTrue(self.intro(demon.name, f'{m.name} is the Marionette'))
            self.assertFalse(self.intro(m.name, 'Demon'))
            self.assertTrue(g.g.unreliable(m))

    def test_the_magician_jinx_the_demon_does_not_know_which_neighbour(self):
        for jinxed in self.both():
            self.dealt([T1, T2, T3, 'Marionette', 'Imp', O1, 'Magician', T4], jinxed)
            told = self.intro(E, 'Marionette')[0]
            self.assertEqual(f'One of your neighbours, {D} or {F}' in told, jinxed)

    def test_the_mathematician_jinx_the_marionettes_false_info_is_abnormal(self):
        for jinxed in self.both():
            g = self.game(['Marionette', 'Imp', T2, 'Poisoner', 'Mathematician', T3], jinxed, extra=['Empath'],
                          forced={'Empath:': {'number': 0}})
            g.g[A].shown = 'Empath'
            g.g[B].alignment = 'evil'
            self.choose(1, D, [C])
            run(g.night(1))
            self.assertEqual(any(a['player'] == A for a in g.g.abnormal), jinxed)

    def test_the_summoner_jinx_the_marionette_enters_beside_the_summoned_demon(self):
        g = self.dealt([T1, 'Marionette', T2, T3, 'Summoner', T4, 'Monk', 'Mayor', 'Sage', 'Exorcist'],
                       extra=['Imp'])
        self.assertNotEqual(g.g[B].character, 'Marionette')
        self.assertEqual(g.g[B].alignment, 'good')
        self.assertTrue(g.g.notes.get('Marionette waiting'))
        for n in (1, 2):
            run(g.night(n))
        self.choose(3, E, [C], character='Imp')
        run(g.night(3))
        self.assertEqual(g.g[C].character, 'Imp')
        m = [p for p in g.g.players if p.character == 'Marionette']
        self.assertEqual(len(m), 1)
        self.assertIn(m[0].name, (B, D))
        self.assertTrue(m[0].evil and m[0].shown != 'Marionette')
        self.assertTrue(self.told(C, f'{m[0].name} is now the Marionette'))

    def test_the_plague_doctor_jinx_a_good_neighbour_of_the_demon_becomes_the_marionette(self):
        g = self.game(['Plague Doctor', T1, T2, 'Imp', T3, 'Poisoner'], extra=['Marionette'])
        g.execute(A)
        run(g.run_pending())
        self.assertEqual(g.g.notes['Storyteller ability'], 'Marionette')
        m = [p for p in g.g.players if p.character == 'Marionette']
        self.assertEqual([p.name for p in m], [C] if m[0].name == C else [E])
        self.assertTrue(m[0].evil)


class WidowTests(Batch2Test):
    CHARS = [T1, T2, T3, T4, 'Widow', 'Imp', O1]

    def test_sees_the_grimoire_poisons_and_a_good_player_learns_a_widow_is_in_play(self):
        g = self.game(self.CHARS)
        self.choose(1, E, [B])
        run(g.night(1))
        self.assertTrue(self.told(E, 'Widow: you look at the Grimoire.\n1. '))
        self.assertTrue(g.g.is_poisoned(g.g[B]))
        knows = [x for x in (A, B, C, D, G) if self.told(x, 'a Widow is in play')]
        self.assertEqual(len(knows), 1)
        self.choose(2, F, [C])
        run(g.night(2))
        self.assertTrue(g.g.is_poisoned(g.g[B]))
        g.g[E].alive = False
        g.g.die(g.g[E])
        self.assertFalse(g.g.is_poisoned(g.g[B]))

    def test_a_drunk_widow_poisons_nobody_but_a_good_player_still_learns(self):
        g = self.game(self.CHARS)
        self.poison(E)
        self.choose(1, E, [B])
        run(g.night(1))
        self.assertFalse(g.g.is_poisoned(g.g[B]))
        self.assertTrue(any(self.told(x, 'a Widow is in play') for x in (A, B, C, D, G)))

    def test_the_magician_jinx_tokens_removed(self):
        for jinxed in self.both():
            g = self.game(['Magician', T1, T2, T3, 'Widow', 'Imp', O1], jinxed)
            self.choose(1, E, [B])
            run(g.night(1))
            seen = self.told(E, 'Widow: you look at the Grimoire')[0]
            self.assertEqual(f'1. {A}: (token removed)' in seen, jinxed)

    def test_the_damsel_jinx_poisoned_once_a_widow_has_been_in_play(self):
        for jinxed in self.both():
            g = self.dealt([T1, T2, 'Damsel', T3, T4, 'Widow', 'Imp', 'Monk'], jinxed)
            self.assertEqual(g.g.is_poisoned(g.g[C]), jinxed)


class GoblinTests(Batch2Test):
    CHARS = [T1, T2, T3, 'Goblin', 'Imp', T4]

    def nominate(self, g, who, by=A):
        g.emit('nomination', {'nominator': by, 'nominee': who, 'text': ''})
        g.g.nominations.append({'day': g.day, 'nominator': by, 'nominee': who})

    def test_claimed_when_nominated_and_executed_evil_wins(self):
        g = self.game(self.CHARS)
        self.nominate(g, D)
        self.say(D, "Fine: I am the Goblin. Execute me if you dare.", 'defense')
        g.execute(D)
        self.assertEqual(g.g.winner, 'evil')

    def test_no_claim_a_claim_before_the_nomination_or_a_poisoned_goblin_nothing(self):
        g = self.game(self.CHARS)
        self.nominate(g, D)
        g.execute(D)
        self.assertIsNone(g.g.winner)
        g = self.game(self.CHARS)
        self.say(D, 'I am the Goblin.')
        self.nominate(g, D)
        g.execute(D)
        self.assertIsNone(g.g.winner)
        g = self.game(self.CHARS)
        self.poison(D)
        self.nominate(g, D)
        g.emit('ability', {'player': D, 'character': 'Goblin'})
        g.execute(D)
        self.assertIsNone(g.g.winner)

    def test_the_cerenovus_jinx_a_player_may_be_made_mad_that_they_are_the_goblin(self):
        for jinxed in self.both():
            g = self.game([T1, T2, T3, 'Cerenovus', 'Imp', T4], jinxed, extra=['Goblin'])
            self.choose(1, D, [A], character='Goblin')
            run(g.night(1))
            req = [r for r in self.seats[D].log if r.kind == 'night' and r.characters][0]
            self.assertEqual('Goblin' in req.characters, jinxed)
            if jinxed:
                self.assertTrue(any(s.kind == 'mad' and s.about == 'Goblin' for s in g.g.states))

    def test_the_plague_doctor_jinx_a_minion_gains_the_goblin_ability(self):
        g = self.game(['Plague Doctor', T1, T2, 'Poisoner', 'Imp', T3], extra=['Goblin'])
        g.execute(A)
        run(g.run_pending())
        self.assertEqual(g.g[D].extra, ['Goblin'])
        self.assertTrue(self.told(D, "gain the Goblin's ability"))
        self.day(g, 2)
        self.nominate(g, D)
        self.say(D, 'I am the Goblin!', 'defense')
        g.execute(D)
        self.assertEqual(g.g.winner, 'evil')


# ---- Demons ------------------------------------------------------------------------------------------------------

class KazaliTests(Batch2Test):
    def test_no_minions_are_dealt_townsfolk_in_their_place(self):
        s = self.script(['Kazali', 'Poisoner', 'Spy', 'Baron', 'Monk', 'Soldier', 'Mayor', 'Sage', 'Empath', 'Chef',
                         'Butler', 'Saint', 'Recluse'], True)
        for n in (5, 9, 12):
            for seed in range(10):
                chars = random_setup(random.Random(seed), 'Poisoner', n, s)
                if 'Kazali' in chars:
                    self.assertFalse([c for c in chars if ch.kind(c) == 'Minion'])
                    self.assertIsNone(setup_error(chars, s))
        self.assertIsNotNone(setup_error(['Kazali', 'Poisoner', T1, T2, T3], s))

    def test_on_the_first_night_the_kazali_chooses_which_players_are_which_minions(self):
        g = self.dealt(['Kazali', T1, T2, T3, T4, 'Monk', 'Soldier', 'Mayor', O1, 'Butler'],
                       extra=['Poisoner', 'Spy', 'Baron'])
        self.assertTrue(self.intro(A, 'No player is a Minion yet'))
        self.seats[A].day['night'] = [{'targets': [C], 'character': 'Spy'}, {'targets': [D], 'character': 'Poisoner'}]
        run(g.night(1))
        self.assertEqual((g.g[C].character, g.g[D].character), ('Spy', 'Poisoner'))
        self.assertTrue(g.g[C].evil and g.g[D].evil)
        self.assertTrue(self.told(C, f'the Demon is {A}. Your fellow Minions: {D}.'))
        self.assertTrue(self.told(D, 'you are now the Poisoner'))

    def test_the_storyteller_may_change_the_outsider_count_at_setup(self):
        names = NAMES[:7]
        chars = ['Kazali', T1, T2, T3, T4, 'Monk', 'Mayor']
        script = self.script(chars + ['Poisoner', O1], True)
        g = Game({n: Seat() for n in names}, Forced({'Kazali outsiders': {'number': 1},
                                                     'Extra Outsider': {'players': [B], 'character': O1}}),
                 names=names, seed=1, script=script, probes=False)
        g.g = Grimoire(names, chars, script=script)
        run(ch.rules('Kazali').setup(g))
        self.assertEqual(g.g[B].character, O1)
        self.assertIsNone(setup_error([p.character for p in g.g.players], script))

    def test_a_grandchild_made_a_minion_before_the_first_night_is_still_shown(self):
        from clocktower.bmr import grandmother_choice
        g = self.game(['Grandmother', 'Poisoner', T2, T3, 'Kazali'])
        g.g.notes['Grandchild'] = B
        self.poison(A)
        self.assertIn({'players': [B], 'character': 'Poisoner'},
                      [{'players': v['players'], 'character': v['character']}
                       for v in grandmother_choice(g.g, g.g[A], B).values])

    def test_kills_on_other_nights(self):
        g = self.game(['Kazali', T1, T2, 'Poisoner', T3])
        self.choose(2, D, [C])
        self.choose(2, A, [B])
        run(g.night(2))
        self.assertFalse(g.g[B].alive)

    def test_the_marionette_jinx_only_a_neighbour_who_keeps_believing(self):
        g = self.dealt(['Kazali', T1, T2, T3, T4, 'Monk', 'Soldier'], extra=['Marionette', 'Poisoner'])
        self.seats[A].day['night'] = [{'targets': [D], 'character': 'Marionette'},
                                      {'targets': [B], 'character': 'Marionette'}]
        run(g.night(1))
        self.assertEqual((g.g[B].character, g.g[B].shown, g.g[B].alignment), ('Marionette', T1, 'evil'))
        self.assertEqual(g.g[D].character, T3)
        self.assertFalse(self.told(B, 'Marionette'))

    def test_the_summoner_jinx_a_second_living_demon_makes_deaths_arbitrary(self):
        g = self.game(['Kazali', T1, T2, 'Summoner', T3, T4, O1], forced={'Summoner deaths': {'players': [],
                                                                                               'yes': True}})
        g.g.notes['Kazali chose'] = True
        self.choose(3, D, [B], character='Kazali')
        self.choose(3, A, [C])
        run(g.night(3))
        self.assertIn('Summoner deaths:Blair', g.st.seen)

    def test_the_heretic_jinx_no_jinxed_minion_with_the_heretic_in_play(self):
        g = self.dealt(['Kazali', T1, T2, T3, 'Heretic'], extra=['Spy', 'Poisoner'])
        run(g.night(1))
        req = [r for r in self.seats[A].log if r.kind == 'night'][0]
        self.assertEqual(req.characters, ['Poisoner'])


class LeviathanTests(Batch2Test):
    CHARS = [T1, T2, T3, T4, 'Poisoner', 'Leviathan', O1]

    def test_announced_and_a_second_good_execution_wins_for_evil(self):
        g = self.game(self.CHARS)
        run(g.night(1))
        self.assertTrue(self.public('the Leviathan is in play'))
        g.execute(A)
        self.assertIsNone(g.g.winner)
        self.day(g, 2)
        g.execute(E)  # evil: not counted
        self.assertIsNone(g.g.winner)
        self.day(g, 3)
        g.execute(B)
        self.assertEqual(g.g.winner, 'evil')

    def test_after_day_5_evil_wins(self):
        g = self.game(self.CHARS)
        self.day(g, 4)
        ch.rules('Leviathan').end_of_day(g, g.g[F])
        self.assertIsNone(g.g.winner)
        self.day(g, 5)
        ch.rules('Leviathan').end_of_day(g, g.g[F])
        self.assertEqual(g.g.winner, 'evil')

    def test_the_mayor_jinx(self):
        for jinxed in self.both():
            g = self.game(['Mayor', T2, T3, T4, 'Poisoner', 'Leviathan', O1], jinxed)
            self.day(g, 5)
            ch.rules('Leviathan').end_of_day(g, g.g[F])
            self.assertEqual(g.g.winner, 'good' if jinxed else 'evil')

    def nominated(self, g, who):
        g.g.nominations.append({'day': g.day, 'nominator': F, 'nominee': who})
        g.execute(who)
        return g.g.winner

    def test_the_soldier_monk_innkeeper_and_exorcist_jinxes(self):
        for jinxed in self.both():
            g = self.game(['Soldier', T2, T3, T4, 'Poisoner', 'Leviathan', O1], jinxed)
            self.assertEqual(self.nominated(g, A), 'good' if jinxed else None)
            for c in ('Monk', 'Innkeeper', 'Exorcist'):
                g = self.game([c, T2, T3, T4, 'Poisoner', 'Leviathan', O1], jinxed)
                g.g.night_choices[1] = {A: [B]}
                self.assertEqual(self.nominated(g, B), 'good' if jinxed else None, c)

    def test_the_grandmother_jinx(self):
        for jinxed in self.both():
            g = self.game(['Grandmother', T2, T3, T4, 'Poisoner', 'Leviathan', O1], jinxed)
            g.g.notes['Grandchild'] = B
            g.execute(B)
            self.assertEqual(g.g.winner, 'evil' if jinxed else None)

    def test_the_banshee_sage_and_ravenkeeper_jinxes(self):
        g = self.game(['Banshee', 'Sage', 'Ravenkeeper', T4, 'Poisoner', 'Leviathan', O1])
        self.choose(2, F, [A])
        self.choose(2, E, [D])
        run(g.night(2))
        self.assertFalse(g.g[A].alive)
        self.assertTrue(self.public(f'{A} has died, killed by the Demon, and is the Banshee'))
        self.choose(3, F, [B])
        self.choose(3, E, [D])
        run(g.night(3))
        self.assertTrue(g.g[B].alive and self.told(B, 'Sage: the Demon is'))
        self.choose(4, F, [C])
        self.choose(4, E, [D])
        self.seats[C].day['ravenkeeper'] = [{'targets': [E]}]
        run(g.night(4))
        self.assertTrue(g.g[C].alive and self.told(C, 'Ravenkeeper: You learn that'))
        self.choose(5, F, [A])  # chosen before: not legal, asked again
        run(g.night(5))
        self.assertTrue([r for r in self.seats[F].log if r.prompt.startswith('(That is not a legal choice')])

    def test_the_pit_hag_and_hatter_jinxes_no_leviathan_after_day_5(self):
        for day, made in ((5, True), (6, False)):
            g = self.game([T1, T2, T3, 'Pit-Hag', 'Imp', T4], extra=['Leviathan'],
                          forced={'Pit-Hag deaths': {'players': [], 'yes': True}})
            self.choose(day, D, [B], character='Leviathan')
            self.choose(day, E, [C])
            run(g.night(day))
            self.assertEqual(g.g[B].character == 'Leviathan', made)
            g = self.game(['Hatter', T2, T3, 'Poisoner', 'Imp', T4], extra=['Leviathan'])
            g.g.day = day
            self.assertEqual('Leviathan' in carousel.tea_party_options(g.g, g.g[E]), made)


# ---- The synthetic script and the corpus -----------------------------------------------------------------------

BATCH = ('Pixie', 'High Priestess', 'Poppy Grower', 'Shugenja', 'Balloonist', 'General', 'Preacher', 'Cannibal',
         'Puzzlemaster', 'Heretic', 'Marionette', 'Widow', 'Goblin', 'Kazali', 'Leviathan')


class Carousel3Tests(unittest.TestCase):
    def test_it_holds_all_fifteen_and_several_jinxes_and_deals_at_every_size(self):
        s = ch.Script('carousel-3')
        for c in BATCH:
            self.assertIn(c, s.all)
        self.assertTrue(all(s.jinxed(a, b) for a, b in JINXES2))
        for n in range(5, 16):
            for seed in range(20):
                chars = random_setup(random.Random(seed), s.minions[seed % len(s.minions)], n, s)
                self.assertIsNone(setup_error(chars, s))

    def test_every_batch_2_character_has_storyteller_notes(self):
        from clocktower import judge
        sections = judge._sections(judge.NOTES / 'carousel.md')
        for c in BATCH:
            self.assertIn(c, sections)
            self.assertEqual(ch.rules(c).__module__, 'clocktower.carousel2')

    def test_it_plays_at_every_size(self):
        self.assertEqual(smoke.smoke(ch.Script('carousel-3'), games=1, out=io.StringIO()), [])

    def test_revenge_of_the_martian_vampires_plays(self):
        path = smoke.corpus_dir().parent.parent.parent / 'carousel-collection' / 'martianvampires' / 'script.json'
        path = path if path.exists() else smoke.Path('/workspace/carousel-collection/martianvampires/script.json')
        if not path.exists():
            raise unittest.SkipTest('no Carousel Script Collection')
        self.assertEqual(smoke.smoke(ch.Script(path), games=1, out=io.StringIO()), [])


if __name__ == '__main__':
    unittest.main()
