"""Custom scripts and the experimental ("carousel") characters: loading real custom scripts, the jinx framework and
the jinxes between built characters, the custom-script player prompt, and smoke runs of the synthetic and corpus
scripts (docs/carousel-rulings.md).

The World Championship corpus is read from $CLOCKTOWER_SCRIPTS (default: the wc25 directory); the tests that need it
are skipped when it is absent. It is never committed."""
import asyncio
import io
import json
import random
import tempfile
import unittest
from pathlib import Path

from clocktower import characters as ch
from clocktower import carousel_extra, official, prompts, smoke
from clocktower.agents import ScriptedStoryteller
from clocktower.game import ALL_NAMES, NAMES, Game
from clocktower.llm import Reply
from clocktower.snv import sage_choice
from clocktower.state import POLICY, Grimoire, State, random_setup

A, B, C, D, E, F, G, H, I = NAMES
BLANK = {'say': '', 'whispers': [], 'nominate': None, 'vote': None, 'targets': []}
BASE = ('tb', 'bmr', 'snv')
JINXES = [('Mastermind', 'Vigormortis'), ('Mathematician', 'Chambermaid'), ('Mathematician', 'Drunk'),
          ('Mathematician', 'Lunatic'), ('Pit-Hag', 'Goon'), ('Recluse', 'Sage'), ('Scarlet Woman', 'Fang Gu')]
# batch 1's (tests/test_carousel1.py)
JINXES1 = [('Al-Hadikhia', 'Mastermind'), ('Magician', 'Spy'), ('Pit-Hag', 'Damsel'), ('Pit-Hag', 'Politician'),
           ('Plague Doctor', 'Baron'), ('Plague Doctor', 'Evil Twin'), ('Plague Doctor', 'Scarlet Woman'),
           ('Plague Doctor', 'Spy'), ('Scarlet Woman', 'Al-Hadikhia'), ('Spy', 'Damsel'), ('Summoner', 'Clockmaker'),
           ('Summoner', 'Courtier'), ('Summoner', 'Hatter'), ('Summoner', 'Pit-Hag'), ('Summoner', 'Pukka'),
           ('Summoner', 'Zombuul'), ('Vortox', 'Banshee')]
# batch 2's (tests/test_carousel2.py)
JINXES2 = [('Cannibal', 'Butler'), ('Cannibal', 'Juggler'), ('Cerenovus', 'Goblin'), ('Heretic', 'Baron'),
           ('Heretic', 'Godfather'), ('Heretic', 'Pit-Hag'), ('Heretic', 'Spy'), ('Heretic', 'Widow'),
           ('Leviathan', 'Banshee'), ('Leviathan', 'Exorcist'), ('Leviathan', 'Grandmother'), ('Leviathan', 'Hatter'),
           ('Leviathan', 'Innkeeper'), ('Leviathan', 'Mayor'), ('Leviathan', 'Monk'), ('Leviathan', 'Pit-Hag'),
           ('Leviathan', 'Ravenkeeper'), ('Leviathan', 'Sage'), ('Leviathan', 'Soldier'), ('Magician', 'Marionette'),
           ('Magician', 'Widow'), ('Marionette', 'Balloonist'), ('Marionette', 'Kazali'), ('Marionette', 'Summoner'),
           ('Mathematician', 'Marionette'), ('Plague Doctor', 'Goblin'), ('Plague Doctor', 'Marionette'),
           ('Spy', 'Poppy Grower'), ('Summoner', 'Kazali'), ('Summoner', 'Poppy Grower'), ('Summoner', 'Preacher'),
           ('Widow', 'Damsel'), ('Widow', 'Poppy Grower')]
# batch 3's (tests/test_carousel3.py)
JINXES3 = [('Alchemist', 'Boffin'), ('Alchemist', 'Marionette'), ('Alchemist', 'Mastermind'),
           ('Alchemist', 'Organ Grinder'), ('Alchemist', 'Spy'), ('Alchemist', 'Summoner'), ('Alchemist', 'Widow'),
           ('Boffin', 'Drunk'), ('Boffin', 'Goon'), ('Boffin', 'Heretic'), ('Boffin', 'Politician'),
           ('Boffin', 'Village Idiot'), ('Butler', 'Organ Grinder'), ('Cannibal', 'Zealot'), ('Leviathan', 'Farmer'),
           ('Pit-Hag', 'Village Idiot'), ('Plague Doctor', 'Boomdandy'), ('Plague Doctor', 'Fearmonger')]
# batch 3b's (tests/test_carousel3b.py)
JINXES4 = [('Boffin', 'Cult Leader'), ('Heretic', 'Lleech'), ('Leviathan', 'King'), ('Lleech', 'Mastermind'),
           ('Lleech', 'Slayer'), ('Marionette', 'Huntsman'), ('Pit-Hag', 'Cult Leader'), ('Summoner', 'Lord of Typhon')]
# batch 4's (tests/test_carousel4.py)
JINXES5 = [('Alchemist', 'Wraith'), ('Al-Hadikhia', 'Princess'), ('Boffin', 'Ogre'), ('Bounty Hunter', 'Kazali'),
           ('Bounty Hunter', 'Philosopher'), ('Cannibal', 'Princess'), ('Magician', 'Vizier'), ('Magician', 'Wraith'),
           ('Pit-Hag', 'Ogre'), ('Plague Doctor', 'Wraith'), ('Recluse', 'Ogre'), ('Spy', 'Ogre'),
           ('Summoner', 'Engineer'), ('Vizier', 'Alsaahir'), ('Vizier', 'Courtier'), ('Vizier', 'Fearmonger'),
           ('Vizier', 'Investigator'), ('Vizier', 'Politician'), ('Vizier', 'Preacher'), ('Vizier', 'Zealot')]
# batch 5's (tests/test_carousel5.py)
JINXES6 = [('Yaggababble', 'Exorcist')]


def run(coro):
    return asyncio.run(coro)


def corpus():
    """The corpus scripts' paths, or skip."""
    paths = sorted(smoke.corpus_dir().glob('*/script.json'))
    if not paths:
        raise unittest.SkipTest(f'no custom script corpus at {smoke.corpus_dir()} (set CLOCKTOWER_SCRIPTS)')
    return paths


def write(d, entries, name='mine.json'):
    path = Path(d) / name
    path.write_text(json.dumps(entries))
    return path


class Town(ch.Townsfolk):
    name = 'Carousel Town'


class Town2(Town):
    name = 'Carousel Town 2'


class Town3(Town):
    name = 'Carousel Town 3'


class Town4(Town):
    name = 'Carousel Town 4'


class Out(ch.Outsider):
    name = 'Carousel Out'


FILLERS = [Town, Town2, Town3, Town4, Out]
T1, T2, T3, T4, O1 = (c.name for c in FILLERS)


class Seat:
    """Answers night requests from {night: answer}; a re-ask (an illegal or missing required choice) gets a legal
    default; day requests get no action."""

    def __init__(self):
        self.answers = {}

    async def act(self, text, request):
        if request.prompt.startswith('(That is not a legal choice'):
            need = request.n_targets if request.min_targets is None else request.min_targets
            return Reply({**BLANK, 'targets': request.options[:need],
                          'character': request.characters[0] if request.characters else None})
        if request.kind == 'night':
            return Reply({**BLANK, **self.answers.get(request.day, {})})
        return Reply({**BLANK, 'vote': False})


class Forced(ScriptedStoryteller):
    """The scripted Storyteller, except for the choices given: {choice id prefix: value}."""

    def __init__(self, forced=None):
        super().__init__(random.Random(1))
        self.forced = forced or {}

    def choose(self, choice):
        for prefix, value in self.forced.items():
            if choice.id.startswith(prefix):
                return value
        return super().choose(choice)


# ---- Loading custom scripts ------------------------------------------------------------------------------------

class ScriptLoadingTests(unittest.TestCase):
    def test_the_base_scripts_load_as_before(self):
        for sid in BASE:
            s = ch.Script(sid)
            name, names = official.script(sid)
            self.assertEqual((s.name, sorted(s.all)), (name, sorted(names)), sid)
            self.assertEqual((s.travellers, s.fabled, s.loric, s.jinxes), ([], [], [], {}), sid)
            self.assertNotIn('not in play in this engine', s.sheet())
            self.assertEqual(s.first_night, ch.after(official.night_order(s.all, True)))
        self.assertEqual(ch.Script('tb').batched_night, True)
        self.assertEqual(ch.Script('snv').batched_night, False)

    def test_odd_ids_travellers_fabled_loric_and_homebrew_ones_are_kept_but_not_in_play(self):
        """Ids match ignoring case and punctuation; an object naming an official id is that character. Travellers,
        Fabled and Loric (official or homebrew) are listed, noted on the sheet, never dealt or woken."""
        with tempfile.TemporaryDirectory() as d:
            path = write(d, [{'id': '_meta', 'name': 'Odd'}, 'Washer_Woman', 'fortune-teller', {'id': 'EMPATH'},
                             'monk', 'soldier', 'slayer', 'Drunk', 'poisoner', {'id': 'imp', 'name': 'ignored'},
                             'gnome', 'scapegoat', 'djinn', 'bootlegger',
                             {'id': 'odd-rule', 'name': 'House Rule', 'team': 'fabled', 'ability': 'Something.'}])
            s = ch.Script(path)
        self.assertEqual(s.townsfolk, ['Washerwoman', 'Fortune Teller', 'Empath', 'Monk', 'Soldier', 'Slayer'])
        self.assertEqual((s.outsiders, s.minions, s.demons), (['Drunk'], ['Poisoner'], ['Imp']))
        self.assertEqual((s.travellers, s.fabled, s.loric), (['Gnome', 'Scapegoat'], ['Djinn', 'House Rule'],
                                                             ['Bootlegger']))
        sheet = s.sheet()
        self.assertIn('Travellers (not in play in this engine): Gnome, Scapegoat', sheet)
        self.assertIn('Fabled (not in play in this engine): Djinn, House Rule', sheet)
        self.assertIn('Loric (not in play in this engine): Bootlegger', sheet)
        others = {'Gnome', 'Scapegoat', 'Djinn', 'House Rule', 'Bootlegger'}
        self.assertFalse(others & set(s.first_night + s.other_nights + s.all))
        rng = random.Random(4)
        for n in (5, 7, 8):
            self.assertFalse(others & set(random_setup(rng, players=n, script=s)))

    def test_a_homebrew_player_character_is_not_built_even_with_an_official_name(self):
        with tempfile.TemporaryDirectory() as d:
            path = write(d, ['washerwoman', 'imp', {'id': 'hunt-witch', 'name': 'Witch', 'team': 'minion',
                                                     'ability': 'Each night, choose a player.'}])
            with self.assertRaises(ValueError) as e:
                ch.Script(path)
        self.assertIn('not implemented yet: Witch (homebrew: hunt-witch)', str(e.exception))

    def test_an_id_that_is_neither_official_nor_defined_is_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError) as e:
                ch.Script(write(d, ['washerwoman', 'imp', 'nosuchcharacter', {'id': 'nameless', 'team': 'minion'}]))
        self.assertIn("not in the official data: ['nosuchcharacter', 'nameless']", str(e.exception))

    def test_every_corpus_script_loads_up_to_its_unbuilt_characters(self):
        for path in corpus():
            try:
                s = ch.Script(path)
            except ValueError as e:
                self.assertIn('characters not implemented yet', str(e), path)
                continue
            self.assertTrue(s.demons and s.minions, path)


# ---- The jinx framework ----------------------------------------------------------------------------------------

class JinxFrameworkTests(unittest.TestCase):
    def test_no_jinx_is_in_effect_on_the_base_scripts(self):
        for sid in BASE:
            s = ch.Script(sid)
            self.assertEqual(s.jinxes, {}, sid)
            self.assertFalse([p for p in official.jinxes() if s.jinxed(*p)], sid)
            self.assertNotIn('Jinx', s.sheet())

    def test_every_official_jinx_between_built_characters_is_implemented(self):
        built = {frozenset(p) for p in official.jinxes() if set(p) <= set(ch.CHARACTERS)}
        self.assertEqual(built, set(ch.IMPLEMENTED_JINXES))
        self.assertEqual(built, {frozenset(p) for p in JINXES + JINXES1 + JINXES2 + JINXES3 + JINXES4 + JINXES5
                                                 + JINXES6 + carousel_extra.JINXES})
        with self.assertRaises(ValueError):
            ch.jinx('Imp', 'Washerwoman', 'nowhere')

    def test_script_of_takes_jinxes_and_the_sheet_shows_only_those_on_the_script(self):
        s = ch.Script.of('t', ['Mathematician', 'Drunk', 'Imp'], jinxes=[('Mathematician', 'Drunk')])
        self.assertTrue(s.jinxed('Mathematician', 'Drunk') and s.jinxed('Drunk', 'Mathematician'))
        self.assertFalse(s.jinxed('Mathematician', 'Lunatic'))
        self.assertEqual(s.sheet().count('Jinx'), 1)
        own = ch.Script.of('t', ['Imp', 'Drunk'], jinxes={('Imp', 'Drunk'): 'A test jinx.'})
        self.assertTrue(own.jinxed('Drunk', 'Imp'))
        self.assertIn('Jinx, Imp and Drunk: A test jinx.', own.sheet())
        self.assertFalse(ch.Script.of('t', ['Mathematician', 'Drunk', 'Imp']).jinxed('Mathematician', 'Drunk'))
        with tempfile.TemporaryDirectory() as d:
            s = ch.Script(write(d, ['mathematician', 'drunk', 'chambermaid', 'poisoner', 'imp']))
        self.assertTrue(s.jinxed('Drunk', 'Mathematician') and s.jinxed('Chambermaid', 'Mathematician'))
        self.assertFalse(s.jinxed('Lunatic', 'Mathematician'))
        self.assertEqual(s.sheet().count('Jinx,'), 2)

    def test_the_synthetic_script_holds_all_seven(self):
        s = ch.Script('carousel-1')
        self.assertTrue(all(s.jinxed(a, b) for a, b in JINXES))
        self.assertEqual(s.sheet().count('Jinx,'), 7)
        for n in range(5, 16):  # dealable at every size
            for seed in range(20):
                self.assertEqual(len(random_setup(random.Random(seed), players=n, script=s)), n)


# ---- The jinxes ------------------------------------------------------------------------------------------------

class JinxTest(unittest.TestCase):
    """Games on a test script of the characters given (plus fillers), with or without the jinxes in effect."""

    @classmethod
    def setUpClass(cls):
        for c in FILLERS:
            ch.CHARACTERS[c.name] = c()

    @classmethod
    def tearDownClass(cls):
        for c in FILLERS:
            del ch.CHARACTERS[c.name]

    def script(self, chars, jinxed):
        real = [c for c in dict.fromkeys(chars) if c not in {f.name for f in FILLERS}]
        on = [p for p in JINXES + JINXES1 + JINXES2 + JINXES3 + JINXES4 + JINXES5 + JINXES6 + carousel_extra.JINXES
              if set(p) <= set(real)] if jinxed else []
        return ch.Script.of('carousel-test', [f.name for f in FILLERS] + real, official.night_order(real, True),
                            official.night_order(real, False), jinxes=on)

    def game(self, chars, jinxed=True, forced=None, extra=()):
        """A game with the Grimoire dealt as given (seat order), at day 1."""
        names = ALL_NAMES[:len(chars)]
        script = self.script(list(chars) + list(extra), jinxed)
        self.seats = {n: Seat() for n in names}
        g = Game(self.seats, Forced(forced), names=names, seed=3, characters=chars, script=script, probes=False,
                 private_beats=1, public_beats=1)
        g.g = Grimoire(names, chars, script=script)
        g.day, g.phase, g.g.day = 1, 'day', 1
        self.g = g
        return g

    def dealt(self, chars, jinxed=True, forced=None, extra=()):
        """A game set up as a real one is (the characters' setup steps), seat order kept."""
        names = NAMES[:len(chars)]
        script = self.script(list(chars) + list(extra), jinxed)
        self.seats = {n: Seat() for n in names}
        g = Game(self.seats, Forced(forced), names=names, seed=3, characters=chars, script=script, probes=False,
                 private_beats=1, public_beats=1)
        run(g.setup())
        self.g = g
        return g

    def choose(self, night, name, targets=(), character=None):
        self.seats[name].answers[night] = {'targets': list(targets), 'character': character}

    def day(self, g, n):
        g.day, g.phase, g.g.day = n, 'day', n

    def told(self, name, text):
        return [e['data']['text'] for e in self.g.events if e['to'] == [name] and e['kind'] in ('info', 'notice')
                and text in e['data'].get('text', '')]

    def both(self):
        return (True, False)


class MastermindVigormortisTests(JinxTest):
    CHARS = [T1, T2, T3, T4, 'Mastermind', 'Vigormortis', O1]

    def test_a_mastermind_the_vigormortis_killed_keeps_their_ability_when_it_dies(self):
        """The jinx: the Vigormortis kills the Mastermind (who keeps their ability), then is executed: the
        Mastermind's extra day still happens. Without the jinx, the Mastermind's kept ability ends with the
        Vigormortis and good wins."""
        for jinxed in self.both():
            g = self.game(self.CHARS, jinxed, forced={'Vigormortis': {'players': [D]}})
            self.choose(2, F, [E])
            run(g.night(2))
            self.assertFalse(g.g[E].alive)
            self.assertTrue(g.g.works(g.g[E], 'Mastermind'))
            self.day(g, 2)
            g.execute(F)
            self.assertFalse(g.g[F].alive)
            if jinxed:
                self.assertIsNone(g.g.winner)
                self.assertTrue(g.g.works(g.g[E], 'Mastermind'))
                self.assertFalse(g.g.is_poisoned(g.g[D]))  # the Vigormortis's poison ends with it
            else:
                self.assertEqual(g.g.winner, 'good')

    def test_a_mastermind_without_their_ability_as_the_vigormortis_dies_does_not_keep_it(self):
        """"A Mastermind that has their ability": a poisoned Vigormortis's Minions have none as it dies."""
        g = self.game(self.CHARS, forced={'Vigormortis': {'players': [D]}})
        self.choose(2, F, [E])
        run(g.night(2))
        g.g.add(State('poisoned', F, source='test', until=None))
        self.day(g, 2)
        g.execute(F)
        self.assertEqual(g.g.winner, 'good')


class MathematicianChambermaidTests(JinxTest):
    CHARS = ['Chambermaid', 'Mathematician', T1, T2, T3, 'Mastermind', 'Imp']

    def test_the_chambermaid_counts_a_mathematician_who_will_wake_tonight(self):
        for jinxed, n in ((True, 1), (False, 0)):
            g = self.game(self.CHARS, jinxed)
            self.choose(1, A, [B, C])
            run(g.night(1))
            self.assertTrue(self.told(A, f'{n} of them woke tonight'), jinxed)

    def test_a_dead_mathematician_does_not_wake(self):
        g = self.game(self.CHARS)
        g.g[B].alive = False
        self.choose(1, A, [B, C])
        run(g.night(1))
        self.assertTrue(self.told(A, '0 of them woke tonight'))


class MathematicianDrunkTests(JinxTest):
    def drunk(self, shown, jinxed=True, forced=None, chars=None):
        g = self.game(chars or ['Mathematician', 'Drunk', T1, T2, T3, 'Mastermind', 'Imp'], jinxed, forced,
                      extra=[shown])
        g.g[B].shown = shown
        return g

    def test_the_drunks_false_information_counts(self):
        for jinxed, n in ((True, "1 player's"), (False, "0 players'")):
            g = self.drunk('Empath', jinxed, forced={'Empath': {'number': 2}})
            run(g.night(1))
            self.assertTrue(self.told(B, '2 of your living neighbours'))
            self.assertTrue(self.told(A, f'Mathematician: {n}'), jinxed)

    def test_true_information_for_the_drunk_does_not(self):
        g = self.drunk('Empath', forced={'Empath': {'number': 0}})
        run(g.night(1))
        self.assertTrue(self.told(A, "Mathematician: 0 players'"))

    def test_a_drunk_soldier_or_monks_protection_failing_counts(self):
        for jinxed in self.both():
            g = self.drunk('Soldier', jinxed)
            self.choose(2, G, [B])
            run(g.night(2))
            self.assertFalse(g.g[B].alive)
            self.assertEqual([a['player'] for a in g.g.abnormal], [B] if jinxed else [])
        g = self.drunk('Monk', chars=['Mathematician', 'Drunk', T1, T2, T3, 'Mastermind', 'Imp'])
        self.choose(2, B, [C])
        self.choose(2, G, [C])
        run(g.night(2))
        self.assertFalse(g.g[C].alive)
        self.assertTrue(self.told(A, "Mathematician: 1 player's"))

    def test_a_drunk_slayer_shooting_the_demon_and_a_drunk_virgin_nominated_by_a_townsfolk_count(self):
        for jinxed in self.both():
            g = self.drunk('Slayer', jinxed)
            self.assertFalse(run(ch.rules('Slayer').act_publicly(g, B, G)))
            run(ch.rules('Slayer').act_publicly(g, B, G))  # once only
            self.assertEqual([a['ability'] for a in g.g.abnormal], ['Slayer'] if jinxed else [])
            g = self.drunk('Virgin', jinxed)
            self.assertFalse(ch.rules('Drunk').nominated(g, g.g[B], C))
            self.assertFalse(ch.rules('Drunk').nominated(g, g.g[B], A))  # the first nomination only
            self.assertEqual([a['ability'] for a in g.g.abnormal], ['Virgin'] if jinxed else [])


class MathematicianLunaticTests(JinxTest):
    CHARS = ['Lunatic', 'Mathematician', T1, T2, T3, T4, 'Mastermind', 'Imp']

    def lunatic(self, jinxed=True):
        return self.dealt(self.CHARS, jinxed, extra=['Monk', 'Empath', 'Chef'],
                          forced={'Lunatic:demon': {'character': 'Imp'}, 'Lunatic:minions': {'players': [C]},
                                  'Lunatic:bluffs': {'characters': [T1, T2, 'Mathematician']}})

    def test_the_lunatic_attacking_a_different_player_than_the_demon_counts(self):
        for jinxed, lunatic, demon, n in ((True, D, E, "1 player's"), (True, E, E, "0 players'"),
                                          (False, D, E, "0 players'")):
            g = self.lunatic(jinxed)
            run(g.night(1))
            self.choose(2, A, [lunatic])
            self.choose(2, H, [demon])
            run(g.night(2))
            self.assertFalse(g.g[E].alive)
            self.assertTrue(self.told(B, f'Mathematician: {n}'), (jinxed, lunatic))


class PitHagGoonTests(JinxTest):
    CHARS = ['Monk', T1, T2, T3, T4, 'Pit-Hag', 'Scarlet Woman', 'Imp']

    def test_an_evil_player_the_pit_hag_made_the_goon_cannot_turn_good_by_it(self):
        """The jinx: the Pit-Hag turns the Scarlet Woman into the Goon; the Monk then chooses the Goon, and is drunk,
        but the Goon stays evil. Without the jinx, the Goon turns good."""
        for jinxed in self.both():
            g = self.game(self.CHARS, jinxed, extra=['Goon'])
            self.choose(2, A, [B])
            self.choose(2, F, [G], 'Goon')
            self.choose(2, H, [C])
            run(g.night(2))
            self.assertEqual((g.g[G].character, g.g[G].alignment), ('Goon', 'evil'))
            self.choose(3, A, [G])
            self.choose(3, F, [B], 'Monk')  # in play: nothing happens
            self.choose(3, H, [D])
            run(g.night(3))
            self.assertTrue(g.g.has(g.g[A], 'drunk'))
            self.assertEqual(g.g[G].alignment, 'evil' if jinxed else 'good')

    def test_the_goon_still_turns_evil_and_a_good_player_made_the_goon_is_free(self):
        g = self.game(self.CHARS, extra=['Goon'])
        self.choose(2, A, [C])
        self.choose(2, F, [B], 'Goon')
        self.choose(2, H, [C])
        run(g.night(2))
        self.choose(3, A, [D])
        self.choose(3, F, [D], 'Monk')
        self.choose(3, H, [B])  # the Imp chooses the Goon first: the Goon turns evil
        run(g.night(3))
        self.assertEqual((g.g[B].character, g.g[B].alignment), ('Goon', 'evil'))
        self.assertNotIn(B, g.g.notes.get('Evil Goons', []))


class RecluseSageTests(JinxTest):
    CHARS = ['Sage', T1, 'Recluse', T3, 'Mastermind', 'Fang Gu', T4]

    def picks(self, g, seeds=400):
        return [sage_choice(g.g, g.g[A], F).options(random.Random(i))['players'] for i in range(seeds)]

    def test_the_recluse_may_register_as_the_demon_to_the_sage(self):
        g = self.game(self.CHARS)
        picks = self.picks(g)
        recluse = [v for v in picks if F not in v]
        self.assertTrue(all(C in v and A not in v for v in recluse))
        self.assertAlmostEqual(len(recluse) / len(picks), POLICY['sage_shows_recluse'], delta=0.07)
        choice = sage_choice(g.g, g.g[A], F)
        self.assertTrue(choice.truth({'players': [C, B]}) and not choice.truth({'players': [B, D]}))
        self.choose(2, F, [A])
        g.st.forced = {'Sage': {'players': [C, B]}}
        run(g.night(2))
        self.assertTrue(self.told(A, f'the Demon who killed you is {B} or {C}'))
        self.assertEqual(g.g.abnormal, [])  # a true result: the Recluse registered

    def test_not_without_the_jinx_nor_a_poisoned_recluse(self):
        g = self.game(self.CHARS, jinxed=False)
        self.assertTrue(all(F in v for v in self.picks(g, 100)))
        g = self.game(self.CHARS)
        g.g.add(State('poisoned', C, source='test', until=None))
        self.assertTrue(all(F in v for v in self.picks(g, 100)))


class ScarletWomanFangGuTests(JinxTest):
    CHARS = [T1, T2, O1, T3, 'Scarlet Woman', 'Fang Gu', T4]

    def test_the_scarlet_woman_stays_herself_when_the_fang_gu_jumps(self):
        """The jinx: the Fang Gu jumps into the Outsider and dies with seven alive; there would be two Demons, so the
        Scarlet Woman remains the Scarlet Woman. Without it, she becomes a second Fang Gu."""
        for jinxed in self.both():
            g = self.game(self.CHARS, jinxed)
            self.choose(2, F, [C])
            run(g.night(2))
            self.assertEqual(g.g[C].character, 'Fang Gu')
            self.assertFalse(g.g[F].alive)
            self.assertEqual(g.g[E].character, 'Scarlet Woman' if jinxed else 'Fang Gu')

    def test_she_still_takes_over_a_fang_gu_executed(self):
        g = self.game(self.CHARS)
        g.execute(F)
        self.assertEqual(g.g[E].character, 'Fang Gu')
        self.assertIsNone(g.g.winner)


# ---- The custom-script prompt ----------------------------------------------------------------------------------

class CustomPromptTests(unittest.TestCase):
    def test_the_generic_prompt_names_the_script_and_holds_its_sheet(self):
        s = ch.Script('carousel-1')
        text = prompts.player_system(9, script=s)
        self.assertIn('using Carousel test 1, a custom script', text)
        self.assertIn(s.sheet(), text)
        self.assertNotIn('Trouble Brewing', text)
        self.assertIn('one Demon (the Imp, the Fang Gu or the Vigormortis)', text)
        self.assertIn('the Lunatic believes they are the Demon', text)
        self.assertIn('(though the Drunk may believe', text)
        self.assertIn('slayer_shot', text)  # the Slayer is on it
        for absent in ('Madness.', 'Visits to the Storyteller', '- visit:', '- ability:'):
            self.assertNotIn(absent, text)

    def test_madness_and_visits_only_when_its_characters_use_them(self):
        s = ch.Script.of('Mad visits', ['Washerwoman', 'Savant', 'Juggler', 'Mutant', 'Cerenovus', 'Imp'])
        text = prompts.player_system(7, script=s)
        self.assertIn('Madness.', text)
        self.assertIn('what you tell them on a visit', text)
        self.assertIn('Visits to the Storyteller. The Savant uses their ability', text)
        self.assertIn('- visit:', text)
        self.assertIn('- ability: to use a public day ability', text)
        self.assertIn('"guesses"', text)
        self.assertNotIn('slayer_shot', text)
        self.assertNotIn('Drunk may', text)
        plain = prompts.player_system(7, script=ch.Script.of('Plain', ['Washerwoman', 'Monk', 'Poisoner', 'Imp']))
        for absent in ('Madness.', 'Visits', 'Lunatic', 'slayer_shot', '- ability:'):
            self.assertNotIn(absent, plain)

    def test_every_generic_swap_finds_its_sentence_and_the_base_prompts_are_their_own(self):
        for old, _ in prompts.custom_text(ch.Script('carousel-1')):
            self.assertIn(old, prompts._PLAYER_SYSTEM)
        self.assertNotIn('a custom script', prompts.player_system(9))
        for sid in ('bmr', 'snv'):
            self.assertNotIn('a custom script', prompts.player_system(9, script=ch.Script(sid)))


# ---- Smoke: the synthetic script, and the corpus scripts whose characters are all built ----------------------

class SmokeTests(unittest.TestCase):
    """A small sample here; the full run (100 games per size, both Storyteller modes):
    `python -m clocktower smoke --script carousel-1` and `python -m clocktower smoke --corpus`."""

    def test_the_synthetic_script_plays_at_every_size(self):
        self.assertEqual(smoke.smoke(ch.Script('carousel-1'), games=1, out=io.StringIO()), [])

    def test_the_corpus_scripts_whose_characters_are_all_built_play(self):
        corpus()
        for path, s in smoke.corpus():
            if isinstance(s, ch.Script):
                with self.subTest(path.parent.name):
                    self.assertEqual(smoke.smoke(s, games=1, sizes=(5, 9, 12, 15), out=io.StringIO()), [])


if __name__ == '__main__':
    unittest.main()
