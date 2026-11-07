"""Batch 6 of the experimental characters, removable by design (clocktower/carousel_extra.py): the generic hooks the
characters share do nothing on any script without them. Each character's own tests are in tests/test_carousel_<id>.py,
in its commit (docs/carousel-rulings.md, batch 6)."""
import random
import unittest

from clocktower import carousel_extra
from clocktower import characters as ch
from clocktower.prompts import custom_text
from clocktower.state import random_setup

SCRIPTS = ['tb', 'bmr', 'snv'] + [f'carousel-{n}' for n in range(1, 8)]


class SharedHooksTests(unittest.TestCase):
    def test_no_character_on_the_earlier_scripts_deals_or_adds_a_rule_sentence(self):
        for sid in SCRIPTS:
            s = ch.Script(sid)
            self.assertEqual(s.dealers, [], sid)
            self.assertEqual([line for c in s.all for line in ch.rules(c).rule_text(s)], [], sid)

    def test_a_character_that_does_not_deal_leaves_the_draw_as_it_was(self):
        c = ch.Character()
        self.assertIsNone(c.deal_error(['Imp'], ch.TB))
        chars = random_setup(random.Random(3), players=9)
        self.assertEqual(c.redeal(random.Random(3), chars, 9, ch.TB), chars)

    def test_the_custom_prompt_is_built_as_before(self):
        self.assertTrue(custom_text(ch.Script('carousel-7')))

    def test_a_section_asks_whether_another_is_built(self):
        self.assertTrue(carousel_extra.built('Imp'))
        self.assertFalse(carousel_extra.built('No Such Character'))


if __name__ == '__main__':
    unittest.main()
