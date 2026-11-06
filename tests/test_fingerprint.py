"""Recorded seeds must replay identically: a sample of tests/data/fingerprints.json on every test run.
The full set: `python -m clocktower fingerprint --check` (about a minute)."""
import json
import unittest

from clocktower import fingerprint


class FingerprintTests(unittest.TestCase):
    def test_a_sample_of_recorded_seeds_replays_identically(self):
        recorded = json.loads(fingerprint.FILE.read_text())['games']
        sample = recorded[::37]  # every table size, several Minions, a few seconds
        self.assertGreater(len({g['players'] for g in sample}), 10)
        for g in sample:
            sha, _ = fingerprint.play(g['players'], g['seed'], g['minion'])
            self.assertEqual(sha, g['sha'], f"{g['players']} players, seed {g['seed']} no longer replays identically")


if __name__ == '__main__':
    unittest.main()
