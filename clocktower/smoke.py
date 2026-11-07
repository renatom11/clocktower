"""Smoke runs: random-bot games of a script at every table size, to show it plays end to end with no crash.

Each game is played by random bots (no API calls), with the guaranteed Minion rotating with the seed as in a batch,
under the scripted Storyteller and under the rules judge. A crash is a bug to fix (or, for a setup that cannot be
dealt, a rules impossibility to report clearly). `--corpus` runs every script under a directory of custom scripts
(`*/script.json`, default $CLOCKTOWER_SCRIPTS) whose characters are all built, and lists the others with what they
still need.

    python -m clocktower smoke --script carousel-1             # 100 games per size 5-15, scripted and rules judge
    python -m clocktower smoke --corpus                        # every corpus script whose characters are all built
    python -m clocktower smoke --script snv --games 10 --judge rules --sizes 5-7
"""
from __future__ import annotations
import argparse
import asyncio
import os
import random
import sys
import time
import traceback
from pathlib import Path

from . import judge
from .agents import RandomSeat
from .characters import Script
from .game import ALL_NAMES, Game

CORPUS = Path('/workspace/thepandemoniuminstitute/botc-release/wc25')
SEED_BASE = 7_000_000  # away from the recorded fingerprints' seeds


def corpus_dir():
    return Path(os.environ.get('CLOCKTOWER_SCRIPTS') or CORPUS)


def corpus(root=None):
    """[(path, Script or the ValueError saying what is not built)] for every `*/script.json` under `root`."""
    out = []
    for path in sorted(Path(root or corpus_dir()).glob('*/script.json')):
        try:
            out.append((path, Script(path)))
        except ValueError as e:
            out.append((path, e))
    return out


def play(script, players, seed, mode='scripted'):
    """Play one random-bot game; returns its result (a crash raises)."""
    names = ALL_NAMES[:players]
    rng = random.Random(seed + 1)
    seats = {n: RandomSeat(n, random.Random(rng.random()), names) for n in names}
    game = Game(seats, None, names=names, seed=seed, minion=script.minions[seed % len(script.minions)],
                probes=False, script=script, judge=judge.make(mode))
    return asyncio.run(game.run())


def smoke(script, games=100, sizes=range(5, 16), modes=('scripted', 'rules'), out=sys.stdout):
    """Play `games` games per size and mode; returns the crashes, [(mode, players, seed, traceback)]."""
    crashes = []
    for mode in modes:
        start, wins = time.time(), {'good': 0, 'evil': 0, None: 0}
        for n in sizes:
            for i in range(games):
                seed = SEED_BASE + n * 1000 + i
                try:
                    wins[play(script, n, seed, mode)['winner']] += 1
                except Exception:
                    crashes.append((mode, n, seed, traceback.format_exc()))
        total = games * len(sizes)
        print(f'{script.name} ({script.id}), {mode}: {total - len([c for c in crashes if c[0] == mode])}/{total} '
              f'games with no crash (good {wins["good"]}, evil {wins["evil"]}, unfinished {wins[None]}; '
              f'{time.time() - start:.0f}s)', file=out)
    for mode, n, seed, tb in crashes[:10]:
        print(f'CRASH: {mode}, {n} players, seed {seed}\n{tb}', file=out)
    return crashes


def sizes_of(text):
    a, _, b = text.partition('-')
    return range(int(a), int(b or a) + 1)


def main(argv=None):
    ap = argparse.ArgumentParser(prog='clocktower smoke', description=__doc__.split('\n\n')[0])
    which = ap.add_mutually_exclusive_group(required=True)
    which.add_argument('--script', help='a built-in script id (tb, bmr, snv, carousel-1) or a script JSON')
    which.add_argument('--corpus', nargs='?', const='', metavar='DIR',
                       help='every */script.json under DIR (default $CLOCKTOWER_SCRIPTS, else the wc25 corpus)')
    ap.add_argument('--games', type=int, default=100, help='games per table size and Storyteller mode')
    ap.add_argument('--sizes', default='5-15', help='table sizes, e.g. 5-15 or 7')
    ap.add_argument('--judge', default='scripted,rules', help='Storyteller modes: scripted, rules or both')
    args = ap.parse_args(argv)
    modes, sizes = args.judge.split(','), sizes_of(args.sizes)
    if args.script:
        scripts = [Script(args.script)]
    else:
        scripts = []
        for path, s in corpus(args.corpus or None):
            if isinstance(s, Script):
                scripts.append(s)
            else:
                print(f'{path.parent.name}: skipped, {s}')
    crashes = [c for s in scripts for c in smoke(s, args.games, sizes, modes)]
    return 1 if crashes else 0


if __name__ == '__main__':
    sys.exit(main())
