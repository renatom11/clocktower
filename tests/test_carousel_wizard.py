"""The Wizard (clocktower/carousel_extra.py, batch 6, removable): its wish chosen from a curated list of effects the
engine can grant, by number or in words the Storyteller matches to the list, the Storyteller's grant, price and clue,
each chosen among the list's, and the edges its text implies (docs/carousel-rulings.md, batch 6, Wizard). Reverting the
commit that built it removes this file with it."""
import io
import json
import random
import unittest

from clocktower import carousel_extra as cx, smoke
from clocktower import characters as ch
from clocktower.agents import RandomSeat, Request
from clocktower.fingerprint import file_for, play
from clocktower.game import NAMES

from test_carousel import T1, T2, T3, T4, run
from test_carousel1 import Batch1Test

A, B, C, D, E, F, G, H, I = NAMES
WZ = 'Wizard'
R = ch.rules


class WizardTest(Batch1Test):
    CHARS = [T1, T2, WZ, T3, 'Imp', T4, 'Empath']  # C is the Wizard, E the Imp

    def wish(self, n, say, targets=(), forced=None, chars=None, night=2):
        g = self.game(chars or self.CHARS, forced=forced)
        self.day(g, night)
        self.choose(night, E, [D])  # (the Imp kills D)
        self.seats[C].day.setdefault('night', []).append({'say': say, 'targets': list(targets)})
        run(g.night(night))
        return g


class WishTests(WizardTest):
    FREE = {'Wizard grant': {'yes': True}, 'Wizard price': {'statements': ['none']},
            'Wizard clue': {'statements': ['none']}}

    def test_the_list_is_shown_and_a_wish_by_number_is_granted(self):
        g = self.wish(2, '1', [A], forced=self.FREE)
        self.assertFalse(g.g[A].alive)
        self.assertIn({'player': A, 'cause': 'wizard', 'source': C, 'day': 2, 'phase': 'night'}, g.g.death_log)
        req = [r for r in self.seats[C].log if r.kind == 'night' and r.menu][0]
        self.assertEqual(req.menu, cx.wish_menu())
        self.assertIn('1. A player of your choice dies tonight.', req.prompt)
        self.assertTrue(self.told(C, 'your wish is granted'))

    def test_once_per_game(self):
        g = self.wish(2, '1', [A], forced=self.FREE)
        self.seats[C].day.setdefault('night', []).append({'say': '1', 'targets': [B]})
        self.day(g, 3)
        run(g.night(3))
        self.assertTrue(g.g[B].alive)
        self.assertFalse([r for r in self.seats[C].log if r.kind == 'night' and r.menu and r.day == 3])

    def test_no_wish_tonight_keeps_it(self):
        g = self.wish(2, '', forced=self.FREE)
        self.assertFalse(g.g.notes.get('Used', {}).get(C))
        self.seats[C].day.setdefault('night', []).append({'say': '4', 'targets': [E]})
        self.day(g, 3)
        run(g.night(3))
        self.assertTrue(self.told(C, f'{E} is the Imp'))

    def test_a_wish_in_words_is_matched_to_the_list_or_to_none(self):
        g = self.wish(2, 'I wish to see the Grimoire', forced=self.FREE)
        self.assertTrue(self.told(C, 'you see the Grimoire'))
        g = self.wish(2, 'I wish for a pony', forced=self.FREE)
        self.assertTrue(self.told(C, 'not a wish the Storyteller can grant'))
        self.assertFalse(g.g.notes.get('Used', {}).get(C))
        values = [v['statements'][0] for v in g.st.seen[f'Wizard wish:{C}'].values]
        self.assertEqual(values, [w.id for w in cx.WISHES] + ['none'])  # the list, never another

    def test_a_wish_needing_a_player_needs_a_fitting_one(self):
        g = self.wish(2, '7', [A], forced=self.FREE)  # revive: A is alive
        self.assertTrue(self.told(C, 'no wish was made'))
        self.assertFalse(g.g.notes.get('Used', {}).get(C))

    def test_not_granted_poisoned_or_by_the_storyteller(self):
        g = self.game(self.CHARS, forced=self.FREE)
        self.poison(C)
        self.day(g, 2)
        self.choose(2, E, [D])
        self.seats[C].day.setdefault('night', []).append({'say': '1', 'targets': [A]})
        run(g.night(2))
        self.assertTrue(g.g[A].alive)
        self.assertTrue(g.g.notes['Used'][C])  # spent all the same
        self.assertTrue(self.told(C, 'does not grant it'))
        g = self.wish(2, '1', [A], forced={'Wizard grant': {'yes': False}})
        self.assertTrue(g.g[A].alive)

    def test_each_effect(self):
        g = self.wish(2, '2', forced=self.FREE)
        self.assertTrue(g.g.safe(g.g[E], 'execution'))
        g = self.wish(2, '3', [A], forced=self.FREE)
        self.assertEqual(g.g[A].alignment, 'evil')
        g = self.wish(2, '6', [G], forced=self.FREE)
        self.assertTrue(g.g.is_drunk(g.g[G]))
        g = self.wish(2, '8', forced=self.FREE)
        self.assertTrue(self.told(C, 'the Demon\'s bluffs are'))
        g = self.game(self.CHARS, forced=self.FREE)
        g.g[E].alive = False
        self.day(g, 2)
        self.choose(2, E, [D])
        self.seats[C].day.setdefault('night', []).append({'say': '7', 'targets': [E]})
        run(g.night(2))
        self.assertTrue(g.g[E].alive)


class PriceAndClueTests(WizardTest):
    def test_the_price_is_one_of_the_wishs_own(self):
        g = self.wish(2, '1', [A], forced={'Wizard grant': {'yes': True}, 'Wizard price': {'statements': ['dies']},
                                           'Wizard clue': {'statements': ['none']}})
        self.assertFalse(g.g[C].alive)
        values = [v['statements'][0] for v in g.st.seen[f'Wizard price:{C}'].values]
        self.assertEqual(values, list(cx.WISH['kill'].prices) + ['none'])
        g = self.wish(2, '1', [A], forced={'Wizard grant': {'yes': True}, 'Wizard price': {'statements': ['poisoned']},
                                           'Wizard clue': {'statements': ['none']}})
        self.assertTrue(g.g.is_poisoned(g.g[C]))
        g = self.wish(2, '1', [A], forced={'Wizard grant': {'yes': True}, 'Wizard price': {'statements': ['exposed']},
                                           'Wizard clue': {'statements': ['none']}, 'Wizard witness': {'players': [G]}})
        self.assertTrue(self.told(G, f'{C} is a Minion'))

    def test_the_clue(self):
        self.wish(2, '5', forced={'Wizard grant': {'yes': True}, 'Wizard price': {'statements': ['none']},
                                  'Wizard clue': {'statements': ['whispered']},
                                  'Wizard hears': {'players': [B]}})
        self.assertTrue(self.told(B, 'a wish was granted tonight: "You see the Grimoire tonight."'))
        self.wish(2, '5', forced={'Wizard grant': {'yes': True}, 'Wizard price': {'statements': ['none']},
                                  'Wizard clue': {'statements': ['announced']}})
        self.assertTrue(self.public('a wish was granted in the night'))


class BotTests(unittest.TestCase):
    def test_bots_pick_from_a_menu_and_draw_nothing_more_without_one(self):
        for menu in ([], ['1. x', '2. y']):
            a, b = RandomSeat(A, random.Random(5), [A, B, C]), RandomSeat(A, random.Random(5), [A, B, C])
            run(a.act('', Request('night', '', 1, n_targets=1, options=[A, B], min_targets=0)))
            run(b.act('', Request('night', '', 1, n_targets=1, options=[A, B], min_targets=0, menu=menu)))
            self.assertEqual(a.rng.random() == b.rng.random(), not menu)


class ScriptTests(unittest.TestCase):
    def test_the_synthetic_script_plays_at_every_size(self):
        s = ch.Script('carousel-10')
        self.assertIn(WZ, s.minions)
        self.assertEqual(smoke.smoke(s, games=1, out=io.StringIO()), [])

    def test_a_sample_of_its_recorded_seeds_replays_identically(self):
        s = ch.Script('carousel-10')
        recorded = json.loads(file_for(s).read_text())
        for g in recorded['games'][::100]:
            sha, _ = play(g['players'], g['seed'], g['minion'], script=s)
            self.assertEqual(sha, g['sha'], f"carousel-10, {g['players']} players, seed {g['seed']}: changed")


if __name__ == '__main__':
    unittest.main()
