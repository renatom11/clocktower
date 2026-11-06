"""The Storyteller judge (judge.py), on situations with a known right ruling. Every case runs free: the rules judge,
or a model judge with a recorded answer. To add a case, describe the situation (players, characters, who said what,
who is impaired), the decision, and the answer a skilled Storyteller gives, with its source."""
import asyncio
import random
import unittest
from collections import Counter
from unittest import mock

from clocktower import judge, state
from clocktower.agents import ScriptedStoryteller
from clocktower.characters import Script, rules
from clocktower.game import ALL_NAMES, Game, Night
from clocktower.llm import Reply
from clocktower.state import Grimoire, character_choice

NAMES = ALL_NAMES[:10]


def table(chars, said=(), whispers=(), script=None, seed=5):
    """A game at day 2 with these characters, after these public lines (and private whispers)."""
    names = NAMES[:len(chars)]
    kw = {'script': script} if script else {}
    g = Game({}, ScriptedStoryteller(random.Random(seed)), names=names, seed=seed, probes=False, **kw)
    g.g = Grimoire(names, chars, **kw)
    g.day, g.phase = 2, 'night'
    for who, text in said:
        g.emit('say', {'speaker': who, 'text': text})
    for who, to, text in whispers:
        g.emit('whisper', {'from': who, 'to': [to], 'text': text}, [who, to])
    return g


def run(coro):
    return asyncio.run(coro)


BASE = ['Imp', 'Poisoner', 'Scarlet Woman', 'Undertaker', 'Chef', 'Empath', 'Monk', 'Soldier', 'Mayor', 'Butler']


class CaseTests(unittest.TestCase):
    def test_a_poisoned_undertaker_sees_the_executed_imps_claim(self):
        """The Imp, claiming Washerwoman, is executed; the Scarlet Woman takes over; the Poisoner poisons the
        Undertaker to support the claim. Rulebook: support the evil players' bluffs; make poisoning harmful."""
        g = table(BASE, said=[('Alex', "I'm the Washerwoman: Gray or Harper is the Mayor."),
                              ('Drew', 'I am the Undertaker, by the way.')])
        g.g.players[0].alive = False
        g.g.alive_at_execution, g.g.executed_death = 10, 'Alex'
        g.g.change_character(g.g['Casey'], 'Imp')
        g.g.poisoned = 'Drew'
        choice = character_choice(g.g, g.g['Drew'], 'Undertaker', 'Alex')
        ranked, reason = run(judge.RulesJudge().rank(g, choice))
        self.assertEqual(ranked[0]['character'], 'Washerwoman')
        self.assertIn('claimed the Washerwoman', reason)
        g.judge = judge.RulesJudge()
        shown = Counter(run(g.decide_judged(choice))['character'] for _ in range(400))
        self.assertGreater(shown['Washerwoman'], 320)  # about 85-90%; the scripted Storyteller: about 20%
        self.assertLess(shown['Imp'], 40)

    def test_a_drunk_ravenkeeper_sees_the_barons_mayor_bluff(self):
        """Rulebook, Drunkenness and Poisoning, Tips: the drunk Ravenkeeper chooses Doug, the Baron bluffing as the
        Mayor; showing the Mayor helps the evil team."""
        chars = ['Imp', 'Baron', 'Drunk', 'Chef', 'Empath', 'Monk', 'Soldier', 'Saint', 'Recluse', 'Washerwoman']
        g = table(chars, said=[('Blair', "I'm the Mayor, so don't kill me at three.")])
        g.g['Casey'].shown = 'Ravenkeeper'
        choice = character_choice(g.g, g.g['Casey'], 'Ravenkeeper', 'Blair')
        ranked, _ = run(judge.RulesJudge().rank(g, choice))
        self.assertEqual(ranked[0]['character'], 'Mayor')

    def test_a_drunk_ravenkeeper_choosing_a_good_player_sees_an_evil_character(self):
        """Rulebook, same tip: 'If the drunk Ravenkeeper instead chooses to learn about a good player, it can be
        helpful to show an evil character token instead.'"""
        chars = ['Imp', 'Baron', 'Drunk', 'Chef', 'Empath', 'Monk', 'Soldier', 'Saint', 'Recluse', 'Washerwoman']
        g = table(chars)
        g.g['Casey'].shown = 'Ravenkeeper'
        choice = character_choice(g.g, g.g['Casey'], 'Ravenkeeper', 'Drew')  # the Chef
        ranked, _ = run(judge.RulesJudge().rank(g, choice))
        self.assertIn(ranked[0]['character'], ('Poisoner', 'Spy', 'Scarlet Woman', 'Baron', 'Imp'))
        self.assertNotIn({'character': 'Chef'}, [{'character': v['character']} for v in ranked])

    def test_the_spy_registers_as_the_character_it_claims(self):
        """Wiki, Storyteller Advice: 'If the Spy is claiming to be the Fortune Teller, and is chosen by the
        Ravenkeeper, then choose the Fortune Teller to be the good character that the Spy registers as.'"""
        chars = ['Imp', 'Spy', 'Ravenkeeper', 'Chef', 'Empath', 'Monk', 'Soldier', 'Saint', 'Mayor', 'Washerwoman']
        g = table(chars, said=[('Blair', 'I am the Fortune Teller. No on Gray and Harper.')])
        choice = character_choice(g.g, g.g['Casey'], 'Ravenkeeper', 'Blair')
        ranked, _ = run(judge.RulesJudge().rank(g, choice))
        self.assertEqual(ranked[0]['character'], 'Fortune Teller')


class JudgeTests(unittest.TestCase):
    def test_a_judge_hearing_only_what_is_said_aloud_never_hears_whispers(self):
        g = table(BASE, said=[('Alex', "I'm the Chef.")], whispers=[('Blair', 'Casey', "I'm secretly the Poisoner")])
        record = '\n'.join(judge.public_record(g))
        self.assertIn("I'm the Chef", record)
        self.assertNotIn('secretly', record)
        self.assertEqual(judge.claims(g), {'Alex': 'Chef'})
        choice = character_choice(g.g, g.g['Drew'], 'Undertaker', 'Alex')
        self.assertNotIn('secretly', judge.prompt(g, choice))

    def test_dry_run_writes_the_prompt_and_calls_nothing(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            g = table(BASE, said=[('Alex', "I'm the Washerwoman.")])
            from pathlib import Path
            g.out = Path(d)
            g.g.poisoned = 'Drew'
            choice = character_choice(g.g, g.g['Drew'], 'Undertaker', 'Alex')
            ranked, _ = run(judge.DryRunJudge().rank(g, choice))
            line = json.loads((Path(d) / 'judge-prompts.jsonl').read_text())
            self.assertIn('Alex claims Washerwoman', line['prompt'])
            self.assertIn('Legal answers:', line['prompt'])
            self.assertEqual(ranked[0]['character'], 'Washerwoman')

    def test_a_model_judge_ranks_by_index_and_only_legal_answers_are_used(self):
        g = table(BASE, said=[('Alex', "I'm the Washerwoman.")])
        g.g.poisoned = 'Drew'
        choice = character_choice(g.g, g.g['Drew'], 'Undertaker', 'Alex')
        want = next(i for i, v in enumerate(choice.values) if v['character'] == 'Washerwoman')

        class Fake:
            async def send(self, text, meta):
                assert 'Legal answers:' in text and meta['kind'] == 'judge'
                return Reply({'ranking': [want, 999, want], 'reason': 'Alex claimed the Washerwoman aloud.'})
        with mock.patch('clocktower.llm.conversation', lambda *a, **k: Fake()):
            ranked, reason = run(judge.ModelJudge('claude-haiku-4-5').rank(g, choice))
        self.assertEqual([v['character'] for v in ranked], ['Washerwoman'])
        self.assertIn('Washerwoman', reason)
        g.judge = judge.ModelJudge('claude-haiku-4-5')
        with mock.patch('clocktower.llm.conversation', lambda *a, **k: Fake()):
            run(g.decide_judged(choice))
        ruling = [e for e in g.events if e['kind'] == 'st_choice'][-1]['data']['judge']
        self.assertEqual((ruling['mode'], ruling['ranked'][0]['character']), ('model', 'Washerwoman'))

    def test_with_no_judge_a_judged_decision_is_the_scripted_one(self):
        g = table(BASE)
        g.g.poisoned = 'Drew'
        choice = character_choice(g.g, g.g['Drew'], 'Undertaker', 'Alex')
        a = run(g.decide_judged(choice))
        g2 = table(BASE)
        g2.g.poisoned = 'Drew'
        b = g2.decide(character_choice(g2.g, g2.g['Drew'], 'Undertaker', 'Alex'))
        self.assertEqual(a, b)
        self.assertIsNone(judge.make('scripted'))



BMR = Script('bmr')
SPY = ['Imp', 'Spy', 'Virgin', 'Slayer', 'Recluse', 'Mayor', 'Empath', 'Chef', 'Monk', 'Soldier']
#       Alex   Blair  Casey     Drew      Ellis      Frankie  Gray      Harper  Indigo  Jules


class Recorder(judge.Judge):
    """A judge that records each call it is asked and has no opinion (the scripted style decides)."""
    mode = 'recorder'

    def __init__(self, wait=False):
        super().__init__('all')
        self.calls, self.wait = [], wait

    async def rank(self, game, choice):
        if self.wait:  # a judge that really waits, as a model's does
            await asyncio.sleep(0)
        self.calls.append((choice.context or {}).get('call'))
        return [], ''


def kill(g, *names):
    for n in names:
        g.g[n].alive = False


class RoutingTests(unittest.TestCase):
    """Every discretionary call reaches a judge, with its context."""

    def test_the_spy_nominating_the_virgin_reaches_the_judge(self):
        g = table(SPY)
        g.judge = Recorder()
        run(g.virgin_judged('Blair', 'Casey'))
        self.assertEqual(g.judge.calls, ['spy_virgin'])
        choice = state.virgin_choice(g.g, g.g['Casey'], g.g['Blair'])
        ctx = choice.context
        self.assertEqual((choice.id, ctx['about'], ctx['recipient'], ctx['helps']),
                         ('Virgin:Blair', 'Blair', 'Casey', 'good'))

    def test_the_slayer_shooting_the_recluse_reaches_the_judge(self):
        g = table(SPY)
        g.judge = Recorder()
        run(g.slayer_judged('Drew', 'Ellis'))
        self.assertEqual(g.judge.calls, ['recluse_slain'])

    def test_the_mayor_bounce_and_the_starpass_reach_the_judge(self):
        g = table(['Imp', 'Poisoner', 'Spy', 'Mayor', 'Chef', 'Empath', 'Monk', 'Soldier', 'Butler', 'Saint'])
        g.judge = Recorder()
        run(g.demon_attack_judged(g.g['Drew'], g.g['Alex'], Night(2)))
        night = Night(2)
        night.chosen['Alex'] = ['Alex']
        g.tonight = night
        run(rules('Imp').resolve_night(g, night))
        self.assertEqual(g.judge.calls, ['mayor_bounce', 'starpass'])

    def test_information_and_registration_reach_the_judge(self):
        g = table(SPY)
        g.judge = Recorder()
        empath = g.g['Gray']  # between Frankie (the Mayor) and Harper (the Chef): nothing misregisters
        g.g.poisoned = 'Gray'
        run(g.tell(empath, 'Empath', state.empath_choice(g.g, empath)))
        chef = g.g['Harper']  # the Spy and the Recluse may each register either way
        run(g.tell(chef, 'Chef', state.chef_choice(g.g, chef)))
        self.assertEqual(g.judge.calls, ['information', 'information'])

    def test_the_setup_calls_reach_the_judge(self):
        chars = ['Imp', 'Poisoner', 'Drunk', 'Fortune Teller', 'Chef', 'Empath', 'Monk', 'Mayor', 'Butler']
        g = Game({}, ScriptedStoryteller(random.Random(2)), names=NAMES[:9], seed=2, probes=False, characters=chars)
        g.judge = Recorder()
        run(g.setup())
        self.assertEqual(g.judge.calls, ['drunk_as', 'red_herring', 'bluffs'])

    def test_every_bad_moon_rising_setup_call_and_the_tinkers_day_reach_the_judge(self):
        chars = ['Zombuul', 'Godfather', 'Lunatic', 'Tinker', 'Grandmother', 'Pacifist', 'Sailor', 'Fool', 'Goon']
        g = Game({}, ScriptedStoryteller(random.Random(4)), names=NAMES[:9], seed=4, probes=False, characters=chars,
                 script=BMR)
        g.judge = Recorder()
        run(g.setup())
        self.assertEqual(g.judge.calls, ['pacifist_never', 'lunatic_demon', 'lunatic_minions', 'lunatic_bluffs',
                                         'grandchild', 'tinker_never', 'bluffs'])
        g.day, g.phase, g.g.notes['Tinker never'] = 1, 'day', False
        run(g.moment_judged('beat'))
        self.assertEqual(g.judge.calls[-1], 'tinker')

    def test_a_judge_that_waits_runs_through_whole_games(self):
        """The game loop awaits every judged hook: a judge that really waits (a model) never reaches a synchronous
        entry point."""
        import argparse
        from clocktower.cli import build
        for script in ('tb', 'bmr'):
            for seed in range(6):
                a = argparse.Namespace(characters=None, players='5-15', private_beats=1, public_beats=1, days=8,
                                       waves=3, probes=False, script=script, judge='scripted', judge_model=None,
                                       judge_hears='all')
                game, _ = build(a, 50 + seed, None)
                game.judge = Recorder(wait=True)
                asyncio.run(game.run())
                self.assertTrue(game.judge.calls)

    def test_a_synchronous_entry_point_refuses_a_judge_that_waits(self):
        g = table(SPY)
        g.judge = Recorder(wait=True)
        with self.assertRaises(RuntimeError):
            g.virgin('Blair', 'Casey')


class NoJudgeTests(unittest.TestCase):
    """With no judge, every routed call gives exactly today's value, with the same random draws."""

    def same(self, build):
        """build(g) -> a Choice; decided by decide() on one table and decide_judged() on an identical one."""
        a, b = table(SPY, seed=9), table(SPY, seed=9)
        va, vb = a.decide(build(a)), run(b.decide_judged(build(b)))
        self.assertEqual(va, vb)
        self.assertEqual(a.st.rng.random(), b.st.rng.random())

    def test_every_routed_choice_is_decided_as_before(self):
        g = lambda t: t.g
        builders = [
            lambda t: state.virgin_choice(g(t), g(t)['Casey'], g(t)['Blair']),
            lambda t: state.slayer_choice(g(t), g(t)['Drew'], g(t)['Ellis']),
            lambda t: state.mayor_choice(g(t), g(t)['Frankie'], g(t)['Alex']),
            lambda t: state.heir_choice(['Blair', 'Gray'], g(t)['Alex']),
            lambda t: state.red_herring_choice(g(t)),
            lambda t: state.drunk_as_choice(['Washerwoman', 'Librarian', 'Butler'], g(t)['Ellis']),
            lambda t: state.bluffs_choice(['Washerwoman', 'Librarian', 'Investigator', 'Saint'], False),
            lambda t: state.pair_choice(g(t), g(t)['Gray'], 'Washerwoman'),
            lambda t: state.pair_choice(g(t), g(t)['Gray'], 'Investigator'),
            lambda t: state.chef_choice(g(t), g(t)['Harper']),
            lambda t: state.empath_choice(g(t), g(t)['Gray']),
            lambda t: state.fortune_teller_choice(g(t), g(t)['Gray'], ['Ellis', 'Jules']),
            lambda t: character_choice(g(t), g(t)['Gray'], 'Ravenkeeper', 'Blair'),
        ]
        for build in builders:
            self.same(build)

    def test_every_routed_bad_moon_rising_choice_is_decided_as_before(self):
        from clocktower import bmr
        chars = ['Zombuul', 'Godfather', 'Lunatic', 'Tinker', 'Grandmother', 'Pacifist', 'Sailor', 'Fool', 'Gambler',
                 'Minstrel']
        for build in [lambda g: bmr.lunatic_demon_choice(g, g['Alex']),
                      lambda g: bmr.lunatic_minions_choice(g, g['Casey'], g['Alex'], 1),
                      lambda g: bmr.lunatic_bluffs_choice(g),
                      lambda g: bmr.grandchild_choice(g, g['Ellis']),
                      lambda g: bmr.tinker_choice(g, g['Drew'], 'beat')]:
            a, b = table(chars, script=BMR, seed=3), table(chars, script=BMR, seed=3)
            self.assertEqual(a.decide(build(a.g)), run(b.decide_judged(build(b.g))))
            self.assertEqual(a.st.rng.random(), b.st.rng.random())

    def test_the_synchronous_entry_points_match_the_judged_ones(self):
        a, b = table(SPY, seed=11), table(SPY, seed=11)
        a.virgin('Blair', 'Casey')
        run(b.virgin_judged('Blair', 'Casey'))
        a.slayer('Drew', 'Ellis')
        run(b.slayer_judged('Drew', 'Ellis'))
        a.demon_attack(a.g['Frankie'], a.g['Alex'], Night(2))
        run(b.demon_attack_judged(b.g['Frankie'], b.g['Alex'], Night(2)))
        strip = lambda g: [(e['kind'], e['data']) for e in g.events]
        self.assertEqual(strip(a), strip(b))
        self.assertEqual([p.alive for p in a.g.players], [p.alive for p in b.g.players])


class HearingTests(unittest.TestCase):
    WHISPERS = [('Blair', 'Casey', "I'm the Chef, honestly"), ('Drew', 'Ellis', 'secretly I am worried')]

    def test_hearing_all_includes_whispers_and_hearing_public_does_not(self):
        g = table(BASE, said=[('Alex', "I'm the Washerwoman.")], whispers=self.WHISPERS)
        self.assertIn('Blair whispers to Casey', '\n'.join(judge.record(g, 'all')))
        self.assertNotIn('whispers', '\n'.join(judge.record(g, 'public')))
        self.assertEqual(judge.claims(g, 'all'), {'Alex': 'Washerwoman', 'Blair': 'Chef'})
        self.assertEqual(judge.claims(g, 'public'), {'Alex': 'Washerwoman'})
        choice = character_choice(g.g, g.g['Drew'], 'Undertaker', 'Alex')
        heard, deaf = judge.prompt(g, choice, 'all'), judge.prompt(g, choice, 'public')
        self.assertIn('secretly I am worried', heard)
        self.assertIn('Blair told Casey they are the Chef', heard)
        self.assertNotIn('secretly', deaf)
        self.assertNotIn('Blair told', deaf)

    def test_the_rules_judge_reads_a_whispered_claim_only_when_hearing_all(self):
        """The Spy (Blair) whispered a Chef claim; the Ravenkeeper chooses them. Hearing all, the judge supports the
        bluff; hearing only what is said aloud, it doesn't know it."""
        g = table(SPY, whispers=[('Blair', 'Indigo', "Between us, I'm the Chef.")])
        choice = character_choice(g.g, g.g['Gray'], 'Ravenkeeper', 'Blair')
        ranked, reason = run(judge.RulesJudge('all').rank(g, choice))
        self.assertEqual(ranked[0]['character'], 'Chef')
        self.assertIn('Blair claimed the Chef', reason)
        self.assertEqual(run(judge.RulesJudge('public').rank(g, choice))[0], [])

    def test_the_most_recent_claim_to_anyone_counts(self):
        g = table(SPY, said=[('Blair', "I'm the Chef.")], whispers=[('Blair', 'Indigo', "Truly, I'm the Monk.")])
        self.assertEqual(judge.claims(g, 'all')['Blair'], 'Monk')
        self.assertEqual(judge.claims(g, 'public')['Blair'], 'Chef')

    def test_the_hearing_setting_reaches_the_judge_from_the_command_line(self):
        import argparse
        from clocktower.cli import build
        a = argparse.Namespace(characters=None, players='7', private_beats=1, public_beats=1, days=3, waves=3,
                               probes=False, script='bmr', judge='rules', judge_model=None, judge_hears='public')
        self.assertEqual(build(a, 1, None)[0].judge.hears, 'public')
        a.judge_hears = None  # the judge's default: hears everything
        self.assertEqual(build(a, 1, None)[0].judge.hears, 'all')
        with self.assertRaises(ValueError):
            judge.make('rules', 'nothing')


class NotesTests(unittest.TestCase):
    def test_every_character_on_each_script_has_storyteller_notes(self):
        for sid in ('tb', 'bmr'):
            sections = judge._sections(judge.NOTES / f'{sid}.md')
            self.assertEqual(set(sections), set(Script(sid).all), sid)
            self.assertTrue(all(len(v.split()) >= 30 for v in sections.values()), sid)

    def test_the_prompt_has_the_notes_for_the_characters_in_play_and_no_others(self):
        g = table(BASE, said=[('Alex', "I'm the Washerwoman.")])
        g.g.poisoned = 'Drew'
        text = judge.prompt(g, character_choice(g.g, g.g['Drew'], 'Undertaker', 'Alex'))
        self.assertIn("STORYTELLER'S NOTES", text)
        for c in BASE:
            self.assertRegex(text, rf'(?m)^{c}: ')
        for c in ('Slayer', 'Virgin', 'Spy', 'Drunk', 'Washerwoman'):  # claimed, but not in play
            self.assertNotRegex(text, rf'(?m)^{c}: ')

    def test_the_drunks_apparent_character_and_bad_moon_rising_notes_are_found(self):
        g = table(['Po', 'Godfather', 'Lunatic', 'Goon', 'Exorcist', 'Sailor', 'Fool'], script=BMR)
        notes = judge.storyteller_notes('bmr', judge.in_play(g.g))
        self.assertRegex(notes, r'(?m)^Goon: ')
        self.assertNotRegex(notes, r'(?m)^Pukka: ')
        self.assertIn('Spy: ', judge.storyteller_notes('bmr', ['Spy']))  # another script's notes, for a custom script

    def test_dry_run_prompts_carry_the_notes(self):
        import json
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            g = table(SPY, said=[('Blair', "I'm the Chef.")])
            g.out = Path(d)
            run(judge.DryRunJudge('all').rank(g, state.virgin_choice(g.g, g.g['Casey'], g.g['Blair'])))
            line = json.loads((Path(d) / 'judge-prompts.jsonl').read_text())
            self.assertEqual(line['hears'], 'all')
            self.assertRegex(line['prompt'], r'(?m)^Virgin: ')
            self.assertIn('Blair (the Spy) nominated Casey', line['prompt'])


class SummaryTests(unittest.TestCase):
    def test_the_state_of_the_game(self):
        g = table(SPY, said=[('Blair', "I'm the Chef.")], whispers=[('Ellis', 'Jules', "I am the Recluse.")])
        kill(g, 'Harper', 'Indigo')
        g.g['Indigo'].ghost_vote = False
        g.g.executions.append({'player': 'Harper', 'day': 1, 'died': True})
        g.g.death_log += [{'player': 'Harper', 'cause': 'execution', 'day': 1, 'phase': 'nominations'},
                          {'player': 'Indigo', 'cause': 'demon', 'day': 2, 'phase': 'night'}]
        g.g.nominations.append({'day': 1, 'nominator': 'Jules', 'nominee': 'Harper', 'votes': 5, 'outcome': 'block'})
        text = judge.summary(g, 'all')
        self.assertIn('Alive (8)', text)
        self.assertIn('Dead (2): Harper, Indigo. Ghost votes left: Harper.', text)
        self.assertIn('Blair claims Chef', text)
        self.assertIn('Ellis told Jules they are the Recluse', text)
        self.assertIn('Executions: day 1 Harper.', text)
        self.assertIn('Indigo (day 2, night, demon)', text)
        self.assertIn('day 1 Jules nominated Harper: 5 votes (block)', text)
        self.assertIn('Who is ahead: close', text)
        self.assertNotIn('Ellis told', judge.summary(g, 'public'))

    def test_who_is_ahead(self):
        g = table(SPY)
        self.assertEqual(judge.standing(g)[0], 'close')
        kill(g, 'Blair')  # the Spy is dead, nine alive
        self.assertEqual(judge.standing(g)[0], 'good')
        g = table(SPY)
        kill(g, 'Casey', 'Drew', 'Ellis', 'Frankie')  # four good players dead, no evil
        self.assertEqual(judge.standing(g)[0], 'evil')
        g = table(SPY)
        kill(g, *[n for n in NAMES if n not in ('Alex', 'Blair', 'Casey')])
        g.g['Blair'].alive = False
        self.assertEqual(judge.standing(g), ('evil', 'only 2 players live, the Demon among them'))
        g = table(SPY)
        g.g.nominations.append({'day': 2, 'nominator': 'Jules', 'nominee': 'Alex', 'votes': 6, 'outcome': 'block'})
        self.assertEqual(judge.standing(g)[0], 'good')


class HeuristicTests(unittest.TestCase):
    """The rules judge's rankings for the new calls (RulesJudge's docstring lists them)."""

    def rank(self, g, choice, hears='all'):
        return run(judge.RulesJudge(hears).rank(g, choice))

    def test_a_spy_claiming_a_townsfolk_dies_to_the_virgin(self):
        g = table(SPY, said=[('Blair', "I'm the Chef, and I nominate the Virgin to prove it.")])
        ranked, reason = self.rank(g, state.virgin_choice(g.g, g.g['Casey'], g.g['Blair']))
        self.assertEqual(ranked[0], {'players': [], 'character': None, 'number': None, 'yes': True, 'characters': []})
        self.assertIn('honours the Virgin', reason)
        g.judge = judge.RulesJudge()
        executed = 0
        for seed in range(100):
            t = table(SPY, said=[('Blair', "I'm the Chef.")], seed=seed)
            t.judge = judge.RulesJudge()
            executed += run(t.virgin_judged('Blair', 'Casey'))
        self.assertGreater(executed, 75)  # the scripted Storyteller: 20%

    def test_a_spy_claiming_an_outsider_does_not_die_to_the_virgin(self):
        g = table(SPY, said=[('Blair', "I'm the Butler.")])
        ranked, _ = self.rank(g, state.virgin_choice(g.g, g.g['Casey'], g.g['Blair']))
        self.assertIs(ranked[0]['yes'], False)

    def test_an_unclaimed_spy_and_the_virgin_go_by_balance(self):
        g = table(SPY)
        self.assertEqual(self.rank(g, state.virgin_choice(g.g, g.g['Casey'], g.g['Blair']))[0], [])
        kill(g, 'Casey', 'Drew', 'Ellis', 'Frankie')  # evil far ahead: the Spy's execution helps good
        ranked, reason = self.rank(g, state.virgin_choice(g.g, g.g['Casey'], g.g['Blair']))
        self.assertIs(ranked[0]['yes'], True)
        self.assertIn('evil is well ahead', reason)

    def test_the_slayer_kills_the_recluse_only_when_good_is_far_ahead(self):
        g = table(SPY)
        choice = lambda: state.slayer_choice(g.g, g.g['Drew'], g.g['Ellis'])
        self.assertEqual(self.rank(g, choice())[0], [])  # close: the scripted weight
        kill(g, 'Blair')
        ranked, reason = self.rank(g, choice())
        self.assertIs(ranked[0]['yes'], True)
        self.assertIn('good is well ahead', reason)
        g = table(SPY)
        kill(g, 'Casey', 'Gray', 'Harper', 'Frankie')
        self.assertIs(self.rank(g, state.slayer_choice(g.g, g.g['Drew'], g.g['Ellis']))[0][0]['yes'], False)

    def test_the_mayor_bounce_follows_the_balance(self):
        g = table(SPY)
        self.assertEqual(self.rank(g, state.mayor_choice(g.g, g.g['Frankie'], g.g['Alex']))[0], [])
        kill(g, 'Blair')
        self.assertEqual(self.rank(g, state.mayor_choice(g.g, g.g['Frankie'], g.g['Alex']))[0][0]['players'],
                         ['Frankie'])
        g = table(SPY)
        kill(g, 'Casey', 'Drew', 'Ellis', 'Indigo')
        ranked, _ = self.rank(g, state.mayor_choice(g.g, g.g['Frankie'], g.g['Alex']))
        self.assertEqual(ranked[0]['players'], ['Gray'])  # clockwise from the Mayor, a good player
        self.assertNotIn(['Blair'], [v['players'] for v in ranked])

    def test_the_starpass_goes_to_the_minion_with_a_good_claim(self):
        chars = ['Imp', 'Poisoner', 'Spy', 'Baron', 'Chef', 'Empath', 'Monk', 'Soldier', 'Saint', 'Butler']
        g = table(chars, said=[('Drew', "I'm the Recluse.")])
        g.g.nominations.append({'day': 1, 'nominator': 'Ellis', 'nominee': 'Blair', 'votes': 4, 'outcome': 'block'})
        ranked, _ = self.rank(g, state.heir_choice(['Blair', 'Casey', 'Drew'], g.g['Alex']))
        self.assertEqual([v['players'][0] for v in ranked], ['Drew', 'Casey', 'Blair'])

    def test_the_pacifist_and_the_tinker_help_the_team_behind(self):
        from clocktower import bmr
        chars = ['Po', 'Godfather', 'Pacifist', 'Tinker', 'Sailor', 'Fool', 'Gambler']
        g = table(chars, script=BMR)
        kill(g, 'Ellis', 'Frankie')  # evil far ahead
        self.assertIs(self.rank(g, bmr.pacifist_choice(g.g, g.g['Casey'], g.g['Gray']))[0][0]['yes'], True)
        self.assertIs(self.rank(g, bmr.tinker_choice(g.g, g.g['Drew'], 'night'))[0][0]['yes'], False)
        g = table(chars, script=BMR)
        kill(g, 'Blair')  # good far ahead
        self.assertIs(self.rank(g, bmr.pacifist_choice(g.g, g.g['Casey'], g.g['Gray']))[0][0]['yes'], False)
        self.assertIs(self.rank(g, bmr.tinker_choice(g.g, g.g['Drew'], 'night'))[0][0]['yes'], True)

    def test_the_gossip_victim_and_the_regurgitation_follow_the_balance(self):
        from clocktower import bmr
        chars = ['Shabaloth', 'Godfather', 'Gossip', 'Tinker', 'Sailor', 'Fool', 'Gambler', 'Chambermaid']
        g = table(chars, script=BMR)
        kill(g, 'Blair')
        ranked, _ = self.rank(g, bmr.gossip_victim_choice(g.g, g.g['Casey']))
        self.assertTrue(ranked and all(not g.g[v['players'][0]].evil for v in ranked))
        self.assertNotIn(['Frankie'], [v['players'] for v in ranked])  # the Fool would not die
        g = table(chars, script=BMR)
        kill(g, 'Drew', 'Ellis', 'Gray', 'Harper')
        ranked, _ = self.rank(g, bmr.regurgitation_choice(g.g, g.g['Alex'], ['Drew', 'Ellis']))
        self.assertEqual(ranked[0]['players'], ['Drew'])

    def test_setup_calls_have_no_opinion(self):
        g = table(SPY)
        for choice in (state.red_herring_choice(g.g), state.drunk_as_choice(['Washerwoman', 'Librarian']),
                       state.bluffs_choice(['Washerwoman', 'Librarian', 'Investigator', 'Saint'], False)):
            self.assertEqual(self.rank(g, choice), ([], ''))

    def test_a_long_list_of_answers_is_shortened_for_a_model(self):
        g = table(BASE)
        g.g.poisoned = 'Drew'
        p = g.g['Drew']
        choice = state.pair_choice(g.g, p, 'Washerwoman')
        before = (dict(g.g.truthful), dict(g.g.decoys), g.st.rng.getstate())
        values = judge.shortlist(g, choice, judge.RulesJudge().ranking(g, choice)[0])
        self.assertEqual(len(values), judge.SHORTLIST)
        self.assertTrue(all(choice.legal(v) for v in values))
        self.assertEqual(len({state._key(v) for v in values}), len(values))  # distinct, in any order
        self.assertEqual(before, (dict(g.g.truthful), dict(g.g.decoys), g.st.rng.getstate()))
        self.assertIn('(A shortlist of 40 of the', judge.prompt(g, choice, 'all', values))

if __name__ == '__main__':
    unittest.main()
