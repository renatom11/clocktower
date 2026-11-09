"""The official worked examples for the experimental ("carousel") characters, as scenario tests: one test per example
on each built character's wiki page (its "Examples" section), named after the character and the example's number,
and the official jinx texts where a wiki page gives a jinx example. Each docstring paraphrases the example and cites
it ("wiki: Banshee, example 1"); an example partly about the players' reasoning is tested for its rules only, and
says so. A Storyteller's choice the example names is forced, so each test checks the rule, not chance.

A test the engine disagrees with is kept, skipped with the finding's number (EC-n, docs/examples-findings.md,
"Experimental characters"). The examples of the five removable characters (Lil' Monsta, the Atheist, the Wizard, Legion
and Riot), and any example that needs one of them, are in test_carousel_extra_examples.py."""
import unittest

from clocktower import carousel, carousel3
from clocktower import characters as ch
from clocktower.game import ALL_NAMES, NAMES
from clocktower.state import State

from test_carousel import O1, T1, T2, T3, T4, run
from test_carousel2 import Batch2Test

A, B, C, D, E, F, G, H, I = NAMES


class ExampleTest(Batch2Test):
    """Batch2Test's games (seats A, B, C... in order), with a few helpers for days and votes."""

    def day(self, g, n):
        g.day, g.phase, g.g.day, g.tonight = n, 'day', n, None

    def drunk(self, name):
        self.g.g.add(State('drunk', name, source='test', until=None))

    def nominate(self, nominator, nominee):
        """A nomination on the record (the day's nominations), without its vote."""
        self.g.emit('nomination', {'nominator': nominator, 'nominee': nominee, 'text': ''})
        self.g.g.nominations.append({'day': self.g.day, 'nominator': nominator, 'nominee': nominee,
                                     'character': self.g.g[nominator].character})

    def votes(self, nominee, yes=(), nominator=None):
        """Nominate (by `nominator`, if given) and vote: the players in `yes` vote yes, the others no. Returns the
        number of votes counted."""
        if nominator:
            self.nominate(nominator, nominee)
        for x in yes:
            self.seats[x].day.setdefault('vote', []).append({'vote': True})
        run(self.g.vote(nominee, None, 0))
        for x in yes:  # an unasked voter's answer is not left for the next vote
            self.seats[x].day['vote'] = []
        return [e['data'] for e in self.g.events if e['kind'] == 'vote_result'][-1]['votes']

    def night(self, n, choices=()):
        """Night n, with {name: targets} or {name: (targets, character)} choices."""
        for name, c in dict(choices).items():
            if isinstance(c, tuple):
                self.choose(n, name, c[0], c[1])
            else:
                self.choose(n, name, c)
        run(self.g.night(n))

    def alive(self, *names):
        return [self.g.g[x].alive for x in names]


# ---- Batch 1 -----------------------------------------------------------------------------------------------------

class BansheeExamples(ExampleTest):
    def test_banshee_example_1(self):
        """The Kazali kills the Banshee and the town learns it; the next day she makes two nominations, voting twice
        on each and twice on a third player's nomination; the day after she votes twice for the Kazali without
        spending a vote token (wiki: Banshee, example 1)."""
        g = self.game(['Banshee', 'Village Idiot', 'Fearmonger', 'Shugenja', 'Kazali', T1, T2])
        self.night(2, {E: [A], B: [C], C: [B]})
        self.assertFalse(g.g[A].alive)
        self.assertTrue(self.public(f'{A} has died, killed by the Demon, and is the Banshee'))
        self.day(g, 2)
        self.assertEqual(g.nomination_limit(g.g[A]), 2)
        self.assertEqual(self.votes(B, [A], nominator=A), 2)
        self.assertEqual(self.votes(C, [A], nominator=A), 2)
        self.assertEqual(self.votes(D, [A], nominator=G), 2)
        self.day(g, 3)
        self.assertEqual(self.votes(E, [A], nominator=F), 2)
        self.assertTrue(g.g[A].ghost_vote)

    def test_banshee_example_2(self):
        """A poisoned Banshee killed by the Ojo is not announced, and may not nominate; she votes as any dead player,
        once, with her token (wiki: Banshee, example 2)."""
        g = self.game(['Banshee', T1, T2, T3, 'Poisoner', 'Ojo', T4])
        self.poison(A)
        self.night(2, {E: [A], F: ([], 'Banshee')})
        self.assertFalse(g.g[A].alive)
        self.assertEqual((self.public('Banshee'), g.nomination_limit(g.g[A])), ([], 0))
        self.day(g, 2)
        self.assertEqual(self.votes(B, [A], nominator=C), 1)
        self.assertFalse(g.g[A].ghost_vote)

    def test_banshee_example_3(self):
        """A Banshee the Lycanthrope kills gains nothing and is not announced (wiki: Banshee, example 3)."""
        g = self.game(['Banshee', 'Lycanthrope', T2, T3, 'Poisoner', 'Imp', T4])
        self.night(2, {B: [A], E: [C], F: [D]})
        self.assertFalse(g.g[A].alive)
        self.assertEqual((self.public('Banshee'), g.nomination_limit(g.g[A])), ([], 0))


class StewardExamples(ExampleTest):
    def test_steward_example_1(self):
        """The Steward is shown a good player, here the Undertaker (wiki: Steward, example 1)."""
        self.game(['Steward', 'Undertaker', 'Poisoner', 'Imp', T2], forced={'Steward': {'players': [B]}})
        self.night(1, {C: [D]})
        self.assertTrue(self.told(A, f'{B} is good'))

    def test_steward_example_2(self):
        """The Pit-Hag makes the Poppy Grower the Steward, who learns that night that a player is good: the Spy,
        registering as good (wiki: Steward, example 2)."""
        g = self.game(['Poppy Grower', T1, 'Spy', 'Pit-Hag', 'Imp', T2], extra=['Steward'],
                      forced={'Steward': {'players': [C]}})
        self.night(2, {D: ([A], 'Steward'), E: [B]})
        self.assertEqual(g.g[A].character, 'Steward')
        self.assertTrue(self.told(A, f'{C} is good'))


class NightwatchmanExamples(ExampleTest):
    def test_nightwatchman_example_1(self):
        """The chosen player learns who the Nightwatchman is (wiki: Nightwatchman, example 1)."""
        self.game(['Nightwatchman', T1, T2, 'Poisoner', 'Imp'])
        self.night(1, {A: [B], D: [E]})
        self.assertTrue(self.told(B, f'{A} is the Nightwatchman'))

    def test_nightwatchman_example_2(self):
        """A drunk Nightwatchman's chosen player is not woken and learns nothing (wiki: Nightwatchman, example 2)."""
        self.game(['Nightwatchman', T1, T2, 'Poisoner', 'Imp'],
                  forced={'Nightwatchman': {'players': []}})
        self.drunk(A)
        self.night(1, {A: [B], D: [E]})
        self.assertFalse(self.told(B, 'Nightwatchman'))

    def test_nightwatchman_example_3(self):
        """With the Vortox in play, the chosen player is told that another player is the Nightwatchman (wiki:
        Nightwatchman, example 3)."""
        self.game(['Nightwatchman', T1, T2, 'Poisoner', 'Vortox'], forced={'Nightwatchman': {'players': [C]}})
        self.night(1, {A: [B], D: [C]})
        self.assertTrue(self.told(B, f'{C} is the Nightwatchman'))
        self.assertFalse(self.told(B, f'{A} is the Nightwatchman'))


class MagicianExamples(ExampleTest):
    def test_magician_example_1(self):
        """The Minions learn that the Demon is the Leviathan or the Magician; the Leviathan learns three Minions, the
        Magician among them (wiki: Magician, example 1)."""
        self.dealt(['Magician', T1, T2, T3, 'Fearmonger', 'Assassin', 'Leviathan', T4, 'Chef', 'Monk'])
        self.assertTrue(self.intro(E, f'The Demon is {A} or {G} (you were shown both).'))
        self.assertTrue(self.intro(F, f'The Demon is {A} or {G} (you were shown both).'))
        self.assertTrue(self.intro(G, f'Your Minions: {A}, {E}, {F}'))


class FishermanExamples(ExampleTest):
    def advice(self, g, who=A):
        return run(g.visit_judged(who, {'character': 'Fisherman', 'text': ''}))

    @unittest.skip('disagrees with the example: finding EC-3')
    def test_fisherman_example_1(self):
        """The Fisherman's advice may be that a good player is not to be trusted: the Empath, who is poisoned and
        giving false information (wiki: Fisherman, example 1). Checked: a true, helpful statement naming the Empath
        as the one impaired is among the advice the Storyteller may give."""
        g = self.game(['Fisherman', 'Empath', T2, 'Poisoner', 'Imp', T3])
        self.poison(B)
        stmts = [s for s in carousel.fisherman_statements(g.g, g.g[A]) if s['form'] == 'impaired'
                 and B in s['about'] and s['true']]
        self.assertTrue(stmts and all(s['helps'] for s in stmts))
        g.st.forced = {'Fisherman': {'statements': [stmts[0]['text']]}}
        self.advice(g)
        self.assertTrue(self.told(A, stmts[0]['text']))

    def test_fisherman_example_2(self):
        """The Fisherman is advised to keep the claimed Outsiders alive, who are evil, because the Storyteller thinks
        it helps good (wiki: Fisherman, example 2). The advice itself is a judgment; the rules part tested: once a
        game, true advice."""
        g = self.game(['Fisherman', 'Klutz', T2, 'Fearmonger', 'Imp', T3])
        self.advice(g)
        choice = g.st.seen[f'Fisherman:{A}']
        value = [e['data']['value'] for e in g.events if e['kind'] == 'st_choice'
                 and e['data']['id'] == f'Fisherman:{A}'][0]
        self.assertTrue(choice.truth(value))
        self.day(g, 2)
        self.advice(g)
        self.assertTrue(self.told(A, 'you have already had your advice'))

    def test_fisherman_example_3(self):
        """A drunk Fisherman is advised to kill a Townsfolk: bad advice is legal for them (wiki: Fisherman, example
        3)."""
        g = self.game(['Fisherman', T1, T2, 'Poisoner', 'Imp', T3], forced={'Fisherman': {'statements': [
            f'{B} is evil.']}})
        self.drunk(A)
        self.day(g, 3)
        self.advice(g)
        self.assertTrue(self.told(A, f'{B} is evil.'))


class DamselExamples(ExampleTest):
    CHARS = [T1, T2, 'Damsel', T3, T4, 'Witch', 'Imp', 'Monk']

    def test_damsel_example_1(self):
        """The Witch publicly guesses the Damsel, who was bluffing: evil wins (wiki: Damsel, example 1)."""
        g = self.game(self.CHARS)
        ch.rules('Damsel').act_publicly(g, F, C)
        self.assertEqual(g.g.winner, 'evil')

    @unittest.skip('disagrees with the example: finding EC-1')
    def test_damsel_example_2(self):
        """The Boomdandy guesses the wrong player; then the Goblin guesses the Damsel right: nothing happens, the
        Minions' one guess was spent (wiki: Damsel, example 2)."""
        g = self.game([T1, T2, 'Damsel', T3, T4, 'Boomdandy', 'Imp', 'Goblin'])
        ch.rules('Damsel').act_publicly(g, F, D)
        self.assertIsNone(g.g.winner)
        ch.rules('Damsel').act_publicly(g, H, C)
        self.assertIsNone(g.g.winner)


class GolemExamples(ExampleTest):
    def test_golem_example_1(self):
        """The Golem nominates the Poppy Grower, who dies; the Golem may not nominate again (wiki: Golem, example
        1)."""
        g = self.game(['Golem', 'Poppy Grower', T2, T3, 'Poisoner', 'Imp', T4])
        run(g.nomination_judged(A, B))
        self.assertFalse(g.g[B].alive)
        self.assertEqual(g.nomination_limit(g.g[A]), 0)

    def test_golem_example_2(self):
        """The Golem nominates the Recluse, who registers as the Demon: nothing happens and the vote goes on; the
        Golem may not nominate again (wiki: Golem, example 2)."""
        g = self.game(['Golem', T1, T2, 'Recluse', 'Poisoner', 'Imp', T3], forced={'Golem': {'yes': True}})
        self.nominate(A, D)
        run(g.nomination_judged(A, D))
        self.assertTrue(g.g[D].alive)
        self.assertEqual(g.nomination_limit(g.g[A]), 0)
        self.assertEqual(self.votes(D, [B, C]), 2)


class PoliticianExamples(ExampleTest):
    CHARS = ['Politician', T1, T2, T3, 'Poisoner', 'Imp', T4]

    @unittest.skip('disagrees with the example: finding EC-2')
    def test_politician_example_1(self):
        """With three alive the Politician talks the town out of executing, for a claimed Mayor who was a Minion;
        evil wins at night, and the Storyteller judges the Politician most responsible: they win too (wiki:
        Politician, example 1)."""
        g = self.game(self.CHARS)
        for x in (B, C, D, G):
            g.g[x].alive = False
        self.day(g, 3)
        self.night(4, {E: [B], F: [A]})
        g.g.check_victory()
        g.g.finish()
        self.assertEqual((g.g.winner, g.g[A].alignment), ('evil', 'evil'))

    def test_politician_example_2(self):
        """On the final day the Politician argues for the Empath, but the Saint is executed and good loses; the
        Storyteller judges the town as a whole responsible, so the Politician loses too (wiki: Politician, example
        2)."""
        g = self.game(['Politician', 'Saint', 'Empath', T3, 'Poisoner', 'Imp', T4])
        self.nominate(D, B)
        g.execute(B)
        g.g.finish()
        self.assertEqual((g.g.winner, g.g[A].alignment), ('evil', 'good'))


class HatterExamples(ExampleTest):
    def test_hatter_example_1(self):
        """After the Hatter dies, the Ojo becomes the No Dashii and the Devil's Advocate becomes the Scarlet Woman
        (wiki: Hatter, example 1)."""
        g = self.game([T1, T2, 'Hatter', T3, "Devil's Advocate", 'Ojo', T4], extra=['No Dashii', 'Scarlet Woman'])
        g.execute(C)
        self.night(2, {E: ([A], 'Scarlet Woman'), F: ([B], 'No Dashii')})
        self.assertEqual((g.g[E].character, g.g[F].character), ('Scarlet Woman', 'No Dashii'))

    def test_hatter_example_2(self):
        """The Vigormortis killed its Pit-Hag, then kills the Hatter; both stay as they are, keeping the
        Vigormortis's effect: the dead Pit-Hag keeps her ability (wiki: Hatter, example 2)."""
        g = self.game([T1, T2, 'Hatter', T3, 'Pit-Hag', 'Vigormortis', T4], extra=['Witch', 'Imp'])
        self.night(2, {E: ([A], 'Pit-Hag'), F: [E]})
        self.assertFalse(g.g[E].alive)
        self.assertTrue(g.g.keeps_ability(g.g[E]))
        self.night(3, {E: ([A], 'Pit-Hag'), F: [C]})
        self.assertFalse(g.g[C].alive)
        self.night(4, {E: ([A], 'Pit-Hag'), F: [B]})
        self.assertEqual((g.g[E].character, g.g[F].character), ('Pit-Hag', 'Vigormortis'))
        self.assertTrue(g.g.keeps_ability(g.g[E]))

    @unittest.skip('disagrees with the example: finding EC-4')
    def test_hatter_example_3(self):
        """After the Hatter's execution, the Assassin becomes the Mastermind; the Mastermind's wish to stay is
        refused, the character being taken, so they become the Assassin and may kill again (wiki: Hatter, example
        3)."""
        g = self.game([T1, T2, 'Hatter', T3, 'Assassin', 'Mastermind', 'Imp', T4])
        self.night(2, {E: [A], G: [B]})  # the Assassin kills
        self.assertFalse(g.g[A].alive)
        self.day(g, 2)
        g.execute(C)
        self.night(3, {E: ([], 'Mastermind'), F: ([], 'Assassin'), G: [H]})
        self.assertEqual((g.g[E].character, g.g[F].character), ('Mastermind', 'Assassin'))
        self.day(g, 3)
        self.night(4, {F: [D], G: [H]})
        self.assertFalse(g.g[D].alive)


class PlagueDoctorExamples(ExampleTest):
    MINIONS = ['Spy', 'Scarlet Woman', 'Baron', 'Witch', 'Cerenovus', 'Organ Grinder', 'Poisoner']

    def died(self, chars, gained, more=None):
        g = self.game(chars, forced={**(more or {}), 'Plague Doctor': {'character': gained}}, extra=self.MINIONS)
        g.execute(A)
        run(g.run_pending())
        return g

    def test_plague_doctor_example_1(self):
        """The Plague Doctor dies and the Storyteller gains the Poisoner's ability, poisoning a player each night
        (wiki: Plague Doctor, example 1)."""
        g = self.died(['Plague Doctor', T1, T2, T3, 'Mastermind', 'Imp', T4], 'Poisoner',
                      {'Storyteller:Poisoner': {'players': [C]}})
        self.assertEqual(g.g.notes['Storyteller ability'], 'Poisoner')
        self.night(2, {F: [B]})
        self.assertTrue(g.g.is_poisoned(g.g[C]))

    def test_plague_doctor_example_2(self):
        """The Storyteller gains the Cerenovus's ability, then the Pit-Hag makes the Witch the Cerenovus: two
        Cerenovus abilities are in play (wiki: Plague Doctor, example 2)."""
        g = self.died(['Plague Doctor', T1, T2, 'Witch', 'Pit-Hag', 'Imp', T4], 'Cerenovus')
        self.assertEqual(g.g.notes['Storyteller ability'], 'Cerenovus')
        self.night(2, {E: ([D], 'Cerenovus'), F: [B]})
        self.assertEqual(g.g[D].character, 'Cerenovus')
        self.assertEqual(g.g.notes['Storyteller ability'], 'Cerenovus')

    @unittest.skip('disagrees with the example: finding EC-5')
    def test_plague_doctor_example_3(self):
        """The Storyteller has had the Organ Grinder's ability for two days; the dead Plague Doctor made drunk by the
        Minstrel changes nothing (wiki: Plague Doctor, example 3)."""
        g = self.died(['Plague Doctor', 'Minstrel', T2, T3, 'Mastermind', 'Imp', T4], 'Organ Grinder')
        self.assertEqual(g.g.notes['Storyteller ability'], 'Organ Grinder')
        self.drunk(A)
        self.day(g, 3)
        self.assertEqual(g.g.notes['Storyteller ability'], 'Organ Grinder')
        self.assertTrue(g.secret_votes())


class SummonerExamples(ExampleTest):
    def test_summoner_example_1(self):
        """On the third night the Summoner makes the Snitch the evil Lleech, who chooses a player to poison and to
        kill (wiki: Summoner, example 1)."""
        g = self.game(['Snitch', T1, T2, T3, 'Summoner', T4, O1], extra=['Lleech'])
        self.night(3, {E: ([A], 'Lleech')})
        self.assertEqual((g.g[A].character, g.g[A].alignment), ('Lleech', 'evil'))
        self.assertTrue(self.told(A, 'you are now the Lleech'))
        self.day(g, 3)
        self.night(4, {A: [B]})
        self.assertTrue(g.g.is_poisoned(g.g[B]) or not g.g[B].alive)

    def test_summoner_example_2(self):
        """The Summoner is executed on the first day: good wins (wiki: Summoner, example 2)."""
        g = self.game([T1, T2, T3, T4, 'Monk', 'Summoner', 'Chef'], extra=['Imp'])
        g.execute(F)
        self.assertEqual(g.g.winner, 'good')

    def test_summoner_example_3(self):
        """On the third night the Summoner makes the Alchemist the Leviathan; at dawn everyone learns the Leviathan
        is in play and it is day 3 of 5 (wiki: Summoner, example 3)."""
        g = self.game(['Alchemist', T1, T2, T3, 'Summoner', T4, O1], extra=['Leviathan', 'Poisoner'])
        self.night(3, {E: ([A], 'Leviathan')})
        self.assertEqual(g.g[A].character, 'Leviathan')
        self.assertTrue(self.public('the Leviathan is in play'))


class OjoExamples(ExampleTest):
    def test_ojo_example_1(self):
        """The Ojo names the Plague Doctor, who dies, then the Poppy Grower, who dies; then the Empath, not in play,
        so the Storyteller kills the Shugenja (wiki: Ojo, example 1)."""
        g = self.game(['Plague Doctor', 'Poppy Grower', 'Shugenja', T3, 'Poisoner', 'Ojo', T4],
                      forced={'Ojo': {'players': [C]}}, extra=['Empath'])
        self.night(2, {E: [D], F: ([], 'Plague Doctor')})
        self.night(3, {E: [D], F: ([], 'Poppy Grower')})
        self.assertEqual(self.alive(A, B), [False, False])
        self.night(4, {E: [D], F: ([], 'Empath')})
        self.assertFalse(g.g[C].alive)


class AlHadikhiaExamples(ExampleTest):
    CHARS = [T1, T2, T3, T4, 'Poisoner', 'Al-Hadikhia', O1]

    def test_al_hadikhia_example_1(self):
        """Of three chosen, two choose to die and one to live: at dawn the two are dead (wiki: Al-Hadikhia, example
        1)."""
        self.game(self.CHARS)
        for x, a in ((A, False), (B, False), (C, True)):
            self.decide(x, a)
        self.night(2, {F: [A, B, C], E: [D]})
        self.assertEqual(self.alive(A, B, C), [False, False, True])

    def test_al_hadikhia_example_2(self):
        """Three chosen, one of them dead, all choose to live: the dead one lives again, and then all three are alive,
        so all three die (wiki: Al-Hadikhia, example 2)."""
        g = self.game(self.CHARS)
        g.g[C].alive = False
        for x in (A, B, C):
            self.decide(x, True)
        self.night(2, {F: [A, B, C], E: [D]})
        self.assertEqual(self.alive(A, B, C), [False, False, False])


# ---- Batch 2 -----------------------------------------------------------------------------------------------------

class PixieExamples(ExampleTest):
    @unittest.skip('disagrees with the example: finding EC-8')
    def test_pixie_example_1(self):
        """The Pixie learns the Washerwoman is in play and claims to be her for days; the Washerwoman is executed, and
        that night the Pixie has her ability and learns that one of two players is the Monk (wiki: Pixie, example
        1)."""
        g = self.game(['Pixie', 'Washerwoman', 'Monk', 'Poisoner', 'Imp', T3], forced={'Pixie': {'character':
                                                                                                  'Washerwoman'}})
        self.night(1, {D: [E], C: [A]})
        for day in (1, 2, 3):
            self.day(g, day)
            self.say(A, 'I am the Washerwoman, and that player is lying.')
        g.execute(B)
        run(g.run_pending())
        self.assertEqual(g.g[A].extra, ['Washerwoman'])
        self.day(g, 3)
        self.night(4, {D: [E], C: [A], E: [F]})
        self.assertTrue(self.told(A, 'is the Monk'))

    def test_pixie_example_2(self):
        """A Drunk who believes they are the Pixie learns the Lycanthrope is in play, which it is not (a Minion
        claims it); when the Minion dies, the Storyteller wakes them each night to attack, but nobody dies (wiki: Pixie,
        example 2). Checked: they may be shown a character not in play, and their attacks kill nobody."""
        g = self.game(['Drunk', T1, T2, 'Poisoner', 'Imp', T3], extra=['Pixie', 'Lycanthrope'],
                      forced={'Pixie': {'character': 'Lycanthrope'}})
        g.g[A].shown = 'Pixie'
        self.night(1, {D: [E]})
        self.assertTrue(self.told(A, 'the Lycanthrope is in play'))
        self.say(D, 'I am the Lycanthrope.')
        g.execute(D)
        run(g.run_pending())
        self.day(g, 2)
        self.night(2, {A: [B], E: [C]})
        self.assertTrue(g.g[B].alive)

    def test_pixie_example_3(self):
        """The Pixie claims the Soldier alongside the real one without pressing it; the Storyteller judges they did
        not really try, so they gain nothing when the Soldier dies (wiki: Pixie, example 3). The judgment is forced;
        checked: no ability without the madness."""
        g = self.game(['Pixie', 'Soldier', T2, 'Poisoner', 'Imp', T3],
                      forced={'Pixie': {'character': 'Soldier'}, 'Madness': {'yes': True}})
        self.night(1, {D: [E]})
        self.say(A, 'I am the Soldier too, I suppose.')
        g.execute(B)
        run(g.run_pending())
        self.assertEqual(g.g[A].extra, [])


class HighPriestessExamples(ExampleTest):
    @unittest.skip('disagrees with the example: finding EC-6')
    def test_high_priestess_example_1(self):
        """The High Priestess is shown the Chef, then the Goblin (an evil player the Storyteller thinks she should
        find out early), then the Drunk (wiki: High Priestess, example 1)."""
        g = self.game(['High Priestess', 'Chef', 'Goblin', 'Drunk', 'Imp', T3],
                      forced={'High Priestess': {'players': [B]}})
        self.night(1, {E: [F]})
        g.st.forced = {'High Priestess': {'players': [C]}}
        self.night(2, {E: [F]})
        g.st.forced = {'High Priestess': {'players': [D]}}
        self.night(3, {E: [F]})
        self.assertEqual(len(self.told(A, 'you should talk to')), 3)
        self.assertTrue(self.told(A, f'talk to {C} most'))

    @unittest.skip('disagrees with the example: finding EC-6')
    def test_high_priestess_example_2(self):
        """Three nights running the High Priestess is shown the Saint, then on the last night the Imp, whose story
        clashes with others' (wiki: High Priestess, example 2)."""
        g = self.game(['High Priestess', 'Saint', T2, 'Poisoner', 'Imp', T3],
                      forced={'High Priestess': {'players': [B]}})
        for n in (1, 2, 3):
            self.night(n, {D: [F], E: [F]})
        g.st.forced = {'High Priestess': {'players': [E]}}
        self.night(4, {D: [F], E: [F]})
        self.assertTrue(self.told(A, f'talk to {E} most'))


class PoppyGrowerExamples(ExampleTest):
    def test_poppy_grower_example_1(self):
        """With the Imp, Poisoner and Witch in play, the Imp learns three bluffs but not its Minions, and the Minions
        learn neither each other nor the Demon (wiki: Poppy Grower, example 1)."""
        self.dealt(['Poppy Grower', T1, T2, T3, T4, 'Poisoner', 'Imp', 'Witch', 'Monk', 'Mayor'])
        for x in (F, H):
            self.assertTrue(self.intro(x, 'You do not learn who the other evil players are.'))
        self.assertFalse(self.intro(G, 'Your Minions'))
        self.assertTrue(self.intro(G, 'Three good characters not in play'))

    def test_poppy_grower_example_2(self):
        """The Poppy Grower is executed and dies; that night the Shabaloth learns its Minions, and the Godfather and
        Baron learn each other and the Demon (wiki: Poppy Grower, example 2)."""
        g = self.dealt(['Poppy Grower', T1, T2, T3, 'Saint', T4, 'Godfather', 'Baron', 'Shabaloth', 'Monk'])
        run(g.night(1))
        self.day(g, 1)
        g.execute(A)
        self.night(2, {I: [B]})
        self.assertTrue(self.told(G, f'The Demon is {I}. Your fellow Minions: {H}.'))
        self.assertTrue(self.told(H, f'The Demon is {I}. Your fellow Minions: {G}.'))
        self.assertTrue(self.told(I, f'you learn who your Minions are: {G}, {H}'))

    def test_poppy_grower_example_3(self):
        """The Poppy Grower is the Drunk: the evil team learn each other as usual, and when the Demon kills them on the
        fourth night nobody learns anything more (wiki: Poppy Grower, example 3)."""
        g = self.dealt(['Drunk', T1, T2, T3, T4, 'Poisoner', 'Imp', 'Monk'], extra=['Poppy Grower'],
                       forced={'drunk_as': {'character': 'Poppy Grower'}})
        self.assertTrue(self.intro(F, f'The Demon is {G}.'))
        for n in (1, 2, 3):
            self.night(n, {F: [B], G: [C] if n > 1 else [], H: [B]})
            self.day(g, n)
        self.night(4, {F: [B], G: [A], H: [B]})
        self.assertFalse(g.g[A].alive)
        self.assertFalse(self.told(G, 'you learn who your Minions are'))


class ShugenjaExamples(ExampleTest):
    def test_shugenja_example_1(self):
        """The Organ Grinder sits two seats clockwise and the Fearmonger three anticlockwise: the Shugenja learns
        clockwise (wiki: Shugenja, example 1)."""
        self.game(['Shugenja', T1, 'Organ Grinder', 'Imp', 'Fearmonger', T2, T3])
        self.night(1, {E: [B]})
        self.assertTrue(self.told(A, 'closest evil player is clockwise'))

    def test_shugenja_example_2(self):
        """The Marionette sits next to the Shugenja clockwise and the Widow anticlockwise: the Storyteller chooses, and
        says clockwise (wiki: Shugenja, example 2)."""
        self.game(['Shugenja', 'Marionette', 'Imp', T1, T2, T3, 'Widow'], forced={'Shugenja': {'yes': True}})
        self.night(1, {G: [D]})
        self.assertTrue(self.told(A, 'closest evil player is clockwise'))


class BalloonistExamples(ExampleTest):
    def test_balloonist_example_1(self):
        """The Balloonist is shown the Vizier, then the High Priestess, then the Politician: three character types
        (wiki: Balloonist, example 1)."""
        g = self.game(['Balloonist', 'Vizier', 'High Priestess', 'Politician', 'Imp', T2])
        for n, x in ((1, B), (2, C), (3, D)):
            g.st.forced = {'Balloonist': {'players': [x]}}
            self.night(n, {E: [F] if n > 1 else []})
            self.assertTrue(self.told(A, f'{x} is of a different character type') or n == 1, n)
            self.day(g, n)
        self.assertEqual(len(self.told(A, 'Balloonist')), 3)

    def test_balloonist_example_2(self):
        """Shown the Nightwatchman on the first night; poisoned on the second, the Balloonist is shown another
        Townsfolk, the Sailor; sober on the third, the Puzzlemaster, a type other than the Sailor's (wiki: Balloonist,
        example 2)."""
        g = self.game(['Balloonist', 'Nightwatchman', 'Sailor', 'Puzzlemaster', 'Poisoner', 'Imp', T2],
                      forced={'Balloonist': {'players': [B]}})
        self.night(1, {E: [G], C: [C]})
        self.day(g, 1)
        g.st.forced = {'Balloonist': {'players': [C]}}
        self.night(2, {E: [A], F: [G], C: [C]})
        self.assertTrue(self.told(A, f'{C} is of a different character type'))
        self.day(g, 2)
        g.st.forced = {'Balloonist': {'players': [D]}}
        self.night(3, {E: [G], F: [G], C: [C]})
        self.assertTrue(self.told(A, f'{D} is of a different character type'))
        self.assertNotIn(C, [v['players'][0] for v in self.values(f'Balloonist:{A}')])


class GeneralExamples(ExampleTest):
    """The General's three examples are the Storyteller's judgment of who is winning. The rules part tested: every
    answer is the Storyteller's to give a sober General, and the General is told it."""

    def told_general(self, answer):
        self.game(['General', T1, T2, 'Scarlet Woman', 'Imp', T3], forced={'General': {'statements': [answer]}})
        self.night(1, {})
        self.assertEqual(self.g.st.seen[f'General:{A}'].truth, None)
        return self.told(A, f'{answer} is winning' if answer != 'neither' else 'neither team is winning')

    def test_general_example_1(self):
        """Five good and four evil alive, the Demon suspected but a trusted Scarlet Woman in play: thumbs down, evil
        is winning (wiki: General, example 1)."""
        self.assertTrue(self.told_general('evil'))

    def test_general_example_2(self):
        """Good has much information and the only Minion is dead: thumbs up, good is winning (wiki: General, example
        2)."""
        self.assertTrue(self.told_general('good'))

    def test_general_example_3(self):
        """An able Po against a well-placed Monk and a well-read town: thumbs to the side, neither team (wiki:
        General, example 3)."""
        self.assertTrue(self.told_general('neither'))


class PreacherExamples(ExampleTest):
    def test_preacher_example_1(self):
        """The Preacher chooses the Engineer: nothing happens (wiki: Preacher, example 1)."""
        g = self.game(['Preacher', 'Engineer', T2, 'Poisoner', 'Imp', T3])
        self.night(1, {A: [B], D: [C]})
        self.assertFalse(self.told(B, 'Preacher'))
        self.assertFalse(g.g.impaired(g.g[B]))

    @unittest.skip('disagrees with the example: finding EC-7')
    def test_preacher_example_2(self):
        """The Preacher chooses the Cerenovus, who learns it and is not woken to use their ability (wiki: Preacher,
        example 2)."""
        g = self.game(['Preacher', T1, T2, 'Cerenovus', 'Imp', T3])
        self.night(1, {A: [D], D: ([B], T1)})
        self.assertTrue(self.told(D, 'the Preacher selected you'))
        self.day(g, 1)
        self.night(2, {A: [B], D: ([C], T2), E: [F]})
        self.assertFalse([r for r in self.seats[D].log if r.kind == 'night' and r.day == 2])

    def test_preacher_example_3(self):
        """The Preacher chooses the Pit-Hag, who is not woken; the next night the Poisoner poisons the Preacher, and
        the Pit-Hag wakes to use her ability (wiki: Preacher, example 3)."""
        g = self.game(['Preacher', T1, T2, 'Pit-Hag', 'Imp', 'Poisoner'], extra=['Saint'])
        self.night(1, {A: [D], F: [B]})
        self.assertTrue(self.told(D, 'the Preacher selected you'))
        self.day(g, 1)
        self.night(2, {A: [B], F: [A], E: [C], D: ([B], 'Saint')})
        self.assertTrue([r for r in self.seats[D].log if r.kind == 'night' and r.day == 2])
        self.assertEqual(g.g[B].character, 'Saint')


class CannibalExamples(ExampleTest):
    def test_cannibal_example_1(self):
        """The Clockmaker is executed; that night the Cannibal learns 2, the Demon and its Minion being two steps
        apart (wiki: Cannibal, example 1)."""
        g = self.game(['Cannibal', 'Clockmaker', 'Poisoner', T2, 'Imp', T3])
        g.execute(B)
        run(g.run_pending())
        self.night(2, {C: [F], E: [D]})
        self.assertTrue(self.told(A, '2'))
        self.assertTrue([t for t in self.told(A, 'Clockmaker') if '2' in t])

    def test_cannibal_example_2(self):
        """On the third night, the Widow (who claimed the Fortune Teller) having been executed, the poisoned
        Cannibal is asked to choose two players as a Fortune Teller and learns "no", though they chose the Demon (wiki:
        Cannibal, example 2)."""
        g = self.game(['Cannibal', T1, T2, 'Widow', 'Imp', T3], forced={'Cannibal': {'character': 'Fortune Teller'},
                                                                       'Fortune Teller': {'yes': False}},
                      extra=['Fortune Teller'])
        self.day(g, 3)
        self.say(D, 'I am the Fortune Teller.')
        g.execute(D)
        run(g.run_pending())
        self.assertTrue(g.g.is_poisoned(g.g[A]))
        self.assertEqual(g.g[A].extra, ['Fortune Teller'])
        self.night(3, {A: [E, B], E: [C]})
        self.assertTrue(self.told(A, 'NO, neither is the Demon'))

    def test_cannibal_example_3(self):
        """On the fourth night, the Mutant having been executed, the Cannibal learns nothing, as a Mutant would not
        wake (wiki: Cannibal, example 3)."""
        g = self.game(['Cannibal', 'Mutant', T2, 'Poisoner', 'Imp', T3])
        self.day(g, 4)
        g.execute(B)
        run(g.run_pending())
        self.assertEqual(g.g[A].extra, ['Mutant'])
        before = len([e for e in g.events if e['to'] == [A]])
        self.night(4, {D: [C], E: [F]})
        self.assertEqual([e for e in g.events[before:] if e['to'] == [A] and e['kind'] == 'info'], [])
        self.assertFalse([r for r in self.seats[A].log if r.kind == 'night' and r.day == 4])


class PuzzlemasterExamples(ExampleTest):
    def guess(self, g, name, who=A):
        return run(g.visit_judged(who, {'character': 'Puzzlemaster', 'text': f'I think it is {name}.'}))

    def test_puzzlemaster_example_1(self):
        """The Puzzlemaster made the Empath drunk; they guess the Empath, and are privately shown the real Demon (wiki:
        Puzzlemaster, example 1)."""
        g = self.dealt(['Puzzlemaster', 'Empath', T2, 'Poisoner', 'Imp', T3], forced={'Puzzlemaster:': {'players':
                                                                                                          [B]}})
        self.day(g, 1)
        self.guess(g, B)
        self.assertTrue(self.told(A, f'the Demon: {E}'))

    def test_puzzlemaster_example_2(self):
        """The Puzzlemaster's drunk is a dead player; another is drunk by the Sailor; they guess the Sailor's drunk,
        and are shown a player who is not the Demon (wiki: Puzzlemaster, example 2)."""
        g = self.dealt(['Puzzlemaster', T1, 'Sailor', 'Poisoner', 'Imp', T3, T4, 'Chef'], forced={'Puzzlemaster:': {
            'players': [B]}})
        g.g[B].alive = False
        self.drunk(F)
        self.day(g, 2)
        self.guess(g, F)
        told = self.told(A, f'you guessed {F}')
        self.assertTrue(told)
        self.assertNotIn(f'the Demon: {E}', told[0])


class HereticExamples(ExampleTest):
    CHARS = ['Heretic', T1, T2, 'Poisoner', 'No Dashii', T3]

    def test_heretic_example_1(self):
        """The Heretic claims it on day 1; that night the Demon kills itself: evil wins (wiki: Heretic, example 1)."""
        g = self.game(self.CHARS)
        self.say(A, 'I am the Heretic.')
        self.night(2, {D: [B], E: [E]})
        self.assertFalse(g.g[E].alive)
        g.g.check_victory()
        g.g.finish()
        self.assertEqual(g.g.winner, 'evil')

    def test_heretic_example_2(self):
        """With three alive, the Heretic convinces the town to execute a good player, leaving the Demon and one other:
        good wins (wiki: Heretic, example 2)."""
        g = self.game(self.CHARS)
        for x in (B, D, F):
            g.g[x].alive = False
        self.day(g, 4)
        g.execute(C)
        g.g.finish()
        self.assertEqual(g.g.winner, 'good')

    def test_heretic_example_3(self):
        """The Heretic is dead; the Saint is executed: good wins (wiki: Heretic, example 3)."""
        g = self.game(['Heretic', 'Saint', T2, 'Poisoner', 'Imp', T3])
        g.g[A].alive = False
        g.execute(B)
        g.g.finish()
        self.assertEqual(g.g.winner, 'good')

    def test_heretic_example_4(self):
        """The Heretic is poisoned; the Assassin kills the Demon: good wins (wiki: Heretic, example 4)."""
        g = self.game(['Heretic', T1, T2, 'Assassin', 'No Dashii', T3])
        self.poison(A)
        self.night(2, {D: [E], E: [B]})
        self.assertFalse(g.g[E].alive)
        g.g.check_victory()
        g.g.finish()
        self.assertEqual(g.g.winner, 'good')

    def test_heretic_example_5(self):
        """Three alive, the Demon is executed: with a Heretic in play, evil wins (wiki: Heretic, example 5)."""
        g = self.game(self.CHARS)
        for x in (B, C, D):
            g.g[x].alive = False
        g.execute(E)
        g.g.finish()
        self.assertEqual(g.g.winner, 'evil')


class MarionetteExamples(ExampleTest):
    def test_marionette_example_1(self):
        """The Marionette believes she is the Undertaker and wakes each night to learn who was executed, often wrongly
        (wiki: Marionette, example 1). The Demon telling her later is talk, not a rule; checked: she wakes as the
        Undertaker, and her information is the Storyteller's to make up."""
        g = self.dealt(['Marionette', 'Imp', T1, T2, T3, T4, 'Monk'], extra=['Undertaker'],
                       forced={'Marionette:': {'character': 'Undertaker'}})
        m = next(p for p in g.g.players if p.character == 'Marionette')
        self.assertEqual(m.shown, 'Undertaker')
        self.assertTrue(g.g.unreliable(m))
        run(g.night(1))
        self.day(g, 1)
        g.execute(C)
        run(g.night(2))
        self.assertTrue(self.told(m.name, 'Undertaker'))

    def test_marionette_example_2(self):
        """The Demon tells a player she is the Marionette, a lie: there is none (wiki: Marionette, example 2). Talk
        only; checked: with no Marionette in play the Demon is told of none."""
        self.dealt(['Imp', T1, T2, T3, 'Poisoner', T4, 'Monk'], extra=['Marionette'])
        self.assertFalse(self.intro(A, 'Marionette'))

    def test_marionette_example_3(self):
        """The Demon tells the player who believes he is the Fortune Teller that he is the Marionette; he does not
        believe it, and the town executes the Demon: good wins (wiki: Marionette, example 3)."""
        g = self.game(['Marionette', 'Imp', T2, T3, T4, 'Monk'], extra=['Fortune Teller'])
        g.g[A].shown = 'Fortune Teller'
        g.execute(B)
        self.assertEqual(g.g.winner, 'good')


class WidowExamples(ExampleTest):
    def test_widow_example_1(self):
        """The Widow sees the Grimoire and poisons the Sailor for the game; the Sailor, now unprotected, dies when
        executed (wiki: Widow, example 1)."""
        g = self.game(['Sailor', T2, T3, T4, 'Widow', 'Imp', O1])
        self.night(1, {E: [A], A: [B]})
        self.assertTrue(self.told(E, 'Widow: you look at the Grimoire'))
        self.assertTrue(g.g.is_poisoned(g.g[A]))
        self.day(g, 1)
        g.execute(A)
        self.assertFalse(g.g[A].alive)

    @unittest.skip('not buildable: the Scapegoat is a Traveller')
    def test_widow_example_2(self):
        """The Pit-Hag makes herself the Widow on the third night, and a good Scapegoat learns a Widow is in play
        (wiki: Widow, example 2)."""

    def test_widow_example_3(self):
        """The Widow poisons the Empath; the Innkeeper makes the Widow drunk, so the Empath is sober; when the
        Innkeeper dies, the Widow is sober and the Empath poisoned again (wiki: Widow, example 3)."""
        g = self.game(['Empath', 'Innkeeper', T3, T4, 'Widow', 'Imp', O1], forced={'Innkeeper': {'players': [E]}})
        self.night(1, {E: [A]})
        self.assertTrue(g.g.is_poisoned(g.g[A]))
        self.day(g, 1)
        self.night(2, {B: [E, C], F: [D]})
        self.assertTrue(g.g.is_drunk(g.g[E]))
        self.assertFalse(g.g.is_poisoned(g.g[A]))
        g.kill(g.g[B], 'test')
        self.assertFalse(g.g.is_drunk(g.g[E]))
        self.assertTrue(g.g.is_poisoned(g.g[A]))


class GoblinExamples(ExampleTest):
    def test_goblin_example_1(self):
        """The Goblin claims it when nominated, has the most votes at the end of the day and is executed: evil wins
        (wiki: Goblin, example 1)."""
        g = self.game([T1, T2, T3, 'Goblin', 'Imp', T4])
        self.nominate(A, D)
        self.say(D, 'I am the Goblin.', 'defense')
        self.nominate(B, C)
        g.execute(D)
        self.assertEqual(g.g.winner, 'evil')

    def test_goblin_example_2(self):
        """The Artist claims to be the Goblin when nominated and is executed: the game goes on (wiki: Goblin, example
        2)."""
        g = self.game(['Artist', T2, T3, 'Goblin', 'Imp', T4])
        self.nominate(B, A)
        self.say(A, 'I am the Goblin.', 'defense')
        g.execute(A)
        self.assertIsNone(g.g.winner)

    def test_goblin_example_3(self):
        """The Goblin claimed it on the two days before but not today, and is executed: the game goes on (wiki:
        Goblin, example 3)."""
        g = self.game([T1, T2, T3, 'Goblin', 'Imp', T4])
        for day in (1, 2):
            self.day(g, day)
            self.nominate(A, D)
            self.say(D, 'I am the Goblin.', 'defense')
        self.day(g, 3)
        self.nominate(A, D)
        self.say(D, 'I am a simple townsperson.', 'defense')
        g.execute(D)
        self.assertIsNone(g.g.winner)


class KazaliExamples(ExampleTest):
    def test_kazali_example_1(self):
        """In a fifteen-player game with no Minions yet, the Kazali makes three players the evil Organ Grinder,
        Vizier and Goblin (wiki: Kazali, example 1)."""
        chars = ['Kazali', T1, T2, T3, T4, 'Soldier', 'Mayor', 'Virgin', 'Slayer', 'Pacifist', 'Tea Lady', 'Fool',
                 'Ravenkeeper', 'Saint', 'Recluse']
        g = self.dealt(chars, extra=['Organ Grinder', 'Vizier', 'Goblin'])
        self.seats[A].day['night'] = [{'targets': [D], 'character': 'Organ Grinder'},
                                      {'targets': [B], 'character': 'Vizier'},
                                      {'targets': [F], 'character': 'Goblin'}]
        run(g.night(1))
        self.assertEqual([(g.g[x].character, g.g[x].alignment) for x in (D, B, F)],
                         [('Organ Grinder', 'evil'), ('Vizier', 'evil'), ('Goblin', 'evil')])


class LeviathanExamples(ExampleTest):
    def test_leviathan_example_1(self):
        """Day 1: the Monk nominates the Virgin and is executed; day 2: the Courtier is executed. Two good players
        executed: evil wins (wiki: Leviathan, example 1)."""
        g = self.game(['Monk', 'Virgin', 'Courtier', T4, 'Poisoner', 'Leviathan', O1])
        self.night(1, {E: [D]})
        self.day(g, 1)
        self.nominate(A, B)
        self.assertTrue(g.virgin(A, B))
        self.assertFalse(g.g[A].alive)
        self.assertIsNone(g.g.winner)
        self.day(g, 2)
        g.execute(C)
        self.assertEqual(g.g.winner, 'evil')

    def test_leviathan_example_2(self):
        """The Scarlet Woman is executed on day 2, the Poisoner on day 3, the Soldier on day 5: evil wins (wiki:
        Leviathan, example 2)."""
        g = self.game(['Soldier', T2, T3, T4, 'Poisoner', 'Leviathan', 'Scarlet Woman'])
        for day, x in ((2, G), (3, E), (5, A)):
            self.day(g, day)
            g.execute(x)
            self.assertIsNone(g.g.winner)
        ch.rules('Leviathan').end_of_day(g, g.g[F])
        self.assertEqual(g.g.winner, 'evil')


# ---- Batch 3 -----------------------------------------------------------------------------------------------------

class VillageIdiotExamples(ExampleTest):
    def test_village_idiot_example_1(self):
        """Three Village Idiots, one drunk, all choose the Kazali: the drunk one learns good, the others evil (wiki:
        Village Idiot, example 1)."""
        self.game(['Village Idiot', 'Village Idiot', 'Village Idiot', T1, 'Kazali', T2],
                      forced={f'Village Idiot:{A}': {'yes': False}})
        self.drunk(A)
        self.night(2, {A: [E], B: [E], C: [E], E: [F]})
        self.assertTrue(self.told(A, f'you chose {E}: they are good'))
        for x in (B, C):
            self.assertTrue(self.told(x, f'you chose {E}: they are evil'))

    def test_village_idiot_example_2(self):
        """Of two Village Idiots, the sober one chooses the evil player bluffing as a third and learns evil; the drunk
        one chooses the Heretic and learns good (wiki: Village Idiot, example 2). The evil player's false claim is
        talk."""
        self.game(['Village Idiot', 'Village Idiot', 'Heretic', 'Poisoner', 'Imp', T1],
                      forced={f'Village Idiot:{B}': {'yes': False}})
        self.drunk(B)
        self.night(2, {A: [D], B: [C], D: [F], E: [F]})
        self.assertTrue(self.told(A, f'you chose {D}: they are evil'))
        self.assertTrue(self.told(B, f'you chose {C}: they are good'))


class AcrobatExamples(ExampleTest):
    def test_acrobat_example_1(self):
        """The Sailor chooses the Assassin and the Storyteller makes the Sailor drunk; the Acrobat chose the Sailor,
        and dies (wiki: Acrobat, example 1)."""
        g = self.game(['Acrobat', 'Sailor', T2, 'Assassin', 'Imp', T3], forced={'Sailor': {'players': [B]}})
        self.night(2, {A: [B], B: [D], E: [C]})
        self.assertTrue(g.g.is_drunk(g.g[B]))
        self.assertFalse(g.g[A].alive)

    def test_acrobat_example_2(self):
        """The Acrobat chooses a sober, healthy Tinker: nothing happens (wiki: Acrobat, example 2)."""
        self.game(['Acrobat', 'Tinker', T2, 'Poisoner', 'Imp', T3], forced={'Tinker': {'yes': False}})
        self.night(2, {A: [B], D: [F], E: [C]})
        self.assertEqual(self.alive(A, B), [True, True])

    def test_acrobat_example_3(self):
        """The Acrobat chooses the Preacher, whom the Pukka poisons later that night: the Acrobat dies (wiki: Acrobat,
        example 3)."""
        g = self.game(['Acrobat', 'Preacher', T2, T3, 'Pukka', T4])
        self.night(2, {A: [B], B: [C], E: [B]})
        self.assertTrue(g.g.is_poisoned(g.g[B]))
        self.assertFalse(g.g[A].alive)


class LycanthropeExamples(ExampleTest):
    def test_lycanthrope_example_1(self):
        """The Lycanthrope attacks the General, who dies; the Imp attacks the Amnesiac, who lives: the Demon cannot
        kill tonight (wiki: Lycanthrope, example 1)."""
        self.game(['Lycanthrope', 'General', 'Amnesiac', 'Poisoner', 'Imp', T3])
        self.night(2, {A: [B], D: [F], E: [C]})
        self.assertEqual(self.alive(B, C), [False, True])

    def test_lycanthrope_example_2(self):
        """The Lycanthrope attacks the Farmer, who dies and another good player becomes a Farmer; the Magician the
        Pukka poisoned last night does not die, the Pukka killing nobody tonight (wiki: Lycanthrope, example 2)."""
        g = self.game(['Lycanthrope', 'Farmer', 'Magician', T3, 'Pukka', T4], forced={'Farmer:': {'players': [D]}})
        self.night(2, {A: [E], E: [C]})
        self.assertTrue(g.g.is_poisoned(g.g[C]))
        self.day(g, 2)
        self.night(3, {A: [B], E: [D]})
        self.assertEqual(self.alive(B, C), [False, True])
        self.assertEqual(g.g[D].character, 'Farmer')

    def test_lycanthrope_example_3(self):
        """The Lycanthrope's attack on the Godfather and on the Zealot (registering as evil by the Lycanthrope's
        ability) kills neither; the Demon kills the Lycanthrope (wiki: Lycanthrope, example 3)."""
        g = self.dealt(['Lycanthrope', T1, T2, T3, 'Zealot', 'Godfather', 'Imp'], forced={'Faux Paw': {'players':
                                                                                                         [E]}})
        run(g.night(1))
        self.night(2, {A: [F], G: [B]})
        self.assertTrue(g.g[F].alive)
        self.night(3, {A: [E], G: [A]})
        self.assertTrue(g.g[E].alive)
        self.assertFalse(g.g[A].alive)


class NobleExamples(ExampleTest):
    def test_noble_example_1(self):
        """The Noble is shown three players, exactly one of them evil (wiki: Noble, example 1)."""
        self.game(['Noble', T1, 'Poisoner', T2, 'Imp', T3], forced={'Noble:': {'players': [B, C, D]}})
        self.night(1, {C: [F]})
        self.assertTrue(self.told(A, f'{B}, {C} and {D}'))

    def test_noble_example_2(self):
        """The Noble is shown the Chambermaid, the Barber and the Recluse, who registered as evil (wiki: Noble,
        example 2)."""
        self.game(['Noble', 'Chambermaid', 'Barber', 'Recluse', 'Poisoner', 'Imp'],
                  forced={'Noble:': {'players': [B, C, D]}})
        self.night(1, {B: [E, F], E: [F]})
        self.assertTrue(self.told(A, f'{B}, {C} and {D}'))

    def test_noble_example_3(self):
        """The Pit-Hag makes a player the Noble on the third night, who learns that one of three players is evil:
        one is good, one the Spy registering as good, one the Po (wiki: Noble, example 3)."""
        g = self.game([T1, T2, 'Spy', 'Pit-Hag', 'Po', T3], extra=['Noble'],
                      forced={'Noble:': {'players': [B, C, E]}})
        self.day(g, 2)
        self.night(3, {D: ([A], 'Noble'), E: [F]})
        self.assertEqual(g.g[A].character, 'Noble')
        self.assertTrue(self.told(A, f'{B}, {C} and {E}'))


class FarmerExamples(ExampleTest):
    def test_farmer_example_1(self):
        """The Demon kills the Farmer; the Alchemist becomes the Farmer, the Fearmonger could not, being evil (wiki:
        Farmer, example 1)."""
        g = self.game(['Farmer', 'Alchemist', T2, 'Fearmonger', 'Imp', T3], forced={'Farmer:': {'players': [B]}})
        self.night(2, {D: [C], E: [A]})
        self.assertEqual(g.g[B].character, 'Farmer')
        self.assertNotIn(D, [v['players'][0] for v in self.values(f'Farmer:{A}')])

    def test_farmer_example_2(self):
        """The Farmer dies on the second night and the Choirboy becomes the Farmer; that Farmer dies on the third and
        the Heretic becomes one: three Farmers, two dead, and no Choirboy or Heretic (wiki: Farmer, example 2)."""
        g = self.game(['Farmer', 'Choirboy', 'Heretic', 'Poisoner', 'Imp', T3], forced={'Farmer:': {'players': [B]}})
        self.night(2, {D: [F], E: [A]})
        self.day(g, 2)
        g.st.forced = {'Farmer:': {'players': [C]}}
        self.night(3, {D: [F], E: [B]})
        farmers = [p for p in g.g.players if p.character == 'Farmer']
        self.assertEqual(([p.name for p in farmers], [p.alive for p in farmers]), ([A, B, C], [False, False, True]))


class ZealotExamples(ExampleTest):
    def zealot_votes(self, nominee, answer):
        """Whether the Zealot's hand was raised on this nomination, answering `answer`."""
        self.seats[A].day['vote'] = [{'vote': answer}]
        run(self.g.vote(nominee, None, 0))
        return [e['data']['yes'] for e in self.g.events if e['kind'] == 'vote' and e['data']['voter'] == A][-1]

    def test_zealot_example_1(self):
        """With seven and then five alive the Zealot votes on every nomination; with three alive they may choose not
        to vote (wiki: Zealot, example 1)."""
        g = self.game(['Zealot', T1, T2, T3, 'Poisoner', 'Imp', T4])
        self.assertTrue(self.zealot_votes(B, False))
        for x in (B, C):
            g.g[x].alive = False
        self.assertTrue(self.zealot_votes(D, False))
        for x in (D, G):
            g.g[x].alive = False
        self.assertFalse(self.zealot_votes(E, False))

    def test_zealot_example_2(self):
        """A dead Zealot with nine alive need not vote, and votes with their token once three are alive (wiki: Zealot,
        example 2)."""
        g = self.game(['Zealot', T1, T2, T3, T4, 'Soldier', 'Mayor', 'Poisoner', 'Imp', 'Chef'])
        g.g[A].alive = False
        self.assertFalse(self.zealot_votes(B, False))
        for x in (B, C, D, E, F, G):
            g.g[x].alive = False
        self.assertTrue(self.zealot_votes(H, True))
        self.assertFalse(g.g[A].ghost_vote)


class OrganGrinderExamples(ExampleTest):
    def test_organ_grinder_example_1(self):
        """With eight alive, votes are eyes closed: the Noble gets 5, the Imp 7, the Pixie 4; the Storyteller declares
        the Imp executed, and good wins (wiki: Organ Grinder, example 1)."""
        g = self.game(['Noble', 'Pixie', T1, T2, T3, 'Organ Grinder', 'Imp', T4])
        block, top = None, 0
        for nominee, yes in ((A, (B, C, D, E, F)), (G, (A, B, C, D, E, F, H)), (B, (A, C, D, E))):
            for x in yes:
                self.seats[x].day['vote'] = [{'vote': True}]
            block, top = run(g.vote(nominee, block, top))
            for x in yes:
                self.seats[x].day['vote'] = []
            self.assertEqual([e['to'] for e in g.events if e['kind'] == 'vote_result'][-1], 'audit')
        self.assertEqual((block, top), (G, 7))
        g.execute(block)
        self.assertEqual(g.g.winner, 'good')


class HarpyExamples(ExampleTest):
    def harpy(self, chars, first, second, forced):
        g = self.game(chars, forced={'Harpy deaths': forced})
        self.night(1, {D: [first, second]})
        self.assertTrue(self.told(first, f'points to {second}'))
        return g

    def test_harpy_example_1(self):
        """The Harpy chooses the Monk and the Engineer; the Monk insists the Engineer is evil, and lives (wiki: Harpy,
        example 1)."""
        g = self.harpy(['Monk', 'Engineer', T3, 'Harpy', 'Imp', T4], A, B, {'players': [A]})
        self.say(A, f'I am the Investigator and I saw {B}: {B} is evil, execute them.')
        run(ch.rules('Harpy').moment(g, g.g[D], 'nominations'))
        self.assertTrue(g.g[A].alive)

    def test_harpy_example_2(self):
        """The Harpy chooses the Oracle and the dead Alchemist; the Oracle says she trusts the Alchemist, and the
        Storyteller declares that the Oracle dies (wiki: Harpy, example 2)."""
        g = self.game(['Oracle', 'Alchemist', T3, 'Harpy', 'Imp', T4], forced={'Harpy deaths': {'players': [A]}})
        g.g[B].alive = False
        self.night(1, {D: [A, B]})
        self.say(A, f'I trust {B}: my Oracle information says {B} was not evil, so {B} is good.')
        run(ch.rules('Harpy').moment(g, g.g[D], 'nominations'))
        self.assertFalse(g.g[A].alive)

    def test_harpy_example_3(self):
        """The Farmer, chosen first, has no information to claim, so clears every other living player to leave the
        second as the Demon by implication (wiki: Harpy, example 3). A strategy for madness, judged by the
        Storyteller; checked: the Farmer is told whom to be mad about."""
        self.harpy(['Farmer', T2, T3, 'Harpy', 'Imp', T4], A, E, {'players': []})


class BoffinExamples(ExampleTest):
    @unittest.skip('disagrees with the example: finding EC-9')
    def test_boffin_example_1(self):
        """The Imp has the Virgin's ability; the Alsaahir nominates it and is executed at once (wiki: Boffin, example
        1)."""
        g = self.game(['Alsaahir', T2, T3, 'Boffin', 'Imp', T4], forced={'Boffin:': {'character': 'Virgin'}},
                      extra=['Virgin'])
        self.assertIn('Virgin', carousel3.boffin_options(g.g))
        run(g.night(1))
        self.day(g, 1)
        self.nominate(A, E)
        self.assertTrue(g.virgin(A, E))
        self.assertFalse(g.g[A].alive)

    @unittest.skip('disagrees with the example: finding EC-9')
    def test_boffin_example_2(self):
        """The Lord of Typhon has the Chambermaid's ability and wakes each night to use it; on the fourth night the
        Boffin is drunk, so the Demon does not wake for it (wiki: Boffin, example 2)."""
        g = self.game(['Boffin', T1, 'Lord of Typhon', T2, T3, T4], forced={'Boffin:': {'character': 'Chambermaid'}},
                      extra=['Chambermaid'])
        self.assertIn('Chambermaid', carousel3.boffin_options(g.g))
        run(g.night(1))
        self.assertTrue(self.told(C, "you have the Chambermaid's ability"))

    @unittest.skip('disagrees with the example: finding EC-9')
    def test_boffin_example_3(self):
        """The Kazali has the Banshee's ability; it dies at night and the Scarlet Woman becomes the Kazali; the dead
        Kazali may nominate and vote twice a day (wiki: Boffin, example 3)."""
        g = self.game([T1, T2, 'Boffin', 'Scarlet Woman', 'Kazali', T3, T4],
                      forced={'Boffin:': {'character': 'Banshee'}}, extra=['Banshee'])
        self.assertIn('Banshee', carousel3.boffin_options(g.g))
        run(g.night(1))
        self.assertTrue(self.told(E, "you have the Banshee's ability"))


class BoomdandyExamples(ExampleTest):
    def test_boomdandy_example_1(self):
        """The Boomdandy is executed and explodes: all but the Po, the Widow and the Fortune Teller die; everyone
        points, the Widow is pointed at most and dies, and evil wins (wiki: Boomdandy, example 1)."""
        g = self.game(['Boomdandy', 'Po', 'Widow', 'Fortune Teller', T1, T2, T3, T4],
                      forced={'Boomdandy:': {'players': [B, C, D]}})
        for x in (A, B, C, D, E, F, G, H):
            self.choose(1, x, [C if x != C else D])
        g.execute(A)
        run(g.run_pending())
        self.assertEqual([q.name for q in g.g.living()], [B, D])
        self.assertEqual(g.g.winner, 'evil')


class FearmongerExamples(ExampleTest):
    def nominated(self, g, nominator, nominee):
        self.nominate(nominator, nominee)
        g.execute(nominee)
        return g.g.winner

    def test_fearmonger_example_1(self):
        """The Fearmonger chooses the Butler on the first night, and everyone learns a new player was chosen; the
        Fearmonger nominates and executes the Butler: evil wins (wiki: Fearmonger, example 1)."""
        g = self.game(['Butler', T1, T2, 'Fearmonger', 'Imp', T3])
        self.night(1, {D: [A], A: [B]})
        self.assertEqual(len(self.public('the Fearmonger has chosen a player')), 1)
        self.day(g, 1)
        self.assertEqual(self.nominated(g, D, A), 'evil')

    def test_fearmonger_example_2(self):
        """The Fearmonger chooses the Juggler; the Flowergirl nominates the Juggler, who is executed: the game goes on
        (wiki: Fearmonger, example 2)."""
        g = self.game(['Juggler', 'Flowergirl', T2, 'Fearmonger', 'Imp', T3])
        self.night(1, {D: [A]})
        self.day(g, 1)
        self.assertIsNone(self.nominated(g, B, A))

    def test_fearmonger_example_3(self):
        """The Fearmonger chooses the Empath, then the Soldier the next night, then nominates and executes the Empath:
        the game goes on (wiki: Fearmonger, example 3)."""
        g = self.game(['Empath', 'Soldier', T2, 'Fearmonger', 'Imp', T3])
        self.night(1, {D: [A]})
        self.day(g, 1)
        self.night(2, {D: [B], E: [C]})
        self.day(g, 2)
        self.assertIsNone(self.nominated(g, D, A))

    def test_fearmonger_example_4(self):
        """With the Poppy Grower in play, the Fearmonger unknowingly chooses the Baron, then nominates and executes
        them: good wins (wiki: Fearmonger, example 4)."""
        g = self.game(['Poppy Grower', T1, 'Baron', 'Fearmonger', 'Imp', T3])
        self.night(1, {D: [C]})
        self.day(g, 1)
        self.assertEqual(self.nominated(g, D, C), 'good')


class XaanExamples(ExampleTest):
    def test_xaan_example_1(self):
        """With three Outsiders, on night 3 the Exorcist's choice of the Demon, the Acrobat's of the Drunk and the
        Seamstress's information all fail: the Townsfolk are poisoned (wiki: Xaan, example 1)."""
        g = self.game(['Exorcist', 'Acrobat', 'Seamstress', 'Drunk', 'Recluse', 'Saint', 'Xaan', 'Imp', T1])
        g.g.notes['Xaan'] = {G: 3}
        self.day(g, 2)
        self.night(3, {A: [H], B: [D], C: [E, F], H: [I]})
        self.assertTrue(all(g.g.is_poisoned(g.g[x]) for x in (A, B, C, I)))
        self.assertTrue(g.g[B].alive)  # the Acrobat chose the Drunk, and lives
        self.assertFalse(g.g[I].alive)  # the Exorcist did not stop the Demon
        self.assertTrue(g.g.unreliable(g.g[C], 'Seamstress'))

    def test_xaan_example_2(self):
        """In an eleven-player game with one Outsider, the Xaan poisons every Townsfolk on the first night; the Pit-Hag
        creates a Hatter on the second, and nobody is poisoned that night (wiki: Xaan, example 2)."""
        chars = [T1, T2, T3, T4, 'Soldier', 'Mayor', 'Virgin', O1, 'Xaan', 'Pit-Hag', 'Imp']
        g = self.game(chars, extra=['Hatter'])
        g.g.notes['Xaan'] = {I: 1}
        self.night(1, {})
        self.assertTrue(all(g.g.is_poisoned(g.g[x]) for x in NAMES[:7]))
        self.day(g, 1)
        self.night(2, {ALL_NAMES[9]: ([B], 'Hatter'), ALL_NAMES[10]: [C]})
        self.assertEqual(g.g[B].character, 'Hatter')
        self.assertFalse(any(g.g.is_poisoned(p) for p in g.g.players))

    @unittest.skip('disagrees with the example: finding EC-10')
    def test_xaan_example_3(self):
        """With no Outsiders in play the Xaan never poisons anyone (its bluff of the Zealot is talk) (wiki: Xaan,
        example 3). Checked: a game may be dealt with the Xaan and no Outsiders, X is then 0, and nobody is
        poisoned."""
        from clocktower import carousel3
        g = self.dealt([T1, T2, 'Xaan', 'Imp', T3], extra=[O1, 'Zealot'])
        g.forced = None
        run(ch.rules('Xaan').setup(g))
        self.assertEqual((carousel3.outsiders(g.g), g.g.notes['Xaan'][C]), (0, 0))
        for n in (1, 2, 3):
            self.night(n, {D: [E] if n > 1 else []})
            self.assertFalse(any(g.g.is_poisoned(p) for p in g.g.players))
            self.day(g, n)


class AlchemistExamples(ExampleTest):
    def test_alchemist_example_1(self):
        """The Alchemist has the Baron's ability: there are two extra Outsiders (wiki: Alchemist, example 1)."""
        g = self.dealt(['Alchemist', T2, T3, 'Poisoner', 'Imp', T4, T1], extra=['Baron', 'Butler', 'Recluse'])
        run(ch.rules('Alchemist').setup_change(g, g.g[A], 'Baron'))
        self.assertEqual(carousel3.outsiders(g.g), 2)


# ---- Batch 3b ----------------------------------------------------------------------------------------------------

def guesses(*pairs):
    return [{'player': p, 'character': c} for p, c in pairs]


class Batch3bExample(ExampleTest):
    def claim(self, name, character, **use):
        self.g.public_abilities([name], {name: {'ability': {'character': character, **use}}})
        run(self.g.run_pending())

    def join(self, *names, vote=True):
        for n in names:
            self.seats[n].day.setdefault('decide', []).append({'vote': vote})


class AlsaahirExamples(Batch3bExample):
    CHARS = ['Alsaahir', T1, T2, 'Poisoner', 'Imp', T3, 'Spy']

    def test_alsaahir_example_1(self):
        """The Alsaahir guesses four good players as Minions and Demons: nothing happens (wiki: Alsaahir, example
        1)."""
        g = self.game(self.CHARS)
        self.claim(A, 'Alsaahir', guesses=guesses((B, 'Imp'), (C, 'Poisoner'), (F, 'Spy'), (A, 'Spy')))
        self.assertIsNone(g.g.winner)

    def test_alsaahir_example_2(self):
        """The Alsaahir names the Demon and both Minions rightly: good wins at once (wiki: Alsaahir, example 2)."""
        g = self.game(self.CHARS)
        self.claim(A, 'Alsaahir', guesses=guesses((E, 'Imp'), (D, 'Poisoner'), (G, 'Spy')))
        self.assertEqual(g.g.winner, 'good')

    def test_alsaahir_example_3(self):
        """A drunk Alsaahir's right guess does nothing; the next day, sober, they swap the Demon and a Minion: nothing
        either (wiki: Alsaahir, example 3)."""
        g = self.game(self.CHARS)
        self.drunk(A)
        self.claim(A, 'Alsaahir', guesses=guesses((E, 'Imp'), (D, 'Poisoner'), (G, 'Spy')))
        self.assertIsNone(g.g.winner)
        g.g.states = [s for s in g.g.states if s.source != 'test']
        self.day(g, 2)
        self.claim(A, 'Alsaahir', guesses=guesses((D, 'Imp'), (E, 'Poisoner'), (G, 'Spy')))
        self.assertIsNone(g.g.winner)


class HuntsmanExamples(Batch3bExample):
    def test_huntsman_example_1(self):
        """Woken on the first night, the Huntsman waits; on the second they choose the Damsel, who becomes the
        Undertaker and learns who died today (wiki: Huntsman, example 1)."""
        g = self.game(['Huntsman', 'Damsel', T2, 'Poisoner', 'Imp', T3], extra=['Undertaker'],
                      forced={'Huntsman:': {'character': 'Undertaker'}})
        self.night(1, {D: [C]})
        self.assertTrue([r for r in self.seats[A].log if r.kind == 'night' and r.day == 1])
        self.day(g, 1)
        g.execute(C)
        self.night(2, {A: [B], D: [F], E: [F]})
        self.assertEqual(g.g[B].character, 'Undertaker')
        self.assertTrue(self.told(B, 'you are now the Undertaker'))
        self.assertTrue([t for t in self.told(B, 'Undertaker:') if C in t])

    def test_huntsman_example_2(self):
        """The Huntsman chooses the General: nothing happens, and they are not woken again (wiki: Huntsman, example
        2)."""
        g = self.game(['Huntsman', 'General', T2, 'Poisoner', 'Imp', T3], extra=['Damsel'])
        self.night(1, {A: [B], D: [C]})
        self.assertEqual(g.g[B].character, 'General')
        self.assertIsNone(ch.rules('Huntsman').night_spec(g, g.g[A], None))


class KnightExamples(Batch3bExample):
    def test_knight_example_1(self):
        """With the Undertaker, the Imp and the Fortune Teller in play, the Knight learns the Undertaker and the
        Fortune Teller (wiki: Knight, example 1)."""
        self.game(['Knight', 'Undertaker', 'Imp', 'Fortune Teller', 'Poisoner', T3],
                  forced={'Knight:': {'players': [B, D]}})
        self.night(1, {D: [B, C], E: [F]})
        self.assertTrue(self.told(A, f'{B} and {D} are not the Demon'))

    def test_knight_example_2(self):
        """Under the Vortox, the Knight learns the Vortox and the Alchemist: false information must include the
        Demon (wiki: Knight, example 2)."""
        g = self.game(['Knight', T1, 'Alchemist', 'Poisoner', 'Vortox', T3], forced={'Knight:': {'players': [C, E]}})
        self.night(1, {D: [B]})
        self.assertTrue(self.told(A, f'{C} and {E} are not the Demon'))
        self.assertTrue(all(E in v['players'] for v in g.false_only(g.st.seen[f'Knight:{A}']).values))


class KingExamples(Batch3bExample):
    def test_king_example_1(self):
        """A King among thirteen learns nothing on nights 2 and 3; once the dead outnumber the living (seven to six)
        she learns an alive character each night: the Snitch, then the Witch (wiki: King, example 1)."""
        chars = ['King', 'Snitch', 'Witch', 'Imp', T1, T2, T3, T4, 'Soldier', 'Pacifist', 'Virgin', 'Saint', 'Recluse']
        g = self.game(chars, forced={'King:': {'character': 'Snitch'}})
        names = ALL_NAMES[:13]
        g.g[names[12]].alive = False
        for n, victim in ((2, names[11]), (3, names[10])):
            self.night(n, {C: [E], D: [victim]})
            self.assertFalse(self.told(A, 'is alive'), n)
            self.day(g, n)
        for x in names[5:9]:
            g.g[x].alive = False
        self.assertEqual(sum(not p.alive for p in g.g.players), 7)
        self.night(4, {C: [E], D: [names[9]]})
        self.assertTrue(self.told(A, 'the Snitch is alive'))
        self.day(g, 4)
        g.st.forced = {'King:': {'character': 'Witch'}}
        self.night(5, {C: [E], D: [E]})
        self.assertTrue(self.told(A, 'the Witch is alive'))

    def test_king_example_2(self):
        """The Demon knows who the King is, and kills him, gambling that the player claiming the Choirboy is not; he
        is the Butler, so nobody learns anything (wiki: King, example 2)."""
        g = self.game(['King', 'Butler', T2, 'Poisoner', 'Imp', T3])
        self.night(1, {B: [C], D: [F]})
        self.assertTrue(self.told(E, f'{A} is the King'))
        self.day(g, 1)
        self.night(2, {B: [C], D: [F], E: [A]})
        self.assertFalse(g.g[A].alive)
        self.assertFalse([x for x in (B, C, D, F) if self.told(x, 'is the Demon')])


class ChoirboyExamples(Batch3bExample):
    def test_choirboy_example_1(self):
        """The Imp kills the Empath; the next night the Monk protects the King from it; the night after the King,
        unprotected, dies, and the Choirboy learns which player is the Imp (wiki: Choirboy, example 1)."""
        g = self.game(['Choirboy', 'King', 'Empath', 'Monk', 'Poisoner', 'Imp', T3])
        self.night(2, {E: [G], F: [C], D: [A]})
        self.assertFalse(g.g[C].alive)
        self.day(g, 2)
        self.night(3, {E: [G], F: [B], D: [B]})
        self.assertTrue(g.g[B].alive)
        self.assertFalse(self.told(A, 'is the Demon'))
        self.day(g, 3)
        self.night(4, {E: [G], F: [B], D: [A]})
        self.assertFalse(g.g[B].alive)
        self.assertTrue(self.told(A, f'{F} is the Demon'))

    def test_choirboy_example_2(self):
        """The Shabaloth kills the King; the drunk Choirboy wakes and is wrongly shown the General as the Demon (wiki:
        Choirboy, example 2)."""
        g = self.game(['Choirboy', 'King', 'General', T3, 'Poisoner', 'Shabaloth', T4],
                      forced={'Choirboy:': {'players': [C]}})
        self.drunk(A)
        self.night(2, {E: [G], F: [B, D]})
        self.assertFalse(g.g[B].alive)
        self.assertTrue(self.told(A, f'{C} is the Demon'))


class CultLeaderExamples(Batch3bExample):
    def test_cult_leader_example_1(self):
        """On day 3 the good Cult Leader, beside the good Town Crier and the evil Goblin, calls a cult and every good
        player joins: good wins (wiki: Cult Leader, example 1)."""
        g = self.game(['Cult Leader', 'Town Crier', T2, T3, 'Imp', T4, 'Goblin'])
        self.day(g, 3)
        self.join(A, B, C, D, F)
        self.claim(A, 'Cult Leader')
        self.assertEqual(g.g.winner, 'good')

    def test_cult_leader_example_2(self):
        """The Cult Leader neighbours the No Dashii; on day 2 every player joins the cult, but none is formed, the
        Cult Leader being poisoned (wiki: Cult Leader, example 2)."""
        g = self.game(['Cult Leader', 'No Dashii', T2, T3, 'Poisoner', T4])
        self.assertTrue(g.g.is_poisoned(g.g[A]))
        self.day(g, 2)
        self.join(A, B, C, D, E, F)
        self.claim(A, 'Cult Leader')
        self.assertIsNone(g.g.winner)


class SnitchExamples(Batch3bExample):
    CHARS = ['Snitch', T1, T2, 'Poisoner', 'Imp', T3, 'Spy', T4, 'Chef', 'Empath', 'Soldier']
    BLUFFS = ['Sage', 'Innkeeper', 'Golem', 'Fool', 'Monk', 'Saint', 'Flowergirl', 'Barber', 'Noble', 'Amnesiac',
              'Heretic']

    def test_snitch_example_1(self):
        """On the first night the Demon and both Minions all learn the same three characters not in play (wiki:
        Snitch, example 1)."""
        same = {'characters': ['Sage', 'Innkeeper', 'Golem']}
        g = self.dealt(self.CHARS, extra=self.BLUFFS, forced={'bluffs': same, 'Snitch:': same})
        self.assertTrue(self.intro(E, 'Sage, Innkeeper, Golem'))
        self.night(1, {D: [B]})
        for m in (D, G):
            self.assertTrue(self.told(m, 'Snitch: three characters not in play, for you to bluff: Sage, Innkeeper, '
                                         'Golem'), m)
        self.assertFalse(g.g[A].evil)

    def test_snitch_example_2(self):
        """The Demon and three Minions each learn three characters not in play, not all the same (wiki: Snitch,
        example 2). Checked: each Minion learns three of their own, none of them in play."""
        g = self.game(['Snitch', T1, 'Mastermind', 'Imp', 'Witch', 'Fearmonger', T2, T3], extra=self.BLUFFS)
        self.night(1, {E: [B], F: [B]})
        in_play = {p.character for p in g.g.players}
        for m in (C, E, F):
            told = self.told(m, 'Snitch: three characters not in play, for you to bluff: ')
            self.assertEqual(len(told), 1)
            named = told[0].split('bluff: ')[1].rstrip('.').split(', ')
            self.assertEqual(len(named), 3)
            self.assertFalse(set(named) & in_play)

    @unittest.skip('disagrees with the example: finding EC-11')
    def test_snitch_example_3(self):
        """On the fourth night the Pit-Hag creates a Snitch: every Minion learns three characters not in play (wiki:
        Snitch, example 3)."""
        g = self.game([T1, T2, T3, 'Pit-Hag', 'Imp', T4, 'Spy'], extra=['Snitch'] + self.BLUFFS)
        self.day(g, 3)
        self.night(4, {D: ([A], 'Snitch'), E: [B]})
        self.assertEqual(g.g[A].character, 'Snitch')
        for m in (D, G):
            self.assertTrue(self.told(m, 'Snitch: three characters not in play'), m)


class LordOfTyphonExamples(Batch3bExample):
    def line(self, g):
        from clocktower import carousel4
        lot = g.g.with_character('Lord of Typhon')
        return carousel4.typhon_line(g.g, lot)

    def test_lord_of_typhon_example_1(self):
        """The Organ Grinder and the Mezepheles sit either side of the Lord of Typhon; the Outsiders are as usual
        (wiki: Lord of Typhon, example 1)."""
        from clocktower.state import setup_error
        chars = [T1, 'Organ Grinder', T2, 'Lord of Typhon', T3, 'Mezepheles', T4, 'Monk']
        g = self.dealt(chars)
        self.assertTrue(self.line(g))
        self.assertIsNone(setup_error(chars, g.script))

    def test_lord_of_typhon_example_2(self):
        """The Vizier, the Harpy, the Lord of Typhon and the Goblin sit in a line, in a ten-player game with two
        Outsiders, brought by the Lord of Typhon (wiki: Lord of Typhon, example 2)."""
        from clocktower.state import setup_error
        chars = ['Vizier', 'Harpy', 'Lord of Typhon', 'Goblin', T1, T2, T3, T4, 'Saint', O1]
        g = self.dealt(chars)
        self.assertTrue(self.line(g))
        self.assertIsNone(setup_error(chars, g.script))

    def test_lord_of_typhon_example_3(self):
        """Fifteen players, five evil in a line (the Fearmonger, the Boomdandy, the Lord of Typhon, the Poisoner, the
        Mastermind) and no Outsiders: the Lord of Typhon removed one and the other became a Minion on the first night
        (wiki: Lord of Typhon, example 3). How the Puzzlemaster became the Boomdandy the example does not say; checked:
        such a line, with one Outsider left by the Lord of Typhon, is dealt."""
        from clocktower.state import setup_error
        chars = ['Fearmonger', 'Boomdandy', 'Lord of Typhon', 'Poisoner', 'Mastermind', T1, T2, T3, T4, 'Monk', 'Chef',
                 'Empath', 'Mayor', 'Soldier', 'Puzzlemaster']
        g = self.dealt(chars, extra=['Sage', 'Innkeeper', 'Golem', 'Saint'])
        self.assertTrue(self.line(g))
        self.assertIsNone(setup_error(chars, g.script))


class LleechExamples(Batch3bExample):
    def test_lleech_example_1(self):
        """The Lleech's host is the Noble, who learns false information; the Lleech is executed and lives; the next day
        the Noble is executed, and both die: good wins (wiki: Lleech, example 1)."""
        g = self.game(['Noble', T2, T3, 'Poisoner', 'Lleech', T4])
        self.night(1, {D: [C], E: [A]})
        self.assertTrue(g.g.is_poisoned(g.g[A]))
        self.assertTrue(g.g.unreliable(g.g[A], 'Noble'))
        self.day(g, 1)
        g.execute(E)
        self.assertTrue(g.g[E].alive)
        self.day(g, 2)
        g.execute(A)
        self.assertEqual(self.alive(A, E), [False, False])
        self.assertEqual(g.g.winner, 'good')

    def test_lleech_example_2(self):
        """The Lleech's host is the Farmer; the Courtier makes the Lleech drunk; the Farmer dies and the game goes on;
        the drunk Lleech is executed and dies: good wins (wiki: Lleech, example 2)."""
        g = self.game(['Farmer', 'Courtier', T3, 'Poisoner', 'Lleech', T4])
        self.night(1, {D: [C], E: [A], B: ([], 'Lleech')})
        self.assertTrue(g.g.is_drunk(g.g[E]))
        self.day(g, 1)
        g.execute(A)
        self.assertTrue(g.g[E].alive)
        self.assertIsNone(g.g.winner)
        self.day(g, 2)
        g.execute(E)
        self.assertFalse(g.g[E].alive)
        self.assertEqual(g.g.winner, 'good')


if __name__ == '__main__':
    unittest.main()
