"""Riot (clocktower/carousel_extra.py, batch 6, removable): the Minions becoming Riot on the third night, the riot of
day 3 (each nominee executed at once, nominating the next), each edge its text implies, and its official jinxes with
built characters (docs/carousel-rulings.md, batch 6, Riot). Reverting the commit that built it removes this file with
it. The jinx with the Atheist, another batch 6 character, is tested only while the Atheist is built."""
import io
import json
import unittest

from clocktower import carousel_extra as cx, smoke
from clocktower import characters as ch
from clocktower.fingerprint import file_for, play
from clocktower.game import NAMES, Night

from test_carousel import T1, T2, T3, T4, run
from test_carousel1 import Batch1Test

A, B, C, D, E, F, G, H, I = NAMES
RT = 'Riot'
R = ch.rules
JINXED = ('Banshee', 'Exorcist', 'Farmer', 'Grandmother', 'Innkeeper', 'King', 'Mayor', 'Monk', 'Ravenkeeper', 'Sage',
          'Soldier')


class RiotTest(Batch1Test):
    CHARS = [T1, T2, 'Poisoner', T3, RT, T4, 'Empath']  # C the Poisoner, E the Riot

    def nom(self, name, *answers):
        self.seats[name].day.setdefault('nominate', []).extend({'nominate': x} for x in answers)

    def queue_riot_start(self, g, riot):
        """Only `riot` nominates first."""
        for q in g.g.players:
            if q.name != riot:
                self.seats[q.name].day.setdefault('nominate', []).insert(0, {'nominate': None})

    def riot_day(self, g):
        self.day(g, 3)
        run(g.nominations())


class RiotTests(RiotTest):
    def test_the_minions_become_riot_on_the_third_night(self):
        g = self.game(self.CHARS)
        self.day(g, 3)
        run(R(RT).resolve_night(g, Night(3)))
        self.assertEqual(g.g[C].character, RT)
        self.assertTrue(self.told(C, 'you are now the Riot'))
        g = self.game(self.CHARS)
        self.day(g, 2)
        run(R(RT).resolve_night(g, Night(2)))
        self.assertEqual(g.g[C].character, 'Poisoner')

    def test_no_kill_at_night(self):
        g = self.game(self.CHARS)
        self.day(g, 2)
        run(g.night(2))
        self.assertFalse([e for e in g.events if e['kind'] == 'death'])

    def test_on_day_3_each_nominee_dies_and_nominates_the_next(self):
        g = self.game(self.CHARS)
        self.queue_riot_start(g, A)
        self.nom(A, B)
        self.nom(B, D)
        self.nom(D, E)
        self.riot_day(g)
        self.assertEqual([x for x in (A, B, D, E) if not g.g[x].alive], [B, D, E])
        self.assertEqual((g.g.winner, g.g.reason), ('good', 'The Demon is dead.'))
        self.assertFalse([e for e in g.events if e['kind'] == 'vote'])

    def test_the_riot_must_happen(self):
        g = self.game(self.CHARS, forced={f'Riot nominee:{E}': {'players': [A]}})
        self.riot_day(g)  # nobody nominates: the Riot must start it; nobody names anyone: the Storyteller's call
        self.assertFalse(g.g[A].alive)
        self.assertIn(f'Riot nominee:{E}', g.st.seen)

    def test_other_days_are_as_usual(self):
        g = self.game(self.CHARS)
        self.day(g, 2)
        self.nom(A, B)
        run(g.nominations())
        self.assertTrue(g.g[B].alive)
        self.assertTrue([e for e in g.events if e['kind'] == 'vote'])


class JinxTests(RiotTest):
    def test_riot_executing_a_protected_player_good_wins(self):
        g = self.game([T1, 'Monk', 'Poisoner', T3, RT, T4, 'Empath'])
        g.g.night_choices[3] = {B: [A]}
        self.nom(E, A)
        self.queue_riot_start(g, E)
        self.riot_day(g)
        self.assertEqual(g.g.winner, 'good')
        self.assertTrue(g.g[A].alive)
        g = self.game([T1, 'Soldier', 'Poisoner', T3, RT, T4, 'Empath'])
        self.queue_riot_start(g, E)
        self.nom(E, B)
        self.riot_day(g)
        self.assertEqual(g.g.winner, 'good')

    def test_the_mayor_may_stop_the_riot(self):
        g = self.game([T1, 'Mayor', 'Poisoner', T3, RT, T4, 'Empath'])
        self.queue_riot_start(g, A)
        self.nom(A, C)
        self.decide(B, True)
        self.riot_day(g)
        self.assertEqual(g.g.winner, 'good')  # one Riot alive (the Poisoner is not one in this hand-built day)
        g = self.game([T1, 'Mayor', RT, T3, RT, T4, 'Empath'])
        self.queue_riot_start(g, A)
        self.nom(A, D)
        self.decide(B, True)
        self.riot_day(g)
        self.assertEqual(g.g.winner, 'evil')

    def test_the_grandchild_executed_evil_wins(self):
        g = self.game(['Grandmother', T2, 'Poisoner', T3, RT, T4, 'Empath'])
        g.g.notes['Grandchild'] = B
        self.queue_riot_start(g, A)
        self.nom(A, B)
        self.riot_day(g)
        self.assertEqual(g.g.winner, 'evil')
        self.assertIn('Grandchild', g.g.reason)

    def test_the_king_learns_once_a_player_is_dead(self):
        g = self.game(['King', T2, 'Poisoner', T3, RT, T4, 'Empath'])
        g.g[B].alive = False
        self.day(g, 2)
        run(R(RT).resolve_night(g, Night(2)))
        self.assertTrue(self.told(A, 'is alive'))

    def test_riot_chooses_a_good_player_each_night_a_sage_uses_their_ability(self):
        g = self.game([T1, 'Sage', 'Poisoner', T3, RT, T4, 'Empath'])
        self.choose(2, E, [B])
        self.day(g, 2)
        run(R(RT).resolve_night(g, Night(2)))
        self.assertTrue(g.g[B].alive)
        self.assertTrue(self.told(B, 'Sage'))
        self.choose(3, E, [B])  # not one chosen before: asked again (the Seat's default: the first legal)
        self.day(g, 3)
        run(R(RT).resolve_night(g, Night(3)))
        self.assertEqual(g.g.notes['Riot chose'][:1], [B])
        self.assertNotEqual(g.g.notes['Riot chose'][1], B)

    def test_a_chosen_banshee_dies(self):
        g = self.game([T1, 'Banshee', 'Poisoner', T3, RT, T4, 'Empath'])
        self.choose(2, E, [B])
        self.day(g, 2)
        g.tonight = Night(2)
        run(R(RT).resolve_night(g, g.tonight))
        self.assertFalse(g.g[B].alive)

    def test_the_atheist_jinx_the_storyteller_nominated_in_the_riot_is_voted_on(self):
        if not cx.built('Atheist'):
            self.skipTest('the Atheist is not built')
        g = self.game(['Atheist', T2, T1, T3, RT, T4, 'Empath'])
        self.queue_riot_start(g, A)
        self.nom(A, 'Storyteller')
        for x in g.names:
            self.seats[x].day.setdefault('vote', []).extend([{'vote': True}])
        self.riot_day(g)
        self.assertEqual(g.g.winner, 'good')

    def test_every_jinx_is_declared(self):
        jinxed = sorted(o for a, o in cx.JINXES if a == RT)
        self.assertEqual(jinxed, sorted(JINXED + (('Atheist',) if cx.built('Atheist') else ())))


class ScriptTests(unittest.TestCase):
    def test_the_synthetic_script_holds_every_jinx_and_plays_at_every_size(self):
        s = ch.Script('carousel-12')
        for other in JINXED:
            self.assertTrue(s.jinxed(RT, other), other)
        self.assertEqual(smoke.smoke(s, games=1, out=io.StringIO()), [])

    def test_a_sample_of_its_recorded_seeds_replays_identically(self):
        s = ch.Script('carousel-12')
        recorded = json.loads(file_for(s).read_text())
        for g in recorded['games'][::100]:
            sha, _ = play(g['players'], g['seed'], g['minion'], script=s)
            self.assertEqual(sha, g['sha'], f"carousel-12, {g['players']} players, seed {g['seed']}: changed")


if __name__ == '__main__':
    unittest.main()
