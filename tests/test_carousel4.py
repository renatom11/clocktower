"""Batch 4 of the experimental characters (clocktower/carousel5.py): the Bounty Hunter, Engineer, Princess, Hermit,
Ogre, Psychopath, Wraith and Vizier, each edge their text implies, and every official jinx between them and a built
character (docs/carousel-rulings.md, batch 4)."""
import io
import random
import unittest

from clocktower import carousel3, carousel5, smoke
from clocktower import characters as ch
from clocktower.state import random_setup, setup_error

from test_carousel import JINXES5, O1, T1, T2, T3, T4, run
from test_carousel2 import A, B, C, D, E, F, G
from test_carousel3b import Batch3bTest

R = ch.rules
H = 'Harper'


class Batch4Test(Batch3bTest):
    def nominate(self, g, nominator, nominee, voters=()):
        g.g.nominations.append({'day': g.day, 'nominator': nominator, 'nominee': nominee, 'voters': list(voters),
                                'outcome': 'block'})

    def intro(self, name, text):
        return [e for e in self.g.events if e['to'] == [name] and e['kind'] == 'intro' and text in e['data']['text']]

    def queue(self, name, kind, *answers):
        self.seats[name].day.setdefault(kind, []).extend(answers)


# ---- Townsfolk ---------------------------------------------------------------------------------------------------

class BountyHunterTests(Batch4Test):
    CHARS = ['Bounty Hunter', T1, T2, 'Poisoner', 'Imp', T3]

    def test_starts_knowing_an_evil_player_and_another_when_that_one_dies(self):
        g = self.game(self.CHARS)
        g.g.notes['Evil Townsfolk'] = 'none'  # (no evil Townsfolk in a Grimoire built by hand)
        self.choose(1, D, [B])
        run(g.night(1))
        know = g.g.notes['Bounty Hunter'][A]['know']
        self.assertIn(know, (D, E))
        self.assertTrue(self.told(A, f'{know} is evil'))
        self.choose(2, D, [B])
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertEqual(len(self.told(A, 'Bounty Hunter')), 1)  # the one they know lives: nothing new
        g.g[know].alive = False
        self.choose(3, D, [B])
        self.choose(3, E, [C])
        run(g.night(3))
        other = ({D, E} - {know}).pop()
        self.assertTrue(self.told(A, f'the player you knew has died: {other} is evil'))

    def test_one_townsfolk_is_evil_and_learns_only_that(self):
        g = self.dealt(self.CHARS + [T4], forced={'Bounty Hunter evil townsfolk': {'players': [B]}})
        self.assertEqual(g.g[B].alignment, 'evil')
        self.assertTrue(self.intro(B, 'You are evil'))
        self.assertFalse(self.intro(B, 'The Demon is'))
        self.assertTrue(self.intro(E, f'Your Minion: {D} ('))  # the Demon is not told
        self.assertFalse(self.intro(A, 'You are evil'))

    def test_a_drunk_who_believes_it_makes_no_evil_townsfolk_and_drunk_or_poisoned_may_learn_a_good_player(self):
        g = self.dealt(['Drunk', T1, T2, 'Poisoner', 'Imp', T3, T4, 'Chef'], extra=['Bounty Hunter'])
        self.assertFalse([q for q in g.g.players if q.evil and ch.kind(q.character) == 'Townsfolk'])
        g = self.game(self.CHARS, forced={'Bounty Hunter:': {'players': [B]}})
        g.g.notes['Evil Townsfolk'] = 'none'
        self.poison(A)
        self.choose(1, D, [C])
        run(g.night(1))
        self.assertTrue(self.told(A, f'{B} is evil'))
        with self.assertRaises(ValueError):  # sober, a good player is not a legal answer
            g = self.game(self.CHARS, forced={'Bounty Hunter:': {'players': [B]}})
            self.choose(1, D, [C])
            run(g.night(1))
        g = self.game(['Bounty Hunter', T1, T2, 'Poisoner', 'Vortox', T3], forced={'Bounty Hunter:': {'players': [B]}})
        self.choose(1, D, [C])
        run(g.night(1))
        self.assertTrue(self.told(A, f'{B} is evil'))

    def test_the_kazali_jinx_no_evil_townsfolk_if_the_kazali_makes_the_bounty_hunter_a_minion(self):
        chars = ['Bounty Hunter', T1, T2, T3, 'Kazali', T4]
        for minion in (A, B):
            g = self.dealt(chars, extra=['Poisoner'])
            self.assertEqual(g.g.notes['Evil Townsfolk'], 'waiting')
            self.assertFalse([q for q in g.g.players if q.evil and ch.kind(q.character) == 'Townsfolk'])
            g.st.forced.update({'Bounty Hunter evil townsfolk': {'players': [C]}})
            self.queue(E, 'night', {'targets': [minion], 'character': 'Poisoner'})
            run(g.night(1))
            self.assertEqual(g.g[minion].character, 'Poisoner')
            self.assertEqual(g.g[C].alignment, 'good' if minion == A else 'evil')

    def test_the_philosopher_jinx_a_townsfolk_might_turn_evil(self):
        g = self.game(['Philosopher', T1, T2, 'Poisoner', 'Imp', T3], extra=['Bounty Hunter'],
                      forced={'Bounty Hunter philosopher': {'yes': True},
                              'Bounty Hunter evil townsfolk': {'players': [B]}})
        self.choose(1, A, character='Bounty Hunter')
        run(g.night(1))
        self.assertEqual(g.g[B].alignment, 'evil')
        self.assertTrue(self.told(B, 'you are now evil'))
        self.assertTrue(self.told(A, 'is evil'))
        g = self.game(['Philosopher', T1, T2, 'Poisoner', 'Imp', T3], jinxed=False, extra=['Bounty Hunter'])
        self.choose(1, A, character='Bounty Hunter')
        run(g.night(1))
        self.assertFalse([q for q in g.g.players if q.evil and ch.kind(q.character) == 'Townsfolk'])


class EngineerTests(Batch4Test):
    CHARS = ['Engineer', T1, T2, 'Poisoner', 'Imp', T3, T4, 'Spy']

    def test_choosing_a_demon_the_demon_becomes_it_once_per_game(self):
        g = self.game(self.CHARS, extra=['Vortox'])
        self.choose(1, A, character='Vortox')
        run(g.night(1))
        self.assertEqual((g.g[E].character, g.g[E].alignment), ('Vortox', 'evil'))
        self.assertTrue(self.told(E, 'you are now the Vortox'))
        self.assertIsNone(R('Engineer').night_spec(g, g.g[A], None))

    def test_choosing_minions_one_in_play_stays_the_others_change(self):
        g = self.game(self.CHARS, extra=['Witch', 'Vizier'])
        self.queue(A, 'night', {'character': 'Witch'}, {'character': 'Spy'})
        run(g.night(1))
        self.assertEqual((g.g[D].character, g.g[H].character), ('Witch', 'Spy'))
        self.assertTrue(self.told(D, 'you are now the Witch'))
        self.assertFalse(self.told(H, 'you are now'))

    def test_null_keeps_it_drunk_spends_it_and_the_marionette_cannot_be_chosen(self):
        g = self.game(self.CHARS, extra=['Vortox', 'Marionette'])
        run(g.night(1))
        self.assertIsNotNone(R('Engineer').night_spec(g, g.g[A], None))
        self.choose(2, A, character='Marionette')
        self.choose(2, D, [B])
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertTrue(self.told(A, 'cannot be chosen'))
        self.assertIsNotNone(R('Engineer').night_spec(g, g.g[A], None))
        self.poison(A)
        self.choose(3, A, character='Vortox')
        self.choose(3, D, [B])
        self.choose(3, E, [C])
        run(g.night(3))
        self.assertEqual(g.g[E].character, 'Imp')
        self.assertIsNone(R('Engineer').night_spec(g, g.g[A], None))

    def test_the_summoner_jinx_the_storyteller_summons(self):
        chars = ['Engineer', T1, T2, 'Summoner', T3, T4, 'Mayor']
        for jinxed in self.both():
            g = self.game(chars, jinxed, extra=['Poisoner', 'Imp'],
                          forced={'Summoner:': {'players': [C], 'character': 'Imp'}})
            self.choose(1, A, character='Poisoner')
            run(g.night(1))
            self.assertEqual(g.g[D].character, 'Poisoner')
            self.assertIsNone(g.g.check_victory() if jinxed else None)
            self.choose(2, D, [B])
            run(g.night(2))
            self.choose(3, D, [B])
            run(g.night(3))
            self.assertEqual(g.g[C].character == 'Imp', jinxed)


class PrincessTests(Batch4Test):
    CHARS = ['Princess', T1, T2, 'Poisoner', 'Imp', T3]

    def night2(self, g, kill=C):
        self.choose(2, D, [B])
        self.choose(2, E, [kill])
        run(g.night(2))

    def test_her_first_day_execution_stops_the_demon_killing_tonight(self):
        g = self.game(self.CHARS)
        self.nominate(g, A, B)
        g.execute(B)
        self.night2(g)
        self.assertTrue(g.g[C].alive)
        self.day(g, 2)
        self.nominate(g, A, F)
        g.execute(F)
        self.choose(3, E, [C])
        run(g.night(3))
        self.assertFalse(g.g[C].alive)  # (only her 1st day)

    def test_another_nominator_or_a_poisoned_princess_the_demon_kills(self):
        g = self.game(self.CHARS)
        self.nominate(g, F, B)
        g.execute(B)
        self.night2(g)
        self.assertFalse(g.g[C].alive)
        g = self.game(self.CHARS)
        self.nominate(g, A, B)
        g.execute(B)
        self.choose(2, D, [A])  # the Poisoner poisons her before her step
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertFalse(g.g[C].alive)

    def test_the_al_hadikhia_jinx_no_one_dies_to_it(self):
        g = self.game(['Princess', T1, T2, 'Poisoner', 'Al-Hadikhia', T3])
        self.nominate(g, A, B)
        g.execute(B)
        self.choose(2, D, [B])
        self.choose(2, E, [A, C, F])
        self.decide(A, False)
        self.decide(C, False)
        self.decide(F, False)
        run(g.night(2))
        self.assertTrue(all(g.g[x].alive for x in (A, C, F)))

    def test_the_cannibal_jinx_the_cannibal_executing_the_princess_stops_the_kill(self):
        for jinxed in self.both():
            g = self.game(['Cannibal', 'Princess', T2, 'Poisoner', 'Imp', T3], jinxed)
            self.day(g, 2)
            self.nominate(g, A, B)
            g.execute(B)
            run(g.run_pending())
            self.assertIn('Princess', g.g[A].extra)
            self.choose(3, D, [F])
            self.choose(3, E, [C])
            run(g.night(3))
            self.assertEqual(g.g[C].alive, jinxed)


# ---- Outsiders ---------------------------------------------------------------------------------------------------

class HermitTests(Batch4Test):
    CHARS = ['Hermit', T1, T2, 'Poisoner', 'Imp', T3]

    def hermit(self, chars=None, extra=('Saint', 'Recluse', 'Drunk', 'Butler'), **kw):
        g = self.dealt(chars or self.CHARS, extra=list(extra), **kw)
        return g

    def test_has_every_outsider_ability_on_the_script_but_the_illusions_and_the_butler(self):
        g = self.hermit()
        self.assertEqual(sorted(set(g.g[A].extra) - {O1}), ['Recluse', 'Saint'])
        self.assertIn('Saint', g.g.abilities(g.g[A]))
        self.assertEqual(R('Hermit').registers_evil(g.g, g.g[A]), {True, False})
        g.execute(A)
        self.assertEqual(g.g.winner, 'evil')  # the Saint's

    def test_poisoned_no_saint_loss_and_no_misregistration(self):
        g = self.hermit()
        self.poison(A)
        self.assertEqual(R('Hermit').registers_evil(g.g, g.g[A]), {False})
        g.execute(A)
        self.assertIsNone(g.g.winner)

    def test_minus_one_outsider_at_setup(self):
        fewer = ['Hermit', T1, T2, T3, T4, 'Washerwoman', 'Chef', 'Poisoner', 'Imp']
        self.assertIsNone(setup_error(fewer, self.script(fewer, True)))
        chars = ['Hermit', 'Saint', T1, T2, T3, T4, 'Washerwoman', 'Poisoner', 'Imp']
        self.assertIsNone(setup_error(chars, self.script(chars, True)))
        g = self.hermit(chars, forced={'Hermit fewer': {'yes': True}}, extra=['Chef', 'Soldier'])
        g.forced = None
        run(R('Hermit').setup(g))
        self.assertEqual(sum(1 for q in g.g.players if ch.kind(q.character) == 'Outsider'), 1)

    def test_the_damsel_heretic_and_politician_abilities(self):
        g = self.hermit(extra=['Damsel', 'Heretic'])
        self.assertTrue(self.intro(D, 'A Damsel is in play'))
        g.g.winner, g.g.reason = 'good', 'test'
        g.g.finish()
        self.assertEqual(g.g.winner, 'evil')  # the Heretic's
        g = self.hermit(extra=['Damsel'])
        self.claim(D, 'Damsel', target=A)
        self.assertEqual(g.g.winner, 'evil')

    def test_the_ogre_and_tinker_abilities_wake_and_act(self):
        g = self.hermit(extra=['Ogre', 'Tinker'], forced={'Tinker:': {'yes': False}})
        self.choose(1, A, [D])
        run(g.night(1))
        self.assertEqual(g.g[A].alignment, 'evil')
        g.st.forced['Tinker:'] = {'yes': True}
        self.choose(2, D, [B])
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertFalse(g.g[A].alive)


class OgreTests(Batch4Test):
    CHARS = ['Ogre', T1, T2, 'Poisoner', 'Imp', T3]

    def test_becomes_the_chosen_players_alignment_and_is_not_told_even_if_drunk(self):
        for poisoned in (False, True):
            g = self.game(self.CHARS)
            if poisoned:
                self.poison(A)
            self.choose(1, A, [E])
            self.choose(1, D, [B])
            run(g.night(1))
            self.assertEqual(g.g[A].alignment, 'evil')
            self.assertFalse(self.told(A, 'evil'))
            self.assertIsNone(R('Ogre').night_spec(g, g.g[A], None))
        g = self.game(self.CHARS)
        self.choose(1, A, [B])
        self.choose(1, D, [B])
        run(g.night(1))
        self.assertEqual(g.g[A].alignment, 'good')

    def test_a_drunk_who_believes_it_changes_nothing(self):
        g = self.game(['Drunk', T1, T2, 'Poisoner', 'Imp', T3], extra=['Ogre'])
        g.g[A].shown = 'Ogre'
        self.choose(1, A, [E])
        self.choose(1, D, [B])
        run(g.night(1))
        self.assertEqual(g.g[A].alignment, 'good')

    def test_the_spy_jinx_the_spy_registers_evil(self):
        for jinxed in self.both():
            g = self.game(['Ogre', T1, T2, 'Spy', 'Imp', T3], jinxed, forced={'Ogre:': {'yes': False}})
            self.choose(1, A, [D])
            run(g.night(1))
            self.assertEqual(g.g[A].alignment, 'evil' if jinxed else 'good')

    def test_the_recluse_jinx_the_ogre_learns_it_is_evil(self):
        for jinxed in self.both():
            g = self.game(['Ogre', 'Recluse', T2, 'Poisoner', 'Imp', T3], jinxed, forced={'Ogre:': {'yes': True}})
            self.choose(1, A, [B])
            self.choose(1, D, [C])
            run(g.night(1))
            self.assertEqual(g.g[A].alignment, 'evil')
            self.assertEqual(bool(self.told(A, 'you are evil')), jinxed)

    def test_the_pit_hag_jinx_an_evil_ogre_stays_evil(self):
        chars = [T1, T2, T3, T4, 'Monk', 'Pit-Hag', 'Imp', 'Scarlet Woman']
        for jinxed in self.both():
            g = self.game(chars, jinxed, extra=['Ogre'])
            self.choose(2, F, [H], 'Ogre')
            self.choose(2, G, [A])
            self.queue(H, 'night', {'targets': [B]})  # (chosen at once, as they become the Ogre)
            run(g.night(2))
            self.assertEqual(g.g[H].character, 'Ogre')
            self.assertEqual(g.g[H].alignment, 'evil' if jinxed else 'good')

    def test_the_boffin_jinx_the_demon_never_has_it(self):
        g = self.game(['Ogre', T1, T2, 'Boffin', 'Imp', T3], extra=['Ogre'])
        self.assertNotIn('Ogre', carousel3.boffin_options(g.g))
        self.assertNotIn('Ogre', carousel3.BOFFIN_USABLE)


# ---- Minions -----------------------------------------------------------------------------------------------------

class PsychopathTests(Batch4Test):
    CHARS = [T1, T2, T3, 'Psychopath', 'Imp', T4]

    def test_kills_by_day_publicly_once_a_day_not_during_nominations(self):
        g = self.game(self.CHARS)
        self.claim(D, 'Psychopath', target=A)
        self.assertFalse(g.g[A].alive)
        self.assertTrue([e for e in g.events if e['kind'] == 'died' and e['data']['player'] == A])
        self.claim(D, 'Psychopath', target=B)
        self.assertTrue(g.g[B].alive)
        self.day(g, 2)
        g.phase = 'nominations'
        self.claim(D, 'Psychopath', target=B)
        self.assertTrue(g.g[B].alive)

    def test_a_bluff_or_a_poisoned_psychopath_kills_nobody(self):
        g = self.game(self.CHARS)
        self.claim(A, 'Psychopath', target=B)
        self.assertTrue(g.g[B].alive)
        self.poison(D)
        self.claim(D, 'Psychopath', target=B)
        self.assertTrue(g.g[B].alive)

    def test_executed_only_dies_losing_roshambo(self):
        for won in (True, False):
            g = self.game(self.CHARS, forced={'Psychopath roshambo': {'yes': won}})
            self.nominate(g, A, D)
            run(g.execution(D))
            self.assertEqual(g.g[D].alive, won)
            self.assertTrue(self.public(f'{D} {"wins" if won else "loses"}'))
        g = self.game(self.CHARS, forced={'Psychopath roshambo': {'yes': True}})
        self.poison(D)
        run(g.execution(D))
        self.assertFalse(g.g[D].alive)
        self.assertFalse(self.public('roshambo'))


class WraithTests(Batch4Test):
    CHARS = [T1, 'Empath', T3, 'Wraith', 'Imp', 'Poisoner', 'Monk']

    def night2(self, g):
        self.choose(2, E, [A])
        self.choose(2, F, [C])
        self.choose(2, G, [B])
        run(g.night(2))

    def test_eyes_open_it_sees_every_wake_shut_only_the_evil_ones(self):
        g = self.game(self.CHARS)
        self.decide(D, True)
        self.night2(g)
        seen = self.told(D, 'Wraith (eyes open)')[0]
        for x in (E, F, G, B):
            self.assertIn(x, seen)
        self.assertIn(f'{G} (chose {B})', seen)
        g = self.game(self.CHARS)
        self.decide(D, False)
        self.night2(g)
        seen = self.told(D, 'Wraith (with the evil players)')[0]
        self.assertIn(f'{E} (chose {A})', seen)
        self.assertNotIn(G, seen)

    def test_poisoned_or_dead_it_sees_nothing(self):
        g = self.game(self.CHARS)
        self.poison(D)
        self.decide(D, True)
        self.night2(g)
        self.assertFalse(self.told(D, 'awake tonight'))

    def test_the_alchemist_jinx_no_ability_and_a_guess_after_each_execution(self):
        g = self.game(['Alchemist', T1, T2, 'Wraith', 'Imp', T3])
        self.alchemist(g, A, 'Wraith')
        self.assertNotIn('Wraith', g.g[A].extra)
        self.queue(A, 'night', {'targets': [D]})
        g.execute(B)
        run(g.run_pending())
        self.assertTrue(self.public(f'{A} publicly guesses that {D} is the Wraith'))
        self.assertEqual(g.g.notes['Demon must choose'][2], D)
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertFalse(g.g[D].alive)

    def test_the_magician_jinx_the_magician_may_guess(self):
        for jinxed in self.both():
            g = self.game(['Magician', T1, T2, 'Wraith', 'Imp', T3], jinxed)
            self.queue(A, 'night', {'targets': [D]})
            g.execute(B)
            run(g.run_pending())
            self.assertEqual(bool(self.public('is the Wraith')), jinxed)

    def test_the_plague_doctor_jinx_a_minion_gains_it(self):
        g = self.game(['Plague Doctor', T2, T3, 'Poisoner', 'Imp', T4], extra=['Wraith'],
                      forced={'Plague Doctor': {'character': 'Wraith'}})
        g.execute(A)
        run(g.run_pending())
        self.assertEqual(g.g[D].extra, ['Wraith'])
        self.decide(D, True)
        self.choose(2, D, [B])
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertTrue(self.told(D, 'Wraith (eyes open)'))


class VizierTests(Batch4Test):
    CHARS = [T1, T2, T3, 'Vizier', 'Imp', T4, 'Empath']

    def test_every_player_knows_unless_the_alsaahir_or_investigator_is_on_the_script(self):
        self.dealt(self.CHARS)
        for x in (A, D, E):
            self.assertTrue(self.intro(x, f'{D} is the Vizier'))
        for other in ('Alsaahir', 'Investigator'):
            self.dealt(self.CHARS, extra=[other])
            self.assertFalse(self.intro(A, 'is the Vizier'))

    def test_cannot_die_by_day_but_by_night(self):
        g = self.game(self.CHARS)
        g.execute(D)
        self.assertTrue(g.g[D].alive)
        self.assertTrue([e for e in g.events if e['kind'] == 'execution' and e['data'].get('survived')])
        self.choose(2, E, [D])
        run(g.night(2))
        self.assertFalse(g.g[D].alive)
        g = self.game(self.CHARS)
        self.poison(D)
        g.execute(D)
        self.assertFalse(g.g[D].alive)

    def test_if_good_voted_it_may_execute_at_once(self):
        g = self.game(self.CHARS)
        self.nominate(g, A, B, voters=[C])
        self.decide(D, True)
        self.assertTrue(run(g.vote_over_judged(B)))
        g = self.game(self.CHARS)
        self.nominate(g, A, B, voters=[E])  # only the Demon voted: not asked
        self.decide(D, True)
        self.assertFalse(run(g.vote_over_judged(B)))
        self.assertFalse([r for r in self.seats[D].log if r.kind == 'decide'])
        g = self.game(self.CHARS)
        self.poison(D)
        self.nominate(g, A, B, voters=[C])
        self.decide(D, True)
        self.assertFalse(run(g.vote_over_judged(B)))

    def test_the_execution_comes_at_once_and_ends_the_nominations(self):
        g = self.game(self.CHARS)
        self.queue(A, 'nominate', {'nominate': B})
        self.queue(C, 'vote', {'vote': True})
        self.decide(D, True)
        run(g.nominations())
        ex = [e['data'] for e in g.events if e['kind'] == 'execution']
        self.assertEqual([x['player'] for x in ex], [B])
        self.assertFalse(g.g[B].alive)
        self.assertTrue(self.public(f'{D}, the Vizier, chooses to execute {B} immediately'))

    def test_the_courtier_and_preacher_jinxes_it_learns_it_and_still_cannot_die_by_day(self):
        for jinxed in self.both():
            g = self.game(['Courtier', T1, T2, 'Vizier', 'Imp', T3], jinxed)
            self.choose(1, A, character='Vizier')
            run(g.night(1))
            self.assertTrue(g.g.is_drunk(g.g[D]))
            self.assertEqual(bool(self.told(D, 'you have lost your ability (the Courtier)')), jinxed)
            g.execute(D)
            self.assertEqual(g.g[D].alive, jinxed)
        g = self.game(['Preacher', T1, T2, 'Vizier', 'Imp', T3])
        self.choose(1, A, [D])
        run(g.night(1))
        self.assertTrue(self.told(D, 'you have lost your ability (the Preacher)'))
        g.execute(D)
        self.assertTrue(g.g[D].alive)

    def test_the_fearmonger_jinx_it_learns_the_choice_and_cannot_execute_them(self):
        g = self.game([T1, T2, T3, 'Vizier', 'Imp', T4, 'Fearmonger'])
        self.choose(1, G, [B])
        run(g.night(1))
        self.assertTrue(self.told(D, f'the Fearmonger ({G}) has chosen {B}'))
        self.nominate(g, A, B, voters=[C])
        self.decide(D, True)
        self.assertFalse(run(g.vote_over_judged(B)))

    def test_the_magician_jinx_no_ability_and_immune(self):
        g = self.dealt(['Magician', T1, T2, 'Vizier', 'Imp', T3, T4])
        self.assertTrue(self.intro(E, f'Your Minion: {D} ('))  # the Demon sees no Magician among its Minions
        self.nominate(g, B, A, voters=[C])
        self.decide(D, True)
        self.assertFalse(run(g.vote_over_judged(A)))

    def test_the_politician_and_zealot_jinxes_they_might_register_evil(self):
        for c in ('Politician', 'Zealot'):
            for evil in (True, False):
                g = self.game([c, T1, T2, 'Vizier', 'Imp', T3], forced={'Vizier sees': {'yes': evil}})
                self.nominate(g, B, C, voters=[A, E])
                self.decide(D, True)
                self.assertEqual(run(g.vote_over_judged(C)), not evil)


# ---- The synthetic script --------------------------------------------------------------------------------------

BATCH = ('Bounty Hunter', 'Engineer', 'Princess', 'Hermit', 'Ogre', 'Psychopath', 'Wraith', 'Vizier')


class Carousel6Tests(unittest.TestCase):
    def test_it_holds_all_eight_and_the_jinxes_and_deals_at_every_size(self):
        s = ch.Script('carousel-6')
        for c in BATCH:
            self.assertIn(c, s.all)
        self.assertTrue(all(s.jinxed(a, b) for a, b in JINXES5))
        for n in range(5, 16):
            for seed in range(20):
                chars = random_setup(random.Random(seed), s.minions[seed % len(s.minions)], n, s)
                self.assertIsNone(setup_error(chars, s))

    def test_every_batch_4_character_has_storyteller_notes(self):
        from clocktower import judge
        sections = judge._sections(judge.NOTES / 'carousel.md')
        for c in BATCH:
            self.assertIn(c, sections)
            self.assertEqual(ch.rules(c).__module__, 'clocktower.carousel5')

    def test_it_plays_at_every_size(self):
        self.assertEqual(smoke.smoke(ch.Script('carousel-6'), games=1, out=io.StringIO()), [])

    def test_contempt_plays(self):
        path = smoke.corpus_dir().parent.parent.parent / 'carousel-collection' / 'contempt' / 'script.json'
        path = path if path.exists() else smoke.Path('/workspace/carousel-collection/contempt/script.json')
        if not path.exists():
            raise unittest.SkipTest('no Carousel Script Collection')
        self.assertEqual(smoke.smoke(ch.Script(path), games=1, out=io.StringIO()), [])

    def test_the_hermit_has_no_ability_the_engine_cannot_hold(self):
        self.assertTrue({'Drunk', 'Lunatic', 'Butler', 'Puzzlemaster'} <= set(carousel5.HERMIT_NONE))
        self.assertEqual(ch.rules('Hermit').outsider_choices, (-1, 0))
        self.assertTrue(O1)


if __name__ == '__main__':
    unittest.main()
