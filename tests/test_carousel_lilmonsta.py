"""Lil' Monsta (clocktower/carousel_extra.py, batch 6, removable): the deal with a Minion in the Demon's seat, the
Minions' nightly choice of a babysitter who is the Demon, its kill, how the babysitter registers and dies, each edge its
text implies, and its official jinxes with built characters (docs/carousel-rulings.md, batch 6, Lil' Monsta). Reverting
the commit that built it removes this file with it."""
import io
import json
import random
import unittest

from clocktower import carousel_extra, smoke
from clocktower import characters as ch
from clocktower.fingerprint import file_for, play
from clocktower.game import NAMES, Night
from clocktower.state import SETUPS, random_setup, setup_error

from test_carousel import T1, T2, T3, T4, run
from test_carousel1 import Batch1Test

A, B, C, D, E, F, G, H, I = NAMES
LM = "Lil' Monsta"
R = ch.rules


class LilMonstaTest(Batch1Test):
    # 7 players: 5 Townsfolk, no Outsider, and Lil' Monsta's 2 Minions (C and E) in the Minion's and the Demon's seats
    CHARS = [T1, T2, 'Poisoner', T3, 'Spy', T4, 'Empath']

    def start(self, chars=None, sitter=C, others=None, extra=(), forced=None, night=True):
        g = self.dealt(chars or self.CHARS, extra=[LM, *extra], forced=forced)
        minions = [q.name for q in g.g.players if ch.kind(q.character) == 'Minion' and R(q.shown).evil]
        for m in minions:
            self.queue(m, 'night', {'targets': [(others or {}).get(m, sitter)]})
        if night:
            run(g.night(1))
        return g

    def queue(self, name, kind, *answers):
        self.seats[name].day.setdefault(kind, []).extend(answers)

    def rec(self):
        return self.g.g.notes[LM]


class DealTests(unittest.TestCase):
    def test_never_dealt_a_minion_in_the_demons_seat_at_every_size(self):
        s = ch.Script.of('lm-only', ['Washerwoman', 'Librarian', 'Investigator', 'Chef', 'Empath', 'Fortune Teller',
                                     'Undertaker', 'Monk', 'Ravenkeeper', 'Virgin', 'Slayer', 'Soldier', 'Mayor',
                                     'Butler', 'Recluse', 'Saint', 'Poisoner', 'Spy', 'Scarlet Woman', 'Assassin', LM])
        for n in range(5, 16):
            for seed in range(20):
                chars = random_setup(random.Random(seed), players=n, script=s)
                self.assertNotIn(LM, chars)
                self.assertFalse([c for c in chars if ch.kind(c) == 'Demon'])
                self.assertEqual(sum(ch.kind(c) == 'Minion' for c in chars), SETUPS[n][2] + 1, (n, chars))
                self.assertIsNone(setup_error(chars, s), (n, chars))

    def test_the_deal_is_checked(self):
        s = ch.Script.of('lm-imp', ['Washerwoman', 'Librarian', 'Chef', 'Empath', 'Monk', 'Butler', 'Poisoner', 'Spy',
                                    'Baron', LM, 'Imp'])
        good = ['Washerwoman', 'Librarian', 'Chef']
        self.assertIsNone(setup_error(good + ['Poisoner', 'Spy'], s))  # 5: Lil' Monsta's two Minions
        self.assertIsNone(setup_error(good + ['Poisoner', 'Imp'], s))  # an Imp's deal
        self.assertIn('never dealt', setup_error(good + ['Poisoner', LM], s))
        self.assertIn('2 Minions', setup_error(good + ['Empath', 'Poisoner'], s))

    def test_the_barons_outsiders_count_with_lil_monsta_too(self):
        s = ch.Script.of('lm-baron', ['Washerwoman', 'Librarian', 'Chef', 'Empath', 'Monk', 'Butler', 'Recluse',
                                      'Saint', 'Drunk', 'Poisoner', 'Spy', 'Baron', LM])
        # 7 players with the Baron: 3 Townsfolk, 2 Outsiders, 2 Minions
        self.assertIsNone(setup_error(['Washerwoman', 'Librarian', 'Chef', 'Butler', 'Saint', 'Baron', 'Spy'], s))
        self.assertIn('Townsfolk', setup_error(['Washerwoman', 'Librarian', 'Chef', 'Empath', 'Monk', 'Baron', 'Spy'],
                                               s))

    def test_the_rule_is_explained_on_its_scripts_only(self):
        s = ch.Script('carousel-8')
        self.assertTrue(any("Lil' Monsta is never dealt" in line for c in s.all for line in R(c).rule_text(s)))
        self.assertEqual(s.dealers, [LM])


class BabysitterTests(LilMonstaTest):
    def test_the_minions_choose_a_babysitter_who_is_the_demon(self):
        g = self.start()
        self.assertEqual((g.g[C].carries, g.g[E].carries), (LM, ''))
        self.assertTrue(g.g[C].is_demon)
        self.assertEqual(g.g.demon(), g.g[C])
        self.assertEqual(g.g[C].character, 'Poisoner')  # their own character, and ability, kept
        self.assertIn(LM, g.g.abilities(g.g[C]))
        self.assertTrue(self.told(C, 'you babysit Lil\' Monsta: you are the Demon'))
        self.assertTrue(self.told(E, f'{C} babysits Lil\' Monsta'))
        self.assertTrue(self.told(E, 'three good characters not in play'))
        self.assertFalse(self.told(A, 'Lil\' Monsta'))
        self.assertIsNone(g.g.check_victory())
        self.assertTrue(self.intro(C, 'No player is the Demon yet'))

    def test_minions_who_disagree_the_storyteller_picks_among_those_named(self):
        g = self.start(others={E: E}, forced={f'{LM} sitter:1': {'players': [E]}})
        self.assertEqual(g.g[E].carries, LM)
        self.assertEqual(self.g.st.seen[f'{LM} sitter:1'].values, [{'players': [C], 'character': None, 'number': None,
                                                                    'yes': None, 'characters': []},
                                                                   {'players': [E], 'character': None, 'number': None,
                                                                    'yes': None, 'characters': []}])

    def test_each_night_they_choose_again(self):
        g = self.start()
        self.queue(C, 'night', {'targets': [A]}, {'targets': [E]})  # (the Poisoner's own choice first)
        self.queue(E, 'night', {'targets': [E]})
        run(g.night(2))
        self.assertEqual((g.g[C].carries, g.g[E].carries), ('', LM))

    def test_registers_as_lil_monsta_and_as_themself_and_the_fortune_teller_sees_a_demon(self):
        g = self.start()
        self.assertEqual(g.g.registers_as(g.g[C]), {LM, 'Poisoner'})
        self.assertEqual(g.g.registers_demon_to_ft(g.g[C]), {True})
        self.assertEqual(g.g.registers_as(g.g[E]) - {'Spy'} and ch.kind(LM), 'Demon')
        self.assertNotIn(LM, g.g.registers_as(g.g[E]))
        self.assertIn('babysits Lil\' Monsta: is the Demon', g.g.grimoire_text())

    def test_the_slayers_shot_kills_the_babysitter_and_lil_monsta_dies(self):
        g = self.start(chars=[T1, 'Slayer', 'Poisoner', T3, 'Spy', T4, 'Empath'])
        g.slayer(B, C)
        self.assertFalse(g.g[C].alive)
        self.assertEqual((g.g.winner, g.g.reason), ('good', 'The Demon is dead.'))

    def test_the_babysitter_executed_good_wins(self):
        g = self.start()
        g.execute(C)
        self.assertEqual(g.g.winner, 'good')

    def test_another_minion_executed_the_game_goes_on(self):
        g = self.start()
        g.execute(E)
        self.assertIsNone(g.g.winner)

    def test_the_babysitter_killed_at_night_good_wins_at_dawn(self):
        g = self.start()
        g.kill(g.g[C], 'assassin')
        self.assertTrue(self.rec()['dead'])
        self.assertEqual(g.g.check_victory(), 'good')


class KillTests(LilMonstaTest):
    def test_each_night_but_the_first_a_player_might_die(self):
        g = self.start(forced={f'{LM}:2': {'players': [A]}})
        self.assertFalse([e for e in g.events if e['kind'] == 'death'])
        self.queue(C, 'night', {'targets': [B]}, {'targets': [C]})
        self.queue(E, 'night', {'targets': [C]})
        run(g.night(2))
        self.assertFalse(g.g[A].alive)
        self.assertEqual(g.g.death_log[-1]['cause'], 'demon')
        values = self.g.st.seen[f'{LM}:2'].values
        self.assertNotIn([C], [v['players'] for v in values])  # never the babysitter
        self.assertIn([], [v['players'] for v in values])  # or nobody

    def test_a_poisoned_babysitter_kills_nobody_and_the_monk_protects(self):
        g = self.start(chars=[T1, 'Monk', 'Poisoner', T3, 'Spy', T4, 'Empath'], forced={f'{LM}:2': {'players': [A]}})
        self.poison(C)
        self.queue(C, 'night', {'targets': [B]}, {'targets': [C]})
        self.queue(E, 'night', {'targets': [C]})
        run(g.night(2))
        self.assertTrue(g.g[A].alive)
        self.assertNotIn(f'{LM}:2', self.g.st.seen)
        g = self.start(chars=[T1, 'Monk', 'Poisoner', T3, 'Spy', T4, 'Empath'], forced={f'{LM}:2': {'players': [A]}})
        self.choose(2, B, [A])
        self.queue(C, 'night', {'targets': [D]}, {'targets': [C]})
        self.queue(E, 'night', {'targets': [C]})
        run(g.night(2))
        self.assertTrue(g.g[A].alive)


class JinxTests(LilMonstaTest):
    def test_the_magician_alive_the_storyteller_chooses_the_babysitter(self):
        g = self.start(chars=[T1, 'Magician', 'Poisoner', T3, 'Spy', T4, 'Empath'],
                       forced={f'{LM} sitter:1': {'players': [E]}})
        self.assertEqual(g.g[E].carries, LM)
        self.assertFalse([e for e in g.events if e['kind'] == 'night_choice' and e['data']['role'] == LM])

    def test_the_poppy_grower_alive_minions_wake_one_by_one_until_one_takes_it(self):
        g = self.dealt([T1, 'Poppy Grower', 'Poisoner', T3, 'Spy', T4, 'Empath'], extra=[LM])
        self.decide(C, False)
        self.decide(E, True)
        run(g.night(1))
        self.assertEqual(g.g[E].carries, LM)
        g = self.dealt([T1, 'Poppy Grower', 'Poisoner', T3, 'Spy', T4, 'Empath'], extra=[LM],
                       forced={f'{LM} sitter:1': {'players': [C]}})
        self.decide(C, False)
        self.decide(E, False)
        run(g.night(1))
        self.assertEqual(g.g[C].carries, LM)  # nobody took it: the Storyteller's

    def test_the_scarlet_woman_babysits_for_the_rest_of_the_game(self):
        g = self.start(chars=[T1, T2, 'Poisoner', T3, 'Scarlet Woman', T4, 'Empath'])
        g.execute(C)
        self.assertIsNone(g.g.winner)
        self.assertEqual(g.g[E].carries, LM)
        self.assertEqual(g.g[E].character, 'Scarlet Woman')  # her own character still
        self.assertTrue(self.told(E, 'you babysit Lil\' Monsta for the rest of the game'))
        run(g.night(2))
        self.assertEqual(g.g[E].carries, LM)
        self.assertFalse([e for e in g.events if e['kind'] == 'night_choice' and e['day'] == 2
                          and e['data']['role'] == LM])

    def test_not_with_fewer_than_five_alive_nor_without_the_jinx(self):
        g = self.start(chars=[T1, T2, 'Poisoner', T3, 'Scarlet Woman', T4, 'Empath'])
        for x in (A, B, D):
            g.g[x].alive = False
        g.execute(C)
        self.assertEqual(g.g.winner, 'good')
        g = self.start(chars=[T1, T2, 'Poisoner', T3, 'Scarlet Woman', T4, 'Empath'])
        g.g.script.jinxes = {}
        g.execute(C)
        self.assertEqual(g.g.winner, 'good')
        self.assertEqual(g.g[E].character, 'Scarlet Woman')  # not made a Poisoner

    def test_a_babysitting_psychopath_dies_when_executed_without_roshambo(self):
        g = self.start(chars=[T1, T2, 'Psychopath', T3, 'Spy', T4, 'Empath'])
        run(g.execution(C))
        self.assertFalse(g.g[C].alive)
        self.assertFalse(self.public('roshambo'))
        g = self.start(chars=[T1, T2, 'Psychopath', T3, 'Spy', T4, 'Empath'], sitter=E,
                       forced={'Psychopath roshambo': {'yes': True}})
        run(g.execution(C))  # not babysitting: the roshambo as usual
        self.assertTrue(g.g[C].alive)

    def test_a_babysitting_vizier_dies_when_executed(self):
        g = self.start(chars=[T1, T2, 'Vizier', T3, 'Spy', T4, 'Empath'])
        g.execute(C)
        self.assertFalse(g.g[C].alive)
        self.assertEqual(g.g.winner, 'good')
        g = self.start(chars=[T1, T2, 'Vizier', T3, 'Spy', T4, 'Empath'], sitter=E)
        g.execute(C)
        self.assertTrue(g.g[C].alive)

    def test_the_marionette_enters_after_the_first_babysitter_as_their_neighbour(self):
        g = self.dealt([T1, T2, 'Poisoner', T3, 'Marionette', T4, 'Empath'], extra=[LM])
        self.assertEqual(g.g[E].character, g.g[E].shown)  # waiting: the good character they believe they are
        self.assertTrue(g.g.notes.get('Marionette waiting'))
        self.queue(C, 'night', {'targets': [C]})
        run(g.night(1))
        m = [q.name for q in g.g.players if q.character == 'Marionette']
        self.assertEqual(len(m), 1)
        self.assertIn(m[0], (B, D))
        self.assertTrue(g.g[m[0]].evil)

    def test_a_demon_who_chooses_lil_monsta_at_the_tea_party_chooses_a_minion_too(self):
        g = self.game([T1, 'Hatter', 'Poisoner', T3, 'Imp', T4, 'Empath'], extra=[LM, 'Spy'])
        g.g.notes['Tea party'] = 2
        g.g[B].alive = False
        self.queue(E, 'night', {'character': LM}, {'character': 'Spy'})
        self.queue(C, 'night', {'character': None})
        g.day = g.g.day = 2
        run(R('Hatter').resolve_night(g, Night(2)))
        self.assertEqual((g.g[E].character, g.g[E].carries), ('Spy', LM))
        self.assertTrue(g.g[E].is_demon)
        self.assertFalse(self.rec()['dead'])


class ScriptTests(unittest.TestCase):
    def test_the_synthetic_script_holds_it_and_every_jinx_and_plays_at_every_size(self):
        s = ch.Script('carousel-8')
        self.assertIn(LM, s.demons)
        for other in ('Hatter', 'Magician', 'Poppy Grower', 'Psychopath', 'Scarlet Woman', 'Vizier', 'Marionette'):
            self.assertTrue(s.jinxed(LM, other), other)
        self.assertEqual(sorted(p for p in carousel_extra.JINXES if LM in p),
                         sorted((LM, o) for o in ('Hatter', 'Magician', 'Poppy Grower', 'Psychopath', 'Scarlet Woman',
                                                  'Vizier', 'Marionette')))
        self.assertEqual(smoke.smoke(s, games=1, out=io.StringIO()), [])

    def test_a_sample_of_its_recorded_seeds_replays_identically(self):
        s = ch.Script('carousel-8')
        recorded = json.loads(file_for(s).read_text())
        for g in recorded['games'][::100]:
            sha, _ = play(g['players'], g['seed'], g['minion'], script=s)
            self.assertEqual(sha, g['sha'], f"carousel-8, {g['players']} players, seed {g['seed']}: changed")

    def test_the_corpus_scripts_with_it_load(self):
        from test_carousel import corpus
        for path in corpus():
            if 'lilmonsta' in path.read_text().replace("'", '').replace('_', '').lower():
                try:
                    ch.Script(path)
                except ValueError as e:
                    self.assertNotIn(LM, str(e))


if __name__ == '__main__':
    unittest.main()
