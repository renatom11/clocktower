"""Batch 6's five removable characters (clocktower/carousel_extra.py) can each be switched off, and all five at once:
CLOCKTOWER_WITHOUT=<id>[,<id>...] (or `python -m clocktower --without ...`) builds the engine without them.

For each of the five, and for all five together, a subprocess with the switch set checks: the engine imports; the
character is absent from CHARACTERS (and its jinxes, Storyteller's weights and notes with it) while the others stay;
its synthetic script and every corpus script naming it say it is not built, with the message any unbuilt character
gets; a sample of the recorded seeds of every other script still replays identically (TB, BMR, S&V, carousel-1..7
and the synthetic scripts of the characters still built); and a fast subset of the test suite passes, the switched-off
character's tests skipped. The full suite and the full fingerprint check under each switch are run by hand (docs/
readiness.md, "Removing a batch 6 character").

Skipped when CLOCKTOWER_WITHOUT is already set: it tests switching off from the full build."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAMES = {'lilmonsta': "Lil' Monsta", 'atheist': 'Atheist', 'wizard': 'Wizard', 'legion': 'Legion', 'riot': 'Riot'}
CASES = [(cid,) for cid in NAMES] + [tuple(NAMES)]
STEP = 100  # every 100th recorded seed: 11 games a script, every table size

PROBE = r'''
import json, sys, unittest
from pathlib import Path
from clocktower import carousel_extra, characters as ch, fingerprint, judge, official, smoke
from clocktower.state import POLICY

off, step = set(json.loads(sys.argv[1])), int(sys.argv[2])
names = {"lilmonsta": "Lil' Monsta", "atheist": "Atheist", "wizard": "Wizard", "legion": "Legion", "riot": "Riot"}
out = {"without": sorted(carousel_extra.WITHOUT), "built": sorted(n for n in names.values() if n in ch.CHARACTERS),
       "jinxes": sorted({c for pair in ch.IMPLEMENTED_JINXES for c in pair} & set(names.values())),
       "policy": sorted(k for k in POLICY if k.split("_")[0] in names),
       "notes": [n for n in names.values() if judge.storyteller_notes("x", [n])],
       "scripts": {}, "corpus": {}, "replays": {}}
gone = {names[c] for c in off}


def wanting(source):
    return sorted(gone & {e["name"] for e in official.script_entries(source)["entries"]})


for path in sorted(official.SCRIPTS.glob("*.json")):
    try:
        ch.Script(path)
        out["scripts"][path.stem] = {"needs": wanting(path), "error": None}
    except ValueError as e:
        out["scripts"][path.stem] = {"needs": wanting(path), "error": str(e)}
for path in sorted(smoke.corpus_dir().glob("*/script.json")):
    if wanting(path):
        try:
            ch.Script(path)
            out["corpus"][path.parent.name] = {"needs": wanting(path), "error": None}
        except ValueError as e:
            out["corpus"][path.parent.name] = {"needs": wanting(path), "error": str(e)}
for sid, r in out["scripts"].items():
    if r["error"] is None and fingerprint.file_for(ch.Script(sid)).exists():
        s = ch.Script(sid)
        games = json.loads(fingerprint.file_for(s).read_text())["games"][::step]
        out["replays"][sid] = [len(games), sum(fingerprint.play(g["players"], g["seed"], g["minion"], script=s)[0]
                                              == g["sha"] for g in games)]
sys.path.insert(0, "tests")
mods = ["test_carousel_extra", "test_carousel.JinxFrameworkTests", "test_lifecycle",
        "examples.test_carousel_extra_examples"] + [f"test_carousel_{c}" for c in names]
res = unittest.TextTestRunner(stream=open("/dev/null", "w")).run(unittest.defaultTestLoader.loadTestsFromNames(mods))
out["suite"] = {"run": res.testsRun, "failed": [str(t) for t, _ in res.failures + res.errors],
                "skipped": [str(t) for t, _ in res.skipped]}
print(json.dumps(out))
'''


@unittest.skipIf(os.environ.get('CLOCKTOWER_WITHOUT'), 'already switched off: this tests switching from the full build')
class SwitchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        procs = {}
        for case in CASES:  # (all at once: a few seconds each)
            env = {**os.environ, 'CLOCKTOWER_WITHOUT': ','.join(case)}
            procs[case] = subprocess.Popen([sys.executable, '-c', PROBE, json.dumps(case), str(STEP)], cwd=ROOT,
                                           env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        cls.results = {}
        for case, p in procs.items():
            stdout, stderr = p.communicate(timeout=600)
            cls.results[case] = (p.returncode, stdout, stderr)

    def result(self, case):
        code, stdout, stderr = self.results[case]
        self.assertEqual(code, 0, f'CLOCKTOWER_WITHOUT={",".join(case)}: the engine did not load or the probe failed:'
                                  f'\n{stderr[-3000:]}')
        return json.loads(stdout.strip().splitlines()[-1])

    def check(self, case):
        r = self.result(case)
        gone = {NAMES[c] for c in case}
        self.assertEqual(r['without'], sorted(case))
        self.assertEqual(set(r['built']), set(NAMES.values()) - gone)  # absent; the others still built
        self.assertFalse(gone & set(r['jinxes']), 'a switched-off character still has a jinx declared')
        weighted = {k.split('_')[0] for k in r['policy']}
        self.assertFalse(weighted & set(case), 'its Storyteller weights remain')
        self.assertEqual(weighted, {'lilmonsta', 'atheist', 'wizard', 'legion'} - set(case))  # (Riot has none)
        self.assertEqual(set(r['notes']), set(NAMES.values()) - gone)  # its Storyteller's notes go too
        needing = 0
        for where in ('scripts', 'corpus'):
            for sid, s in r[where].items():
                if s['needs']:  # names a switched-off character: not built, as any unbuilt character says
                    needing += 1
                    self.assertIsNotNone(s['error'], f'{sid} loaded without {s["needs"]}')
                    self.assertIn('characters not implemented yet: ', s['error'], sid)
                    for name in s['needs']:
                        self.assertIn(name, s['error'], sid)
                elif where == 'scripts':
                    self.assertIsNone(s['error'], f'{sid} no longer loads: {s["error"]}')
        self.assertGreaterEqual(needing, len(case))  # (each has a synthetic script of its own)
        must = {'tb', 'bmr', 'snv'} | {f'carousel-{n}' for n in range(1, 8)}
        self.assertLessEqual(must, set(r['replays']))
        for sid, (n, same) in r['replays'].items():
            self.assertEqual(same, n, f'{sid}: {n - same} of {n} sampled recorded seeds replay differently')
        self.assertEqual(r['suite']['failed'], [])
        self.assertGreater(r['suite']['run'], 50)
        for c in case:  # its own tests were skipped, not run
            self.assertTrue(any(f'test_carousel_{c}' in t for t in r['suite']['skipped']), c)
        return r

    def test_without_lil_monsta(self):
        self.check(('lilmonsta',))

    def test_without_the_atheist(self):
        r = self.check(('atheist',))
        self.assertIn('Riot', r['built'])  # (Riot stays, without its jinx with the Atheist)

    def test_without_the_wizard(self):
        self.check(('wizard',))

    def test_without_legion(self):
        self.check(('legion',))

    def test_without_riot(self):
        self.check(('riot',))

    def test_without_all_five(self):
        r = self.check(tuple(NAMES))
        self.assertEqual(r['built'], [])
        self.assertEqual(r['jinxes'], [])

    def test_an_unknown_id_is_refused(self):
        env = {**os.environ, 'CLOCKTOWER_WITHOUT': 'lilmonsta,nobody'}
        p = subprocess.run([sys.executable, '-c', 'import clocktower.state'], cwd=ROOT, env=env, capture_output=True,
                           text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("'nobody' is not one of", p.stderr)

    def test_the_command_line_option_sets_the_switch(self):
        env = {k: v for k, v in os.environ.items() if k != 'CLOCKTOWER_WITHOUT'}
        p = subprocess.run([sys.executable, '-m', 'clocktower', '--without', 'riot,legion', 'smoke', '--script',
                            'carousel-12'], cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('characters not implemented yet: Riot', p.stderr)

    def test_the_ids_parse(self):
        from clocktower import carousel_extra
        self.assertEqual(carousel_extra.switched_off(''), frozenset())
        self.assertEqual(carousel_extra.switched_off("Lil' Monsta, RIOT"), {'lilmonsta', 'riot'})
        self.assertEqual(carousel_extra.switched_off('all'), set(NAMES))
        self.assertEqual(set(carousel_extra.IDS), set(NAMES))


if __name__ == '__main__':
    unittest.main()
