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


    def test_a_sample_of_the_second_carousel_scripts_recorded_seeds_replays_identically(self):
        from clocktower.characters import Script
        c2 = Script('carousel-2')
        recorded = json.loads(fingerprint.file_for(c2).read_text())['games']
        for g in recorded[::37]:
            sha, _ = fingerprint.play(g['players'], g['seed'], g['minion'], script=c2)
            self.assertEqual(sha, g['sha'], f"carousel-2, {g['players']} players, seed {g['seed']}: changed")

    def test_a_sample_of_the_third_carousel_scripts_recorded_seeds_replays_identically(self):
        from clocktower.characters import Script
        c3 = Script('carousel-3')
        recorded = json.loads(fingerprint.file_for(c3).read_text())['games']
        for g in recorded[::37]:
            sha, _ = fingerprint.play(g['players'], g['seed'], g['minion'], script=c3)
            self.assertEqual(sha, g['sha'], f"carousel-3, {g['players']} players, seed {g['seed']}: changed")

    def test_a_sample_of_the_fourth_carousel_scripts_recorded_seeds_replays_identically(self):
        from clocktower.characters import Script
        c4 = Script('carousel-4')
        recorded = json.loads(fingerprint.file_for(c4).read_text())['games']
        for g in recorded[::37]:
            sha, _ = fingerprint.play(g['players'], g['seed'], g['minion'], script=c4)
            self.assertEqual(sha, g['sha'], f"carousel-4, {g['players']} players, seed {g['seed']}: changed")

    def test_a_sample_of_the_fifth_carousel_scripts_recorded_seeds_replays_identically(self):
        from clocktower.characters import Script
        c5 = Script('carousel-5')
        recorded = json.loads(fingerprint.file_for(c5).read_text())['games']
        for g in recorded[::37]:
            sha, _ = fingerprint.play(g['players'], g['seed'], g['minion'], script=c5)
            self.assertEqual(sha, g['sha'], f"carousel-5, {g['players']} players, seed {g['seed']}: changed")

    def test_a_sample_of_the_sixth_carousel_scripts_recorded_seeds_replays_identically(self):
        from clocktower.characters import Script
        c6 = Script('carousel-6')
        recorded = json.loads(fingerprint.file_for(c6).read_text())['games']
        for g in recorded[::37]:
            sha, _ = fingerprint.play(g['players'], g['seed'], g['minion'], script=c6)
            self.assertEqual(sha, g['sha'], f"carousel-6, {g['players']} players, seed {g['seed']}: changed")

    def test_a_sample_of_the_seventh_carousel_scripts_recorded_seeds_replays_identically(self):
        from clocktower.characters import Script
        c7 = Script('carousel-7')
        recorded = json.loads(fingerprint.file_for(c7).read_text())['games']
        for g in recorded[::37]:
            sha, _ = fingerprint.play(g['players'], g['seed'], g['minion'], script=c7)
            self.assertEqual(sha, g['sha'], f"carousel-7, {g['players']} players, seed {g['seed']}: changed")


if __name__ == '__main__':
    unittest.main()
