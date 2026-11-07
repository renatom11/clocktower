"""Batch 5 of the experimental characters (clocktower/carousel6.py): the Mezepheles, the Yaggababble and the Amnesiac,
the core hook through which abilities hear what is said, each edge their texts imply, and the official jinx between
them and a built character (the Yaggababble's with the Exorcist) (docs/carousel-rulings.md, batch 5)."""
import io
import random
import unittest

from clocktower import carousel6, judge, smoke
from clocktower import characters as ch
from clocktower.agents import RandomSeat, Request
from clocktower.game import Game, nearly_said, said, words
from clocktower.prompts import custom_text
from clocktower.state import POLICY

from test_carousel import O1, T1, T2, T3, T4, run
from test_carousel2 import A, B, C, D, E, F, G
from test_carousel4 import Batch4Test

R = ch.rules


class Low(random.Random):
    """A Storyteller rng whose draws take the judge's first choice (Game._decide_judged)."""

    def random(self):
        return 0.0


class FirstChoice(judge.Judge):
    """A judge that ranks the values it is given, in order: the first wins."""
    mode = 'test'

    def __init__(self, prefer):
        super().__init__()
        self.prefer = prefer

    async def rank(self, game, choice):
        return [v for v in choice.values if self.prefer(choice, v)], 'test'


class Batch5Test(Batch4Test):
    def whisper(self, name, to, text):
        self.g.emit('whisper', {'from': name, 'to': [to], 'text': text}, [name, to])

    def secret(self, character, name):
        return self.g.g.notes[character][name]['secret']

    def setup_step(self, character):
        run(R(character).setup(self.g))

    def with_judge(self, prefer):
        self.g.judge = FirstChoice(prefer)
        self.g.st.rng = Low()


# ---- hearing what is said ----------------------------------------------------------------------------------------

class SpeechTests(unittest.TestCase):
    def test_a_word_or_phrase_is_said_as_whole_words_whatever_the_case_or_punctuation(self):
        self.assertEqual(words("Let's be REAL -- honestly?!"), ['lets', 'be', 'real', 'honestly'])
        self.assertEqual(said('To be fair, TO BE fair... to-be-fair!', 'to be fair'), 3)
        self.assertEqual(said("Let's be real, folks", "let's be real"), 1)
        self.assertEqual(said('I trusted Alex', 'trust'), 0)  # a whole word only
        self.assertEqual(said('distrust', 'trust'), 0)
        self.assertEqual(said('be fair to be', 'to be fair'), 0)

    def test_near_misses_are_found_but_exact_sayings_are_not_near_misses(self):
        self.assertEqual(nearly_said('I trusted Alex', 'trust'), ['trusted'])
        self.assertEqual(nearly_said('honestlly, I think', 'honestly'), ['honestlly'])
        self.assertEqual(nearly_said('to be very fair', 'to be fair'), ['to be very fair'])
        self.assertEqual(nearly_said('to be fair', 'to be fair'), [])
        self.assertEqual(nearly_said('the cat sat', 'honestly'), [])

    def test_the_rules_judge_counts_another_form_of_the_word_only(self):
        rj = judge.RulesJudge()
        for form, phrase, counts in (('promised', 'promise', True), ('carefully', 'careful', True),
                                     ('honestlly', 'honestly', False), ('to be very fair', 'to be fair', False),
                                     ('theory', 'theory', True)):
            choice = carousel6.near_miss_choice(None, A, form, phrase, form, B, 'Mezepheles')
            ranked, _ = rj.ranking(None, choice)
            self.assertEqual(ranked[0]['yes'], counts, form)

    def test_no_listening_ability_no_hook_and_no_chatter(self):
        tb = ch.Script('tb')
        self.assertEqual(tb.listeners, [])
        self.assertEqual(ch.Script('carousel-6').listeners, [])
        g = Game({}, script=tb)
        self.assertEqual(g.chatter(A), [])
        self.assertEqual(Request('beat', '', 1).chatter, [])
        self.assertEqual(ch.Script('carousel-7').listeners, ['Mezepheles', 'Yaggababble'])

    def test_random_bots_draw_nothing_more_without_chatter(self):
        import asyncio
        for chatter in ([], ['Honestly, I am not sure yet.']):
            a, b = RandomSeat(A, random.Random(5), [A, B, C]), RandomSeat(A, random.Random(5), [A, B, C])
            asyncio.run(a.act('', Request('beat', '', 1, mode='public')))
            asyncio.run(b.act('', Request('beat', '', 1, mode='public', chatter=chatter)))
            self.assertEqual(a.rng.random() == b.rng.random(), not chatter)

    def test_the_prompt_explains_listening_abilities_and_never_the_secret(self):
        s = ch.Script('carousel-7')
        text = ' '.join(new for _, new in custom_text(s))
        self.assertIn('triggered by what players say (the Mezepheles and the Yaggababble)', text)
        self.assertIn('Only the player with such an ability learns its word or phrase', text)
        self.assertNotIn('triggered by what players say', ' '.join(new for _, new in custom_text(
            ch.Script('carousel-6'))))


# ---- Minions -----------------------------------------------------------------------------------------------------

class MezephelesTests(Batch5Test):
    CHARS = [T1, T2, T3, 'Mezepheles', 'Imp', T4]

    def start(self, chars=None, word='honestly', **kw):
        g = self.game(chars or self.CHARS, forced={'Mezepheles word': {'statements': [word]}}, **kw)
        self.setup_step('Mezepheles')
        self.choose(1, E, [])
        run(g.night(1))
        return g

    def night2(self):
        self.day(self.g, 1)
        self.choose(2, E, [F])
        run(self.g.night(2))

    def test_the_word_is_drawn_from_the_list_told_only_to_the_mezepheles(self):
        g = self.start()
        self.assertEqual(self.secret('Mezepheles', D), 'honestly')
        self.assertIn('honestly', carousel6.SPEECH['mezepheles_words'])
        self.assertTrue(self.told(D, 'your secret word is "honestly"'))
        self.assertFalse([e for e in g.events if e['to'] != [D] and 'honestly' in str(e['data'])
                          and e['to'] != 'audit'])

    def test_the_first_good_player_to_say_it_turns_evil_that_night_and_only_they(self):
        g = self.start()
        self.say(B, 'Honestly, I am the Chef.')
        self.say(C, 'honestly too')
        self.assertEqual(g.g[B].alignment, 'good')  # (not yet: that night)
        self.night2()
        self.assertEqual((g.g[B].alignment, g.g[C].alignment), ('evil', 'good'))
        self.assertTrue(self.told(B, 'you are now evil'))
        self.say(A, 'honestly')
        self.day(g, 2)
        self.choose(3, E, [F])
        run(g.night(3))
        self.assertEqual(g.g[A].alignment, 'good')  # spent

    def test_a_whisper_counts_an_evil_player_does_not_and_nor_does_a_near_miss(self):
        g = self.start()
        self.say(E, 'honestly')  # the Demon: evil
        self.say(A, 'I honestlyy think so')
        self.whisper(C, B, 'HONESTLY, trust me')
        self.night2()
        self.assertEqual([q.name for q in g.g.players if q.evil], [C, D, E])

    def test_a_judge_may_count_a_near_miss(self):
        g = self.start(word='promise')
        self.with_judge(lambda c, v: v.get('yes') is True or bool(v.get('players')))
        self.say(A, 'I promised nothing')
        run(g.run_pending())
        self.say(B, 'promise')
        self.night2()
        self.assertEqual(g.g[A].alignment, 'evil')
        self.assertEqual(g.g[B].alignment, 'good')

    def test_a_dead_good_player_counts_but_not_while_the_mezepheles_is_dead(self):
        g = self.start()
        g.g[A].alive = False
        self.say(A, 'honestly')
        self.night2()
        self.assertEqual(g.g[A].alignment, 'evil')
        g = self.start()
        g.g[D].alive = False
        self.say(A, 'honestly')
        self.night2()
        self.assertEqual(g.g[A].alignment, 'good')

    def test_drunk_or_poisoned_that_night_nobody_turns_and_it_is_spent(self):
        g = self.start()
        self.say(A, 'honestly')
        self.poison(D)
        self.night2()
        self.assertEqual(g.g[A].alignment, 'good')
        self.assertTrue([x for x in g.g.abnormal if x['ability'] == 'Mezepheles'])
        self.say(B, 'honestly')
        self.day(g, 2)
        self.choose(3, E, [F])
        run(g.night(3))
        self.assertEqual(g.g[B].alignment, 'good')

    def test_a_mezepheles_made_later_learns_a_new_word_at_once(self):
        g = self.game([T1, T2, T3, 'Pit-Hag', 'Imp', T4], extra=['Mezepheles'],
                      forced={'Mezepheles word': {'statements': ['gut']}})
        run(g.change(g.g[C], 'Mezepheles', 'evil'))
        self.assertTrue(self.told(C, 'your secret word is "gut"'))
        self.say(A, 'my gut says so')
        self.day(g, 1)
        self.choose(2, E, [F])
        run(g.night(2))
        self.assertEqual(g.g[A].alignment, 'evil')

    def test_reminded_of_the_word_each_dawn(self):
        self.start()
        self.night2()
        self.assertTrue(self.told(D, '(a reminder) your secret word is "honestly"'))


# ---- Demons ------------------------------------------------------------------------------------------------------

class YaggababbleTests(Batch5Test):
    CHARS = [T1, 'Monk', T3, 'Poisoner', 'Yaggababble', T4, 'Soldier']

    def start(self, chars=None, phrase='to be fair', **kw):
        g = self.game(chars or self.CHARS, forced={'Yaggababble phrase': {'statements': [phrase]}, **kw.pop(
            'forced', {})}, **kw)
        self.setup_step('Yaggababble')
        self.choose(1, D, [A])
        run(g.night(1))
        self.day(g, 1)
        return g

    def night2(self, **answers):
        for name, t in answers.items():
            self.choose(2, {'A': A, 'B': B, 'C': C, 'D': D, 'E': E}[name], t)
        run(self.g.night(2))

    def test_the_phrase_is_told_to_the_yaggababble_only(self):
        g = self.start()
        self.assertTrue(self.told(E, 'your secret phrase is "to be fair"'))
        self.assertIn('to be fair', carousel6.SPEECH['yaggababble_phrases'])
        self.assertFalse([e for e in g.events if e['to'] not in ([E], 'audit') and 'to be fair' in str(e['data'])])

    def test_each_time_it_says_it_publicly_a_player_might_die(self):
        g = self.start(forced={'Yaggababble:Ellis:1': {'players': [A]}, 'Yaggababble:Ellis:2': {'players': [C]}})
        self.say(E, 'To be fair, I think... to be fair.')
        self.night2(D=[F], B=[F])
        self.assertEqual({q.name for q in g.g.players if not q.alive}, {A, C})
        g = self.start(forced={'Yaggababble:Ellis:1': {'players': []}})
        self.say(E, 'to be fair')
        self.night2(D=[F], B=[F])
        self.assertTrue(all(q.alive for q in g.g.players))  # "might"

    def test_whispers_and_other_players_do_not_count(self):
        g = self.start()
        self.whisper(E, A, 'to be fair')
        self.say(A, 'to be fair')
        self.night2(D=[F], B=[F])
        self.assertTrue(all(q.alive for q in g.g.players))
        self.assertFalse([k for k in g.st.seen if k.startswith('Yaggababble:')])

    def test_the_monk_and_the_soldier_stop_its_kills(self):
        g = self.start(forced={'Yaggababble:Ellis:1': {'players': [A]}, 'Yaggababble:Ellis:2': {'players': [G]}})
        self.say(E, 'to be fair, to be fair')
        self.night2(D=[F], B=[A])
        self.assertTrue(g.g[A].alive and g.g[G].alive)

    def test_drunk_or_poisoned_it_kills_nobody(self):
        g = self.start(forced={'Yaggababble:Ellis': {'players': [A]}})
        self.say(E, 'to be fair')
        self.night2(D=[E], B=[F])
        self.assertTrue(g.g[A].alive)
        self.assertTrue([x for x in g.g.abnormal if x['ability'] == 'Yaggababble'])

    def test_the_exorcist_jinx_an_exorcised_yaggababble_does_not_kill(self):
        chars = [T1, 'Exorcist', T3, 'Poisoner', 'Yaggababble', T4]
        for jinxed in self.both():
            g = self.start(chars, jinxed=jinxed, forced={'Yaggababble:Ellis': {'players': [A]}})
            self.say(E, 'to be fair')
            self.night2(D=[F], B=[E])
            self.assertEqual(g.g[A].alive, jinxed)

    def test_a_lunatic_who_believes_it_learns_a_phrase_that_kills_nobody(self):
        g = self.game([T1, 'Lunatic', T3, 'Poisoner', 'Imp', T4], extra=['Yaggababble'],
                      forced={'Yaggababble phrase': {'statements': ['fair enough']}})
        g.g[B].shown = 'Yaggababble'
        self.setup_step('Yaggababble')
        self.assertEqual(self.secret('Yaggababble', B), 'fair enough')
        self.say(B, 'fair enough')
        self.assertEqual(g.g.notes['Yaggababble'][B]['count'], {})

    def test_a_judge_may_count_a_near_miss(self):
        g = self.start(phrase='fair enough', forced={'Yaggababble:Ellis:1': {'players': [A]}})
        self.with_judge(lambda c, v: v.get('yes') is True or v.get('players') == [A])
        self.say(E, 'fairs enough')
        run(g.run_pending())
        self.assertEqual(g.g.notes['Yaggababble'][E]['count'], {1: 1})


# ---- Townsfolk: the Amnesiac -------------------------------------------------------------------------------------

GIFT = {x.id: x for x in carousel6.AMNESIAC}


class AmnesiacTests(Batch5Test):
    CHARS = ['Amnesiac', T1, T2, 'Poisoner', 'Imp', T3]

    def start(self, gift, chars=None, **kw):
        g = self.game(chars or self.CHARS, forced={'Amnesiac ability': {'statements': [GIFT[gift].text]},
                                                   **kw.pop('forced', {})}, **kw)
        self.setup_step('Amnesiac')
        return g

    def guess(self, name, text):
        run(self.g.visit_judged(name, {'character': 'Amnesiac', 'text': text}))

    def test_a_curated_list_each_entry_run_by_the_engine(self):
        self.assertTrue(25 <= len(carousel6.AMNESIAC) <= 40)
        self.assertEqual(len(carousel6.GIFTS), len(carousel6.AMNESIAC))
        for gift in carousel6.AMNESIAC:
            self.assertTrue(not gift.model or gift.model in ch.CHARACTERS, gift.id)
            self.assertIn(gift.when, ('first', 'each', 'other', 'once', 'other once', 'passive'))

    def test_drawn_at_setup_from_the_list_and_never_told(self):
        g = self.dealt(['Amnesiac', T1, T2, 'Poisoner', 'Imp', O1])
        gift = carousel6.Amnesiac.gift(g.g, g.g[A])
        self.assertIn(gift, carousel6.AMNESIAC)
        self.assertTrue(self.intro(A, 'You do not know your ability'))
        self.assertFalse([e for e in g.events if e['to'] == [A] and gift.text in str(e['data'])])
        self.assertEqual(len(g.st.seen['Amnesiac ability:Alex'].values), len(carousel6.AMNESIAC))

    def test_the_guess_is_hot_warm_or_cold(self):
        close = carousel6.amnesiac_closeness
        self.assertEqual(close(GIFT['empath'], 'I think I am basically an Empath'), 'hot')
        self.assertEqual(close(GIFT['empath'], 'I learn how many of my neighbours are evil'), 'hot')
        self.assertEqual(close(GIFT['empath'], 'something about my neighbors'), 'warm')
        self.assertEqual(close(GIFT['empath'], 'I learn something'), 'warm')
        self.assertEqual(close(GIFT['empath'], 'I am safe from the Demon'), 'cold')
        self.assertEqual(close(GIFT['fortune teller'], 'fortune teller'), 'hot')
        g = self.start('monk')
        self.guess(A, 'I protect a player from the Demon each night')
        self.assertTrue(self.told(A, 'The Storyteller says: HOT'))
        self.day(g, 2)
        self.guess(A, 'I get information')
        self.assertTrue(self.told(A, 'The Storyteller says: COLD'))
        self.assertEqual(len(g.g.notes['Amnesiac'][A]['guesses']), 2)

    def test_once_a_day_alive_and_a_bluff_learns_nothing(self):
        g = self.start('monk')
        self.guess(A, 'Monk')
        self.guess(A, 'Monk')
        self.assertEqual(len(self.told(A, 'The Storyteller says')), 1)
        self.guess(B, 'Monk')
        self.assertTrue(self.told(B, 'nothing happens'))
        g.g[A].alive = False
        self.day(g, 2)
        self.guess(A, 'Monk')
        self.assertEqual(len(self.told(A, 'The Storyteller says')), 1)

    def test_a_sober_guess_may_be_judged_any_way_a_drunk_one_misinformed_the_vortox_only_false(self):
        g = self.start('monk')
        self.guess(A, 'Monk')
        self.assertEqual(len(g.st.seen['Amnesiac guess:Alex'].values), 3)
        g = self.start('monk', forced={'Amnesiac guess': {'statements': ['cold']}})
        self.poison(A)
        self.guess(A, 'Monk')
        self.assertTrue(self.told(A, 'The Storyteller says: COLD'))
        self.assertTrue([x for x in g.g.abnormal if x['ability'] == 'Amnesiac'])
        g = self.start('monk', chars=['Amnesiac', T1, T2, 'Poisoner', 'Vortox', T3])
        self.guess(A, 'Monk')
        self.assertNotEqual(g.g.notes['Amnesiac'][A]['guesses'][0]['answer'], 'hot')

    def test_woken_to_choose_without_being_told_why_and_protecting(self):
        g = self.start('monk')
        self.choose(1, D, [B])
        run(g.night(1))
        self.assertFalse([r for r in self.seats[A].log if r.kind == 'night'])  # (each night*: not the first)
        self.day(g, 1)
        self.choose(2, A, [B])
        self.choose(2, D, [C])
        self.choose(2, E, [B])
        run(g.night(2))
        prompt = [r.prompt for r in self.seats[A].log if r.kind == 'night'][-1]
        self.assertIn('Amnesiac: Your ability asks you to choose a player (not yourself). You are not told why.',
                      prompt)
        self.assertNotIn('Demon', prompt)
        self.assertTrue(g.g[B].alive)

    def test_its_step_comes_before_the_demons(self):
        s = self.script(['Amnesiac', 'Monk', 'Imp', 'Yaggababble', 'Empath'], True)
        self.assertLess(s.other_nights.index('Amnesiac'), s.other_nights.index('Imp'))
        self.assertLess(s.other_nights.index('Monk'), s.other_nights.index('Amnesiac'))

    def test_information_comes_at_the_nights_end_without_naming_the_ability(self):
        g = self.start('empath', chars=['Amnesiac', T1, T2, 'Poisoner', T3, 'Imp'])
        self.choose(1, D, [B])
        run(g.night(1))
        self.assertTrue(self.told(A, 'Amnesiac: your ability tells you: You learn that 1 of your living neighbours is '
                                     'evil.'))
        g = self.start('chef', forced={'Chef:Alex': {'number': 0}})
        self.choose(1, D, [B])
        run(g.night(1))
        self.day(g, 1)
        self.choose(2, D, [B])
        self.choose(2, E, [C])
        run(g.night(2))
        self.assertEqual(len(self.told(A, 'your ability tells you')), 1)  # ("you start knowing": once)

    def test_drunk_or_poisoned_its_protection_fails_and_information_may_be_false(self):
        g = self.start('monk')
        self.day(g, 1)
        self.poison(A)
        self.choose(2, A, [B])
        self.choose(2, D, [C])
        self.choose(2, E, [B])
        run(g.night(2))
        self.assertFalse(g.g[B].alive)
        g = self.start('empath', forced={'Empath:Alex': {'number': 2}})
        self.poison(A)
        self.choose(1, D, [B])
        run(g.night(1))
        self.assertTrue(self.told(A, '2 of your living neighbours'))

    def test_every_entry_plays_three_nights(self):
        chars = ['Amnesiac', 'Empath', 'Chef', 'Poisoner', 'Imp', 'Recluse', 'Monk']
        for gift in carousel6.AMNESIAC:
            with self.subTest(gift.id):
                g = self.start(gift.id, chars=chars)
                for n in (1, 2, 3):
                    self.choose(n, A, [B, C][:gift.choose])
                    self.choose(n, D, [F])
                    self.choose(n, E, [] if n == 1 else [G])
                    self.choose(n, G, [B])
                    if n > 1:
                        g.g.executed_death = C if n == 3 else None
                    run(g.night(n))
                    if g.g.winner:
                        break
                    self.day(g, n)
                if gift.family == carousel6.INFO:
                    self.assertTrue(self.told(A, 'your ability tells you'))

    def test_the_standing_abilities(self):
        g = self.start('soldier')
        self.day(g, 1)
        self.choose(2, E, [A])
        self.choose(2, D, [B])
        run(g.night(2))
        self.assertTrue(g.g[A].alive)
        g = self.start('fool')
        g.execute(A)
        self.assertTrue(g.g[A].alive)
        g.execute(A)
        self.assertFalse(g.g[A].alive)
        g = self.start('virgin')
        self.assertTrue(run(g.virgin_judged(B, A)))
        self.assertFalse(g.g[B].alive)
        self.assertFalse(run(g.virgin_judged(C, A)))
        g = self.start('mayor')
        for x in (B, C, F):
            g.g[x].alive = False
        R('Amnesiac').end_of_day(g, g.g[A])
        self.assertEqual(g.g.winner, 'good')
        g = self.start('tea lady', chars=[T4, 'Amnesiac', T1, T2, 'Poisoner', 'Imp'])
        self.day(g, 1)
        self.choose(2, F, [A])
        self.choose(2, E, [D])
        run(g.night(2))
        self.assertTrue(g.g[A].alive)

    def test_the_ravenkeeper_and_sage_entries_act_on_its_death(self):
        g = self.start('ravenkeeper', forced={'Ravenkeeper:Alex': {'character': 'Imp'}})
        self.day(g, 1)
        self.queue(A, 'ravenkeeper', {'targets': [E]})
        self.choose(2, D, [B])
        self.choose(2, E, [A])
        run(g.night(2))
        self.assertTrue(self.told(A, f'your ability tells you: {E} is the Imp'))
        g = self.start('sage')
        self.day(g, 1)
        self.choose(2, D, [B])
        self.choose(2, E, [A])
        run(g.night(2))
        self.assertTrue(self.told(A, 'the Demon who killed you is'))

    def test_once_per_game_entries_are_spent(self):
        g = self.start('alignment check')
        self.choose(1, A, [D])
        self.choose(1, D, [B])
        run(g.night(1))
        self.assertTrue(self.told(A, f'{D} is evil'))
        self.day(g, 1)
        self.assertIsNone(R('Amnesiac').night_spec(g, g.g[A], g.tonight))

    def test_a_drunk_who_believes_it_is_woken_as_one_and_protects_nobody(self):
        g = self.game(['Drunk', T1, T2, 'Poisoner', 'Imp', T3], extra=['Amnesiac'],
                      forced={'Amnesiac ability': {'statements': [GIFT['monk'].text]}})
        g.g[A].shown = 'Amnesiac'
        self.setup_step('Amnesiac')
        self.day(g, 1)
        self.choose(2, A, [B])
        self.choose(2, E, [B])
        self.choose(2, D, [C])
        run(g.night(2))
        self.assertFalse(g.g[B].alive)
        self.guess(A, 'Monk')
        self.assertTrue(self.told(A, 'The Storyteller says'))

    def test_a_philosopher_or_a_pit_hag_s_new_amnesiac_draws_one(self):
        g = self.game(['Philosopher', T1, T2, 'Poisoner', 'Imp', T3], extra=['Amnesiac'],
                      forced={'Amnesiac ability': {'statements': [GIFT['empath'].text]}})
        self.choose(1, A, character='Amnesiac')
        run(g.night(1))
        self.assertEqual(carousel6.Amnesiac.gift(g.g, g.g[A]).id, 'empath')
        self.assertTrue(self.told(A, 'your ability tells you'))
        g = self.game([T1, T2, T3, 'Pit-Hag', 'Imp', T4], extra=['Amnesiac'],
                      forced={'Amnesiac ability': {'statements': [GIFT['soldier'].text]}})
        run(g.change(g.g[B], 'Amnesiac'))
        self.assertEqual(carousel6.Amnesiac.gift(g.g, g.g[B]).id, 'soldier')
        self.assertTrue(self.told(B, 'you do not know your ability'))

    def test_a_choice_made_for_another_ability_is_not_its_own(self):
        # finding B23: a Philosopher who gains it on the first night has no Amnesiac choice tonight (it crashed)
        g = self.game(['Philosopher', T1, T2, 'Poisoner', 'Imp', T3], extra=['Amnesiac'],
                      forced={'Amnesiac ability': {'statements': [GIFT['monk'].text]}})
        self.choose(1, A, character='Amnesiac')
        run(g.night(1))
        self.assertFalse([s for s in g.g.states if s.kind == 'safe'])
        self.assertIsNone(g.g.notes['Amnesiac'][A]['chosen'])

    def test_a_judge_chooses_from_the_list_never_inventing(self):
        g = self.start('monk')
        choice = carousel6.gift_choice(g.g, g.g[A])
        self.assertFalse(choice.legal({'statements': ['You win.']}))
        self.assertTrue(choice.legal({'statements': [GIFT['sage'].text]}))


class Batch5ScriptTests(unittest.TestCase):
    def test_the_seventh_synthetic_script_deals_at_every_size_and_holds_the_jinx(self):
        from clocktower.state import random_setup, setup_error
        s = ch.Script('carousel-7')
        self.assertTrue({'Mezepheles', 'Yaggababble', 'Amnesiac'} <= set(s.all))
        self.assertIn(('Yaggababble', 'Exorcist'), s.jinxes)
        for n in range(5, 16):
            chars = random_setup(random.Random(n), None, n, s)
            self.assertIsNone(setup_error(chars, s))

    def test_every_batch_5_character_has_storyteller_notes(self):
        sections = judge._sections(judge.NOTES / 'carousel.md')
        for c in ('Mezepheles', 'Yaggababble', 'Amnesiac'):
            self.assertIn(c, sections)
            self.assertEqual(ch.rules(c).__module__, 'clocktower.carousel6')

    def test_it_plays_at_every_size(self):
        self.assertEqual(smoke.smoke(ch.Script('carousel-7'), games=1, out=io.StringIO()), [])

    def test_the_corpus_scripts_it_completes_play(self):
        roots = [smoke.Path('/workspace/carousel-collection'), smoke.corpus_dir()]
        paths = [r / n / 'script.json' for r in roots for n in ('haroldholt', 'insanityintuition', 'onesyouleastexpect',
                                                                 'punchy', 'deadcouncil', 'phantomdetectives',
                                                                 'riverstyx', 'warrens')]
        paths = [x for x in paths if x.exists()]
        if not paths:
            raise unittest.SkipTest('no corpus')
        for path in paths:
            with self.subTest(path.parent.name):
                self.assertEqual(smoke.smoke(ch.Script(path), games=1, sizes=(5, 9, 15), out=io.StringIO()), [])

    def test_new_weights_are_on_the_policy(self):
        self.assertEqual(POLICY['yaggababble_kill'], 0.75)


if __name__ == '__main__':
    unittest.main()
