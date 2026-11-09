"""The lifecycle of an ability instance and the one change path (docs/state-machines.md, "Refactor results"): a
regression test for each item of the audit's families 1 and 2 (identity by player name, not ability instance; two ways
to change a character), and for G13 and S2. Each test is named after its item and plays the audit's scenario. Items the
owner has still to rule on (U1, U13, G2) are pinned to the engine's current behaviour, so a change to it is a decision
and not an accident."""
import unittest

from clocktower import carousel2, snv
from clocktower.characters import rules
from clocktower.game import Night
from clocktower.state import State

from test_carousel import T1, T2, T3, T4, run
from test_interactions import Test, quiet, woken_as

A, B, C, D, E, F, G = 'Alex', 'Blair', 'Casey', 'Drew', 'Ellis', 'Frankie', 'Gray'


def instance(g, name, character):
    return g.g.ability(g.g[name], character, create=False)


# ---- family 1: identity by player name, not by ability instance ---------------------------------------------------

class InstanceTests(Test):
    def pukka_charmed(self):
        """Night 2 the Pukka (Frankie) poisons Casey; night 3 the Snake Charmer (Alex) charms it, and as the new Pukka
        chooses Drew."""
        g = self.game(['Snake Charmer', T1, T2, T3, T4, 'Pukka', 'Soldier'])
        self.as_role(2, A, 'Snake Charmer', [B])
        self.as_role(2, F, 'Pukka', [C])
        run(g.night(2))
        self.assertTrue(g.g.is_poisoned(g.g[C]))
        self.day(g, 2)
        self.as_role(3, A, 'Snake Charmer', [F])
        self.as_role(3, A, 'Pukka', [D])
        run(g.night(3))
        return g

    def test_S1_pukka_snake_charmer(self):
        g = self.pukka_charmed()
        self.assertEqual((g.g[A].character, g.g[F].character), ('Pukka', 'Snake Charmer'))
        self.assertTrue(g.g[F].alive)  # the charm's poison is not the new Pukka's victim
        self.assertTrue(g.g.is_poisoned(g.g[F]))  # and stays, "permanently"
        self.assertTrue(g.g[C].alive and not g.g.is_poisoned(g.g[C]))  # the old Pukka's victim: ended with it
        self.assertTrue(g.g.is_poisoned(g.g[D]))  # the new Pukka's own victim, who dies next time

    def test_G7_states_name_their_ability(self):
        g = self.pukka_charmed()
        charm = next(s for s in g.g.states if s.kind == 'poisoned' and s.target == F)
        pukka = next(s for s in g.g.states if s.kind == 'poisoned' and s.target == D)
        old = next(a for a in g.g.instances if a.holder == A and a.character == 'Snake Charmer')
        self.assertEqual((charm.ability, old.ended), (old.id, 'changed'))
        self.assertEqual(pukka.ability, instance(g, A, 'Pukka').id)
        self.assertEqual(rules('Pukka').poisons(g.g, g.g[A]), [pukka])

    def test_G8_po_charge_and_shabaloth_meal_are_the_instances(self):
        # a Courtier who declined (chose no one) is made the Po: their "no one" was not the Po's
        g = self.game(['Courtier', T1, T2, T3, 'Poisoner', 'Imp', 'Soldier'], extra=['Po', 'Shabaloth'])
        quiet(self, 2)
        self.as_role(2, A, 'Courtier', character=None)
        run(g.night(2))
        self.assertEqual(g.g.last_choices[A], [])
        run(g.change(g.g[A], 'Po'))
        self.assertEqual(rules('Po').night_spec(g, g.g[A], Night(3)).players, 1)  # not charged
        g.g.ability(g.g[A], 'Po').data['last'] = []  # the Po's own "no one": charged
        self.assertEqual(rules('Po').night_spec(g, g.g[A], Night(3)).players, 3)
        # the Shabaloth's meal is what the Shabaloth chose last night, not its player's choice as another character
        g = self.game(['Monk', T1, T2, T3, 'Poisoner', 'Imp', 'Soldier'], extra=['Shabaloth'])
        quiet(self, 2)
        self.as_role(2, A, 'Monk', [B])
        run(g.night(2))
        run(g.change(g.g[A], 'Shabaloth'))
        night = Night(3)
        night.prior = {a.id: (a.data.get('last_night'), a.data['last']) for a in g.g.instances if 'last' in a.data}
        self.assertEqual(night.before.get(A), None)
        self.assertEqual(night.before_of(g.g, g.g[A], 'Shabaloth'), [])
        self.assertEqual(night.before_of(g.g, g.g[A], 'Monk'), [])  # (ended: a fresh one, never woken)

    def test_G8_checkpoint_before_instances_keeps_the_charge_and_the_meal(self):
        # a checkpoint saved before ability instances: no instances, the last choice by player (last_choices) and the
        # nights each woke (woke). Restored, the Po is still charged and the Shabaloth still has last night's meal
        import pickle
        from clocktower.state import Grimoire
        g = self.game(['Po', T1, T2, T3, 'Poisoner', 'Shabaloth', 'Soldier'])
        d = dict(g.g.__dict__)
        del d['instances']
        d['last_choices'], d['woke'], d['day'] = {A: [], F: [C, D]}, {2: [E, A, F]}, 3
        old = object.__new__(Grimoire)
        old.__dict__.update(d)
        g.g = restored = pickle.loads(pickle.dumps(old))
        self.assertEqual(rules('Po').night_spec(g, restored[A], Night(3)).players, 3)
        night = Night(3)
        night.prior = {a.id: (a.data.get('last_night'), a.data['last']) for a in restored.instances if 'last' in a.data}
        self.assertEqual(night.before_of(restored, restored[F], 'Shabaloth'), [C, D])

    def test_G3_two_zombuuls_each_have_a_first_death(self):
        # the Summoner's second Zombuul (U7): the first one's seeming death no longer spends the second's
        g = self.game(['Zombuul', T1, T2, T3, 'Poisoner', T4, 'Soldier'], extra=['Summoner'])
        run(g.change(g.g[B], 'Zombuul', alignment='evil'))
        g.execute(A)
        self.assertTrue(g.g[A].alive and g.g[A].seems_dead)
        g.execute(B)
        self.assertTrue(g.g[B].alive and g.g[B].seems_dead)
        g.execute(A)
        self.assertFalse(g.g[A].alive)

    def test_G4_once_per_game_fresh_after_a_change_and_back(self):
        g = self.game(['Huntsman', T1, T2, T3, 'Poisoner', 'Imp', 'Soldier'], extra=['Damsel'])
        snv.use(g.g, g.g[A], 'Huntsman')
        self.assertIsNone(rules('Huntsman').night_spec(g, g.g[A], Night(2)))
        run(g.change(g.g[A], T1))
        run(g.change(g.g[A], 'Huntsman'))
        self.assertIsNotNone(rules('Huntsman').night_spec(g, g.g[A], Night(3)))
        self.assertEqual(g.g.notes['Used'][A], [])  # the view the fuzzer reads

    def test_G4_a_marionette_still_believes_its_spent_ability(self):
        # the other side: a player made the Marionette believes they are still what they were, so what they used as it
        # stays used for that belief (waking them again would tell them they changed)
        g = self.game(['Huntsman', 'Imp', T2, T3, 'Poisoner', T4, 'Soldier'], extra=['Damsel', 'Marionette'])
        snv.use(g.g, g.g[A], 'Huntsman')
        run(carousel2.make_marionette(g, g.g[A], g.g[B]))
        self.assertEqual((g.g[A].character, g.g[A].shown), ('Marionette', 'Huntsman'))
        self.assertEqual(instance(g, A, 'Huntsman').how, 'believed')
        self.assertIsNone(rules('Huntsman').night_spec(g, g.g[A], Night(3)))

    def test_G4_a_marionette_still_believes_its_records(self):
        # and what the belief recorded for its holder (Character.instance_notes) stays theirs: a Balloonist made the
        # Marionette is still told "a different character type than last night's", as before
        g = self.game(['Balloonist', 'Imp', T2, T3, 'Poisoner', T4, 'Soldier'], extra=['Marionette'])
        g.g.notes['Balloonist'] = {A: 'Townsfolk'}
        run(carousel2.make_marionette(g, g.g[A], g.g[B]))
        self.assertEqual(g.g.notes['Balloonist'], {A: 'Townsfolk'})
        run(g.change(g.g[A], T1))  # (a real change: gone)
        self.assertEqual(g.g.notes['Balloonist'], {})

    def test_G4_a_cannibals_new_meal_is_a_fresh_instance(self):
        # a gained ability is an instance of its own: the same character gained again (a later meal) starts fresh
        g = self.game(['Cannibal', T1, T2, T3, 'Poisoner', 'Imp', 'Soldier'], extra=['Philosopher'])
        g.g.set_gained(g.g[A], ['Philosopher'], 'Cannibal')
        snv.use(g.g, g.g[A], 'Philosopher')
        first = instance(g, A, 'Philosopher')
        g.g.set_gained(g.g[A], [], 'Cannibal')
        g.g.set_gained(g.g[A], ['Philosopher'], 'Cannibal')
        self.assertEqual(first.ended, 'lost')
        self.assertIsNot(instance(g, A, 'Philosopher'), first)
        self.assertFalse(snv.used(g.g, g.g[A], 'Philosopher'))

    def test_S4_stale_spent_wizard_baron_wizard(self):
        # the fuzz repro (seed 9006975): the tea party makes the Wizard the Baron, and a later one the Wizard again
        g = self.game(['Wizard', T1, T2, T3, 'Poisoner', 'Imp', 'Soldier'], extra=['Baron', 'Hatter'])
        snv.use(g.g, g.g[A], 'Wizard')
        run(g.change(g.g[A], 'Baron'))
        run(g.change(g.g[A], 'Wizard'))
        self.assertFalse(snv.used(g.g, g.g[A], 'Wizard'))
        self.assertNotIn('Wizard', g.g.notes['Used'].get(A, []))

    def test_G16_per_holder_marks_end_with_the_instance(self):
        g = self.game(['Golem', T1, T2, T3, 'Fearmonger', 'Lleech', 'Soldier'])
        g.g.notes['Golem nominated'] = [A]
        g.g.notes['Fear'] = {E: B}
        g.g.notes['Lleech lost'] = [F]
        self.assertEqual(g.nomination_limit(g.g[A]), 0)
        for name, other, back in ((A, T1, 'Golem'), (E, 'Poisoner', 'Fearmonger'), (F, 'Imp', 'Lleech')):
            run(g.change(g.g[name], other))
            run(g.change(g.g[name], back))
        self.assertEqual(g.nomination_limit(g.g[A]), 1)  # a new Golem has its own nomination
        self.assertEqual((g.g.notes['Golem nominated'], g.g.notes['Fear'], g.g.notes['Lleech lost']), ([], {}, []))
        self.assertFalse(rules('Lleech').lost(g.g, g.g[F]))

    def test_G16_balloonist_acrobat_xaan_wraith_marks_end_with_the_instance(self):
        # the same shape: a mark by player outlived a change and back, and the new instance acted on it
        g = self.game(['Balloonist', 'Acrobat', T2, T3, 'Xaan', 'Wraith', 'Soldier'], extra=['Imp', 'Poisoner'])
        g.g.notes.update({'Balloonist': {A: 'Minion'}, 'Acrobat': {B: (1, C)}, 'Xaan night': {E: 1},
                          'Wraith eyes': {F: (1, True)}})
        for name, other, back in ((A, T1, 'Balloonist'), (B, T1, 'Acrobat'), (E, 'Poisoner', 'Xaan'),
                                  (F, 'Imp', 'Wraith')):
            run(g.change(g.g[name], other))
            run(g.change(g.g[name], back))
        self.assertEqual([g.g.notes[k] for k in ('Balloonist', 'Acrobat', 'Xaan night', 'Wraith eyes')],
                         [{}, {}, {}, {}])
        self.assertFalse(rules('Xaan').ongoing(g.g, g.g[E]))  # (day 1: the old Xaan's night X would poison today)

    def test_G16_a_new_drunk_belief_has_its_own_first_shot_and_nomination(self):
        # the Mathematician/Drunk jinx's marks are the believed instance's, not the player's
        g = self.game(['Drunk', 'Drunk', T2, T3, 'Poisoner', 'Imp', 'Soldier'], extra=['Mathematician', 'Slayer',
                                                                                         'Virgin'])
        g.g[A].shown, g.g[B].shown = 'Slayer', 'Virgin'
        run(rules('Slayer').act_publicly(g, A, F))
        rules('Drunk').nominated(g, g.g[B], C)
        self.assertEqual([len(g.g.abnormal), g.g.ability(g.g[A], 'Slayer').data, g.g.ability(g.g[B], 'Virgin').data],
                         [2, {'shot': True}, {'nominated': True}])
        run(rules('Slayer').act_publicly(g, A, F))
        rules('Drunk').nominated(g, g.g[B], C)
        self.assertEqual(len(g.g.abnormal), 2)  # once each
        for name, believed in ((A, 'Slayer'), (B, 'Virgin')):
            run(g.change(g.g[name], T1))
            run(g.change(g.g[name], 'Drunk'))
            g.g[name].shown = believed
        run(rules('Slayer').act_publicly(g, A, F))
        rules('Drunk').nominated(g, g.g[B], C)
        self.assertEqual(len(g.g.abnormal), 4)  # a new belief: its own first shot and nomination

    def test_G2_revival_restores_the_instance(self):
        # the owner's question (what a revived player holds) is left open: the engine's reading is kept. The revived
        # player's own instance is the same one, fresh again; a gained ability's instance is kept as it was
        g = self.game(['Philosopher', T1, T2, T3, 'Poisoner', 'Imp', 'Soldier'], extra=['Courtier', 'Professor'])
        p = g.g[A]
        snv.use(g.g, p, 'Philosopher')
        g.g.gain(p, 'Courtier', 'Philosopher')
        snv.use(g.g, p, 'Courtier')
        own, gained = instance(g, A, 'Philosopher'), instance(g, A, 'Courtier')
        g.g.die(p)
        g.g.revive(p, 'Professor')
        self.assertIs(instance(g, A, 'Philosopher'), own)
        self.assertFalse(snv.used(g.g, p, 'Philosopher'))
        self.assertIs(instance(g, A, 'Courtier'), gained)
        self.assertEqual((gained.how, snv.used(g.g, p, 'Courtier')), ('Philosopher', True))

    def test_B3_a_drunk_believer_spends_their_belief(self):
        g = self.game(['Drunk', T1, T2, T3, 'Poisoner', 'Imp', 'Soldier'], extra=['Courtier'])
        g.g[A].shown = 'Courtier'
        quiet(self, 2, 3)
        self.as_role(2, A, 'Courtier', character=T1)
        run(g.night(2))
        run(g.night(3))
        self.assertEqual(len(woken_as(self.seats[A], 'Courtier')), 1)
        self.assertEqual(instance(g, A, 'Courtier').how, 'believed')
        self.assertFalse(g.g.is_drunk(g.g[B]))

    def test_B4_philosopher_courtier_and_courtier_each_spend_their_own(self):
        g = self.game(['Philosopher', 'Courtier', T2, T3, 'Poisoner', 'Imp', 'Soldier'])
        quiet(self, 1, 2, 3)
        self.as_role(1, A, 'Philosopher', character='Courtier')
        self.as_role(1, A, 'Courtier', character=None)
        self.as_role(1, B, 'Courtier', character=None)
        run(g.night(1))
        self.assertEqual(instance(g, A, 'Courtier').how, 'Philosopher')
        self.as_role(2, A, 'Courtier', character=T2)
        self.as_role(2, B, 'Courtier', character=T3)
        run(g.night(2))
        self.assertTrue(g.g.is_drunk(g.g[C]))
        self.assertFalse(g.g.is_drunk(g.g[D]))  # the real Courtier, drunk while the Philosopher has it
        run(g.night(3))
        self.assertEqual((len(woken_as(self.seats[A], 'Courtier')), len(woken_as(self.seats[B], 'Courtier'))), (2, 2))

    def test_B12_two_assassins_each_act(self):
        g = self.game(['Alchemist', T1, T2, T3, 'Assassin', 'Imp', 'Soldier'])
        g.g.gain(g.g[A], 'Assassin', 'Alchemist')
        self.as_role(2, A, 'Assassin', [B])
        self.as_role(2, E, 'Assassin', [C])
        self.as_role(2, F, 'Imp', [G])
        run(g.night(2))
        self.assertFalse(g.g[B].alive or g.g[C].alive)
        self.as_role(3, F, 'Imp', [G])
        run(g.night(3))
        self.assertEqual((len(woken_as(self.seats[A], 'Assassin')), len(woken_as(self.seats[E], 'Assassin'))), (1, 1))

    def test_B19_lleech_swapped_onto_a_dead_player(self):
        g = self.game(['Barber', T1, T2, T3, 'Poisoner', 'Lleech', 'Soldier'])
        g.g.notes['Lleech host'] = {F: C}
        g.g.add(State('poisoned', C, source=F, until=None, ends_with_source=True, while_source_sober=True))
        g.g.die(g.g[D])
        run(g.swap(g.g[F], g.g[D]))
        self.assertEqual((g.g[D].character, g.g.notes['Lleech host']), ('Lleech', {D: C}))
        self.assertFalse(g.g.is_poisoned(g.g[C]))  # a dead Lleech poisons nobody

    def test_B21_a_spent_assassin_ignores_another_abilitys_choice(self):
        g = self.game([T1, T2, T3, T4, 'Assassin', 'Imp', 'Soldier'], extra=['Fearmonger'])
        g.g.gain(g.g[E], 'Fearmonger', 'Plague Doctor')
        snv.use(g.g, g.g[E], 'Assassin')
        self.as_role(2, E, 'Fearmonger', [C])
        self.as_role(2, F, 'Imp', [G])
        run(g.night(2))
        self.assertTrue(g.g[C].alive)
        self.assertEqual(woken_as(self.seats[E], 'Assassin'), [])

    def test_U6_vigormortis_swapped_onto_a_dead_player(self):
        # the Vigormortis killed the Poisoner, who keeps her ability and has poisoned Casey; the Barber's swap moves
        # the Vigormortis onto dead Drew: a dead Vigormortis has no ability, so she loses hers and the poison ends.
        # (Whether the Storyteller should choose such a swap at all is the owner's, and is not changed.)
        g = self.game(['Barber', T1, T2, T3, 'Poisoner', 'Vigormortis', 'Soldier'])
        g.g.add(State('has ability', E, source=F, until=None, ends_with_source=True, while_source_works=True,
                      about='Minion'))
        g.g.die(g.g[E])
        g.g.add(State('poisoned', C, source=E, until='night', ends_with_source=True, while_source_sober=True))
        self.assertTrue(g.g.keeps_ability(g.g[E]) and g.g.is_poisoned(g.g[C]))
        g.g.die(g.g[D])
        run(g.swap(g.g[F], g.g[D]))
        self.assertEqual(g.g[D].character, 'Vigormortis')
        self.assertFalse(g.g.keeps_ability(g.g[E]))
        self.assertFalse(g.g.is_poisoned(g.g[C]))
        # a living new Vigormortis keeps them (the batch 3 ruling, unchanged)
        g = self.game(['Barber', T1, T2, T3, 'Poisoner', 'Vigormortis', 'Soldier'])
        g.g.add(State('has ability', E, source=F, until=None, ends_with_source=True, while_source_works=True,
                      about='Minion'))
        g.g.die(g.g[E])
        run(g.swap(g.g[F], g.g[D]))
        self.assertTrue(g.g.keeps_ability(g.g[E]))


# ---- family 2: two ways to change a character -----------------------------------------------------------------

class ChangePathTests(Test):
    def test_G1_scarlet_woman_takes_over_a_fresh_zombuul(self):
        g = self.game(['Zombuul', 'Scarlet Woman', T1, T2, T3, T4, 'Soldier'])
        g.execute(A)
        g.execute(A)  # the second death is real
        self.assertEqual(g.g[B].character, 'Zombuul')
        self.assertEqual(instance(g, B, 'Zombuul').how, 'changed')
        g.execute(B)  # her own first death only seems
        self.assertTrue(g.g[B].alive and g.g[B].seems_dead)

    def test_G1_scarlet_woman_yaggababble_learns_a_phrase(self):
        g = self.game(['Yaggababble', 'Scarlet Woman', T1, T2, T3, T4, 'Soldier'])
        g.execute(A)
        run(g.run_pending())  # (its `becomes` consults the Storyteller: at the next safe point)
        self.assertEqual(g.g[B].character, 'Yaggababble')
        self.assertIn(B, g.g.notes.get('Yaggababble', {}))
        self.assertTrue(any('your secret phrase is' in e['data']['text'] for e in g.events
                            if e['to'] == [B] and e['kind'] == 'info'))

    def test_G1_imp_starpass_runs_the_change_hooks(self):
        g = self.game(['Imp', T1, T2, T3, 'Poisoner', T4, 'Soldier'])
        seen = []
        orig = type(rules(T1)).changed
        type(rules(T1)).changed = lambda self, game, me, other: seen.append((me.name, other.name))
        try:
            self.as_role(2, A, 'Imp', [A])
            self.as_role(2, E, 'Poisoner', [G])
            run(g.night(2))
        finally:
            type(rules(T1)).changed = orig
        self.assertEqual(g.g[E].character, 'Imp')
        self.assertIn((B, E), seen)  # everyone's `changed` heard of the new Imp
        self.assertEqual(instance(g, E, 'Imp').how, 'changed')
        self.assertIsNone(instance(g, E, 'Poisoner'))

    def test_G11_a_seeming_zombuul_changed_is_dead(self):
        g = self.game(['Zombuul', T1, T2, T3, 'Poisoner', T4, 'Soldier'], extra=['Po'])
        g.execute(A)
        self.assertTrue(g.g[A].seems_dead)
        run(g.change(g.g[A], 'Po'))
        self.assertFalse(g.g[A].alive or g.g[A].seems_dead)
        self.assertFalse([d for d in g.g.death_log if d['player'] == A and d.get('seems')])

    def test_S3_barber_swaps_a_seeming_zombuul(self):
        g = self.game(['Zombuul', T1, T2, T3, 'Poisoner', 'Barber', 'Soldier'])
        g.execute(A)
        run(g.swap(g.g[A], g.g[B]))
        self.assertEqual((g.g[A].character, g.g[B].character), (T1, 'Zombuul'))
        self.assertFalse(g.g[A].alive or g.g[A].seems_dead)  # dead, as the town believes
        self.assertTrue(g.g[B].alive and not g.g[B].seems_dead)
        g.execute(B)  # the new Zombuul has a first death of its own (the Barber's fresh ability, as before)
        self.assertTrue(g.g[B].alive and g.g[B].seems_dead)

    def test_U16_marionette_seat_swap_moves_the_gained_ability(self):
        g = self.game(['Alchemist', 'Marionette', T2, T3, 'Poisoner', 'Imp', 'Soldier'])
        g.g.gain(g.g[A], 'Spy', 'Alchemist')
        g.g.notes['Alchemist'] = {A: 'Spy'}
        g.g.swap_seats(g.g[B], g.g[A])  # the Marionette (Blair) takes Alex's seat beside the Demon
        self.assertEqual((g.g[A].character, g.g[A].extra), ('Marionette', []))
        self.assertEqual((g.g[B].character, g.g[B].extra), ('Alchemist', ['Spy']))
        self.assertEqual(instance(g, B, 'Spy').how, 'Alchemist')
        self.assertIsNone(instance(g, A, 'Spy'))
        self.assertEqual(g.g.notes['Alchemist'], {B: 'Spy'})
        self.assertEqual(g.g.abilities(g.g[A]), ['Marionette'])

    def test_U16_marionette_setup_uses_the_seat_swap(self):
        g = self.dealt(['Marionette', T1, 'Alchemist', 'Imp', T2, T3, 'Soldier'],
                       forced={'Marionette seat': {'players': [C]}, 'Alchemist:': {'character': 'Witch'}},
                       extra=['Witch'])
        m = next(p for p in g.g.players if p.character == 'Marionette')
        self.assertEqual(m.name, C)
        self.assertEqual(m.extra, [])
        self.assertEqual(g.g[A].character, 'Alchemist')
        self.assertEqual(g.g[A].extra, ['Witch'])  # (it was Casey's, the Alchemist's seat, before the swap)
        self.assertEqual(g.g.notes['Alchemist'], {A: 'Witch'})

    def test_B11_a_setup_step_never_takes_the_alchemist(self):
        g = self.game(['Alchemist', 'Balloonist', 'Poisoner', 'Imp', 'Saint'], extra=['Recluse'])
        self.assertFalse(carousel2.add_outsider(g, g.g[B]))  # the Alchemist (whose step has run) is not taken
        self.assertEqual(g.g[A].character, 'Alchemist')

    def test_B13_a_dead_lycanthrope_places_no_faux_paw(self):
        g = self.game(['Lycanthrope', T1, T2, T3, 'Poisoner', 'Imp', 'Soldier'])
        g.g.die(g.g[A])
        run(rules('Lycanthrope').paw(g, g.g[A]))
        self.assertFalse([s for s in g.g.states if s.kind == 'registers evil'])

    def test_B18_bounty_hunter_turns_a_townsfolk_evil_before_the_good_picks(self):
        order = [c.name for c in self.script(['Bounty Hunter', 'Grandmother', 'Fortune Teller', 'Evil Twin',
                                              'Lycanthrope'], True).setup_steps]
        bh = order.index('Bounty Hunter')
        self.assertTrue(all(bh < order.index(c) for c in ('Grandmother', 'Evil Twin', 'Lycanthrope')))
        g = self.dealt(['Bounty Hunter', 'Grandmother', T1, T2, 'Poisoner', 'Imp', 'Soldier'])
        self.assertFalse(g.g[g.g.notes['Grandchild']].evil)
        self.assertFalse(g.g[g.g.red_herring].evil if g.g.red_herring else False)

    def test_U1_undertaker_after_a_change(self):
        # the owner's question (the character they died as, or the one now) is left open: the engine still shows
        # the current character; the death log now records the one they died as, for the owner's ruling
        g = self.game(['Undertaker', T1, T2, T3, 'Pit-Hag', 'Imp', 'Soldier'], extra=['Goon'])
        g.execute(B)
        run(g.change(g.g[B], 'Goon'))
        self.assertEqual(next(d for d in g.g.death_log if d['player'] == B)['as'], T1)
        self.assertEqual(rules('Undertaker').information(g, g.g[A], None)[0].values, [{
            'players': [], 'character': 'Goon', 'number': None, 'yes': None, 'characters': []}])

    def test_U13_make_marionette_takes_the_one_path(self):
        # the owner's question (may a dead neighbour become the Marionette?) is left open: a dead one may still be
        # chosen. The change itself is the one path: a fresh instance, the change hooks
        g = self.game([T1, 'Imp', T2, T3, 'Poisoner', T4, 'Soldier'], extra=['Marionette', 'Plague Doctor'])
        g.g.die(g.g[A])
        seen = []
        orig = type(rules(T2)).changed
        type(rules(T2)).changed = lambda self, game, me, other: seen.append(other.name)
        try:
            run(carousel2.make_marionette(g, g.g[A], g.g[B]))
        finally:
            type(rules(T2)).changed = orig
        self.assertEqual((g.g[A].character, g.g[A].shown, g.g[A].alive), ('Marionette', T1, False))
        self.assertEqual(seen, [A])
        self.assertEqual(instance(g, A, 'Marionette').how, 'changed')
        pool = [q.name for q in carousel2.seat_neighbours(g.g, g.g[B]) if not q.evil]
        self.assertIn(C, pool)


# ---- G13 (the sobriety predicate) and S2 (the Organ Grinder's secret tally) ------------------------------------------

class OtherTests(Test):
    def test_G13_a_drunk_spy_or_recluse_registers_truly(self):
        g = self.game(['Recluse', 'Spy', T2, T3, 'Sailor', 'Imp', 'Soldier'])
        for name in (A, B):
            g.g.add(State('drunk', name, source=E, until=None))
        self.assertEqual(g.g.registers_evil(g.g[A]), {False})
        self.assertEqual(g.g.registers_as(g.g[A]), {'Recluse'})
        self.assertEqual(rules('Recluse').registers_demon_to_ft(g.g, g.g[A]), {False})
        self.assertEqual((g.g.registers_evil(g.g[B]), g.g.registers_as(g.g[B])), ({True}, {'Spy'}))
        import random
        r = random.Random(1)
        for _ in range(50):
            self.assertNotIn(A, g.g.sample_evil(r))
            self.assertIn(B, g.g.sample_evil(r))

    def test_G13_a_drunk_slayer_or_imp_does_not_act(self):
        # made drunk by an ability (the Sailor's, the Innkeeper's): "drunk or poisoned", as a poisoned one
        g = self.game(['Slayer', T1, T2, T3, 'Sailor', 'Imp', 'Soldier'])
        g.g.add(State('drunk', A, source=E, until=None))
        self.assertFalse(run(rules('Slayer').act_publicly(g, A, F)))
        self.assertTrue(g.g[F].alive)
        self.assertTrue(g.g.spent_ability('Slayer', g.g[A]))  # (the shot is spent all the same)
        g.g.add(State('drunk', F, source=E, until=None))
        self.as_role(2, F, 'Imp', [B])
        self.as_role(2, E, 'Sailor', [C])
        run(g.night(2))
        self.assertTrue(g.g[B].alive)

    def test_S2_organ_grinder_secret_tally_stays_secret(self):
        # a secret vote puts Casey on the block with 5; the Organ Grinder (Ellis) is then poisoned, and two public votes
        # follow: Drew gets none, Gray ties at 5. Nothing public, and no prompt, may show the secret 5 (as the votes
        # needed beyond the majority of 4, a tie, a block or a replaced block)
        from clocktower.render import render
        g = self.game([T1, T2, T3, T4, 'Organ Grinder', 'Imp', 'Soldier'])
        for name in (A, B, C, D, G):
            self.seats[name].day['vote'] = [{'vote': True}, {'vote': False}, {'vote': True}]
        block, top = run(g.vote(C, None, 0))
        self.assertEqual((block, top, g.secret_day), (C, 5, g.day))
        g.g.add(State('poisoned', E, source=F, until=None))
        self.assertFalse(g.secret_votes())
        start = len(g.events)
        block, top = run(g.vote(D, block, top))
        block, top = run(g.vote(G, block, top))
        self.assertEqual((block, top), (None, 5))  # (the tie: the Storyteller's tally is kept)
        public = [render(e, 'public', set()) for e in g.events[start:] if e['to'] == 'public']
        self.assertTrue([t for t in public if 'Gray received 5 votes' in t])  # (the hands raised are seen)
        prompts = [r.prompt for s in self.seats.values() for r in s.log if r.kind in ('vote', 'nominate')]
        for text in public + prompts:
            for leak in ('6 needed', 'It takes 6', 'ties the leader', 'about to be executed.', '(replacing ',
                         'is on the block with', 'of an earlier tied vote', 'an earlier vote tied at', 'who has 5'):
                self.assertNotIn(leak, text)
        g = self.game([T1, T2, T3, T4, 'Poisoner', 'Imp', 'Soldier'])  # without one, as before
        run(g.vote(C, B, 4))
        self.assertTrue([r for s in self.seats.values() for r in s.log if r.kind == 'vote'
                         and '(replacing Blair, who has 4)' in r.prompt])
        self.assertTrue([e for e in g.events if e['kind'] == 'vote_result' and e['to'] == 'public'
                         and render(e, 'public', set()) == 'Casey received 0 votes (5 needed).'])

if __name__ == '__main__':
    unittest.main()
