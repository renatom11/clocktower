"""The Atheist (clocktower/carousel_extra.py, batch 6, removable): the deal with no evil characters, the Storyteller's
bounded rule-breaking (a fake evil team its information follows, night deaths as a Demon's), nominating and executing
the Storyteller, the end of the game, and the edges its text implies (docs/carousel-rulings.md, batch 6, Atheist).
Deleting it deletes this file (clocktower/carousel_extra.py's docstring); switching it off skips it."""
import io
import json
import random
import unittest

from clocktower import smoke
from clocktower import characters as ch
from clocktower.fingerprint import file_for, play
from clocktower.game import NAMES
from clocktower.prompts import custom_text
from clocktower.schema import player_schema
from clocktower.state import random_setup, setup_error

from test_carousel import T1, T2, T3, T4, run
from test_carousel1 import Batch1Test

A, B, C, D, E, F, G, H, I = NAMES
AT = 'Atheist'
R = ch.rules


def setUpModule():
    if AT not in ch.CHARACTERS:  # switched off (CLOCKTOWER_WITHOUT=atheist: clocktower/carousel_extra.py)
        raise unittest.SkipTest('the Atheist is not built')


class AtheistTest(Batch1Test):
    CHARS = [AT, T1, T2, 'Empath', T3, T4, 'Chef']  # 7 players, all good

    def start(self, chars=None, forced=None, extra=('Imp', 'Poisoner')):
        return self.dealt(chars or self.CHARS, extra=list(extra), forced=forced)

    def queue(self, name, kind, *answers):
        self.seats[name].day.setdefault(kind, []).extend(answers)


class DealTests(unittest.TestCase):
    def test_with_the_atheist_dealt_no_evil_character_at_every_size(self):
        s = ch.Script('carousel-9')
        seen = 0
        for n in range(5, 16):
            for seed in range(40):
                chars = random_setup(random.Random(seed), players=n, script=s)
                self.assertIsNone(setup_error(chars, s))
                if AT in chars:
                    seen += 1
                    self.assertFalse([c for c in chars if ch.kind(c) in ('Minion', 'Demon')], chars)
                    self.assertEqual(len(chars), n)
        self.assertTrue(seen)

    def test_the_deal_is_checked(self):
        s = ch.Script('carousel-9')
        self.assertIn('no evil characters', setup_error([AT, 'Chef', 'Empath', 'Poisoner', 'Imp'], s))
        self.assertIsNone(setup_error([AT, 'Chef', 'Empath', 'Monk', 'Soldier'], s))

    def test_the_storyteller_may_be_nominated_on_its_scripts_only(self):
        s = ch.Script('carousel-9')
        self.assertEqual(s.nominees, {'Storyteller': AT})
        enum = player_schema(NAMES[:5], s)['properties']['nominate']['anyOf'][0]['enum']
        self.assertIn('Storyteller', enum)
        c8 = ch.Script('carousel-7')
        self.assertEqual(c8.nominees, {})
        self.assertNotIn('Storyteller', player_schema(NAMES[:5], c8)['properties']['nominate']['anyOf'][0]['enum'])
        self.assertIn('nominate the Storyteller', ' '.join(new for _, new in custom_text(s)))


class RuleBreakingTests(AtheistTest):
    def test_a_fake_evil_team_the_information_follows(self):
        g = self.start(forced={'Atheist fake team': {'players': [B, E], 'character': 'Imp'}})
        rec = g.g.notes[AT]
        self.assertEqual((rec['team'], rec['demon'], rec['as']), ([B, E], B, 'Imp'))
        self.assertTrue(g.g.notes['Storyteller lies'])
        self.assertFalse([q for q in g.g.players if q.evil])
        self.assertTrue(g.g.unreliable(g.g[D]))
        self.assertEqual(g.g.decoys[D], (B, {B, E}))
        self.assertEqual(g.g.decoys[B], (E, {E}))  # (a fake team member's world leaves them out)

    def test_information_may_be_false_and_usually_follows_the_fake_team(self):
        g = self.start(forced={'Atheist fake team': {'players': [C, E], 'character': 'Imp'}})
        run(g.night(1))
        self.assertTrue(self.told(D, 'Empath'))  # D (Empath) sits between C and E, the fake team
        self.assertEqual(len(g.st.seen['Empath:' + D].values), 3)  # 0, 1 or 2: any value is legal

    def test_each_night_but_the_first_a_player_may_die(self):
        g = self.start(forced={f'{AT}:2': {'players': [B]}})
        run(g.night(1))
        self.assertFalse([e for e in g.events if e['kind'] == 'death'])
        run(g.night(2))
        self.assertFalse(g.g[B].alive)
        values = [v['players'] for v in g.st.seen[f'{AT}:2'].values]
        self.assertIn([], values)

    def test_no_demon_is_no_win_and_two_alive_is_evils(self):
        g = self.start()
        self.assertIsNone(g.g.check_victory())
        for x in (B, C, D, E, F):
            g.g[x].alive = False
        self.assertEqual(g.g.check_victory(), 'evil')
        self.assertIn('never executed the Storyteller', g.g.reason)

    def test_without_the_atheist_in_play_nothing_changes(self):
        g = self.start(chars=['Drunk', T1, T2, 'Empath', 'Poisoner', T4, 'Imp', T3],
                       forced={'drunk_as': {'character': AT}}, extra=(AT,))
        self.assertNotIn(AT, g.g.notes)
        self.assertFalse(g.g.notes.get('Storyteller lies'))


class StorytellerExecutionTests(AtheistTest):
    def vote_in(self, g):
        for x in g.names:
            self.queue(x, 'vote', {'vote': True})

    def test_the_storyteller_executed_with_the_atheist_in_play_good_wins_even_if_dead(self):
        g = self.start()
        g.g[A].alive = False
        g.day = g.g.day = 1
        self.queue(B, 'nominate', {'nominate': 'Storyteller'})
        self.vote_in(g)
        run(g.nominations())
        self.assertEqual((g.g.winner, g.g.reason),
                         ('good', 'The Storyteller was executed, and the Atheist is in play.'))
        self.assertTrue([e for e in g.events if e['kind'] == 'execution' and e['data']['player'] == 'Storyteller'])

    def test_without_the_atheist_in_play_evil_wins(self):
        g = self.dealt([T1, T2, 'Empath', 'Poisoner', T3, 'Imp', 'Chef'], extra=[AT])
        g.day = g.g.day = 1
        self.queue(A, 'nominate', {'nominate': 'Storyteller'})
        self.vote_in(g)
        run(g.nominations())
        self.assertEqual(g.g.winner, 'evil')

    def test_too_few_votes_nothing_happens(self):
        g = self.start()
        g.day = g.g.day = 1
        self.queue(B, 'nominate', {'nominate': 'Storyteller'})
        run(g.nominations())
        self.assertIsNone(g.g.winner)
        self.assertTrue([e for e in g.events if e['kind'] == 'no_execution'])


class ScriptTests(unittest.TestCase):
    def test_the_synthetic_script_plays_at_every_size(self):
        s = ch.Script('carousel-9')
        self.assertIn(AT, s.townsfolk)
        self.assertEqual(smoke.smoke(s, games=1, out=io.StringIO()), [])

    def test_a_sample_of_its_recorded_seeds_replays_identically(self):
        s = ch.Script('carousel-9')
        recorded = json.loads(file_for(s).read_text())
        for g in recorded['games'][::100]:
            sha, _ = play(g['players'], g['seed'], g['minion'], script=s)
            self.assertEqual(sha, g['sha'], f"carousel-9, {g['players']} players, seed {g['seed']}: changed")


if __name__ == '__main__':
    unittest.main()
