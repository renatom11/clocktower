"""Batch 3b of the experimental characters (clocktower/carousel4.py): the Alsaahir, Huntsman, Snitch, Knight, Choirboy,
King, Cult Leader, Lord of Typhon and Lleech, each edge their text implies, and every official jinx between them and a
built character (docs/carousel-rulings.md, batch 3b)."""
import io
import random
import unittest

from clocktower import carousel3, carousel4, smoke
from clocktower import characters as ch
from clocktower.state import random_setup, setup_error

from test_carousel import JINXES4, O1, T1, T2, T3, T4, run
from test_carousel2 import A, B, C, D, E, F, G
from test_carousel3 import Batch3Test

R = ch.rules
H = 'Harper'


def guess(*pairs):
    return [{'player': p, 'character': c} for p, c in pairs]


class Batch3bTest(Batch3Test):
    def claim(self, name, character, **use):
        self.g.public_abilities([name], {name: {'ability': {'character': character, **use}}})
        run(self.g.run_pending())

    def join(self, *names, vote=True):
        for n in names:
            self.seats[n].day.setdefault('decide', []).append({'vote': vote})


# ---- Townsfolk ---------------------------------------------------------------------------------------------------

class AlsaahirTests(Batch3bTest):
    CHARS = ['Alsaahir', T1, T2, 'Poisoner', 'Imp', T3]

    def test_a_right_guess_wins_for_good_a_wrong_one_nothing(self):
        g = self.game(self.CHARS)
        self.claim(A, 'Alsaahir', guesses=guess((D, 'Imp'), (E, 'Poisoner')))
        self.assertIsNone(g.g.winner)  # (the types swapped: wrong)
        g = self.game(self.CHARS)
        self.claim(A, 'Alsaahir', guesses=guess((D, 'Poisoner'), (B, 'Imp')))
        self.assertIsNone(g.g.winner)
        g = self.game(self.CHARS, extra=['Spy'])
        self.claim(A, 'Alsaahir', guesses=guess((D, 'Spy'), (E, 'Imp'), (B, T1)))  # any Minion character: a Minion
        self.assertEqual(g.g.winner, 'good')

    def test_every_minion_and_demon_counts_dead_ones_too(self):
        g = self.game(['Alsaahir', T1, T2, 'Poisoner', 'Imp', T3, T4, 'Spy'])
        g.g[H].alive = False
        self.claim(A, 'Alsaahir', guesses=guess((D, 'Poisoner'), (E, 'Imp')))
        self.assertIsNone(g.g.winner)
        self.claim(A, 'Alsaahir', guesses=guess((D, 'Poisoner'), (E, 'Imp'), (H, 'Spy')))
        self.assertIsNone(g.g.winner)  # (once a day)
        self.day(g, 2)
        self.claim(A, 'Alsaahir', guesses=guess((D, 'Poisoner'), (E, 'Imp'), (H, 'Spy')))
        self.assertEqual(g.g.winner, 'good')

    def test_poisoned_dead_or_a_bluff_nothing(self):
        right = guess((D, 'Poisoner'), (E, 'Imp'))
        g = self.game(self.CHARS)
        self.poison(A)
        self.claim(A, 'Alsaahir', guesses=right)
        self.assertIsNone(g.g.winner)
        self.assertTrue([x for x in g.g.abnormal if x['ability'] == 'Alsaahir'])
        g = self.game(self.CHARS)
        g.g[A].alive = False
        self.claim(A, 'Alsaahir', guesses=right)
        self.assertIsNone(g.g.winner)
        g = self.game(self.CHARS)
        self.claim(B, 'Alsaahir', guesses=right)
        self.assertIsNone(g.g.winner)
        g = self.game(['Drunk', T1, T2, 'Poisoner', 'Imp', T3], extra=['Alsaahir'])
        g.g[A].shown = 'Alsaahir'
        self.claim(A, 'Alsaahir', guesses=right)
        self.assertIsNone(g.g.winner)

    def test_its_guesses_are_on_the_prompt(self):
        from clocktower.prompts import custom_text
        s = self.script(self.CHARS, True)
        self.assertIn('Alsaahir', s.guessable)
        self.assertTrue(any('"guesses"' in new for _, new in custom_text(s)))


class HuntsmanTests(Batch3bTest):
    CHARS = ['Huntsman', 'Damsel', T2, 'Poisoner', 'Imp', T3]

    def test_choosing_the_damsel_she_becomes_a_townsfolk_not_in_play_once(self):
        g = self.game(self.CHARS, extra=['Chef'], forced={'Huntsman:': {'character': 'Chef'}})
        self.choose(1, D, [C])
        self.choose(1, A, [B])
        run(g.night(1))
        self.assertEqual((g.g[B].character, g.g[B].alignment), ('Chef', 'good'))
        self.assertTrue(self.told(B, 'you are now the Chef'))
        self.assertIsNone(R('Huntsman').night_spec(g, g.g[A], g.tonight))
        self.assertFalse(self.told(A, 'Chef'))

    def test_another_player_spends_it_and_waiting_does_not(self):
        g = self.game(self.CHARS, extra=['Chef'])
        self.choose(1, D, [C])
        run(g.night(1))  # chose no one
        self.assertIsNotNone(R('Huntsman').night_spec(g, g.g[A], None))
        self.choose(2, A, [C])
        self.choose(2, D, [C])
        self.choose(2, E, [F])
        run(g.night(2))
        self.assertEqual(g.g[B].character, 'Damsel')
        self.assertIsNone(R('Huntsman').night_spec(g, g.g[A], None))

    def test_poisoned_spent_and_the_damsel_stays(self):
        g = self.game(self.CHARS, extra=['Chef'])
        self.poison(A)
        self.choose(1, A, [B])
        self.choose(1, D, [C])
        run(g.night(1))
        self.assertEqual(g.g[B].character, 'Damsel')
        self.assertIsNone(R('Huntsman').night_spec(g, g.g[A], None))
        g = self.game(['Drunk', 'Damsel', T2, 'Poisoner', 'Imp', T3], extra=['Huntsman', 'Chef'])
        g.g[A].shown = 'Huntsman'
        self.choose(1, A, [B])
        self.choose(1, D, [C])
        run(g.night(1))
        self.assertEqual(g.g[B].character, 'Damsel')
        self.assertIsNone(R('Huntsman').night_spec(g, g.g[A], None))  # (not woken again)

    def test_the_damsel_is_added_at_setup_in_an_outsiders_seat_or_a_townsfolks(self):
        for chars, taken in ((['Huntsman', T1, T2, T3, O1, 'Poisoner', 'Imp', T4], O1),
                             (['Huntsman', T1, T2, T3, T4, 'Poisoner', 'Imp'], None)):
            g = self.dealt(chars, extra=['Damsel'])
            g.forced = None
            run(R('Huntsman').setup(g))
            damsel = [q for q in g.g.players if q.character == 'Damsel']
            self.assertEqual(len(damsel), 1)
            if taken:
                self.assertFalse([q for q in g.g.players if q.character == taken])
            self.assertEqual(g.g[A].character, 'Huntsman')

    def test_a_drunk_huntsman_adds_none_and_the_marionette_jinx_does(self):
        g = self.dealt(['Drunk', T1, T2, T3, T4, 'Chef', 'Poisoner', 'Imp'], extra=['Damsel', 'Huntsman'],
                       forced={'Drunk': {'character': 'Huntsman'}})
        g.forced = None
        run(R('Huntsman').setup(g))
        self.assertFalse([q for q in g.g.players if q.character == 'Damsel'])
        for jinxed in (True, False):
            g = self.dealt([T1, T2, T3, 'Marionette', 'Imp', T4, 'Mayor'], jinxed=jinxed,
                           extra=['Damsel', 'Huntsman'], forced={'Marionette:': {'character': 'Huntsman'}})
            g.forced = None
            run(R('Huntsman').setup(g))
            self.assertEqual(bool([q for q in g.g.players if q.character == 'Damsel']), jinxed)


class KnightTests(Batch3bTest):
    CHARS = ['Knight', T1, T2, 'Poisoner', 'Imp', T3]

    def test_two_players_neither_the_demon(self):
        for seed in range(6):
            g = self.game(self.CHARS)
            g.st.rng = random.Random(seed)
            self.choose(1, D, [B])
            run(g.night(1))
            told = self.told(A, 'are not the Demon')
            self.assertEqual(len(told), 1)
            self.assertNotIn(E, told[0])
            self.assertNotIn(f'{A} and', told[0])

    def test_poisoned_or_under_the_vortox_the_demon_may_be_shown(self):
        g = self.game(self.CHARS, forced={'Knight:': {'players': [B, E]}})
        self.choose(1, D, [A])
        run(g.night(1))
        self.assertTrue(self.told(A, f'{B} and {E} are not the Demon'))
        g = self.game(['Knight', T1, T2, 'Poisoner', 'Vortox', T3])
        self.choose(1, D, [B])
        run(g.night(1))
        self.assertIn(E, self.told(A, 'are not the Demon')[0])

    def test_a_recluse_may_be_shown(self):
        g = self.game(['Knight', 'Recluse', T2, 'Poisoner', 'Imp', T3])
        self.assertIn([B, C], [v['players'] for v in carousel4.knight_choice(g.g, g.g[A]).values])


class KingTests(Batch3bTest):
    CHARS = ['King', T1, T2, 'Poisoner', 'Imp', T3, T4]

    def test_the_demon_learns_the_king_on_the_first_night(self):
        g = self.game(self.CHARS)
        self.choose(1, D, [B])
        run(g.night(1))
        self.assertTrue(self.told(E, f'{A} is the King'))
        self.assertFalse(self.told(A, 'is alive'))

    def test_an_alive_character_once_the_dead_equal_the_living(self):
        g = self.game(self.CHARS)
        g.g[B].alive = g.g[C].alive = False
        self.choose(2, D, [F])
        self.choose(2, E, [G])
        run(g.night(2))
        self.assertFalse(self.told(A, 'is alive'))  # 3 dead, 4 alive at the King's step (Gray died tonight: 4/3)
        g = self.game(self.CHARS)
        g.g[B].alive = g.g[C].alive = g.g[F].alive = False
        self.choose(2, D, [G])
        self.choose(2, E, [G])
        run(g.night(2))
        told = self.told(A, 'is alive')
        self.assertEqual(len(told), 1)
        self.assertTrue(any(f'the {c} is alive' in told[0] for c in ('Poisoner', 'Imp', T4)))

    def test_poisoned_any_character_and_the_leviathan_jinx(self):
        g = self.game(self.CHARS, forced={'King:': {'character': T1}})
        g.g[B].alive = g.g[C].alive = g.g[F].alive = False
        self.choose(2, D, [A])
        self.choose(2, E, [G])
        run(g.night(2))
        self.assertTrue(self.told(A, f'the {T1} is alive'))
        for jinxed in (True, False):
            g = self.game(['King', T1, T2, 'Poisoner', 'Leviathan', T3, T4], jinxed=jinxed)
            g.g[B].alive = False
            self.choose(2, D, [G])
            run(g.night(2))
            self.assertEqual(bool(self.told(A, 'is alive')), jinxed)

    def test_a_new_demon_learns_the_king(self):
        g = self.game(['King', T1, T2, 'Pit-Hag', 'Imp', T3, T4], forced={'Pit-Hag deaths': {'yes': False}},
                      extra=['Vortox'])
        run(g.night(1))
        self.choose(2, D, [C], character='Vortox')
        self.choose(2, E, [F])
        run(g.night(2))
        self.assertTrue(self.told(C, f'{A} is the King'))


class ChoirboyTests(Batch3bTest):
    CHARS = ['Choirboy', 'King', T2, 'Poisoner', 'Imp', T3]

    def test_the_demon_kills_the_king_the_choirboy_learns_the_demon(self):
        g = self.game(self.CHARS)
        self.choose(2, D, [C])
        self.choose(2, E, [B])
        run(g.night(2))
        self.assertTrue(self.told(A, f'{E} is the Demon'))

    def test_another_death_of_the_king_or_a_poisoned_choirboy(self):
        g = self.game(self.CHARS)
        g.execute(B)
        self.choose(2, D, [C])
        self.choose(2, E, [F])
        run(g.night(2))
        self.assertFalse(self.told(A, 'is the Demon'))
        g = self.game(self.CHARS, forced={'Choirboy:': {'players': [C]}})
        self.choose(2, D, [A])
        self.choose(2, E, [B])
        run(g.night(2))
        self.assertTrue(self.told(A, f'{C} is the Demon'))

    def test_the_king_is_added_at_setup(self):
        g = self.dealt(['Choirboy', T1, T2, T3, T4, 'Poisoner', 'Imp'], extra=['King'])
        g.forced = None
        run(R('Choirboy').setup(g))
        self.assertEqual(len([q for q in g.g.players if q.character == 'King']), 1)
        self.assertIsNone(setup_error([q.character for q in g.g.players], g.script))


class CultLeaderTests(Batch3bTest):
    CHARS = ['Cult Leader', T1, T2, 'Poisoner', 'Imp', T3]

    def test_each_night_they_become_an_alive_neighbours_alignment(self):
        g = self.game(['Cult Leader', 'Poisoner', T2, 'Imp', T1, 'Spy'])
        self.choose(1, B, [C])
        run(g.night(1))
        self.assertEqual(g.g[A].alignment, 'evil')
        self.assertTrue(self.told(A, 'you are now evil'))
        g = self.game(self.CHARS, forced={'Cult Leader:': {'yes': True}})
        g.g[A].alignment = 'evil'
        self.choose(1, D, [C])
        run(g.night(1))
        self.assertEqual(g.g[A].alignment, 'good')
        g = self.game(['Cult Leader', 'Poisoner', T2, T3, 'Imp', T1], forced={'Cult Leader:': {'yes': True}})
        self.choose(1, B, [C])
        run(g.night(1))
        self.assertEqual(g.g[A].alignment, 'evil')

    def test_poisoned_no_change(self):
        g = self.game(['Cult Leader', 'Poisoner', T2, 'Imp', T1, 'Spy'])
        self.poison(A)
        self.choose(1, B, [C])
        run(g.night(1))
        self.assertEqual(g.g[A].alignment, 'good')

    def test_a_cult_vote_every_good_player_joins_their_team_wins(self):
        g = self.game(self.CHARS)
        self.join(A, B, C, F)
        self.claim(A, 'Cult Leader')
        self.assertEqual(g.g.winner, 'good')
        self.assertTrue(self.public('calls a cult vote'))
        g = self.game(self.CHARS)
        g.g[A].alignment = 'evil'
        self.join(B, C, F)
        g.g[F].alive = False
        self.claim(A, 'Cult Leader')
        self.assertEqual(g.g.winner, 'evil')  # (the dead too: every good player)

    def test_one_good_player_out_a_bluff_a_poisoned_one_or_a_second_vote_nothing(self):
        g = self.game(self.CHARS)
        self.join(A, B, C)
        self.claim(A, 'Cult Leader')
        self.assertIsNone(g.g.winner)
        self.assertTrue(self.public('The cult vote is over'))
        g = self.game(self.CHARS)
        self.join(A, B, C, F)
        self.claim(B, 'Cult Leader')
        self.assertIsNone(g.g.winner)
        self.join(A, B, C, F)
        self.claim(A, 'Cult Leader')
        self.assertIsNone(g.g.winner)  # one cult vote a day
        g = self.game(self.CHARS)
        self.poison(A)
        self.join(A, B, C, F)
        self.claim(A, 'Cult Leader')
        self.assertIsNone(g.g.winner)

    def test_the_boffin_jinx_a_demon_with_it_never_turns_good(self):
        g = self.game(['Monk', 'Boffin', T2, 'Imp', T1, T3], forced={'Boffin:': {'character': 'Cult Leader'}},
                      extra=['Cult Leader'])
        self.assertIn('Cult Leader', carousel3.boffin_options(g.g))
        run(g.night(1))
        self.assertIn('Cult Leader', g.g.abilities(g.g[D]))
        self.assertEqual(g.g[D].alignment, 'evil')
        g = self.game(['Monk', 'Boffin', T2, 'Imp', T1, T3], forced={'Boffin:': {'character': 'Cult Leader'}},
                      extra=['Cult Leader'], jinxed=False)
        run(g.night(1))
        self.assertEqual(g.g[D].alignment, 'good')

    def test_the_pit_hag_jinx_an_evil_cult_leader_never_turns_good(self):
        for jinxed in (True, False):
            g = self.game(['Monk', T1, T2, 'Pit-Hag', 'Imp', T3], jinxed=jinxed, extra=['Cult Leader', 'Spy'])
            g.g[B].alignment = 'evil'
            self.choose(2, D, [B], character='Cult Leader')
            self.choose(2, E, [F])
            run(g.night(2))
            self.assertEqual(g.g[B].character, 'Cult Leader')
            self.assertEqual(g.g[B].alignment, 'evil' if jinxed else 'good')


# ---- Outsiders ---------------------------------------------------------------------------------------------------

class SnitchTests(Batch3bTest):
    CHARS = ['Snitch', T1, T2, 'Poisoner', 'Imp', T3, 'Spy', 'Marionette']

    def test_each_minion_gets_three_bluffs_not_in_play(self):
        g = self.game(self.CHARS, extra=['Chef', 'Empath', 'Monk', 'Mayor'])
        g.g['Harper'].shown = 'Mayor'
        self.choose(1, D, [B])
        run(g.night(1))
        for m in (D, G):
            told = self.told(m, 'Snitch: three characters not in play')
            self.assertEqual(len(told), 1)
            for c in ('Snitch', T1, T2, T3, 'Mayor'):
                self.assertNotIn(f' {c},', told[0] + ',')
        self.assertFalse(self.told('Harper', 'Snitch'))  # (the Marionette doesn't know)
        self.assertFalse(self.told(E, 'Snitch'))

    def test_poisoned_none(self):
        g = self.game(self.CHARS, extra=['Chef', 'Empath', 'Monk', 'Mayor'])
        self.poison(A)
        self.choose(1, D, [B])
        run(g.night(1))
        self.assertFalse(self.told(D, 'Snitch'))


# ---- Demons ------------------------------------------------------------------------------------------------------

class LordOfTyphonTests(Batch3bTest):
    def script5(self):
        return ch.Script('carousel-5')

    def test_one_more_minion_is_dealt(self):
        s = self.script5()
        for n in range(5, 16):
            for seed in range(40):
                chars = random_setup(random.Random(seed), s.minions[seed % len(s.minions)], n, s)
                if 'Lord of Typhon' in chars:
                    self.assertEqual(sum(1 for c in chars if ch.kind(c) == 'Minion'), ch.SETUPS[n][2] + 1)
                self.assertIsNone(setup_error(chars, s))
        self.assertIsNotNone(setup_error(['Lord of Typhon', 'Poisoner', T1, T2, T3], self.script(
            ['Lord of Typhon', 'Poisoner', 'Spy'], True)))
        self.assertIsNone(setup_error(['Lord of Typhon', 'Poisoner', 'Spy', T1, O1], self.script(
            ['Lord of Typhon', 'Poisoner', 'Spy'], True)))

    def test_the_evil_characters_sit_in_a_line_with_it_in_the_middle(self):
        for chars in (['Lord of Typhon', T1, 'Poisoner', T2, T3, 'Spy', T4],
                      [T1, 'Spy', T2, 'Lord of Typhon', T3, 'Poisoner', 'Mayor', 'Baron', T4, 'Monk', 'Chef']):
            g = self.dealt(chars)
            lot = g.g.with_character('Lord of Typhon')
            self.assertTrue(carousel4.typhon_line(g.g, lot))
            left, right = (g.g.players[(lot.seat + d) % len(chars)] for d in (-1, 1))
            self.assertEqual((ch.kind(left.character), ch.kind(right.character)), ('Minion', 'Minion'))
            for q in (left, right):
                self.assertTrue(self.intro(q.name, f'The Demon is {lot.name}'))

    def test_it_kills_each_night_but_the_first(self):
        g = self.game(['Poisoner', 'Lord of Typhon', 'Spy', T1, T2, T3])
        self.assertIsNone(R('Lord of Typhon').night_spec(g, g.g[B], type('N', (), {'first': True})()))
        self.choose(2, A, [D])
        self.choose(2, B, [E])
        run(g.night(2))
        self.assertFalse(g.g[E].alive)

    def test_the_summoner_jinx(self):
        g = self.game([T1, 'Summoner', T2, T3, T4, 'Mayor', 'Monk'], extra=['Lord of Typhon', 'Poisoner'],
                      forced={'Typhon minion': {'character': 'Poisoner'}})
        self.choose(3, B, [E], character='Lord of Typhon')
        run(g.night(3))
        lot = g.g.with_character('Lord of Typhon')
        self.assertIsNotNone(lot)
        self.assertIn(lot.name, (A, C))
        other = D if lot.name == C else G
        self.assertEqual((g.g[other].character, g.g[other].alignment), ('Poisoner', 'evil'))


class LleechTests(Batch3bTest):
    CHARS = [T1, T2, T3, 'Poisoner', 'Lleech', T4]

    def host(self, g, name=B):
        self.choose(1, D, [C])
        self.choose(1, E, [name])
        run(g.night(1))

    def test_the_host_is_poisoned_and_the_lleech_dies_only_with_them(self):
        g = self.game(self.CHARS)
        self.host(g)
        self.assertTrue(g.g.is_poisoned(g.g[B]))
        g.execute(E)
        self.assertTrue(g.g[E].alive)
        self.choose(2, D, [C])
        self.choose(2, E, [E])
        run(g.night(2))
        self.assertTrue(g.g[E].alive)
        self.day(g, 3)
        g.execute(B)
        self.assertFalse(g.g[E].alive)
        self.assertEqual(g.g.winner, 'good')

    def test_killing_the_host_at_night_kills_the_lleech(self):
        g = self.game(self.CHARS)
        self.host(g)
        self.choose(2, D, [C])
        self.choose(2, E, [B])
        run(g.night(2))
        self.assertFalse(g.g[E].alive)
        self.assertIn(E, [e['data'] for e in g.events if e['kind'] == 'dawn'][-1]['deaths'])

    def test_a_poisoned_lleech_can_die_and_poisons_no_one(self):
        g = self.game(self.CHARS)
        self.host(g)
        self.poison(E)
        self.assertFalse(g.g.is_poisoned(g.g[B]))
        g.execute(E)
        self.assertFalse(g.g[E].alive)

    def test_the_assassin_kills_it(self):
        g = self.game([T1, T2, T3, 'Assassin', 'Lleech', T4])
        self.host(g)
        self.choose(2, D, [E])
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertFalse(g.g[E].alive)

    def test_the_slayer_jinx_shooting_the_host_kills_it(self):
        for jinxed in (True, False):
            g = self.game(['Slayer', T2, T3, 'Poisoner', 'Lleech', T4], jinxed=jinxed)
            self.host(g)
            g.slayer(A, B)
            self.assertEqual((g.g[B].alive, g.g[E].alive), (not jinxed, not jinxed))
        g = self.game(['Slayer', T2, T3, 'Poisoner', 'Lleech', T4])
        self.host(g)
        g.slayer(A, E)
        self.assertTrue(g.g[E].alive)

    def test_the_mastermind_jinx_an_executed_host_leaves_it_alive_without_its_ability(self):
        for jinxed in (True, False):
            g = self.game([T1, T2, T3, 'Mastermind', 'Lleech', T4], jinxed=jinxed)
            self.host(g)
            g.execute(B)
            self.assertEqual(g.g[E].alive, jinxed)
            if jinxed:
                self.assertIsNone(g.g.winner)
                self.choose(2, E, [C])
                run(g.night(2))
                self.assertTrue(g.g[C].alive)
                g.execute(E)
                self.assertFalse(g.g[E].alive)

    def test_the_heretic_jinx_only_one_in_play(self):
        s = self.script(['Heretic', 'Lleech', 'Poisoner', 'Imp', 'Monk', 'Mayor', 'Sage'], True)
        self.assertIn('only one of', setup_error(['Heretic', 'Lleech', T1, T2, 'Poisoner'], s))
        for seed in range(30):
            self.assertIsNone(s.clash(random_setup(random.Random(seed), None, 7, s)))

    def test_the_heretic_jinx_a_summoner_summons_another_demon(self):
        g = self.game([T1, 'Summoner', T2, T3, 'Heretic', T4, 'Mayor'], extra=['Lleech', 'Imp'])
        self.choose(3, B, [C], character='Lleech')
        run(g.night(3))
        self.assertEqual((g.g[C].character, g.g[C].alignment), ('Imp', 'evil'))

    def test_a_new_lleech_chooses_a_host_on_its_next_night(self):
        g = self.game([T1, T2, T3, 'Scarlet Woman', 'Lleech', T4, 'Monk'])
        self.host(g)
        self.choose(2, E, [B])
        run(g.night(2))
        self.assertEqual(g.g[D].character, 'Lleech')
        self.choose(3, D, [C])
        run(g.night(3))
        self.assertTrue(g.g[C].alive)
        self.assertTrue(g.g.is_poisoned(g.g[C]))


# ---- The synthetic script and Buyer's Remorse ------------------------------------------------------------------

BATCH = ('Alsaahir', 'Huntsman', 'Snitch', 'Knight', 'Choirboy', 'King', 'Cult Leader', 'Lord of Typhon', 'Lleech')


class Carousel5Tests(unittest.TestCase):
    def test_it_holds_all_nine_and_the_jinxes_and_deals_at_every_size(self):
        s = ch.Script('carousel-5')
        for c in BATCH:
            self.assertIn(c, s.all)
        self.assertTrue(all(s.jinxed(a, b) for a, b in JINXES4))
        for n in range(5, 16):
            for seed in range(20):
                chars = random_setup(random.Random(seed), s.minions[seed % len(s.minions)], n, s)
                self.assertIsNone(setup_error(chars, s))

    def test_every_batch_3b_character_has_storyteller_notes(self):
        from clocktower import judge
        sections = judge._sections(judge.NOTES / 'carousel.md')
        for c in BATCH:
            self.assertIn(c, sections)
            self.assertEqual(ch.rules(c).__module__, 'clocktower.carousel4')

    def test_it_plays_at_every_size(self):
        self.assertEqual(smoke.smoke(ch.Script('carousel-5'), games=1, out=io.StringIO()), [])

    def test_buyers_remorse_plays(self):
        path = smoke.corpus_dir() / 'buyersremorse' / 'script.json'
        if not path.exists():
            raise unittest.SkipTest('no World Championship corpus')
        self.assertEqual(smoke.smoke(ch.Script(path), games=1, out=io.StringIO()), [])


if __name__ == '__main__':
    unittest.main()
