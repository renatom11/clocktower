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

    def test_a_sample_of_bad_moon_risings_recorded_seeds_replays_identically(self):
        from clocktower.characters import Script
        bmr = Script('bmr')
        recorded = json.loads(fingerprint.file_for(bmr).read_text())['games']
        for g in recorded[::37]:
            sha, _ = fingerprint.play(g['players'], g['seed'], g['minion'], script=bmr)
            self.assertEqual(sha, g['sha'], f"BMR, {g['players']} players, seed {g['seed']}: no longer identical")

    def test_a_sample_of_sects_and_violets_recorded_seeds_replays_identically(self):
        from clocktower.characters import Script
        snv = Script('snv')
        recorded = json.loads(fingerprint.file_for(snv).read_text())['games']
        for g in recorded[::37]:
            sha, _ = fingerprint.play(g['players'], g['seed'], g['minion'], script=snv)
            self.assertEqual(sha, g['sha'], f"S&V, {g['players']} players, seed {g['seed']}: no longer identical")

    def test_a_sample_of_the_first_carousel_scripts_recorded_seeds_replays_identically(self):
        from clocktower.characters import Script
        c1 = Script('carousel-1')
        recorded = json.loads(fingerprint.file_for(c1).read_text())['games']
        for g in recorded[::37]:
            sha, _ = fingerprint.play(g['players'], g['seed'], g['minion'], script=c1)
            self.assertEqual(sha, g['sha'], f"carousel-1, {g['players']} players, seed {g['seed']}: changed")


if __name__ == '__main__':
    unittest.main()
