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

    def test_the_experimental_characters_oracles(self):
        script = fuzz.make_script(['Steward', 'Shugenja', 'Balloonist', 'Nightwatchman', 'Pixie', 'Fisherman', 'Chef',
                                   'Monk', 'Mayor', 'Soldier', 'Empath', 'Recluse', 'Poisoner', 'Imp'])
        g = self.game(['Steward', 'Shugenja', 'Imp', 'Monk', 'Recluse', 'Poisoner', 'Soldier', 'Balloonist'], script)
        m, st, sh, bal = g.fz, g.g['Alex'], g.g['Blair'], g.g['Harper']
        self.assertIsNone(fuzz.steward(m, st, {}, {'players': ['Drew']}))
        self.assertIn('evil', fuzz.steward(m, st, {}, {'players': ['Casey']}))
        # Blair's closest evil: Casey (the Imp), one seat clockwise
        self.assertIsNone(fuzz.shugenja(m, sh, {}, {'yes': True}))
        self.assertIsNotNone(fuzz.shugenja(m, sh, {}, {'yes': False}))
        self.assertIsNone(fuzz.nightwatchman(m, st, {'about': 'Drew'}, {'players': ['Alex']}))
        self.assertIsNotNone(fuzz.nightwatchman(m, st, {'about': 'Drew'}, {'players': ['Ellis']}))
        self.assertIsNone(fuzz.pixie(m, st, {}, {'character': 'Monk'}))
        self.assertIsNotNone(fuzz.pixie(m, st, {}, {'character': 'Chef'}))
        self.assertIsNone(fuzz.fisherman(m, st, {}, {'statements': ['Drew is the Monk.']}))
        self.assertIsNotNone(fuzz.fisherman(m, st, {}, {'statements': ['Drew is the Chef.']}))
        m.balloon[bal.name] = {'Townsfolk'}
        self.assertIsNone(fuzz.balloonist(m, bal, {}, {'players': ['Casey']}))
        self.assertIsNotNone(fuzz.balloonist(m, bal, {}, {'players': ['Drew']}))
        self.assertIsNone(fuzz.widow_knower(m, {}, {'players': ['Drew']}))
        self.assertIsNotNone(fuzz.widow_knower(m, {}, {'players': ['Frankie']}))

    def test_the_batch_3_oracles_and_the_faux_paw(self):
        script = fuzz.make_script(['Noble', 'Village Idiot', 'Lycanthrope', 'Boffin', 'Alchemist', 'Chef', 'Monk',
                                   'Mayor', 'Soldier', 'Empath', 'Drunk', 'Poisoner', 'Imp'])
        g = self.game(['Noble', 'Village Idiot', 'Imp', 'Monk', 'Lycanthrope', 'Poisoner', 'Soldier'], script)
        m, noble, vi = g.fz, g.g['Alex'], g.g['Blair']
        self.assertIsNone(fuzz.noble(m, noble, {}, {'players': ['Casey', 'Drew', 'Ellis']}))
        self.assertIsNotNone(fuzz.noble(m, noble, {}, {'players': ['Casey', 'Frankie', 'Ellis']}))
        self.assertIsNotNone(fuzz.noble(m, noble, {}, {'players': ['Drew', 'Ellis', 'Gray']}))
        self.assertIsNone(fuzz.village_idiot(m, vi, {'about': 'Casey'}, {'yes': True}))
        self.assertIsNotNone(fuzz.village_idiot(m, vi, {'about': 'Drew'}, {'yes': True}))
        fuzz.FAUX.add('Drew')  # the Lycanthrope's Faux Paw registers as evil
        self.assertIsNone(fuzz.village_idiot(m, vi, {'about': 'Drew'}, {'yes': True}))
        fuzz.FAUX.clear()
        self.assertIsNotNone(fuzz.boffin_ability(m, {}, {'character': 'Drunk'}))
        self.assertIsNotNone(fuzz.boffin_ability(m, {}, {'character': 'Monk'}))
        self.assertIsNone(fuzz.boffin_ability(m, {}, {'character': 'Chef'}))
        self.assertIsNotNone(fuzz.alchemist_minion(m, {}, {'character': 'Poisoner'}))
        self.assertIsNone(fuzz.faux_paw(m, {}, {'players': ['Drew']}))
        self.assertIsNotNone(fuzz.faux_paw(m, {}, {'players': ['Casey']}))

    def test_the_batch_3b_checks(self):
        script = fuzz.make_script(['Knight', 'King', 'Choirboy', 'Alsaahir', 'Cult Leader', 'Huntsman', 'Chef', 'Monk',
                                   'Mayor', 'Soldier', 'Damsel', 'Poisoner', 'Spy', 'Imp', 'Lord of Typhon', 'Lleech'])
        g = self.game(['Knight', 'King', 'Imp', 'Monk', 'Choirboy', 'Poisoner', 'Soldier'], script)
        m, kn = g.fz, g.g['Alex']
        self.assertIsNone(fuzz.knight(m, kn, {}, {'players': ['Blair', 'Drew']}))
        self.assertIsNotNone(fuzz.knight(m, kn, {}, {'players': ['Blair', 'Casey']}))
        self.assertIsNotNone(fuzz.knight(m, kn, {}, {'players': ['Alex', 'Drew']}))
        self.assertIsNone(fuzz.king(m, g.g['Blair'], {}, {'character': 'Monk'}))
        self.assertIsNotNone(fuzz.king(m, g.g['Blair'], {}, {'character': 'Chef'}))
        self.assertIsNone(fuzz.choirboy(m, g.g['Ellis'], {}, {'players': ['Casey']}))
        self.assertIsNotNone(fuzz.choirboy(m, g.g['Ellis'], {}, {'players': ['Drew']}))
        self.assertIsNotNone(fuzz.huntsman_townsfolk(m, {}, {'character': 'Monk'}))
        self.assertIsNone(fuzz.huntsman_townsfolk(m, {}, {'character': 'Chef'}))
        # a right guess by a working Alsaahir must win at once
        g = self.game(['Alsaahir', 'King', 'Imp', 'Monk', 'Chef', 'Poisoner', 'Soldier'], script)
        g.emit('ability', {'player': 'Alex', 'character': 'Alsaahir',
                           'guesses': [{'player': 'Casey', 'character': 'Imp'},
                                       {'player': 'Frankie', 'character': 'Spy'}]})
        g.fz.step('test')
        self.assertEqual([v['type'] for v in g.fz.violations], ['missed-win'])
        # the Lord of Typhon in the middle of a line of evil characters
        g = self.game(['Knight', 'Spy', 'Lord of Typhon', 'Poisoner', 'Chef', 'Monk', 'Soldier'], script)
        self.assertEqual(g.fz.violations, [])
        g.fz.check_setup([{'name': n, 'character': c} for n, c in zip(
            'ABCDEFG', ['Spy', 'Knight', 'Lord of Typhon', 'Poisoner', 'Chef', 'Monk', 'Soldier'])])
        self.assertEqual([v['type'] for v in g.fz.violations], ['setup'])

    def test_the_batch_4_checks(self):
        script = fuzz.make_script(['Bounty Hunter', 'Chef', 'Monk', 'Mayor', 'Soldier', 'Empath', 'Librarian', 'Hermit',
                                   'Recluse', 'Vizier', 'Psychopath', 'Poisoner', 'Imp'])
        g = self.game(['Bounty Hunter', 'Chef', 'Imp', 'Monk', 'Vizier', 'Hermit', 'Soldier', 'Mayor'], script)
        m, bh = g.fz, g.g['Alex']
        for q in g.g.players:  # (the evil Townsfolk, if any, is made good again for the test)
            if fuzz.kind(q.character) == 'Townsfolk':
                q.alignment = 'good'
        self.assertIsNone(fuzz.bounty_hunter(m, bh, {}, {'players': ['Casey']}))
        self.assertIsNotNone(fuzz.bounty_hunter(m, bh, {}, {'players': ['Blair']}))
        self.assertIsNotNone(fuzz.bounty_hunter(m, bh, {}, {'players': ['Alex']}))
        self.assertTrue(fuzz.misreg(g.g['Frankie']))  # the Hermit holds the Recluse's ability
        self.assertIsNotNone(fuzz.evil_townsfolk(m, {}, {'players': ['Alex']}))
        self.assertIsNone(fuzz.evil_townsfolk(m, {}, {'players': ['Blair']}))
        g.fz.batch4_death(g.g['Ellis'], 'execution', None)  # a working Vizier dying by day
        self.assertEqual([v['type'] for v in g.fz.violations], ['vizier'])

    def test_the_batch_5_checks(self):
        script = fuzz.make_script(['Amnesiac', 'Chef', 'Monk', 'Mayor', 'Soldier', 'Empath', 'Librarian', 'Recluse',
                                   'Mezepheles', 'Poisoner', 'Yaggababble'])
        g = self.game(['Amnesiac', 'Chef', 'Yaggababble', 'Monk', 'Mezepheles', 'Soldier', 'Mayor'], script)
        m = g.fz
        word = g.g.notes['Mezepheles']['Ellis']['secret']
        phrase = g.g.notes['Yaggababble']['Casey']['secret']
        g.day, g.phase = 1, 'day'
        g.emit('say', {'speaker': 'Blair', 'text': 'nothing to see'})
        g.g.notes['Mezepheles']['Ellis']['first'] = {'player': 'Blair', 'seq': len(g.events) - 1}
        g.emit('say', {'speaker': 'Casey', 'text': phrase})
        g.day, g.phase = 2, 'night'
        for k in (1, 2):
            g.emit('st_choice', {'id': f'Yaggababble:Casey:{k}', 'value': {'players': ['Alex']}, 'valid': True},
                   'audit')
        m.speech(2)
        self.assertEqual(sorted(v['type'] for v in m.violations), ['mezepheles', 'yaggababble'])
        self.assertTrue(word)
        # the Amnesiac's information is checked by its model character's oracle
        g.g.notes['Amnesiac']['Alex']['gift'] = 'Each night, you learn how many of your 2 alive neighbours are evil.'
        from clocktower import carousel6
        choice = carousel6.info_for(g, g.g['Alex'], carousel6.Amnesiac.gift(g.g, g.g['Alex']), g.tonight or
                                    type('N', (), {'n': 2, 'first': False})())[0]
        m.decided(choice, {'number': 2})
        self.assertTrue([v for v in m.violations if v['type'] == 'oracle'])

    def test_extra_abilities_need_a_gains_event(self):
        g = self.game(['Empath', 'Chef', 'Imp', 'Soldier', 'Monk', 'Mayor', 'Poisoner'])
        g.g['Alex'].extra.append('Monk')
        g.fz.step('test')
        self.assertEqual([v['type'] for v in g.fz.violations], ['coherence'])
        g = self.game(['Empath', 'Chef', 'Imp', 'Soldier', 'Monk', 'Mayor', 'Poisoner'])
        g.g['Alex'].extra.append('Monk')
        g.emit('gains', {'player': 'Alex', 'character': 'Monk'}, 'audit')
        g.fz.step('test')
        self.assertEqual(g.fz.violations, [])

    def test_setups_with_the_kazali_or_the_summoner(self):
        r = random.Random(5)
        for pair in (['Kazali', 'Chef'], ['Summoner', 'Chef']):
            chars = fuzz.random_script(r, force=pair)
            setup = fuzz.setup_with(fuzz.make_script(chars), pair, r)
            self.assertTrue(setup and set(pair) <= set(setup), pair)
        specs = fuzz.make_specs(fuzz.SEED_BASE, 3, 1, ['scripted'], range(5, 16), force=['Kazali', 'Poisoner'])
        for spec in specs:  # no setup holds both: the Kazali is dealt, the Poisoner is one it may make
            self.assertIn('Kazali', spec['setup'])
            self.assertIn('Poisoner', spec['chars'])

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
