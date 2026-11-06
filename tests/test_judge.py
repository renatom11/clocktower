"""The Storyteller judge (judge.py), on situations with a known right ruling. Every case runs free: the rules judge,
or a model judge with a recorded answer. To add a case, describe the situation (players, characters, who said what,
who is impaired), the decision, and the answer a skilled Storyteller gives, with its source."""
import asyncio
import random
import unittest
from collections import Counter
from unittest import mock

from clocktower import judge
from clocktower.agents import ScriptedStoryteller
from clocktower.game import ALL_NAMES, Game
from clocktower.llm import Reply
from clocktower.state import Grimoire, character_choice

NAMES = ALL_NAMES[:10]


def table(chars, said=(), whispers=()):
    """A game at day 2 with these characters, after these public lines (and private whispers)."""
    g = Game({}, ScriptedStoryteller(random.Random(5)), names=NAMES, seed=5, probes=False)
    g.g = Grimoire(NAMES, chars)
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
    def test_the_judge_never_hears_whispers(self):
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


if __name__ == '__main__':
    unittest.main()
