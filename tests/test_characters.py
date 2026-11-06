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
            self.assertEqual(official.role(name)['edition'], 'tb', name)

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
        steps = set(characters.FIRST_NIGHT) | set(characters.OTHER_NIGHTS)
        for name, c in characters.CHARACTERS.items():
            if c.night_choice or c.info:
                self.assertIn(name, steps, name)

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


class NoNameTestsTests(unittest.TestCase):
    def test_the_game_loop_never_tests_a_character_name(self):
        src = (Path(characters.__file__).parent / 'game.py').read_text()
        names = '|'.join(re.escape(n) for n in characters.ALL)
        self.assertEqual(re.findall(rf"'({names})'", src), [])


if __name__ == '__main__':
    unittest.main()
