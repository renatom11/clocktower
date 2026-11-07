"""The fuzzer (clocktower/fuzz.py): it watches without changing play, its games replay, and its checks catch what they
are for. The full runs: `python -m clocktower fuzz run` (docs/interaction-findings.md)."""
import asyncio
import json
import random
import unittest
from unittest import mock

from clocktower import fingerprint, fuzz, official
from clocktower.agents import RandomSeat
from clocktower.characters import TB, Script, kind
from clocktower.game import ALL_NAMES
from clocktower.state import setup_error


class Watched(fuzz.FuzzGame):
    games = []

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        Watched.games.append(self)


class FuzzTests(unittest.TestCase):
    def test_watching_does_not_change_play(self):
        # the recorded fingerprints replay identically through FuzzGame: its checks draw nothing and change nothing
        for script in (TB, Script('snv')):
            recorded = json.loads(fingerprint.file_for(script).read_text())['games']
            with mock.patch.object(fingerprint, 'Game', Watched):
                for g in recorded[::97]:
                    sha, _ = fingerprint.play(g['players'], g['seed'], g['minion'], script=script)
                    self.assertEqual(sha, g['sha'], f"{script.id}, {g['players']} players, seed {g['seed']}")

    def test_a_handful_of_random_scripts_play_and_replay(self):
        specs = fuzz.make_specs(fuzz.SEED_BASE, 6, fuzz.SEED_BASE, ['scripted', 'rules'], range(5, 16))
        for spec in specs:
            self.assertEqual([len([c for c in spec['chars'] if kind(c) == k]) for k in fuzz.TYPES],
                             list(fuzz.SCRIPT_COUNTS))
            out = fuzz.play(spec)
            self.assertFalse([v for v in out['violations'] if v['type'] in ('crash', 'loop', 'timeout')],
                             out['repro'])
            self.assertTrue(out['in_play'] and set(out['acted']) <= set(out['in_play']))
            self.assertIn('fuzz repro --seed', out['repro'])
            again = fuzz.play(spec)  # seeded: the same game, the same findings
            self.assertEqual((again['winner'], again['days'], again['violations']),
                             (out['winner'], out['days'], out['violations']))

    def test_forced_setups_hold_their_characters(self):
        r = random.Random(3)
        chars = fuzz.random_script(r, force=['Vortox', 'Fang Gu', 'Baron', 'Chambermaid'])
        script = fuzz.make_script(chars)
        self.assertEqual(script.jinxes, {k: v for k, v in official.jinxes().items() if set(k) <= set(chars)})
        setup = fuzz.setup_with(script, ['Baron', 'Chambermaid', 'Fang Gu'], r)
        self.assertIsNotNone(setup)
        self.assertIsNone(setup_error(setup, script))
        self.assertTrue({'Baron', 'Chambermaid', 'Fang Gu'} <= set(setup))

    def game(self, characters, script=TB):
        names = ALL_NAMES[:len(characters)]
        seats = {n: RandomSeat(n, random.Random(i), names) for i, n in enumerate(names)}
        g = fuzz.FuzzGame(seats, None, names=names, seed=1, characters=characters, probes=False, script=script)
        asyncio.run(g.setup())
        return g

    def test_the_oracle_catches_false_information_for_a_healthy_player(self):
        g = self.game(['Empath', 'Chef', 'Imp', 'Soldier', 'Monk', 'Poisoner', 'Mayor'])
        m, empath = g.fz, g.g['Alex']
        self.assertIsNone(fuzz.empath(m, empath, {}, {'number': 0}))  # Blair (the Chef) and Gray (the Mayor): 0
        self.assertIn('neighbours', fuzz.empath(m, empath, {}, {'number': 2}))
        self.assertIsNone(fuzz.fortune_teller(m, empath, {'players': ['Casey', 'Drew']}, {'yes': True}))
        self.assertIn('NO, but', fuzz.fortune_teller(m, empath, {'players': ['Casey', 'Drew']}, {'yes': False}))
        wash = fuzz.ORACLES['Washerwoman']
        self.assertIsNone(wash(m, empath, {}, {'players': ['Blair', 'Casey'], 'character': 'Chef'}))
        self.assertIn('neither', wash(m, empath, {}, {'players': ['Casey', 'Gray'], 'character': 'Chef'}))

    def test_a_misregistering_character_may_register_otherwise(self):
        g = self.game(['Empath', 'Spy', 'Imp', 'Recluse', 'Monk', 'Mayor', 'Chef', 'Soldier'])
        m, empath = g.fz, g.g['Alex']
        # Alex's neighbours: Blair (the Spy) and Harper (the Soldier): 0 or 1
        self.assertIsNone(fuzz.empath(m, empath, {}, {'number': 0}))
        self.assertIsNone(fuzz.empath(m, empath, {}, {'number': 1}))
        self.assertIsNotNone(fuzz.empath(m, empath, {}, {'number': 2}))

    def test_a_once_per_game_ability_used_twice_is_caught(self):
        g = self.game(['Empath', 'Chef', 'Imp', 'Soldier', 'Monk', 'Mayor', 'Poisoner'])
        m = g.fz
        for _ in range(2):
            m.event('night_choice', {'player': 'Drew', 'role': 'Courtier', 'targets': [], 'character': 'Chef'})
        self.assertEqual([v['type'] for v in m.violations], ['once-rewoken'])
        m.epoch['Drew'] += 1  # a new character or a return to life: a fresh ability
        m.event('night_choice', {'player': 'Drew', 'role': 'Courtier', 'targets': [], 'character': 'Chef'})
        self.assertEqual(len(m.violations), 1)

    def test_a_mechanism_scenario_plays(self):
        spec = fuzz.scenario('Empath', 'poisoned', 11, 'scripted')
        self.assertIn('Poisoner', spec['setup'])
        self.assertIn('Empath', spec['setup'])
        d = fuzz.Directives('Empath', 'poisoned', random.Random(1))
        out = fuzz.play(spec, d)
        self.assertTrue(out['notes']['hit'])  # the Poisoner was aimed at the Empath
        self.assertFalse([v for v in out['violations'] if v['type'] == 'crash'])


if __name__ == '__main__':
    unittest.main()
