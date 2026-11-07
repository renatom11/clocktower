"""Batch 3 of the experimental characters (clocktower/carousel3.py): the Village Idiot, Acrobat, Lycanthrope,
Alchemist, Zealot, Organ Grinder, Noble, Farmer, Harpy, Boffin, Boomdandy, Fearmonger and Xaan, each edge their text
implies, their interactions on Monkey Do Math, and every official jinx between them and a built character
(docs/carousel-rulings.md, batch 3)."""
import io
import random
import unittest

from clocktower import carousel3, smoke
from clocktower import characters as ch
from clocktower.state import State, random_setup, setup_error

from test_carousel import JINXES3, O1, T1, T2, T3, T4, run
from test_carousel2 import A, B, C, D, E, F, G, Batch2Test

R = ch.rules


class Batch3Test(Batch2Test):
    def votes(self, nominee):
        return [e for e in self.g.events if e['kind'] == 'vote' and e['data']['nominee'] == nominee]

    def result(self):
        return [e for e in self.g.events if e['kind'] == 'vote_result'][-1]

    def alchemist(self, g, name, m):
        g.st.forced[f'Alchemist:{name}'] = {'character': m}
        return run(R('Alchemist').pick(g, g.g[name]))


# ---- Townsfolk ---------------------------------------------------------------------------------------------------

class VillageIdiotTests(Batch3Test):
    CHARS = ['Village Idiot', T1, T2, 'Poisoner', 'Imp', T3]

    def test_learns_the_alignment_of_the_chosen_player_each_night(self):
        g = self.game(self.CHARS)
        self.choose(1, A, [D])
        self.choose(1, D, [E])
        run(g.night(1))
        self.assertTrue(self.told(A, f'you chose {D}: they are evil'))
        self.choose(2, A, [B])
        self.choose(2, D, [E])
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertTrue(self.told(A, f'you chose {B}: they are good'))

    def test_extras_are_dealt_and_one_of_them_is_drunk(self):
        chars = ['Village Idiot', T1, T2, T3, T4, 'Poisoner', 'Imp']
        g = self.dealt(chars, forced={'Village Idiot extras': {'players': [B, C]}})
        g.forced = None
        run(R('Village Idiot').setup(g))
        idiots = [q.name for q in g.g.players if q.character == 'Village Idiot']
        self.assertEqual(idiots, [A, B, C])
        drunk = g.g.notes['Village Idiot drunk']
        self.assertIn(drunk, idiots)
        self.assertEqual([x for x in idiots if g.g.is_drunk(g.g[x])], [drunk])
        script = ch.Script.of('t', ['Village Idiot', T1, T2, 'Poisoner', 'Imp'])
        self.assertIsNone(setup_error(['Village Idiot'] * 3 + ['Poisoner', 'Imp'], script))
        self.assertIsNotNone(setup_error(['Village Idiot'] * 4 + ['Imp'], script))
        self.assertIsNotNone(setup_error([T1, T1, T2, 'Poisoner', 'Imp'], script))

    def test_drunk_poisoned_or_under_the_vortox_may_be_told_the_other_alignment(self):
        g = self.game(self.CHARS, forced={'Village Idiot:': {'yes': False}})
        self.choose(1, A, [E])
        self.choose(1, D, [A])
        run(g.night(1))
        self.assertTrue(self.told(A, f'you chose {E}: they are good'))
        g = self.game(['Village Idiot', T1, T2, 'Poisoner', 'Vortox', T3])
        self.choose(1, A, [E])
        self.choose(1, D, [B])
        run(g.night(1))
        self.assertTrue(self.told(A, f'you chose {E}: they are good'))


class AcrobatTests(Batch3Test):
    CHARS = ['Acrobat', T1, T2, 'Poisoner', 'Imp', T3]

    def test_dies_if_their_player_is_poisoned_tonight_else_lives(self):
        for poisoned in (True, False):
            g = self.game(self.CHARS)
            self.choose(2, A, [B])
            self.choose(2, D, [B if poisoned else F])
            self.choose(2, E, [C])
            run(g.night(2))
            self.assertEqual(g.g[A].alive, not poisoned)

    def test_the_drunk_and_a_player_who_becomes_drunk_later_tonight(self):
        g = self.game(['Acrobat', 'Drunk', T2, 'Poisoner', 'Imp', T3])
        self.choose(2, A, [B])
        self.choose(2, D, [F])
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertFalse(g.g[A].alive)
        g = self.game(['Acrobat', T1, T2, 'Organ Grinder', 'Imp', T3])  # the Organ Grinder wakes after the Acrobat
        self.choose(2, A, [D])
        self.choose(2, E, [C])
        self.decide(D, True)
        run(g.night(2))
        self.assertFalse(g.g[A].alive)
        self.assertTrue(g.g.is_drunk(g.g[D]))

    def test_a_poisoned_acrobat_does_not_die(self):
        g = self.game(self.CHARS)
        self.poison(A)
        self.choose(2, A, [B])
        self.choose(2, D, [B])
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertTrue(g.g[A].alive)


class LycanthropeTests(Batch3Test):
    CHARS = ['Lycanthrope', T1, T2, 'Poisoner', 'Imp', T3]

    def test_a_good_choice_dies_and_the_demon_does_not_kill(self):
        g = self.game(self.CHARS)
        self.choose(2, A, [B])
        self.choose(2, D, [F])
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertEqual((g.g[B].alive, g.g[C].alive), (False, True))

    def test_an_evil_choice_nothing_and_the_demon_kills(self):
        g = self.game(self.CHARS)
        self.choose(2, A, [D])
        self.choose(2, D, [F])
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertEqual((g.g[D].alive, g.g[C].alive), (True, False))

    def test_the_faux_paw_registers_evil_while_the_lycanthrope_has_their_ability(self):
        g = self.dealt(['Lycanthrope', T1, T2, 'Poisoner', 'Imp', O1], forced={'Faux Paw': {'players': [B]}})
        self.assertEqual(g.g.registers_evil(g.g[B]), {True})
        self.assertIn(B, g.g.sample_evil(random.Random(1)))
        self.choose(1, D, [E])
        run(g.night(1))
        self.choose(2, A, [B])
        self.choose(2, D, [F])
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertTrue(g.g[B].alive)  # registers evil: no death, and the Demon kills
        self.assertFalse(g.g[C].alive)
        self.poison(A)
        self.assertEqual(g.g.registers_evil(g.g[B]), {False})

    def test_a_poisoned_lycanthrope_kills_nobody(self):
        g = self.game(self.CHARS)
        self.choose(2, A, [B])
        self.choose(2, D, [A])
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertEqual((g.g[B].alive, g.g[C].alive), (True, False))


class NobleTests(Batch3Test):
    CHARS = ['Noble', T1, T2, 'Poisoner', 'Imp', T3, T4]

    def test_three_players_exactly_one_evil(self):
        for seed in range(6):
            g = self.game(self.CHARS)
            g.st.rng = random.Random(seed)
            self.choose(1, D, [B])
            run(g.night(1))
            told = self.told(A, 'one and only one of them is evil')
            self.assertEqual(len(told), 1)
            named = [x for x in (B, C, D, E, F, G) if x in told[0]]
            self.assertEqual(len(named), 3)
            self.assertEqual(sum(1 for x in named if g.g[x].evil), 1)

    def test_poisoned_any_three(self):
        g = self.game(self.CHARS, forced={'Noble:': {'players': [B, C, F]}})
        self.choose(1, D, [A])
        run(g.night(1))
        self.assertTrue(self.told(A, f'{B}, {C} and {F}'))


class FarmerTests(Batch3Test):
    CHARS = ['Farmer', T1, T2, 'Poisoner', 'Imp', T3]

    def test_dying_at_night_a_living_good_player_becomes_a_farmer(self):
        g = self.game(self.CHARS, forced={'Farmer:': {'players': [C]}})
        self.choose(2, D, [F])
        self.choose(2, E, [A])
        run(g.night(2))
        self.assertEqual(g.g[C].character, 'Farmer')
        self.assertTrue(self.told(C, 'you are now the Farmer'))

    def test_by_day_or_poisoned_nothing(self):
        g = self.game(self.CHARS)
        g.execute(A)
        run(g.run_pending())
        self.assertEqual([q.name for q in g.g.players if q.character == 'Farmer'], [A])
        g = self.game(self.CHARS)
        self.choose(2, D, [A])
        self.choose(2, E, [A])
        run(g.night(2))
        self.assertEqual([q.name for q in g.g.players if q.character == 'Farmer'], [A])

    def test_the_leviathan_jinx_a_chosen_farmer_uses_their_ability_and_lives(self):
        g = self.game(['Farmer', T1, T2, 'Poisoner', 'Leviathan', T3], forced={'Farmer:': {'players': [B]}})
        run(g.night(1))
        self.choose(2, E, [A])
        self.choose(2, D, [F])
        run(g.night(2))
        self.assertTrue(g.g[A].alive)
        self.assertEqual((g.g[A].character, g.g[B].character), ('Farmer', 'Farmer'))


# ---- Outsiders ---------------------------------------------------------------------------------------------------

class ZealotTests(Batch3Test):
    CHARS = ['Zealot', T1, T2, 'Poisoner', 'Imp', T3]

    def test_with_five_alive_their_hand_is_raised_and_they_are_told(self):
        g = self.game(self.CHARS)
        run(g.vote(B, None, 0))
        self.assertTrue(self.votes(B)[0]['data']['yes'] if self.votes(B)[0]['data']['voter'] == A else
                        next(e['data']['yes'] for e in self.votes(B) if e['data']['voter'] == A))
        self.assertTrue([r for r in self.seats[A].log if 'You must vote yes' in r.prompt])
        g.g[B].alive = False
        g.g[C].alive = False
        run(g.vote(D, None, 0))
        self.assertFalse(next(e['data']['yes'] for e in self.votes(D) if e['data']['voter'] == A))

    def test_a_poisoned_zealot_is_told_but_free(self):
        g = self.game(self.CHARS)
        self.poison(A)
        run(g.vote(B, None, 0))
        self.assertFalse(next(e['data']['yes'] for e in self.votes(B) if e['data']['voter'] == A))
        self.assertTrue([r for r in self.seats[A].log if 'You must vote yes' in r.prompt])

    def test_the_cannibal_jinx_the_cannibal_learns_they_have_it(self):
        g = self.game(['Cannibal', 'Zealot', T2, 'Poisoner', 'Imp', T3])
        g.execute(B)
        run(g.run_pending())
        self.assertEqual(g.g[A].extra, ['Zealot'])
        self.assertTrue(self.told(A, "gained the Zealot's ability"))


# ---- Minions -----------------------------------------------------------------------------------------------------

class OrganGrinderTests(Batch3Test):
    CHARS = [T1, T2, T3, 'Organ Grinder', 'Imp', T4]

    def test_votes_are_secret_unless_they_choose_to_be_drunk(self):
        for drunk in (False, True):
            g = self.game(self.CHARS)
            self.decide(D, drunk)
            self.choose(2, E, [C])
            run(g.night(2))
            self.day(g, 2)
            self.seats[A].day['vote'] = [{'vote': True}]
            run(g.vote(B, None, 0))
            self.assertEqual({tuple(e['to']) if isinstance(e['to'], list) else e['to'] for e in self.votes(B)},
                             {'public'} if drunk else {(x,) for x in (A, C, D, E, F, B)})
            self.assertEqual(self.result()['to'], 'public' if drunk else 'audit')
            prompt = [r.prompt for r in self.seats[A].log if r.kind == 'vote'][-1]
            self.assertEqual('eyes closed' in prompt, not drunk)

    def test_the_butler_jinx_a_hand_counts_only_if_the_master_voted(self):
        for master in (True, False):
            g = self.game(['Butler', T2, T3, 'Organ Grinder', 'Imp', T4])
            g.g.master = B
            self.seats[A].day['vote'] = [{'vote': True}]
            self.seats[B].day['vote'] = [{'vote': master}]
            run(g.vote(C, None, 0))
            self.assertEqual(self.result()['data']['votes'], 2 if master else 0)
            self.assertFalse(self.told(A, 'you cannot vote'))

    def test_the_alchemist_jinx_both_sober_both_drunk(self):
        g = self.game(['Alchemist', T2, T3, 'Organ Grinder', 'Imp', T4])
        self.alchemist(g, A, 'Organ Grinder')
        self.assertTrue(g.g.is_drunk(g.g[A]) and g.g.is_drunk(g.g[D]))
        self.assertFalse(g.secret_votes())
        g.g.add(State('drunk', D, source=D, until='night'))  # the Organ Grinder chose to be drunk
        self.assertFalse(g.g.is_drunk(g.g[A]))
        self.assertTrue(g.secret_votes())


class HarpyTests(Batch3Test):
    CHARS = [T1, T2, T3, 'Harpy', 'Imp', T4]

    def night(self, g, harpy_ok=True):
        if not harpy_ok:
            self.poison(D)
        self.choose(1, D, [B, C])
        run(g.night(1))
        self.assertTrue(self.told(B, f'points to {C}'))

    def test_mad_that_the_2nd_is_evil_nobody_dies(self):
        g = self.game(self.CHARS, forced={'Harpy deaths': {'players': [B]}})
        self.night(g)
        self.say(B, f'I am sure {C} is evil.')
        run(R('Harpy').moment(g, g.g[D], 'nominations'))
        self.assertTrue(g.g[B].alive)

    def test_broken_madness_one_or_both_might_die(self):
        for victims in ([B], [B, C], []):
            g = self.game(self.CHARS, forced={'Harpy deaths': {'players': victims}})
            self.night(g)
            self.say(B, f'{C} is good, I think.')
            run(R('Harpy').moment(g, g.g[D], 'nominations'))
            self.assertEqual([x for x in (B, C) if not g.g[x].alive], victims)

    def test_a_poisoned_harpy_tells_but_kills_nobody(self):
        g = self.game(self.CHARS, forced={'Harpy deaths': {'players': [B]}})
        self.night(g, harpy_ok=False)
        run(R('Harpy').moment(g, g.g[D], 'nominations'))
        self.assertTrue(g.g[B].alive)


class BoffinTests(Batch3Test):
    CHARS = [T1, T2, T3, 'Boffin', 'Imp', T4]

    def test_the_demon_has_a_good_ability_and_both_know(self):
        g = self.game(self.CHARS, forced={'Boffin:': {'character': 'Empath'}}, extra=['Empath'])
        run(g.night(1))
        self.assertTrue(self.told(E, "you have the Empath's ability"))
        self.assertTrue(self.told(D, "has the Empath's ability"))
        self.assertTrue(self.told(E, 'Empath:'))
        self.assertIn('Empath', g.g.abilities(g.g[E]))

    def test_even_if_the_demon_is_poisoned_but_not_the_boffin(self):
        g = self.game(self.CHARS, forced={'Boffin:': {'character': 'Empath'}}, extra=['Empath'])
        run(g.night(1))
        self.poison(E)
        self.assertFalse(g.g.unreliable(g.g[E], 'Empath'))
        self.assertTrue(g.g.works(g.g[E], 'Empath'))
        self.assertTrue(g.g.unreliable(g.g[E], 'Imp'))
        self.poison(D)
        self.assertTrue(g.g.unreliable(g.g[E], 'Empath'))
        g.g[D].alive = False
        self.assertNotIn('Empath', g.g.abilities(g.g[E]))

    def test_the_drunk_heretic_and_politician_jinxes_never_given(self):
        g = self.game(self.CHARS, extra=['Drunk', 'Heretic', 'Politician', 'Empath'])
        self.assertEqual(carousel3.boffin_options(g.g), ['Empath'])

    def test_the_goon_jinx_the_demon_does_not_turn_good(self):
        g = self.game([T1, T2, T3, 'Boffin', 'Imp', 'Monk'], forced={'Boffin:': {'character': 'Goon'}}, extra=['Goon'])
        run(g.night(1))
        g.g.add(State('drunk', F, source='test', until=None))
        R('Goon').chosen(g, g.g[E], g.g[F], g.tonight or type('N', (), {'n': 2})())
        self.assertTrue(g.g[E].evil)

    def test_the_village_idiot_jinx_even_in_play(self):
        g = self.game(['Village Idiot', T2, T3, 'Boffin', 'Imp', T4])
        self.assertEqual(carousel3.boffin_options(g.g), ['Village Idiot'])

    def test_the_alchemist_jinx_the_alchemist_does_not_learn_it(self):
        g = self.game(['Alchemist', T2, T3, 'Poisoner', 'Imp', T4], forced={'Boffin:': {'character': 'Empath'}},
                      extra=['Boffin', 'Empath'])
        self.alchemist(g, A, 'Boffin')
        self.choose(1, D, [B])
        run(g.night(1))
        self.assertTrue(self.told(E, "you have the Empath's ability"))
        self.assertFalse(self.told(A, 'Empath'))


class BoomdandyTests(Batch3Test):
    CHARS = [T1, T2, T3, 'Boomdandy', 'Imp', T4, 'Monk']

    def test_executed_all_but_3_die_then_the_most_pointed_at_dies(self):
        g = self.game(self.CHARS, forced={'Boomdandy:': {'players': [A, B, E]}})
        for x in (A, B, C, D, F, G):
            self.choose(1, x, [E])
        self.choose(1, E, [A])
        g.execute(D)
        run(g.run_pending())
        self.assertEqual([q.name for q in g.g.living()], [A, B])
        self.assertEqual(g.g.winner, 'good')

    def test_a_tie_kills_nobody_and_a_poisoned_boomdandy_nothing(self):
        g = self.game(self.CHARS, forced={'Boomdandy:': {'players': [A, B, E]}})
        for x, t in ((A, B), (B, A), (E, E), (C, E), (D, A), (F, B), (G, A)):
            self.choose(1, x, [t])
        g.execute(D)
        run(g.run_pending())
        self.assertEqual([q.name for q in g.g.living()], [B, E])
        g = self.game(self.CHARS)
        self.poison(D)
        g.execute(D)
        run(g.run_pending())
        self.assertEqual(len(g.g.living()), 6)

    def test_the_plague_doctor_jinx_a_player_becomes_the_boomdandy(self):
        g = self.game(['Plague Doctor', T2, T3, 'Poisoner', 'Imp', T4], extra=['Boomdandy'],
                      forced={'Plague Doctor:Boomdandy': {'players': [D]}, 'Plague Doctor': {'character': 'Boomdandy'}})
        g.execute(A)
        run(g.run_pending())
        self.assertEqual(g.g[D].character, 'Boomdandy')


class FearmongerTests(Batch3Test):
    CHARS = [T1, T2, T3, 'Fearmonger', 'Imp', T4]

    def test_a_new_choice_is_announced_and_executing_them_loses_their_team(self):
        g = self.game(self.CHARS)
        self.choose(1, D, [B])
        run(g.night(1))
        self.assertEqual(len(self.public('the Fearmonger has chosen a player')), 1)
        self.choose(2, D, [B])
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertEqual(len(self.public('the Fearmonger has chosen a player')), 1)
        self.day(g, 2)
        g.g.nominations.append({'day': 2, 'nominator': D, 'nominee': B, 'character': 'Fearmonger'})
        g.execute(B)
        self.assertEqual(g.g.winner, 'evil')

    def test_another_nominator_or_a_poisoned_fearmonger_nothing(self):
        for poisoned in (False, True):
            g = self.game(self.CHARS)
            self.choose(1, D, [B])
            run(g.night(1))
            if poisoned:
                self.poison(D)
            g.g.nominations.append({'day': 1, 'nominator': A if not poisoned else D, 'nominee': B,
                                    'character': 'x'})
            g.execute(B)
            self.assertIsNone(g.g.winner)

    def test_the_plague_doctor_jinx_a_minion_gains_it(self):
        g = self.game(['Plague Doctor', T2, T3, 'Poisoner', 'Imp', T4], extra=['Fearmonger'],
                      forced={'Plague Doctor': {'character': 'Fearmonger'}})
        g.execute(A)
        run(g.run_pending())
        self.assertEqual(g.g[D].extra, ['Fearmonger'])
        self.assertTrue(self.told(D, "gain the Fearmonger's ability"))


class XaanTests(Batch3Test):
    def test_on_night_x_every_townsfolk_is_poisoned_until_dusk(self):
        g = self.dealt([T1, T2, 'Recluse', 'Xaan', 'Imp', T4], extra=['Recluse'])
        self.assertEqual(g.g.notes['Xaan'][D], 1)
        self.assertTrue(self.intro(D, 'X is 1'))
        run(g.night(1))
        self.assertEqual([x for x in (A, B, C, F) if g.g.is_poisoned(g.g[x])], [A, B, F])
        self.day(g, 2)
        g.g.day = 2
        self.assertFalse(g.g.is_poisoned(g.g[A]))

    def test_x_outsiders_a_poisoned_xaan_and_setup_counts(self):
        g = self.dealt([T1, T2, 'Recluse', 'Xaan', 'Imp', 'Butler', T3, T4], extra=['Recluse', 'Butler'])
        self.assertEqual(g.g.notes['Xaan'][D], 2)
        g.g.add(State('poisoned', D, source='test', until=None))
        run(g.night(1))
        self.day(g, 2)
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertFalse(g.g.is_poisoned(g.g[A]))
        script = ch.Script.of('t', [T1, T2, T3, T4, 'Recluse', 'Butler', 'Xaan', 'Imp'])
        for chars in ([T1, T2, 'Xaan', 'Imp', T3], [T1, 'Recluse', 'Xaan', 'Imp', T3]):
            self.assertIsNone(setup_error(chars, script))


# ---- The Alchemist and its jinxes -----------------------------------------------------------------------------

class AlchemistTests(Batch3Test):
    def test_a_minion_ability_not_in_play_that_works(self):
        g = self.dealt(['Alchemist', T2, T3, 'Godfather', 'Imp', T4], forced={'Alchemist:': {'character': 'Poisoner'}},
                       extra=['Poisoner'])
        self.assertEqual(g.g[A].extra, ['Poisoner'])
        self.choose(1, A, [B])
        run(g.night(1))
        self.assertTrue(self.told(A, "you have the Poisoner's ability"))
        self.assertTrue(g.g.is_poisoned(g.g[B]))
        self.assertNotIn('Godfather', carousel3.alchemist_options(g))

    def test_the_godfather_and_baron_change_the_outsiders_in_a_dealt_game(self):
        g = self.dealt(['Alchemist', T2, T3, 'Poisoner', 'Imp', T4, T1], extra=['Baron', 'Butler', 'Recluse'])
        run(R('Alchemist').setup_change(g, g.g[A], 'Baron'))
        self.assertEqual(carousel3.outsiders(g.g), 2)

    def test_a_drunk_who_believes_they_are_the_alchemist(self):
        g = self.game(['Drunk', T2, T3, 'Poisoner', 'Imp', T4], extra=['Alchemist', "Devil's Advocate"],
                      forced={'Alchemist:': {'character': "Devil's Advocate"}})
        g.g[A].shown = 'Alchemist'
        self.choose(1, A, [B])
        self.choose(1, D, [C])
        run(g.night(1))
        self.assertTrue(self.told(A, "you have the Devil's Advocate's ability"))
        g.execute(B)
        self.assertFalse(g.g[B].alive)

    def test_the_spy_and_widow_jinxes_a_right_guess_makes_the_demon_choose_them(self):
        for m in ('Spy', 'Widow'):
            g = self.game(['Alchemist', T2, T3, m, 'Imp', T4])
            self.assertIn(m, carousel3.alchemist_options(g))
            self.alchemist(g, A, m)
            self.assertEqual(g.g[A].extra, [])
            self.choose(1, A, [D])
            g.execute(B)
            run(g.run_pending())
            self.assertTrue(self.public(f'{A} publicly guesses that {D} is the {m}'))
            self.choose(2, E, [C])
            run(g.night(2))
            self.assertFalse(g.g[D].alive)
            self.assertTrue(g.g[C].alive)
            g = self.game(['Alchemist', T2, T3, 'Poisoner', 'Imp', T4], extra=[m])
            self.assertNotIn(m, carousel3.alchemist_options(g))

    def test_the_marionette_and_mastermind_jinxes(self):
        g = self.game(['Alchemist', 'Marionette', T3, 'Poisoner', 'Imp', T4], extra=['Mastermind'])
        self.assertEqual(sorted(carousel3.alchemist_options(g)), ['Marionette', 'Mastermind'])
        self.alchemist(g, A, 'Mastermind')
        self.assertEqual(g.g[A].extra, [])
        g = self.game(['Alchemist', T2, T3, 'Mastermind', 'Imp', T4], extra=['Marionette'])
        self.assertEqual(carousel3.alchemist_options(g), [])

    def test_the_summoner_jinx(self):
        g = self.dealt(['Alchemist', T2, T3, 'Poisoner', 'Imp', O1], extra=['Summoner', 'Pukka'],
                       forced={'Alchemist:': {'character': 'Poisoner'}})
        self.assertNotIn('Summoner', carousel3.alchemist_options(g))  # (a forced setup: none)
        g.forced = None
        self.assertIn('Summoner', carousel3.alchemist_options(g))
        g.g.notes['Alchemist'] = {A: 'Summoner'}
        g.g[A].extra = ['Summoner']
        run(R('Alchemist').setup_change(g, g.g[A], 'Summoner'))
        self.assertIsNone(g.g.demon())
        self.assertIsNone(g.g.check_victory())
        g.st.forced['Alchemist summons'] = {'players': [B]}
        self.choose(3, A, character='Pukka')
        self.choose(3, D, [C])
        self.day(g, 2)
        run(g.night(3))
        self.assertEqual((g.g[B].character, g.g[B].alignment), ('Pukka', 'evil'))
        g = self.dealt(['Alchemist', T2, T3, 'Poisoner', 'Imp', O1], extra=['Summoner'])
        g.g.notes['Alchemist'] = {A: 'Summoner'}
        g.g[A].extra = ['Summoner']
        g.execute(A)
        self.assertEqual(g.g.winner, 'evil')


class FuzzFoundTests(Batch3Test):
    """The fuzzer's and the smoke runs' findings (docs/interaction-findings.md, B11-B14)."""

    def test_setup_steps_never_convert_the_alchemist(self):
        g = self.dealt(['Alchemist', 'Village Idiot', T3, T4, T1, 'Poisoner', 'Imp'])
        g.forced = None
        run(R('Village Idiot').setup(g))
        self.assertFalse([v for v in self.values('Village Idiot extras') if A in v['players']])

    def test_two_players_with_the_assassins_ability_each_use_it_once(self):
        g = self.game(['Alchemist', T2, T3, 'Assassin', 'Imp', T4, 'Monk'], extra=['Pit-Hag'])
        g.g.notes['Alchemist'] = {A: 'Assassin'}
        g.g[A].extra = ['Assassin']
        self.choose(2, A, [B])
        self.choose(2, D, [C])
        self.choose(2, E, [F])
        run(g.night(2))
        self.assertEqual([x for x in (B, C) if not g.g[x].alive], [B, C])
        night = type('N', (), {'first': False, 'n': 3})()
        self.assertIsNone(R('Assassin').night_spec(g, g.g[A], night))
        self.assertIsNone(R('Assassin').night_spec(g, g.g[D], night))

    def test_a_dead_player_made_the_lycanthrope_gives_no_faux_paw(self):
        g = self.game([T1, T2, T3, 'Poisoner', 'Imp', T4])
        g.g[A].alive = False
        g.g.change_character(g.g[A], 'Lycanthrope')
        run(R('Lycanthrope').becomes(g, g.g[A]))
        self.assertFalse([st for st in g.g.states if st.kind == 'registers evil'])

    def test_no_alchemist_summoner_when_the_marionette_is_the_only_other_evil_player(self):
        g = self.dealt(['Alchemist', T2, T3, 'Marionette', 'Imp', T4, T1], extra=['Summoner'],
                       forced={'Marionette:': {'character': 'Empath'}})
        g.forced = None
        self.assertNotIn('Summoner', carousel3.alchemist_options(g))


class PitHagVillageIdiotTests(Batch3Test):
    def test_the_pit_hag_can_make_an_extra_village_idiot_and_the_drunk_one_might_change(self):
        g = self.game(['Village Idiot', T2, T3, 'Pit-Hag', 'Imp', T4], forced={'Village Idiot drunk': {'players': [B]},
                                                                                 'Pit-Hag deaths': {'yes': True}})
        self.choose(2, D, [B], character='Village Idiot')
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertEqual(g.g[B].character, 'Village Idiot')
        self.assertTrue(g.g.is_drunk(g.g[B]))
        g = self.game(['Village Idiot', T2, T3, 'Pit-Hag', 'Imp', T4], jinxed=False)
        self.choose(2, D, [B], character='Village Idiot')
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertEqual(g.g[B].character, T2)


# ---- Monkey Do Math: the six together, with built characters ---------------------------------------------------

class MonkeyDoMathTests(Batch3Test):
    def test_the_acrobat_choosing_the_drunk_village_idiot_dies(self):
        g = self.game(['Acrobat', 'Village Idiot', 'Village Idiot', 'Poisoner', 'Imp', T4])
        g.g.notes['Village Idiot drunk'] = C
        self.choose(2, A, [C])
        self.choose(2, B, [D])
        self.choose(2, C, [D])
        self.choose(2, D, [F])
        self.choose(2, E, [F])
        run(g.night(2))
        self.assertFalse(g.g[A].alive)

    def test_the_village_idiot_sees_the_faux_paw_as_evil(self):
        g = self.dealt(['Lycanthrope', 'Village Idiot', T2, 'Poisoner', 'Imp', O1],
                       forced={'Faux Paw': {'players': [C]}})
        self.choose(1, B, [C])
        self.choose(1, D, [E])
        run(g.night(1))
        self.assertTrue(self.told(B, f'you chose {C}: they are evil'))

    def test_the_zealot_votes_eyes_closed_under_the_organ_grinder(self):
        g = self.game(['Zealot', T2, T3, 'Organ Grinder', 'Imp', T4])
        run(g.vote(B, None, 0))
        own = [e for e in self.votes(B) if e['data']['voter'] == A]
        self.assertEqual((own[0]['to'], own[0]['data']['yes']), ([A], True))

    def test_an_alchemist_assassin_and_devils_advocate(self):
        g = self.game(['Alchemist', T2, T3, 'Godfather', 'Imp', T4], extra=['Assassin'])
        self.alchemist(g, A, 'Assassin')
        self.choose(2, A, [E])
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertFalse(g.g[E].alive)
        g = self.game(['Alchemist', T2, T3, 'Godfather', 'Imp', T4], extra=["Devil's Advocate"])
        self.alchemist(g, A, "Devil's Advocate")
        self.choose(1, A, [B])
        run(g.night(1))
        g.execute(B)
        self.assertTrue(g.g[B].alive)

    def test_it_plays(self):
        path = smoke.Path('/workspace/carousel-collection/monkeydomath/script.json')
        if not path.exists():
            raise unittest.SkipTest('no Carousel Script Collection')
        self.assertEqual(smoke.smoke(ch.Script(path), games=1, out=io.StringIO()), [])


# ---- The synthetic script --------------------------------------------------------------------------------------

BATCH = ('Village Idiot', 'Acrobat', 'Lycanthrope', 'Alchemist', 'Zealot', 'Organ Grinder', 'Noble', 'Farmer',
         'Harpy', 'Boffin', 'Boomdandy', 'Fearmonger', 'Xaan')


class Carousel4Tests(unittest.TestCase):
    def test_it_holds_all_thirteen_and_the_jinxes_and_deals_at_every_size(self):
        s = ch.Script('carousel-4')
        for c in BATCH:
            self.assertIn(c, s.all)
        self.assertTrue(all(s.jinxed(a, b) for a, b in JINXES3))
        for n in range(5, 16):
            for seed in range(20):
                chars = random_setup(random.Random(seed), s.minions[seed % len(s.minions)], n, s)
                self.assertIsNone(setup_error(chars, s))

    def test_every_batch_3_character_has_storyteller_notes(self):
        from clocktower import judge
        sections = judge._sections(judge.NOTES / 'carousel.md')
        for c in BATCH:
            self.assertIn(c, sections)
            self.assertEqual(ch.rules(c).__module__, 'clocktower.carousel3')

    def test_it_plays_at_every_size(self):
        self.assertEqual(smoke.smoke(ch.Script('carousel-4'), games=1, out=io.StringIO()), [])


if __name__ == '__main__':
    unittest.main()
