"""Replay fingerprints: proof that a change to the engine leaves play unchanged.

A fingerprint is a hash of everything a game produces for a seed, played by random bots with no API calls:
every event (with who could see it), every text and request each seat received, and the result. If the
engine, the Storyteller or the prompts change how a game plays, the fingerprint changes. CONTRIBUTING.md
asks harness changes to show that a seed replays identically; `python -m clocktower fingerprint --check`
does it for a fixed set of games across every table size and Minion (tests/data/fingerprints.json).

    python -m clocktower fingerprint --check            # compare every game with the recorded set
    python -m clocktower fingerprint --write            # re-record (only for a deliberate change of play)
    python -m clocktower fingerprint --check --script bmr   # Bad Moon Rising's recorded set
"""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import json
import random
import sys
from pathlib import Path

from .agents import RandomSeat
from .characters import TB, Script
from .game import ALL_NAMES, Game

DATA = Path(__file__).resolve().parent.parent / 'tests' / 'data'
FILE = DATA / 'fingerprints.json'  # Trouble Brewing's (protocol v17)


def file_for(script):
    return FILE if script.id == 'tb' else DATA / f'fingerprints-{script.id}.json'
SIZES = range(5, 16)
SEEDS_PER_SIZE = 100


class _Recorder:
    """A random bot that also records what it was shown and asked."""

    def __init__(self, seat, log, extra=False):
        self.seat, self.log, self.extra = seat, log, extra

    async def act(self, text, request):
        entry = [self.seat.name, text, request.kind, request.prompt, request.day, request.beat,
                 request.n_targets, list(request.options), request.alive, request.mode]
        if self.extra:  # the request fields beyond Trouble Brewing's (TB's recorded set predates them)
            entry += [request.min_targets, list(request.characters), list(getattr(request, 'claimable', []))]
        self.log.append(entry)
        return await self.seat.act(text, request)


def games(script=TB):
    """The recorded set: every table size from 5 to 15, a hundred seeds each, the guaranteed Minion
    rotating with the seed as in a batch."""
    return [{'players': n, 'seed': s, 'minion': script.minions[s % len(script.minions)]}
            for n in SIZES for s in range(n * 1000, n * 1000 + SEEDS_PER_SIZE)]


def play(players, seed, minion=None, characters=None, script=TB):
    """(fingerprint, summary) of one random-bot game."""
    names = ALL_NAMES[:len(characters) if characters else players]
    log = []
    rng = random.Random(seed + 1)  # the same bots as `run --model random` and `sim`
    seats = {n: _Recorder(RandomSeat(n, random.Random(rng.random()), names), log, extra=script.id != 'tb')
             for n in names}
    game = Game(seats, None, names=names, seed=seed, minion=minion, characters=characters, probes=False,
                script=script)
    try:
        result = asyncio.run(game.run())
        result = {k: v for k, v in result.items() if k != 'seconds'}
    except Exception as e:  # a crash is part of how this seed plays: record it, so a fix shows up as a change
        result = {'crash': f'{type(e).__name__}: {e}', 'winner': None, 'days': game.day,
                  'starting': game.starting or {}}
    events = [{k: v for k, v in ev.items() if k != 'time'} for ev in game.events]
    blob = json.dumps({'events': events, 'seats': log, 'result': result}, sort_keys=True, ensure_ascii=False)
    summary = {'winner': result['winner'], 'days': result['days'], 'starting': sorted(result['starting'].values())}
    if 'crash' in result:
        summary['crash'] = result['crash']
    return hashlib.sha256(blob.encode()).hexdigest(), summary


def main(argv=None):
    ap = argparse.ArgumentParser(prog='clocktower fingerprint', description=__doc__.split('\n\n')[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true', help='compare with the recorded fingerprints')
    mode.add_argument('--write', action='store_true', help='record fingerprints for the current engine')
    ap.add_argument('--script', default='tb', help='tb (the default) or bmr')
    ap.add_argument('--file', help='the recorded set (default: tests/data/fingerprints[-SCRIPT].json)')
    ap.add_argument('--limit', type=int, help='only the first N games (a quick check)')
    args = ap.parse_args(argv)
    script = Script(args.script)
    todo = games(script)[:args.limit] if args.limit else games(script)
    path = Path(args.file) if args.file else file_for(script)
    if args.write:
        out = []
        for i, g in enumerate(todo, 1):
            sha, summary = play(**g, script=script)
            out.append({**g, 'sha': sha, **summary})
            if i % 100 == 0:
                print(f'{i}/{len(todo)}', file=sys.stderr)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'games': out}, indent=0) + '\n')
        print(f'wrote {len(out)} fingerprints to {path}')
        return 0
    recorded = {(g['players'], g['seed']): g for g in json.loads(path.read_text())['games']}
    bad = []
    for i, g in enumerate(todo, 1):
        sha, _ = play(**g, script=script)
        if recorded[(g['players'], g['seed'])]['sha'] != sha:
            bad.append(g)
        if i % 100 == 0:
            print(f'{i}/{len(todo)} checked, {len(bad)} differ', file=sys.stderr)
    for g in bad[:20]:
        print(f"DIFFERS: {g['players']} players, seed {g['seed']}, minion {g['minion']}")
    print(f'{len(todo) - len(bad)}/{len(todo)} games replay identically')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
