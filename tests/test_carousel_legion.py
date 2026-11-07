"""Legion (clocktower/carousel_extra.py, batch 6, removable): most players Legion, one Demon character shared, its night
kill, executions that fail when only evil voted, its registration as a Minion too, each edge its text implies, and its
official jinxes with built characters (docs/carousel-rulings.md, batch 6, Legion). Reverting the commit that built it
removes this file with it."""
import io
import json
import random
import unittest

from clocktower import carousel_extra as cx, smoke
from clocktower import characters as ch
from clocktower.fingerprint import file_for, play
from clocktower.game import NAMES, Night
from clocktower.state import random_setup, setup_error

from test_carousel import T1, T2, T3, run
from test_carousel1 import Batch1Test

A, B, C, D, E, F, G, H, I = NAMES
LG = 'Legion'
R = ch.rules
JINXED = ('Engineer', 'Hatter', 'Minstrel', 'Politician', 'Preacher', 'Summoner', 'Zealot', 'Magician')


class LegionTest(Batch1Test):
    CHARS = [T1, LG, T2, LG, LG, T3, LG]  # 7 players: four Legion (B, D, E, G), three good

    def vote(self, nominee, voters):
        g = self.g
        g.g.nominations.append({'day': g.day, 'nominator': voters[0], 'nominee': nominee, 'voters': list(voters),
                                'outcome': 'block'})


class DealTests(unittest.TestCase):
    def test_most_players_are_legion_at_every_size(self):
        s = ch.Script('carousel-11')
        seen = 0
        for n in range(5, 16):
            for seed in range(40):
                chars = random_setup(random.Random(seed), players=n, script=s)
                self.assertIsNone(setup_error(chars, s), chars)
                if LG in chars:
                    seen += 1
                    self.assertEqual(chars.count(LG), n // 2 + 1)
                    self.assertFalse([c for c in chars if ch.kind(c) == 'Minion'])
        self.assertTrue(seen)

    def test_the_deal_is_checked(self):
        s = ch.Script('carousel-11')
        self.assertIsNone(setup_error(['Chef', 'Empath', LG, LG, LG], s))
        self.assertIn('most players', setup_error(['Chef', 'Empath', 'Monk', LG, LG], s))
        self.assertIn('only Legion', setup_error(['Chef', 'Empath', LG, LG, 'Poisoner'], s))


class LegionTests(LegionTest):
    def test_the_legion_learn_each_other_and_the_bluffs_and_no_minions(self):
        self.dealt(self.CHARS, extra=['Imp', 'Chef', 'Empath', 'Monk'])
        text = self.intro(B, 'You are one of the Legion')[0]
        self.assertIn(f'the other Legion are {D}, {E}, {G}', text)
        self.assertIn('for evil to bluff', text)
        self.assertFalse(self.intro(B, 'No player is a Minion yet'))

    def test_one_player_might_die_each_night_but_the_first(self):
        g = self.game(self.CHARS, forced={f'{LG}:2': {'players': [A]}})
        run(g.night(1))
        self.assertTrue(g.g[A].alive)
        self.day(g, 2)
        run(g.night(2))
        self.assertFalse(g.g[A].alive)
        self.assertEqual([v['players'] for v in g.st.seen[f'{LG}:2'].values], [[A], [C], [F], []])

    def test_good_wins_only_when_every_legion_is_dead(self):
        g = self.game(self.CHARS)
        for x in (B, D, E):
            g.g[x].alive = False
        self.assertIsNone(g.g.check_victory())
        g.g[G].alive = False
        self.assertEqual(g.g.check_victory(), 'good')

    def test_an_execution_fails_if_only_evil_voted(self):
        g = self.game(self.CHARS)
        self.vote(A, [B, D, E])
        run(g.execution(A))
        self.assertTrue(g.g[A].alive)
        self.assertTrue([e for e in g.events if e['kind'] == 'execution' and e['data'].get('survived')])
        g = self.game(self.CHARS)
        self.vote(A, [B, D, C])  # a good player voted too
        run(g.execution(A))
        self.assertFalse(g.g[A].alive)
        g = self.game(self.CHARS)
        run(g.execution(A))  # no vote (the Storyteller's execution): not "only evil voted"
        self.assertFalse(g.g[A].alive)

    def test_registers_as_a_minion_too_and_the_slayer_kills_it(self):
        g = self.game([T1, LG, 'Slayer', LG, LG, T3, LG], extra=['Poisoner'])
        self.assertEqual(g.g.registers_as(g.g[B]), {LG})  # (as a Minion too only to the Investigator)
        g.slayer(C, B)
        self.assertFalse(g.g[B].alive)

    def test_the_investigator_may_see_a_legion_as_a_minion(self):
        g = self.game(['Investigator', LG, T2, LG, LG, T3, LG], extra=['Poisoner'])
        run(g.night(1))
        self.assertTrue(self.told(A, 'is the Poisoner'))


class JinxTests(LegionTest):
    def test_the_engineer_knows_and_has_no_ability_the_hatter_has_none(self):
        g = self.dealt(['Engineer', LG, 'Hatter', LG, LG, T3, LG], extra=['Imp', 'Poisoner'])
        self.assertTrue(self.intro(A, 'Legion is in play, so you have no ability'))
        self.assertTrue(g.g.is_drunk(g.g[A]))
        g.g.notes['Tea party'] = 2  # the Hatter died: no tea party while Legion is in play
        self.day(g, 2)
        run(R(LG).resolve_night(g, Night(2)))
        self.assertIsNone(g.g.notes['Tea party'])

    def test_legion_created_makes_every_evil_player_legion(self):
        g = self.game([T1, 'Poisoner', T2, 'Imp', 'Spy', T3, 'Chef'], extra=[LG])
        run(g.change(g.g[D], character=LG))
        self.assertEqual([q.character for q in g.g.players if q.evil], [LG, LG, LG])

    def test_politician_and_zealot_might_register_evil_to_legion(self):
        g = self.game([T1, LG, 'Politician', LG, LG, T3, LG], forced={'Legion sees': {'yes': True}})
        self.vote(A, [B, C])
        run(g.execution(A))
        self.assertTrue(g.g[A].alive)
        self.assertIn(f'Legion sees:{C}', g.st.seen)

    def test_the_minstrel_legion_keep_their_ability_and_the_minstrel_might_learn(self):
        g = self.game(['Minstrel', LG, T2, LG, LG, T3, LG], forced={'Legion revealed': {'yes': True}})
        self.vote(B, [A, C])
        run(g.execution(B))
        run(g.run_pending())
        self.assertFalse(g.g[B].alive)
        self.assertTrue(g.g.is_drunk(g.g[C]))
        self.assertFalse(g.g.is_drunk(g.g[D]))
        self.assertTrue(self.told(A, f'{B} is Legion'))

    def test_the_preacher_might_learn_they_are_legion_who_keep_their_ability(self):
        g = self.game(['Preacher', LG, T2, LG, LG, T3, LG], forced={'Legion revealed': {'yes': True}})
        self.choose(1, A, [B])
        run(g.night(1))
        self.assertTrue(self.told(A, f'{B} is Legion'))
        self.assertFalse(g.g.is_drunk(g.g[B]))

    def test_with_the_magician_each_legion_learns_only_the_good_players_but_the_magician(self):
        self.dealt(['Magician', LG, T2, LG, LG, T3, LG], extra=['Imp', 'Poisoner'])
        text = self.intro(B, 'You are one of the Legion')[0]
        self.assertIn(f'which players are good: {C}, {F}.', text)
        self.assertNotIn('other Legion', text)

    def test_every_jinx_is_declared(self):
        self.assertEqual(sorted(o for a, o in cx.JINXES if a == LG), sorted(JINXED))


class ScriptTests(unittest.TestCase):
    def test_the_synthetic_script_holds_every_jinx_and_plays_at_every_size(self):
        s = ch.Script('carousel-11')
        for other in JINXED:
            self.assertTrue(s.jinxed(LG, other), other)
        self.assertEqual(smoke.smoke(s, games=1, out=io.StringIO()), [])

    def test_a_sample_of_its_recorded_seeds_replays_identically(self):
        s = ch.Script('carousel-11')
        recorded = json.loads(file_for(s).read_text())
        for g in recorded['games'][::100]:
            sha, _ = play(g['players'], g['seed'], g['minion'], script=s)
            self.assertEqual(sha, g['sha'], f"carousel-11, {g['players']} players, seed {g['seed']}: changed")


if __name__ == '__main__':
    unittest.main()
