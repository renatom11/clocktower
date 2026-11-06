"""The character entries agree with the official data (clocktower/data/official), and the game loop and
Grimoire ask characters what to do instead of testing their names."""
import re
import unittest
from pathlib import Path

from clocktower import characters, official

# The protocol's ability wording (part of the frozen player prompt) differs from the official text here, and only here.
WORDING = {
    'Chef': 'adds "(evil players sitting next to each other)"',
    'Empath': '"neighbours" (official: "neighbors")',
    'Scarlet Woman': 'leaves out "(Travellers don\'t count.)", since this table has no Travellers',
}


class OfficialDataTests(unittest.TestCase):
    def test_every_character_is_official_with_its_official_type(self):
        for name, c in characters.CHARACTERS.items():
            self.assertEqual(official.kind(name), c.kind, name)
            self.assertIn(official.role(name)['edition'], ('tb', 'bmr'), name)

    def test_the_night_order_is_the_official_one(self):
        steps = official.nightsheet()
        for first, order in ((True, characters.FIRST_NIGHT), (False, characters.OTHER_NIGHTS)):
            ids = [official.ids()[n] for n in order]
            sheet = [i for i in steps['firstNight' if first else 'otherNight'] if i in ids]
            self.assertEqual(ids, sheet)
        self.assertEqual(characters.FIRST_NIGHT, ['Poisoner', 'Washerwoman', 'Librarian', 'Investigator', 'Chef',
                                                  'Empath', 'Fortune Teller', 'Butler', 'Spy'])
        self.assertEqual(characters.OTHER_NIGHTS, ['Poisoner', 'Monk', 'Scarlet Woman', 'Imp', 'Ravenkeeper', 'Empath',
                                                   'Fortune Teller', 'Undertaker', 'Butler', 'Spy'])

    def test_ability_wording_differs_from_the_official_text_only_where_listed(self):
        differ = {n for n, c in characters.CHARACTERS.items() if c.ability != official.role(n)['ability']}
        self.assertEqual(differ, set(WORDING))

    def test_every_character_with_a_night_choice_has_a_night_step(self):
        for name, c in characters.CHARACTERS.items():
            if c.night_choice or c.info:
                self.assertTrue(official.night_order([name], True) or official.night_order([name], False), name)

    def test_the_universal_night_order_covers_every_character_with_a_night_instruction(self):
        roles = official.roles()
        for key, reminder in (('firstNight', 'firstNightReminder'), ('otherNight', 'otherNightReminder')):
            listed = {i for i in official.nightsheet()[key] if i in roles}
            self.assertEqual(listed, {i for i, r in roles.items() if r.get(reminder)})

    def test_jinxes_are_symmetric(self):
        j = official.jinxes()
        self.assertGreater(len(j), 200)
        for (a, b), ruling in j.items():
            self.assertEqual(j[(b, a)], ruling)


class ScriptTests(unittest.TestCase):
    def test_trouble_brewing_is_the_default_script_and_its_order_is_v17s(self):
        tb = characters.TB
        self.assertEqual(tb.all, characters.ALL)
        self.assertEqual(tb.townsfolk[:3], ['Washerwoman', 'Librarian', 'Investigator'])
        self.assertEqual(tb.minions, ['Poisoner', 'Spy', 'Scarlet Woman', 'Baron'])
        self.assertEqual(characters.Script('tb'), tb)

    def test_a_script_file_in_the_official_format_loads_by_path(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'mine.json'
            path.write_text(json.dumps([{'id': '_meta', 'name': 'Mine'}, 'washerwoman', {'id': 'imp'}, 'poisoner']))
            s = characters.Script(path)
            self.assertEqual((s.id, s.name, s.townsfolk, s.minions, s.demons),
                             ('mine', 'Mine', ['Washerwoman'], ['Poisoner'], ['Imp']))
            self.assertEqual(s.other_nights, ['Poisoner', 'Imp'])
            path.write_text(json.dumps(['washerwoman', 'notacharacter']))
            with self.assertRaises(ValueError):
                characters.Script(path)

    def test_a_script_with_characters_not_implemented_says_which(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'carousel.json'
            path.write_text(json.dumps(['washerwoman', 'steward', 'imp']))  # an official character not built yet
            with self.assertRaises(ValueError) as e:
                characters.Script(path)
            self.assertIn('Steward', str(e.exception))

    def test_each_script_is_its_own_protocol(self):
        from clocktower.cli import PROTOCOL, protocol
        self.assertEqual(protocol(characters.TB), PROTOCOL)
        self.assertNotEqual(characters.Script('tb').id, 'bmr')

    def test_the_bmr_prompt_changes_only_sentences_that_still_exist_in_the_tb_prompt(self):
        from clocktower import prompts
        for old, _ in prompts.SCRIPT_TEXT['bmr']:
            self.assertIn(old, prompts._PLAYER_SYSTEM)


class NoNameTestsTests(unittest.TestCase):
    def test_the_game_loop_never_tests_a_character_name(self):
        src = (Path(characters.__file__).parent / 'game.py').read_text()
        names = '|'.join(re.escape(n) for n in characters.ALL)
        self.assertEqual(re.findall(rf"'({names})'", src), [])


class ImportTests(unittest.TestCase):
    def test_every_module_can_be_imported_first(self):
        import subprocess
        import sys
        root = Path(characters.__file__).parent.parent
        for module in ('state', 'characters', 'bmr', 'game', 'judge', 'official', 'cli', 'fingerprint'):
            r = subprocess.run([sys.executable, '-c', f'import clocktower.{module}; '
                                'from clocktower.characters import CHARACTERS; assert "Zombuul" in CHARACTERS'],
                               cwd=root, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f'importing clocktower.{module} first: {r.stderr[-400:]}')


if __name__ == '__main__':
    unittest.main()
