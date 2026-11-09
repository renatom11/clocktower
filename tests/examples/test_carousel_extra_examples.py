"""The official worked examples for the five removable experimental characters of batch 6 (Lil' Monsta, the Atheist,
the Wizard, Legion and Riot), and for other characters' examples that need one of them, as scenario tests (see
test_carousel_examples.py for the conventions; the findings are EC-n in docs/examples-findings.md).

One test class per removable character, holding every example that needs it: reverting that character's commit
(each can be reverted on its own) needs only its class here deleted, and nothing else in this file names it. Each class
builds its games on the shared ExampleTest of test_carousel_examples.py, which names none of the five."""
import unittest

from clocktower import characters as ch
from clocktower.game import NAMES

from test_carousel import O1, T1, T2, T3, T4, run

from examples.test_carousel_examples import ExampleTest

A, B, C, D, E, F, G, H, I = NAMES


# ---- Lil' Monsta -------------------------------------------------------------------------------------------------

class LilMonstaExamples(ExampleTest):
    LM = "Lil' Monsta"

    def test_lil_monsta_example_1(self):
        """The Poisoner and the Widow wake and point, and settle on the Widow, who takes Lil' Monsta's token; the next
        night they both choose the Poisoner to babysit instead (wiki: Lil' Monsta, example 1)."""
        g = self.dealt([T1, T2, 'Poisoner', T3, 'Widow', T4, 'Empath'], extra=[self.LM])
        for m in (C, E):
            self.seats[m].day.setdefault('night', []).append({'targets': [E]})
        run(g.night(1))
        self.assertEqual((g.g[C].carries, g.g[E].carries), ('', self.LM))
        self.assertTrue(g.g[E].is_demon)
        self.day(g, 1)
        self.seats[C].day['night'] = [{'targets': [A]}, {'targets': [C]}]  # (the Poisoner's own choice first)
        self.seats[E].day['night'] = [{'targets': [C]}]
        run(g.night(2))
        self.assertEqual((g.g[C].carries, g.g[E].carries), (self.LM, ''))


# ---- Atheist -----------------------------------------------------------------------------------------------------

class AtheistExamples(ExampleTest):
    AT = 'Atheist'

    def storyteller_executed(self, g, nominator):
        g.day = g.g.day = 1
        self.seats[nominator].day.setdefault('nominate', []).append({'nominate': 'Storyteller'})
        for x in g.names:
            self.seats[x].day.setdefault('vote', []).append({'vote': True})
        run(g.nominations())

    @unittest.skip('disagrees with the example: finding EC-16')
    def test_atheist_example_1(self):
        """With the Atheist in play the Storyteller breaks rules: the Investigator is shown a Boomdandy pair of two
        good players, the Sweetheart dies on nominating though there is no Witch, and the Slayer's shot kills the
        Gossip (wiki: Atheist, example 1)."""
        g = self.dealt([self.AT, 'Investigator', 'Grandmother', 'Seamstress', 'Gossip', 'Slayer', 'Sweetheart'],
                       extra=['Boomdandy', 'Imp', 'Witch'],
                       forced={'Atheist fake team': {'players': [C, D], 'character': 'Imp'}})
        self.assertTrue(g.g.unreliable(g.g[B]))  # the Investigator's lie is allowed
        self.day(g, 1)
        g.slayer(F, E)
        self.assertFalse(g.g[E].alive)

    def test_atheist_example_2(self):
        """Three Outsiders are in play where there should be two; the players execute the Storyteller, and good wins
        (wiki: Atheist, example 2). Checked: such a deal is accepted with the Atheist, and executing the Storyteller
        wins for good."""
        from clocktower.state import setup_error
        g = self.dealt([self.AT, T1, T2, 'Empath', T3, T4, 'Chef'], extra=['Imp', 'Poisoner', 'Saint', 'Recluse'])
        self.storyteller_executed(g, B)
        self.assertEqual(g.g.winner, 'good')
        more = [self.AT, T1, T2, 'Empath', T3, 'Saint', 'Recluse']  # seven players: two Outsiders, not none
        self.assertIsNone(setup_error(more, g.script))

    @unittest.skip('disagrees with the example: finding EC-23')
    def test_politician_example_3(self):
        """With no Atheist in play, the Politician (thinking evil is winning) claims the Atheist and the town executes
        the Storyteller: evil wins, and the Politician with them (wiki: Politician, example 3). Checked with the
        Politician as the nominator, the engine's "most responsible"."""
        g = self.dealt(['Politician', T1, T2, 'Poisoner', T3, 'Imp', 'Chef', T4], extra=[self.AT])
        self.say(A, 'I am the Atheist: execute the Storyteller.')
        self.storyteller_executed(g, A)
        g.g.finish()
        self.assertEqual((g.g.winner, g.g[A].alignment), ('evil', 'evil'))


# ---- Wizard ------------------------------------------------------------------------------------------------------

class WizardExamples(ExampleTest):
    WZ = 'Wizard'
    CHARS = [T1, T2, 'Wizard', T3, 'Imp', T4, 'Empath']  # C is the Wizard, E the Imp
    FREE = {'Wizard grant': {'yes': True}, 'Wizard price': {'statements': ['none']},
            'Wizard clue': {'statements': ['none']}}

    def wish(self, say, targets=(), forced=None, chars=None, night=2):
        g = self.game(chars or self.CHARS, forced=forced)
        self.day(g, night)
        self.choose(night, E, [D])
        self.seats[C].day.setdefault('night', []).append({'say': say, 'targets': list(targets)})
        run(g.night(night))
        return g

    def test_wizard_example_1(self):
        """The Wizard wishes to see the Grimoire; the wish is granted, with no price and no clue (wiki: Wizard,
        example 1)."""
        g = self.wish('I wish to see the Grimoire', forced=self.FREE)
        self.assertTrue(self.told(C, 'you see the Grimoire'))
        self.assertFalse(self.public('a wish was granted'))
        self.assertTrue(g.g[C].alive and not g.g.is_poisoned(g.g[C]))

    @unittest.skip('disagrees with the example: finding EC-17')
    def test_wizard_example_2(self):
        """The Wizard wishes every good player drunk; it is granted, the town is told only that things are wrong, and
        all information is false from then on (wiki: Wizard, example 2)."""
        g = self.wish('I wish that all good players are drunk', forced=self.FREE)
        self.assertTrue(all(g.g.is_drunk(p) for p in g.g.players if not p.evil))

    @unittest.skip('disagrees with the example: finding EC-17')
    def test_wizard_example_3(self):
        """The Wizard wishes to become a Demon; it is granted, the town is told a cryptic clue, the Storyteller kills
        the Lord of Typhon and the Wizard becomes the Ojo (wiki: Wizard, example 3)."""
        g = self.wish('I wish to become a Demon', forced=self.FREE,
                      chars=[T1, T2, 'Wizard', T3, 'Lord of Typhon', T4, 'Empath'])
        self.assertEqual(ch.kind(g.g[C].character), 'Demon')

    @unittest.skip('disagrees with the example: finding EC-17')
    def test_wizard_example_4(self):
        """The Wizard wishes to win; it is granted (evil wins at the end of the day), the town learns the Demon is one
        of three players, executes the Demon, and good wins (wiki: Wizard, example 4)."""
        g = self.wish('I wish to win the game', forced=self.FREE)
        values = [v['statements'][0] for v in g.st.seen[f'Wizard wish:{C}'].values]
        self.assertIn('win', values)

    @unittest.skip('disagrees with the example: finding EC-22')
    def test_wizard_example_5(self):
        """The Wizard wishes everyone five lives and every reminder token in play; the Storyteller finds it too
        awkward, declines, and asks for another wish (wiki: Wizard, example 5). The engine's wish is matched to its
        list, here to none: no wish is made, and the Wizard may wish again (on a later night)."""
        g = self.wish('I wish everyone had 5 lives, with the reminders of the script all out', forced=self.FREE)
        self.assertTrue(self.told(C, 'not a wish the Storyteller can grant'))
        self.assertFalse(g.g.notes.get('Used', {}).get(C))
        self.seats[C].day.setdefault('night', []).append({'say': '5', 'targets': []})
        self.day(g, 3)
        run(g.night(3))
        self.assertTrue(self.told(C, 'you see the Grimoire'))

    @unittest.skip('disagrees with the example: finding EC-18')
    def test_alchemist_example_2(self):
        """The Alchemist with the Poisoner's ability poisons the Wizard, then the Alsaahir; on the third night they
        choose the Lord of Typhon, are asked to choose again, and poison the King instead (wiki: Alchemist, example
        2)."""
        g = self.game(['Alchemist', 'Alsaahir', 'Wizard', 'Lord of Typhon', 'Poisoner', 'King', T1])
        g.g.notes['Alchemist'] = {A: 'Poisoner'}
        g.g[A].extra = ['Poisoner']
        self.night(1, {A: [C]})
        self.assertTrue(g.g.is_poisoned(g.g[C]))
        self.day(g, 1)
        self.night(2, {A: [B], D: [G]})
        self.assertTrue(g.g.is_poisoned(g.g[B]))
        self.day(g, 2)
        self.seats[A].day['night'] = [{'targets': [D]}, {'targets': [F]}]
        self.night(3, {D: [G]})
        self.assertEqual((g.g.is_poisoned(g.g[D]), g.g.is_poisoned(g.g[F])), (False, True))

    @unittest.skip('disagrees with the example: finding EC-12')
    def test_hermit_example_1(self):
        """The Hermit has the Klutz's, Butler's and Recluse's abilities: she chooses a master each night; the dying
        Ravenkeeper learns she is the Lord of Typhon; executed, she chooses the Wizard by the Klutz's ability, and good
        loses (wiki: Hermit, example 1)."""
        g = self.dealt(['Hermit', 'Ravenkeeper', T2, 'Wizard', 'Lord of Typhon', 'Poisoner', T3],
                       extra=['Klutz', 'Butler', 'Recluse'])
        self.assertIn('Butler', g.g.abilities(g.g[A]))

    def test_cult_leader_example_3(self):
        """Seated between the Poisoner (evil) and the Fortune Teller (good), the Cult Leader is poisoned, and the
        Kazali's kill of the Fortune Teller leaves two evil living neighbours, the Poisoner and the Wizard; poisoned,
        the Cult Leader cannot change alignment (wiki: Cult Leader, example 3)."""
        g = self.game(['Cult Leader', 'Poisoner', T1, 'Kazali', T2, 'Wizard', 'Fortune Teller'])
        self.night(2, {B: [A], D: [G], G: [C, E]})
        self.assertFalse(g.g[G].alive)
        self.assertEqual(g.g[A].alignment, 'good')
        self.day(g, 2)
        self.night(3, {B: [A], D: [C]})
        self.assertEqual(g.g[A].alignment, 'good')


# ---- Legion ------------------------------------------------------------------------------------------------------

class LegionExamples(ExampleTest):
    LG = 'Legion'

    @unittest.skip('disagrees with the example: finding EC-20')
    def test_legion_example_1(self):
        """Two good players remain, a Fortune Teller and a Slayer; the Slayer joins six Legion in voting the Fortune
        Teller out, and with one good player left evil wins (wiki: Legion, example 1)."""
        lg = self.LG
        g = self.game(['Fortune Teller', lg, lg, 'Slayer', lg, lg, lg, lg])
        self.nominate(B, A)
        for x in (B, C, D, E, F, G, H):
            self.seats[x].day['vote'] = [{'vote': True}]
        block, _ = run(g.vote(A, None, 0))
        run(g.execution(block))
        self.assertFalse(g.g[A].alive)
        self.assertEqual(g.g.winner, 'evil')

    @unittest.skip('disagrees with the example: finding EC-19')
    def test_legion_example_2(self):
        """Four alive: three Legion, and no good player, vote for Julian, who is not executed; Alex, with two votes,
        one of them a good player's, is executed instead: evil wins (wiki: Legion, example 2)."""
        lg = self.LG
        g = self.game([T1, lg, lg, lg, T2, T3])  # A is Julian (good), B is Alex (a Legion)
        for x in (E, F):
            g.g[x].alive = False
        self.nominate(C, A)
        for x in (B, C, D):
            self.seats[x].day['vote'] = [{'vote': True}]
        block, top = run(g.vote(A, None, 0))
        self.nominate(A, B)
        for x in (A, C):
            self.seats[x].day['vote'] = [{'vote': True}]
        block, top = run(g.vote(B, block, top))
        run(g.execution(block))
        self.assertEqual(self.alive(A, B), [True, False])
        self.assertEqual(g.g.winner, 'evil')


# ---- Riot --------------------------------------------------------------------------------------------------------

class RiotExamples(ExampleTest):
    RT = 'Riot'

    def test_riot_example_1(self):
        """A good player nominates a Riot, who dies and nominates another Riot, and so on down four Riot players; the
        last dies, every Riot is dead, and good wins (wiki: Riot, example 1)."""
        rt = self.RT
        g = self.game([T1, rt, rt, rt, rt, T2, T3, T4, O1])
        for q in g.g.players:
            if q.name != A:
                self.seats[q.name].day.setdefault('nominate', []).insert(0, {'nominate': None})
        for who, whom in ((A, B), (B, C), (C, D), (D, E)):
            self.seats[who].day.setdefault('nominate', []).append({'nominate': whom})
        self.day(g, 3)
        run(g.nominations())
        self.assertEqual(self.alive(B, C, D, E), [False] * 4)
        self.assertEqual(g.g.winner, 'good')


if __name__ == '__main__':
    unittest.main()
