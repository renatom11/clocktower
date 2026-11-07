"""Interactions between characters of different base scripts that the fuzzer found wrong (docs/interaction-findings.md,
B1-B4) and their fixes: each meeting only happens on a custom script, so the base scripts play as before."""
import unittest

from clocktower import bmr
from clocktower.llm import Reply

from test_carousel import BLANK, T1, T2, T3, T4, run
from test_carousel1 import Batch1Test, Seat

A, B, C, D, E, F, G = 'Alex', 'Blair', 'Casey', 'Drew', 'Ellis', 'Frankie', 'Gray'


def woken_as(seat, role):
    return [r for r in seat.log if r.kind == 'night' and f'— {role}:' in r.prompt]


class RoleSeat(Seat):
    """A Seat whose night answers may be given per role ({(night, role): answer}), for a player woken at two steps."""

    def __init__(self):
        super().__init__()
        self.roles = {}

    async def act(self, text, request):
        for (n, role), answer in self.roles.items():
            if request.kind == 'night' and request.day == n and f'— {role}:' in request.prompt:
                self.log.append(request)
                return Reply({**BLANK, **answer})
        return await super().act(text, request)


class Test(Batch1Test):
    def game(self, chars, jinxed=True, forced=None, extra=()):
        g = super().game(chars, jinxed, forced, extra)
        for name in list(self.seats):
            seat = RoleSeat()
            self.seats[name] = g.seats[name] = seat
        return g

    def as_role(self, night, name, role, targets=(), character=None):
        self.seats[name].roles[(night, role)] = {'targets': list(targets), 'character': character}


class ScarletWomanZombuulTests(Test):
    CHARS = ['Zombuul', 'Scarlet Woman', T1, T2, T3, T4, 'Soldier']

    def test_a_zombuul_that_only_seems_to_die_is_not_taken_over(self):
        g = self.game(self.CHARS)
        g.execute(A)
        self.assertTrue(g.g[A].alive and g.g[A].seems_dead)
        self.assertEqual((g.g[A].character, g.g[B].character), ('Zombuul', 'Scarlet Woman'))
        g.execute(A)  # the second death is real: now she becomes the Zombuul
        self.assertFalse(g.g[A].alive)
        self.assertEqual(g.g[B].character, 'Zombuul')


class VortoxBMRInformationTests(Test):
    def test_the_chambermaid_is_told_a_false_count_under_the_vortox(self):
        g = self.game(['Chambermaid', 'Vortox', T1, T2, 'Poisoner', T3, T4])
        g.g.woke[2] = [C]
        choice = g.false_only(bmr.chambermaid_choice(g.g, g.g[A], [C, D], 2))
        self.assertEqual(sorted(v['number'] for v in choice.values), [0, 2])  # one of them woke: never 1

    def test_the_grandmother_is_shown_a_false_grandchild_under_the_vortox(self):
        g = self.game(['Grandmother', 'Vortox', T1, T2, 'Poisoner', T3, T4])
        choice = g.false_only(bmr.grandmother_choice(g.g, g.g[A], C))
        self.assertTrue(choice.values)
        self.assertNotIn({'players': [C], 'character': T1}, choice.values)
        g = self.game(['Grandmother', 'Imp', T1, T2, 'Poisoner', T3, T4], extra=['Vortox'])
        values = bmr.grandmother_choice(g.g, g.g[A], C).values
        self.assertEqual([(v['players'], v['character']) for v in values], [([C], T1)])


class OncePerGameBelieverTests(Test):
    """A Drunk who believes they have a once-per-game ability spends it as the real one would, and is not woken to
    use it again."""

    def believer(self, role, extra=()):
        g = self.game(['Drunk', T1, T2, T3, 'Poisoner', 'Imp', 'Soldier'], extra=[role, *extra])
        g.g[A].shown = role
        quiet(self, 1, 2, 3)
        return g

    def test_courtier(self):
        g = self.believer('Courtier')
        self.as_role(2, A, 'Courtier', character=T1)
        run(g.night(2))
        self.assertEqual(len(woken_as(self.seats[A], 'Courtier')), 1)
        self.assertFalse(g.g.is_drunk(g.g[B]))  # the Drunk's choice does nothing
        run(g.night(3))
        self.assertEqual(len(woken_as(self.seats[A], 'Courtier')), 1)

    def test_professor(self):
        g = self.believer('Professor')
        g.g.die(g.g[B])
        self.as_role(2, A, 'Professor', [B])
        run(g.night(2))
        self.assertFalse(g.g[B].alive)
        run(g.night(3))
        self.assertEqual(len(woken_as(self.seats[A], 'Professor')), 1)

    def test_seamstress(self):
        g = self.believer('Seamstress')
        self.as_role(1, A, 'Seamstress', [B, C])
        run(g.night(1))
        self.assertTrue(self.told(A, 'the same alignment'))  # told something, as a Seamstress is
        run(g.night(2))
        self.assertEqual(len(woken_as(self.seats[A], 'Seamstress')), 1)

    def test_philosopher(self):
        g = self.believer('Philosopher', extra=['Monk'])
        self.as_role(1, A, 'Philosopher', character='Monk')
        run(g.night(1))
        self.assertEqual(g.g[A].extra, [])
        run(g.night(2))
        self.assertEqual(len(woken_as(self.seats[A], 'Philosopher')), 1)

    def test_a_resurrected_player_has_their_ability_again(self):
        g = self.game(['Courtier', 'Professor', T2, T3, 'Poisoner', 'Imp', 'Soldier'])
        quiet(self, 2, 3, 4)
        self.as_role(2, A, 'Courtier', character=T2)
        self.as_role(2, B, 'Professor', [])
        run(g.night(2))
        g.g.die(g.g[A])
        self.as_role(3, B, 'Professor', [A])
        run(g.night(3))
        self.assertTrue(g.g[A].alive)
        self.as_role(4, A, 'Courtier', character=T3)
        run(g.night(4))
        self.assertEqual(len(woken_as(self.seats[A], 'Courtier')), 2)


def quiet(t, *nights):
    """The Poisoner (Ellis) poisons the Imp (Frankie), who attacks the Soldier (Gray): no one is touched."""
    for n in nights:
        t.as_role(n, E, 'Poisoner', [F])
        t.as_role(n, F, 'Imp', [G])


class PhilosopherOncePerGameTests(Test):
    def test_a_philosopher_courtier_makes_a_character_drunk_and_spends_their_own(self):
        g = self.game(['Philosopher', 'Courtier', T2, T3, 'Poisoner', 'Imp', 'Soldier'])
        quiet(self, 1, 2, 3)
        self.as_role(1, A, 'Philosopher', character='Courtier')
        self.as_role(1, A, 'Courtier', character=None)  # gained: keeps it tonight
        self.as_role(1, B, 'Courtier', character=None)
        run(g.night(1))
        self.as_role(2, A, 'Courtier', character=T2)
        self.as_role(2, B, 'Courtier', character=T3)  # the real Courtier, drunk: spent, nothing happens
        run(g.night(2))
        self.assertTrue(g.g.is_drunk(g.g[C]))
        self.assertFalse(g.g.is_drunk(g.g[D]))
        run(g.night(3))
        self.assertEqual((len(woken_as(self.seats[A], 'Courtier')), len(woken_as(self.seats[B], 'Courtier'))), (2, 2))

    def test_a_philosopher_professor_and_the_real_one_each_choose(self):
        g = self.game(['Philosopher', T1, 'Professor', T3, 'Poisoner', 'Imp', 'Soldier'])
        quiet(self, 1, 2, 3, 4)
        self.as_role(1, A, 'Philosopher', character='Professor')
        run(g.night(1))
        g.g.die(g.g[B])
        g.g.die(g.g[D])
        self.as_role(2, A, 'Professor', [])  # keeps it
        self.as_role(2, C, 'Professor', [D])  # the real Professor, drunk: spent, nothing happens
        run(g.night(2))
        self.assertFalse(g.g[D].alive)
        self.as_role(3, A, 'Professor', [B])
        run(g.night(3))
        self.assertTrue(g.g[B].alive)
        run(g.night(4))
        self.assertEqual((len(woken_as(self.seats[A], 'Professor')), len(woken_as(self.seats[C], 'Professor'))),
                         (2, 1))


if __name__ == '__main__':
    unittest.main()
