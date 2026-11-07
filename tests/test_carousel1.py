"""Batch 1 of the experimental characters (clocktower/carousel.py): the Banshee, Damsel, Steward, Nightwatchman,
Al-Hadikhia, Magician, Golem, Summoner, Ojo, Fisherman, Plague Doctor, Hatter and Politician, each edge their text
implies, and every official jinx between them and a built character (docs/carousel-rulings.md, batch 1)."""
import io
import random
import unittest

from clocktower import carousel, smoke
from clocktower import characters as ch
from clocktower.agents import ScriptedStoryteller
from clocktower.game import ALL_NAMES, NAMES, Game
from clocktower.llm import Reply
from clocktower.state import Grimoire, State, random_setup, setup_error

from test_carousel import BLANK, JinxTest, O1, T1, T2, T3, T4, run

A, B, C, D, E, F, G, H, I = NAMES


class Seat:
    """Night requests from {night: answer}; other requests from {kind: [answers]} (each used once); a re-ask gets a
    legal default; every request is recorded."""

    def __init__(self):
        self.answers, self.day, self.log = {}, {}, []

    async def act(self, text, request):
        self.log.append(request)
        if request.prompt.startswith('(That is not a legal choice'):
            need = request.n_targets if request.min_targets is None else request.min_targets
            return Reply({**BLANK, 'targets': request.options[:need],
                          'character': request.characters[0] if request.characters else None})
        queue = self.day.get(request.kind)
        if queue:
            return Reply({**BLANK, **queue.pop(0)})
        if request.kind == 'night':
            return Reply({**BLANK, **self.answers.get(request.day, {})})
        return Reply({**BLANK, 'vote': False})


class Forced(ScriptedStoryteller):
    """The scripted Storyteller, except for the choices given ({choice id prefix: value}, the first match), recording
    every Choice it is asked."""

    def __init__(self, forced=None):
        super().__init__(random.Random(1))
        self.forced, self.seen = forced or {}, {}

    def choose(self, choice):
        self.seen[choice.id] = choice
        for prefix, value in self.forced.items():
            if choice.id.startswith(prefix):
                return value
        return super().choose(choice)


class Batch1Test(JinxTest):
    def game(self, chars, jinxed=True, forced=None, extra=()):
        names = ALL_NAMES[:len(chars)]
        script = self.script(list(chars) + list(extra), jinxed)
        self.seats = {n: Seat() for n in names}
        g = Game(self.seats, Forced(forced), names=names, seed=3, characters=chars, script=script, probes=False,
                 private_beats=1, public_beats=1)
        g.g = Grimoire(names, chars, script=script)
        self.day(g, 1)
        self.g = g
        return g

    def dealt(self, chars, jinxed=True, forced=None, extra=()):
        names = NAMES[:len(chars)]
        script = self.script(list(chars) + list(extra) + ['Soldier', 'Empath', 'Chef', 'Undertaker'], jinxed)
        self.seats = {n: Seat() for n in names}
        g = Game(self.seats, Forced(forced), names=names, seed=3, characters=chars, script=script, probes=False,
                 private_beats=1, public_beats=1)
        run(g.setup())
        self.g = g
        return g

    def intro(self, name, text):
        return [e['data']['text'] for e in self.g.events if e['to'] == [name] and e['kind'] == 'intro'
                and text in e['data']['text']]

    def decide(self, name, *answers):
        self.seats[name].day.setdefault('decide', []).extend({'vote': a} for a in answers)

    def public(self, text):
        return [e['data']['text'] for e in self.g.events if e['to'] == 'public' and e['kind'] == 'text'
                and text in e['data']['text']]

    def poison(self, name):
        self.g.g.add(State('poisoned', name, source='test', until=None))


# ---- Townsfolk ---------------------------------------------------------------------------------------------------

class BansheeTests(Batch1Test):
    CHARS = ['Banshee', T1, T2, T3, 'Poisoner', 'Imp', T4]

    def test_killed_by_the_demon_everyone_learns_it_and_she_nominates_and_votes_twice(self):
        g = self.game(self.CHARS)
        self.choose(2, E, [B])
        self.choose(2, F, [A])
        run(g.night(2))
        self.assertFalse(g.g[A].alive)
        self.assertEqual(len(self.public(f'{A} has died, killed by the Demon, and is the Banshee')), 1)
        self.assertEqual((g.nomination_limit(g.g[A]), g.nomination_limit(g.g[B])), (2, 1))
        self.day(g, 2)
        self.seats[A].day['vote'] = [{'vote': True}, {'vote': True}]
        run(g.vote(C, None, 0))
        result = [e['data'] for e in g.events if e['kind'] == 'vote_result'][-1]
        self.assertEqual(result['votes'], 2)
        self.assertTrue(g.g[A].ghost_vote)  # no ghost vote spent
        run(g.vote(D, None, 0))  # every nomination
        self.assertEqual([e['data'] for e in g.events if e['kind'] == 'vote_result'][-1]['votes'], 2)

    def test_drunk_poisoned_or_not_killed_by_the_demon_nothing(self):
        g = self.game(self.CHARS)
        self.choose(2, E, [A])
        self.choose(2, F, [A])
        run(g.night(2))
        self.assertFalse(g.g[A].alive)
        self.assertEqual((self.public('Banshee'), g.nomination_limit(g.g[A])), ([], 0))
        g = self.game(self.CHARS)
        g.execute(A)
        self.assertEqual((self.public('Banshee'), g.nomination_limit(g.g[A])), ([], 0))
        g = self.game(['Drunk', T1, T2, T3, 'Poisoner', 'Imp', T4], extra=['Banshee'])
        g.g[A].shown = 'Banshee'
        self.choose(2, E, [B])
        self.choose(2, F, [A])
        run(g.night(2))
        self.assertEqual((self.public('Banshee'), g.nomination_limit(g.g[A])), ([], 0))

    def test_a_philosopher_with_the_banshees_ability(self):
        g = self.game(['Philosopher', 'Banshee', T2, T3, 'Poisoner', 'Imp', T4])
        self.choose(2, A, character='Banshee')
        self.choose(2, E, [C])
        self.choose(2, F, [A])
        run(g.night(2))
        self.assertTrue(self.public(f'{A} has died, killed by the Demon'))
        self.assertEqual(g.nomination_limit(g.g[A]), 2)

    def test_the_vortox_jinx_the_banshee_is_announced(self):
        """With the jinx, a Banshee the Vortox kills is announced; without it, the announcement would be false
        information about a Townsfolk, so none is made (the powers still come)."""
        for jinxed in self.both():
            g = self.game(['Banshee', T1, T2, T3, 'Poisoner', 'Vortox', T4], jinxed)
            self.choose(2, E, [B])
            self.choose(2, F, [A])
            run(g.night(2))
            self.assertEqual(len(self.public('is the Banshee')), 1 if jinxed else 0)
            self.assertEqual(g.nomination_limit(g.g[A]), 2)


class StewardTests(Batch1Test):
    CHARS = ['Steward', T1, 'Poisoner', 'Imp', T2]

    def test_the_steward_learns_a_good_player(self):
        for seed in range(5):
            g = self.game(self.CHARS)
            g.st.rng = random.Random(seed)
            self.choose(1, C, [B])
            run(g.night(1))
            told = self.told(A, 'Steward:')
            self.assertEqual(len(told), 1)
            self.assertTrue(any(f'{x} is good' in told[0] for x in (B, E)), told)

    def test_poisoned_or_under_the_vortox_the_steward_may_learn_an_evil_player(self):
        g = self.game(self.CHARS, forced={'Steward': {'players': [D]}})
        self.choose(1, C, [A])
        run(g.night(1))
        self.assertTrue(self.told(A, f'{D} is good'))
        with self.assertRaises(ValueError):  # sober, an evil player is not a legal answer
            g = self.game(self.CHARS, forced={'Steward': {'players': [D]}})
            self.choose(1, C, [B])
            run(g.night(1))
        for seed in range(5):
            g = self.game(['Steward', T1, 'Poisoner', 'Vortox', T2])
            g.st.rng = random.Random(seed)
            self.choose(1, C, [B])
            run(g.night(1))
            self.assertTrue(self.told(A, f'{C} is good') or self.told(A, f'{D} is good'))

    def test_a_drunk_steward_is_woken_and_a_new_steward_learns_at_once(self):
        g = self.game(['Drunk', T1, 'Poisoner', 'Imp', T2], extra=['Steward'])
        g.g[A].shown = 'Steward'
        self.choose(1, C, [B])
        run(g.night(1))
        self.assertTrue(self.told(A, 'Steward:'))
        g = self.game(self.CHARS)
        run(g.change(g.g[B], character='Steward'))
        self.assertTrue(self.told(B, 'Steward:'))


class NightwatchmanTests(Batch1Test):
    CHARS = ['Nightwatchman', T1, T2, 'Poisoner', 'Imp']

    def test_the_chosen_player_learns_the_nightwatchman_once_per_game(self):
        g = self.game(self.CHARS)
        self.choose(1, A, [B])
        self.choose(1, D, [E])
        run(g.night(1))
        self.assertTrue(self.told(B, f'{A} is the Nightwatchman'))
        self.choose(2, A, [C])
        self.choose(2, D, [E])
        run(g.night(2))
        self.assertFalse(self.told(C, 'Nightwatchman'))
        self.assertEqual([r for r in self.seats[A].log if 'Nightwatchman' in r.prompt and r.day == 2], [])

    def test_choosing_no_one_keeps_it(self):
        g = self.game(self.CHARS)
        self.choose(1, D, [E])
        run(g.night(1))
        self.choose(2, A, [C])
        self.choose(2, D, [E])
        run(g.night(2))
        self.assertTrue(self.told(C, f'{A} is the Nightwatchman'))

    def test_poisoned_or_under_the_vortox_another_player_or_nothing(self):
        g = self.game(self.CHARS, forced={'Nightwatchman': {'players': [C]}})
        self.choose(1, D, [A])
        self.choose(1, A, [B])
        run(g.night(1))
        self.assertTrue(self.told(B, f'{C} is the Nightwatchman'))
        g = self.game(['Nightwatchman', T1, T2, 'Poisoner', 'Vortox'])
        self.choose(1, A, [B])
        self.choose(1, D, [C])
        run(g.night(1))
        self.assertFalse(self.told(B, f'{A} is the Nightwatchman'))
        self.assertTrue(carousel.snv.used(g.g, g.g[A], 'Nightwatchman'))


class MagicianTests(Batch1Test):
    CHARS = ['Magician', T1, T2, T3, T4, 'Poisoner', 'Imp', O1]

    def test_the_demon_sees_the_magician_as_a_minion_and_the_minions_see_them_as_the_demon(self):
        self.dealt(self.CHARS)
        self.assertTrue(self.intro(G, f'Your Minions: {A}, {F} (you do not know'))
        self.assertTrue(self.intro(F, f'The Demon is {A} or {G} (you were shown both).'))

    def test_a_poisoned_or_drunk_magician_does_nothing(self):
        g = self.dealt([T1, T2, T3, 'Magician', 'No Dashii', 'Poisoner', T4, O1])
        self.assertTrue(g.g.is_poisoned(g.g[D]))
        self.assertTrue(self.intro(E, f'Your Minion: {F} (you do not know'))
        self.assertTrue(self.intro(F, f'The Demon is {E}.'))
        g = self.dealt(['Drunk', T1, T2, T3, T4, 'Poisoner', 'Imp', 'Monk'], extra=['Magician'],
                       forced={'drunk_as': {'character': 'Magician'}})
        self.assertEqual(g.g[A].shown, 'Magician')
        self.assertTrue(self.intro(F, f'The Demon is {G}.'))

    def test_with_no_demon_the_minions_are_shown_the_magician(self):
        self.dealt(['Magician', T1, T2, T3, T4, 'Summoner', 'Monk'], extra=['Imp'])
        self.assertTrue(self.intro(F, f'The Demon is {A}.'))

    def test_the_spy_jinx_the_demon_and_magician_tokens_are_removed(self):
        for jinxed in self.both():
            g = self.game(['Magician', T1, T2, T3, 'Spy', 'Imp', T4], jinxed)
            run(g.night(1))
            seen = self.told(E, 'Spy: you look at the Grimoire')[0]
            self.assertEqual(f'1. {A}: (token removed)' in seen, jinxed)
            self.assertEqual(f'6. {F}: (token removed)' in seen, jinxed)
            self.assertEqual('Magician (good)' in seen, not jinxed)
            self.assertIn(f'2. {B}: {T1}', seen)


class FishermanTests(Batch1Test):
    CHARS = ['Fisherman', T1, T2, 'Poisoner', 'Imp', T3, 'Recluse']

    def advice(self, g, who=A):
        return run(g.visit_judged(who, {'character': 'Fisherman', 'text': ''}))

    def test_one_true_piece_of_advice_once_per_game(self):
        for seed in range(6):
            g = self.game(self.CHARS)
            g.st.rng = random.Random(seed)
            self.assertTrue(self.advice(g))
            told = self.told(A, 'advice to help your team win')
            self.assertEqual(len(told), 1)
            choice = g.st.seen[f'Fisherman:{A}']
            value = [e['data']['value'] for e in g.events if e['kind'] == 'st_choice'
                     and e['data']['id'] == f'Fisherman:{A}'][0]
            self.assertTrue(choice.truth(value), value)
            self.assertNotIn(f'{E} is evil', told[0])  # never the Demon outright
            self.assertNotIn(f'{E} is the Imp', told[0])
        self.day(g, 2)
        self.advice(g)
        self.assertTrue(self.told(A, 'you have already had your advice'))

    def test_poisoned_bad_advice_is_legal_and_under_the_vortox_only_bad(self):
        g = self.game(self.CHARS, forced={'Fisherman': {'statements': [f'{B} is evil.']}})
        with self.assertRaises(ValueError):  # a sober Fisherman: only true advice
            self.advice(g)
        g = self.game(self.CHARS)
        self.poison(A)
        choice = carousel.fisherman_choice(g.g, g.g[A])
        self.assertTrue(any(not choice.truth(v) for v in choice.values))
        g = self.game(['Fisherman', T1, T2, 'Poisoner', 'Vortox', T3, 'Recluse'])
        self.advice(g)
        choice = g.false_only(g.st.seen[f'Fisherman:{A}'])
        self.assertTrue(choice.values and not any(choice.truth(v) for v in choice.values))

    def test_anyone_else_visiting_gets_a_nod_and_the_drunk_fisherman_is_answered(self):
        g = self.game(self.CHARS)
        self.advice(g, B)
        self.assertTrue(self.told(B, 'listened and nodded'))
        g = self.game(['Drunk', T1, T2, 'Poisoner', 'Imp', T3, 'Recluse'], extra=['Fisherman'])
        g.g[A].shown = 'Fisherman'
        self.advice(g)
        self.assertTrue(self.told(A, 'advice to help your team win'))

    def test_an_evil_fishermans_advice_helps_evil(self):
        g = self.game(self.CHARS)
        g.g[A].alignment = 'evil'
        stmts = carousel.fisherman_statements(g.g, g.g[A])
        self.assertTrue(any(s['helps'] and s['form'] == 'character' and s['character'] == T1 for s in stmts))
        self.assertFalse(any(s['helps'] and s['form'] == 'evil' for s in stmts))


# ---- Outsiders ---------------------------------------------------------------------------------------------------

class DamselTests(Batch1Test):
    CHARS = [T1, T2, 'Damsel', T3, T4, 'Poisoner', 'Imp', 'Monk']

    def test_the_minions_know_a_damsel_is_in_play(self):
        self.dealt(self.CHARS)
        self.assertTrue(self.intro(F, 'A Damsel is in play'))
        self.assertFalse(self.intro(G, 'Damsel'))

    def test_a_minions_right_public_guess_makes_her_team_lose_each_minion_once(self):
        damsel = ch.rules('Damsel')
        g = self.game(self.CHARS)
        damsel.act_publicly(g, A, C)  # not a Minion: nothing
        damsel.act_publicly(g, G, C)  # the Demon: nothing
        self.assertIsNone(g.g.winner)
        damsel.act_publicly(g, F, B)  # wrong: the guess is spent
        damsel.act_publicly(g, F, C)
        self.assertIsNone(g.g.winner)
        g = self.game(self.CHARS)
        damsel.act_publicly(g, F, C)
        self.assertEqual(g.g.winner, 'evil')
        g = self.game(self.CHARS)
        self.poison(F)
        damsel.act_publicly(g, F, C)
        self.assertIsNone(g.g.winner)
        self.assertEqual([a['ability'] for a in g.g.abnormal], ['Damsel'])

    def test_a_dead_damsel_guessed_does_nothing(self):
        g = self.game(self.CHARS)
        g.g[C].alive = False
        ch.rules('Damsel').act_publicly(g, F, C)
        self.assertIsNone(g.g.winner)

    def test_the_spy_jinx_the_damsel_is_poisoned_while_a_spy_is_or_has_been_in_play(self):
        chars = [T1, T2, 'Damsel', T3, T4, 'Spy', 'Imp', 'Monk']
        for jinxed in self.both():
            g = self.game(chars, jinxed, extra=['Poisoner'])
            self.assertEqual(g.g.is_poisoned(g.g[C]), jinxed)
            run(g.change(g.g[F], character='Poisoner'))
            self.assertEqual(g.g.is_poisoned(g.g[C]), jinxed)  # has been in play
            ch.rules('Damsel').act_publicly(g, F, C)
            self.assertEqual(g.g.winner, None if jinxed else 'evil')

    def test_the_pit_hag_jinx_the_storyteller_chooses_who_is_the_damsel(self):
        chars = [T1, T2, T3, T4, 'Monk', 'Pit-Hag', 'Imp']
        for jinxed in self.both():
            g = self.game(chars, jinxed, forced={'Damsel': {'players': [D]}}, extra=['Damsel'])
            self.choose(2, F, [B], 'Damsel')
            self.choose(2, G, [A])
            run(g.night(2))
            damsel = D if jinxed else B
            self.assertEqual(g.g[damsel].character, 'Damsel')
            self.assertTrue(self.told(F, 'a Damsel is now in play'))


class GolemTests(Batch1Test):
    CHARS = ['Golem', T1, T2, 'Recluse', 'Poisoner', 'Imp', T3]

    def test_the_golems_one_nomination_kills_a_nominee_who_is_not_the_demon(self):
        g = self.game(self.CHARS)
        self.assertEqual(g.nomination_limit(g.g[A]), 1)
        run(g.nomination_judged(A, B))
        self.assertFalse(g.g[B].alive)
        self.assertEqual(g.nomination_limit(g.g[A]), 0)
        g = self.game(self.CHARS)
        run(g.nomination_judged(A, F))
        self.assertTrue(g.g[F].alive)

    def test_a_poisoned_golem_kills_nobody_but_has_nominated(self):
        g = self.game(self.CHARS)
        self.poison(A)
        run(g.nomination_judged(A, B))
        self.assertTrue(g.g[B].alive)
        self.assertEqual(g.nomination_limit(g.g[A]), 0)

    def test_the_recluse_may_register_as_the_demon(self):
        for yes in (True, False):
            g = self.game(self.CHARS, forced={'Golem': {'yes': yes}})
            run(g.nomination_judged(A, D))
            self.assertEqual(g.g[D].alive, yes)


class PoliticianTests(Batch1Test):
    CHARS = ['Politician', 'Saint', T1, T2, 'Poisoner', 'Imp', T3]

    def nominate(self, g, nominator, nominee):
        g.g.nominations.append({'day': g.day, 'nominator': nominator, 'nominee': nominee, 'outcome': 'block'})

    def test_nominating_the_saint_who_loses_the_game_the_politician_turns_evil_and_wins(self):
        g = self.game(self.CHARS)
        self.nominate(g, A, B)
        g.execute(B)
        g.g.finish()
        self.assertEqual((g.g.winner, g.g[A].alignment), ('evil', 'evil'))
        self.assertIn('the Politician, was the player most responsible', g.g.reason)

    def test_executed_into_evils_win_the_dead_politician_wins_with_evil(self):
        g = self.game(self.CHARS)
        for x in (B, C, D, G):
            g.g[x].alive = False
        self.nominate(g, E, A)
        g.execute(A)
        g.g.finish()
        self.assertEqual((g.g.winner, g.g[A].alive, g.g[A].alignment), ('evil', False, 'evil'))

    def test_someone_else_responsible_or_a_poisoned_politician_nothing(self):
        g = self.game(self.CHARS)
        self.nominate(g, C, B)
        g.execute(B)
        g.g.finish()
        self.assertEqual(g.g[A].alignment, 'good')
        g = self.game(self.CHARS)
        self.poison(A)
        self.nominate(g, A, B)
        g.execute(B)
        g.g.finish()
        self.assertEqual(g.g[A].alignment, 'good')

    def test_the_pit_hag_jinx_an_evil_politician_cannot_turn_good(self):
        chars = [T1, T2, T3, T4, 'Monk', 'Pit-Hag', 'Imp', 'Scarlet Woman']
        for jinxed in self.both():
            g = self.game(chars, jinxed, extra=['Politician'])
            self.choose(2, F, [H], 'Politician')
            self.choose(2, G, [A])
            run(g.night(2))
            self.assertEqual((g.g[H].character, g.g[H].alignment), ('Politician', 'evil'))
            self.day(g, 2)
            self.nominate(g, H, G)
            g.execute(G)  # the Demon, with no Scarlet Woman left: good wins, and the Politician nominated it
            g.g.finish()
            self.assertEqual(g.g.winner, 'good')
            self.assertEqual(g.g[H].alignment, 'evil' if jinxed else 'good')


class HatterTests(Batch1Test):
    CHARS = [T1, T2, 'Hatter', T3, 'Poisoner', 'Imp', T4]

    def test_after_the_hatter_dies_the_minions_and_demons_may_become_others_of_their_type(self):
        g = self.game(self.CHARS, extra=['Spy', 'Vortox', 'Baron'])
        g.execute(C)
        self.choose(2, E, [A], 'Spy')
        self.choose(2, F, [B], 'Vortox')
        run(g.night(2))
        self.assertEqual((g.g[E].character, g.g[F].character), ('Spy', 'Vortox'))
        self.assertTrue(self.told(F, 'you are now the Vortox'))
        party = [r for r in self.seats[E].log if 'tea party' in r.prompt][0]
        self.assertEqual(sorted(party.characters), ['Baron', 'Spy'])
        self.choose(3, E, [A], 'Baron')
        run(g.night(3))
        self.assertEqual(g.g[E].character, 'Spy')  # one tea party

    def test_null_keeps_and_a_drunk_hatters_death_gives_none(self):
        g = self.game(self.CHARS, extra=['Spy', 'Vortox'])
        g.execute(C)
        self.choose(2, E, [A])
        run(g.night(2))
        self.assertEqual(g.g[E].character, 'Poisoner')
        g = self.game(self.CHARS, extra=['Spy', 'Vortox'])
        self.poison(C)
        g.execute(C)
        self.choose(2, E, [A], 'Spy')
        run(g.night(2))
        self.assertEqual(g.g[E].character, 'Poisoner')


class PlagueDoctorTests(Batch1Test):
    CHARS = ['Plague Doctor', T1, T2, T3, 'Poisoner', 'Imp', T4]
    MINIONS = ['Spy', 'Scarlet Woman', 'Baron', 'Evil Twin', 'Witch', 'Mastermind', 'Pit-Hag', 'Godfather',
               "Devil's Advocate", 'Assassin', 'Cerenovus']

    def died(self, gained, chars=None, more=None, extra=()):
        g = self.game(chars or self.CHARS, forced={**(more or {}), 'Plague Doctor': {'character': gained}},
                      extra=self.MINIONS + list(extra))
        g.execute(A)
        run(g.run_pending())
        return g

    def test_the_storyteller_gains_a_minion_ability_not_in_play_but_never_the_pit_hags(self):
        g = self.died('Witch')
        options = [v['character'] for v in g.st.seen['Plague Doctor'].values]
        self.assertNotIn('Pit-Hag', options)
        self.assertNotIn('Poisoner', options)  # in play
        self.assertIn('Spy', options)
        self.assertEqual(g.g.notes['Storyteller ability'], 'Witch')

    def test_a_poisoned_plague_doctor_gives_nothing(self):
        g = self.game(self.CHARS, extra=self.MINIONS)
        self.poison(A)
        g.execute(A)
        run(g.run_pending())
        self.assertNotIn('Storyteller ability', g.g.notes)

    def test_the_storytellers_poisoner_and_witch_act_at_their_step(self):
        g = self.died('Witch', chars=['Plague Doctor', T1, T2, T3, 'Mastermind', 'Imp', T4],
                      more={'Storyteller:Witch': {'players': [B]}}, extra=['Poisoner'])
        self.day(g, 1)
        run(g.night(2))
        self.day(g, 2)
        run(g.nomination_judged(B, C))
        self.assertFalse(g.g[B].alive)
        g = self.died('Poisoner', chars=['Plague Doctor', T1, T2, T3, 'Mastermind', 'Imp', T4],
                      more={'Storyteller:Poisoner': {'players': [C]}}, extra=['Poisoner'])
        run(g.night(2))
        self.assertTrue(g.g.is_poisoned(g.g[C]))

    def test_the_storytellers_mastermind_plays_one_more_day(self):
        g = self.died('Mastermind')
        self.day(g, 2)
        g.execute(F)
        self.assertIsNone(g.g.winner)
        self.assertEqual(g.g.notes['Mastermind'], 2)

    def test_the_spy_and_scarlet_woman_jinxes_a_minion_gains_it_and_learns_it(self):
        g = self.died('Spy')
        self.assertEqual(g.g[E].extra, ['Spy'])
        self.assertTrue(self.told(E, "you gain the Spy's ability"))
        run(g.night(2))
        self.assertEqual(len(self.told(E, 'Spy: you look at the Grimoire')), 1)
        g = self.died('Scarlet Woman')
        self.day(g, 2)
        g.execute(F)
        self.assertEqual(g.g[E].character, 'Imp')
        self.assertIsNone(g.g.winner)

    def test_the_baron_jinx_up_to_two_players_become_outsiders(self):
        g = self.died('Baron', more={'Plague Doctor:Baron:': {'character': 'Saint'},
                                     'Plague Doctor:Baron': {'players': [B]}}, extra=['Saint', 'Recluse'])
        self.assertEqual((g.g[B].character, g.g[B].alignment), ('Saint', 'good'))
        self.assertTrue(self.told(B, 'you are now the Saint'))

    def test_the_evil_twin_jinx_a_player_becomes_the_evil_twin(self):
        g = self.died('Evil Twin', more={'Plague Doctor:Evil Twin': {'players': [C]}})
        self.assertEqual((g.g[C].character, g.g[C].alignment), ('Evil Twin', 'good'))
        self.assertTrue(self.told(C, 'Evil Twin: your twin is'))


# ---- Minions -----------------------------------------------------------------------------------------------------

class SummonerTests(Batch1Test):
    CHARS = [T1, T2, T3, T4, 'Monk', 'Summoner', 'Chef']

    def test_no_demon_is_dealt_a_townsfolk_in_its_place(self):
        s = self.script(self.CHARS + ['Empath', 'Imp', 'Pukka'], True)
        for seed in range(20):
            chars = random_setup(random.Random(seed), 'Summoner', 7, s)
            self.assertEqual([ch.kind(c) for c in chars].count('Demon'), 0)
            self.assertEqual([ch.kind(c) for c in chars].count('Townsfolk'), 6)
            self.assertIsNone(setup_error(chars, s))
        self.assertIn('no Demon', setup_error([T1, T2, T3, T4, 'Monk', 'Summoner', 'Imp'], s))

    def test_the_summoner_gets_bluffs_and_the_game_waits_for_the_third_night(self):
        g = self.dealt(self.CHARS, extra=['Imp', 'Empath'])
        self.assertTrue(self.intro(F, 'There is no Demon in play'))
        self.assertIn('Three good characters not in play', self.intro(F, 'bluff')[0])
        self.assertIsNone(g.g.check_victory())
        run(g.night(1))
        self.assertIsNone(g.g.check_victory())
        run(g.night(2))
        self.assertIsNone(g.g.check_victory())
        self.choose(3, F, [A], 'Imp')
        run(g.night(3))
        self.assertEqual((g.g[A].character, g.g[A].alignment), ('Imp', 'evil'))
        self.assertTrue(self.told(A, 'you are now the Imp'))
        self.assertIsNone(g.g.check_victory())

    def test_a_dead_or_poisoned_summoner_summons_nobody_and_good_wins(self):
        g = self.game(self.CHARS, extra=['Imp'])
        g.execute(F)
        self.assertEqual(g.g.winner, 'good')
        g = self.game(self.CHARS, extra=['Imp'])
        self.poison(F)
        self.choose(3, F, [A], 'Imp')
        run(g.night(3))
        self.assertEqual(g.g[A].character, T1)
        self.assertEqual(g.g.check_victory(), 'good')

    def test_the_courtier_jinx_the_storyteller_has_the_ability_of_a_summoner_with_none(self):
        chars = [T1, T2, T3, T4, 'Courtier', 'Summoner', 'Chef']
        g = self.game(chars, forced={'Summoner': {'players': [B], 'character': 'Imp'}}, extra=['Imp'])
        g.g.add(State('drunk', F, source='test', until=None))
        self.choose(3, F, [A], 'Imp')
        run(g.night(3))
        self.assertEqual((g.g[B].character, g.g[B].alignment), ('Imp', 'evil'))
        self.assertEqual(g.g[A].character, T1)

    def test_the_pukka_jinx_a_pukka_may_come_on_the_second_night(self):
        for jinxed in self.both():
            g = self.game(self.CHARS, jinxed, extra=['Pukka', 'Imp'])
            self.choose(2, F, [A], 'Pukka')
            run(g.night(2))
            self.assertEqual(g.g[A].character, 'Pukka' if jinxed else T1)
        g = self.game(self.CHARS, extra=['Pukka', 'Imp'])
        self.choose(2, F, [A], 'Imp')  # only a Pukka on the 2nd night: nothing
        run(g.night(2))
        self.assertEqual(g.g[A].character, T1)

    def test_the_zombuul_jinx_a_dead_player_summoned_into_the_zombuul_has_died_once(self):
        g = self.game(self.CHARS, extra=['Zombuul'])
        g.g[A].alive = False
        self.choose(3, F, [A], 'Zombuul')
        run(g.night(3))
        p = g.g[A]
        self.assertEqual((p.character, p.alive, p.seems_dead), ('Zombuul', True, True))
        self.assertTrue(g.g.spent_ability('Zombuul'))
        self.assertIsNone(g.g.check_victory())

    def test_the_pit_hag_and_hatter_jinxes_a_second_living_demon_makes_deaths_arbitrary(self):
        for other in ('Pit-Hag', 'Hatter'):
            for jinxed in self.both():
                chars = [T1, T2, T3, T4, 'Imp', 'Summoner', other]
                g = self.game(chars, jinxed, forced={'Summoner deaths': {'players': [E], 'yes': True}},
                              extra=['Vortox'])
                self.choose(3, F, [A], 'Vortox')
                self.choose(3, E, [B])
                run(g.night(3))
                self.assertEqual(g.g[A].character, 'Vortox')
                self.assertEqual(g.g[E].alive, not jinxed, (other, jinxed))

    def test_the_clockmaker_jinx_the_summoner_registers_as_the_demon(self):
        chars = ['Clockmaker', T1, 'Summoner', T2, 'Poisoner', T3, T4]
        for jinxed in self.both():
            g = self.game(chars, jinxed, extra=['Imp'])
            choice = carousel.snv.clockmaker_choice(g.g, g.g[A])
            if jinxed:
                self.assertEqual([v['number'] for v in choice.values], [2])
            else:
                self.assertIsNone(choice)


# ---- Demons ------------------------------------------------------------------------------------------------------

class OjoTests(Batch1Test):
    CHARS = [T1, T2, 'Soldier', T3, 'Poisoner', 'Ojo', T4]

    def test_the_ojo_kills_the_player_of_the_character_it_names(self):
        g = self.game(self.CHARS)
        self.choose(2, F, character=T1)
        run(g.night(2))
        self.assertFalse(g.g[A].alive)
        g = self.game(self.CHARS)
        self.choose(2, F, character='Soldier')
        run(g.night(2))
        self.assertTrue(g.g[C].alive)

    def test_not_in_play_the_storyteller_chooses_who_dies(self):
        g = self.game(self.CHARS, forced={'Ojo': {'players': [B]}}, extra=['Monk'])
        self.choose(2, F, character='Monk')
        run(g.night(2))
        self.assertFalse(g.g[B].alive)

    def test_a_poisoned_ojo_kills_nobody_and_a_dead_players_character_kills_nobody(self):
        g = self.game(self.CHARS)
        self.choose(2, E, [F])
        self.choose(2, F, character=T1)
        run(g.night(2))
        self.assertTrue(g.g[A].alive)
        g = self.game(self.CHARS)
        g.g[A].alive = False
        self.choose(2, F, character=T1)
        run(g.night(2))
        self.assertEqual([d['player'] for d in g.g.death_log], [])


class AlHadikhiaTests(Batch1Test):
    CHARS = [T1, T2, T3, T4, 'Poisoner', 'Al-Hadikhia', O1]

    def test_each_chooses_to_live_or_die_and_all_learn_who_was_chosen(self):
        g = self.game(self.CHARS)
        self.choose(2, F, [A, B, C])
        self.decide(A, True)
        self.decide(B, False)
        self.decide(C, True)
        run(g.night(2))
        self.assertEqual([g.g[x].alive for x in (A, B, C)], [True, False, True])
        self.assertEqual(len(self.public(f'the Al-Hadikhia chose {A}, {B} and {C}')), 1)
        asked = [r for r in self.seats[A].log if r.kind == 'decide']
        self.assertIn('the first of three', asked[0].prompt)

    def test_if_all_three_live_all_three_die(self):
        g = self.game(self.CHARS)
        self.choose(2, F, [A, B, C])
        for x in (A, B, C):
            self.decide(x, True)
        run(g.night(2))
        self.assertEqual([g.g[x].alive for x in (A, B, C)], [False, False, False])

    def test_a_dead_player_who_chooses_to_live_comes_back(self):
        g = self.game(self.CHARS)
        g.g[A].alive = False
        self.choose(2, F, [A, B, C])
        self.decide(A, True)
        self.decide(B, True)
        self.decide(C, False)
        run(g.night(2))
        self.assertEqual([g.g[x].alive for x in (A, B, C)], [True, True, False])

    def test_a_poisoned_al_hadikhia_or_fewer_than_three_chosen_does_nothing(self):
        g = self.game(self.CHARS)
        self.choose(2, E, [F])
        self.choose(2, F, [A, B, C])
        for x in (A, B, C):
            self.decide(x, False)
        run(g.night(2))
        self.assertTrue(all(g.g[x].alive for x in (A, B, C)))
        g = self.game(self.CHARS)
        self.choose(2, F, [A, B])
        run(g.night(2))
        self.assertTrue(all(g.g[x].alive for x in (A, B, C)))
        self.assertEqual([r for r in self.seats[A].log if r.kind == 'decide'], [])

    def test_the_mastermind_jinx_three_good_players_choose_the_winner(self):
        chars = [T1, T2, T3, T4, 'Mastermind', 'Al-Hadikhia', O1]
        for answers, winner in (((True, True, True), 'evil'), ((True, False, True), 'good')):
            g = self.game(chars)
            self.day(g, 2)
            g.execute(F)
            self.assertIsNone(g.g.winner)
            self.assertNotIn('Mastermind', g.g.notes)
            self.choose(3, F, [A, B, C])
            for x, a in zip((A, B, C), answers):
                self.decide(x, a)
            run(g.night(3))
            self.assertEqual(g.g.winner, winner)
        g = self.game(chars, jinxed=False)
        self.day(g, 2)
        g.execute(F)
        self.assertEqual((g.g.winner, g.g.notes['Mastermind']), (None, 2))  # the Mastermind's own extra day

    def test_the_scarlet_woman_jinx_two_demons_and_she_is_the_scarlet_woman_again(self):
        chars = [T1, T2, T3, T4, 'Scarlet Woman', 'Al-Hadikhia', O1]
        for jinxed in self.both():
            g = self.game(chars, jinxed)
            self.choose(2, F, [F, A, B])
            self.decide(F, False)
            self.decide(A, True)
            self.decide(B, True)
            run(g.night(2))
            self.assertEqual(g.g[E].character, 'Al-Hadikhia')
            self.choose(3, E, [F, C, D])
            self.decide(F, True)
            self.decide(C, False)
            self.decide(D, False)
            run(g.night(3))
            self.assertTrue(g.g[F].alive)
            self.assertEqual(g.g[E].character, 'Scarlet Woman' if jinxed else 'Al-Hadikhia')


# ---- The synthetic script and the corpus ---------------------------------------------------------------------------

class Carousel2Tests(unittest.TestCase):
    def test_it_holds_all_thirteen_and_every_batch_1_jinx_and_deals_at_every_size(self):
        from test_carousel import JINXES1
        s = ch.Script('carousel-2')
        for c in ('Banshee', 'Damsel', 'Steward', 'Nightwatchman', 'Al-Hadikhia', 'Magician', 'Golem', 'Summoner',
                  'Ojo', 'Fisherman', 'Plague Doctor', 'Hatter', 'Politician'):
            self.assertIn(c, s.all)
        self.assertTrue(all(s.jinxed(a, b) for a, b in JINXES1))
        for n in range(5, 16):
            for seed in range(20):
                chars = random_setup(random.Random(seed), s.minions[seed % len(s.minions)], n, s)
                self.assertIsNone(setup_error(chars, s))

    def test_every_batch_1_character_has_storyteller_notes_and_the_judge_reads_them(self):
        from clocktower import judge
        sections = judge._sections(judge.NOTES / 'carousel.md')
        batch = [c for c in ch.CHARACTERS if c in ch.Script('carousel-2').all and ch.rules(c).__module__.endswith(
            'carousel')]
        self.assertEqual(len(batch), 13)
        self.assertLessEqual(set(batch), set(sections))  # (and batch 2's: tests/test_carousel2.py)
        self.assertIn('Golem: The Golem nominates', judge.storyteller_notes('custom', ['Golem', 'Imp']))

    def test_it_plays_at_every_size(self):
        self.assertEqual(smoke.smoke(ch.Script('carousel-2'), games=1, out=io.StringIO()), [])



if __name__ == '__main__':
    unittest.main()
